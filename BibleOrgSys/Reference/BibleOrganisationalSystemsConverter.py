#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# BibleOrganisationalSystemsConverter.py
#
# Module handling BibleOrganisationalSystems.xml to produce C and Python data tables
#
# Copyright (C) 2010-2018 Robert Hunt
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
Module handling BibleOrganisationalSystems.xml to produce C and Python data tables.
"""

from gettext import gettext as _

lastModifiedDate = '2018-12-12' # by RJH
shortProgramName = "BibleOrganisationalSystemsConverter"
programName = "Bible Organisation Systems converter"
programVersion = '0.26'
programNameVersion = f'{programName} v{programVersion}'


import logging, os.path
from datetime import datetime
from xml.etree.ElementTree import ElementTree

if __name__ == '__main__':
    import sys
    sys.path.append( os.path.join(os.path.dirname(__file__), '../') ) # So we can run it from the above folder and still do these imports
from Misc.singleton import singleton
import BibleOrgSysGlobals
from Reference.ISO_639_3_Languages import ISO_639_3_Languages
from Reference.BibleBookOrders import BibleBookOrderSystems
from Reference.BiblePunctuationSystems import BiblePunctuationSystems
from Reference.BibleVersificationSystems import BibleVersificationSystems
from Reference.BibleBooksNames import BibleBooksNamesSystems


allowedTypes = ( 'edition', 'revision', 'translation', 'original', ) # NOTE: The order is important here



@singleton # Can only ever have one instance
class BibleOrganisationalSystemsConverter:
    """
    Class for handling and converting BibleOrganisationalSystems.
    """

    def __init__( self ):
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
        self.header, self._XMLtree = None, None
        self.__dataDicts = None

        # Get the data tables that we need for proper checking
        self._ISOLanguages = ISO_639_3_Languages().loadData()
        self._BibleBookOrderSystems = BibleBookOrderSystems().loadData()
        self._BiblePunctuationSystems = BiblePunctuationSystems().loadData()
        self._BibleVersificationSystems = BibleVersificationSystems().loadData()
        self._BibleBooksNamesSystems = BibleBooksNamesSystems().loadData()
    # end of BibleOrganisationalSystemsConverter.__init__


    def __str__( self ):
        """
        This method returns the string representation of a Bible book code.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = ""
        if self.title: result += ('\n' if result else '') + self.title
        if self.version: result += ('\n' if result else '') + "  Version: {}".format( self.version )
        if self.date: result += ('\n' if result else '') + "  Date: {}".format( self.date )
        result += ('\n' if result else '') + "  Number of entries = {}".format( len(self._XMLtree) )
        return result
    # end of BibleOrganisationalSystemsConverter.__str__


    def __len__( self ):
        """ Returns the number of items loaded. """
        return len( self._XMLtree )
    # end of BibleOrganisationalSystemsConverter.__len__


    def loadAndValidate( self, XMLFilepath=None ):
        """
        Loads (and crudely validates the XML file) into an element tree.
            Allows the filepath of the source XML file to be specified, otherwise uses the default.
        """
        if self._XMLtree is None: # We mustn't have already have loaded the data
            if XMLFilepath is None:
                XMLFilepath = BibleOrgSysGlobals.BOS_DATA_FILES_FOLDERPATH.joinpath( self._filenameBase + '.xml' ) # Relative to module, not cwd

            self._load( XMLFilepath )
            if BibleOrgSysGlobals.strictCheckingFlag:
                self._validate()
        return self
    # end of BibleOrganisationalSystemsConverter.loadAndValidate


    def _load( self, XMLFilepath ):
        """
        Load the source XML file and remove the header from the tree.
        Also, extracts some useful elements from the header element.
        """
        assert XMLFilepath
        self.__XMLFilepath = XMLFilepath
        assert self._XMLtree is None or len(self._XMLtree)==0 # Make sure we're not doing this twice

        if BibleOrgSysGlobals.verbosityLevel > 2: print( _("Loading BibleOrganisationalSystems XML file from {!r}…").format( self.__XMLFilepath ) )
        self._XMLtree = ElementTree().parse( self.__XMLFilepath )
        assert self._XMLtree # Fail here if we didn't load anything at all

        if self._XMLtree.tag  == self._treeTag:
            header = self._XMLtree[0]
            if header.tag == self._headerTag:
                self.header = header
                self._XMLtree.remove( header )
                if len(header)>1:
                    logging.info( _("Unexpected elements in header") )
                elif len(header)==0:
                    logging.info( _("Missing work element in header") )
                else:
                    work = header[0]
                    if work.tag == "work":
                        self.version = work.find('version').text
                        self.date = work.find("date").text
                        self.title = work.find("title").text
                    else:
                        logging.warning( _("Missing work element in header") )
            else:
                logging.warning( _("Missing header element (looking for {!r} tag)").format( self._headerTag ) )
        else:
            logging.error( _("Expected to load {!r} but got {!r}").format( self._treeTag, self._XMLtree.tag ) )
    # end of BibleOrganisationalSystemsConverter._load


    def _validate( self ):
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

                ID = element.find("referenceAbbreviation").text

                # Check compulsory elements
                for elementName in self._compulsoryElements:
                    if element.find( elementName ) is None:
                        logging.error( _("Compulsory {!r} element is missing in record with ID {!r} (record {})").format( elementName, ID, j ) )
                    elif not element.find( elementName ).text:
                        logging.warning( _("Compulsory {!r} element is blank in record with ID {!r} (record {})").format( elementName, ID, j ) )

                # Check optional elements
                for elementName in self._optionalElements:
                    if element.find( elementName ) is not None:
                        if not element.find( elementName ).text:
                            logging.warning( _("Optional {!r} element is blank in record with ID {!r} (record {})").format( elementName, ID, j ) )

                # Check for unexpected additional elements
                for subelement in element:
                    if subelement.tag not in self._compulsoryElements and subelement.tag not in self._optionalElements:
                        logging.warning( _("Additional {!r} element ({!r}) found in record with ID {!r} (record {})").format( subelement.tag, subelement.text, ID, j ) )

                # Check the elements that must contain unique information (in that particular element -- doesn't check across different elements)
                for elementName in self._uniqueElements:
                    if element.find( elementName ) is not None:
                        text = element.find( elementName ).text
                        if text in uniqueDict["Element_"+elementName]:
                            logging.error( _("Found {!r} data repeated in {!r} element in record with ID {!r} (record {})").format( text, elementName, ID, j ) )
                        uniqueDict["Element_"+elementName].append( text )

                # Special checks of particular fields
                if element.find('includesBooks') is not None:
                    bookList = element.find('includesBooks').text.split()
                    for BBB in bookList:
                        if not BibleOrgSysGlobals.BibleBooksCodes.isValidBBB( BBB ):
                            logging.critical( _("Unrecognized {!r} Bible book code found in 'includesBooks' in record with ID {!r} (record {})").format( BBB, ID, j) )
                        if bookList.count( BBB ) > 1:
                            logging.error( _("Multiple {!r} Bible book codes found in 'includesBooks' in record with ID {!r} (record {})").format( BBB, ID, j) )

            else:
                logging.warning( _("Unexpected element: {} in record {}").format( element.tag, j ) )
    # end of BibleOrganisationalSystemsConverter._validate


    def importDataToPython( self ):
        """
        Loads (and pivots) the data (not including the header) into suitable Python containers to use in a Python program.
        (Of course, you can just use the elementTree in self._XMLtree if you prefer.)
        """
        assert self._XMLtree
        if self.__dataDicts: # We've already done an import/restructuring -- no need to repeat it
            return self.__dataDicts

        # We'll create a number of dictionaries with different elements as the key
        dataDict, indexDict, combinedIndexDict = {}, {}, {}
        for element in self._XMLtree:
            bits = {}
            # Get the required information out of the tree for this element
            # Start with the compulsory elements and type attribute
            referenceAbbreviation = element.find('referenceAbbreviation').text
            bits['referenceAbbreviation'] = referenceAbbreviation
            myType = element.get( 'type' )
            bits['type'] = myType
            if myType not in allowedTypes: logging.error( _("Unrecognized {!r} type for {!r} (expected one of {})").format(myType,referenceAbbreviation,allowedTypes) )
            languageCode = element.find('languageCode').text
            if self._ISOLanguages and not self._ISOLanguages.isValidLanguageCode( languageCode ): # Check that we have a valid language code
                if languageCode != '???':
                    logging.error( "Unrecognized {!r} ISO-639-3 language code in {!r} organisational system".format( languageCode, referenceAbbreviation ) )
            bits['languageCode'] = languageCode

            # Now work on the optional elements
            for name in ( 'name', 'publicationDate', 'versificationSystem', 'punctuationSystem', 'bookOrderSystem', 'booksNamesSystem', 'derivedFrom', 'usesText', 'includesBooks' ):
                for nameData in element.findall(name):
                    if name in self._allowedMultiple: # Put multiple entries into a list
                        if name not in bits: bits[name] = [nameData.text]
                        else: bits[name].append( nameData.text )
                    else: # Not allowed multiples
                        if name in bits: logging.error( _("Unexpected multiple {} elements found in {} {}").format(name, referenceAbbreviation, myType) )
                        if name=='includesBooks': # special handling
                            bits['includesBooks'] = nameData.text.split()
                            for BBB in bits['includesBooks']:
                                if not BibleOrgSysGlobals.BibleBooksCodes.isValidBBB( BBB ):
                                    logging.error( _("Unrecognized {!r} Bible book code found in 'includesBooks' in {} {}").format( BBB, referenceAbbreviation, myType) )
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
                if extendedRA in combinedIndexDict: logging.error( _("Found {} in combinedIndexDict").format( extendedRA ) )
                combinedIndexDict[extendedRA] = [extendedRA]
        assert len(indexDict) <= len(dataDict)
        assert len(combinedIndexDict) >= len(indexDict)

        if BibleOrgSysGlobals.strictCheckingFlag: # We'll do quite a bit more cross-checking now
            for extendedReferenceAbbreviation,data in dataDict.items():
                #print( extendedReferenceAbbreviation, data )
                systemType = data['type']
                if systemType=='edition':
                    if 'derivedFrom' in data: logging.error( _("{} shouldn't use 'derivedFrom' {!r}").format( extendedReferenceAbbreviation, data['derivedFrom'] ) )
                    if 'usesText' not in data: logging.error( _("{} doesn't specify 'usesText'").format( extendedReferenceAbbreviation ) )
                    else: # have a 'usesText' list
                        for textAbbrev in data['usesText']:
                            if textAbbrev not in indexDict: logging.error( _("{} specifies unknown {!r} text in 'usesText' field").format(extendedReferenceAbbreviation,textAbbrev) )
                            elif len(indexDict[textAbbrev]) > 1: # it could be ambiguous
                                found = 0
                                for thisType in ('revision','translation','original'): # but not 'edition'
                                    usesTextExtended = textAbbrev + '_' + thisType
                                    if usesTextExtended in dataDict:
                                        foundOne = usesTextExtended
                                        found += 1
                                assert found > 0
                                if found==1: # ah, it's not actually ambiguous
                                    if BibleOrgSysGlobals.verbosityLevel > 2: print( _("Adjusted text used for {} from the ambiguous {!r} to the extended name {!r}").format( extendedReferenceAbbreviation, textAbbrev, foundOne ) )
                                    data['usesText'].remove( textAbbrev)
                                    data['usesText'].append( foundOne )
                                else: logging.warning( _("{} specifies ambiguous {!r} (could be {}) texts in 'usesText' field").format(extendedReferenceAbbreviation,textAbbrev,indexDict[textAbbrev]) )
                elif systemType=='revision':
                    if 'derivedFrom' not in data: logging.error( _("{} doesn't specify 'derivedFrom'").format( extendedReferenceAbbreviation ) )
                    else:
                        for df in data['derivedFrom']:
                            if df not in indexDict: logging.error( _("{} specifies unknown {!r} text in 'derivedFrom' field").format(extendedReferenceAbbreviation,df) )
                            elif len(indexDict[df]) > 1: logging.warning( _("{} specifies ambiguous {!r} (could be {}) texts in 'derivedFrom' field").format(extendedReferenceAbbreviation,df,indexDict[df]) )
                elif systemType=='translation':
                    if 'derivedFrom' not in data: logging.warning( _("{} doesn't specify 'derivedFrom'").format( extendedReferenceAbbreviation ) )
                    else:
                        for df in data['derivedFrom']:
                            if df not in indexDict: logging.error( _("{} specifies unknown {!r} text in 'derivedFrom' field").format(extendedReferenceAbbreviation,df) )
                            elif len(indexDict[df]) > 1: logging.warning( _("{} specifies ambiguous {!r} (could be {}) texts in 'derivedFrom' field").format(extendedReferenceAbbreviation,df,indexDict[df]) )
                elif systemType=='original':
                    if 'derivedFrom' in data: logging.error( _("{} shouldn't use 'derivedFrom' {!r}").format( extendedReferenceAbbreviation, data['derivedFrom'] ) )
                if 'versificationSystem' in data and data['versificationSystem'] not in ('None', 'Unknown'):
                    if not self._BibleVersificationSystems.isValidVersificationSystemName( data['versificationSystem'] ):
                        extra = "\n  Available systems are {}".format( self._BibleVersificationSystems.getAvailableVersificationSystemNames()) if BibleOrgSysGlobals.verbosityLevel > 2 else ''
                        logging.error( _("Unknown {!r} versification system name in {}{}").format(data['versificationSystem'],extendedReferenceAbbreviation,extra) )
                if 'punctuationSystem' in data and data['punctuationSystem'] not in ('None', 'Unknown'):
                    if not self._BiblePunctuationSystems.isValidPunctuationSystemName( data['punctuationSystem'] ):
                        extra = "\n  Available systems are {}".format( self._BiblePunctuationSystems.getAvailablePunctuationSystemNames()) if BibleOrgSysGlobals.verbosityLevel > 2 else ''
                        logging.error( _("Unknown {!r} punctuation system name in {}{}").format(data['punctuationSystem'],extendedReferenceAbbreviation,extra) )

        self.__dataDicts = dataDict, indexDict, combinedIndexDict
        return self.__dataDicts
    # end of importDataToPython


    def pickle( self, filepath=None ):
        """
        Writes the information tables to a .pickle file that can be easily loaded into a Python3 program.
        """
        import pickle

        assert self._XMLtree
        self.importDataToPython()
        assert self.__dataDicts

        if not filepath:
            folder = os.path.join( os.path.split(self.__XMLFilepath)[0], "DerivedFiles/" )
            if not os.path.exists( folder ): os.mkdir( folder )
            filepath = os.path.join( folder, self._filenameBase + "_Tables.pickle" )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Exporting to {}…").format( filepath ) )
        with open( filepath, 'wb' ) as myFile:
            pickle.dump( self.__dataDicts, myFile )
    # end of pickle


    def exportDataToPython( self, filepath=None ):
        """
        Writes the information tables to a .py file that can be cut and pasted into a Python program.
        """
        def exportPythonDict( theFile, theDict, dictName, keyComment, fieldsComment ):
            """Exports theDict to theFile."""
            theFile.write( "{} = {{\n  # Key is {}\n  # Fields are: {}\n".format( dictName, keyComment, fieldsComment ) )
            for dictKey in sorted(theDict.keys()):
                theFile.write( '  {}: {},\n'.format( repr(dictKey), theDict[dictKey] ) )
            theFile.write( "}}\n# end of {}\n\n".format( dictName ) )
        # end of exportPythonDict


        assert self._XMLtree
        self.importDataToPython()
        assert self.__dataDicts

        if not filepath: filepath = os.path.join( os.path.split(self.__XMLFilepath)[0], 'DerivedFiles/', self._filenameBase + "_Tables.py" )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Exporting to {}…").format( filepath ) )

        dataDict, indexDict, combinedIndexDict = self.importDataToPython()
        with open( filepath, 'wt', encoding='utf-8' ) as myFile:
            myFile.write( "# {}\n#\n".format( filepath ) )
            myFile.write( "# This UTF-8 file was automatically generated by BibleOrganisationalSystemsConverter.py V{} on {}\n#\n".format( programVersion, datetime.now() ) )
            if self.title: myFile.write( "# {}\n".format( self.title ) )
            if self.version: myFile.write( "#  Version: {}\n".format( self.version ) )
            if self.date: myFile.write( "#  Date: {}\n#\n".format( self.date ) )
            myFile.write( "#   {} {} entries loaded from the original XML file.\n".format( len(self._XMLtree), self._treeTag ) )
            #myFile.write( "#   {} {} loaded from the original XML files.\n#\n\n".format( len(self.systems), self._treeTag ) )
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

        assert self._XMLtree
        self.importDataToPython()
        assert self.__dataDicts

        if not filepath: filepath = os.path.join( os.path.split(self.__XMLFilepath)[0], 'DerivedFiles/', self._filenameBase + "_Tables.json" )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Exporting to {}…").format( filepath ) )
        with open( filepath, 'wt', encoding='utf-8' ) as myFile:
            #myFile.write( "# {}\n#\n".format( filepath ) ) # Not sure yet if these comment fields are allowed in JSON
            #myFile.write( "# This UTF-8 file was automatically generated by BibleBooksCodes.py V{} on {}\n#\n".format( programVersion, datetime.now() ) )
            #if self.titleString: myFile.write( "# {} data\n".format( self.titleString ) )
            #if self.programVersion: myFile.write( "#  Version: {}\n".format( self.programVersion ) )
            #if self.dateString: myFile.write( "#  Date: {}\n#\n".format( self.dateString ) )
            #myFile.write( "#   {} {} loaded from the original XML file.\n#\n\n".format( len(self._XMLtree), self._treeTag ) )
            json.dump( self.__dataDicts, myFile, indent=2 )
            #myFile.write( "\n\n# end of {}".format( os.path.basename(filepath) ) )
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
                    else: logging.error( _("Cannot convert unknown field type {!r} in entry {!r}").format( field, entry ) )
                return result

            theFile.write( "static struct {} {}[] = {\n  // Fields are {}\n".format( structName, dictName, fieldsComment ) )
            for entry in sorted(theDict.keys()):
                if isinstance( entry, str ):
                    theFile.write( "  {\"{}\", {}},\n".format( entry, convertEntry(theDict[entry]) ) )
                elif isinstance( entry, int ):
                    theFile.write( "  {{}, {}},\n".format( entry, convertEntry(theDict[entry]) ) )
                else:
                    logging.error( _("Can't handle this type of data yet: {}").format( entry ) )
            theFile.write( "}; // {}\n\n".format( dictName) )
        # end of exportPythonDict


        assert self._XMLtree
        self.importDataToPython()
        assert self.__dataDicts

        if not filepath: filepath = os.path.join( os.path.split(self.__XMLFilepath)[0], 'DerivedFiles/', self._filenameBase + "_Tables.h" )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Exporting to {}…").format( filepath ) )

        dataDict, indexDict, combinedIndexDict = self.importDataToPython()
        ifdefName = self._filenameBase.upper() + "_Tables_h"
        with open( filepath, 'wt', encoding='utf-8' ) as myFile:
            myFile.write( "// {}\n//\n".format( filepath ) )
            myFile.write( "// This UTF-8 file was automatically generated by BibleOrganisationalSystemsConverter.py V{} on {}\n//\n".format( programVersion, datetime.now() ) )
            if self.title: myFile.write( "// {}\n".format( self.title ) )
            if self.version: myFile.write( "//  Version: {}\n".format( self.version ) )
            if self.date: myFile.write( "//  Date: {}\n//\n".format( self.date ) )
            myFile.write( "//   {} {} loaded from the original XML file.\n//\n\n".format( len(self._XMLtree), self._treeTag ) )
            myFile.write( "#ifndef {}\n#define {}\n\n".format( ifdefName, ifdefName ) )
            exportPythonDict( myFile, IDDict, "IDDict", "{int id; char* refAbbrev; char* SBLAbbrev; char* OSISAbbrev; char* PTAbbrev; char* PTNum; char* EngName;}", "id (sorted), referenceAbbreviation, SBLAbbreviation, OSISAbbreviation, ParatextAbbreviation, ParatextNumberString, nameEnglish (comment only)" )
            exportPythonDict( myFile, RADict, "RADict", "{char* refAbbrev; int id; char* SBLAbbrev; char* OSISAbbrev; char* PTAbbrev; char* PTNum; char* EngName;}", "referenceAbbreviation (sorted), SBLAbbreviation, OSISAbbreviation, ParatextAbbreviation, ParatextNumberString, id, nameEnglish (comment only)" )
            exportPythonDict( myFile, SBLDict, "SBLDict", "{char* SBLAbbrev; int id; char* refAbbrev; char* OSISAbbrev; char* PTAbbrev; char* PTNum; char* EngName;}", "SBLAbbreviation (sorted), ReferenceAbbreviation, OSISAbbreviation, ParatextAbbreviation, ParatextNumberString, id, nameEnglish (comment only)" )
            exportPythonDict( myFile, OADict, "OADict", "{char* OSISAbbrev; int id; char* refAbbrev; char* SBLAbbrev; char* PTAbbrev; char* PTNum; char* EngName;}", "OSISAbbreviation (sorted), ReferenceAbbreviation, SBLAbbreviation, ParatextAbbreviation, ParatextNumberString, id, nameEnglish (comment only)" )
            exportPythonDict( myFile, PADict, "PADict", "{char* PTAbbrev; int id; char* refAbbrev; char* SBLAbbrev; char* OSISAbbrev; char* PTNum; char* EngName;}", "ParatextAbbreviation (sorted), referenceAbbreviation, SBLAbbreviation, OSISAbbreviation, ParatextNumberString, id, nameEnglish (comment only)" )
            exportPythonDict( myFile, PNDict, "PNDict", "{char* PTNum; int id; char* PTAbbrev; char* refAbbrev; char* SBLAbbrev; char* OSISAbbrev; char* EngName;}", "ParatextNumberString (sorted), ParatextAbbreviation, referenceAbbreviation, SBLAbbreviation, OSISAbbreviation, id, nameEnglish (comment only)" )
            myFile.write( "#endif // {}\n".format( ifdefName ) )
    # end of exportDataToC
# end of BibleOrganisationalSystemsConverter class



def demo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel > 1: print( programNameVersion )

    if BibleOrgSysGlobals.commandLineArguments.export:
        bosc = BibleOrganisationalSystemsConverter().loadAndValidate()
        bosc.pickle() # Produce a pickle output file
        bosc.exportDataToPython() # Produce the .py tables
        bosc.exportDataToJSON() # Produce a json output file
        bosc.exportDataToC() # Produce the .h and .c tables

    else: # Must be demo mode
        # Demo the converter object
        bosc = BibleOrganisationalSystemsConverter().loadAndValidate()
        if BibleOrgSysGlobals.verbosityLevel > 1:
            print( bosc ) # Just print a summary
# end of demo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( programName, programVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    demo()

    BibleOrgSysGlobals.closedown( programName, programVersion )
# end of BibleOrganisationalSystemsConverter.py
