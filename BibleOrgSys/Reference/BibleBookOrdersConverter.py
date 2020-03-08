#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# BibleBookOrdersConverter.py
#
# Module handling BibleBookOrderSystem_*.xml to produce C and Python data tables
#
# Copyright (C) 2010-2017 Robert Hunt
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
Module handling BibleBookOrder_*.xml files and to export to pickle, JSON, C, and Python data tables.
"""

from gettext import gettext as _

lastModifiedDate = '2017-12-09' # by RJH
shortProgramName = "BibleBookOrderSystemsConverter"
programName = "Bible Book Order Systems converter"
programVersion = '0.84'
programNameVersion = f'{shortProgramName} v{programVersion}'
programNameVersionDate = f'{programNameVersion} {_("last modified")} {lastModifiedDate}'

debuggingThisModule = False


import os
import logging
from datetime import datetime
from xml.etree.ElementTree import ElementTree

if __name__ == '__main__':
    import sys
    sys.path.append( os.path.join(os.path.dirname(__file__), '../') ) # So we can run it from the above folder and still do these imports
from Misc.singleton import singleton
import BibleOrgSysGlobals



@singleton # Can only ever have one instance
class BibleBookOrdersConverter:
    """
    A class to handle data for Bible book order systems.
    """

    def __init__( self ):
        """
        Constructor.
        """
        self.__filenameBase = "BibleBookOrders"

        # These fields are used for parsing the XML
        self.XMLTreeTag = "BibleBookOrderSystem"
        self.headerTag = "header"
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
            if XMLFolder==None: XMLFolder = BibleOrgSysGlobals.BOS_DATA_FILES_FOLDERPATH.joinpath( 'BookOrders/' ) # Relative to module, not cwd
            self.__XMLFolder = XMLFolder
            if BibleOrgSysGlobals.verbosityLevel > 2: print( _("Loading book order systems from {}…").format( self.__XMLFolder ) )
            filenamePrefix = "BIBLEBOOKORDER_"
            for filename in os.listdir( self.__XMLFolder ):
                filepart, extension = os.path.splitext( filename )
                if extension.upper() == '.XML' and filepart.upper().startswith(filenamePrefix):
                    bookOrderSystemCode = filepart[len(filenamePrefix):]
                    if BibleOrgSysGlobals.verbosityLevel > 3: print( _("  Loading{} book order system from {}…").format( bookOrderSystemCode, filename ) )
                    self._XMLSystems[bookOrderSystemCode] = {}
                    self._XMLSystems[bookOrderSystemCode]['tree'] = ElementTree().parse( os.path.join( self.__XMLFolder, filename ) )
                    assert self._XMLSystems[bookOrderSystemCode]['tree'] # Fail here if we didn't load anything at all

                    # Check and remove the header element
                    if self._XMLSystems[bookOrderSystemCode]['tree'].tag  == self.XMLTreeTag:
                        header = self._XMLSystems[bookOrderSystemCode]['tree'][0]
                        if header.tag == self.headerTag:
                            self._XMLSystems[bookOrderSystemCode]["header"] = header
                            self._XMLSystems[bookOrderSystemCode]['tree'].remove( header )
                            BibleOrgSysGlobals.checkXMLNoText( header, "header" )
                            BibleOrgSysGlobals.checkXMLNoTail( header, "header" )
                            BibleOrgSysGlobals.checkXMLNoAttributes( header, "header" )
                            if len(header)>1:
                                logging.info( _("Unexpected elements in header") )
                            elif len(header)==0:
                                logging.info( _("Missing work element in header") )
                            else:
                                work = header[0]
                                BibleOrgSysGlobals.checkXMLNoText( work, "work in header" )
                                BibleOrgSysGlobals.checkXMLNoTail( work, "work in header" )
                                BibleOrgSysGlobals.checkXMLNoAttributes( work, "work in header" )
                                if work.tag == "work":
                                    self._XMLSystems[bookOrderSystemCode]['version'] = work.find('version').text
                                    self._XMLSystems[bookOrderSystemCode]["date"] = work.find("date").text
                                    self._XMLSystems[bookOrderSystemCode]["title"] = work.find("title").text
                                else:
                                    logging.warning( _("Missing work element in header") )
                        else:
                            logging.warning( _("Missing header element (looking for {!r} tag)").format( self.headerTag ) )
                    else:
                        logging.error( _("Expected to load {!r} but got {!r}").format( self.XMLTreeTag, self._XMLSystems[bookOrderSystemCode]['tree'].tag ) )
                    bookCount = 0 # There must be an easier way to do this
                    for subelement in self._XMLSystems[bookOrderSystemCode]['tree']:
                        bookCount += 1
                    if BibleOrgSysGlobals.verbosityLevel > 2:
                        print( _("    Loaded {} books for {}").format( bookCount, bookOrderSystemCode ) )
                    logging.info( _("    Loaded {} books for {}").format( bookCount, bookOrderSystemCode ) )

                if BibleOrgSysGlobals.strictCheckingFlag:
                    self.__validateSystem( self._XMLSystems[bookOrderSystemCode]['tree'], bookOrderSystemCode )
        else: # The data must have been already loaded
            if XMLFolder is not None and XMLFolder!=self.__XMLFolder: logging.error( _("Bible book order systems are already loaded -- your different folder of {!r} was ignored").format( self.__XMLFolder ) )
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
                    logging.error( _("ID numbers out of sequence in record {} (got {} when expecting {}) for {}").format( k, intID, expectedID, systemName ) )
                expectedID += 1

                # Check that this is unique
                if element.text:
                    if element.text in uniqueDict:
                        logging.error( _("Found {!r} data repeated in {!r} element in record with ID {!r} (record {}) for {}").format( element.text, element.tag, ID, k, systemName ) )
                    uniqueDict[element.text] = None

                # Check compulsory attributes on this main element
                for attributeName in self.compulsoryAttributes:
                    attributeValue = element.get( attributeName )
                    if attributeValue is None:
                        logging.error( _("Compulsory {!r} attribute is missing from {} element in record {}").format( attributeName, element.tag, k ) )
                    if not attributeValue:
                        logging.warning( _("Compulsory {!r} attribute is blank on {} element in record {}").format( attributeName, element.tag, k ) )

                # Check optional attributes on this main element
                for attributeName in self.optionalAttributes:
                    attributeValue = element.get( attributeName )
                    if attributeValue is not None:
                        if not attributeValue:
                            logging.warning( _("Optional {!r} attribute is blank on {} element in record {}").format( attributeName, element.tag, k ) )

                # Check for unexpected additional attributes on this main element
                for attributeName in element.keys():
                    attributeValue = element.get( attributeName )
                    if attributeName not in self.compulsoryAttributes and attributeName not in self.optionalAttributes:
                        logging.warning( _("Additional {!r} attribute ({!r}) found on {} element in record {}").format( attributeName, attributeValue, element.tag, k ) )

                # Check the attributes that must contain unique information (in that particular field -- doesn't check across different attributes)
                for attributeName in self.uniqueAttributes:
                    attributeValue = element.get( attributeName )
                    if attributeValue is not None:
                        if attributeValue in uniqueDict["Attribute_"+attributeName]:
                            logging.error( _("Found {!r} data repeated in {!r} field on {} element in record {}").format( attributeValue, attributeName, element.tag, k ) )
                        uniqueDict["Attribute_"+attributeName].append( attributeValue )

                # Check compulsory elements
                for elementName in self.compulsoryElements:
                    if element.find( elementName ) is None:
                        logging.error( _("Compulsory {!r} element is missing in record with ID {!r} (record {})").format( elementName, ID, k ) )
                    if not element.find( elementName ).text:
                        logging.warning( _("Compulsory {!r} element is blank in record with ID {!r} (record {})").format( elementName, ID, k ) )

                # Check optional elements
                for elementName in self.optionalElements:
                    if element.find( elementName ) is not None:
                        if not element.find( elementName ).text:
                            logging.warning( _("Optional {!r} element is blank in record with ID {!r} (record {})").format( elementName, ID, k ) )

                # Check for unexpected additional elements
                for subelement in element:
                    if subelement.tag not in self.compulsoryElements and subelement.tag not in self.optionalElements:
                        logging.warning( _("Additional {!r} element ({!r}) found in record with ID {!r} (record {})").format( subelement.tag, subelement.text, ID, k ) )

                # Check the elements that must contain unique information (in that particular element -- doesn't check across different elements)
                for elementName in self.uniqueElements:
                    if element.find( elementName ) is not None:
                        text = element.find( elementName ).text
                        if text in uniqueDict["Element_"+elementName]:
                            logging.error( _("Found {!r} data repeated in {!r} element in record with ID {!r} (record {})").format( text, elementName, ID, k ) )
                        uniqueDict["Element_"+elementName].append( text )
            else:
                logging.warning( _("Unexpected element: {} in record {}").format( element.tag, k ) )
    # end of __validateSystem

    def __str__( self ):
        """
        This method returns the string representation of a Bible book order system.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = "BibleBookOrdersConverter object"
        result += ('\n' if result else '') + "  Number of book order systems loaded = {}".format( len(self._XMLSystems) )
        if BibleOrgSysGlobals.verbosityLevel > 2: # Make it verbose
            for x in self._XMLSystems:
                result += ('\n' if result else '') + " {}".format( x )
                title = self._XMLSystems[x]["title"]
                if title: result += ('\n' if result else '') + "   {}".format( title )
                version = self._XMLSystems[x]['version']
                if version: result += ('\n' if result else '') + "    Version:{}".format( version )
                date = self._XMLSystems[x]["date"]
                if date: result += ('\n' if result else '') + "    Last updated:{}".format( date )
                result += ('\n' if result else '') + "    Number of books = {}".format( len(self._XMLSystems[x]['tree']) )
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
        if self.__DataDicts and self.__DataLists: # We've already done an import/restructuring -- no need to repeat it
            return self.__DataDicts, self.__DataLists

        # We'll create a number of dictionaries
        for bookOrderSystemCode in self._XMLSystems.keys():
            #print( bookOrderSystemCode )
            # Make the data dictionary for this book order system
            bookDataDict, idDataDict, BBBList = {}, {}, []
            for bookElement in self._XMLSystems[bookOrderSystemCode]['tree']:
                bookRA = bookElement.text
                ID = bookElement.get( "id" )
                intID = int( ID )
                if not BibleOrgSysGlobals.BibleBooksCodes.isValidBBB( bookRA ):
                    logging.error( _("Unrecognized {!r} book abbreviation in {!r} book order system").format( bookRA, bookOrderSystemCode ) )
                # Save it by book reference abbreviation
                if bookRA in bookDataDict:
                    logging.error( _("Duplicate {} book reference abbreviations in {!r} book order system").format( bookRA, bookOrderSystemCode ) )
                bookDataDict[bookRA] = intID
                if intID in idDataDict:
                    logging.error( _("Duplicate {} ID (book index) numbers in {!r} book order system").format( intID, bookOrderSystemCode ) )
                idDataDict[intID] = bookRA
                BBBList.append( bookRA )
            assert len(bookDataDict) == len(idDataDict)
            assert len(bookDataDict) == len(BBBList)

            if BibleOrgSysGlobals.strictCheckingFlag: # check for duplicates
                for checkSystemCode in self.__DataLists:
                    if self.__DataLists[checkSystemCode] == BBBList:
                        logging.error( _("{} and {} book order systems are identical ({} books)").format( bookOrderSystemCode, checkSystemCode, len(BBBList) ) )

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
                            #print( BBB, index, lastIndex )
                            if index < lastIndex: isSubset=False; break # they must be in a different order
                            lastIndex = index
                        if isSubset: logging.error( _("{} ({} books) is a subset of {} book order system ({} books)").format( checkSystemCode, len(self.__DataLists[checkSystemCode]), otherSystemCode, len(self.__DataLists[otherSystemCode]) ) )

        return self.__DataDicts, self.__DataLists
    # end of importDataToPython

    def pickle( self, filepath=None ):
        """
        Writes the information tables to a .pickle file that can be easily loaded into a Python3 program.
        """
        import pickle

        assert self._XMLSystems
        self.importDataToPython()
        assert self.__DataDicts and self.__DataLists

        if not filepath:
            folder = os.path.join( self.__XMLFolder, "../", "DerivedFiles/" )
            if not os.path.exists( folder ): os.mkdir( folder )
            filepath = os.path.join( folder, self.__filenameBase + "_Tables.pickle" )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Exporting to {}…").format( filepath ) )
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
            theFile.write( '  "{}": {{\n    # Key is{}\n    # Fields are:{}\n'.format( dictName, keyComment, fieldsComment ) )
            for dictKey in theDict.keys():
                theFile.write( '   {}:{},\n'.format( repr(dictKey), repr(theDict[dictKey]) ) )
            theFile.write( "  }}, # end of {} ({} entries)\n\n".format( dictName, len(theDict) ) )
        # end of exportPythonDict


        assert self._XMLSystems
        self.importDataToPython()
        assert self.__DataDicts and self.__DataLists

        if not filepath: filepath = os.path.join( self.__XMLFolder, "../", 'DerivedFiles/', self.__filenameBase + "_Tables.py" )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Exporting to {}…").format( filepath ) )

        # Split into two dictionaries
        with open( filepath, 'wt', encoding='utf-8' ) as myFile:
            myFile.write( "#{}\n#\n".format( filepath ) )
            myFile.write( "# This UTF-8 file was automatically generated by BibleBookOrders.py V{} on {}\n#\n".format( programVersion, datetime.now() ) )
            #if self.title: myFile.write( "#{}\n".format( self.title ) )
            #if self.version: myFile.write( "#  Version:{}\n".format( self.version ) )
            #if self.date: myFile.write( "#  Date:{}\n#\n".format( self.date ) )
            #myFile.write( "#  {}{} entries loaded from the original XML file.\n".format( len(self.namesTree), self.XMLTreeTag ) )
            myFile.write( "#  {}{} loaded from the original XML files.\n#\n\n".format( len(self._XMLSystems), self.XMLTreeTag ) )
            #myFile.write( "from collections import OrderedDict\n\n\n" )
            myFile.write( "bookDataDict = {\n  # Key is versificationSystemName\n  # Fields are omittedVersesSystem\n\n" )
            for systemName in self.__DataDicts:
                bookDataDict, idDataDict = self.__DataDicts[systemName]
                exportPythonDict( myFile, bookDataDict, systemName, "referenceAbbreviation", "id" )
            myFile.write( "}} # end of bookDataDict ({} systems)\n\n\n\n".format( len(self.__DataDicts) ) )
            myFile.write( "idDataDict = {\n  # Key is versificationSystemName\n  # Fields are omittedVersesSystem\n\n" )
            for systemName in self.__DataDicts:
                bookDataDict, idDataDict = self.__DataDicts[systemName]
                exportPythonDict( myFile, idDataDict, systemName, "id", "referenceAbbreviation" )
            myFile.write( "}} # end of idDataDict ({} systems)\n".format( len(self.__DataDicts) ) )
            myFile.write( "# end of {}".format( os.path.basename(filepath) ) )
    # end of exportDataToPython

    def exportDataToJSON( self, filepath=None ):
        """
        Writes the information tables to a .json file that can be easily loaded into a Java program.

        See http://en.wikipedia.org/wiki/JSON.
        """
        import json

        assert self._XMLSystems
        self.importDataToPython()
        assert self.__DataDicts and self.__DataLists

        if not filepath: filepath = os.path.join( self.__XMLFolder, "../", 'DerivedFiles/', self.__filenameBase + "_Tables.json" )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Exporting to {}…").format( filepath ) )
        with open( filepath, 'wt', encoding='utf-8' ) as myFile:
            json.dump( self.__DataDicts, myFile, indent=2 )
    # end of exportDataToJSON

    def exportDataToC( self, filepath=None ):
        """
        Writes the information tables to a .h file that can be included in c and c++ programs.
        """
        def writeStructure( hFile, structName, structure ):
            """ Writes a typedef to the .h file. """
            hFile.write( "typedef struct{}EntryStruct {{\n".format( structName ) )
            for declaration in structure.split(';'):
                adjDeclaration = declaration.strip()
                if adjDeclaration: hFile.write( "   {};\n".format( adjDeclaration ) )
            hFile.write( "}}{}Entry;\n\n".format( structName ) )
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
                        else: logging.error( _("Cannot convert unknown field type {!r} in entry {!r}").format( field, entry ) )
                return result
            # end of convertEntry

            #for dictKey in theDict.keys(): # Have to iterate this :(
            #    fieldsCount = len( theDict[dictKey] ) + 1 # Add one since we include the key in the count
            #    break # We only check the first (random) entry we get
            fieldsCount = 2

            cFile.write( "const static{}\n{}[{}] = {{\n  // Fields ({}) are{}\n  // Sorted by{}\n".format( structName, dictName, len(theDict), fieldsCount, structure, sortedBy ) )
            for dictKey in sorted(theDict.keys()):
                if isinstance( dictKey, str ):
                    cFile.write( "  {{\"{}\",{}}},\n".format( dictKey, convertEntry(theDict[dictKey]) ) )
                elif isinstance( dictKey, int ):
                    cFile.write( "  {{{},{}}},\n".format( dictKey, convertEntry(theDict[dictKey]) ) )
                else:
                    logging.error( _("Can't handle this type of data yet: {}").format( dictKey ) )
            cFile.write( "}}; //{} ({} entries)\n\n".format( dictName, len(theDict) ) )
        # end of exportPythonDict


        assert self._XMLSystems
        self.importDataToPython()
        assert self.__DataDicts and self.__DataLists

        if not filepath: filepath = os.path.join( self.__XMLFolder, "../", 'DerivedFiles/', self.__filenameBase + "_Tables" )
        hFilepath = filepath + '.h'
        cFilepath = filepath + '.c'
        if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Exporting to {}…").format( cFilepath ) ) # Don't bother telling them about the .h file
        ifdefName = self.__filenameBase.upper() + "_Tables_h"

        with open( hFilepath, 'wt', encoding='utf-8' ) as myHFile, \
             open( cFilepath, 'wt', encoding='utf-8' ) as myCFile:
            myHFile.write( "//{}\n//\n".format( hFilepath ) )
            myCFile.write( "//{}\n//\n".format( cFilepath ) )
            lines = "// This UTF-8 file was automatically generated by BibleBookOrders.py V{} on {}\n//\n".format( programVersion, datetime.now() )
            myHFile.write( lines ); myCFile.write( lines )
            myCFile.write( "//  {}{} loaded from the original XML file.\n//\n\n".format( len(self._XMLSystems), self.XMLTreeTag ) )
            myHFile.write( "\n#ifndef{}\n#define{}\n\n".format( ifdefName, ifdefName ) )
            myCFile.write( '#include "{}"\n\n'.format( os.path.basename(hFilepath) ) )

            CHAR = "const unsigned char"
            BYTE = "const int"
            N1 = "bookOrderByRef"
            N2 = "bookOrderByIndex"
            S1 = "{} referenceAbbreviation[3+1];{} indexNumber;".format(CHAR,BYTE)
            S2 = "{} indexNumber;{} referenceAbbreviation[3+1];".format(BYTE,CHAR)
            writeStructure( myHFile, N1, S1 )
            writeStructure( myHFile, N2, S2 )
            writeStructure( myHFile, "table", "{}* systemName;{}Entry* byReference;{}Entry* byBook;".format(CHAR,N1,N2) ) # I'm not sure if I need one or two asterisks on those last two
                                                                                                        # They're supposed to be pointers to an array of structures
            myHFile.write( "#endif //{}\n\n".format( ifdefName ) )
            myHFile.write( "// end of {}".format( os.path.basename(hFilepath) ) )

            for systemName in self.__DataDicts: # Now write out the actual data into the .c file
                bookDataDict, idDataDict = self.__DataDicts[systemName]
                myCFile.write( "\n//{}\n".format( systemName ) )
                exportPythonDict( myCFile, bookDataDict, systemName+"BookDataDict", N1+"Entry", "referenceAbbreviation", S1 )
                exportPythonDict( myCFile, idDataDict, systemName+"IndexNumberDataDict", N2+"Entry", "indexNumber", S2 )

            # Write out the final table of pointers to the above information
            myCFile.write( "\n// Pointers to above data\nconst static tableEntry bookOrderSystemTable[{}] = {{\n".format( len(self.__DataDicts) ) )
            for systemName in self.__DataDicts: # Now write out the actual pointer data into the .c file
                myCFile.write( '  {{ "{}",{},{} }},\n'.format( systemName, systemName+"BookDataDict", systemName+"IndexNumberDataDict" ) )
            myCFile.write( "}}; //{} entries\n\n".format( len(self.__DataDicts) ) )
            myCFile.write( "// end of {}".format( os.path.basename(cFilepath) ) )
    # end of exportDataToC

    #def obsoleteCheckBookOrderSystem( self, systemName, bookOrderSchemeToCheck ):
        #"""
        #Check the given book order scheme against all the loaded systems.
        #Create a new book order file if it doesn't match any.
        #"""
        #assert systemName
        #assert bookOrderSchemeToCheck
        #assert self.Lists
        ##print( systemName, bookOrderSchemeToCheck )

        #matchedBookOrderSystemCodes = []
        #systemMatchCount, systemMismatchCount, allErrors, errorSummary = 0, 0, '', ''
        #for bookOrderSystemCode in self.Lists: # Step through the various reference schemes
            #theseErrors = ''
            #if self.Lists[bookOrderSystemCode] == bookOrderSchemeToCheck:
                ##print( "  {} matches {!r} book order system".format( systemName, bookOrderSystemCode ) )
                #systemMatchCount += 1
                #matchedBookOrderSystemCodes.append( bookOrderSystemCode )
            #else:
                #if len(self.Lists[bookOrderSystemCode]) == len(bookOrderSchemeToCheck):
                    #for BBB1,BBB2 in zip(self.Lists[bookOrderSystemCode],bookOrderSchemeToCheck):
                        #if BBB1 != BBB2: break
                    #thisError = "    Doesn't match {!r} system (Both have {} books, but {} instead of {})".format( bookOrderSystemCode, len(bookOrderSchemeToCheck), BBB1, BBB2 )
                #else:
                    #thisError = "    Doesn't match {!r} system ({} books instead of {})".format( bookOrderSystemCode, len(bookOrderSchemeToCheck), len(self.Lists[bookOrderSystemCode]) )
                #theseErrors += ("\n" if theseErrors else "") + thisError
                #errorSummary += ("\n" if errorSummary else "") + thisError
                #systemMismatchCount += 1

        #if systemMatchCount:
            #if systemMatchCount == 1: # What we hope for
                #print( _("  {} matched {} book order (with these {} books)").format( systemName, matchedBookOrderSystemCodes[0], len(bookOrderSchemeToCheck) ) )
                #if BibleOrgSysGlobals.commandLineArguments.debug: print( errorSummary )
            #else:
                #print( _("  {} matched {} book order system(s): {} (with these {} books)").format( systemName, systemMatchCount, matchedBookOrderSystemCodes, len(bookOrderSchemeToCheck) ) )
                #if BibleOrgSysGlobals.commandLineArguments.debug: print( errorSummary )
        #else:
            #print( _("  {} mismatched {} book order systems (with these {} books)").format( systemName, systemMismatchCount, len(bookOrderSchemeToCheck) ) )
            #print( allErrors if BibleOrgSysGlobals.commandLineArguments.debug else errorSummary )

        #if BibleOrgSysGlobals.commandLineArguments.export and not systemMatchCount: # Write a new file
            #outputFilepath = BibleOrgSysGlobals.BOS_DATA_FILES_FOLDERPATH.joinpath( 'ScrapedFiles/', "BibleBookOrder_"+systemName + '.xml' )
            #print( _("Writing {} {} books to {}…").format( len(bookOrderSchemeToCheck), systemName, outputFilepath ) )
            #with open( outputFilepath, 'wt', encoding='utf-8' ) as myFile:
                #for n,BBB in enumerate(bookOrderSchemeToCheck):
                    #myFile.write( '  <book id="{}">{}</book>\n'.format( n+1,BBB ) )
                #myFile.write( "</BibleBookOrderSystem>" )
    ## end of obsoleteCheckBookOrderSystem
# end of BibleBookOrdersConverter class



def demo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel > 1: print( programNameVersion )

    if BibleOrgSysGlobals.commandLineArguments.export:
        bbosc = BibleBookOrdersConverter().loadSystems() # Load the XML
        bbosc.pickle() # Produce the .pickle file
        bbosc.exportDataToPython() # Produce the .py tables
        bbosc.exportDataToJSON() # Produce a json output file
        bbosc.exportDataToC() # Produce the .h and .c tables

    else: # Must be demo mode
        # Demo the converter object
        bbosc = BibleBookOrdersConverter().loadSystems() # Load the XML
        print( bbosc ) # Just print a summary
# end of demo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( programName, programVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    demo()

    BibleOrgSysGlobals.closedown( programName, programVersion )
# end of BibleBookOrdersConverter.py
