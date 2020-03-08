#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# BibleVersificationSystemsConverter.py
#
# Module handling loading of BibleVersificationSystem_*.xml to produce C and Python data tables
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
Module handling BibleVersificationSystem_*.xml to produce C and Python data tables.

NOTE: We still lack a REFERENCE Bible versification system
        with back-and-forth mappings. This is a MAJOR outstanding deficiency.
"""

from gettext import gettext as _

lastModifiedDate = '2017-12-09' # by RJH
shortProgramName = "BibleVersificationSystemsConverter"
programName = "Bible Versification Systems converter"
programVersion = '0.51'
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
class BibleVersificationSystemsConverter:
    """
    A class to load and export XML data for Bible versification systems.
    """

    def __init__( self ):
        """
        Constructor.
        """
        self.__filenameBase = "BibleVersificationSystems"

        # These fields are used for parsing the XML
        self.__treeTag = "BibleVersificationSystem"
        self.__headerTag = "header"
        self.__mainElementTag = "BibleBookVersification"

        # These fields are used for automatically checking/validating the XML
        self.__compulsoryAttributes = ()
        self.__optionalAttributes = ( "omittedVerses", "combinedVerses", "reorderedVerses", )
        self.__uniqueAttributes = self.__compulsoryAttributes + self.__optionalAttributes
        self.__compulsoryElements = ( "nameEnglish", "referenceAbbreviation", "numChapters", "numVerses", )
        self.__optionalElements = ()
        self.__uniqueElements = ( "nameEnglish", "referenceAbbreviation", ) + self.__optionalElements

        # These are fields that we will fill later
        self.__XMLSystems, self.__DataDict = {}, {}
    # end of BibleVersificationSystemsConverter.__init__


    def loadSystems( self, XMLFolder=None ):
        """
        Load and pre-process the specified versification systems.
        """
        if not self.__XMLSystems: # Only ever do this once
            if XMLFolder==None: XMLFolder = BibleOrgSysGlobals.BOS_DATA_FILES_FOLDERPATH.joinpath( "VersificationSystems" ) # Relative to module, not cwd
            self.__XMLFolder = XMLFolder
            if BibleOrgSysGlobals.verbosityLevel > 2: print( _("Loading versification systems from {}…").format( XMLFolder ) )
            filenamePrefix = "BIBLEVERSIFICATIONSYSTEM_"
            for filename in os.listdir( XMLFolder ):
                filepart, extension = os.path.splitext( filename )
                if extension.upper() == '.XML' and filepart.upper().startswith(filenamePrefix):
                    versificationSystemCode = filepart[len(filenamePrefix):]
                    if BibleOrgSysGlobals.verbosityLevel > 3: print( _("Loading{} versification system from {}…").format( versificationSystemCode, filename ) )
                    self.__XMLSystems[versificationSystemCode] = {}
                    self.__XMLSystems[versificationSystemCode]['tree'] = ElementTree().parse( os.path.join( XMLFolder, filename ) )
                    assert self.__XMLSystems[versificationSystemCode]['tree'] # Fail here if we didn't load anything at all

                    # Check and remove the header element
                    if self.__XMLSystems[versificationSystemCode]['tree'].tag  == self.__treeTag:
                        header = self.__XMLSystems[versificationSystemCode]['tree'][0]
                        if header.tag == self.__headerTag:
                            self.__XMLSystems[versificationSystemCode]["header"] = header
                            self.__XMLSystems[versificationSystemCode]['tree'].remove( header )
                            if len(header)>1:
                                logging.info( _("Unexpected elements in header") )
                            elif len(header)==0:
                                logging.info( _("Missing work element in header") )
                            else:
                                work = header[0]
                                if work.tag == "work":
                                    self.__XMLSystems[versificationSystemCode]['version'] = work.find('version').text
                                    self.__XMLSystems[versificationSystemCode]["date"] = work.find("date").text
                                    self.__XMLSystems[versificationSystemCode]["title"] = work.find("title").text
                                else:
                                    logging.warning( _("Missing work element in header") )
                        else:
                            logging.warning( _("Missing header element (looking for {!r} tag)").format( self.__headerTag ) )
                    else:
                        logging.error( _("Expected to load {!r} but got {!r}").format( self.__treeTag, self.__XMLSystems[versificationSystemCode]['tree'].tag ) )
                    bookCount = 0 # There must be an easier way to do this
                    for subelement in self.__XMLSystems[versificationSystemCode]['tree']:
                        bookCount += 1
                    if BibleOrgSysGlobals.verbosityLevel > 2:
                        print( _("    Loaded {} books for {}").format( bookCount, versificationSystemCode ) )
                    logging.info( _("    Loaded {} books for {}").format( bookCount, versificationSystemCode ) )

                    if BibleOrgSysGlobals.strictCheckingFlag:
                        self._validateSystem( self.__XMLSystems[versificationSystemCode]['tree'] )
        else: # The data must have been already loaded
            if XMLFolder is not None and XMLFolder!=self.__XMLFolder: logging.error( _("Bible versification systems are already loaded -- your different folder of {!r} was ignored").format( XMLFolder ) )
        return self
    # end of BibleVersificationSystemsConverter.loadSystems


    def _validateSystem( self, versificationTree ):
        """
        """
        assert versificationTree

        uniqueDict = {}
        for elementName in self.__uniqueElements: uniqueDict["Element_"+elementName] = []
        for attributeName in self.__uniqueAttributes: uniqueDict["Attribute_"+attributeName] = []

        expectedID = 1
        for k,element in enumerate(versificationTree):
            if element.tag == self.__mainElementTag:
                # Check compulsory attributes on this main element
                for attributeName in self.__compulsoryAttributes:
                    attributeValue = element.get( attributeName )
                    if attributeValue is None:
                        logging.error( _("Compulsory {!r} attribute is missing from {} element in record {}").format( attributeName, element.tag, k ) )
                    if not attributeValue:
                        logging.warning( _("Compulsory {!r} attribute is blank on {} element in record {}").format( attributeName, element.tag, k ) )

                # Check optional attributes on this main element
                for attributeName in self.__optionalAttributes:
                    attributeValue = element.get( attributeName )
                    if attributeValue is not None:
                        if not attributeValue:
                            logging.warning( _("Optional {!r} attribute is blank on {} element in record {}").format( attributeName, element.tag, k ) )

                # Check for unexpected additional attributes on this main element
                for attributeName in element.keys():
                    attributeValue = element.get( attributeName )
                    if attributeName not in self.__compulsoryAttributes and attributeName not in self.__optionalAttributes:
                        logging.warning( _("Additional {!r} attribute ({!r}) found on {} element in record {}").format( attributeName, attributeValue, element.tag, k ) )

                # Check the attributes that must contain unique information (in that particular field -- doesn't check across different attributes)
                for attributeName in self.__uniqueAttributes:
                    attributeValue = element.get( attributeName )
                    if attributeValue is not None:
                        if attributeValue in uniqueDict["Attribute_"+attributeName]:
                            logging.error( _("Found {!r} data repeated in {!r} field on {} element in record {}").format( attributeValue, attributeName, element.tag, k ) )
                        uniqueDict["Attribute_"+attributeName].append( attributeValue )

                # Check compulsory elements
                ID = element.find("referenceAbbreviation").text
                for elementName in self.__compulsoryElements:
                    if element.find( elementName ) is None:
                        logging.error( _("Compulsory {!r} element is missing in record with ID {!r} (record {})").format( elementName, ID, k ) )
                    if not element.find( elementName ).text:
                        logging.warning( _("Compulsory {!r} element is blank in record with ID {!r} (record {})").format( elementName, ID, k ) )

                # Check optional elements
                for elementName in self.__optionalElements:
                    if element.find( elementName ) is not None:
                        if not element.find( elementName ).text:
                            logging.warning( _("Optional {!r} element is blank in record with ID {!r} (record {})").format( elementName, ID, k ) )

                # Check for unexpected additional elements
                for subelement in element:
                    if subelement.tag not in self.__compulsoryElements and subelement.tag not in self.__optionalElements:
                        logging.warning( _("Additional {!r} element ({!r}) found in record with ID {!r} (record {})").format( subelement.tag, subelement.text, ID, k ) )

                # Check the elements that must contain unique information (in that particular element -- doesn't check across different elements)
                for elementName in self.__uniqueElements:
                    if element.find( elementName ) is not None:
                        text = element.find( elementName ).text
                        if text in uniqueDict["Element_"+elementName]:
                            logging.error( _("Found {!r} data repeated in {!r} element in record with ID {!r} (record {})").format( text, elementName, ID, k ) )
                        uniqueDict["Element_"+elementName].append( text )
            else:
                logging.warning( _("Unexpected element: {} in record {}").format( element.tag, k ) )
    # end of BibleVersificationSystemsConverter._validateSystem


    def __str__( self ):
        """
        This method returns the string representation of a Bible versification system.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = "BibleVersificationSystemsConverter object"
        #if self.__title: result += ('\n' if result else '') + self.__title
        #if self.__version: result += ('\n' if result else '') + "Version:{}".format( self.__version )
        #if self.__date: result += ('\n' if result else '') + "Date:{}".format( self.__date )
        result += ('\n' if result else '') + "  Number of versification systems loaded = {}".format( len(self.__XMLSystems) )
        if 0: # Make it verbose
            for x in self.__XMLSystems:
                result += ('\n' if result else '') + " {}".format( x )
                title = self.__XMLSystems[x]["title"]
                if title: result += ('\n' if result else '') + "   {}".format( title )
                version = self.__XMLSystems[x]['version']
                if version: result += ('\n    ' if result else '    ') + _("Version: {}").format( version )
                date = self.__XMLSystems[x]["date"]
                if date: result += ('\n    ' if result else '    ') + _("Last updated: {}").format( date )
                result += ('\n' if result else '') + "    Number of books = {}".format( len(self.__XMLSystems[x]['tree']) )
                totalChapters, totalVerses, totalOmittedVerses, numCombinedVersesInstances, numRecorderedVersesInstances = 0, 0, 0, 0, 0
                for bookElement in self.__XMLSystems[x]['tree']:
                    totalChapters += int( bookElement.find("numChapters").text )
                    for chapterElement in bookElement.findall("numVerses"):
                        totalVerses += int( chapterElement.text )
                        omittedVerses = chapterElement.get( "omittedVerses" )
                        if omittedVerses is not None: totalOmittedVerses += len(omittedVerses.split(','))
                        combinedVerses = chapterElement.get( "combinedVerses" )
                        if combinedVerses is not None: numCombinedVersesInstances += 1
                        reorderedVerses = chapterElement.get( "reorderedVerses" )
                        if reorderedVerses is not None: numRecorderedVersesInstances += 1
                if totalChapters: result += ('\n' if result else '') + "      Total chapters = {}".format( totalChapters )
                if totalVerses: result += ('\n' if result else '') + "      Total verses = {}".format( totalVerses )
                if totalOmittedVerses: result += ('\n' if result else '') + "      Total omitted verses = {}".format( totalOmittedVerses )
                if numCombinedVersesInstances: result += ('\n' if result else '') + "      Number of combined verses instances = {}".format( numCombinedVersesInstances )
                if numRecorderedVersesInstances: result += ('\n' if result else '') + "      Number of reordered verses instances = {}".format( numRecorderedVersesInstances )
        return result
    # end of BibleVersificationSystemsConverter.__str__


    def __len__( self ):
        """ Returns the number of systems loaded. """
        return len( self.__XMLSystems )
    # end of BibleVersificationSystemsConverter.__len__


    def importDataToPython( self ):
        """
        Loads (and pivots) the data (not including the header) into suitable Python containers to use in a Python program.
        """
        assert self.__XMLSystems
        if self.__DataDict: # We've already done an import/restructuring -- no need to repeat it
            return self.__DataDict

        # We'll create a number of dictionaries
        self.__DataDict = {}
        for versificationSystemCode in self.__XMLSystems.keys():
            #print( versificationSystemCode )
            # Make the data dictionary for this versification system
            chapterDataDict, omittedVersesDict, combinedVersesDict, reorderedVersesDict = {}, {}, {}, {}
            for bookElement in self.__XMLSystems[versificationSystemCode]['tree']:
                BBB = bookElement.find("referenceAbbreviation").text
                #print( BBB )
                if not BibleOrgSysGlobals.BibleBooksCodes.isValidBBB( BBB ):
                    logging.error( _("Unrecognized {!r} book abbreviation in {!r} versification system").format( BBB, versificationSystemCode ) )
                numChapters = bookElement.find("numChapters").text # This is a string

                # Check the chapter data against the expected chapters in the BibleBooksCodes data
                if numChapters not in BibleOrgSysGlobals.BibleBooksCodes.getExpectedChaptersList(BBB):
                    logging.info( _("Expected number of chapters for {} is {} but we got {!r} for {}").format(BBB, BibleOrgSysGlobals.BibleBooksCodes.getExpectedChaptersList(BBB), numChapters, versificationSystemCode ) )

                chapterData, omittedVersesData, combinedVersesData, reorderedVersesData = {}, [], [], []
                chapterData['numChapters'] = numChapters
                for chapterElement in bookElement.findall("numVerses"):
                    chapter = chapterElement.get("chapter")
                    numVerses = chapterElement.text
                    assert chapter not in chapterData
                    chapterData[chapter] = numVerses
                    omittedVerses = chapterElement.get( "omittedVerses" )
                    if omittedVerses is not None:
                        bits = omittedVerses.split(',')
                        for bit in bits:
                            omittedVersesData.append( (chapter, bit,) )
                    combinedVerses = chapterElement.get( "combinedVerses" )
                    if combinedVerses is not None:
                        combinedVersesData.append( (chapter, combinedVerses,) )
                    reorderedVerses = chapterElement.get( "reorderedVerses" )
                    if reorderedVerses is not None:
                        reorderedVersesData.append( (chapter, reorderedVerses,) )
                # Save it by book reference abbreviation
                #assert BBB not in bookData
                #bookData[BBB] = (chapterData, omittedVersesData,)
                if BBB in chapterDataDict:
                    logging.error( _("Duplicate {} in {}").format( BBB, versificationSystemCode ) )
                chapterDataDict[BBB] = chapterData
                if BBB in omittedVersesDict:
                    logging.error( _("Duplicate omitted verse data for {} in {}").format( BBB, versificationSystemCode ) )
                if omittedVersesData: omittedVersesDict[BBB] = omittedVersesData
                if combinedVersesData: combinedVersesDict[BBB] = combinedVersesData
                if reorderedVersesData: reorderedVersesDict[BBB] = reorderedVersesData

            if BibleOrgSysGlobals.strictCheckingFlag: # check for duplicates
                for checkSystemCode in self.__DataDict:
                    checkChapterDataDict, checkOmittedVersesDict, checkCombinedVersesDict, checkReorderedVersesDict = self.__DataDict[checkSystemCode]['CV'], self.__DataDict[checkSystemCode]['omitted'], self.__DataDict[checkSystemCode]['combined'], self.__DataDict[checkSystemCode]['reordered']
                    if checkChapterDataDict==chapterDataDict:
                        if checkOmittedVersesDict==omittedVersesDict:
                            logging.error( _("{} and {} versification systems are exactly identical").format( versificationSystemCode, checkSystemCode ) )
                        else: # only the omitted verse lists differ
                            logging.warning( _("{} and {} versification systems are mostly identical (omitted verse lists differ)").format( versificationSystemCode, checkSystemCode ) )
                    else: # check if one is the subset of the other
                        BBBcombinedSet = set( checkChapterDataDict.keys() ) or set( chapterDataDict.keys() )
                        different, numCommon = False, 0
                        for BBB in BBBcombinedSet:
                            if BBB in checkChapterDataDict and BBB in chapterDataDict: # This book is in both
                                numCommon += 1
                                if checkChapterDataDict[BBB] != chapterDataDict[BBB]: different = True
                        if not different:
                            different2, numCommon2 = False, 0
                            for BBB in BBBcombinedSet:
                                if BBB in checkOmittedVersesDict and BBB in omittedVersesDict: # This book is in both
                                    numCommon2 += 1
                                    if checkOmittedVersesDict[BBB] != omittedVersesDict[BBB]: different2 = True
                            if not different2:
                                logging.warning( _("The {} common books in {} ({}) and {} ({}) versification systems are exactly identical").format( numCommon, versificationSystemCode, len(chapterDataDict), checkSystemCode, len(checkChapterDataDict) ) )
                            else: # only the omitted verse lists differ
                                logging.warning( _("The {} common books in {} ({}) and {} ({}) versification systems are mostly identical (omitted verse lists differ)").format( numCommon, versificationSystemCode, len(chapterDataDict), checkSystemCode, len(checkChapterDataDict) ) )


            # Now put it into my dictionaries for easy access
            self.__DataDict[versificationSystemCode] = {'CV':chapterDataDict, 'omitted':omittedVersesDict, 'combined':combinedVersesDict, 'reordered':reorderedVersesDict }

        if BibleOrgSysGlobals.strictCheckingFlag:
            self._validateSystems()
        return self.__DataDict
    # end of BibleVersificationSystemsConverter.importDataToPython


    def _validateSystems( self ):
        """
        Checks that none of the versification systems are identical.

        Checks that the BibMaxRef versification system contains the most books / chapters / verses.
        """
        assert self.__DataDict
        referenceCode = "BibMaxRef"
        referenceVersificationSystem = self.__DataDict[referenceCode]

        for versificationSystemCode in self.__DataDict:
            print( "Validating {}…".format( versificationSystemCode ) )
            thisSystem = self.__DataDict[versificationSystemCode]
            for versificationSystemCode2 in self.__DataDict:
                if versificationSystemCode2 != versificationSystemCode:
                    #print( "  Comparing with", versificationSystemCode2 )
                    secondSystem = self.__DataDict[versificationSystemCode2]
                    if thisSystem == secondSystem: logging.warning( _("The {} and {} systems are identical.").format( versificationSystemCode, versificationSystemCode2 ) )

            if versificationSystemCode == referenceCode:
                assert not thisSystem['omitted']
                assert not thisSystem['combined']
                assert not thisSystem['reordered']
            else:
                for BBB in thisSystem['CV']:
                    #print( BBB )
                    if BBB not in referenceVersificationSystem['CV']:
                        logging.warning( _("The {} system contains book {} which is not in {}").format( versificationSystemCode, BBB, referenceCode ) )
                    elif int(thisSystem['CV'][BBB]['numChapters']) > int(referenceVersificationSystem['CV'][BBB]['numChapters']):
                        #print( '2', thisSystem['CV'][BBB]['numChapters'], referenceVersificationSystem['CV'][BBB]['numChapters'] )
                        logging.warning( _("The {} system contains {} chapters for {} while only {} in {}").format( versificationSystemCode, thisSystem['CV'][BBB]['numChapters'], BBB, referenceVersificationSystem['CV'][BBB]['numChapters'], referenceCode ) )
                    else:
                        for ch in range( 1, int(thisSystem['CV'][BBB]['numChapters']) + 1 ):
                            #print( ch )
                            ok = True
                            try: v = int( thisSystem['CV'][BBB][str(ch)] )
                            except KeyError:
                                logging.warning( _("The {} system has chapter {} missing for {}").format( versificationSystemCode, ch, BBB ) )
                                ok = False
                            try: vr = int( referenceVersificationSystem['CV'][BBB][str(ch)] )
                            except KeyError:
                                logging.warning( _("The {} system has chapter {} missing for {}").format( referenceCode, ch, BBB ) )
                                ok = False
                            if ok and v > vr:
                                logging.warning( _("The {} system contains {} verses for {} {} while only {} in {}") \
                                        .format( versificationSystemCode, v, BBB, ch, vr, referenceCode ) )

    def pickle( self, filepath=None ):
        """
        Writes the information tables to a .pickle file that can be easily loaded into a Python3 program.
        """
        import pickle

        assert self.__XMLSystems
        self.importDataToPython()
        assert self.__DataDict

        if not filepath:
            folder = os.path.join( self.__XMLFolder, "../", "DerivedFiles/" )
            if not os.path.exists( folder ): os.mkdir( folder )
            filepath = os.path.join( folder, self.__filenameBase + "_Tables.pickle" )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Exporting to {}…").format( filepath ) )
        with open( filepath, 'wb' ) as pickleFile:
            pickle.dump( self.__DataDict, pickleFile )
    # end of BibleVersificationSystemsConverter.pickle


    def exportDataToPython( self, filepath=None ):
        """
        Writes the information tables to a .py file that can be cut and pasted into a Python program.
        """
        def exportPythonDict( theFile, theDict, systemName, keyComment, fieldsComment ):
            """Exports theDict to theFile."""
            theFile.write( '  "{}": {{\n    # Key is{}\n    # Fields are:{}\n'.format( systemName, keyComment, fieldsComment ) )
            for dictKey in theDict.keys():
                theFile.write( '   {}:{},\n'.format( repr(dictKey), theDict[dictKey] ) )
            theFile.write( "  }}, # end of {} ({} entries)\n\n".format( systemName, len(theDict) ) )
        # end of exportPythonDict


        assert self.__XMLSystems
        self.importDataToPython()
        assert self.__DataDict

        if not filepath: filepath = os.path.join( self.__XMLFolder, "../", 'DerivedFiles/', self.__filenameBase + "_Tables.py" )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Exporting to {}…").format( filepath ) )
        versificationSystemDict = self.importDataToPython()
        # Split into two dictionaries
        with open( filepath, 'wt', encoding='utf-8' ) as myFile:
            myFile.write( "#{}\n#\n".format( filepath ) )
            myFile.write( "# This UTF-8 file was automatically generated by BibleVersificationSystems.py V{} on {}\n#\n".format( programVersion, datetime.now() ) )
            #if self.__title: myFile.write( "#{}\n".format( self.__title ) )
            #if self.__version: myFile.write( "#  Version:{}\n".format( self.__version ) )
            #if self.__date: myFile.write( "#  Date:{}\n#\n".format( self.__date ) )
            myFile.write( "#  {}{} loaded from the original XML files.\n#\n\n".format( len(self.__XMLSystems), self.__treeTag ) )
            #myFile.write( "from collections import OrderedDict\n\n" )
            myFile.write( "chapterVerseDict = {\n  # Key is versificationSystemName\n  # Fields are versificationSystem\n" )
            for systemName in versificationSystemDict:
                exportPythonDict( myFile, versificationSystemDict[systemName]['CV'], systemName, "BBB referenceAbbreviation", "tuples containing (\"numChapters\", numChapters) then (chapterNumber, numVerses)" )
            myFile.write( "}} # end of chapterVerseDict ({} systems)\n\n".format( len(versificationSystemDict) ) )
            myFile.write( "omittedVersesDict = {{\n  # Key is versificationSystemName\n  # Fields are omittedVersesSystem\n" )
            for systemName in versificationSystemDict:
                exportPythonDict( myFile, versificationSystemDict[systemName]['omitted'], systemName, "BBB referenceAbbreviation", "tuples containing (chapterNumber, omittedVerseNumber)" )
            myFile.write( "}} # end of omittedVersesDict ({} systems)\n\n".format( len(versificationSystemDict) ) )
            myFile.write( "combinedVersesDict = {{\n  # Key is versificationSystemName\n  # Fields are combinedVersesSystem\n" )
            for systemName in versificationSystemDict:
                exportPythonDict( myFile, versificationSystemDict[systemName]['combined'], systemName, "BBB referenceAbbreviation", "tuples containing (chapterNumber, omittedVerseNumber)" )
            myFile.write( "}} # end of combinedVersesDict ({} systems)\n\n".format( len(versificationSystemDict) ) )
            myFile.write( "reorderedVersesDict = {{\n  # Key is versificationSystemName\n  # Fields are reorderedVersesSystem\n" )
            for systemName in versificationSystemDict:
                exportPythonDict( myFile, versificationSystemDict[systemName]['reordered'], systemName, "BBB referenceAbbreviation", "tuples containing (chapterNumber, omittedVerseNumber)" )
            myFile.write( "}} # end of reorderedVersesDict ({} systems)\n\n".format( len(versificationSystemDict) ) )
    # end of BibleVersificationSystemsConverter.exportDataToPython


    def exportDataToJSON( self, filepath=None ):
        """
        Writes the information tables to a .json file that can be easily loaded into a Java program.

        See http://en.wikipedia.org/wiki/JSON.
        """
        import json

        assert self.__XMLSystems
        self.importDataToPython()
        assert self.__DataDict

        if not filepath: filepath = os.path.join( self.__XMLFolder, "../", 'DerivedFiles/', self.__filenameBase + "_Tables.json" )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Exporting to {}…").format( filepath ) )
        with open( filepath, 'wt', encoding='utf-8' ) as myFile:
            #myFile.write( "#{}\n#\n".format( filepath ) ) # Not sure yet if these comment fields are allowed in JSON
            #myFile.write( "# This UTF-8 file was automatically generated by BibleVersificationSystems.py V{} on {}\n#\n".format( programVersion, datetime.now() ) )
            #if self.__titleString: myFile.write( "#{} data\n".format( self.__titleString ) )
            #if self.__ProgVersion: myFile.write( "#  Version:{}\n".format( self.__ProgVersion ) )
            #if self.__dateString: myFile.write( "#  Date:{}\n#\n".format( self.__dateString ) )
            #myFile.write( "#  {}{} loaded from the original XML file.\n#\n\n".format( len(self.__XMLtree), self.__treeTag ) )
            json.dump( self.__DataDict, myFile, indent=2 )
            #myFile.write( "\n\n# end of {}".format( os.path.basename(filepath) ) )
    # end of BibleVersificationSystemsConverter.exportDataToJSON


    def exportDataToC( self, filepath=None ):
        """
        Writes the information tables to a .h file that can be included in c and c++ programs.
        """
        def writeStructure( hFile, structName, structure ):
            """ Writes a typedef to the .h file. """
            hFile.write( "typedef struct{}EntryStruct {\n".format( structName ) )
            for declaration in structure.split(';'):
                adjDeclaration = declaration.strip()
                if adjDeclaration: hFile.write( "   {};\n".format( adjDeclaration ) )
            hFile.write( "}{}Entry;\n\n".format( structName ) )
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
                        elif isinstance( field, tuple):
                            tupleResult = ""
                            for value in field:
                                if tupleResult: tupleResult += "," # Separate the fields (without a space)
                                tupleResult += convertEntry( value ) # recursive call
                            result += "{{} }".format( tupleResult )
                        else: logging.error( _("Cannot convert unknown field type {!r} in entry {!r}").format( field, entry ) )
                return result
            # end of convertEntry

            #for dictKey in theDict.keys(): # Have to iterate this :(
            #    fieldsCount = len( theDict[dictKey] ) + 1 # Add one since we include the key in the count
            #    break # We only check the first (random) entry we get
            fieldsCount = 2

            cFile.write( "const static{}\n{}[{}] = {\n  // Fields ({}) are{}\n  // Sorted by{}\n".format( structName, dictName, len(theDict), fieldsCount, structure, sortedBy ) )
            for dictKey in sorted(theDict.keys()):
                if isinstance( dictKey, str ):
                    cFile.write( "  {\"{}\",{}},\n".format( dictKey, convertEntry(theDict[dictKey]) ) )
                elif isinstance( dictKey, int ):
                    cFile.write( "  {{},{}},\n".format( dictKey, convertEntry(theDict[dictKey]) ) )
                else:
                    logging.error( _("Can't handle this type of data yet: {}").format( dictKey ) )
            cFile.write( "}; //{} ({} entries)\n\n".format( dictName, len(theDict) ) )
        # end of exportPythonDict

        def XXXexportPythonDict( theFile, theDict, dictName, structName, fieldsComment ):
            """Exports theDict to theFile."""
            def convertEntry( entry ):
                """Convert special characters in an entry…"""
                result = ""
                for field in entry if isinstance( entry, list) else entry.items():
                    #print( field )
                    if result: result += ", " # Separate the fields
                    if field is None: result += '""'
                    elif isinstance( field, str): result += '"' + str(field).replace('"','\\"') + '"'
                    elif isinstance( field, int): result += str(field)
                    elif isinstance( field, tuple):
                        tupleResult = ""
                        for tupleField in field:
                            #print( field, tupleField )
                            if tupleResult: tupleResult += "," # Separate the fields (without a space)
                            if tupleField is None: tupleResult += '""'
                            elif isinstance( tupleField, str): tupleResult += '"' + str(tupleField).replace('"','\\"') + '"'
                            elif isinstance( tupleField, int): tupleResult += str(tupleField)
                            else: logging.error( _("Cannot convert unknown tuplefield type {!r} in entry {!r} for {}").format( tupleField, entry, field ) )
                        result += tupleResult
                    else: logging.error( _("Cannot convert unknown field type {!r} in entry {!r}").format( field, entry ) )
                return result

            theFile.write( "static struct{}{}[{}] = {\n  // Fields are{}\n".format( structName, dictName, len(theDict), fieldsComment ) )
            for dictKey in sorted(theDict.keys()):
                if isinstance( dictKey, str ):
                    #print( dictKey, theDict[dictKey] )
                    theFile.write( "  {\"{}\",{}},\n".format( dictKey, convertEntry(theDict[dictKey]) ) )
                elif isinstance( dictKey, int ):
                    theFile.write( "  {{},{}},\n".format( dictKey, convertEntry(theDict[dictKey]) ) )
                else:
                    logging.error( _("Can't handle this type of key data yet: {}").format( dictKey ) )
            theFile.write( "}; //{} ({} entries)\n\n".format( dictName, len(theDict) ) )
        # end of XXXexportPythonDict


        assert self.__XMLSystems
        self.importDataToPython()
        assert self.__DataDict

        if not filepath: filepath = os.path.join( self.__XMLFolder, "../", 'DerivedFiles/', self.__filenameBase + "_Tables" )
        hFilepath = filepath + '.h'
        cFilepath = filepath + '.c'
        if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Exporting to {}…").format( cFilepath ) ) # Don't bother telling them about the .h file
        ifdefName = self.__filenameBase.upper() + "_Tables_h"

        with open( hFilepath, 'wt', encoding='utf-8' ) as myHFile, \
             open( cFilepath, 'wt', encoding='utf-8' ) as myCFile:
            myHFile.write( "//{}\n//\n".format( hFilepath ) )
            myCFile.write( "//{}\n//\n".format( cFilepath ) )
            lines = "// This UTF-8 file was automatically generated by BibleVersificationSystems.py V{} on {}\n//\n".format( programVersion, datetime.now() )
            myHFile.write( lines ); myCFile.write( lines )
            myCFile.write( "//  {}{} loaded from the original XML file.\n//\n\n".format( len(self.__XMLSystems), self.__treeTag ) )
            myHFile.write( "\n#ifndef{}\n#define{}\n\n".format( ifdefName, ifdefName ) )
            myCFile.write( '#include "{}"\n\n'.format( os.path.basename(hFilepath) ) )

            # This needs to be thought out better :(
            # Need to put all CV data for all books into an array
            #  and then have another level that points into it
            #    BBB, numChapters, startIndex
            raise Exception( "Sorry, this c export isn't working yet :(" )

            CHAR = "const unsigned char"
            BYTE = "const int"
            N1 = "CVCount"
            N2 = "CVCounts"
            N3 = "CVOmitted"
            N4 = "CVOmits"
            S1 = "{}* chapterNumberString;{}* numVersesString;".format(CHAR,CHAR)
            S2 = "{} referenceAbbreviation[3+1];{}Entry numVersesString[];".format(CHAR,N1)
            S3 = "{}* chapterNumberString;{}* verseNumberString;".format(CHAR,CHAR)
            S4 = "{} referenceAbbreviation[3+1];{}Entry numVersesString[];".format(CHAR,N3)
            writeStructure( myHFile, N1, S1 )
            writeStructure( myHFile, N2, S2 )
            writeStructure( myHFile, N3, S4 )
            writeStructure( myHFile, N4, S4 )
            writeStructure( myHFile, "table", "{}* systemName;{}Entry* systemCVCounts;{}Entry* systemOmittedVerses;".format(CHAR,N2,N4) ) # I'm not sure if I need one or two asterisks on those last two
                                                                                                        # They're supposed to be pointers to an array of structures
            myHFile.write( "#endif //{}\n\n".format( ifdefName ) )
            myHFile.write( "// end of {}".format( os.path.basename(hFilepath) ) )

            #myHFile.write( "static struct {struct char*, void*, void*} versificationSystemNames[{}] = {\n  // Fields are systemName, systemVersification, systemOmittedVerses\n".format( len(versificationSystemDict) ) )

            for systemName,systemInfo in self.__DataDict.items(): # Now write out the actual data into the .c file
                myCFile.write( "\n//{}\n".format( systemName ) )
                exportPythonDict( myCFile, systemInfo[0], systemName+"CVDict", N1+"Entry", "referenceAbbreviation", S1 )
                exportPythonDict( myCFile, systemInfo[1], systemName+"OmittedVersesDict", N2+"Entry", "indexNumber", S2 )

                break # Just do one for now
#            for systemName in self.__DataDict: # Now write out the actual data into the .c file
#                print( systemName )
#                myCFile.write( '  { "{}",{}_versificationSystem,{}_omittedVerses },\n'.format( systemName, systemName, systemName ) )
#            myCFile.write( "}; // versificationSystemNames ({} entries)\n\n".format( len(self.__DataDict) ) )
#            for systemName in self.__DataDict:
#                print( systemName )
#                myCFile.write( "#\n#{}\n".format( systemName ) )
#                exportPythonDict( myCFile, self.__DataDict[systemName][0], systemName+"_versificationSystem", "{struct char* stuff[]}", "tables containing referenceAbbreviation, (\"numChapters\", numChapters) then pairs of chapterNumber,numVerses" )
#                exportPythonDict( myCFile, self.__DataDict[systemName][1], systemName+"_omittedVerses", "{struct char* stuff[]}", "tables containing referenceAbbreviation then pairs of chapterNumber,omittedVerseNumber" )
#                exportPythonDict( myCFile, self.__DataDict[systemName][1], "omittedVersesDict", "{struct char* stuff[]}", "tables containing referenceAbbreviation then pairs of chapterNumber,omittedVerseNumber" )

            # Write out the final table of pointers to the above information
            myCFile.write( "\n// Pointers to above data\nconst static tableEntry bookOrderSystemTable[{}] = {\n".format( len(self.__DataDict) ) )
            for systemName in self.__DataDict: # Now write out the actual pointer data into the .c file
                myCFile.write( '  { "{}",{},{} },\n'.format( systemName, systemName+"CVDict", systemName+"OmittedVersesDict" ) )
            myCFile.write( "}; //{} entries\n\n".format( len(self.__DataDict) ) )
            myCFile.write( "// end of {}".format( os.path.basename(cFilepath) ) )
    # end of BibleVersificationSystemsConverter.exportDataToC
# end of BibleVersificationSystemsConverter class



def demo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel > 1: print( programNameVersion )

    bvsc = BibleVersificationSystemsConverter().loadSystems() # Load the XML
    if BibleOrgSysGlobals.commandLineArguments.export:
        bvsc.pickle() # Produce the .pickle file
        bvsc.exportDataToPython() # Produce the .py tables
        bvsc.exportDataToJSON() # Produce a json output file
        bvsc.exportDataToC() # Produce the .h and .c tables

    else: # Must be demo mode
        print( bvsc ) # Just print a summary
# end of demo


if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( programName, programVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    demo()

    BibleOrgSysGlobals.closedown( programName, programVersion )
# end of BibleVersificationSystemsConverter.py
