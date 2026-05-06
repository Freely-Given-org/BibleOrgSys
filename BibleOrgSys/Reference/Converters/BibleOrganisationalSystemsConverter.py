#!/usr/bin/env -S uv run
# -\*- coding: utf-8 -\*-
# SPDX-License-Identifier: GPL-3.0-or-later
#
# BibleOrganisationalSystemsConverter.py
#
# Module handling BibleOrganisationalSystems.xml to produce C and Python data tables
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
Module handling BibleOrganisationalSystems.xml to produce C and Python data tables.
"""

import logging
import os.path
from datetime import datetime
from xml.etree.ElementTree import ElementTree

from BibleOrgSys.Misc.singleton import singleton
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys.Reference.ISO_639_3_Languages import ISO_639_3_Languages
from BibleOrgSys.Reference.BibleBookOrders import BibleBookOrderSystems
from BibleOrgSys.Reference.BiblePunctuationSystems import BiblePunctuationSystems
from BibleOrgSys.Reference.BibleVersificationSystems import BibleVersificationSystems
from BibleOrgSys.Reference.BibleBooksNames import BibleBooksNamesSystems


LAST_MODIFIED_DATE = '2022-07-12' # by RJH
SHORT_PROGRAM_NAME = "BibleOrganisationalSystemsConverter"
PROGRAM_NAME = "Bible Organisation Systems converter"
PROGRAM_VERSION = '0.27'
PROGRAM_NAME_VERSION = f'{PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False



@singleton # Can only ever have one instance
class BibleOrganisationalSystemsConverter:
    """
    Class for handling and converting BibleOrganisationalSystems.
    """

    def __init__( self ) -> None:
        """
        Constructor: expects the filepath of the source XML file.
        Loads (and crudely validates the XML file) into an element tree.
        """
        self._filenameBase = 'BibleOrganisationalSystems'

        # These fields are used for parsing the XML
        self._treeTag = 'BibleOrganisationalSystems'
        self._headerTag = 'header'
        self._mainElementTag = 'BibleOrganisationalSystem'

        # These fields are used for automatically checking/validating the XML
        self._compulsoryAttributes = ( 'type', )
        self._optionalAttributes = ()
        self._uniqueAttributes = ()
        self._compulsoryElements = ( 'referenceAbbreviation', 'languageCode', )
        self._optionalElements = ( 'name', 'completionDate', 'publicationDate', 'copyright', 'versificationSystem', 'punctuationSystem', 'bookOrderSystem', 'booksNamesSystem',
                                    'translator', 'publisher', 'derivedFrom', 'usesText', 'includesBooks', 'url', 'comment', )
        self._uniqueElements = ()
        self._allowedMultiple = ( 'name', 'translator', 'derivedFrom', 'usesText', 'url', 'comment', )

        # These are fields that we will fill later
        self.title, self.version, self.date = None, None, None
        self.header, self._XMLTree = None, None
        self.__dataDicts = None

        # Get the data tables that we need for proper checking
        self._ISOLanguages = ISO_639_3_Languages().loadData()
        self._BibleBookOrderSystems = BibleBookOrderSystems().loadData()
        self._BiblePunctuationSystems = BiblePunctuationSystems().loadData()
        self._BibleVersificationSystems = BibleVersificationSystems().loadData()
        self._BibleBooksNamesSystems = BibleBooksNamesSystems().loadData()
    # end of BibleOrganisationalSystemsConverter.__init__


    def __str__( self ) -> str:
        """
        This method returns the string representation of a Bible book code.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = ""
        if self.title: result += ('\n' if result else '') + self.title
        if self.version: result += ('\n' if result else '') + f"  Version: {self.version}"
        if self.date: result += ('\n' if result else '') + f"  Date: {self.date}"
        result += ('\n' if result else '') + f"  Number of entries = {len(self._XMLTree)}"
        return result
    # end of BibleOrganisationalSystemsConverter.__str__


    def __len__( self ):
        """ Returns the number of items loaded. """
        return len( self._XMLTree )
    # end of BibleOrganisationalSystemsConverter.__len__


    def loadAndValidate( self, XMLFileOrFilepath=None ):
        """
        Loads (and crudely validates the XML file) into an element tree.
            Allows the filepath of the source XML file to be specified, otherwise uses the default.
        """
        if self._XMLTree is None: # We mustn't have already have loaded the data
            if XMLFileOrFilepath is None:
                # XMLFileOrFilepath = BibleOrgSysGlobals.BOS_DATAFILES_FOLDERPATH.joinpath( f'{self._filenameBase}.xml' ) # Relative to module, not cwd
                import importlib.resources # From Python 3.7 onwards -- handles zipped resources also
                XMLFileOrFilepath = importlib.resources.files('BibleOrgSys.DataFiles').joinpath( f'{self._filenameBase}.xml' )

            self._load( XMLFileOrFilepath )
            if BibleOrgSysGlobals.strictCheckingFlag:
                self._validate()
        return self
    # end of BibleOrganisationalSystemsConverter.loadAndValidate


    def _load( self, XMLFileOrFilepath ):
        """
        Load the source XML file and remove the header from the tree.
        Also, extracts some useful elements from the header element.
        """
        assert XMLFileOrFilepath
        self.__XMLFileOrFilepath = XMLFileOrFilepath
        assert self._XMLTree is None or len(self._XMLTree)==0 # Make sure we're not doing this twice

        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"Loading BibleOrganisationalSystems XML file from {self.__XMLFileOrFilepath!r}…" )
        self._XMLTree = ElementTree().parse( self.__XMLFileOrFilepath )
        assert len(self._XMLTree) # Fail here if we didn't load anything at all

        if self._XMLTree.tag  == self._treeTag:
            header = self._XMLTree[0]
            if header.tag == self._headerTag:
                self.header = header
                self._XMLTree.remove( header )
                if len(header)>1:
                    logging.info( "Unexpected elements in header" )
                elif len(header)==0:
                    logging.info( "Missing work element in header" )
                else:
                    work = header[0]
                    if work.tag == "work":
                        self.version = work.find('version').text
                        self.date = work.find('date').text
                        self.title = work.find('title').text
                    else:
                        logging.warning( "Missing work element in header" )
            else:
                logging.warning( f"Missing header element (looking for {self._headerTag!r} tag)" )
        else:
            logging.error( f"Expected to load {self._treeTag!r} but got {self._XMLTree.tag!r}" )
    # end of BibleOrganisationalSystemsConverter._load


    def _validate( self ):
        """
        Check/validate the loaded data.
        """
        assert len(self._XMLTree)

        uniqueDict = {}
        for elementName in self._uniqueElements: uniqueDict["Element_"+elementName] = []
        for attributeName in self._uniqueAttributes: uniqueDict["Attribute_"+attributeName] = []

        expectedID = 1
        for j,element in enumerate(self._XMLTree):
            if element.tag == self._mainElementTag:
                # Check compulsory attributes on this main element
                for attributeName in self._compulsoryAttributes:
                    attributeValue = element.get( attributeName )
                    if attributeValue is None:
                        logging.error( f"Compulsory {j!r} attribute is missing from {attributeName} element in record {element.tag}" )
                    if not attributeValue:
                        logging.warning( f"Compulsory {j!r} attribute is blank on {attributeName} element in record {element.tag}" )

                # Check optional attributes on this main element
                for attributeName in self._optionalAttributes:
                    attributeValue = element.get( attributeName )
                    if attributeValue is not None:
                        if not attributeValue:
                            logging.warning( f"Optional {j!r} attribute is blank on {attributeName} element in record {element.tag}" )

                # Check for unexpected additional attributes on this main element
                for attributeName in element.keys():
                    attributeValue = element.get( attributeName )
                    if attributeName not in self._compulsoryAttributes and attributeName not in self._optionalAttributes:
                        logging.warning( f"Additional {element.tag!r} attribute ({j!r}) found on {attributeName} element in record {attributeValue}" )

                # Check the attributes that must contain unique information (in that particular field -- doesn't check across different attributes)
                for attributeName in self._uniqueAttributes:
                    attributeValue = element.get( attributeName )
                    if attributeValue is not None:
                        if attributeValue in uniqueDict["Attribute_"+attributeName]:
                            logging.error( f"Found {element.tag!r} data repeated in {j!r} field on {attributeValue} element in record {attributeName}" )
                        uniqueDict["Attribute_"+attributeName].append( attributeValue )

                ID = element.find("referenceAbbreviation").text

                # Check compulsory elements
                for elementName in self._compulsoryElements:
                    if element.find( elementName ) is None:
                        logging.error( f"Compulsory {ID!r} element is missing in record with ID {j!r} (record {elementName})" )
                    elif not element.find( elementName ).text:
                        logging.warning( f"Compulsory {ID!r} element is blank in record with ID {j!r} (record {elementName})" )

                # Check optional elements
                for elementName in self._optionalElements:
                    if element.find( elementName ) is not None:
                        if not element.find( elementName ).text:
                            logging.warning( f"Optional {ID!r} element is blank in record with ID {j!r} (record {elementName})" )

                # Check for unexpected additional elements
                for subelement in element:
                    if subelement.tag not in self._compulsoryElements and subelement.tag not in self._optionalElements:
                        logging.warning( f"Additional {subelement.text!r} element ({ID!r}) found in record with ID {j!r} (record {subelement.tag})" )

                # Check the elements that must contain unique information (in that particular element -- doesn't check across different elements)
                for elementName in self._uniqueElements:
                    if element.find( elementName ) is not None:
                        text = element.find( elementName ).text
                        if text in uniqueDict["Element_"+elementName]:
                            logging.error( f"Found {elementName!r} data repeated in {ID!r} element in record with ID {j!r} (record {text})" )
                        uniqueDict["Element_"+elementName].append( text )

                # Special checks of particular fields
                if element.find('includesBooks') is not None:
                    bookList = element.find('includesBooks').text.split()
                    for BBB in bookList:
                        if not bos_books_codes_py.is_valid_reference_abbreviation_py( BBB ):
                            logging.critical( f"Unrecognized {ID!r} Bible book code found in 'includesBooks' in record with ID {j!r} (record {BBB})" )
                        if bookList.count( BBB ) > 1:
                            logging.error( f"Multiple {ID!r} Bible book codes found in 'includesBooks' in record with ID {j!r} (record {BBB})" )

            else:
                logging.warning( f"Unexpected element: {element.tag} in record {j}" )
    # end of BibleOrganisationalSystemsConverter._validate


    def importDataToPython( self ):
        """
        Loads (and pivots) the data (not including the header) into suitable Python containers to use in a Python program.
        (Of course, you can just use the elementTree in self._XMLTree if you prefer.)
        """
        assert len(self._XMLTree)
        if self.__dataDicts: # We've already done an import/restructuring -- no need to repeat it
            return self.__dataDicts

        # We'll create a number of dictionaries with different elements as the key
        dataDict, indexDict, combinedIndexDict = {}, {}, {}
        for element in self._XMLTree:
            bits = {}
            # Get the required information out of the tree for this element
            # Start with the compulsory elements and type attribute
            referenceAbbreviation = element.find('referenceAbbreviation').text
            bits['referenceAbbreviation'] = referenceAbbreviation
            myType = element.get( 'type' )
            bits['type'] = myType
            if myType not in BibleOrgSysGlobals.ALLOWED_ORGANISATIONAL_TYPES:
                logging.error( f"Unrecognized {referenceAbbreviation!r} type for {BibleOrgSysGlobals.ALLOWED_ORGANISATIONAL_TYPES!r} (expected one of {myType})" )
            languageCode = element.find('languageCode').text
            if self._ISOLanguages and not self._ISOLanguages.isValidLanguageCode( languageCode ): # Check that we have a valid language code
                if languageCode != '???':
                    logging.error( f"Unrecognized {languageCode!r} ISO-639-3 language code in {referenceAbbreviation!r} organisational system" )
            bits['languageCode'] = languageCode

            # Now work on the optional elements
            for name in ( 'name', 'publicationDate', 'versificationSystem', 'punctuationSystem', 'bookOrderSystem', 'booksNamesSystem', 'derivedFrom', 'usesText', 'includesBooks' ):
                for nameData in element.findall(name):
                    if name in self._allowedMultiple: # Put multiple entries into a list
                        if name not in bits: bits[name] = [nameData.text]
                        else: bits[name].append( nameData.text )
                    else: # Not allowed multiples
                        if name in bits: logging.error( f"Unexpected multiple {name} elements found in {referenceAbbreviation} {myType}" )
                        if name=='includesBooks': # special handling
                            bits['includesBooks'] = nameData.text.split()
                            for BBB in bits['includesBooks']:
                                if not bos_books_codes_py.is_valid_reference_abbreviation_py( BBB ):
                                    logging.error( f"Unrecognized {myType!r} Bible book code found in 'includesBooks' in {BBB} {referenceAbbreviation}" )
                        else: bits[name] = nameData.text # normal handling

            extension = '_' + myType
            extendedRA = referenceAbbreviation if referenceAbbreviation.endswith(extension) else (referenceAbbreviation + extension)
            dataDict[extendedRA] = bits
            if referenceAbbreviation in indexDict: indexDict[referenceAbbreviation].append( extendedRA )
            else: indexDict[referenceAbbreviation] = [extendedRA]
            if referenceAbbreviation in combinedIndexDict: combinedIndexDict[referenceAbbreviation].append( extendedRA )
            else: combinedIndexDict[referenceAbbreviation] = [extendedRA]
            if extendedRA != referenceAbbreviation:
                #assert extendedRA not in combinedIndexDict
                if extendedRA in combinedIndexDict: logging.error( f"Found {extendedRA} in combinedIndexDict" )
                combinedIndexDict[extendedRA] = [extendedRA]
        assert len(indexDict) <= len(dataDict)
        assert len(combinedIndexDict) >= len(indexDict)

        if BibleOrgSysGlobals.strictCheckingFlag: # We'll do quite a bit more cross-checking now
            for extendedReferenceAbbreviation,data in dataDict.items():
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, extendedReferenceAbbreviation, data )
                systemType = data['type']
                if systemType=='edition':
                    if 'derivedFrom' in data: logging.error( f"{extendedReferenceAbbreviation} shouldn't use 'derivedFrom' {data['derivedFrom']!r}" )
                    if 'usesText' not in data: logging.error( f"{extendedReferenceAbbreviation} doesn't specify 'usesText'" )
                    else: # have a 'usesText' list
                        for textAbbrev in data['usesText']:
                            if textAbbrev not in indexDict: logging.error( f"{extendedReferenceAbbreviation} specifies unknown {textAbbrev!r} text in 'usesText' field" )
                            elif len(indexDict[textAbbrev]) > 1: # it could be ambiguous
                                found = 0
                                for thisType in ('revision','translation','original'): # but not 'edition'
                                    usesTextExtended = textAbbrev + '_' + thisType
                                    if usesTextExtended in dataDict:
                                        foundOne = usesTextExtended
                                        found += 1
                                assert found > 0
                                if found==1: # ah, it's not actually ambiguous
                                    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"Adjusted text used for {extendedReferenceAbbreviation} from the ambiguous {textAbbrev!r} to the extended name {foundOne!r}" )
                                    data['usesText'].remove( textAbbrev)
                                    data['usesText'].append( foundOne )
                                else: logging.warning( f"{extendedReferenceAbbreviation} specifies ambiguous {textAbbrev!r} (could be {indexDict[textAbbrev]}) texts in 'usesText' field" )
                elif systemType=='revision':
                    if 'derivedFrom' not in data: logging.error( f"{extendedReferenceAbbreviation} doesn't specify 'derivedFrom'" )
                    else:
                        for df in data['derivedFrom']:
                            if df not in indexDict: logging.error( f"{extendedReferenceAbbreviation} specifies unknown {df!r} text in 'derivedFrom' field" )
                            elif len(indexDict[df]) > 1: logging.warning( f"{extendedReferenceAbbreviation} specifies ambiguous {df!r} (could be {indexDict[df]}) texts in 'derivedFrom' field" )
                elif systemType=='translation':
                    if 'derivedFrom' not in data: logging.warning( f"{extendedReferenceAbbreviation} doesn't specify 'derivedFrom'" )
                    else:
                        for df in data['derivedFrom']:
                            if df not in indexDict: logging.error( f"{extendedReferenceAbbreviation} specifies unknown {df!r} text in 'derivedFrom' field" )
                            elif len(indexDict[df]) > 1: logging.warning( f"{extendedReferenceAbbreviation} specifies ambiguous {df!r} (could be {indexDict[df]}) texts in 'derivedFrom' field" )
                elif systemType=='original':
                    if 'derivedFrom' in data: logging.error( f"{extendedReferenceAbbreviation} shouldn't use 'derivedFrom' {data['derivedFrom']!r}" )
                if 'versificationSystem' in data and data['versificationSystem'] not in ('None', 'Unknown'):
                    if not self._BibleVersificationSystems.isValidVersificationSystemName( data['versificationSystem'] ):
                        extra = f"\n  Available systems are {self._BibleVersificationSystems.getAvailableVersificationSystemNames()}" if BibleOrgSysGlobals.verbosityLevel > 2 else ''
                        logging.error( f"Unknown {data['versificationSystem']!r} versification system name in {extendedReferenceAbbreviation}{extra}" )
                if 'punctuationSystem' in data and data['punctuationSystem'] not in ('None', 'Unknown'):
                    if not self._BiblePunctuationSystems.isValidPunctuationSystemName( data['punctuationSystem'] ):
                        extra = f"\n  Available systems are {self._BiblePunctuationSystems.getAvailablePunctuationSystemNames()}" if BibleOrgSysGlobals.verbosityLevel > 2 else ''
                        logging.error( f"Unknown {data['punctuationSystem']!r} punctuation system name in {extendedReferenceAbbreviation}{extra}" )

        self.__dataDicts = dataDict, indexDict, combinedIndexDict
        return self.__dataDicts
    # end of importDataToPython


    def pickle( self, filepath=None ):
        """
        Writes the information tables to a .pickle file that can be easily loaded into a Python3 program.
        """
        import pickle

        assert len(self._XMLTree)
        self.importDataToPython()
        assert self.__dataDicts

        if not filepath:
            folder = BibleOrgSysGlobals.DEFAULT_WRITEABLE_DERIVED_DATAFILES_FOLDERPATH
            if not os.path.exists( folder ): os.mkdir( folder )
            filepath = os.path.join( folder, self._filenameBase + '_Tables.pickle' )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Exporting BibleOrganisationalSystems to {filepath}…" )
        with open( filepath, 'wb' ) as myFile:
            pickle.dump( self.__dataDicts, myFile )
    # end of pickle


    def exportDataToPython( self, filepath=None ):
        """
        Writes the information tables to a .py file that can be cut and pasted into a Python program.
        """
        def exportPythonDict( theFile, theDict, dictName, keyComment, fieldsComment ):
            """Exports theDict to theFile."""
            theFile.write( f"{dictName} = {{\n  # Key is {keyComment}\n  # Fields are: {fieldsComment}\n" )
            for dictKey in sorted(theDict.keys()):
                theFile.write( f'  {repr(dictKey)}: {theDict[dictKey]},\n' )
            theFile.write( f"}}\n# end of {dictName}\n\n" )
        # end of exportPythonDict


        assert len(self._XMLTree)
        self.importDataToPython()
        assert self.__dataDicts

        if not filepath: filepath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_DERIVED_DATAFILES_FOLDERPATH.joinpath( self._filenameBase + '_Tables.py' )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Exporting to {filepath}…" )

        dataDict, indexDict, combinedIndexDict = self.importDataToPython()
        with open( filepath, 'wt', encoding='utf-8' ) as myFile:
            myFile.write( f"# {filepath}\n#\n" )
            myFile.write( f"# This UTF-8 file was automatically generated by BibleOrganisationalSystemsConverter.py V{PROGRAM_VERSION} on {datetime.now()}\n#\n" )
            if self.title: myFile.write( f"# {self.title}\n" )
            if self.version: myFile.write( f"#  Version: {self.version}\n" )
            if self.date: myFile.write( f"#  Date: {self.date}\n#\n" )
            myFile.write( f"#   {len(self._XMLTree)} {self._treeTag} entries loaded from the original XML file.\n" )
            #myFile.write( f"#   {len(self.systems)} {self._treeTag} loaded from the original XML files.\n#\n\n" )
            exportPythonDict( myFile, dataDict, "dataDict", "extendedReferenceAbbreviation", "referenceAbbreviation, SBLAbbreviation, OSISAbbreviation, ParatextAbbreviation, ParatextNumberString, nameEnglish (comment only)" )
            exportPythonDict( myFile, indexDict, "indexDict", "referenceAbbreviation", "id, SBLAbbreviation, OSISAbbreviation, ParatextAbbreviation, ParatextNumberString, nameEnglish (comment only)" )
            exportPythonDict( myFile, combinedIndexDict, "combinedIndexDict", "referenceAbbreviation", "id, SBLAbbreviation, OSISAbbreviation, ParatextAbbreviation, ParatextNumberString, nameEnglish (comment only)" )
    # end of exportDataToPython


    def exportDataToJSON( self, filepath=None ):
        """
        Writes the information tables to a .json file that can be easily loaded into a Java program.

        See http://en.wikipedia.org/wiki/JSON.
        """
        import json

        assert len(self._XMLTree)
        self.importDataToPython()
        assert self.__dataDicts

        if not filepath: filepath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_DERIVED_DATAFILES_FOLDERPATH.joinpath( self._filenameBase + '_Tables.json' )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Exporting to {filepath}…" )
        with open( filepath, 'wt', encoding='utf-8' ) as myFile:
            #myFile.write( f"# {filepath}\n#\n" ) # Not sure yet if these comment fields are allowed in JSON
            #myFile.write( f"# This UTF-8 file was automatically generated by BibleBooksCodes.py V{PROGRAM_VERSION} on {datetime.now()}\n#\n" )
            #if self.titleString: myFile.write( f"# {self.titleString} data\n" )
            #if self.PROGRAM_VERSION: myFile.write( f"#  Version: {self.PROGRAM_VERSION}\n" )
            #if self.dateString: myFile.write( f"#  Date: {self.dateString}\n#\n" )
            #myFile.write( f"#   {len(self._XMLTree)} {self._treeTag} loaded from the original XML file.\n#\n\n" )
            json.dump( self.__dataDicts, myFile, ensure_ascii=False, indent=2 )
            #myFile.write( f"\n\n# end of {os.path.basename(filepath)}" )
    # end of exportDataToJSON


    def exportDataToC( self, filepath=None ):
        """
        Writes the information tables to a .h file that can be included in c and c++ programs.
        """
        raise Exception( "C export not written yet" )
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


        assert len(self._XMLTree)
        self.importDataToPython()
        assert self.__dataDicts

        if not filepath: filepath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_DERIVED_DATAFILES_FOLDERPATH.joinpath( self._filenameBase + '_Tables.h' )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Exporting to {filepath}…" )

        dataDict, indexDict, combinedIndexDict = self.importDataToPython()
        ifdefName = self._filenameBase.upper() + "_Tables_h"
        with open( filepath, 'wt', encoding='utf-8' ) as myFile:
            myFile.write( f"// {filepath}\n//\n" )
            myFile.write( f"// This UTF-8 file was automatically generated by BibleOrganisationalSystemsConverter.py V{PROGRAM_VERSION} on {datetime.now()}\n//\n" )
            if self.title: myFile.write( f"// {self.title}\n" )
            if self.version: myFile.write( f"//  Version: {self.version}\n" )
            if self.date: myFile.write( f"//  Date: {self.date}\n//\n" )
            myFile.write( f"//   {len(self._XMLTree)} {self._treeTag} loaded from the original XML file.\n//\n\n" )
            myFile.write( f"#ifndef {ifdefName}\n#define {ifdefName}\n\n" )
            exportPythonDict( myFile, IDDict, "IDDict", "{int id; char* refAbbrev; char* SBLAbbrev; char* OSISAbbrev; char* PTAbbrev; char* PTNum; char* EngName;}", "id (sorted), referenceAbbreviation, SBLAbbreviation, OSISAbbreviation, ParatextAbbreviation, ParatextNumberString, nameEnglish (comment only)" )
            exportPythonDict( myFile, RADict, "RADict", "{char* refAbbrev; int id; char* SBLAbbrev; char* OSISAbbrev; char* PTAbbrev; char* PTNum; char* EngName;}", "referenceAbbreviation (sorted), SBLAbbreviation, OSISAbbreviation, ParatextAbbreviation, ParatextNumberString, id, nameEnglish (comment only)" )
            exportPythonDict( myFile, SBLDict, "SBLDict", "{char* SBLAbbrev; int id; char* refAbbrev; char* OSISAbbrev; char* PTAbbrev; char* PTNum; char* EngName;}", "SBLAbbreviation (sorted), ReferenceAbbreviation, OSISAbbreviation, ParatextAbbreviation, ParatextNumberString, id, nameEnglish (comment only)" )
            exportPythonDict( myFile, OADict, "OADict", "{char* OSISAbbrev; int id; char* refAbbrev; char* SBLAbbrev; char* PTAbbrev; char* PTNum; char* EngName;}", "OSISAbbreviation (sorted), ReferenceAbbreviation, SBLAbbreviation, ParatextAbbreviation, ParatextNumberString, id, nameEnglish (comment only)" )
            exportPythonDict( myFile, PADict, "PADict", "{char* PTAbbrev; int id; char* refAbbrev; char* SBLAbbrev; char* OSISAbbrev; char* PTNum; char* EngName;}", "ParatextAbbreviation (sorted), referenceAbbreviation, SBLAbbreviation, OSISAbbreviation, ParatextNumberString, id, nameEnglish (comment only)" )
            exportPythonDict( myFile, PNDict, "PNDict", "{char* PTNum; int id; char* PTAbbrev; char* refAbbrev; char* SBLAbbrev; char* OSISAbbrev; char* EngName;}", "ParatextNumberString (sorted), ParatextAbbreviation, referenceAbbreviation, SBLAbbreviation, OSISAbbreviation, id, nameEnglish (comment only)" )
            myFile.write( f"#endif // {ifdefName}\n" )
    # end of exportDataToC
# end of BibleOrganisationalSystemsConverter class



def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    if BibleOrgSysGlobals.commandLineArguments.export:
        bosc = BibleOrganisationalSystemsConverter().loadAndValidate()
        bosc.pickle() # Produce a pickle output file
        bosc.exportDataToJSON() # Produce a json output file
        bosc.exportDataToPython() # Produce the .py tables
        # bosc.exportDataToC() # Produce the .h and .c tables

    else: # Must be demo mode
        # Demo the converter object
        bosc = BibleOrganisationalSystemsConverter().loadAndValidate()
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, bosc ) # Just print a summary
# end of fullDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    briefDemo()
# end of fullDemo

if __name__ == '__main__':
    from multiprocessing import set_start_method, freeze_support
    set_start_method('fork') # The default was changed on POSIX systems from 'fork' to 'forkserver' in Python3.14
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of BibleOrganisationalSystemsConverter.py
