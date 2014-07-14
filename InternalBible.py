#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# InternalBible.py
#   Last modified: 2014-07-15 by RJH (also update ProgVersion below)
#
# Module handling the USFM markers for Bible books
#
# Copyright (C) 2010-2014 Robert Hunt
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
Module for defining and manipulating Bibles in our internal USFM-based 'lines' format.

The calling class needs to call this base class __init__ routine and also set:
    self.objectTypeString (e.g., "USFM" or "USX")
    self.objectNameString (with a description of the type of Bible object, e.g., "USFM Bible object")

It also needs to provide a "load" routine that sets any of the relevant fields:
    self.sourceFolder, self.sourceFilename, self.sourceFilepath, self.fileExtension
    self.name, self.givenName, self.shortName, self.abbreviation
    self.status, self.revision, self.version

If you have access to any metadata, that goes in
    self.ssfFilepath, self.ssfDict, self.settingsDict

and then fills
    self.books by calling saveBook() which updates:
        self.BBBToNameDict, self.bookNameDict, self.combinedBookNameDict
"""

ProgName = "Internal Bible handler"
ProgVersion = "0.46"
ProgNameVersion = "{} v{}".format( ProgName, ProgVersion )

debuggingThisModule = False


import os, logging
from gettext import gettext as _
from collections import OrderedDict

import Globals
from InternalBibleInternals import InternalBibleEntryList



class InternalBible:
    """
    Class to define and manipulate InternalBibles.

    This class contains no load function -- that is expected to be supplied by the superclass.
    """
    def __init__( self ):
        """
        Create the object.
        """
        # Set up empty variables for the object
        #       some of which will be filled in later depending on what is known from the Bible type
        self.name = self.givenName = self.shortName = self.abbreviation = None
        self.sourceFolder = self.sourceFilename = self.sourceFilepath = self.fileExtension = None
        self.status = self.revision = self.version = None

        # Set up empty containers for the object
        self.books = OrderedDict()
        self.ssfFilepath, self.ssfDict, self.settingsDict = '', {}, {}
        self.BBBToNameDict, self.bookNameDict, self.combinedBookNameDict, self.bookAbbrevDict = {}, {}, {}, {} # Used to store book name and abbreviations (pointing to the BBB codes)
        self.reverseDict, self.guesses = {}, '' # A program history
        self.triedLoadingBook = {}
        self.divisions = OrderedDict()
        self.errorDictionary = OrderedDict()
        self.errorDictionary['Priority Errors'] = [] # Put this one first in the ordered dictionary
    # end of InternalBible.__init_


    def __getNames( self ):
        """
        Try to improve our names.
        """
        if not self.abbreviation and 'WorkAbbreviation' in self.settingsDict: self.abbreviation = self.settingsDict['WorkAbbreviation']
        if not self.name and 'FullName' in self.ssfDict: self.name = self.ssfDict['FullName']
        if not self.shortName and 'Name' in self.ssfDict: self.shortName = self.ssfDict['Name']
        self.projectName = self.name if self.name else "Unknown"
    # end of __getNames


    def doPostLoadProcessing( self ):
        """
        This method should be called once all books are loaded.
        """
        # Try to improve our names (may also be called from loadMetadataFile)
        self.__getNames()

        # Discover what we've got loaded so we don't have to worry about doing it later
        self.discover()
    # end of doPostLoadProcessing


    def loadMetadataFile( self, mdFilepath ):
        """
        Load the fields from the given metadata text file.
        """
        def saveMD( fieldName, contents ):
            """
            Save an entry in the settings dictionary
                but check for duplicates first.
            """
            if fieldName in self.settingsDict: # We have a duplicate
                logging.warning("About to replace {}={} from metadata file".format( repr(fieldName), repr(self.settingsDict[fieldName]) ) )
            else: # Also check for "duplicates" with a different case
                ucFieldName = fieldName.upper()
                for key in self.settingsDict:
                    ucKey = key.upper()
                    if ucKey == ucFieldName:
                        logging.warning("About to add {} from metadata file even though already have {}".format( repr(fieldName), repr(key) ) )
                        break
            self.settingsDict[fieldName] = Globals.makeSafeString( contents )
        # end of saveMD

        logging.info( "Loading supplied project metadata..." )
        if Globals.verbosityLevel > 1: print( "Loading supplied project metadata..." )
        if Globals.verbosityLevel > 2: print( "Old metadata settings", len(self.settingsDict), self.settingsDict )
        lineCount, continuedFlag = 0, False
        with open( mdFilepath, 'rt' ) as mdFile:
            for line in mdFile:
                while line and line[-1] in '\n\r': line=line[:-1] # Remove trailing newline characters (Linux or Windows)
                #print( "MD line: '{}'".format( line ) )
                if not line: continue # Just discard additional blank lines
                lineCount += 1
                if line[0] == '#': continue # Just discard comment lines
                if not continuedFlag:
                    if '=' not in line:
                        logging.warning( "Missing equals sign from metadata line (ignored): {}".format( repr(line) ) )
                    else: # Seems like a field=something type line
                        bits = line.split( '=', 1 )
                        assert( len(bits) == 2 )
                        fieldName = bits[0]
                        fieldContents = bits[1]
                        if fieldContents.endswith( '\\' ):
                            continuedFlag = True
                            fieldContents = fieldContents[:-1] # Remove the continuation character
                        else: saveMD( fieldName, fieldContents )
                else: # continuedFlag
                    if line.endswith( '\\' ): line = line[:-1] # Remove the continuation character
                    else: continuedFlag = False
                    fieldContents += line
                    if not continuedFlag: saveMD( fieldName, fieldContents )
            if Globals.verbosityLevel > 1: print( "  {} non-blank lines read from uploaded metadata file".format( lineCount ) )
        if Globals.verbosityLevel > 2: print( "New metadata settings", len(self.settingsDict), self.settingsDict )

        # Try to improve our names (also called earlier from doPostLoadProcessing)
        self.__getNames()
    # end of loadMetadataFile




    def __str__( self ):
        """
        This method returns the string representation of a Bible.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = self.objectNameString
        indent = 2
        if Globals.debugFlag or Globals.verbosityLevel>2: result += ' v' + ProgVersion
        if self.name: result += ('\n' if result else '') + ' '*indent + _("Name: {}").format( self.name )
        if self.sourceFolder: result += ('\n' if result else '') + ' '*indent + _("Source folder: {}").format( self.sourceFolder )
        elif self.sourceFilepath: result += ('\n' if result else '') + ' '*indent + _("Source: {}").format( self.sourceFilepath )
        if self.status: result += ('\n' if result else '') + ' '*indent + _("Status: {}").format( self.status )
        if self.revision: result += ('\n' if result else '') + ' '*indent + _("Revision: {}").format( self.revision )
        if self.version: result += ('\n' if result else '') + ' '*indent + _("Version: {}").format( self.version )
        result += ('\n' if result else '') + ' '*indent + _("Number of books: {}{}") \
                                        .format( len(self.books), " {}".format( self.getBookList() ) if 0<len(self.books)<5 else '' )
        return result
    # end of InternalBible.__str__


    def __len__( self ):
        """
        This method returns the number of books in the Bible.
        """
        return len( self.books )
    # end of InternalBible.__len__


    def __contains__( self, BBB ):
        """
        This method checks whether the Bible contains the BBB book.
        Returns True or False.
        """
        if Globals.debugFlag: assert( isinstance(BBB,str) and len(BBB)==3 )
        return BBB in self.books
    # end of InternalBible.__contains__


    def __getitem__( self, keyIndex ):
        """
        Given an index integer, return the book object (or raise an IndexError)

        This function also accepts a BBB so you can use it to get a book from the Bible by BBB.
        """
        #print( "InternalBible.__getitem__( {} )".format( keyIndex ) )
        #print( list(self.books.items()) )
        if isinstance( keyIndex, int ):
            return list(self.books.items())[keyIndex][1] # element 0 is BBB, element 1 is the book object
        if isinstance( keyIndex, str ) and len(keyIndex)==3: # assume it's a BBB
            return self.books[keyIndex]
    # end of InternalBible.__getitem__


    def __iter__( self ):
        """ Yields the next book object. """
        for BBB in self.books:
            yield self.books[BBB]
    # end of InternalBible.__iter__


    def getBookList( self ):
        return [BBB for BBB in self.books]


    def pickle( self, filename=None, folder=None ):
        """
        Writes the object to a .pickle file that can be easily loaded into a Python3 program.
            If folder is None (or missing), defaults to the default cache folder specified in Globals.
            Created the folder(s) if necessary.
        """
        #print( "pickle( *, {}, {} )".format( repr(filename), repr(folder ) ) )
        #print( repr(self.objectNameString), repr(self.objectTypeString) )
        #print( (self.abbreviation), repr(self.name) )
        if filename is None:
            filename = self.abbreviation if self.abbreviation else self.name
        if Globals.debugFlag: assert( filename )
        filename = Globals.makeSafeFilename( filename ) + '.pickle'
        if Globals.verbosityLevel > 2:
            print( _("InternalBible.pickle: Saving {} to {}...") \
                .format( self.objectNameString, filename if folder is None else os.path.join( folder, filename ) ) )
        Globals.pickleObject( self, filename, folder )
    # end of InternalBible.pickle


    def getAssumedBookName( self, BBB ):
        """Gets the book name for the given book reference code."""
        if Globals.debugFlag: assert( BBB in Globals.BibleBooksCodes)
        #if BBB in self.BBBToNameDict: return self.BBBToNameDict[BBB] # What was this ???
        try: return self.books[BBB].assumedBookName
        except: return None
    # end of InternalBible.getAssumedBookName


    def getLongTOCName( self, BBB ):
        """Gets the long table of contents book name for the given book reference code."""
        if Globals.debugFlag: assert( BBB in Globals.BibleBooksCodes)
        try: return self.books[BBB].longTOCName
        except: return None
    # end of InternalBible.getLongTOCName


    def getShortTOCName( self, BBB ):
        """Gets the short table of contents book name for the given book reference code."""
        if Globals.debugFlag: assert( BBB in Globals.BibleBooksCodes)
        try: return self.books[BBB].shortTOCName
        except: return None
    # end of InternalBible.getShortTOCName


    def getBooknameAbbreviation( self, BBB ):
        """Gets the book abbreviation for the given book reference code."""
        if Globals.debugFlag: assert( BBB in Globals.BibleBooksCodes)
        try: return self.books[BBB].booknameAbbreviation
        except: return None
    # end of InternalBible.getBooknameAbbreviation


    def saveBook( self, bookData ):
        """
        Save the Bible book into our object
            and uupdate our indexes.
        """
        #print( "saveBook( {} )".format( bookData ) )
        BBB = bookData.BBB
        if BBB in self.books: # already
            logging.critical( "InternalBible.saveBook: " + _("overwriting already existing {} book!").format( BBB ) )
        self.books[BBB] = bookData
        # Make up our book name dictionaries while we're at it
        assumedBookNames = bookData.getAssumedBookNames()
        for assumedBookName in assumedBookNames:
            self.BBBToNameDict[BBB] = assumedBookName
            assumedBookNameLower = assumedBookName.lower()
            self.bookNameDict[assumedBookNameLower] = BBB # Store the deduced book name (just lower case)
            self.combinedBookNameDict[assumedBookNameLower] = BBB # Store the deduced book name (just lower case)
            if ' ' in assumedBookNameLower: self.combinedBookNameDict[assumedBookNameLower.replace(' ','')] = BBB # Store the deduced book name (lower case without spaces)
    # end of InternalBible.saveBook


    def guessXRefBBB( self, referenceString ):
        """
        Attempt to return a book reference code given a book reference code (e.g., 'PRO'),
                a book name (e.g., Proverbs) or abbreviation (e.g., Prv).
            Uses self.combinedBookNameDict and makes and uses self.bookAbbrevDict.
            Return None if unsuccessful."""
        if Globals.debugFlag: assert( referenceString and isinstance( referenceString, str ) )
        result = Globals.BibleBooksCodes.getBBB( referenceString )
        if result is not None: return result # It's already a valid BBB

        adjRefString = referenceString.lower()
        if adjRefString in self.combinedBookNameDict:
            BBB = self.combinedBookNameDict[adjRefString]
            #assert( BBB not in self.reverseDict )
            self.reverseDict[BBB] = referenceString
            return BBB # Found a whole name match
        if adjRefString in self.bookAbbrevDict:
            BBB = self.bookAbbrevDict[adjRefString]
            #print( referenceString, adjRefString, BBB, self.reverseDict )
            #assert( BBB not in self.reverseDict )
            self.reverseDict[BBB] = referenceString
            return BBB # Found a whole abbreviation match

        # Do a program check
        for BBB in self.reverseDict: assert( self.reverseDict[BBB] != referenceString )

        # See if a book name starts with this string
        if Globals.debugFlag and debuggingThisModule: print( "  getXRefBBB using startswith1..." )
        count = 0
        for bookName in self.bookNameDict:
            if bookName.startswith( adjRefString ):
                BBB = self.bookNameDict[bookName]
                count += 1
        if count == 1: # Found exactly one
            self.bookAbbrevDict[adjRefString] = BBB # Save to make it faster next time
            self.guesses += ('\n' if self.guesses else '') + "Guessed '{}' to be {} (startswith1)".format( referenceString, BBB )
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
                self.guesses += ('\n' if self.guesses else '') + "Guessed '{}' to be {} (startswith1SECOND)".format( referenceString, BBB )
                self.reverseDict[BBB] = referenceString
                return BBB
        if Globals.debugFlag and debuggingThisModule and count > 1:
            print( "  getXRefBBB has multiple startswith matches for '{}' in {}".format( adjRefString, self.combinedBookNameDict ) )
        if count == 0:
            if Globals.debugFlag and debuggingThisModule: print( "  getXRefBBB using startswith2..." )
            for bookName in self.combinedBookNameDict:
                if bookName.startswith( adjRefString ):
                    BBB = self.combinedBookNameDict[bookName]
                    count += 1
            if count == 1: # Found exactly one now
                self.bookAbbrevDict[adjRefString] = BBB # Save to make it faster next time
                self.guesses += ('\n' if self.guesses else '') + "Guessed '{}' to be {} (startswith2)".format( referenceString, BBB )
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
                self.guesses += ('\n' if self.guesses else '') + "Guessed '{}' to be {} (startswith2SECOND)".format( referenceString, BBB )
                self.reverseDict[BBB] = referenceString
                return BBB

        # See if a book name contains a word that starts with this string
        if count == 0:
            if Globals.debugFlag and debuggingThisModule: print( "  getXRefBBB using word startswith..." )
            for bookName in self.bookNameDict:
                if ' ' in bookName:
                    for bit in bookName.split():
                        if bit.startswith( adjRefString ):
                            BBB = self.bookNameDict[bookName]
                            count += 1
            if count == 1: # Found exactly one
                self.bookAbbrevDict[adjRefString] = BBB # Save to make it faster next time
                self.guesses += ('\n' if self.guesses else '') + "Guessed '{}' to be {} (word startswith)".format( referenceString, BBB )
                self.reverseDict[BBB] = referenceString
                return BBB
            if Globals.debugFlag and debuggingThisModule and count > 1:
                print( "  getXRefBBB has multiple startswith matches for '{}' in {}".format( adjRefString, self.bookNameDict ) )

        # See if a book name starts with the same letter plus contains the letters in this string (slow)
        if count == 0:
            if Globals.debugFlag and debuggingThisModule: print ("  getXRefBBB using first plus other characters..." )
            for bookName in self.bookNameDict:
                if not bookName: print( self.bookNameDict ); halt # temp...
                #print( "aRS='{}', bN='{}'".format( adjRefString, bookName ) )
                if adjRefString[0] != bookName[0]: continue # The first letters don't match
                found = True
                for char in adjRefString[1:]:
                    if char not in bookName[1:]: # We could also check that they're in the correct order........................might give less ambiguities???
                        found = False
                        break
                if not found: continue
                #print( "  getXRefBBB: p...", bookName )
                BBB = self.bookNameDict[bookName]
                count += 1
            if count == 1: # Found exactly one
                self.bookAbbrevDict[adjRefString] = BBB # Save to make it faster next time
                self.guesses += ('\n' if self.guesses else '') + "Guessed '{}' to be {} (firstletter+)".format( referenceString, BBB )
                return BBB
            if Globals.debugFlag and debuggingThisModule and count > 1:
                print( "  getXRefBBB has first and other character multiple matches for '{}' in {}".format( adjRefString, self.bookNameDict ) )

        if 0: # Too error prone!!!
            # See if a book name contains the letters in this string (slow)
            if count == 0:
                if Globals.debugFlag and debuggingThisModule: print ("  getXRefBBB using characters..." )
                for bookName in self.bookNameDict:
                    found = True
                    for char in adjRefString:
                        if char not in bookName: # We could also check that they're in the correct order........................might give less ambiguities???
                            found = False
                            break
                    if not found: continue
                    #print( "  getXRefBBB: q...", bookName )
                    BBB = self.bookNameDict[bookName]
                    count += 1
                if count == 1: # Found exactly one
                    self.bookAbbrevDict[adjRefString] = BBB # Save to make it faster next time
                    self.guesses += ('\n' if self.guesses else '') + "Guessed '{}' to be {} (letters)".format( referenceString, BBB )
                    return BBB
                if Globals.debugFlag and debuggingThisModule and count > 1:
                    print( "  getXRefBBB has character multiple matches for '{}' in {}".format( adjRefString, self.bookNameDict ) )

        if Globals.debugFlag and debuggingThisModule or Globals.verbosityLevel>2:
            print( "  getXRefBBB failed for '{}' with {} and {}".format( referenceString, self.bookNameDict, self.bookAbbrevDict ) )
        string = "Couldn't guess '{}'".format( referenceString[:5] )
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
        if Globals.debugFlag: assert( self.books )
        totalVersification, totalOmittedVerses, totalCombinedVerses, totalReorderedVerses = OrderedDict(), OrderedDict(), OrderedDict(), OrderedDict()
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
        if Globals.debugFlag: assert( self.books )
        haveParagraphs = haveQParagraphs = haveSectionHeadings = haveSectionReferences = haveWordsOfJesus = False
        AllParagraphs, AllQParagraphs, AllSectionHeadings, AllSectionReferences, AllWordsOfJesus = OrderedDict(), OrderedDict(), OrderedDict(), OrderedDict(), OrderedDict()
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


    def discover( self ):
        """Runs a series of checks and count on each book of the Bible
            in order to try to determine what are the normal standards."""
        if Globals.verbosityLevel > 0: print( "InternalBible:discover()" )
        if Globals.debugFlag and  'discoveryResults' in dir(self): halt # We've already called this once

        self.discoveryResults = OrderedDict()

        # Get our recommendations for added units -- only load this once per Bible
        #import pickle
        #folder = os.path.join( os.path.dirname(__file__), "DataFiles/", "ScrapedFiles/" ) # Relative to module, not cwd
        #filepath = os.path.join( folder, "AddedUnitData.pickle" )
        #if Globals.verbosityLevel > 3: print( _("Importing from {}...").format( filepath ) )
        #with open( filepath, 'rb' ) as pickleFile:
        #    typicalAddedUnits = pickle.load( pickleFile ) # The protocol version used is detected automatically, so we do not have to specify it

        if Globals.verbosityLevel > 2: print( _("Running discover on {}...").format( self.name ) )
        for BBB in self.books: # Do individual book prechecks
            if Globals.verbosityLevel > 3: print( "  " + _("Prechecking {}...").format( BBB ) )
            self.books[BBB]._discover( self.discoveryResults )

        # Now get the aggregate results for the entire Bible
        aggregateResults = {}
        if Globals.debugFlag: assert( 'ALL' not in self.discoveryResults )
        for BBB in self.discoveryResults:
            #print( "discoveryResults for", BBB, len(self.discoveryResults[BBB]), self.discoveryResults[BBB] )
            isOT = isNT = isDC = False
            if Globals.BibleBooksCodes.isOldTestament_NR( BBB ):
                isOT = True
                if 'OTBookCount' not in aggregateResults: aggregateResults['OTBookCount'], aggregateResults['OTBookCodes'] = 1, [BBB]
                else: aggregateResults['OTBookCount'] += 1; aggregateResults['OTBookCodes'].append( BBB )
            elif Globals.BibleBooksCodes.isNewTestament_NR( BBB ):
                isNT = True
                if 'NTBookCount' not in aggregateResults: aggregateResults['NTBookCount'], aggregateResults['NTBookCodes'] = 1, [BBB]
                else: aggregateResults['NTBookCount'] += 1; aggregateResults['NTBookCodes'].append( BBB )
            elif Globals.BibleBooksCodes.isDeuterocanon_NR( BBB ):
                isDC = True
                if 'DCBookCount' not in aggregateResults: aggregateResults['DCBookCount'], aggregateResults['DCBookCodes'] = 1, [BBB]
                else: aggregateResults['DCBookCount'] += 1; aggregateResults['DCBookCodes'].append( BBB )
            else: # not conventional OT or NT or DC
                if 'OtherBookCount' not in aggregateResults: aggregateResults['OtherBookCount'], aggregateResults['OtherBookCodes'] = 1, [BBB]
                else: aggregateResults['OtherBookCount'] += 1; aggregateResults['OtherBookCodes'].append( BBB )

            for key,value in self.discoveryResults[BBB].items():
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

                if key=='percentageProgress':
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
                    #print( 'xxx', value, aggregateResults['percentageProgressByBook'] )
                elif isinstance( value, float ):
                    #print( "got", BBB, key, value )
                    if 0.0 <= value <= 1.0:
                        if key not in aggregateResults: aggregateResults[key] = [value]
                        else: aggregateResults[key].append( value )
                elif isinstance( value, int ):
                    #print( "igot", BBB, key, value )
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
                elif value==True: # This test must come below the isinstance tests
                    #print( "tgot", BBB, key, value )
                    if key not in aggregateResults: aggregateResults[key] = 1
                    else: aggregateResults[key] += 1
                    if isOT:
                        if 'OT'+key not in aggregateResults: aggregateResults['OT'+key] = 1
                        else: aggregateResults['OT'+key] += 1
                    elif isNT:
                        if 'NT'+key not in aggregateResults: aggregateResults['NT'+key] = 1
                        else: aggregateResults['NT'+key] += 1
                    elif isDC:
                        if 'DC'+key not in aggregateResults: aggregateResults['DC'+key] = 1
                        else: aggregateResults['DC'+key] += 1
                elif value==False:
                    pass # No action needed here
                else:
                    print( "WARNING: unactioned discovery result", BBB, key, value )

        for arKey in list(aggregateResults.keys()): # Make a list first so we can delete entries later
            # Create summaries of lists with entries for various books
            #print( "check", arKey, aggregateResults[arKey] )
            if isinstance( aggregateResults[arKey], list ) and isinstance( aggregateResults[arKey][0], float ):
                if Globals.debugFlag: assert( arKey.endswith( 'Ratio' ) )
                #print( "this", arKey, aggregateResults[arKey] )
                aggregateRatio = round( sum( aggregateResults[arKey] ) / len( aggregateResults[arKey] ), 2 )
                aggregateFlag = None
                if aggregateRatio > 0.6: aggregateFlag = True
                if aggregateRatio < 0.4: aggregateFlag = False
                #print( "now", arKey, aggregateResults[arKey] )
                del aggregateResults[arKey] # Get rid of the ratio
                aggregateResults[arKey[:-5]+'Flag'] = aggregateFlag

        # Now calculate our overall statistics
        #print( "pre-aggregateResults", len(self), len(aggregateResults), aggregateResults )
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
        self.discoveryResults['ALL'] = aggregateResults

        if Globals.verbosityLevel > 2: # or self.name=="Matigsalug": # Display some of these results
            print( "Discovered Bible parameters:" )
            if Globals.verbosityLevel > 2: # or self.name=="Matigsalug": # Print completion level for each book
                for BBB in self.discoveryResults:
                    if BBB != 'ALL':
                        if 'seemsFinished' in self.discoveryResults[BBB] and self.discoveryResults[BBB]['seemsFinished']:
                            print( "   ", BBB, 'seems finished' ) #, str(self.discoveryResults[BBB]['percentageProgress'])+'%' )
                        elif not self.discoveryResults[BBB]['haveVerseText']:
                            print( "   ", BBB, 'not started' ) #, str(self.discoveryResults[BBB]['percentageProgress'])+'%' )
                        else: print( "   ", BBB, 'in progress', (str(self.discoveryResults[BBB]['percentageProgress'])+'%') if 'percentageProgress' in self.discoveryResults[BBB] else '' )
            for key,value in sorted(self.discoveryResults['ALL'].items()):
                if 'percentage' in key or key.endswith('Count') or key.endswith('Flag') or key.endswith('Codes'):
                    print( " ", key, "is", value )
                else:
                    #print( "key", repr(key), "value", repr(value) )
                    print( " ", key, "in", value if value<len(self) else "all", "books" )
    # end of InternalBible.discover


    def check( self ):
        """Runs a series of individual checks (and counts) on each book of the Bible
            and then a number of overall checks on the entire Bible."""
        # Get our recommendations for added units -- only load this once per Bible
        if Globals.verbosityLevel > 1: print( _("Checking {} Bible...").format( self.name ) )
        import pickle
        pickleFolder = os.path.join( os.path.dirname(__file__), "DataFiles/", "ScrapedFiles/" ) # Relative to module, not cwd
        pickleFilepath = os.path.join( pickleFolder, "AddedUnitData.pickle" )
        if Globals.verbosityLevel > 3: print( _("Importing from {}...").format( pickleFilepath ) )
        with open( pickleFilepath, 'rb' ) as pickleFile:
            typicalAddedUnitData = pickle.load( pickleFile ) # The protocol version used is detected automatically, so we do not have to specify it

        #self.discover() # Try to automatically determine our norms
        if Globals.verbosityLevel > 2: print( _("Running checks on {}...").format( self.name ) )
        for BBB in self.books: # Do individual book checks
            if Globals.verbosityLevel > 3: print( "  " + _("Checking {}...").format( BBB ) )
            self.books[BBB].check( self.discoveryResults['ALL'], typicalAddedUnitData )

        # Do overall Bible checks here
        # xxxxxxxxxxxxxxxxx ......................................
    # end of InternalBible.check


    def getErrors( self ):
        """Returns the error dictionary.
            All keys ending in 'Errors' give lists of strings.
            All keys ending in 'Counts' give OrderedDicts with [value]:count entries
            All other keys give subkeys
            The structure is:
                errors: OrderedDict
                    ['ByBook']: OrderedDict
                        ['All Books']: OrderedDict
                        [BBB] in order: OrderedDict
                            ['Priority Errors']: list
                            ['Load Errors']: list
                            ['Fix Text Errors']: list
                            ['Versification Errors']: list
                            ['SFMs']: OrderedDict
                                ['Newline Marker Errors']: list
                                ['Internal Marker Errors']: list
                                ['All Newline Marker Counts']: OrderedDict
                            ['Characters']: OrderedDict
                                ['All Character Counts']: OrderedDict
                                ['Letter Counts']: OrderedDict
                                ['Punctuation Counts']: OrderedDict
                            ['Words']: OrderedDict
                                ['All Word Counts']: OrderedDict
                                ['Case Insensitive Word Counts']: OrderedDict
                            ['Headings']: OrderedDict
                    ['ByCategory']: OrderedDict
        """
        def appendList( BBB, errorDict, firstKey, secondKey=None ):
            """Appends a list to the ALL BOOKS errors."""
            #print( "  appendList", BBB, firstKey, secondKey )
            if secondKey is None:
                if Globals.debugFlag: assert( isinstance (errorDict[BBB][firstKey], list ) )
                if firstKey not in errorDict['All Books']: errorDict['All Books'][firstKey] = []
                errorDict['All Books'][firstKey].extend( errorDict[BBB][firstKey] )
            else: # We have an extra level
                if Globals.debugFlag: assert( isinstance (errorDict[BBB][firstKey], dict ) )
                if Globals.debugFlag: assert( isinstance (errorDict[BBB][firstKey][secondKey], list ) )
                if firstKey not in errorDict['All Books']: errorDict['All Books'][firstKey] = OrderedDict()
                if secondKey not in errorDict['All Books'][firstKey]: errorDict['All Books'][firstKey][secondKey] = []
                errorDict['All Books'][firstKey][secondKey].extend( errorDict[BBB][firstKey][secondKey] )
        # end of appendList

        def mergeCount( BBB, errorDict, firstKey, secondKey=None ):
            """Merges the counts together."""
            #print( "  mergeCount", BBB, firstKey, secondKey )
            if secondKey is None:
                if Globals.debugFlag: assert( isinstance (errorDict[BBB][firstKey], dict ) )
                if firstKey not in errorDict['All Books']: errorDict['All Books'][firstKey] = {}
                for something in errorDict[BBB][firstKey]:
                    errorDict['All Books'][firstKey][something] = 1 if something not in errorDict['All Books'][firstKey] else errorDict[BBB][firstKey][something] + 1
            else:
                if Globals.debugFlag: assert( isinstance (errorDict[BBB][firstKey], (dict, OrderedDict,) ) )
                if Globals.debugFlag: assert( isinstance (errorDict[BBB][firstKey][secondKey], dict ) )
                if firstKey not in errorDict['All Books']: errorDict['All Books'][firstKey] = OrderedDict()
                if secondKey not in errorDict['All Books'][firstKey]: errorDict['All Books'][firstKey][secondKey] = {}
                for something in errorDict[BBB][firstKey][secondKey]:
                    errorDict['All Books'][firstKey][secondKey][something] = errorDict[BBB][firstKey][secondKey][something] if something not in errorDict['All Books'][firstKey][secondKey] \
                                                                                else errorDict['All Books'][firstKey][secondKey][something] + errorDict[BBB][firstKey][secondKey][something]
        # end of mergeCount

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
                if Globals.debugFlag: assert( tcWord != lcWord )
                tcCount = wordDict[tcWord] if tcWord in wordDict else 0
                if tcCount: tempResult.append( (tcCount,tcWord,) ); total += tcCount
            if total < lcTotal:
                TcWord = lcWord[0].upper() + lcWord[1:] # NOTE: This can make in-enew into In-enew
                #print( lcWord, tcWord, TcWord )
                #assert( TcWord != lcWord )
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
                if Globals.debugFlag: assert( UCWord!=lcWord )
                if UCWord != TcWord:
                    UCCount = wordDict[UCWord] if UCWord in wordDict else 0
                    if UCCount: tempResult.append( (UCCount,UCWord,) ); total += UCCount
            if total < lcTotal: # There's only one (slow) way left -- look at every word
                for word in wordDict:
                    if word.lower()==lcWord and word not in ( lcWord, tcWord, TcWord, tCWord, UCWord ):
                        tempResult.append( (wordDict[word],word,) ); total += wordDict[word]
                        # Seems we don't know the BCV reference here unfortunately
                        if 'Possible Word Errors' not in errors['ByBook']['All Books']['Words']: errors['ByBook']['All Books']['Words']['Possible Word Errors'] = []
                        errors['ByBook']['All Books']['Words']['Possible Word Errors'].append( _("Word '{}' appears to have unusual capitalization").format( word ) )
                        if total == lcTotal: break # no more to find

            if total < lcTotal:
                print( "Couldn't get word total with", lcWord, lcTotal, total, tempResult )
                print( lcWord, tcWord, TcWord, tCWord, UCWord )

            result = [w for c,w in sorted(tempResult)]
            #if len(tempResult)>2: print( lcWord, lcTotal, total, tempResult, result )
            return result
        # end of getCapsList

        # Set up
        errors = OrderedDict(); errors['ByBook'] = OrderedDict(); errors['ByCategory'] = OrderedDict()
        for category in ('Priority Errors','Load Errors','Fix Text Errors','Validation Errors','Versification Errors',):
            errors['ByCategory'][category] = [] # get these in a logical order (remember: they might not all occur for each book)
        for category in ('SFMs','Characters','Words','Headings','Introduction','Notes','Controls',): # get these in a logical order
            errors['ByCategory'][category] = OrderedDict()
        errors['ByBook']['All Books'] = OrderedDict()

        # Make sure that the error lists come first in the All Books ordered dictionaries (even if there's no errors for the first book)
        for BBB in self.books.keys():
            errors['ByBook'][BBB] = self.books[BBB].getErrors()
            for thisKey in errors['ByBook'][BBB]:
                if thisKey.endswith('Errors'):
                    errors['ByBook']['All Books'][thisKey] = []
                    errors['ByCategory'][thisKey] = []
                elif not thisKey.endswith('List') and not thisKey.endswith('Lines'):
                    for anotherKey in errors['ByBook'][BBB][thisKey]:
                        if anotherKey.endswith('Errors'):
                            if thisKey not in errors['ByBook']['All Books']: errors['ByBook']['All Books'][thisKey] = OrderedDict()
                            errors['ByBook']['All Books'][thisKey][anotherKey] = []
                            if thisKey not in errors['ByCategory']: errors['ByCategory'][thisKey] = OrderedDict()
                            errors['ByCategory'][thisKey][anotherKey] = []

        # Combine book errors into Bible totals plus into categories
        for BBB in self.books.keys():
            #errors['ByBook'][BBB] = self.books[BBB].getErrors()

            # Correlate some of the totals (i.e., combine book totals into Bible totals)
            # Also, create a dictionary of errors by category (as well as the main one by book reference code BBB)
            for thisKey in errors['ByBook'][BBB]:
                #print( "thisKey", BBB, thisKey )
                if thisKey.endswith('Errors') or thisKey.endswith('List') or thisKey.endswith('Lines'):
                    if Globals.debugFlag: assert( isinstance( errors['ByBook'][BBB][thisKey], list ) )
                    appendList( BBB, errors['ByBook'], thisKey )
                    errors['ByCategory'][thisKey].extend( errors['ByBook'][BBB][thisKey] )
                elif thisKey.endswith('Counts'):
                    NEVER_HAPPENS # does this happen?
                    mergeCount( BBB, errors['ByBook'], thisKey )
                else: # it's things like SFMs, Characters, Words, Headings, Notes
                    for anotherKey in errors['ByBook'][BBB][thisKey]:
                        #print( " anotherKey", BBB, anotherKey )
                        if anotherKey.endswith('Errors') or anotherKey.endswith('List') or anotherKey.endswith('Lines'):
                            if Globals.debugFlag: assert( isinstance( errors['ByBook'][BBB][thisKey][anotherKey], list ) )
                            appendList( BBB, errors['ByBook'], thisKey, anotherKey )
                            if thisKey not in errors['ByCategory']: errors['ByCategory'][thisKey] = OrderedDict() #; print( "Added", thisKey )
                            if anotherKey not in errors['ByCategory'][thisKey]: errors['ByCategory'][thisKey][anotherKey] = []
                            errors['ByCategory'][thisKey][anotherKey].extend( errors['ByBook'][BBB][thisKey][anotherKey] )
                        elif anotherKey.endswith('Counts'):
                            mergeCount( BBB, errors['ByBook'], thisKey, anotherKey )
                            # Haven't put counts into category array yet
                        else:
                            print( anotherKey, "not done yet" )
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
        for category in errors['ByCategory']:
            if not errors['ByCategory'][category]:
                #print( "InternalBible.getErrors: Removing empty category", category, "from errors['ByCategory']" )
                del errors['ByCategory'][category]
        return errors
    # end of InternalBible.getErrors


    def getBCVRef( self, ref ):
        """
        Search for a Bible reference
            and return the Bible text (in a list) along with the context.

        Expects a SimpleVerseKey for the parameter
            but also copes with a (B,C,V,S) tuple.

        Returns None if there is no information for this book.
        Raises a KeyError if there is no CV reference.
        """
        #print( "InternalBible.getBCVRef( {} )".format( ref ) )
        if isinstance( ref, tuple ): BBB = ref[0]
        else: BBB = ref.getBBB() # Assume it's a SimpleVerseKeyObject
        #print( " ", BBB in self.books )
        if BBB not in self.books and BBB not in self.triedLoadingBook:
            try: self.loadBook( BBB ) # Some types of Bibles have this function (so an entire Bible doesn't have to be loaded at startup)
            except AttributeError: logging.info( "Unable to load individual Bible book: {}".format( BBB ) ) # Ignore errors
            self.triedLoadingBook[BBB] = True
        if BBB in self.books: return self.books[BBB].getCVRef( ref )
        #else: print( "InternalBible {} doesn't have {}".format( self.name, BBB ) ); halt
    # end of InternalBible.getBCVRef


    def getVerseData( self, key ):
        """
        Return (USFM-like) verseData (a list).

        Returns None if there is no information for this book.
        Raises a KeyError if there is no CV reference.
        """
        #print( "InternalBible.getVerseData( {} )".format( key ) )
        result = self.getBCVRef( key )
        #print( "  gVD", self.name, key, verseData )
        if result is None:
            if Globals.debugFlag or Globals.verbosityLevel>2: print( "InternalBible.getVerseData: no VD", self.name, key, result )
            if Globals.debugFlag: assert( key.getChapterNumberStr()=='0' or key.getVerseNumberStr()=='0' ) # Why did we get nothing???
        else:
            verseData, context = result
            if Globals.debugFlag: assert( isinstance( verseData, InternalBibleEntryList ) )
            if Globals.debugFlag:
                #if 2 > len(verseData) > 20: print( "len", len(verseData) )
                assert( 1 <= len(verseData) <= 20 ) # Smallest is just a chapter number line
            return verseData
    # end of InternalBible.getVerseData


    def getVerseText( self, key ):
        """
        First miserable attempt at converting (USFM-like) verseData into a string.

        Uses uncommon Unicode symbols to represent various formatted styles

        Raises a key error if the key isn't found/valid.
        """
        result = self.getBCVRef( key )
        if result is not None:
            verseData, context = result
            #print( "gVT", self.name, key, verseData )
            assert( isinstance( verseData, InternalBibleEntryList ) )
            #if Globals.debugFlag: assert( 1 <= len(verseData) <= 5 )
            verseText, firstWord = '', False
            for entry in verseData:
                marker, cleanText = entry.getMarker(), entry.getCleanText()
                if marker == 'c': pass # Ignore
                elif marker == 'c~': pass # Ignore text after chapter marker
                elif marker == 'c#': pass # Ignore print chapter number
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
                else: logging.warning( "InternalBible.getVerseText Unknown marker {}={}".format( marker, repr(cleanText) ) )
            return verseText
    # end of InternalBible.getVerseText
# end of class InternalBible



def demo():
    """
    A very basic test/demo of the InternalBible class.
    """
    if Globals.verbosityLevel > 0: print( ProgNameVersion )

    # Since this is only designed to be a base class, it can't actually do much at all
    IB = InternalBible()
    IB.objectNameString = "Dummy test Internal Bible object"
    if Globals.verbosityLevel > 0: print( IB )
# end of demo


if __name__ == '__main__':
    # Configure basic set-up
    parser = Globals.setup( ProgName, ProgVersion )
    Globals.addStandardOptionsAndProcess( parser )

    demo()

    Globals.closedown( ProgName, ProgVersion )
# end of InternalBible.py