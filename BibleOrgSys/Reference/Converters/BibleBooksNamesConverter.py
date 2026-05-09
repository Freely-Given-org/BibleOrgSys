#!/usr/bin/env -S uv run
# -\*- coding: utf-8 -\*-
# SPDX-License-Identifier: GPL-3.0-or-later
#
# BibleBooksNamesConverter.py
#
# Module handling BibleBooksNames_*.xml to produce C and Python data tables
#
# Copyright (C) 2010-2021 Robert Hunt
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
Module handling BibleBooksNames_*.xml to produce pickle, JSON, C and Python data tables.
"""
import os
import logging
from xml.etree.ElementTree import ElementTree

from BibleOrgSys.Misc.singleton import singleton
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint


LAST_MODIFIED_DATE = '2021-01-19' # by RJH
SHORT_PROGRAM_NAME = "BibleBooksNamesConverter"
PROGRAM_NAME = "Bible Books Names Systems converter"
PROGRAM_VERSION = '0.36'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False



@singleton # Can only ever have one instance
class BibleBooksNamesConverter:
    """
    A class to handle data for Bible booksNames systems.
    """

    def __init__( self ) -> None:
        """
        Constructor.
        """
        self.__filenameBase = "BibleBooksNames"

        # These fields are used for parsing the XML
        self.XMLTreeTag = "BibleBooksNames"
        self.headerTag = 'header'
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
        self.__XMLFolder, self.__XMLSystems, self.__BookNamesSystemsDict, self.__expandedInputSystems = None, {}, {}, {}
    # end of __init__

    def loadSystems( self, folder=None ):
        """
        Load and pre-process the specified booksNames systems.
        """
        if not self.__XMLSystems: # Only ever do this once
            if folder is None: folder = BibleOrgSysGlobals.BOS_DATAFILES_FOLDERPATH.joinpath( 'BookNames/' ) # Relative to module, not cwd
            self.__XMLFolder = folder
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"Loading book names systems from {folder}…" )
            for filename in os.listdir( folder ):
                filepart, extension = os.path.splitext( filename )
                if extension.upper() == '.XML' and filepart.upper().startswith(self.__filenameBase.upper()+"_"):
                    booksNamesSystemCode = filepart[len(self.__filenameBase)+1:]
                    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"Loading {booksNamesSystemCode} books names system from {filename}…" )
                    self.__XMLSystems[booksNamesSystemCode] = {}
                    self.__XMLSystems[booksNamesSystemCode]["languageCode"] = booksNamesSystemCode.split('_',1)[0]
                    self.__XMLSystems[booksNamesSystemCode]['tree'] = ElementTree().parse( os.path.join( folder, filename ) )
                    assert self.__XMLSystems[booksNamesSystemCode]['tree'] # Fail here if we didn't load anything at all

                    # Check and remove the header element
                    if self.__XMLSystems[booksNamesSystemCode]['tree'].tag  == self.XMLTreeTag:
                        header = self.__XMLSystems[booksNamesSystemCode]['tree'][0]
                        if header.tag == self.headerTag:
                            self.__XMLSystems[booksNamesSystemCode]['header'] = header
                            self.__XMLSystems[booksNamesSystemCode]['tree'].remove( header )
                            BibleOrgSysGlobals.checkXMLNoText( header, 'header' )
                            BibleOrgSysGlobals.checkXMLNoTail( header, 'header' )
                            BibleOrgSysGlobals.checkXMLNoAttributes( header, 'header' )
                            if len(header)>1:
                                logging.info( "Unexpected elements in header" )
                            elif len(header)==0:
                                logging.info( "Missing work element in header" )
                            else:
                                work = header[0]
                                BibleOrgSysGlobals.checkXMLNoText( work, "work in header" )
                                BibleOrgSysGlobals.checkXMLNoTail( work, "work in header" )
                                BibleOrgSysGlobals.checkXMLNoAttributes( work, "work in header" )
                                if work.tag == "work":
                                    self.__XMLSystems[booksNamesSystemCode]['version'] = work.find('version').text
                                    self.__XMLSystems[booksNamesSystemCode]['date'] = work.find('date').text
                                    self.__XMLSystems[booksNamesSystemCode]['title'] = work.find('title').text
                                else:
                                    logging.warning( "Missing work element in header" )
                        else:
                            logging.warning( f"Missing header element (looking for {self.headerTag!r} tag)" )
                    else:
                        logging.error( f"Expected to load {self.XMLTreeTag!r} but got {self.__XMLSystems[booksNamesSystemCode]['tree'].tag!r}" )
                    bookCount = 0 # There must be an easier way to do this
                    for subelement in self.__XMLSystems[booksNamesSystemCode]['tree']:
                        bookCount += 1
                    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    Loaded {bookCount} books for {booksNamesSystemCode}" )
                    logging.info( f"    Loaded {bookCount} books for {booksNamesSystemCode}" )

                    if BibleOrgSysGlobals.strictCheckingFlag:
                        self.__validateSystem( booksNamesSystemCode )
        return self
    # end of loadSystems

    def __validateSystem( self, systemName ):
        """
        Checks for basic formatting/content errors in a Bible book name system.
        """
        assert systemName
        assert self.__XMLSystems[systemName]['tree']

        if len(self.__XMLSystems[systemName]["languageCode"]) != 3:
            logging.error( f"Couldn't find 3-letter language code in {systemName!r} book names system" )
        #if self.__ISOLanguages and not self.__ISOLanguages.isValidLanguageCode( self.__XMLSystems[systemName]["languageCode"] ): # Check that we have a valid language code
            #logging.error( f'Unrecognized {self.__XMLSystems[systemName]["languageCode"]!r} ISO-639-3 language code in {systemName!r} book names system' )

        uniqueDict = {}
        for index in range( len(self.mainElementTags) ):
            for elementName in self.uniqueElements[index]: uniqueDict["Element_"+str(index)+"_"+elementName] = []
            for attributeName in self.uniqueAttributes[index]: uniqueDict["Attribute_"+str(index)+"_"+attributeName] = []

        expectedID = 1
        for k,element in enumerate(self.__XMLSystems[systemName]['tree']):
            if element.tag in self.mainElementTags:
                BibleOrgSysGlobals.checkXMLNoText( element, element.tag )
                BibleOrgSysGlobals.checkXMLNoTail( element, element.tag )
                if not self.compulsoryAttributes and not self.optionalAttributes: BibleOrgSysGlobals.checkXMLNoAttributes( element, element.tag )
                if not self.compulsoryElements and not self.optionalElements: BibleOrgSysGlobals.checkXMLNoSubelements( element, element.tag )

                index = self.mainElementTags.index( element.tag )

                # Check compulsory attributes on this main element
                for attributeName in self.compulsoryAttributes[index]:
                    attributeValue = element.get( attributeName )
                    if attributeValue is None:
                        logging.error( f"Compulsory {systemName!r} attribute is missing from {attributeName} element in record {element.tag} in {k}" )
                    if not attributeValue:
                        logging.warning( f"Compulsory {systemName!r} attribute is blank on {attributeName} element in record {element.tag} in {k}" )

                # Check optional attributes on this main element
                for attributeName in self.optionalAttributes[index]:
                    attributeValue = element.get( attributeName )
                    if attributeValue is not None:
                        if not attributeValue:
                            logging.warning( f"Optional {systemName!r} attribute is blank on {attributeName} element in record {element.tag} in {k}" )

                # Check for unexpected additional attributes on this main element
                for attributeName in element.keys():
                    attributeValue = element.get( attributeName )
                    if attributeName not in self.compulsoryAttributes[index] and attributeName not in self.optionalAttributes[index]:
                        logging.warning( f"Additional {k!r} attribute ({systemName!r}) found on {attributeName} element in record {attributeValue} in {element.tag}" )

                # Check the attributes that must contain unique information (in that particular field -- doesn't check across different attributes)
                for attributeName in self.uniqueAttributes[index]:
                    attributeValue = element.get( attributeName )
                    if attributeValue is not None:
                        if attributeValue in uniqueDict["Attribute_"+str(index)+"_"+attributeName]:
                            logging.error( f"Found {k!r} data repeated in {systemName!r} field on {attributeValue} element in record {attributeName} in {element.tag}" )
                        uniqueDict["Attribute_"+str(index)+"_"+attributeName].append( attributeValue )

                # Check compulsory elements
                for elementName in self.compulsoryElements[index]:
                    if element.find( elementName ) is None:
                        logging.error( f"Compulsory {systemName!r} element is missing (record {elementName}) in {k}" )
                    if not element.find( elementName ).text:
                        logging.warning( f"Compulsory {systemName!r} element is blank (record {elementName}) in {k}" )

                # Check optional elements
                for elementName in self.optionalElements[index]:
                    if element.find( elementName ) is not None:
                        if not element.find( elementName ).text:
                            logging.warning( f"Optional {systemName!r} element is blank (record {elementName}) in {k}" )

                # Check for unexpected additional elements
                for subelement in element:
                    if subelement.tag not in self.compulsoryElements[index] and subelement.tag not in self.optionalElements[index]:
                        logging.warning( f"Additional {systemName!r} element ({element.tag!r}) found (record {subelement.tag}) in {subelement.text} {k}" )

                # Check the elements that must contain unique information (in that particular element -- doesn't check across different elements)
                for elementName in self.uniqueElements[index]:
                    if element.find( elementName ) is not None:
                        text = element.find( elementName ).text
                        if text in uniqueDict["Element_"+str(index)+"_"+elementName]:
                            myLogging = logging.info if element.tag == 'BibleDivisionNames' else logging.error
                            myLogging( f"Found {k!r} data repeated in {systemName!r} element (record {text}) in {elementName}" )
                        uniqueDict["Element_"+str(index)+"_"+elementName].append( text )
            else:
                logging.warning( f"Unexpected element: {element.tag} in record {k} in {systemName}" )
    # end of __validateSystem

    def __str__( self ) -> str:
        """
        This method returns the string representation of a Bible booksNames system.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = "BibleBooksNamesConverter object"
        result += ('\n' if result else '') + f"  Number of bookname systems loaded = {len(self.__XMLSystems)}"
        if BibleOrgSysGlobals.verbosityLevel > 2: # Make it verbose
            for x in self.__XMLSystems:
                result += ('\n' if result else '') + f"  {x}"
                # if self.__ISOLanguages and self.__XMLSystems[x]["languageCode"] and self.__ISOLanguages.isValidLanguageCode( self.__XMLSystems[x]["languageCode"] ):
                #     result += ('\n' if result else '') + "    " + f'Language code {self.__XMLSystems[x]["languageCode"]} = {self.__ISOLanguages.getLanguageName( self.__XMLSystems[x]["languageCode"])}'
                title = self.__XMLSystems[x]['title']
                if title: result += ('\n' if result else '') + f"    {title}"
                version = self.__XMLSystems[x]['version']
                if version: result += ('\n' if result else '') + '    ' + f"Version: {version}"
                date = self.__XMLSystems[x]['date']
                if date: result += ('\n' if result else '') + '    ' + f"Last updated: {date}"
                result += ('\n' if result else '') + '    ' + f"Number of entries = {len(self.__XMLSystems[x]['tree']):,}"
                numDivisions, numLeaders, numBooks = 0, 0, 0
                for element in self.__XMLSystems[x]['tree']:
                    if element.tag == "BibleDivisionNames":
                        numDivisions += 1
                    elif element.tag == "BibleBooknameLeaders":
                        numLeaders += 1
                    elif element.tag == "BibleBookNames":
                        numBooks += 1
                if numDivisions: result += ('\n' if result else '') + '      ' + f"Number of divisions = {numDivisions:,}"
                if numLeaders: result += ('\n' if result else '') + '      ' + f"Number of bookname leaders = {numLeaders:,}"
                if numBooks: result += ('\n' if result else '') + '      ' + f"Number of books = {numBooks:,}"
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
        assert bookList
        assert self.__XMLSystems
        self.importDataToPython()
        assert self.__BookNamesSystemsDict
        if self.__expandedInputSystems: return # No need to do this again

        if bookList is not None:
            for BBB in bookList: # Just check this list is valid
                if not bos_books_codes_py.is_valid_reference_abbreviation( BBB ): logging.error( f"Invalid {BBB!r} in booklist requested for expansion" )

        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "Expanding input abbreviations…" )
        for systemName in self.__BookNamesSystemsDict:
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Expanding {systemName}…" )
            divisionsNamesDict, booknameLeadersDict, bookNamesDict = self.__BookNamesSystemsDict[systemName]
            self.__expandedInputSystems[systemName] = self.expandBibleNamesInputs( systemName, divisionsNamesDict, booknameLeadersDict, bookNamesDict, bookList )
    # end of expandInputs

    def importDataToPython( self ):
        """
        Loads (and pivots) the data (not including the header) into suitable Python containers to use in a Python program.

        If necessary (but not actually recommended), expandInputs could be called before this to fill self.__expandedInputSystems.

        Returns two dictionaries which should each contain entries for each named system.
        """
        assert self.__XMLSystems
        if self.__BookNamesSystemsDict: # We've already done an import/restructuring -- no need to repeat it
            return self.__BookNamesSystemsDict, self.__expandedInputSystems

        # We'll create a number of dictionaries
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, "Importing data into Python dictionary…" )
        self.__BookNamesSystemsDict = {}
        for booksNamesSystemCode in self.__XMLSystems.keys():
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, booksNamesSystemCode )
            # Make the data dictionary for this booksNames system
            myDivisionsNamesDict, myBooknameLeadersDict, myBookNamesDict = {}, {}, {}
            for element in self.__XMLSystems[booksNamesSystemCode]['tree']:
                if element.tag == "BibleDivisionNames":
                    standardAbbreviation = element.get("standardAbbreviation")
                    defaultName = element.find("defaultName").text
                    defaultAbbreviation = element.find("defaultAbbreviation").text
                    inputFields = [ defaultName ]
                    if not defaultName.startswith( defaultAbbreviation ):
                        inputFields.append( defaultAbbreviation )
                    for subelement in element.findall("inputAbbreviation"):
                        if subelement.text in inputFields:
                            logging.warning( f"Superfluous {defaultName!r} entry in inputAbbreviation field for {subelement.text} division in {booksNamesSystemCode!r} booksNames system" )
                        else: inputFields.append( subelement.text )
                    includedBooks = []
                    for subelement in element.findall("includesBook"):
                        BBB = subelement.text
                        if not bos_books_codes_py.is_valid_reference_abbreviation( BBB ):
                            logging.error( f"Unrecognized {BBB!r} book abbreviation in BibleDivisionNames in {booksNamesSystemCode!r} booksNames system" )
                        if BBB in includedBooks:
                            logging.error( f"Duplicate {subelement.text!r} entry in includesBook field for {defaultName!r} division in {booksNamesSystemCode!r} booksNames system" )
                        else: includedBooks.append( BBB )
                    myDivisionsNamesDict[standardAbbreviation] = {"includedBooks":includedBooks, "defaultName":defaultName, "defaultAbbreviation":defaultAbbreviation, "inputFields":inputFields }
                elif element.tag == "BibleBooknameLeaders":
                    standardLeader = element.get("standardLeader")
                    inputFields = [] # Don't include the standard leader here
                    for subelement in element.findall("inputAbbreviation"):
                        adjField = subelement.text + ' '
                        if adjField in inputFields:
                            logging.error( f"Duplicate {subelement.text!r} entry in inputAbbreviation field for {standardLeader!r} bookname leaders in {booksNamesSystemCode!r} booksNames system" )
                        else: inputFields.append( adjField )
                    myBooknameLeadersDict[standardLeader+' '] = inputFields
                elif element.tag == "BibleBookNames":
                    referenceAbbreviation = element.get("referenceAbbreviation")
                    if not bos_books_codes_py.is_valid_reference_abbreviation( referenceAbbreviation ):
                        logging.error( f"Unrecognized {referenceAbbreviation!r} book abbreviation in BibleBookNames in {booksNamesSystemCode!r} booksNames system" )
                    defaultName = element.find("defaultName").text
                    defaultAbbreviation = element.find("defaultAbbreviation").text
                    inputFields = [ defaultName ] # Add the default name to the allowed input fields
                    if defaultAbbreviation != defaultName: inputFields.append( defaultAbbreviation ) # Automatically add the default abbreviation if it's different
                    for subelement in element.findall("inputAbbreviation"):
                        if subelement.text in inputFields:
                            logging.info( f"Superfluous {defaultName!r} entry in inputAbbreviation field for {subelement.text} book in {booksNamesSystemCode!r} booksNames system" )
                        else: inputFields.append( subelement.text )
                    myBookNamesDict[referenceAbbreviation] = { "defaultName":defaultName, "defaultAbbreviation":defaultAbbreviation, "inputFields":inputFields }

            if BibleOrgSysGlobals.strictCheckingFlag: # check for duplicates
                for checkSystemCode in self.__BookNamesSystemsDict:
                    checkDivisionsNamesList, checkBooknameLeadersDict, checkBookNamesDict = self.__BookNamesSystemsDict[checkSystemCode]
                    if checkDivisionsNamesList==myDivisionsNamesDict and checkBookNamesDict==myBookNamesDict:
                        if checkBooknameLeadersDict == myBooknameLeadersDict:
                            logging.error( f"{booksNamesSystemCode} and {checkSystemCode} book name systems are exactly identical ({len(myDivisionsNamesDict)} divisions, {len(myBookNamesDict)} book names, {len(myBooknameLeadersDict)} leaders)" )
                        else: # only the leaders are different
                            logging.error( f"{booksNamesSystemCode} and {checkSystemCode} book name systems are mostly identical ({len(myDivisionsNamesDict)} divisions, {len(myBookNamesDict)} book names)" )

            # Now put it into my dictionary for easy access
            self.__BookNamesSystemsDict[booksNamesSystemCode] = myDivisionsNamesDict, myBooknameLeadersDict, myBookNamesDict
        return self.__BookNamesSystemsDict, self.__expandedInputSystems
    # end of importDataToPython


    def pickle( self, filepath=None ):
        """
        Writes the information tables to a .pickle file that can be easily loaded into a Python3 program.
        """
        import pickle

        assert self.__XMLSystems
        self.importDataToPython()
        assert self.__BookNamesSystemsDict

        if not filepath:
            folder = BibleOrgSysGlobals.DEFAULT_WRITEABLE_DERIVED_DATAFILES_FOLDERPATH
            if not os.path.exists( folder ): os.mkdir( folder )
            filepath = os.path.join( folder, self.__filenameBase + '_Tables.pickle' )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Exporting to {filepath}…" )
        with open( filepath, 'wb' ) as myFile:
            pickle.dump( self.__BookNamesSystemsDict, myFile )
            #pickle.dump( self.__expandedInputSystems, myFile )
    # end of pickle


    def exportDataToPython( self, filepath=None ):
        """
        Writes the information tables to a .py file that can be cut and pasted into a Python program.
        """
        def exportPythonDict( theFile, theDict, dictName, keyComment, fieldsComment ):
            """Exports theDict to theFile."""
            assert isinstance( theDict, dict )
            for dictKey in theDict.keys(): # Have to iterate this :(
                fieldsCount = len( theDict[dictKey] ) if isinstance( theDict[dictKey], (tuple,dict,list) ) else 1
                break # We only check the first (random) entry we get
            theFile.write( f'  "{dictName}": {{\n    # Key is {keyComment}\n    # Fields ({fieldsCount}) are: {fieldsComment}\n' )
            for dictKey in theDict.keys():
                theFile.write( f'    {repr(dictKey)}: {repr(theDict[dictKey])},\n' )
            theFile.write( f"  }}, # end of {dictName} ({len(theDict)} entries)\n\n" )
        # end of exportPythonDict

        #def exportPythonOrderedDict( theFile, theDict, dictName, keyComment, fieldsComment ):
            #"""Exports theDict to theFile."""
            #assert isinstance( theDict, OrderedDict )
            #for dictKey in theDict.keys(): # Have to iterate this :(
                #fieldsCount = len( theDict[dictKey] ) if isinstance( theDict[dictKey], (tuple,dict,list) ) else 1
                #break # We only check the first (random) entry we get
            #theFile.write( f'  "{dictName}": OrderedDict([\n    # Key is {keyComment}\n    # Fields ({fieldsCount}) are: {fieldsComment}\n' )
            #for dictKey in theDict.keys():
                #theFile.write( f'    ({repr(dictKey)}, {repr(theDict[dictKey])}),\n' )
            #theFile.write( f"  ]), # end of {dictName} ({len(theDict)} entries)\n\n" )
        ## end of exportPythonOrderedDict

        def exportPythonList( theFile, theList, listName, fieldsComment ):
            """Exports theList to theFile."""
            assert isinstance( theList, list )
            fieldsCount = len( theList[0] ) if isinstance( theList[0], (tuple,dict,list) ) else 1
            theFile.write( f'  "{listName}": [\n    # Fields ({fieldsCount}) are: {fieldsComment}\n' )
            for j,entry in enumerate(theList):
                theFile.write( f'    {repr(entry)}, # {j}\n' )
            theFile.write( f"  ], # end of {listName} ({len(theList)} entries)\n\n" )
        # end of exportPythonList

        from datetime import datetime

        assert self.__XMLSystems
        self.importDataToPython()
        assert self.__BookNamesSystemsDict

        raise Exception( "Python export not working properly yet" )
        if not filepath: filepath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_DERIVED_DATAFILES_FOLDERPATH.joinpath( self.__filenameBase + '_Tables.py' )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Exporting to {filepath}…" )
        # Split into three lists/dictionaries
        with open( filepath, 'wt', encoding='utf-8' ) as myFile:
            myFile.write( f"# {filepath}\n#\n" )
            myFile.write( f"# This UTF-8 file was automatically generated by BibleBooksNames.py V{PROGRAM_VERSION} on {datetime.now()}\n#\n" )
            #if self.title: myFile.write( f"# {self.title}\n" )
            #if self.version: myFile.write( f"#  Version: {self.version}\n" )
            #if self.date: myFile.write( f"#  Date: {self.date}\n#\n" )
            #myFile.write( f"#   {len(self.namesTree)} {self.XMLTreeTag} entries loaded from the original XML file.\n" )
            myFile.write( f"#   {len(self.__XMLSystems)} {self.XMLTreeTag} loaded from the original XML files.\n#\n\n" )
            #myFile.write( "from collections import OrderedDict\n\n" )
            myFile.write( "\ndivisionNamesList = {\n  # Key is languageCode\n  # Fields are divisionNames\n\n" )
            for systemName in self.__BookNamesSystemsDict:
                divisionsNamesDict, booknameLeadersDict, bookNamesDict = self.__BookNamesSystemsDict[systemName]
                exportPythonList( myFile, divisionsNamesDict, systemName, "startsWith( string), defaultName (string), defaultAbbreviation (string), inputFields (list of strings) all in a dictionary" )
            myFile.write( f"}} # end of divisionNamesList ({len(self.__BookNamesSystemsDict)} systems)\n\n\n" )
            myFile.write( "\nbooknameLeadersDict = {\n  # Key is languageCode\n  # Fields are divisionNames\n\n" )
            for systemName in self.__BookNamesSystemsDict:
                divisionsNamesDict, booknameLeadersDict, bookNamesDict = self.__BookNamesSystemsDict[systemName]
                exportPythonDict( myFile, booknameLeadersDict, systemName, "standardLeader (all fields include a trailing space)", "inputAlternatives (list of strings)" )
            myFile.write( f"}} # end of booknameLeadersDict ({len(self.__BookNamesSystemsDict)} systems)\n\n\n" )
            myFile.write( "\nbookNamesDict = {\n  # Key is languageCode\n  # Fields are divisionNames\n\n" )
            for systemName in self.__BookNamesSystemsDict:
                divisionsNamesDict, booknameLeadersDict, bookNamesDict = self.__BookNamesSystemsDict[systemName]
                exportPythonDict( myFile, bookNamesDict, systemName, "referenceAbbreviation", "defaultName (string), defaultAbbreviation (string), inputAbbreviations (list of strings) all in a dictionary" )
            myFile.write( f"}} # end of bookNamesDict ({len(self.__BookNamesSystemsDict)} systems)\n\n\n" )
            if self.__expandedInputSystems:
                myFile.write( "\ndivisionsNamesInputDict = {\n  # Key is languageCode\n  # Fields are divisionNames\n\n" )
                for systemName in self.__BookNamesSystemsDict:
                    if systemName in self.__expandedInputSystems:
                        divisionsNamesInputDict, bookNamesInputDict = self.__expandedInputSystems[systemName]
                        exportPythonDict( myFile, divisionsNamesInputDict, "divisionsNamesInputDict", "UpperCaseInputString (sorted with longest first)", "index (into divisionNamesList above)" )
                myFile.write( f"}} # end of divisionsNamesInputDict ({len(self.__BookNamesSystemsDict)} systems)\n\n\n" )
                myFile.write( "\nbookNamesInputDict = {\n  # Key is languageCode\n  # Fields are divisionNames\n\n" )
                for systemName in self.__BookNamesSystemsDict:
                    if systemName in self.__expandedInputSystems:
                        divisionsNamesInputDict, bookNamesInputDict = self.__expandedInputSystems[systemName]
                        exportPythonDict( myFile, bookNamesInputDict, "bookNamesInputDict", "UpperCaseInputString (sorted with longest first)", "referenceAbbreviation (string)" )
                myFile.write( f"}} # end of bookNamesInputDict ({len(self.__BookNamesSystemsDict)} systems)\n" )
    # end of exportDataToPython

    def exportDataToJSON( self, filepath=None ):
        """
        Writes the information tables to a .json file that can be easily loaded into a Java program.

        See http://en.wikipedia.org/wiki/JSON.
        """
        from datetime import datetime
        import json

        assert self.__XMLSystems
        self.importDataToPython()
        assert self.__BookNamesSystemsDict

        if not filepath: filepath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_DERIVED_DATAFILES_FOLDERPATH.joinpath( self.__filenameBase + '_Tables.json' )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Exporting to {filepath}…" )
        with open( filepath, 'wt', encoding='utf-8' ) as myFile:
            #myFile.write( f"# {filepath}\n#\n" ) # Not sure yet if these comment fields are allowed in JSON
            #myFile.write( f"# This UTF-8 file was automatically generated by BibleBooksCodes.py V{PROGRAM_VERSION} on {datetime.now()}\n#\n" )
            #if self.titleString: myFile.write( f"# {self.titleString} data\n" )
            #if self.PROGRAM_VERSION: myFile.write( f"#  Version: {self.PROGRAM_VERSION}\n" )
            #if self.dateString: myFile.write( f"#  Date: {self.dateString}\n#\n" )
            #myFile.write( f"#   {len(self.XMLTree)} {self.XMLTreeTag} loaded from the original XML file.\n#\n\n" )
            json.dump( self.__BookNamesSystemsDict, myFile, ensure_ascii=False, indent=2 )
            #myFile.write( f"\n\n# end of {os.path.basename(filepath)}"
    # end of exportDataToJSON

    def exportDataToC( self, filepath=None ):
        """
        Writes the information tables to a .h file that can be included in c and c++ programs.
        """
        def exportPythonDict( theFile, theDict, dictName, structName, fieldsComment ):
            """Exports theDict to theFile."""
            def convertEntry( entry ):
                """Convert special characters in an entry…"""
                result = ""
                for field in entry:
                    if result: result += ", " # Separate the fields
                    if field is None: result += '""'
                    elif isinstance( field, str): result += '"' + str(field).replace('"','\\"') + '"'
                    elif isinstance( field, int): result += str(field)
                    else: logging.error( f"Cannot convert unknown field type {field!r} in entry {entry!r}" )
                return result

            theFile.write( f"static struct {structName} {dictName}[] = {\n  // Fields are {fieldsComment}\n" )
            for entry in sorted(theDict.keys()):
                if isinstance( entry, str ):
                    theFile.write( f"  {\"{entry}\", {convertEntry(theDict[entry])}},\n" )
                elif isinstance( entry, int ):
                    theFile.write( f"  {{entry}, {convertEntry(theDict[entry])}},\n" )
                else:
                    logging.error( f"Can't handle this type of data yet: {entry}" )
            theFile.write( f"}; // {dictName}\n\n" )
        # end of exportPythonDict

        from datetime import datetime

        assert self.__XMLSystems
        self.importDataToPython()
        assert self.__BookNamesSystemsDict

        if not filepath: filepath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_DERIVED_DATAFILES_FOLDERPATH.joinpath( self.__filenameBase + '_Tables.h' )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Exporting to {filepath}…" )
        raise Exception( "C export not written yet -- sorry." )

        ifdefName = self.__filenameBase.upper() + "_Tables_h"
        with open( filepath, 'wt', encoding='utf-8' ) as myFile:
            myFile.write( f"// {filepath}\n//\n" )
            myFile.write( f"// This UTF-8 file was automatically generated by BibleBooksNames.py V{PROGRAM_VERSION} on {datetime.now()}\n//\n" )
            if self.title: myFile.write( f"// {self.title}\n" )
            if self.version: myFile.write( f"//  Version: {self.version}\n" )
            if self.date: myFile.write( f"//  Date: {self.date}\n//\n" )
            myFile.write( f"//   {len(self.namesTree)} {self.XMLTreeTag} loaded from the original XML file.\n//\n\n" )
            myFile.write( f"#ifndef {ifdefName}\n#define {ifdefName}\n\n" )
            exportPythonDict( myFile, IDDict, "IDDict", "{int id; char* refAbbrev; char* SBLAbbrev; char* OSISAbbrev; char* PTAbbrev; char* PTNum; char* EngName;}", "id (sorted), referenceAbbreviation, SBLAbbreviation, OSISAbbreviation, USFMAbbreviation, USFMNumberString, nameEnglish (comment only)" )
            myFile.write( f"#endif // {ifdefName}\n" )
    # end of exportDataToC
# end of BibleBooksNamesConverter class


def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    sampleBookList = ['GEN','JDG','SA1','SA2','KI1','KI2','MA4','MAT','MRK','LUK','JHN','ACT','ROM','CO1','CO2','PE1','PE2','JDE','REV']
    #sampleBookList = ['GEN','JDG','SA1','SA2','KI1','KI2','MA1','MA2']
    #sampleBookList = ['MAT','MRK','LUK','JHN','ACT','ROM','CO1','CO2','GAL','EPH','PHP','COL','PE1','PE2','JDE','REV']
    if BibleOrgSysGlobals.commandLineArguments.export:
        bbnsc = BibleBooksNamesConverter().loadSystems() # Load the XML
        #if BibleOrgSysGlobals.commandLineArguments.expandDemo: # Expand the inputAbbreviations to find all shorter unambiguous possibilities
        #    bbnsc.expandInputs( sampleBookList )
        bbnsc.pickle() # Produce the .pickle file
        bbnsc.exportDataToJSON() # Produce a json output file
        # bbnsc.exportDataToPython() # Produce the .py tables
        # bbnsc.exportDataToC() # Produce the .h and .c tables

    else: # Must be demo mode
        # Demo the converter object
        bbnsc = BibleBooksNamesConverter().loadSystems() # Load the XML
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, bbnsc ) # Just print a summary
        #if BibleOrgSysGlobals.commandLineArguments.expandDemo: # Expand the inputAbbreviations to find all shorter unambiguous possibilities
        #    bbnsc.expandInputs( sampleBookList )
        #    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, bbnsc ) # Just print a summary
# end of BibleBooksNamesConverter.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    sampleBookList = ['GEN','JDG','SA1','SA2','KI1','KI2','MA4','MAT','MRK','LUK','JHN','ACT','ROM','CO1','CO2','PE1','PE2','JDE','REV']
    #sampleBookList = ['GEN','JDG','SA1','SA2','KI1','KI2','MA1','MA2']
    #sampleBookList = ['MAT','MRK','LUK','JHN','ACT','ROM','CO1','CO2','GAL','EPH','PHP','COL','PE1','PE2','JDE','REV']
    if BibleOrgSysGlobals.commandLineArguments.export:
        bbnsc = BibleBooksNamesConverter().loadSystems() # Load the XML
        #if BibleOrgSysGlobals.commandLineArguments.expandDemo: # Expand the inputAbbreviations to find all shorter unambiguous possibilities
        #    bbnsc.expandInputs( sampleBookList )
        bbnsc.pickle() # Produce the .pickle file
        bbnsc.exportDataToJSON() # Produce a json output file
        # bbnsc.exportDataToPython() # Produce the .py tables
        # bbnsc.exportDataToC() # Produce the .h and .c tables

    else: # Must be demo mode
        # Demo the converter object
        bbnsc = BibleBooksNamesConverter().loadSystems() # Load the XML
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, bbnsc ) # Just print a summary
        #if BibleOrgSysGlobals.commandLineArguments.expandDemo: # Expand the inputAbbreviations to find all shorter unambiguous possibilities
        #    bbnsc.expandInputs( sampleBookList )
        #    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, bbnsc ) # Just print a summary
# end of BibleBooksNamesConverter.fullDemo

if __name__ == '__main__':
    from multiprocessing import set_start_method, freeze_support
    set_start_method('fork') # The default was changed on POSIX systems from 'fork' to 'forkserver' in Python3.14
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of BibleBooksNamesConverter.py
