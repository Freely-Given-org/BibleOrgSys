#!/usr/bin/env python3
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

from gettext import gettext as _
import logging
import os.path
from datetime import datetime
from xml.etree.ElementTree import ElementTree

if __name__ == '__main__':
    import sys
    aboveAboveAboveFolderpath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) ) )
    if aboveAboveAboveFolderpath not in sys.path:
        sys.path.insert( 0, aboveAboveAboveFolderpath )
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
            if XMLFileOrFilepath is not None and XMLFileOrFilepath!=self.__XMLFileOrFilepath: logging.error( _("ISO 639-3 language codes are already loaded -- your different filepath of {!r} was ignored").format( XMLFileOrFilepath ) )
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

        vPrint( 'Info', DEBUGGING_THIS_MODULE, _("Loading ISO 639-3 languages XML file from {!r}…").format( XMLFileOrFilepath ) )
        self._XMLTree = ElementTree().parse( XMLFileOrFilepath )
        assert len(self._XMLTree) # Fail here if we didn't load anything at all

        if self._XMLTree.tag  != self._treeTag:
            logging.error( "Expected to load {!r} but got {!r}".format( self._treeTag, self._XMLTree.tag ) )
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
                        logging.error( "Compulsory {!r} attribute is missing from {} element in record {}".format( attributeName, element.tag, j ) )
                    if not attributeValue and attributeName!="type":
                        logging.warning( "Compulsory {!r} attribute is blank on {} element in record {}".format( attributeName, element.tag, j ) )

                # Check optional attributes on this main element
                for attributeName in self._optionalAttributes:
                    attributeValue = element.get( attributeName )
                    if attributeValue is not None:
                        if not attributeValue:
                            logging.warning( "Optional {!r} attribute is blank on {} element in record {}".format( attributeName, element.tag, j ) )

                # Check for unexpected additional attributes on this main element
                for attributeName in element.keys():
                    attributeValue = element.get( attributeName )
                    if attributeName not in self._compulsoryAttributes and attributeName not in self._optionalAttributes:
                        logging.warning( "Additional {!r} attribute ({!r}) found on {} element in record {}".format( attributeName, attributeValue, element.tag, j ) )

                # Check the attributes that must contain unique information (in that particular field -- doesn't check across different attributes)
                for attributeName in self._uniqueAttributes:
                    attributeValue = element.get( attributeName )
                    if attributeValue is not None and attributeName!="reference_name":
                        if attributeValue in uniqueDict["Attribute_"+attributeName]:
                            logging.error( "Found {!r} data repeated in {!r} field on {} element in record {}".format( attributeValue, attributeName, element.tag, j ) )
                        uniqueDict["Attribute_"+attributeName].append( attributeValue )
            else:
                logging.warning( "Unexpected element: {} in record {}".format( element.tag, j ) )
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
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, _("Exporting to {}…").format( filepath ) )
        with open( filepath, 'wb' ) as myFile:
            pickle.dump( self.__DataDicts, myFile )
    # end of pickle

    def exportDataToPython( self, filepath=None ):
        """
        Writes the information tables to a .py file that can be cut and pasted into a Python program.
        """
        def exportPythonDict( theFile, theDict, dictName, keyComment, fieldsComment ):
            """Exports theDict to theFile."""
            theFile.write( "{} = {{\n  # Key is {}\n  # Fields are: {}\n".format( dictName, keyComment, fieldsComment ) )
            for dictKey in sorted(theDict.keys()):
                theFile.write( "  {}: {},\n".format( repr(dictKey), repr(theDict[dictKey]) ) )
            theFile.write( "}}\n# end of {}\n\n".format( dictName ) )
        # end of exportPythonDict


        assert len(self._XMLTree)
        self.importDataToPython()
        assert len(self.__DataDicts)

        if not filepath:
            folder = BibleOrgSysGlobals.DEFAULT_WRITEABLE_DERIVED_DATAFILES_FOLDERPATH
            if not os.path.exists( folder ): os.mkdir( folder )
            filepath = os.path.join( folder, self._filenameBase + "_Languages_Tables.py" )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, _("Exporting to {}…").format( filepath ) )

        IDDict, NameDict = self.__DataDicts
        with open( filepath, 'wt', encoding='utf-8' ) as myFile:
            myFile.write( "# {}\n#\n".format( filepath ) )
            myFile.write( "# This UTF-8 file was automatically generated by ISO_639_3_Languages_Converter.py V{} on {}\n#\n".format( PROGRAM_VERSION, datetime.now() ) )
            if self.title: myFile.write( "# {}\n".format( self.title ) )
            myFile.write( "#   {} {} loaded from the original XML file.\n#\n\n".format( len(self._XMLTree), self._treeTag ) )
            exportPythonDict( myFile, IDDict, "ISO639_3_Languages_IDDict", "id", "Name, Type, Scope, Part1Code, Part2Code" )
            exportPythonDict( myFile, NameDict, "ISO639_3_Languages_NameDict", "name", "ID" )
            myFile.write( "# end of {}".format( os.path.basename(filepath) ) )
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
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, _("Exporting to {}…").format( filepath ) )
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
                        else: logging.error( "Cannot convert unknown field type {!r} in entry {!r}".format( field, entry ) )
                elif isinstance( entry, str):
                    result += '"' + str(entry).replace('"','\\"') + '"' # String fields
                else:
                    logging.error( "Can't handle this type of entry yet: {}".format( repr(entry) ) )
                return result
            # end of convertEntry

            for dictKey in theDict.keys(): # Have to iterate this :(
                fieldsCount = len( theDict[dictKey] ) + 1 # Add one since we include the key in the count
                break # We only check the first (random) entry we get

            #hFile.write( "typedef struct {}EntryStruct { {} } {}Entry;\n\n".format( dictName, structure, dictName ) )
            hFile.write( "typedef struct {}EntryStruct {{\n".format( dictName ) )
            for declaration in structure.split(';'):
                adjDeclaration = declaration.strip()
                if adjDeclaration: hFile.write( "    {};\n".format( adjDeclaration ) )
            hFile.write( "}} {}Entry;\n\n".format( dictName ) )

            cFile.write( "const static {}Entry\n {}[{}] = {{\n  // Fields ({}) are {}\n  // Sorted by {}\n".format( dictName, dictName, len(theDict), fieldsCount, structure, sortedBy ) )
            for dictKey in sorted(theDict.keys()):
                if isinstance( dictKey, str ):
                    cFile.write( "  {{\"{}\", {}}},\n".format( dictKey, convertEntry(theDict[dictKey]) ) )
                elif isinstance( dictKey, int ):
                    cFile.write( "  {{{}, {}}},\n".format( dictKey, convertEntry(theDict[dictKey]) ) )
                else:
                    logging.error( "Can't handle this type of key data yet: {}".format( dictKey ) )
            cFile.write( "}}; // {} ({} entries)\n\n".format( dictName, len(theDict) ) )
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
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, _("Exporting to {}…").format( cFilepath ) ) # Don't bother telling them about the .h file
        ifdefName = self._filenameBase.upper() + "_Tables_h"

        IDDict, NameDict = self.__DataDicts
        with open( hFilepath, 'wt', encoding='utf-8' ) as myHFile, open( cFilepath, 'wt', encoding='utf-8' ) as myCFile:
            myHFile.write( "// {}\n//\n".format( hFilepath ) )
            myCFile.write( "// {}\n//\n".format( cFilepath ) )
            lines = "// This UTF-8 file was automatically generated by ISO_639_3_Languages.py V{} on {}\n//\n".format( PROGRAM_VERSION, datetime.now() )
            myHFile.write( lines ); myCFile.write( lines )
            myCFile.write( "//   {} {} loaded from the original XML file.\n//\n\n".format( len(self._XMLTree), self._treeTag ) )
            myHFile.write( "\n#ifndef {}\n#define {}\n\n".format( ifdefName, ifdefName ) )
            myCFile.write( '#include "{}"\n\n'.format( os.path.basename(hFilepath) ) )

            CHAR = "const unsigned char"
            BYTE = "const int"
            exportPythonDict( myHFile, myCFile, IDDict, "IDDict", "3-character lower-case ID field", "{}[3+1] ID; {}* Name; {} Type; {} Scope; {}[2+1] Part1Code; {}[3+1] Part2Code;".format(CHAR,CHAR,CHAR,CHAR,CHAR,CHAR) )
            exportPythonDict( myHFile, myCFile, NameDict, "NameDict", "language name (alphabetical)", "{}* Name; {}[3+1] ID;".format(CHAR,CHAR)  )

            myHFile.write( "#endif // {}\n\n".format( ifdefName ) )
            myHFile.write( "// end of {}".format( os.path.basename(hFilepath) ) )
            myCFile.write( "// end of {}".format( os.path.basename(cFilepath) ) )
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
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of ISO_639_3_LanguagesConverter.py
