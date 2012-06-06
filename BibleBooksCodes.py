#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# BibleBooksCodes.py
#   Last modified: 2012-06-06 (also update versionString below)
#
# Module handling BibleBooksCodes functions
#
# Copyright (C) 2010-2012 Robert Hunt
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
Module handling BibleBooksCodes functions.
"""

progName = "Bible Books Codes handler"
versionString = "0.61"


import os, logging
from gettext import gettext as _
from collections import OrderedDict

from singleton import singleton
import Globals


@singleton # Can only ever have one instance
class BibleBooksCodes:
    """
    Class for handling BibleBooksCodes.

    This class doesn't deal at all with XML, only with Python dictionaries, etc.

    Note: BBB is used in this class to represent the three-character referenceAbbreviation.
    """

    def __init__( self ): # We can't give this parameters because of the singleton
        """
        Constructor: 
        """
        self.__DataDicts = None # We'll import into this in loadData
    # end of __init__

    def loadData( self, XMLFilepath=None ):
        """ Loads the pickle or XML data file and imports it to dictionary format (if not done already). """
        if not self.__DataDicts: # We need to load them once -- don't do this unnecessarily
            # See if we can load from the pickle file (faster than loading from the XML)
            dataFilepath = os.path.join( os.path.dirname(__file__), "DataFiles" )
            standardXMLFilepath = os.path.join( dataFilepath, "BibleBooksCodes.xml" )
            standardPickleFilepath = os.path.join( dataFilepath, "DerivedFiles", "BibleBooksCodes_Tables.pickle" )
            if XMLFilepath is None \
            and os.access( standardPickleFilepath, os.R_OK ) \
            and os.stat(standardPickleFilepath)[8] > os.stat(standardXMLFilepath)[8] \
            and os.stat(standardPickleFilepath)[9] > os.stat(standardXMLFilepath)[9]: # There's a newer pickle file
                import pickle
                if Globals.verbosityLevel > 2: print( "Loading pickle file {}...".format( standardPickleFilepath ) )
                with open( standardPickleFilepath, 'rb') as pickleFile:
                    self.__DataDicts = pickle.load( pickleFile ) # The protocol version used is detected automatically, so we do not have to specify it
            else: # We have to load the XML (much slower)
                from BibleBooksCodesConverter import BibleBooksCodesConverter
                if XMLFilepath is not None: logging.warning( _("Bible books codes are already loaded -- your given filepath of '{}' was ignored").format(XMLFilepath) )
                bbcc = BibleBooksCodesConverter()
                bbcc.loadAndValidate( XMLFilepath ) # Load the XML (if not done already)
                self.__DataDicts = bbcc.importDataToPython() # Get the various dictionaries organised for quick lookup
        return self
    # end of loadData

    def __str__( self ):
        """
        This method returns the string representation of a Bible book code.
        
        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        indent = 2
        result = "BibleBooksCodes object"
        result += ('\n' if result else '') + ' '*indent + _("Number of entries = {}").format( len(self.__DataDicts["referenceAbbreviationDict"]) )
        return result
    # end of __str__

    def __len__( self ):
        """ Return the number of available codes. """
        assert( len(self.__DataDicts["referenceAbbreviationDict"]) == len(self.__DataDicts["referenceNumberDict"]) ) 
        return len(self.__DataDicts["referenceAbbreviationDict"])

    def __contains__( self, BBB ):
        """ Returns True or False. """
        return BBB in self.__DataDicts["referenceAbbreviationDict"]

    def isValidReferenceAbbreviation( self, BBB ):
        """ Returns True or False. """
        return BBB in self.__DataDicts["referenceAbbreviationDict"]

    def getBBBFromReferenceNumber( self, referenceNumber ):
        """ Return the referenceAbbreviation for the given book number (referenceNumber). """
        if not 1 <= referenceNumber <= 255: raise ValueError
        return self.__DataDicts["referenceNumberDict"][referenceNumber]["referenceAbbreviation"]

    def getAllReferenceAbbreviations( self ):
        """ Returns a list of all possible BBB codes. """
        return [BBB for BBB in self.__DataDicts["referenceAbbreviationDict"]]
        #return self.__DataDicts["referenceAbbreviationDict"].keys() # Why didn't this work?

    def getReferenceNumber( self, BBB ):
        """ Return the referenceNumber 1..255 for the given book code (referenceAbbreviation). """
        return self.__DataDicts["referenceAbbreviationDict"][BBB]["referenceNumber"]

    def getCCELNumber( self, BBB ):
        """ Return the CCEL number string for the given book code (referenceAbbreviation). """
        return self.__DataDicts["referenceAbbreviationDict"][BBB]["CCELNumberString"]

    def getSBLAbbreviation( self, BBB ):
        """ Return the SBL abbreviation string for the given book code (referenceAbbreviation). """
        return self.__DataDicts["referenceAbbreviationDict"][BBB]["SBLAbbreviation"]

    def getOSISAbbreviation( self, BBB ):
        """ Return the OSIS abbreviation string for the given book code (referenceAbbreviation). """
        return self.__DataDicts["referenceAbbreviationDict"][BBB]["OSISAbbreviation"]

    def getSwordAbbreviation( self, BBB ):
        """ Return the Sword abbreviation string for the given book code (referenceAbbreviation). """
        return self.__DataDicts["referenceAbbreviationDict"][BBB]["SwordAbbreviation"]

    def getUSFMAbbreviation( self, BBB ):
        """ Return the USFM abbreviation string for the given book code (referenceAbbreviation). """
        return self.__DataDicts["referenceAbbreviationDict"][BBB]["USFMAbbreviation"]

    def getUSFMNumber( self, BBB ):
        """ Return the two-digit USFM number string for the given book code (referenceAbbreviation). """
        return self.__DataDicts["referenceAbbreviationDict"][BBB]["USFMNumberString"]

    def getUSXNumber( self, BBB ):
        """ Return the three-digit USX number string for the given book code (referenceAbbreviation). """
        return self.__DataDicts["referenceAbbreviationDict"][BBB]["USXNumberString"]

    def getNETBibleAbbreviation( self, BBB ):
        """ Return the NET Bible abbreviation string for the given book code (referenceAbbreviation). """
        return self.__DataDicts["referenceAbbreviationDict"][BBB]["NETBibleAbbreviation"]

    def getByzantineAbbreviation( self, BBB ):
        """ Return the Byzantine abbreviation string for the given book code (referenceAbbreviation). """
        return self.__DataDicts["referenceAbbreviationDict"][BBB]["ByzantineAbbreviation"]

    def getBBBFromOSIS( self, osisAbbreviation ):
        """ Return the reference abbreviation string for the given OSIS book code string. """
        return self.__DataDicts["OSISAbbreviationDict"][osisAbbreviation.upper()][1]

    def getBBBFromUSFM( self, USFMAbbreviation ):
        """ Return the reference abbreviation string for the given USFM book code string. """
        assert( len(USFMAbbreviation) == 3 )
        return self.__DataDicts["USFMAbbreviationDict"][USFMAbbreviation.upper()][1]

    def getBBB( self, something ):
        """ Attempt to return the BBB reference abbreviation string for the given book information.
            Returns BBB or None. """
        assert( something )
        UCSomething = something.upper()
        if UCSomething in self.__DataDicts["referenceAbbreviationDict"]: return UCSomething # it's already a BBB code
        #if something.isdigit() and 1 <= int(something) <= 255: return self.__DataDicts["referenceNumberDict"][int(something)]["referenceAbbreviation"]
        if UCSomething in self.__DataDicts["allAbbreviationsDict"]: return self.__DataDicts["allAbbreviationsDict"][UCSomething]
    # end of getBBB

    def getExpectedChaptersList( self, BBB ):
        """
        Gets a list with the number of expected chapters for the given book code (referenceAbbreviation).
        The number(s) of expected chapters is left in string form (not int).

        Why is it a list?
            Because some books have alternate possible numbers of chapters depending on the Biblical tradition.
        """
        #if BBB not in self.__DataDicts["referenceAbbreviationDict"] \
        #or "numExpectedChapters" not in self.__DataDicts["referenceAbbreviationDict"][BBB] \
        #or self.__DataDicts["referenceAbbreviationDict"][BBB]["numExpectedChapters"] is None:
        if "numExpectedChapters" not in self.__DataDicts["referenceAbbreviationDict"][BBB] \
        or self.__DataDicts["referenceAbbreviationDict"][BBB]["numExpectedChapters"] is None:
            return []

        eC = self.__DataDicts["referenceAbbreviationDict"][BBB]["numExpectedChapters"]
        if eC: return [v for v in eC.split(',')]
    # end of getExpectedChaptersList

    def getSingleChapterBooksList( self ):
        """ Gets a list of single chapter book codes. """
        results = []
        for BBB in self.__DataDicts["referenceAbbreviationDict"]:
            if self.__DataDicts["referenceAbbreviationDict"][BBB]["numExpectedChapters"] is not None \
            and self.__DataDicts["referenceAbbreviationDict"][BBB]["numExpectedChapters"] == '1':
                results.append( BBB )
        return results
    # end of getSingleChapterBooksList

    def getOSISSingleChapterBooksList( self ):
        """ Gets a list of OSIS single chapter book abbreviations. """
        results = []
        for BBB in self.getSingleChapterBooksList():
            osisAbbrev = self.getOSISAbbreviation(BBB)
            if osisAbbrev is not None: results.append( osisAbbrev )
        return results
    # end of getOSISSingleChapterBooksList

    def getAllOSISBooksCodes( self ):
        """
        Return a list of all available OSIS book codes (in no particular order).
        """
        return [bk for bk in self.__DataDicts["OSISAbbreviationDict"]]
    #end of getAllOSISBooksCodes

    def getAllUSFMBooksCodes( self, toUpper=False ):
        """
        Return a list of all available USFM book codes.
        """
        result = []
        for BBB, values in self.__DataDicts["referenceAbbreviationDict"].items():
            pA = values["USFMAbbreviation"]
            if pA is not None and pA not in result: # Don't want duplicates (where more than one book maps to a single USFMAbbreviation)
                result.append( pA.upper() if toUpper else pA )
        return result
    # end of getAllUSFMBooksCodes

    def getAllUSFMBooksCodeNumberTriples( self ):
        """
        Return a list of all available USFM book codes.

        The list contains tuples of: USFMAbbreviation, USFMNumber, referenceAbbreviation
        """
        found, result = [], []
        for BBB, values in self.__DataDicts["referenceAbbreviationDict"].items():
            pA = values["USFMAbbreviation"]
            pN = values["USFMNumberString"]
            if pA is not None and pN is not None:
                if pA not in found: # Don't want duplicates (where more than one book maps to a single USFMAbbreviation)
                    result.append( (pA, pN, BBB,) )
                    found.append( pA )
        return result
    # end of getAllUSFMBooksCodeNumberTriples

    def getAllUSXBooksCodeNumberTriples( self ):
        """
        Return a list of all available USX book codes.

        The list contains tuples of: USFMAbbreviation, USXNumber, referenceAbbreviation
        """
        found, result = [], []
        for BBB, values in self.__DataDicts["referenceAbbreviationDict"].items():
            pA = values["USFMAbbreviation"]
            pN = values["USXNumberString"]
            if pA is not None and pN is not None:
                if pA not in found: # Don't want duplicates (where more than one book maps to a single USFMAbbreviation)
                    result.append( (pA, pN, BBB,) )
                    found.append( pA )
        return result
    # end of getAllUSXBooksCodeNumberTriples

    # NOTE: The following functions are all not recommended (NR) because they rely on assumed information that may be incorrect
    #           i.e., they assume English language or European book order conventions
    #       They are included because they might be necessary for error messages or similar uses
    #           (where the correct information is unknown)
    def getEnglishName_NR( self, BBB ): # NR = not recommended
        """
        Returns the first English name for a book.

        Remember: These names are only intended as comments or for some basic module processing.
            They are not intended to be used for a proper international human interface.
            The first one in the list is supposed to be the more common.
        """
        return self.__DataDicts["referenceAbbreviationDict"][BBB]["nameEnglish"].split('/',1)[0].strip()
    # end of getEnglishName_NR

    def getEnglishNameList_NR( self, BBB ): # NR = not recommended
        """
        Returns a list of possible English names for a book.

        Remember: These names are only intended as comments or for some basic module processing.
            They are not intended to be used for a proper international human interface.
            The first one in the list is supposed to be the more common.
        """
        names = self.__DataDicts["referenceAbbreviationDict"][BBB]["nameEnglish"]
        return [name.strip() for name in names.split('/')]
    # end of getEnglishNameList_NR

    def isOldTestament_NR( self, BBB ): # NR = not recommended
        """ Returns True if the given referenceAbbreviation indicates a European Protestant Old Testament book.
            NOTE: This is not truly international so it's not a recommended function. """
        return 1 <= self.getReferenceNumber(BBB) <= 39
    # end of isOldTestament_NR

    def isNewTestament_NR( self, BBB ): # NR = not recommended
        """ Returns True if the given referenceAbbreviation indicates a European Protestant New Testament book.
            NOTE: This is not truly international so it's not a recommended function. """
        return 40 <= self.getReferenceNumber(BBB) <= 66
    # end of isNewTestament_NR
# end of BibleBooksCodes class


def main():
    """
    Main program to handle command line parameters and then run what they want.
    """
    # Handle command line parameters
    from optparse import OptionParser
    parser = OptionParser( version="v{}".format( versionString ) )
    #parser.add_option("-e", "--export", action="store_true", dest="export", default=False, help="export the XML file to .py and .h/.c formats suitable for directly including into other programs, as well as .json.")
    Globals.addStandardOptionsAndProcess( parser )

    if Globals.verbosityLevel > 1: print( "{} V{}".format( progName, versionString ) )

    # Demo the BibleBooksCodes object
    bbc = BibleBooksCodes().loadData() # Doesn't reload the XML unnecessarily :)
    print( bbc ) # Just print a summary
    print( "Esther has {} expected chapters".format(bbc.getExpectedChaptersList("EST")) )
    print( "Apocalypse of Ezra has {} expected chapters".format(bbc.getExpectedChaptersList("EZA")) )
    print( "Names for Genesis are:", bbc.getEnglishNameList_NR("GEN") )
    print( "Names for Sirach are:", bbc.getEnglishNameList_NR('SIR') )
    print( "All BBBs:", len(bbc.getAllReferenceAbbreviations()), bbc.getAllReferenceAbbreviations() )
    print( "USFM triples:", len(bbc.getAllUSFMBooksCodeNumberTriples()), bbc.getAllUSFMBooksCodeNumberTriples() )
    print( "USX triples:", len(bbc.getAllUSXBooksCodeNumberTriples()), bbc.getAllUSXBooksCodeNumberTriples() )
    print( "Single chapter books (and OSIS):\n  {}\n  {}".format(bbc.getSingleChapterBooksList(), bbc.getOSISSingleChapterBooksList()) )
    for something in ('PE2', '2Pe', '2 Pet', '2Pet', 'Job', ):
        print( something, bbc.getBBB( something ) )
# end of main

if __name__ == '__main__':
    main()
# end of BibleBooksCodes.py
