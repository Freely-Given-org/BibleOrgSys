#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# BiblePunctuationSystems.py
#
# Module handling BiblePunctuationSystem_*.xml to produce C and Python data tables
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
Module handling BiblePunctuation_*.xml and to export to JSON, C, and Python data tables.
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2019-12-23' # by RJH
SHORT_PROGRAM_NAME = "BiblePunctuationSystems"
PROGRAM_NAME = "Bible Punctuation Systems handler"
PROGRAM_VERSION = '0.44'
programNameVersion = f'{PROGRAM_NAME} v{PROGRAM_VERSION}'
programNameVersionDate = f'{programNameVersion} {_("last modified")} {LAST_MODIFIED_DATE}'


import os
import logging

if __name__ == '__main__':
    import sys
#from BibleOrgSys.Misc.singleton import singleton
from BibleOrgSys import BibleOrgSysGlobals


#@singleton # Can only ever have one instance
class BiblePunctuationSystems:
    """
    Class for handling Bible punctuation systems.

    This class doesn't deal at all with XML, only with Python dictionaries, etc.
    """

    def __init__( self ): # We can't give this parameters because of the singleton
        """
        Constructor:
        """
        self.__DataDict = None # We'll import into this in loadData
    # end of __init__

    def loadData( self, XMLFolder=None ):
        """ Loads the XML data file and imports it to dictionary format (if not done already). """
        if not self.__DataDict: # Don't do this unnecessarily
            # See if we can load from the pickle file (faster than loading from the XML)
            picklesGood = False
            standardPickleFilepath = BibleOrgSysGlobals.BOS_DATA_FILES_FOLDERPATH.joinpath( 'DerivedFiles/', "BiblePunctuationSystems_Tables.pickle" )
            if XMLFolder is None and os.access( standardPickleFilepath, os.R_OK ):
                standardXMLFolder = BibleOrgSysGlobals.BOS_DATA_FILES_FOLDERPATH.joinpath( 'PunctuationSystems/' )
                pickle8, pickle9 = os.stat(standardPickleFilepath)[8:10]
                picklesGood = True
                for filename in os.listdir( standardXMLFolder ):
                    filepart, extension = os.path.splitext( filename )
                    XMLFileOrFilepath = os.path.join( standardXMLFolder, filename )
                    if extension.upper() == '.XML' and filepart.upper().startswith("BIBLEPUNCTUATIONSYSTEM_"):
                        if pickle8 <= os.stat( XMLFileOrFilepath ).st_mtime \
                        or pickle9 <= os.stat( XMLFileOrFilepath ).st_ctime: # The pickle file is older
                            picklesGood = False; break
            if picklesGood:
                import pickle
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "Loading pickle file {}…".format( standardPickleFilepath ) )
                with open( standardPickleFilepath, 'rb') as pickleFile:
                    self.__DataDict = pickle.load( pickleFile ) # The protocol version used is detected automatically, so we do not have to specify it
            else: # We have to load the XML (much slower)
                from BibleOrgSys.Reference.Converters.BiblePunctuationSystemsConverter import BiblePunctuationSystemsConverter
                if XMLFolder is not None: logging.warning( _("Bible punctuation systems are already loaded -- your given folder of {!r} was ignored").format(XMLFolder) )
                bpsc = BiblePunctuationSystemsConverter()
                bpsc.loadSystems( XMLFolder ) # Load the XML (if not done already)
                self.__DataDict = bpsc.importDataToPython() # Get the various dictionaries organised for quick lookup
        return self
    # end of loadData

    def __str__( self ):
        """
        This method returns the string representation of a Bible punctuation.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        assert self.__DataDict
        result = "BiblePunctuationSystems object"
        result += ('\n  ' if result else '  ') + _("Number of systems = {}").format( len(self.__DataDict) )
        return result
    # end of __str__

    def __len__( self ):
        """ Returns the number of systems loaded. """
        return len( self.__DataDict )
    # end of __len__

    def __contains__( self, name ):
        """ Returns True/False if the name is in this system. """
        return name in self.__DataDict
    # end of __contains__

    def getAvailablePunctuationSystemNames( self ):
        """ Returns a list of available system name strings. """
        assert self.__DataDict
        return [x for x in self.__DataDict]
    # end of getAvailablePunctuationSystemNames

    def isValidPunctuationSystemName( self, systemName ):
        """ Returns True or False. """
        assert self.__DataDict
        assert systemName
        return systemName in self.__DataDict
    # end of isValidPunctuationSystemName

    def getPunctuationSystem( self, systemName ):
        """ Returns the corresponding dictionary."""
        assert self.__DataDict
        assert systemName
        if systemName in self.__DataDict:
            return self.__DataDict[systemName]
        # else
        logging.error( _("No {!r} system in Bible Punctuation Systems").format(systemName) )
        if BibleOrgSysGlobals.verbosityLevel>2: logging.error( "  " + _("Available systems are {}").format(self.getAvailablePunctuationSystemNames()) )
    # end of getPunctuationSystem

    def checkPunctuationSystem( self, systemName, punctuationSchemeToCheck, exportFlag=False, debugFlag=False ):
        """
        Check the given punctuation scheme against all the loaded systems.
        Create a new punctuation file if it doesn't match any.
        """
        assert systemName
        assert punctuationSchemeToCheck
        assert self.Lists
        #print( systemName, punctuationSchemeToCheck )

        matchedPunctuationSystemCodes = []
        systemMatchCount, systemMismatchCount, allErrors, errorSummary = 0, 0, '', ''
        for punctuationSystemCode in self.Lists: # Step through the various reference schemes
            theseErrors = ''
            if self.Lists[punctuationSystemCode] == punctuationSchemeToCheck:
                #print( "  Matches {!r} punctuation system".format( punctuationSystemCode ) )
                systemMatchCount += 1
                matchedPunctuationSystemCodes.append( punctuationSystemCode )
            else:
                if len(self.Lists[punctuationSystemCode]) == len(punctuationSchemeToCheck):
                    for BBB1,BBB2 in zip(self.Lists[punctuationSystemCode],punctuationSchemeToCheck):
                        if BBB1 != BBB2: break
                    thisError = "    Doesn't match {!r} system (Both have {} books, but {} instead of {})".format( punctuationSystemCode, len(punctuationSchemeToCheck), BBB1, BBB2 )
                else:
                    thisError = "    Doesn't match {!r} system ({} books instead of {})".format( punctuationSystemCode, len(punctuationSchemeToCheck), len(self.Lists[punctuationSystemCode]) )
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
            outputFilepath = BibleOrgSysGlobals.BOS_DATA_FILES_FOLDERPATH.joinpath( 'ScrapedFiles/', 'BiblePunctuation_'+systemName + '.xml' )
            if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Writing {} books to {}…").format( len(punctuationSchemeToCheck), outputFilepath ) )
            with open( outputFilepath, 'wt', encoding='utf-8' ) as myFile:
                for n,BBB in enumerate(punctuationSchemeToCheck):
                    myFile.write( '  <book id="{}">{}</book>\n'.format( n+1,BBB ) )
                myFile.write( "</BiblePunctuationSystem>" )
    # end of checkPunctuationSystem
# end of BiblePunctuationSystems class


class BiblePunctuationSystem:
    """
    Class for handling a particular Bible punctuation system.

    This class doesn't deal at all with XML, only with Python dictionaries, etc.
    """

    def __init__( self, systemName ):
        """
        Constructor:
        """
        assert systemName
        self.__systemName = systemName
        self.__bpss = BiblePunctuationSystems().loadData() # Doesn't reload the XML unnecessarily :)
        self.__punctuationDict = self.__bpss.getPunctuationSystem( self.__systemName )
        #print( "xxx", self.__punctuationDict )
    # end of __init__

    def __str__( self ):
        """
        This method returns the string representation of a Bible punctuation system.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = "BiblePunctuationSystem object"
        result += ('\n' if result else '') + "  " + _("{} Bible punctuation system").format( self.__systemName )
        result += ('\n' if result else '') + "  " + _("Number of values = {}").format( len(self.__punctuationDict) )
        if BibleOrgSysGlobals.verbosityLevel > 2:
            for key in self.__punctuationDict.keys(): # List the contents of the dictionary
                result += ('\n' if result else '') + "    " + _("{} is {!r}").format( key, self.__punctuationDict[key] )
        return result
    # end of __str__

    def __len__( self ):
        """ Returns the number of entries in this system. """
        return len( self.__punctuationDict )
    # end of __len__

    def __contains__( self, name ):
        """ Returns True/False if the name is in this system. """
        assert name
        return name in self.__punctuationDict
    # end of __contains__

    def getPunctuationSystemName( self ):
        """ Return the book order system name. """
        return self.__systemName
    # end of getPunctuationSystemName

    def getPunctuationDict( self ):
        """ Returns the entire punctuation dictionary. """
        return self.__punctuationDict
    # end of getPunctuationDict

    def getAvailablePunctuationValueNames( self ):
        """ Returns a list of available value name strings. """
        return [x for x in self.__punctuationDict]
    # end of getAvailablePunctuationValueNames

    def getPunctuationValue( self, name ):
        """ Returns the value for the name. """
        assert name
        return self.__punctuationDict[name]
        ##print( "yyy", self.__punctuationDict )
        #if name in self.__punctuationDict: return self.__punctuationDict[name]
        #logging.error( _("No {!r} value in {} punctuation system").format(name,self.__systemName) )
        #if BibleOrgSysGlobals.verbosityLevel > 3: logging.error( "  " + _("Available values are: {}").format(self.getAvailablePunctuationValueNames()) )
    # end of getPunctuationValue
# end of BiblePunctuationSystem class


def demo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( programNameVersion )

    # Demo the BiblePunctuationSystems object
    bpss = BiblePunctuationSystems().loadData() # Doesn't reload the XML unnecessarily :)
    print( bpss ) # Just print a summary
    print( _("Available system names are: {}").format(bpss.getAvailablePunctuationSystemNames()) )

    # Demo the BiblePunctuationSystem object
    bps = BiblePunctuationSystem( "English" ) # Doesn't reload the XML unnecessarily :)
    print( bps ) # Just print a summary
    print( "Variables are: {}".format(bps.getAvailablePunctuationValueNames()) )
    name = 'chapterVerseSeparator'
    print( "{} for {} is {!r}".format( name, bps.getPunctuationSystemName(), bps.getPunctuationValue(name) ) )
# end of demo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    demo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of BiblePunctuationSystems.py
