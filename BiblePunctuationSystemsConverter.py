#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# BiblePunctuationSystemsConverter.py
#
# Module handling BiblePunctuationSystem_*.xml to produce C and Python data tables
#   Last modified: 2011-05-29 (also update versionString below)
#
# Copyright (C) 2010-2011 Robert Hunt
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
Module handling BiblePunctuation_*.xml and to export to JSON, C, and Python data tables.
"""

progName = "Bible Punctuation Systems handler"
versionString = "0.43"


import os, logging
from gettext import gettext as _
from collections import OrderedDict
from xml.etree.cElementTree import ElementTree

from singleton import singleton
import Globals


@singleton # Can only ever have one instance
class BiblePunctuationSystemsConverter:
    """
    A class to handle data for Bible punctuation systems.
    """

    def __init__( self ):
        """
        Constructor.
        """
        self.__filenameBase = "BiblePunctuationSystems"

        # These fields are used for parsing the XML
        self.treeTag = "BiblePunctuationSystem"
        self.headerTag = "header"
        self.mainElementTags = ( "sentenceCapitalisation", "properNounCapitalisation", "statementTerminator", "questionTerminator", "exclamationTerminator", "commaPauseCharacter",
                    "startQuoteLevel1", "endQuoteLevel1", "startQuoteLevel2", "endQuoteLevel2", "startQuoteLevel3", "endQuoteLevel3", "startQuoteLevel4", "endQuoteLevel4",
                    "booknameCase", "booknameLength", "punctuationAfterBookAbbreviation", "bookChapterSeparator", "spaceAllowedAfterBCS",
                    "chapterVerseSeparator", "verseSeparator", "bookBridgeCharacter", "chapterBridgeCharacter", "verseBridgeCharacter", "chapterSeparator", "bookSeparator", "allowedVerseSuffixes" )

        # These fields are used for automatically checking/validating the XML
        self.compulsoryAttributes = ()
        self.optionalAttributes = ()
        self.uniqueAttributes = self.compulsoryAttributes + self.optionalAttributes
        self.compulsoryElements = ()
        self.optionalElements = ()
        self.uniqueElements = self.compulsoryElements + self.optionalElements


        # These are fields that we will fill later
        self.__XMLFolder = None
        self._XMLSystems = {}
        self._DataDict = {} # Used for import
    # end of __init__

    def loadSystems( self, XMLFolder=None ):
        """
        Load and pre-process the specified punctuation systems.
        """
        if not self._XMLSystems: # Only ever do this once
            if XMLFolder==None: XMLFolder = os.path.join( os.path.dirname(__file__), "DataFiles", "PunctuationSystems" ) # Relative to module, not cwd
            self.__XMLFolder = XMLFolder
            if Globals.verbosityLevel > 2: print( _("Loading punctuations systems from {}...").format( self.__XMLFolder ) )
            filenamePrefix = "BIBLEPUNCTUATIONSYSTEM_"
            for filename in os.listdir( self.__XMLFolder ):
                filepart, extension = os.path.splitext( filename )

                if extension.upper() == '.XML' and filepart.upper().startswith(filenamePrefix):
                    punctuationSystemCode = filepart[len(filenamePrefix):]
                    if Globals.verbosityLevel > 3: print( _("Loading {} punctuation system from {}...").format( punctuationSystemCode, filename ) )
                    self._XMLSystems[punctuationSystemCode] = {}
                    self._XMLSystems[punctuationSystemCode]["tree"] = ElementTree().parse( os.path.join( self.__XMLFolder, filename ) )
                    assert( self._XMLSystems[punctuationSystemCode]["tree"] ) # Fail here if we didn't load anything at all

                    # Check and remove the header element
                    if self._XMLSystems[punctuationSystemCode]["tree"].tag  == self.treeTag:
                        header = self._XMLSystems[punctuationSystemCode]["tree"][0]
                        if header.tag == self.headerTag:
                            self._XMLSystems[punctuationSystemCode]["header"] = header
                            self._XMLSystems[punctuationSystemCode]["tree"].remove( header )
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
                                    self._XMLSystems[punctuationSystemCode]["version"] = work.find("version").text
                                    self._XMLSystems[punctuationSystemCode]["date"] = work.find("date").text
                                    self._XMLSystems[punctuationSystemCode]["title"] = work.find("title").text
                                else:
                                    logging.warning( _("Missing work element in header") )
                        else:
                            logging.warning( _("Missing header element (looking for '{}' tag)").format( headerTag ) )
                    else:
                        logging.error( _("Expected to load '{}' but got '{}'").format( treeTag, self._XMLSystems[punctuationSystemCode]["tree"].tag ) )
                    bookCount = 0 # There must be an easier way to do this
                    for subelement in self._XMLSystems[punctuationSystemCode]["tree"]:
                        bookCount += 1
                    logging.info( _("    Loaded {} books").format( bookCount ) )

                    if Globals.strictCheckingFlag:
                        self._validateSystem( self._XMLSystems[punctuationSystemCode]["tree"], punctuationSystemCode )
        return self
    # end of loadSystems

    def _validateSystem( self, punctuationTree, systemName ):
        """
        """
        assert( punctuationTree )

        uniqueDict = {}
        for elementName in self.uniqueElements: uniqueDict["Element_"+elementName] = []
        for attributeName in self.uniqueAttributes: uniqueDict["Attribute_"+attributeName] = []

        for k,element in enumerate(punctuationTree):
            if element.tag in self.mainElementTags:
                Globals.checkXMLNoTail( element, element.tag )
                if not self.compulsoryAttributes and not self.optionalAttributes: Globals.checkXMLNoAttributes( element, element.tag )
                if not self.compulsoryElements and not self.optionalElements: Globals.checkXMLNoSubelements( element, element.tag )

                # Check compulsory attributes on this main element
                for attributeName in self.compulsoryAttributes:
                    attributeValue = element.get( attributeName )
                    if attributeValue is None:
                        logging.error( _("Compulsory '{}' attribute is missing from {} element in record {}").format( attributeName, element.tag, k ) )
                    if not attributeValue:
                        logging.warning( _("Compulsory '{}' attribute is blank on {} element in record {}").format( attributeName, element.tag, k ) )

                # Check optional attributes on this main element
                for attributeName in self.optionalAttributes:
                    attributeValue = element.get( attributeName )
                    if attributeValue is not None:
                        if not attributeValue:
                            logging.warning( _("Optional '{}' attribute is blank on {} element in record {}").format( attributeName, element.tag, k ) )

                # Check for unexpected additional attributes on this main element
                for attributeName in element.keys():
                    attributeValue = element.get( attributeName )
                    if attributeName not in self.compulsoryAttributes and attributeName not in self.optionalAttributes:
                        logging.warning( _("Additional '{}' attribute ('{}') found on {} element in record {}").format( attributeName, attributeValue, element.tag, k ) )

                # Check the attributes that must contain unique information (in that particular field -- doesn't check across different attributes)
                for attributeName in self.uniqueAttributes:
                    attributeValue = element.get( attributeName )
                    if attributeValue is not None:
                        if attributeValue in uniqueDict["Attribute_"+attributeName]:
                            logging.error( _("Found '{}' data repeated in '{}' field on {} element in record {}").format( attributeValue, attributeName, element.tag, k ) )
                        uniqueDict["Attribute_"+attributeName].append( attributeValue )

                # Check compulsory elements
                for elementName in self.compulsoryElements:
                    if element.find( elementName ) is None:
                        logging.error( _("Compulsory '{}' element is missing in record with ID '{}' (record {})").format( elementName, ID, k ) )
                    if not element.find( elementName ).text:
                        logging.warning( _("Compulsory '{}' element is blank in record with ID '{}' (record {})").format( elementName, ID, k ) )

                # Check optional elements
                for elementName in self.optionalElements:
                    if element.find( elementName ) is not None:
                        if not element.find( elementName ).text:
                            logging.warning( _("Optional '{}' element is blank in record with ID '{}' (record {})").format( elementName, ID, k ) )

                # Check for unexpected additional elements
                for subelement in element:
                    if subelement.tag not in self.compulsoryElements and subelement.tag not in self.optionalElements:
                        logging.warning( _("Additional '{}' element ('{}') found in record with ID '{}' (record {})").format( subelement.tag, subelement.text, ID, k ) )

                # Check the elements that must contain unique information (in that particular element -- doesn't check across different elements)
                for elementName in self.uniqueElements:
                    if element.find( elementName ) is not None:
                        text = element.find( elementName ).text
                        if text in uniqueDict["Element_"+elementName]:
                            logging.error( _("Found '{}' data repeated in '{}' element in record with ID '{}' (record {})").format( text, elementName, ID, k ) )
                        uniqueDict["Element_"+elementName].append( text )
            else:
                logging.warning( _("Unexpected element: {} in record {}").format( element.tag, k ) )
    # end of _validateSystem

    def __str__( self ):
        """
        This method returns the string representation of a Bible punctuation system.
        
        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = "BiblePunctuationSystemsConverter object"
        result += ('\n' if result else '') + "  Number of punctuation systems loaded = {}".format( len(self._XMLSystems) )
        if Globals.verbosityLevel > 2: # Make it verbose
            for x in self._XMLSystems:
                result += ('\n' if result else '') + "  {}".format( x )
                title = self._XMLSystems[x]["title"]
                if title: result += ('\n' if result else '') + "    {}".format( title )
                version = self._XMLSystems[x]["version"]
                if version: result += ('\n    ' if result else '    ') + _("Version: {}").format( version )
                date = self._XMLSystems[x]["date"]
                if date: result += ('\n    ' if result else '    ') + _("Last updated: {}").format( date )
                result += ('\n    ' if result else '    ') + _("Number of values = {}").format( len(self._XMLSystems[x]["tree"]) )
        return result
    # end of __str__

    def __len__( self ):
        """ Returns the number of systems loaded. """
        return len( self._XMLSystems )
    # end of __len__

    def importDataToPython( self ):
        """
        Loads (and pivots) the data (not including the header) into suitable Python containers to use in a Python program.
        """
        assert( self._XMLSystems )
        if self._DataDict: # We've already done an import/restructuring -- no need to repeat it
            return self._DataDict

        # We'll create a dictionary of dictionaries
        for punctuationSystemCode in self._XMLSystems.keys():
            # Make the data dictionary for this punctuation system
            punctuationDict = {}
            for element in self._XMLSystems[punctuationSystemCode]["tree"]:
                tag = element.tag
                text = element.text
                if text is None: text = '' # If a tag was given, but contained an empty string, indicate that 
                if tag in punctuationDict: logging.error( _("Multiple {} entries in {} punctuation system").format( tag, punctuationSystemCode ) )
                punctuationDict[tag] = text

            if Globals.strictCheckingFlag: # check for duplicates
                for checkSystemCode,checkSystemDataDict in self._DataDict.items():
                    if checkSystemDataDict == punctuationDict:
                        logging.error( _("{} and {} punctuation systems are identical").format( punctuationSystemCode, checkSystemCode ) )
                    elif Globals.verbosityLevel>2: # check for very similar systems
                        differenceCount, firstTag, description = 0, '', ''
                        for tag in punctuationDict:
                            if tag not in checkSystemDataDict:
                                differenceCount += 1
                                if not firstTag: firstTag = tag
                            elif punctuationDict[tag] != checkSystemDataDict[tag]:
                                differenceCount += 1
                                if not firstTag:
                                    firstTag = tag
                                    description = _(" (-->{}<-- versus -->{}<--)".format( punctuationDict[tag], checkSystemDataDict[tag] ) )
                        if differenceCount==1: 
                            logging.warning( _("{} and {} punctuation systems differ only by {}{}").format( punctuationSystemCode, checkSystemCode, firstTag, description ) )

            # Now put it into my dictionaries for easy access
            self._DataDict[punctuationSystemCode] = punctuationDict

        return self._DataDict
    # end of importDataToPython

    def pickle( self, filepath=None ):
        """
        Writes the information tables to a .pickle file that can be easily loaded into a Python3 program.
        """
        import pickle

        assert( self._XMLSystems )
        self.importDataToPython()
        assert( self._DataDict )

        if not filepath:
            folder = os.path.join( self.__XMLFolder, "../", "DerivedFiles/" )
            if not os.path.exists( folder ): os.mkdir( folder )
            filepath = os.path.join( folder, self.__filenameBase + "_Tables.pickle" )
        if Globals.verbosityLevel > 1: print( _("Exporting to {}...").format( filepath ) )
        with open( filepath, 'wb' ) as myFile:
            pickle.dump( self._DataDict, myFile )
    # end of pickle

    def exportDataToPython( self, filepath=None ):
        """
        Writes the information tables to a .py file that can be cut and pasted into a Python program.
        """
        def exportPythonDict( theFile, theDict, dictName, keyComment, fieldsComment ):
            """Exports theDict to theFile."""
            theFile.write( '  "{}": {{\n    # Key is {}\n    # Fields are: {}\n'.format( dictName, keyComment, fieldsComment ) )
            for dictKey in theDict.keys():
                theFile.write( '    {}: {},\n'.format( repr(dictKey), repr(theDict[dictKey]) ) )
            theFile.write( "  }}, # end of {} ({} entries)\n\n".format( dictName, len(theDict) ) )
        # end of exportPythonDict

        from datetime import datetime

        assert( self._XMLSystems )
        self.importDataToPython()
        assert( self._DataDict )

        if not filepath: filepath = os.path.join( self.__XMLFolder, "../", "DerivedFiles", self.__filenameBase + "_Tables.py" )
        if Globals.verbosityLevel > 1: print( _("Exporting to {}...").format( filepath ) )

        with open( filepath, 'wt' ) as myFile:
            myFile.write( "# {}\n#\n".format( filepath ) )
            myFile.write( "# This UTF-8 file was automatically generated by BiblePunctuationSystems.py V{} on {}\n#\n".format( versionString, datetime.now() ) )
            #if self.title: myFile.write( "# {}\n".format( self.title ) )
            #if self.version: myFile.write( "#  Version: {}\n".format( self.version ) )
            #if self.date: myFile.write( "#  Date: {}\n#\n".format( self.date ) )
            #myFile.write( "#   {} {} entries loaded from the original XML file.\n".format( len(self.namesTree), self.treeTag ) )
            myFile.write( "#   {} {} loaded from the original XML files.\n#\n\n".format( len(self._XMLSystems), self.treeTag ) )
            myFile.write( "from collections import OrderedDict\n\n\n" )
            myFile.write( "bookDataDict = {\n  # Key is versificationSystemName\n  # Fields are omittedVersesSystem\n\n" )
            for systemName, systemDict in self._DataDict.items():
                exportPythonDict( myFile, systemDict, systemName, "referenceAbbreviation", "id" )
            myFile.write( "}} # end of bookDataDict ({} systems)\n\n\n\n".format( len(self._DataDict) ) )
            myFile.write( "# end of {}".format(os.path.basename(filepath)) )
    # end of exportDataToPython

    def exportDataToJSON( self, filepath=None ):
        """
        Writes the information tables to a .json file that can be easily loaded into a Java program.

        See http://en.wikipedia.org/wiki/JSON.
        """
        from datetime import datetime
        import json

        assert( self._XMLSystems )
        self.importDataToPython()
        assert( self._DataDict )

        if not filepath: filepath = os.path.join( self.__XMLFolder, "../", "DerivedFiles", self.__filenameBase + "_Tables.json" )
        if Globals.verbosityLevel > 1: print( _("Exporting to {}...").format( filepath ) )
        with open( filepath, 'wt' ) as myFile:
            json.dump( self._DataDict, myFile, indent=2 )
    # end of exportDataToJSON

    def exportDataToC( self, filepath=None ):
        """
        Writes the information tables to a .h file that can be included in c and c++ programs.
        """
        def writeStructure( hFile, structName, structure ):
            """ Writes a typedef to the .h file. """
            hFile.write( "typedef struct {}EntryStruct {{\n".format(structName) )
            for declaration in structure.split(';'):
                adjDeclaration = declaration.strip()
                if adjDeclaration: hFile.write( "    {};\n".format(adjDeclaration) )
            hFile.write( "}} {}Entry;\n\n".format(structName) )
        # end of writeStructure

        def exportPythonDict( cFile, theDict, dictName, structName, sortedBy, structure ):
            """ Exports theDict to the .h and .c files. """
            def convertEntry( entry ):
                """ Convert special characters in an entry... """
                result = ""
                if isinstance( entry, int ): result += str(entry)
                elif isinstance( entry, str): result += '"' + str(entry).replace('"','\\"') + '"'
                else:
                    for field in entry:
                        if result: result += ", " # Separate the fields
                        if field is None: result += '""'
                        elif isinstance( field, str): result += '"' + str(field).replace('"','\\"') + '"'
                        elif isinstance( field, int): result += str(field)
                        else: logging.error( _("Cannot convert unknown field type '{}' in entry '{}'").format( field, entry ) )
                return result
            # end of convertEntry

            #for dictKey in theDict.keys(): # Have to iterate this :(
            #    fieldsCount = len( theDict[dictKey] ) + 1 # Add one since we include the key in the count
            #    break # We only check the first (random) entry we get
            fieldsCount = 2

            cFile.write( "const static {}\n {}[{}] = {{\n  // Fields ({}) are {}\n  // Sorted by {}\n".format( structName, dictName, len(theDict), fieldsCount, structure, sortedBy ) )
            for dictKey in sorted(theDict.keys()):
                if isinstance( dictKey, str ):
                    cFile.write( "  {{\"{}\", {}}},\n".format( dictKey, convertEntry(theDict[dictKey]) ) )
                elif isinstance( dictKey, int ):
                    cFile.write( "  {{{}, {}}},\n".format( dictKey, convertEntry(theDict[dictKey]) ) )
                else:
                    logging.error( _("Can't handle this type of data yet: {}").format( dictKey ) )
            cFile.write( "}}; // {} ({} entries)\n\n".format( dictName, len(theDict) ) )
        # end of exportPythonDict

        from datetime import datetime

        assert( self._XMLSystems )
        self.importDataToPython()
        assert( self._DataDict )

        if not filepath: filepath = os.path.join( self.__XMLFolder, "../", "DerivedFiles", self.__filenameBase + "_Tables" )
        hFilepath = filepath + '.h'
        cFilepath = filepath + '.c'
        if Globals.verbosityLevel > 1: print( _("Exporting to {}...").format( cFilepath ) ) # Don't bother telling them about the .h file
        ifdefName = self.__filenameBase.upper() + "_Tables_h"

        with open( hFilepath, 'wt' ) as myHFile, open( cFilepath, 'wt' ) as myCFile:
            myHFile.write( "// {}\n//\n".format( hFilepath ) )
            myCFile.write( "// {}\n//\n".format( cFilepath ) )
            lines = "// This UTF-8 file was automatically generated by BiblePunctuationSystems.py V{} on {}\n//\n".format( versionString, datetime.now() )
            myHFile.write( lines ); myCFile.write( lines )
            myCFile.write( "//   {} {} loaded from the original XML file.\n//\n\n".format( len(self._XMLSystems), self.treeTag ) )
            myHFile.write( "\n#ifndef {}\n#define {}\n\n".format( ifdefName, ifdefName ) )
            myCFile.write( '#include "{}"\n\n'.format(os.path.basename(hFilepath)) )

            CHAR = "const unsigned char"
            BYTE = "const int"
            N1 = "punctuationByRef"
            N2 = "punctuationByIndex"
            S1 = "{} referenceAbbreviation[3+1]; {} indexNumber;".format(CHAR,BYTE)
            S2 = "{} indexNumber; {} referenceAbbreviation[3+1];".format(BYTE,CHAR)
            writeStructure( myHFile, N1, S1 )
            writeStructure( myHFile, N2, S2 )
            writeStructure( myHFile, "table", "{}* systemName; {}Entry* byReference; {}Entry* byBook;".format(CHAR,N1,N2) ) # I'm not sure if I need one or two asterisks on those last two
                                                                                                        # They're supposed to be pointers to an array of structures
            myHFile.write( "#endif // {}\n\n".format( ifdefName ) )
            myHFile.write( "// end of {}".format(os.path.basename(hFilepath)) )

            for systemName, systemDict in self._DataDict.items(): # Now write out the actual data into the .c file
                myCFile.write( "\n// {}\n".format( systemName ) )
                exportPythonDict( myCFile, systemDict, systemName+"BookDataDict", N1+"Entry", "referenceAbbreviation", S1 )

            # Write out the final table of pointers to the above information
            myCFile.write( "\n// Pointers to above data\nconst static tableEntry punctuationSystemTable[{}] = {{\n".format(len(self._DataDict)) )
            for systemName in self._DataDict: # Now write out the actual pointer data into the .c file
                myCFile.write( '  {{ "{}", {}, {} }},\n'.format( systemName, systemName+"BookDataDict", systemName+"IndexNumberDataDict" ) )
            myCFile.write( "}}; // {} entries\n\n".format(len(self._DataDict)) )
            myCFile.write( "// end of {}".format(os.path.basename(cFilepath)) )
    # end of exportDataToC

    def checkPunctuationSystem( self, systemName, punctuationSchemeToCheck, exportFlag=False, debugFlag=False ):
        """
        Check the given punctuation scheme against all the loaded systems.
        Create a new punctuation file if it doesn't match any.
        """
        assert( systemName )
        assert( punctuationSchemeToCheck )
        assert( self.Lists )
        #print( systemName, punctuationSchemeToCheck )

        matchedPunctuationSystemCodes = []
        systemMatchCount, systemMismatchCount, allErrors, errorSummary = 0, 0, '', ''
        for punctuationSystemCode in self.Lists: # Step through the various reference schemes
            theseErrors = ''
            if self.Lists[punctuationSystemCode] == punctuationSchemeToCheck:
                #print( "  Matches '{}' punctuation system".format( punctuationSystemCode ) )
                systemMatchCount += 1
                matchedPunctuationSystemCodes.append( punctuationSystemCode )
            else:
                if len(self.Lists[punctuationSystemCode]) == len(punctuationSchemeToCheck):
                    for BBB1,BBB2 in zip(self.Lists[punctuationSystemCode],punctuationSchemeToCheck):
                        if BBB1 != BBB2: break
                    thisError = "    Doesn't match '{}' system (Both have {} books, but {} instead of {})".format( punctuationSystemCode, len(punctuationSchemeToCheck), BBB1, BBB2 )
                else:
                    thisError = "    Doesn't match '{}' system ({} books instead of {})".format( punctuationSystemCode, len(punctuationSchemeToCheck), len(self.Lists[punctuationSystemCode]) )
                theseErrors += ("\n" if theseErrors else "") + thisError
                errorSummary += ("\n" if errorSummary else "") + thisError
                systemMismatchCount += 1

        if systemMatchCount:
            if systemMatchCount == 1: # What we hope for
                print( "  Matched {} punctuation (with these {} books)".format( matchedPunctuationSystemCodes[0], len(punctuationSchemeToCheck) ) )
                if debugFlag: print( errorSummary )
            else:
                print( "  Matched {} punctuation system(s): {} (with these {} books)".format( systemMatchCount, matchedPunctuationSystemCodes, len(punctuationSchemeToCheck) ) )
                if debugFlag: print( errorSummary )
        else:
            print( "  Mismatched {} punctuation systems (with these {} books)".format( systemMismatchCount, len(punctuationSchemeToCheck) ) )
            if debugFlag: print( allErrors )
            else: print( errorSummary)

        if exportFlag and not systemMatchCount: # Write a new file
            outputFilepath = os.path.join( "ScrapedFiles", "BiblePunctuation_"+systemName + ".xml" )
            if Globals.verbosityLevel > 1: print( _("Writing {} books to {}...").format( len(punctuationSchemeToCheck), outputFilepath ) )
            with open( outputFilepath, 'wt' ) as myFile:
                for n,BBB in enumerate(punctuationSchemeToCheck):
                    myFile.write( '  <book id="{}">{}</book>\n'.format( n+1,BBB ) )
                myFile.write( "</BiblePunctuationSystem>" )
    # end of checkPunctuationSystem
# end of BiblePunctuationSystemsConverter class


def main():
    """
    Main program to handle command line parameters and then run what they want.
    """
    # Handle command line parameters
    from optparse import OptionParser
    parser = OptionParser( version="v{}".format( versionString ) )
    parser.add_option("-e", "--export", action="store_true", dest="export", default=False, help="export the XML files to .py and .h tables suitable for directly including into other programs")
    Globals.addStandardOptionsAndProcess( parser )

    if Globals.verbosityLevel > 0: print( "{} V{}".format( progName, versionString ) )

    if Globals.commandLineOptions.export:
        bpsc = BiblePunctuationSystemsConverter().loadSystems() # Load the XML
        bpsc.pickle() # Produce the .pickle file
        bpsc.exportDataToPython() # Produce the .py tables
        bpsc.exportDataToJSON() # Produce a json output file
        bpsc.exportDataToC() # Produce the .h and .c tables

    else: # Must be demo mode
        # Demo the converter object
        bpsc = BiblePunctuationSystemsConverter().loadSystems() # Load the XML
        print( bpsc ) # Just print a summary
# end of main

if __name__ == '__main__':
    main()
# end of BiblePunctuationSystemsConverter.py
