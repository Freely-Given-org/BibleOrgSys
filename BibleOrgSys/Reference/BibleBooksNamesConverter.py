#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# BibleBooksNamesConverter.py
#
# Module handling BibleBooksNames_*.xml to produce C and Python data tables
#
# Copyright (C) 2010-2019 Robert Hunt
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
Module handling BibleBooksNames_*.xml to produce pickle, JSON, C and Python data tables.
"""

from gettext import gettext as _

lastModifiedDate = '2019-05-12' # by RJH
shortProgramName = "BibleBooksNamesConverter"
programName = "Bible Books Names Systems converter"
programVersion = '0.36'
programNameVersion = f'{shortProgramName} v{programVersion}'
programNameVersionDate = f'{programNameVersion} {_("last modified")} {lastModifiedDate}'

debuggingThisModule = False


import os
import logging
from xml.etree.ElementTree import ElementTree

if __name__ == '__main__':
    import sys
    sys.path.append( os.path.join(os.path.dirname(__file__), '../') ) # So we can run it from the above folder and still do these imports
from Misc.singleton import singleton
import BibleOrgSysGlobals


@singleton # Can only ever have one instance
class BibleBooksNamesConverter:
    """
    A class to handle data for Bible booksNames systems.
    """

    def __init__( self ):
        """
        Constructor.
        """
        self.__filenameBase = "BibleBooksNames"

        # These fields are used for parsing the XML
        self.XMLTreeTag = "BibleBooksNames"
        self.headerTag = "header"
        self.mainElementTags = ( "BibleDivisionNames", "BibleBooknameLeaders", "BibleBookNames" )

        # These fields are used for automatically checking/validating the XML
        #   0,1,2 = entries for the three mainElementTags above
        self.compulsoryAttributes = { 0:("standardAbbreviation",), 1:("standardLeader",), 2:("referenceAbbreviation",) }
        self.optionalAttributes = { 0:(), 1:(), 2:() }
        self.uniqueAttributes = {}
        for key in self.compulsoryAttributes.keys():
            self.uniqueAttributes[key] = self.compulsoryAttributes[key] + self.optionalAttributes[key]
        self.compulsoryElements = { 0:("defaultName","defaultAbbreviation","includesBook",), 1:("inputAbbreviation",), 2:("defaultName","defaultAbbreviation",) }
        self.optionalElements =  { 0:("inputAbbreviation",), 1:(), 2:("inputAbbreviation",) }
        self.uniqueElements = { 0:("defaultName","defaultAbbreviation","inputAbbreviation",), 1:("inputAbbreviation",), 2:("defaultName","defaultAbbreviation","inputAbbreviation",) }

        # These are fields that we will fill later
        self.__XMLFolder, self.__XMLSystems, self.__BookNamesSystemsDict, self.__expandedInputSystems = None, {}, {}, {}
    # end of __init__

    def loadSystems( self, folder=None ):
        """
        Load and pre-process the specified booksNames systems.
        """
        if not self.__XMLSystems: # Only ever do this once
            if folder==None: folder = BibleOrgSysGlobals.BOS_DATA_FILES_FOLDERPATH.joinpath( 'BookNames/' ) # Relative to module, not cwd
            self.__XMLFolder = folder
            if BibleOrgSysGlobals.verbosityLevel > 2: print( _("Loading book names systems from {}…").format( folder ) )
            for filename in os.listdir( folder ):
                filepart, extension = os.path.splitext( filename )
                if extension.upper() == '.XML' and filepart.upper().startswith(self.__filenameBase.upper()+"_"):
                    booksNamesSystemCode = filepart[len(self.__filenameBase)+1:]
                    if BibleOrgSysGlobals.verbosityLevel > 3: print( _("Loading {} books names system from {}…").format( booksNamesSystemCode, filename ) )
                    self.__XMLSystems[booksNamesSystemCode] = {}
                    self.__XMLSystems[booksNamesSystemCode]["languageCode"] = booksNamesSystemCode.split('_',1)[0]
                    self.__XMLSystems[booksNamesSystemCode]['tree'] = ElementTree().parse( os.path.join( folder, filename ) )
                    assert self.__XMLSystems[booksNamesSystemCode]['tree'] # Fail here if we didn't load anything at all

                    # Check and remove the header element
                    if self.__XMLSystems[booksNamesSystemCode]['tree'].tag  == self.XMLTreeTag:
                        header = self.__XMLSystems[booksNamesSystemCode]['tree'][0]
                        if header.tag == self.headerTag:
                            self.__XMLSystems[booksNamesSystemCode]["header"] = header
                            self.__XMLSystems[booksNamesSystemCode]['tree'].remove( header )
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
                                    self.__XMLSystems[booksNamesSystemCode]['version'] = work.find('version').text
                                    self.__XMLSystems[booksNamesSystemCode]["date"] = work.find("date").text
                                    self.__XMLSystems[booksNamesSystemCode]["title"] = work.find("title").text
                                else:
                                    logging.warning( _("Missing work element in header") )
                        else:
                            logging.warning( _("Missing header element (looking for {!r} tag)").format( self.headerTag ) )
                    else:
                        logging.error( _("Expected to load {!r} but got {!r}").format( self.XMLTreeTag, self.__XMLSystems[booksNamesSystemCode]['tree'].tag ) )
                    bookCount = 0 # There must be an easier way to do this
                    for subelement in self.__XMLSystems[booksNamesSystemCode]['tree']:
                        bookCount += 1
                    if BibleOrgSysGlobals.verbosityLevel > 2:
                        print( _("    Loaded {} books for {}").format( bookCount, booksNamesSystemCode ) )
                    logging.info( _("    Loaded {} books for {}").format( bookCount, booksNamesSystemCode ) )

                    if BibleOrgSysGlobals.strictCheckingFlag:
                        self.__validateSystem( booksNamesSystemCode )
        return self
    # end of loadSystems

    def __validateSystem( self, systemName ):
        """
        Checks for basic formatting/content errors in a Bible book name system.
        """
        assert systemName
        assert self.__XMLSystems[systemName]['tree']

        if len(self.__XMLSystems[systemName]["languageCode"]) != 3:
            logging.error( _("Couldn't find 3-letter language code in {!r} book names system").format( systemName ) )
        #if self.__ISOLanguages and not self.__ISOLanguages.isValidLanguageCode( self.__XMLSystems[systemName]["languageCode"] ): # Check that we have a valid language code
            #logging.error( _("Unrecognized {!r} ISO-639-3 language code in {!r} book names system").format( self.__XMLSystems[systemName]["languageCode"], systemName ) )

        uniqueDict = {}
        for index in range( len(self.mainElementTags) ):
            for elementName in self.uniqueElements[index]: uniqueDict["Element_"+str(index)+"_"+elementName] = []
            for attributeName in self.uniqueAttributes[index]: uniqueDict["Attribute_"+str(index)+"_"+attributeName] = []

        expectedID = 1
        for k,element in enumerate(self.__XMLSystems[systemName]['tree']):
            if element.tag in self.mainElementTags:
                BibleOrgSysGlobals.checkXMLNoText( element, element.tag )
                BibleOrgSysGlobals.checkXMLNoTail( element, element.tag )
                if not self.compulsoryAttributes and not self.optionalAttributes: BibleOrgSysGlobals.checkXMLNoAttributes( element, element.tag )
                if not self.compulsoryElements and not self.optionalElements: BibleOrgSysGlobals.checkXMLNoSubelements( element, element.tag )

                index = self.mainElementTags.index( element.tag )

                # Check compulsory attributes on this main element
                for attributeName in self.compulsoryAttributes[index]:
                    attributeValue = element.get( attributeName )
                    if attributeValue is None:
                        logging.error( _("Compulsory {!r} attribute is missing from {} element in record {} in {}").format( attributeName, element.tag, k, systemName ) )
                    if not attributeValue:
                        logging.warning( _("Compulsory {!r} attribute is blank on {} element in record {} in {}").format( attributeName, element.tag, k, systemName ) )

                # Check optional attributes on this main element
                for attributeName in self.optionalAttributes[index]:
                    attributeValue = element.get( attributeName )
                    if attributeValue is not None:
                        if not attributeValue:
                            logging.warning( _("Optional {!r} attribute is blank on {} element in record {} in {}").format( attributeName, element.tag, k, systemName ) )

                # Check for unexpected additional attributes on this main element
                for attributeName in element.keys():
                    attributeValue = element.get( attributeName )
                    if attributeName not in self.compulsoryAttributes[index] and attributeName not in self.optionalAttributes[index]:
                        logging.warning( _("Additional {!r} attribute ({!r}) found on {} element in record {} in {}").format( attributeName, attributeValue, element.tag, k, systemName ) )

                # Check the attributes that must contain unique information (in that particular field -- doesn't check across different attributes)
                for attributeName in self.uniqueAttributes[index]:
                    attributeValue = element.get( attributeName )
                    if attributeValue is not None:
                        if attributeValue in uniqueDict["Attribute_"+str(index)+"_"+attributeName]:
                            logging.error( _("Found {!r} data repeated in {!r} field on {} element in record {} in {}").format( attributeValue, attributeName, element.tag, k, systemName ) )
                        uniqueDict["Attribute_"+str(index)+"_"+attributeName].append( attributeValue )

                # Check compulsory elements
                for elementName in self.compulsoryElements[index]:
                    if element.find( elementName ) is None:
                        logging.error( _("Compulsory {!r} element is missing (record {}) in {}").format( elementName, k, systemName ) )
                    if not element.find( elementName ).text:
                        logging.warning( _("Compulsory {!r} element is blank (record {}) in {}").format( elementName, k, systemName ) )

                # Check optional elements
                for elementName in self.optionalElements[index]:
                    if element.find( elementName ) is not None:
                        if not element.find( elementName ).text:
                            logging.warning( _("Optional {!r} element is blank (record {}) in {}").format( elementName, k, systemName ) )

                # Check for unexpected additional elements
                for subelement in element:
                    if subelement.tag not in self.compulsoryElements[index] and subelement.tag not in self.optionalElements[index]:
                        logging.warning( _("Additional {!r} element ({!r}) found (record {}) in {} {}").format( subelement.tag, subelement.text, k, systemName, element.tag ) )

                # Check the elements that must contain unique information (in that particular element -- doesn't check across different elements)
                for elementName in self.uniqueElements[index]:
                    if element.find( elementName ) is not None:
                        text = element.find( elementName ).text
                        if text in uniqueDict["Element_"+str(index)+"_"+elementName]:
                            myLogging = logging.info if element.tag == 'BibleDivisionNames' else logging.error
                            myLogging( _("Found {!r} data repeated in {!r} element (record {}) in {}").format( text, elementName, k, systemName ) )
                        uniqueDict["Element_"+str(index)+"_"+elementName].append( text )
            else:
                logging.warning( _("Unexpected element: {} in record {} in {}").format( element.tag, k, systemName ) )
    # end of __validateSystem

    def __str__( self ):
        """
        This method returns the string representation of a Bible booksNames system.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = "BibleBooksNamesConverter object"
        result += ('\n' if result else '') + "  Number of bookname systems loaded = {}".format( len(self.__XMLSystems) )
        if BibleOrgSysGlobals.verbosityLevel > 2: # Make it verbose
            for x in self.__XMLSystems:
                result += ('\n' if result else '') + "  {}".format( x )
                if self.__ISOLanguages and self.__XMLSystems[x]["languageCode"] and self.__ISOLanguages.isValidLanguageCode( self.__XMLSystems[x]["languageCode"] ):
                    result += ('\n' if result else '') + "    " + _("Language code {} = {}").format( self.__XMLSystems[x]["languageCode"], self.__ISOLanguages.getLanguageName( self.__XMLSystems[x]["languageCode"]) )
                title = self.__XMLSystems[x]["title"]
                if title: result += ('\n' if result else '') + "    {}".format( title )
                version = self.__XMLSystems[x]['version']
                if version: result += ('\n' if result else '') + '    ' + _("Version: {}").format( version )
                date = self.__XMLSystems[x]["date"]
                if date: result += ('\n' if result else '') + '    ' + _("Last updated: {}").format( date )
                result += ('\n' if result else '') + '    ' + _("Number of entries = {}").format( len(self.__XMLSystems[x]['tree']) )
                numDivisions, numLeaders, numBooks = 0, 0, 0
                for element in self.__XMLSystems[x]['tree']:
                    if element.tag == "BibleDivisionNames":
                        numDivisions += 1
                    elif element.tag == "BibleBooknameLeaders":
                        numLeaders += 1
                    elif element.tag == "BibleBookNames":
                        numBooks += 1
                if numDivisions: result += ('\n' if result else '') + '      ' + _("Number of divisions = {}").format( numDivisions )
                if numLeaders: result += ('\n' if result else '') + '      ' + _("Number of bookname leaders = {}").format( numLeaders )
                if numBooks: result += ('\n' if result else '') + '      ' + _("Number of books = {}").format( numBooks )
        return result
    # end of __str__

    def __len__( self ):
        """ Returns the number of systems loaded. """
        return len( self.__XMLSystems )
    # end of __len__

    def expandInputs ( self, bookList ):
        """
        This is a helper function to expand the inputAbbreviation fields to include all unambiguous shorter abbreviations.

        It is best to do this for a specific publication since there will be less ambiguities if there are less actual books included.
        This routine is only really included here as a demo -- it's much better to call expandBibleNamesInputs
            when the actual list of books for your publication is already known.

        Saves divisions name and book name ordered dictionaries, all UPPER CASE, sorted with longest first.
        """
        assert bookList
        assert self.__XMLSystems
        self.importDataToPython()
        assert self.__BookNamesSystemsDict
        if self.__expandedInputSystems: return # No need to do this again

        if bookList is not None:
            for BBB in bookList: # Just check this list is valid
                if not BibleOrgSysGlobals.BibleBooksCodes.isValidBBB( BBB ): logging.error( _("Invalid {!r} in booklist requested for expansion").format(BBB) )

        if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Expanding input abbreviations…") )
        for systemName in self.__BookNamesSystemsDict:
            if BibleOrgSysGlobals.verbosityLevel > 2: print( _("  Expanding {}…").format( systemName ) )
            divisionsNamesDict, booknameLeadersDict, bookNamesDict = self.__BookNamesSystemsDict[systemName]
            self.__expandedInputSystems[systemName] = self.expandBibleNamesInputs( systemName, divisionsNamesDict, booknameLeadersDict, bookNamesDict, bookList )
    # end of expandInputs

    def importDataToPython( self ):
        """
        Loads (and pivots) the data (not including the header) into suitable Python containers to use in a Python program.

        If necessary (but not actually recommended), expandInputs could be called before this to fill self.__expandedInputSystems.

        Returns two dictionaries which should each contain entries for each named system.
        """
        assert self.__XMLSystems
        if self.__BookNamesSystemsDict: # We've already done an import/restructuring -- no need to repeat it
            return self.__BookNamesSystemsDict, self.__expandedInputSystems

        # We'll create a number of dictionaries
        if BibleOrgSysGlobals.verbosityLevel > 3: print( _("Importing data into Python dictionary…") )
        self.__BookNamesSystemsDict = {}
        for booksNamesSystemCode in self.__XMLSystems.keys():
            #print( booksNamesSystemCode )
            # Make the data dictionary for this booksNames system
            myDivisionsNamesDict, myBooknameLeadersDict, myBookNamesDict = {}, {}, {}
            for element in self.__XMLSystems[booksNamesSystemCode]['tree']:
                if element.tag == "BibleDivisionNames":
                    standardAbbreviation = element.get("standardAbbreviation")
                    defaultName = element.find("defaultName").text
                    defaultAbbreviation = element.find("defaultAbbreviation").text
                    inputFields = [ defaultName ]
                    if not defaultName.startswith( defaultAbbreviation ):
                        inputFields.append( defaultAbbreviation )
                    for subelement in element.findall("inputAbbreviation"):
                        if subelement.text in inputFields:
                            logging.warning( _("Superfluous {!r} entry in inputAbbreviation field for {} division in {!r} booksNames system").format( subelement.text, defaultName, booksNamesSystemCode ) )
                        else: inputFields.append( subelement.text )
                    includedBooks = []
                    for subelement in element.findall("includesBook"):
                        BBB = subelement.text
                        if not BibleOrgSysGlobals.BibleBooksCodes.isValidBBB( BBB ):
                            logging.error( _("Unrecognized {!r} book abbreviation in BibleDivisionNames in {!r} booksNames system").format( BBB, booksNamesSystemCode ) )
                        if BBB in includedBooks:
                            logging.error( _("Duplicate {!r} entry in includesBook field for {!r} division in {!r} booksNames system").format( subelement.text, defaultName, booksNamesSystemCode ) )
                        else: includedBooks.append( BBB )
                    myDivisionsNamesDict[standardAbbreviation] = {"includedBooks":includedBooks, "defaultName":defaultName, "defaultAbbreviation":defaultAbbreviation, "inputFields":inputFields }
                elif element.tag == "BibleBooknameLeaders":
                    standardLeader = element.get("standardLeader")
                    inputFields = [] # Don't include the standard leader here
                    for subelement in element.findall("inputAbbreviation"):
                        adjField = subelement.text + ' '
                        if adjField in inputFields:
                            logging.error( _("Duplicate {!r} entry in inputAbbreviation field for {!r} bookname leaders in {!r} booksNames system").format( subelement.text, standardLeader, booksNamesSystemCode ) )
                        else: inputFields.append( adjField )
                    myBooknameLeadersDict[standardLeader+' '] = inputFields
                elif element.tag == "BibleBookNames":
                    referenceAbbreviation = element.get("referenceAbbreviation")
                    if not BibleOrgSysGlobals.BibleBooksCodes.isValidBBB( referenceAbbreviation ):
                        logging.error( _("Unrecognized {!r} book abbreviation in BibleBookNames in {!r} booksNames system").format( referenceAbbreviation, booksNamesSystemCode ) )
                    defaultName = element.find("defaultName").text
                    defaultAbbreviation = element.find("defaultAbbreviation").text
                    inputFields = [ defaultName ] # Add the default name to the allowed input fields
                    if defaultAbbreviation != defaultName: inputFields.append( defaultAbbreviation ) # Automatically add the default abbreviation if it's different
                    for subelement in element.findall("inputAbbreviation"):
                        if subelement.text in inputFields:
                            logging.info( _("Superfluous {!r} entry in inputAbbreviation field for {} book in {!r} booksNames system").format( subelement.text, defaultName, booksNamesSystemCode ) )
                        else: inputFields.append( subelement.text )
                    myBookNamesDict[referenceAbbreviation] = { "defaultName":defaultName, "defaultAbbreviation":defaultAbbreviation, "inputFields":inputFields }

            if BibleOrgSysGlobals.strictCheckingFlag: # check for duplicates
                for checkSystemCode in self.__BookNamesSystemsDict:
                    checkDivisionsNamesList, checkBooknameLeadersDict, checkBookNamesDict = self.__BookNamesSystemsDict[checkSystemCode]
                    if checkDivisionsNamesList==myDivisionsNamesDict and checkBookNamesDict==myBookNamesDict:
                        if checkBooknameLeadersDict == myBooknameLeadersDict:
                            logging.error( _("{} and {} book name systems are exactly identical ({} divisions, {} book names, {} leaders)").format( booksNamesSystemCode, checkSystemCode, len(myDivisionsNamesDict), len(myBookNamesDict), len(myBooknameLeadersDict) ) )
                        else: # only the leaders are different
                            logging.error( _("{} and {} book name systems are mostly identical ({} divisions, {} book names)").format( booksNamesSystemCode, checkSystemCode, len(myDivisionsNamesDict), len(myBookNamesDict) ) )

            # Now put it into my dictionary for easy access
            self.__BookNamesSystemsDict[booksNamesSystemCode] = myDivisionsNamesDict, myBooknameLeadersDict, myBookNamesDict
        return self.__BookNamesSystemsDict, self.__expandedInputSystems
    # end of importDataToPython


    def pickle( self, filepath=None ):
        """
        Writes the information tables to a .pickle file that can be easily loaded into a Python3 program.
        """
        import pickle

        assert self.__XMLSystems
        self.importDataToPython()
        assert self.__BookNamesSystemsDict

        if not filepath:
            folder = os.path.join( self.__XMLFolder, "../", "DerivedFiles/" )
            if not os.path.exists( folder ): os.mkdir( folder )
            filepath = os.path.join( folder, self.__filenameBase + "_Tables.pickle" )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Exporting to {}…").format( filepath ) )
        with open( filepath, 'wb' ) as myFile:
            pickle.dump( self.__BookNamesSystemsDict, myFile )
            #pickle.dump( self.__expandedInputSystems, myFile )
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
            theFile.write( '  "{}": {{\n    # Key is {}\n    # Fields ({}) are: {}\n'.format( dictName, keyComment, fieldsCount, fieldsComment ) )
            for dictKey in theDict.keys():
                theFile.write( '    {}: {},\n'.format( repr(dictKey), repr(theDict[dictKey]) ) )
            theFile.write( "  }}, # end of {} ({} entries)\n\n".format( dictName, len(theDict) ) )
        # end of exportPythonDict

        #def exportPythonOrderedDict( theFile, theDict, dictName, keyComment, fieldsComment ):
            #"""Exports theDict to theFile."""
            #assert isinstance( theDict, OrderedDict )
            #for dictKey in theDict.keys(): # Have to iterate this :(
                #fieldsCount = len( theDict[dictKey] ) if isinstance( theDict[dictKey], (tuple,dict,list) ) else 1
                #break # We only check the first (random) entry we get
            #theFile.write( '  "{}": OrderedDict([\n    # Key is {}\n    # Fields ({}) are: {}\n'.format( dictName, keyComment, fieldsCount, fieldsComment ) )
            #for dictKey in theDict.keys():
                #theFile.write( '    ({}, {}),\n'.format( repr(dictKey), repr(theDict[dictKey]) ) )
            #theFile.write( "  ]), # end of {} ({} entries)\n\n".format( dictName, len(theDict) ) )
        ## end of exportPythonOrderedDict

        def exportPythonList( theFile, theList, listName, fieldsComment ):
            """Exports theList to theFile."""
            assert isinstance( theList, list )
            fieldsCount = len( theList[0] ) if isinstance( theList[0], (tuple,dict,list) ) else 1
            theFile.write( '  "{}": [\n    # Fields ({}) are: {}\n'.format( listName, fieldsCount, fieldsComment ) )
            for j,entry in enumerate(theList):
                theFile.write( '    {}, # {}\n'.format( repr(entry), j ) )
            theFile.write( "  ], # end of {} ({} entries)\n\n".format( listName, len(theList) ) )
        # end of exportPythonList

        from datetime import datetime

        assert self.__XMLSystems
        self.importDataToPython()
        assert self.__BookNamesSystemsDict

        raise Exception( "Python export not working properly yet" )
        if not filepath: filepath = os.path.join( self.__XMLFolder, "../", 'DerivedFiles/', self.__filenameBase + "_Tables.py" )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Exporting to {}…").format( filepath ) )
        # Split into three lists/dictionaries
        with open( filepath, 'wt', encoding='utf-8' ) as myFile:
            myFile.write( "# {}\n#\n".format( filepath ) )
            myFile.write( "# This UTF-8 file was automatically generated by BibleBooksNames.py V{} on {}\n#\n".format( programVersion, datetime.now() ) )
            #if self.title: myFile.write( "# {}\n".format( self.title ) )
            #if self.version: myFile.write( "#  Version: {}\n".format( self.version ) )
            #if self.date: myFile.write( "#  Date: {}\n#\n".format( self.date ) )
            #myFile.write( "#   {} {} entries loaded from the original XML file.\n".format( len(self.namesTree), self.XMLTreeTag ) )
            myFile.write( "#   {} {} loaded from the original XML files.\n#\n\n".format( len(self.__XMLSystems), self.XMLTreeTag ) )
            #myFile.write( "from collections import OrderedDict\n\n" )
            myFile.write( "\ndivisionNamesList = {\n  # Key is languageCode\n  # Fields are divisionNames\n\n" )
            for systemName in self.__BookNamesSystemsDict:
                divisionsNamesDict, booknameLeadersDict, bookNamesDict = self.__BookNamesSystemsDict[systemName]
                exportPythonList( myFile, divisionsNamesDict, systemName, "startsWith( string), defaultName (string), defaultAbbreviation (string), inputFields (list of strings) all in a dictionary" )
            myFile.write( "}} # end of divisionNamesList ({} systems)\n\n\n".format( len(self.__BookNamesSystemsDict) ) )
            myFile.write( "\nbooknameLeadersDict = {\n  # Key is languageCode\n  # Fields are divisionNames\n\n" )
            for systemName in self.__BookNamesSystemsDict:
                divisionsNamesDict, booknameLeadersDict, bookNamesDict = self.__BookNamesSystemsDict[systemName]
                exportPythonDict( myFile, booknameLeadersDict, systemName, "standardLeader (all fields include a trailing space)", "inputAlternatives (list of strings)" )
            myFile.write( "}} # end of booknameLeadersDict ({} systems)\n\n\n".format( len(self.__BookNamesSystemsDict) ) )
            myFile.write( "\nbookNamesDict = {\n  # Key is languageCode\n  # Fields are divisionNames\n\n" )
            for systemName in self.__BookNamesSystemsDict:
                divisionsNamesDict, booknameLeadersDict, bookNamesDict = self.__BookNamesSystemsDict[systemName]
                exportPythonDict( myFile, bookNamesDict, systemName, "referenceAbbreviation", "defaultName (string), defaultAbbreviation (string), inputAbbreviations (list of strings) all in a dictionary" )
            myFile.write( "}} # end of bookNamesDict ({} systems)\n\n\n".format( len(self.__BookNamesSystemsDict) ) )
            if self.__expandedInputSystems:
                myFile.write( "\ndivisionsNamesInputDict = {\n  # Key is languageCode\n  # Fields are divisionNames\n\n" )
                for systemName in self.__BookNamesSystemsDict:
                    if systemName in self.__expandedInputSystems:
                        divisionsNamesInputDict, bookNamesInputDict = self.__expandedInputSystems[systemName]
                        exportPythonDict( myFile, divisionsNamesInputDict, "divisionsNamesInputDict", "UpperCaseInputString (sorted with longest first)", "index (into divisionNamesList above)" )
                myFile.write( "}} # end of divisionsNamesInputDict ({} systems)\n\n\n".format( len(self.__BookNamesSystemsDict) ) )
                myFile.write( "\nbookNamesInputDict = {\n  # Key is languageCode\n  # Fields are divisionNames\n\n" )
                for systemName in self.__BookNamesSystemsDict:
                    if systemName in self.__expandedInputSystems:
                        divisionsNamesInputDict, bookNamesInputDict = self.__expandedInputSystems[systemName]
                        exportPythonDict( myFile, bookNamesInputDict, "bookNamesInputDict", "UpperCaseInputString (sorted with longest first)", "referenceAbbreviation (string)" )
                myFile.write( "}} # end of bookNamesInputDict ({} systems)\n".format( len(self.__BookNamesSystemsDict) ) )
    # end of exportDataToPython

    def exportDataToJSON( self, filepath=None ):
        """
        Writes the information tables to a .json file that can be easily loaded into a Java program.

        See http://en.wikipedia.org/wiki/JSON.
        """
        from datetime import datetime
        import json

        assert self.__XMLSystems
        self.importDataToPython()
        assert self.__BookNamesSystemsDict

        if not filepath: filepath = os.path.join( self.__XMLFolder, "../", 'DerivedFiles/', self.__filenameBase + "_Tables.json" )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Exporting to {}…").format( filepath ) )
        with open( filepath, 'wt', encoding='utf-8' ) as myFile:
            #myFile.write( "# {}\n#\n".format( filepath ) ) # Not sure yet if these comment fields are allowed in JSON
            #myFile.write( "# This UTF-8 file was automatically generated by BibleBooksCodes.py V{} on {}\n#\n".format( programVersion, datetime.now() ) )
            #if self.titleString: myFile.write( "# {} data\n".format( self.titleString ) )
            #if self.programVersion: myFile.write( "#  Version: {}\n".format( self.programVersion ) )
            #if self.dateString: myFile.write( "#  Date: {}\n#\n".format( self.dateString ) )
            #myFile.write( "#   {} {} loaded from the original XML file.\n#\n\n".format( len(self.XMLtree), self.XMLTreeTag ) )
            json.dump( self.__BookNamesSystemsDict, myFile, indent=2 )
            #myFile.write( "\n\n# end of {}".format(os.path.basename(filepath) )
    # end of exportDataToJSON

    def exportDataToC( self, filepath=None ):
        """
        Writes the information tables to a .h file that can be included in c and c++ programs.
        """
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

        from datetime import datetime

        assert self.__XMLSystems
        self.importDataToPython()
        assert self.__BookNamesSystemsDict

        if not filepath: filepath = os.path.join( 'DerivedFiles/', self.__filenameBase + "_Tables.h" )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Exporting to {}…").format( filepath ) )
        raise Exception( "C export not written yet -- sorry." )

        ifdefName = self.__filenameBase.upper() + "_Tables_h"
        with open( filepath, 'wt', encoding='utf-8' ) as myFile:
            myFile.write( "// {}\n//\n".format( filepath ) )
            myFile.write( "// This UTF-8 file was automatically generated by BibleBooksNames.py V{} on {}\n//\n".format( programVersion, datetime.now() ) )
            if self.title: myFile.write( "// {}\n".format( self.title ) )
            if self.version: myFile.write( "//  Version: {}\n".format( self.version ) )
            if self.date: myFile.write( "//  Date: {}\n//\n".format( self.date ) )
            myFile.write( "//   {} {} loaded from the original XML file.\n//\n\n".format( len(self.namesTree), self.XMLTreeTag ) )
            myFile.write( "#ifndef {}\n#define {}\n\n".format( ifdefName, ifdefName ) )
            exportPythonDict( myFile, IDDict, "IDDict", "{int id; char* refAbbrev; char* SBLAbbrev; char* OSISAbbrev; char* PTAbbrev; char* PTNum; char* EngName;}", "id (sorted), referenceAbbreviation, SBLAbbreviation, OSISAbbreviation, USFMAbbreviation, USFMNumberString, nameEnglish (comment only)" )
            myFile.write( "#endif // {}\n".format( ifdefName ) )
    # end of exportDataToC
# end of BibleBooksNamesConverter class


def demo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel > 1: print( programNameVersion )

    sampleBookList = ['GEN','JDG','SA1','SA2','KI1','KI2','MA4','MAT','MRK','LUK','JHN','ACT','ROM','CO1','CO2','PE1','PE2','JDE','REV']
    #sampleBookList = ['GEN','JDG','SA1','SA2','KI1','KI2','MA1','MA2']
    #sampleBookList = ['MAT','MRK','LUK','JHN','ACT','ROM','CO1','CO2','GAL','EPH','PHP','COL','PE1','PE2','JDE','REV']
    if BibleOrgSysGlobals.commandLineArguments.export:
        bbnsc = BibleBooksNamesConverter().loadSystems() # Load the XML
        #if BibleOrgSysGlobals.commandLineArguments.expandDemo: # Expand the inputAbbreviations to find all shorter unambiguous possibilities
        #    bbnsc.expandInputs( sampleBookList )
        bbnsc.pickle() # Produce the .pickle file
        bbnsc.exportDataToPython() # Produce the .py tables
        bbnsc.exportDataToJSON() # Produce a json output file
        bbnsc.exportDataToC() # Produce the .h and .c tables

    else: # Must be demo mode
        # Demo the converter object
        bbnsc = BibleBooksNamesConverter().loadSystems() # Load the XML
        print( bbnsc ) # Just print a summary
        #if BibleOrgSysGlobals.commandLineArguments.expandDemo: # Expand the inputAbbreviations to find all shorter unambiguous possibilities
        #    bbnsc.expandInputs( sampleBookList )
        #    print( bbnsc ) # Just print a summary
# end of demo

if __name__ == '__main__':
    import multiprocessing
    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( programName, programVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    demo()

    BibleOrgSysGlobals.closedown( programName, programVersion )
# end of BibleBooksNamesConverter.py
