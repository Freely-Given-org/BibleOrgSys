#!/usr/bin/env -S uv run
# -\*- coding: utf-8 -\*-
# SPDX-License-Identifier: GPL-3.0-or-later
#
# BibleReferencesLinksConverter.py
#
# Module handling BibleReferencesLinks.xml to produce C and Python data tables
#
# Copyright (C) 2015-2021 Robert Hunt
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
Module handling BibleReferencesLinks.xml and to export to JSON, C, and Python data tables.
"""
import logging
import os.path
from datetime import datetime
from xml.etree.ElementTree import ElementTree

from BibleOrgSys.Misc.singleton import singleton
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys.Reference.BibleOrganisationalSystems import BibleOrganisationalSystem
#from BibleReferences import BibleSingleReference, BibleReferenceList
from BibleOrgSys.Reference.VerseReferences import SimpleVerseKey, FlexibleVersesKey


LAST_MODIFIED_DATE = '2021-01-19' # by RJH
SHORT_PROGRAM_NAME = "BibleReferencesLinksConverter"
PROGRAM_NAME = "Bible References Links converter"
PROGRAM_VERSION = '0.41'
PROGRAM_NAME_VERSION = f'{PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False



@singleton # Can only ever have one instance
class BibleReferencesLinksConverter:
    """
    Class for reading, validating, and converting BibleReferencesLinks.
    This is only intended as a transitory class (used at start-up).
    The BibleReferencesLinks class has functions more generally useful.
    """

    def __init__( self ) -> None: # We can't give this parameters because of the singleton
        """
        Constructor: expects the filepath of the source XML file.
        Loads (and crudely validates the XML file) into an element tree.
        """
        self._filenameBase = 'BibleReferencesLinks'

        # These fields are used for parsing the XML
        self._treeTag = 'BibleReferencesLinks'
        self._headerTag = 'header'
        self._mainElementTag = 'BibleReferenceLinks'

        # These fields are used for automatically checking/validating the XML
        self._compulsoryAttributes = ()
        self._optionalAttributes = ()
        self._uniqueAttributes = self._compulsoryAttributes + self._optionalAttributes
        self._compulsoryElements = ( 'sourceReference', 'sourceComponent', 'BibleReferenceLink', )
        self._optionalElements = (  )
        self._uniqueElements = ( 'sourceReference' )

        # These are fields that we will fill later
        self._XMLheader, self._XMLTree = None, None
        self.__DataList = {} # Used for import
        self.titleString = self.PROGRAM_VERSION = self.dateString = ''
    # end of BibleReferencesLinksConverter.__init__


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
            if XMLFileOrFilepath is not None and XMLFileOrFilepath!=self.__XMLFileOrFilepath: logging.error( f"Bible references links are already loaded -- your different filepath of {XMLFileOrFilepath!r} was ignored" )
        return self
    # end of BibleReferencesLinksConverter.loadAndValidate


    def __load( self, XMLFileOrFilepath ):
        """
        Load the source XML file and remove the header from the tree.
        Also, extracts some useful elements from the header element.
        """
        assert XMLFileOrFilepath
        self.__XMLFileOrFilepath = XMLFileOrFilepath
        assert self._XMLTree is None or len(self._XMLTree)==0 # Make sure we're not doing this twice

        vPrint( 'Info', DEBUGGING_THIS_MODULE, f"Loading BibleReferencesLinks XML file from {self.__XMLFileOrFilepath!r}…" )
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
            if header.tail is not None and header.tail.strip(): logging.error( f"Unexpected {header.tail!r} tail data after header" )
        else:
            logging.error( f"Expected to load {self._treeTag!r} but got {self._XMLTree.tag!r}" )
    # end of BibleReferencesLinksConverter.__load


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

                # Get the sourceComponent to use as a record ID
                ID = element.find("sourceComponent").text

                # Check compulsory elements
                for elementName in self._compulsoryElements:
                    foundElement = element.find( elementName )
                    if foundElement is None:
                        logging.error( f"Compulsory {ID!r} element is missing in record with ID {j!r} (record {elementName})" )
                    else:
                        BibleOrgSysGlobals.checkXMLNoTail( foundElement, foundElement.tag + " in " + element.tag )
                        BibleOrgSysGlobals.checkXMLNoAttributes( foundElement, foundElement.tag + " in " + element.tag )
                        #BibleOrgSysGlobals.checkXMLNoSubelements( foundElement, foundElement.tag + " in " + element.tag )
                        if not foundElement.text:
                            logging.warning( f"Compulsory {ID!r} element is blank in record with ID {j!r} (record {elementName})" )

                # Check optional elements
                for elementName in self._optionalElements:
                    foundElement = element.find( elementName )
                    if foundElement is not None:
                        BibleOrgSysGlobals.checkXMLNoTail( foundElement, foundElement.tag + " in " + element.tag )
                        BibleOrgSysGlobals.checkXMLNoAttributes( foundElement, foundElement.tag + " in " + element.tag )
                        BibleOrgSysGlobals.checkXMLNoSubelements( foundElement, foundElement.tag + " in " + element.tag )
                        if not foundElement.text:
                            logging.warning( f"Optional {ID!r} element is blank in record with ID {j!r} (record {elementName})" )

                # Check for unexpected additional elements
                for subelement in element:
                    if subelement.tag not in self._compulsoryElements and subelement.tag not in self._optionalElements:
                        logging.warning( f"Additional {subelement.text!r} element ({ID!r}) found in record with ID {j!r} (record {subelement.tag})" )

                # Check the elements that must contain unique information (in that particular element -- doesn't check across different elements)
                for elementName in self._uniqueElements:
                    if element.find( elementName ) is not None:
                        text = element.find( elementName ).text
                        if text in uniqueDict["Element_"+elementName]:
                            logging.error( f"Found {elementName!r} data repeated in {ID!r} element in record with ID {j!r} (record {text})" )
                        uniqueDict["Element_"+elementName].append( text )
            else:
                logging.warning( f"Unexpected element: {element.tag} in record {j}" )
            if element.tail is not None and element.tail.strip(): logging.error( f"Unexpected {j!r} tail data after {element.tail} element in record {element.tag}" )
        if self._XMLTree.tail is not None and self._XMLTree.tail.strip(): logging.error( f"Unexpected {self._XMLTree.tag!r} tail data after {self._XMLTree.tail} element" )
    # end of BibleReferencesLinksConverter.__validate


    def __str__( self ) -> str:
        """
        This method returns the string representation of a Bible book code.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        indent = 2
        result = "BibleReferencesLinksConverter object"
        if self.titleString: result += ('\n' if result else '') + ' '*indent + f"Title: {self.titleString}"
        if self.PROGRAM_VERSION: result += ('\n' if result else '') + ' '*indent + f"Version: {self.PROGRAM_VERSION}"
        if self.dateString: result += ('\n' if result else '') + ' '*indent + f"Date: {self.dateString}"
        if self._XMLTree is not None: result += ('\n' if result else '') + ' '*indent + f"Number of entries = {len(self._XMLTree):,}"
        return result
    # end of BibleReferencesLinksConverter.__str__


    def __len__( self ):
        """
        Returns the number of references links loaded.
        """
        return len( self._XMLTree )
    # end of BibleReferencesLinksConverter.__len__


    def importDataToPython( self ):
        """
        Loads (and pivots) the data (not including the header) into suitable Python containers to use in a Python program.
        (Of course, you can just use the elementTree in self._XMLTree if you prefer.)
        """
        def makeList( parameter1, parameter2 ):
            """
            Returns a list containing all parameters. Parameter1 may already be a list.
            """
            if isinstance( parameter1, list ):
                #assert parameter2 not in parameter1
                parameter1.append( parameter2 )
                return parameter1
            else:
                return [ parameter1, parameter2 ]
        # end of makeList


        assert len(self._XMLTree)
        if self.__DataList: # We've already done an import/restructuring -- no need to repeat it
            return self.__DataList, self.__DataDict

        # We'll create a number of dictionaries with different elements as the key
        rawRefLinkList = []
        actualLinkCount = 0
        for element in self._XMLTree:
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, BibleOrgSysGlobals.elementStr( element ) )

            # Get these first for helpful error messages
            sourceReference = element.find('sourceReference').text
            sourceComponent = element.find('sourceComponent').text
            assert sourceComponent in ('Section','Verses','Verse',)

            BibleOrgSysGlobals.checkXMLNoText( element, sourceReference, 'kls1' )
            BibleOrgSysGlobals.checkXMLNoAttributes( element, sourceReference, 'kd21' )
            BibleOrgSysGlobals.checkXMLNoTail( element, sourceReference, 'so20' )

            actualRawLinksList = []
            for subelement in element:
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, BibleOrgSysGlobals.elementStr( subelement ) )
                if subelement.tag in ( 'sourceReference','sourceComponent',): # already processed these
                    BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sourceReference, 'ls12' )
                    BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sourceReference, 'ks02' )
                    BibleOrgSysGlobals.checkXMLNoTail( subelement, sourceReference, 'sqw1' )

                elif subelement.tag == 'BibleReferenceLink':
                    BibleOrgSysGlobals.checkXMLNoText( subelement, sourceReference, 'haw9' )
                    BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sourceReference, 'hs19' )
                    BibleOrgSysGlobals.checkXMLNoTail( subelement, sourceReference, 'jsd9' )

                    targetReference = subelement.find('targetReference').text
                    targetComponent = subelement.find('targetComponent').text
                    assert targetComponent in ('Section','Verses','Verse',)
                    linkType = subelement.find('linkType').text
                    assert linkType in ('TSK','QuotedOTReference','AlludedOTReference','PossibleOTReference',)

                    actualRawLinksList.append( (targetReference,targetComponent,linkType,) )
                    actualLinkCount += 1

            rawRefLinkList.append( (sourceReference,sourceComponent,actualRawLinksList,) )

        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  {len(rawRefLinkList):,} raw links loaded (with {actualLinkCount:,} actual raw link entries)" )


        myRefLinkList = []
        actualLinkCount = 0
        BOS = BibleOrganisationalSystem( 'GENERIC-KJV-66-ENG' )

        for j,(sourceReference,sourceComponent,actualRawLinksList) in enumerate( rawRefLinkList ):
            # Just do some testing first
            if sourceComponent == 'Verse':
                x = SimpleVerseKey( sourceReference )
            else:
                flag = False
                try:
                    x = SimpleVerseKey( sourceReference, ignoreParseErrors=True )
                    flag = True
                except TypeError: pass # This should happen coz it should fail the SVK
                if flag:
                    logging.error( f"{sourceComponent} {sourceReference!r} failed!" )
                    raise TypeError
            # Now do the actual parsing
            parsedSourceReference = FlexibleVersesKey( sourceReference )
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"{j:,} sC={sourceComponent} sR={sourceReference} pSR={parsedSourceReference}" )
                #assert parsedSourceReference.getShortText().replace(' ','_') == sourceReference
            actualLinksList = []
            for k,(targetReference,targetComponent,linkType) in enumerate( actualRawLinksList ):
                # Just do some testing first
                if targetComponent == 'Verse':
                    x = SimpleVerseKey( targetReference )
                else:
                    flag = False
                    try:
                        x = SimpleVerseKey( targetReference, ignoreParseErrors=True )
                        flag = True
                    except TypeError: pass # This should happen coz it should fail the SVK
                    if flag:
                        logging.error( f"{targetComponent} {targetReference!r} failed!" )
                        raise TypeError
                # Now do the actual parsing
                try: parsedTargetReference = FlexibleVersesKey( targetReference )
                except TypeError:
                    logging.error( f"  Temporarily ignored {targetReference!r} (TypeError from FlexibleVersesKey)" )
                    parsedTargetReference = None
                vPrint( 'Verbose', DEBUGGING_THIS_MODULE, ' ', targetComponent, targetReference, parsedTargetReference )
                # if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE:
                #     assert parsedTargetReference.getShortText().replace(' ','_',1) == targetReference

                actualLinksList.append( (targetReference,targetComponent,parsedTargetReference,linkType,) )
                actualLinkCount += 1

            myRefLinkList.append( (sourceReference,sourceComponent,parsedSourceReference,actualLinksList,) )

        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"  {len(rawRefLinkList):,} links processed (with {actualLinkCount:,} actual link entries)" )
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, myRefLinkList ); halt
        self.__DataList = myRefLinkList

        # Now put it into my dictionaries for easy access
        # This part should be customized or added to for however you need to process the data

        # Create a link dictionary (by verse key)
        myRefLinkDict = {}
        for sourceReference,sourceComponent,parsedSourceReference,actualLinksList in myRefLinkList:
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, sourceReference, sourceComponent, parsedSourceReference )
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, sourceReference, sourceComponent, parsedSourceReference, actualLinksList )
            for verseRef in parsedSourceReference.getIncludedVerses():
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, verseRef )
                assert isinstance( verseRef, SimpleVerseKey )
                if verseRef not in myRefLinkDict: myRefLinkDict[verseRef] = []
                myRefLinkDict[verseRef].append( (sourceReference,sourceComponent,parsedSourceReference,actualLinksList,) )
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, myRefLinkDict ); halt
        originalLinks = len( myRefLinkDict )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  {originalLinks:,} verse links added to dictionary (includes filling out spans)" )
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, myRefLinkDict ); halt

        # Create a reversed link dictionary (by verse key)
        for sourceReference,sourceComponent,parsedSourceReference,actualLinksList in myRefLinkList:
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, sourceReference, sourceComponent, parsedSourceReference )
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, sourceReference, sourceComponent, parsedSourceReference, actualLinksList )
            for targetReference,targetComponent,parsedTargetReference,linkType in actualLinksList:
                if parsedTargetReference is not None:
                    for verseRef in parsedTargetReference.getIncludedVerses():
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, verseRef )
                        assert isinstance( verseRef, SimpleVerseKey )
                        if linkType == 'TSK': reverseLinkType = 'TSKQuoted'
                        elif linkType == 'QuotedOTReference': reverseLinkType = 'OTReferenceQuoted'
                        elif linkType == 'AlludedOTReference': reverseLinkType = 'OTReferenceAlluded'
                        elif linkType == 'PossibleOTReference': reverseLinkType = 'OTReferencePossible'
                        else: halt # Have a new linkType!
                        if verseRef not in myRefLinkDict: myRefLinkDict[verseRef] = []
                        myRefLinkDict[verseRef].append( (targetReference,targetComponent,parsedTargetReference,[(sourceReference,sourceComponent,parsedSourceReference,reverseLinkType)]) )
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, myRefLinkDict ); halt
        totalLinks = len( myRefLinkDict )
        reverseLinks = totalLinks - originalLinks
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  {reverseLinks:,} reverse links added to dictionary to give {totalLinks:,} total" )
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, myRefLinkDict ); halt

        self.__DataDict = myRefLinkDict

        # Let's find the most number of references for a verse
        mostReferences = totalReferences = 0
        for verseRef, entryList in self.__DataDict.items():
            numRefs = len( entryList )
            if numRefs > mostReferences: mostReferences, mostVerseRef = numRefs, verseRef
            totalReferences += numRefs
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  {mostReferences:,} maximum links for any one reference ({mostVerseRef.getShortText()})" )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  {totalReferences:,} total links for all references" )

        return self.__DataList, self.__DataDict
    # end of BibleReferencesLinksConverter.importDataToPython


    def pickle( self, filepath=None ):
        """
        Writes the information tables to a .pickle file that can be easily loaded into a Python3 program.
        """
        import pickle

        assert len(self._XMLTree)
        self.importDataToPython()
        assert self.__DataList
        assert self.__DataDict

        if not filepath:
            folder = BibleOrgSysGlobals.DEFAULT_WRITEABLE_DERIVED_DATAFILES_FOLDERPATH
            if not os.path.exists( folder ): os.mkdir( folder )
            filepath = os.path.join( folder, self._filenameBase + '_Tables.pickle' )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Exporting to {filepath}…" )
        with open( filepath, 'wb' ) as myFile:
            pickle.dump( self.__DataList, myFile )
            pickle.dump( self.__DataDict, myFile )
    # end of BibleReferencesLinksConverter.pickle


    def exportDataWithIndex( self, filepath=None ):
        """
        Writes the information tables to a .pickle index file and .json file that can be easily loaded into a Java program.

        See http://en.wikipedia.org/wiki/JSON.
        """
        import pickle

        assert len(self._XMLTree)
        self.importDataToPython()
        assert self.__DataList
        assert self.__DataDict

        if not filepath:
            folder = BibleOrgSysGlobals.DEFAULT_WRITEABLE_DERIVED_DATAFILES_FOLDERPATH
            if not os.path.exists( folder ): os.mkdir( folder )
            indexFilepath = os.path.join( folder, self._filenameBase + '_Tables.index.pickle' )
            dataFilepath = os.path.join( folder, self._filenameBase + '_Tables.data.pickle' )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Exporting to {dataFilepath}…" )
        index = {}
        filePosition = 0
        with open( dataFilepath, 'wb' ) as myFile:
            for vKey,refList in self.__DataDict.items():
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "vKey", vKey, vKey.getVerseKeyText() )
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, " ", refList )
                length = myFile.write( pickle.dumps( refList ) )
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, " ", filePosition, length )
                assert vKey not in index
                index[vKey] = (filePosition, length )
                filePosition += length
        with open( indexFilepath, 'wb' ) as myFile:
            pickle.dump( index, myFile )
    # end of BibleReferencesLinksConverter.exportDataWithIndex


    def exportDataToPython( self, filepath=None ):
        """
        Writes the information tables to a .py file that can be cut and pasted into a Python program.
        """
        def exportPythonDictOrList( theFile, theDictOrList, dictName, keyComment, fieldsComment ):
            """Exports theDictOrList to theFile."""
            assert theDictOrList
            raise Exception( "Not written yet" )
            for dictKey in theDict.keys(): # Have to iterate this :(
                fieldsCount = len( theDict[dictKey] )
                break # We only check the first (random) entry we get
            theFile.write( f"{dictName} = {{\n  # Key is {keyComment}\n  # Fields ({fieldsCount}) are: {fieldsComment}\n" )
            for dictKey in sorted(theDict.keys()):
                theFile.write( f'  {repr(dictKey)}: {repr(theDict[dictKey])},\n' )
            theFile.write( f"}}\n# end of {dictName} ({len(theDict)} entries)\n\n" )
        # end of exportPythonDictOrList


        assert len(self._XMLTree)
        self.importDataToPython()
        assert self.__DataList
        assert self.__DataDict

        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Export to Python not written yet!" )
        halt

        if not filepath:
            folder = BibleOrgSysGlobals.DEFAULT_WRITEABLE_DERIVED_DATAFILES_FOLDERPATH
            if not os.path.exists( folder ): os.mkdir( folder )
            filepath = os.path.join( folder, self._filenameBase + '_Tables.py' )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Exporting to {filepath}…" )
        with open( filepath, 'wt', encoding='utf-8' ) as myFile:
            myFile.write( f"# {filepath}\n#\n" )
            myFile.write( f"# This UTF-8 file was automatically generated by BibleReferencesLinks.py V{PROGRAM_VERSION} on {datetime.now()}\n#\n" )
            if self.titleString: myFile.write( f"# {self.titleString} data\n" )
            if self.PROGRAM_VERSION: myFile.write( f"#  Version: {self.PROGRAM_VERSION}\n" )
            if self.dateString: myFile.write( f"#  Date: {self.dateString}\n#\n" )
            myFile.write( f"#   {len(self._XMLTree)} {self._treeTag} loaded from the original XML file.\n#\n\n" )
            mostEntries = "0=referenceNumber (integer 1..255), 1=sourceComponent/BBB (3-uppercase characters)"
            dictInfo = { "referenceNumberDict":("referenceNumber (integer 1..255)","specified"),
                    "sourceComponentDict":("sourceComponent","specified"),
                    "sequenceList":("sourceComponent/BBB (3-uppercase characters)",""),
                    "initialAllAbbreviationsDict":("allAbbreviations", mostEntries) }
            for dictName,dictData in self.__DataList.items():
                exportPythonDictOrList( myFile, dictData, dictName, dictInfo[dictName][0], dictInfo[dictName][1] )
            myFile.write( f"# end of {os.path.basename(filepath)}" )
    # end of BibleReferencesLinksConverter.exportDataToPython


    def exportDataToJSON( self, filepath=None ):
        """
        Writes the information tables to a .json file that can be easily loaded into a Java program.

        See http://en.wikipedia.org/wiki/JSON.
        """
        import json

        assert len(self._XMLTree)
        self.importDataToPython()
        assert self.__DataList
        assert self.__DataDict

        if not filepath:
            folder = BibleOrgSysGlobals.DEFAULT_WRITEABLE_DERIVED_DATAFILES_FOLDERPATH
            if not os.path.exists( folder ): os.mkdir( folder )
            filepath = os.path.join( folder, self._filenameBase + '_Tables.json' )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Exporting to {filepath}…" )
        with open( filepath, 'wt', encoding='utf-8' ) as myFile:
            for something in self.__DataList: # temp for debugging … xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Dumping something", something )
                json.dump( something, myFile, ensure_ascii=False, indent=2 )
            json.dump( self.__DataList, myFile, ensure_ascii=False, indent=2 )

            for someKey,someItem in self.__DataDict.items(): # temp for debugging … xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Dumping someKey", someKey )
                json.dump( someKey, myFile, ensure_ascii=False, indent=2 )
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Dumping someItem", someItem )
                json.dump( someItem, myFile, ensure_ascii=False, indent=2 )
            json.dump( self.__DataDict, myFile, ensure_ascii=False, indent=2 )
    # end of BibleReferencesLinksConverter.exportDataToJSON


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
                if isinstance( entry, str ):
                    result = entry
                elif isinstance( entry, tuple ):
                    for field in entry:
                        if result: result += ", " # Separate the fields
                        if field is None: result += '""'
                        elif isinstance( field, str): result += '"' + str(field).replace('"','\\"') + '"'
                        elif isinstance( field, int): result += str(field)
                        elif isinstance( field, list): raise Exception( "Not written yet (list1)" )
                        else: logging.error( f"Cannot convert unknown field type {field!r} in tuple entry {entry!r}" )
                elif isinstance( entry, dict ):
                    for key in sorted(entry.keys()):
                        field = entry[key]
                        if result: result += ", " # Separate the fields
                        if field is None: result += '""'
                        elif isinstance( field, str): result += '"' + str(field).replace('"','\\"') + '"'
                        elif isinstance( field, int): result += str(field)
                        elif isinstance( field, list): raise Exception( "Not written yet (list2)" )
                        else: logging.error( f"Cannot convert unknown field type {field!r} in dict entry {entry!r}" )
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
        assert self.__DataList

        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Export to C not written yet!" )
        halt

        if not filepath:
            folder = BibleOrgSysGlobals.DEFAULT_WRITEABLE_DERIVED_DATAFILES_FOLDERPATH
            if not os.path.exists( folder ): os.mkdir( folder )
            filepath = os.path.join( folder, self._filenameBase + '_Tables' )
        hFilepath = filepath + '.h'
        cFilepath = filepath + '.c'
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Exporting to {cFilepath}…" ) # Don't bother telling them about the .h file
        ifdefName = self._filenameBase.upper() + "_Tables_h"

        with open( hFilepath, 'wt', encoding='utf-8' ) as myHFile, \
             open( cFilepath, 'wt', encoding='utf-8' ) as myCFile:
            myHFile.write( f"// {hFilepath}\n//\n" )
            myCFile.write( f"// {cFilepath}\n//\n" )
            lines = f"// This UTF-8 file was automatically generated by BibleReferencesLinks.py V{PROGRAM_VERSION} on {datetime.now()}\n//\n"
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
                    f"{BYTE} referenceNumber; {CHAR}* ByzantineAbbreviation; {CHAR}* CCELNumberString; {CHAR}* NETBibleAbbreviation; {CHAR}* OSISAbbreviation; {CHAR} USFMAbbreviation[3+1]; {CHAR} USFMNumberString[2+1]; {CHAR}* SBLAbbreviation; {CHAR}* SwordAbbreviation; {CHAR}* sourceReference; {CHAR}* numExpectedChapters; {CHAR}* possibleAlternativeBooks; {CHAR} sourceComponent[3+1];" ),
                "sourceComponentDict":("sourceComponent",
                    f"{CHAR} sourceComponent[3+1]; {CHAR}* ByzantineAbbreviation; {CHAR}* CCELNumberString; {BYTE} referenceNumber; {CHAR}* NETBibleAbbreviation; {CHAR}* OSISAbbreviation; {CHAR} USFMAbbreviation[3+1]; {CHAR} USFMNumberString[2+1]; {CHAR}* SBLAbbreviation; {CHAR}* SwordAbbreviation; {CHAR}* sourceReference; {CHAR}* numExpectedChapters; {CHAR}* possibleAlternativeBooks;" ),
                "sequenceList":("sequenceList",),
                "CCELDict":("CCELNumberString", f"{CHAR}* CCELNumberString; {BYTE} referenceNumber; {CHAR} sourceComponent[3+1];" ),
                "initialAllAbbreviationsDict":("abbreviation", f"{CHAR}* abbreviation; {CHAR} sourceComponent[3+1];" ) }

            for dictName,dictData in self.__DataList.items():
                exportPythonDict( myHFile, myCFile, dictData, dictName, dictInfo[dictName][0], dictInfo[dictName][1] )

            myHFile.write( f"#endif // {ifdefName}\n\n" )
            myHFile.write( f"// end of {os.path.basename(hFilepath)}" )
            myCFile.write( f"// end of {os.path.basename(cFilepath)}" )
    # end of BibleReferencesLinksConverter.exportDataToC
# end of BibleReferencesLinksConverter class



def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    if BibleOrgSysGlobals.commandLineArguments.export:
        brlc = BibleReferencesLinksConverter().loadAndValidate() # Load the XML
        brlc.exportDataWithIndex() # Produce a data file and an index file
        brlc.pickle() # Produce a pickle output file
        #brlc.exportDataToJSON() # Produce a json output file TypeError: Object of type FlexibleVersesKey is not JSON serializable
        #brlc.exportDataToPython() # Produce the .py tables NOT WRITTEN YET
        #brlc.exportDataToC() # Produce the .h and .c tables NOT WRITTEN YET

    else: # Must be demo mode
        # Demo the converter object
        brlc = BibleReferencesLinksConverter().loadAndValidate() # Load the XML
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, brlc ) # Just print a summary
# end of BibleReferencesLinksConverter.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    if BibleOrgSysGlobals.commandLineArguments.export:
        brlc = BibleReferencesLinksConverter().loadAndValidate() # Load the XML
        brlc.exportDataWithIndex() # Produce a data file and an index file
        brlc.pickle() # Produce a pickle output file
        #brlc.exportDataToJSON() # Produce a json output file TypeError: Object of type FlexibleVersesKey is not JSON serializable
        #brlc.exportDataToPython() # Produce the .py tables NOT WRITTEN YET
        #brlc.exportDataToC() # Produce the .h and .c tables NOT WRITTEN YET

    else: # Must be demo mode
        # Demo the converter object
        brlc = BibleReferencesLinksConverter().loadAndValidate() # Load the XML
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, brlc ) # Just print a summary
# end of BibleReferencesLinksConverter.fullDemo

if __name__ == '__main__':
    from multiprocessing import set_start_method, freeze_support
    set_start_method('fork') # The default was changed on POSIX systems from 'fork' to 'forkserver' in Python3.14
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of BibleReferencesLinksConverter.py
