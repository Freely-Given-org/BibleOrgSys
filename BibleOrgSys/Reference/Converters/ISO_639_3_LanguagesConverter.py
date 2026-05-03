#!/usr/bin/env -S uv run
# -\*- coding: utf-8 -\*-
# SPDX-License-Identifier: GPL-3.0-or-later
#
# ISO_639_3_LanguagesConverter.py
#
# Module handling ISO_639_3.xml to produce C and Python data tables
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
Module handling ISO_639_3_Languages.xml and to export to JSON, C, and Python data tables.
"""

import logging
import os.path
from datetime import datetime
from xml.etree.ElementTree import ElementTree

from BibleOrgSys.Misc.singleton import singleton
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint


LAST_MODIFIED_DATE = '2023-10-12' # by RJH
SHORT_PROGRAM_NAME = "ISOLanguagesConverter"
PROGRAM_NAME = "ISO 639_3_Languages handler"
PROGRAM_VERSION = '0.85'
PROGRAM_NAME_VERSION = f'{PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False



@singleton # Can only ever have one instance
class ISO_639_3_LanguagesConverter:
    """
    Class for handling and converting ISO 639-3 language codes.
    """

    def __init__( self ) -> None:
        """
        Constructor: expects the filepath of the source XML file.
        Loads (and crudely validates the XML file) into an element tree.
        """
        self._filenameBase = "iso_639_3"

        # These fields are used for parsing the XML
        self._treeTag = "iso_639_3_entries"
        self._mainElementTag = "iso_639_3_entry"

        # These fields are used for automatically checking/validating the XML
        self._compulsoryAttributes = ( "id", "status", "scope", "type", "reference_name", "name" )
        self._optionalAttributes = ( "part1_code", "part2_code", "inverted_name", "common_name" )
        self._uniqueAttributes = ( "id", "reference_name", "part1_code", "part2_code", )
        self._compulsoryElements = ()
        self._optionalElements = ()
        self._uniqueElements = self._compulsoryElements + self._optionalElements

        self.title = "ISO 639-3 language codes"

        # These are fields that we will fill later
        self._XMLTree, self.__DataDicts = None, {}
    # end of __init__

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
        else: # The data must have been already loaded
            if XMLFileOrFilepath is not None and XMLFileOrFilepath!=self.__XMLFileOrFilepath: logging.error( f"ISO 639-3 language codes are already loaded -- your different filepath of {XMLFileOrFilepath!r} was ignored" )
        return self
    # end of loadAndValidate

    def _load( self, XMLFileOrFilepath ):
        """
        Load the source XML file and remove the header from the tree.
        Also, extracts some useful Attributes from the header element.
        """
        assert XMLFileOrFilepath
        self.__XMLFileOrFilepath = XMLFileOrFilepath
        assert self._XMLTree is None or len(self._XMLTree)==0 # Make sure we're not doing this twice

        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"Loading ISO 639-3 languages XML file from {XMLFileOrFilepath!r}…" )
        self._XMLTree = ElementTree().parse( XMLFileOrFilepath )
        assert len(self._XMLTree) # Fail here if we didn't load anything at all

        if self._XMLTree.tag  != self._treeTag:
            logging.error( f"Expected to load {self._treeTag!r} but got {self._XMLTree.tag!r}" )
    # end of _load

    def _validate( self ):
        """
        Check/validate the loaded data.
        """
        assert len(self._XMLTree)

        uniqueDict = {}
        #for elementName in self._uniqueElements: uniqueDict["Element_"+elementName] = []
        for attributeName in self._uniqueAttributes: uniqueDict["Attribute_"+attributeName] = []

        for j,element in enumerate(self._XMLTree):
            if element.tag == self._mainElementTag:
                BibleOrgSysGlobals.checkXMLNoText( element, element.tag )
                BibleOrgSysGlobals.checkXMLNoTail( element, element.tag )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, element.tag )

                # Check compulsory attributes on this main element
                for attributeName in self._compulsoryAttributes:
                    attributeValue = element.get( attributeName )
                    if attributeValue is None:
                        logging.error( f"Compulsory {j!r} attribute is missing from {attributeName} element in record {element.tag}" )
                    if not attributeValue and attributeName!="type":
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
                    if attributeValue is not None and attributeName!="reference_name":
                        if attributeValue in uniqueDict["Attribute_"+attributeName]:
                            logging.error( f"Found {element.tag!r} data repeated in {j!r} field on {attributeValue} element in record {attributeName}" )
                        uniqueDict["Attribute_"+attributeName].append( attributeValue )
            else:
                logging.warning( f"Unexpected element: {element.tag} in record {j}" )
    # end of _validate

    def __str__( self ) -> str:
        """
        This method returns the string representation of a Bible book code.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = "ISO_639_3_Languages_Converter object"
        if self.title: result += ('\n' if result else '') + self.title
        result += ('\n' if result else '') + "  Number of entries = " + str(len(self._XMLTree))
        return result
    # end of __str__

    def __len__( self ):
        """ Returns the number of languages loaded. """
        return len( self._XMLTree )
    # end of __len__

    def importDataToPython( self ):
        """
        Loads (and pivots) the data into suitable Python containers to use in a Python program.
        (Of course, you can just use the elementTree in self._XMLTree if you prefer.)
        """
        assert len(self._XMLTree)
        if len(self.__DataDicts): # We've already done an import/restructuring -- no need to repeat it
            return self.__DataDicts

        # We'll create a number of dictionaries with different Attributes as the key
        myIDDict, myNameDict = {}, {}
        for element in self._XMLTree:
            # Get the required information out of the tree for this element
            # Start with the compulsory attributes
            ID = element.get("id")
            Name = element.get("name")
            Scope = element.get("scope")
            Type = element.get("type")
            # The optional attributes are set to None if they don't exist
            Part1Code = element.get("part1_code")
            Part2Code = element.get("part2_code")

            # Now put it into my dictionaries for easy access
            # This part should be customized or added to for however you need to process the data
            #   Add .upper() if you require the abbreviations to be uppercase (or .lower() for lower case)
            if "id" in self._compulsoryAttributes or ID:
                if "id" in self._uniqueElements: assert ID not in myIDDict # Shouldn't be any duplicates
                myIDDict[ID] = ( Name, Scope, Type, Part1Code, Part2Code, )
            if "name" in self._compulsoryAttributes or Name:
                if "name" in self._uniqueElements: assert Name not in myNameDict # Shouldn't be any duplicates
                myNameDict[Name.upper()] = ID # Save it as UPPERCASE
            self.__DataDicts = myIDDict, myNameDict
        return self.__DataDicts
    # end of importDataToPython

    def pickle( self, filepath=None ):
        """
        Writes the information tables to a .pickle file that can be easily loaded into a Python3 program.
        """
        import pickle

        assert len(self._XMLTree)
        self.importDataToPython()
        assert len(self.__DataDicts)

        if not filepath:
            folder = BibleOrgSysGlobals.DEFAULT_WRITEABLE_DERIVED_DATAFILES_FOLDERPATH
            if not os.path.exists( folder ): os.mkdir( folder )
            filepath = os.path.join( folder, self._filenameBase + "_Languages_Tables.pickle" )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Exporting to {filepath}…" )
        with open( filepath, 'wb' ) as myFile:
            pickle.dump( self.__DataDicts, myFile )
    # end of pickle

    def exportDataToPython( self, filepath=None ):
        """
        Writes the information tables to a .py file that can be cut and pasted into a Python program.
        """
        def exportPythonDict( theFile, theDict, dictName, keyComment, fieldsComment ):
            """Exports theDict to theFile."""
            theFile.write( f"{dictName} = {{\n  # Key is {keyComment}\n  # Fields are: {fieldsComment}\n" )
            for dictKey in sorted(theDict.keys()):
                theFile.write( f"  {repr(dictKey)}: {repr(theDict[dictKey])},\n" )
            theFile.write( f"}}\n# end of {dictName}\n\n" )
        # end of exportPythonDict


        assert len(self._XMLTree)
        self.importDataToPython()
        assert len(self.__DataDicts)

        if not filepath:
            folder = BibleOrgSysGlobals.DEFAULT_WRITEABLE_DERIVED_DATAFILES_FOLDERPATH
            if not os.path.exists( folder ): os.mkdir( folder )
            filepath = os.path.join( folder, self._filenameBase + "_Languages_Tables.py" )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Exporting to {filepath}…" )

        IDDict, NameDict = self.__DataDicts
        with open( filepath, 'wt', encoding='utf-8' ) as myFile:
            myFile.write( f"# {filepath}\n#\n" )
            myFile.write( f"# This UTF-8 file was automatically generated by ISO_639_3_Languages_Converter.py V{PROGRAM_VERSION} on {datetime.now()}\n#\n" )
            if self.title: myFile.write( f"# {self.title}\n" )
            myFile.write( f"#   {len(self._XMLTree)} {self._treeTag} loaded from the original XML file.\n#\n\n" )
            exportPythonDict( myFile, IDDict, "ISO639_3_Languages_IDDict", "id", "Name, Type, Scope, Part1Code, Part2Code" )
            exportPythonDict( myFile, NameDict, "ISO639_3_Languages_NameDict", "name", "ID" )
            myFile.write( f"# end of {os.path.basename(filepath)}" )
    # end of exportDataToPython

    def exportDataToJSON( self, filepath=None ):
        """
        Writes the information tables to a .json file that can be easily loaded into a Java program.

        See http://en.wikipedia.org/wiki/JSON.
        """
        import json

        assert len(self._XMLTree)
        self.importDataToPython()
        assert len(self.__DataDicts)

        if not filepath:
            folder = BibleOrgSysGlobals.DEFAULT_WRITEABLE_DERIVED_DATAFILES_FOLDERPATH
            if not os.path.exists( folder ): os.mkdir( folder )
            filepath = os.path.join( folder, self._filenameBase + "_Languages_Tables.json" )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Exporting to {filepath}…" )
        with open( filepath, 'wt', encoding='utf-8' ) as myFile:
            json.dump( self.__DataDicts, myFile, ensure_ascii=False, indent=2 )
    # end of exportDataToJSON

    def exportDataToC( self, filepath=None ):
        """
        Writes the information tables to a .h and .c files that can be included in c and c++ programs.

        NOTE: The (optional) filepath should not have the file extension specified -- this is added automatically.
        """
        def exportPythonDict( hFile, cFile, theDict, dictName, sortedBy, structure ):
            """ Exports theDict to the .h and .c files. """
            def convertEntry( entry ):
                """ Convert special characters in an entry… """
                result = ""
                if isinstance( entry, tuple ):
                    for j, field in enumerate(entry):
                        if result: result += ", " # Separate the fields
                        if field is None: result += '""'
                        elif isinstance( field, str):
                            if j>0 and len(field)==1: result += "'" + field + "'" # Catch the character fields
                            else: result += '"' + str(field).replace('"','\\"') + '"' # String fields
                        else: logging.error( f"Cannot convert unknown field type {field!r} in entry {entry!r}" )
                elif isinstance( entry, str):
                    result += '"' + str(entry).replace('"','\\"') + '"' # String fields
                else:
                    logging.error( f"Can't handle this type of entry yet: {repr(entry)}" )
                return result
            # end of convertEntry

            for dictKey in theDict.keys(): # Have to iterate this :(
                fieldsCount = len( theDict[dictKey] ) + 1 # Add one since we include the key in the count
                break # We only check the first (random) entry we get

            #hFile.write( f"typedef struct {dictName}EntryStruct { {structure} } {dictName}Entry;\n\n" )
            hFile.write( f"typedef struct {dictName}EntryStruct {{\n" )
            for declaration in structure.split(';'):
                adjDeclaration = declaration.strip()
                if adjDeclaration: hFile.write( f"    {adjDeclaration};\n" )
            hFile.write( f"}} {dictName}Entry;\n\n" )

            cFile.write( f"const static {dictName}Entry\n {dictName}[{len(theDict)}] = {{\n  // Fields ({fieldsCount}) are {structure}\n  // Sorted by {sortedBy}\n" )
            for dictKey in sorted(theDict.keys()):
                if isinstance( dictKey, str ):
                    cFile.write( f"  {{\"{dictKey}\", {convertEntry(theDict[dictKey])}}},\n" )
                elif isinstance( dictKey, int ):
                    cFile.write( f"  {{{dictKey}, {convertEntry(theDict[dictKey])}}},\n" )
                else:
                    logging.error( f"Can't handle this type of key data yet: {dictKey}" )
            cFile.write( f"}}; // {dictName} ({len(theDict)} entries)\n\n" )
        # end of exportPythonDict


        assert len(self._XMLTree)
        self.importDataToPython()
        assert len(self.__DataDicts)

        if not filepath:
            folder = BibleOrgSysGlobals.DEFAULT_WRITEABLE_DERIVED_DATAFILES_FOLDERPATH
            if not os.path.exists( folder ): os.mkdir( folder )
            filepath = os.path.join( folder, self._filenameBase + "_Languages_Tables" )
        hFilepath = filepath + '.h'
        cFilepath = filepath + '.c'
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Exporting to {cFilepath}…" ) # Don't bother telling them about the .h file
        ifdefName = self._filenameBase.upper() + "_Tables_h"

        IDDict, NameDict = self.__DataDicts
        with open( hFilepath, 'wt', encoding='utf-8' ) as myHFile, open( cFilepath, 'wt', encoding='utf-8' ) as myCFile:
            myHFile.write( f"// {hFilepath}\n//\n" )
            myCFile.write( f"// {cFilepath}\n//\n" )
            lines = f"// This UTF-8 file was automatically generated by ISO_639_3_Languages.py V{PROGRAM_VERSION} on {datetime.now()}\n//\n"
            myHFile.write( lines ); myCFile.write( lines )
            myCFile.write( f"//   {len(self._XMLTree)} {self._treeTag} loaded from the original XML file.\n//\n\n" )
            myHFile.write( f"\n#ifndef {ifdefName}\n#define {ifdefName}\n\n" )
            myCFile.write( f'#include "{os.path.basename(hFilepath)}"\n\n' )

            CHAR = "const unsigned char"
            BYTE = "const int"
            exportPythonDict( myHFile, myCFile, IDDict, "IDDict", "3-character lower-case ID field", f"{CHAR}[3+1] ID; {CHAR}* Name; {CHAR} Type; {CHAR} Scope; {CHAR}[2+1] Part1Code; {CHAR}[3+1] Part2Code;" )
            exportPythonDict( myHFile, myCFile, NameDict, "NameDict", "language name (alphabetical)", f"{CHAR}* Name; {CHAR}[3+1] ID;"  )

            myHFile.write( f"#endif // {ifdefName}\n\n" )
            myHFile.write( f"// end of {os.path.basename(hFilepath)}" )
            myCFile.write( f"// end of {os.path.basename(cFilepath)}" )
    # end of exportDataToC
# end of ISO_639_3_LanguagesConverter class



def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    if BibleOrgSysGlobals.commandLineArguments.export:
        lgC = ISO_639_3_LanguagesConverter().loadAndValidate() # Load the XML
        lgC.pickle() # Produce a pickle output file
        lgC.exportDataToPython() # Produce the .py tables
        lgC.exportDataToJSON() # Produce a json output file
        lgC.exportDataToC() # Produce the .h and .c tables

    else: # Must be demo mode
        # Demo the converter object
        lgC = ISO_639_3_LanguagesConverter().loadAndValidate() # Load the XML
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, lgC ) # Just print a summary
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
# end of ISO_639_3_LanguagesConverter.py
