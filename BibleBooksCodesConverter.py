#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# BibleBooksCodesConverter.py
#   Last modified: 2013-05-20 by RJH (also update versionString below)
#
# Module handling BibleBooksCodes.xml to produce C and Python data tables
#
# Copyright (C) 2010-2013 Robert Hunt
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

progName = "Bible Books Codes converter"
versionString = "0.68"


import logging, os.path
from gettext import gettext as _
from datetime import datetime
from collections import OrderedDict
from xml.etree.ElementTree import ElementTree

from singleton import singleton
import Globals



@singleton # Can only ever have one instance
class BibleBooksCodesConverter:
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
        self._compulsoryElements = ( "nameEnglish", "referenceAbbreviation", "referenceNumber", "sequenceNumber" )
        self._optionalElements = ( "expectedChapters", "SBLAbbreviation", "OSISAbbreviation", "SwordAbbreviation", "CCELNumber",
                                        "USFMAbbreviation", "USFMNumber", "USXNumber", "UnboundCode", "BibleditNumber",
                                        "NETBibleAbbreviation", "ByzantineAbbreviation", "possibleAlternativeBooks" )
        self._uniqueElements = self._compulsoryElements + \
                    ( "USXNumber", "UnboundCode", "BibleditNumber", "NETBibleAbbreviation", "ByzantineAbbreviation" )

        # These are fields that we will fill later
        self._XMLheader, self._XMLtree = None, None
        self.__DataDicts = {} # Used for import
        self.titleString = self.versionString = self.dateString = ''
    # end of BibleBooksCodesConverter.__init__

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
    # end of BibleBooksCodesConverter.loadAndValidate

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
    # end of BibleBooksCodesConverter.__load

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

                # Get the referenceAbbreviation to use as a record ID
                ID = element.find("referenceAbbreviation").text

                # Check compulsory elements
                for elementName in self._compulsoryElements:
                    foundElement = element.find( elementName )
                    if foundElement is None:
                        logging.error( _("Compulsory '{}' element is missing in record with ID '{}' (record {})").format( elementName, ID, j ) )
                    else:
                        Globals.checkXMLNoTail( foundElement, foundElement.tag + " in " + element.tag )
                        Globals.checkXMLNoAttributes( foundElement, foundElement.tag + " in " + element.tag )
                        Globals.checkXMLNoSubelements( foundElement, foundElement.tag + " in " + element.tag )
                        if not foundElement.text:
                            logging.warning( _("Compulsory '{}' element is blank in record with ID '{}' (record {})").format( elementName, ID, j ) )

                # Check optional elements
                for elementName in self._optionalElements:
                    foundElement = element.find( elementName )
                    if foundElement is not None:
                        Globals.checkXMLNoTail( foundElement, foundElement.tag + " in " + element.tag )
                        Globals.checkXMLNoAttributes( foundElement, foundElement.tag + " in " + element.tag )
                        Globals.checkXMLNoSubelements( foundElement, foundElement.tag + " in " + element.tag )
                        if not foundElement.text:
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
    # end of BibleBooksCodesConverter.__validate

    def __str__( self ):
        """
        This method returns the string representation of a Bible book code.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        indent = 2
        result = "BibleBooksCodesConverter object"
        if self.titleString: result += ('\n' if result else '') + ' '*indent + _("Title: {}").format( self.titleString )
        if self.versionString: result += ('\n' if result else '') + ' '*indent + _("Version: {}").format( self.versionString )
        if self.dateString: result += ('\n' if result else '') + ' '*indent + _("Date: {}").format( self.dateString )
        if self._XMLtree is not None: result += ('\n' if result else '') + ' '*indent + _("Number of entries = {}").format( len(self._XMLtree) )
        return result
    # end of BibleBooksCodesConverter.__str__

    def __len__( self ):
        """ Returns the number of books codes loaded. """
        return len( self._XMLtree )
    # end of BibleBooksCodesConverter.__len__

    def importDataToPython( self ):
        """
        Loads (and pivots) the data (not including the header) into suitable Python containers to use in a Python program.
        (Of course, you can just use the elementTree in self._XMLtree if you prefer.)
        """
        def makeList( parameter1, parameter2 ):
            """ Returns a list containing all parameters. Parameter1 may already be a list. """
            if isinstance( parameter1, list ):
                #assert( parameter2 not in parameter1 )
                parameter1.append( parameter2 )
                return parameter1
            else:
                return [ parameter1, parameter2 ]
        # end of makeList


        assert( self._XMLtree )
        if self.__DataDicts: # We've already done an import/restructuring -- no need to repeat it
            return self.__DataDicts

        # We'll create a number of dictionaries with different elements as the key
        myIDDict, myRefAbbrDict = OrderedDict(), OrderedDict()
        mySBLDict,myOADict,mySwDict,myCCELDict,myUSFMAbbrDict,myUSFMNDict,myUSXNDict,myUCDict,myBENDict,myNETDict,myBzDict, myENDict, allAbbreviationsDict = {},{},{},{},{},{},{},{},{},{},{}, {}, {}
        sequenceNumberList, sequenceTupleList = [], [] # Both have the integer form (not the string form) of the sequenceNumber
        for element in self._XMLtree:
            # Get the required information out of the tree for this element
            # Start with the compulsory elements
            nameEnglish = element.find("nameEnglish").text # This name is really just a comment element
            referenceAbbreviation = element.find("referenceAbbreviation").text
            if referenceAbbreviation.upper() != referenceAbbreviation:
                logging.error( _("Reference abbreviation '{}' should be UPPER CASE").format( referenceAbbreviation ) )
            ID = element.find("referenceNumber").text
            intID = int( ID )
            sequenceNumber = element.find("sequenceNumber").text
            intSequenceNumber = int( sequenceNumber )
            # The optional elements are set to None if they don't exist
            expectedChapters = None if element.find("expectedChapters") is None else element.find("expectedChapters").text
            SBLAbbreviation = None if element.find("SBLAbbreviation") is None else element.find("SBLAbbreviation").text
            OSISAbbreviation = None if element.find("OSISAbbreviation") is None else element.find("OSISAbbreviation").text
            SwordAbbreviation = None if element.find("SwordAbbreviation") is None else element.find("SwordAbbreviation").text
            CCELNumberString = None if element.find("CCELNumber") is None else element.find("CCELNumber").text
            #CCELNumber = int( CCELNumberString ) if CCELNumberString else -1
            USFMAbbreviation = None if element.find("USFMAbbreviation") is None else element.find("USFMAbbreviation").text
            USFMNumberString = None if element.find("USFMNumber") is None else element.find("USFMNumber").text
            #USFMNumber = int( USFMNumberString ) if USFMNumberString else -1
            USXNumberString = None if element.find("USXNumber") is None else element.find("USXNumber").text
            UnboundCodeString = None if element.find("UnboundCode") is None else element.find("UnboundCode").text
            BibleditNumberString = None if element.find("BibleditNumber") is None else element.find("BibleditNumber").text
            NETBibleAbbreviation = None if element.find("NETBibleAbbreviation") is None else element.find("NETBibleAbbreviation").text
            ByzantineAbbreviation = None if element.find("ByzantineAbbreviation") is None else element.find("ByzantineAbbreviation").text
            possibleAlternativeBooks = None if element.find("possibleAlternativeBooks") is None else element.find("possibleAlternativeBooks").text.split(',')

            # Now put it into my dictionaries for easy access
            # This part should be customized or added to for however you need to process the data
            #   Add .upper() if you require the abbreviations to be uppercase (or .lower() for lower case)
            #   The referenceAbbreviation is UPPER CASE by definition
            if "referenceAbbreviation" in self._compulsoryElements or referenceAbbreviation:
                if "referenceAbbreviation" in self._uniqueElements: assert( referenceAbbreviation not in myRefAbbrDict ) # Shouldn't be any duplicates
                if referenceAbbreviation in myRefAbbrDict: halt
                else: myRefAbbrDict[referenceAbbreviation] = { "referenceNumber":intID, "SBLAbbreviation":SBLAbbreviation, "OSISAbbreviation":OSISAbbreviation,
                                                    "SwordAbbreviation":SwordAbbreviation, "CCELNumberString":CCELNumberString,
                                                    "USFMAbbreviation":USFMAbbreviation, "USFMNumberString":USFMNumberString, "USXNumberString":USXNumberString,
                                                    "UnboundCodeString":UnboundCodeString, "BibleditNumberString":BibleditNumberString,
                                                    "NETBibleAbbreviation":NETBibleAbbreviation, "ByzantineAbbreviation":ByzantineAbbreviation,
                                                    "numExpectedChapters":expectedChapters, "possibleAlternativeBooks":possibleAlternativeBooks, "nameEnglish":nameEnglish }
            if "referenceNumber" in self._compulsoryElements or ID:
                if "referenceNumber" in self._uniqueElements: assert( intID not in myIDDict ) # Shouldn't be any duplicates
                if intID in myIDDict: halt
                else: myIDDict[intID] = { "referenceAbbreviation":referenceAbbreviation, "SBLAbbreviation":SBLAbbreviation, "OSISAbbreviation":OSISAbbreviation,
                                    "SwordAbbreviation":SwordAbbreviation, "CCELNumberString":CCELNumberString,
                                    "USFMAbbreviation":USFMAbbreviation, "USFMNumberString":USFMNumberString, "USXNumberString":USXNumberString,
                                    "UnboundCodeString":UnboundCodeString, "BibleditNumberString":BibleditNumberString,
                                    "NETBibleAbbreviation":NETBibleAbbreviation, "ByzantineAbbreviation":ByzantineAbbreviation,
                                    "numExpectedChapters":expectedChapters, "possibleAlternativeBooks":possibleAlternativeBooks, "nameEnglish":nameEnglish }
            if "sequenceNumber" in self._compulsoryElements or sequenceNumber:
                if "sequenceNumber" in self._uniqueElements: assert( intSequenceNumber not in sequenceNumberList ) # Shouldn't be any duplicates
                if intSequenceNumber in sequenceNumberList: halt
                else:
                    sequenceNumberList.append( intSequenceNumber ) # Only used for checking duplicates
                    sequenceTupleList.append( (intSequenceNumber,referenceAbbreviation,) ) # We'll sort this later
            if "SBLAbbreviation" in self._compulsoryElements or SBLAbbreviation:
                if "SBLAbbreviation" in self._uniqueElements: assert( SBLAbbreviation not in myOADict ) # Shouldn't be any duplicates
                UCAbbreviation = SBLAbbreviation.upper()
                if UCAbbreviation in mySBLDict: mySBLDict[UCAbbreviation] = ( intID, makeList(mySBLDict[UCAbbreviation][1],referenceAbbreviation), )
                else: mySBLDict[UCAbbreviation] = ( intID, referenceAbbreviation, )
                if UCAbbreviation in allAbbreviationsDict and allAbbreviationsDict[UCAbbreviation] != referenceAbbreviation:
                    logging.info( _("This SBL '{}' abbreviation ({}) already assigned to '{}'").format( UCAbbreviation, referenceAbbreviation, allAbbreviationsDict[UCAbbreviation] ) )
                    allAbbreviationsDict[UCAbbreviation] = "MultipleValues"
                else: allAbbreviationsDict[UCAbbreviation] = referenceAbbreviation
            if "OSISAbbreviation" in self._compulsoryElements or OSISAbbreviation:
                if "OSISAbbreviation" in self._uniqueElements: assert( OSISAbbreviation not in myOADict ) # Shouldn't be any duplicates
                UCAbbreviation = OSISAbbreviation.upper()
                if UCAbbreviation in myOADict: myOADict[UCAbbreviation] = ( intID, makeList(myOADict[UCAbbreviation][1],referenceAbbreviation), )
                else: myOADict[UCAbbreviation] = ( intID, referenceAbbreviation, )
                if UCAbbreviation in allAbbreviationsDict and allAbbreviationsDict[UCAbbreviation] != referenceAbbreviation:
                    logging.info( _("This OSIS '{}' abbreviation ({}) already assigned to '{}'").format( UCAbbreviation, referenceAbbreviation, allAbbreviationsDict[UCAbbreviation] ) )
                    allAbbreviationsDict[UCAbbreviation] = "MultipleValues"
                else: allAbbreviationsDict[UCAbbreviation] = referenceAbbreviation
            if "SwordAbbreviation" in self._compulsoryElements or SwordAbbreviation:
                if "SwordAbbreviation" in self._uniqueElements: assert( SwordAbbreviation not in mySwDict ) # Shouldn't be any duplicates
                UCAbbreviation = SwordAbbreviation.upper()
                if UCAbbreviation in mySwDict: mySwDict[UCAbbreviation] = ( intID, makeList(mySwDict[UCAbbreviation][1],referenceAbbreviation), )
                else: mySwDict[UCAbbreviation] = ( intID, referenceAbbreviation, )
                if UCAbbreviation in allAbbreviationsDict and allAbbreviationsDict[UCAbbreviation] != referenceAbbreviation:
                    logging.info( _("This Sword '{}' abbreviation ({}) already assigned to '{}'").format( UCAbbreviation, referenceAbbreviation, allAbbreviationsDict[UCAbbreviation] ) )
                    allAbbreviationsDict[UCAbbreviation] = "MultipleValues"
                else: allAbbreviationsDict[UCAbbreviation] = referenceAbbreviation
            if "CCELNumberString" in self._compulsoryElements or CCELNumberString:
                if "CCELNumberString" in self._uniqueElements: assert( CCELNumberString not in myCCELDict ) # Shouldn't be any duplicates
                UCNumberString = CCELNumberString.upper()
                if UCNumberString in myCCELDict: myCCELDict[UCNumberString] = ( intID, makeList(myCCELDict[UCNumberString][1],referenceAbbreviation), )
                else: myCCELDict[UCNumberString] = ( intID, referenceAbbreviation, )
            if "USFMAbbreviation" in self._compulsoryElements or USFMAbbreviation:
                if "USFMAbbreviation" in self._uniqueElements: assert( USFMAbbreviation not in myUSFMAbbrDict ) # Shouldn't be any duplicates
                UCAbbreviation = USFMAbbreviation.upper()
                if UCAbbreviation in myUSFMAbbrDict: myUSFMAbbrDict[UCAbbreviation] = ( intID, makeList(myUSFMAbbrDict[UCAbbreviation][1],referenceAbbreviation), makeList(myUSFMAbbrDict[UCAbbreviation][2],USFMNumberString), )
                else: myUSFMAbbrDict[UCAbbreviation] = ( intID, referenceAbbreviation, USFMNumberString, )
                if UCAbbreviation in allAbbreviationsDict and allAbbreviationsDict[UCAbbreviation] != referenceAbbreviation:
                    logging.error( _("This USFM '{}' abbreviation ({}) already assigned to '{}'").format( UCAbbreviation, referenceAbbreviation, allAbbreviationsDict[UCAbbreviation] ) )
                    allAbbreviationsDict[UCAbbreviation] = "MultipleValues"
                else: allAbbreviationsDict[UCAbbreviation] = referenceAbbreviation
            if "USFMNumberString" in self._compulsoryElements or USFMNumberString:
                if "USFMNumberString" in self._uniqueElements: assert( USFMNumberString not in myUSFMNDict ) # Shouldn't be any duplicates
                UCNumberString = USFMNumberString.upper()
                if UCNumberString in myUSFMNDict: myUSFMNDict[UCNumberString] = ( intID, makeList(myUSFMNDict[UCNumberString][1],referenceAbbreviation), makeList(myUSFMNDict[UCNumberString][2],USFMAbbreviation), )
                else: myUSFMNDict[UCNumberString] = ( intID, referenceAbbreviation, USFMAbbreviation, )
            if "USXNumberString" in self._compulsoryElements or USXNumberString:
                if "USXNumberString" in self._uniqueElements: assert( USXNumberString not in myUSXNDict ) # Shouldn't be any duplicates
                UCNumberString = USXNumberString.upper()
                if UCNumberString in myUSXNDict: halt
                else: myUSXNDict[UCNumberString] = ( intID, referenceAbbreviation, USFMAbbreviation, )
            if "UnboundCodeString" in self._compulsoryElements or UnboundCodeString:
                if "UnboundCodeString" in self._uniqueElements: assert( UnboundCodeString not in myUCDict ) # Shouldn't be any duplicates
                UCCodeString = UnboundCodeString.upper()
                assert( len(UCCodeString)==3 and UCCodeString[0].isdigit() and UCCodeString[1].isdigit() and UCCodeString[2] in ('N','O','A') )
                if UCCodeString in myUCDict: print( UCCodeString, myUCDict ); halt
                else: myUCDict[UCCodeString] = ( intID, referenceAbbreviation, USFMAbbreviation, )
            if "BibleditNumberString" in self._compulsoryElements or BibleditNumberString:
                if "BibleditNumberString" in self._uniqueElements: assert( BibleditNumberString not in myBENDict ) # Shouldn't be any duplicates
                UCNumberString = BibleditNumberString.upper()
                if UCNumberString in myBENDict: print( UCNumberString, myBENDict ); halt
                else: myBENDict[UCNumberString] = ( intID, referenceAbbreviation, USFMAbbreviation, )
            if "NETBibleAbbreviation" in self._compulsoryElements or NETBibleAbbreviation:
                if "NETBibleAbbreviation" in self._uniqueElements: assert( NETBibleAbbreviation not in myBzDict ) # Shouldn't be any duplicates
                UCAbbreviation = NETBibleAbbreviation.upper()
                if UCAbbreviation in myNETDict: myNETDict[UCAbbreviation] = ( intID, makeList(myNETDict[UCAbbreviation][1],referenceAbbreviation), )
                else: myNETDict[UCAbbreviation] = ( intID, referenceAbbreviation, )
                if UCAbbreviation in allAbbreviationsDict and allAbbreviationsDict[UCAbbreviation] != referenceAbbreviation:
                    logging.info( _("This NET Bible '{}' abbreviation ({}) already assigned to '{}'").format( UCAbbreviation, referenceAbbreviation, allAbbreviationsDict[UCAbbreviation] ) )
                    allAbbreviationsDict[UCAbbreviation] = "MultipleValues"
                else: allAbbreviationsDict[UCAbbreviation] = referenceAbbreviation
            if "ByzantineAbbreviation" in self._compulsoryElements or ByzantineAbbreviation:
                if "ByzantineAbbreviation" in self._uniqueElements: assert( ByzantineAbbreviation not in myBzDict ) # Shouldn't be any duplicates
                UCAbbreviation = ByzantineAbbreviation.upper()
                if UCAbbreviation in myBzDict: halt
                else: myBzDict[UCAbbreviation] = ( intID, referenceAbbreviation, )
                if UCAbbreviation in allAbbreviationsDict and allAbbreviationsDict[UCAbbreviation] != referenceAbbreviation:
                    logging.info( _("This Byzantine '{}' abbreviation ({}) already assigned to '{}'").format( UCAbbreviation, referenceAbbreviation, allAbbreviationsDict[UCAbbreviation] ) )
                    allAbbreviationsDict[UCAbbreviation] = "MultipleValues"
                else: allAbbreviationsDict[UCAbbreviation] = referenceAbbreviation
            if "nameEnglish" in self._compulsoryElements or USFMNumberString:
                if "nameEnglish" in self._uniqueElements: assert( nameEnglish not in myENDict ) # Shouldn't be any duplicates
                UCName = nameEnglish.upper()
                if UCName in myENDict: halt
                else: myENDict[UCName] = ( intID, referenceAbbreviation )
        for BBB in myRefAbbrDict: # Do some cross-checking
            if myRefAbbrDict[BBB]["possibleAlternativeBooks"]:
                for possibility in myRefAbbrDict[BBB]["possibleAlternativeBooks"]:
                    if possibility not in myRefAbbrDict:
                        logging.error( _("Possible alternative books for '{}' contains invalid '{}' entry").format( BBB, possibility ) )
        adjAllAbbreviationsDict = {}
        for abbreviation, value in allAbbreviationsDict.items(): # Remove useless entries
            if value != "MultipleValues": adjAllAbbreviationsDict[abbreviation] = value
        sequenceList = [BBB for seqNum,BBB in sorted(sequenceTupleList)] # Get the book reference codes in order but discard the sequence numbers which have no absolute meaning
        self.__DataDicts = { "referenceNumberDict":myIDDict, "referenceAbbreviationDict":myRefAbbrDict, "sequenceList":sequenceList,
                        "SBLAbbreviationDict":mySBLDict, "OSISAbbreviationDict":myOADict, "SwordAbbreviationDict":mySwDict,
                        "CCELDict":myCCELDict, "USFMAbbreviationDict":myUSFMAbbrDict, "USFMNumberDict":myUSFMNDict,
                        "USXNumberDict":myUSXNDict, "UnboundCodeDict":myUCDict, "BibleditNumberDict":myBENDict,
                        "NETBibleAbbreviationDict":myNETDict, "ByzantineAbbreviationDict":myBzDict,
                        "EnglishNameDict":myENDict, "allAbbreviationsDict":adjAllAbbreviationsDict }

        #if 0:
            ## Print available reference book numbers
            #free = []
            #for num in range(1, 1000):
                #if num not in myIDDict:
                    #if free: # Already have some -- collect ranges
                        #if isinstance(free[-1], int):
                            #if free[-1]==num-1: free.append( (free.pop(), num) ); continue
                        #else:
                            #s,f = free[-1]
                            #if f==num-1: free.pop(); free.append( (s, num) ); continue
                    #free.append( num )
            #print( "Free reference numbers = {}".format( free ) )
            #free = [] # Print available sequence numbers
            #for num in range(1, 1000):
                #if num not in sequenceNumberList:
                    #if free: # Already have some -- collect ranges
                        #if isinstance(free[-1], int):
                            #if free[-1]==num-1: free.append( (free.pop(), num) ); continue
                        #else:
                            #s,f = free[-1]
                            #if f==num-1: free.pop(); free.append( (s, num) ); continue
                    #free.append( num )
            #print( "Free sequence numbers = {}".format( free ) )

            ## Compare OSIS and Sword entries
            #print( "referenceNumberDict", len(myIDDict), myIDDict[1] )
            #print( "referenceAbbreviationDict", len(myRefAbbrDict), myRefAbbrDict['GEN'] )
            #print( "OSISAbbreviationDict", len(myOADict) ) #myOADict )
            #print( "SwordAbbreviationDict", len(mySwDict) ) #mySwDict )
            #for num, entry in myIDDict.items():
                #if entry['SwordAbbreviation']!=entry['OSISAbbreviation']:
                    #print( "{} {} OSIS='{}' Sword='{}'".format( num, entry['referenceAbbreviation'], entry['OSISAbbreviation'], entry['SwordAbbreviation'] ) )

        return self.__DataDicts # Just delete any of the dictionaries that you don't need
    # end of BibleBooksCodesConverter.importDataToPython


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
    # end of BibleBooksCodesConverter.pickle


    def exportDataToPython( self, filepath=None ):
        """
        Writes the information tables to a .py file that can be cut and pasted into a Python program.
        """
        def exportPythonDictOrList( theFile, theDictOrList, dictName, keyComment, fieldsComment ):
            """Exports theDictOrList to theFile."""
            assert( theDictOrList )
            raise Exception( "Not written yet" )
            for dictKey in theDict.keys(): # Have to iterate this :(
                fieldsCount = len( theDict[dictKey] )
                break # We only check the first (random) entry we get
            theFile.write( "{} = {{\n  # Key is {}\n  # Fields ({}) are: {}\n".format( dictName, keyComment, fieldsCount, fieldsComment ) )
            for dictKey in sorted(theDict.keys()):
                theFile.write( '  {}: {},\n'.format( repr(dictKey), repr(theDict[dictKey]) ) )
            theFile.write( "}}\n# end of {} ({} entries)\n\n".format( dictName, len(theDict) ) )
        # end of exportPythonDictOrList


        assert( self._XMLtree )
        self.importDataToPython()
        assert( self.__DataDicts )

        if not filepath:
            folder = os.path.join( os.path.split(self.__XMLFilepath)[0], "DerivedFiles/" )
            if not os.path.exists( folder ): os.mkdir( folder )
            filepath = os.path.join( folder, self._filenameBase + "_Tables.py" )
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
                            "sequenceList":("referenceAbbreviation/BBB (3-uppercase characters)",""),
                            "CCELDict":("CCELNumberString", mostEntries), "SBLAbbreviationDict":("SBLAbbreviation", mostEntries), "OSISAbbreviationDict":("OSISAbbreviation", mostEntries), "SwordAbbreviationDict":("SwordAbbreviation", mostEntries),
                            "USFMAbbreviationDict":("USFMAbbreviation", "0=referenceNumber (integer 1..255), 1=referenceAbbreviation/BBB (3-uppercase characters), 2=USFMNumberString (2-characters)"),
                            "USFMNumberDict":("USFMNumberString", "0=referenceNumber (integer 1..255), 1=referenceAbbreviation/BBB (3-uppercase characters), 2=USFMAbbreviationString (3-characters)"),
                            "USXNumberDict":("USXNumberString", "0=referenceNumber (integer 1..255), 1=referenceAbbreviation/BBB (3-uppercase characters), 2=USFMAbbreviationString (3-characters)"),
                            "UnboundCodeDict":("UnboundCodeString", "0=referenceNumber (integer 1..88), 1=referenceAbbreviation/BBB (3-uppercase characters), 2=USFMAbbreviationString (3-characters)"),
                            "BibleditNumberDict":("BibleditNumberString", "0=referenceNumber (integer 1..88), 1=referenceAbbreviation/BBB (3-uppercase characters), 2=USFMAbbreviationString (3-characters)"),
                            "NETBibleAbbreviationDict":("NETBibleAbbreviation", mostEntries), "ByzantineAbbreviationDict":("ByzantineAbbreviation", mostEntries),
                            "EnglishNameDict":("nameEnglish", mostEntries), "allAbbreviationsDict":("allAbbreviations", mostEntries) }
            for dictName,dictData in self.__DataDicts.items():
                exportPythonDictOrList( myFile, dictData, dictName, dictInfo[dictName][0], dictInfo[dictName][1] )
            myFile.write( "# end of {}".format( os.path.basename(filepath) ) )
    # end of BibleBooksCodesConverter.exportDataToPython


    def exportDataToJSON( self, filepath=None ):
        """
        Writes the information tables to a .json file that can be easily loaded into a Java program.

        See http://en.wikipedia.org/wiki/JSON.
        """
        import json

        assert( self._XMLtree )
        self.importDataToPython()
        assert( self.__DataDicts )

        if not filepath:
            folder = os.path.join( os.path.split(self.__XMLFilepath)[0], "DerivedFiles/" )
            if not os.path.exists( folder ): os.mkdir( folder )
            filepath = os.path.join( folder, self._filenameBase + "_Tables.json" )
        if Globals.verbosityLevel > 1: print( _("Exporting to {}...").format( filepath ) )
        with open( filepath, 'wt' ) as myFile:
            json.dump( self.__DataDicts, myFile, indent=2 )
    # end of BibleBooksCodesConverter.exportDataToJSON


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
                if isinstance( entry, str ):
                    result = entry
                elif isinstance( entry, tuple ):
                    for field in entry:
                        if result: result += ", " # Separate the fields
                        if field is None: result += '""'
                        elif isinstance( field, str): result += '"' + str(field).replace('"','\\"') + '"'
                        elif isinstance( field, int): result += str(field)
                        elif isinstance( field, list): raise Exception( "Not written yet (list1)" )
                        else: logging.error( _("Cannot convert unknown field type '{}' in tuple entry '{}'").format( field, entry ) )
                elif isinstance( entry, dict ):
                    for key in sorted(entry.keys()):
                        field = entry[key]
                        if result: result += ", " # Separate the fields
                        if field is None: result += '""'
                        elif isinstance( field, str): result += '"' + str(field).replace('"','\\"') + '"'
                        elif isinstance( field, int): result += str(field)
                        elif isinstance( field, list): raise Exception( "Not written yet (list2)" )
                        else: logging.error( _("Cannot convert unknown field type '{}' in dict entry '{}'").format( field, entry ) )
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


        assert( self._XMLtree )
        self.importDataToPython()
        assert( self.__DataDicts )

        if not filepath:
            folder = os.path.join( os.path.split(self.__XMLFilepath)[0], "DerivedFiles/" )
            if not os.path.exists( folder ): os.mkdir( folder )
            filepath = os.path.join( folder, self._filenameBase + "_Tables" )
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
                    "{} referenceNumber; {}* ByzantineAbbreviation; {}* CCELNumberString; {}* NETBibleAbbreviation; {}* OSISAbbreviation; {} USFMAbbreviation[3+1]; {} USFMNumberString[2+1]; {}* SBLAbbreviation; {}* SwordAbbreviation; {}* nameEnglish; {}* numExpectedChapters; {}* possibleAlternativeBooks; {} referenceAbbreviation[3+1];"
                   .format(BYTE, CHAR, CHAR, CHAR, CHAR, CHAR, CHAR, CHAR, CHAR, CHAR, CHAR, CHAR, CHAR ) ),
                "referenceAbbreviationDict":("referenceAbbreviation",
                    "{} referenceAbbreviation[3+1]; {}* ByzantineAbbreviation; {}* CCELNumberString; {} referenceNumber; {}* NETBibleAbbreviation; {}* OSISAbbreviation; {} USFMAbbreviation[3+1]; {} USFMNumberString[2+1]; {}* SBLAbbreviation; {}* SwordAbbreviation; {}* nameEnglish; {}* numExpectedChapters; {}* possibleAlternativeBooks;"
                   .format(CHAR, CHAR, CHAR, BYTE, CHAR, CHAR, CHAR, CHAR, CHAR, CHAR, CHAR, CHAR, CHAR ) ),
                "sequenceList":("sequenceList",),
                "CCELDict":("CCELNumberString", "{}* CCELNumberString; {} referenceNumber; {} referenceAbbreviation[3+1];".format(CHAR,BYTE,CHAR) ),
                "SBLAbbreviationDict":("SBLAbbreviation", "{}* SBLAbbreviation; {} referenceNumber; {} referenceAbbreviation[3+1];".format(CHAR,BYTE,CHAR) ),
                "OSISAbbreviationDict":("OSISAbbreviation", "{}* OSISAbbreviation; {} referenceNumber; {} referenceAbbreviation[3+1];".format(CHAR,BYTE,CHAR) ),
                "SwordAbbreviationDict":("SwordAbbreviation", "{}* SwordAbbreviation; {} referenceNumber; {} referenceAbbreviation[3+1];".format(CHAR,BYTE,CHAR) ),
                "USFMAbbreviationDict":("USFMAbbreviation", "{} USFMAbbreviation[3+1]; {} referenceNumber; {} referenceAbbreviation[3+1]; {} USFMNumberString[2+1];".format(CHAR,BYTE,CHAR,CHAR) ),
                "USFMNumberDict":("USFMNumberString", "{} USFMNumberString[2+1]; {} referenceNumber; {} referenceAbbreviation[3+1]; {} USFMAbbreviation[3+1];".format(CHAR,BYTE,CHAR,CHAR) ),
                "USXNumberDict":("USXNumberString", "{} USXNumberString[3+1]; {} referenceNumber; {} referenceAbbreviation[3+1]; {} USFMAbbreviation[3+1];".format(CHAR,BYTE,CHAR,CHAR) ),
                "UnboundCodeDict":("UnboundCodeString", "{} UnboundCodeString[3+1]; {} referenceNumber; {} referenceAbbreviation[3+1]; {} USFMAbbreviation[3+1];".format(CHAR,BYTE,CHAR,CHAR) ),
                "BibleditNumberDict":("BibleditNumberString", "{} BibleditNumberString[2+1]; {} referenceNumber; {} referenceAbbreviation[3+1]; {} USFMAbbreviation[3+1];".format(CHAR,BYTE,CHAR,CHAR) ),
                "NETBibleAbbreviationDict":("NETBibleAbbreviation", "{}* NETBibleAbbreviation; {} referenceNumber; {} referenceAbbreviation[3+1];".format(CHAR,BYTE,CHAR) ),
                "ByzantineAbbreviationDict":("ByzantineAbbreviation", "{}* ByzantineAbbreviation; {} referenceNumber; {} referenceAbbreviation[3+1];".format(CHAR,BYTE,CHAR) ),
                "EnglishNameDict":("nameEnglish", "{}* nameEnglish; {} referenceNumber; {} referenceAbbreviation[3+1];".format(CHAR,BYTE,CHAR) ),
                "allAbbreviationsDict":("abbreviation", "{}* abbreviation; {} referenceAbbreviation[3+1];".format(CHAR,CHAR) ) }

            for dictName,dictData in self.__DataDicts.items():
                exportPythonDict( myHFile, myCFile, dictData, dictName, dictInfo[dictName][0], dictInfo[dictName][1] )

            myHFile.write( "#endif // {}\n\n".format( ifdefName ) )
            myHFile.write( "// end of {}".format( os.path.basename(hFilepath) ) )
            myCFile.write( "// end of {}".format( os.path.basename(cFilepath) ) )
    # end of BibleBooksCodesConverter.exportDataToC
# end of BibleBooksCodesConverter class



def demo():
    """
    Main program to handle command line parameters and then run what they want.
    """
    # Configure basic logging
    logging.basicConfig( format='%(levelname)s: %(message)s', level=logging.INFO ) # Removes the unnecessary and unhelpful 'root:' part of the logged messages

    # Handle command line parameters
    from optparse import OptionParser
    parser = OptionParser( version="v{}".format( versionString ) )
    parser.add_option("-e", "--export", action="store_true", dest="export", default=False, help="export the XML file to .py and .h/.c formats suitable for directly including into other programs, as well as .json.")
    Globals.addStandardOptionsAndProcess( parser )

    if Globals.verbosityLevel > 1: print( "{} V{}".format( progName, versionString ) )

    if Globals.commandLineOptions.export:
        bbcc = BibleBooksCodesConverter().loadAndValidate() # Load the XML
        bbcc.pickle() # Produce a pickle output file
        bbcc.exportDataToPython() # Produce the .py tables
        bbcc.exportDataToJSON() # Produce a json output file
        bbcc.exportDataToC() # Produce the .h and .c tables

    else: # Must be demo mode
        # Demo the converter object
        bbcc = BibleBooksCodesConverter().loadAndValidate() # Load the XML
        print( bbcc ) # Just print a summary
# end of demo

if __name__ == '__main__':
    demo()
# end of BibleBooksCodesConverter.py