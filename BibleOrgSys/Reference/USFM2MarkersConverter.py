#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# USFM2MarkersConverter.py
#
# Module handling USFM2Markers.xml to produce C and Python data tables
#
# Copyright (C) 2011-2018 Robert Hunt
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
Module handling USFM2Markers.xml and to export to JSON, C, and Python data tables.
"""

from gettext import gettext as _

lastModifiedDate = '2018-12-03' # by RJH
shortProgramName = "USFM2MarkersConverter"
programName = "USFM2 Markers converter"
programVersion = '0.64'
programNameVersion = f'{shortProgramName} v{programVersion}'
programNameVersionDate = f'{programNameVersion} {_("last modified")} {lastModifiedDate}'

debuggingThisModule = False


import logging, os.path
from datetime import datetime
from xml.etree.ElementTree import ElementTree

if __name__ == '__main__':
    import sys
    sys.path.append( os.path.join(os.path.dirname(__file__), '../') ) # So we can run it from the above folder and still do these imports
from Misc.singleton import singleton
import BibleOrgSysGlobals



@singleton # Can only ever have one instance
class USFM2MarkersConverter:
    """
    Class for reading, validating, and converting USFM2Markers.
    This is only intended as a transitory class (used at start-up).
    The USFM2Markers class has functions more generally useful.
    """

    def __init__( self ): # We can't give this parameters because of the singleton
        """
        Constructor: expects the filepath of the source XML file.
        Loads (and crudely validates the XML file) into an element tree.
        """
        self._filenameBase = 'USFM2Markers'

        # These fields are used for parsing the XML
        self._treeTag = 'USFM2Markers'
        self._headerTag = 'header'
        self._mainElementTag = 'USFMMarker'

        # These fields are used for automatically checking/validating the XML
        self._compulsoryAttributes = ()
        self._optionalAttributes = ()
        self._uniqueAttributes = self._compulsoryAttributes + self._optionalAttributes
        self._compulsoryElements = ( 'nameEnglish', 'marker', 'compulsory', 'level', 'highestNumberSuffix', 'nests', 'hasContent', 'printed', 'closed', 'occursIn', 'deprecated', )
        self._optionalElements = ( 'description', )
        #self._uniqueElements = self._compulsoryElements + self.optionalElements
        self._uniqueElements = ( 'nameEnglish', 'marker', )

        # These are fields that we will fill later
        self._XMLheader, self._XMLtree = None, None
        self.__DataDicts = {} # Used for import
        self.titleString = self.programVersion = self.dateString = ''
    # end of __init__

    def loadAndValidate( self, XMLFilepath=None ):
        """
        Loads (and crudely validates the XML file) into an element tree.
            Allows the filepath of the source XML file to be specified, otherwise uses the default.
        """
        if self._XMLtree is None: # We mustn't have already have loaded the data
            if XMLFilepath is None:
                XMLFilepath = BibleOrgSysGlobals.BOS_DATA_FILES_FOLDERPATH.joinpath( self._filenameBase + '.xml' ) # Relative to module, not cwd
            self.__load( XMLFilepath )
            if BibleOrgSysGlobals.strictCheckingFlag:
                self.__validate()
        else: # The data must have been already loaded
            if XMLFilepath is not None and XMLFilepath!=self.__XMLFilepath: logging.error( _("Bible books codes are already loaded -- your different filepath of {!r} was ignored").format( XMLFilepath ) )
        return self
    # end of loadAndValidate

    def __load( self, XMLFilepath ):
        """
        Load the source XML file and remove the header from the tree.
        Also, extracts some useful elements from the header element.
        """
        assert XMLFilepath
        self.__XMLFilepath = XMLFilepath
        assert self._XMLtree is None or len(self._XMLtree)==0 # Make sure we're not doing this twice

        if BibleOrgSysGlobals.verbosityLevel > 2: print( _("Loading USFM2Markers XML file from {!r}…").format( self.__XMLFilepath ) )
        self._XMLtree = ElementTree().parse( self.__XMLFilepath )
        assert self._XMLtree # Fail here if we didn't load anything at all

        if self._XMLtree.tag == self._treeTag:
            header = self._XMLtree[0]
            if header.tag == self._headerTag:
                self.XMLheader = header
                self._XMLtree.remove( header )
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
                        self.programVersion = work.find('version').text
                        self.dateString = work.find("date").text
                        self.titleString = work.find("title").text
                    else:
                        logging.warning( _("Missing work element in header") )
            else:
                logging.warning( _("Missing header element (looking for {!r} tag)".format( self._headerTag ) ) )
            if header.tail is not None and header.tail.strip(): logging.error( _("Unexpected {!r} tail data after header").format( element.tail ) )
        else:
            logging.error( _("Expected to load {!r} but got {!r}").format( self._treeTag, self._XMLtree.tag ) )
    # end of __load

    def __validate( self ):
        """
        Check/validate the loaded data.
        """
        assert self._XMLtree

        uniqueDict = {}
        for elementName in self._uniqueElements: uniqueDict["Element_"+elementName] = []
        for attributeName in self._uniqueAttributes: uniqueDict["Attribute_"+attributeName] = []

        expectedID = 1
        for j,element in enumerate(self._XMLtree):
            if element.tag == self._mainElementTag:
                BibleOrgSysGlobals.checkXMLNoText( element, element.tag )
                BibleOrgSysGlobals.checkXMLNoTail( element, element.tag )
                if not self._compulsoryAttributes and not self._optionalAttributes: BibleOrgSysGlobals.checkXMLNoAttributes( element, element.tag )
                if not self._compulsoryElements and not self._optionalElements: BibleOrgSysGlobals.checkXMLNoSubelements( element, element.tag )

                # Check compulsory attributes on this main element
                for attributeName in self._compulsoryAttributes:
                    attributeValue = element.get( attributeName )
                    if attributeValue is None:
                        logging.error( _("Compulsory {!r} attribute is missing from {} element in record {}").format( attributeName, element.tag, j ) )
                    if not attributeValue:
                        logging.warning( _("Compulsory {!r} attribute is blank on {} element in record {}").format( attributeName, element.tag, j ) )

                # Check optional attributes on this main element
                for attributeName in self._optionalAttributes:
                    attributeValue = element.get( attributeName )
                    if attributeValue is not None:
                        if not attributeValue:
                            logging.warning( _("Optional {!r} attribute is blank on {} element in record {}").format( attributeName, element.tag, j ) )

                # Check for unexpected additional attributes on this main element
                for attributeName in element.keys():
                    attributeValue = element.get( attributeName )
                    if attributeName not in self._compulsoryAttributes and attributeName not in self._optionalAttributes:
                        logging.warning( _("Additional {!r} attribute ({!r}) found on {} element in record {}").format( attributeName, attributeValue, element.tag, j ) )

                # Check the attributes that must contain unique information (in that particular field -- doesn't check across different attributes)
                for attributeName in self._uniqueAttributes:
                    attributeValue = element.get( attributeName )
                    if attributeValue is not None:
                        if attributeValue in uniqueDict["Attribute_"+attributeName]:
                            logging.error( _("Found {!r} data repeated in {!r} field on {} element in record {}").format( attributeValue, attributeName, element.tag, j ) )
                        uniqueDict["Attribute_"+attributeName].append( attributeValue )

                # Get the marker to use as a record ID
                marker = element.find("marker").text

                # Check compulsory elements
                for elementName in self._compulsoryElements:
                    if element.find( elementName ) is None:
                        logging.error( _("Compulsory {!r} element is missing in record with marker {!r} (record {})").format( elementName, marker, j ) )
                    elif not element.find( elementName ).text:
                        logging.warning( _("Compulsory {!r} element is blank in record with marker {!r} (record {})").format( elementName, marker, j ) )

                # Check optional elements
                for elementName in self._optionalElements:
                    if element.find( elementName ) is not None:
                        if not element.find( elementName ).text:
                            logging.warning( _("Optional {!r} element is blank in record with marker {!r} (record {})").format( elementName, marker, j ) )

                # Check for unexpected additional elements
                for subelement in element:
                    if subelement.tag not in self._compulsoryElements and subelement.tag not in self._optionalElements:
                        logging.warning( _("Additional {!r} element ({!r}) found in record with marker {!r} (record {})").format( subelement.tag, subelement.text, marker, j ) )

                # Check the elements that must contain unique information (in that particular element -- doesn't check across different elements)
                for elementName in self._uniqueElements:
                    if element.find( elementName ) is not None:
                        text = element.find( elementName ).text
                        if text in uniqueDict["Element_"+elementName]:
                            logging.error( _("Found {!r} data repeated in {!r} element in record with marker {!r} (record {})").format( text, elementName, marker, j ) )
                        uniqueDict["Element_"+elementName].append( text )
            else:
                logging.warning( _("Unexpected element: {} in record {}").format( element.tag, j ) )
            if element.tail is not None and element.tail.strip(): logging.error( _("Unexpected {!r} tail data after {} element in record {}").format( element.tail, element.tag, j ) )
        if self._XMLtree.tail is not None and self._XMLtree.tail.strip(): logging.error( _("Unexpected {!r} tail data after {} element").format( self._XMLtree.tail, self._XMLtree.tag ) )
    # end of __validate

    def __str__( self ):
        """
        This method returns the string representation of a Bible book code.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        indent = 2
        result = "USFM2MarkersConverter object"
        if self.titleString: result += ('\n' if result else '') + ' '*indent + _("Title: {}").format( self.titleString )
        if self.programVersion: result += ('\n' if result else '') + ' '*indent + _("Version: {}").format( self.programVersion )
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
        assert self._XMLtree
        if self.__DataDicts: # We've already done an import/restructuring -- no need to repeat it
            return self.__DataDicts

        # Load and validate entries and create the dictionaries and lists
        # Note that the combined lists include the numbered markers, e.g., s as well as s1, s2, …
        rawMarkerDict, numberedMarkerList, combinedMarkerDict, = {}, [], {}
        conversionDict, backConversionDict = {}, {}
        newlineMarkersList, numberedNewlineMarkersList, combinedNewlineMarkersList = [], [], []
        internalMarkersList, numberedInternalMarkersList, combinedInternalMarkersList = [], [], []
        noteMarkersList, deprecatedMarkersList = [], []
        for element in self._XMLtree:
            # Get the required information out of the tree for this element
            # Start with the compulsory elements
            nameEnglish = element.find('nameEnglish').text # This name is really just a comment element
            marker = element.find('marker').text
            if marker.lower() != marker:
                logging.error( _("Marker {!r} should be lower case").format( marker ) )
            compulsory = element.find('compulsory').text
            if  compulsory not in ( 'Yes', 'No' ): logging.error( _("Unexpected {!r} compulsory field for marker {!r}").format( compulsory, marker ) )
            level = element.find('level').text
            compulsoryFlag = compulsory == 'Yes'
            if  level == 'Newline': newlineMarkersList.append( marker ); combinedNewlineMarkersList.append( marker )
            elif level == 'Internal': internalMarkersList.append( marker )
            elif level == 'Note': noteMarkersList.append( marker )
            else: logging.error( _("Unexpected {!r} level field for marker {!r}").format( level, marker ) )
            highestNumberSuffix = element.find('highestNumberSuffix').text
            if  highestNumberSuffix not in ( 'None', '3','4','5','6','7','8','9' ):
                logging.error( _("Unexpected {!r} highestNumberSuffix field for marker {!r}").format( highestNumberSuffix, marker ) )
            numberableFlag = highestNumberSuffix != 'None'
            if numberableFlag and level == 'Character':
                logging.error( _("Unexpected {!r} highestNumberSuffix field for character marker {!r}").format( highestNumberSuffix, marker ) )
            nests = element.find("nests").text
            if  nests not in ( 'Yes', 'No' ): logging.error( _("Unexpected {!r} nests field for marker {!r}").format( nests, marker ) )
            nestsFlag = nests == 'Yes'
            hasContent = element.find('hasContent').text
            if  hasContent not in ( 'Always', 'Never', 'Sometimes' ): logging.error( _("Unexpected {!r} hasContent field for marker {!r}").format( hasContent, marker ) )
            printed = element.find('printed').text
            if  printed not in ( 'Yes', 'No' ): logging.error( _("Unexpected {!r} printed field for marker {!r}").format( printed, marker ) )
            printedFlag = printed == 'Yes'
            closed = element.find('closed').text
            if  closed not in ( 'No', 'Always', 'Optional' ): logging.error( _("Unexpected {!r} closed field for marker {!r}").format( closed, marker ) )
            occursIn = element.find('occursIn').text
            if  occursIn not in ( 'Header', 'Introduction', 'Numbering', 'Text', 'Canonical Text', 'Poetry', 'Text, Poetry', 'Acrostic verse', 'Table row', 'Footnote', 'Cross-reference', 'Front and back matter' ):
                logging.error( _("Unexpected {!r} occursIn field for marker {!r}").format( occursIn, marker ) )
            deprecated = element.find('deprecated').text
            if  deprecated not in ( 'Yes', 'No' ): logging.error( _("Unexpected {!r} deprecated field for marker {!r}").format( deprecated, marker ) )
            deprecatedFlag = deprecated == 'Yes'

            # The optional elements are set to None if they don't exist
            #closed = None if element.find("closed") is None else element.find("closed").text
            #if closed is not None and closed not in ( "No", "Always", "Optional" ): logging.error( _("Unexpected {!r} closed field for marker {!r}").format( closed, marker ) )
            #if level=="Character" and closed is None: logging.error( _("Entry for character marker {!r} doesn't have a \"closed\" field").format( marker ) )
            description = None if element.find('description') is None else element.find('description').text
            if description is not None: assert description

            # Now put it into my dictionaries and lists for easy access
            #   The marker is lowercase by definition
            if 'marker' in self._uniqueElements: assert marker not in rawMarkerDict # Shouldn't be any duplicates
            rawMarkerDict[marker] = { 'compulsoryFlag':compulsoryFlag, 'level':level, 'highestNumberSuffix':highestNumberSuffix, 'nestsFlag':nestsFlag,
                                        'hasContent':hasContent, 'occursIn':occursIn, 'printedFlag':printedFlag, 'closed':closed, 'deprecatedFlag':deprecatedFlag,
                                        'description':description, 'nameEnglish':nameEnglish }
            combinedMarkerDict[marker] = marker
            if highestNumberSuffix != 'None': # We have some extra work to do
                conversionDict[marker] = marker + '1'
                for suffix in range(1,int(highestNumberSuffix)+1): # These are the suffix digits that we allow
                    numberedMarker = marker + str(suffix)
                    backConversionDict[numberedMarker] = marker
                    numberedMarkerList.append( numberedMarker )
                    combinedMarkerDict[numberedMarker] = marker
                    if marker in newlineMarkersList: numberedNewlineMarkersList.append( numberedMarker ); combinedNewlineMarkersList.append( numberedMarker )
                    else: numberedInternalMarkersList.append( numberedMarker ); combinedInternalMarkersList.append( numberedMarker )
                    if deprecatedFlag: deprecatedMarkersList.append( numberedMarker )
            else: # it's not numberable
                numberedMarkerList.append( marker )
                if marker in newlineMarkersList: numberedNewlineMarkersList.append( marker )
                else: numberedInternalMarkersList.append( marker )
                if deprecatedFlag: deprecatedMarkersList.append( marker )

        #print( conversionDict ); print( backConversionDict )
        #print( "newlineMarkersList", len(newlineMarkersList), newlineMarkersList )
        #print( "numberedNewlineMarkersList", len(numberedNewlineMarkersList), numberedNewlineMarkersList )
        #print( "combinedNewlineMarkersList", len(combinedNewlineMarkersList), combinedNewlineMarkersList )
        #print( "internalMarkersList", len(internalMarkersList), internalMarkersList )
        #print( "deprecatedMarkersList", len(deprecatedMarkersList), deprecatedMarkersList )
        self.__DataDicts = { "rawMarkerDict":rawMarkerDict, "numberedMarkerList":numberedMarkerList, "combinedMarkerDict":combinedMarkerDict,
                                "conversionDict":conversionDict, "backConversionDict":backConversionDict,
                                "newlineMarkersList":newlineMarkersList, "numberedNewlineMarkersList":numberedNewlineMarkersList, "combinedNewlineMarkersList":combinedNewlineMarkersList,
                                "internalMarkersList":internalMarkersList, "numberedInternalMarkersList":numberedInternalMarkersList, "combinedInternalMarkersList":combinedInternalMarkersList,
                                "noteMarkersList":noteMarkersList, "deprecatedMarkersList":deprecatedMarkersList, }
        return self.__DataDicts # Just delete any of the dictionaries that you don't need
    # end of importDataToPython

    def pickle( self, filepath=None ):
        """
        Writes the information tables to a .pickle file that can be easily loaded into a Python3 program.
        """
        import pickle

        assert self._XMLtree
        self.importDataToPython()
        assert self.__DataDicts

        if not filepath:
            folder = os.path.join( os.path.split(self.__XMLFilepath)[0], "DerivedFiles/" )
            if not os.path.exists( folder ): os.mkdir( folder )
            filepath = os.path.join( folder, self._filenameBase + "_Tables.pickle" )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Exporting to {}…").format( filepath ) )
        with open( filepath, 'wb' ) as myFile:
            pickle.dump( self.__DataDicts, myFile )
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
            theFile.write( "{} = {{\n  # Key is {}\n  # Fields ({}) are: {}\n".format( dictName, keyComment, fieldsCount, fieldsComment ) )
            for dictKey in sorted(theDict.keys()):
                theFile.write( '  {}: {},\n'.format( repr(dictKey), repr(theDict[dictKey]) ) )
            theFile.write( "}}\n# end of {} ({} entries)\n\n".format( dictName, len(theDict) ) )
        # end of exportPythonDict

        #def exportPythonOrderedDict( theFile, theDict, dictName, keyComment, fieldsComment ):
            #"""Exports theDict to theFile."""
            #assert isinstance( theDict, OrderedDict )
            #for dictKey in theDict.keys(): # Have to iterate this :(
                #fieldsCount = len( theDict[dictKey] ) if isinstance( theDict[dictKey], (tuple,dict,list) ) else 1
                #break # We only check the first (random) entry we get
            #theFile.write( '{} = OrderedDict([\n    # Key is {}\n    # Fields ({}) are: {}\n'.format( dictName, keyComment, fieldsCount, fieldsComment ) )
            #for dictKey in theDict.keys():
                #theFile.write( '  ({}, {}),\n'.format( repr(dictKey), repr(theDict[dictKey]) ) )
            #theFile.write( "]), # end of {} ({} entries)\n\n".format( dictName, len(theDict) ) )
        ## end of exportPythonOrderedDict

        def exportPythonList( theFile, theList, listName, dummy, fieldsComment ):
            """Exports theList to theFile."""
            assert isinstance( theList, list )
            fieldsCount = len( theList[0] ) if isinstance( theList[0], (tuple,dict,list) ) else 1
            theFile.write( '{} = [\n    # Fields ({}) are: {}\n'.format( listName, fieldsCount, fieldsComment ) )
            for j,entry in enumerate(theList):
                theFile.write( '  {}, # {}\n'.format( repr(entry), j ) )
            theFile.write( "], # end of {} ({} entries)\n\n".format( listName, len(theList) ) )
        # end of exportPythonList

        assert self._XMLtree
        self.importDataToPython()
        assert self.__DataDicts

        if not filepath: filepath = os.path.join( os.path.split(self.__XMLFilepath)[0], 'DerivedFiles/', self._filenameBase + "_Tables.py" )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Exporting to {}…").format( filepath ) )
        with open( filepath, 'wt', encoding='utf-8' ) as myFile:
            myFile.write( "# {}\n#\n".format( filepath ) )
            myFile.write( "# This UTF-8 file was automatically generated by USFM2Markers.py V{} on {}\n#\n".format( programVersion, datetime.now() ) )
            if self.titleString: myFile.write( "# {} data\n".format( self.titleString ) )
            if self.programVersion: myFile.write( "#  Version: {}\n".format( self.programVersion ) )
            if self.dateString: myFile.write( "#  Date: {}\n#\n".format( self.dateString ) )
            myFile.write( "#   {} {} loaded from the original XML file.\n#\n\n".format( len(self._XMLtree), self._treeTag ) )
            #myFile.write( "from collections import OrderedDict\n\n" )
            dictInfo = { "rawMarkerDict":(exportPythonDict, "rawMarker (in the original XML order)","specified"),
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
                            "noteMarkersList":(exportPythonList, "","rawMarker"),
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
        import json

        assert self._XMLtree
        self.importDataToPython()
        assert self.__DataDicts

        if not filepath: filepath = os.path.join( os.path.split(self.__XMLFilepath)[0], 'DerivedFiles/', self._filenameBase + "_Tables.json" )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Exporting to {}…").format( filepath ) )
        with open( filepath, 'wt', encoding='utf-8' ) as myFile:
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
                """ Convert special characters in an entry… """
                result = ""
                if isinstance( entry, tuple ):
                    for field in entry:
                        if result: result += ", " # Separate the fields
                        if field is None: result += '""'
                        elif isinstance( field, str): result += '"' + str(field).replace('"','\\"') + '"'
                        elif isinstance( field, int): result += str(field)
                        else: logging.error( _("Cannot convert unknown field type {!r} in entry {!r}").format( field, entry ) )
                elif isinstance( entry, dict ):
                    for key in sorted(entry.keys()):
                        field = entry[key]
                        if result: result += ", " # Separate the fields
                        if field is None: result += '""'
                        elif isinstance( field, str): result += '"' + str(field).replace('"','\\"') + '"'
                        elif isinstance( field, int): result += str(field)
                        else: logging.error( _("Cannot convert unknown field type {!r} in entry {!r}").format( field, entry ) )
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

        assert self._XMLtree
        self.importDataToPython()
        assert self.__DataDicts

        raise Exception( "C export not written yet, sorry." )
        if not filepath: filepath = os.path.join( os.path.split(self.__XMLFilepath)[0], 'DerivedFiles/', self._filenameBase + "_Tables" )
        hFilepath = filepath + '.h'
        cFilepath = filepath + '.c'
        if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Exporting to {}…").format( cFilepath ) ) # Don't bother telling them about the .h file
        ifdefName = self._filenameBase.upper() + "_Tables_h"

        with open( hFilepath, 'wt', encoding='utf-8' ) as myHFile, \
             open( cFilepath, 'wt', encoding='utf-8' ) as myCFile:
            myHFile.write( "// {}\n//\n".format( hFilepath ) )
            myCFile.write( "// {}\n//\n".format( cFilepath ) )
            lines = "// This UTF-8 file was automatically generated by USFM2Markers.py V{} on {}\n//\n".format( programVersion, datetime.now() )
            myHFile.write( lines ); myCFile.write( lines )
            if self.titleString:
                lines = "// {} data\n".format( self.titleString )
                myHFile.write( lines ); myCFile.write( lines )
            if self.programVersion:
                lines = "//  Version: {}\n".format( self.programVersion )
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
                "EnglishNameDict":("nameEnglish", "{}* nameEnglish; {} referenceNumber; {} marker[3+1];".format(CHAR,BYTE,CHAR) ) }

            for dictName,dictData in self.__DataDicts.items():
                exportPythonDict( myHFile, myCFile, dictData, dictName, dictInfo[dictName][0], dictInfo[dictName][1] )

            myHFile.write( "#endif // {}\n\n".format( ifdefName ) )
            myHFile.write( "// end of {}".format( os.path.basename(hFilepath) ) )
            myCFile.write( "// end of {}".format( os.path.basename(cFilepath) ) )
    # end of exportDataToC
# end of USFM2MarkersConverter class



def demo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel > 1: print( programNameVersion )

    if BibleOrgSysGlobals.commandLineArguments.export:
        umc = USFM2MarkersConverter().loadAndValidate() # Load the XML
        umc.pickle() # Produce a pickle output file
        umc.exportDataToPython() # Produce the .py tables
        umc.exportDataToJSON() # Produce a json output file
        umc.exportDataToC() # Produce the .h and .c tables

    else: # Must be demo mode
        # Demo the converter object
        umc = USFM2MarkersConverter().loadAndValidate() # Load the XML
        print( umc ) # Just print a summary
# end of demo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( programName, programVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    demo()

    BibleOrgSysGlobals.closedown( programName, programVersion )
# end of USFM2MarkersConverter.py
