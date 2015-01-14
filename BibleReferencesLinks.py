#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# BibleReferencesLinks.py
#
# Module handling BibleReferencesLinks functions
#
# Copyright (C) 2015 Robert Hunt
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
Module handling BibleReferencesLinks functions.
"""

from gettext import gettext as _

LastModifiedDate = '2015-01-13' # by RJH
ShortProgName = "BibleReferencesLinks"
ProgName = "Bible References Links handler"
ProgVersion = '0.20'
ProgNameVersion = '{} v{}'.format( ProgName, ProgVersion )
ProgNameVersionDate = '{} {} {}'.format( ProgNameVersion, _("last modified"), LastModifiedDate )

debuggingThisModule = False


import os, logging
from collections import OrderedDict

from singleton import singleton
import BibleOrgSysGlobals


def t( messageString ):
    """
    Prepends the module name to a error or warning message string if we are in debug mode.
    Returns the new string.
    """
    try: nameBit, errorBit = messageString.split( ': ', 1 )
    except ValueError: nameBit, errorBit = '', messageString
    if BibleOrgSysGlobals.debugFlag or debuggingThisModule:
        nameBit = '{}{}{}'.format( ShortProgName, '.' if nameBit else '', nameBit )
    return '{}: {}'.format( nameBit, _(errorBit) )
# end of t



@singleton # Can only ever have one instance
class BibleReferencesLinks:
    """
    Class for handling BibleReferencesLinks.

    This class doesn't deal at all with XML, only with Python dictionaries, etc.

    Note: BBB is used in this class to represent the three-character referenceAbbreviation.
    """

    def __init__( self ): # We can't give this parameters because of the singleton
        """
        Constructor:
        """
        self.__DataList = None # We'll import into this in loadData
    # end of BibleReferencesLinks.__init__


    def loadData( self, XMLFilepath=None ):
        """ Loads the pickle or XML data file and imports it to dictionary format (if not done already). """
        if not self.__DataList: # We need to load them once -- don't do this unnecessarily
            # See if we can load from the pickle file (faster than loading from the XML)
            dataFilepath = os.path.join( os.path.dirname(__file__), "DataFiles" )
            standardXMLFilepath = os.path.join( dataFilepath, "BibleReferencesLinks.xml" )
            standardPickleFilepath = os.path.join( dataFilepath, "DerivedFiles", "BibleReferencesLinks_Tables.pickle" )
            if XMLFilepath is None \
            and os.access( standardPickleFilepath, os.R_OK ) \
            and os.stat(standardPickleFilepath)[8] > os.stat(standardXMLFilepath)[8] \
            and os.stat(standardPickleFilepath)[9] > os.stat(standardXMLFilepath)[9]: # There's a newer pickle file
                import pickle
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "Loading pickle file {}...".format( standardPickleFilepath ) )
                with open( standardPickleFilepath, 'rb') as pickleFile:
                    self.__DataList = pickle.load( pickleFile ) # The protocol version used is detected automatically, so we do not have to specify it
            else: # We have to load the XML (much slower)
                from BibleReferencesLinksConverter import BibleReferencesLinksConverter
                if XMLFilepath is not None: logging.warning( _("Bible books codes are already loaded -- your given filepath of {!r} was ignored").format(XMLFilepath) )
                bbcc = BibleReferencesLinksConverter()
                bbcc.loadAndValidate( XMLFilepath ) # Load the XML (if not done already)
                self.__DataList = bbcc.importDataToPython() # Get the various dictionaries organised for quick lookup
        return self # So this command can be chained after the object creation
    # end of BibleReferencesLinks.loadData


    def __str__( self ):
        """
        This method returns the string representation of a Bible book code.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        indent = 2
        result = "BibleReferencesLinks object"
        result += ('\n' if result else '') + ' '*indent + _("Number of entries = {}").format( len(self.__DataList) )
        return result
    # end of BibleReferencesLinks.__str__


    def __len__( self ):
        """ Return the number of available codes. """
        assert( len(self.__DataList["referenceAbbreviationDict"]) == len(self.__DataList["referenceNumberDict"]) )
        return len(self.__DataList["referenceAbbreviationDict"])


    def __contains__( self, BBB ):
        """ Returns True or False. """
        return BBB in self.__DataList["referenceAbbreviationDict"]


    def __iter__( self ):
        """ Yields the next BBB. """
        for BBB in self.__DataList["referenceAbbreviationDict"]:
            yield BBB


# end of BibleReferencesLinks class



def demo():
    """
    Main program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel > 1: print( ProgNameVersion )

    # Demo the BibleReferencesLinks object
    bbc = BibleReferencesLinks().loadData() # Doesn't reload the XML unnecessarily :)
    print( bbc ) # Just print a summary
# end of demo


if __name__ == '__main__':
    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( ProgName, ProgVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    demo()

    BibleOrgSysGlobals.closedown( ProgName, ProgVersion )
# end of BibleReferencesLinks.py