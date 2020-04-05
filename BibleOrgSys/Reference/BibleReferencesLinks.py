#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# BibleReferencesLinks.py
#
# Module handling BibleReferencesLinks functions
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
Module handling BibleReferencesLinks functions.
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2019-09-19' # by RJH
SHORT_PROGRAM_NAME = "BibleReferencesLinks"
PROGRAM_NAME = "Bible References Links handler"
PROGRAM_VERSION = '0.40'
programNameVersion = f'{PROGRAM_NAME} v{PROGRAM_VERSION}'
programNameVersionDate = f'{programNameVersion} {_("last modified")} {LAST_MODIFIED_DATE}'

debuggingThisModule = False


import os
import pickle

if __name__ == '__main__':
    import sys
    aboveAboveFolderPath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderPath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderPath )
from BibleOrgSys.Misc.singleton import singleton
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.Reference.VerseReferences import SimpleVerseKey




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
        self.__Index = None # We'll import into this in loadData
    # end of BibleReferencesLinks.__init__


    def loadData( self ):
        """ Loads the index file (if not done already). """
        if not self.__Index: # We need to load it once -- don't do this unnecessarily
            # See if we can load from the pickle file (faster than loading from the XML)
            standardIndexPickleFilepath = BibleOrgSysGlobals.BOS_DATA_FILES_FOLDERPATH.joinpath( 'DerivedFiles/', 'BibleReferencesLinks_Tables.index.pickle' )
            self.dataPickleFilepath = BibleOrgSysGlobals.BOS_DATA_FILES_FOLDERPATH.joinpath( 'DerivedFiles/', 'BibleReferencesLinks_Tables.data.pickle' )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "Loading pickle index file {}…".format( standardIndexPickleFilepath ) )
            with open( standardIndexPickleFilepath, 'rb') as pickleFile:
                self.__Index = pickle.load( pickleFile ) # The protocol version used is detected automatically, so we do not have to specify it
        return self # So this command can be chained after the object creation
    # end of BibleReferencesLinks.loadData


    def __str__( self ):
        """
        This method returns the string representation of this object.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        indent = 2
        result = "BibleReferencesLinks object"
        result += ('\n' if result else '') + ' '*indent + _("Number of index entries = {:,}").format( len(self.__Index) )
        return result
    # end of BibleReferencesLinks.__str__


    #def __len__( self ):
        #"""
        #Return the number of available codes.
        #"""
        #assert len(self.__DataList["referenceAbbreviationDict"]) == len(self.__DataList["referenceNumberDict"]) )
        #return len(self.__DataList["referenceAbbreviationDict"])


    #def __contains__( self, BBB ):
        #""" Returns True or False. """
        #return BBB in self.__DataList["referenceAbbreviationDict"]


    #def __iter__( self ):
        #""" Yields the next BBB. """
        #for BBB in self.__DataList["referenceAbbreviationDict"]:
            #yield BBB


    def __getEntry( self, verseKey ):
        """
        """
        filePosition, segmentLength = self.__Index[verseKey]
        with open( self.dataPickleFilepath, 'rb') as pickleFile:
            pickleFile.seek( filePosition )
            pickleEntry = pickleFile.read( segmentLength )
            #print( "pe", pickleEntry )
            entry = pickle.loads( pickleEntry )
            #print( "e", entry )
            return entry
    # end of BibleReferencesLinks.__getEntry


    def getFullRelatedPassagesList( self, verseKey ):
        """
        Given a verse key, return a list containing 4-tuples:
            0: Verse key string (same as given parameter)
            1: Key type ('Verse' or 'Verses')
            2: FlexibleVersesKey object
            3: List of links containing 4-tuples:
                0: Link verse key string
                1: Link key type ('Verse' or 'Verses')
                2: Link FlexibleVersesKey object
                3: Link type ('QuotedOTReference','AlludedOTReference','PossibleOTReference')
        """
        return self.__getEntry( verseKey )
    # end of BibleReferencesLinks.getFullRelatedPassagesList

    def getRelatedPassagesList( self, verseKey ):
        """
        Given a verse key, return a list containing 2-tuples:
            0: Link type ('QuotedOTReference','AlludedOTReference','PossibleOTReference')
            1: Link FlexibleVersesKey object
        """
        if verseKey in self.__Index:
            relatedPassageList = self.__getEntry( verseKey )
            if relatedPassageList:
                resultList = []
                for relatedPassage in relatedPassageList:
                    #print( ' ', relatedPassage )
                    sourceReference,sourceComponent,parsedSourceReference,actualLinksList = relatedPassage
                    #print( ' ', sourceReference )
                    for actualLink in actualLinksList:
                        #print( '    ', actualLink )
                        targetReference,targetComponent,parsedTargetReference,linkType = actualLink
                        #print( '    ', linkType, targetReference )
                        resultList.append( (linkType,parsedTargetReference) )
                return resultList
    # end of BibleReferencesLinks.getRelatedPassagesList
# end of BibleReferencesLinks class



#@singleton # Can only ever have one instance
#class XXXBibleReferencesLinks:
    #"""
    #Class for handling BibleReferencesLinks.

    #This class doesn't deal at all with XML, only with Python dictionaries, etc.

    #Note: BBB is used in this class to represent the three-character referenceAbbreviation.
    #"""

    #def __init__( self ): # We can't give this parameters because of the singleton
        #"""
        #Constructor:
        #"""
        #self.__DataList = self.__DataDict = None # We'll import into this in loadData
    ## end of BibleReferencesLinks.__init__


    #def loadData( self, XMLFileOrFilepath=None ):
        #""" Loads the pickle or XML data file and imports it to dictionary format (if not done already). """
        #if not self.__DataList: # We need to load them once -- don't do this unnecessarily
            ## See if we can load from the pickle file (faster than loading from the XML)
            #standardXMLFileOrFilepath = BibleOrgSysGlobals.BOS_DATA_FILES_FOLDERPATH.joinpath( "BibleReferencesLinks.xml" )
            #standardPickleFilepath = BibleOrgSysGlobals.BOS_DATA_FILES_FOLDERPATH.joinpath( 'DerivedFiles/', "BibleReferencesLinks_Tables.pickle" )
            ##print( os.access( standardPickleFilepath, os.R_OK ) )
            ##print( os.stat(standardPickleFilepath).st_mtime > os.stat(standardXMLFileOrFilepath).st_mtime )
            ##print( os.stat(standardPickleFilepath).st_ctime )
            ##print( os.stat(standardXMLFileOrFilepath).st_ctime )
            ##print( os.stat(standardPickleFilepath).st_ctime > os.stat(standardXMLFileOrFilepath).st_ctime )
            #if XMLFileOrFilepath is None \
            #and os.access( standardPickleFilepath, os.R_OK ) \
            #and os.stat(standardPickleFilepath).st_mtime > os.stat(standardXMLFileOrFilepath).st_mtime \
            #and os.stat(standardPickleFilepath).st_ctime > os.stat(standardXMLFileOrFilepath).st_ctime: # There's a newer pickle file
                #import pickle
                #if BibleOrgSysGlobals.verbosityLevel > 2: print( "Loading pickle file {}…".format( standardPickleFilepath ) )
                #with open( standardPickleFilepath, 'rb') as pickleFile:
                    #self.__DataList = pickle.load( pickleFile ) # The protocol version used is detected automatically, so we do not have to specify it
                    #self.__DataDict = pickle.load( pickleFile ) # The protocol version used is detected automatically, so we do not have to specify it
            #else: # We have to load the XML (much slower)
                #from BibleOrgSys.Reference.BibleReferencesLinksConverter import BibleReferencesLinksConverter
                #if XMLFileOrFilepath is not None: logging.warning( _("Bible books codes are already loaded -- your given filepath of {!r} was ignored").format(XMLFileOrFilepath) )
                #bbcc = BibleReferencesLinksConverter()
                #bbcc.loadAndValidate( XMLFileOrFilepath ) # Load the XML (if not done already)
                #self.__DataList, self.__DataDict = bbcc.importDataToPython() # Get the various dictionaries organised for quick lookup
        #self.__DataList = None # Get rid of this as we don't need it
        #return self # So this command can be chained after the object creation
    ## end of BibleReferencesLinks.loadData


    #def __str__( self ):
        #"""
        #This method returns the string representation of this object.

        #@return: the name of a Bible object formatted as a string
        #@rtype: string
        #"""
        #indent = 2
        #result = "BibleReferencesLinks object"
        #result += ('\n' if result else '') + ' '*indent + _("Number of list entries = {:,}").format( len(self.__DataList) )
        #result += ('\n' if result else '') + ' '*indent + _("Number of dict entries = {:,}").format( len(self.__DataDict) )
        #return result
    ## end of BibleReferencesLinks.__str__


    ##def __len__( self ):
        ##"""
        ##Return the number of available codes.
        ##"""
        ##assert len(self.__DataList["referenceAbbreviationDict"]) == len(self.__DataList["referenceNumberDict"]) )
        ##return len(self.__DataList["referenceAbbreviationDict"])


    ##def __contains__( self, BBB ):
        ##""" Returns True or False. """
        ##return BBB in self.__DataList["referenceAbbreviationDict"]


    ##def __iter__( self ):
        ##""" Yields the next BBB. """
        ##for BBB in self.__DataList["referenceAbbreviationDict"]:
            ##yield BBB

    #def getFullRelatedPassagesList( self, verseKey ):
        #"""
        #Given a verse key, return a list containing 4-tuples:
            #0: Verse key string (same as given parameter)
            #1: Key type ('Verse' or 'Verses')
            #2: FlexibleVersesKey object
            #3: List of links containing 4-tuples:
                #0: Link verse key string
                #1: Link key type ('Verse' or 'Verses')
                #2: Link FlexibleVersesKey object
                #3: Link type ('QuotedOTReference','AlludedOTReference','PossibleOTReference')
        #"""
        #if verseKey in self.__DataDict:
            #return self.__DataDict[verseKey]
    ## end of BibleReferencesLinks.getFullRelatedPassagesList

    #def getRelatedPassagesList( self, verseKey ):
        #"""
        #Given a verse key, return a list containing 2-tuples:
            #0: Link type ('QuotedOTReference','AlludedOTReference','PossibleOTReference')
            #1: Link FlexibleVersesKey object
        #"""
        #if verseKey in self.__DataDict:
            #relatedPassageList = self.getFullRelatedPassagesList( verseKey )
            #if relatedPassageList:
                #resultList = []
                #for relatedPassage in relatedPassageList:
                    ##print( ' ', relatedPassage )
                    #sourceReference,sourceComponent,parsedSourceReference,actualLinksList = relatedPassage
                    ##print( ' ', sourceReference )
                    #for actualLink in actualLinksList:
                        ##print( '    ', actualLink )
                        #targetReference,targetComponent,parsedTargetReference,linkType = actualLink
                        ##print( '    ', linkType, targetReference )
                        #resultList.append( (linkType,parsedTargetReference) )
                #return resultList
    ## end of BibleReferencesLinks.getRelatedPassagesList
## end of BibleReferencesLinks class



def demo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel > 1: print( programNameVersion )

    # Demo the BibleReferencesLinks object
    brl = BibleReferencesLinks().loadData() # Doesn't reload the XML unnecessarily :)
    print( brl ) # Just print a summary

    testKeys = ( 'MAT_1:23', 'MAT_3:12', 'MRK_7:7', 'ACT_7:8', 'ISA_7:14', )

    print( "\nTest full passage list…" )
    for verseReferenceString in testKeys:
        svk = SimpleVerseKey( verseReferenceString )
        print( svk.getShortText() )
        #print( svk, brl.getFullRelatedPassagesList( svk ) )
        relatedPassageList = brl.getFullRelatedPassagesList( svk )
        if relatedPassageList:
            for relatedPassage in relatedPassageList:
                #print( ' ', relatedPassage )
                sourceReference,sourceComponent,parsedSourceReference,actualLinksList = relatedPassage
                print( ' ', sourceReference )
                for actualLink in actualLinksList:
                    #print( '    ', actualLink )
                    targetReference,targetComponent,parsedTargetReference,linkType = actualLink
                    print( '    ', linkType, targetReference )

    print( "\nTest passage list…" )
    for verseReferenceString in testKeys:
        svk = SimpleVerseKey( verseReferenceString )
        print( svk.getVerseKeyText(), brl.getRelatedPassagesList( svk ) )
# end of demo


if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    demo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of BibleReferencesLinks.py
