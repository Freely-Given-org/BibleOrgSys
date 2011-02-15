#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# BibleBooksCodes.py
#
# Module handling BibleBooksCodes.xml to produce C and Python data tables
#   Last modified: 2011-02-15 (also update versionString below)
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
Module handling BibleBooksCodes.xml and to export to JSON, C, and Python data tables.
"""

progName = "Bible Books Codes handler"
versionString = "0.51"


import logging, os.path
from gettext import gettext as _
from collections import OrderedDict
from xml.etree.cElementTree import ElementTree

from singleton import singleton
import Globals


@singleton # Can only ever have one instance
class _BibleBooksCodesConverter:
    """
    Class for reading, validating, and converting BibleBooksCodes.
    This is only intended as a transitory class (used at start-up).
    The BibleBooksCodes class has functions more generally useful.
    """

    def __init__( self ): # We can't give this parameters because of the singleton
        """
        Constructor: expects the filepath of the source XML file.
        Loads (and crudely validates the XML file) into an element tree.
        """
        self._filenameBase = "BibleBooksCodes"

        # These fields are used for parsing the XML
        self._treeTag = "BibleBooksCodes"
        self._headerTag = "header"
        self._mainElementTag = "BibleBookCodes"

        # These fields are used for automatically checking/validating the XML
        self._compulsoryAttributes = ()
        self._optionalAttributes = ()
        self._uniqueAttributes = self._compulsoryAttributes + self._optionalAttributes
        self._compulsoryElements = ( "nameEnglish", "referenceAbbreviation", "referenceNumber" )
        self._optionalElements = ( "expectedChapters", "SBLAbbreviation", "OSISAbbreviation", "SwordAbbreviation", "CCELNumber", "ParatextAbbreviation", "ParatextNumber", "NETBibleAbbreviation", "ByzantineAbbreviation", "possibleAlternativeBooks" )
        #self._uniqueElements = self._compulsoryElements + self.optionalElements
        self._uniqueElements = self._compulsoryElements # Relax the checking

        # These are fields that we will fill later
        self._XMLheader, self._XMLtree = None, None
        self.__DataDicts = {} # Used for import
        self.titleString = self.versionString = self.dateString = ''
    # end of __init__

    def loadAndValidate( self, XMLFilepath=None ):
        """
        Loads (and crudely validates the XML file) into an element tree.
            Allows the filepath of the source XML file to be specified, otherwise uses the default.
        """
        if self._XMLtree is None: # We mustn't have already have loaded the data
            if XMLFilepath is None:
                XMLFilepath = os.path.join( "DataFiles", self._filenameBase + ".xml" )
            self.__load( XMLFilepath )
            if Globals.strictCheckingFlag:
                self.__validate()
        else: # The data must have been already loaded
            if XMLFilepath is not None and XMLFilepath!=self.__XMLFilepath: logging.error( _("Bible books codes are already loaded -- your different filepath of '{}' was ignored").format( XMLFilepath ) )
        return self
    # end of loadAndValidate

    def __load( self, XMLFilepath ):
        """
        Load the source XML file and remove the header from the tree.
        Also, extracts some useful elements from the header element.
        """
        assert( XMLFilepath )
        self.__XMLFilepath = XMLFilepath
        assert( self._XMLtree is None or len(self._XMLtree)==0 ) # Make sure we're not doing this twice

        if Globals.verbosityLevel > 2: print( _("Loading BibleBooksCodes XML file from '{}'...").format( self.__XMLFilepath ) )
        self._XMLtree = ElementTree().parse( self.__XMLFilepath )
        assert( self._XMLtree ) # Fail here if we didn't load anything at all

        if self._XMLtree.tag == self._treeTag:
            header = self._XMLtree[0]
            if header.tag == self._headerTag:
                self.XMLheader = header
                self._XMLtree.remove( header )
                if len(header)>1:
                    logging.info( _("Unexpected elements in header") )
                elif len(header)==0:
                    logging.info( _("Missing work element in header") )
                else:
                    work = header[0]
                    if work.tag == "work":
                        self.versionString = work.find("version").text
                        self.dateString = work.find("date").text
                        self.titleString = work.find("title").text
                    else:
                        logging.warning( _("Missing work element in header") )
            else:
                logging.warning( _("Missing header element (looking for '{}' tag)".format( self._headerTag ) ) )
            if header.tail is not None and header.tail.strip(): logging.error( _("Unexpected '{}' tail data after header").format( element.tail ) )
        else:
            logging.error( _("Expected to load '{}' but got '{}'").format( self._treeTag, self._XMLtree.tag ) )
    # end of __load

    def __validate( self ):
        """
        Check/validate the loaded data.
        """
        assert( self._XMLtree )

        uniqueDict = {}
        for elementName in self._uniqueElements: uniqueDict["Element_"+elementName] = []
        for attributeName in self._uniqueAttributes: uniqueDict["Attribute_"+attributeName] = []

        expectedID = 1
        for j,element in enumerate(self._XMLtree):
            if element.tag == self._mainElementTag:
                # Check compulsory attributes on this main element
                for attributeName in self._compulsoryAttributes:
                    attributeValue = element.get( attributeName )
                    if attributeValue is None:
                        logging.error( _("Compulsory '{}' attribute is missing from {} element in record {}").format( attributeName, element.tag, j ) )
                    if not attributeValue:
                        logging.warning( _("Compulsory '{}' attribute is blank on {} element in record {}").format( attributeName, element.tag, j ) )

                # Check optional attributes on this main element
                for attributeName in self._optionalAttributes:
                    attributeValue = element.get( attributeName )
                    if attributeValue is not None:
                        if not attributeValue:
                            logging.warning( _("Optional '{}' attribute is blank on {} element in record {}").format( attributeName, element.tag, j ) )

                # Check for unexpected additional attributes on this main element
                for attributeName in element.keys():
                    attributeValue = element.get( attributeName )
                    if attributeName not in self._compulsoryAttributes and attributeName not in self._optionalAttributes:
                        logging.warning( _("Additional '{}' attribute ('{}') found on {} element in record {}").format( attributeName, attributeValue, element.tag, j ) )

                # Check the attributes that must contain unique information (in that particular field -- doesn't check across different attributes)
                for attributeName in self._uniqueAttributes:
                    attributeValue = element.get( attributeName )
                    if attributeValue is not None:
                        if attributeValue in uniqueDict["Attribute_"+attributeName]:
                            logging.error( _("Found '{}' data repeated in '{}' field on {} element in record {}").format( attributeValue, attributeName, element.tag, j ) )
                        uniqueDict["Attribute_"+attributeName].append( attributeValue )

                # Get the referenceAbbreviation to use as a record ID
                ID = element.find("referenceAbbreviation").text

                # Check compulsory elements
                for elementName in self._compulsoryElements:
                    if element.find( elementName ) is None:
                        logging.error( _("Compulsory '{}' element is missing in record with ID '{}' (record {})").format( elementName, ID, j ) )
                    elif not element.find( elementName ).text:
                        logging.warning( _("Compulsory '{}' element is blank in record with ID '{}' (record {})").format( elementName, ID, j ) )

                # Check optional elements
                for elementName in self._optionalElements:
                    if element.find( elementName ) is not None:
                        if not element.find( elementName ).text:
                            logging.warning( _("Optional '{}' element is blank in record with ID '{}' (record {})").format( elementName, ID, j ) )

                # Check for unexpected additional elements
                for subelement in element:
                    if subelement.tag not in self._compulsoryElements and subelement.tag not in self._optionalElements:
                        logging.warning( _("Additional '{}' element ('{}') found in record with ID '{}' (record {})").format( subelement.tag, subelement.text, ID, j ) )

                # Check the elements that must contain unique information (in that particular element -- doesn't check across different elements)
                for elementName in self._uniqueElements:
                    if element.find( elementName ) is not None:
                        text = element.find( elementName ).text
                        if text in uniqueDict["Element_"+elementName]:
                            logging.error( _("Found '{}' data repeated in '{}' element in record with ID '{}' (record {})").format( text, elementName, ID, j ) )
                        uniqueDict["Element_"+elementName].append( text )
            else:
                logging.warning( _("Unexpected element: {} in record {}").format( element.tag, j ) )
            if element.tail is not None and element.tail.strip(): logging.error( _("Unexpected '{}' tail data after {} element in record {}").format( element.tail, element.tag, j ) )
        if self._XMLtree.tail is not None and self._XMLtree.tail.strip(): logging.error( _("Unexpected '{}' tail data after {} element").format( self._XMLtree.tail, self._XMLtree.tag ) )
    # end of __validate

    def __str__( self ):
        """
        This method returns the string representation of a Bible book code.
        
        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        indent = 2
        result = "_BibleBooksCodesConverter object"
        if self.titleString: result += ('\n' if result else '') + ' '*indent + _("Title: {}").format( self.titleString )
        if self.versionString: result += ('\n' if result else '') + ' '*indent + _("Version: {}").format( self.versionString )
        if self.dateString: result += ('\n' if result else '') + ' '*indent + _("Date: {}").format( self.dateString )
        if self._XMLtree is not None: result += ('\n' if result else '') + ' '*indent + _("Number of entries = {}").format( len(self._XMLtree) )
        return result
    # end of __str__

    def __len__( self ):
        """ Returns the number of books codes loaded. """
        return len( self._XMLtree )
    # end of __len__

    def importDataToPython( self ):
        """
        Loads (and pivots) the data (not including the header) into suitable Python containers to use in a Python program.
        (Of course, you can just use the elementTree in self._XMLtree if you prefer.)
        """
        assert( self._XMLtree )
        if self.__DataDicts: # We've already done an import/restructuring -- no need to repeat it
            return self.__DataDicts

        # We'll create a number of dictionaries with different elements as the key
        myIDDict,myRADict, mySBLDict,myOADict,mySwDict,myCCELDict,myPADict,myPNDict,myNETDict,myBzDict, myENDict = OrderedDict(),OrderedDict(), {},{},{},{},{},{},{},{}, {}
        for element in self._XMLtree:
            # Get the required information out of the tree for this element
            # Start with the compulsory elements
            nameEnglish = element.find("nameEnglish").text # This name is really just a comment element
            referenceAbbreviation = element.find("referenceAbbreviation").text
            if referenceAbbreviation.upper() != referenceAbbreviation:
                logging.error( _("Reference abbreviation '{}' should be UPPER CASE").format( referenceAbbreviation ) )
            ID = element.find("referenceNumber").text
            intID = int( ID )
            # The optional elements are set to None if they don't exist
            expectedChapters = None if element.find("expectedChapters") is None else element.find("expectedChapters").text
            SBLAbbreviation = None if element.find("SBLAbbreviation") is None else element.find("SBLAbbreviation").text
            OSISAbbreviation = None if element.find("OSISAbbreviation") is None else element.find("OSISAbbreviation").text
            SwordAbbreviation = None if element.find("SwordAbbreviation") is None else element.find("SwordAbbreviation").text
            CCELNumberString = None if element.find("CCELNumber") is None else element.find("CCELNumber").text
            #CCELNumber = int( CCELNumberString ) if CCELNumberString else -1
            ParatextAbbreviation = None if element.find("ParatextAbbreviation") is None else element.find("ParatextAbbreviation").text
            ParatextNumberString = None if element.find("ParatextNumber") is None else element.find("ParatextNumber").text
            #ParatextNumber = int( ParatextNumberString ) if ParatextNumberString else -1
            NETBibleAbbreviation = None if element.find("NETBibleAbbreviation") is None else element.find("NETBibleAbbreviation").text
            ByzantineAbbreviation = None if element.find("ByzantineAbbreviation") is None else element.find("ByzantineAbbreviation").text
            possibleAlternativeBooks = None if element.find("possibleAlternativeBooks") is None else element.find("possibleAlternativeBooks").text

            # Now put it into my dictionaries for easy access
            # This part should be customized or added to for however you need to process the data
            #   Add .upper() if you require the abbreviations to be uppercase (or .lower() for lower case)
            #   The referenceAbbreviation is UPPER CASE by definition
            if "referenceAbbreviation" in self._compulsoryElements or referenceAbbreviation:
                if "referenceAbbreviation" in self._uniqueElements: assert( referenceAbbreviation not in myRADict ) # Shouldn't be any duplicates
                #myRADict[referenceAbbreviation] = ( intID, SBLAbbreviation, OSISAbbreviation, SwordAbbreviation, CCELNumberString, ParatextAbbreviation, ParatextNumberString, NETBibleAbbreviation, ByzantineAbbreviation, expectedChapters, possibleAlternativeBooks, nameEnglish, )
                myRADict[referenceAbbreviation] = { "referenceNumber":intID, "SBLAbbreviation":SBLAbbreviation, "OSISAbbreviation":OSISAbbreviation,
                                                    "SwordAbbreviation":SwordAbbreviation, "CCELNumberString":CCELNumberString,
                                                    "ParatextAbbreviation":ParatextAbbreviation, "ParatextNumberString":ParatextNumberString,
                                                    "NETBibleAbbreviation":NETBibleAbbreviation, "ByzantineAbbreviation":ByzantineAbbreviation,
                                                    "numExpectedChapters":expectedChapters, "possibleAlternativeBooks":possibleAlternativeBooks, "nameEnglish":nameEnglish }
            if "referenceNumber" in self._compulsoryElements or ID:
                if "referenceNumber" in self._uniqueElements: assert( intID not in myIDDict ) # Shouldn't be any duplicates
                #myIDDict[intID] = ( referenceAbbreviation, SBLAbbreviation, OSISAbbreviation, SwordAbbreviation, CCELNumberString, ParatextAbbreviation, ParatextNumberString, NETBibleAbbreviation, ByzantineAbbreviation, expectedChapters, possibleAlternativeBooks, nameEnglish, )
                myIDDict[intID] = { "referenceAbbreviation":referenceAbbreviation, "SBLAbbreviation":SBLAbbreviation, "OSISAbbreviation":OSISAbbreviation,
                                    "SwordAbbreviation":SwordAbbreviation, "CCELNumberString":CCELNumberString,
                                    "ParatextAbbreviation":ParatextAbbreviation, "ParatextNumberString":ParatextNumberString,
                                    "NETBibleAbbreviation":NETBibleAbbreviation, "ByzantineAbbreviation":ByzantineAbbreviation,
                                    "numExpectedChapters":expectedChapters, "possibleAlternativeBooks":possibleAlternativeBooks, "nameEnglish":nameEnglish }
            if "SBLAbbreviation" in self._compulsoryElements or SBLAbbreviation:
                if "SBLAbbreviation" in self._uniqueElements: ssert( SBLAbbreviation not in myOADict ) # Shouldn't be any duplicates 
                mySBLDict[SBLAbbreviation] = ( intID, referenceAbbreviation, )
            if "OSISAbbreviation" in self._compulsoryElements or OSISAbbreviation:
                if "OSISAbbreviation" in self._uniqueElements: assert( OSISAbbreviation not in myOADict ) # Shouldn't be any duplicates 
                myOADict[OSISAbbreviation] = ( intID, referenceAbbreviation )
            if "SwordAbbreviation" in self._compulsoryElements or SwordAbbreviation:
                if "SwordAbbreviation" in self._uniqueElements: assert( SwordAbbreviation not in mySwDict ) # Shouldn't be any duplicates
                mySwDict[SwordAbbreviation] = ( intID, referenceAbbreviation, )
            if "CCELNumberString" in self._compulsoryElements or CCELNumberString:
                if "CCELNumberString" in self._uniqueElements: assert( CCELNumberString not in myCCELDict ) # Shouldn't be any duplicates
                myCCELDict[CCELNumberString] = ( intID, referenceAbbreviation, )
            if "ParatextAbbreviation" in self._compulsoryElements or ParatextAbbreviation:
                if "ParatextAbbreviation" in self._uniqueElements: assert( ParatextAbbreviation not in myPADict ) # Shouldn't be any duplicates
                myPADict[ParatextAbbreviation] = ( intID, referenceAbbreviation, ParatextNumberString, )
            if "ParatextNumberString" in self._compulsoryElements or ParatextNumberString:
                if "ParatextNumberString" in self._uniqueElements: assert( ParatextNumberString not in myPNDict ) # Shouldn't be any duplicates
                myPNDict[ParatextNumberString] = ( intID, referenceAbbreviation, ParatextAbbreviation, )
            if "NETBibleAbbreviation" in self._compulsoryElements or NETBibleAbbreviation:
                if "NETBibleAbbreviation" in self._uniqueElements: assert( NETBibleAbbreviation not in myBzDict ) # Shouldn't be any duplicates
                myNETDict[NETBibleAbbreviation] = ( intID, referenceAbbreviation, )
            if "ByzantineAbbreviation" in self._compulsoryElements or ByzantineAbbreviation:
                if "ByzantineAbbreviation" in self._uniqueElements: assert( ByzantineAbbreviation not in myBzDict ) # Shouldn't be any duplicates
                myBzDict[ByzantineAbbreviation] = ( intID, referenceAbbreviation, )
            if "nameEnglish" in self._compulsoryElements or ParatextNumberString:
                if "nameEnglish" in self._uniqueElements: assert( nameEnglish not in myENDict ) # Shouldn't be any duplicates
                myENDict[nameEnglish] = ( intID, referenceAbbreviation )
        self.__DataDicts = { "referenceNumberDict":myIDDict, "referenceAbbreviationDict":myRADict, "SBLDict":mySBLDict, "OSISAbbreviationDict":myOADict, "SwordAbbreviationDict":mySwDict,
                        "CCELDict":myCCELDict, "ParatextAbbreviationDict":myPADict, "ParatextNumberDict":myPNDict, "NETBibleAbbreviationDict":myNETDict,
                        "ByzantineAbbreviationDict":myBzDict, "EnglishNameDict":myENDict }
        return self.__DataDicts # Just delete any of the dictionaries that you don't need
    # end of importDataToPython

    def exportDataToPython( self, filepath=None ):
        """
        Writes the information tables to a .py file that can be cut and pasted into a Python program.
        """
        def exportPythonDict( theFile, theDict, dictName, keyComment, fieldsComment ):
            """Exports theDict to theFile."""
            for dictKey in theDict.keys(): # Have to iterate this :(
                fieldsCount = len( theDict[dictKey] )
                break # We only check the first (random) entry we get
            theFile.write( "{} = {{\n  # Key is {}\n  # Fields ({}) are: {}\n".format( dictName, keyComment, fieldsCount, fieldsComment ) )
            for dictKey in sorted(theDict.keys()):
                theFile.write( '  {}: {},\n'.format( repr(dictKey), repr(theDict[dictKey]) ) )
            theFile.write( "}}\n# end of {} ({} entries)\n\n".format( dictName, len(theDict) ) )
        # end of exportPythonDict

        from datetime import datetime

        assert( self._XMLtree )
        self.importDataToPython()
        assert( self.__DataDicts )

        if not filepath: filepath = os.path.join( "DerivedFiles", self._filenameBase + "_Tables.py" )
        if Globals.verbosityLevel > 1: print( _("Exporting to {}...").format( filepath ) )
        with open( filepath, 'wt' ) as myFile:
            myFile.write( "# {}\n#\n".format( filepath ) )
            myFile.write( "# This UTF-8 file was automatically generated by BibleBooksCodes.py V{} on {}\n#\n".format( versionString, datetime.now() ) )
            if self.titleString: myFile.write( "# {} data\n".format( self.titleString ) )
            if self.versionString: myFile.write( "#  Version: {}\n".format( self.versionString ) )
            if self.dateString: myFile.write( "#  Date: {}\n#\n".format( self.dateString ) )
            myFile.write( "#   {} {} loaded from the original XML file.\n#\n\n".format( len(self._XMLtree), self._treeTag ) )
            mostEntries = "0=referenceNumber (integer 1..255), 1=referenceAbbreviation/BBB (3-uppercase characters)"
            dictInfo = { "referenceNumberDict":("referenceNumber (integer 1..255)","specified"), "referenceAbbreviationDict":("referenceAbbreviation","specified"),
                            "CCELDict":("CCELNumberString", mostEntries), "SBLDict":("SBLAbbreviation", mostEntries), "OSISAbbreviationDict":("OSISAbbreviation", mostEntries), "SwordAbbreviationDict":("SwordAbbreviation", mostEntries),
                            "ParatextAbbreviationDict":("ParatextAbbreviation", "0=referenceNumber (integer 1..255), 1=referenceAbbreviation/BBB (3-uppercase characters), 2=ParatextNumberString (2-characters)"),
                            "ParatextNumberDict":("ParatextNumberString", "0=referenceNumber (integer 1..255), 1=referenceAbbreviation/BBB (3-uppercase characters), 2=ParatextAbbreviationString (3-characters)"),
                            "NETBibleAbbreviationDict":("NETBibleAbbreviation", mostEntries), "ByzantineAbbreviationDict":("ByzantineAbbreviation", mostEntries), "EnglishNameDict":("nameEnglish", mostEntries) }
            for dictName,dictData in self.__DataDicts.items():
                exportPythonDict( myFile, dictData, dictName, dictInfo[dictName][0], dictInfo[dictName][1] )
            myFile.write( "# end of {}".format( os.path.basename(filepath) ) )
    # end of exportDataToPython

    def exportDataToJSON( self, filepath=None ):
        """
        Writes the information tables to a .json file that can be easily loaded into a Java program.

        See http://en.wikipedia.org/wiki/JSON.
        """
        from datetime import datetime
        import json

        assert( self._XMLtree )
        self.importDataToPython()
        assert( self.__DataDicts )

        if not filepath: filepath = os.path.join( "DerivedFiles", self._filenameBase + "_Tables.json" )
        if Globals.verbosityLevel > 1: print( _("Exporting to {}...").format( filepath ) )
        with open( filepath, 'wt' ) as myFile:
            json.dump( self.__DataDicts, myFile, indent=2 )
    # end of exportDataToJSON

    def exportDataToC( self, filepath=None ):
        """
        Writes the information tables to a .h and .c files that can be included in c and c++ programs.

        NOTE: The (optional) filepath should not have the file extension specified -- this is added automatically.
        """
        def exportPythonDict( hFile, cFile, theDict, dictName, sortedBy, structure ):
            """ Exports theDict to the .h and .c files. """
            def convertEntry( entry ):
                """ Convert special characters in an entry... """
                result = ""
                if isinstance( entry, tuple ):
                    for field in entry:
                        if result: result += ", " # Separate the fields
                        if field is None: result += '""'
                        elif isinstance( field, str): result += '"' + str(field).replace('"','\\"') + '"'
                        elif isinstance( field, int): result += str(field)
                        else: logging.error( _("Cannot convert unknown field type '{}' in entry '{}'").format( field, entry ) )
                elif isinstance( entry, dict ):
                    for key in sorted(entry.keys()):
                        field = entry[key]
                        if result: result += ", " # Separate the fields
                        if field is None: result += '""'
                        elif isinstance( field, str): result += '"' + str(field).replace('"','\\"') + '"'
                        elif isinstance( field, int): result += str(field)
                        else: logging.error( _("Cannot convert unknown field type '{}' in entry '{}'").format( field, entry ) )
                else:
                    logging.error( _("Can't handle this type of entry yet: {}").format( repr(entry) ) )
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
                    logging.error( _("Can't handle this type of key data yet: {}").format( dictKey ) )
            cFile.write( "]}}; // {} ({} entries)\n\n".format( dictName, len(theDict) ) )
        # end of exportPythonDict

        from datetime import datetime

        assert( self._XMLtree )
        self.importDataToPython()
        assert( self.__DataDicts )

        if not filepath: filepath = os.path.join( "DerivedFiles", self._filenameBase + "_Tables" )
        hFilepath = filepath + '.h'
        cFilepath = filepath + '.c'
        if Globals.verbosityLevel > 1: print( _("Exporting to {}...").format( cFilepath ) ) # Don't bother telling them about the .h file
        ifdefName = self._filenameBase.upper() + "_Tables_h"

        with open( hFilepath, 'wt' ) as myHFile, open( cFilepath, 'wt' ) as myCFile:
            myHFile.write( "// {}\n//\n".format( hFilepath ) )
            myCFile.write( "// {}\n//\n".format( cFilepath ) )
            lines = "// This UTF-8 file was automatically generated by BibleBooksCodes.py V{} on {}\n//\n".format( versionString, datetime.now() )
            myHFile.write( lines ); myCFile.write( lines )
            if self.titleString:
                lines = "// {} data\n".format( self.titleString )
                myHFile.write( lines ); myCFile.write( lines )
            if self.versionString:
                lines = "//  Version: {}\n".format( self.versionString )
                myHFile.write( lines ); myCFile.write( lines )
            if self.dateString:
                lines = "//  Date: {}\n//\n".format( self.dateString )
                myHFile.write( lines ); myCFile.write( lines )
            myCFile.write( "//   {} {} loaded from the original XML file.\n//\n\n".format( len(self._XMLtree), self._treeTag ) )
            myHFile.write( "\n#ifndef {}\n#define {}\n\n".format( ifdefName, ifdefName ) )
            myCFile.write( '#include "{}"\n\n'.format( os.path.basename(hFilepath) ) )

            CHAR = "const unsigned char"
            BYTE = "const int"
            dictInfo = {
                "referenceNumberDict":("referenceNumber (integer 1..255)",
                    "{} referenceNumber; {}* ByzantineAbbreviation; {}* CCELNumberString; {}* NETBibleAbbreviation; {}* OSISAbbreviation; {} ParatextAbbreviation[3+1]; {} ParatextNumberString[2+1]; {}* SBLAbbreviation; {}* SwordAbbreviation; {}* nameEnglish; {}* numExpectedChapters; {}* possibleAlternativeBooks; {} referenceAbbreviation[3+1];"
                   .format(BYTE, CHAR, CHAR, CHAR, CHAR, CHAR, CHAR, CHAR, CHAR, CHAR, CHAR, CHAR, CHAR ) ),
                "referenceAbbreviationDict":("referenceAbbreviation",
                    "{} referenceAbbreviation[3+1]; {}* ByzantineAbbreviation; {}* CCELNumberString; {} referenceNumber; {}* NETBibleAbbreviation; {}* OSISAbbreviation; {} ParatextAbbreviation[3+1]; {} ParatextNumberString[2+1]; {}* SBLAbbreviation; {}* SwordAbbreviation; {}* nameEnglish; {}* numExpectedChapters; {}* possibleAlternativeBooks;"
                   .format(CHAR, CHAR, CHAR, BYTE, CHAR, CHAR, CHAR, CHAR, CHAR, CHAR, CHAR, CHAR, CHAR ) ),
                "CCELDict":("CCELNumberString", "{}* CCELNumberString; {} referenceNumber; {} referenceAbbreviation[3+1];".format(CHAR,BYTE,CHAR) ),
                "SBLDict":("SBLAbbreviation", "{}* SBLAbbreviation; {} referenceNumber; {} referenceAbbreviation[3+1];".format(CHAR,BYTE,CHAR) ),
                "OSISAbbreviationDict":("OSISAbbreviation", "{}* OSISAbbreviation; {} referenceNumber; {} referenceAbbreviation[3+1];".format(CHAR,BYTE,CHAR) ),
                "SwordAbbreviationDict":("SwordAbbreviation", "{}* SwordAbbreviation; {} referenceNumber; {} referenceAbbreviation[3+1];".format(CHAR,BYTE,CHAR) ),
                "ParatextAbbreviationDict":("ParatextAbbreviation", "{} ParatextAbbreviation[3+1]; {} referenceNumber; {} referenceAbbreviation[3+1]; {} ParatextNumberString[2+1];".format(CHAR,BYTE,CHAR,CHAR) ),
                "ParatextNumberDict":("ParatextNumberString", "{} ParatextNumberString[2+1]; {} referenceNumber; {} referenceAbbreviation[3+1]; {} ParatextAbbreviation[3+1];".format(CHAR,BYTE,CHAR,CHAR) ),
                "NETBibleAbbreviationDict":("NETBibleAbbreviation", "{}* NETBibleAbbreviation; {} referenceNumber; {} referenceAbbreviation[3+1];".format(CHAR,BYTE,CHAR) ),
                "ByzantineAbbreviationDict":("ByzantineAbbreviation", "{}* ByzantineAbbreviation; {} referenceNumber; {} referenceAbbreviation[3+1];".format(CHAR,BYTE,CHAR) ),
                "EnglishNameDict":("nameEnglish", "{}* nameEnglish; {} referenceNumber; {} referenceAbbreviation[3+1];".format(CHAR,BYTE,CHAR) ) }

            for dictName,dictData in self.__DataDicts.items():
                exportPythonDict( myHFile, myCFile, dictData, dictName, dictInfo[dictName][0], dictInfo[dictName][1] )

            myHFile.write( "#endif // {}\n\n".format( ifdefName ) )
            myHFile.write( "// end of {}".format( os.path.basename(hFilepath) ) )
            myCFile.write( "// end of {}".format( os.path.basename(cFilepath) ) )
    # end of exportDataToC
# end of _BibleBooksCodesConverter class


@singleton # Can only ever have one instance
class BibleBooksCodes:
    """
    Class for handling BibleBooksCodes.

    This class doesn't deal at all with XML, only with Python dictionaries, etc.

    Note: BBB is used in this class to represent the three-character referenceAbbreviation.
    """

    def __init__( self ): # We can't give this parameters because of the singleton
        """
        Constructor: 
        """
        self._bbcc = _BibleBooksCodesConverter()
        self.__DataDicts = None # We'll import into this in loadData
    # end of __init__

    def loadData( self, XMLFilepath=None ):
        """ Loads the XML data file and imports it to dictionary format (if not done already). """
        if not self.__DataDicts: # We need to load them once -- don't do this unnecessarily
            self._bbcc.loadAndValidate( XMLFilepath ) # Load the XML (if not done already)
            self.__DataDicts = self._bbcc.importDataToPython() # Get the various dictionaries organised for quick lookup
            del self._bbcc # Now the converter class (that handles the XML) is no longer needed
        return self
    # end of loadData

    def __str__( self ):
        """
        This method returns the string representation of a Bible book code.
        
        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        indent = 2
        result = "BibleBooksCodes object"
        result += ('\n' if result else '') + ' '*indent + _("Number of entries = {}").format( len(self.__DataDicts["referenceAbbreviationDict"]) )
        return result
    # end of __str__

    def __len__( self ):
        """ Return the number of available codes. """
        assert( len(self.__DataDicts["referenceAbbreviationDict"]) == len(self.__DataDicts["referenceNumberDict"]) ) 
        return len(self.__DataDicts["referenceAbbreviationDict"])

    def getBBB( self, referenceNumber ):
        """ Return the referenceAbbreviation for the given book number (referenceNumber). """
        if not 1 <= referenceNumber <= 255: raise ValueError
        return self.__DataDicts["referenceNumberDict"][referenceNumber]["referenceAbbreviation"]

    def isValidReferenceAbbreviation( self, BBB ):
        """ Returns True or False. """
        return BBB in self.__DataDicts["referenceAbbreviationDict"]

    def getAllReferenceAbbreviations( self ):
        """ Returns a list of all possible BBB codes. """
        return [BBB for BBB in self.__DataDicts["referenceAbbreviationDict"]]
        #return self.__DataDicts["referenceAbbreviationDict"].keys() # Why didn't this work?

    def getReferenceNumber( self, BBB ):
        """ Return the referenceNumber 1..255 for the given book code (referenceAbbreviation). """
        return self.__DataDicts["referenceAbbreviationDict"][BBB]["referenceNumber"]

    def getCCELNumber( self, BBB ):
        """ Return the CCEL number string for the given book code (referenceAbbreviation). """
        return self.__DataDicts["referenceAbbreviationDict"][BBB]["CCELNumberString"]

    def getSBLAbbreviation( self, BBB ):
        """ Return the SBL abbreviation string for the given book code (referenceAbbreviation). """
        return self.__DataDicts["referenceAbbreviationDict"][BBB]["SBLAbbreviation"]

    def getOSISAbbreviation( self, BBB ):
        """ Return the OSIS abbreviation string for the given book code (referenceAbbreviation). """
        return self.__DataDicts["referenceAbbreviationDict"][BBB]["OSISAbbreviation"]

    def getSwordAbbreviation( self, BBB ):
        """ Return the Sword abbreviation string for the given book code (referenceAbbreviation). """
        return self.__DataDicts["referenceAbbreviationDict"][BBB]["SwordAbbreviation"]

    def getParatextAbbreviation( self, BBB ):
        """ Return the Paratext abbreviation string for the given book code (referenceAbbreviation). """
        return self.__DataDicts["referenceAbbreviationDict"][BBB]["ParatextAbbreviation"]

    def getParatextNumber( self, BBB ):
        """ Return the Paratext number string for the given book code (referenceAbbreviation). """
        return self.__DataDicts["referenceAbbreviationDict"][BBB]["ParatextNumberString"]

    def getNETBibleAbbreviation( self, BBB ):
        """ Return the NET Bible abbreviation string for the given book code (referenceAbbreviation). """
        return self.__DataDicts["referenceAbbreviationDict"][BBB]["NETBibleAbbreviation"]

    def getByzantineAbbreviation( self, BBB ):
        """ Return the Byzantine abbreviation string for the given book code (referenceAbbreviation). """
        return self.__DataDicts["referenceAbbreviationDict"][BBB]["ByzantineAbbreviation"]

    def getBBBFromOSIS( self, osisAbbreviation ):
        """ Return the reference abbreviation strin for the given OSIS book code string. """
        return self.__DataDicts["OSISAbbreviationDict"][osisAbbreviation][1]

    def getExpectedChaptersList( self, BBB ):
        """
        Gets a list with the number of expected chapters for the given book code (referenceAbbreviation).
        The number(s) of expected chapters is left in string form (not int).

        Why is it a list?
            Because some books have alternate possible numbers of chapters depending on the Biblical tradition.
        """
        #if BBB not in self.__DataDicts["referenceAbbreviationDict"] \
        #or "numExpectedChapters" not in self.__DataDicts["referenceAbbreviationDict"][BBB] \
        #or self.__DataDicts["referenceAbbreviationDict"][BBB]["numExpectedChapters"] is None:
        if "numExpectedChapters" not in self.__DataDicts["referenceAbbreviationDict"][BBB] \
        or self.__DataDicts["referenceAbbreviationDict"][BBB]["numExpectedChapters"] is None:
            return []

        eC = self.__DataDicts["referenceAbbreviationDict"][BBB]["numExpectedChapters"]
        if eC: return [v for v in eC.split(',')]
    # end of getExpectedChaptersList

    def getSingleChapterBooksList( self ):
        """ Gets a list of single chapter book codes. """
        results = []
        for BBB in self.__DataDicts["referenceAbbreviationDict"]:
            if self.__DataDicts["referenceAbbreviationDict"][BBB]["numExpectedChapters"] is not None \
            and self.__DataDicts["referenceAbbreviationDict"][BBB]["numExpectedChapters"] == '1':
                results.append( BBB )
        return results
    # end of getSingleChapterBooksList

    def getOSISSingleChapterBooksList( self ):
        """ Gets a list of OSIS single chapter book abbreviations. """
        results = []
        for BBB in self.getSingleChapterBooksList():
            osisAbbrev = self.getOSISAbbreviation(BBB)
            if osisAbbrev is not None: results.append( osisAbbrev )
        return results
    # end of getOSISSingleChapterBooksList

    def getAllOSISBooksCodes( self ):
        """
        Return a list of all available OSIS book codes.
        """
        return [bk for bk in self.__DataDicts["OSISAbbreviationDict"]]
    #end of getAllOSISBooksCodes

    def getAllParatextBooksCodeNumberTriples( self ):
        """
        Return a list of all available Paratext book codes.

        The list contains tuples of: paratextAbbreviation, paratextNumber, referenceAbbreviation
        """
        found, result = [], []
        for BBB, values in self.__DataDicts["referenceAbbreviationDict"].items():
            pA = values["ParatextAbbreviation"]
            pN = values["ParatextNumberString"]
            if pA is not None and pN is not None:
                if pA not in found: # Don't want duplicates (where more than one book maps to a single paratextAbbreviation)
                    result.append( (pA, pN, BBB,) )
                    found.append( pA )
        return result
    # end of getAllParatextBooksCodeNumberTriples

    def getEnglishName_NR( self, BBB ): # NR = not recommended
        """
        Returns the first English name for a book.

        Remember: These names are only intended as comments or for some basic module processing.
            They are not intended to be used for a proper international human interface.
            The first one in the list is supposed to be the more common.
        """
        return self.__DataDicts["referenceAbbreviationDict"][BBB]["nameEnglish"].split('/',1)[0].strip()
    # end of getEnglishName_NR

    def getEnglishNameList_NR( self, BBB ): # NR = not recommended
        """
        Returns a list of possible English names for a book.

        Remember: These names are only intended as comments or for some basic module processing.
            They are not intended to be used for a proper international human interface.
            The first one in the list is supposed to be the more common.
        """
        names = self.__DataDicts["referenceAbbreviationDict"][BBB]["nameEnglish"]
        return [name.strip() for name in names.split('/')]
    # end of getEnglishNameList_NR

    def isOldTestament_NR( self, BBB ): # NR = not recommended
        """ Returns True if the given referenceAbbreviation indicates a European Protestant Old Testament book.
            NOTE: This is not truly international so it's not a recommended function. """
        return 1 <= self.getReferenceNumber(BBB) <= 39
    # end of isOldTestament_NR

    def isNewTestament_NR( self, BBB ): # NR = not recommended
        """ Returns True if the given referenceAbbreviation indicates a European Protestant New Testament book.
            NOTE: This is not truly international so it's not a recommended function. """
        return 40 <= self.getReferenceNumber(BBB) <= 66
    # end of isNewTestament_NR
# end of BibleBooksCodes class


def main():
    """
    Main program to handle command line parameters and then run what they want.
    """
    # Handle command line parameters
    from optparse import OptionParser
    parser = OptionParser( version="v{}".format( versionString ) )
    parser.add_option("-e", "--export", action="store_true", dest="export", default=False, help="export the XML file to .py and .h/.c formats suitable for directly including into other programs, as well as .json.")
    Globals.addStandardOptionsAndProcess( parser )

    if Globals.verbosityLevel > 1: print( "{} V{}".format( progName, versionString ) )

    if Globals.commandLineOptions.export:
        bbcc = _BibleBooksCodesConverter().loadAndValidate() # Load the XML
        bbcc.exportDataToPython() # Produce the .py tables
        bbcc.exportDataToJSON() # Produce a json output file
        bbcc.exportDataToC() # Produce the .h and .c tables

    else: # Must be demo mode
        # Demo the converter object
        bbcc = _BibleBooksCodesConverter().loadAndValidate() # Load the XML
        print( bbcc ) # Just print a summary

        # Demo the BibleBooksCodes object
        bbc = BibleBooksCodes().loadData() # Doesn't reload the XML unnecessarily :)
        print( bbc ) # Just print a summary
        print( "Esther has {} expected chapters".format(bbc.getExpectedChaptersList("EST")) )
        print( "Apocalypse of Ezra has {} expected chapters".format(bbc.getExpectedChaptersList("EZA")) )
        print( "Names for Genesis are:", bbc.getEnglishNameList_NR("GEN") )
        print( "Names for Sirach are:", bbc.getEnglishNameList_NR('SIR') )
        print( "All BBBs:", bbc.getAllReferenceAbbreviations() )
        print( "PT triples:", bbc.getAllParatextBooksCodeNumberTriples() )
        print( "Single chapter books (and OSIS):\n  {}\n  {}".format(bbc.getSingleChapterBooksList(), bbc.getOSISSingleChapterBooksList()) )
# end of main

if __name__ == '__main__':
    main()
# end of BibleBooksCodes.py
