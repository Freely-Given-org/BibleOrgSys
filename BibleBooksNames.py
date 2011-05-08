#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# BibleBooksNames.py
#
# Module handling BibleBooksNames_*.xml to produce C and Python data tables
#   Last modified: 2011-04-25 (also update versionString below)
#
# Copyright (C) 2010-2011 Robert Hunt
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
Module handling BibleBooksNames_*.xml to produce C and Python data tables.
"""

progName = "Bible Books Names Systems handler"
versionString = "0.33"


import os, logging
from gettext import gettext as _
from collections import OrderedDict
from xml.etree.cElementTree import ElementTree

from singleton import singleton

import Globals
from BibleBooksCodes import BibleBooksCodes
from ISO_639_3_Languages import ISO_639_3_Languages


@singleton # Can only ever have one instance
class _BibleBooksNamesConverter:
    """
    A class to handle data for Bible booksNames systems.
    """

    def __init__( self ):
        """
        Constructor.
        """
        self.filenameBase = "BibleBooksNames"

        # These fields are used for parsing the XML
        self.treeTag = "BibleBooksNames"
        self.headerTag = "header"
        self.mainElementTags = ( "BibleDivisionNames", "BibleBooknameLeaders", "BibleBookNames" )

        # These fields are used for automatically checking/validating the XML
        #   0,1,2 = entries for the three mainElementTags above
        self.compulsoryAttributes = { 0:("standardAbbreviation",), 1:("standardLeader",), 2:("referenceAbbreviation",) }
        self.optionalAttributes = { 0:(), 1:(), 2:() }
        self.uniqueAttributes = {}
        for key in self.compulsoryAttributes.keys():
            self.uniqueAttributes[key] = self.compulsoryAttributes[key] + self.optionalAttributes[key]
        self.compulsoryElements = { 0:("defaultName","defaultAbbreviation","includesBook",), 1:("inputAbbreviation",), 2:("defaultName","defaultAbbreviation",) }
        self.optionalElements =  { 0:("inputAbbreviation",), 1:(), 2:("inputAbbreviation",) }
        self.uniqueElements = { 0:("defaultName","defaultAbbreviation","inputAbbreviation",), 1:("inputAbbreviation",), 2:("defaultName","defaultAbbreviation","inputAbbreviation",) }

        # These are fields that we will fill later
        self.__XMLSystems, self.__BookNamesSystemsDict, self.__expandedInputSystems = {}, {}, {}

        # Get the data tables that we need for proper checking
        self.__BibleBooksCodes = BibleBooksCodes().loadData()
        self.__ISOLanguages = ISO_639_3_Languages().loadData() if Globals.strictCheckingFlag else None
    # end of __init__

    def loadSystems( self, folder=None ):
        """
        Load and pre-process the specified booksNames systems.
        """
        if not self.__XMLSystems: # Only ever do this once
            if folder==None: folder = os.path.join( os.path.dirname(__file__), "DataFiles", "BookNames" ) # Relative to module, not cwd
            if Globals.verbosityLevel > 2: print( _("Loading book names systems from {}...").format( folder ) )
            for filename in os.listdir( folder ):
                filepart, extension = os.path.splitext( filename )
                if extension.upper() == '.XML' and filepart.upper().startswith(self.filenameBase.upper()+"_"):
                    booksNamesSystemCode = filepart[len(self.filenameBase)+1:]
                    if Globals.verbosityLevel > 3: print( _("Loading {} books names system from {}...").format( booksNamesSystemCode, filename ) )
                    self.__XMLSystems[booksNamesSystemCode] = {}
                    self.__XMLSystems[booksNamesSystemCode]["languageCode"] = booksNamesSystemCode.split('_',1)[0]
                    self.__XMLSystems[booksNamesSystemCode]["tree"] = ElementTree().parse( os.path.join( folder, filename ) )
                    assert( self.__XMLSystems[booksNamesSystemCode]["tree"] ) # Fail here if we didn't load anything at all

                    # Check and remove the header element
                    if self.__XMLSystems[booksNamesSystemCode]["tree"].tag  == self.treeTag:
                        header = self.__XMLSystems[booksNamesSystemCode]["tree"][0]
                        if header.tag == self.headerTag:
                            self.__XMLSystems[booksNamesSystemCode]["header"] = header
                            self.__XMLSystems[booksNamesSystemCode]["tree"].remove( header )
                            if len(header)>1:
                                logging.info( _("Unexpected elements in header") )
                            elif len(header)==0:
                                logging.info( _("Missing work element in header") )
                            else:
                                work = header[0]
                                if work.tag == "work":
                                    self.__XMLSystems[booksNamesSystemCode]["version"] = work.find("version").text
                                    self.__XMLSystems[booksNamesSystemCode]["date"] = work.find("date").text
                                    self.__XMLSystems[booksNamesSystemCode]["title"] = work.find("title").text
                                else:
                                    logging.warning( _("Missing work element in header") )
                        else:
                            logging.warning( _("Missing header element (looking for '{}' tag)").format( headerTag ) )
                    else:
                        logging.error( _("Expected to load '{}' but got '{}'").format( self.treeTag, self.__XMLSystems[booksNamesSystemCode]["tree"].tag ) )
                    bookCount = 0 # There must be an easier way to do this
                    for subelement in self.__XMLSystems[booksNamesSystemCode]["tree"]:
                        bookCount += 1
                    logging.info( _("    Loaded {} books").format( bookCount ) )

                    if Globals.strictCheckingFlag:
                        self.__validateSystem( booksNamesSystemCode )
        return self
    # end of loadSystems

    def __validateSystem( self, systemName ):
        """
        Checks for basic formatting/content errors in a Bible book name system.
        """
        assert( systemName )
        assert( self.__XMLSystems[systemName]["tree"] )

        if len(self.__XMLSystems[systemName]["languageCode"]) != 3:
            logging.error( _("Couldn't find 3-letter language code in '{}' book names system").format( systemName ) )
        if self.__ISOLanguages and not self.__ISOLanguages.isValidLanguageCode( self.__XMLSystems[systemName]["languageCode"] ): # Check that we have a valid language code
            logging.error( _("Unrecognized '{}' ISO-639-3 language code in '{}' book names system").format( self.__XMLSystems[systemName]["languageCode"], systemName ) )

        uniqueDict = {}
        for index in range( 0, len(self.mainElementTags) ):
            for elementName in self.uniqueElements[index]: uniqueDict["Element_"+str(index)+"_"+elementName] = []
            for attributeName in self.uniqueAttributes[index]: uniqueDict["Attribute_"+str(index)+"_"+attributeName] = []

        expectedID = 1
        for k,element in enumerate(self.__XMLSystems[systemName]["tree"]):
            if element.tag in self.mainElementTags:
                index = self.mainElementTags.index( element.tag )

                # Check compulsory attributes on this main element
                for attributeName in self.compulsoryAttributes[index]:
                    attributeValue = element.get( attributeName )
                    if attributeValue is None:
                        logging.error( _("Compulsory '{}' attribute is missing from {} element in record {} in {}").format( attributeName, element.tag, k, systemName ) )
                    if not attributeValue:
                        logging.warning( _("Compulsory '{}' attribute is blank on {} element in record {} in {}").format( attributeName, element.tag, k, systemName ) )

                # Check optional attributes on this main element
                for attributeName in self.optionalAttributes[index]:
                    attributeValue = element.get( attributeName )
                    if attributeValue is not None:
                        if not attributeValue:
                            logging.warning( _("Optional '{}' attribute is blank on {} element in record {} in {}").format( attributeName, element.tag, k, systemName ) )

                # Check for unexpected additional attributes on this main element
                for attributeName in element.keys():
                    attributeValue = element.get( attributeName )
                    if attributeName not in self.compulsoryAttributes[index] and attributeName not in self.optionalAttributes[index]:
                        logging.warning( _("Additional '{}' attribute ('{}') found on {} element in record {} in {}").format( attributeName, attributeValue, element.tag, k, systemName ) )

                # Check the attributes that must contain unique information (in that particular field -- doesn't check across different attributes)
                for attributeName in self.uniqueAttributes[index]:
                    attributeValue = element.get( attributeName )
                    if attributeValue is not None:
                        if attributeValue in uniqueDict["Attribute_"+str(index)+"_"+attributeName]:
                            logging.error( _("Found '{}' data repeated in '{}' field on {} element in record {} in {}").format( attributeValue, attributeName, element.tag, k, systemName ) )
                        uniqueDict["Attribute_"+str(index)+"_"+attributeName].append( attributeValue )

                # Check compulsory elements
                for elementName in self.compulsoryElements[index]:
                    if element.find( elementName ) is None:
                        logging.error( _("Compulsory '{}' element is missing (record {}) in {}").format( elementName, k, systemName ) )
                    if not element.find( elementName ).text:
                        logging.warning( _("Compulsory '{}' element is blank (record {}) in {}").format( elementName, k, systemName ) )

                # Check optional elements
                for elementName in self.optionalElements[index]:
                    if element.find( elementName ) is not None:
                        if not element.find( elementName ).text:
                            logging.warning( _("Optional '{}' element is blank (record {}) in {}").format( elementName, k, systemName ) )

                # Check for unexpected additional elements
                for subelement in element:
                    if subelement.tag not in self.compulsoryElements[index] and subelement.tag not in self.optionalElements[index]:
                        logging.warning( _("Additional '{}' element ('{}') found (record {}) in {} {}").format( subelement.tag, subelement.text, k, systemName, element.tag ) )

                # Check the elements that must contain unique information (in that particular element -- doesn't check across different elements)
                for elementName in self.uniqueElements[index]:
                    if element.find( elementName ) is not None:
                        text = element.find( elementName ).text
                        if text in uniqueDict["Element_"+str(index)+"_"+elementName]:
                            myLogging = logging.info if element.tag == 'BibleDivisionNames' else logging.error
                            myLogging( _("Found '{}' data repeated in '{}' element (record {}) in {}").format( text, elementName, k, systemName ) )
                        uniqueDict["Element_"+str(index)+"_"+elementName].append( text )
            else:
                logging.warning( _("Unexpected element: {} in record {} in {}").format( element.tag, k, systemName ) )
    # end of __validateSystem

    def __str__( self ):
        """
        This method returns the string representation of a Bible booksNames system.
        
        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = "_BibleBooksNamesConverter object"
        result += ('\n' if result else '') + "  Number of bookname systems loaded = {}".format( len(self.__XMLSystems) )
        if Globals.verbosityLevel > 2: # Make it verbose
            for x in self.__XMLSystems:
                result += ('\n' if result else '') + "  {}".format( x )
                if self.__ISOLanguages and self.__XMLSystems[x]["languageCode"] and self.__ISOLanguages.isValidLanguageCode( self.__XMLSystems[x]["languageCode"] ):
                    result += ('\n' if result else '') + "    " + _("Language code {} = {}").format( self.__XMLSystems[x]["languageCode"], self.__ISOLanguages.getLanguageName( self.__XMLSystems[x]["languageCode"]) )
                title = self.__XMLSystems[x]["title"]
                if title: result += ('\n' if result else '') + "    {}".format( title )
                version = self.__XMLSystems[x]["version"]
                if version: result += ('\n' if result else '') + '    ' + _("Version: {}").format( version )
                date = self.__XMLSystems[x]["date"]
                if date: result += ('\n' if result else '') + '    ' + _("Last updated: {}").format( date )
                result += ('\n' if result else '') + '    ' + _("Number of entries = {}").format( len(self.__XMLSystems[x]["tree"]) )
                numDivisions, numLeaders, numBooks = 0, 0, 0
                for element in self.__XMLSystems[x]["tree"]:
                    if element.tag == "BibleDivisionNames":
                        numDivisions += 1
                    elif element.tag == "BibleBooknameLeaders":
                        numLeaders += 1
                    elif element.tag == "BibleBookNames":
                        numBooks += 1
                if numDivisions: result += ('\n' if result else '') + '      ' + _("Number of divisions = {}").format( numDivisions )
                if numLeaders: result += ('\n' if result else '') + '      ' + _("Number of bookname leaders = {}").format( numLeaders )
                if numBooks: result += ('\n' if result else '') + '      ' + _("Number of books = {}").format( numBooks )
        return result
    # end of __str__

    def __len__( self ):
        """ Returns the number of systems loaded. """
        return len( self.__XMLSystems )
    # end of __len__

    def expandInputs ( self, bookList ):
        """
        This is a helper function to expand the inputAbbreviation fields to include all unambiguous shorter abbreviations.

        It is best to do this for a specific publication since there will be less ambiguities if there are less actual books included.
        This routine is only really included here as a demo -- it's much better to call expandBibleNamesInputs
            when the actual list of books for your publication is already known.

        Saves divisions name and book name ordered dictionaries, all UPPER CASE, sorted with longest first.
        """
        assert( bookList )
        assert( self.__XMLSystems )
        self.importDataToPython()
        assert( self.__BookNamesSystemsDict )
        if self.__expandedInputSystems: return # No need to do this again

        if bookList is not None:
            for BBB in bookList: # Just check this list is valid
                if not self.__BibleBooksCodes.isValidReferenceAbbreviation( BBB ): logging.error( _("Invalid '{}' in booklist requested for expansion").format(BBB) )

        if Globals.verbosityLevel > 1: print( _("Expanding input abbreviations...") )
        for systemName in self.__BookNamesSystemsDict:
            if Globals.verbosityLevel > 2: print( _("  Expanding {}...").format( systemName ) )
            divisionsNamesDict, booknameLeadersDict, bookNamesDict = self.__BookNamesSystemsDict[systemName]
            self.__expandedInputSystems[systemName] = expandBibleNamesInputs( systemName, divisionsNamesDict, booknameLeadersDict, bookNamesDict, bookList )
    # end of expandInputs

    def importDataToPython( self ):
        """
        Loads (and pivots) the data (not including the header) into suitable Python containers to use in a Python program.

        If necessary (but not actually recommended), expandInputs could be called before this to fill self.__expandedInputSystems.

        Returns two dictionaries which should each contain entries for each named system.
        """
        assert( self.__XMLSystems )
        if self.__BookNamesSystemsDict: # We've already done an import/restructuring -- no need to repeat it
            return self.__BookNamesSystemsDict, self.__expandedInputSystems

        # We'll create a number of dictionaries
        if Globals.verbosityLevel > 3: print( _("Importing data into Python dictionary...") )
        self.__BookNamesSystemsDict = {}
        for booksNamesSystemCode in self.__XMLSystems.keys():
            #print( booksNamesSystemCode )
            # Make the data dictionary for this booksNames system
            myDivisionsNamesDict, myBooknameLeadersDict, myBookNamesDict = {}, {}, {}
            for element in self.__XMLSystems[booksNamesSystemCode]["tree"]:
                if element.tag == "BibleDivisionNames":
                    standardAbbreviation = element.get("standardAbbreviation")
                    defaultName = element.find("defaultName").text
                    defaultAbbreviation = element.find("defaultAbbreviation").text
                    inputFields = [ defaultName ]
                    if not defaultName.startswith( defaultAbbreviation ):
                        inputFields.append( defaultAbbreviation )
                    for subelement in element.findall("inputAbbreviation"):
                        if subelement.text in inputFields:
                            logging.warning( _("Superfluous '{}' entry in inputAbbreviation field for {} division in '{}' booksNames system").format( subelement.text, defaultName, booksNamesSystemCode ) )
                        else: inputFields.append( subelement.text )
                    includedBooks = []
                    for subelement in element.findall("includesBook"):
                        BBB = subelement.text
                        if not self.__BibleBooksCodes.isValidReferenceAbbreviation( BBB ):
                            logging.error( _("Unrecognized '{}' book abbreviation in BibleDivisionNames in '{}' booksNames system").format( BBB, booksNamesSystemCode ) )
                        if BBB in includedBooks:
                            logging.error( _("Duplicate '{}' entry in includesBook field for '{}' division in '{}' booksNames system").format( subelement.text, defaultName, booksNamesSystemCode ) )
                        else: includedBooks.append( BBB )
                    myDivisionsNamesDict[standardAbbreviation] = {"includedBooks":includedBooks, "defaultName":defaultName, "defaultAbbreviation":defaultAbbreviation, "inputFields":inputFields }
                elif element.tag == "BibleBooknameLeaders":
                    standardLeader = element.get("standardLeader")
                    inputFields = [] # Don't include the standard leader here
                    for subelement in element.findall("inputAbbreviation"):
                        adjField = subelement.text + ' '
                        if adjField in inputFields:
                            logging.error( _("Duplicate '{}' entry in inputAbbreviation field for '{}' bookname leaders in '{}' booksNames system").format( subelement.text, standardLeader, booksNamesSystemCode ) )
                        else: inputFields.append( adjField )
                    myBooknameLeadersDict[standardLeader+' '] = inputFields
                elif element.tag == "BibleBookNames":
                    referenceAbbreviation = element.get("referenceAbbreviation")
                    if not self.__BibleBooksCodes.isValidReferenceAbbreviation( referenceAbbreviation ):
                        logging.error( _("Unrecognized '{}' book abbreviation in BibleBookNames in '{}' booksNames system").format( referenceAbbreviation, booksNamesSystemCode ) )
                    defaultName = element.find("defaultName").text
                    defaultAbbreviation = element.find("defaultAbbreviation").text
                    inputFields = [ defaultName ] # Add the default name to the allowed input fields
                    if defaultAbbreviation != defaultName: inputFields.append( defaultAbbreviation ) # Automatically add the default abbreviation if it's different
                    for subelement in element.findall("inputAbbreviation"):
                        if subelement.text in inputFields:
                            logging.info( _("Superfluous '{}' entry in inputAbbreviation field for {} book in '{}' booksNames system").format( subelement.text, defaultName, booksNamesSystemCode ) )
                        else: inputFields.append( subelement.text )
                    myBookNamesDict[referenceAbbreviation] = { "defaultName":defaultName, "defaultAbbreviation":defaultAbbreviation, "inputFields":inputFields }

            if Globals.strictCheckingFlag: # check for duplicates
                for checkSystemCode in self.__BookNamesSystemsDict:
                    checkDivisionsNamesList, checkBooknameLeadersDict, checkBookNamesDict = self.__BookNamesSystemsDict[checkSystemCode]
                    if checkDivisionsNamesList==myDivisionsNamesDict and checkBookNamesDict==myBookNamesDict:
                        if checkBooknameLeadersDict == myBooknameLeadersDict:
                            logging.error( _("{} and {} book name systems are exactly identical ({} divisions, {} book names, {} leaders)").format( booksNamesSystemCode, checkSystemCode, len(myDivisionsNamesDict), len(myBookNamesDict), len(myBooknameLeadersDict) ) )
                        else: # only the leaders are different
                            logging.error( _("{} and {} book name systems are mostly identical ({} divisions, {} book names)").format( booksNamesSystemCode, checkSystemCode, len(myDivisionsNamesDict), len(myBookNamesDict) ) )

            # Now put it into my dictionary for easy access
            self.__BookNamesSystemsDict[booksNamesSystemCode] = myDivisionsNamesDict, myBooknameLeadersDict, myBookNamesDict
        return self.__BookNamesSystemsDict, self.__expandedInputSystems
    # end of importDataToPython

    def exportDataToPython( self, filepath=None ):
        """
        Writes the information tables to a .py file that can be cut and pasted into a Python program.
        """
        def exportPythonDict( theFile, theDict, dictName, keyComment, fieldsComment ):
            """Exports theDict to theFile."""
            assert( isinstance( theDict, dict ) )
            for dictKey in theDict.keys(): # Have to iterate this :(
                fieldsCount = len( theDict[dictKey] ) if isinstance( theDict[dictKey], (tuple,dict,list) ) else 1
                break # We only check the first (random) entry we get
            theFile.write( '  "{}": {{\n    # Key is {}\n    # Fields ({}) are: {}\n'.format( dictName, keyComment, fieldsCount, fieldsComment ) )
            for dictKey in theDict.keys():
                theFile.write( '    {}: {},\n'.format( repr(dictKey), repr(theDict[dictKey]) ) )
            theFile.write( "  }}, # end of {} ({} entries)\n\n".format( dictName, len(theDict) ) )
        # end of exportPythonDict

        def exportPythonOrderedDict( theFile, theDict, dictName, keyComment, fieldsComment ):
            """Exports theDict to theFile."""
            assert( isinstance( theDict, OrderedDict ) )
            for dictKey in theDict.keys(): # Have to iterate this :(
                fieldsCount = len( theDict[dictKey] ) if isinstance( theDict[dictKey], (tuple,dict,list) ) else 1
                break # We only check the first (random) entry we get
            theFile.write( '  "{}": OrderedDict([\n    # Key is {}\n    # Fields ({}) are: {}\n'.format( dictName, keyComment, fieldsCount, fieldsComment ) )
            for dictKey in theDict.keys():
                theFile.write( '    ({}, {}),\n'.format( repr(dictKey), repr(theDict[dictKey]) ) )
            theFile.write( "  ]), # end of {} ({} entries)\n\n".format( dictName, len(theDict) ) )
        # end of exportPythonDict

        def exportPythonList( theFile, theList, listName, fieldsComment ):
            """Exports theList to theFile."""
            assert( isinstance( theList, list ) )
            fieldsCount = len( theList[0] ) if isinstance( theList[0], (tuple,dict,list) ) else 1
            theFile.write( '  "{}": [\n    # Fields ({}) are: {}\n'.format( listName, fieldsCount, fieldsComment ) )
            for j,entry in enumerate(theList):
                theFile.write( '    {}, # {}\n'.format( repr(entry), j ) )
            theFile.write( "  ], # end of {} ({} entries)\n\n".format( listName, len(theList) ) )
        # end of exportPythonList

        from datetime import datetime

        assert( self.__XMLSystems )
        self.importDataToPython()
        assert( self.__BookNamesSystemsDict )

        raise Exception( "Python export not working properly yet" )
        if not filepath: filepath = os.path.join( "DerivedFiles", self.filenameBase + "_Tables.py" )
        if Globals.verbosityLevel > 1: print( _("Exporting to {}...").format( filepath ) )
        # Split into three lists/dictionaries
        with open( filepath, 'wt' ) as myFile:
            myFile.write( "# {}\n#\n".format( filepath ) )
            myFile.write( "# This UTF-8 file was automatically generated by BibleBooksNames.py V{} on {}\n#\n".format( versionString, datetime.now() ) )
            #if self.title: myFile.write( "# {}\n".format( self.title ) )
            #if self.version: myFile.write( "#  Version: {}\n".format( self.version ) )
            #if self.date: myFile.write( "#  Date: {}\n#\n".format( self.date ) )
            #myFile.write( "#   {} {} entries loaded from the original XML file.\n".format( len(self.namesTree), self.treeTag ) )
            myFile.write( "#   {} {} loaded from the original XML files.\n#\n\n".format( len(self.__XMLSystems), self.treeTag ) )
            myFile.write( "from collections import OrderedDict\n\n" )
            myFile.write( "\ndivisionNamesList = {\n  # Key is languageCode\n  # Fields are divisionNames\n\n" )
            for systemName in self.__BookNamesSystemsDict:
                divisionsNamesDict, booknameLeadersDict, bookNamesDict = self.__BookNamesSystemsDict[systemName]
                exportPythonList( myFile, divisionsNamesDict, systemName, "startsWith( string), defaultName (string), defaultAbbreviation (string), inputFields (list of strings) all in a dictionary" )
            myFile.write( "}} # end of divisionNamesList ({} systems)\n\n\n".format( len(self.__BookNamesSystemsDict) ) )
            myFile.write( "\nbooknameLeadersDict = {\n  # Key is languageCode\n  # Fields are divisionNames\n\n" )
            for systemName in self.__BookNamesSystemsDict:
                divisionsNamesDict, booknameLeadersDict, bookNamesDict = self.__BookNamesSystemsDict[systemName]
                exportPythonDict( myFile, booknameLeadersDict, systemName, "standardLeader (all fields include a trailing space)", "inputAlternatives (list of strings)" )
            myFile.write( "}} # end of booknameLeadersDict ({} systems)\n\n\n".format( len(self.__BookNamesSystemsDict) ) )
            myFile.write( "\nbookNamesDict = {\n  # Key is languageCode\n  # Fields are divisionNames\n\n" )
            for systemName in self.__BookNamesSystemsDict:
                divisionsNamesDict, booknameLeadersDict, bookNamesDict = self.__BookNamesSystemsDict[systemName]
                exportPythonDict( myFile, bookNamesDict, systemName, "referenceAbbreviation", "defaultName (string), defaultAbbreviation (string), inputAbbreviations (list of strings) all in a dictionary" )
            myFile.write( "}} # end of bookNamesDict ({} systems)\n\n\n".format( len(self.__BookNamesSystemsDict) ) )
            if self.__expandedInputSystems:
                myFile.write( "\ndivisionsNamesInputDict = {\n  # Key is languageCode\n  # Fields are divisionNames\n\n" )
                for systemName in self.__BookNamesSystemsDict:
                    if systemName in self.__expandedInputSystems:
                        divisionsNamesInputDict, bookNamesInputDict = self.__expandedInputSystems[systemName]
                        exportPythonOrderedDict( myFile, divisionsNamesInputDict, "divisionsNamesInputDict", "UpperCaseInputString (sorted with longest first)", "index (into divisionNamesList above)" )
                myFile.write( "}} # end of divisionsNamesInputDict ({} systems)\n\n\n".format( len(self.__BookNamesSystemsDict) ) )
                myFile.write( "\nbookNamesInputDict = {\n  # Key is languageCode\n  # Fields are divisionNames\n\n" )
                for systemName in self.__BookNamesSystemsDict:
                    if systemName in self.__expandedInputSystems:
                        divisionsNamesInputDict, bookNamesInputDict = self.__expandedInputSystems[systemName]
                        exportPythonOrderedDict( myFile, bookNamesInputDict, "bookNamesInputDict", "UpperCaseInputString (sorted with longest first)", "referenceAbbreviation (string)" )
                myFile.write( "}} # end of bookNamesInputDict ({} systems)\n".format( len(self.__BookNamesSystemsDict) ) )
    # end of exportDataToPython

    def exportDataToJSON( self, filepath=None ):
        """
        Writes the information tables to a .json file that can be easily loaded into a Java program.

        See http://en.wikipedia.org/wiki/JSON.
        """
        from datetime import datetime
        import json

        assert( self.__XMLSystems )
        self.importDataToPython()
        assert( self.__BookNamesSystemsDict )

        if not filepath: filepath = os.path.join( "DerivedFiles", self.filenameBase + "_Tables.json" )
        if Globals.verbosityLevel > 1: print( _("Exporting to {}...").format( filepath ) )
        with open( filepath, 'wt' ) as myFile:
            #myFile.write( "# {}\n#\n".format( filepath ) ) # Not sure yet if these comment fields are allowed in JSON
            #myFile.write( "# This UTF-8 file was automatically generated by BibleBooksCodes.py V{} on {}\n#\n".format( versionString, datetime.now() ) )
            #if self.titleString: myFile.write( "# {} data\n".format( self.titleString ) )
            #if self.versionString: myFile.write( "#  Version: {}\n".format( self.versionString ) )
            #if self.dateString: myFile.write( "#  Date: {}\n#\n".format( self.dateString ) )
            #myFile.write( "#   {} {} loaded from the original XML file.\n#\n\n".format( len(self.XMLtree), self.treeTag ) )
            json.dump( self.__BookNamesSystemsDict, myFile, indent=2 )
            #myFile.write( "\n\n# end of {}".format(os.path.basename(filepath) )
    # end of exportDataToJSON

    def exportDataToC( self, filepath=None ):
        """
        Writes the information tables to a .h file that can be included in c and c++ programs.
        """
        def exportPythonDict( theFile, theDict, dictName, structName, fieldsComment ):
            """Exports theDict to theFile."""
            def convertEntry( entry ):
                """Convert special characters in an entry..."""
                result = ""
                for field in entry:
                    if result: result += ", " # Separate the fields
                    if field is None: result += '""'
                    elif isinstance( field, str): result += '"' + str(field).replace('"','\\"') + '"'
                    elif isinstance( field, int): result += str(field)
                    else: logging.error( _("Cannot convert unknown field type '{}' in entry '{}'").format( field, entry ) )
                return result

            theFile.write( "static struct {} {}[] = {\n  // Fields are {}\n".format( structName, dictName, fieldsComment ) )
            for entry in sorted(theDict.keys()):
                if isinstance( entry, str ):
                    theFile.write( "  {\"{}\", {}},\n".format( entry, convertEntry(theDict[entry]) ) )
                elif isinstance( entry, int ):
                    theFile.write( "  {{}, {}},\n".format( entry, convertEntry(theDict[entry]) ) )
                else:
                    logging.error( _("Can't handle this type of data yet: {}").format( entry ) )
            theFile.write( "}; // {}\n\n".format( dictName) )
        # end of exportPythonDict

        from datetime import datetime

        assert( self.__XMLSystems )
        self.importDataToPython()
        assert( self.__BookNamesSystemsDict )

        if not filepath: filepath = os.path.join( "DerivedFiles", self.filenameBase + "_Tables.h" )
        if Globals.verbosityLevel > 1: print( _("Exporting to {}...").format( filepath ) )
        raise Exception( "C export not written yet -- sorry." )

        ifdefName = self.filenameBase.upper() + "_Tables_h"
        with open( filepath, 'wt' ) as myFile:
            myFile.write( "// {}\n//\n".format( filepath ) )
            myFile.write( "// This UTF-8 file was automatically generated by BibleBooksNames.py V{} on {}\n//\n".format( versionString, datetime.now() ) )
            if self.title: myFile.write( "// {}\n".format( self.title ) )
            if self.version: myFile.write( "//  Version: {}\n".format( self.version ) )
            if self.date: myFile.write( "//  Date: {}\n//\n".format( self.date ) )
            myFile.write( "//   {} {} loaded from the original XML file.\n//\n\n".format( len(self.namesTree), self.treeTag ) )
            myFile.write( "#ifndef {}\n#define {}\n\n".format( ifdefName, ifdefName ) )
            exportPythonDict( myFile, IDDict, "IDDict", "{int id; char* refAbbrev; char* SBLAbbrev; char* OSISAbbrev; char* PTAbbrev; char* PTNum; char* EngName;}", "id (sorted), referenceAbbreviation, SBLAbbreviation, OSISAbbreviation, ParatextAbbreviation, ParatextNumberString, nameEnglish (comment only)" )
            exportPythonDict( myFile, RADict, "RADict", "{char* refAbbrev; int id; char* SBLAbbrev; char* OSISAbbrev; char* PTAbbrev; char* PTNum; char* EngName;}", "referenceAbbreviation (sorted), SBLAbbreviation, OSISAbbreviation, ParatextAbbreviation, ParatextNumberString, id, nameEnglish (comment only)" )
            exportPythonDict( myFile, SBLDict, "SBLDict", "{char* SBLAbbrev; int id; char* refAbbrev; char* OSISAbbrev; char* PTAbbrev; char* PTNum; char* EngName;}", "SBLAbbreviation (sorted), ReferenceAbbreviation, OSISAbbreviation, ParatextAbbreviation, ParatextNumberString, id, nameEnglish (comment only)" )
            exportPythonDict( myFile, OADict, "OADict", "{char* OSISAbbrev; int id; char* refAbbrev; char* SBLAbbrev; char* PTAbbrev; char* PTNum; char* EngName;}", "OSISAbbreviation (sorted), ReferenceAbbreviation, SBLAbbreviation, ParatextAbbreviation, ParatextNumberString, id, nameEnglish (comment only)" )
            exportPythonDict( myFile, PADict, "PADict", "{char* PTAbbrev; int id; char* refAbbrev; char* SBLAbbrev; char* OSISAbbrev; char* PTNum; char* EngName;}", "ParatextAbbreviation (sorted), referenceAbbreviation, SBLAbbreviation, OSISAbbreviation, ParatextNumberString, id, nameEnglish (comment only)" )
            exportPythonDict( myFile, PNDict, "PNDict", "{char* PTNum; int id; char* PTAbbrev; char* refAbbrev; char* SBLAbbrev; char* OSISAbbrev; char* EngName;}", "ParatextNumberString (sorted), ParatextAbbreviation, referenceAbbreviation, SBLAbbreviation, OSISAbbreviation, id, nameEnglish (comment only)" )
            myFile.write( "#endif // {}\n".format( ifdefName ) )
    # end of exportDataToC
# end of _BibleBooksNamesConverter class


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
        assert( UCString)
        assert( originalDict )

        # Drop off final letters and remove internal spaces
        tempString = UCString
        while( tempString ):
            if not tempString.isdigit() and tempString[-1]!=' ': # Don't allow single digits (even if unambiguous) and gnore any truncated strings that end in a space
                if tempString in originalDict:
                    if originalDict[tempString] == value:
                        if Globals.verbosityLevel > 3: logging.debug( "'{}' is superfluous: won't add to tempDict".format(tempString) )
                        theAmbigSet.add( tempString )
                    else: # it's a different value
                        if Globals.verbosityLevel > 3: logging.debug( "'{}' is ambiguous: won't add to tempDict".format(tempString) )
                        theAmbigSet.add( tempString )
                elif tempString in tempDict and tempDict[tempString]!=value:
                    if Globals.verbosityLevel > 3: logging.info( "'{}' is ambiguous: will remove from tempDict".format(tempString) )
                    theAmbigSet.add( tempString )
                else:
                    tempDict[tempString] = value
                tempTempString = tempString
                while ' ' in tempTempString:
                    tempTempString = tempTempString.replace( " ", "", 1 ) # Remove the first space
                    if tempTempString in originalDict:
                        if originalDict[tempTempString] == value:
                            if Globals.verbosityLevel > 3: logging.debug( "'{}' (spaces removed) is superfluous: won't add to tempDict".format(tempTempString) )
                            theAmbigSet.add( tempTempString )
                        else: # it's a different value
                            if Globals.verbosityLevel > 3: logging.debug( "'{}' (spaces removed) is ambiguous: won't add to tempDict".format(tempTempString) )
                            theAmbigSet.add( tempTempString )
                    elif tempTempString in tempDict and tempDict[tempTempString]!=value:
                        if Globals.verbosityLevel > 3: logging.info( "'{}' (spaces removed) is ambiguous: will remove from tempDict".format(tempTempString) )
                        theAmbigSet.add( tempTempString )
                    else:
                        tempDict[tempTempString] = value
            tempString = tempString[:-1] # Drop off another letter
    # end of expandAbbrevs

    assert( systemName )
    assert( divisionsNamesDict ); assert( booknameLeadersDict ); assert( bookNamesDict )
    assert( bookList )

    if Globals.verbosityLevel > 2: print( _("  Expanding {} input abbreviations (for {} books)...").format( systemName, len(bookList) ) )

    # Firstly, make a new UPPER CASE leaders dictionary., e.g., Saint/Snt goes to SAINT/SNT
    UCBNLeadersDict = {}
    #print( "bnLD", len(booknameLeadersDict), booknameLeadersDict )
    for leader in booknameLeadersDict:
        UCLeader = leader.upper()
        assert( UCLeader not in UCBNLeadersDict )
        UCBNLeadersDict[UCLeader] = [x.upper() for x in booknameLeadersDict[leader]]
        #UCBNLeadersDict[UCLeader].append( UCLeader ) # We have to add ourselves to this list
    #print( "UCbnl", len(UCBNLeadersDict), UCBNLeadersDict )

    # Secondly make a set of the given allowed names
    divNameInputDict, bkNameInputDict, ambigSet = {}, {}, set()
    for divAbbrev in divisionsNamesDict.keys():
        for field in divisionsNamesDict[divAbbrev]["inputFields"]:
            UCField = field.upper()
            if UCField in divNameInputDict or UCField in bkNameInputDict:
                logging.warning( _("Have duplicate entries of '{}' in divisionsNames for {}").format( UCField, systemName ) )
                ambigSet.add( UCField )
            divNameInputDict[UCField] = divAbbrev # Store the index into divisionsNamesDict
    for refAbbrev in bookNamesDict.keys():
        if refAbbrev in bookList:
            for field in bookNamesDict[refAbbrev]["inputFields"]: # inputFields include the defaultName, defaultAbbreviation, and inputAbbreviations
                UCField = field.upper()
                if UCField in divNameInputDict or UCField in bkNameInputDict:
                    logging.warning( _("Have duplicate entries of '{}' in divisions and book names for {}").format( UCField, systemName ) )
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
            assert( field not in divNameInputDict )
            divNameInputDict[field] = tempDNDict[field]
    #print( "\ndivNameInputDict--final", len(divNameInputDict), divNameInputDict )
    for field in tempBNDict:
        if field not in ambigSet:
            assert( field not in bkNameInputDict )
            bkNameInputDict[field] = tempBNDict[field]
        #else: print( "Didn't add '{}'", field )
    #print( "\nbkNameInputDict--final", len(bkNameInputDict) )

    # Now sort both dictionaries to be longest string first
    sortedDNDict = OrderedDict( sorted(divNameInputDict.items(), key=lambda s: -len(s[0])) )
    sortedBNDict = OrderedDict( sorted( bkNameInputDict.items(), key=lambda s: -len(s[0])) )

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
        self.__bbnsc = _BibleBooksNamesConverter()
        self.__BibleBooksCodes = BibleBooksCodes().loadData()
        self.__DataDicts, self.__ExpandedDicts = None, None # We'll import into this in loadData
    # end of __init__

    def loadData( self, XMLFilepath=None ):
        """ Loads the XML data file and imports it to dictionary format (if not done already). """
        if not self.__DataDicts: # Don't do this unnecessarily
            self.__bbnsc.loadSystems( XMLFilepath ) # Load the XML (if not done already)
            self.__DataDicts, self.__ExpandedDicts = self.__bbnsc.importDataToPython() # Get the various dictionaries organised for quick lookup
            del self.__bbnsc # Now the converter class (that handles the XML) is no longer needed
        return self
    # end of loadData

    def __str__( self ):
        """
        This method returns the string representation of a Bible book code.
        
        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = "BibleBooksNamesSystems object"
        if self.__ExpandedDicts: assert( len(self.__DataDicts) == len(self.__ExpandedDicts) )
        result += ('\n' if result else '') + '  ' + _("Number of loaded bookname systems = {}").format( len(self.__DataDicts) )
        return result
    # end of __str__

    def __len__( self ):
        """ Returns the number of systems loaded. """
        return len( self.__DataDicts )
    # end of __len__

    def __contains__( self, name ):
        """ Returns True/False if the name is in this system. """
        return name in self.__DataDicts
    # end of __contains__

    def getAvailableBooksNamesSystemNames( self, languageCode=None ):
        """ Returns a list of available system name strings. """
        if languageCode is None:
            return [systemName for systemName in self.__DataDicts]
        # else -- we were given a language code
        assert( len(languageCode) == 3 ) # ISO 639-3
        search = languageCode + '_'
        result = []
        for systemName in self.__DataDicts:
            if systemName==languageCode: result.append( '' )
            if systemName.startswith( search ): result.append( systemName[4:] ) # Get the bit after the underline
        return result
    # end of getAvailableBooksNamesSystemNames

    def getAvailableLanguageCodes( self ):
        """ Returns a list of available ISO 639-3 language code strings. """
        result = set()
        for systemName in self.__DataDicts:
            assert( len(systemName) >= 3 )
            languageCode = systemName[:3]
            result.add( languageCode )
        return result
    # end of getAvailableLanguageCodes

    def getBooksNamesSystem( self, systemName, bookList=None ):
        """ Returns two dictionaries and a list object."""
        if bookList is not None:
            for BBB in bookList: # Just check this list is valid
                if not self.__BibleBooksCodes.isValidReferenceAbbreviation( BBB ): logging.error( _("Invalid '{}' in booklist requested for {} books names system").format(BBB,systemName) )

        if systemName in self.__DataDicts:
            assert( len(self.__DataDicts[systemName]) == 3 )
            divisionsNamesDict, booknameLeadersDict, bookNamesDict = self.__DataDicts[systemName] # unpack it so it's clearer what we're doing here
            if bookList is None:
                if self.__ExpandedDicts:
                    assert( len(self.__ExpandedDicts[systemName]) == 2 )
                    return divisionsNamesDict, booknameLeadersDict, bookNamesDict, self.__ExpandedDicts[systemName][0], self.__ExpandedDicts[systemName][1]
                # else we haven't done any previous input abbreviation expansion
                return divisionsNamesDict, booknameLeadersDict, bookNamesDict, OrderedDict(), OrderedDict()

            # Else we were given a booklist so we need to expand the input abbreviations here now
            if self.__ExpandedDicts: logging.warning( _("This {} book names system was already expanded, but never mind :)").format(systemName) )

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
                bookNamesDictCopy[BBB] = bookNamesDict[BBB]

            if not Globals.commandLineOptions.fast: # check that this system contains all the books we need
                missingList = []
                for BBB in bookList:
                    if BBB not in bookNamesDictCopy: missingList.append( BBB )
                if missingList: logging.error( "The following book(s) have no information in {} bookname system: {}".format( systemName, missingList ) )

            # Now expand to get unambiguous input abbreviations for a publication only containing the books we specified
            sortedDNDict, sortedBNDict = expandBibleNamesInputs( systemName, divisionsNamesDictCopy, booknameLeadersDict, bookNamesDictCopy, bookList )
            #print( sortedBNDict )
            #print( sortedDNDict )
            #print( len(divisionsNamesDict), len(divisionsNamesDictCopy), len(booknameLeadersDict), len(bookNamesDict), len(bookNamesDictCopy), len(sortedDNDict), len(sortedBNDict) )
            return divisionsNamesDictCopy, booknameLeadersDict, bookNamesDictCopy, sortedDNDict, sortedBNDict

        # else we couldn't find the requested system name
        logging.error( _("No '{}' system in Bible Books Names Systems").format(systemName) )
        if Globals.verbosityLevel > 2: logging.error( _("Available systems are {}").format(self.getAvailableBooksNamesSystemNames()) )
    # end of getBooksNamesSystem
# end of BibleBooksNamesSystems class


class BibleBooksNamesSystem:
    """
    Class for handling a particular Bible book names system.

    This class doesn't deal at all with XML, only with Python dictionaries, etc.
    """

    def __init__( self, systemName, bookList=None ):
        """
        Grabs a particular BibleBooksNames system from the singleton object which contains all of the known books names systems.
            The optional (but highly recommended) book list is used for automatically determining non-ambiguous bookname abbreviations.
                i.e., if you just have English Old Testament, G could automatically represent Genesis, but if you have an entire Bible, G would be ambiguous (Genesis or Galatians).
                    NOTE: However, of course, you can manually specify in the data file that you want G to be an inputAbbreviation for say, Genesis.
        """
        self.__systemName = systemName
        self.__languageCode = systemName.split('_',1)[0]
        self.__bnss = BibleBooksNamesSystems().loadData() # Doesn't reload the XML unnecessarily :)
        self.__bookList = bookList
        result = self.__bnss.getBooksNamesSystem( self.__systemName, bookList )
        if result is not None:
            self.__divisionsNamesDict, self.__booknameLeadersDict, self.__bookNamesDict, self.__sortedDivisionNamesDict, self.__sortedBookNamesDict = result
    # end of __init__

    def __str__( self ):
        """
        This method returns the string representation of a Bible books names system.
        
        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = "BibleBooksNamesSystem object"
        result += ('\n' if result else '') + "  " + _("{} Bible books names system").format( self.__systemName )
        result += ('\n' if result else '') + "  " + _("Language code = {}").format( self.__languageCode )
        if Globals.verbosityLevel > 2: # Make it verbose
            result += ('\n' if result else '') + "    " + _("Number of divisions = {}").format( len(self.__divisionsNamesDict) )
            result += ('\n' if result else '') + "    " + _("Number of bookname leaders = {}").format( len(self.__booknameLeadersDict) )
            result += ('\n' if result else '') + "    " + _("Number of books = {}").format( len(self.__bookNamesDict) )
            result += ('\n' if result else '') + "    " + _("Number of expanded division name abbreviations = {}").format( len(self.__sortedDivisionNamesDict) )
            result += ('\n' if result else '') + "    " + _("Number of expanded book name abbreviations = {}").format( len(self.__sortedBookNamesDict) )
        return result
    # end of __str__

    def getBooksNamesSystemName( self ):
        """ Return the book names system name. """
        return self.__systemName
    # end of getBooksNamesSystemName

    def getBookName( self, BBB ):
        """ Get the default book name from the given referenceAbbreviation. """
        assert( len(BBB) == 3 )
        return self.__bookNamesDict[BBB]['defaultName']
    # end of getBookName

    def getBookAbbreviation( self, BBB ):
        """ Get the default book abbreviation from the given referenceAbbreviation. """
        assert( len(BBB) == 3 )
        return self.__bookNamesDict[BBB]['defaultAbbreviation']
    # end of getBookAbbreviation

    def getBBB( self, bookNameOrAbbreviation ):
        """ Get the referenceAbbreviation from the given book name or abbreviation.
                (Automatically converts to upper case before comparing strings.) """
        assert( bookNameOrAbbreviation )
        upperCaseBookNameOrAbbreviation = bookNameOrAbbreviation.upper()
        if upperCaseBookNameOrAbbreviation in self.__sortedBookNamesDict:
            return self.__sortedBookNamesDict[upperCaseBookNameOrAbbreviation]
        if Globals.commandLineOptions.debug:
            # It failed so print what the closest alternatives were
            print( "getBBB", bookNameOrAbbreviation, upperCaseBookNameOrAbbreviation )
            myList, thisLen = [], len(upperCaseBookNameOrAbbreviation)
            for key in self.__sortedBookNamesDict.keys():
                if key.startswith( upperCaseBookNameOrAbbreviation[0] ) and len(key)==thisLen: myList.append( key )
            print( "Possibility list is", myList )
    # end of getBBB

    def getDivisionAbbreviation( self, divisionNameOrAbbreviation ):
        """ Get the division standardAbbreviation from the given division name or abbreviation.
                (Automatically converts to upper case before comparing strings.) """
        assert( divisionNameOrAbbreviation )
        upperCaseDivisionNameOrAbbreviation = divisionNameOrAbbreviation.upper()
        if upperCaseDivisionNameOrAbbreviation in self.__sortedDivisionNamesDict:
            #print( self.__sortedDivisionNamesDict[upperCaseDivisionNameOrAbbreviation], self.__divisionsNamesDict[self.__sortedDivisionNamesDict[upperCaseDivisionNameOrAbbreviation]]['defaultAbbreviation'] )
            return self.__sortedDivisionNamesDict[upperCaseDivisionNameOrAbbreviation]
        if Globals.commandLineOptions.debug:
            # It failed so print what the closest alternatives were
            print( "getDivisionAbbrev", divisionNameOrAbbreviation, upperCaseDivisionNameOrAbbreviation )
            myList, thisLen = [], len(upperCaseDivisionNameOrAbbreviation)
            for key in self.__sortedDivisionNamesDict.keys():
                if key.startswith( upperCaseDivisionNameOrAbbreviation[0] ) and len(key)==thisLen: myList.append( key )
            print( "Possibility list is", myList )
    # end of getDivisionAbbreviation

    def getDivisionBooklist( self, divisionAbbreviation ):
        """ Returns the booklist for the division given the division standardAbbreviation
                                                or else given a vernacular inputAbbreviation. """
        assert( divisionAbbreviation )
        if divisionAbbreviation in self.__divisionsNamesDict:
            return self.__divisionsNamesDict[divisionAbbreviation]['includedBooks']
        # else it might be a vernacular value
        standardDivisionAbbreviation = self.getDivisionAbbreviation( divisionAbbreviation )
        if standardDivisionAbbreviation is not None:
            return self.__divisionsNamesDict[standardDivisionAbbreviation]['includedBooks']
    # end of getDivisionBooklist
# end of BibleBookNamesSystem class


def main():
    """
    Main program to handle command line parameters and then run what they want.
    """
    # Handle command line parameters
    from optparse import OptionParser
    parser = OptionParser( version="v{}".format( versionString ) )
    parser.add_option("-x", "--expandDemo", action="store_true", dest="expandDemo", default=False, help="expand the input abbreviations to include all unambiguous shorter forms")
    parser.add_option("-e", "--export", action="store_true", dest="export", default=False, help="export the XML files to .py and .h tables suitable for directly including into other programs")
    Globals.addStandardOptionsAndProcess( parser )

    if Globals.verbosityLevel > 1: print( "{} V{}".format( progName, versionString ) )

    sampleBookList = ['GEN','JDG','SA1','SA2','KI1','KI2','MA4','MAT','MRK','LUK','JHN','ACT','ROM','CO1','CO2','PE1','PE2','JDE','REV']
    #sampleBookList = ['GEN','JDG','SA1','SA2','KI1','KI2','MA1','MA2']
    #sampleBookList = ['MAT','MRK','LUK','JHN','ACT','ROM','CO1','CO2','GAL','EPH','PHP','COL','PE1','PE2','JDE','REV']
    if Globals.commandLineOptions.export:
        bbnsc = _BibleBooksNamesConverter().loadSystems() # Load the XML
        if Globals.commandLineOptions.expandDemo: # Expand the inputAbbreviations to find all shorter unambiguous possibilities
            bbnsc.expandInputs( sampleBookList )
        bbnsc.exportDataToPython() # Produce the .py tables
        bbnsc.exportDataToJSON() # Produce a json output file
        bbnsc.exportDataToC() # Produce the .h and .c tables

    else: # Must be demo mode
        # Demo the converter object
        bbnsc = _BibleBooksNamesConverter().loadSystems() # Load the XML
        print( bbnsc ) # Just print a summary
        if Globals.commandLineOptions.expandDemo: # Expand the inputAbbreviations to find all shorter unambiguous possibilities
            bbnsc.expandInputs( sampleBookList )
            print( bbnsc ) # Just print a summary

        # Demo the BibleBooksNamesSystems object
        bbnss = BibleBooksNamesSystems().loadData() # Doesn't reload the XML unnecessarily :)
        print( bbnss ) # Just print a summary
        print( "Available system names are:", bbnss.getAvailableBooksNamesSystemNames() )
        print( "Available eng system names are:", bbnss.getAvailableBooksNamesSystemNames( 'eng' ) ) # Just get the ones for this language code
        print( "Available mbt system names are:", bbnss.getAvailableBooksNamesSystemNames( languageCode='mbt' ) )
        print( "Available language codes are:", bbnss.getAvailableLanguageCodes() )

        # Demo the BibleBooksNamesSystem object
        bbns1 = BibleBooksNamesSystem("eng_traditional") # Doesn't reload the XML unnecessarily :)
        print( bbns1 ) # Just print a summary

        # Demo the BibleBooksNamesSystem object with a book list
        bbns2 = BibleBooksNamesSystem("eng_traditional",sampleBookList) # Doesn't reload the XML unnecessarily :)
        print( bbns2 ) # Just print a summary
        print( "Checking book name inputs..." )
        for bookAbbrevInput in ('Gen', 'GEN', 'Gn', 'Exo', '1 Samuel', '1Samuel', '1Sam', '1 Sam', '1 Sml', '1Sml', '1 S', '1S','II Sa','IIS','1Kgs', '1 Kgs', '1K', '1 K', 'IK', 'I K', '1M', 'IV Mac', 'Mt', 'Rvl' ):
            # NOTE: '1S' is ambiguous with '1st' :(
            print( "  Searching for '{}' got {}".format(bookAbbrevInput, bbns2.getBBB(bookAbbrevInput)) )
        print( "Checking division name inputs..." )
        for divisionAbbrevInput in ('OT','NewTest', 'Paul', 'Deutero', 'Gn', 'Exo' ): # Last two should always fail
            print( "  Searching for '{}' got {}".format(divisionAbbrevInput, bbns2.getDivisionAbbreviation(divisionAbbrevInput)) )
        print( "Getting division booklists..." )
        for divisionAbbrevInput in ('OT','NT', 'NewTest', 'Paul', 'Deutero', 'Gn', 'Exo', '1 Samuel' ):
            print( "  Searching for '{}' got {}".format(divisionAbbrevInput, bbns2.getDivisionBooklist(divisionAbbrevInput)) )
# end of main

if __name__ == '__main__':
    main()
# end of BibleBooksNames.py
