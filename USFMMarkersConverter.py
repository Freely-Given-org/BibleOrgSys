#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# USFMMarkersConverter.py
#
# Module handling USFMMarkers.xml to produce C and Python data tables
#   Last modified: 2011-06-13 (also update versionString below)
#
# Copyright (C) 2011 Robert Hunt
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
Module handling USFMMarkers.xml and to export to JSON, C, and Python data tables.
"""

progName = "USFM Markers converter"
versionString = "0.53"


import logging, os.path
from gettext import gettext as _
from collections import OrderedDict
from xml.etree.cElementTree import ElementTree

from singleton import singleton
import Globals


deprecatedUSFMMarkers = [ 'pdi', 'pde', 'wr', 'ps' ] # These aren't listed in the XML file


@singleton # Can only ever have one instance
class USFMMarkersConverter:
    """
    Class for reading, validating, and converting USFMMarkers.
    This is only intended as a transitory class (used at start-up).
    The USFMMarkers class has functions more generally useful.
    """

    def __init__( self ): # We can't give this parameters because of the singleton
        """
        Constructor: expects the filepath of the source XML file.
        Loads (and crudely validates the XML file) into an element tree.
        """
        self._filenameBase = "USFMMarkers"

        # These fields are used for parsing the XML
        self._treeTag = "USFMMarkers"
        self._headerTag = "header"
        self._mainElementTag = "USFMMarker"

        # These fields are used for automatically checking/validating the XML
        self._compulsoryAttributes = ()
        self._optionalAttributes = ()
        self._uniqueAttributes = self._compulsoryAttributes + self._optionalAttributes
        self._compulsoryElements = ( "nameEnglish", "marker", "compulsory", "level", "numberable", "nests", "hasContent", "printed", "closed", "occursIn", )
        self._optionalElements = ( "description", )
        #self._uniqueElements = self._compulsoryElements + self.optionalElements
        self._uniqueElements = ( "nameEnglish", "marker", )

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
                XMLFilepath = os.path.join( os.path.dirname(__file__), "DataFiles", self._filenameBase + ".xml" ) # Relative to module, not cwd
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

        if Globals.verbosityLevel > 2: print( _("Loading USFMMarkers XML file from '{}'...").format( self.__XMLFilepath ) )
        self._XMLtree = ElementTree().parse( self.__XMLFilepath )
        assert( self._XMLtree ) # Fail here if we didn't load anything at all

        if self._XMLtree.tag == self._treeTag:
            header = self._XMLtree[0]
            if header.tag == self._headerTag:
                self.XMLheader = header
                self._XMLtree.remove( header )
                Globals.checkXMLNoText( header, "header" )
                Globals.checkXMLNoTail( header, "header" )
                Globals.checkXMLNoAttributes( header, "header" )
                if len(header)>1:
                    logging.info( _("Unexpected elements in header") )
                elif len(header)==0:
                    logging.info( _("Missing work element in header") )
                else:
                    work = header[0]
                    Globals.checkXMLNoText( work, "work in header" )
                    Globals.checkXMLNoTail( work, "work in header" )
                    Globals.checkXMLNoAttributes( work, "work in header" )
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
                Globals.checkXMLNoText( element, element.tag )
                Globals.checkXMLNoTail( element, element.tag )
                if not self._compulsoryAttributes and not self._optionalAttributes: Globals.checkXMLNoAttributes( element, element.tag )
                if not self._compulsoryElements and not self._optionalElements: Globals.checkXMLNoSubelements( element, element.tag )

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

                # Get the marker to use as a record ID
                marker = element.find("marker").text

                # Check compulsory elements
                for elementName in self._compulsoryElements:
                    if element.find( elementName ) is None:
                        logging.error( _("Compulsory '{}' element is missing in record with marker '{}' (record {})").format( elementName, marker, j ) )
                    elif not element.find( elementName ).text:
                        logging.warning( _("Compulsory '{}' element is blank in record with marker '{}' (record {})").format( elementName, marker, j ) )

                # Check optional elements
                for elementName in self._optionalElements:
                    if element.find( elementName ) is not None:
                        if not element.find( elementName ).text:
                            logging.warning( _("Optional '{}' element is blank in record with marker '{}' (record {})").format( elementName, marker, j ) )

                # Check for unexpected additional elements
                for subelement in element:
                    if subelement.tag not in self._compulsoryElements and subelement.tag not in self._optionalElements:
                        logging.warning( _("Additional '{}' element ('{}') found in record with marker '{}' (record {})").format( subelement.tag, subelement.text, marker, j ) )

                # Check the elements that must contain unique information (in that particular element -- doesn't check across different elements)
                for elementName in self._uniqueElements:
                    if element.find( elementName ) is not None:
                        text = element.find( elementName ).text
                        if text in uniqueDict["Element_"+elementName]:
                            logging.error( _("Found '{}' data repeated in '{}' element in record with marker '{}' (record {})").format( text, elementName, marker, j ) )
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
        result = "USFMMarkersConverter object"
        if self.titleString: result += ('\n' if result else '') + ' '*indent + _("Title: {}").format( self.titleString )
        if self.versionString: result += ('\n' if result else '') + ' '*indent + _("Version: {}").format( self.versionString )
        if self.dateString: result += ('\n' if result else '') + ' '*indent + _("Date: {}").format( self.dateString )
        if self._XMLtree is not None: result += ('\n' if result else '') + ' '*indent + _("Number of entries = {}").format( len(self._XMLtree) )
        return result
    # end of __str__

    def __len__( self ):
        """ Returns the number of SFM markers loaded. """
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

        # Load and validate entries and create the dictionaries and lists
        # Note that the combined lists include the numbered markers, e.g., s as well as s1, s2, ...
        rawMarkerDict, numberedMarkerList, combinedMarkerDict, = OrderedDict(), [], {}
        conversionDict, backConversionDict = {}, {}
        newlineMarkersList, numberedNewlineMarkersList, combinedNewlineMarkersList = [], [], []
        internalMarkersList, numberedInternalMarkersList, combinedInternalMarkersList = [], [], []
        for element in self._XMLtree:
            # Get the required information out of the tree for this element
            # Start with the compulsory elements
            nameEnglish = element.find("nameEnglish").text # This name is really just a comment element
            marker = element.find("marker").text
            assert( marker not in deprecatedUSFMMarkers )
            if marker.lower() != marker:
                logging.error( _("Marker '{}' should be lower case").format( marker ) )
            compulsory = element.find("compulsory").text
            if  compulsory not in ( "Yes", "No" ): logging.error( _("Unexpected '{}' compulsory field for marker '{}'").format( compulsory, marker ) )
            level = element.find("level").text
            compulsoryFlag = compulsory == "Yes"
            if  level == "Newline": newlineMarkersList.append( marker ); combinedNewlineMarkersList.append( marker )
            elif level == "Internal": internalMarkersList.append( marker )
            else: logging.error( _("Unexpected '{}' level field for marker '{}'").format( level, marker ) )
            numberable = element.find("numberable").text
            if  numberable not in ( "Yes", "No" ): logging.error( _("Unexpected '{}' numberable field for marker '{}'").format( numberable, marker ) )
            numberableFlag = numberable == "Yes"
            if numberableFlag and level == "Character": logging.error( _("Unexpected '{}' numberable field for character marker '{}'").format( numberable, marker ) )
            nests = element.find("nests").text
            if  nests not in ( "Yes", "No" ): logging.error( _("Unexpected '{}' nests field for marker '{}'").format( nests, marker ) )
            nestsFlag = nests == "Yes"
            hasContent = element.find("hasContent").text
            if  hasContent not in ( "Always", "Never", "Sometimes" ): logging.error( _("Unexpected '{}' hasContent field for marker '{}'").format( hasContent, marker ) )
            printed = element.find("printed").text
            if  printed not in ( "Yes", "No" ): logging.error( _("Unexpected '{}' printed field for marker '{}'").format( printed, marker ) )
            printedFlag = printed == "Yes"
            closed = element.find("closed").text
            if  closed not in ( "No", "Always", "Optional" ): logging.error( _("Unexpected '{}' closed field for marker '{}'").format( closed, marker ) )
            occursIn = element.find("occursIn").text
            if  occursIn not in ( "Header", "Introduction", "Text", "Poetry", "Text, Poetry", "Acrostic verse", "Table row", "Footnote", "Cross reference", "Front and back matter" ):
                logging.error( _("Unexpected '{}' occursIn field for marker '{}'").format( occursIn, marker ) )

            # The optional elements are set to None if they don't exist
            #closed = None if element.find("closed") is None else element.find("closed").text
            #if closed is not None and closed not in ( "No", "Always", "Optional" ): logging.error( _("Unexpected '{}' closed field for marker '{}'").format( closed, marker ) )
            #if level=="Character" and closed is None: logging.error( _("Entry for character marker '{}' doesn't have a \"closed\" field").format( marker ) )
            description = None if element.find("description") is None else element.find("description").text
            if description is not None: assert( description )

            # Now put it into my dictionaries and lists for easy access
            #   The marker is lowercase by definition
            if "marker" in self._uniqueElements: assert( marker not in rawMarkerDict ) # Shouldn't be any duplicates
            rawMarkerDict[marker] = { "compulsoryFlag":compulsoryFlag, "level":level, "numberableFlag":numberableFlag, "nestsFlag":nestsFlag,
                                        "hasContent":hasContent, "occursIn":occursIn, "printedFlag":printedFlag, "closed":closed, "description":description, "nameEnglish":nameEnglish }
            combinedMarkerDict[marker] = marker
            if numberableFlag: # We have some extra work to do
                conversionDict[marker] = marker + '1'
                for suffix in ( '123' ): # These are the suffix digits that we allow
                    numberedMarker = marker + suffix
                    backConversionDict[numberedMarker] = marker
                    numberedMarkerList.append( numberedMarker )
                    combinedMarkerDict[numberedMarker] = marker
                    if marker in newlineMarkersList: numberedNewlineMarkersList.append( numberedMarker ); combinedNewlineMarkersList.append( numberedMarker )
                    else: numberedInternalMarkersList.append( numberedMarker ); combinedInternalMarkersList.append( numberedMarker )
            else: # it's not numberable
                numberedMarkerList.append( marker )
                if marker in newlineMarkersList: numberedNewlineMarkersList.append( marker )
                else: numberedInternalMarkersList.append( marker )

        #print( conversionDict ); print( backConversionDict )
        #print( "newlineMarkersList", len(newlineMarkersList), newlineMarkersList )
        #print( "numberedNewlineMarkersList", len(numberedNewlineMarkersList), numberedNewlineMarkersList )
        #print( "combinedNewlineMarkersList", len(combinedNewlineMarkersList), combinedNewlineMarkersList )
        #print( "internalMarkersList", len(internalMarkersList), internalMarkersList )
        self.__DataDicts = { "rawMarkerDict":rawMarkerDict, "numberedMarkerList":numberedMarkerList, "combinedMarkerDict":combinedMarkerDict,
                                "conversionDict":conversionDict, "backConversionDict":backConversionDict,
                                "newlineMarkersList":newlineMarkersList, "numberedNewlineMarkersList":numberedNewlineMarkersList, "combinedNewlineMarkersList":combinedNewlineMarkersList,
                                "internalMarkersList":internalMarkersList, "numberedInternalMarkersList":numberedInternalMarkersList, "combinedInternalMarkersList":combinedInternalMarkersList,
                                "deprecatedMarkersList":deprecatedUSFMMarkers, }
        return self.__DataDicts # Just delete any of the dictionaries that you don't need
    # end of importDataToPython

    def pickle( self, filepath=None ):
        """
        Writes the information tables to a .pickle file that can be easily loaded into a Python3 program.
        """
        import pickle

        assert( self._XMLtree )
        self.importDataToPython()
        assert( self.__DataDicts )

        if not filepath:
            folder = os.path.join( os.path.split(self.__XMLFilepath)[0], "DerivedFiles/" )
            if not os.path.exists( folder ): os.mkdir( folder )
            filepath = os.path.join( folder, self._filenameBase + "_Tables.pickle" )
        if Globals.verbosityLevel > 1: print( _("Exporting to {}...").format( filepath ) )
        with open( filepath, 'wb' ) as myFile:
            pickle.dump( self.__DataDicts, myFile )
    # end of pickle

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
            theFile.write( "{} = {{\n  # Key is {}\n  # Fields ({}) are: {}\n".format( dictName, keyComment, fieldsCount, fieldsComment ) )
            for dictKey in sorted(theDict.keys()):
                theFile.write( '  {}: {},\n'.format( repr(dictKey), repr(theDict[dictKey]) ) )
            theFile.write( "}}\n# end of {} ({} entries)\n\n".format( dictName, len(theDict) ) )
        # end of exportPythonDict

        def exportPythonOrderedDict( theFile, theDict, dictName, keyComment, fieldsComment ):
            """Exports theDict to theFile."""
            assert( isinstance( theDict, OrderedDict ) )
            for dictKey in theDict.keys(): # Have to iterate this :(
                fieldsCount = len( theDict[dictKey] ) if isinstance( theDict[dictKey], (tuple,dict,list) ) else 1
                break # We only check the first (random) entry we get
            theFile.write( '{} = OrderedDict([\n    # Key is {}\n    # Fields ({}) are: {}\n'.format( dictName, keyComment, fieldsCount, fieldsComment ) )
            for dictKey in theDict.keys():
                theFile.write( '  ({}, {}),\n'.format( repr(dictKey), repr(theDict[dictKey]) ) )
            theFile.write( "]), # end of {} ({} entries)\n\n".format( dictName, len(theDict) ) )
        # end of exportPythonDict

        def exportPythonList( theFile, theList, listName, dummy, fieldsComment ):
            """Exports theList to theFile."""
            assert( isinstance( theList, list ) )
            fieldsCount = len( theList[0] ) if isinstance( theList[0], (tuple,dict,list) ) else 1
            theFile.write( '{} = [\n    # Fields ({}) are: {}\n'.format( listName, fieldsCount, fieldsComment ) )
            for j,entry in enumerate(theList):
                theFile.write( '  {}, # {}\n'.format( repr(entry), j ) )
            theFile.write( "], # end of {} ({} entries)\n\n".format( listName, len(theList) ) )
        # end of exportPythonList

        from datetime import datetime

        assert( self._XMLtree )
        self.importDataToPython()
        assert( self.__DataDicts )

        if not filepath: filepath = os.path.join( os.path.split(self.__XMLFilepath)[0], "DerivedFiles", self._filenameBase + "_Tables.py" )
        if Globals.verbosityLevel > 1: print( _("Exporting to {}...").format( filepath ) )
        with open( filepath, 'wt' ) as myFile:
            myFile.write( "# {}\n#\n".format( filepath ) )
            myFile.write( "# This UTF-8 file was automatically generated by USFMMarkers.py V{} on {}\n#\n".format( versionString, datetime.now() ) )
            if self.titleString: myFile.write( "# {} data\n".format( self.titleString ) )
            if self.versionString: myFile.write( "#  Version: {}\n".format( self.versionString ) )
            if self.dateString: myFile.write( "#  Date: {}\n#\n".format( self.dateString ) )
            myFile.write( "#   {} {} loaded from the original XML file.\n#\n\n".format( len(self._XMLtree), self._treeTag ) )
            myFile.write( "from collections import OrderedDict\n\n" )
            dictInfo = { "rawMarkerDict":(exportPythonOrderedDict, "rawMarker (in the original XML order)","specified"),
                            "numberedMarkerList":(exportPythonList, "marker","rawMarker"),
                            "combinedMarkerDict":(exportPythonDict, "marker","rawMarker"),
                            "conversionDict":(exportPythonDict, "rawMarker","numberedMarker"),
                            "backConversionDict":(exportPythonDict, "numberedMarker","rawMarker"),
                            "newlineMarkersList":(exportPythonList, "","rawMarker"),
                            "numberedNewlineMarkersList":(exportPythonList, "","rawMarker"),
                            "combinedNewlineMarkersList":(exportPythonList, "","rawMarker"),
                            "internalMarkersList":(exportPythonList, "","rawMarker"),
                            "numberedInternalMarkersList":(exportPythonList, "","rawMarker"),
                            "combinedInternalMarkersList":(exportPythonList, "","rawMarker"),
                            "deprecatedMarkersList":(exportPythonList, "","rawMarker") }
            for dictName in self.__DataDicts:
                exportFunction, keyComment, fieldsComment = dictInfo[dictName]
                exportFunction( myFile, self.__DataDicts[dictName], dictName, keyComment, fieldsComment )
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

        if not filepath: filepath = os.path.join( os.path.split(self.__XMLFilepath)[0], "DerivedFiles", self._filenameBase + "_Tables.json" )
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

        raise Exception( "C export not written yet, sorry." )
        if not filepath: filepath = os.path.join( os.path.split(self.__XMLFilepath)[0], "DerivedFiles", self._filenameBase + "_Tables" )
        hFilepath = filepath + '.h'
        cFilepath = filepath + '.c'
        if Globals.verbosityLevel > 1: print( _("Exporting to {}...").format( cFilepath ) ) # Don't bother telling them about the .h file
        ifdefName = self._filenameBase.upper() + "_Tables_h"

        with open( hFilepath, 'wt' ) as myHFile, open( cFilepath, 'wt' ) as myCFile:
            myHFile.write( "// {}\n//\n".format( hFilepath ) )
            myCFile.write( "// {}\n//\n".format( cFilepath ) )
            lines = "// This UTF-8 file was automatically generated by USFMMarkers.py V{} on {}\n//\n".format( versionString, datetime.now() )
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
                    "{} referenceNumber; {}* ByzantineAbbreviation; {}* CCELNumberString; {}* NETBibleAbbreviation; {}* OSISAbbreviation; {} ParatextAbbreviation[3+1]; {} ParatextNumberString[2+1]; {}* SBLAbbreviation; {}* SwordAbbreviation; {}* nameEnglish; {}* numExpectedChapters; {}* possibleAlternativeBooks; {} marker[3+1];"
                   .format(BYTE, CHAR, CHAR, CHAR, CHAR, CHAR, CHAR, CHAR, CHAR, CHAR, CHAR, CHAR, CHAR ) ),
                "rawMarkerDict":("marker",
                    "{} marker[3+1]; {}* ByzantineAbbreviation; {}* CCELNumberString; {} referenceNumber; {}* NETBibleAbbreviation; {}* OSISAbbreviation; {} ParatextAbbreviation[3+1]; {} ParatextNumberString[2+1]; {}* SBLAbbreviation; {}* SwordAbbreviation; {}* nameEnglish; {}* numExpectedChapters; {}* possibleAlternativeBooks;"
                   .format(CHAR, CHAR, CHAR, BYTE, CHAR, CHAR, CHAR, CHAR, CHAR, CHAR, CHAR, CHAR, CHAR ) ),
                "CCELDict":("CCELNumberString", "{}* CCELNumberString; {} referenceNumber; {} marker[3+1];".format(CHAR,BYTE,CHAR) ),
                "SBLDict":("SBLAbbreviation", "{}* SBLAbbreviation; {} referenceNumber; {} marker[3+1];".format(CHAR,BYTE,CHAR) ),
                "OSISAbbreviationDict":("OSISAbbreviation", "{}* OSISAbbreviation; {} referenceNumber; {} marker[3+1];".format(CHAR,BYTE,CHAR) ),
                "SwordAbbreviationDict":("SwordAbbreviation", "{}* SwordAbbreviation; {} referenceNumber; {} marker[3+1];".format(CHAR,BYTE,CHAR) ),
                "ParatextAbbreviationDict":("ParatextAbbreviation", "{} ParatextAbbreviation[3+1]; {} referenceNumber; {} marker[3+1]; {} ParatextNumberString[2+1];".format(CHAR,BYTE,CHAR,CHAR) ),
                "ParatextNumberDict":("ParatextNumberString", "{} ParatextNumberString[2+1]; {} referenceNumber; {} marker[3+1]; {} ParatextAbbreviation[3+1];".format(CHAR,BYTE,CHAR,CHAR) ),
                "NETBibleAbbreviationDict":("NETBibleAbbreviation", "{}* NETBibleAbbreviation; {} referenceNumber; {} marker[3+1];".format(CHAR,BYTE,CHAR) ),
                "ByzantineAbbreviationDict":("ByzantineAbbreviation", "{}* ByzantineAbbreviation; {} referenceNumber; {} marker[3+1];".format(CHAR,BYTE,CHAR) ),
                "EnglishNameDict":("nameEnglish", "{}* nameEnglish; {} referenceNumber; {} marker[3+1];".format(CHAR,BYTE,CHAR) ) }

            for dictName,dictData in self.__DataDicts.items():
                exportPythonDict( myHFile, myCFile, dictData, dictName, dictInfo[dictName][0], dictInfo[dictName][1] )

            myHFile.write( "#endif // {}\n\n".format( ifdefName ) )
            myHFile.write( "// end of {}".format( os.path.basename(hFilepath) ) )
            myCFile.write( "// end of {}".format( os.path.basename(cFilepath) ) )
    # end of exportDataToC
# end of USFMMarkersConverter class


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
        umc = USFMMarkersConverter().loadAndValidate() # Load the XML
        umc.pickle() # Produce a pickle output file
        umc.exportDataToPython() # Produce the .py tables
        umc.exportDataToJSON() # Produce a json output file
        umc.exportDataToC() # Produce the .h and .c tables

    else: # Must be demo mode
        # Demo the converter object
        umc = USFMMarkersConverter().loadAndValidate() # Load the XML
        print( umc ) # Just print a summary
# end of main

if __name__ == '__main__':
    main()
# end of USFMMarkersConverter.py
