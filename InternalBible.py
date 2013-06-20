#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# InternalBible.py
#   Last modified: 2013-06-20 by RJH (also update versionString below)
#
# Module handling the USFM markers for Bible books
#
# Copyright (C) 2010-2013 Robert Hunt
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
    self.objectTypeString (with "USFM" or "USX")
    self.objectNameString (with a description of the type of Bible object)
It also needs to provide a "load" routine that sets:
    self.sourceFolder
and then fills
    self.books
"""

progName = "Internal Bible handler"
versionString = "0.24"


import os, logging
from gettext import gettext as _
from collections import OrderedDict

import Globals
from InternalBibleBook import InternalBibleEntryList



class InternalBible:
    """
    Class to define and manipulate InternalBibles.

    This class contains no load function -- that is expected to be supplied by the superclass.
    """
    def __init__( self ):
        """
        Create the object.
        """
        # Set up empty variables for the object (to be filled in later)
        self.name = self.shortName = self.abbreviation = None
        self.sourceFolder = self.sourceFilepath = None
        self.status = self.revision = self.version = None

        # Set up empty containers for the object
        self.books = OrderedDict()
        self.ssfPathName, self.ssfData = '', {}
        self.BBBToNameDict, self.bookNameDict, self.combinedBookNameDict, self.bookAbbrevDict = {}, {}, {}, {} # Used to store book name and abbreviations (pointing to the BBB codes)
        self.reverseDict, self.guesses = {}, '' # A program history

        # Set up filled containers for the object
        #self.OneChapterBBBBookCodes = Globals.BibleBooksCodes.getSingleChapterBooksList()

        self.triedLoadingBook = {}
    # end of InternalBible.__init_


    def __str__( self ):
        """
        This method returns the string representation of a Bible.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = self.objectNameString
        if Globals.debugFlag or Globals.verbosityLevel>2: result += ' v' + versionString
        if self.name: result += ('\n' if result else '') + "  Name: " + self.name
        if self.sourceFolder: result += ('\n' if result else '') + "  Source folder: " + self.sourceFolder
        elif self.sourceFilepath: result += ('\n' if result else '') + "  Source: " + self.sourceFilepath
        if self.status: result += ('\n' if result else '') + "  Status: " + self.status
        if self.revision: result += ('\n' if result else '') + "  Revision: " + self.revision
        if self.version: result += ('\n' if result else '') + "  Version: " + self.version
        result += ('\n' if result else '') + "  Number of books = " + str(len(self.books))
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
        Given an index, return the book object (or raise an IndexError)
        """
        return list(self.books.items())[keyIndex][1] # element 0 is BBB, element 1 is the book object
    # end of InternalBible.__getitem__


    def __iter__( self ):
        """ Yields the next book. """
        for BBB in self.books:
            yield self.books[BBB]
    # end of InternalBible.__iter__


    def pickleBible( self, filename=None, folder=None ):
        """
        Writes the object to a .pickle file that can be easily loaded into a Python3 program.
            If folder is None (or missing), defaults to the default cache folder specified in Globals.
            Created the folder(s) if necessary.
        """
        #print( repr(self.abbreviation), repr(self.name) )
        if filename is None:
            filename = self.abbreviation if self.abbreviation else self.name
        assert( filename )
        filename += '.pickle'
        if Globals.verbosityLevel > 1:
            print( _("InternalBible.pickleBible: Saving {} to {}...").format( self.objectNameString, filename if folder is None else os.path.join( folder, filename ) ) )
        # Causes SEG FAULT
        #Globals.pickleObject( self, filename, folder )
    # end of InternalBible.pickleBible


    def getAssumedBookName( self, BBB ):
        """Gets the book name for the given book reference code."""
        if Globals.debugFlag: assert( BBB in Globals.BibleBooksCodes)
        #assert( self.books[BBB] )
        if BBB in self.BBBToNameDict: return self.BBBToNameDict[BBB]
    # end of InternalBible.getAssumedBookName


    def saveBook( self, bookData ):
        """
        Save the Bible book into our object
            and uupdate our indexes.
        """
        #print( "saveBook( {} )".format( bookData ) )
        BBB = bookData.bookReferenceCode
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
        if Globals.debugFlag: print( "  getXRefBBB using startswith1..." )
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
        if Globals.debugFlag and count > 1: print( "  getXRefBBB has multiple startswith matches for '{}' in {}".format( adjRefString, self.combinedBookNameDict ) )
        if count == 0:
            if Globals.debugFlag: print( "  getXRefBBB using startswith2..." )
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
            if Globals.debugFlag: print( "  getXRefBBB using word startswith..." )
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
            if Globals.debugFlag and count > 1: print( "  getXRefBBB has multiple startswith matches for '{}' in {}".format( adjRefString, self.bookNameDict ) )

        # See if a book name starts with the same letter plus contains the letters in this string (slow)
        if count == 0:
            if Globals.debugFlag: print ("  getXRefBBB using first plus other characters..." )
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
            if Globals.debugFlag and count > 1: print( "  getXRefBBB has first and other character multiple matches for '{}' in {}".format( adjRefString, self.bookNameDict ) )

        if 0: # Too error prone!!!
            # See if a book name contains the letters in this string (slow)
            if count == 0:
                if Globals.debugFlag: print ("  getXRefBBB using characters..." )
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
                if Globals.debugFlag and count > 1: print( "  getXRefBBB has character multiple matches for '{}' in {}".format( adjRefString, self.bookNameDict ) )

        if Globals.debugFlag or Globals.verbosityLevel>2: print( "  getXRefBBB failed for '{}' with {} and {}".format( referenceString, self.bookNameDict, self.bookAbbrevDict ) )
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
        for bookReferenceCode in self.books.keys():
            versification, omittedVerses, combinedVerses, reorderedVerses = self.books[bookReferenceCode].getVersification()
            totalVersification[bookReferenceCode] = versification
            if omittedVerses: totalOmittedVerses[bookReferenceCode] = omittedVerses # Only add an entry if there are some
            if combinedVerses: totalCombinedVerses[bookReferenceCode] = combinedVerses
            if reorderedVerses: totalReorderedVerses[bookReferenceCode] = reorderedVerses
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
        #print( "\nInternalBible:discover" )
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
            self.books[BBB].discover( self.discoveryResults )

        # Now get the aggregate results for the entire Bible
        aggregateResults = {}
        if Globals.debugFlag: assert( 'ALL' not in self.discoveryResults )
        for BBB in self.discoveryResults:
            #print( "discoveryResults", BBB, self.discoveryResults[BBB] )
            isOT = isNT = isDC = False
            if Globals.BibleBooksCodes.isOldTestament_NR( BBB ):
                isOT = True
                if 'OTBookCount' not in aggregateResults: aggregateResults['OTBookCount'] = 1
                else: aggregateResults['OTBookCount'] += 1
            elif Globals.BibleBooksCodes.isNewTestament_NR( BBB ):
                isNT = True
                if 'NTBookCount' not in aggregateResults: aggregateResults['NTBookCount'] = 1
                else: aggregateResults['NTBookCount'] += 1
            elif Globals.BibleBooksCodes.isDeuterocanon_NR( BBB ):
                isDC = True
                if 'DCBookCount' not in aggregateResults: aggregateResults['DCBookCount'] = 1
                else: aggregateResults['DCBookCount'] += 1
            else: # not conventional OT or NT or DC
                if 'OtherBookCount' not in aggregateResults: aggregateResults['OtherBookCount'] = 1
                else: aggregateResults['OtherBookCount'] += 1

            for key,value in self.discoveryResults[BBB].items():
                if key=='percentageProgress':
                    if 'percentageProgressByBook' not in aggregateResults: aggregateResults['percentageProgressByBook'] = value
                    else: aggregateResults['percentageProgressByBook'] += value
                    if isOT:
                        if 'percentageProgressByOTBook' not in aggregateResults: aggregateResults['percentageProgressByOTBook'] = value
                        else: aggregateResults['percentageProgressByOTBook'] += value
                    elif isNT:
                        if 'percentageProgressByNTBook' not in aggregateResults: aggregateResults['percentageProgressByNTBook'] = value
                        else: aggregateResults['percentageProgressByNTBook'] += value
                    elif isDC:
                        if 'percentageProgressByDCBook' not in aggregateResults: aggregateResults['percentageProgressByDCBook'] = value
                        else: aggregateResults['percentageProgressByDCBook'] += value
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
                aggregateRatio = sum( aggregateResults[arKey] ) / len( aggregateResults[arKey] )
                aggregateFlag = None
                if aggregateRatio > 0.6: aggregateFlag = True
                if aggregateRatio < 0.4: aggregateFlag = False
                #print( "now", arKey, aggregateResults[arKey] )
                del aggregateResults[arKey] # Get rid of the ratio
                aggregateResults[arKey[:-5]+'Flag'] = aggregateFlag

        #print( 'yyy', "aggregateResults", aggregateResults['percentageProgressByBook'], len(self) )
        if 'percentageProgressByBook' in aggregateResults:
            aggregateResults['percentageProgressByBook'] = str( round( aggregateResults['percentageProgressByBook'] / len(self) ) ) + '%'
        if 'percentageProgressByOTBook' in aggregateResults:
            aggregateResults['percentageProgressByOTBook'] = str( round( aggregateResults['percentageProgressByOTBook'] / 39 ) ) + '%'
        if 'percentageProgressByNTBook' in aggregateResults:
            aggregateResults['percentageProgressByNTBook'] = str( round( aggregateResults['percentageProgressByNTBook'] / 27 ) ) + '%'
        if 'percentageProgressByDCBook' in aggregateResults:
            aggregateResults['percentageProgressByDCBook'] = str( round( aggregateResults['percentageProgressByDCBook'] / 15 ) ) + '%'
        if 'percentageProgressByVerse' in aggregateResults:
            aggregateResults['percentageProgressByVerse'] = str( round( aggregateResults['completedVerseCount'] * 100 / aggregateResults['verseCount'] ) ) + '%'
        if 'percentageProgressByOTVerse' in aggregateResults:
            aggregateResults['percentageProgressByOTVerse'] = str( round( aggregateResults['OTcompletedVerseCount'] * 100 / aggregateResults['OTverseCount'] ) ) + '%'
        if 'percentageProgressByNTVerse' in aggregateResults:
            aggregateResults['percentageProgressByNTVerse'] = str( round( aggregateResults['NTcompletedVerseCount'] * 100 / aggregateResults['NTverseCount'] ) ) + '%'
        if 'percentageProgressByDCVerse' in aggregateResults:
            aggregateResults['percentageProgressByDCVerse'] = str( round( aggregateResults['DCcompletedVerseCount'] * 100 / aggregateResults['DCverseCount'] ) ) + '%'

        # Save the results
        self.discoveryResults['ALL'] = aggregateResults

        if Globals.verbosityLevel > 2: # or self.name=="Matigsalug": # Display some of these results
            print( "Discovered Bible parameters:" )
            if Globals.verbosityLevel > 2: # or self.name=="Matigsalug": # Print completion level for each book
                for BBB in self.discoveryResults:
                    if BBB != 'ALL':
                        if 'seemsFinished' in self.discoveryResults[BBB] and self.discoveryResults[BBB]['seemsFinished']:
                            print( "   ", BBB, "seems finished" ) #, str(self.discoveryResults[BBB]['percentageProgress'])+'%' )
                        elif not self.discoveryResults[BBB]['haveVerseText']:
                            print( "   ", BBB, "not started" ) #, str(self.discoveryResults[BBB]['percentageProgress'])+'%' )
                        else: print( "   ", BBB, "in progress", str(self.discoveryResults[BBB]['percentageProgress'])+'%' )
            for key,value in sorted(self.discoveryResults['ALL'].items()):
                if key.startswith("percentage") or key.endswith("Count") or key.endswith("Flag"):
                    print( " ", key, "is", value )
                else: print( " ", key, "in", value if value<len(self) else "All", "books" )
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

        self.discover() # Try to automatically determine our norms
        if Globals.verbosityLevel > 2: print( _("Running checks on {}...").format( self.name ) )
        for BBB in self.books: # Do individual book checks
            if Globals.verbosityLevel > 3: print( "  " + _("Checking {}...").format( BBB ) )
            self.books[BBB].check( self.discoveryResults['ALL'], typicalAddedUnitData )

        # Do overall Bible checks
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
        for category in ('SFMs','Characters','Words','Headings','Introduction','Notes',): # get these in a logical order
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
        """
        #print( "InternalBible.getBCVRef( {} )".format( ref ) )
        if isinstance( ref, tuple ): BBB = ref[0]
        else: BBB = ref.getBBB() # Assume it's a SimpleVerseKeyObject
        #print( " ", BBB in self.books )
        if BBB not in self.triedLoadingBook:
            try: self.loadBook( BBB ) # Some types of Bibles have this function (so an entire Bible doesn't have to be loaded at startup)
            except: pass # Ignore errors
            self.triedLoadingBook[BBB] = True
        if BBB in self.books: return self.books[BBB].getCVRef( ref )
        #else: print( "InternalBible {} doesn't have {}".format( self.name, BBB ) ); halt
    # end of InternalBible.getBCVRef


    def getVerseData( self, key ):
        """
        Return (USFM-like) verseData (a list).
        """
        #print( "InternalBible.getVerseData( {} )".format( key ) )
        result = self.getBCVRef( key )
        #print( "  gVD", self.name, key, verseData )
        if result is None:
            print( "IB.gVD no VD", self.name, key, result )
            if Globals.debugFlag: assert( key.getChapterNumberStr()=='0' or key.getVerseNumberStr()=='0' )
        else:
            verseData, context = result
            if Globals.debugFlag: assert( isinstance( verseData, InternalBibleEntryList ) )
            if Globals.debugFlag: assert( 2 <= len(verseData) <= 20 )
            return verseData
    # end of InternalBible.getVerseData


    def getVerseText( self, key ):
        """
        First miserable attempt at converting (USFM-like) verseData into a string.
        """
        result = self.getBCVRef( key )
        if result is not None:
            verseData, context = result
            #print( "gVT", self.name, key, verseData )
            assert( isinstance( verseData, InternalBibleEntryList ) )
            #if Globals.debugFlag: assert( 1 <= len(verseData) <= 5 )
            verseText, firstWord = '', False
            for marker,originalMarker,text,cleanText,extras in verseData:
                if marker == 'c': pass # Ignore
                elif marker == 'c~': pass # Ignore text after chapter marker
                elif marker == 'c#': pass # Ignore print chapter number
                elif marker == 's1': verseText += '¥' + cleanText + '¥'
                elif marker == 'p': verseText += '¶' + cleanText
                elif marker == 'm': verseText += '§' + cleanText
                elif marker == 'v': firstWord = True # Ignore
                elif marker == 'v~': verseText += cleanText
                elif marker == 'vw':
                    if not firstWord: verseText += ' '
                    verseText += cleanText
                    firstWord = False
                elif Globals.logErrorsFlag: logging.warning( "InternalBible.getVerseText Unknown marker {}={}".format( marker, repr(cleanText) ) )
            return verseText
    # end of InternalBible.getVerseText
# end of class InternalBible



def demo():
    """
    A very basic test/demo of the InternalBible class.
    """
    if Globals.verbosityLevel > 0: print( "{} V{}".format( progName, versionString ) )

    # Since this is only designed to be a base class, it can't actually do much at all
    IB = InternalBible()
    IB.objectNameString = "Dummy test Internal Bible object"
    if Globals.verbosityLevel > 0: print( IB )
# end of demo

if __name__ == '__main__':
    # Configure basic logging
    logging.basicConfig( format='%(levelname)s: %(message)s', level=logging.INFO ) # Removes the unnecessary and unhelpful 'root:' part of the logged messages

    # Handle command line parameters
    from optparse import OptionParser
    parser = OptionParser( version="v{}".format( versionString ) )
    #parser.add_option("-e", "--export", action="store_true", dest="export", default=False, help="export the XML file to .py and .h tables suitable for directly including into other programs")
    Globals.addStandardOptionsAndProcess( parser )

    demo()
# end of InternalBible.py