#!/usr/bin/env -S uv run
# -\*- coding: utf-8 -\*-
# SPDX-License-Identifier: GPL-3.0-or-later
#
# BibleBookOrdersConverter.py
#
# Module handling BibleBookOrderSystem_*.xml to produce C and Python data tables
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
Module handling BibleBookOrder_*.xml files and to export to pickle, JSON, C, and Python data tables.
"""

import os
import logging
from datetime import datetime
from xml.etree.ElementTree import ElementTree

from BibleOrgSys.Misc.singleton import singleton
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint


LAST_MODIFIED_DATE = '2021-01-19' # by RJH
SHORT_PROGRAM_NAME = "BibleBookOrderSystemsConverter"
PROGRAM_NAME = "Bible Book Order Systems converter"
PROGRAM_VERSION = '0.85'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False



@singleton # Can only ever have one instance
class BibleBookOrdersConverter:
    """
    A class to handle data for Bible book order systems.
    """

    def __init__( self ) -> None:
        """
        Constructor.
        """
        self.__filenameBase = "BibleBookOrders"

        # These fields are used for parsing the XML
        self.XMLTreeTag = "BibleBookOrderSystem"
        self.headerTag = 'header'
        self.mainElementTag = "book"

        # These fields are used for automatically checking/validating the XML
        self.compulsoryAttributes = ( "id", )
        self.optionalAttributes = ()
        self.uniqueAttributes = self.compulsoryAttributes + self.optionalAttributes
        self.compulsoryElements = ()
        self.optionalElements = ()
        self.uniqueElements = self.compulsoryElements + self.optionalElements


        # These are fields that we will fill later
        self._XMLSystems = {}
        self.__DataDicts, self.__DataLists = {}, {} # Used for import
    # end of __init__

    def loadSystems( self, XMLFolder=None ):
        """
        Load and pre-process the specified book order systems.
        """
        if not self._XMLSystems: # Only ever do this once
            if XMLFolder is None: XMLFolder = BibleOrgSysGlobals.BOS_DATAFILES_FOLDERPATH.joinpath( 'BookOrders/' ) # Relative to module, not cwd
            self.__XMLFolder = XMLFolder
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"Loading book order systems from {self.__XMLFolder}…" )
            filenamePrefix = "BIBLEBOOKORDER_"
            for filename in os.listdir( self.__XMLFolder ):
                filepart, extension = os.path.splitext( filename )
                if extension.upper() == '.XML' and filepart.upper().startswith(filenamePrefix):
                    bookOrderSystemCode = filepart[len(filenamePrefix):]
                    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  Loading{bookOrderSystemCode} book order system from {filename}…" )
                    self._XMLSystems[bookOrderSystemCode] = {}
                    self._XMLSystems[bookOrderSystemCode]['tree'] = ElementTree().parse( os.path.join( self.__XMLFolder, filename ) )
                    assert self._XMLSystems[bookOrderSystemCode]['tree'] # Fail here if we didn't load anything at all

                    # Check and remove the header element
                    if self._XMLSystems[bookOrderSystemCode]['tree'].tag  == self.XMLTreeTag:
                        header = self._XMLSystems[bookOrderSystemCode]['tree'][0]
                        if header.tag == self.headerTag:
                            self._XMLSystems[bookOrderSystemCode]['header'] = header
                            self._XMLSystems[bookOrderSystemCode]['tree'].remove( header )
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
                                    self._XMLSystems[bookOrderSystemCode]['version'] = work.find('version').text
                                    self._XMLSystems[bookOrderSystemCode]['date'] = work.find('date').text
                                    self._XMLSystems[bookOrderSystemCode]['title'] = work.find('title').text
                                else:
                                    logging.warning( "Missing work element in header" )
                        else:
                            logging.warning( f"Missing header element (looking for {self.headerTag!r} tag)" )
                    else:
                        logging.error( f"Expected to load {self.XMLTreeTag!r} but got {self._XMLSystems[bookOrderSystemCode]['tree'].tag!r}" )
                    bookCount = 0 # There must be an easier way to do this
                    for subelement in self._XMLSystems[bookOrderSystemCode]['tree']:
                        bookCount += 1
                    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    Loaded {bookCount} books for {bookOrderSystemCode}" )
                    logging.info( f"    Loaded {bookCount} books for {bookOrderSystemCode}" )

                if BibleOrgSysGlobals.strictCheckingFlag:
                    self.__validateSystem( self._XMLSystems[bookOrderSystemCode]['tree'], bookOrderSystemCode )
        else: # The data must have been already loaded
            if XMLFolder is not None and XMLFolder!=self.__XMLFolder: logging.error( f"Bible book order systems are already loaded -- your different folder of {self.__XMLFolder!r} was ignored" )
        return self
    # end of loadSystems

    def __validateSystem( self, bookOrderTree, systemName ):
        """ Do a semi-automatic check of the XML file validity. """
        assert bookOrderTree

        uniqueDict = {}
        for elementName in self.uniqueElements: uniqueDict["Element_"+elementName] = []
        for attributeName in self.uniqueAttributes: uniqueDict["Attribute_"+attributeName] = []

        expectedID = 1
        for k,element in enumerate(bookOrderTree):
            if element.tag == self.mainElementTag:
                BibleOrgSysGlobals.checkXMLNoTail( element, element.tag )
                if not self.compulsoryAttributes and not self.optionalAttributes: BibleOrgSysGlobals.checkXMLNoAttributes( element, element.tag )
                if not self.compulsoryElements and not self.optionalElements: BibleOrgSysGlobals.checkXMLNoSubelements( element, element.tag )

                # Check ascending ID field
                ID = element.get("id")
                intID = int( ID )
                if intID != expectedID:
                    logging.error( f"ID numbers out of sequence in record {k} (got {intID} when expecting {expectedID}) for {systemName}" )
                expectedID += 1

                # Check that this is unique
                if element.text:
                    if element.text in uniqueDict:
                        logging.error( f"Found {ID!r} data repeated in {k!r} element in record with ID {systemName!r} (record {element.text}) for {element.tag}" )
                    uniqueDict[element.text] = None

                # Check compulsory attributes on this main element
                for attributeName in self.compulsoryAttributes:
                    attributeValue = element.get( attributeName )
                    if attributeValue is None:
                        logging.error( f"Compulsory {k!r} attribute is missing from {attributeName} element in record {element.tag}" )
                    if not attributeValue:
                        logging.warning( f"Compulsory {k!r} attribute is blank on {attributeName} element in record {element.tag}" )

                # Check optional attributes on this main element
                for attributeName in self.optionalAttributes:
                    attributeValue = element.get( attributeName )
                    if attributeValue is not None:
                        if not attributeValue:
                            logging.warning( f"Optional {k!r} attribute is blank on {attributeName} element in record {element.tag}" )

                # Check for unexpected additional attributes on this main element
                for attributeName in element.keys():
                    attributeValue = element.get( attributeName )
                    if attributeName not in self.compulsoryAttributes and attributeName not in self.optionalAttributes:
                        logging.warning( f"Additional {element.tag!r} attribute ({k!r}) found on {attributeName} element in record {attributeValue}" )

                # Check the attributes that must contain unique information (in that particular field -- doesn't check across different attributes)
                for attributeName in self.uniqueAttributes:
                    attributeValue = element.get( attributeName )
                    if attributeValue is not None:
                        if attributeValue in uniqueDict["Attribute_"+attributeName]:
                            logging.error( f"Found {element.tag!r} data repeated in {k!r} field on {attributeValue} element in record {attributeName}" )
                        uniqueDict["Attribute_"+attributeName].append( attributeValue )

                # Check compulsory elements
                for elementName in self.compulsoryElements:
                    if element.find( elementName ) is None:
                        logging.error( f"Compulsory {ID!r} element is missing in record with ID {k!r} (record {elementName})" )
                    if not element.find( elementName ).text:
                        logging.warning( f"Compulsory {ID!r} element is blank in record with ID {k!r} (record {elementName})" )

                # Check optional elements
                for elementName in self.optionalElements:
                    if element.find( elementName ) is not None:
                        if not element.find( elementName ).text:
                            logging.warning( f"Optional {ID!r} element is blank in record with ID {k!r} (record {elementName})" )

                # Check for unexpected additional elements
                for subelement in element:
                    if subelement.tag not in self.compulsoryElements and subelement.tag not in self.optionalElements:
                        logging.warning( f"Additional {subelement.text!r} element ({ID!r}) found in record with ID {k!r} (record {subelement.tag})" )

                # Check the elements that must contain unique information (in that particular element -- doesn't check across different elements)
                for elementName in self.uniqueElements:
                    if element.find( elementName ) is not None:
                        text = element.find( elementName ).text
                        if text in uniqueDict["Element_"+elementName]:
                            logging.error( f"Found {elementName!r} data repeated in {ID!r} element in record with ID {k!r} (record {text})" )
                        uniqueDict["Element_"+elementName].append( text )
            else:
                logging.warning( f"Unexpected element: {element.tag} in record {k}" )
    # end of __validateSystem

    def __str__( self ) -> str:
        """
        This method returns the string representation of a Bible book order system.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = "BibleBookOrdersConverter object"
        result += ('\n' if result else '') + f"  Number of book order systems loaded = {len(self._XMLSystems)}"
        if BibleOrgSysGlobals.verbosityLevel > 2: # Make it verbose
            for x in self._XMLSystems:
                result += ('\n' if result else '') + f" {x}"
                title = self._XMLSystems[x]['title']
                if title: result += ('\n' if result else '') + f"   {title}"
                version = self._XMLSystems[x]['version']
                if version: result += ('\n' if result else '') + f"    Version:{version}"
                date = self._XMLSystems[x]['date']
                if date: result += ('\n' if result else '') + f"    Last updated:{date}"
                result += ('\n' if result else '') + f"    Number of books = {len(self._XMLSystems[x]['tree'])}"
        return result
    # end of __str__

    def __len__( self ):
        """ Returns the number of systems loaded. """
        return len( self._XMLSystems )
    # end of __len__

    def importDataToPython( self ):
        """
        Loads (and pivots) the data (not including the header) into suitable Python containers to use in a Python program.
        """
        assert self._XMLSystems
        if self.__DataDicts and len(self.__DataLists): # We've already done an import/restructuring -- no need to repeat it
            return self.__DataDicts, self.__DataLists

        # We'll create a number of dictionaries
        for bookOrderSystemCode in self._XMLSystems.keys():
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, bookOrderSystemCode )
            # Make the data dictionary for this book order system
            bookDataDict, idDataDict, BBBList = {}, {}, []
            for bookElement in self._XMLSystems[bookOrderSystemCode]['tree']:
                bookRA = bookElement.text
                ID = bookElement.get( "id" )
                intID = int( ID )
                if not bos_books_codes_py.is_valid_reference_abbreviation( bookRA ):
                    logging.error( f"Unrecognized {bookRA!r} book abbreviation in {bookOrderSystemCode!r} book order system" )
                # Save it by book reference abbreviation
                if bookRA in bookDataDict:
                    logging.error( f"Duplicate {bookRA} book reference abbreviations in {bookOrderSystemCode!r} book order system" )
                bookDataDict[bookRA] = intID
                if intID in idDataDict:
                    logging.error( f"Duplicate {intID} ID (book index) numbers in {bookOrderSystemCode!r} book order system" )
                idDataDict[intID] = bookRA
                BBBList.append( bookRA )
            assert len(bookDataDict) == len(idDataDict)
            assert len(bookDataDict) == len(BBBList)

            if BibleOrgSysGlobals.strictCheckingFlag: # check for duplicates
                for checkSystemCode in self.__DataLists:
                    if self.__DataLists[checkSystemCode] == BBBList:
                        logging.error( f"{bookOrderSystemCode} and {checkSystemCode} book order systems are identical ({len(BBBList)} books)" )

            # Now put it into my dictionaries for easy access
            self.__DataDicts[bookOrderSystemCode] = bookDataDict, idDataDict
            self.__DataLists[bookOrderSystemCode] = BBBList # Don't explicitly include the book index numbers, but otherwise the same information in a different form

        if BibleOrgSysGlobals.strictCheckingFlag: # check for subsets
            for checkSystemCode in self.__DataLists:
                for otherSystemCode in self.__DataLists:
                    if checkSystemCode != otherSystemCode:
                        lastIndex, isSubset = -1, True
                        for BBB in self.__DataLists[checkSystemCode]:
                            if not BBB in self.__DataLists[otherSystemCode]: isSubset=False; break # This book isn't even in the other system
                            index = self.__DataLists[otherSystemCode].index( BBB )
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, BBB, index, lastIndex )
                            if index < lastIndex: isSubset=False; break # they must be in a different order
                            lastIndex = index
                        if isSubset: logging.error( f"{checkSystemCode} ({len(self.__DataLists[checkSystemCode])} books) is a subset of {otherSystemCode} book order system ({len(self.__DataLists[otherSystemCode])} books)" )

        return self.__DataDicts, self.__DataLists
    # end of importDataToPython

    def pickle( self, filepath=None ):
        """
        Writes the information tables to a .pickle file that can be easily loaded into a Python3 program.
        """
        import pickle

        assert self._XMLSystems
        self.importDataToPython()
        assert len(self.__DataDicts) and len(self.__DataLists)

        if not filepath:
            folder = BibleOrgSysGlobals.DEFAULT_WRITEABLE_DERIVED_DATAFILES_FOLDERPATH
            if not os.path.exists( folder ): os.mkdir( folder )
            filepath = os.path.join( folder, self.__filenameBase + '_Tables.pickle' )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Exporting to {filepath}…" )
        with open( filepath, 'wb' ) as pickleFile:
            pickle.dump( self.__DataDicts, pickleFile )
            pickle.dump( self.__DataLists, pickleFile )
    # end of pickle

    def exportDataToPython( self, filepath=None ):
        """
        Writes the information tables to a .py file that can be cut and pasted into a Python program.
        """
        def exportPythonDict( theFile, theDict, dictName, keyComment, fieldsComment ):
            """Exports theDict to theFile."""
            theFile.write( f'  "{dictName}": {{\n    # Key is{keyComment}\n    # Fields are:{fieldsComment}\n' )
            for dictKey in theDict.keys():
                theFile.write( f'   {repr(dictKey)}:{repr(theDict[dictKey])},\n' )
            theFile.write( f"  }}, # end of {dictName} ({len(theDict)} entries)\n\n" )
        # end of exportPythonDict


        assert self._XMLSystems
        self.importDataToPython()
        assert len(self.__DataDicts) and len(self.__DataLists)

        if not filepath: filepath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_DERIVED_DATAFILES_FOLDERPATH.joinpath( self.__filenameBase + '_Tables.py' )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Exporting to {filepath}…" )

        # Split into two dictionaries
        with open( filepath, 'wt', encoding='utf-8' ) as myFile:
            myFile.write( f"#{filepath}\n#\n" )
            myFile.write( f"# This UTF-8 file was automatically generated by BibleBookOrders.py V{PROGRAM_VERSION} on {datetime.now()}\n#\n" )
            #if self.title: myFile.write( f"#{self.title}\n" )
            #if self.version: myFile.write( f"#  Version:{self.version}\n" )
            #if self.date: myFile.write( f"#  Date:{self.date}\n#\n" )
            #myFile.write( f"#  {len(self.namesTree)}{self.XMLTreeTag} entries loaded from the original XML file.\n" )
            myFile.write( f"#  {len(self._XMLSystems)}{self.XMLTreeTag} loaded from the original XML files.\n#\n\n" )
            #myFile.write( "from collections import OrderedDict\n\n\n" )
            myFile.write( "bookDataDict = {\n  # Key is versificationSystemName\n  # Fields are omittedVersesSystem\n\n" )
            for systemName in self.__DataDicts:
                bookDataDict, idDataDict = self.__DataDicts[systemName]
                exportPythonDict( myFile, bookDataDict, systemName, "referenceAbbreviation", "id" )
            myFile.write( f"}} # end of bookDataDict ({len(self.__DataDicts)} systems)\n\n\n\n" )
            myFile.write( "idDataDict = {\n  # Key is versificationSystemName\n  # Fields are omittedVersesSystem\n\n" )
            for systemName in self.__DataDicts:
                bookDataDict, idDataDict = self.__DataDicts[systemName]
                exportPythonDict( myFile, idDataDict, systemName, "id", "referenceAbbreviation" )
            myFile.write( f"}} # end of idDataDict ({len(self.__DataDicts)} systems)\n" )
            myFile.write( f"# end of {os.path.basename(filepath)}" )
    # end of exportDataToPython

    def exportDataToJSON( self, filepath=None ):
        """
        Writes the information tables to a .json file that can be easily loaded into a Java program.

        See http://en.wikipedia.org/wiki/JSON.
        """
        import json

        assert self._XMLSystems
        self.importDataToPython()
        assert len(self.__DataDicts) and len(self.__DataLists)

        if not filepath: filepath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_DERIVED_DATAFILES_FOLDERPATH.joinpath( self.__filenameBase + '_Tables.json' )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Exporting to {filepath}…" )
        with open( filepath, 'wt', encoding='utf-8' ) as myFile:
            json.dump( self.__DataDicts, myFile, ensure_ascii=False, indent=2 )
    # end of exportDataToJSON

    def exportDataToC( self, filepath=None ):
        """
        Writes the information tables to a .h file that can be included in c and c++ programs.
        """
        def writeStructure( hFile, structName, structure ):
            """ Writes a typedef to the .h file. """
            hFile.write( f"typedef struct{structName}EntryStruct {{\n" )
            for declaration in structure.split(';'):
                adjDeclaration = declaration.strip()
                if adjDeclaration: hFile.write( f"   {adjDeclaration};\n" )
            hFile.write( f"}}{structName}Entry;\n\n" )
        # end of writeStructure

        def exportPythonDict( cFile, theDict, dictName, structName, sortedBy, structure ):
            """ Exports theDict to the .h and .c files. """
            def convertEntry( entry ):
                """ Convert special characters in an entry… """
                result = ""
                if isinstance( entry, int ): result += str(entry)
                elif isinstance( entry, str): result += '"' + str(entry).replace('"','\\"') + '"'
                else:
                    for field in entry:
                        if result: result += ", " # Separate the fields
                        if field is None: result += '""'
                        elif isinstance( field, str): result += '"' + str(field).replace('"','\\"') + '"'
                        elif isinstance( field, int): result += str(field)
                        else: logging.error( f"Cannot convert unknown field type {field!r} in entry {entry!r}" )
                return result
            # end of convertEntry

            #for dictKey in theDict.keys(): # Have to iterate this :(
            #    fieldsCount = len( theDict[dictKey] ) + 1 # Add one since we include the key in the count
            #    break # We only check the first (random) entry we get
            fieldsCount = 2

            cFile.write( f"const static{structName}\n{dictName}[{len(theDict)}] = {{\n  // Fields ({fieldsCount}) are{structure}\n  // Sorted by{sortedBy}\n" )
            for dictKey in sorted(theDict.keys()):
                if isinstance( dictKey, str ):
                    cFile.write( f"  {{\"{dictKey}\",{convertEntry(theDict[dictKey])}}},\n" )
                elif isinstance( dictKey, int ):
                    cFile.write( f"  {{{dictKey},{convertEntry(theDict[dictKey])}}},\n" )
                else:
                    logging.error( f"Can't handle this type of data yet: {dictKey}" )
            cFile.write( f"}}; //{dictName} ({len(theDict)} entries)\n\n" )
        # end of exportPythonDict


        assert self._XMLSystems
        self.importDataToPython()
        assert len(self.__DataDicts) and len(self.__DataLists)

        if not filepath: filepath = str( BibleOrgSysGlobals.DEFAULT_WRITEABLE_DERIVED_DATAFILES_FOLDERPATH.joinpath( self.__filenameBase + '_Tables' ) )
        hFilepath = filepath + '.h'
        cFilepath = filepath + '.c'
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Exporting to {cFilepath}…" ) # Don't bother telling them about the .h file
        ifdefName = self.__filenameBase.upper() + "_Tables_h"

        with open( hFilepath, 'wt', encoding='utf-8' ) as myHFile, \
             open( cFilepath, 'wt', encoding='utf-8' ) as myCFile:
            myHFile.write( f"//{hFilepath}\n//\n" )
            myCFile.write( f"//{cFilepath}\n//\n" )
            lines = f"// This UTF-8 file was automatically generated by BibleBookOrders.py V{PROGRAM_VERSION} on {datetime.now()}\n//\n"
            myHFile.write( lines ); myCFile.write( lines )
            myCFile.write( f"//  {len(self._XMLSystems)}{self.XMLTreeTag} loaded from the original XML file.\n//\n\n" )
            myHFile.write( f"\n#ifndef{ifdefName}\n#define{ifdefName}\n\n" )
            myCFile.write( f'#include "{os.path.basename(hFilepath)}"\n\n' )

            CHAR = "const unsigned char"
            BYTE = "const int"
            N1 = "bookOrderByRef"
            N2 = "bookOrderByIndex"
            S1 = f"{CHAR} referenceAbbreviation[3+1];{BYTE} indexNumber;"
            S2 = f"{BYTE} indexNumber;{CHAR} referenceAbbreviation[3+1];"
            writeStructure( myHFile, N1, S1 )
            writeStructure( myHFile, N2, S2 )
            writeStructure( myHFile, "table", f"{CHAR}* systemName;{N1}Entry* byReference;{N2}Entry* byBook;" ) # I'm not sure if I need one or two asterisks on those last two
                                                                                                        # They're supposed to be pointers to an array of structures
            myHFile.write( f"#endif //{ifdefName}\n\n" )
            myHFile.write( f"// end of {os.path.basename(hFilepath)}" )

            for systemName in self.__DataDicts: # Now write out the actual data into the .c file
                bookDataDict, idDataDict = self.__DataDicts[systemName]
                myCFile.write( f"\n//{systemName}\n" )
                exportPythonDict( myCFile, bookDataDict, systemName+"BookDataDict", N1+"Entry", "referenceAbbreviation", S1 )
                exportPythonDict( myCFile, idDataDict, systemName+"IndexNumberDataDict", N2+"Entry", "indexNumber", S2 )

            # Write out the final table of pointers to the above information
            myCFile.write( f"\n// Pointers to above data\nconst static tableEntry bookOrderSystemTable[{len(self.__DataDicts)}] = {{\n" )
            for systemName in self.__DataDicts: # Now write out the actual pointer data into the .c file
                myCFile.write( f'  {{ "{systemName}",{systemName+"BookDataDict"},{systemName+"IndexNumberDataDict"} }},\n' )
            myCFile.write( f"}}; //{len(self.__DataDicts)} entries\n\n" )
            myCFile.write( f"// end of {os.path.basename(cFilepath)}" )
    # end of exportDataToC

    #def obsoleteCheckBookOrderSystem( self, systemName, bookOrderSchemeToCheck ):
        #"""
        #Check the given book order scheme against all the loaded systems.
        #Create a new book order file if it doesn't match any.
        #"""
        #assert systemName
        #assert bookOrderSchemeToCheck
        #assert self.Lists
        ##dPrint( 'Quiet', DEBUGGING_THIS_MODULE, systemName, bookOrderSchemeToCheck )

        #matchedBookOrderSystemCodes = []
        #systemMatchCount, systemMismatchCount, allErrors, errorSummary = 0, 0, '', ''
        #for bookOrderSystemCode in self.Lists: # Step through the various reference schemes
            #theseErrors = ''
            #if self.Lists[bookOrderSystemCode] == bookOrderSchemeToCheck:
                ##dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  {systemName} matches {bookOrderSystemCode!r} book order system" )
                #systemMatchCount += 1
                #matchedBookOrderSystemCodes.append( bookOrderSystemCode )
            #else:
                #if len(self.Lists[bookOrderSystemCode]) == len(bookOrderSchemeToCheck):
                    #for BBB1,BBB2 in zip(self.Lists[bookOrderSystemCode],bookOrderSchemeToCheck):
                        #if BBB1 != BBB2: break
                    #thisError = f"    Doesn't match {bookOrderSystemCode!r} system (Both have {len(bookOrderSchemeToCheck)} books, but {BBB1} instead of {BBB2})"
                #else:
                    #thisError = f"    Doesn't match {bookOrderSystemCode!r} system ({len(bookOrderSchemeToCheck)} books instead of {len(self.Lists[bookOrderSystemCode])})"
                #theseErrors += ("\n" if theseErrors else "") + thisError
                #errorSummary += ("\n" if errorSummary else "") + thisError
                #systemMismatchCount += 1

        #if systemMatchCount:
            #if systemMatchCount == 1: # What we hope for
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  {systemName} matched {matchedBookOrderSystemCodes[0]} book order (with these {len(bookOrderSchemeToCheck)} books)" )
                #if BibleOrgSysGlobals.debugFlag: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, errorSummary )
            #else:
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  {systemName} matched {systemMatchCount} book order system(s): {matchedBookOrderSystemCodes} (with these {len(bookOrderSchemeToCheck)} books)" )
                #if BibleOrgSysGlobals.debugFlag: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, errorSummary )
        #else:
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  {systemName} mismatched {systemMismatchCount} book order systems (with these {len(bookOrderSchemeToCheck)} books)" )
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, allErrors if BibleOrgSysGlobals.debugFlag else errorSummary )

        #if BibleOrgSysGlobals.commandLineArguments.export and not systemMatchCount: # Write a new file
            #outputFilepath = BibleOrgSysGlobals.BOS_DATAFILES_FOLDERPATH.joinpath( 'ScrapedFiles/', "BibleBookOrder_"+systemName + '.xml' )
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Writing {len(bookOrderSchemeToCheck)} {systemName} books to {outputFilepath}…" )
            #with open( outputFilepath, 'wt', encoding='utf-8' ) as myFile:
                #for n,BBB in enumerate(bookOrderSchemeToCheck):
                    #myFile.write( f'  <book id="{n+1}">{BBB}</book>\n' )
                #myFile.write( "</BibleBookOrderSystem>" )
    ## end of obsoleteCheckBookOrderSystem
# end of BibleBookOrdersConverter class



def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    if BibleOrgSysGlobals.commandLineArguments.export:
        bbosc = BibleBookOrdersConverter().loadSystems() # Load the XML
        bbosc.pickle() # Produce the .pickle file
        bbosc.exportDataToPython() # Produce the .py tables
        bbosc.exportDataToJSON() # Produce a json output file
        # bbosc.exportDataToC() # Produce the .h and .c tables

    else: # Must be demo mode
        # Demo the converter object
        bbosc = BibleBookOrdersConverter().loadSystems() # Load the XML
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, bbosc ) # Just print a summary
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
# end of BibleBookOrdersConverter.py
