#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# BibleReferencesLinksConverter.py
#
# Module handling BibleReferencesLinks.xml to produce C and Python data tables
#
# Copyright (C) 2015-2019 Robert Hunt
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
Module handling BibleReferencesLinks.xml and to export to JSON, C, and Python data tables.
"""

from gettext import gettext as _

lastModifiedDate = '2019-12-24' # by RJH
shortProgramName = "BibleReferencesLinksConverter"
programName = "Bible References Links converter"
programVersion = '0.40'
programNameVersion = f'{programName} v{programVersion}'
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
from Reference.BibleOrganisationalSystems import BibleOrganisationalSystem
#from BibleReferences import BibleSingleReference, BibleReferenceList
from Reference.VerseReferences import SimpleVerseKey, FlexibleVersesKey



def exp( messageString ):
    """
    Expands the message string in debug mode.
    Prepends the module name to a error or warning message string
        if we are in debug mode.
    Returns the new string.
    """
    try: nameBit, errorBit = messageString.split( ': ', 1 )
    except ValueError: nameBit, errorBit = '', messageString
    if BibleOrgSysGlobals.debugFlag or debuggingThisModule:
        nameBit = '{}{}{}'.format( shortProgramName, '.' if nameBit else '', nameBit )
    return '{}{}'.format( nameBit+': ' if nameBit else '', errorBit )
# end of exp



@singleton # Can only ever have one instance
class BibleReferencesLinksConverter:
    """
    Class for reading, validating, and converting BibleReferencesLinks.
    This is only intended as a transitory class (used at start-up).
    The BibleReferencesLinks class has functions more generally useful.
    """

    def __init__( self ): # We can't give this parameters because of the singleton
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
        self._XMLheader, self._XMLtree = None, None
        self.__DataList = {} # Used for import
        self.titleString = self.programVersion = self.dateString = ''
    # end of BibleReferencesLinksConverter.__init__


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
            if XMLFilepath is not None and XMLFilepath!=self.__XMLFilepath: logging.error( _("Bible references links are already loaded -- your different filepath of {!r} was ignored").format( XMLFilepath ) )
        return self
    # end of BibleReferencesLinksConverter.loadAndValidate


    def __load( self, XMLFilepath ):
        """
        Load the source XML file and remove the header from the tree.
        Also, extracts some useful elements from the header element.
        """
        assert XMLFilepath
        self.__XMLFilepath = XMLFilepath
        assert self._XMLtree is None or len(self._XMLtree)==0 # Make sure we're not doing this twice

        if BibleOrgSysGlobals.verbosityLevel > 2: print( _("Loading BibleReferencesLinks XML file from {!r}…").format( self.__XMLFilepath ) )
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
            if header.tail is not None and header.tail.strip(): logging.error( _("Unexpected {!r} tail data after header").format( header.tail ) )
        else:
            logging.error( _("Expected to load {!r} but got {!r}").format( self._treeTag, self._XMLtree.tag ) )
    # end of BibleReferencesLinksConverter.__load


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

                # Get the sourceComponent to use as a record ID
                ID = element.find("sourceComponent").text

                # Check compulsory elements
                for elementName in self._compulsoryElements:
                    foundElement = element.find( elementName )
                    if foundElement is None:
                        logging.error( _("Compulsory {!r} element is missing in record with ID {!r} (record {})").format( elementName, ID, j ) )
                    else:
                        BibleOrgSysGlobals.checkXMLNoTail( foundElement, foundElement.tag + " in " + element.tag )
                        BibleOrgSysGlobals.checkXMLNoAttributes( foundElement, foundElement.tag + " in " + element.tag )
                        #BibleOrgSysGlobals.checkXMLNoSubelements( foundElement, foundElement.tag + " in " + element.tag )
                        if not foundElement.text:
                            logging.warning( _("Compulsory {!r} element is blank in record with ID {!r} (record {})").format( elementName, ID, j ) )

                # Check optional elements
                for elementName in self._optionalElements:
                    foundElement = element.find( elementName )
                    if foundElement is not None:
                        BibleOrgSysGlobals.checkXMLNoTail( foundElement, foundElement.tag + " in " + element.tag )
                        BibleOrgSysGlobals.checkXMLNoAttributes( foundElement, foundElement.tag + " in " + element.tag )
                        BibleOrgSysGlobals.checkXMLNoSubelements( foundElement, foundElement.tag + " in " + element.tag )
                        if not foundElement.text:
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
            else:
                logging.warning( _("Unexpected element: {} in record {}").format( element.tag, j ) )
            if element.tail is not None and element.tail.strip(): logging.error( _("Unexpected {!r} tail data after {} element in record {}").format( element.tail, element.tag, j ) )
        if self._XMLtree.tail is not None and self._XMLtree.tail.strip(): logging.error( _("Unexpected {!r} tail data after {} element").format( self._XMLtree.tail, self._XMLtree.tag ) )
    # end of BibleReferencesLinksConverter.__validate


    def __str__( self ):
        """
        This method returns the string representation of a Bible book code.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        indent = 2
        result = "BibleReferencesLinksConverter object"
        if self.titleString: result += ('\n' if result else '') + ' '*indent + _("Title: {}").format( self.titleString )
        if self.programVersion: result += ('\n' if result else '') + ' '*indent + _("Version: {}").format( self.programVersion )
        if self.dateString: result += ('\n' if result else '') + ' '*indent + _("Date: {}").format( self.dateString )
        if self._XMLtree is not None: result += ('\n' if result else '') + ' '*indent + _("Number of entries = {}").format( len(self._XMLtree) )
        return result
    # end of BibleReferencesLinksConverter.__str__


    def __len__( self ):
        """
        Returns the number of references links loaded.
        """
        return len( self._XMLtree )
    # end of BibleReferencesLinksConverter.__len__


    def importDataToPython( self ):
        """
        Loads (and pivots) the data (not including the header) into suitable Python containers to use in a Python program.
        (Of course, you can just use the elementTree in self._XMLtree if you prefer.)
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


        assert self._XMLtree
        if self.__DataList: # We've already done an import/restructuring -- no need to repeat it
            return self.__DataList, self.__DataDict

        # We'll create a number of dictionaries with different elements as the key
        rawRefLinkList = []
        actualLinkCount = 0
        for element in self._XMLtree:
            #print( BibleOrgSysGlobals.elementStr( element ) )

            # Get these first for helpful error messages
            sourceReference = element.find('sourceReference').text
            sourceComponent = element.find('sourceComponent').text
            assert sourceComponent in ('Section','Verses','Verse',)

            BibleOrgSysGlobals.checkXMLNoText( element, sourceReference, 'kls1' )
            BibleOrgSysGlobals.checkXMLNoAttributes( element, sourceReference, 'kd21' )
            BibleOrgSysGlobals.checkXMLNoTail( element, sourceReference, 'so20' )

            actualRawLinksList = []
            for subelement in element:
                #print( BibleOrgSysGlobals.elementStr( subelement ) )
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

        if BibleOrgSysGlobals.verbosityLevel > 1:
            print( "  {} raw links loaded (with {} actual raw link entries)".format( len(rawRefLinkList), actualLinkCount ) )


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
                    logging.error( "{} {!r} failed!".format( sourceComponent, sourceReference ) )
                    raise TypeError
            # Now do the actual parsing
            parsedSourceReference = FlexibleVersesKey( sourceReference )
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                print( j, sourceComponent, sourceReference, parsedSourceReference )
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
                        logging.error( "{} {!r} failed!".format( targetComponent, targetReference ) )
                        raise TypeError
                # Now do the actual parsing
                try: parsedTargetReference = FlexibleVersesKey( targetReference )
                except TypeError:
                    print( "  Temporarily ignored {!r} (TypeError from FlexibleVersesKey)".format( targetReference ) )
                    parsedTargetReference = None
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                    print( ' ', targetComponent, targetReference, parsedTargetReference )
                    #assert parsedTargetReference.getShortText().replace(' ','_',1) == targetReference

                actualLinksList.append( (targetReference,targetComponent,parsedTargetReference,linkType,) )
                actualLinkCount += 1

            myRefLinkList.append( (sourceReference,sourceComponent,parsedSourceReference,actualLinksList,) )

        if BibleOrgSysGlobals.verbosityLevel > 1:
            print( "  {:,} links processed (with {:,} actual link entries)".format( len(rawRefLinkList), actualLinkCount ) )
        #print( myRefLinkList ); halt
        self.__DataList = myRefLinkList

        # Now put it into my dictionaries for easy access
        # This part should be customized or added to for however you need to process the data

        # Create a link dictionary (by verse key)
        myRefLinkDict = {}
        for sourceReference,sourceComponent,parsedSourceReference,actualLinksList in myRefLinkList:
            #print( sourceReference, sourceComponent, parsedSourceReference )
            #print( sourceReference, sourceComponent, parsedSourceReference, actualLinksList )
            for verseRef in parsedSourceReference.getIncludedVerses():
                #print( verseRef )
                assert isinstance( verseRef, SimpleVerseKey )
                if verseRef not in myRefLinkDict: myRefLinkDict[verseRef] = []
                myRefLinkDict[verseRef].append( (sourceReference,sourceComponent,parsedSourceReference,actualLinksList,) )
            #print( myRefLinkDict ); halt
        originalLinks = len( myRefLinkDict )
        print( "  {:,} verse links added to dictionary (includes filling out spans)".format( originalLinks ) )
        #print( myRefLinkDict ); halt

        # Create a reversed link dictionary (by verse key)
        for sourceReference,sourceComponent,parsedSourceReference,actualLinksList in myRefLinkList:
            #print( sourceReference, sourceComponent, parsedSourceReference )
            #print( sourceReference, sourceComponent, parsedSourceReference, actualLinksList )
            for targetReference,targetComponent,parsedTargetReference,linkType in actualLinksList:
                if parsedTargetReference is not None:
                    for verseRef in parsedTargetReference.getIncludedVerses():
                        #print( verseRef )
                        assert isinstance( verseRef, SimpleVerseKey )
                        if linkType == 'TSK': reverseLinkType = 'TSKQuoted'
                        elif linkType == 'QuotedOTReference': reverseLinkType = 'OTReferenceQuoted'
                        elif linkType == 'AlludedOTReference': reverseLinkType = 'OTReferenceAlluded'
                        elif linkType == 'PossibleOTReference': reverseLinkType = 'OTReferencePossible'
                        else: halt # Have a new linkType!
                        if verseRef not in myRefLinkDict: myRefLinkDict[verseRef] = []
                        myRefLinkDict[verseRef].append( (targetReference,targetComponent,parsedTargetReference,[(sourceReference,sourceComponent,parsedSourceReference,reverseLinkType)]) )
            #print( myRefLinkDict ); halt
        totalLinks = len( myRefLinkDict )
        reverseLinks = totalLinks - originalLinks
        print( "  {:,} reverse links added to dictionary to give {:,} total".format( reverseLinks, totalLinks ) )
        #print( myRefLinkDict ); halt

        self.__DataDict = myRefLinkDict

        # Let's find the most number of references for a verse
        mostReferences = totalReferences = 0
        for verseRef, entryList in self.__DataDict.items():
            numRefs = len( entryList )
            if numRefs > mostReferences: mostReferences, mostVerseRef = numRefs, verseRef
            totalReferences += numRefs
        print( "  {} maximum links for any one reference ({})".format( mostReferences, mostVerseRef.getShortText() ) )
        print( "  {} total links for all references".format( totalReferences ) )

        return self.__DataList, self.__DataDict
    # end of BibleReferencesLinksConverter.importDataToPython


    def pickle( self, filepath=None ):
        """
        Writes the information tables to a .pickle file that can be easily loaded into a Python3 program.
        """
        import pickle

        assert self._XMLtree
        self.importDataToPython()
        assert self.__DataList
        assert self.__DataDict

        if not filepath:
            folder = os.path.join( os.path.split(self.__XMLFilepath)[0], "DerivedFiles/" )
            if not os.path.exists( folder ): os.mkdir( folder )
            filepath = os.path.join( folder, self._filenameBase + "_Tables.pickle" )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Exporting to {}…").format( filepath ) )
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

        assert self._XMLtree
        self.importDataToPython()
        assert self.__DataList
        assert self.__DataDict

        if not filepath:
            folder = os.path.join( os.path.split(self.__XMLFilepath)[0], "DerivedFiles/" )
            if not os.path.exists( folder ): os.mkdir( folder )
            indexFilepath = os.path.join( folder, self._filenameBase + "_Tables.index.pickle" )
            dataFilepath = os.path.join( folder, self._filenameBase + "_Tables.data.pickle" )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Exporting to {}…").format( dataFilepath ) )
        index = {}
        filePosition = 0
        with open( dataFilepath, 'wb' ) as myFile:
            for vKey,refList in self.__DataDict.items():
                #print( "vKey", vKey, vKey.getVerseKeyText() )
                #print( " ", refList )
                length = myFile.write( pickle.dumps( refList ) )
                #print( " ", filePosition, length )
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
            theFile.write( "{} = {{\n  # Key is {}\n  # Fields ({}) are: {}\n".format( dictName, keyComment, fieldsCount, fieldsComment ) )
            for dictKey in sorted(theDict.keys()):
                theFile.write( '  {}: {},\n'.format( repr(dictKey), repr(theDict[dictKey]) ) )
            theFile.write( "}}\n# end of {} ({} entries)\n\n".format( dictName, len(theDict) ) )
        # end of exportPythonDictOrList


        assert self._XMLtree
        self.importDataToPython()
        assert self.__DataList
        assert self.__DataDict

        print( "Export to Python not written yet!" )
        halt

        if not filepath:
            folder = os.path.join( os.path.split(self.__XMLFilepath)[0], "DerivedFiles/" )
            if not os.path.exists( folder ): os.mkdir( folder )
            filepath = os.path.join( folder, self._filenameBase + "_Tables.py" )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Exporting to {}…").format( filepath ) )
        with open( filepath, 'wt', encoding='utf-8' ) as myFile:
            myFile.write( "# {}\n#\n".format( filepath ) )
            myFile.write( "# This UTF-8 file was automatically generated by BibleReferencesLinks.py V{} on {}\n#\n".format( programVersion, datetime.now() ) )
            if self.titleString: myFile.write( "# {} data\n".format( self.titleString ) )
            if self.programVersion: myFile.write( "#  Version: {}\n".format( self.programVersion ) )
            if self.dateString: myFile.write( "#  Date: {}\n#\n".format( self.dateString ) )
            myFile.write( "#   {} {} loaded from the original XML file.\n#\n\n".format( len(self._XMLtree), self._treeTag ) )
            mostEntries = "0=referenceNumber (integer 1..255), 1=sourceComponent/BBB (3-uppercase characters)"
            dictInfo = { "referenceNumberDict":("referenceNumber (integer 1..255)","specified"),
                    "sourceComponentDict":("sourceComponent","specified"),
                    "sequenceList":("sourceComponent/BBB (3-uppercase characters)",""),
                    "initialAllAbbreviationsDict":("allAbbreviations", mostEntries) }
            for dictName,dictData in self.__DataList.items():
                exportPythonDictOrList( myFile, dictData, dictName, dictInfo[dictName][0], dictInfo[dictName][1] )
            myFile.write( "# end of {}".format( os.path.basename(filepath) ) )
    # end of BibleReferencesLinksConverter.exportDataToPython


    def exportDataToJSON( self, filepath=None ):
        """
        Writes the information tables to a .json file that can be easily loaded into a Java program.

        See http://en.wikipedia.org/wiki/JSON.
        """
        import json

        assert self._XMLtree
        self.importDataToPython()
        assert self.__DataList
        assert self.__DataDict

        if not filepath:
            folder = os.path.join( os.path.split(self.__XMLFilepath)[0], "DerivedFiles/" )
            if not os.path.exists( folder ): os.mkdir( folder )
            filepath = os.path.join( folder, self._filenameBase + "_Tables.json" )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Exporting to {}…").format( filepath ) )
        with open( filepath, 'wt', encoding='utf-8' ) as myFile:
            for something in self.__DataList: # temp for debugging … xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
                print( "Dumping something", something )
                json.dump( something, myFile, indent=2 )
            json.dump( self.__DataList, myFile, indent=2 )

            for someKey,someItem in self.__DataDict.items(): # temp for debugging … xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
                print( "Dumping someKey", someKey )
                json.dump( someKey, myFile, indent=2 )
                print( "Dumping someItem", someItem )
                json.dump( someItem, myFile, indent=2 )
            json.dump( self.__DataDict, myFile, indent=2 )
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
                        else: logging.error( _("Cannot convert unknown field type {!r} in tuple entry {!r}").format( field, entry ) )
                elif isinstance( entry, dict ):
                    for key in sorted(entry.keys()):
                        field = entry[key]
                        if result: result += ", " # Separate the fields
                        if field is None: result += '""'
                        elif isinstance( field, str): result += '"' + str(field).replace('"','\\"') + '"'
                        elif isinstance( field, int): result += str(field)
                        elif isinstance( field, list): raise Exception( "Not written yet (list2)" )
                        else: logging.error( _("Cannot convert unknown field type {!r} in dict entry {!r}").format( field, entry ) )
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
        assert self.__DataList

        print( "Export to C not written yet!" )
        halt

        if not filepath:
            folder = os.path.join( os.path.split(self.__XMLFilepath)[0], "DerivedFiles/" )
            if not os.path.exists( folder ): os.mkdir( folder )
            filepath = os.path.join( folder, self._filenameBase + "_Tables" )
        hFilepath = filepath + '.h'
        cFilepath = filepath + '.c'
        if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Exporting to {}…").format( cFilepath ) ) # Don't bother telling them about the .h file
        ifdefName = self._filenameBase.upper() + "_Tables_h"

        with open( hFilepath, 'wt', encoding='utf-8' ) as myHFile, \
             open( cFilepath, 'wt', encoding='utf-8' ) as myCFile:
            myHFile.write( "// {}\n//\n".format( hFilepath ) )
            myCFile.write( "// {}\n//\n".format( cFilepath ) )
            lines = "// This UTF-8 file was automatically generated by BibleReferencesLinks.py V{} on {}\n//\n".format( programVersion, datetime.now() )
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
                    "{} referenceNumber; {}* ByzantineAbbreviation; {}* CCELNumberString; {}* NETBibleAbbreviation; {}* OSISAbbreviation; {} USFMAbbreviation[3+1]; {} USFMNumberString[2+1]; {}* SBLAbbreviation; {}* SwordAbbreviation; {}* sourceReference; {}* numExpectedChapters; {}* possibleAlternativeBooks; {} sourceComponent[3+1];"
                   .format(BYTE, CHAR, CHAR, CHAR, CHAR, CHAR, CHAR, CHAR, CHAR, CHAR, CHAR, CHAR, CHAR ) ),
                "sourceComponentDict":("sourceComponent",
                    "{} sourceComponent[3+1]; {}* ByzantineAbbreviation; {}* CCELNumberString; {} referenceNumber; {}* NETBibleAbbreviation; {}* OSISAbbreviation; {} USFMAbbreviation[3+1]; {} USFMNumberString[2+1]; {}* SBLAbbreviation; {}* SwordAbbreviation; {}* sourceReference; {}* numExpectedChapters; {}* possibleAlternativeBooks;"
                   .format(CHAR, CHAR, CHAR, BYTE, CHAR, CHAR, CHAR, CHAR, CHAR, CHAR, CHAR, CHAR, CHAR ) ),
                "sequenceList":("sequenceList",),
                "CCELDict":("CCELNumberString", "{}* CCELNumberString; {} referenceNumber; {} sourceComponent[3+1];".format(CHAR,BYTE,CHAR) ),
                "initialAllAbbreviationsDict":("abbreviation", "{}* abbreviation; {} sourceComponent[3+1];".format(CHAR,CHAR) ) }

            for dictName,dictData in self.__DataList.items():
                exportPythonDict( myHFile, myCFile, dictData, dictName, dictInfo[dictName][0], dictInfo[dictName][1] )

            myHFile.write( "#endif // {}\n\n".format( ifdefName ) )
            myHFile.write( "// end of {}".format( os.path.basename(hFilepath) ) )
            myCFile.write( "// end of {}".format( os.path.basename(cFilepath) ) )
    # end of BibleReferencesLinksConverter.exportDataToC
# end of BibleReferencesLinksConverter class



def demo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel > 1: print( programNameVersion )

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
        print( brlc ) # Just print a summary
# end of demo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( programName, programVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    demo()

    BibleOrgSysGlobals.closedown( programName, programVersion )
# end of BibleReferencesLinksConverter.py
