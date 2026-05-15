#!/usr/bin/env -S uv run
# -\*- coding: utf-8 -\*-
# SPDX-License-Identifier: GPL-3.0-or-later
#
# BibleVersificationSystemsConverter.py
#
# Module handling loading of BibleVersificationSystem_*.xml to produce C and Python data tables
#
# Copyright (C) 2010-2021 Robert Hunt
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
Module handling BibleVersificationSystem_*.xml to produce C and Python data tables.

NOTE: We still lack a REFERENCE Bible versification system
        with back-and-forth mappings. This is a MAJOR outstanding deficiency.
"""
import os
import logging
from datetime import datetime
from xml.etree.ElementTree import ElementTree

from BibleOrgSys.Misc.singleton import singleton
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
import bos_books_codes_py


LAST_MODIFIED_DATE = '2021-01-19' # by RJH
SHORT_PROGRAM_NAME = "BibleVersificationSystemsConverter"
PROGRAM_NAME = "Bible Versification Systems converter"
PROGRAM_VERSION = '0.51'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False




@singleton # Can only ever have one instance
class BibleVersificationSystemsConverter:
    """
    A class to load and export XML data for Bible versification systems.
    """

    def __init__( self ) -> None:
        """
        Constructor.
        """
        self.__filenameBase = "BibleVersificationSystems"

        # These fields are used for parsing the XML
        self.__treeTag = "BibleVersificationSystem"
        self.__headerTag = 'header'
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
            if XMLFolder is None: XMLFolder = BibleOrgSysGlobals.BOS_DATAFILES_FOLDERPATH.joinpath( "VersificationSystems" ) # Relative to module, not cwd
            self.__XMLFolder = XMLFolder
            vPrint( 'Info', DEBUGGING_THIS_MODULE, f"Loading versification systems from {XMLFolder}…" )
            filenamePrefix = "BIBLEVERSIFICATIONSYSTEM_"
            for filename in os.listdir( XMLFolder ):
                filepart, extension = os.path.splitext( filename )
                if extension.upper() == '.XML' and filepart.upper().startswith(filenamePrefix):
                    versificationSystemCode = filepart[len(filenamePrefix):]
                    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"Loading{versificationSystemCode} versification system from {filename}…" )
                    self.__XMLSystems[versificationSystemCode] = {}
                    self.__XMLSystems[versificationSystemCode]['tree'] = ElementTree().parse( os.path.join( XMLFolder, filename ) )
                    assert self.__XMLSystems[versificationSystemCode]['tree'] # Fail here if we didn't load anything at all

                    # Check and remove the header element
                    if self.__XMLSystems[versificationSystemCode]['tree'].tag  == self.__treeTag:
                        header = self.__XMLSystems[versificationSystemCode]['tree'][0]
                        if header.tag == self.__headerTag:
                            self.__XMLSystems[versificationSystemCode]['header'] = header
                            self.__XMLSystems[versificationSystemCode]['tree'].remove( header )
                            if len(header)>1:
                                logging.info( "Unexpected elements in header" )
                            elif len(header)==0:
                                logging.info( "Missing work element in header" )
                            else:
                                work = header[0]
                                if work.tag == "work":
                                    self.__XMLSystems[versificationSystemCode]['version'] = work.find('version').text
                                    self.__XMLSystems[versificationSystemCode]['date'] = work.find('date').text
                                    self.__XMLSystems[versificationSystemCode]['title'] = work.find('title').text
                                else:
                                    logging.warning( "Missing work element in header" )
                        else:
                            logging.warning( f"Missing header element (looking for {self.__headerTag!r} tag)" )
                    else:
                        logging.error( f"Expected to load {self.__treeTag!r} but got {self.__XMLSystems[versificationSystemCode]['tree'].tag!r}" )
                    bookCount = 0 # There must be an easier way to do this
                    for subelement in self.__XMLSystems[versificationSystemCode]['tree']:
                        bookCount += 1
                    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"    Loaded {bookCount} books for {versificationSystemCode}" )
                    logging.info( f"    Loaded {bookCount} books for {versificationSystemCode}" )

                    if BibleOrgSysGlobals.strictCheckingFlag:
                        self._validateSystem( self.__XMLSystems[versificationSystemCode]['tree'] )
        else: # The data must have been already loaded
            if XMLFolder is not None and XMLFolder!=self.__XMLFolder: logging.error( f"Bible versification systems are already loaded -- your different folder of {XMLFolder!r} was ignored" )
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
                        logging.error( f"Compulsory {k!r} attribute is missing from {attributeName} element in record {element.tag}" )
                    if not attributeValue:
                        logging.warning( f"Compulsory {k!r} attribute is blank on {attributeName} element in record {element.tag}" )

                # Check optional attributes on this main element
                for attributeName in self.__optionalAttributes:
                    attributeValue = element.get( attributeName )
                    if attributeValue is not None:
                        if not attributeValue:
                            logging.warning( f"Optional {k!r} attribute is blank on {attributeName} element in record {element.tag}" )

                # Check for unexpected additional attributes on this main element
                for attributeName in element.keys():
                    attributeValue = element.get( attributeName )
                    if attributeName not in self.__compulsoryAttributes and attributeName not in self.__optionalAttributes:
                        logging.warning( f"Additional {element.tag!r} attribute ({k!r}) found on {attributeName} element in record {attributeValue}" )

                # Check the attributes that must contain unique information (in that particular field -- doesn't check across different attributes)
                for attributeName in self.__uniqueAttributes:
                    attributeValue = element.get( attributeName )
                    if attributeValue is not None:
                        if attributeValue in uniqueDict["Attribute_"+attributeName]:
                            logging.error( f"Found {element.tag!r} data repeated in {k!r} field on {attributeValue} element in record {attributeName}" )
                        uniqueDict["Attribute_"+attributeName].append( attributeValue )

                # Check compulsory elements
                ID = element.find("referenceAbbreviation").text
                for elementName in self.__compulsoryElements:
                    if element.find( elementName ) is None:
                        logging.error( f"Compulsory {ID!r} element is missing in record with ID {k!r} (record {elementName})" )
                    if not element.find( elementName ).text:
                        logging.warning( f"Compulsory {ID!r} element is blank in record with ID {k!r} (record {elementName})" )

                # Check optional elements
                for elementName in self.__optionalElements:
                    if element.find( elementName ) is not None:
                        if not element.find( elementName ).text:
                            logging.warning( f"Optional {ID!r} element is blank in record with ID {k!r} (record {elementName})" )

                # Check for unexpected additional elements
                for subelement in element:
                    if subelement.tag not in self.__compulsoryElements and subelement.tag not in self.__optionalElements:
                        logging.warning( f"Additional {subelement.text!r} element ({ID!r}) found in record with ID {k!r} (record {subelement.tag})" )

                # Check the elements that must contain unique information (in that particular element -- doesn't check across different elements)
                for elementName in self.__uniqueElements:
                    if element.find( elementName ) is not None:
                        text = element.find( elementName ).text
                        if text in uniqueDict["Element_"+elementName]:
                            logging.error( f"Found {elementName!r} data repeated in {ID!r} element in record with ID {k!r} (record {text})" )
                        uniqueDict["Element_"+elementName].append( text )
            else:
                logging.warning( f"Unexpected element: {element.tag} in record {k}" )
    # end of BibleVersificationSystemsConverter._validateSystem


    def __str__( self ) -> str:
        """
        This method returns the string representation of a Bible versification system.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = "BibleVersificationSystemsConverter object"
        #if self.__title: result += ('\n' if result else '') + self.__title
        #if self.__version: result += ('\n' if result else '') + f"Version:{self.__version}"
        #if self.__date: result += ('\n' if result else '') + f"Date:{self.__date}"
        result += ('\n' if result else '') + f"  Number of versification systems loaded = {len(self.__XMLSystems)}"
        if 0: # Make it verbose
            for x in self.__XMLSystems:
                result += ('\n' if result else '') + f" {x}"
                title = self.__XMLSystems[x]['title']
                if title: result += ('\n' if result else '') + f"   {title}"
                version = self.__XMLSystems[x]['version']
                if version: result += ('\n    ' if result else '    ') + f"Version: {version}"
                date = self.__XMLSystems[x]['date']
                if date: result += ('\n    ' if result else '    ') + f"Last updated: {date}"
                result += ('\n' if result else '') + f"    Number of books = {len(self.__XMLSystems[x]['tree'])}"
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
                if totalChapters: result += ('\n' if result else '') + f"      Total chapters = {totalChapters}"
                if totalVerses: result += ('\n' if result else '') + f"      Total verses = {totalVerses}"
                if totalOmittedVerses: result += ('\n' if result else '') + f"      Total omitted verses = {totalOmittedVerses}"
                if numCombinedVersesInstances: result += ('\n' if result else '') + f"      Number of combined verses instances = {numCombinedVersesInstances}"
                if numRecorderedVersesInstances: result += ('\n' if result else '') + f"      Number of reordered verses instances = {numRecorderedVersesInstances}"
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
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, versificationSystemCode )
            # Make the data dictionary for this versification system
            chapterDataDict, omittedVersesDict, combinedVersesDict, reorderedVersesDict = {}, {}, {}, {}
            for bookElement in self.__XMLSystems[versificationSystemCode]['tree']:
                BBB = bookElement.find("referenceAbbreviation").text
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, BBB )
                if not bos_books_codes_py.is_valid_bos_book_code( BBB ):
                    logging.error( f"Unrecognized {BBB!r} book abbreviation in {versificationSystemCode!r} versification system" )
                numChapters = bookElement.find("numChapters").text # This is a string

                # Check the chapter data against the expected chapters in the BibleBooksCodes data
                if numChapters not in bos_books_codes_py.get_expected_chapters_list(BBB):
                    logging.info( f"Expected number of chapters for {BBB} is {bos_books_codes_py.get_expected_chapters_list(BBB)} but we got {numChapters!r} for {versificationSystemCode}" )

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
                    logging.error( f"Duplicate {BBB} in {versificationSystemCode}" )
                chapterDataDict[BBB] = chapterData
                if BBB in omittedVersesDict:
                    logging.error( f"Duplicate omitted verse data for {BBB} in {versificationSystemCode}" )
                if omittedVersesData: omittedVersesDict[BBB] = omittedVersesData
                if combinedVersesData: combinedVersesDict[BBB] = combinedVersesData
                if reorderedVersesData: reorderedVersesDict[BBB] = reorderedVersesData

            if BibleOrgSysGlobals.strictCheckingFlag: # check for duplicates
                for checkSystemCode in self.__DataDict:
                    checkChapterDataDict, checkOmittedVersesDict, checkCombinedVersesDict, checkReorderedVersesDict = self.__DataDict[checkSystemCode]['CV'], self.__DataDict[checkSystemCode]['omitted'], self.__DataDict[checkSystemCode]['combined'], self.__DataDict[checkSystemCode]['reordered']
                    if checkChapterDataDict==chapterDataDict:
                        if checkOmittedVersesDict==omittedVersesDict:
                            logging.error( f"{versificationSystemCode} and {checkSystemCode} versification systems are exactly identical" )
                        else: # only the omitted verse lists differ
                            logging.warning( f"{versificationSystemCode} and {checkSystemCode} versification systems are mostly identical (omitted verse lists differ)" )
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
                                logging.warning( f"The {numCommon} common books in {versificationSystemCode} ({len(chapterDataDict)}) and {checkSystemCode} ({len(checkChapterDataDict)}) versification systems are exactly identical" )
                            else: # only the omitted verse lists differ
                                logging.warning( f"The {numCommon} common books in {versificationSystemCode} ({len(chapterDataDict)}) and {checkSystemCode} ({len(checkChapterDataDict)}) versification systems are mostly identical (omitted verse lists differ)" )


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
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Validating {versificationSystemCode}…" )
            thisSystem = self.__DataDict[versificationSystemCode]
            for versificationSystemCode2 in self.__DataDict:
                if versificationSystemCode2 != versificationSystemCode:
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  Comparing with", versificationSystemCode2 )
                    secondSystem = self.__DataDict[versificationSystemCode2]
                    if thisSystem == secondSystem: logging.warning( f"The {versificationSystemCode} and {versificationSystemCode2} systems are identical." )

            if versificationSystemCode == referenceCode:
                assert not thisSystem['omitted']
                assert not thisSystem['combined']
                assert not thisSystem['reordered']
            else:
                for BBB in thisSystem['CV']:
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, BBB )
                    if BBB not in referenceVersificationSystem['CV']:
                        logging.warning( f"The {versificationSystemCode} system contains book {BBB} which is not in {referenceCode}" )
                    elif int(thisSystem['CV'][BBB]['numChapters']) > int(referenceVersificationSystem['CV'][BBB]['numChapters']):
                        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, '2', thisSystem['CV'][BBB]['numChapters'], referenceVersificationSystem['CV'][BBB]['numChapters'] )
                        logging.warning( f"The {versificationSystemCode} system contains {thisSystem['CV'][BBB]['numChapters']} chapters for {BBB} while only {referenceVersificationSystem['CV'][BBB]['numChapters']} in {referenceCode}" )
                    else:
                        for ch in range( 1, int(thisSystem['CV'][BBB]['numChapters']) + 1 ):
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, ch )
                            ok = True
                            try: v = int( thisSystem['CV'][BBB][str(ch)] )
                            except KeyError:
                                logging.warning( f"The {versificationSystemCode} system has chapter {ch} missing for {BBB}" )
                                ok = False
                            try: vr = int( referenceVersificationSystem['CV'][BBB][str(ch)] )
                            except KeyError:
                                logging.warning( f"The {referenceCode} system has chapter {ch} missing for {BBB}" )
                                ok = False
                            if ok and v > vr:
                                logging.warning( f"The {versificationSystemCode} system contains {v} verses for {BBB} {ch} while only {vr} in {referenceCode}" )

    def pickle( self, filepath=None ):
        """
        Writes the information tables to a .pickle file that can be easily loaded into a Python3 program.
        """
        import pickle

        assert self.__XMLSystems
        self.importDataToPython()
        assert self.__DataDict

        if not filepath:
            folder = BibleOrgSysGlobals.DEFAULT_WRITEABLE_DERIVED_DATAFILES_FOLDERPATH
            if not os.path.exists( folder ): os.mkdir( folder )
            filepath = os.path.join( folder, self.__filenameBase + '_Tables.pickle' )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Exporting to {filepath}…" )
        with open( filepath, 'wb' ) as pickleFile:
            pickle.dump( self.__DataDict, pickleFile )
    # end of BibleVersificationSystemsConverter.pickle


    def exportDataToPython( self, filepath=None ):
        """
        Writes the information tables to a .py file that can be cut and pasted into a Python program.
        """
        def exportPythonDict( theFile, theDict, systemName, keyComment, fieldsComment ):
            """Exports theDict to theFile."""
            theFile.write( f'  "{systemName}": {{\n    # Key is{keyComment}\n    # Fields are:{fieldsComment}\n' )
            for dictKey in theDict.keys():
                theFile.write( f'   {repr(dictKey)}:{theDict[dictKey]},\n' )
            theFile.write( f"  }}, # end of {systemName} ({len(theDict)} entries)\n\n" )
        # end of exportPythonDict


        assert self.__XMLSystems
        self.importDataToPython()
        assert self.__DataDict

        if not filepath: filepath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_DERIVED_DATAFILES_FOLDERPATH.joinpath( self.__filenameBase + '_Tables.py' )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Exporting to {filepath}…" )
        versificationSystemDict = self.importDataToPython()
        # Split into two dictionaries
        with open( filepath, 'wt', encoding='utf-8' ) as myFile:
            myFile.write( f"#{filepath}\n#\n" )
            myFile.write( f"# This UTF-8 file was automatically generated by BibleVersificationSystems.py V{PROGRAM_VERSION} on {datetime.now()}\n#\n" )
            #if self.__title: myFile.write( f"#{self.__title}\n" )
            #if self.__version: myFile.write( f"#  Version:{self.__version}\n" )
            #if self.__date: myFile.write( f"#  Date:{self.__date}\n#\n" )
            myFile.write( f"#  {len(self.__XMLSystems)}{self.__treeTag} loaded from the original XML files.\n#\n\n" )
            #myFile.write( "from collections import OrderedDict\n\n" )
            myFile.write( "chapterVerseDict = {\n  # Key is versificationSystemName\n  # Fields are versificationSystem\n" )
            for systemName in versificationSystemDict:
                exportPythonDict( myFile, versificationSystemDict[systemName]['CV'], systemName, "BBB referenceAbbreviation", "tuples containing (\"numChapters\", numChapters) then (chapterNumber, numVerses)" )
            myFile.write( f"}} # end of chapterVerseDict ({len(versificationSystemDict)} systems)\n\n" )
            myFile.write( "omittedVersesDict = {{\n  # Key is versificationSystemName\n  # Fields are omittedVersesSystem\n" )
            for systemName in versificationSystemDict:
                exportPythonDict( myFile, versificationSystemDict[systemName]['omitted'], systemName, "BBB referenceAbbreviation", "tuples containing (chapterNumber, omittedVerseNumber)" )
            myFile.write( f"}} # end of omittedVersesDict ({len(versificationSystemDict)} systems)\n\n" )
            myFile.write( "combinedVersesDict = {{\n  # Key is versificationSystemName\n  # Fields are combinedVersesSystem\n" )
            for systemName in versificationSystemDict:
                exportPythonDict( myFile, versificationSystemDict[systemName]['combined'], systemName, "BBB referenceAbbreviation", "tuples containing (chapterNumber, omittedVerseNumber)" )
            myFile.write( f"}} # end of combinedVersesDict ({len(versificationSystemDict)} systems)\n\n" )
            myFile.write( "reorderedVersesDict = {{\n  # Key is versificationSystemName\n  # Fields are reorderedVersesSystem\n" )
            for systemName in versificationSystemDict:
                exportPythonDict( myFile, versificationSystemDict[systemName]['reordered'], systemName, "BBB referenceAbbreviation", "tuples containing (chapterNumber, omittedVerseNumber)" )
            myFile.write( f"}} # end of reorderedVersesDict ({len(versificationSystemDict)} systems)\n\n" )
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

        if not filepath: filepath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_DERIVED_DATAFILES_FOLDERPATH.joinpath( self.__filenameBase + '_Tables.json' )
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Exporting to {filepath}…" )
        with open( filepath, 'wt', encoding='utf-8' ) as myFile:
            #myFile.write( f"#{filepath}\n#\n" ) # Not sure yet if these comment fields are allowed in JSON
            #myFile.write( f"# This UTF-8 file was automatically generated by BibleVersificationSystems.py V{PROGRAM_VERSION} on {datetime.now()}\n#\n" )
            #if self.__titleString: myFile.write( f"#{self.__titleString} data\n" )
            #if self.__ProgVersion: myFile.write( f"#  Version:{self.__ProgVersion}\n" )
            #if self.__dateString: myFile.write( f"#  Date:{self.__dateString}\n#\n" )
            #myFile.write( f"#  {len(self.__XMLTree)}{self.__treeTag} loaded from the original XML file.\n#\n\n" )
            json.dump( self.__DataDict, myFile, ensure_ascii=False, indent=2 )
            #myFile.write( f"\n\n# end of {os.path.basename(filepath)}" )
    # end of BibleVersificationSystemsConverter.exportDataToJSON


    def exportDataToC( self, filepath=None ):
        """
        Writes the information tables to a .h file that can be included in c and c++ programs.
        """
        def writeStructure( hFile, structName, structure ):
            """ Writes a typedef to the .h file. """
            hFile.write( f"typedef struct{structName}EntryStruct {\n" )
            for declaration in structure.split(';'):
                adjDeclaration = declaration.strip()
                if adjDeclaration: hFile.write( f"   {adjDeclaration};\n" )
            hFile.write( f"}{structName}Entry;\n\n" )
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
                            result += f"{{tupleResult} }"
                        else: logging.error( f"Cannot convert unknown field type {field!r} in entry {entry!r}" )
                return result
            # end of convertEntry

            #for dictKey in theDict.keys(): # Have to iterate this :(
            #    fieldsCount = len( theDict[dictKey] ) + 1 # Add one since we include the key in the count
            #    break # We only check the first (random) entry we get
            fieldsCount = 2

            cFile.write( f"const static{structName}\n{dictName}[{len(theDict)}] = {\n  // Fields ({fieldsCount}) are{structure}\n  // Sorted by{sortedBy}\n" )
            for dictKey in sorted(theDict.keys()):
                if isinstance( dictKey, str ):
                    cFile.write( f"  {\"{dictKey}\",{convertEntry(theDict[dictKey])}},\n" )
                elif isinstance( dictKey, int ):
                    cFile.write( f"  {{dictKey},{convertEntry(theDict[dictKey])}},\n" )
                else:
                    logging.error( f"Can't handle this type of data yet: {dictKey}" )
            cFile.write( f"}; //{dictName} ({len(theDict)} entries)\n\n" )
        # end of exportPythonDict

        def XXXexportPythonDict( theFile, theDict, dictName, structName, fieldsComment ):
            """Exports theDict to theFile."""
            def convertEntry( entry ):
                """Convert special characters in an entry…"""
                result = ""
                for field in entry if isinstance( entry, list) else entry.items():
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, field )
                    if result: result += ", " # Separate the fields
                    if field is None: result += '""'
                    elif isinstance( field, str): result += '"' + str(field).replace('"','\\"') + '"'
                    elif isinstance( field, int): result += str(field)
                    elif isinstance( field, tuple):
                        tupleResult = ""
                        for tupleField in field:
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, field, tupleField )
                            if tupleResult: tupleResult += "," # Separate the fields (without a space)
                            if tupleField is None: tupleResult += '""'
                            elif isinstance( tupleField, str): tupleResult += '"' + str(tupleField).replace('"','\\"') + '"'
                            elif isinstance( tupleField, int): tupleResult += str(tupleField)
                            else: logging.error( f"Cannot convert unknown tuplefield type {entry!r} in entry {field!r} for {tupleField}" )
                        result += tupleResult
                    else: logging.error( f"Cannot convert unknown field type {field!r} in entry {entry!r}" )
                return result

            theFile.write( f"static struct{structName}{dictName}[{len(theDict)}] = {\n  // Fields are{fieldsComment}\n" )
            for dictKey in sorted(theDict.keys()):
                if isinstance( dictKey, str ):
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, dictKey, theDict[dictKey] )
                    theFile.write( f"  {\"{dictKey}\",{convertEntry(theDict[dictKey])}},\n" )
                elif isinstance( dictKey, int ):
                    theFile.write( f"  {{dictKey},{convertEntry(theDict[dictKey])}},\n" )
                else:
                    logging.error( f"Can't handle this type of key data yet: {dictKey}" )
            theFile.write( f"}; //{dictName} ({len(theDict)} entries)\n\n" )
        # end of XXXexportPythonDict


        assert self.__XMLSystems
        self.importDataToPython()
        assert self.__DataDict

        if not filepath: filepath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_DERIVED_DATAFILES_FOLDERPATH.joinpath( self.__filenameBase + '_Tables' )
        hFilepath = filepath + '.h'
        cFilepath = filepath + '.c'
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Exporting to {cFilepath}…" ) # Don't bother telling them about the .h file
        ifdefName = self.__filenameBase.upper() + "_Tables_h"

        with open( hFilepath, 'wt', encoding='utf-8' ) as myHFile, \
             open( cFilepath, 'wt', encoding='utf-8' ) as myCFile:
            myHFile.write( f"//{hFilepath}\n//\n" )
            myCFile.write( f"//{cFilepath}\n//\n" )
            lines = f"// This UTF-8 file was automatically generated by BibleVersificationSystems.py V{PROGRAM_VERSION} on {datetime.now()}\n//\n"
            myHFile.write( lines ); myCFile.write( lines )
            myCFile.write( f"//  {len(self.__XMLSystems)}{self.__treeTag} loaded from the original XML file.\n//\n\n" )
            myHFile.write( f"\n#ifndef{ifdefName}\n#define{ifdefName}\n\n" )
            myCFile.write( f'#include "{os.path.basename(hFilepath)}"\n\n' )

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
            S1 = f"{CHAR}* chapterNumberString;{CHAR}* numVersesString;"
            S2 = f"{CHAR} referenceAbbreviation[3+1];{N1}Entry numVersesString[];"
            S3 = f"{CHAR}* chapterNumberString;{CHAR}* verseNumberString;"
            S4 = f"{CHAR} referenceAbbreviation[3+1];{N3}Entry numVersesString[];"
            writeStructure( myHFile, N1, S1 )
            writeStructure( myHFile, N2, S2 )
            writeStructure( myHFile, N3, S4 )
            writeStructure( myHFile, N4, S4 )
            writeStructure( myHFile, "table", f"{CHAR}* systemName;{N2}Entry* systemCVCounts;{N4}Entry* systemOmittedVerses;" ) # I'm not sure if I need one or two asterisks on those last two
                                                                                                        # They're supposed to be pointers to an array of structures
            myHFile.write( f"#endif //{ifdefName}\n\n" )
            myHFile.write( f"// end of {os.path.basename(hFilepath)}" )

            #myHFile.write( f"static struct {struct char*, void*, void*} versificationSystemNames[{len(versificationSystemDict)}] = {\n  // Fields are systemName, systemVersification, systemOmittedVerses\n" )

            for systemName,systemInfo in self.__DataDict.items(): # Now write out the actual data into the .c file
                myCFile.write( f"\n//{systemName}\n" )
                exportPythonDict( myCFile, systemInfo[0], systemName+"CVDict", N1+"Entry", "referenceAbbreviation", S1 )
                exportPythonDict( myCFile, systemInfo[1], systemName+"OmittedVersesDict", N2+"Entry", "indexNumber", S2 )

                break # Just do one for now
#            for systemName in self.__DataDict: # Now write out the actual data into the .c file
#                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, systemName )
#                myCFile.write( f'  { "{systemName}",{systemName}_versificationSystem,{systemName}_omittedVerses },\n' )
#            myCFile.write( f"}; // versificationSystemNames ({len(self.__DataDict)} entries)\n\n" )
#            for systemName in self.__DataDict:
#                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, systemName )
#                myCFile.write( f"#\n#{systemName}\n" )
#                exportPythonDict( myCFile, self.__DataDict[systemName][0], systemName+"_versificationSystem", "{struct char* stuff[]}", "tables containing referenceAbbreviation, (\"numChapters\", numChapters) then pairs of chapterNumber,numVerses" )
#                exportPythonDict( myCFile, self.__DataDict[systemName][1], systemName+"_omittedVerses", "{struct char* stuff[]}", "tables containing referenceAbbreviation then pairs of chapterNumber,omittedVerseNumber" )
#                exportPythonDict( myCFile, self.__DataDict[systemName][1], "omittedVersesDict", "{struct char* stuff[]}", "tables containing referenceAbbreviation then pairs of chapterNumber,omittedVerseNumber" )

            # Write out the final table of pointers to the above information
            myCFile.write( f"\n// Pointers to above data\nconst static tableEntry bookOrderSystemTable[{len(self.__DataDict)}] = {\n" )
            for systemName in self.__DataDict: # Now write out the actual pointer data into the .c file
                myCFile.write( f'  { "{systemName}",{systemName+"CVDict"},{systemName+"OmittedVersesDict"} },\n' )
            myCFile.write( f"}; //{len(self.__DataDict)} entries\n\n" )
            myCFile.write( f"// end of {os.path.basename(cFilepath)}" )
    # end of BibleVersificationSystemsConverter.exportDataToC
# end of BibleVersificationSystemsConverter class



def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    bvsc = BibleVersificationSystemsConverter().loadSystems() # Load the XML
    if BibleOrgSysGlobals.commandLineArguments.export:
        bvsc.pickle() # Produce the .pickle file
        bvsc.exportDataToJSON() # Produce a json output file
        bvsc.exportDataToPython() # Produce the .py tables
        # bvsc.exportDataToC() # Produce the .h and .c tables

    else: # Must be demo mode
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, bvsc ) # Just print a summary
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

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of BibleVersificationSystemsConverter.py
