#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# InternalBible.py
#
# Module handling the internal representation of the overall Bible
#       and which in turn holds the Bible book objects.
#
# Copyright (C) 2010-2020 Robert Hunt
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
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Module for defining and manipulating Bibles in our internal USFM-based 'lines' format.

InternalBible is the base class containing self.books which contains the Bible text.
    The BibleWriter class builds on this by adding export routines.
    The Bible class builds on that by adding metadata
        and understanding of divisions (e.g., Old Testament) and things like that.

The calling class needs to call this base class __init__ routine and also set:
    self.objectTypeString (e.g., 'USFM2' or 'USX')
    self.objectNameString (with a description of the type of Bible object, e.g., 'USFM Bible object')

It also needs to provide a "load" routine that sets any of the relevant fields:
    self.sourceFolder, self.sourceFilename, self.sourceFilepath, self.fileExtension
    self.name, self.givenName, self.shortName, self.abbreviation
    self.status, self.revision, self.version

If you have access to any metadata, that goes in self.suppliedMetadata dictionary
    and then call or supply applySuppliedMetadata
    to standardise and copy it to self.settingsDict.
self.suppliedMetadata is a dictionary containing the following possible entries (all dictionaries):
    'Project' for metadata supplied for the project
    'File' for metadata submitted in a separate text file (this is given priority)
    'SSF','PTX7','PTX8' for USFM/Paratext Bibles
    'OSIS', 'DBL', 'BCV' for other Bibles

The calling class then fills
    self.books by calling stashBook() which updates:
        self.BBBToNameDict, self.bookNameDict, self.combinedBookNameDict
"""
from gettext import gettext as _
from typing import Dict, List, Tuple, Optional, Union
import os
import sys
import logging
from pathlib import Path
from collections import defaultdict
import re
import multiprocessing

if __name__ == '__main__':
    aboveAboveFolderpath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderpath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderpath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys.Internals.InternalBibleInternals import InternalBibleEntryList, BOS_EXTRA_TYPES, BOS_EXTRA_MARKERS
from BibleOrgSys.Internals.InternalBibleBook import BCV_VERSION
from BibleOrgSys.Reference.VerseReferences import SimpleVerseKey


LAST_MODIFIED_DATE = '2020-05-23' # by RJH
SHORT_PROGRAM_NAME = "InternalBible"
PROGRAM_NAME = "Internal Bible handler"
PROGRAM_VERSION = '0.84'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

debuggingThisModule = False


OT39_BOOKLIST = ( 'GEN', 'EXO', 'LEV', 'NUM', 'DEU', 'JOS', 'JDG', 'RUT', 'SA1', 'SA2', 'KI1', 'KI2', 'CH1', 'CH2', \
        'EZR', 'NEH', 'EST', 'JOB', 'PSA', 'PRO', 'ECC', 'SNG', 'ISA', 'JER', 'LAM', 'EZE', 'DAN', \
        'HOS', 'JOL', 'AMO', 'OBA', 'JNA', 'MIC', 'NAH', 'HAB', 'ZEP', 'HAG', 'ZEC', 'MAL' )
assert len( OT39_BOOKLIST ) == 39
NT27_BOOKLIST = ( 'MAT', 'MRK', 'LUK', 'JHN', 'ACT', 'ROM', 'CO1', 'CO2', 'GAL', 'EPH', 'PHP', 'COL', \
        'TH1', 'TH2', 'TI1', 'TI2', 'TIT', 'PHM', 'HEB', 'JAM', 'PE1', 'PE2', 'JN1', 'JN2', 'JN3', 'JDE', 'REV' )
assert len( NT27_BOOKLIST ) == 27



InternalBibleProperties = {} # Used for diagnostic reasons

class InternalBible:
    """
    Class to define and manipulate InternalBibles.

    The BibleWriter class is based on this class.

    This class contains no load function -- that is expected to be supplied by the superclass.

    The superclass MUST also set:
        self.objectNameString = 'XYZ Bible object'
        self.objectTypeString = 'XYZ'
    """
    def __init__( self ):
        """
        Create the InternalBible object with empty variables.
        """
        fnPrint( debuggingThisModule, "InternalBible.__init__()" )

        # Set up empty variables for the object
        #       some of which will be filled in later depending on what is known from the Bible type
        self.name = self.givenName = self.shortName = self.projectName = self.abbreviation = None
        self.sourceFolder = self.sourceFilename = self.sourceFilepath = self.fileExtension = None
        self.status = self.revision = self.version = self.encoding = None

        # Set up empty containers for the object
        self.books = {}
        self.availableBBBs = set() # Will eventually contain a set of the books codes which we know are in this particular Bible (even if the book is not loaded yet)
        self.givenBookList = [] # Only if we're given this (cf. deduced)
        self.suppliedMetadata = None
        self.settingsDict = {} # This is often filled from self.suppliedMetadata in applySuppliedMetadata()
        self.BBBToNameDict, self.bookNameDict, self.combinedBookNameDict, self.bookAbbrevDict = {}, {}, {}, {} # Used to store book name and abbreviations (pointing to the BBB codes)
        self.reverseDict, self.guesses = {}, '' # A program history
        self.preloadDone = self.loadedAllBooks = False
        self.triedLoadingBook, self.bookNeedsReloading = {}, {} # Dictionaries with BBB as key
        self.divisions = {}
        self.checkResultsDictionary = {}
        self.checkResultsDictionary['Priority Errors'] = [] # Put this one first in the ordered dictionary
    # end of InternalBible.__init__


    def __str__( self ) -> str:
        """
        This method returns the string representation of a Bible.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        # fnPrint( debuggingThisModule, "InternalBible.__str__()" )

        set1 = ( 'Title', 'Description', 'Version', 'Revision', ) # Ones to print at verbosityLevel > 1
        set2 = ( 'Status', 'Font', 'Copyright', 'Licence', ) # Ones to print at verbosityLevel > 2
        set3 = set1 + set2 + ( 'Name', 'Abbreviation' ) # Ones not to print at verbosityLevel > 3

        result = self.objectNameString
        indent = 2
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>2: result += ' v' + PROGRAM_VERSION
        if self.name: result += ('\n' if result else '') + ' '*indent + _("Name: {}").format( self.name )
        if self.abbreviation: result += ('\n' if result else '') + ' '*indent + _("Abbreviation: {}").format( self.abbreviation )
        if self.sourceFolder: result += ('\n' if result else '') + ' '*indent + _("Source folder: {}").format( self.sourceFolder )
        elif self.sourceFilepath: result += ('\n' if result else '') + ' '*indent + _("Source: {}").format( self.sourceFilepath )
        if BibleOrgSysGlobals.verbosityLevel > 1:
            for fieldName in set1:
                fieldContents = self.getSetting( fieldName )
                if fieldContents:
                    result += ('\n' if result else '') + ' '*indent + _("{}: {!r}").format( fieldName, fieldContents )
            if 'uWaligned' in self.__dict__ and self.uWaligned:
                result += ('\n' if result else '') + ' '*indent + _("Contains translation alignments: True")
        if BibleOrgSysGlobals.verbosityLevel > 2:
            for fieldName in ( 'Status', 'Font', 'Copyright', 'Licence', ):
                fieldContents = self.getSetting( fieldName )
                if fieldContents:
                    result += ('\n' if result else '') + ' '*indent + _("{}: {!r}").format( fieldName, fieldContents )
        if (BibleOrgSysGlobals.debugFlag or debuggingThisModule) and BibleOrgSysGlobals.verbosityLevel > 3 \
        and self.suppliedMetadata and self.objectTypeString not in ('PTX7','PTX8'): # There's too much potential Paratext metadata
            for metadataType in self.suppliedMetadata:
                for fieldName in self.suppliedMetadata[metadataType]:
                    if fieldName not in set3:
                        fieldContents = self.suppliedMetadata[metadataType][fieldName]
                        if fieldContents:
                            result += ('\n' if result else '') + '  '*indent + _("{}: {!r}").format( fieldName, fieldContents )
        #if self.revision: result += ('\n' if result else '') + ' '*indent + _("Revision: {}").format( self.revision )
        #if self.version: result += ('\n' if result else '') + ' '*indent + _("Version: {}").format( self.version )
        result += ('\n' if result else '') + ' '*indent + _("Number of{} books: {}{}") \
                                        .format( '' if self.loadedAllBooks else ' loaded', len(self.books), ' {}'.format( self.getBookList() ) if 0<len(self.books)<5 else '' )
        return result
    # end of InternalBible.__str__


    def __len__( self ):
        """
        This method returns the number of loaded books in the Bible.
        """
        if BibleOrgSysGlobals.debugFlag and not self.loadedAllBooks:
            logging.critical( _("__len__ result is unreliable because all books not loaded!") )
        return len( self.books )
    # end of InternalBible.__len__


    def __contains__( self, BBB:str ):
        """
        This method checks whether the Bible (as loaded so far) contains the BBB book.

        Note that we also have a member self.availableBBBs which contains a set of all
            books which we know to be in this Bible even if not yet loaded.

        Returns True or False.
        """
        if BibleOrgSysGlobals.debugFlag: assert isinstance(BBB,str) and len(BBB)==3
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule and not self.loadedAllBooks:
            logging.critical( _("__contains__ result is unreliable because all books not loaded!") )

        return BBB in self.books
    # end of InternalBible.__contains__


    def __getitem__( self, keyIndex ):
        """
        Given an index integer, return the book object (or raise an IndexError)
            Note that it returns the book object, not just the BBB.

        This function also accepts a BBB so you can use it to get a book from the Bible by BBB.
        """
        # fnPrint( debuggingThisModule, f"InternalBible.__getitem__( {keyIndex} )" )
        #dPrint( 'Quiet', debuggingThisModule, list(self.books.items()) )
        if isinstance( keyIndex, int ):
            return list(self.books.items())[keyIndex][1] # element 0 is BBB, element 1 is the book object
        if isinstance( keyIndex, str ) and len(keyIndex)==3: # assume it's a BBB
            return self.books[keyIndex]
    # end of InternalBible.__getitem__


    def __iter__( self ):
        """
        Yields the next book object.

        NOTE: Most other functions return the BBB -- this returns the actual book object!
        """
        if BibleOrgSysGlobals.debugFlag and not self.loadedAllBooks:
            logging.critical( _("__iter__ result is unreliable because all books not loaded!") )

        for BBB in self.books:
            yield self.books[BBB]
    # end of InternalBible.__iter__


    def discoverProperties( self ):
        """
        This is a diagnostic function which lists the properties of various types of internal Bibles.

        We need this to standardise all the different Bible types.
        """
        fnPrint( debuggingThisModule, f"InternalBible.discoverProperties() for {self.objectTypeString}" )
        InternalBibleProperties[self.objectTypeString] = {}

        for myPropertyName in self.__dict__:
            if myPropertyName in ( '__class__','__contains__','__delattr__','__dict__','__dir__','__doc__','__eq__',
                              '__format__','__ge__','__getattribute__','__getitem__','__gt__','__hash__','__init__',
                              '__iter__','__le__','__len__','__lt__','__module__','__ne__','__new__','__reduce__',
                              '__reduce_ex__','__repr__','__setattr__','__sizeof__','__str__','__subclasshook__',
                              '__weakref__' ):
                continue # ignore Python built-ins
            if myPropertyName in ( 'containsAnyOT39Books', 'containsAnyNT27Books', '_InternalBible__getNames',
                              'loadBookIfNecessary', 'reloadBook', 'doPostLoadProcessing', 'xxxunloadBooks',
                              'loadMetadataTextFile', 'getBookList', 'pickle', 'getAssumedBookName', 'getLongTOCName',
                              'getShortTOCName', 'getBooknameAbbreviation', 'stashBook', 'guessXRefBBB',
                              'getVersification', 'getAddedUnits', 'discover', '__aggregateDiscoveryResults',
                              'check', 'getCheckResults', 'makeErrorHTML', 'getNumVerses', 'getNumChapters', 'getContextVerseData',
                              'getVerseDataList', 'getVerseText', 'writeBOSBCVFiles' ):
                continue # ignore my own functions
            if myPropertyName in ( 'toBOSBCV', 'toBibleDoor', 'toDoor43', 'toDrupalBible', 'toESFM', 'toESword',
                              'toHTML5', 'toHaggaiXML', 'toMarkdown', 'toMySword', 'toODF', 'toOSISXML',
                              'toOpenSongXML', 'toPhotoBible', 'toPickleObject', 'toPseudoUSFM', 'toSwordModule',
                              'toSwordSearcher', 'toTeX', 'toText', 'toUSFM', 'toUSFXXML', 'toUSXXML',
                              'toZefaniaXML', 'totheWord', 'doAllExports', 'doExportHelper',
                              '_BibleWriter__adjustControlDict', '_BibleWriter__formatHTMLVerseText',
                              '_BibleWriter__setupWriter', '_writeSwordLocale',
                              'doneSetupGeneric', ):
                continue # ignore BibleWriter functions

            myProperty = getattr( self, myPropertyName )
            #dPrint( 'Quiet', debuggingThisModule, type(myProperty), type(myProperty).__name__, myProperty.__class__ )
            if myProperty is None or isinstance( myProperty, str ) or isinstance( myProperty, int ):
                vPrint( 'Quiet', debuggingThisModule, myPropertyName, '=', myProperty )
                InternalBibleProperties[self.objectTypeString][myPropertyName] = myProperty
            else: # not any of the above simple types
                vPrint( 'Quiet', debuggingThisModule, myPropertyName, 'is', type(myProperty).__name__ )
                InternalBibleProperties[self.objectTypeString][myPropertyName] = type(myProperty).__name__

        vPrint( 'Quiet', debuggingThisModule, InternalBibleProperties )
    #end of InternalBible.discoverProperties


    def containsAnyOT39Books( self ):
        """
        Returns True if any of the 39 common OT books are present.
        """
        if BibleOrgSysGlobals.debugFlag and not self.loadedAllBooks:
            logging.critical( _("containsAnyOT39Books result is unreliable because all books not loaded!") )
        for BBB in OT39_BOOKLIST:
            if BBB in self: return True
        return False
    #end of InternalBible.containsAnyOT39Books


    def containsAnyNT27Books( self ):
        """
        Returns True if any of the 27 common NT books are present.
        """
        if BibleOrgSysGlobals.debugFlag and not self.loadedAllBooks:
            logging.critical( _("containsAnyNT27Books result is unreliable because all books not loaded!") )
        for BBB in NT27_BOOKLIST:
            if BBB in self: return True
        return False
    #end of InternalBible.containsAnyNT27Books


    def __getNames( self ):
        """
        Try to improve our names from supplied metadata in self.settingsDict.

        This method should be called once all books are loaded.
        May be called again if external metadata is also loaded.
        """
        fnPrint( debuggingThisModule, "InternalBible.__getNames()" )
        if not self.abbreviation and 'WorkAbbreviation' in self.settingsDict: self.abbreviation = self.settingsDict['WorkAbbreviation']
        if not self.name and self.givenName: self.name = self.givenName
        if not self.name and 'FullName' in self.settingsDict: self.name = self.settingsDict['FullName']
        if not self.shortName and 'ShortName' in self.settingsDict: self.shortName = self.settingsDict['ShortName']
        if not self.shortName and 'Name' in self.settingsDict: self.shortName = self.settingsDict['Name']
        self.projectName = self.name if self.name else 'Unknown'

        if self.settingsDict: # we have metadata loaded
            for BBB in self.books:
                for fieldName in self.settingsDict:
                    if fieldName.startswith( BBB ):
                        self.books[BBB].getAssumedBookNames() # don't need the returned result
                        break
    # end of InternalBible.__getNames


    def getAName( self, abbrevFirst:bool=False ) -> str:
        """
        Try to find a name to identify this internal Bible.

        Returns a string or None.
        """
        fnPrint( debuggingThisModule, f"InternalBible.getAName( abbrevFirst={abbrevFirst} )" )

        if abbrevFirst and self.abbreviation: return self.abbreviation

        if self.name: return self.name
        if self.givenName: return self.givenName
        if self.shortName: return self.shortName
        if self.projectName and self.projectName != 'Unknown': return self.projectName
        if self.abbreviation: return self.abbreviation
        if self.sourceFilename: return self.sourceFilename
        if self.sourceFolder:
            return os.path.basename( str(self.sourceFolder)[:-1] if str(self.sourceFolder)[-1] in ('\\','/')
                                                                                else str(self.sourceFolder) )
        return self.objectTypeString
    # end of InternalBible.getAName


    def loadBookIfNecessary( self, BBB ) -> None:
        """
        Checks to see if a requested book has already been loaded
            or already failed at loading.
        If not, tries to load the book.
        """
        fnPrint( debuggingThisModule, f"InternalBible.loadBookIfNecessary( {BBB} )" )
        #dPrint( 'Quiet', debuggingThisModule, "b {} tlb {}".format( self.books, self.triedLoadingBook ) )
        #dPrint( 'Quiet', debuggingThisModule, "bnr {}".format( self.bookNeedsReloading ) )

        if (BBB not in self.books and BBB not in self.triedLoadingBook) \
        or (BBB in self.bookNeedsReloading and self.bookNeedsReloading[BBB]):
            try: self.loadBook( BBB ) # Some types of Bibles have this function (so an entire Bible doesn't have to be loaded at startup)
            except AttributeError: # Could be that our Bible doesn't have the ability to load individual books
                errorClass, exceptionInstance, traceback = sys.exc_info()
                #dPrint( 'Quiet', debuggingThisModule, '{!r}  {!r}  {!r}'.format( errorClass, exceptionInstance, traceback ) )
                if "object has no attribute 'loadBook'" in str(exceptionInstance):
                    logging.info( _("No 'loadBook()' function to load individual {} Bible book for {}") \
                        .format( BBB, self.getAName( abbrevFirst=True ) ) ) # Ignore errors
                else: # it's some other attribute error in the loadBook function
                    raise
            except KeyError:
                errorClass, exceptionInstance, traceback = sys.exc_info()
                vPrint( 'Quiet', debuggingThisModule, 'loadBookIfNecessary {!r}  {!r}  {!r}'.format( errorClass, exceptionInstance, traceback ) )
                # TODO: Fix the text in the following line
                if "object has no attribute 'loadBook'" in str(exceptionInstance):
                    logging.critical( _("No individual {} Bible book available for {}") \
                                    .format( BBB, self.getAName( abbrevFirst=True ) ) ) # Ignore errors
                else: # it's some other key error in the loadBook function
                    raise
            except FileNotFoundError: logging.critical( _("Unable to find and load individual {} Bible book for {}") \
                                    .format( BBB, self.getAName( abbrevFirst=True ) ) ) # Ignore errors
            self.triedLoadingBook[BBB] = True
            self.bookNeedsReloading[BBB] = False
        else: # didn't try loading the book
            vPrint( 'Quiet', debuggingThisModule, 'NOLOAD1', BBB in self.books, BBB in self.triedLoadingBook )
            vPrint( 'Quiet', debuggingThisModule, 'NOLOAD2', BBB in self.bookNeedsReloading, self.bookNeedsReloading[BBB] if BBB in self.bookNeedsReloading else 'NONE' )
    # end of InternalBible.loadBookIfNecessary


    def reloadBook( self, BBB:str ):
        """
        Tries to load or reload a book (perhaps because we changed it on disk).
        """
        fnPrint( debuggingThisModule, f"InternalBible.reloadBook( {BBB} )" )

        #if BBB not in self.books and BBB not in self.triedLoadingBook:
        try: self.loadBook( BBB ) # Some types of Bibles have this function (so an entire Bible doesn't have to be loaded at startup)
        except AttributeError: logging.info( "No function to load individual Bible book: {}".format( BBB ) ) # Ignore errors
        except FileNotFoundError: logging.info( "Unable to find and load individual Bible book: {}".format( BBB ) ) # Ignore errors
        self.triedLoadingBook[BBB] = True
        self.bookNeedsReloading[BBB] = False

        self.reProcessBook( BBB )
    # end of InternalBible.reloadBook


    def reProcessBook( self, BBB:str ):
        """
        Tries to re-index a loaded book.
        """
        fnPrint( debuggingThisModule, f"InternalBible.reProcessBook( {BBB} )" )
        if BibleOrgSysGlobals.debugFlag:
            assert BBB in self.books

        #try: del self.discoveryResults # These are now out-of-date
        #except KeyError:
            #if BibleOrgSysGlobals.debugFlag: vPrint( 'Quiet', debuggingThisModule, _("reloadBook has no discoveryResults to delete") )

        if 'discoveryResults' in self.__dict__: # need to update them
            # Need to double-check that this doesn't cause any double-ups …XXXXXXXXXXXXXXXXXXXXXX
            self.discoveryResults[BBB] = self.books[BBB]._discover()
            self.__aggregateDiscoveryResults()
    # end of InternalBible.reProcessBook


    def doPostLoadProcessing( self ):
        """
        This method should be called once all books are loaded to do critical book-keeping.

        Doesn't do a "discover" yet, in case it's not really required yet,
            coz discover() is quite time-consuming.
        """
        fnPrint( debuggingThisModule, "InternalBible.doPostLoadProcessing()" )

        self.loadedAllBooks = True

        # Try to improve our names (may also be called from loadMetadataTextFile)
        self.__getNames()

        # Discover what we've got loaded so we don't have to worry about doing it later
        #self.discover() # Removed from here coz it's quite time consuming if we don't really need it yet

        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            self.discoverProperties()
    # end of InternalBible.doPostLoadProcessing


    #def xxxunloadBooks( self ):
        #"""
        #Called to unload books, usually coz one or more of them has been edited.
        #"""
        #if BibleOrgSysGlobals.debugFlag: vPrint( 'Quiet', debuggingThisModule, _("unloadBooks()…") )
        #self.books = {}
        #self.BBBToNameDict, self.bookNameDict, self.combinedBookNameDict, self.bookAbbrevDict = {}, {}, {}, {} # Used to store book name and abbreviations (pointing to the BBB codes)
        #self.reverseDict, self.guesses = {}, '' # A program history
        #self.loadedAllBooks, self.triedLoadingBook = False, {}
        #self.divisions = {}
        #self.checkResultsDictionary = {}
        #self.checkResultsDictionary['Priority Errors'] = [] # Put this one first in the ordered dictionary

        #try: del self.discoveryResults # These are now irrelevant
        #except KeyError:
            #if BibleOrgSysGlobals.debugFlag: vPrint( 'Quiet', debuggingThisModule, _("unloadBooks has no discoveryResults to delete") )
    ## end of InternalBible.unloadBooks


    def loadMetadataTextFile( self, mdFilepath ):
        """
        Load the fields from the given metadata text file into self.suppliedMetadata['File']
            and then copy them into self.settingsDict.

        See http://freely-given.org/Software/BibleDropBox/Metadata.html for
            a description of the format and the typical, allowed fields.
        """
        def saveMetadataField( fieldName, contents ):
            """
            Save an entry in the settings dictionary
                but check for duplicates first.
            """
            if fieldName in self.suppliedMetadata['File']: # We have a duplicate
                logging.warning("About to replace {!r}={!r} from supplied metadata file with {!r}".format( fieldName, self.suppliedMetadata['File'][fieldName], contents ) )
            else: # Also check for "duplicates" with a different case
                ucFieldName = fieldName.upper()
                for key in self.suppliedMetadata['File']:
                    ucKey = key.upper()
                    if ucKey == ucFieldName:
                        logging.warning("About to add {!r} from supplied metadata file even though already have {!r}".format( fieldName, key ) )
                        break
            self.suppliedMetadata['File'][fieldName] = BibleOrgSysGlobals.makeSafeString( contents )
        # end of loadMetadataTextFile.saveMetadataField

        # Main code for loadMetadataTextFile()
        if self.suppliedMetadata is None: self.suppliedMetadata = {}
        elif 'File' in self.suppliedMetadata:
            logging.critical( "loadMetadataTextFile: Already have 'File' metadata loaded—will be overridden!" )

        # Loads the metadata into self.suppliedMetadata
        logging.info( "Loading supplied project metadata…" )
        vPrint( 'Normal', debuggingThisModule, "Loading supplied project metadata…" )
        #dPrint( 'Info', debuggingThisModule, "Old metadata settings", len(self.suppliedMetadata), self.suppliedMetadata )
        self.suppliedMetadata['File'] = {}
        lineCount, continuedFlag = 0, False
        with open( mdFilepath, 'rt', encoding='utf-8' ) as mdFile:
            for line in mdFile:
                while line and line[-1] in '\n\r': line=line[:-1] # Remove trailing newline characters (Linux or Windows)
                #dPrint( 'Quiet', debuggingThisModule, "MD line: {!r}".format( line ) )
                if not line: continue # Just discard additional blank lines
                lineCount += 1
                if line[0] == '#': continue # Just discard comment lines
                if not continuedFlag:
                    if '=' not in line:
                        logging.warning( _("loadMetadataTextFile: Missing equals sign from metadata line (ignored): {!r}").format( line ) )
                    else: # Seems like a field=something type line
                        if line.count( '=' ) > 1:
                            logging.warning( _("loadMetadataTextFile: Surprised to find multiple equal signs in line: {!r}").format( line ) )
                        bits = line.split( '=', 1 )
                        assert len(bits) == 2
                        fieldName = bits[0]
                        fieldContents = bits[1]
                        if fieldContents.endswith( '\\' ):
                            continuedFlag = True
                            fieldContents = fieldContents[:-1] # Remove the continuation character
                        else:
                            if not fieldContents:
                                logging.warning( "Metadata line has a blank entry for {!r}".format( fieldName ) )
                            saveMetadataField( fieldName, fieldContents )
                else: # continuedFlag
                    if line.endswith( '\\' ): line = line[:-1] # Remove the continuation character
                    else: continuedFlag = False
                    fieldContents += line
                    if not continuedFlag:
                        logging.warning( _("loadMetadataTextFile: Metadata lines result in a blank entry for {!r}").format( fieldName ) )
                        saveMetadataField( fieldName, fieldContents )
            vPrint( 'Normal', debuggingThisModule, "  {} non-blank lines read from uploaded metadata file".format( lineCount ) )
        vPrint( 'Info', debuggingThisModule, "New metadata settings", len(self.suppliedMetadata), self.suppliedMetadata )

        # Now move the information into our settingsDict
        self.applySuppliedMetadata( 'File' )

        # Try to improve our names (also called earlier from doPostLoadProcessing)
        self.__getNames()
    # end of InternalBible.loadMetadataTextFile


    def applySuppliedMetadata( self, applyMetadataType ):
        """
        Using the dictionary at self.suppliedMetadata[applyMetadataType],
            load the fields into self.settingsDict
            and try to standardise it at the same time.

        Note that this function also takes 'SSF' as a special case
            since it's a commonly used subset of self.suppliedMetadata['PTXn'].

        Note that some importers might prefer to supply their own function instead.
            (DBL Bible does this.)

        Standard settings values include:
            Abbreviation
            FullName, Workname, Name, ProjectName
            ShortName
            Language, ISOLanguageCode
            Copyright, Rights
            Creator, Publisher
        """
        fnPrint( debuggingThisModule, f"applySuppliedMetadata( {applyMetadataType} )" )
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>2:
            assert applyMetadataType in ( 'Project','File', 'SSF', 'PTX7','PTX8', 'OSIS', 'uW',
                                         'e-Sword-Bible','e-Sword-Commentary', 'MySword','MyBible',
                                         'BCV','Online','theWord','Unbound','VerseView','Forge4SS','VPL' )

        if not self.suppliedMetadata: # How/Why can this happen?
            logging.warning( f"No {applyMetadataType} metadata supplied to applySuppliedMetadata() function" )
            if debuggingThisModule or BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag:
                halt # No self.suppliedMetadata supplied to applySuppliedMetadata()
            return

        if BibleOrgSysGlobals.debugFlag and debuggingThisModule and BibleOrgSysGlobals.verbosityLevel > 2:
            vPrint( 'Quiet', debuggingThisModule, "Supplied {} metadata ({}):".format( applyMetadataType, len(self.suppliedMetadata[applyMetadataType]) ) )
            for key,value in sorted( self.suppliedMetadata[applyMetadataType].items() ):
                vPrint( 'Quiet', debuggingThisModule, "  {} = {!r}".format( key, value ) )

        if applyMetadataType in ( 'File', 'BCV','Online','theWord','Unbound','VerseView','Forge4SS','VPL' ):
            # These types copy ALL the data across, but through a name-changing dictionary if necessary
            # The dictionary entries map from the left-hand type to the right-hand type
            nameChangeDict = {}
            nameChangeDict['File'] = {} # This is metadata submitted by the user in a separate text file
            nameChangeDict['BCV'] = {}
            nameChangeDict['Online'] = { 'LongName':'FullName' }
            nameChangeDict['theWord'] = { 'description':'FullName', 'short.title':'ShortName' }
            nameChangeDict['Unbound'] = { 'name':'FullName', 'filetype':'Filetype', 'copyright':'Copyright', 'abbreviation':'Abbreviation', 'language':'Language', 'note':'Note', 'columns':'Columns' }
            nameChangeDict['VerseView'] = { 'Title':'FullName' }
            nameChangeDict['Forge4SS'] = { 'TITLE':'FullName', 'ABBREVIATION':'Abbreviation', 'AUTHORDETAIL':'AuthorDetailHTML' }
            nameChangeDict['VPL'] = { 'TITLE':'FullName', 'ABBREVIATION':'Abbreviation', } # Not sure if these two are needed here???
            if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>3:
                vPrint( 'Quiet', debuggingThisModule, "applySuppliedMetadata is processing {} {!r} metadata items".format( len(self.suppliedMetadata[applyMetadataType]), applyMetadataType ) )
            for oldKey,value in self.suppliedMetadata[applyMetadataType].items():
                if not value: # We don't expect blank metadata values
                    logging.warning( "Why did we get a blank {} {!r} metadata key?".format( applyMetadataType, oldKey ) )
                newKey = nameChangeDict[applyMetadataType][oldKey] if oldKey in nameChangeDict[applyMetadataType] else oldKey
                if newKey in self.settingsDict: # We have a duplicate
                    logging.warning("About to replace {}={!r} from {} metadata file with {!r}".format( newKey, self.settingsDict[newKey], applyMetadataType, value ) )
                else: # Also check for "duplicates" with a different case
                    ucNewKey = newKey.upper()
                    for key in self.settingsDict:
                        ucKey = key.upper()
                        if ucKey == ucNewKey:
                            logging.warning("About to copy {!r} from {} metadata file even though already have {!r}".format( newKey, applyMetadataType, key ) )
                            break
                self.settingsDict[newKey] = value

        elif applyMetadataType == 'Project':
            # This is user-submitted project metadata -- available fields include:
            #   ContactName, EmailAddress, Goals, Permission, ProjectCode, ProjectName,
            #   SubmittedBibleFileInfo, SubmittedMetadataFileInfo,
            #   WantODFs, WantPDFs, WantPhotoBible
            wantedDict = { 'ProjectName':'ProjectName', }
            if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>3:
                vPrint( 'Quiet', debuggingThisModule, "applySuppliedMetadata is processing {} {!r} metadata items".format( len(self.suppliedMetadata[applyMetadataType]), applyMetadataType ) )
            for oldKey,value in self.suppliedMetadata[applyMetadataType].items():
                if oldKey in wantedDict: #  Only copy wanted entries
                    if not value: # We don't expect blank metadata values
                        logging.warning( "Why did we get a blank {} {!r} metadata key?".format( applyMetadataType, oldKey ) )
                    newKey = wantedDict[oldKey]
                    if newKey in self.settingsDict: # We have a duplicate
                        logging.warning("About to replace {}={!r} from {} metadata file with {!r}".format( newKey, self.settingsDict[newKey], applyMetadataType, value ) )
                    else: # Also check for "duplicates" with a different case
                        ucNewKey = newKey.upper()
                        for key in self.settingsDict:
                            ucKey = key.upper()
                            if ucKey == ucNewKey:
                                logging.warning("About to copy {}={!r} from {} metadata file even though already have {!r} (different case)={!r}".format( newKey, value, applyMetadataType, key, self.settingsDict[key] ) )
                                break
                    self.settingsDict[newKey] = value

# NOTE: Some of these could be spread out into individual modules, e.g., the DBL example ???
#           Either that, or bring the DBL one into here
        elif applyMetadataType == 'SSF':
            # This is a special case (coz it's inside the PTX7 metadata)
            wantedDict = { 'Copyright':'Copyright', 'FullName':'WorkName', 'LanguageIsoCode':'ISOLanguageCode' }
            if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>3:
                vPrint( 'Quiet', debuggingThisModule, "applySuppliedMetadata is processing {} {!r} metadata items".format( len(self.suppliedMetadata['PTX7']['SSF']), applyMetadataType ) )
            for oldKey,value in self.suppliedMetadata['PTX7']['SSF'].items():
                if value and oldKey in wantedDict: # Only copy wanted, non-blank entries
                    newKey = wantedDict[oldKey]
                    if newKey in self.settingsDict: # We have a duplicate
                        logging.warning("About to replace {}={!r} from {} metadata file with {!r}".format( newKey, self.settingsDict[newKey], applyMetadataType, value ) )
                    else: # Also check for "duplicates" with a different case
                        ucNewKey = newKey.upper()
                        for key in self.settingsDict:
                            ucKey = key.upper()
                            if ucKey == ucNewKey:
                                logging.warning("About to copy {}={!r} from {} metadata file even though already have {!r} (different case)={!r}".format( newKey, value, applyMetadataType, key, self.settingsDict[key] ) )
                                break
                    self.settingsDict[newKey] = value
            # Determine our encoding while we're at it
            if 'Encoding' in self.suppliedMetadata['PTX7']['SSF']: # See if the SSF file gives some help to us
                ssfEncoding = self.suppliedMetadata['PTX7']['SSF']['Encoding']
                if ssfEncoding == '65001': adjSSFencoding = 'utf-8'
                else:
                    if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 1:
                        vPrint( 'Quiet', debuggingThisModule, _("__init__: File encoding in SSF is set to {!r}").format( ssfEncoding ) )
                    if ssfEncoding.isdigit():
                        adjSSFencoding = 'cp' + ssfEncoding
                        if BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.verbosityLevel > 2:
                            vPrint( 'Quiet', debuggingThisModule, _("__init__: Adjusted to {!r} file encoding").format( adjSSFencoding ) )
                    else:
                        logging.critical( _("__init__: Unsure how to handle {!r} file encoding").format( ssfEncoding ) )
                        adjSSFencoding = ssfEncoding
                if self.encoding is None:
                    self.encoding = adjSSFencoding
                    if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
                        vPrint( 'Quiet', debuggingThisModule, _("__init__: Switched to {!r} file encoding").format( self.encoding ) )
                elif self.encoding == adjSSFencoding:
                    if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
                        vPrint( 'Quiet', debuggingThisModule, _("__init__: Confirmed {!r} file encoding").format( self.encoding ) )
                else: # we have a conflict of encodings for some reason !
                    logging.critical( _("__init__: We were already set to  {!r} file encoding").format( self.encoding ) )
                    self.encoding = adjSSFencoding
                    logging.critical( _("__init__: Switched now to  {!r} file encoding").format( self.encoding ) )

        elif applyMetadataType == 'PTX8':
            # This is a special case (coz it's inside 'Settings' inside the PTX8 metadata)
            wantedDict = { 'Copyright':'Copyright', 'FullName':'WorkName', 'LanguageIsoCode':'ISOLanguageCode', }
            if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>3:
                vPrint( 'Quiet', debuggingThisModule, "applySuppliedMetadata is processing {} {!r} metadata items".format( len(self.suppliedMetadata['PTX8']['Settings']), applyMetadataType ) )
            for oldKey,value in self.suppliedMetadata['PTX8']['Settings'].items():
                if value and oldKey in wantedDict: # Only copy wanted, non-blank entries
                    newKey = wantedDict[oldKey]
                    if newKey in self.settingsDict: # We have a duplicate
                        logging.warning("About to replace {}={!r} from {} metadata file with {!r}".format( newKey, self.settingsDict[newKey], applyMetadataType, value ) )
                    else: # Also check for "duplicates" with a different case
                        ucNewKey = newKey.upper()
                        for key in self.settingsDict:
                            ucKey = key.upper()
                            if ucKey == ucNewKey:
                                logging.warning("About to copy {}={!r} from {} metadata file even though already have {!r} (different case)={!r}".format( newKey, value, applyMetadataType, key, self.settingsDict[key] ) )
                                break
                    self.settingsDict[newKey] = value
            # Determine our encoding while we're at it
            if 'Encoding' in self.suppliedMetadata['PTX8']['Settings']: # See if the settings file gives some help to us
                settingsEncoding = self.suppliedMetadata['PTX8']['Settings']['Encoding']
                if settingsEncoding == '65001': adjSettingsEncoding = 'utf-8'
                else:
                    if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 1:
                        vPrint( 'Quiet', debuggingThisModule, _("__init__: File encoding in settings is set to {!r}").format( settingsEncoding ) )
                    if settingsEncoding.isdigit():
                        adjSettingsEncoding = 'cp' + settingsEncoding
                        if BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.verbosityLevel > 2:
                            vPrint( 'Quiet', debuggingThisModule, _("__init__: Adjusted to {!r} file encoding").format( adjSettingsEncoding ) )
                    else:
                        logging.critical( _("__init__: Unsure how to handle {!r} file encoding").format( settingsEncoding ) )
                        adjSettingsEncoding = settingsEncoding
                if self.encoding is None:
                    self.encoding = adjSettingsEncoding
                    if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
                        vPrint( 'Quiet', debuggingThisModule, _("__init__: Switched to {!r} file encoding").format( self.encoding ) )
                elif self.encoding == adjSettingsEncoding:
                    if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
                        vPrint( 'Quiet', debuggingThisModule, _("__init__: Confirmed {!r} file encoding").format( self.encoding ) )
                else: # we have a conflict of encodings for some reason !
                    logging.critical( _("__init__: We were already set to  {!r} file encoding").format( self.encoding ) )
                    self.encoding = adjSettingsEncoding
                    logging.critical( _("__init__: Switched now to  {!r} file encoding").format( self.encoding ) )

        elif applyMetadataType == 'uW':
            # This is a special case (coz it's inside 'Manifest' inside the uW metadata)
            if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>3:
                vPrint( 'Quiet', debuggingThisModule, "applySuppliedMetadata is processing {} {!r} metadata items".format( len(self.suppliedMetadata['uW']['Manifest']), applyMetadataType ) )
                assert len(self.suppliedMetadata['uW']['Manifest']) >= 3
                assert 'dublin_core' in self.suppliedMetadata['uW']['Manifest']
                assert 'checking' in self.suppliedMetadata['uW']['Manifest']
                assert 'projects' in self.suppliedMetadata['uW']['Manifest']
                assert isinstance( self.suppliedMetadata['uW']['Manifest']['dublin_core'], dict )
                assert isinstance( self.suppliedMetadata['uW']['Manifest']['checking'], dict )
                assert isinstance( self.suppliedMetadata['uW']['Manifest']['projects'], list )
            manifestDict = self.suppliedMetadata['uW']['Manifest']
            dublinCoreDict = manifestDict['dublin_core']
            projectsList = manifestDict['projects']
            # Where exactly should we be putting this stuff ???
            self.settingsDict['FullName'] = self.Workname = self.Name= self.ProjectName = dublinCoreDict['title']
            self.settingsDict['Abbreviation'] = dublinCoreDict['identifier'].upper()
            self.settingsDict['Creator'] = dublinCoreDict['creator']
            self.settingsDict['Rights'] = dublinCoreDict['rights']
            self.settingsDict['Language'] = dublinCoreDict['language']['title']
            self.settingsDict['ISOLanguageCode'] = dublinCoreDict['language']['identifier']
            self.settingsDict['Publisher'] = dublinCoreDict['publisher']
            self.encoding = 'utf-8'
            self.possibleFilenameDict = {}
            # dPrint( 'Info', debuggingThisModule, "projectsList", len(projectsList), projectsList )
            for bookDict in projectsList:
                # dPrint( 'Info', debuggingThisModule, "bookDict", len(bookDict), bookDict )
                USFMBookCode = bookDict['identifier']
                if USFMBookCode == 'obs':
                    BBB = 'OBS' # Special case
                    contentPath = bookDict['path']
                    assert contentPath == './content' # No need to save this here
                else:
                    BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromUSFMAbbreviation( USFMBookCode )
                    filename = bookDict['path']
                    if filename.startswith( './' ): filename = filename[2:]
                    self.possibleFilenameDict[BBB] = filename
                self.givenBookList.append( BBB )
                self.availableBBBs.add( BBB )

        elif applyMetadataType == 'OSIS':
            # Available fields include: Version, Creator, Contributor, Subject, Format, Type, Identifier, Source,
            #                           Publisher, Scope, Coverage, RefSystem, Language, Rights
            # dPrint( 'Quiet', debuggingThisModule, "here3450", self.suppliedMetadata )
            wantedDict = { 'Rights':'Rights', }
            if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>3:
                vPrint( 'Quiet', debuggingThisModule, "applySuppliedMetadata is processing {} {!r} metadata items".format( len(self.suppliedMetadata[applyMetadataType]), applyMetadataType ) )
            # dPrint( 'Quiet', debuggingThisModule, "here3452", self.suppliedMetadata[applyMetadataType] )
            for oldKey,value in self.suppliedMetadata[applyMetadataType].items():
                if oldKey in wantedDict: #  Only copy wanted entries
                    if BibleOrgSysGlobals.debugFlag: assert value
                    newKey = wantedDict[oldKey]
                    if newKey in self.settingsDict: # We have a duplicate
                        logging.warning("About to replace {}={!r} from {} metadata file with {!r}".format( newKey, self.settingsDict[newKey], applyMetadataType, value ) )
                    else: # Also check for "duplicates" with a different case
                        ucNewKey = newKey.upper()
                        for key in self.settingsDict:
                            ucKey = key.upper()
                            if ucKey == ucNewKey:
                                logging.warning("About to copy {}={!r} from {} metadata file even though already have {!r} (different case)={!r}".format( newKey, value, applyMetadataType, key, self.settingsDict[key] ) )
                                break
                    self.settingsDict[newKey] = value

        elif applyMetadataType == 'MyBible':
            # Available fields include: Version, Creator, Contributor, Subject, Format, Type, Identifier, Source,
            #                           Publisher, Scope, Coverage, RefSystem, Language, Rights
            wantedDict = { 'language':'Language', 'description':'FullName', 'detailed_info':'Description' }
            if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>3:
                vPrint( 'Quiet', debuggingThisModule, "applySuppliedMetadata is processing {} {!r} metadata items".format( len(self.suppliedMetadata[applyMetadataType]), applyMetadataType ) )
            for oldKey,value in self.suppliedMetadata[applyMetadataType].items():
                if oldKey in wantedDict: #  Only copy wanted entries
                    if BibleOrgSysGlobals.debugFlag: assert value
                    newKey = wantedDict[oldKey]
                    if newKey in self.settingsDict: # We have a duplicate
                        logging.warning("About to replace {}={!r} from {} metadata file with {!r}".format( newKey, self.settingsDict[newKey], applyMetadataType, value ) )
                    else: # Also check for "duplicates" with a different case
                        ucNewKey = newKey.upper()
                        for key in self.settingsDict:
                            ucKey = key.upper()
                            if ucKey == ucNewKey:
                                logging.warning("About to copy {}={!r} from {} metadata file even though already have {!r} (different case)={!r}".format( newKey, value, applyMetadataType, key, self.settingsDict[key] ) )
                                break
                    self.settingsDict[newKey] = value
            #dPrint( 'Quiet', debuggingThisModule, self.settingsDict ); halt

        elif applyMetadataType in ( 'e-Sword-Bible', 'e-Sword-Commentary', 'MySword' ):
            # Available fields include: Abbreviation, Apocrypha, Comments, Description, Font, NT, OT,
            #                           RightToLeft, Strong, Version
            wantedDict = { 'Abbreviation':'Abbreviation', 'Description':'Description', }
            if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>3:
                vPrint( 'Quiet', debuggingThisModule, "applySuppliedMetadata is processing {} {!r} metadata items".format( len(self.suppliedMetadata[applyMetadataType]), applyMetadataType ) )
            for oldKey,value in self.suppliedMetadata[applyMetadataType].items():
                if oldKey in wantedDict: #  Only copy wanted entries
                    if not value: # We don't expect blank metadata values
                        logging.warning( "Why did we get a blank {} {!r} metadata key?".format( applyMetadataType, oldKey ) )
                    newKey = wantedDict[oldKey]
                    if newKey in self.settingsDict: # We have a duplicate
                        logging.warning("About to replace {}={!r} from {} metadata file with {!r}".format( newKey, self.settingsDict[newKey], applyMetadataType, value ) )
                    else: # Also check for "duplicates" with a different case
                        ucNewKey = newKey.upper()
                        for key in self.settingsDict:
                            ucKey = key.upper()
                            if ucKey == ucNewKey:
                                logging.warning("About to copy {}={!r} from {} metadata file even though already have {!r} (different case)={!r}".format( newKey, value, applyMetadataType, key, self.settingsDict[key] ) )
                                break
                    self.settingsDict[newKey] = value

        else:
            logging.critical( "Unknown {!r} metadata type given to applySuppliedMetadata".format( applyMetadataType ) )
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt

        if BibleOrgSysGlobals.debugFlag and debuggingThisModule and BibleOrgSysGlobals.verbosityLevel>3:
            vPrint( 'Quiet', debuggingThisModule, "Updated settings dict ({}):".format( len(self.settingsDict) ) )
            for key,value in sorted( self.settingsDict.items() ):
                vPrint( 'Quiet', debuggingThisModule, "  {} = {!r}".format( key, value ) )

        # Ensure that self.name and self.abbreviation are set
        for fieldName in ('FullName','WorkName','Name','ProjectName',):
            if fieldName in self.settingsDict: self.name = self.settingsDict[fieldName]; break
        if not self.name: self.name = self.givenName
        if self.sourceFilename and not self.name: self.name = os.path.basename( self.sourceFilename )
        if self.sourceFolder and not self.name: self.name = os.path.basename( str(self.sourceFolder)[:-1] ) # Remove the final slash
        if not self.name: self.name = self.objectTypeString + ' Bible'

        if not self.abbreviation: self.abbreviation = self.getSetting( 'Abbreviation' )
    # end of InternalBible.applySuppliedMetadata


    def getSetting( self, settingName:str ):
        """
        Given a setting name, tries to find a value for that setting.

        First it looks in self.settingsDict
            then in self.suppliedMetadata['File']
            then in self.suppliedMetadata[…].

        Returns None if nothing found.
        """
        fnPrint( debuggingThisModule, f"getSetting( {settingName} )" )
        #dPrint( 'Quiet', debuggingThisModule, "\nSettingsDict:", self.settingsDict )
        #dPrint( 'Quiet', debuggingThisModule, "\nSupplied Metadata:", self.suppliedMetadata )

        if self.settingsDict:
            try: return self.settingsDict[settingName]
            except KeyError: pass
        if self.suppliedMetadata:
            try: return self.suppliedMetadata['File'][settingName]
            except KeyError: pass
            for metadataType in self.suppliedMetadata:
                if settingName in self.suppliedMetadata[metadataType]:
                    return self.suppliedMetadata[metadataType][settingName]
    # end of InternalBible.getSetting


    def getAssumedBookName( self, BBB:str ):
        """
        Gets the assumed book name for the given book reference code.

        The assumedBookName defaults to the long book name from \toc1 field.
        """
        if BibleOrgSysGlobals.debugFlag: assert BBB in BibleOrgSysGlobals.loadedBibleBooksCodes
        #if BBB in self.BBBToNameDict: return self.BBBToNameDict[BBB] # What was this ???
        try: return self.books[BBB].assumedBookName
        except (KeyError, AttributeError): return None
    # end of InternalBible.getAssumedBookName


    def getLongTOCName( self, BBB:str ):
        """
        Gets the long table of contents book name for the given book reference code.
        """
        if BibleOrgSysGlobals.debugFlag: assert BBB in BibleOrgSysGlobals.loadedBibleBooksCodes
        try: return self.books[BBB].longTOCName
        except (KeyError, AttributeError): return None
    # end of InternalBible.getLongTOCName


    def getShortTOCName( self, BBB:str ):
        """Gets the short table of contents book name for the given book reference code."""
        if BibleOrgSysGlobals.debugFlag: assert BBB in BibleOrgSysGlobals.loadedBibleBooksCodes
        try: return self.books[BBB].shortTOCName
        except (KeyError, AttributeError): return None
    # end of InternalBible.getShortTOCName


    def getBooknameAbbreviation( self, BBB:str ):
        """Gets the book abbreviation for the given book reference code."""
        if BibleOrgSysGlobals.debugFlag: assert BBB in BibleOrgSysGlobals.loadedBibleBooksCodes
        try: return self.books[BBB].booknameAbbreviation
        except (KeyError, AttributeError): return None
    # end of InternalBible.getBooknameAbbreviation


    def getBookList( self ):
        """
        Returns a list of loaded book codes.
        """
        if BibleOrgSysGlobals.debugFlag and not self.loadedAllBooks:
            logging.critical( _("getBookList result is unreliable because all books not loaded!") )
        return [BBB for BBB in self.books]


    def stashBook( self, bookData ) -> None:
        """
        Save the Bible book into our Bible object
            and update our indexes.
        """
        fnPrint( debuggingThisModule, f"stashBook( {len(bookData)} )" )

        BBB = bookData.BBB
        if BBB in self.books: # already
            vPrint( 'Info', debuggingThisModule, _("stashBook: Already have"), self.getBookList() )
            import __main__
            #dPrint( 'Quiet', debuggingThisModule, "main file", __main__.__file__ )
            suppressErrorFlag = False
            try:
                if 'Biblelator' in __main__.__file__: # This is normal behaviour for a Bible editor
                    suppressErrorFlag = True
            except AttributeError: pass
            if not suppressErrorFlag:
                logging.critical( _("stashBook: stashing already stashed {} book!").format( BBB ) )
        self.books[BBB] = bookData
        self.availableBBBs.add( BBB )

        # Make up our book name dictionaries while we're at it
        assumedBookNames = bookData.getAssumedBookNames()
        for assumedBookName in assumedBookNames:
            self.BBBToNameDict[BBB] = assumedBookName
            assumedBookNameLower = assumedBookName.lower()
            self.bookNameDict[assumedBookNameLower] = BBB # Store the deduced book name (just lower case)
            self.combinedBookNameDict[assumedBookNameLower] = BBB # Store the deduced book name (just lower case)
            if ' ' in assumedBookNameLower: self.combinedBookNameDict[assumedBookNameLower.replace(' ','')] = BBB # Store the deduced book name (lower case without spaces)
    # end of InternalBible.stashBook


    def pickle( self, filename=None, folderpath=None ):
        """
        Writes the object to a .pickle file that can be easily loaded into a Python3 program.
            If folder is None (or missing), defaults to the default cache folder specified in BibleOrgSysGlobals.
            Created the folder(s) if necessary.

        Returns a True/False flag for success.
        """
        #dPrint( 'Quiet', debuggingThisModule, "pickle( *, {}, {} )".format( repr(filename), repr(folderpath ) ) )
        #dPrint( 'Quiet', debuggingThisModule, repr(self.objectNameString), repr(self.objectTypeString) )
        #dPrint( 'Quiet', debuggingThisModule, (self.abbreviation), repr(self.name) )
        if filename is None:
            filename = self.getAName( abbrevFirst=True )
        if filename is None:
            filename = self.objectTypeString
        if BibleOrgSysGlobals.debugFlag: assert filename
        filename = BibleOrgSysGlobals.makeSafeFilename( filename ) + '.pickle'
        vPrint( 'Info', debuggingThisModule, _("pickle: Saving {} to {}…") \
                .format( self.objectNameString, filename if folderpath is None else os.path.join( folderpath, filename ) ) )
        try: pResult = BibleOrgSysGlobals.pickleObject( self, filename, folderpath )
        except TypeError: # Could be a yet undebugged SWIG error
            pResult = False
            errorClass, exceptionInstance, traceback = sys.exc_info()
            #dPrint( 'Quiet', debuggingThisModule, '{!r}  {!r}  {!r}'.format( errorClass, exceptionInstance, traceback ) )
            if 'SwigPyObject' in str(exceptionInstance):
                logging.critical( _("SWIG binding error when pickling {} Bible") \
                    .format( self.getAName( abbrevFirst=True ) ) ) # Ignore errors
            else: # it's some other attribute error in the loadBook function
                raise
        return pResult
    # end of InternalBible.pickle


    def guessXRefBBB( self, referenceString:str ) -> str:
        """
        Attempt to return a book reference code given a book reference code (e.g., 'PRO'),
                a book name (e.g., Proverbs) or abbreviation (e.g., Prv).
            Uses self.combinedBookNameDict and makes and uses self.bookAbbrevDict.
            Return None if unsuccessful.
        """
        if BibleOrgSysGlobals.debugFlag: assert referenceString and isinstance( referenceString, str )
        result = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromText( referenceString )
        if result is not None: return result # It's already a valid BBB

        adjRefString = referenceString.lower()
        if adjRefString in self.combinedBookNameDict:
            BBB = self.combinedBookNameDict[adjRefString]
            #assert BBB not in self.reverseDict
            self.reverseDict[BBB] = referenceString
            return BBB # Found a whole name match
        if adjRefString in self.bookAbbrevDict:
            BBB = self.bookAbbrevDict[adjRefString]
            #dPrint( 'Quiet', debuggingThisModule, referenceString, adjRefString, BBB, self.reverseDict )
            #assert BBB not in self.reverseDict
            self.reverseDict[BBB] = referenceString
            return BBB # Found a whole abbreviation match

        # Do a program check
        for BBB in self.reverseDict: assert self.reverseDict[BBB] != referenceString

        # See if a book name starts with this string
        vPrint( 'Never', debuggingThisModule, "  getXRefBBB using startswith1…" )
        count = 0
        for bookName in self.bookNameDict:
            if bookName.startswith( adjRefString ):
                BBB = self.bookNameDict[bookName]
                count += 1
        if count == 1: # Found exactly one
            self.bookAbbrevDict[adjRefString] = BBB # Save to make it faster next time
            self.guesses += ('\n' if self.guesses else '') + "Guessed {!r} to be {} (startswith1)".format( referenceString, BBB )
            self.reverseDict[BBB] = referenceString
            return BBB
        elif count == 2: # Found exactly two but one of them might have a different abbreviation that we already know
            secondCount = 0
            for bookName in self.bookNameDict: # Gotta go through them all again now :(
                if bookName.startswith( adjRefString ):
                    BBBx = self.bookNameDict[bookName]
                    if BBBx not in self.reverseDict: BBB = BBBx; secondCount += 1
            if secondCount == 1: # Found exactly one
                self.bookAbbrevDict[adjRefString] = BBB # Save to make it faster next time
                self.guesses += ('\n' if self.guesses else '') + "Guessed {!r} to be {} (startswith1SECOND)".format( referenceString, BBB )
                self.reverseDict[BBB] = referenceString
                return BBB
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule and count > 1:
            vPrint( 'Quiet', debuggingThisModule, _("  guessXRefBBB has multiple startswith matches for {!r} in {}").format( adjRefString, self.combinedBookNameDict ) )
        if count == 0:
            vPrint( 'Never', debuggingThisModule, "  getXRefBBB using startswith2…" )
            for bookName in self.combinedBookNameDict:
                if bookName.startswith( adjRefString ):
                    BBB = self.combinedBookNameDict[bookName]
                    count += 1
            if count == 1: # Found exactly one now
                self.bookAbbrevDict[adjRefString] = BBB # Save to make it faster next time
                self.guesses += ('\n' if self.guesses else '') + "Guessed {!r} to be {} (startswith2)".format( referenceString, BBB )
                self.reverseDict[BBB] = referenceString
                return BBB
        elif count == 2: # Found exactly two but one of them might have a different abbreviation that we already know
            secondCount = 0
            for bookName in self.bookNameDict: # Gotta go through them all again now :(
                if bookName.startswith( adjRefString ):
                    BBBx = self.bookNameDict[bookName]
                    if BBBx not in self.reverseDict: BBB = BBBx; secondCount += 1
            if secondCount == 1: # Found exactly one now
                self.bookAbbrevDict[adjRefString] = BBB # Save to make it faster next time
                self.guesses += ('\n' if self.guesses else '') + "Guessed {!r} to be {} (startswith2SECOND)".format( referenceString, BBB )
                self.reverseDict[BBB] = referenceString
                return BBB

        # See if a book name contains a word that starts with this string
        if count == 0:
            vPrint( 'Never', debuggingThisModule, "  getXRefBBB using word startswith…" )
            for bookName in self.bookNameDict:
                if ' ' in bookName:
                    for bit in bookName.split():
                        if bit.startswith( adjRefString ):
                            BBB = self.bookNameDict[bookName]
                            count += 1
            if count == 1: # Found exactly one
                self.bookAbbrevDict[adjRefString] = BBB # Save to make it faster next time
                self.guesses += ('\n' if self.guesses else '') + "Guessed {!r} to be {} (word startswith)".format( referenceString, BBB )
                self.reverseDict[BBB] = referenceString
                return BBB
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule and count > 1:
                vPrint( 'Quiet', debuggingThisModule, _("  guessXRefBBB has multiple startswith matches for {!r} in {}").format( adjRefString, self.bookNameDict ) )

        # See if a book name starts with the same letter plus contains the letters in this string (slow)
        if count == 0:
            vPrint( 'Never', debuggingThisModule, _("  guessXRefBBB using first plus other characters…") )
            for bookName in self.bookNameDict:
                if not bookName: vPrint( 'Quiet', debuggingThisModule, self.bookNameDict ); halt # temp……
                #dPrint( 'Quiet', debuggingThisModule, "aRS={!r}, bN={!r}".format( adjRefString, bookName ) )
                if adjRefString[0] != bookName[0]: continue # The first letters don't match
                found = True
                for char in adjRefString[1:]:
                    if char not in bookName[1:]: # We could also check that they're in the correct order…might give less ambiguities???
                        found = False
                        break
                if not found: continue
                #dPrint( 'Quiet', debuggingThisModule, "  getXRefBBB: p…", bookName )
                BBB = self.bookNameDict[bookName]
                count += 1
            if count == 1: # Found exactly one
                self.bookAbbrevDict[adjRefString] = BBB # Save to make it faster next time
                self.guesses += ('\n' if self.guesses else '') + "Guessed {!r} to be {} (firstletter+)".format( referenceString, BBB )
                return BBB
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule and count > 1:
                vPrint( 'Quiet', debuggingThisModule, _("  guessXRefBBB has first and other character multiple matches for {!r} in {}").format( adjRefString, self.bookNameDict ) )

        if 0: # Too error prone!!!
            # See if a book name contains the letters in this string (slow)
            if count == 0:
                vPrint( 'Never', debuggingThisModule, "  getXRefBBB using characters…" )
                for bookName in self.bookNameDict:
                    found = True
                    for char in adjRefString:
                        if char not in bookName: # We could also check that they're in the correct order…might give less ambiguities???
                            found = False
                            break
                    if not found: continue
                    #dPrint( 'Quiet', debuggingThisModule, "  getXRefBBB: q…", bookName )
                    BBB = self.bookNameDict[bookName]
                    count += 1
                if count == 1: # Found exactly one
                    self.bookAbbrevDict[adjRefString] = BBB # Save to make it faster next time
                    self.guesses += ('\n' if self.guesses else '') + "Guessed {!r} to be {} (letters)".format( referenceString, BBB )
                    return BBB
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule and count > 1:
                    vPrint( 'Quiet', debuggingThisModule, _("  guessXRefBBB has character multiple matches for {!r} in {}").format( adjRefString, self.bookNameDict ) )

        if BibleOrgSysGlobals.debugFlag and debuggingThisModule or BibleOrgSysGlobals.verbosityLevel>2:
            vPrint( 'Quiet', debuggingThisModule, _("  guessXRefBBB failed for {!r} with {} and {}").format( referenceString, self.bookNameDict, self.bookAbbrevDict ) )
        string = "Couldn't guess {!r}".format( referenceString[:5] )
        if string not in self.guesses: self.guesses += ('\n' if self.guesses else '') + string
    # end of InternalBible.guessXRefBBB


    def getVersification( self ):
        """
        Get the versification of the Bible into four ordered dictionaries with the referenceAbbreviation as key.
            Entries in both are lists of tuples, being (c, v).
            The first list contains an entry for each chapter in the book showing the number of verses.
            The second list contains an entry for each missing verse in the book (not including verses that are missing at the END of a chapter).
            The third list contains an entry for combined verses in the book.
            The fourth list contains an entry for reordered verses in the book.
        """
        if BibleOrgSysGlobals.debugFlag: assert self.books
        totalVersification, totalOmittedVerses, totalCombinedVerses, totalReorderedVerses = {}, {}, {}, {}
        for BBB in self.books.keys():
            versification, omittedVerses, combinedVerses, reorderedVerses = self.books[BBB].getVersification()
            totalVersification[BBB] = versification
            if omittedVerses: totalOmittedVerses[BBB] = omittedVerses # Only add an entry if there are some
            if combinedVerses: totalCombinedVerses[BBB] = combinedVerses
            if reorderedVerses: totalReorderedVerses[BBB] = reorderedVerses
        return totalVersification, totalOmittedVerses, totalCombinedVerses, totalReorderedVerses
    # end of InternalBible.getVersification


    def getAddedUnits( self ):
        """
        Get the added units in the Bible text, such as section headings, paragraph breaks, and section references.
        """
        if BibleOrgSysGlobals.debugFlag: assert self.books
        haveParagraphs = haveQParagraphs = haveSectionHeadings = haveSectionReferences = haveWordsOfJesus = False
        AllParagraphs, AllQParagraphs, AllSectionHeadings, AllSectionReferences, AllWordsOfJesus = {}, {}, {}, {}, {}
        for BBB in self.books:
            paragraphReferences, qReferences, sectionHeadings, sectionReferences, wordsOfJesus = self.books[BBB].getAddedUnits()
            if paragraphReferences: haveParagraphs = True
            AllParagraphs[BBB] = paragraphReferences # Add an entry for each given book, even if the entry is blank
            if qReferences: haveQParagraphs = True
            AllQParagraphs[BBB] = qReferences
            if sectionHeadings: haveSectionHeadings = True
            AllSectionHeadings[BBB] = sectionHeadings
            if sectionReferences: haveSectionReferences = True
            AllSectionReferences[BBB] = sectionReferences
            if wordsOfJesus: haveWordsOfJesus = True
            AllWordsOfJesus[BBB] = wordsOfJesus
        # If a version lacks a feature completely, return None (rather than an empty dictionary)
        return AllParagraphs if haveParagraphs else None, AllQParagraphs if haveQParagraphs else None, AllSectionHeadings if haveSectionHeadings else None, AllSectionReferences if haveSectionReferences else None, AllWordsOfJesus if haveWordsOfJesus else None
    # end of InternalBible.getAddedUnits


    # def _discoverBookMP( self, BBB:str ):
    #     """
    #     """
    #     # TODO: Make this a lambda function
    #     return self.books[BBB]._discover()
    # # end of _discoverBookMP

    def discover( self ) -> None:
        """
        Runs a series of checks and count on each book of the Bible
            in order to try to determine what are the normal standards.
        """
        fnPrint( debuggingThisModule, "InternalBible:discover()" )
        if 'discoveryResults' in self.__dict__:
            logging.warning( _("discover: We had done this already!") )
            if debuggingThisModule: halt

        self.discoveryResults = {}

        # Get our recommendations for added units -- only load this once per Bible
        #import pickle
        #folder = os.path.join( os.path.dirname(__file__), 'DataFiles/', 'ScrapedFiles/' ) # Relative to module, not cwd
        #filepath = os.path.join( folder, "AddedUnitData.pickle" )
        #dPrint( 'Verbose', debuggingThisModule, _("Importing from {}…").format( filepath ) )
        #with open( filepath, 'rb' ) as pickleFile:
        #    typicalAddedUnits = pickle.load( pickleFile ) # The protocol version used is detected automatically, so we do not have to specify it

        vPrint( 'Info', debuggingThisModule, _("Running discover on {}…").format( self.name ) )
        # NOTE: We can't pickle sqlite3.Cursor objects so can not use multiprocessing here for e-Sword Bibles or commentaries
        # NOTE: Multiprocessing discover is considerably slower, hence disabled
        #           68 books 12 sec, but multithreaded 16s using 67s of processing!!!
        if 0 and self.objectTypeString not in ('CrosswireSword','e-Sword-Bible','e-Sword-Commentary','MyBible') \
        and BibleOrgSysGlobals.maxProcesses > 1 \
        and not BibleOrgSysGlobals.alreadyMultiprocessing: # Check all the books as quickly as possible
            BibleOrgSysGlobals.alreadyMultiprocessing = True
            vPrint( 'Normal', debuggingThisModule, _("Prechecking/“discover” {} books using {} processes…").format( len(self.books), BibleOrgSysGlobals.maxProcesses ) )
            vPrint( 'Normal', debuggingThisModule, "  NOTE: Outputs (including error and warning messages) from scanning various books may be interspersed." )
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.map( self._discoverBookMP, [BBB for BBB in self.books] ) # have the pool do our loads
                assert len(results) == len(self.books)
                for j,BBB in enumerate( self.books ):
                    self.discoveryResults[BBB] = results[j] # Saves them in the correct order
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            for BBB in self.books: # Do individual book prechecks
                vPrint( 'Verbose', debuggingThisModule, "  " + _("Prechecking {}…").format( BBB ) )
                self.discoveryResults[BBB] = self.books[BBB]._discover()

        if self.objectTypeString == 'PTX8':
            self.discoverPTX8()

        self.__aggregateDiscoveryResults()
        if 'uWaligned' in self.__dict__ and self.uWaligned:
            self.__aggregateAlignmentResults()
    # end of InternalBible.discover


    def __aggregateDiscoveryResults( self ):
        """
        Assuming that the individual discoveryResults have been collected for each book,
            puts them all together.
        """
        fnPrint( debuggingThisModule, "InternalBible:__aggregateDiscoveryResults()" )
        aggregateResults = {}
        if BibleOrgSysGlobals.debugFlag: assert 'ALL' not in self.discoveryResults
        for BBB in self.discoveryResults:
            #dPrint( 'Quiet', debuggingThisModule, "discoveryResults for", BBB, len(self.discoveryResults[BBB]), self.discoveryResults[BBB] )
            isOT = isNT = isDC = False
            if BibleOrgSysGlobals.loadedBibleBooksCodes.isOldTestament_NR( BBB ):
                isOT = True
                if 'OTBookCount' not in aggregateResults: aggregateResults['OTBookCount'], aggregateResults['OTBookCodes'] = 1, [BBB]
                else: aggregateResults['OTBookCount'] += 1; aggregateResults['OTBookCodes'].append( BBB )
            elif BibleOrgSysGlobals.loadedBibleBooksCodes.isNewTestament_NR( BBB ):
                isNT = True
                if 'NTBookCount' not in aggregateResults: aggregateResults['NTBookCount'], aggregateResults['NTBookCodes'] = 1, [BBB]
                else: aggregateResults['NTBookCount'] += 1; aggregateResults['NTBookCodes'].append( BBB )
            elif BibleOrgSysGlobals.loadedBibleBooksCodes.isDeuterocanon_NR( BBB ):
                isDC = True
                if 'DCBookCount' not in aggregateResults: aggregateResults['DCBookCount'], aggregateResults['DCBookCodes'] = 1, [BBB]
                else: aggregateResults['DCBookCount'] += 1; aggregateResults['DCBookCodes'].append( BBB )
            else: # not conventional OT or NT or DC
                if 'OtherBookCount' not in aggregateResults: aggregateResults['OtherBookCount'], aggregateResults['OtherBookCodes'] = 1, [BBB]
                else: aggregateResults['OtherBookCount'] += 1; aggregateResults['OtherBookCodes'].append( BBB )

            for key,value in self.discoveryResults[BBB].items():
                # Create some lists of books
                #if key == 'wordCount': vPrint( 'Quiet', debuggingThisModule, BBB, key, value )
                if key=='notStarted' and value:
                    if 'NotStartedBookCodes' not in aggregateResults: aggregateResults['NotStartedBookCodes'] = [BBB]
                    else: aggregateResults['NotStartedBookCodes'].append( BBB )
                    if isOT:
                        if 'OTNotStartedBookCodes' not in aggregateResults: aggregateResults['OTNotStartedBookCodes'] = [BBB]
                        else: aggregateResults['OTNotStartedBookCodes'].append( BBB )
                    elif isNT:
                        if 'NTNotStartedBookCodes' not in aggregateResults: aggregateResults['NTNotStartedBookCodes'] = [BBB]
                        else: aggregateResults['NTNotStartedBookCodes'].append( BBB )
                    elif isDC:
                        if 'DCNotStartedBookCodes' not in aggregateResults: aggregateResults['DCNotStartedBookCodes'] = [BBB]
                        else: aggregateResults['DCNotStartedBookCodes'].append( BBB )
                elif key=='seemsFinished' and value:
                    if 'SeemsFinishedBookCodes' not in aggregateResults: aggregateResults['SeemsFinishedBookCodes'] = [BBB]
                    else: aggregateResults['SeemsFinishedBookCodes'].append( BBB )
                    if isOT:
                        if 'OTSeemsFinishedBookCodes' not in aggregateResults: aggregateResults['OTSeemsFinishedBookCodes'] = [BBB]
                        else: aggregateResults['OTSeemsFinishedBookCodes'].append( BBB )
                    elif isNT:
                        if 'NTSeemsFinishedBookCodes' not in aggregateResults: aggregateResults['NTSeemsFinishedBookCodes'] = [BBB]
                        else: aggregateResults['NTSeemsFinishedBookCodes'].append( BBB )
                    elif isDC:
                        if 'DCSeemsFinishedBookCodes' not in aggregateResults: aggregateResults['DCSeemsFinishedBookCodes'] = [BBB]
                        else: aggregateResults['DCSeemsFinishedBookCodes'].append( BBB )
                elif key=='partlyDone' and value:
                    if 'PartlyDoneBookCodes' not in aggregateResults: aggregateResults['PartlyDoneBookCodes'] = [BBB]
                    else: aggregateResults['PartlyDoneBookCodes'].append( BBB )
                    if isOT:
                        if 'OTPartlyDoneBookCodes' not in aggregateResults: aggregateResults['OTPartlyDoneBookCodes'] = [BBB]
                        else: aggregateResults['OTPartlyDoneBookCodes'].append( BBB )
                    elif isNT:
                        if 'NTPartlyDoneBookCodes' not in aggregateResults: aggregateResults['NTPartlyDoneBookCodes'] = [BBB]
                        else: aggregateResults['NTPartlyDoneBookCodes'].append( BBB )
                    elif isDC:
                        if 'DCPartlyDoneBookCodes' not in aggregateResults: aggregateResults['DCPartlyDoneBookCodes'] = [BBB]
                        else: aggregateResults['DCPartlyDoneBookCodes'].append( BBB )

                # Aggregate book statistics into a whole
                if key == 'percentageProgress':
                    if 'percentageProgressByBook' not in aggregateResults: aggregateResults['percentageProgressByBook'] = value
                    else: aggregateResults['percentageProgressByBook'] += value
                    if isOT:
                        if 'OTpercentageProgressByBook' not in aggregateResults: aggregateResults['OTpercentageProgressByBook'] = value
                        else: aggregateResults['OTpercentageProgressByBook'] += value
                    elif isNT:
                        if 'NTpercentageProgressByBook' not in aggregateResults: aggregateResults['NTpercentageProgressByBook'] = value
                        else: aggregateResults['NTpercentageProgressByBook'] += value
                    elif isDC:
                        if 'DCpercentageProgressByBook' not in aggregateResults: aggregateResults['DCpercentageProgressByBook'] = value
                        else: aggregateResults['DCpercentageProgressByBook'] += value
                    #dPrint( 'Quiet', debuggingThisModule, 'xxx', value, aggregateResults['percentageProgressByBook'] )
                elif key == 'uniqueWordCount': pass # Makes no sense to aggregate this
                elif key.endswith( 'WordCounts' ): # We need to combine these word count dictionaries
                    #dPrint( 'Quiet', debuggingThisModule, "wcGot", BBB, key )
                    if key not in aggregateResults: aggregateResults[key] = {}
                    assert isinstance( value, dict )
                    for word in value:
                        assert isinstance( word, str )
                        assert isinstance( value[word], int )
                        if word not in aggregateResults[key]: aggregateResults[key][word] = 0
                        aggregateResults[key][word] += value[word]
                elif isinstance( value, float ): # e.g., crossReferencesPeriodRatio
                    #dPrint( 'Quiet', debuggingThisModule, "fgot", BBB, key, value )
                    if 0.0 <= value <= 1.0:
                        if key not in aggregateResults: aggregateResults[key] = [value]
                        else: aggregateResults[key].append( value )
                    elif value != -1.0: logging.warning( _("discover: invalid ratio (float) {} {} {!r}").format( BBB, key, value ) )
                elif isinstance( value, int ): # e.g., completedVerseCount and also booleans such as havePopulatedCVmarkers
                    #dPrint( 'Quiet', debuggingThisModule, "igot", BBB, key, value )
                    if key not in aggregateResults: aggregateResults[key] = value
                    else: aggregateResults[key] += value
                    if isOT:
                        if 'OT'+key not in aggregateResults: aggregateResults['OT'+key] = value
                        else: aggregateResults['OT'+key] += value
                    elif isNT:
                        if 'NT'+key not in aggregateResults: aggregateResults['NT'+key] = value
                        else: aggregateResults['NT'+key] += value
                    elif isDC:
                        if 'DC'+key not in aggregateResults: aggregateResults['DC'+key] = value
                        else: aggregateResults['DC'+key] += value
                    else: # front-back matter
                        if 'OTHER'+key not in aggregateResults: aggregateResults['OTHER'+key] = value
                        else: aggregateResults['OTHER'+key] += value
                #elif value==True: # This test must come below the isinstance tests
                    #dPrint( 'Quiet', debuggingThisModule, "tgot", BBB, key, value ); halt
                    #if key not in aggregateResults: aggregateResults[key] = 1
                    #else: aggregateResults[key] += 1
                    #if isOT:
                        #if 'OT'+key not in aggregateResults: aggregateResults['OT'+key] = 1
                        #else: aggregateResults['OT'+key] += 1
                    #elif isNT:
                        #if 'NT'+key not in aggregateResults: aggregateResults['NT'+key] = 1
                        #else: aggregateResults['NT'+key] += 1
                    #elif isDC:
                        #if 'DC'+key not in aggregateResults: aggregateResults['DC'+key] = 1
                        #else: aggregateResults['DC'+key] += 1
                #elif value==False:
                    #halt
                    #pass # No action needed here
                else:
                    logging.warning( _("discover: unactioned discovery result {} {} {!r}").format( BBB, key, value ) )

        for arKey in list(aggregateResults.keys()): # Make a list first so we can delete entries later
            # Create summaries of lists with entries for various books
            #dPrint( 'Quiet', debuggingThisModule, "check", arKey, aggregateResults[arKey] )
            if isinstance( aggregateResults[arKey], list ) and isinstance( aggregateResults[arKey][0], float ):
                if BibleOrgSysGlobals.debugFlag: assert arKey.endswith( 'Ratio' )
                #dPrint( 'Quiet', debuggingThisModule, "this", arKey, aggregateResults[arKey] )
                aggregateRatio = round( sum( aggregateResults[arKey] ) / len( aggregateResults[arKey] ), 2 )
                aggregateFlag = None
                if aggregateRatio > 0.6: aggregateFlag = True
                if aggregateRatio < 0.4: aggregateFlag = False
                #dPrint( 'Quiet', debuggingThisModule, "now", arKey, aggregateResults[arKey] )
                del aggregateResults[arKey] # Get rid of the ratio
                aggregateResults[arKey[:-5]+'Flag'] = aggregateFlag

        # Now calculate our overall statistics
        #dPrint( 'Quiet', debuggingThisModule, "pre-aggregateResults", len(self), len(aggregateResults), aggregateResults )
        if 'percentageProgressByBook' in aggregateResults:
            aggregateResults['percentageProgressByBook'] = str( round( aggregateResults['percentageProgressByBook'] / len(self) ) ) + '%'
        if 'OTpercentageProgressByBook' in aggregateResults:
            aggregateResults['OTpercentageProgressByBook'] = str( round( aggregateResults['OTpercentageProgressByBook'] / 39 ) ) + '%'
        if 'NTpercentageProgressByBook' in aggregateResults:
            aggregateResults['NTpercentageProgressByBook'] = str( round( aggregateResults['NTpercentageProgressByBook'] / 27 ) ) + '%'
        if 'DCpercentageProgressByBook' in aggregateResults:
            aggregateResults['DCpercentageProgressByBook'] = str( round( aggregateResults['DCpercentageProgressByBook'] / 15 ) ) + '%'
        if 'completedVerseCount' in aggregateResults and 'verseCount' in aggregateResults:
            aggregateResults['percentageProgressByVerse'] = str( round( aggregateResults['completedVerseCount'] * 100 / aggregateResults['verseCount'] ) ) + '%'
        if 'OTcompletedVerseCount' in aggregateResults and 'OTverseCount' in aggregateResults:
            aggregateResults['OTpercentageProgressByVerse'] = str( round( aggregateResults['OTcompletedVerseCount'] * 100 / aggregateResults['OTverseCount'] ) ) + '%'
        if 'NTcompletedVerseCount' in aggregateResults and 'NTverseCount' in aggregateResults:
            aggregateResults['NTpercentageProgressByVerse'] = str( round( aggregateResults['NTcompletedVerseCount'] * 100 / aggregateResults['NTverseCount'] ) ) + '%'
        if 'DCcompletedVerseCount' in aggregateResults and 'DCverseCount' in aggregateResults:
            aggregateResults['DCpercentageProgressByVerse'] = str( round( aggregateResults['DCcompletedVerseCount'] * 100 / aggregateResults['DCverseCount'] ) ) + '%'

        # Save the results
        #dPrint( 'Quiet', debuggingThisModule, "ALL discoveryResults", aggregateResults ); halt
        #for key,value in aggregateResults.items():
            #if key.endswith( 'ordCount' ): vPrint( 'Quiet', debuggingThisModule, key, value )
        self.discoveryResults['ALL'] = aggregateResults

        if BibleOrgSysGlobals.verbosityLevel > 2: # or self.name=="Matigsalug": # Display some of these results
            vPrint( 'Quiet', debuggingThisModule, "Discovered Bible parameters:" )
            if BibleOrgSysGlobals.verbosityLevel > 2: # or self.name=="Matigsalug": # Print completion level for each book
                for BBB in self.discoveryResults:
                    if BBB != 'ALL':
                        if 'seemsFinished' in self.discoveryResults[BBB] and self.discoveryResults[BBB]['seemsFinished']:
                            vPrint( 'Quiet', debuggingThisModule, "   ", BBB, 'seems finished' ) #, str(self.discoveryResults[BBB]['percentageProgress'])+'%' )
                        elif not self.discoveryResults[BBB]['haveVerseText']:
                            vPrint( 'Quiet', debuggingThisModule, "   ", BBB, 'not started' ) #, str(self.discoveryResults[BBB]['percentageProgress'])+'%' )
                        else: vPrint( 'Quiet', debuggingThisModule, "   ", BBB, 'in progress', (str(self.discoveryResults[BBB]['percentageProgress'])+'%') if 'percentageProgress' in self.discoveryResults[BBB] else '' )
            for key,value in sorted(self.discoveryResults['ALL'].items()):
                if 'percentage' in key or key.endswith('Count') or key.endswith('Flag') or key.endswith('Codes'):
                    vPrint( 'Quiet', debuggingThisModule, " ", key, "is", value )
                elif key.endswith( 'WordCounts' ): pass # ignore these
                else:
                    #dPrint( 'Quiet', debuggingThisModule, "key", repr(key), "value", repr(value) )
                    vPrint( 'Quiet', debuggingThisModule, " ", key, "in", value if value<len(self) else "all", "books" )
        # dPrint( 'Info', debuggingThisModule, f"  __aggregateDiscoveryResults() finished." )
    # end of InternalBible.__aggregateDiscoveryResults


    # def _makeBookSectionIndexMP( self, BBB:str ):
    #     """
    #     """
    #     # TODO: Make this a lambda function
    #     return self.books[BBB]._makeBookSectionIndex()
    # # end of _makeBookSectionIndexMP

    def makeSectionIndex( self ):
        """
        Runs self.discover() first if necessary.

        Creates an index for each book of the Bible.
        """
        # Get our recommendations for added units -- only load this once per Bible
        fnPrint( debuggingThisModule, f"makeSectionIndex() for {self.name} Bible" )
        # dPrint( 'Info', debuggingThisModule, "makeSectionIndex1", id(self) )
        assert self.books
        # assert len(self.books) == 68
        assert 'discoveryResults' in self.__dict__

        self.sectionIndex = {}

        vPrint( 'Info', debuggingThisModule, _("Running makeSectionIndex on {}…").format( self.name ) )
        # NOTE: We can't pickle sqlite3.Cursor objects so can not use multiprocessing here for e-Sword Bibles or commentaries
        # NOTE: Multiprocessing index build is considerably slower, hence disabled
        if 0 and BibleOrgSysGlobals.maxProcesses > 1 \
        and not BibleOrgSysGlobals.alreadyMultiprocessing:
            BibleOrgSysGlobals.alreadyMultiprocessing = True
            vPrint( 'Normal', debuggingThisModule, _("Making section index for {} books using {} processes…").format( len(self.books), BibleOrgSysGlobals.maxProcesses ) )
            vPrint( 'Normal', debuggingThisModule, "  NOTE: Outputs (including error and warning messages) from scanning various books may be interspersed." )
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.map( self._makeBookSectionIndexMP, [BBB for BBB in self.books] ) # have the pool do our loads
                assert len(results) == len(self.books)
                for j,BBB in enumerate( self.books ):
                    self.sectionIndex[BBB] = results[j] # Saves them in the correct order
                assert len(self.sectionIndex) == len(self.books)
            # assert len(self.books) == 68
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            from BibleOrgSys.Bible import Bible
            # dPrint( 'Info', debuggingThisModule, "makeSectionIndex2", id(self) )
            for BBB,bookObject in self.books.items(): # Make individual book section indexes
                vPrint( 'Verbose', debuggingThisModule, "  " + f"Making section index for {BBB}…" )
                assert isinstance( bookObject.containerBibleObject, Bible )
                # dPrint( 'Info', debuggingThisModule, "makeSectionIndex", BBB, id(bookObject.containerBibleObject) )
                assert bookObject.containerBibleObject.books
                # assert len(bookObject.containerBibleObject.books) == 68
                self.sectionIndex[BBB] = bookObject._makeBookSectionIndex()
            assert len(self.sectionIndex) == len(self.books)
        # assert len(self.books) == 68
    # end of InternalBible.makeSectionIndex()


    def check( self, givenBookList=None ):
        """
        Runs self.discover() first if necessary.

        By default, runs a series of individual checks (and counts) on each book of the Bible
            and then a number of overall checks on the entire Bible.

        If a book list is given, only checks those books.

        getCheckResults() must be called to request the results.
        """
        # Get our recommendations for added units -- only load this once per Bible
        if BibleOrgSysGlobals.verbosityLevel > 1:
            if givenBookList is None: vPrint( 'Quiet', debuggingThisModule, _("Checking {} Bible…").format( self.name ) )
            else: vPrint( 'Quiet', debuggingThisModule, _("Checking {} Bible books {}…").format( self.name, givenBookList ) )
        if 'discoveryResults' not in self.__dict__: self.discover()

        import pickle
        pickleFolder = os.path.join( os.path.dirname(__file__), 'DataFiles/', 'ScrapedFiles/' ) # Relative to module, not cwd
        pickleFilepath = os.path.join( pickleFolder, "AddedUnitData.pickle" )
        vPrint( 'Verbose', debuggingThisModule, _("Importing from {}…").format( pickleFilepath ) )
        try:
            with open( pickleFilepath, 'rb' ) as pickleFile:
                typicalAddedUnitData = pickle.load( pickleFile ) # The protocol version used is detected automatically, so we do not have to specify it
        except FileNotFoundError:
                logging.error( "InternalBible.check: Unable to find file for typical added units checks: {}".format( pickleFilepath ) )
                typicalAddedUnitData = None

        if BibleOrgSysGlobals.debugFlag: assert self.discoveryResults
        vPrint( 'Info', debuggingThisModule, _("Running checks on {}…").format( self.name ) )
        if givenBookList is None:
            givenBookList = self.books.keys()
        for BBB in givenBookList: # Do individual book checks
            vPrint( 'Info', debuggingThisModule, "  " + _("Checking {}…").format( BBB ) )
            self.books[BBB].checkBook( self.discoveryResults['ALL'], typicalAddedUnitData )

        # Do overall Bible checks here
        # xxxxxxxxxxxxxxxxx …
    # end of InternalBible.check


    def doExtensiveChecks( self, givenOutputFolderName=None, ntFinished=None, otFinished=None, dcFinished=None, allFinished=None ):
        """
        If the output folder is specified, it is expected that it's already created.
        Otherwise a new subfolder is created in the current folder.

        The optional flags (None means 'unknown') give indications if books should actually be finished.

        Returns a dictionary of result flags.
        """
        fnPrint( debuggingThisModule, f"InternalBible-V{PROGRAM_VERSION}.doExtensiveChecks: " + _("Doing extensive checks on {} ({})").format( self.name, self.objectTypeString ) )

        if givenOutputFolderName is None:
            givenOutputFolderName = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'CheckResultFiles/' )
            if not os.access( givenOutputFolderName, os.F_OK ):
                if 1 or BibleOrgSysGlobals.verbosityLevel > 2: vPrint( 'Quiet', debuggingThisModule, "BibleWriter.doExtensiveChecks: " + _("creating {!r} output folder").format( givenOutputFolderName ) )
                os.makedirs( givenOutputFolderName ) # Make the empty folder if there wasn't already one there
        if BibleOrgSysGlobals.debugFlag:
            assert givenOutputFolderName and isinstance( givenOutputFolderName, (str,Path) )
        if not os.access( givenOutputFolderName, os.W_OK ): # Then our output folder is not writeable!
            logging.critical( "BibleWriter.doExtensiveChecks: " + _("Given {!r} folder is unwritable" ).format( givenOutputFolderName ) )
            return False

        vPrint( 'Quiet', debuggingThisModule, "Should be doing extensive checks here!" )
        vPrint( 'Quiet', debuggingThisModule, "Should be doing extensive checks here!" )
        vPrint( 'Quiet', debuggingThisModule, "Should be doing extensive checks here!" )
    #end of InternalBible.doExtensiveChecks


    def getCheckResults( self, givenBookList=None ):
        """
        Returns the error dictionary.
            All keys ending in 'Errors' give lists of strings.
            All keys ending in 'Counts' give dicts with [value]:count entries
            All other keys give subkeys
            The structure is:
                errors: dict
                    ['ByBook']: dict
                        ['All Books']: dict
                        [BBB] in order: dict
                            ['Priority Errors']: list
                            ['Load Errors']: list
                            ['Fix Text Errors']: list
                            ['Versification Errors']: list
                            ['SFMs']: dict
                                ['Newline Marker Errors']: list
                                ['Internal Marker Errors']: list
                                ['All Newline Marker Counts']: dict
                            ['Characters']: dict
                                ['All Character Counts']: dict
                                ['Letter Counts']: dict
                                ['Punctuation Counts']: dict
                            ['Words']: dict
                                ['All Word Counts']: dict
                                ['Case Insensitive Word Counts']: dict
                            ['Headings']: dict
                    ['ByCategory']: dict
        """
        if givenBookList is None: givenBookList = self.books.keys() # this is a dict

        def appendList( BBB, errorDict, firstKey, secondKey=None ):
            """Appends a list to the ALL BOOKS errors."""
            #dPrint( 'Quiet', debuggingThisModule, "  appendList", BBB, firstKey, secondKey )
            if secondKey is None:
                if BibleOrgSysGlobals.debugFlag: assert isinstance (errorDict[BBB][firstKey], list )
                if firstKey not in errorDict['All Books']: errorDict['All Books'][firstKey] = []
                errorDict['All Books'][firstKey].extend( errorDict[BBB][firstKey] )
            else: # We have an extra level
                if BibleOrgSysGlobals.debugFlag: assert isinstance (errorDict[BBB][firstKey], dict )
                if BibleOrgSysGlobals.debugFlag: assert isinstance (errorDict[BBB][firstKey][secondKey], list )
                if firstKey not in errorDict['All Books']: errorDict['All Books'][firstKey] = {}
                if secondKey not in errorDict['All Books'][firstKey]: errorDict['All Books'][firstKey][secondKey] = []
                errorDict['All Books'][firstKey][secondKey].extend( errorDict[BBB][firstKey][secondKey] )
        # end of getCheckResults.appendList

        def mergeCount( BBB:str, errorDict, firstKey:str, secondKey:Optional[str]=None ) -> None:
            """Merges the counts together."""
            #dPrint( 'Quiet', debuggingThisModule, "  mergeCount", BBB, firstKey, secondKey )
            if secondKey is None:
                if BibleOrgSysGlobals.debugFlag: assert isinstance (errorDict[BBB][firstKey], dict )
                if firstKey not in errorDict['All Books']: errorDict['All Books'][firstKey] = {}
                for something in errorDict[BBB][firstKey]:
                    errorDict['All Books'][firstKey][something] = 1 if something not in errorDict['All Books'][firstKey] else errorDict[BBB][firstKey][something] + 1
            else:
                if BibleOrgSysGlobals.debugFlag: assert isinstance (errorDict[BBB][firstKey], dict )
                if BibleOrgSysGlobals.debugFlag: assert isinstance (errorDict[BBB][firstKey][secondKey], dict )
                if firstKey not in errorDict['All Books']: errorDict['All Books'][firstKey] = {}
                if secondKey not in errorDict['All Books'][firstKey]: errorDict['All Books'][firstKey][secondKey] = {}
                for something in errorDict[BBB][firstKey][secondKey]:
                    errorDict['All Books'][firstKey][secondKey][something] = errorDict[BBB][firstKey][secondKey][something] if something not in errorDict['All Books'][firstKey][secondKey] \
                                                                                else errorDict['All Books'][firstKey][secondKey][something] + errorDict[BBB][firstKey][secondKey][something]
        # end of getCheckResults.mergeCount

        def getCapsList( lcWord, lcTotal, wordDict ):
            """ Given that a lower case word has a lowercase count of lcTotal,
                search wordDict to find all the ways that it occurs
                and return this as a list sorted with the most frequent first."""
            tempResult = []

            lcCount = wordDict[lcWord] if lcWord in wordDict else 0
            if lcCount: tempResult.append( (lcCount,lcWord,) )
            total = lcCount

            if total < lcTotal:
                tcWord = lcWord.title() # NOTE: This can make in-enew into In-Enew
                if BibleOrgSysGlobals.debugFlag: assert tcWord != lcWord
                tcCount = wordDict[tcWord] if tcWord in wordDict else 0
                if tcCount: tempResult.append( (tcCount,tcWord,) ); total += tcCount
            if total < lcTotal:
                TcWord = lcWord[0].upper() + lcWord[1:] # NOTE: This can make in-enew into In-enew
                #dPrint( 'Quiet', debuggingThisModule, lcWord, tcWord, TcWord )
                #assert TcWord != lcWord
                if TcWord!=lcWord and TcWord!=tcWord: # The first two can be equal if the first char is non-alphabetic
                    TcCount = wordDict[TcWord] if TcWord in wordDict else 0
                    if TcCount: tempResult.append( (TcCount,TcWord,) ); total += TcCount
            if total < lcTotal:
                tCWord = tcWord[0].lower() + tcWord[1:] # NOTE: This can make Matig-Kurintu into matig-Kurintu (but won't change 1Cor)
                if tCWord!=lcWord and tCWord!=tcWord and tCWord!=TcWord:
                    tCCount = wordDict[tCWord] if tCWord in wordDict else 0
                    if tCCount: tempResult.append( (tCCount,tCWord,) ); total += tCCount
            if total < lcTotal:
                UCWord = lcWord.upper()
                if BibleOrgSysGlobals.debugFlag: assert UCWord!=lcWord
                if UCWord != TcWord:
                    UCCount = wordDict[UCWord] if UCWord in wordDict else 0
                    if UCCount: tempResult.append( (UCCount,UCWord,) ); total += UCCount
            if total < lcTotal: # There's only one (slow) way left -- look at every word
                for word in wordDict:
                    if word.lower()==lcWord and word not in ( lcWord, tcWord, TcWord, tCWord, UCWord ):
                        tempResult.append( (wordDict[word],word,) ); total += wordDict[word]
                        # Seems we don't know the BCV reference here unfortunately
                        if 'Possible Word Errors' not in errors['ByBook']['All Books']['Words']: errors['ByBook']['All Books']['Words']['Possible Word Errors'] = []
                        errors['ByBook']['All Books']['Words']['Possible Word Errors'].append( _("Word {!r} appears to have unusual capitalization").format( word ) )
                        if total == lcTotal: break # no more to find

            if total < lcTotal:
                vPrint( 'Quiet', debuggingThisModule, "Couldn't get word total with", lcWord, lcTotal, total, tempResult )
                vPrint( 'Quiet', debuggingThisModule, lcWord, tcWord, TcWord, tCWord, UCWord )

            result = [w for c,w in sorted(tempResult)]
            #if len(tempResult)>2: vPrint( 'Quiet', debuggingThisModule, lcWord, lcTotal, total, tempResult, result )
            return result
        # end of getCheckResults.getCapsList

        # Set up
        errors = {}; errors['ByBook'] = {}; errors['ByCategory'] = {}
        for category in ('Priority Errors','Load Errors','Fix Text Errors','Validation Errors','Versification Errors',):
            errors['ByCategory'][category] = [] # get these in a logical order (remember: they might not all occur for each book)
        for category in ('SFMs','Characters','Words','Headings','Introduction','Notes','Controls',): # get these in a logical order
            errors['ByCategory'][category] = {}
        errors['ByBook']['All Books'] = {}

        # Make sure that the error lists come first in the All Books ordered dictionaries (even if there's no errors for the first book)
        for BBB in self.books.keys():
            if BBB in givenBookList:
                errors['ByBook'][BBB] = self.books[BBB].getCheckResults()
                for thisKey in errors['ByBook'][BBB]:
                    if thisKey.endswith('Errors'):
                        errors['ByBook']['All Books'][thisKey] = []
                        errors['ByCategory'][thisKey] = []
                    elif not thisKey.endswith('List') and not thisKey.endswith('Lines'):
                        for anotherKey in errors['ByBook'][BBB][thisKey]:
                            if anotherKey.endswith('Errors'):
                                if thisKey not in errors['ByBook']['All Books']: errors['ByBook']['All Books'][thisKey] = {}
                                errors['ByBook']['All Books'][thisKey][anotherKey] = []
                                if thisKey not in errors['ByCategory']: errors['ByCategory'][thisKey] = {}
                                errors['ByCategory'][thisKey][anotherKey] = []

        # Combine book errors into Bible totals plus into categories
        for BBB in self.books.keys():
            if BBB in givenBookList:
                #errors['ByBook'][BBB] = self.books[BBB].getCheckResults()

                # Correlate some of the totals (i.e., combine book totals into Bible totals)
                # Also, create a dictionary of errors by category (as well as the main one by book reference code BBB)
                for thisKey in errors['ByBook'][BBB]:
                    #dPrint( 'Quiet', debuggingThisModule, "thisKey", BBB, thisKey )
                    if thisKey.endswith('Errors') or thisKey.endswith('List') or thisKey.endswith('Lines'):
                        if BibleOrgSysGlobals.debugFlag: assert isinstance( errors['ByBook'][BBB][thisKey], list )
                        appendList( BBB, errors['ByBook'], thisKey )
                        errors['ByCategory'][thisKey].extend( errors['ByBook'][BBB][thisKey] )
                    elif thisKey.endswith('Counts'):
                        NEVER_HAPPENS # does this happen?
                        mergeCount( BBB, errors['ByBook'], thisKey )
                    else: # it's things like SFMs, Characters, Words, Headings, Notes
                        for anotherKey in errors['ByBook'][BBB][thisKey]:
                            #dPrint( 'Quiet', debuggingThisModule, " anotherKey", BBB, anotherKey )
                            if anotherKey.endswith('Errors') or anotherKey.endswith('List') or anotherKey.endswith('Lines'):
                                if BibleOrgSysGlobals.debugFlag: assert isinstance( errors['ByBook'][BBB][thisKey][anotherKey], list )
                                appendList( BBB, errors['ByBook'], thisKey, anotherKey )
                                if thisKey not in errors['ByCategory']: errors['ByCategory'][thisKey] = {} #; vPrint( 'Quiet', debuggingThisModule, "Added", thisKey )
                                if anotherKey not in errors['ByCategory'][thisKey]: errors['ByCategory'][thisKey][anotherKey] = []
                                errors['ByCategory'][thisKey][anotherKey].extend( errors['ByBook'][BBB][thisKey][anotherKey] )
                            elif anotherKey.endswith('Counts'):
                                mergeCount( BBB, errors['ByBook'], thisKey, anotherKey )
                                # Haven't put counts into category array yet
                            else:
                                vPrint( 'Quiet', debuggingThisModule, anotherKey, "not done yet" )
                                #halt # Not done yet

        # Taking those word lists, find uncommon words
        threshold = 4 # i.e., find words used less often that this many times as possible candidates for spelling errors
        uncommonWordCounts = {}
        if 'Words' in errors['ByBook']['All Books']:
            for word, lcCount in errors['ByBook']['All Books']['Words']['Case Insensitive Word Counts'].items():
                adjWord = word
                if word not in errors['ByBook']['All Books']['Words']['All Word Counts'] \
                or errors['ByBook']['All Books']['Words']['All Word Counts'][word] < lcCount: # then it sometimes occurs capitalized in some way
                    # Look for uncommon capitalizations
                    results = getCapsList( word, lcCount, errors['ByBook']['All Books']['Words']['All Word Counts'] )
                    if len(results) > 2:
                        if 'Possible Word Errors' not in errors['ByBook']['All Books']['Words']: errors['ByBook']['All Books']['Words']['Possible Word Errors'] = []
                        errors['ByBook']['All Books']['Words']['Possible Word Errors'].append( _("Lots of ways of capitalizing {}").format( results ) )
                if lcCount < threshold: # look for uncommon words
                    if word not in errors['ByBook']['All Books']['Words']['All Word Counts']: # then it ONLY occurs capitalized in some way
                        adjWord = getCapsList( word, lcCount, errors['ByBook']['All Books']['Words']['All Word Counts'] )[0]
                    uncommonWordCounts[adjWord] = lcCount
            if uncommonWordCounts: errors['ByBook']['All Books']['Words']['Uncommon Word Counts'] = uncommonWordCounts

    	# Remove any unnecessary empty categories
        for category in list( errors['ByCategory'].keys() ):
            if not errors['ByCategory'][category]:
                #dPrint( 'Quiet', debuggingThisModule, "InternalBible.getCheckResults: Removing empty category", category, "from errors['ByCategory']" )
                del errors['ByCategory'][category]
        return errors
    # end of InternalBible.getCheckResults


    def makeErrorHTML( self, givenOutputFolder, givenBookList=None, titlePrefix=None, webPageTemplate=None ):
        """
        Gets the error dictionaries that were the result of the check
            and produce linked HTML pages in the given output folder.

        All pages are built with relative links.

        Returns the path to the index.html file
            or None if there was a problem.
        """
        from datetime import datetime
        fnPrint( debuggingThisModule, f"makeErrorHTML( {givenOutputFolder!r}, {titlePrefix!r}, {webPageTemplate!r} )" )
        #logging.info( "Doing Bible checks…" )
        #dPrint( 'Info', debuggingThisModule, "Doing Bible checks…" )

        errorDictionary = self.getCheckResults( givenBookList )
        if givenBookList is None: givenBookList = self.books.keys() # this is a dict

        # Note that this requires a CSS file called Overall.css
        if webPageTemplate is None:
            webPageTemplate = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta http-equiv="content-type" content="text/html;charset=UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<link rel="stylesheet" href="__TOP_PATH__Overall.css" type="text/css"/>
    <title>__TITLE__</title>
</head>

<body class="HTMLBody">
<div id="TopBar"><a href="__TOP_PATH__"><img class="Banner" height="120" src="__TOP_PATH__Logo/FG-Banner.jpg" alt="Top logo banner graphic"/></a>
    <h1 class="PageHeading">__HEADING__</h1></div>
<div id="MainContent">
    <div id="MainSection">
    __MAIN_PART__
    </div>
</div>

<div id="Footer">
    <p class="GeneratedNotice">This page automatically generated __DATE__ from a template created 2016-08-29</p>
    </p></div>
</body></html>
"""
        webPageTemplate = webPageTemplate.replace( '__DATE__', datetime.now().strftime('%Y-%m-%d') )

        defaultTopPath = ""

        # Make our own output folder
        outputFolder = os.path.join( givenOutputFolder, 'BOS_Check_Results/' )
        try: os.mkdir( outputFolder, 0o755 )
        except FileExistsError: pass # Must be redoing it
        pagesFolder = os.path.join( outputFolder, 'Pages/' )
        try: os.mkdir( pagesFolder, 0o755 )
        except FileExistsError: pass # Must be redoing it

        ourTitle = _("Bible Checks")
        if titlePrefix is None: titlePrefix = self.abbreviation
        if titlePrefix: ourTitle = titlePrefix + ' ' + ourTitle

        if not errorDictionary: indexPart = "<p>No Bible errors found.</p>"
        else:
            BBBIndexPart, categoryIndexPart = "", ""
            BBBIndexPart += '<table>'
            if len(errorDictionary['ByBook']) < 3: # Assume there's only one BBB book, plus 'All Books'
                del errorDictionary['ByBook']['All Books']
            for BBB in errorDictionary['ByBook']: # Create an error page for each book (and for all books if there's more than one book)
                #dPrint( 'Quiet', debuggingThisModule, "Have errors for", BBB )
                if not errorDictionary['ByBook'][BBB]: # Then it's blank
                    vPrint( 'Quiet', debuggingThisModule, "HEY 0—Should not have had blank entry for", BBB )
                BBBPart = ""
                for thisKey in errorDictionary['ByBook'][BBB]:
                    if BibleOrgSysGlobals.debugFlag: assert isinstance( thisKey, str )
                    if not errorDictionary['ByBook'][BBB][thisKey]: vPrint( 'Quiet', debuggingThisModule, "HEY 1—Should not have had", BBB, thisKey )
                    #dPrint( 'Quiet', debuggingThisModule, 'ByBook', BBB, thisKey )
                    if errorDictionary['ByBook'][BBB][thisKey]:
                        BBBPart += "<h1>{}</h1>".format( thisKey )
                        if thisKey == 'Priority Errors': # it should be a list
                            if BibleOrgSysGlobals.debugFlag: assert isinstance( errorDictionary['ByBook'][BBB][thisKey], list )
                            count, lastError, lastBk, lastCh, lastVs = 0, '', '', '', ''
                            #for priority,errorText,ref in sorted( errorDictionary['ByBook'][BBB][thisKey], reverse=True ): # Sorts by the first tuple value which is priority
                            for priority,errorText,ref in sorted( errorDictionary['ByBook'][BBB][thisKey], key=lambda theTuple: theTuple[0], reverse=True ): # Sorts by the first tuple value which is priority
                            #for priority,errorText,ref in errorDictionary['ByBook'][BBB][thisKey]: # Sorts by the first tuple value which is priority
                                #dPrint( 'Quiet', debuggingThisModule, 'BBB', priority,errorText,ref )
                                if BibleOrgSysGlobals.debugFlag: assert isinstance( priority, int ) and 0 <= priority <= 100
                                if BibleOrgSysGlobals.debugFlag: assert isinstance( errorText, str ) and errorText
                                if BibleOrgSysGlobals.debugFlag: assert isinstance( ref, tuple ) and len(ref)==3
                                bk, ch, vs = ref
                                if errorText != lastError:
                                    if count: BBBPart += '</p>'
                                    BBBPart += "<p>{} in {} {}:{}".format( errorText, bk, ch, vs )
                                    count += 1
                                elif bk and bk!=lastBk: BBBPart += "; {} {}:{}".format( bk, ch, vs )
                                elif ch and ch!=lastCh: BBBPart += "; {}:{}".format( ch, vs )
                                elif vs and vs!=lastVs: BBBPart += ",{}".format( vs )
                                if count>=20 or priority<30:
                                    BBBPart += "</p><p><small>Showing {} out of {} priority errors</small></p>".format( count, len(errorDictionary['ByBook'][BBB][thisKey]) )
                                    break
                                if bk: lastBk = bk
                                if ch: lastCh = ch
                                if vs: lastVs = vs
                                lastError = errorText
                        elif thisKey.endswith('Errors'): # it should be a list
                            if BibleOrgSysGlobals.debugFlag: assert isinstance( errorDictionary['ByBook'][BBB][thisKey], list )
                            for error in errorDictionary['ByBook'][BBB][thisKey]:
                                #dPrint( 'Quiet', debuggingThisModule, "nice1", 'ByBook', BBB, thisKey, error )
                                if BibleOrgSysGlobals.debugFlag: assert isinstance( error, str )
                                BBBPart += "<p>{}</p>".format( error )
                        elif thisKey.endswith('List'): # it should be a list
                            NEVER_HAPPENS
                            if BibleOrgSysGlobals.debugFlag: assert isinstance( errorDictionary['ByBook'][BBB][thisKey], list )
                            BBBPart += "<h1>{}</h1>".format( thisKey )
                            for error in errorDictionary['ByBook'][BBB][thisKey]:
                                if BibleOrgSysGlobals.debugFlag: assert isinstance( error, str )
                                BBBPart += "<p>{}</p>".format( error )
                        elif thisKey.endswith('Lines'): # it should be a list
                            NEVER_HAPPENS
                            if BibleOrgSysGlobals.debugFlag: assert isinstance( errorDictionary['ByBook'][BBB][thisKey], list )
                        elif thisKey.endswith('Counts'): # it should be an ordered dict
                            NEVER_HAPPENS
                            if BibleOrgSysGlobals.debugFlag: assert isinstance( errorDictionary['ByBook'][BBB][thisKey], dict )
                            for subCategory in errorDictionary['ByBook'][BBB][thisKey]:
                                #dPrint( 'Quiet', debuggingThisModule, "subCategory1", subCategory )
                                if subCategory.endswith('Errors'):
                                    BBBPart += "<h2>{}</h2>".format( subCategory )
                                    for error in errorDictionary['ByBook'][BBB][thisKey][subCategory]:
                                        BBBPart += "<p>{}</p>".format( error )
                                elif subCategory.endswith('Counts'):
                                    BBBPart += "<h2>{}</h2>".format( subCategory ) + "<p>"
                                    for something in sorted(errorDictionary['ByBook'][BBB][thisKey][subCategory]):
                                        BBBPart += "&nbsp;<b>{}</b>:&nbsp;{}&nbsp;&nbsp; ".format( something, errorDictionary['ByBook'][BBB][thisKey][subCategory][something] )
                                    BBBPart += "</p>"
                                else: vPrint( 'Quiet', debuggingThisModule, "A weird 1" ); halt
                        else: # Have a category with subcategories
                            for secondKey in errorDictionary['ByBook'][BBB][thisKey]:
                                if not errorDictionary['ByBook'][BBB][thisKey][secondKey]: vPrint( 'Quiet', debuggingThisModule, "HEY 3—Should not have had", BBB, thisKey, secondKey )
                                if errorDictionary['ByBook'][BBB][thisKey][secondKey]:
                                    if secondKey.endswith('Errors'): # it should be a list
                                        #dPrint( 'Quiet', debuggingThisModule, "BBB Have ..Errors", BBB, thisKey, secondKey )
                                        if BibleOrgSysGlobals.debugFlag: assert isinstance( errorDictionary['ByBook'][BBB][thisKey][secondKey], list )
                                        BBBPart += "<h2>{}</h2>".format( secondKey )
                                        for error in errorDictionary['ByBook'][BBB][thisKey][secondKey]:
                                            if BibleOrgSysGlobals.debugFlag: assert isinstance( error, str )
                                            BBBPart += "<p>{}</p>".format( error )
                                    elif secondKey.endswith('List'): # it should be a list
                                        #dPrint( 'Quiet', debuggingThisModule, "BBB Have ..List", BBB, thisKey, secondKey, len(errorDictionary['ByBook'][BBB][thisKey][secondKey]), len(errorDictionary['ByBook'][BBB][thisKey][secondKey][0]) )
                                        if BibleOrgSysGlobals.debugFlag: assert isinstance( errorDictionary['ByBook'][BBB][thisKey][secondKey], list )
                                        if secondKey == "Modified Marker List" and len(errorDictionary['ByBook'][BBB][thisKey][secondKey])>60: # Put onto a separate page
                                            ListPart = '<p>'
                                            for jj,entry in enumerate( errorDictionary['ByBook'][BBB][thisKey][secondKey] ):
                                                if BibleOrgSysGlobals.debugFlag: assert isinstance( entry, str )
                                                if thisKey=='USFMs' and secondKey=='Modified Marker List' and entry[0]=='[' and entry[-1]==']':
                                                    if BBB!='All Books': continue # Don't display the BBB book reference code
                                                    if BBB=='All Books' and jj: ListPart += "</p>\n<p>" # Start each new book on a new line
                                                ListPart += "{} ".format( entry )
                                            ListPart += '</p>'
                                            webPage = webPageTemplate.replace( "__TITLE__", ourTitle+" USFM {}".format(secondKey) ).replace( "__HEADING__", ourTitle+" USFM Bible {}".format(secondKey) ) \
                                                        .replace( "__MAIN_PART__", ListPart ).replace( "__EXTRAS__", '' ) \
                                                        .replace( "__TOP_PATH__", defaultTopPath ).replace( "__SUB_PATH__", "/Software/" ).replace( "__SUB_SUB_PATH__", "/Software/BibleDropBox/" )
                                                        #.replace( "__TOP_PATH__", '../'*6 ).replace( "__SUB_PATH__", '../'*5 ).replace( "__SUB_SUB_PATH__", '../'*4 )
                                            webPageFilename = "{}_{}.html".format( BBB, secondKey.replace(' ','') )
                                            with open( os.path.join(pagesFolder, webPageFilename), 'wt', encoding='utf-8' ) as myFile: # Automatically closes the file when done
                                                myFile.write( webPage )
                                            BBBPart += '<p><a href="{}">{}</a></p>'.format( webPageFilename, secondKey )
                                        else: # Just show it inline
                                            BBBPart += "<h2>{}</h2><p>".format( secondKey )
                                            for jj,entry in enumerate( errorDictionary['ByBook'][BBB][thisKey][secondKey] ):
                                                if BibleOrgSysGlobals.debugFlag: assert isinstance( entry, str )
                                                if thisKey=='USFMs' and secondKey=='Modified Marker List' and entry[0]=='[' and entry[-1]==']':
                                                    if BBB!='All Books': continue # Don't display the BBB book reference code
                                                    if BBB=='All Books' and jj: BBBPart += "</p>\n<p>" # Start each new book on a new line
                                                BBBPart += "{} ".format( entry )
                                            BBBPart += '</p>'
                                    elif secondKey.endswith('Lines'): # it should be a list
                                        #dPrint( 'Quiet', debuggingThisModule, "BBB Have ..Lines", BBB, thisKey, secondKey )
                                        if BibleOrgSysGlobals.debugFlag: assert isinstance( errorDictionary['ByBook'][BBB][thisKey][secondKey], list )
                                        BBBPart += "<h2>{}</h2><table>".format( secondKey )
                                        for line in errorDictionary['ByBook'][BBB][thisKey][secondKey]: # Line them up nicely in a table
                                            #dPrint( 'Quiet', debuggingThisModule, "line {} {!r}".format( len(line), line ) )
                                            if BibleOrgSysGlobals.debugFlag: assert isinstance( line, str ) and line[-1]=="'"
                                            #if line[-1] != "'": vPrint( 'Quiet', debuggingThisModule, BBB, thisKey, secondKey, line )
                                            bits = line[:-1].split( " '", 1 ); assert len(bits) == 2 # Remove the final quote and split at the first quote
                                            if "Main Title 1" in bits[0]: bits[1] = "<b>" + bits[1] + "</b>"
                                            BBBPart += "<tr><td>{}</td><td>{}</td></tr>".format( bits[0], bits[1] ) # Put in a table row
                                        BBBPart += '</table>'
                                    elif secondKey.endswith('Counts'): # it should be an ordered dict
                                        #dPrint( 'Quiet', debuggingThisModule, "BBB Have ..Counts", BBB, thisKey, secondKey )
                                        if BibleOrgSysGlobals.debugFlag: assert isinstance( errorDictionary['ByBook'][BBB][thisKey][secondKey], dict )
                                        if len(errorDictionary['ByBook'][BBB][thisKey][secondKey]) < 50: # Small list -- just include it in this page
                                            BBBPart += "<h2>{}</h2>".format( secondKey ) + "<p>"
                                            for something, count in sorted( errorDictionary['ByBook'][BBB][thisKey][secondKey].items(), key=lambda theTuple: theTuple[0].lower() ): # Sort by lower-case values
                                                BBBPart += "&nbsp;<b>{}</b>:&nbsp;{}&nbsp;&nbsp; ".format( something, count )
                                            BBBPart += "</p>"
                                            BBBPart += "<h2>{} (sorted by count)</h2>".format( secondKey ) + "<p>"
                                            for something, count in sorted( errorDictionary['ByBook'][BBB][thisKey][secondKey].items(), key=lambda theTuple: theTuple[1] ): # Sort by count
                                                BBBPart += "&nbsp;<b>{}</b>:&nbsp;{}&nbsp;&nbsp; ".format( something, count )
                                            BBBPart += "</p>"
                                        else: # Large list of counts -- put it on a separate page
                                            CountPart = ''
                                            for something,count in sorted( errorDictionary['ByBook'][BBB][thisKey][secondKey].items(), key=lambda theTuple: theTuple[0].lower() ): # Sort by lower-case values
                                                CountPart += "&nbsp;<b>{}</b>:&nbsp;{}&nbsp;&nbsp; ".format( something, count )
                                            webPage = webPageTemplate.replace( "__TITLE__", ourTitle+" USFM {}".format(secondKey) ).replace( "__HEADING__", ourTitle+" USFM Bible {}".format(secondKey) ) \
                                                        .replace( "__MAIN_PART__", CountPart ).replace( "__EXTRAS__", '' ) \
                                                        .replace( "__TOP_PATH__", defaultTopPath ).replace( "__SUB_PATH__", "/Software/" ).replace( "__SUB_SUB_PATH__", "/Software/BibleDropBox/" )
                                                        #.replace( "__TOP_PATH__", '../'*6 ).replace( "__SUB_PATH__", '../'*5 ).replace( "__SUB_SUB_PATH__", '../'*4 )
                                            webPageFilename = "{}_{}.html".format( BBB, secondKey.replace(' ','') )
                                            with open( os.path.join(pagesFolder, webPageFilename), 'wt', encoding='utf-8' ) as myFile: # Automatically closes the file when done
                                                myFile.write( webPage )
                                            BBBPart += '<p><a href="{}">{}</a></p>'.format( webPageFilename, secondKey )
                                            CountPart = ''
                                            for something,count in sorted( errorDictionary['ByBook'][BBB][thisKey][secondKey].items(), key=lambda theTuple: theTuple[1] ): # Sort by count
                                                CountPart += "&nbsp;<b>{}</b>:&nbsp;{}&nbsp;&nbsp; ".format( something, count )
                                            webPage = webPageTemplate.replace( "__TITLE__", ourTitle+" USFM {}".format(secondKey) ).replace( "__HEADING__", ourTitle+" USFM Bible {}".format(secondKey) ) \
                                                        .replace( "__MAIN_PART__", CountPart ).replace( "__EXTRAS__", '' ) \
                                                        .replace( "__TOP_PATH__", defaultTopPath ).replace( "__SUB_PATH__", "/Software/" ).replace( "__SUB_SUB_PATH__", "/Software/BibleDropBox/" )
                                                        #.replace( "__TOP_PATH__", '../'*6 ).replace( "__SUB_PATH__", '../'*5 ).replace( "__SUB_SUB_PATH__", '../'*4 )
                                            webPageFilename = "{}_{}_byCount.html".format( BBB, secondKey.replace(' ','') )
                                            with open( os.path.join(pagesFolder, webPageFilename), 'wt', encoding='utf-8' ) as myFile: # Automatically closes the file when done
                                                myFile.write( webPage )
                                            BBBPart += '<p><a href="{}">{} (sorted by count)</a></p>'.format( webPageFilename, secondKey )
                                    else: raise KeyError
                if BBBPart: # Create the error page for this book
                    webPage = webPageTemplate.replace( "__TITLE__", ourTitle ).replace( "__HEADING__", ourTitle+" USFM Bible {} Checks".format(BBB) ) \
                                .replace( "__MAIN_PART__", BBBPart ).replace( "__EXTRAS__", '' ) \
                                .replace( "__TOP_PATH__", defaultTopPath ).replace( "__SUB_PATH__", "/Software/" ).replace( "__SUB_SUB_PATH__", "/Software/BibleDropBox/" )
                                #.replace( "__TOP_PATH__", '../'*6 ).replace( "__SUB_PATH__", '../'*5 ).replace( "__SUB_SUB_PATH__", '../'*4 )
                    webPageFilename = "{}.html".format( BBB )
                    with open( os.path.join(pagesFolder, webPageFilename), 'wt', encoding='utf-8' ) as myFile: # Automatically closes the file when done
                        myFile.write( webPage )
                    #BBBIndexPart += '<p>Errors for book <a href="{}">{}</a></p>'.format( webPageFilename, BBB )
                    if BBB == 'All Books': BBBIndexPart += '<tr><td><a href="{}">ALL</a></td><td>All Books</td></tr>'.format( webPageFilename )
                    else: BBBIndexPart += '<tr><td><a href="{}">{}</a></td><td>{}</td></tr>'.format( webPageFilename, BBB, self.getAssumedBookName(BBB) )
            BBBIndexPart += '</table>'
            categoryIndexPart += '<table>'
            for category in errorDictionary['ByCategory']: # Create an error page for each book (and for all books)
                if not errorDictionary['ByCategory'][category]: vPrint( 'Quiet', debuggingThisModule, "HEY 2—Should not have had", category )
                #dPrint( 'Quiet', debuggingThisModule, "ProcessUSFMUploads.makeErrorHTML: Processing category", category, "…" )
                categoryPart = ""
                categoryPart += "<h1>{}</h1>".format( category )
                if category == 'Priority Errors': # it should be a list
                    if BibleOrgSysGlobals.debugFlag: assert isinstance( errorDictionary['ByCategory'][category], list )
                    count, lastError, lastBk, lastCh, lastVs = 0, '', '', '', ''
                    #for priority,errorText,ref in sorted( errorDictionary['ByCategory'][category], reverse=True ): # Sorts by the first tuple value which is priority
                    for priority,errorText,ref in sorted( errorDictionary['ByCategory'][category], key=lambda theTuple: theTuple[0], reverse=True ): # Sorts by the first tuple value which is priority
                    #for priority,errorText,ref in errorDictionary['ByCategory'][category]: # Sorts by the first tuple value which is priority
                        #dPrint( 'Quiet', debuggingThisModule, 'cat', priority,errorText,ref )
                        if BibleOrgSysGlobals.debugFlag: assert isinstance( priority, int ) and 0 <= priority <= 100
                        if BibleOrgSysGlobals.debugFlag: assert isinstance( errorText, str ) and errorText
                        if BibleOrgSysGlobals.debugFlag: assert isinstance( ref, tuple ) and len(ref)==3
                        bk, ch, vs = ref
                        if errorText != lastError:
                            if count: categoryPart += '</p>'
                            categoryPart += "<p>{} in {} {}:{}".format( errorText, bk, ch, vs )
                            count += 1
                        elif bk and bk!=lastBk: categoryPart += "; {} {}:{}".format( bk, ch, vs )
                        elif ch and ch!=lastCh: categoryPart += "; {}:{}".format( ch, vs )
                        elif vs and vs!=lastVs: categoryPart += ",{}".format( vs )
                        if count>=50:
                            categoryPart += "</p><p><small>Showing {} out of {} priority errors</small></p>".format( count, len(errorDictionary['ByCategory'][category]) )
                            break
                        if bk: lastBk = bk
                        if ch: lastCh = ch
                        if vs: lastVs = vs
                        lastError = errorText
                elif category.endswith('Errors'): # it should be a list
                    if BibleOrgSysGlobals.debugFlag: assert isinstance( errorDictionary['ByCategory'][category], list )
                    for error in errorDictionary['ByCategory'][category]:
                        if BibleOrgSysGlobals.debugFlag: assert isinstance( error, str )
                        categoryPart += "<p>{}</p>".format( error )
                elif category.endswith('Counts'): # it should be an ordered dict
                    NEVER_HAPPENS
                    for thisKey in errorDictionary['ByCategory'][category]:
                        if thisKey.endswith('Errors'): # it should be a list
                            if BibleOrgSysGlobals.debugFlag: assert isinstance( errorDictionary['ByCategory'][category][thisKey], list )
                            categoryPart += "<h1>{}</h1>".format( thisKey )
                            for error in errorDictionary['ByCategory'][category][thisKey]:
                                if BibleOrgSysGlobals.debugFlag: assert isinstance( error, str )
                                categoryPart += "<p>{}</p>".format( error )
                        elif thisKey.endswith('Counts'): # it should be a list
                            vPrint( 'Quiet', debuggingThisModule, "Counts key", thisKey )
                            categoryPart += "<h1>{}</h1>".format( thisKey )
                            if isinstance( errorDictionary['ByCategory'][category][thisKey], list ): # always true
                            #    for error in errorDictionary['ByCategory'][category][thisKey]:
                            #        if BibleOrgSysGlobals.debugFlag: assert isinstance( error, str )
                            #        categoryPart += "<p>{}</p>".format( error )
                            #elif isinstance( errorDictionary['ByCategory'][category][thisKey], dict ):
                                for subCategory in errorDictionary['ByCategory'][category][thisKey]:
                                    #dPrint( 'Quiet', debuggingThisModule, subCategory )
                                    if subCategory.endswith('Errors'):
                                        categoryPart += "<h2>{}</h2>".format( subCategory )
                                        for error in errorDictionary['ByCategory'][category][BBB][subCategory]:
                                            categoryPart += "<p>{}</p>".format( error )
                                    elif subCategory.endswith('Counts'):
                                        categoryPart += "<h2>{}</h2>".format( subCategory ) + "<p>"
                                        for something in sorted(errorDictionary['ByCategory'][category][BBB][subCategory]):
                                            categoryPart += "{}:{} ".format( something, errorDictionary['ByCategory'][category][BBB][subCategory][something] )
                                        categoryPart += "</p>"
                                    else: vPrint( 'Quiet', debuggingThisModule, "A weird 2" ); halt
                        else:
                            vPrint( 'Quiet', debuggingThisModule, "Have left-over thisKey", thisKey )
                            continue # ignore for now temp …
                            raise KeyError# it wasn't a list or a dictionary
                else: # it's a subcategory
                    for thisKey in errorDictionary['ByCategory'][category]:
                        if thisKey.endswith('Errors'): # it should be a list
                            if BibleOrgSysGlobals.debugFlag: assert isinstance( errorDictionary['ByCategory'][category][thisKey], list )
                            categoryPart += "<h1>{}</h1>".format( thisKey )
                            for error in errorDictionary['ByCategory'][category][thisKey]:
                                if BibleOrgSysGlobals.debugFlag: assert isinstance( error, str )
                                categoryPart += "<p>{}</p>".format( error )
                        elif thisKey.endswith('List'): # it should be a list
                            if BibleOrgSysGlobals.debugFlag: assert isinstance( errorDictionary['ByCategory'][category][thisKey], list )
                            categoryPart += "<h2>{}</h2><p>".format( thisKey )
                            for jj,entry in enumerate( errorDictionary['ByCategory'][category][thisKey] ):
                                if BibleOrgSysGlobals.debugFlag: assert isinstance( entry, str )
                                if thisKey=='Modified Marker List' and entry[0]=='[' and entry[-1]==']' and jj:
                                    categoryPart += "</p>\n<p>" # Start each new book on a new line
                                categoryPart += "{} ".format( entry )
                            categoryPart += '</p>'
                        elif thisKey.endswith('Lines'): # it should be a list
                            if BibleOrgSysGlobals.debugFlag: assert isinstance( errorDictionary['ByCategory'][category][thisKey], list )
                            categoryPart += "<h2>{}</h2><table>".format( thisKey )
                            for line in errorDictionary['ByCategory'][category][thisKey]: # Line them up nicely in a table
                                if BibleOrgSysGlobals.debugFlag: assert isinstance( line, str ) and line[-1]=="'"
                                bits = line[:-1].split( " '", 1 ); assert len(bits) == 2 # Remove the final quote and split at the first quote
                                if "Main Title 1" in bits[0]: bits[1] = "<b>" + bits[1] + "</b>"
                                categoryPart += "<tr><td>{}</td><td>{}</td></tr>".format( bits[0], bits[1] ) # Put in a table row
                            categoryPart += '</table>'
                        elif thisKey.endswith('Counts'): # it should be a list
                            vPrint( 'Quiet', debuggingThisModule, "Counts key", thisKey )
                            categoryPart += "<h1>{}</h1>".format( thisKey )
                            if isinstance( errorDictionary['ByCategory'][category][thisKey], list ): # always true
                            #    for error in errorDictionary['ByCategory'][category][thisKey]:
                            #        if BibleOrgSysGlobals.debugFlag: assert isinstance( error, str )
                            #        categoryPart += "<p>{}</p>".format( error )
                            #elif isinstance( errorDictionary['ByCategory'][category][thisKey], dict ):
                                for subCategory in errorDictionary['ByCategory'][category][thisKey]:
                                    #dPrint( 'Quiet', debuggingThisModule, subCategory )
                                    if subCategory.endswith('Errors'):
                                        categoryPart += "<h2>{}</h2>".format( subCategory )
                                        for error in errorDictionary['ByCategory'][category][BBB][subCategory]:
                                            categoryPart += "<p>{}</p>".format( error )
                                    elif subCategory.endswith('Counts'):
                                        categoryPart += "<h2>{}</h2>".format( subCategory ) + "<p>"
                                        for something in sorted(errorDictionary['ByCategory'][category][BBB][subCategory]):
                                            categoryPart += "{}:{} ".format( something, errorDictionary['ByCategory'][category][BBB][subCategory][something] )
                                        categoryPart += "</p>"
                                    else: vPrint( 'Quiet', debuggingThisModule, "A weird 2" ); halt
                        else:
                            vPrint( 'Quiet', debuggingThisModule, "Have left-over thisKey", thisKey )
                            continue # ignore for now temp …
                            raise KeyError# it wasn't a list or a dictionary
                if categoryPart: # Create the error page for this catebory
                    webPage = webPageTemplate.replace( "__TITLE__", ourTitle ).replace( "__HEADING__", ourTitle+" USFM Bible {} Checks".format(BBB) ) \
                                .replace( "__MAIN_PART__", categoryPart ).replace( "__EXTRAS__", '' ) \
                                .replace( "__TOP_PATH__", defaultTopPath ).replace( "__SUB_PATH__", "/Software/" ).replace( "__SUB_SUB_PATH__", "/Software/BibleDropBox/" )
                                #.replace( "__TOP_PATH__", '../'*6 ).replace( "__SUB_PATH__", '../'*5 ).replace( "__SUB_SUB_PATH__", '../'*4 )
                    webPageFilename = "{}.html".format( category )
                    with open( os.path.join(pagesFolder, webPageFilename), 'wt', encoding='utf-8' ) as myFile: # Automatically closes the file when done
                        myFile.write( webPage )
                    categoryCommentDict = { 'Priority Errors': 'Errors that the program thinks are most important',
                                            'Load Errors': 'Errors discovered when loading the USFM files',
                                            'Fix Text Errors': 'Errors found in the actual text',
                                            'Versification Errors': 'Errors with the chapter and verse numbers',
                                            'USFMs': 'Errors to do with the Unified Standard Format Markers',
                                            'Validation Errors': 'Errors found on detailed checking of the USFMs',
                                            'Words': 'Possible spelling and other word errors and counts',
                                            'Characters': 'Possible punctuation and other character errors and counts',
                                            'Notes': 'Footnote and cross-reference errors and counts',
                                            'Headings': 'Titles, section headers and section cross-references',
                                            'Introduction': 'Errors in the introductory section',
                                            'Added Formatting': 'Placement of section headings and paragraph breaks, etc.',
                                            'Speech Marks': 'Possible errors to do with placement of quote marks',
                                        }
                    categoryIndexPart += '<tr><td><a href="{}">{}</a></td><td>{}</td></tr>'.format( webPageFilename, category, categoryCommentDict[category] if category in categoryCommentDict else '' )
            categoryIndexPart += '</table>'
        indexPart = ""
        help1Part = '<p>Note that the checking program does make some changes to some USFM markers internally, e.g., <b>\\s</b> will be converted internally to <b>\\s1</b>, and <b>\\q</b> to <b>\\q1</b>. ' + \
                        'You may need to be aware of this when comparing these messages with the actual codes present in your files.</p>'
        help2Part = '<p><b>Errors</b> entries give lists of possible errors and warnings. <b>Priority Errors</b> is our attempt for the program to pick out the more serious errors in your work—the same information is also available in the other lists of Errors.</p>' + \
                    '<p><b>Lines</b> entries list all lines in certain categories (such as titles or headings) so that you can visually check through the lists in order to see how consistent you have been throughout your work.</p>' + \
                    '<p><b>List</b> entries also list similar items for you to scan through. The <b>Modified Marker List</b> gives you a quick way to scan through all of the main USFM markers used in your file—if a marker occurs several times in a row, it only lists it once.</p>' + \
                    '<p><b>Counts</b> entries list counts of characters and words, etc. and are usually provided sorted in different ways. It’s often helpful to look at items that only occur one or two times in your work as they might indicate possible mistakes.</p>' + \
                    '<p>We are still working on improving error detection, removing false alarms, and better prioritising the errors and warnings. If you have any suggestions, feel free to let us know. Thanks.</p>'
        if BBBIndexPart: # Create the by book index page
            BBBIndexPart += '<small>{}</small>'.format( help1Part )
            webPage = webPageTemplate.replace( "__TITLE__", ourTitle ).replace( "__HEADING__", ourTitle + " by Book" ) \
                        .replace( "__MAIN_PART__", BBBIndexPart ).replace( "__EXTRAS__", '' ) \
                        .replace( "__TOP_PATH__", defaultTopPath ).replace( "__SUB_PATH__", "/Software/" ).replace( "__SUB_SUB_PATH__", "/Software/BibleDropBox/" )
                        #.replace( "__TOP_PATH__", '../'*6 ).replace( "__SUB_PATH__", '../'*5 ).replace( "__SUB_SUB_PATH__", '../'*4 )
            webPageFilename = "BBBIndex.html"
            with open( os.path.join(pagesFolder, webPageFilename), 'wt', encoding='utf-8' ) as myFile: # Automatically closes the file when done
                myFile.write( webPage )
            if len(givenBookList) == 1:
                #indexPart += '<p><a href="{}">All books</a></p>'.format( "All Books.html" )
                pass
            else:
                indexPart += '<p><a href="{}">All books</a></p>'.format( "All Books.html" )
                indexPart += '<p><a href="{}">By Bible book</a></p>'.format( webPageFilename )
        if categoryIndexPart: # Create the by category index page
            webPage = webPageTemplate.replace( "__TITLE__", ourTitle ).replace( "__HEADING__", ourTitle + " by Category" ) \
                        .replace( "__MAIN_PART__", categoryIndexPart ).replace( "__EXTRAS__", '' ) \
                        .replace( "__TOP_PATH__", defaultTopPath ).replace( "__SUB_PATH__", "/Software/" ).replace( "__SUB_SUB_PATH__", "/Software/BibleDropBox/" )
                        #.replace( "__TOP_PATH__", '../'*6 ).replace( "__SUB_PATH__", '../'*5 ).replace( "__SUB_SUB_PATH__", '../'*4 )
            webPageFilename = "categoryIndex.html"
            with open( os.path.join(pagesFolder, webPageFilename), 'wt', encoding='utf-8' ) as myFile: # Automatically closes the file when done
                myFile.write( webPage )
            indexPart += '<p><a href="{}">By error category</a></p>'.format( webPageFilename )
        if indexPart:
            # Create the main index page
            if BBBIndexPart.count('<tr>') + categoryIndexPart.count('<tr>') < 10: # Let's just combine them (ignoring the two files already written above)
                indexPart = "<h1>By Bible book</h1>" + BBBIndexPart + "<h1>By error category</h1>" + categoryIndexPart
            indexPart += '<small>{}</small>'.format( help2Part )
            webPage = webPageTemplate.replace( "__TITLE__", ourTitle ).replace( "__HEADING__", ourTitle ) \
                        .replace( "__MAIN_PART__", indexPart ).replace( "__EXTRAS__", '' ) \
                        .replace( "__TOP_PATH__", defaultTopPath ).replace( "__SUB_PATH__", "/Software/" ).replace( "__SUB_SUB_PATH__", "/Software/BibleDropBox/" )
                        #.replace( "__TOP_PATH__", '../'*6 ).replace( "__SUB_PATH__", '../'*5 ).replace( "__SUB_SUB_PATH__", '../'*4 )
            webPageFilename = "index.html"
            webPagePath = os.path.join( pagesFolder, webPageFilename )
            if BibleOrgSysGlobals.verbosityLevel>3: vPrint( 'Quiet', debuggingThisModule, "Writing error checks web index page at {}".format( webPagePath ) )
            with open( webPagePath, 'wt', encoding='utf-8' ) as myFile: # Automatically closes the file when done
                myFile.write( webPage )
            #dPrint( 'Quiet', debuggingThisModule, "Test web page at {}".format( webPageURL ) )

        return webPagePath if len(indexPart) > 0 else None
    # end of InternalBible.makeErrorHTML


    def getNumChapters( self, BBB:str ) -> int:
        """
        Returns the number of chapters (int) in the given book.
        Returns None if we don't have that book.
        """
        fnPrint( debuggingThisModule, f"getNumChapters( {BBB} )" )
        assert len(BBB) == 3

        #if 'KJV' not in self.sourceFolder and BBB in self.triedLoadingBook: halt
        if not BibleOrgSysGlobals.loadedBibleBooksCodes.isValidBBB( BBB ): raise KeyError
        self.loadBookIfNecessary( BBB )
        if BBB in self:
            #dPrint( 'Quiet', debuggingThisModule, "getNumChapters", self, self.books[BBB].getNumChapters() )
            return self.books[BBB].getNumChapters()
        # else return None
    # end of InternalBible.getNumChapters


    def getNumVerses( self, BBB:str, C:str ) -> int:
        """
        Returns the number of verses (int) in the given book and chapter.
        Returns None if we don't have that book.
        """
        fnPrint( debuggingThisModule, f"getNumVerses( {BBB}, {C!r} )" )
        assert len(BBB) == 3

        if not BibleOrgSysGlobals.loadedBibleBooksCodes.isValidBBB( BBB ): raise KeyError
        self.loadBookIfNecessary( BBB )
        if BBB in self:
            if isinstance( C, int ): # Just double-check the parameter
                logging.debug( _("getNumVerses was passed an integer chapter instead of a string with {} {}").format( BBB, C ) )
                C = str( C )
            return self.books[BBB].getNumVerses( C )
    # end of InternalBible.getNumVerses


    def getContextVerseData( self, BCVReference:Union[SimpleVerseKey,Tuple[str,str,str,str]] ):
        """
        Search for a Bible reference
            and return a 2-tuple containing
                the Bible text (in a InternalBibleEntryList)
                along with the context.

        Expects a SimpleVerseKey for the parameter
            but also copes with a (B,C,V,S) tuple.

        Returns None if there is no information for this book.
        Raises a KeyError if there is no such CV reference.
        """
        fnPrint( debuggingThisModule, f"InternalBible.getContextVerseData( {BCVReference} ) for {self.name}" )

        if isinstance( BCVReference, tuple ): BBB = BCVReference[0]
        else: BBB = BCVReference.getBBB() # Assume it's a SimpleVerseKey object
        #dPrint( 'Quiet', debuggingThisModule, " ", BBB in self.books )
        self.loadBookIfNecessary( BBB )
        if BBB in self.books: return self.books[BBB].getContextVerseData( BCVReference )
        #else: vPrint( 'Quiet', debuggingThisModule, "InternalBible {} doesn't have {}".format( self.name, BBB ) ); halt
    # end of InternalBible.getContextVerseData


    def getVerseDataList( self, BCVReference:Union[SimpleVerseKey,Tuple[str,str,str,str]] ):
        """
        Return (USFM-like) verseData (InternalBibleEntryList -- a specialised list).

        Returns None if there is no information for this book.
        Raises a KeyError if there is no CV reference.
        """
        fnPrint( debuggingThisModule, f"InternalBible.getVerseDataList( {BCVReference} )" )
        result = self.getContextVerseData( BCVReference )
        #dPrint( 'Quiet', debuggingThisModule, "  gVD", self.name, BCVReference, verseData )
        if result is None:
            if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>2:
                vPrint( 'Quiet', debuggingThisModule, "InternalBible.getVerseDataList: no VerseData for {} {} got {}".format( self.name, BCVReference, result ) )
            #if BibleOrgSysGlobals.debugFlag: assert BCVReference.getChapterNumberStr()=='0' or BCVReference.getVerseNumberStr()=='0' # Why did we get nothing???
        else:
            verseData, context = result
            if BibleOrgSysGlobals.debugFlag:
                assert isinstance( verseData, InternalBibleEntryList )
                # The following numbers include end markers, i.e., \q1 xyz becomes q1,p~ xyz,¬q1
                if len(verseData)<1 or len(verseData)>30: vPrint( 'Quiet', debuggingThisModule, "IB:vdLen", len(verseData), self.abbreviation, BCVReference )
                if len(verseData)>35: vPrint( 'Quiet', debuggingThisModule, verseData )
                if self.abbreviation not in ('mhl','sua',): # This version has Matt 1:1-11 combined! 57 entries
                    assert 1 <= len(verseData) <= 35 # Smallest is just a chapter number line
            return verseData
    # end of InternalBible.getVerseDataList


    def getVerseText( self, BCVReference, fullTextFlag:bool=False ) -> str:
        """
        First miserable attempt at converting (USFM-like) verseData into a string.

        Gets cleanText (no notes) unless fullTextFlag is specified.

        Uses uncommon Unicode symbols to represent various formatted styles

        Raises a KeyError if the BCVReference isn't found/valid.
        """
        fnPrint( debuggingThisModule, f"InternalBible.getVerseText( {BCVReference}, fullTextFlag={fullTextFlag} )" )

        result = self.getContextVerseData( BCVReference )
        if result is not None:
            verseData, context = result
            #dPrint( 'Quiet', debuggingThisModule, "gVT", self.name, BCVReference, verseData )
            assert isinstance( verseData, InternalBibleEntryList )
            #if BibleOrgSysGlobals.debugFlag: assert 1 <= len(verseData) <= 5
            verseText, firstWord = '', False
            for entry in verseData:
                marker, cleanText = entry.getMarker(), entry.getOriginalText() if fullTextFlag else entry.getCleanText()
                if marker[0] == '¬': pass # Ignore end markers
                elif marker == 'id': verseText += 'ID: ' + cleanText
                elif marker == 'c': pass # Ignore
                elif marker == 'c~': pass # Ignore text after chapter marker
                elif marker == 'c#': pass # Ignore print chapter number
                elif marker == 'cl': pass # Ignore cl markers AFTER the '\c 1' marker (the text for the individual chapter/psalm heading)
                elif marker == 'v=': pass # Ignore the verse number (not to be printed) that the next field(s) (usually a section heading) logically belong together with
                elif marker == 'd': verseText += '¦' + cleanText + '¦'
                elif marker == 's1': verseText += '¥' + cleanText + '¥'
                elif marker == 'p': verseText += '¶' + cleanText
                elif marker == 'q1': verseText += '₁' + cleanText
                elif marker == 'q2': verseText += '₂' + cleanText
                elif marker == 'q3': verseText += '₃' + cleanText
                elif marker == 'q4': verseText += '₄' + cleanText
                elif marker == 'm': verseText += '§' + cleanText
                elif marker == 'v': firstWord = True # Ignore
                elif marker == 'v~': verseText += cleanText
                elif marker == 'p~': verseText += cleanText
                elif marker == 'vw':
                    if not firstWord: verseText += ' '
                    verseText += cleanText
                    firstWord = False
                else: logging.warning( f"InternalBible.getVerseText Unknown marker '{marker}'='{cleanText}'" )
            return verseText
    # end of InternalBible.getVerseText


    def findText( self, optionsDict ):
        """
        Search the internal Bible for the given text which is contained in a dictionary of options.
            Search string must be in optionsDict['findText'].
            (We add default options for any missing ones as well as updating the 'findHistoryList'.)

        Assumes that all Bible books are already loaded.

        Always returns three values:.
            1/ The updated dictionary of all parameters, i.e., updated optionsDict
            2/ The result summary dict, containing the following entries:
                searchedBookList, foundBookList
            3/ A list with (zero or more) search results
                being 4-tuples or 5-tuples for caseless searches.

        For the normal search, the 4-tuples are:
            SimpleVerseKey, marker (none if v~), contextBefore, contextAfter
        If the search is caseless, the 5-tuples are:
            SimpleVerseKey, marker (none if v~), contextBefore, foundWordForm, contextAfter

        NOTE: ignoreDiacriticsFlag uses BibleOrgSysGlobals.removeAccents() which might not be general enough for all languages.
        """
        fnPrint( debuggingThisModule, f"findText( {optionsDict} )" )
        if BibleOrgSysGlobals.debugFlag or debuggingThisModule:
            assert 'findText' in optionsDict

        optionsList = ( 'parentWindow', 'parentBox', 'givenBible', 'workName',
                'findText', 'findHistoryList', 'wordMode', 'caselessFlag', 'ignoreDiacriticsFlag',
                'includeIntroFlag', 'includeMainTextFlag', 'includeMarkerTextFlag', 'includeExtrasFlag',
                'contextLength', 'bookList', 'chapterList', 'markerList', 'regexFlag',
                'currentBCV', )
        for someKey in optionsDict:
            if someKey not in optionsList:
                vPrint( 'Quiet', debuggingThisModule, "findText warning: unexpected {!r} option = {!r}".format( someKey, optionsDict[someKey] ) )
                if debuggingThisModule: halt

        # Go through all the given options
        if 'workName' not in optionsDict: optionsDict['workName'] = self.getAName( abbrevFirst=True )
        if 'findHistoryList' not in optionsDict: optionsDict['findHistoryList'] = [] # Oldest first
        if 'wordMode' not in optionsDict: optionsDict['wordMode'] = 'Any' # or 'Whole' or 'EndsWord' or 'Begins' or 'EndsLine'
        if 'caselessFlag' not in optionsDict: optionsDict['caselessFlag'] = True
        if 'ignoreDiacriticsFlag' not in optionsDict: optionsDict['ignoreDiacriticsFlag'] = False
        if 'includeIntroFlag' not in optionsDict: optionsDict['includeIntroFlag'] = True
        if 'includeMainTextFlag' not in optionsDict: optionsDict['includeMainTextFlag'] = True
        if 'includeMarkerTextFlag' not in optionsDict: optionsDict['includeMarkerTextFlag'] = False
        if 'includeExtrasFlag' not in optionsDict: optionsDict['includeExtrasFlag'] = False
        if 'contextLength' not in optionsDict: optionsDict['contextLength'] = 30 # each side
        if 'bookList' not in optionsDict: optionsDict['bookList'] = 'ALL' # or BBB or a list
        if 'chapterList' not in optionsDict: optionsDict['chapterList'] = None
        if 'markerList' not in optionsDict: optionsDict['markerList'] = None
        optionsDict['regexFlag'] = False

        if BibleOrgSysGlobals.debugFlag:
            if optionsDict['chapterList']: assert optionsDict['bookList'] is None or len(optionsDict['bookList']) == 1 \
                                or optionsDict['chapterList'] == [0] # Only combinations that make sense
            assert '\r' not in optionsDict['findText'] and '\n' not in optionsDict['findText']
            assert optionsDict['wordMode'] in ( 'Any', 'Whole', 'Begins', 'EndsWord', 'EndsLine', )
            if optionsDict['wordMode'] != 'Any': assert ' ' not in optionsDict['findText']
            if optionsDict['markerList']:
                assert isinstance( markerList, list )
                assert not optionsDict['includeIntroFlag']
                assert not optionsDict['includeMainTextFlag']
                assert not optionsDict['includeMarkerTextFlag']
                assert not optionsDict['includeExtrasFlag']

        ourMarkerList = []
        if optionsDict['markerList']:
            for marker in optionsDict['markerList']:
                ourMarkerList.append( BibleOrgSysGlobals.loadedUSFMMarkers.toStandardMarker( marker ) )

        ourFindText = optionsDict['findText']
        # Save the search history (with the 'regex:' text still prefixed if applicable)
        try: optionsDict['findHistoryList'].remove( ourFindText )
        except ValueError: pass
        optionsDict['findHistoryList'].append( ourFindText ) # Make sure it goes on the end

        if ourFindText.lower().startswith( 'regex:' ):
            optionsDict['regexFlag'] = True
            ourFindText = ourFindText[6:]
            compiledFindText = re.compile( ourFindText )
        if optionsDict['ignoreDiacriticsFlag']: ourFindText = BibleOrgSysGlobals.removeAccents( ourFindText )
        if optionsDict['caselessFlag']: ourFindText = ourFindText.lower()
        searchLen = len( ourFindText )
        if BibleOrgSysGlobals.debugFlag: assert searchLen
        #dPrint( 'Quiet', debuggingThisModule, "  Searching for {!r} in {} loaded books".format( ourFindText, len(self) ) )

        # Now do the actual search
        resultSummaryDict = { 'searchedBookList':[], 'foundBookList':[], }
        resultList = [] # Contains 4-tuples or 5-tuples -- first entry is the SimpleVerseKey
        for BBB,bookObject in self.books.items():
            #dPrint( 'Quiet', debuggingThisModule, _("  findText: got book {}").format( BBB ) )
            if optionsDict['bookList'] is None or optionsDict['bookList']=='ALL' or BBB in optionsDict['bookList']:
                #dPrint( 'Quiet', debuggingThisModule, _("  findText: will search book {}").format( BBB ) )
                #self.loadBookIfNecessary( BBB )
                resultSummaryDict['searchedBookList'].append( BBB )
                C, V = '-1', '-1' # So first/id line starts at -1:0
                marker = None
                for lineEntry in bookObject:
                    if marker in BibleOrgSysGlobals.USFMParagraphMarkers:
                        lastParagraphMarker = marker

                    marker, cleanText = lineEntry.getMarker(), lineEntry.getCleanText()
                    if marker[0] == '¬': continue # we'll always ignore these added lines
                    if marker in ('intro','chapters'): continue # we'll always ignore these added lines
                    if marker == 'c': C, V = cleanText, '0'
                    elif marker == 'v': V = cleanText
                    elif C == '-1' and marker!='intro': V = str( int(V) + 1 )
                    if ourMarkerList:
                        if marker not in ourMarkerList and not (marker in ('v~','p~') and lastParagraphMarker in ourMarkerList):
                            continue
                    elif C=='-1' and not optionsDict['includeIntroFlag']: continue
                    #dPrint( 'Quiet', debuggingThisModule, "Searching in {} {}:{} {} = {}".format( BBB, C, V, marker, cleanText ) )

                    if optionsDict['chapterList'] is None \
                    or C in optionsDict['chapterList'] \
                    or int(C) in optionsDict['chapterList']:
                        #if optionsDict['chapterList'] and V=='0':
                            #dPrint( 'Quiet', debuggingThisModule, _("  findText: will search {} chapter {}").format( BBB, C ) )

                        # Get our text to search
                        origTextToBeSearched = lineEntry.getFullText() if optionsDict['includeExtrasFlag'] else cleanText
                        if C != '0' and not optionsDict['includeMainTextFlag']:
                            #dPrint( 'Quiet', debuggingThisModule, "Got {!r} but  don't include main text".format( origTextToBeSearched ) )
                            if marker in ('v~','p~') or marker in BibleOrgSysGlobals.USFMParagraphMarkers:
                                origTextToBeSearched = ''
                                if origTextToBeSearched != cleanText: # we must have extras -- we need to remove the main text
                                    #dPrint( 'Quiet', debuggingThisModule, "  Got extras" )
                                    assert optionsDict['includeExtrasFlag']
                                    origTextToBeSearched = ''
                                    for extra in lineEntry.getExtras():
                                        #dPrint( 'Quiet', debuggingThisModule, "extra", extra )
                                        extraStart = ''
                                        if optionsDict['includeMarkerTextFlag']:
                                            eTypeIndex = BOS_EXTRA_TYPES.index( extra.getType() )
                                            extraStart = '\\{} '.format( BOS_EXTRA_MARKERS[eTypeIndex] )
                                        origTextToBeSearched += ' ' if origTextToBeSearched else '' + extraStart + extra.getText()
                                    #dPrint( 'Quiet', debuggingThisModule, "  Now", repr(origTextToBeSearched) )
                        if optionsDict['includeMarkerTextFlag']:
                            origTextToBeSearched = '\\{} {}'.format( marker, origTextToBeSearched )
                        if not origTextToBeSearched: continue
                        textToBeSearched = origTextToBeSearched
                        if optionsDict['ignoreDiacriticsFlag']: textToBeSearched = BibleOrgSysGlobals.removeAccents( textToBeSearched )
                        if optionsDict['caselessFlag']: textToBeSearched = textToBeSearched.lower()
                        textLen = len( textToBeSearched )

                        if optionsDict['regexFlag']: # ignores wordMode flag
                            for match in compiledFindText.finditer( textToBeSearched ):
                                ix, ixAfter = match.span()

                                if optionsDict['contextLength']: # Find the context in the original (fully-cased) string
                                    contextBefore = origTextToBeSearched[max(0,ix-optionsDict['contextLength']):ix]
                                    contextAfter = origTextToBeSearched[ixAfter:ixAfter+optionsDict['contextLength']]
                                else: contextBefore = contextAfter = None

                                ixHyphen = V.find( '-' )
                                if ixHyphen != -1: V = V[:ixHyphen] # Remove verse bridges
                                resultTuple = (SimpleVerseKey(BBB, C, V, ix), lineEntry.getOriginalMarker(), contextBefore,
                                                                    origTextToBeSearched[ix:ixAfter], contextAfter, ) \
                                            if optionsDict['caselessFlag'] else \
                                                (SimpleVerseKey(BBB, C, V, ix), lineEntry.getOriginalMarker(), contextBefore, contextAfter, )
                                resultList.append( resultTuple )
                                if BBB not in resultSummaryDict['foundBookList']: resultSummaryDict['foundBookList'].append( BBB )
                        else: # not regExp
                            ix = -1
                            while True:
                                ix = textToBeSearched.find( ourFindText, ix+1 )
                                if ix == -1: break
                                ixAfter = ix + searchLen
                                if optionsDict['wordMode'] == 'Whole':
                                    #dPrint( 'Quiet', debuggingThisModule, "BF", repr(textToBeSearched[ix-1]) )
                                    #dPrint( 'Quiet', debuggingThisModule, "AF", repr(textToBeSearched[ixAfter]) )
                                    if ix>0 and textToBeSearched[ix-1].isalpha(): continue
                                    if ixAfter<textLen and textToBeSearched[ixAfter].isalpha(): continue
                                elif optionsDict['wordMode'] == 'Begins':
                                    if ix>0 and textToBeSearched[ix-1].isalpha(): continue
                                elif optionsDict['wordMode'] == 'EndsWord':
                                    if ixAfter<textLen and textToBeSearched[ixAfter].isalpha(): continue
                                elif optionsDict['wordMode'] == 'EndsLine':
                                    if ixAfter<textLen: continue

                                if optionsDict['contextLength']: # Find the context in the original (fully-cased) string
                                    contextBefore = origTextToBeSearched[max(0,ix-optionsDict['contextLength']):ix]
                                    contextAfter = origTextToBeSearched[ixAfter:ixAfter+optionsDict['contextLength']]
                                else: contextBefore = contextAfter = None

                                ixHyphen = V.find( '-' )
                                if ixHyphen != -1: V = V[:ixHyphen] # Remove verse bridges
                                #adjMarker = None if marker=='v~' else marker # most markers are v~ -- ignore them (for space)
                                resultTuple = (SimpleVerseKey(BBB, C, V, ix), lineEntry.getOriginalMarker(), contextBefore,
                                                                    origTextToBeSearched[ix:ixAfter], contextAfter, ) \
                                            if optionsDict['caselessFlag'] else \
                                                (SimpleVerseKey(BBB, C, V, ix), lineEntry.getOriginalMarker(), contextBefore, contextAfter, )
                                resultList.append( resultTuple )
                                if BBB not in resultSummaryDict['foundBookList']: resultSummaryDict['foundBookList'].append( BBB )

        #dPrint( 'Quiet', debuggingThisModule, _("findText: returning {}").format( resultList ) )
        return optionsDict, resultSummaryDict, resultList
    # end of InternalBible.findText


    def writeBOSBCVFiles( self, outputFolderpath ):
        """
        Write the internal pseudoUSFM out directly with one file per verse.
        """
        fnPrint( debuggingThisModule, f"writeBOSBCVFiles( {outputFolderpath} )" )

        BBBList = []
        for BBB,bookObject in self.books.items():
            BBBList.append( BBB )
            bookFolderpath = os.path.join( outputFolderpath, BBB + '/' )
            os.mkdir( bookFolderpath )
            bookObject.writeBOSBCVFiles( bookFolderpath )

        # Write the Bible metadata
        vPrint( 'Info', debuggingThisModule, "  " + _("Writing BCV metadata…") )
        metadataLines = 'BCVVersion = {}\n'.format( BCV_VERSION )
        if self.projectName: metadataLines += 'ProjectName = {}\n'.format( self.projectName )
        if self.name: metadataLines += 'Name = {}\n'.format( self.name )
        if self.abbreviation: metadataLines += 'Abbreviation = {}\n'.format( self.abbreviation )
        metadataLines += 'BookList = {}\n'.format( BBBList )
        with open( os.path.join( outputFolderpath, 'Metadata.txt' ), 'wt', encoding='utf-8' ) as metadataFile:
            metadataFile.write( metadataLines )
    # end of InternalBible.writeBOSBCVFiles


    def analyseUWalignments( self ) -> None:
        """
        Aggregate all the alignments from each book.

        The cleaned aligments are
            List[Tuple[str,str,List[Tuple[str,str,str,str,str,str]],str,List[Tuple[str,str,str]]]]
            i.e., list entries of 5-tuples of C,V,originalWordsList,translatedWordsString,translatedWordsList.

        Also produces some other interesting dicts and lists
            and saves them as json files for analysis by other programs
            and also saves some as text files for direct viewing.
        """
        from BibleOrgSys.Internals.InternalBibleBook import cleanUWalignments

        fnPrint( debuggingThisModule, f"analyseUWalignments() for {self.abbreviation}" )
        if BibleOrgSysGlobals.debugFlag or debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 2:
            assert self.uWaligned

        # Firstly, aggregate the alignment data from all of the separate books
        alignedBookCount = 0
        alignedBookList:List[str] = []
        alignedOTBookList:List[str] = []
        alignedDCBookList:List[str] = []
        alignedNTBookList:List[str] = []
        aggregatedAlignmentsList:List[Tuple[str,str,str,list,str,list]] = []
        aggregatedAlignmentsOTList:List[Tuple[str,str,str,list,str,list]] = []
        aggregatedAlignmentsDCList:List[Tuple[str,str,str,list,str,list]] = []
        aggregatedAlignmentsNTList:List[Tuple[str,str,str,list,str,list]] = []
        largeAlignmentsList:List[Tuple[str,str,str,list,str,list]] = []
        alignmentDict:Dict[Tuple[str,str,str],List[Tuple[list,str,list]]] = defaultdict( list )
        alignmentOTDict:Dict[Tuple[str,str,str],List[Tuple[list,str,list]]] = defaultdict( list )
        alignmentDCDict:Dict[Tuple[str,str,str],List[Tuple[list,str,list]]] = defaultdict( list )
        alignmentNTDict:Dict[Tuple[str,str,str],List[Tuple[list,str,list]]] = defaultdict( list )
        for BBB,bookObject in self.books.items():
            if 'uWalignments' in bookObject.__dict__:
                vPrint( 'Never', debuggingThisModule, f"Cleaning alignments for {BBB} and aggregating…" )
                alignedBookList.append( BBB )
                if BibleOrgSysGlobals.loadedBibleBooksCodes.isOldTestament_NR( BBB ):
                    alignedOTBookList.append( BBB )
                elif BibleOrgSysGlobals.loadedBibleBooksCodes.isNewTestament_NR( BBB ):
                    alignedNTBookList.append( BBB )
                elif BibleOrgSysGlobals.loadedBibleBooksCodes.isDeuterocanon_NR( BBB ):
                    alignedDCBookList.append( BBB )
                alignedBookCount += 1

                for C,V,originalWordsList,translatedWordsString,translatedWordsList \
                                    in cleanUWalignments( self.abbreviation, BBB, bookObject.uWalignments):
                    aggregatedAlignmentsList.append( (BBB,C,V,originalWordsList,translatedWordsString,translatedWordsList) )
                    # Best to leave these decisions to the analysis software!
                    # if len(originalWordsList) > OK_ORIGINAL_WORDS_COUNT \
                    # or len(translatedWordsList) > OK_TRANSLATED_WORDS_COUNT:
                    #     largeAlignmentsList.append( (BBB,C,V,originalWordsList,translatedWordsString,translatedWordsList) )

                    ref = f'{BBB}_{C}:{V}' # Must be a str for json (can't be a tuple)
                    # if ref not in alignmentDict: alignmentDict[ref] = []
                    alignmentDict[ref].append( (originalWordsList,translatedWordsString,translatedWordsList) )

                    if BibleOrgSysGlobals.loadedBibleBooksCodes.isOldTestament_NR( BBB ):
                        thisList, thisDict = aggregatedAlignmentsOTList, alignmentOTDict
                    elif BibleOrgSysGlobals.loadedBibleBooksCodes.isNewTestament_NR( BBB ):
                        thisList, thisDict = aggregatedAlignmentsNTList, alignmentNTDict
                    elif BibleOrgSysGlobals.loadedBibleBooksCodes.isDeuterocanon_NR( BBB ):
                        thisList, thisDict = aggregatedAlignmentsDCList, alignmentDCDict
                    thisList.append( (BBB,C,V,originalWordsList,translatedWordsString,translatedWordsList) )
                    # if ref not in thisDict: thisDict[ref] = []
                    thisDict[ref].append( (originalWordsList,translatedWordsString,translatedWordsList) )


        # Preliminary pass to go through the alignment data for the whole Bible
        #   and make a set of all single translated words.
        # Used later to determine which words don't need to be capitalised (sort of works for English at least).
        maxOriginalWords = maxTranslatedWords = 0
        singleTranslatedWordsSet = set()
        for BBB,C,V,originalWordsList,translatedWordsString,translatedWordsList in aggregatedAlignmentsList:
            # dPrint( 'Quiet', debuggingThisModule, f"{BBB} {C}:{V} oWL={len(originalWordsList)} tWS={len(translatedWordsString)} tWL={len(translatedWordsList)}")
            # if len(originalWordsList) == 0: vPrint( 'Quiet', debuggingThisModule, f"tWS='{translatedWordsString}'")
            assert isinstance( BBB, str ) and len(BBB)==3
            assert isinstance( C, str ) and C
            assert isinstance( V, str ) and V
            assert isinstance( originalWordsList, list )
            if not originalWordsList:
                logging.critical( f"{self.abbreviation} {BBB} {C}:{V} is missing original words around '{translatedWordsString}'" )
            assert isinstance( translatedWordsString, str ) and translatedWordsString
            assert isinstance( translatedWordsList, list ) and translatedWordsList

            maxOriginalWords = max( len(originalWordsList), maxOriginalWords )
            maxTranslatedWords = max( len(translatedWordsList), maxTranslatedWords )

            if len(translatedWordsList) == 1:
                singleTranslatedWordsSet.add( translatedWordsString )
        if debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 2:
            vPrint( 'Quiet', debuggingThisModule, f"Have {len(singleTranslatedWordsSet):,} unique single translated words")


        # Second pass to go through the alignment data for the whole Bible
        if debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 2:
            vPrint( 'Quiet', debuggingThisModule, f"Analysing {len(aggregatedAlignmentsList):,} alignment results for {alignedBookCount} {self.abbreviation} books…" )
        originalFormToTransOccurrencesDict:Dict[str,dict] = {}
        originalFormToTransOccurrencesOTDict:Dict[str,dict] = {}
        originalFormToTransOccurrencesDCDict:Dict[str,dict] = {}
        originalFormToTransOccurrencesNTDict:Dict[str,dict] = {}
        originalLemmaToTransOccurrencesDict:Dict[str,dict] = {}
        originalLemmaToTransOccurrencesOTDict:Dict[str,dict] = {}
        originalLemmaToTransOccurrencesDCDict:Dict[str,dict] = {}
        originalLemmaToTransOccurrencesNTDict:Dict[str,dict] = {}
        originalFormToTransAlignmentsDict:Dict[str,list] = defaultdict( list )
        originalFormToTransAlignmentsOTDict:Dict[str,list] = defaultdict( list )
        originalFormToTransAlignmentsDCDict:Dict[str,list] = defaultdict( list )
        originalFormToTransAlignmentsNTDict:Dict[str,list] = defaultdict( list )
        originalLemmaToTransAlignmentsDict:Dict[str,list] = defaultdict( list )
        originalLemmaToTransAlignmentsOTDict:Dict[str,list] = defaultdict( list )
        originalLemmaToTransAlignmentsDCDict:Dict[str,list] = defaultdict( list )
        originalLemmaToTransAlignmentsNTDict:Dict[str,list] = defaultdict( list )
        origStrongsToTransAlignmentsDict:Dict[str,list] = defaultdict( list )
        origStrongsToTransAlignmentsOTDict:Dict[str,list] = defaultdict( list )
        origStrongsToTransAlignmentsDCDict:Dict[str,list] = defaultdict( list )
        origStrongsToTransAlignmentsNTDict:Dict[str,list] = defaultdict( list )
        oneToOneTransToOriginalAlignmentsDict:Dict[str,list] = defaultdict( list )
        oneToOneTransToOriginalAlignmentsOTDict:Dict[str,list] = defaultdict( list )
        oneToOneTransToOriginalAlignmentsDCDict:Dict[str,list] = defaultdict( list )
        oneToOneTransToOriginalAlignmentsNTDict:Dict[str,list] = defaultdict( list )
        for BBB,C,V,originalWordsList,translatedWordsString,translatedWordsList in aggregatedAlignmentsList:
            # dPrint( 'Quiet', debuggingThisModule, f"{BBB} {C}:{V} oWL={len(originalWordsList)} tWS={len(translatedWordsString)} tWL={len(translatedWordsList)}")
            # if len(originalWordsList) == 0: vPrint( 'Quiet', debuggingThisModule, f"tWS='{translatedWordsString}'")
            # assert isinstance( BBB, str ) and len(BBB)==3
            # assert isinstance( C, str ) and C
            # assert isinstance( V, str ) and V
            # assert isinstance( originalWordsList, list )
            # if not originalWordsList:
            #     logging.critical( f"{self.abbreviation} {BBB} {C}:{V} is missing original words around '{translatedWordsString}'" )
            # assert isinstance( translatedWordsString, str ) and translatedWordsString
            # assert isinstance( translatedWordsList, list ) and translatedWordsList

            # maxOriginalWords = max( len(originalWordsList), maxOriginalWords )
            # maxTranslatedWords = max( len(translatedWordsList), maxTranslatedWords )

            # For counting occurrences (not alignments), remove ellipsis (non-continguous words joiner)
            cleanedTranslatedWordsString = translatedWordsString.replace( ' … ', ' ' )

            if len(originalWordsList) == 1:
                thisOrigEntry = originalWordsList[0]
                thisOrigStrongs, thisoriginalLemma, thisoriginalWord = thisOrigEntry[0], thisOrigEntry[1], thisOrigEntry[5]
                thisOriginalWordPlusLemma = f'{thisoriginalWord}~~{thisoriginalLemma}'

                if thisOriginalWordPlusLemma not in originalFormToTransOccurrencesDict:
                    originalFormToTransOccurrencesDict[thisOriginalWordPlusLemma] = {cleanedTranslatedWordsString:1}
                elif cleanedTranslatedWordsString in originalFormToTransOccurrencesDict[thisOriginalWordPlusLemma]:
                    originalFormToTransOccurrencesDict[thisOriginalWordPlusLemma][cleanedTranslatedWordsString] += 1
                else:
                    originalFormToTransOccurrencesDict[thisOriginalWordPlusLemma][cleanedTranslatedWordsString] = 1
                assert isinstance( originalFormToTransOccurrencesDict[thisOriginalWordPlusLemma], dict )
                if BibleOrgSysGlobals.loadedBibleBooksCodes.isOldTestament_NR( BBB ):
                    thisDict = originalFormToTransOccurrencesOTDict
                elif BibleOrgSysGlobals.loadedBibleBooksCodes.isNewTestament_NR( BBB ):
                    thisDict = originalFormToTransOccurrencesNTDict
                elif BibleOrgSysGlobals.loadedBibleBooksCodes.isDeuterocanon_NR( BBB ):
                    thisDict = originalFormToTransOccurrencesDCDict
                if thisOriginalWordPlusLemma not in thisDict:
                    thisDict[thisOriginalWordPlusLemma] = {cleanedTranslatedWordsString:1}
                elif cleanedTranslatedWordsString in thisDict[thisOriginalWordPlusLemma]:
                    thisDict[thisOriginalWordPlusLemma][cleanedTranslatedWordsString] += 1
                else:
                    thisDict[thisOriginalWordPlusLemma][cleanedTranslatedWordsString] = 1

                if thisoriginalLemma not in originalLemmaToTransOccurrencesDict:
                    originalLemmaToTransOccurrencesDict[thisoriginalLemma] = {cleanedTranslatedWordsString:1}
                elif cleanedTranslatedWordsString in originalLemmaToTransOccurrencesDict[thisoriginalLemma]:
                    originalLemmaToTransOccurrencesDict[thisoriginalLemma][cleanedTranslatedWordsString] += 1
                else:
                    originalLemmaToTransOccurrencesDict[thisoriginalLemma][cleanedTranslatedWordsString] = 1
                assert isinstance( originalLemmaToTransOccurrencesDict[thisoriginalLemma], dict )
                if BibleOrgSysGlobals.loadedBibleBooksCodes.isOldTestament_NR( BBB ):
                    thisDict = originalLemmaToTransOccurrencesOTDict
                elif BibleOrgSysGlobals.loadedBibleBooksCodes.isNewTestament_NR( BBB ):
                    thisDict = originalLemmaToTransOccurrencesNTDict
                elif BibleOrgSysGlobals.loadedBibleBooksCodes.isDeuterocanon_NR( BBB ):
                    thisDict = originalLemmaToTransOccurrencesDCDict
                if thisoriginalLemma not in thisDict:
                    thisDict[thisoriginalLemma] = {cleanedTranslatedWordsString:1}
                elif cleanedTranslatedWordsString in thisDict[thisoriginalLemma]:
                    thisDict[thisoriginalLemma][cleanedTranslatedWordsString] += 1
                else:
                    thisDict[thisoriginalLemma][cleanedTranslatedWordsString] = 1

                originalFormToTransAlignmentsDict[thisOriginalWordPlusLemma].append( (BBB,C,V,translatedWordsString) )
                if BibleOrgSysGlobals.loadedBibleBooksCodes.isOldTestament_NR( BBB ):
                    thisDict = originalFormToTransAlignmentsOTDict
                elif BibleOrgSysGlobals.loadedBibleBooksCodes.isNewTestament_NR( BBB ):
                    thisDict = originalFormToTransAlignmentsNTDict
                elif BibleOrgSysGlobals.loadedBibleBooksCodes.isDeuterocanon_NR( BBB ):
                    thisDict = originalFormToTransAlignmentsDCDict
                thisDict[thisOriginalWordPlusLemma].append( (BBB,C,V,translatedWordsString) )

                originalLemmaToTransAlignmentsDict[thisoriginalLemma].append( (BBB,C,V,translatedWordsString) )
                if BibleOrgSysGlobals.loadedBibleBooksCodes.isOldTestament_NR( BBB ):
                    thisDict = originalLemmaToTransAlignmentsOTDict
                elif BibleOrgSysGlobals.loadedBibleBooksCodes.isNewTestament_NR( BBB ):
                    thisDict = originalLemmaToTransAlignmentsNTDict
                elif BibleOrgSysGlobals.loadedBibleBooksCodes.isDeuterocanon_NR( BBB ):
                    thisDict = originalLemmaToTransAlignmentsDCDict
                thisDict[thisoriginalLemma].append( (BBB,C,V,translatedWordsString) )

                origStrongsToTransAlignmentsDict[thisOrigStrongs].append( (BBB,C,V,translatedWordsString) )
                if BibleOrgSysGlobals.loadedBibleBooksCodes.isOldTestament_NR( BBB ):
                    thisDict = origStrongsToTransAlignmentsOTDict
                elif BibleOrgSysGlobals.loadedBibleBooksCodes.isNewTestament_NR( BBB ):
                    thisDict = origStrongsToTransAlignmentsNTDict
                elif BibleOrgSysGlobals.loadedBibleBooksCodes.isDeuterocanon_NR( BBB ):
                    thisDict = origStrongsToTransAlignmentsDCDict
                thisDict[thisOrigStrongs].append( (BBB,C,V,translatedWordsString) )

            else: # len(originalWordsList) > 1:
                # TODO: Find/count multi-word forms!!!
                pass

            if len(translatedWordsList) == 1:
                thistranslatedWordEntry = translatedWordsList[0]
                thistranslatedWord = thistranslatedWordEntry[0]
                thistranslatedWordLower = thistranslatedWord.lower()
                if thistranslatedWordLower!=thistranslatedWord:
                    # Lowercase form of word differs from the present case
                    #   -- it could be a proper name or it might have just started a sentence
                    if thistranslatedWordLower in singleTranslatedWordsSet \
                    or thistranslatedWord in ( # words that didn't appear in uncapitalised form in the text
                                'Accompanying','Alas','Amen',
                                'Beyond','Chase','Dismiss'): # special cases -- Grrrh!!!
                        # TODO: Maybe could use an English dictionary here ???
                        # Then maybe this word was only capitalised because it started a sentence???
                        if debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 3:
                            vPrint( 'Quiet', debuggingThisModule, f"  Investigating '{thistranslatedWord}' from {originalWordsList}…")
                        combinedMorphString = ' + '.join( (x[2] for x in originalWordsList) )
                        if debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 3:
                            vPrint( 'Quiet', debuggingThisModule, f"    combinedMorphString='{combinedMorphString}'")
                        if ',Np' not in combinedMorphString \
                        and thistranslatedWord not in ('God','Lord','Father',): # special words which might intentionally occur in both cases
                            # Not a Hebrew proper noun -- don't have anything similar for Greek unfortunately
                            if debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 2:
                                vPrint( 'Quiet', debuggingThisModule, f"    Converting '{thistranslatedWord}' to '{thistranslatedWordLower}'")
                            thistranslatedWord = thistranslatedWordLower
                        else:
                            if debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 3:
                                vPrint( 'Quiet', debuggingThisModule, f"    Not converting exception '{thistranslatedWord}'")
                    else:
                        if debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 3:
                            vPrint( 'Quiet', debuggingThisModule, f"    Not converting '{thistranslatedWord}'")

                oneToOneTransToOriginalAlignmentsDict[thistranslatedWord].append( (BBB,C,V,originalWordsList) )
                if BibleOrgSysGlobals.loadedBibleBooksCodes.isOldTestament_NR( BBB ):
                    thisDict = oneToOneTransToOriginalAlignmentsOTDict
                elif BibleOrgSysGlobals.loadedBibleBooksCodes.isNewTestament_NR( BBB ):
                    thisDict = oneToOneTransToOriginalAlignmentsNTDict
                elif BibleOrgSysGlobals.loadedBibleBooksCodes.isDeuterocanon_NR( BBB ):
                    thisDict = oneToOneTransToOriginalAlignmentsDCDict
                thisDict[thistranslatedWord].append( (BBB,C,V,originalWordsList) )

            else: # len(translatedWordsList) > 1:
                # TODO: Find/count multi-word forms!!!
                pass

        if debuggingThisModule and BibleOrgSysGlobals.debugFlag:
            max_each = 6
            vPrint( 'Quiet', debuggingThisModule, f"\nHave {len(originalFormToTransOccurrencesDict):,} form occurrences" )
            for j, (key,value) in enumerate( originalFormToTransOccurrencesDict.items(), start=1 ):
                vPrint( 'Quiet', debuggingThisModule, f"{j} {key} = {value if len(value)<200 else len(value)}" )
                assert isinstance( key, str )
                assert isinstance( value, dict )
                if j > max_each: break
            vPrint( 'Quiet', debuggingThisModule, f"\nHave {len(originalLemmaToTransOccurrencesDict):,} lemma occurrences" )
            for j, (key,value) in enumerate( originalLemmaToTransOccurrencesDict.items(), start=1 ):
                vPrint( 'Quiet', debuggingThisModule, f"{j} {key} = {value if len(value)<200 else len(value)}" )
                assert isinstance( key, str )
                assert isinstance( value, dict )
                if j > max_each: break
            vPrint( 'Quiet', debuggingThisModule, f"\nHave {len(originalFormToTransAlignmentsDict):,} form alignments" )
            for j, (key,value) in enumerate( originalFormToTransAlignmentsDict.items(), start=1 ):
                vPrint( 'Quiet', debuggingThisModule, f"{j} {key} = {value if len(value)<200 else len(value)}" )
                assert isinstance( key, str )
                assert isinstance( value, list )
                if j > max_each: break
            vPrint( 'Quiet', debuggingThisModule, f"\nHave {len(originalLemmaToTransAlignmentsDict):,} lemma alignments" )
            for j, (key,value) in enumerate( originalLemmaToTransAlignmentsDict.items(), start=1 ):
                vPrint( 'Quiet', debuggingThisModule, f"{j} {key} = {value if len(value)<200 else len(value)}" )
                assert isinstance( key, str )
                assert isinstance( value, list )
                if j > max_each: break
            vPrint( 'Quiet', debuggingThisModule, f"\nHave {len(origStrongsToTransAlignmentsDict):,} Strongs alignments" )
            for j, (key,value) in enumerate( origStrongsToTransAlignmentsDict.items(), start=1 ):
                vPrint( 'Quiet', debuggingThisModule, f"{j} {key} = {value if len(value)<200 else len(value)}" )
                assert isinstance( key, str )
                assert isinstance( value, list )
                if j > max_each: break
            vPrint( 'Quiet', debuggingThisModule, f"\nHave {len(oneToOneTransToOriginalAlignmentsDict):,} word reverse alignments" )
            for j, (key,value) in enumerate( oneToOneTransToOriginalAlignmentsDict.items(), start=1 ):
                vPrint( 'Quiet', debuggingThisModule, f"{j} {key} = {value if len(value)<200 else len(value)}" )
                assert isinstance( key, str )
                assert isinstance( value, list )
                if j > max_each: break

        self.uWalignments:Dict[str,Dict[str,list]] = {}
        self.uWalignments['originalFormToTransOccurrencesDict'] = originalFormToTransOccurrencesDict
        self.uWalignments['originalFormToTransAlignmentsDict'] = originalFormToTransAlignmentsDict
        self.uWalignments['originalLemmaToTransAlignmentsDict'] = originalLemmaToTransAlignmentsDict
        self.uWalignments['origStrongsToTransAlignmentsDict'] = origStrongsToTransAlignmentsDict
        self.uWalignments['oneToOneTransToOriginalAlignmentsDict'] = oneToOneTransToOriginalAlignmentsDict

        # Save the original list and all the derived dictionaries for any futher analysis/processing
        import json
        outputFolderpath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'unfoldingWordAlignments/' )
        try: os.makedirs( outputFolderpath )
        except FileExistsError: pass
        for dataObject, objectName in (
                (alignedBookList, 'alignedBookList'),
                    (alignedOTBookList, 'alignedOTBookList'),
                    (alignedDCBookList, 'alignedDCBookList'),
                    (alignedNTBookList, 'alignedNTBookList'),
                (aggregatedAlignmentsList, 'aggregatedAlignmentsList'),
                    (aggregatedAlignmentsOTList, 'aggregatedAlignmentsOTList'),
                    (aggregatedAlignmentsDCList, 'aggregatedAlignmentsDCList'),
                    (aggregatedAlignmentsNTList, 'aggregatedAlignmentsNTList'),
                (alignmentDict, 'alignmentDict'),
                    (alignmentOTDict, 'alignmentOTDict'),
                    (alignmentDCDict, 'alignmentDCDict'),
                    (alignmentNTDict, 'alignmentNTDict'),
                (originalFormToTransOccurrencesDict, 'originalFormToTransOccurrencesDict'),
                    (originalFormToTransOccurrencesOTDict, 'originalFormToTransOccurrencesOTDict'),
                    (originalFormToTransOccurrencesDCDict, 'originalFormToTransOccurrencesDCDict'),
                    (originalFormToTransOccurrencesNTDict, 'originalFormToTransOccurrencesNTDict'),
                (originalLemmaToTransOccurrencesDict, 'originalLemmaToTransOccurrencesDict'),
                    (originalLemmaToTransOccurrencesOTDict, 'originalLemmaToTransOccurrencesOTDict'),
                    (originalLemmaToTransOccurrencesDCDict, 'originalLemmaToTransOccurrencesDCDict'),
                    (originalLemmaToTransOccurrencesNTDict, 'originalLemmaToTransOccurrencesNTDict'),
                (originalFormToTransAlignmentsDict, 'originalFormToTransAlignmentsDict'),
                    (originalFormToTransAlignmentsOTDict, 'originalFormToTransAlignmentsOTDict'),
                    (originalFormToTransAlignmentsDCDict, 'originalFormToTransAlignmentsDCDict'),
                    (originalFormToTransAlignmentsNTDict, 'originalFormToTransAlignmentsNTDict'),
                (originalLemmaToTransAlignmentsDict, 'originalLemmaToTransAlignmentsDict'),
                    (originalLemmaToTransAlignmentsOTDict, 'originalLemmaToTransAlignmentsOTDict'),
                    (originalLemmaToTransAlignmentsDCDict, 'originalLemmaToTransAlignmentsDCDict'),
                    (originalLemmaToTransAlignmentsNTDict, 'originalLemmaToTransAlignmentsNTDict'),
                (origStrongsToTransAlignmentsDict, 'originalStrongsToTransAlignmentsDict'),
                    (origStrongsToTransAlignmentsOTDict, 'originalStrongsToTransAlignmentsOTDict'),
                    (origStrongsToTransAlignmentsDCDict, 'originalStrongsToTransAlignmentsDCDict'),
                    (origStrongsToTransAlignmentsNTDict, 'originalStrongsToTransAlignmentsNTDict'),
                (oneToOneTransToOriginalAlignmentsDict, 'oneToOneTransToOriginalAlignmentsDict'),
                    (oneToOneTransToOriginalAlignmentsOTDict, 'oneToOneTransToOriginalAlignmentsOTDict'),
                    (oneToOneTransToOriginalAlignmentsDCDict, 'oneToOneTransToOriginalAlignmentsDCDict'),
                    (oneToOneTransToOriginalAlignmentsNTDict, 'oneToOneTransToOriginalAlignmentsNTDict'),
                ):
            assert isinstance( dataObject, (dict,list) )
            if dataObject: # Don't write blank files
                with open( outputFolderpath.joinpath( f'{self.abbreviation}_{objectName}.json' ), 'wt' ) as xf:
                    json.dump( dataObject, xf )

        # Save some text files for manually looking through
        with open( outputFolderpath.joinpath( f'{self.abbreviation}_TransOccurrences.byForm.txt' ), 'wt' ) as xf:
            for originalWord in sorted(originalFormToTransOccurrencesDict, key=lambda theWord: theWord.lower()):
                assert isinstance( originalWord, str )
                assert originalWord
                translations = originalFormToTransOccurrencesDict[originalWord]
                #dPrint( 'Quiet', debuggingThisModule, "translations", translations ) # dict of word: numOccurrences
                assert isinstance( translations, dict )
                for translation,tCount in translations.items():
                    assert isinstance( translation, str )
                    assert isinstance( tCount, int )
                    #dPrint( 'Quiet', debuggingThisModule, "translation", translation, "tCount", tCount )
                    #dPrint( 'Quiet', debuggingThisModule, f"For '{originalWord}', have {translation}: {tCount}" )
                    if tCount == 1: # Let's find the reference
                        refList = originalFormToTransAlignmentsDict[originalWord] # List of 4-tuples B,C,V,translation
                        #dPrint( 'Quiet', debuggingThisModule, "refList1", refList )
                        assert isinstance( refList, list )
                        for ref in refList:
                            #dPrint( 'Quiet', debuggingThisModule, "ref", ref )
                            assert isinstance( ref, tuple )
                            assert len(ref) == 4
                            if ref[3] == translation:
                                translations[translation] = f'{ref[0]}_{ref[1]}:{ref[2]}'
                                #dPrint( 'Quiet', debuggingThisModule, f"Now '{originalWord}', have {translations}" )
                                break
                xf.write( f"'{originalWord}' translated as {str(translations).replace(': ',':')}\n" )
        #dPrint( 'Quiet', debuggingThisModule, "keys", originalLemmaToTransOccurrencesDict.keys() )
        #dPrint( 'Quiet', debuggingThisModule, "\n", sorted(originalLemmaToTransOccurrencesDict, key=lambda theLemma: theLemma.lower()) )
        #dPrint( 'Quiet', debuggingThisModule, "blank", originalLemmaToTransOccurrencesDict[''] )
        with open( outputFolderpath.joinpath( f'{self.abbreviation}_TransOccurrences.byLemma.txt' ), 'wt' ) as xf:
            for originalLemma in sorted(originalLemmaToTransOccurrencesDict, key=lambda theLemma: theLemma.lower()):
                assert isinstance( originalLemma, str )
                #assert originalLemma # NO, THESE CAN BE BLANK
                translations = originalLemmaToTransOccurrencesDict[originalLemma]
                #dPrint( 'Quiet', debuggingThisModule, "translations", translations ) # dict of word: numOccurrences
                assert isinstance( translations, dict )
                for translation,tCount in translations.items():
                    assert isinstance( translation, str )
                    assert isinstance( tCount, int )
                    #dPrint( 'Quiet', debuggingThisModule, "translation", translation, "tCount", tCount )
                    #dPrint( 'Quiet', debuggingThisModule, f"For '{originalLemma}', have {translation}: {tCount}" )
                    if tCount == 1: # Let's find the reference
                        refList = originalLemmaToTransAlignmentsDict[originalLemma] # List of 4-tuples B,C,V,translation
                        #dPrint( 'Quiet', debuggingThisModule, "refList2", refList )
                        assert isinstance( refList, list )
                        for ref in refList:
                            #dPrint( 'Quiet', debuggingThisModule, "ref", ref )
                            assert isinstance( ref, tuple )
                            assert len(ref) == 4
                            if ref[3] == translation:
                                translations[translation] = f'{ref[0]}_{ref[1]}:{ref[2]}'
                                #dPrint( 'Quiet', debuggingThisModule, f"Now '{originalLemma}', have {translations}" )
                                break
                xf.write( f"'{originalLemma}' translated as {str(translations).replace(': ',':')}\n" )

        # Best to make these decisions in the analysis -- not here
        # if self.abbreviation == 'ULT':
        #     with open( outputFolderpath.joinpath( f'{self.abbreviation}_LargeAggregates.byBCV.txt' ), 'wt' ) as xf:
        #         fromList, toList = [], []
        #         for BBB,C,V,originalWordsList,translatedWordsString,translatedWordsList in aggregatedAlignmentsList:
        #             if len(originalWordsList) == 1:
        #                 originalWordsCountStr = ''
        #                 originalWordsStr = originalWordsList[0]
        #             else:
        #                 originalWordsCountStr = f' ({len(originalWordsList)} words)'
        #                 originalWordsStr = f"'{' '.join( (entry[5] for entry in originalWordsList) )}'"
        #             outputString = f"{BBB} {C}:{V} '{translatedWordsString}'" \
        #                             f" ({len(translatedWordsList)} word{'' if len(translatedWordsList)==1 else 's'})" \
        #                             f" from{originalWordsCountStr} {originalWordsStr}\n"
        #             if len(originalWordsList) > OK_ORIGINAL_WORDS_COUNT:
        #                 fromList.append( (len(originalWordsList),outputString) )
        #             if len(translatedWordsList) > OK_TRANSLATED_WORDS_COUNT:
        #                 toList.append( (len(translatedWordsList),outputString) )
        #             if len(originalWordsList) > OK_ORIGINAL_WORDS_COUNT \
        #             or len(translatedWordsList) > OK_TRANSLATED_WORDS_COUNT:
        #                 xf.write( outputString )
        #     with open( outputFolderpath.joinpath( f'{self.abbreviation}_LargeAggregates.byOriginalCount.txt' ), 'wt' ) as xf:
        #         for count,outputString in sorted( fromList, reverse=True ):
        #             xf.write( outputString )
        #     with open( outputFolderpath.joinpath( f'{self.abbreviation}_LargeAggregates.byTranslatedCount.txt' ), 'wt' ) as xf:
        #         for count,outputString in sorted( toList, reverse=True ):
        #             xf.write( outputString )

        if debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 1:
            vPrint( 'Quiet', debuggingThisModule, f"Have {len(aggregatedAlignmentsList):,} alignment entries for {self.abbreviation}" )
            vPrint( 'Quiet', debuggingThisModule, f"  Maximum of {maxOriginalWords} original language words in one {self.abbreviation} entry" )
            vPrint( 'Quiet', debuggingThisModule, f"  Maximum of {maxTranslatedWords} translated words in one {self.abbreviation} entry" )
        #halt
    # end of InternalBible.analyseUWalignments
# end of class InternalBible



def briefDemo() -> None:
    """
    A very basic test/demo of the InternalBible class.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, programNameVersion, LAST_MODIFIED_DATE )

    # Since this is only designed to be a base class, it can't actually do much at all
    IB = InternalBible()
    IB.objectNameString = 'Dummy test Internal Bible object'
    vPrint( 'Quiet', debuggingThisModule, IB )

    # But we'll load a USFM Bible so we can test some other functions
    from BibleOrgSys.UnknownBible import UnknownBible
    from BibleOrgSys.Bible import Bible
    testFolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PTX8Test2/' )
    uB = UnknownBible( testFolder )
    result = uB.search( autoLoadAlways=True, autoLoadBooks=True )
    vPrint( 'Normal', debuggingThisModule, "IB Test", result )
    if isinstance( result, Bible ):
        iB = result
        if BibleOrgSysGlobals.strictCheckingFlag:
            iB.check()
            IBErrors = iB.getCheckResults()
            vPrint( 'Info', debuggingThisModule, IBErrors )
        iB.doExtensiveChecks()

        if 0:
            searchOptions = {}
            searchOptions['bookList'] = None #['JNA','PE1']
            searchOptions['chapterList'] = None #[0]
            for searchString in ( "keen", "Keen", "junk", ):
                vPrint( 'Quiet', debuggingThisModule, "\n{}:".format( searchString ) )
                searchOptions['findText'] = searchString
                searchOptions['wordMode'] = 'Any'
                searchOptions['caselessFlag'] = False
                optionsDict, resultSummaryDict, sResult = iB.findText( searchOptions )
                adjResult = '({}) {}'.format( len(sResult), sResult if len(sResult)<20 else str(sResult[:20])+' …' )
                if BibleOrgSysGlobals.verbosityLevel > 0:
                    vPrint( 'Quiet', debuggingThisModule, "\n  sResult for {!r} is {}  {}".format( searchString, resultSummaryDict, adjResult ) )
                searchOptions['wordMode'] = 'Whole'
                optionsDict, resultSummaryDict, sResult = iB.findText( searchOptions )
                adjResult = '({}) {}'.format( len(sResult), sResult if len(sResult)<20 else str(sResult[:20])+' …' )
                if BibleOrgSysGlobals.verbosityLevel > 0:
                    vPrint( 'Quiet', debuggingThisModule, "\n  sResult for whole word {!r} is {}  {}".format( searchString, resultSummaryDict, adjResult ) )
                searchOptions['wordMode'] = 'Any'
                searchOptions['caselessFlag'] = True
                optionsDict, resultSummaryDict, sResult = iB.findText( searchOptions )
                adjResult = '({}) {}'.format( len(sResult), sResult if len(sResult)<20 else str(sResult[:20])+' …' )
                if BibleOrgSysGlobals.verbosityLevel > 0:
                    vPrint( 'Quiet', debuggingThisModule, "\n  sResult for caseless {!r} is {}  {}".format( searchString, resultSummaryDict, adjResult ) )
# end of InternalBible.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, programNameVersion, LAST_MODIFIED_DATE )

    # Since this is only designed to be a base class, it can't actually do much at all
    IB = InternalBible()
    IB.objectNameString = 'Dummy test Internal Bible object'
    vPrint( 'Quiet', debuggingThisModule, IB )

    # But we'll load a USFM Bible so we can test some other functions
    from BibleOrgSys.UnknownBible import UnknownBible
    from BibleOrgSys.Bible import Bible
    testFolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PTX8Test2/' )
    uB = UnknownBible( testFolder )
    result = uB.search( autoLoadAlways=True, autoLoadBooks=True )
    vPrint( 'Normal', debuggingThisModule, "IB Test", result )
    if isinstance( result, Bible ):
        iB = result
        if BibleOrgSysGlobals.strictCheckingFlag:
            iB.check()
            IBErrors = iB.getCheckResults()
            vPrint( 'Info', debuggingThisModule, IBErrors )
        iB.doExtensiveChecks()

        if 0:
            searchOptions = {}
            searchOptions['bookList'] = None #['JNA','PE1']
            searchOptions['chapterList'] = None #[0]
            for searchString in ( "keen", "Keen", "junk", ):
                vPrint( 'Quiet', debuggingThisModule, "\n{}:".format( searchString ) )
                searchOptions['findText'] = searchString
                searchOptions['wordMode'] = 'Any'
                searchOptions['caselessFlag'] = False
                optionsDict, resultSummaryDict, sResult = iB.findText( searchOptions )
                adjResult = '({}) {}'.format( len(sResult), sResult if len(sResult)<20 else str(sResult[:20])+' …' )
                if BibleOrgSysGlobals.verbosityLevel > 0:
                    vPrint( 'Quiet', debuggingThisModule, "\n  sResult for {!r} is {}  {}".format( searchString, resultSummaryDict, adjResult ) )
                searchOptions['wordMode'] = 'Whole'
                optionsDict, resultSummaryDict, sResult = iB.findText( searchOptions )
                adjResult = '({}) {}'.format( len(sResult), sResult if len(sResult)<20 else str(sResult[:20])+' …' )
                if BibleOrgSysGlobals.verbosityLevel > 0:
                    vPrint( 'Quiet', debuggingThisModule, "\n  sResult for whole word {!r} is {}  {}".format( searchString, resultSummaryDict, adjResult ) )
                searchOptions['wordMode'] = 'Any'
                searchOptions['caselessFlag'] = True
                optionsDict, resultSummaryDict, sResult = iB.findText( searchOptions )
                adjResult = '({}) {}'.format( len(sResult), sResult if len(sResult)<20 else str(sResult[:20])+' …' )
                if BibleOrgSysGlobals.verbosityLevel > 0:
                    vPrint( 'Quiet', debuggingThisModule, "\n  sResult for caseless {!r} is {}  {}".format( searchString, resultSummaryDict, adjResult ) )
# end of InternalBible.fullDemo

if __name__ == '__main__':
    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of InternalBible.py
