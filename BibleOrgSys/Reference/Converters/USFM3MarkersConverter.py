#!/usr/bin/env -S uv run
# -\*- coding: utf-8 -\*-
# SPDX-License-Identifier: GPL-3.0-or-later
#
# USFM3MarkersConverter.py
#
# Module handling USFM3Markers.xml to produce C and Python data tables
#
# Copyright (C) 2011-2021 Robert Hunt
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
Module handling USFM3Markers.xml and to export to JSON, C, and Python data tables.
"""

import logging
import os.path
from datetime import datetime
from xml.etree.ElementTree import ElementTree

from BibleOrgSys.Misc.singleton import singleton
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import vPrint


LAST_MODIFIED_DATE = '2023-10-12' # by RJH
SHORT_PROGRAM_NAME = "USFM3MarkersConverter"
PROGRAM_NAME = "USFM3 Markers converter"
PROGRAM_VERSION = '0.07'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False



@singleton # Can only ever have one instance
class USFM3MarkersConverter:
    """
    Class for reading, validating, and converting USFM3Markers.
    This is only intended as a transitory class (used at start-up).
    The USFM3Markers class has functions more generally useful.
    """

    def __init__( self ) -> None: # We can't give this parameters because of the singleton
        """
        Constructor: expects the filepath of the source XML file.
        Loads (and crudely validates the XML file) into an element tree.
        """
        self._filenameBase = 'USFM3Markers'

        # These fields are used for parsing the XML
        self._treeTag = 'USFM3Markers'
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
        self._XMLheader, self._XMLTree = None, None
        self.__DataDicts = {} # Used for import
        self.titleString = self.PROGRAM_VERSION = self.dateString = ''
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

            self.__load( XMLFileOrFilepath )
            if BibleOrgSysGlobals.strictCheckingFlag:
                self.__validate()
        else: # The data must have been already loaded
            if XMLFileOrFilepath is not None and XMLFileOrFilepath!=self.__XMLFileOrFilepath: logging.error( f"Bible books codes are already loaded -- your different filepath of {XMLFileOrFilepath!r} was ignored" )
        return self
    # end of loadAndValidate

    def __load( self, XMLFileOrFilepath ):
        """
        Load the source XML file and remove the header from the tree.
        Also, extracts some useful elements from the header element.
        """
        assert XMLFileOrFilepath
        self.__XMLFileOrFilepath = XMLFileOrFilepath
        assert self._XMLTree is None or len(self._XMLTree)==0 # Make sure we're not doing this twice

        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"Loading USFM3Markers XML file from {self.__XMLFileOrFilepath!r}…" )
        self._XMLTree = ElementTree().parse( self.__XMLFileOrFilepath )
        assert len(self._XMLTree) # Fail here if we didn't load anything at all

        if self._XMLTree.tag == self._treeTag:
            header = self._XMLTree[0]
            if header.tag == self._headerTag:
                self.XMLheader = header
                self._XMLTree.remove( header )
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
                        self.PROGRAM_VERSION = work.find('version').text
                        self.dateString = work.find('date').text
                        self.titleString = work.find('title').text
                    else:
                        logging.warning( "Missing work element in header" )
            else:
                logging.warning( _(f"Missing header element (looking for {self._headerTag!r} tag)" ) )
            if header.tail is not None and header.tail.strip(): logging.error( f"Unexpected {element.tail!r} tail data after header" )
        else:
            logging.error( f"Expected to load {self._treeTag!r} but got {self._XMLTree.tag!r}" )
    # end of __load

    def __validate( self ):
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
                BibleOrgSysGlobals.checkXMLNoText( element, element.tag )
                BibleOrgSysGlobals.checkXMLNoTail( element, element.tag )
                if not self._compulsoryAttributes and not self._optionalAttributes: BibleOrgSysGlobals.checkXMLNoAttributes( element, element.tag )
                if not self._compulsoryElements and not self._optionalElements: BibleOrgSysGlobals.checkXMLNoSubelements( element, element.tag )

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

                # Get the marker to use as a record ID
                marker = element.find("marker").text

                # Check compulsory elements
                for elementName in self._compulsoryElements:
                    if element.find( elementName ) is None:
                        logging.error( f"Compulsory {marker!r} element is missing in record with marker {j!r} (record {elementName})" )
                    elif not element.find( elementName ).text:
                        logging.warning( f"Compulsory {marker!r} element is blank in record with marker {j!r} (record {elementName})" )

                # Check optional elements
                for elementName in self._optionalElements:
                    if element.find( elementName ) is not None:
                        if not element.find( elementName ).text:
                            logging.warning( f"Optional {marker!r} element is blank in record with marker {j!r} (record {elementName})" )

                # Check for unexpected additional elements
                for subelement in element:
                    if subelement.tag not in self._compulsoryElements and subelement.tag not in self._optionalElements:
                        logging.warning( f"Additional {subelement.text!r} element ({marker!r}) found in record with marker {j!r} (record {subelement.tag})" )

                # Check the elements that must contain unique information (in that particular element -- doesn't check across different elements)
                for elementName in self._uniqueElements:
                    if element.find( elementName ) is not None:
                        text = element.find( elementName ).text
                        if text in uniqueDict["Element_"+elementName]:
                            logging.error( f"Found {elementName!r} data repeated in {marker!r} element in record with marker {j!r} (record {text})" )
                        uniqueDict["Element_"+elementName].append( text )
            else:
                logging.warning( f"Unexpected element: {element.tag} in record {j}" )
            if element.tail is not None and element.tail.strip(): logging.error( f"Unexpected {j!r} tail data after {element.tail} element in record {element.tag}" )
        if self._XMLTree.tail is not None and self._XMLTree.tail.strip(): logging.error( f"Unexpected {self._XMLTree.tag!r} tail data after {self._XMLTree.tail} element" )
    # end of __validate

    def __str__( self ) -> str:
        """
        This method returns the string representation of a Bible book code.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        indent = 2
        result = "USFM3MarkersConverter object"
        if self.titleString: result += ('\n' if result else '') + ' '*indent + f"Title: {self.titleString}"
        if self.PROGRAM_VERSION: result += ('\n' if result else '') + ' '*indent + f"Version: {self.PROGRAM_VERSION}"
        if self.dateString: result += ('\n' if result else '') + ' '*indent + f"Date: {self.dateString}"
        if self._XMLTree is not None: result += ('\n' if result else '') + ' '*indent + f"Number of entries = {len(self._XMLTree):,}"
        return result
    # end of __str__

    def __len__( self ):
        """ Returns the number of SFM markers loaded. """
        return len( self._XMLTree )
    # end of __len__

    def importDataToPython( self ):
        """
        Loads (and pivots) the data (not including the header) into suitable Python containers to use in a Python program.
        (Of course, you can just use the elementTree in self._XMLTree if you prefer.)
        """
        assert len(self._XMLTree)
        if len(self.__DataDicts): # We've already done an import/restructuring -- no need to repeat it
            return self.__DataDicts

        # Load and validate entries and create the dictionaries and lists
        # Note that the combined lists include the numbered markers, e.g., s as well as s1, s2, …
        rawMarkerDict, numberedMarkerList, combinedMarkerDict, = {}, [], {}
        conversionDict, backConversionDict = {}, {}
        newlineMarkersList, numberedNewlineMarkersList, combinedNewlineMarkersList = [], [], []
        internalMarkersList, numberedInternalMarkersList, combinedInternalMarkersList = [], [], []
        noteMarkersList, deprecatedMarkersList = [], []
        for element in self._XMLTree:
            # Get the required information out of the tree for this element
            # Start with the compulsory elements
            nameEnglish = element.find('nameEnglish').text # This name is really just a comment element
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Processing", nameEnglish )
            marker = element.find('marker').text
            if marker.lower() != marker:
                logging.error( f"Marker {marker!r} should be lower case" )
            compulsory = element.find('compulsory').text
            if  compulsory not in ( 'Yes', 'No' ): logging.error( f"Unexpected {compulsory!r} compulsory field for marker {marker!r}" )
            level = element.find('level').text
            compulsoryFlag = compulsory == 'Yes'
            if  level == 'Newline': newlineMarkersList.append( marker ); combinedNewlineMarkersList.append( marker )
            elif level == 'Internal': internalMarkersList.append( marker )
            elif level == 'Note': noteMarkersList.append( marker )
            else: logging.error( f"Unexpected {level!r} level field for marker {marker!r}" )
            highestNumberSuffix = element.find('highestNumberSuffix').text
            if  highestNumberSuffix not in ( 'None', '2','3','4','5','6','7','8','9' ):
                logging.error( f"Unexpected {highestNumberSuffix!r} highestNumberSuffix field for marker {marker!r}" )
            numberableFlag = highestNumberSuffix != 'None'
            if numberableFlag and level == 'Character':
                logging.error( f"Unexpected {highestNumberSuffix!r} highestNumberSuffix field for character marker {marker!r}" )
            nests = element.find("nests").text
            if  nests not in ( 'Yes', 'No' ): logging.error( f"Unexpected {nests!r} nests field for marker {marker!r}" )
            nestsFlag = nests == 'Yes'
            hasContent = element.find('hasContent').text
            if  hasContent not in ( 'Always', 'Never', 'Sometimes' ): logging.error( f"Unexpected {hasContent!r} hasContent field for marker {marker!r}" )
            printed = element.find('printed').text
            if  printed not in ( 'Yes', 'No' ): logging.error( f"Unexpected {printed!r} printed field for marker {marker!r}" )
            printedFlag = printed == 'Yes'
            closed = element.find('closed').text
            if  closed not in ( 'No', 'Always', 'Self', 'Optional' ): logging.error( f"Unexpected {closed!r} closed field for marker {marker!r}" )
            occursIn = element.find('occursIn').text
            if  occursIn not in ( 'Header', 'Introduction', 'Numbering', 'Text', 'Canonical Text', 'Poetry', 'Text, Poetry', 'Acrostic verse', 'Table row', 'Footnote', 'Cross-reference', 'Front and back matter' ):
                logging.error( f"Unexpected {occursIn!r} occursIn field for marker {marker!r}" )
            deprecated = element.find('deprecated').text
            if  deprecated not in ( 'Yes', 'No' ): logging.error( f"Unexpected {deprecated!r} deprecated field for marker {marker!r}" )
            deprecatedFlag = deprecated == 'Yes'

            # The optional elements are set to None if they don't exist
            #closed = None if element.find("closed") is None else element.find("closed").text
            #if closed is not None and closed not in ( "No", "Always", "Optional" ): logging.error( f"Unexpected {closed!r} closed field for marker {marker!r}" )
            #if level=="Character" and closed is None: logging.error( f"Entry for character marker {marker!r} doesn't have a \"closed\" field" )
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
                if marker.endswith('-s') or marker.endswith('-e'):
                    assert marker in ('qt-s','qt-e') # Only ones we know of so far
                    # Numberical suffix can't just be appended to the end of these
                    conversionDict[marker] = f'{marker[:-2]}1{marker[-2:]}'
                else: # not a milestone start/end marker
                    conversionDict[marker] = marker + '1'
                for suffix in range(1,int(highestNumberSuffix)+1): # These are the suffix digits that we allow
                    if marker.endswith('-s') or marker.endswith('-e'):
                        # Numberical suffix can't just be appended to the end of these
                        numberedMarker = f'{marker[:-2]}{suffix}{marker[-2:]}'
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Marker '{marker}' led to '{numberedMarker}'" )
                    else: # not a milestone start/end marker
                        numberedMarker = marker + str(suffix)
                    backConversionDict[numberedMarker] = marker
                    numberedMarkerList.append( numberedMarker )
                    combinedMarkerDict[numberedMarker] = marker
                    if marker in newlineMarkersList:
                        numberedNewlineMarkersList.append( numberedMarker )
                        combinedNewlineMarkersList.append( numberedMarker )
                    else:
                        numberedInternalMarkersList.append( numberedMarker )
                        combinedInternalMarkersList.append( numberedMarker )
                    if deprecatedFlag:
                        deprecatedMarkersList.append( numberedMarker )
            else: # it's not numberable
                numberedMarkerList.append( marker )
                if marker in newlineMarkersList: numberedNewlineMarkersList.append( marker )
                else: numberedInternalMarkersList.append( marker )
                if deprecatedFlag: deprecatedMarkersList.append( marker )

        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, conversionDict ); vPrint( 'Quiet', DEBUGGING_THIS_MODULE, backConversionDict )
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "newlineMarkersList", len(newlineMarkersList), newlineMarkersList )
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "numberedNewlineMarkersList", len(numberedNewlineMarkersList), numberedNewlineMarkersList )
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "combinedNewlineMarkersList", len(combinedNewlineMarkersList), combinedNewlineMarkersList )
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "internalMarkersList", len(internalMarkersList), internalMarkersList )
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "deprecatedMarkersList", len(deprecatedMarkersList), deprecatedMarkersList )
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

        assert len(self._XMLTree)
        self.importDataToPython()
        assert len(self.__DataDicts)

        if not filepath:
            folder = BibleOrgSysGlobals.DEFAULT_WRITEABLE_DERIVED_DATAFILES_FOLDERPATH
            if not os.path.exists( folder ): os.mkdir( folder )
            filepath = os.path.join( folder, self._filenameBase + '_Tables.pickle' )
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
            assert isinstance( theDict, dict )
            for dictKey in theDict.keys(): # Have to iterate this :(
                fieldsCount = len( theDict[dictKey] ) if isinstance( theDict[dictKey], (tuple,dict,list) ) else 1
                break # We only check the first (random) entry we get
            theFile.write( f"{dictName} = {{\n  # Key is {keyComment}\n  # Fields ({fieldsCount}) are: {fieldsComment}\n" )
            for dictKey in sorted(theDict.keys()):
                theFile.write( f'  {repr(dictKey)}: {repr(theDict[dictKey])},\n' )
            theFile.write( f"}}\n# end of {dictName} ({len(theDict)} entries)\n\n" )
        # end of exportPythonDict

        #def exportPythonOrderedDict( theFile, theDict, dictName, keyComment, fieldsComment ):
            #"""Exports theDict to theFile."""
            #assert isinstance( theDict, OrderedDict )
            #for dictKey in theDict.keys(): # Have to iterate this :(
                #fieldsCount = len( theDict[dictKey] ) if isinstance( theDict[dictKey], (tuple,dict,list) ) else 1
                #break # We only check the first (random) entry we get
            #theFile.write( f'{dictName} = OrderedDict([\n    # Key is {keyComment}\n    # Fields ({fieldsCount}) are: {fieldsComment}\n' )
            #for dictKey in theDict.keys():
                #theFile.write( f'  ({repr(dictKey)}, {repr(theDict[dictKey])}),\n' )
            #theFile.write( f"]), # end of {dictName} ({len(theDict)} entries)\n\n" )
        ## end of exportPythonOrderedDict

        def exportPythonList( theFile, theList, listName, dummy, fieldsComment ):
            """Exports theList to theFile."""
            assert isinstance( theList, list )
            fieldsCount = len( theList[0] ) if isinstance( theList[0], (tuple,dict,list) ) else 1
            theFile.write( f'{listName} = [\n    # Fields ({fieldsCount}) are: {fieldsComment}\n' )
            for j,entry in enumerate(theList):
                theFile.write( f'  {repr(entry)}, # {j}\n' )
            theFile.write( f"], # end of {listName} ({len(theList)} entries)\n\n" )
        # end of exportPythonList

        assert len(self._XMLTree)
        self.importDataToPython()
        assert len(self.__DataDicts)

        if not filepath: filepath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_DERIVED_DATAFILES_FOLDERPATH.joinpath( self._filenameBase + '_Tables.py' )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Exporting to {filepath}…" )
        with open( filepath, 'wt', encoding='utf-8' ) as myFile:
            myFile.write( f"# {filepath}\n#\n" )
            myFile.write( f"# This UTF-8 file was automatically generated by USFM3Markers.py V{PROGRAM_VERSION} on {datetime.now()}\n#\n" )
            if self.titleString: myFile.write( f"# {self.titleString} data\n" )
            if self.PROGRAM_VERSION: myFile.write( f"#  Version: {self.PROGRAM_VERSION}\n" )
            if self.dateString: myFile.write( f"#  Date: {self.dateString}\n#\n" )
            myFile.write( f"#   {len(self._XMLTree)} {self._treeTag} loaded from the original XML file.\n#\n\n" )
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

        if not filepath: filepath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_DERIVED_DATAFILES_FOLDERPATH.joinpath( self._filenameBase + '_Tables.json' )
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
                    for field in entry:
                        if result: result += ", " # Separate the fields
                        if field is None: result += '""'
                        elif isinstance( field, str): result += '"' + str(field).replace('"','\\"') + '"'
                        elif isinstance( field, int): result += str(field)
                        else: logging.error( f"Cannot convert unknown field type {field!r} in entry {entry!r}" )
                elif isinstance( entry, dict ):
                    for key in sorted(entry.keys()):
                        field = entry[key]
                        if result: result += ", " # Separate the fields
                        if field is None: result += '""'
                        elif isinstance( field, str): result += '"' + str(field).replace('"','\\"') + '"'
                        elif isinstance( field, int): result += str(field)
                        else: logging.error( f"Cannot convert unknown field type {field!r} in entry {entry!r}" )
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
            cFile.write( f"]}}; // {dictName} ({len(theDict)} entries)\n\n" )
        # end of exportPythonDict

        assert len(self._XMLTree)
        self.importDataToPython()
        assert len(self.__DataDicts)

        raise Exception( "C export not written yet, sorry." )
        if not filepath: filepath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_DERIVED_DATAFILES_FOLDERPATH.joinpath( self._filenameBase + '_Tables' )
        hFilepath = filepath + '.h'
        cFilepath = filepath + '.c'
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Exporting to {cFilepath}…" ) # Don't bother telling them about the .h file
        ifdefName = self._filenameBase.upper() + "_Tables_h"

        with open( hFilepath, 'wt', encoding='utf-8' ) as myHFile, \
             open( cFilepath, 'wt', encoding='utf-8' ) as myCFile:
            myHFile.write( f"// {hFilepath}\n//\n" )
            myCFile.write( f"// {cFilepath}\n//\n" )
            lines = f"// This UTF-8 file was automatically generated by USFM3Markers.py V{PROGRAM_VERSION} on {datetime.now()}\n//\n"
            myHFile.write( lines ); myCFile.write( lines )
            if self.titleString:
                lines = f"// {self.titleString} data\n"
                myHFile.write( lines ); myCFile.write( lines )
            if self.PROGRAM_VERSION:
                lines = f"//  Version: {self.PROGRAM_VERSION}\n"
                myHFile.write( lines ); myCFile.write( lines )
            if self.dateString:
                lines = f"//  Date: {self.dateString}\n//\n"
                myHFile.write( lines ); myCFile.write( lines )
            myCFile.write( f"//   {len(self._XMLTree)} {self._treeTag} loaded from the original XML file.\n//\n\n" )
            myHFile.write( f"\n#ifndef {ifdefName}\n#define {ifdefName}\n\n" )
            myCFile.write( f'#include "{os.path.basename(hFilepath)}"\n\n' )

            CHAR = "const unsigned char"
            BYTE = "const int"
            dictInfo = {
                "referenceNumberDict":("referenceNumber (integer 1..255)",
                    f"{BYTE} referenceNumber; {CHAR}* ByzantineAbbreviation; {CHAR}* CCELNumberString; {CHAR}* NETBibleAbbreviation; {CHAR}* OSISAbbreviation; {CHAR} ParatextAbbreviation[3+1]; {CHAR} ParatextNumberString[2+1]; {CHAR}* SBLAbbreviation; {CHAR}* SwordAbbreviation; {CHAR}* nameEnglish; {CHAR}* numExpectedChapters; {CHAR}* possibleAlternativeBooks; {CHAR} marker[3+1];" ),
                "rawMarkerDict":("marker",
                    f"{CHAR} marker[3+1]; {CHAR}* ByzantineAbbreviation; {CHAR}* CCELNumberString; {BYTE} referenceNumber; {CHAR}* NETBibleAbbreviation; {CHAR}* OSISAbbreviation; {CHAR} ParatextAbbreviation[3+1]; {CHAR} ParatextNumberString[2+1]; {CHAR}* SBLAbbreviation; {CHAR}* SwordAbbreviation; {CHAR}* nameEnglish; {CHAR}* numExpectedChapters; {CHAR}* possibleAlternativeBooks;" ),
                "CCELDict":("CCELNumberString", f"{CHAR}* CCELNumberString; {BYTE} referenceNumber; {CHAR} marker[3+1];" ),
                "SBLDict":("SBLAbbreviation", f"{CHAR}* SBLAbbreviation; {BYTE} referenceNumber; {CHAR} marker[3+1];" ),
                "EnglishNameDict":("nameEnglish", f"{CHAR}* nameEnglish; {BYTE} referenceNumber; {CHAR} marker[3+1];" ) }

            for dictName,dictData in self.__DataDicts.items():
                exportPythonDict( myHFile, myCFile, dictData, dictName, dictInfo[dictName][0], dictInfo[dictName][1] )

            myHFile.write( f"#endif // {ifdefName}\n\n" )
            myHFile.write( f"// end of {os.path.basename(hFilepath)}" )
            myCFile.write( f"// end of {os.path.basename(cFilepath)}" )
    # end of exportDataToC
# end of USFM3MarkersConverter class



def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    if BibleOrgSysGlobals.commandLineArguments.export:
        umc = USFM3MarkersConverter().loadAndValidate() # Load the XML
        umc.pickle() # Produce a pickle output file
        umc.exportDataToPython() # Produce the .py tables
        umc.exportDataToJSON() # Produce a json output file
        # umc.exportDataToC() # Produce the .h and .c tables

    else: # Must be demo mode
        # Demo the converter object
        umc = USFM3MarkersConverter().loadAndValidate() # Load the XML
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, umc ) # Just print a summary
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

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of USFM3MarkersConverter.py
