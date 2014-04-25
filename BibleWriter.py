#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# BibleWriter.py
#   Last modified: 2014-04-24 by RJH (also update ProgVersion below)
#
# Module writing out InternalBibles in various formats.
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
EARLY PROTOTYPE ONLY AT THIS STAGE! (Developmental code not very well structured yet.)

Module for exporting Bibles in various formats including USFM, USX, USFX, and OSIS.

A class which extends InternalBible.

This is intended to be a virtual class, i.e., to be extended further
    by classes which load particular kinds of Bibles (e.g., OSIS, USFM, USX, etc.)

Contains functions:
    makeLists( outputFolder=None )
    toPseudoUSFM( outputFolder=None ) -- this is our internal Bible format -- exportable for debugging purposes
            For more details see InternalBible.py, InternalBibleBook.py, InternalBibleInternals.py
    toUSFM( outputFolder=None )
    toText( outputFolder=None )
    toHTML5( outputFolder=None, controlDict=None, validationSchema=None, humanReadable=True )
    toCustomBible( outputFolder=None )
    toPhotoBible( outputFolder=None )
    toMediaWiki( outputFolder=None, controlDict=None, validationSchema=None )
    toZefaniaXML( outputFolder=None, controlDict=None, validationSchema=None )
    toHaggaiXML( outputFolder=None, controlDict=None, validationSchema=None )
    toOpenSongXML( outputFolder=None, controlDict=None, validationSchema=None )
    toUSXXML( outputFolder=None, controlDict=None, validationSchema=None )
    toUSFXXML( outputFolder=None, controlDict=None, validationSchema=None )
    toOSISXML( outputFolder=None, controlDict=None, validationSchema=None )
    toSwordModule( outputFolder=None, controlDict=None, validationSchema=None )
    totheWord( outputFolder=None )
    toMySword( outputFolder=None )
    toESword( outputFolder=None )
    toTeX( outputFolder=None )
    toSwordSearcher( outputFolder=None )
    toDrupalBible( outputFolder=None )
    doAllExports( givenOutputFolderName=None, wantPhotoBible=False, wantPDFs=False )
"""

ProgName = "Bible writer"
ProgVersion = "0.66"
ProgNameVersion = "{} v{}".format( ProgName, ProgVersion )

debuggingThisModule = False


OSISNameSpace = "http://www.bibletechnologies.net/2003/OSIS/namespace"
OSISSchemaLocation = "http://www.bibletechnologies.net/osisCore.2.1.1.xsd"


import sys, os, shutil, logging
from datetime import datetime
from collections import OrderedDict
import re, sqlite3, json
import zipfile, tarfile
import subprocess, multiprocessing
from gettext import gettext as _

import Globals, ControlFiles
from InternalBible import InternalBible
from BibleOrganizationalSystems import BibleOrganizationalSystem
from BibleReferences import BibleReferenceList
from USFMMarkers import oftenIgnoredIntroMarkers, removeUSFMCharacterField, replaceUSFMCharacterFields
from MLWriter import MLWriter


allCharMarkers = Globals.USFMMarkers.getCharacterMarkersList( expandNumberableMarkers=True )
#print( allCharMarkers ); halt


defaultControlFolder = "ControlFiles/" # Relative to the current working directory
def setDefaultControlFolder( newFolderName ):
    global defaultControlFolder
    if Globals.verbosityLevel > 1:
        print( "defaultControlFolder changed from {} to {}".format( defaultControlFolder, newFolderName ) )
    defaultControlFolder = newFolderName
# end of BibleWriter.setDefaultControlFolder



class BibleWriter( InternalBible ):
    """
    Class to export Bibles.

    """
    def __init__( self ):
        """
        #    Create the object.
        #    """
        InternalBible.__init__( self  ) # Initialise the base class
        self.doneSetupGeneric = False
        #self.genericBOS = BibleOrganizationalSystem( "GENERIC-KJV-81" )
        #self.genericBRL = BibleReferenceList( self.genericBOS, BibleObject=self ) # self isn't actualised yet!!!
    # end of BibleWriter.__init_


    def __setupWriter( self ):
        """
        Do some generic system setting up.

        Unfortunately, I don't know how to do this in the _init__ function
            coz it uses self (which isn't actualised yet in init).
        """
        if Globals.debugFlag: assert( not self.doneSetupGeneric )
        if not self.doneSetupGeneric:
            self.genericBOS = BibleOrganizationalSystem( "GENERIC-KJV-81" )
            self.genericBRL = BibleReferenceList( self.genericBOS, BibleObject=self ) # this prevents pickling!
                # because unfortunately it causes a recursive linking of objects
            self.projectName = "Unknown"
            if self.name: self.projectName = self.name
            self.discover() # Find out stats about the Bible
            self.doneSetupGeneric = True
    # end of BibleWriter.__setupWriter


    def __adjustControlDict( self, existingControlDict ):
        """
        Do some global name replacements in the given control dictionary.
        """
        if Globals.debugFlag: assert( existingControlDict and isinstance( existingControlDict, dict ) )
        for entry in existingControlDict:
            existingControlDict[entry] = existingControlDict[entry].replace( '__PROJECT_NAME__', self.projectName )
                #.replace( '__PROJECT_NAME__', Globals.makeSafeFilename( self.projectName.replace( ' ', '_' ) ) )
            #print( entry, repr(existingControlDict[entry]) )
    # end of BibleWriter.__adjustControlDict


    def makeLists( self, outputFolder=None ):
        """
        Write the pseudo USFM out directly (for debugging, etc.).
            May write the rawLines 2-tuples to .rSFM files (if _rawLines still exists)
            Always writes the processed 5-tuples to .pSFM files (from _processedLines).
        """
        import InternalBibleBook
        if Globals.verbosityLevel > 1: print( "Running BibleWriter:makeLists..." )
        if Globals.debugFlag: assert( self.books )

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolder: outputFolder = "OutputFiles/BOS_Lists/"
        if not os.access( outputFolder, os.F_OK ): os.makedirs( outputFolder ) # Make the empty folder if there wasn't already one there


        def countWords( marker, segment, location ):
            """ Breaks the segment into words and counts them.
            """
            def stripWordPunctuation( word ):
                """Removes leading and trailing punctuation from a word.
                    Returns the "clean" word."""
                while word and word[0] in InternalBibleBook.leadingWordPunctChars:
                    word = word[1:] # Remove leading punctuation
                while word and word[-1] in InternalBibleBook.trailingWordPunctChars:
                    word = word[:-1] # Remove trailing punctuation
                return word
            # end of stripWordPunctuation

            words = segment.replace('—',' ').replace('–',' ').split() # Treat em-dash and en-dash as word break characters
            for j,rawWord in enumerate(words):
                if marker=='c' or marker=='v' and j==1 and rawWord.isdigit(): continue # Ignore the chapter and verse numbers (except ones like 6a)
                word = rawWord
                for internalMarker in InternalBibleBook.INTERNAL_SFMS_TO_REMOVE: word = word.replace( internalMarker, '' )
                word = stripWordPunctuation( word )
                if word and not word[0].isalnum():
                    #print( word, stripWordPunctuation( word ) )
                    if len(word) > 1:
                        if Globals.debugFlag: print( "{} {}:{} ".format( BBB, c, v ) + _("Have unexpected character starting word '{}'").format( word ) )
                        word = word[1:]
                if word: # There's still some characters remaining after all that stripping
                    if Globals.verbosityLevel > 3: # why???
                        for k,char in enumerate(word):
                            if not char.isalnum() and (k==0 or k==len(word)-1 or char not in InternalBibleBook.medialWordPunctChars):
                                if Globals.debugFlag: print( "{} {}:{} ".format( BBB, c, v ) + _("Have unexpected '{}' in word '{}'").format( char, word ) )
                    lcWord = word.lower()
                    isAReferenceOrNumber = True
                    for char in word:
                        if not char.isdigit() and char not in ':-,.': isAReferenceOrNumber = False; break
                    if not isAReferenceOrNumber:
                        allWordCounts[word] = 1 if word not in allWordCounts else allWordCounts[word] + 1
                        allCaseInsensitiveWordCounts[lcWord] = 1 if lcWord not in allCaseInsensitiveWordCounts else allCaseInsensitiveWordCounts[lcWord] + 1
                        if location == "main":
                            mainTextWordCounts[word] = 1 if word not in mainTextWordCounts else mainTextWordCounts[word] + 1
                            mainTextCaseInsensitiveWordCounts[lcWord] = 1 if lcWord not in mainTextCaseInsensitiveWordCounts else mainTextCaseInsensitiveWordCounts[lcWord] + 1
                    #else: print( "excluded reference or number", word )
        # end of countWords


        def printWordCounts( typeString, dictionary ):
            """ Given a description and a dictionary,
                    sorts and writes the word count data to text, csv, and xml files. """
            filenamePortion = typeString + "_sorted_by_word."
            filepathPortion = os.path.join( outputFolder, Globals.makeSafeFilename( filenamePortion ) )
            if Globals.verbosityLevel > 2: print( "  " + _("Writing '{}*'...").format( filepathPortion ) )
            sortedWords = sorted(dictionary)
            with open( filepathPortion+'txt', 'wt' ) as txtFile:
                with open( filepathPortion+'csv', 'wt' ) as csvFile:
                    with open( filepathPortion+'xml', 'wt' ) as xmlFile:
                        xmlFile.write( '<?xml version="1.0" encoding="utf-8"?>\n' ) # Write the xml header
                        xmlFile.write( '<entries>\n' ) # root element
                        for word in sortedWords:
                            if Globals.debugFlag: assert( ' ' not in word )
                            txtFile.write( "{} {}\n".format( word, dictionary[word] ) )
                            csvFile.write( "{},{}\n".format( repr(word) if ',' in word else word, dictionary[word] ) )
                            if Globals.debugFlag: assert( '<' not in word and '>' not in word and '"' not in word )
                            xmlFile.write( "<entry><word>{}</word><count>{}</count></entry>\n".format( word, dictionary[word] ) )
                        xmlFile.write( '</entries>' ) # close root element
            filenamePortion = typeString + "_sorted_by_count."
            filepathPortion = os.path.join( outputFolder, Globals.makeSafeFilename( filenamePortion ) )
            if Globals.verbosityLevel > 2: print( "  " + _("Writing '{}*'...").format( filepathPortion ) )
            with open( filepathPortion+'txt', 'wt' ) as txtFile:
                with open( filepathPortion+'csv', 'wt' ) as csvFile:
                    with open( filepathPortion+'xml', 'wt' ) as xmlFile:
                        xmlFile.write( '<?xml version="1.0" encoding="utf-8"?>\n' ) # Write the xml header
                        xmlFile.write( '<entries>\n' ) # root element
                        for word in sorted(sortedWords, key=dictionary.get):
                            if Globals.debugFlag: assert( ' ' not in word )
                            txtFile.write( "{} {}\n".format( word, dictionary[word] ) )
                            csvFile.write( "{},{}\n".format( repr(word) if ',' in word else word, dictionary[word] ) )
                            if Globals.debugFlag: assert( '<' not in word and '>' not in word and '"' not in word )
                            xmlFile.write( "<entry><word>{}</word><count>{}</count></entry>\n".format( word, dictionary[word] ) )
                        xmlFile.write( '</entries>' ) # close root element
        # end of printWordCounts


        # Initialise all our counters
        allWordCounts, allCaseInsensitiveWordCounts = {}, {}
        mainTextWordCounts, mainTextCaseInsensitiveWordCounts = {}, {}


        # Determine all the counts
        for BBB,bookObject in self.books.items():
            c = v = '0' # Just for error messages
            for entry in bookObject._processedLines:
                marker, text, cleanText = entry.getMarker(), entry.getText(), entry.getCleanText()

                # Keep track of where we are for more helpful error messages
                if marker=='c' and text: c = text.split()[0]; v = '0'
                elif marker=='v' and text: v = text.split()[0]

                if text and Globals.USFMMarkers.isPrinted(marker): # process this main text
                    countWords( marker, cleanText, "main" )

                for extraType, extraIndex, extraText, cleanExtraText in entry.getExtras(): # do any footnotes and cross-references
                    if Globals.debugFlag:
                        assert( extraText ) # Shouldn't be blank
                        #assert( extraText[0] != '\\' ) # Shouldn't start with backslash code
                        assert( extraText[-1] != '\\' ) # Shouldn't end with backslash code
                        #print( extraType, extraIndex, len(text), "'"+extraText+"'", "'"+cleanExtraText+"'" )
                        assert( extraIndex >= 0 )
                        #assert( 0 <= extraIndex <= len(text)+3 )
                        assert( extraType in ('fn','xr',) )
                        assert( '\\f ' not in extraText and '\\f*' not in extraText and '\\x ' not in extraText and '\\x*' not in extraText ) # Only the contents of these fields should be in extras
                    countWords( extraType, cleanExtraText, "notes" )

        # Now sort the lists and write them each twice (sorted by word and sorted by count)
        printWordCounts( "all_wordcounts", allWordCounts )
        printWordCounts( "main_text_wordcounts", mainTextWordCounts )
        printWordCounts( "all_wordcounts_case_insensitive", allCaseInsensitiveWordCounts )
        printWordCounts( "main_text_wordcounts_case_insensitive", mainTextCaseInsensitiveWordCounts )

        return True
    # end of BibleWriter.makeLists


    def toPseudoUSFM( self, outputFolder=None ):
        """
        Write the pseudo USFM out directly (for debugging, etc.).
            May write the rawLines 2-tuples to .rSFM files (if _rawLines still exists)
            Always writes the processed 5-tuples to .pSFM files (from _processedLines).
        """
        if Globals.verbosityLevel > 1: print( "Running BibleWriter:toPseudoUSFM..." )
        if Globals.debugFlag: assert( self.books )

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolder: outputFolder = "OutputFiles/BOS_PseudoUSFM_Export/"
        if not os.access( outputFolder, os.F_OK ): os.makedirs( outputFolder ) # Make the empty folder if there wasn't already one there

        # Write the raw and pseudo-USFM files
        for BBB,bookObject in self.books.items():
            try: rawUSFMData = bookObject._rawLines
            except: rawUSFMData = None # it's been deleted  :-(
            if rawUSFMData:
                #print( "\pseudoUSFMData", pseudoUSFMData[:50] ); halt
                USFMAbbreviation = Globals.BibleBooksCodes.getUSFMAbbreviation( BBB )
                USFMNumber = Globals.BibleBooksCodes.getUSFMNumber( BBB )

                filename = "{}{}BWr.rSFM".format( USFMNumber, USFMAbbreviation.upper() ) # BWr = BibleWriter
                filepath = os.path.join( outputFolder, Globals.makeSafeFilename( filename ) )
                if Globals.verbosityLevel > 2: print( "  " + _("Writing '{}'...").format( filepath ) )
                with open( filepath, 'wt' ) as myFile:
                    for marker,text in rawUSFMData:
                        myFile.write( "{}: '{}'\n".format( marker, text ) )

            pseudoUSFMData = bookObject._processedLines
            #print( "\pseudoUSFMData", pseudoUSFMData[:50] ); halt
            USFMAbbreviation = Globals.BibleBooksCodes.getUSFMAbbreviation( BBB )
            USFMNumber = Globals.BibleBooksCodes.getUSFMNumber( BBB )

            filename = "{}{}BWr.pSFM".format( USFMNumber, USFMAbbreviation.upper() ) # BWr = BibleWriter
            filepath = os.path.join( outputFolder, Globals.makeSafeFilename( filename ) )
            if Globals.verbosityLevel > 2: print( "  " + _("Writing '{}'...").format( filepath ) )
            with open( filepath, 'wt' ) as myFile:
                for entry in pseudoUSFMData:
                    myFile.write( "{} ({}): '{}' '{}' {}\n" \
                        .format( entry.getMarker(), entry.getOriginalMarker(), entry.getAdjustedText(), entry.getCleanText(), entry.getExtras() ) )

        # Now create a zipped collection
        if Globals.verbosityLevel > 2: print( "  Zipping PseudoUSFM files..." )
        zf = zipfile.ZipFile( os.path.join( outputFolder, 'AllFiles.zip' ), 'w', compression=zipfile.ZIP_DEFLATED )
        for filename in os.listdir( outputFolder ):
            if not filename.endswith( '.zip' ):
                filepath = os.path.join( outputFolder, filename )
                zf.write( filepath, filename ) # Save in the archive without the path
        zf.close()

        return True
    # end of BibleWriter.toPseudoUSFM



    def toUSFM( self, outputFolder=None, removeVerseBridges=False ):
        """
        Adjust the pseudo USFM and write the USFM files.
        """
        if Globals.verbosityLevel > 1: print( "Running BibleWriter:toUSFM..." )
        if Globals.debugFlag: assert( self.books )

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolder: outputFolder = "OutputFiles/BOS_USFM_" + ("Reexport/" if self.objectTypeString=="USFM" else "Export/")
        if not os.access( outputFolder, os.F_OK ): os.makedirs( outputFolder ) # Make the empty folder if there wasn't already one there
        #if not controlDict: controlDict = {}; ControlFiles.readControlFile( 'ControlFiles', "To_MediaWiki_controls.txt", controlDict )
        #assert( controlDict and isinstance( controlDict, dict ) )

        # Adjust the extracted outputs
        for BBB,bookObject in self.books.items():
            pseudoUSFMData = bookObject._processedLines
            #print( "\pseudoUSFMData", pseudoUSFMData[:50] ); halt
            USFMAbbreviation = Globals.BibleBooksCodes.getUSFMAbbreviation( BBB )
            USFMNumber = Globals.BibleBooksCodes.getUSFMNumber( BBB )

            USFM = ""
            inField = None
            value1 = value2 = None # For printing missing (bridged) verse numbers
            if Globals.verbosityLevel > 2: print( "  " + _("Adjusting USFM output..." ) )
            for verseDataEntry in pseudoUSFMData:
                pseudoMarker, value = verseDataEntry.getMarker(), verseDataEntry.getFullText()
                #print( BBB, pseudoMarker, repr(value) )
                if (not USFM) and pseudoMarker!='id': # We need to create an initial id line
                    USFM += '\\id {} -- BibleOrgSys USFM export v{}'.format( USFMAbbreviation.upper(), ProgVersion )
                if pseudoMarker in ('c#',): continue # Ignore our additions
                #value = cleanText # (temp)
                #if Globals.debugFlag and debuggingThisModule: print( "toUSFM: pseudoMarker = '{}' value = '{}'".format( pseudoMarker, value ) )
                if removeVerseBridges and pseudoMarker in ('v','c',):
                    if value1 and value2:
                        for vNum in range( value1+1, value2+1 ): # Fill in missing verse numbers
                            USFM += '\n\\v {}'.format( vNum )
                    value1 = value2 = None

                if pseudoMarker in ('v','f','fr','x','xo',): # These fields should always end with a space but the processing will have removed them
                    if Globals.debugFlag: assert( value )
                    if pseudoMarker=='v' and removeVerseBridges:
                        vString = value
                        for bridgeChar in ('-', '–', '—'): # hyphen, endash, emdash
                            ix = vString.find( bridgeChar )
                            if ix != -1:
                                value = vString[:ix] # Remove verse bridges
                                vEnd = vString[ix+1:]
                                #print( BBB, repr(value), repr(vEnd) )
                                try: value1, value2 = int( value ), int( vEnd )
                                except ValueError:
                                    print( "toUSFM: bridge doesn't seem to be integers in {} {}".format( BBB, repr(vString) ) )
                                    value1 = value2 = None # One of them isn't an integer
                                #print( ' ', BBB, repr(value1), repr(value2) )
                                break
                    if value and value[-1] != ' ': value += ' ' # Append a space since it didn't have one
                if pseudoMarker[-1]=='~' or Globals.USFMMarkers.isNewlineMarker(pseudoMarker): # Have a continuation field
                    if inField is not None:
                        USFM += '\\{}*'.format( inField ) # Do a close marker for footnotes and cross-references
                        inField = None
                if pseudoMarker[-1] == '~':
                    #print( "psMarker ends with squiggle: '{}'='{}'".format( pseudoMarker, value ) )
                    if Globals.debugFlag: assert( pseudoMarker[:-1] in ('v','p','c') )
                    USFM += (' ' if USFM and USFM[-1]!=' ' else '') + value
                else: # not a continuation marker
                    adjValue = value
                    #if pseudoMarker in ('it','bk','ca','nd',): # Character markers to be closed -- had to remove ft and xt from this list for complex footnotes with f fr fq ft fq ft f*
                    if pseudoMarker in allCharMarkers: # Character markers to be closed
                        #if (USFM[-2]=='\\' or USFM[-3]=='\\') and USFM[-1]!=' ':
                        if USFM[-1] != ' ':
                            USFM += ' ' # Separate markers by a space e.g., \p\bk Revelation
                            if Globals.debugFlag: print( "toUSFM: Added space to '{}' before '{}'".format( USFM[-2], pseudoMarker ) )
                        adjValue += '\\{}*'.format( pseudoMarker ) # Do a close marker
                    elif pseudoMarker in ('f','x',): inField = pseudoMarker # Remember these so we can close them later
                    elif pseudoMarker in ('fr','fq','ft','xo',): USFM += '' # These go on the same line just separated by spaces and don't get closed
                    elif USFM: USFM += '\n' # paragraph markers go on a new line
                    if not value: USFM += '\\{}'.format( pseudoMarker )
                    else: USFM += '\\{} {}'.format( pseudoMarker,adjValue )
                #print( pseudoMarker, USFM[-200:] )

            # Write the USFM output
            #print( "\nUSFM", USFM[:3000] )
            filename = "{}{}BWr.SFM".format( USFMNumber, USFMAbbreviation.upper() ) # This seems to be the undocumented standard filename format (and BWr = BibleWriter)
            #if not os.path.exists( USFMOutputFolder ): os.makedirs( USFMOutputFolder )
            filepath = os.path.join( outputFolder, Globals.makeSafeFilename( filename ) )
            if Globals.verbosityLevel > 2: print( "  " + _("Writing '{}'...").format( filepath ) )
            with open( filepath, 'wt' ) as myFile: myFile.write( USFM )

        # Now create a zipped collection
        if Globals.verbosityLevel > 2: print( "  Zipping USFM files..." )
        zf = zipfile.ZipFile( os.path.join( outputFolder, 'AllUSFMFiles.zip' ), 'w', compression=zipfile.ZIP_DEFLATED )
        for filename in os.listdir( outputFolder ):
            if not filename.endswith( '.zip' ):
                filepath = os.path.join( outputFolder, filename )
                zf.write( filepath, filename ) # Save in the archive without the path
        zf.close()

        return True
    # end of BibleWriter.toUSFM



    def toText( self, outputFolder=None ):
        """
        Write the pseudo USFM out into a simple plain-text format.
            The format varies, depending on whether or not there are paragraph markers in the text.
        """
        if Globals.verbosityLevel > 1: print( "Running BibleWriter:toText..." )
        if Globals.debugFlag: assert( self.books )

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolder: outputFolder = "OutputFiles/BOS_PlainText_Export/"
        if not os.access( outputFolder, os.F_OK ): os.makedirs( outputFolder ) # Make the empty folder if there wasn't already one there

        # First determine our format
        columnWidth = 80
        verseByVerse = True

        # Write the plain text files
        for BBB,bookObject in self.books.items():
            pseudoUSFMData = bookObject._processedLines

            filename = "BOS-BWr-{}.txt".format( BBB )
            filepath = os.path.join( outputFolder, Globals.makeSafeFilename( filename ) )
            if Globals.verbosityLevel > 2: print( "  " + _("Writing '{}'...").format( filepath ) )
            textBuffer = ""
            with open( filepath, 'wt' ) as myFile:
                for entry in pseudoUSFMData:
                    marker, text = entry.getMarker(), entry.getCleanText()
                    if marker in ('id','ide','toc1','toc2','toc3','c#',): pass # Completely ignore these fields
                    elif marker == 'h':
                        if textBuffer: myFile.write( "{}".format( textBuffer ) ); textBuffer = ""
                        myFile.write( "{}\n\n".format( text ) )
                    elif marker in ('mt1','mt2','mt3','mt4',):
                        if textBuffer: myFile.write( "{}".format( textBuffer ) ); textBuffer = ""
                        myFile.write( "{}{}\n\n".format( ' '*((columnWidth-len(text))//2), text ) )
                    elif marker in ('is1','is2','is3','is4','ip','ipi','iot','io1','io2','io3','io4',): pass # Drop the introduction
                    elif marker == 'c':
                        C = text
                        if textBuffer: myFile.write( "{}".format( textBuffer ) ); textBuffer = ""
                        myFile.write( "\n\nChapter {}".format( text ) )
                    elif marker == 'v':
                        V = text
                        if textBuffer: myFile.write( "{}".format( textBuffer ) ); textBuffer = ""
                        myFile.write( "\n{} ".format( text ) )
                    elif marker in ('p','s1','s2','s3','s4',): pass # Drop out these fields
                    elif text:
                        textBuffer += (' ' if textBuffer else '') + text
                if textBuffer: myFile.write( "{}\n".format( textBuffer ) ) # Write the last bit

                    #if verseByVerse:
                        #myFile.write( "{} ({}): '{}' '{}' {}\n" \
                            #.format( entry.getMarker(), entry.getOriginalMarker(), entry.getAdjustedText(), entry.getCleanText(), entry.getExtras() ) )

        # Now create a zipped collection
        if Globals.verbosityLevel > 2: print( "  Zipping text files..." )
        zf = zipfile.ZipFile( os.path.join( outputFolder, 'AllTextFiles.zip' ), 'w', compression=zipfile.ZIP_DEFLATED )
        for filename in os.listdir( outputFolder ):
            if not filename.endswith( '.zip' ):
                filepath = os.path.join( outputFolder, filename )
                zf.write( filepath, filename ) # Save in the archive without the path
        zf.close()

        return True
    # end of BibleWriter.toText


    # The following are used by both toHTML5 and toCustomBible
    ipHTMLClassDict = {'ip':'introductoryParagraph', 'ipi':'introductoryParagraphIndented'}
    pqHTMLClassDict = {'p':'proseParagraph', 'm':'flushLeftParagraph',
                       'pmo':'embeddedOpeningParagraph', 'pm':'embeddedParagraph', 'pmc':'embeddedClosingParagraph',
                       'pmr':'embeddedRefrainParagraph',
                       'pi1':'indentedProseParagraph1','pi2':'indentedProseParagraph2','pi3':'indentedProseParagraph3','pi4':'indentedProseParagraph4',
                       'mi':'indentedFlushLeftParagraph', 'cls':'closureParagraph',
                       'pc':'centeredProseParagraph', 'pr':'rightAlignedProseParagraph',
                       'ph1':'hangingProseParagraph1','ph2':'hangingProseParagraph2','ph3':'hangingProseParagraph3','ph4':'hangingProseParagraph4',

                       'q1':'poetryParagraph1','q2':'poetryParagraph2','q3':'poetryParagraph3','q4':'poetryParagraph4',
                       'qr':'rightAlignedPoetryParagraph', 'qc':'centeredPoetryParagraph',
                       'qm1':'embeddedPoetryParagraph1','qm2':'embeddedPoetryParagraph2','qm3':'embeddedPoetryParagraph3','qm4':'embeddedPoetryParagraph4'}


    def __formatHTMLVerseText( BBB, C, V, givenText, extras, ourGlobals ):
        """
        Format character codes within the text into HTML

        Called by toHTML5 and toCustomBible
        """
        #print( "__formatHTMLVerseText( {}, {}, {} )".format( repr(givenText), len(extras), ourGlobals.keys() ) )
        if Globals.debugFlag: assert( givenText or extras )

        def handleExtras( text, extras, ourGlobals ):
            """
            Returns the HTML5 text with footnotes and xrefs processed.
            It also accumulates HTML5 in ourGlobals for the end notes.
            """
            def liveCV( CV ):
                """
                Given a CV text (in the same book), make it live
                    e.g., given 1:3 return #C1V3
                        given 17:4-9 return #C17V4
                        given 1:1-3:19 return #C1V1
                """
                #print( "formatHTMLVerseText.liveCV( {} )".format( repr(CV) ) )
                if len(CV) < 3: return ''
                if CV and CV[-1]==':': CV = CV[:-1]

                result = 'C' + CV.strip().replace( ':', 'V')
                for bridgeChar in ('-', '–', '—'): # hyphen, endash, emdash
                    ix = result.find( bridgeChar )
                    if ix != -1: result = result[:ix] # Remove verse bridges
                #print( " returns", result )
                if Globals.debugFlag and (result.count('C')>1 or result.count('V')>1): halt
                return '#' + result
            # end of liveCV


            def processNote( rawFootnoteContents, ourGlobals, noteType ):
                """
                Return the HTML5 for the processed footnote or endnote.
                It also accumulates HTML5 in ourGlobals for the end notes.

                NOTE: The first parameter here already has the /f or (/fe) and /f* (or /fe*) removed.

                \\f + \\fr 1:20 \\ft Su ka kaluwasan te Nawumi ‘keupianan,’ piru ka kaluwasan te Mara ‘masakit se geyinawa.’\\f* (Backslashes are shown doubled here)
                    gives
                <a title="Su ka kaluwasan te Nawumi &lsquo;keupianan,&rsquo; piru ka kaluwasan te Mara &lsquo;masakit se geyinawa.&rsquo;" href="#FNote0"><span class="FootnoteLinkSymbol"><sup>[fn]</sup></span></a>
                <note style="f" caller="+"><char style="fr" closed="false">2:23 </char><char style="ft">Te Hibruwanen: bayew egpekegsahid ka ngaran te “malitan” wey “lukes.”</char></note>
                    plus
                <p id="FNote0" class="footnote"><a title="Go back up to 1:20 in the text" href="#C1V20"><span class="ChapterVerse">1:20 </span></a><a title="su" href="../../Lexicon/indexLSIM-45.htm#su1"><span class="WordLink">Su</span></a> <a title="ka" href="../../Lexicon/indexLK-87.htm#ka"><span class="WordLink">ka</span></a> <a title="kaluwasan" href="../../Lexicon/indexLLO-67.htm#luwas2"><span class="WordLink">kaluwasan</span></a> <a title="te" href="../../Lexicon/indexLT-96.htm#ta"><span class="WordLink">te</span></a> <span class="NameWordLink">Nawumi</span> &lsquo;<a title="n. fortunate (upian)" href="../../Lexicon/Details/upian.htm"><span class="WordLink">keupianan</span></a>,&rsquo; <a title="conj. but" href="../../Lexicon/Details/piru.htm"><span class="WordLink">piru</span></a> <a title="ka" href="../../Lexicon/indexLK-87.htm#ka"><span class="WordLink">ka</span></a> <a title="kaluwasan" href="../../Lexicon/indexLLO-67.htm#luwas2"><span class="WordLink">kaluwasan</span></a> <a title="te" href="../../Lexicon/indexLT-96.htm#ta"><span class="WordLink">te</span></a> <a title="mara" href="../../Lexicon/Details/mara.htm"><span class="WordLink">Mara</span></a> &lsquo;<a title="adj. painful (sakit)" href="../../Lexicon/Details/sakit.htm"><span class="WordLink">masakit</span></a> <a title="se" href="../../Lexicon/indexLSE-64.htm#se1"><span class="WordLink">se</span></a> <a title="n. breath" href="../../Lexicon/Details/geyinawa.htm"><span class="WordLink">geyinawa</span></a>.&rsquo;</p>
                <p id="FNote1" class="footnote"><a title="Go back up to 3:9 in the text" href="#C3V9"><span class="ChapterVerse">3:9 </span></a><a title="te" href="../../Lexicon/indexLT-96.htm#ta"><span class="WordLink">Te</span></a> <a title="prop_n. Hebrew language (Hibru)" href="../../Lexicon/Details/Hibru.htm"><span class="WordLink">Hibruwanen</span></a>: <a title="buni" href="../../Lexicon/Details/buni2.htm"><span class="WordLink">Bunbuni</span></a> <a title="pron. you(sg); by you(sg)" href="../../Lexicon/Details/nu.htm"><span class="WordLink">nu</span></a> <a title="te" href="../../Lexicon/indexLT-96.htm#ta"><span class="WordLink">te</span></a> <a title="kumbalè" href="../../Lexicon/Details/kumbal%C3%A8.htm"><span class="WordLink">kumbale</span></a> <a title="pron. you(sg); by you(sg)" href="../../Lexicon/Details/nu.htm"><span class="WordLink">nu</span></a> <a title="ka" href="../../Lexicon/indexLK-87.htm#ka"><span class="WordLink">ka</span></a> <a title="suluhuanen" href="../../Lexicon/indexLSIM-45.htm#suluh%C3%B9"><span class="WordLink">suluhuanen</span></a> <a title="pron. you(sg); by you(sg)" href="../../Lexicon/Details/nu.htm"><span class="WordLink">nu</span></a>.</p>
                <p id="FNote2" class="footnote"><a title="Go back up to 4:11 in the text" href="#C4V11"><span class="ChapterVerse">4:11 </span></a><a title="ne" href="../../Lexicon/indexLN-90.htm#ne1a"><span class="WordLink">Kene</span></a> <a title="ne" href="../../Lexicon/indexLN-90.htm#ne1a"><span class="WordLink">ne</span></a> <a title="adj. clear" href="../../Lexicon/Details/klaru.htm"><span class="WordLink">klaru</span></a> <a title="diya" href="../../Lexicon/indexLD-80.htm#diyav"><span class="WordLink">diye</span></a> <a title="te" href="../../Lexicon/indexLT-96.htm#ta"><span class="WordLink">te</span></a> <a title="adj. true (lehet)" href="../../Lexicon/Details/lehet1.htm"><span class="WordLink">malehet</span></a> <a title="ne" href="../../Lexicon/indexLN-90.htm#ne1a"><span class="WordLink">ne</span></a> <a title="migpuun" href="../../Lexicon/Details/puun.htm"><span class="WordLink">migpuunan</span></a> <a title="ke" href="../../Lexicon/indexLK-87.htm#ka"><span class="WordLink">ke</span></a> <a title="n. other" href="../../Lexicon/Details/lein.htm"><span class="WordLink">lein</span></a> <a title="e" href="../../Lexicon/indexLA-77.htm#a"><span class="WordLink">e</span></a> <a title="part. also" href="../../Lexicon/Details/degma.htm"><span class="WordLink">degma</span></a> <a title="ne" href="../../Lexicon/indexLN-90.htm#ne1a"><span class="WordLink">ne</span></a> <a title="n. place" href="../../Lexicon/Details/inged.htm"><span class="WordLink">inged</span></a> <a title="ka" href="../../Lexicon/indexLK-87.htm#ka"><span class="WordLink">ka</span></a> <span class="NameWordLink">Iprata</span>. <a title="kahiyen" href="../../Lexicon/Details/kahi.htm"><span class="WordLink">Kahiyen</span></a> <a title="te" href="../../Lexicon/indexLT-96.htm#ta"><span class="WordLink">te</span></a> <a title="adj. other" href="../../Lexicon/Details/duma.htm"><span class="WordLink">duma</span></a> <a title="ne" href="../../Lexicon/indexLN-90.htm#ne1a"><span class="WordLink">ne</span></a> <a title="ka" href="../../Lexicon/indexLK-87.htm#ka"><span class="WordLink">ka</span></a> <span class="NameWordLink">Iprata</span> <a title="dem. that" href="../../Lexicon/Details/iyan.htm"><span class="WordLink">iyan</span></a> <a title="ka" href="../../Lexicon/indexLK-87.htm#ka"><span class="WordLink">ka</span></a> <a title="tapey" href="../../Lexicon/indexLT-96.htm#tapey1"><span class="WordLink">tapey</span></a> <a title="ne" href="../../Lexicon/indexLN-90.htm#ne1a"><span class="WordLink">ne</span></a> <a title="n. name" href="../../Lexicon/Details/ngaran.htm"><span class="WordLink">ngaran</span></a> <a title="te" href="../../Lexicon/indexLT-96.htm#ta"><span class="WordLink">te</span></a> <a title="See glossary entry for Bitlihim" href="../indexGlossary.htm#Bitlihim"><span class="WordLink">Bitlihim</span><span class="GlossaryLinkSymbol"><sup>[gl]</sup></span></a>.</p></div>
                """
                assert( noteType in ('footnote','endnote',) )
                markerList = Globals.USFMMarkers.getMarkerListFromText( rawFootnoteContents, includeInitialText=True )
                #print( "formatHTMLVerseText.processFootnote( {}, {} ) found {}".format( repr(rawFootnoteContents), ourGlobals, markerList ) )
                if noteType == 'footnote':
                    fnIndex = ourGlobals['nextFootnoteIndex']; ourGlobals['nextFootnoteIndex'] += 1
                elif noteType == 'endnote':
                    fnIndex = ourGlobals['nextEndnoteIndex']; ourGlobals['nextEndnoteIndex'] += 1
                caller = origin = originCV = fnText = fnTitle = ''
                if markerList: # We found some internal footnote markers
                    spanOpen = False
                    for marker, ixBS, nextSignificantChar, fullMarkerText, context, ixEnd, txt in markerList:
                        if spanOpen: fnText += '</span>'; spanOpen = False
                        if marker is None:
                            #if txt not in '-+': # just a caller
                            caller = txt
                        elif marker == 'fr':
                            origin = txt
                            originCV = origin
                            if originCV and originCV[-1] in (':','.'): originCV = originCV[:-1]
                            originCV = originCV.strip()
                        elif marker == 'ft':
                            fnText += txt
                            fnTitle += txt
                        elif marker == 'fk':
                            fnText += '<span class="{}Keyword">'.format( noteType ) + txt
                            fnTitle += txt
                            spanOpen = True
                        elif marker == 'fq':
                            fnText += '<span class="{}TranslationQuotation">'.format( noteType ) + txt
                            fnTitle += txt
                            spanOpen = True
                        elif marker == 'fqa':
                            fnText += '<span class="{}AlternateTranslation">'.format( noteType ) + txt
                            fnTitle += txt
                            spanOpen = True
                        elif marker == 'fl':
                            fnText += '<span class="{}Label">'.format( noteType ) + txt
                            fnTitle += txt
                            spanOpen = True
                        #elif marker == Should handle other internal markers here
                        else:
                            logging.error( "formatHTMLVerseText.processNote didn't handle {} {}:{} {} marker: {}".format( BBB, C, V, noteType, marker ) )
                            fnText += txt
                            fnTitle += txt
                    if spanOpen: fnText += '</span>'; spanOpen = False
                else: # no internal markers found
                    bits = rawFootnoteContents.split( ' ', 1 )
                    if len(bits)==2: # assume the caller is the first bit
                        caller = bits[0]
                        if Globals.debugFlag: assert( len(caller) == 1 ) # Normally a +
                        fnText = fnTitle = bits[1]
                    else: # no idea really what the format was
                        fnText = fnTitle = rawFootnoteContents

                idName = "{}{}".format( 'FNote' if noteType=='footnote' else 'ENote', fnIndex )
                noteHTML5 = '<a class="{}LinkSymbol" title="{}" href="#{}">[fn]</a>' \
                                .format( noteType, fnTitle, idName )

                endHTML5 = '<p id="{}" class="{}">'.format( idName, noteType )
                if originCV:
                    endHTML5 += '<a class="{}Origin" title="Go back up to {} in the text" href="{}">{}</a> ' \
                                                        .format( noteType, originCV, liveCV(originCV), origin )
                endHTML5 += '<span class="{}Entry">{}</span>'.format( noteType, fnText )
                endHTML5 += '</p>'

                #print( "noteHTML5", BBB, noteHTML5 )
                #print( "endHTML5", endHTML5 )
                ourGlobals['footnoteHTML5' if noteType=='footnote' else 'endnoteHTML5'].append( endHTML5 )
                #if fnIndex > 2: halt

                return noteHTML5
            # end of __formatHTMLVerseText.processNote


            def processXRef( HTML5xref, ourGlobals ):
                """
                Return the HTML5 for the processed cross-reference (xref).
                It also accumulates HTML5 in ourGlobals for the end notes.

                NOTE: The parameter here already has the /x and /x* removed.

                \\x - \\xo 2:2: \\xt Lib 19:9-10; Diy 24:19.\\xt*\\x* (Backslashes are shown doubled here)
                    gives
                <a title="Lib 19:9-10; Diy 24:19" href="#XRef0"><span class="XRefLinkSymbol"><sup>[xr]</sup></span></a>
                <a title="Lib 25:25" href="#XRef1"><span class="XRefLinkSymbol"><sup>[xr]</sup></span></a>
                <a title="Rut 2:20" href="#XRef2"><span class="XRefLinkSymbol"><sup>[xr]</sup></span></a>
                    plus
                <p id="XRef0" class="XRef"><a title="Go back up to 2:2 in the text" href="#C2V2"><span class="ChapterVerse">2:2</span></a> <span class="VernacularCrossReference">Lib 19:9&#x2011;10</span>; <span class="VernacularCrossReference">Diy 24:19</span></p>
                """
                markerList = Globals.USFMMarkers.getMarkerListFromText( HTML5xref, includeInitialText=True )
                #print( "\nformatHTMLVerseText.processXRef( {}, {} ) gives {}".format( repr(HTML5xref), "...", markerList ) )
                xrefIndex = ourGlobals['nextXRefIndex']; ourGlobals['nextXRefIndex'] += 1
                caller = origin = originCV = xrefText = ''
                if markerList:
                    for marker, ixBS, nextSignificantChar, fullMarkerText, context, ixEnd, txt in markerList:
                        if marker is None:
                            #if txt not in '-+': # just a caller
                            caller = txt
                        elif marker == 'xo':
                            origin = txt
                            originCV = origin
                            originCV = originCV.strip()
                            if originCV and originCV[-1] in (':','.'): originCV = originCV[:-1]
                        elif marker == 'xt':
                            xrefText += txt
                        #elif marker == Should handle other internal markers here
                        else:
                            logging.error( "formatHTMLVerseText.processXRef didn't handle {} {}:{} xref marker: {}".format( BBB, C, V, marker ) )
                            xrefText += txt
                else: # there's no USFM markers at all in the xref --  presumably a caller and then straight text
                    if HTML5xref.startswith('+ ') or HTML5xref.startswith('- '):
                        caller = HTML5xref[0]
                        xrefText = HTML5xref[2:].strip()
                    else: # don't really know what it is -- assume it's all just text
                        xrefText = HTML5xref.strip()

                xrefHTML5 = '<a class="xrefLinkSymbol" title="{}" href="#XRef{}">[xr]</a>' \
                                .format( xrefText, xrefIndex )

                endHTML5 = '<p id="XRef{}" class="xref">'.format( xrefIndex )
                if not origin: # we'll try to make one
                    originCV = "{}:{}".format( C, V )
                if originCV: # This only handles CV separator of : so far
                    endHTML5 += '<a class="xrefOrigin" title="Go back up to {} in the text" href="{}">{}</a> ' \
                                                        .format( originCV, liveCV(originCV), originCV )
                endHTML5 += '<span class="xrefEntry">{}</span>'.format( xrefText )
                endHTML5 += '</p>'

                #print( "xrefHTML5", BBB, xrefHTML5 )
                #print( "endHTML5", endHTML5 )
                ourGlobals['xrefHTML5'].append( endHTML5 )
                #if xrefIndex > 2: halt

                return xrefHTML5
            # end of __formatHTMLVerseText.processXRef


            def processFigure( HTML5figure, ourGlobals ):
                """
                Return the HTML5 for the processed figure.

                NOTE: The parameter here already has the /fig and /fig* removed.
                """
                logging.critical( "toHTML5: figure not handled yet at {} {}:{} {}".format( BBB, C, V, repr(HTML5figure) ) )
                figureHTML5 = ''
                #footnoteHTML5 = '<a class="footnoteLinkSymbol" title="{}" href="#FNote{}">[fn]</a>' \
                                #.format( fnTitle, fnIndex )

                #endHTML5 = '<p id="FNote{}" class="footnote">'.format( fnIndex )
                #if originCV: # This only handles CV separator of : so far
                    #endHTML5 += '<a class="footnoteOrigin" title="Go back up to {} in the text" href="{}">{}</a> ' \
                                                        #.format( originCV, liveCV(originCV), origin )
                #endHTML5 += '<span class="footnoteEntry">{}</span>'.format( fnText )
                #endHTML5 += '</p>'

                ##print( "footnoteHTML5", BBB, footnoteHTML5 )
                ##print( "endHTML5", endHTML5 )
                #ourGlobals['footnoteHTML5'].append( endHTML5 )
                ##if fnIndex > 2: halt

                return figureHTML5
            # end of __formatHTMLVerseText.processFigure


            adjText = text
            offset = 0
            for extraType, extraIndex, extraText, cleanExtraText in extras: # do any footnotes and cross-references
                #print( "{} {}:{} Text='{}' eT={}, eI={}, eText='{}'".format( BBB, C, V, text, extraType, extraIndex, extraText ) )
                adjIndex = extraIndex - offset
                lenT = len( adjText )
                if adjIndex > lenT: # This can happen if we have verse/space/notes at end (and the space was deleted after the note was separated off)
                    logging.warning( _("formatHTMLVerseText: Space before note at end of verse in {} {}:{} has been lost").format( BBB, C, V ) )
                    # No need to adjust adjIndex because the code below still works
                elif adjIndex<0 or adjIndex>lenT: # The extras don't appear to fit correctly inside the text
                    print( "formatHTMLVerseText: Extras don't fit inside verse at {} {}:{}: eI={} o={} len={} aI={}".format( BBB, C, V, extraIndex, offset, len(text), adjIndex ) )
                    print( "  Verse='{}'".format( text ) )
                    print( "  Extras='{}'".format( extras ) )
                #assert( 0 <= adjIndex <= len(verse) )
                #adjText = checkText( extraText, checkLeftovers=False ) # do any general character formatting
                #if adjText!=extraText: print( "processXRefsAndFootnotes: {}@{}-{}={} '{}' now '{}'".format( extraType, extraIndex, offset, adjIndex, extraText, adjText ) )
                if extraType == 'fn':
                    extra = processNote( extraText, ourGlobals, 'footnote' )
                    #print( "fn got", extra )
                elif extraType == 'en':
                    extra = processNote( extraText, ourGlobals, 'endnote' )
                    #print( "en got", extra )
                elif extraType == 'xr':
                    extra = processXRef( extraText, ourGlobals )
                    #print( "xr got", extra )
                elif extraType == 'fig':
                    extra = processFigure( extraText, ourGlobals )
                    #print( "fig got", extra )
                elif Globals.debugFlag and debuggingThisModule: print( 'eT', extraType ); halt
                #print( "was", verse )
                adjText = adjText[:adjIndex] + extra + adjText[adjIndex:]
                offset -= len( extra )
                #print( "now", verse )
            return adjText
        # end of __formatHTMLVerseText.handleExtras


        # __formatHTMLVerseText main code
        text = handleExtras( givenText, extras, ourGlobals )

        # Semantic stuff
        text = text.replace( '\\ior ', '<span class="outlineReferenceRange">' ).replace( '\\ior*', '</span>' )
        text = text.replace( '\\bk ', '<span class="bookName">' ).replace( '\\bk*', '</span>' )
        text = text.replace( '\\add ', '<span class="addedText">' ).replace( '\\add*', '</span>' )
        text = text.replace( '\\nd ', '<span class="divineName">' ).replace( '\\nd*', '</span>' )
        text = text.replace( '\\+nd ', '<span class="divineName">' ).replace( '\\+nd*', '</span>' )
        text = text.replace( '\\wj ', '<span class="wordsOfJesus">' ).replace( '\\wj*', '</span>' )
        text = text.replace( '\\sig ', '<span class="signature">' ).replace( '\\sig*', '</span>' )
        text = text.replace( '\\k ', '<span class="keyWord">' ).replace( '\\k*', '</span>' )
        text = text.replace( '\\rq ', '<span class="quotationReference">' ).replace( '\\rq*', '</span>' )
        text = text.replace( '\\qs ', '<span class="Selah">' ).replace( '\\qs*', '</span>' )

        # Direct formatting
        text = text.replace( '\\bdit ', '<span class="boldItalic">' ).replace( '\\bdit*', '</span>' )
        text = text.replace( '\\it ', '<span class="italic">' ).replace( '\\it*', '</span>' )
        text = text.replace( '\\bd ', '<span class="bold">' ).replace( '\\bd*', '</span>' )
        text = text.replace( '\\sc ', '<span class="smallCaps">' ).replace( '\\sc*', '</span>' )

        if '\\' in text:
            logging.error( "formatHTMLVerseText programming error: unprocessed code in {} from {} at {} {}:{}".format( repr(text), repr(givenText), BBB, C, V ) )
            if Globals.debugFlag or Globals.verbosityLevel > 2:
                print( "formatHTMLVerseText: unprocessed code in {} from {} at {} {}:{}".format( repr(text), repr(givenText), BBB, C, V ) )
            if Globals.debugFlag and debuggingThisModule: halt
        return text
    # end of __formatHTMLVerseText


    def toHTML5( self, outputFolder=None, controlDict=None, validationSchema=None, humanReadable=True ):
        """
        Using settings from the given control file,
            converts the USFM information to UTF-8 HTML files.
        """
        if Globals.verbosityLevel > 1: print( "Running BibleWriter:toHTML5..." )
        if Globals.debugFlag:
            #print( self )
            assert( self.books )
            assert( self.name )

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolder: outputFolder = "OutputFiles/BOS_HTML5_Export/"
        WEBoutputFolder = os.path.join( outputFolder, "Website/" )
        if not os.access( outputFolder, os.F_OK ): os.makedirs( WEBoutputFolder ) # Make the empty folder if there wasn't already one there

        if not controlDict:
            controlDict, defaultControlFilename = {}, "To_HTML5_controls.txt"
            try:
                ControlFiles.readControlFile( defaultControlFolder, defaultControlFilename, controlDict )
            except:
                logging.critical( "Unable to read control dict {} from {}".format( defaultControlFilename, defaultControlFolder ) )
        self.__adjustControlDict( controlDict )

        # Copy across our css style files
        for filenamePart in ( 'BibleBook', ):
            filepath = os.path.join( defaultControlFolder, filenamePart+'.css' )
            try:
                shutil.copy( filepath, WEBoutputFolder ) # Copy it under its own name
                #shutil.copy( filepath, os.path.join( WEBoutputFolder, "Bible.css" ) ) # Copy it also under the generic name
            except FileNotFoundError: logging.error( "Unable to find CSS style file: {}".format( filepath ) )

        unhandledMarkers = set()


        def writeHeader( writerObject, myBBB ):
            """
            Writes the HTML5 header to the HTML writerObject.
            MyBBB can be the book code or 'home' or 'about'.
            """
            writerObject.writeLineOpen( 'head' )
            writerObject.writeLineText( '<meta http-equiv="Content-Type" content="text/html;charset=utf-8">', noTextCheck=True )
            writerObject.writeLineText( '<link rel="stylesheet" type="text/css" href="BibleBook.css">', noTextCheck=True )
            if 'HTML5Title' in controlDict and controlDict['HTML5Title']:
                writerObject.writeLineOpenClose( 'title' , controlDict['HTML5Title'] )
            #if "HTML5Subject" in controlDict and controlDict["HTML5Subject"]: writerObject.writeLineOpenClose( 'subject', controlDict["HTML5Subject"] )
            #if "HTML5Description" in controlDict and controlDict["HTML5Description"]: writerObject.writeLineOpenClose( 'description', controlDict["HTML5Description"] )
            #if "HTML5Publisher" in controlDict and controlDict["HTML5Publisher"]: writerObject.writeLineOpenClose( 'publisher', controlDict["HTML5Publisher"] )
            #if "HTML5Contributors" in controlDict and controlDict["HTML5Contributors"]: writerObject.writeLineOpenClose( 'contributors', controlDict["HTML5Contributors"] )
            #if "HTML5Identifier" in controlDict and controlDict["HTML5Identifier"]: writerObject.writeLineOpenClose( 'identifier', controlDict["HTML5Identifier"] )
            #if "HTML5Source" in controlDict and controlDict["HTML5Source"]: writerObject.writeLineOpenClose( 'identifier', controlDict["HTML5Source"] )
            #if "HTML5Coverage" in controlDict and controlDict["HTML5Coverage"]: writerObject.writeLineOpenClose( 'coverage', controlDict["HTML5Coverage"] )
            #writerObject.writeLineOpenClose( 'format', 'HTML5 markup language' )
            #writerObject.writeLineOpenClose( 'date', datetime.now().date().isoformat() )
            #writerObject.writeLineOpenClose( 'creator', 'BibleWriter.py' )
            #writerObject.writeLineOpenClose( 'type', 'bible text' )
            #if "HTML5Language" in controlDict and controlDict["HTML5Language"]: writerObject.writeLineOpenClose( 'language', controlDict["HTML5Language"] )
            #if "HTML5Rights" in controlDict and controlDict["HTML5Rights"]: writerObject.writeLineOpenClose( 'rights', controlDict["HTML5Rights"] )
            writerObject.writeLineClose( 'head' )

            writerObject.writeLineOpen( 'body' )

            writerObject.writeLineOpen( 'header' )
            if myBBB == 'home': writerObject.writeLineOpenClose( 'p', 'Home', ('class','homeNonlink') )
            else: writerObject.writeLineOpenClose( 'a', 'Home', [('href','index.html'),('class','homeLink')] )
            if myBBB == 'about': writerObject.writeLineOpenClose( 'p', 'About', ('class','homeNonlink') )
            else: writerObject.writeLineOpenClose( 'a', 'About', [('href','about.html'),('class','aboutLink')] )
            writerObject.writeLineOpenClose( 'h1', self.name, ('class','mainHeader') )
            bkList = self.getBookList()
            if myBBB  in bkList:
                ix = bkList.index( myBBB )
                if ix > 0:
                    writerObject.writeLineOpenClose( 'a', 'Previous book', [('href',filenameDict[bkList[ix-1]]),('class','bookNav')] )
                writerObject.writeLineOpenClose( 'a', 'Book start', [('href','#C1V1'),('class','bookNav')] )
                if ix < len(bkList)-1:
                    writerObject.writeLineOpenClose( 'a', 'Next book', [('href',filenameDict[bkList[ix+1]]),('class','bookNav')] )
            writerObject.writeLineClose( 'header' )

            # Create the nav bar for books
            writerObject.writeLineOpen( 'nav' )
            writerObject.writeLineOpen( 'ul' )
            for bkData in self:
                BBB = bkData.bookReferenceCode
                bkName = bkData.getAssumedBookNames()[0]
                if BBB == myBBB:
                    writerObject.writeLineText( '<li class="bookNameEntry"><span class="currentBookName">{}</span></li>'.format( bkName ), noTextCheck=True )
                else:
                    writerObject.writeLineText( '<li class="bookNameEntry"><a class="bookNameLink" href="{}">{}</a></li>'.format( filenameDict[BBB], bkName ), noTextCheck=True )
            writerObject.writeLineClose( 'ul' )
            writerObject.writeLineClose( 'nav' )
        # end of toHTML5.writeHeader


        def writeEndNotes( writerObject, ourGlobals ):
            """
            Writes the HTML5 end notes (footnotes, endnotes, and cross-references) to the HTML writerObject.

            <div id="XRefs- Normal"><h2 class="XRefsHeading">Cross References</h2>
            <p id="XRef0" class="XRef"><a title="Go back up to 2:2 in the text" href="#C2V2"><span class="ChapterVerse">2:2</span></a> <span class="VernacularCrossReference">Lib 19:9&#x2011;10</span>; <span class="VernacularCrossReference">Diy 24:19</span></p>
            <p id="XRef1" class="XRef"><a title="Go back up to 2:20 in the text" href="#C2V20"><span class="ChapterVerse">2:20</span></a> <span class="VernacularCrossReference">Lib 25:25</span></p>
            <p id="XRef2" class="XRef"><a title="Go back up to 3:12 in the text" href="#C3V12"><span class="ChapterVerse">3:12</span></a> <a title="Go to Rut 2:20" href="RUT.htm#C2V20"><span class="VernacularCrossReference">Rut 2:20</span></a></p>
            <p id="XRef3" class="XRef"><a title="Go back up to 4:7 in the text" href="#C4V7"><span class="ChapterVerse">4:7</span></a> <span class="VernacularCrossReference">Diy 25:9</span></p>
            <p id="XRef4" class="XRef"><a title="Go back up to 4:10 in the text" href="#C4V10"><span class="ChapterVerse">4:10</span></a> <span class="VernacularCrossReference">Diy 25:5&#x2011;6</span></p>
            <p id="XRef5" class="XRef"><a title="Go back up to 4:11 in the text" href="#C4V11"><span class="ChapterVerse">4:11</span></a> <a title="Go to Hinisis 29:31" href="GEN.htm#C29V31"><span class="VernacularCrossReference">Hin 29:31</span></a></p>
            <p id="XRef6" class="XRef"><a title="Go back up to 4:12 in the text" href="#C4V12"><span class="ChapterVerse">4:12</span></a> <a title="Go to Hinisis 38:27" href="GEN.htm#C38V27"><span class="VernacularCrossReference">Hin 38:27&#x2011;30</span></a></p></div>
            <div id="FNotes"><h2 class="FootnotesHeading">Footnotes</h2>
            <p id="FNote0" class="Footnote"><a title="Go back up to 1:20 in the text" href="#C1V20"><span class="ChapterVerse">1:20 </span></a><a title="su" href="../../Lexicon/indexLSIM-45.htm#su1"><span class="WordLink">Su</span></a> <a title="ka" href="../../Lexicon/indexLK-87.htm#ka"><span class="WordLink">ka</span></a> <a title="kaluwasan" href="../../Lexicon/indexLLO-67.htm#luwas2"><span class="WordLink">kaluwasan</span></a> <a title="te" href="../../Lexicon/indexLT-96.htm#ta"><span class="WordLink">te</span></a> <span class="NameWordLink">Nawumi</span> &lsquo;<a title="n. fortunate (upian)" href="../../Lexicon/Details/upian.htm"><span class="WordLink">keupianan</span></a>,&rsquo; <a title="conj. but" href="../../Lexicon/Details/piru.htm"><span class="WordLink">piru</span></a> <a title="ka" href="../../Lexicon/indexLK-87.htm#ka"><span class="WordLink">ka</span></a> <a title="kaluwasan" href="../../Lexicon/indexLLO-67.htm#luwas2"><span class="WordLink">kaluwasan</span></a> <a title="te" href="../../Lexicon/indexLT-96.htm#ta"><span class="WordLink">te</span></a> <a title="mara" href="../../Lexicon/Details/mara.htm"><span class="WordLink">Mara</span></a> &lsquo;<a title="adj. painful (sakit)" href="../../Lexicon/Details/sakit.htm"><span class="WordLink">masakit</span></a> <a title="se" href="../../Lexicon/indexLSE-64.htm#se1"><span class="WordLink">se</span></a> <a title="n. breath" href="../../Lexicon/Details/geyinawa.htm"><span class="WordLink">geyinawa</span></a>.&rsquo;</p>
            <p id="FNote1" class="Footnote"><a title="Go back up to 3:9 in the text" href="#C3V9"><span class="ChapterVerse">3:9 </span></a><a title="te" href="../../Lexicon/indexLT-96.htm#ta"><span class="WordLink">Te</span></a> <a title="prop_n. Hebrew language (Hibru)" href="../../Lexicon/Details/Hibru.htm"><span class="WordLink">Hibruwanen</span></a>: <a title="buni" href="../../Lexicon/Details/buni2.htm"><span class="WordLink">Bunbuni</span></a> <a title="pron. you(sg); by you(sg)" href="../../Lexicon/Details/nu.htm"><span class="WordLink">nu</span></a> <a title="te" href="../../Lexicon/indexLT-96.htm#ta"><span class="WordLink">te</span></a> <a title="kumbalè" href="../../Lexicon/Details/kumbal%C3%A8.htm"><span class="WordLink">kumbale</span></a> <a title="pron. you(sg); by you(sg)" href="../../Lexicon/Details/nu.htm"><span class="WordLink">nu</span></a> <a title="ka" href="../../Lexicon/indexLK-87.htm#ka"><span class="WordLink">ka</span></a> <a title="suluhuanen" href="../../Lexicon/indexLSIM-45.htm#suluh%C3%B9"><span class="WordLink">suluhuanen</span></a> <a title="pron. you(sg); by you(sg)" href="../../Lexicon/Details/nu.htm"><span class="WordLink">nu</span></a>.</p>
            <p id="FNote2" class="Footnote"><a title="Go back up to 4:11 in the text" href="#C4V11"><span class="ChapterVerse">4:11 </span></a><a title="ne" href="../../Lexicon/indexLN-90.htm#ne1a"><span class="WordLink">Kene</span></a> <a title="ne" href="../../Lexicon/indexLN-90.htm#ne1a"><span class="WordLink">ne</span></a> <a title="adj. clear" href="../../Lexicon/Details/klaru.htm"><span class="WordLink">klaru</span></a> <a title="diya" href="../../Lexicon/indexLD-80.htm#diyav"><span class="WordLink">diye</span></a> <a title="te" href="../../Lexicon/indexLT-96.htm#ta"><span class="WordLink">te</span></a> <a title="adj. true (lehet)" href="../../Lexicon/Details/lehet1.htm"><span class="WordLink">malehet</span></a> <a title="ne" href="../../Lexicon/indexLN-90.htm#ne1a"><span class="WordLink">ne</span></a> <a title="migpuun" href="../../Lexicon/Details/puun.htm"><span class="WordLink">migpuunan</span></a> <a title="ke" href="../../Lexicon/indexLK-87.htm#ka"><span class="WordLink">ke</span></a> <a title="n. other" href="../../Lexicon/Details/lein.htm"><span class="WordLink">lein</span></a> <a title="e" href="../../Lexicon/indexLA-77.htm#a"><span class="WordLink">e</span></a> <a title="part. also" href="../../Lexicon/Details/degma.htm"><span class="WordLink">degma</span></a> <a title="ne" href="../../Lexicon/indexLN-90.htm#ne1a"><span class="WordLink">ne</span></a> <a title="n. place" href="../../Lexicon/Details/inged.htm"><span class="WordLink">inged</span></a> <a title="ka" href="../../Lexicon/indexLK-87.htm#ka"><span class="WordLink">ka</span></a> <span class="NameWordLink">Iprata</span>. <a title="kahiyen" href="../../Lexicon/Details/kahi.htm"><span class="WordLink">Kahiyen</span></a> <a title="te" href="../../Lexicon/indexLT-96.htm#ta"><span class="WordLink">te</span></a> <a title="adj. other" href="../../Lexicon/Details/duma.htm"><span class="WordLink">duma</span></a> <a title="ne" href="../../Lexicon/indexLN-90.htm#ne1a"><span class="WordLink">ne</span></a> <a title="ka" href="../../Lexicon/indexLK-87.htm#ka"><span class="WordLink">ka</span></a> <span class="NameWordLink">Iprata</span> <a title="dem. that" href="../../Lexicon/Details/iyan.htm"><span class="WordLink">iyan</span></a> <a title="ka" href="../../Lexicon/indexLK-87.htm#ka"><span class="WordLink">ka</span></a> <a title="tapey" href="../../Lexicon/indexLT-96.htm#tapey1"><span class="WordLink">tapey</span></a> <a title="ne" href="../../Lexicon/indexLN-90.htm#ne1a"><span class="WordLink">ne</span></a> <a title="n. name" href="../../Lexicon/Details/ngaran.htm"><span class="WordLink">ngaran</span></a> <a title="te" href="../../Lexicon/indexLT-96.htm#ta"><span class="WordLink">te</span></a> <a title="See glossary entry for Bitlihim" href="../indexGlossary.htm#Bitlihim"><span class="WordLink">Bitlihim</span><span class="GlossaryLinkSymbol"><sup>[gl]</sup></span></a>.</p></div>
            """
            if ourGlobals['footnoteHTML5'] or ourGlobals['endnoteHTML5'] or ourGlobals['xrefHTML5']:
                writerObject.writeLineOpen( 'div' ) # endNotes
                if ourGlobals['footnoteHTML5']:
                    #writerObject.writeLineOpenSelfclose( 'hr' )
                    writerObject.writeLineOpenClose( 'h3', 'Footnotes', ('class','footnotesHeader') )
                    writerObject.writeLineOpen( 'div', ('class','footnoteLine') )
                    for line in ourGlobals['footnoteHTML5']:
                        writerObject.writeLineText( line, noTextCheck=True )
                    writerObject.writeLineClose( 'div' )
                if ourGlobals['endnoteHTML5']:
                    #writerObject.writeLineOpenSelfclose( 'hr' )
                    writerObject.writeLineOpenClose( 'h3', 'Endnotes', ('class','endnotesHeader') )
                    writerObject.writeLineOpen( 'div', ('class','endnoteLine') )
                    for line in ourGlobals['endnoteHTML5']:
                        writerObject.writeLineText( line, noTextCheck=True )
                    writerObject.writeLineClose( 'div' )
                if ourGlobals['xrefHTML5']:
                    #writerObject.writeLineOpenSelfclose( 'hr' )
                    writerObject.writeLineOpenClose( 'h3', 'Cross References', ('class','xrefsHeader') )
                    writerObject.writeLineOpen( 'div', ('class','xrefSection') )
                    for line in ourGlobals['xrefHTML5']:
                        writerObject.writeLineText( line, noTextCheck=True )
                    writerObject.writeLineClose( 'div' )
                writerObject.writeLineClose( 'div' ) # endNotes
        # end of toHTML5.writeEndNotes


        def writeFooter( writerObject ):
            """Writes the HTML5 footer to the HTML writerObject."""
            writerObject.writeLineOpen( 'footer' )
            writerObject.writeLineOpen( 'p', ('class','footerLine') )
            writerObject.writeLineOpen( 'a', ('href','http://www.w3.org/html/logo/') )
            writerObject.writeLineText( '<img src="http://www.w3.org/html/logo/badge/html5-badge-h-css3-semantics.png" width="165" height="64" alt="HTML5 Powered with CSS3 / Styling, and Semantics" title="HTML5 Powered with CSS3 / Styling, and Semantics">', noTextCheck=True )
            writerObject.writeLineClose( 'a' )
            writerObject.writeLineText( "This page automatically created {} by {} v{}".format( datetime.today().strftime("%d-%b-%Y"), ProgName, ProgVersion ) )
            writerObject.writeLineClose( 'p' )
            writerObject.writeLineClose( 'footer' )
            writerObject.writeLineClose( 'body' )
        # end of toHTML5.writeFooter


        def convertToPageReference( refTuple ):
            """
            Given a reference 4-tuple like ('LUK','15','18','')
                convert it to an HTML link.
            """
            #print( "toHTML5.convertToPageReference( {} )".format( refTuple ) )
            assert( refTuple and len(refTuple)==4 )
            assert( refTuple[0] is None or ( refTuple[0] and len(refTuple[0])==3 ) ) #BBB
            if refTuple[0] in filenameDict:
                return '{}#C{}V{}'.format( filenameDict[refTuple[0]], refTuple[1], refTuple[2] )
            else: logging.error( "toHTML5.convertToPageReference can't find book: {}".format( repr(refTuple[0]) ) )
        # end of toHTML5.convertToPageReference


        def createSectionCrossReference( givenRef ):
            """
            Returns an HTML string for a section cross-reference.

            Must be able to handle things like:
                (Mat. 19:9; Mar. 10:11-12; Luk. 16:18)
                (Luk. 6:27-28,32-36)
                (Luk. 16:13; 12:22-31)
                (1 Kru. 11:1-9; 14:1-7)
            """
            #print( "toHTML5.createSectionCrossReference: '{}'".format( givenRef ) )
            adjRef = givenRef
            result = bracket = ''
            for bracketLeft,bracketRight in (('(',')'),('[',']'),):
                if adjRef and adjRef[0]==bracketLeft and adjRef[-1]==bracketRight:
                    result += bracketLeft
                    bracket = bracketRight
                    adjRef = adjRef[1:-1] # Remove the brackets
            for j,originalRef in enumerate( adjRef.split( ';' ) ):
                #print( " ", j, originalRef )
                if j: result += ';' # Restore the semicolons
                ref = originalRef.strip()
                if ref:
                    if j: # later section refs might not include the book name, e.g., Luk. 16:13; 12:22-31
                        letterCount = 0
                        for char in ref:
                            if char.isalpha(): letterCount += 1
                        if letterCount < 2: # Allows for something like 16:13a but assumes no single letter book abbrevs
                            ref = ((analysis[0]+' ') if analysis else '' ) + ref # Prepend the last BBB if there was one
                    analysis = BRL.getFirstReference( ref, "section cross-reference '{}' from '{}'".format( ref, givenRef ) )
                    #print( "a", analysis )
                    link = convertToPageReference(analysis) if analysis else None
                    result += '<a class="sectionCrossReferenceLink" href="{}">{}</a>'.format( link, originalRef ) if link else originalRef
            #print( "  Returning '{}'".format( result + bracket ) )
            return result + bracket
        # end of toHTML5.createSectionCrossReference


        def writeHomePage():
            if Globals.verbosityLevel > 1: print( _("    Creating HTML5 home/index page...") )
            xw = MLWriter( 'index.html', WEBoutputFolder, 'HTML' )
            xw.setHumanReadable()
            xw.start( noAutoXML=True )
            xw.writeLineText( '<!DOCTYPE html>', noTextCheck=True )
            xw.writeLineOpen( 'html' )
            writeHeader( xw, 'home' )
            writeFooter( xw )
            xw.writeLineClose( 'html' )
            xw.close()
        # end of toHTML5.writeHomePage


        def writeAboutPage():
            if Globals.verbosityLevel > 1: print( _("    Creating HTML5 about page...") )
            xw = MLWriter( 'about.html', WEBoutputFolder, 'HTML' )
            xw.setHumanReadable()
            xw.start( noAutoXML=True )
            xw.writeLineText( '<!DOCTYPE html>', noTextCheck=True )
            xw.writeLineOpen( 'html' )
            writeHeader( xw, 'about' )
            xw.writeLineOpenClose( 'p', 'These pages were created by the BibleWriter module of the Open Scriptures Bible Organisational System.' )
            writeFooter( xw )
            xw.writeLineClose( 'html' )
            xw.close()
        # end of toHTML5.writeAboutPage


        def writeHTML5Book( writerObject, BBB, bkData, ourGlobals ):
            """Writes a book to the HTML5 writerObject."""

            def liveLocal( text ):
                """
                Return the line with live links to the local page.

                Replaces only the first reference.
                """
                text = text.replace( '\\ior ', '<span class="outlineReferenceRange">' ).replace( '\\ior*', '</span>' )
                match = re.search( '([1-9][0-9]{0,2}):([1-9][0-9]{0,2})', text )
                if match:
                    #print( '0', repr(match.group(0)) )
                    #print( '1', repr(match.group(1)) )
                    #print( '2', repr(match.group(2)) )
                    text = text.replace( match.group(0), '<a class="CVReference" href="#C{}V{}">{}</a>'.format( match.group(1), match.group(2), match.group(0) ) )
                    #print( repr(text) )
                return text
            # end of liveLocal


            writeHeader( writerObject, BBB )
            haveOpenSection = haveOpenParagraph = haveOpenListItem = haveOpenVerse = False
            haveOpenList = {}
            html5Globals['nextFootnoteIndex'] = html5Globals['nextXRefIndex'] = 0
            html5Globals['footnoteHTML5'], html5Globals['endnoteHTML5'], html5Globals['xrefHTML5'] = [], [], []
            C = V = '0'
            for verseDataEntry in bkData._processedLines: # Process internal Bible data lines
                marker, text, extras = verseDataEntry.getMarker(), verseDataEntry.getAdjustedText(), verseDataEntry.getExtras()
                #if BBB=='MRK': print( "writeHTML5Book", marker, text )
                #print( "toHTML5.writeHTML5Book", BBB, C, V, marker, text )

                # Markers usually only found in the introduction
                if marker in oftenIgnoredIntroMarkers: pass # Just ignore these lines
                elif marker in ('mt1','mt2','mt3','mt4',):
                    if Globals.debugFlag: assert( not haveOpenParagraph )
                    #if haveOpenParagraph: writerObject.writeLineClose( 'p' ); haveOpenParagraph = False
                    if text: writerObject.writeLineOpenClose( 'h1', text, ('class','mainTitle'+marker[2]) )
                elif marker in ('is1','is2','is3','is4',):
                    if Globals.debugFlag: assert( not haveOpenParagraph )
                    #if not haveOpenParagraph:
                        #logging.warning( "toHTML5: Have {} introduction section heading {} outside a paragraph in {}".format( marker, text, BBB ) )
                        #writerObject.writeLineOpen( 'p', ('class','unknownParagraph') ); haveOpenParagraph = True
                    if text: writerObject.writeLineOpenClose( 'h3', text, ('class','introductionSectionHeading'+marker[2]) )
                elif marker in ('ip','ipi',):
                    if haveOpenParagraph:
                        logging.error( "toHTML5: didn't expect {} field with paragraph still open at {} {}:{}".format( marker, BBB, C, V ) )
                        writerObject.writeLineClose( 'p' ); haveOpenParagraph = False
                    #if haveOpenParagraph: writerObject.writeLineClose( 'p' ); haveOpenParagraph = False
                    if not haveOpenSection:
                        writerObject.writeLineOpen( 'section', ('class','regularSection') ); haveOpenSection = True
                    if text or extras:
                        writerObject.writeLineOpenClose( 'p', BibleWriter.__formatHTMLVerseText( BBB, C, V, text, extras, ourGlobals ), ('class',BibleWriter.ipHTMLClassDict[marker]), noTextCheck=True )
                        #writerObject.writeLineText( BibleWriter.__formatHTMLVerseText( BBB, C, V, text, extras, ourGlobals ), noTextCheck=True )
                elif marker == 'iot':
                    if haveOpenParagraph:
                        logging.error( "toHTML5: didn't expect {} field with paragraph still open at {} {}:{}".format( marker, BBB, C, V ) )
                        writerObject.writeLineClose( 'p' ); haveOpenParagraph = False
                    #if haveOpenParagraph: writerObject.writeLineClose( 'p' ); haveOpenParagraph = False
                    if text: writerObject.writeLineOpenClose( 'h3', text, ('class','outlineTitle') )
                elif marker in ('io1','io2','io3','io4',):
                    if Globals.debugFlag: assert( not haveOpenParagraph )
                    #if haveOpenParagraph: writerObject.writeLineClose( 'p' ); haveOpenParagraph = False
                    if text: writerObject.writeLineOpenClose( 'p', liveLocal(text), ('class','outlineEntry'+marker[2]), noTextCheck=True )
                elif marker == 'periph':
                    if haveOpenParagraph: writerObject.writeLineClose( 'p' ); haveOpenParagraph = False
                    if Globals.debugFlag:
                        assert( BBB in ('FRT','INT','BAK','OTH',) )
                        assert( text and not extras )
                    writerObject.writeLineOpenClose( 'p', ' ', ('class','peripheralContent') )
                elif marker in ('mte1','mte2','mte3','mte4',):
                    if haveOpenParagraph: writerObject.writeLineClose( 'p' ); haveOpenParagraph = False
                    if text: writerObject.writeLineOpenClose( 'h1', text, ('class','endTitle'+marker[3]) )

                # Now markers in the main text
                elif marker == 'c':
                    if haveOpenVerse: writerObject.writeLineClose( 'span' ); haveOpenVerse = False
                    if extras: print( "toHTML5: have extras at c at",BBB,C)
                    # What should we put in here -- we don't need/want to display it, but it's a place to jump to
                    writerObject.writeLineOpenClose( 'span', ' ', [('class','chapterStart'),('id','CS'+text)] )
                elif marker == 'cp': pass # ignore this for now
                elif marker == 'c#':
                    if extras: print( "toHTML5: have extras at c# at",BBB,C)
                    C = text
                    if not haveOpenParagraph:
                        logging.warning( "toHTML5: Have chapter number {} outside a paragraph in {} {}:{}".format( text, BBB, C, V ) )
                        writerObject.writeLineOpen( 'p', ('class','unknownParagraph') ); haveOpenParagraph = True
                    # Put verse 1 id here on the chapter number (since we don't output a v1 number)
                    writerObject.writeLineOpenClose( 'span', text, [('class','chapterNumber'),('id','CT'+text)] )
                    writerObject.writeLineOpenClose( 'span', '&nbsp;', ('class','chapterNumberPostspace') )
                elif marker in ('ms1','ms2','ms3','ms4',):
                    if haveOpenVerse: writerObject.writeLineClose( 'span' ); haveOpenVerse = False
                    if haveOpenParagraph: writerObject.writeLineClose( 'p' ); haveOpenParagraph = False
                    if text: writerObject.writeLineOpenClose( 'h2', text, ('class','majorSectionHeading'+marker[2]) )
                elif marker in ('s1','s2','s3','s4',):
                    if haveOpenVerse: writerObject.writeLineClose( 'span' ); haveOpenVerse = False
                    if haveOpenParagraph: writerObject.writeLineClose( 'p' ); haveOpenParagraph = False
                    if marker == 's1':
                        if haveOpenSection: writerObject.writeLineClose( 'section' ); haveOpenSection = False
                        writerObject.writeLineOpen( 'section', ('class','regularSection') ); haveOpenSection = True
                    if text or extras: writerObject.writeLineOpenClose( 'h3', BibleWriter.__formatHTMLVerseText( BBB, C, V, text, extras, ourGlobals ), ('class','sectionHeading'+marker[1]) )
                elif marker in ('r', 'sr', 'mr',):
                    if Globals.debugFlag: assert( not haveOpenVerse )
                    if haveOpenParagraph: writerObject.writeLineClose( 'p' ); haveOpenParagraph = False
                    if not haveOpenSection:
                        logging.warning( "toHTML5: Have {} section reference {} outside a section in {} {}:{}".format( marker, text, BBB, C, V ) )
                        writerObject.writeLineOpen( 'section', ('class','regularSection') ); haveOpenSection = True

                    if marker == 'r': rClass = 'sectionCrossReference'
                    elif marker == 'sr': rClass = 'sectionReferenceRange'
                    elif marker == 'mr': rClass = 'majorSectionReferenceRange'
                    if text: writerObject.writeLineOpenClose( 'p', createSectionCrossReference(text), ('class',rClass), noTextCheck=True )
                elif marker == 'd': # descriptive title or Hebrew subtitle
                    if text or extras: writerObject.writeLineOpenClose( 'p', BibleWriter.__formatHTMLVerseText( BBB, C, V, text, extras, ourGlobals ), ('class','descriptiveTitle') )
                elif marker == 'sp': # speaker
                    if text: writerObject.writeLineOpenClose( 'p', text, ('class','speaker') )
                elif marker == 'v':
                    if haveOpenVerse: writerObject.writeLineClose( 'span' ); haveOpenVerse = False
                    V = text
                    if not haveOpenParagraph:
                        logging.warning( "toHTML5: Have verse number {} outside a paragraph in {} {}:{}".format( text, BBB, C, V ) )
                    writerObject.writeLineOpen( 'span', [('class','verse'),('id','C'+C+'V'+V)] ); haveOpenVerse = True
                    if V == '1': # Different treatment for verse 1
                        writerObject.writeLineOpenClose( 'span', ' ', ('class','verseOnePrespace') )
                        writerObject.writeLineOpenClose( 'span', V, ('class','verseOneNumber') )
                        writerObject.writeLineOpenClose( 'span', '&nbsp;', ('class','verseOnePostspace') )
                    else: # not verse one
                        writerObject.writeLineOpenClose( 'span', ' ', ('class','verseNumberPrespace') )
                        writerObject.writeLineOpenClose( 'span', V, ('class','verseNumber') )
                        writerObject.writeLineOpenClose( 'span', '&nbsp;', ('class','verseNumberPostspace') )
                elif marker in ('p','m','pmo','pm','pmc','pmr','pi1','pi2','pi3','pi4','mi','cls','pc','pr','ph1','ph2','ph3','ph4',) \
                or marker in ('q1','q2','q3','q4','qr','qc','qm1','qm2','qm3','qm4',):
                    if haveOpenListItem: writerObject.writeLineClose( 'span' ); haveOpenListItem = False
                    if haveOpenList:
                        for lx in ('4','3','2','1',): # Close any open lists
                            if lx in haveOpenList and haveOpenList[lx]: writerObject.writeLineClose( 'p' ); del haveOpenList[lx]
                    if haveOpenVerse: writerObject.writeLineClose( 'span' ); haveOpenVerse = False
                    if haveOpenParagraph: writerObject.writeLineClose( 'p' ); haveOpenParagraph = False
                    writerObject.writeLineOpen( 'p', ('class',BibleWriter.pqHTMLClassDict[marker]) ); haveOpenParagraph = True
                    if text and Globals.debugFlag and debuggingThisModule: halt
                elif marker in ('li1','li2','li3','li4','ili1','ili2','ili3','ili4',):
                    if marker.startswith('li'): m, pClass, iClass = marker[2], 'list'+marker[2], 'listItem'+marker[2]
                    else: m, pClass, iClass = marker[3], 'introductionList'+marker[3], 'introductionListItem'+marker[3]
                    if not haveOpenList or m not in haveOpenList or not haveOpenList[m]:
                        writerObject.writeLineOpen( 'p', ('class',pClass) ); haveOpenList[m] = True
                    if marker.startswith('li'):
                        if Globals.debugFlag: assert( not text )
                        writerObject.writeLineOpen( 'span', ('class',iClass) ); haveOpenListItem = True
                    elif text: writerObject.writeLineOpenClose( 'span', BibleWriter.__formatHTMLVerseText( BBB, C, V, text, extras, ourGlobals ), ('class',iClass) )
                elif marker == 'b':
                    if haveOpenVerse: writerObject.writeLineClose( 'span' ); haveOpenVerse = False
                    if haveOpenParagraph: writerObject.writeLineClose( 'p' ); haveOpenParagraph = False
                    if Globals.debugFlag: assert( not text )
                    writerObject.writeLineOpenClose( 'p', ' ', ('class','blankParagraph') )

                # Character markers
                elif marker in ('v~','p~',):
                    if Globals.debugFlag and marker=='v~': assert( haveOpenVerse )
                    if not haveOpenParagraph:
                        logging.warning( "toHTML5: Have verse text {} outside a paragraph in {} {}:{}".format( text, BBB, C, V ) )
                        writerObject.writeLineOpen( 'p', ('class','unknownParagraph') ); haveOpenParagraph = True
                    if not haveOpenVerse:
                        writerObject.writeLineOpen( 'span', ('class','verse') ); haveOpenVerse = True
                    if text or extras:
                        writerObject.writeLineOpenClose( 'span', BibleWriter.__formatHTMLVerseText( BBB, C, V, text, extras, ourGlobals ), ('class','verseText'), noTextCheck=True )

                elif marker in ('nb','cl=','cl',): # These are the markers that we can safely ignore for this export
                    if Globals.debugFlag and marker=='nb': assert( not text and not extras )
                else:
                    if text:
                        logging.critical( "toHTML5: lost text in {} field in {} {}:{} {}".format( marker, BBB, C, V, repr(text) ) )
                        if Globals.debugFlag: halt
                    if extras:
                        logging.critical( "toHTML5: lost extras in {} field in {} {}:{}".format( marker, BBB, C, V ) )
                        #if Globals.debugFlag: halt
                    unhandledMarkers.add( marker )
                if extras and marker not in ('v~','p~','s1','s2','s3','s4','d',):
                    logging.critical( "toHTML5: extras not handled for {} at {} {}:{}".format( marker, BBB, C, V ) )
                    #if Globals.debugFlag: halt

            if haveOpenListItem: writerObject.writeLineClose( 'span' ); haveOpenListItem = False
            if haveOpenList:
                for lx in ('4','3','2','1',): # Close any open lists
                    if lx in haveOpenList and haveOpenList[lx]: writerObject.writeLineClose( 'p' ); del haveOpenList[lx]
            if haveOpenVerse: writerObject.writeLineClose( 'span' )
            if haveOpenParagraph: writerObject.writeLineClose( 'p' )
            if haveOpenSection: writerObject.writeLineClose( 'section' )
            writeEndNotes( writerObject, ourGlobals )
            writeFooter( writerObject )
        # end of toHTML5.writeHTML5Book


        # Set-up our Bible reference system
        if controlDict['PublicationCode'] == "GENERIC":
            BOS = self.genericBOS
            BRL = self.genericBRL
        else:
            BOS = BibleOrganizationalSystem( controlDict["PublicationCode"] )
            BRL = BibleReferenceList( BOS, BibleObject=None )

        if Globals.verbosityLevel > 2: print( _("  Exporting to HTML5 format...") )
        suffix = controlDict['HTML5Suffix'] if 'HTML5Suffix' in controlDict else 'html'
        filenameDict = {}
        for BBB in self.books: # Make a list of filenames
            filename = controlDict['HTML5OutputFilenameTemplate'].replace('__BOOKCODE__',BBB ).replace('__SUFFIX__',suffix)
            filenameDict[BBB] = Globals.makeSafeFilename( filename.replace( ' ', '_' ) )

        html5Globals = {}
        if controlDict["HTML5Files"]=="byBook":
            for BBB,bookData in self.books.items(): # Now export the books
                if Globals.verbosityLevel > 2: print( _("    Exporting {} to HTML5 format...").format( BBB ) )
                xw = MLWriter( filenameDict[BBB], WEBoutputFolder, 'HTML' )
                xw.setHumanReadable()
                xw.start( noAutoXML=True )
                xw.writeLineText( '<!DOCTYPE html>', noTextCheck=True )
                xw.writeLineOpen( 'html' )
                if Globals.debugFlag: writeHTML5Book( xw, BBB, bookData, html5Globals ) # Halts on errors
                else:
                    try: writeHTML5Book( xw, BBB, bookData, html5Globals )
                    except Exception as err:
                        print( BBB, "Unexpected error:", sys.exc_info()[0], err)
                        logging.error( "toHTML5: Oops, creating {} failed!".format( BBB ) )
                xw.writeLineClose( 'html' )
                xw.close()
            writeHomePage()
            writeAboutPage()
        elif Globals.debugFlag and debuggingThisModule: halt # not done yet
        if unhandledMarkers:
            logging.warning( "toHTML5: Unhandled markers were {}".format( unhandledMarkers ) )
            if Globals.verbosityLevel > 1:
                print( "  " + _("WARNING: Unhandled toHTML5 markers were {}").format( unhandledMarkers ) )

        # Now create a zipped collection
        if Globals.verbosityLevel > 2: print( "  Zipping HTML5 files..." )
        zf = zipfile.ZipFile( os.path.join( outputFolder, 'AllWebFiles.zip' ), 'w', compression=zipfile.ZIP_DEFLATED )
        for filename in os.listdir( WEBoutputFolder ):
            if not filename.endswith( '.zip' ):
                filepath = os.path.join( WEBoutputFolder, filename )
                zf.write( filepath, filename ) # Save in the archive without the path
        zf.close()

        if validationSchema: return xw.validate( validationSchema )
        return True
    # end of BibleWriter.toHTML5



    def toCustomBible( self, outputFolder=None, removeVerseBridges=False ):
        """
        Adjust the pseudo USFM and write the customized USFM files for the (forthcoming) CustomBible (Android) app.
        """
        if Globals.verbosityLevel > 1: print( "Running BibleWriter:toCustomBible..." )
        if Globals.debugFlag: assert( self.books )

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolder: outputFolder = "OutputFiles/BOS_CustomBible_" + ("Reexport/" if self.objectTypeString=="CustomBible" else "Export/")
        if not os.access( outputFolder, os.F_OK ): os.makedirs( outputFolder ) # Make the empty folder if there wasn't already one there
        #if not controlDict: controlDict = {}; ControlFiles.readControlFile( 'ControlFiles', "To_MediaWiki_controls.txt", controlDict )
        #assert( controlDict and isinstance( controlDict, dict ) )

        CBDataFormatVersion = 1 # Increment this when the data files / arrays change
        jsonIndent = 1 # Keep files small for small phones

        bookOutputFolderJSON = os.path.join( outputFolder, "ByBook.{}.JSON".format( CBDataFormatVersion ) )
        if not os.access( bookOutputFolderJSON, os.F_OK ): os.makedirs( bookOutputFolderJSON ) # Make the empty folder if there wasn't already one there
        chapterOutputFolderJSON = os.path.join( outputFolder, "ByChapter.{}.JSON".format( CBDataFormatVersion ) )
        if not os.access( chapterOutputFolderJSON, os.F_OK ): os.makedirs( chapterOutputFolderJSON ) # Make the empty folder if there wasn't already one there
        bookOutputFolderHTML = os.path.join( outputFolder, "BySection.{}.HTML".format( CBDataFormatVersion ) )
        if not os.access( bookOutputFolderHTML, os.F_OK ): os.makedirs( bookOutputFolderHTML ) # Make the empty folder if there wasn't already one there
        #chapterOutputFolderHTML = os.path.join( outputFolder, "ByChapter.{}.HTML".format( CBDataFormatVersion ) )
        #if not os.access( chapterOutputFolderHTML, os.F_OK ): os.makedirs( chapterOutputFolderHTML ) # Make the empty folder if there wasn't already one there

        headerFilepath = os.path.join( outputFolder, 'CBHeader.json' )
        divisionNamesFilepath = os.path.join( outputFolder, 'CBDivisionNames.{}.json'.format( CBDataFormatVersion ) )
        bookNamesFilepath = os.path.join( outputFolder, 'CBBookNames.{}.json'.format( CBDataFormatVersion ) )
        compressionDictFilepath = os.path.join( outputFolder, "CBCmprnDict.{}.json".format( CBDataFormatVersion ) )
        destinationIndexFilepath = os.path.join( outputFolder, "CB-BCV-index.{}.json".format( CBDataFormatVersion ) )
        destinationHTMLFilepathTemplate = os.path.join( bookOutputFolderHTML, "CBBook.{}.{}.html".format( '{}', CBDataFormatVersion ) ) # Missing the BBB

        unhandledMarkers = set()

        CBCompressions = (
            ('@A','<h1 class="mainTitle'), # numbered
            ('@B','<h2 class="introductionSectionHeading'), # numbered
            ('@C','<section class="introSection">'),
            ('@D','<p class="introductoryParagraph">'),
            ('@E','<h3 class="outlineTitle">'),
            ('@F','<p class="outlineEntry'), # numbered
            ('@G','<section class="regularSection">'),
            ('@u','<section class="chapterSection">'),
            ('@H','<section class="regularSection"><h3 class="sectionHeading1">'),
            ('@I','<p class="sectionCrossReference">'),
            ('@J','<span class="chapterStart" id="C'),
            #('@F','<p class="sectionHeading1">'),
            ('@K','<span class="chapterNumber" id="C'),
            ('@L','</span><span class="chapterNumberPostspace">&nbsp;</span><span class="verse" id="C'),
            #('@M','</span><span class="chapterNumberPostspace">&nbsp;</span>'),
            ('@M','</span></span><span class="verse" id="C'),
            ('@s','<span class="verse" id="C'),
            ('@N','"><span class="verseOnePrespace"> </span><span class="verseOneNumber">1</span><span class="verseOnePostspace">&nbsp;</span>'),
            ('@z','"><span class="verseNumberPrespace"> </span><span class="verseNumber">'),
            #('@Y','</span><span class="verseNumberPrespace"> </span><span class="verseNumber" id="C'), # Makes bigger! Why???
            ('@O','</span><span class="verseNumberPostspace">&nbsp;</span>'),
            ('@P','</span><span class="verseNumberPostspace">&nbsp;</span><span class="verseText">'),
            ('@U','</span><span class="verseNumberPostspace">&nbsp;</span><span class="verseText"><a class="xrefLinkSymbol" title="'),
            ('@Q','<span class="verseText">'),
            ('@R','<p class="proseParagraph"><span class="chapterNumber" id="C'),
            ('@S','<p class="proseParagraph">'),
            ('@T','<p class="proseParagraph"><span class="verse" id="C'),
            #('@T','<p class="proseParagraph"><span class="verseNumberPrespace"> </span><span class="verseNumber" id="C'),
            #('@U','</h3><p class="proseParagraph"><span class="verse" id="C'),
            #('@U','</h3><p class="proseParagraph"><span class="verseNumberPrespace"> </span><span class="verseNumber" id="C'),
            ('@V','<p class="poetryParagraph1">'),
            ('@W','<p class="poetryParagraph1"><span class="verse" id="C'),
            #('@W','<p class="poetryParagraph1"><span class="verseNumberPrespace"> </span><span class="verseNumber" id="C'),
            #('@X','<p class="poetryParagraph1"><span class="verseText">'),
            ('@Y','<p class="poetryParagraph2">'),
            ('@Z','<p class="poetryParagraph3">'),
            ('@a','<p class="poetryParagraph4">'),
            ('@r','<p class="flushLeftParagraph"><span class="verse" id="C'),
            ('@b','<p class="flushLeftParagraph">'),
            ('@c','<p class="list'), # numbered
            ('@d','<span class="listItem'), # numbered

            ('@e','<a class="footnoteLinkSymbol" title="'),
            ('@f','" href="#FNote'),
            ('@g','">[fn]</a>'),
            ('@h','<a class="xrefLinkSymbol" title="'),
            ('@i','" href="#XRef'),
            ('@j','">[xr]</a>'),

            ('@k','<span class="'), # For relatively rare character formatting which doesn't deserve its own compression entry
            ('@l','</section>'),
            ('@m','</h1>'),
            ('@n','</h3>'),
            ('@o','</p>'),
            ('@p','</span>'),
            ('@y','</span></span>'),
            ('@q','</span></p>'),
            ('@t','</span></span></p>'),
            ('^','">'),

            ('~~','@'), # Must be last
        )

        usageCount = {}
        codeSet, dataSet, reversedCompressions = [], [], []
        for shortString, longString in CBCompressions:
            usageCount[shortString] = 0
            if shortString in codeSet: # check for duplicates
                logging.critical( "Duplicate {} in compression dict".format( repr(shortString) ) )
                print( shortString, codeSet )
                halt
            codeSet.append( shortString )
            if longString in dataSet: # check for duplicates
                logging.critical( "Duplicate {} in compression dict".format( repr(longString) ) )
                print( longString, dataSet )
                halt
            dataSet.append( longString )
            if longString != '@':
                reversedCompressions.append( (longString,shortString,) )
        reversedCompressions = sorted( reversedCompressions, key=lambda s: -len(s[0]) ) # Longest string length first
        #print( len(reversedCompressions), reversedCompressions )


        def writeCompressions():
            """
            """
            if Globals.verbosityLevel > 1:
                print( "  Writing compression entries..." )
            #filepath = os.path.join( outputFolder, 'CBHeader.json' )
            if Globals.verbosityLevel > 2: print( "    toCustomBible " +  _("Exporting index to {}...").format( compressionDictFilepath ) )
            with open( compressionDictFilepath, 'wt' ) as jsonFile:
                #for compression in SDCompressions:
                    #compFile.write( compression[0] + compression[1] + '\n' )
                json.dump( CBCompressions, jsonFile, indent=jsonIndent )
            if Globals.verbosityLevel > 2:
                print( "    {} compression entries written.".format( len(CBCompressions) ) )
        # end of writeCompressions


        bytesRaw = bytesCompressed = 0
        def compress( entry ):
            """
            """
            nonlocal bytesRaw, bytesCompressed
            #print( '\n', entry )
            #if C=='4': halt
            bytesRaw += len( entry.encode('UTF8') )
            result = entry
            if '@' in result:
                #print( 'have@', entry )
                result = result.replace( '@', '~~' )
                usageCount['~~'] += 1
            if '^' in result:
                print( 'have^', entry )
                halt # CustomBible compression will fail!
            for longString, shortString in reversedCompressions:
                if longString in result:
                    result = result.replace( longString, shortString )
                    usageCount[shortString] += 1
            bytesCompressed += len( result.encode('UTF8') )
            return result
        # end of compress


        def decompress( entry ):
            """
            """
            result = entry
            for shortString, longString in CBCompressions:
                result = result.replace( shortString, longString )
            return result
        # end of decompress


        def writeCBHeader():
            """
            """
            headerDict = OrderedDict()
            headerDict['Data format version'] = CBDataFormatVersion
            headerDict['Conversion date'] = datetime.today().strftime("%Y-%m-%d")
            headerDict['Conversion program'] = ProgNameVersion
            headerDict['Version name'] = self.settingsDict['WorkTitle'] if 'WorkTitle' in self.settingsDict else self.name
            headerDict['Version abbreviation'] = self.settingsDict['WorkAbbreviation'] if 'WorkAbbreviation' in self.settingsDict else self.abbreviation
            #print( headerDict )

            if Globals.verbosityLevel > 2: print( "  " +  _("Exporting CB header to {}...").format( headerFilepath ) )
            with open( headerFilepath, 'wt' ) as jsonFile:
                json.dump( headerDict, jsonFile, indent=jsonIndent )
        # end of writeCBHeader


        def writeCBBookNames():
            """
            Writes the two files:
                list of division names
                list of book names and abbreviations
            """
            def getDivisionName( BBB, doneAny=None, doneBooks=None ):
                """ Given a book code, return the division name. """
                result = ""
                if Globals.BibleBooksCodes.isOldTestament_NR( BBB ) or BBB == 'PS2':
                    result = self.settingsDict['OldTestamentName'] if "OldTestamentName" in self.settingsDict else "Old Testament"
                elif Globals.BibleBooksCodes.isNewTestament_NR( BBB ):
                    result = self.settingsDict['NewTestamentName'] if "NewTestamentName" in self.settingsDict else "New Testament"
                elif Globals.BibleBooksCodes.isDeuterocanon_NR( BBB ) or BBB in ('MA3','MA4'):
                    result = self.settingsDict['DeuterocanonName'] if "DeuterocanonName" in self.settingsDict else "Deuterocanon"
                elif doneAny == False:
                    result = self.settingsDict['FrontMatterName'] if "FrontMatterName" in self.settingsDict else "Front Matter"
                elif doneBooks == True:
                    result = self.settingsDict['BackMatterName'] if "BackMatterName" in self.settingsDict else "Back Matter"
                return result
            # end of getDivisionName

            # Make a list of division names and write them to a very small JSON file
            divisionData = []
            doneAny = doneBooks = False
            for BBB,bookObject in self.books.items():
                divisionName = getDivisionName( BBB, doneAny, doneBooks )
                if divisionName and divisionName not in divisionData:
                    divisionData.append( divisionName )
                if Globals.BibleBooksCodes.isOldTestament_NR(BBB) or Globals.BibleBooksCodes.isNewTestament_NR(BBB) or Globals.BibleBooksCodes.isDeuterocanon_NR(BBB):
                    doneAny = doneBooks = True
            #print( divisionData )
            if Globals.verbosityLevel > 2: print( "  " + _("Exporting division names to {}...").format( divisionNamesFilepath ) )
            with open( divisionNamesFilepath, 'wt' ) as jsonFile:
                json.dump( divisionData, jsonFile, indent=jsonIndent )

            # Make a list of book data including names and abbreviations and write them to a JSON file
            bkData = []
            doneAny = doneBooks = False
            for BBB,bookObject in self.books.items():
                abbreviation = self.getBooknameAbbreviation( BBB )
                shortName = self.getShortTOCName( BBB )
                longName = self.getAssumedBookName( BBB )
                try: divisionNumber = divisionData.index( getDivisionName( BBB, doneAny, doneBooks ) )
                except: divisionNumber = -1
                numChapters = ""
                for dataLine in bookObject._processedLines:
                    if dataLine.getMarker() == 'c':
                        numChapters = dataLine.getCleanText()
                try: intNumChapters = int( numChapters )
                except:
                    logging.error( "toCustomBible: no chapters in {}".format( BBB ) )
                    intNumChapters = 0
                bkData.append( (BBB,abbreviation,shortName,longName,intNumChapters,numSectionsDict[BBB],divisionNumber) )
                if Globals.BibleBooksCodes.isOldTestament_NR(BBB) or Globals.BibleBooksCodes.isNewTestament_NR(BBB) or Globals.BibleBooksCodes.isDeuterocanon_NR(BBB):
                    doneAny = doneBooks = True
            #print( bkData )
            if Globals.verbosityLevel > 2: print( "  " + _("Exporting book names to {}...").format( bookNamesFilepath ) )
            with open( bookNamesFilepath, 'wt' ) as jsonFile:
                json.dump( bkData, jsonFile, indent=jsonIndent )
        # end of writeCBBookNames


        def writeCBBookAsJSON( BBB, bookData ):
            """
            """
            def writeCBChapter( BBB, chapter, cData ):
                """
                """
                filepath = os.path.join( chapterOutputFolderJSON, '{}_{}.{}.json'.format( BBB, chapter, CBDataFormatVersion ) )
                if Globals.verbosityLevel > 2: print( "  " + _("Exporting {}_{} chapter to {}...").format( BBB, chapter, filepath ) )
                with open( filepath, 'wt' ) as jsonFile:
                    json.dump( cData, jsonFile, indent=jsonIndent )
            # end of writeCBChapter

            outputData, chapterOutputData = [], []
            lastC = '0'
            for dataLine in bookData:
                marker, text, extras = dataLine.getMarker(), dataLine.getAdjustedText(), dataLine.getExtras()
                if marker == 'c':
                    C = text
                    writeCBChapter( BBB, lastC, chapterOutputData )
                    chapterOutputData = [] # Start afresh
                    lastC = C
                extrasList = []
                for extra in extras:
                    extrasList.append( (extra.getType(),extra.getIndex(),extra.getText()) )
                    #print( extra )
                if extrasList:
                    chapterOutputData.append( (marker,text,extrasList) )
                    outputData.append( (marker,text,extrasList) )
                else: # Try to keep filesizes down for mobile devices by omitting this often empty field
                    chapterOutputData.append( (marker,text) )
                    outputData.append( (marker,text) )
                #print( outputData )
            writeCBChapter( BBB, lastC, chapterOutputData ) # Write the last chapter

            filepath = os.path.join( bookOutputFolderJSON, '{}.{}.json'.format( BBB, CBDataFormatVersion ) )
            if Globals.verbosityLevel > 2: print( "  " + _("Exporting {} book to {}...").format( BBB, filepath ) )
            with open( filepath, 'wt' ) as jsonFile:
                json.dump( outputData, jsonFile, indent=jsonIndent )
        # end of writeCBBookAsJSON


        def writeCBBookAsHTML( BBB, bookData, currentIndex ):
            """
            If the book has section headings, breaks it by section
                otherwise breaks the book by chapter.

            Returns the number of sections written.
            """
            numCBSections = 0
            CBGlobals = {}
            CBGlobals['nextFootnoteIndex'] = CBGlobals['nextXRefIndex'] = 0
            CBGlobals['footnoteHTML5'], CBGlobals['endnoteHTML5'], CBGlobals['xrefHTML5'] = [], [], []

            def handleSection( sectionCV, sectionHTML, outputFile ):
                """
                First parameter is a C,V tuple (C = '0' for introduction)
                Section parameter is the HTML5 segment for the section
                """
                nonlocal numCBSections
                #print( "  toCustomBible.handleSection( {} ) {} haveSectionHeadings={}".format( sectionCV, BBB, haveSectionHeadings ) )
                assert( sectionHTML )
                numCBSections += 1
                #if BBB == 'GLS': print( BBB, sectionHTML ); halt
                if '\\' in sectionHTML: # shouldn't happen
                    ix = sectionHTML.index( '\\' )
                    segment = sectionHTML[ix-10 if ix>10 else 0 : ix+30]
                    logging.error( "toCustomBible programming error: unprocessed backslash code in {} {}:{} section: ...{}...".format( BBB, C, V, repr(segment) ) )
                    if Globals.debugFlag or Globals.verbosityLevel > 2:
                        print( "toCustomBible: unprocessed backslash code in {} {}:{} section: ...{}...".format( BBB, C, V, repr(segment) ) )
                    if Globals.debugFlag and debuggingThisModule: halt
                compressedHTML = compress( sectionHTML )
                if Globals.debugFlag:
                    checkHTML = decompress( compressedHTML )
                    if checkHTML != sectionHTML:
                        print( "\noriginal: {} {}".format( len(sectionHTML), repr(sectionHTML) ) )
                        print( "\ndecompressed: {} {}".format( len(checkHTML), repr(checkHTML) ) )
                        for ix in range( 0, min( len(sectionHTML), len(checkHTML) ) ):
                            if checkHTML[ix] != sectionHTML[ix]:
                                if ix > 10: print( '\n', repr(sectionHTML[ix-10:ix+2]), '\n', repr(checkHTML[ix-10:ix+2]) )
                                print( ix, repr(sectionHTML[ix]), repr(checkHTML[ix]) ); break
                        halt
                #if Globals.debugFlag: compressedHTML = sectionHTML # Leave it uncompressed so we can easily look at it
                if Globals.debugFlag: compressedHTML += '\n'
                bytesWritten = outputFile.write( compressedHTML.encode('UTF8') )
                return bytesWritten
            # end of writeCBBookAsHTML.handleSection

            try: haveSectionHeadings = self.discoveryResults[BBB]['haveSectionHeadings']
            except: haveSectionHeadings = False
            #print( haveSectionHeadings, BBB ) #, self.discoveryResults[BBB] )

            htmlFile = open( destinationHTMLFilepathTemplate.format( BBB ), 'wb' )
            fileOffset = 0

            lastHTML = sectionHTML = outputHTML = ""
            lastMarker = None
            C = lastC = V = '0'
            lastV = '999' # For introduction section
            BCV = (BBB,C,V)
            sOpen = sJustOpened = pOpen = vOpen = False
            listOpen = {}
            for dataLine in bookData:
                thisHTML = ''
                marker, text, extras = dataLine.getMarker(), dataLine.getAdjustedText(), dataLine.getExtras()
                #print( " toCB: {} {}:{} {}:{}".format( BBB, C, V, marker, repr(text) ) )

                # Markers usually only found in the introduction
                if marker in oftenIgnoredIntroMarkers: pass # Just ignore these lines
                elif marker in ('mt1','mt2','mt3','mt4',):
                    if Globals.debugFlag: assert( not pOpen )
                    if not sOpen:
                        thisHTML += '<section class="introSection">'; sOpen = sJustOpened = True; BCV=(BBB,C,V)
                    thisHTML += '<h1 class="mainTitle{}">{}</h1>'.format( marker[2], text )
                elif marker in ('is1','is2','is3','is4',):
                    if pOpen:
                        logging.warning( "toCustomBible: didn't expect {} field with paragraph still open at {} {}:{}".format( marker, BBB, C, V ) )
                        thisHTML += '</p>'; pOpen = False
                        if Globals.debugFlag: thisHTML += '\n'
                    if BBB == 'FRT' and marker == 'is1':
                        if sOpen: lastHTML += '</section>'; sOpen = False
                        if lastHTML or sectionHTML:
                            sectionHTML += lastHTML
                            lastHTML = ''
                            bytesWritten = handleSection( BCV, sectionHTML, htmlFile )
                            sectionHTML = ''
                            indexEntry = BCV[0],BCV[1],BCV[2],lastC,lastV,fileOffset,bytesWritten
                            currentIndex.append( indexEntry )
                            fileOffset += bytesWritten
                    if not sOpen:
                        thisHTML += '<section class="introSection">'; sOpen = sJustOpened = True; BCV=(BBB,C,V)
                    thisHTML += '<h2 class="introductionSectionHeading{}">{}</h2>'.format( marker[2], text )
                elif marker in ('ip','ipi',):
                    for lx in ('4','3','2','1'): # Close any open lists
                        if listOpen and lx in listOpen and listOpen[lx]: thisHTML += '</p>'; del listOpen[lx]
                    if pOpen:
                        logging.warning( "toCustomBible: didn't expect {} field with paragraph still open at {} {}:{}".format( marker, BBB, C, V ) )
                        thisHTML += '</p>'; pOpen = False
                        if Globals.debugFlag: thisHTML += '\n'
                    if not sOpen:
                        thisHTML += '<section class="introSection">'; sOpen = sJustOpened = True; BCV=(BBB,C,V)
                    #if not text and not extras: print( "{} at {} {}:{} has nothing!".format( marker, BBB, C, V ) );halt
                    if text or extras:
                        thisHTML += '<p class="{}">{}</p>'.format( BibleWriter.ipHTMLClassDict[marker], BibleWriter.__formatHTMLVerseText( BBB, C, V, text, extras, CBGlobals ) )
                elif marker == 'iot':
                    if pOpen:
                        logging.warning( "toCustomBible: didn't expect {} field with paragraph still open at {} {}:{}".format( marker, BBB, C, V ) )
                        thisHTML += '</p>'; pOpen = False
                        if Globals.debugFlag: thisHTML += '\n'
                    if not sOpen:
                        thisHTML += '<section class="introSection">'; sOpen = sJustOpened = True; BCV=(BBB,C,V)
                    thisHTML += '<h3 class="outlineTitle">{}</h3>'.format( text )
                elif marker in ('io1','io2','io3','io4',):
                    if pOpen:
                        logging.warning( "toCustomBible: didn't expect {} field with paragraph still open at {} {}:{}".format( marker, BBB, C, V ) )
                        thisHTML += '</p>'; pOpen = False
                        if Globals.debugFlag: thisHTML += '\n'
                    if not sOpen:
                        thisHTML += '<section class="introSection">'; sOpen = sJustOpened = True; BCV=(BBB,C,V)
                    if text or extras:
                        thisHTML += '<p class="outlineEntry{}">{}</p>'.format( marker[2], BibleWriter.__formatHTMLVerseText( BBB, C, V, text, extras, CBGlobals ) )
                elif marker == 'periph':
                    if pOpen:
                        if Globals.debugFlag: assert( sOpen )
                        thisHTML += '</p>'; pOpen = False
                        if Globals.debugFlag: thisHTML += '\n'
                    if Globals.debugFlag:
                        assert( BBB in ('FRT','INT','BAK','OTH',) )
                        assert( text and not extras )
                    thisHTML += '<p class="peripheralContent">{}</p>'.format( text )
                elif marker in ('mte1','mte2','mte3','mte4',):
                    if pOpen:
                        if Globals.debugFlag: assert( sOpen )
                        thisHTML += '</p>'; pOpen = False
                        if Globals.debugFlag: thisHTML += '\n'
                    if Globals.debugFlag: assert( sOpen )
                    thisHTML += '<h1 class="endTitle{}">{}</h1>'.format( marker[3], text )

                # Now markers in the main text
                elif marker == 'c':
                    if vOpen: lastHTML += '</span>'; vOpen = False
                    #if extras: print( "have extras at c at",BBB,C); halt
                    C, V = text, '0'
                    if not haveSectionHeadings: # Treat each chapter as a new section
                        if pOpen: lastHTML += '</p>'; pOpen = False
                        if sOpen: lastHTML += '</section>'; sOpen = False
                        if lastHTML or sectionHTML:
                            sectionHTML += lastHTML
                            lastHTML = ''
                            bytesWritten = handleSection( BCV, sectionHTML, htmlFile )
                            sectionHTML = ''
                            indexEntry = BCV[0],BCV[1],BCV[2],lastC,lastV,fileOffset,bytesWritten
                            currentIndex.append( indexEntry )
                            fileOffset += bytesWritten
                        thisHTML += '<section class="chapterSection">'; sOpen = sJustOpened = True; BCV=(BBB,C,V)
                    elif C=='1': # Must be the end of the introduction -- so close that section
                        if pOpen: lastHTML += '</p>'; pOpen = False
                        if sOpen: lastHTML += '</section>'; sOpen = False
                    # What should we put in here -- we don't need/want to display it, but it's a place to jump to
                    # NOTE: If we include the next line, it usually goes at the end of a section where it's no use
                    thisHTML += '<span class="chapterStart" id="{}"></span>'.format( 'CT'+C )
                elif marker == 'cp': # ignore this for now
                    logging.error( "toCustomBible: ignored cp field {} for {}".format( repr(text), C ) )
                elif marker in ('ms1','ms2','ms3','ms4',):
                    if vOpen: lastHTML += '</span>'; vOpen = False
                    if pOpen: lastHTML += '</p>'; pOpen = False
                    if sOpen: lastHTML += '</section>'; sOpen = False
                    if lastHTML or sectionHTML:
                        sectionHTML += lastHTML
                        lastHTML = ''
                        bytesWritten = handleSection( BCV, sectionHTML, htmlFile )
                        sectionHTML = ''
                        indexEntry = BCV[0],BCV[1],BCV[2],lastC,lastV,fileOffset,bytesWritten
                        currentIndex.append( indexEntry )
                        fileOffset += bytesWritten
                    thisHTML += '<h2 class="majorSectionHeading{}">{}</h2>'.format( marker[2], text )
                elif marker in ('s1','s2','s3','s4'):
                    if Globals.debugFlag: assert( haveSectionHeadings )
                    if vOpen: lastHTML += '</span>'; vOpen = False
                    if marker == 's1':
                        if pOpen: lastHTML += '</p>'; pOpen = False
                        if sOpen: lastHTML += '</section>'; sOpen = False
                        if lastHTML or sectionHTML:
                            sectionHTML += lastHTML
                            lastHTML = ''
                            bytesWritten = handleSection( BCV, sectionHTML, htmlFile )
                            sectionHTML = ''
                            indexEntry = BCV[0],BCV[1],BCV[2],lastC,lastV,fileOffset,bytesWritten
                            currentIndex.append( indexEntry )
                            fileOffset += bytesWritten
                        thisHTML += '<section class="regularSection">'; sOpen = sJustOpened = True; BCV=(BBB,C,V)
                    if text or extras:
                        thisHTML += '<h3 class="sectionHeading{}">{}</h3>'.format( marker[1], BibleWriter.__formatHTMLVerseText( BBB, C, V, text, extras, CBGlobals ) )
                        if Globals.debugFlag: thisHTML += '\n'
                elif marker in ('r', 'sr', 'mr',):
                    if Globals.debugFlag: assert( not vOpen )
                    if pOpen: lastHTML += '</p>'; pOpen = False
                    if not sOpen:
                        logging.warning( "toCustomBible: Have {} section reference {} outside a section in {} {}:{}".format( marker, text, BBB, C, V ) )
                        thisHTML += '<section class="regularSection">'; sOpen = sJustOpened = True; BCV=(BBB,C,V)
                    if marker == 'r': rClass = 'sectionCrossReference'
                    elif marker == 'sr': rClass = 'sectionReferenceRange'
                    elif marker == 'mr': rClass = 'majorSectionReferenceRange'
                    thisHTML += '<p class="{}">{}</p>'.format( rClass, text )
                elif marker == 'd': # descriptive title or Hebrew subtitle
                    if text or extras:
                        thisHTML = '<p class="descriptiveTitle">{}</p>'.format( BibleWriter.__formatHTMLVerseText( BBB, C, V, text, extras, CBGlobals ) )
                elif marker == 'sp': # speaker
                    thisHTML = '<p class="speaker">{}</p>'.format( text )

                elif marker == 'c#':
                    #if extras: print( "have extras at c# at",BBB,C); halt
                    thisHTML += '<span class="chapterNumber" id="{}">{}</span>'.format( 'CS'+C, text )
                    #thisHTML += '<span class="chapterNumber">{}</span>'.format( text )
                    thisHTML += '<span class="chapterNumberPostspace">&nbsp;</span>'
                elif marker in ('p','m','pmo','pm','pmc','pmr','pi1','pi2','pi3','pi4','mi','cls','pc','pr','ph1','ph2','ph3','ph4',) \
                or marker in ('q1','q2','q3','q4','qr','qc','qm1','qm2','qm3','qm4',):
                    for lx in ('4','3','2','1'): # Close any open lists
                        if listOpen and lx in listOpen and listOpen[lx]: thisHTML += '</p>'; del listOpen[lx]
                    if vOpen: lastHTML += '</span>'; vOpen = False
                    if pOpen:
                        if Globals.debugFlag: assert( sOpen )
                        thisHTML += '</p>'; pOpen = False
                        if Globals.debugFlag: thisHTML += '\n'
                    elif not sOpen:
                        if lastHTML or sectionHTML:
                            sectionHTML += lastHTML
                            lastHTML = ''
                            bytesWritten = handleSection( BCV, sectionHTML, htmlFile )
                            sectionHTML = ''
                            indexEntry = BCV[0],BCV[1],BCV[2],lastC,lastV,fileOffset,bytesWritten
                            currentIndex.append( indexEntry )
                            fileOffset += bytesWritten
                        thisHTML += '<section class="regularSection">'; sOpen = sJustOpened = True; BCV=(BBB,C,V)
                    if Globals.debugFlag: assert( not text )
                    thisHTML += '<p class="{}">'.format( BibleWriter.pqHTMLClassDict[marker] )
                    pOpen = True
                elif marker == 'v':
                    if vOpen: lastHTML += '</span>'; vOpen = False
                    V = text
                    if sJustOpened: BCV=(BBB,C,V)
                    thisHTML += '<span class="verse" id="{}">'.format( 'C'+C+'V'+V ); vOpen = True
                    if V == '1': # Different treatment for verse 1
                        thisHTML += '<span class="verseOnePrespace"> </span>'
                        thisHTML += '<span class="verseOneNumber">{}</span>'.format( text )
                        thisHTML += '<span class="verseOnePostspace">&nbsp;</span>'
                    else: # not verse one
                        thisHTML += '<span class="verseNumberPrespace"> </span>'
                        thisHTML += '<span class="verseNumber">{}</span>'.format( text )
                        thisHTML += '<span class="verseNumberPostspace">&nbsp;</span>'
                    sJustOpened = False
                    lastC, lastV = C, V
                elif marker in ('v~','p~',):
                    if Globals.debugFlag and marker=='v~': assert( vOpen )
                    if text or extras:
                        if not vOpen:
                            thisHTML += '<span class="verse" id="{}">'.format( 'C'+C+'V'+V+'b' ); vOpen = True
                        thisHTML += '<span class="verseText">{}</span>'.format( BibleWriter.__formatHTMLVerseText( BBB, C, V, text, extras, CBGlobals ) )
                    sJustOpened = False
                elif marker in ('li1','li2','li3','li4','ili1','ili2','ili3','ili4',):
                    if marker.startswith('li'): level, pClass, iClass = marker[2], 'list'+marker[2], 'listItem'+marker[2]
                    else: level, pClass, iClass = marker[3], 'introductionList'+marker[3], 'introductionListItem'+marker[3]
                    if listOpen and level not in listOpen:
                        for lx in ('4','3','2','1'): # Close the last open list
                            if lx!=level and lx in listOpen and listOpen[lx]:
                                thisHTML += '</p>'
                                del listOpen[lx]; break
                    if not listOpen or level not in listOpen or not listOpen[level]:
                        thisHTML += '<p class="{}">'.format( pClass ); listOpen[level] = True
                    if marker.startswith('li'):
                        if Globals.debugFlag: assert( not text )
                        thisHTML += '<span class="{}">'.format( iClass )
                    elif text: thisHTML += '<span class="{}">{}</span>'.format( iClass, BibleWriter.__formatHTMLVerseText( BBB, C, V, text, extras, CBGlobals ) )
                    sJustOpened = False
                elif marker == 'b':
                    if vOpen: lastHTML += '</span>'; vOpen = False
                    if pOpen:
                        if Globals.debugFlag: assert( sOpen )
                        thisHTML += '</p>'; pOpen = False
                        if Globals.debugFlag: thisHTML += '\n'
                    if Globals.debugFlag: assert( not text )
                    thisHTML += '<p class="blankParagraph"></p>'

                elif marker in ('nb','cl=','cl',): # These are the markers that we can safely ignore for this export
                    if Globals.debugFlag and marker=='nb': assert( not text and not extras )
                else:
                    if text:
                        logging.critical( "toCustomBible: lost text in {} field in {} {}:{} {}".format( marker, BBB, C, V, repr(text) ) )
                        if Globals.debugFlag: halt
                    if extras:
                        logging.critical( "toCustomBible: lost extras in {} field in {} {}:{}".format( marker, BBB, C, V ) )
                        if Globals.debugFlag: halt
                    unhandledMarkers.add( marker )
                if extras and marker not in ('v~','p~','s1','s2','s3','s4','d',):
                    logging.critical( "toCustomBible: extras not handled for {} at {} {}:{}".format( marker, BBB, C, V ) )
                    #if Globals.debugFlag: halt

                sectionHTML += lastHTML
                lastMarker, lastHTML = marker, thisHTML

            for lx in ('4','3','2','1'): # Close any open lists
                if listOpen and lx in listOpen and listOpen[lx]: lastHTML += '</p>'; del listOpen[lx]
            if vOpen: lastHTML += '</span>'
            if pOpen: lastHTML += '</p>'
            if sOpen: lastHTML += '</section>'
            sectionHTML += lastHTML
            if sectionHTML:
                bytesWritten = handleSection( BCV, sectionHTML, htmlFile )
                indexEntry = BCV[0],BCV[1],BCV[2],lastC,lastV,fileOffset,bytesWritten
                currentIndex.append( indexEntry )

            htmlFile.close()
            return numCBSections
            #if Globals.verbosityLevel > 2 or Globals.debugFlag:
                #for key,count in usageCount.items():
                    #if count == 0: logging.error( "Compression code {} is unused".format( key ) )
                    #elif count < 20: logging.warning( "Compression code {} is rarely used".format( key ) )
                    #elif count < 100: logging.warning( "Compression code {} is under-used".format( key ) )

                #if bytesRaw and Globals.verbosityLevel > 2:
                    #print( "  {} compression ratio: {}".format( BBB, round( bytesCompressed / bytesRaw, 3 ) ) )
                    #if Globals.verbosityLevel > 2:
                        #print( "    {} raw bytes: {}".format( BBB, bytesRaw ) )
                        #print( "    {} compressed bytes: {}".format( BBB, bytesCompressed ) )
            #if Globals.debugFlag: print( "Finished", BBB ); halt
        # end of writeCBBookAsHTML


        writeCBHeader()

        # Write the books
        createdHTMLIndex = []
        numSectionsDict = {}
        for BBB,bookObject in self.books.items():
            pseudoUSFMData = bookObject._processedLines
            writeCBBookAsJSON( BBB, pseudoUSFMData )
            numSections = writeCBBookAsHTML( BBB, pseudoUSFMData, createdHTMLIndex )
            numSectionsDict[BBB] = numSections

        writeCBBookNames()

        if createdHTMLIndex: # Sort the main index and write it
            if Globals.verbosityLevel > 1:
                print( "  Fixing and writing main index..." )

            def toInt( CVstring ):
                try: return int( CVstring )
                except:
                    if Globals.debugFlag: assert( CVstring )
                    newCV = '0'
                    for char in CVstring:
                        if char.isdigit(): newCV += char
                        else: break
                    return int( newCV )
            # end of toInt

            newHTMLIndex = []
            for B,C1,V1,C2,V2,fO,rL in createdHTMLIndex: # Convert strings to integers for the JSON index
                intC1, intC2 = toInt( C1 ), toInt( C2 )
                intV1, intV2 = toInt( V1 ), toInt( V2 )
                newHTMLIndex.append( (B,intC1,intV1,intC2,intV2,fO,rL) )
            #createdHTMLIndex = sorted(createdHTMLIndex)
            print( "    {} index entries created.".format( len(newHTMLIndex) ) )
            #filepath = os.path.join( outputFolder, 'CBHeader.json' )
            if Globals.verbosityLevel > 2: print( "    toCustomBible: " +  _("Exporting index to {}...").format( destinationIndexFilepath ) )
            with open( destinationIndexFilepath, 'wt' ) as jsonFile:
                json.dump( newHTMLIndex, jsonFile, indent=jsonIndent )
            writeCompressions()

        if unhandledMarkers:
            logging.warning( "toCustomBible: Unhandled markers were {}".format( unhandledMarkers ) )
            if Globals.verbosityLevel > 1:
                print( "  " + _("WARNING: Unhandled toCustomBible markers were {}").format( unhandledMarkers ) )

        # Display compression info
        if Globals.verbosityLevel > 2 or Globals.debugFlag:
            for key,count in usageCount.items():
                if count == 0: logging.error( "Compression code {} is unused".format( key ) )
                elif count < 20: logging.warning( "Compression code {} is rarely used".format( key ) )
                elif count < 100: logging.warning( "Compression code {} is under-used".format( key ) )
            if bytesRaw and Globals.verbosityLevel > 2:
                print( "  Compression ratio: {}".format( round( bytesCompressed / bytesRaw, 3 ) ) )
                if Globals.verbosityLevel > 2:
                    print( "    Raw bytes: {}".format( bytesRaw ) )
                    print( "    Compressed bytes: {}".format( bytesCompressed ) )

        ## Now create a zipped collection
        #if Globals.verbosityLevel > 2: print( "  Zipping CustomBible files..." )
        #zf = zipfile.ZipFile( os.path.join( outputFolder, 'AllCBUSFMFiles.zip' ), 'w', compression=zipfile.ZIP_DEFLATED )
        #for filename in os.listdir( outputFolder ):
            #if not filename.endswith( '.zip' ):
                #filepath = os.path.join( outputFolder, filename )
                #zf.write( filepath, filename ) # Save in the archive without the path
        #zf.close()

        return True
    # end of BibleWriter.toCustomBible



    def toPhotoBible( self, outputFolder=None ):
        """
        Write the pseudo USFM out into a simple plain-text format.
            The format varies, depending on whether or not there are paragraph markers in the text.
                I need to see a page showing 26-32 characters per line and 13-14 lines per page
        """
        if Globals.verbosityLevel > 1: print( "Running BibleWriter:toPhotoBible..." )
        if Globals.debugFlag: assert( self.books )

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolder: outputFolder = "OutputFiles/BOS_PhotoBible_Export/"
        if not os.access( outputFolder, os.F_OK ): os.makedirs( outputFolder ) # Make the empty folder if there wasn't already one there

        unhandledMarkers = set()

        # First determine our format
        pixelWidth, pixelHeight = 240, 320
        leftPadding = 1
        defaultFontSize, defaultLeadingRatio = 20, 1.2
        defaultLineSize = int( defaultLeadingRatio * defaultFontSize )
        maxLineCharacters, maxLines = 26, 12
        maxDown = pixelHeight-1 - defaultLineSize - 3 # Be sure to leave one blank line at the bottom
        # Use "identify -list font" or "convert -list font" to see all fonts on the system
        defaultTextFontname, defaultHeadingFontname = "Times-Roman", "FreeSans-Bold"
        topLineColor = "opaque"
        defaultMainHeadingFontcolor, defaultSectionHeadingFontcolor, defaultSectionCrossReferenceFontcolor = "indigo", "red1", "royalBlue"
        defaultVerseNumberFontcolor = "DarkOrange1"
        maxBooknameLetters = 12 # For the header line -- the chapter number is appended to this
        namingFormat = "Short" # "Short" or "Long" -- affects folder and filenames
        colorVerseNumbersFlag = False
        #digitSpace = chr(8199) # '\u2007'

        #blankFilepath = os.path.join( defaultControlFolder, "blank-240x320.jpg" )
        # Used: convert -fill khaki1 -draw 'rectangle 0,0 240,24' blank-240x320.jpg.jpg yblank-240x320.jpg
        #       Available colors are at http://www.imagemagick.org/script/color.php
        blankFilepath = os.path.join( defaultControlFolder, "yblank-240x320.jpg" )

        def render( commandList, jpegFilepath ):
            """
            """
            #print( "render: {} on {}".format( commandList, jpegFilepath ) )

            # Run the script on our data
            parameters = ['/usr/bin/timeout', '10s', '/usr/bin/convert' ]
            parameters.extend( commandList )
            parameters.append( jpegFilepath ) # input file
            parameters.append( jpegFilepath ) # output file
            #print( "Parameters", repr(parameters) )
            myProcess = subprocess.Popen( parameters, stdout=subprocess.PIPE, stderr=subprocess.PIPE )
            programOutputBytes, programErrorOutputBytes = myProcess.communicate()
            returnCode = myProcess.returncode

            # Process the output
            if programOutputBytes:
                programOutputString = programOutputBytes.decode( encoding="utf-8", errors="replace" )
                logging.critical( "renderLine: " + programOutputString )
                #with open( os.path.join( outputFolder, "UncompressedScriptOutput.txt" ), 'wt' ) as myFile: myFile.write( programOutputString )
            if programErrorOutputBytes:
                programErrorOutputString = programErrorOutputBytes.decode( encoding="utf-8", errors="replace" )
                logging.critical( "renderLineE: " + programErrorOutputString )
                #with open( os.path.join( outputFolder, "UncompressedScriptErrorOutput.txt" ), 'wt' ) as myFile: myFile.write( programErrorOutputString )

            return returnCode
        # end of render

        lastFontcolor = lastFontsize = lastFontname = None
        def renderLine( across, down, text, jpegFilepath, fontsize, fontname, fontcolor ):
            """
                convert -pointsize 36 -fill red -draw 'text 10,10 "Happy Birthday - You old so and so" ' test.jpg test1.jpg
            """
            nonlocal lastFontcolor, lastFontsize, lastFontname
            #print( "renderLine( {}, {}, {}, {}, {}, {}, {} )".format( across, down, repr(text), jpegFilepath, fontsize, fontcolor, leading ) )
            #fc = " -fill {}".format( fontcolor ) if fontcolor is not None else ''

            # Prepare the commands to render this line of text on the page
            commands = []
            if fontname != lastFontname:
                commands.append( '-font' ); commands.append( fontname )
                lastFontname = fontname
            if fontsize != lastFontsize:
                commands.append( '-pointsize' ); commands.append( str(fontsize) )
                lastFontsize = fontsize
            if fontcolor != lastFontcolor:
                commands.append( '-fill' ); commands.append( fontcolor )
                lastFontcolor = fontcolor
            commands.append( '-draw' )
            commands.append( 'text {},{} {}'.format( across, down, repr(text) ) )
            return commands
        # end of renderLine


        def renderVerseNumbers( givenAcross, down, vnInfo, jpegFilepath, fontsize, fontname, fontcolor ):
            """
            Failed experiment. A space is narrower than a digit. The Unicode digitSpace doesn't work in ImageMagick.
            """
            vnLineBuffer = ""
            vnCommands = []
            for posn,vn in vnInfo:
                #print( posn, repr(vn) )
                vnLineBuffer += ' ' * (posn - len(vnLineBuffer) ) + vn # Space is too narrow
                print( repr(vnLineBuffer), vnInfo )

                across = givenAcross + posn * fontsize * 3 / 10
                vnCommands.extend( renderLine( across, down, vn, jpegFilepath, fontsize, fontname, fontcolor ) )
            return vnCommands
        # end of renderVerseNumbers


        def renderPage( BBB, C, bookName, text, jpegFilepath, fontsize=None ):
            """
                I need to see a page showing 26-32 characters per line and 13-14 lines per page
            """
            nonlocal lastFontcolor, lastFontsize, lastFontname
            lastFontcolor = lastFontsize = lastFontname = None # So we're sure to get the initial commands in the stream

            #print( "\nrenderPage( {}, {}, {}, {}, {}, {} )".format( BBB, C, repr(bookName), repr(text), jpegFilepath, fontsize ) )

            # Create the blank file
            shutil.copy( blankFilepath, jpegFilepath ) # Copy it under its own name

            if fontsize is None: fontsize = defaultFontSize
            leading = int( defaultLeadingRatio * fontsize )
            #print( "Leading is {} for {}".format( leading, fontsize ) )
            across, down = leftPadding, leading - 2

            # Write the heading
            heading = "{}{}".format( bookName, '' if C=='0' else ' '+C )
            totalCommands = renderLine( across, down, heading, jpegFilepath, fontsize, defaultHeadingFontname, topLineColor )
            down += leading
            outputLineCount = 1

            # Clean up by removing any leading and trailing new lines
            if text and text[0]=='\n': text = text[1:]
            if text and text[-1]=='\n': text = text[:-1]

            indenter, extraLineIndent = '', 0
            textLineCount = textWordCount = 0
            lastLine = False
            lines = text.split('\n')
            #print( "Have lines:", len(lines) )
            for originalLine in lines:
                #print( textLineCount, "line", repr(originalLine) )
                line = originalLine
                fontcolor = "opaque" # gives black as default

                # extraLineIndent is used for indented text
                indenter, extraLineIndent = '', 0
                if '_I1_' in line: indenter, extraLineIndent = '_I1_', 1; line = line.replace( '_I1_', '', 1 )
                elif '_I2_' in line: indenter, extraLineIndent = '_I2_', 2; line = line.replace( '_I2_', '', 1 )
                elif '_I3_' in line: indenter, extraLineIndent = '_I3_', 3; line = line.replace( '_I3_', '', 1 )
                elif '_I4_' in line: indenter, extraLineIndent = '_I4_', 4; line = line.replace( '_I4_', '', 1 )
                if Globals.debugFlag: # Should only be one
                    assert( '_I1_' not in line and '_I2_' not in line and '_I3_' not in line and '_I4_' not in line )

                verseNumberList = [] # Contains a list of 2-tuples indicating where verse numbers should go

                if down >= maxDown - leading \
                or outputLineCount == maxLines - 1:
                    lastLine = True
                if down >= maxDown: break # We're finished
                #print( BBB, C, textLineCount, outputLineCount, down, maxDown, lastLine, repr(line) )

                isMainHeading = isSectionHeading = isSectionCrossReference = False
                if line.startswith('HhH'):
                    if lastLine:
                        #print( BBB, C, "Don't start main heading on last line", repr(line) )
                        break; # Don't print headings on the last line
                    line = line[3:] # Remove the heading marker
                    #print( "Got main heading:", BBB, C, repr(line) )
                    isMainHeading = True
                    fontcolor = defaultMainHeadingFontcolor
                elif line.startswith('SsS'):
                    if lastLine:
                        #print( BBB, C, "Don't start section heading on last line", repr(line) )
                        break; # Don't print headings on the last line
                    line = line[3:] # Remove the SsS heading marker
                    #print( "Got section heading:", BBB, C, repr(line) )
                    isSectionHeading = True
                    fontcolor = defaultSectionHeadingFontcolor
                elif line.startswith('RrR'):
                    line = line[3:] # Remove the RrR heading marker
                    #print( "Got section cross-reference:", BBB, C, repr(line) )
                    isSectionCrossReference = True
                    fontcolor = defaultSectionCrossReferenceFontcolor

                textLineCount += 1
                textWordCount = 0
                lineBuffer = ' ' * extraLineIndent # Handle indented paragraphs
                words = [] # Just in case the line is blank
                if line:
                    verseNumberLast = False
                    words = line.split(' ')
                    #print( textWordCount, "words", words )
                    for w,originalWord in enumerate( words ):
                        word = originalWord.replace( ' ', ' ' ) # Put back normal spaces
                        isVerseNumber = False
                        vix = word.find( 'VvV' )
                        if vix != -1: # This must be a verse number (perhaps preceded by some spaces)
                            word = word[:vix]+word[vix+3:]
                            isVerseNumber = True
                        #assert( 'VvV' not in word )

                        if down >= maxDown - leading \
                        or outputLineCount == maxLines - 1: lastLine = True
                        if down >= maxDown: break # We're finished
                        #print( '     ', textLineCount, outputLineCount, down, maxDown, lastLine, textWordCount, repr(word) )

                        # Allow for some letter-width variations
                        #   a bigger offset value will allow less to be added to the line
                        # NOTE: verse numbers start with VvV
                        #       and we don't want the last line to end with a verse number
                        offset = 1
                        potentialString = lineBuffer + word
                        potentialStringLower =  potentialString.lower()
                        capsCount = 0
                        for letter in potentialString:
                            if letter.isupper(): capsCount += 1
                        offset += (potentialStringLower.count('m')+potentialStringLower.count('w')+potentialStringLower.count('—')+capsCount)/3
                        offset -= (potentialStringLower.count(' ')+potentialStringLower.count('i')+potentialString.count('l')+potentialString.count('t'))/4
                        #if offset != 1:
                            #print( "Adjusted offset to", offset, "from", repr(potentialString) )

                        potentialLength = len(lineBuffer) + len(word) + offset
                        if lastLine and isVerseNumber: # We would have to include the next word also
                            if Globals.debugFlag: assert( w < len(words)-1 )
                            potentialLength += len(words[w+1]) + 1
                            #print( "Adjusted pL for", BBB, C, repr(word), repr(words[w+1]) )
                        if potentialLength  >= maxLineCharacters:
                            # Print this line as we've already got it coz it would be too long if we added the word
                            totalCommands.extend( renderLine( across, down, lineBuffer, jpegFilepath, fontsize, defaultTextFontname, fontcolor ) )
                            if verseNumberList:
                                print( repr(lineBuffer) )
                                totalCommands.extend( renderVerseNumbers( across, down, verseNumberList, jpegFilepath, fontsize, defaultTextFontname, defaultVerseNumberFontcolor ) )
                                verseNumberList = []
                            down += leading
                            outputLineCount += 1
                            lineBuffer = ' ' * extraLineIndent # Handle indented paragraphs
                            #print( outputLineCount, maxLines, outputLineCount>=maxLines )
                            if outputLineCount >= maxLines: break
                            if down >= maxDown: break # We're finished
                        # Add the word (without the verse number markers)
                        lineBuffer += (' ' if lineBuffer.lstrip() else '')
                        if isVerseNumber and colorVerseNumbersFlag:
                            verseNumberList.append( (len(lineBuffer),word,) )
                            lineBuffer += ' ' * int( 1.6 * len(word) ) # Just put spaces in for place holders for the present
                        else: lineBuffer += word
                        textWordCount += 1

                    # Words in this source text line are all processed
                    if lineBuffer.lstrip(): # do the last line
                        totalCommands.extend( renderLine( across, down, lineBuffer, jpegFilepath, fontsize, defaultTextFontname, fontcolor ) )
                        if verseNumberList:
                            print( repr(lineBuffer) )
                            totalCommands.extend( renderVerseNumbers( across, down, verseNumberList, jpegFilepath, fontsize, defaultTextFontname, defaultVerseNumberFontcolor ) )
                            verseNumberList = []
                        down += leading
                        outputLineCount += 1
                elif textLineCount!=1: # it's a blank line (but not the first line on the page)
                    down += defaultFontSize / 3 # Leave a blank 1/3 line
                    outputLineCount += 0.4
                #print( outputLineCount, maxLines, outputLineCount>=maxLines )
                if outputLineCount >= maxLines: break

            # Now render all those commands at once
            render( totalCommands, jpegFilepath ) # Do all the rendering at once

            # Find the left-over text
            leftoverText = ''
            #print( "textWordCount was", textWordCount, len(words) )
            #print( "textLineCount was", textLineCount, len(lines) )
            leftoverText += ' '.join( words[textWordCount:] )
            if textLineCount < len(lines):
                leftoverText += '\n' + '\n'.join( lines[textLineCount:] )


            #print( "leftoverText was", repr(leftoverText) )
            #if 'Impanalanginan te Manama si Nuwi' in text: halt
            return indenter+leftoverText if leftoverText else ''
        # end of renderPage


        def renderText( BBB, BBBnum, bookName, bookAbbrev, C, maxChapters, numVerses, text, bookFolderName, fontsize=None ):
            """
            """
            #print( "\nrenderText( {}, {}, {}, {}, {}, {}, {} )".format( BBB, C, repr(text), jpegFoldername, fontsize, fontcolor, leading ) )

            intC = int( C )
            if namingFormat == "Short":
                if maxChapters < 10: chapterFoldernameTemplate = "{:01}-{}/"
                elif maxChapters < 100: chapterFoldernameTemplate = "{:02}-{}/"
                else: chapterFoldernameTemplate = "{:03}-{}/"
                chapterFolderName = chapterFoldernameTemplate.format( intC, bookAbbrev )
                filenameTemplate = "{:02}.jpg" if numVerses < 80 else "{:03}.jpg" # Might go over 99 pages for the chapter
            elif namingFormat == "Long":
                if BBBnum < 100:
                    if maxChapters < 10:
                        chapterFoldernameTemplate, filenameTemplate = "{:02}-{:01}-{}/", "{:02}-{:01}-{:02}-{}.jpg"
                    elif maxChapters < 100:
                        chapterFoldernameTemplate, filenameTemplate = "{:02}-{:02}-{}/", "{:02}-{:02}-{:02}-{}.jpg"
                    else:
                        chapterFoldernameTemplate, filenameTemplate = "{:02}-{:03}-{}/", "{:02}-{:03}-{:02}-{}.jpg"
                else: # not normally expected
                    if maxChapters < 10:
                        chapterFoldernameTemplate, filenameTemplate = "{:03}-{:01}-{}/", "{:03}-{:01}-{:02}-{}.jpg"
                    elif maxChapters < 100:
                        chapterFoldernameTemplate, filenameTemplate = "{:03}-{:02}-{}/", "{:03}-{:02}-{:02}-{}.jpg"
                    else:
                        chapterFoldernameTemplate, filenameTemplate = "{:03}-{:03}-{}/", "{:03}-{:03}-{:02}-{}.jpg"
                chapterFolderName = chapterFoldernameTemplate.format( Globals.BibleBooksCodes.getReferenceNumber( BBB ), intC, BBB )
                if numVerses > 80: filenameTemplate = filenameTemplate.replace( "{:02}-{}", "{:03}-{}" )
            else: halt

            chapterFolderPath = os.path.join( bookFolderName, chapterFolderName )
            if not os.access( chapterFolderPath, os.F_OK ): os.makedirs( chapterFolderPath ) # Make the empty folder if there wasn't already one there

            pagesWritten = 0
            leftoverText = text
            while leftoverText:
                if namingFormat == "Short":
                    jpegOutputFilepath = os.path.join( chapterFolderPath, filenameTemplate.format( pagesWritten ) )
                elif namingFormat == "Long":
                    jpegOutputFilepath = os.path.join( chapterFolderPath, filenameTemplate.format( BBBnum, intC, pagesWritten, BBB ) )
                leftoverText = renderPage( BBB, C, bookName, leftoverText, jpegOutputFilepath )
                pagesWritten += 1
            if Globals.debugFlag and debuggingThisModule and BBB not in ('FRT','GLS',) and pagesWritten>99 and numVerses<65: halt # Template is probably bad

            #print( "pagesWritten were", pagesWritten )
            return pagesWritten
        # end of renderText


        # Write the plain text files
        for BBB,bookObject in self.books.items():
            pseudoUSFMData = bookObject._processedLines

            # Find a suitable bookname
            bookName = self.getAssumedBookName( BBB )
            for bookName in (self.getAssumedBookName(BBB), self.getLongTOCName(BBB), self.getShortTOCName(BBB), self.getBooknameAbbreviation(BBB), ):
                #print( "Tried bookName:", repr(bookName) )
                if bookName is not None and len(bookName)<=maxBooknameLetters: break
            bookAbbrev = self.getBooknameAbbreviation( BBB )
            bookAbbrev = BBB if not bookAbbrev else Globals.makeSafeFilename( bookAbbrev.replace( ' ', '' ) )

            BBBnum = Globals.BibleBooksCodes.getReferenceNumber( BBB )
            maxChapters = Globals.BibleBooksCodes.getMaxChapters( BBB )

            # Find a suitable folder name and make the necessary folder(s)
            if Globals.BibleBooksCodes.isOldTestament_NR( BBB ):
                subfolderName = "OT/"
            elif Globals.BibleBooksCodes.isNewTestament_NR( BBB ):
                subfolderName = "NT/"
            else:
                subfolderName = "Other/"
            if BBBnum < 100: bookFolderName = "{:02}-{}/".format( BBBnum, bookAbbrev )
            else: bookFolderName = "{:03}-{}/".format( BBBnum, bookAbbrev ) # Should rarely happen
            bookFolderPath = os.path.join( outputFolder, subfolderName, bookFolderName )
            if not os.access( bookFolderPath, os.F_OK ): os.makedirs( bookFolderPath ) # Make the empty folder if there wasn't already one there

            # First of all, get the text (by chapter)
            C = V = "0"
            numVerses = 0
            textBuffer, lastMarker = "", None
            for entry in pseudoUSFMData:
                marker, cleanText = entry.getMarker(), entry.getCleanText()
                #print( BBB, C, V, marker, repr(cleanText) )
                if marker in oftenIgnoredIntroMarkers: pass # Just ignore these lines
                elif marker in ('mt1','mt2','mt3','mt4','mte1','mte2','mte3','mte4','periph',): # Simple headings
                    #if textBuffer: textBuffer += '\n'
                    textBuffer += '\n\nHhH' + cleanText + '\n'
                elif marker in ('s1','s2','s3','s4', 'is1','is2','is3','is4','ms1','ms2','ms3','ms4', 'sr',): # Simple headings
                    #if textBuffer: textBuffer += '\n'
                    textBuffer += '\n\nSsS' + cleanText + '\n'
                elif marker in ('iot','io1','io2','io3','io4',): pass # Drop the introduction
                elif marker in ('c','cp',): # cp should follow (and thus override) c
                    if textBuffer: renderText( BBB, BBBnum, bookName, bookAbbrev, C, maxChapters, numVerses, textBuffer, bookFolderPath ); textBuffer = ""
                    C = cleanText
                    numVerses = 0
                elif marker == 'v':
                    V = cleanText
                    textBuffer += (' ' if textBuffer and textBuffer[-1]!='\n' else '') + 'VvV' + cleanText + ' '
                    numVerses += 1
                elif marker in ('r','mr',):
                    #numSpaces = ( maxLineCharacters - len(cleanText) ) // 2
                    #print( BBB, C, len(cleanText), "numSpaces:", numSpaces, repr(cleanText) )
                    #textBuffer += '\n' + ' '*numSpaces + cleanText # Roughly centred
                    if lastMarker not in ('s1','s2','s3','s4',): textBuffer += '\n' # Section headings already have one at the end
                    textBuffer += 'RrR' + ' '*((maxLineCharacters+1-len(cleanText))//2) + cleanText + '\n' # Roughly centred
                elif marker == 'b':
                    if Globals.debugFlag: assert( not cleanText )
                    textBuffer += '\n'
                elif marker == 'nb':
                    textBuffer += '\n' + cleanText
                elif marker in ('p', 'pi1','pi2','pi3','pi4', 'q1','q2','q3','q4', 'm','mi', 'ph1','ph2','ph3','ph4','pc',
                                'li1','li2','li3','li4', 'ip','ipi', 'ili1','ili2','ili3','ili4',): # Just put it on a new line
                    textBuffer += '\n'
                    if marker not in ('m','mi','ph1','ph2','ph3','ph4',): textBuffer += '  ' # Non-break spaces won't be lost later
                    if marker in ('li1','li2','li3','li4', 'ili1','ili2','ili3','ili4',): textBuffer += '• '
                    if marker in ('ipi','pi1','q1','ph1','mi','li1','ili1',): textBuffer += '_I1_'
                    elif marker in ('pi2','q2','ph2','li2','ili2',): textBuffer += '_I2_'
                    elif marker in ('pi3','q3','ph3','li3','ili3',): textBuffer += '_I3_'
                    elif marker in ('pi4','q4','ph4','li4','ili4',): textBuffer += '_I4_'
                    #if marker == 'q2': textBuffer += ' '
                    #elif marker == 'q3': textBuffer += '  '
                    if marker in ('ip','ipi','ili1','ili2','ili3','ili4',): textBuffer += cleanText
                    elif Globals.debugFlag: assert( not cleanText )
                elif marker in ('v~','p~',):
                    #assert( cleanText or extras )
                    textBuffer += cleanText
                elif marker in ('d','sp',):
                    #assert( cleanText or extras )
                    textBuffer += '\n' + cleanText
                elif marker not in ('c#','cl=',): # These are the markers that we can safely ignore for this export
                    if cleanText:
                        logging.critical( "toPhotoBible: lost text in {} field in {} {}:{} {}".format( marker, BBB, C, V, repr(cleanText) ) )
                        if Globals.debugFlag: halt
                    unhandledMarkers.add( marker )
                #if extras and marker not in ('v~','p~',):
                    #logging.critical( "toPhotoBible: extras not handled for {} at {} {}:{}".format( marker, BBB, C, V ) )
                    #if Globals.debugFlag: halt
                lastMarker = marker
            if textBuffer: renderText( BBB, BBBnum, bookName, bookAbbrev, C, maxChapters, numVerses, textBuffer, bookFolderPath ) # Write the last bit

                    #if verseByVerse:
                        #myFile.write( "{} ({}): '{}' '{}' {}\n" \
                            #.format( entry.getMarker(), entry.getOriginalMarker(), entry.getAdjustedText(), entry.getCleanText(), entry.getExtras() ) )

        if unhandledMarkers:
            logging.warning( "toPhotoBible: Unhandled markers were {}".format( unhandledMarkers ) )
            if Globals.verbosityLevel > 1:
                print( "  " + _("WARNING: Unhandled toPhotoBible markers were {}").format( unhandledMarkers ) )

        # Now create some zipped collections
        if Globals.verbosityLevel > 2: print( "  Zipping photo files..." )
        for subset in ('OT','NT','Other','All'):
            loadFolder = outputFolder if subset=='All' else os.path.join( outputFolder, subset+'/' )
            #print( repr(subset), "Load folder =", repr(loadFolder) )
            if os.path.exists( loadFolder ):
                zf = zipfile.ZipFile( os.path.join( outputFolder, subset+'PhotoFiles.zip' ), 'w', compression=zipfile.ZIP_DEFLATED )
                for root, dirs, files in os.walk( loadFolder ):
                    for filename in files:
                        if not filename.endswith( '.zip' ):
                            #print( repr(loadFolder), repr(root), repr(dirs), repr(files) )
                            #print( repr(os.path.relpath(os.path.join(root, filename))), repr(os.path.join(loadFolder, '..')) )
                            #print( os.path.join(root,filename), os.path.relpath(os.path.join(root, filename), os.path.join(loadFolder, '..')) ) # Save in the archive without the path
                            #  Save in the archive without the path --
                            #   parameters are filename to compress, archive name (relative path) to save as
                            zf.write( os.path.join(root,filename), os.path.relpath(os.path.join(root, filename), os.path.join(loadFolder, '..')) ) # Save in the archive without the path
                            #zf.write( filepath, filename ) # Save in the archive without the path
                zf.close()
        if self.abbreviation in ('MBTV','WEB','OEB',): # Do a special zip file of just Matthew as a test download
            zf = zipfile.ZipFile( os.path.join( outputFolder, 'MatthewPhotoFiles.zip' ), 'w', compression=zipfile.ZIP_DEFLATED )
            loadFolder = os.path.join( outputFolder, 'NT/' )
            for root, dirs, files in os.walk( loadFolder ):
                for filename in files:
                    #print( root, filename )
                    if '40-Mat' in root and not filename.endswith( '.zip' ): #  Save in the archive without the path --
                        #   parameters are filename to compress, archive name (relative path) to save as
                        zf.write( os.path.join(root,filename), os.path.relpath(os.path.join(root, filename), os.path.join(loadFolder, '..')) ) # Save in the archive without the path
            zf.close()

        return True
    # end of BibleWriter.toPhotoBible



    def toMediaWiki( self, outputFolder=None, controlDict=None, validationSchema=None ):
        """
        Using settings from the given control file,
            converts the USFM information to a Media Wiki file.
        """
        if Globals.verbosityLevel > 1: print( "Running BibleWriter:toMediaWiki..." )
        if Globals.debugFlag: assert( self.books )

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolder: outputFolder = "OutputFiles/BOS_MediaWiki_Export/"
        if not os.access( outputFolder, os.F_OK ): os.makedirs( outputFolder ) # Make the empty folder if there wasn't already one there
        if not controlDict:
            controlDict, defaultControlFilename = {}, "To_MediaWiki_controls.txt"
            try:
                ControlFiles.readControlFile( defaultControlFolder, defaultControlFilename, controlDict )
            except:
                logging.critical( "Unable to read control dict {} from {}".format( defaultControlFilename, defaultControlFolder ) )
        self.__adjustControlDict( controlDict )

        unhandledMarkers = set()

        bookAbbrevDict, bookNameDict, bookAbbrevNameDict = {}, {}, {}
        for BBB in Globals.BibleBooksCodes.getAllReferenceAbbreviations(): # Pre-process the language booknames
            if BBB in controlDict and controlDict[BBB]:
                bits = controlDict[BBB].split(',')
                if len(bits)!=2: logging.error( _("toMediaWiki: Unrecognized language book abbreviation and name for {}: '{}'").format( BBB, controlDict[BBB] ) )
                bookAbbrev = bits[0].strip().replace('"','') # Remove outside whitespace then the double quote marks
                bookName = bits[1].strip().replace('"','') # Remove outside whitespace then the double quote marks
                bookAbbrevDict[bookAbbrev], bookNameDict[bookName], bookAbbrevNameDict[BBB] = BBB, BBB, (bookAbbrev,bookName,)
                if ' ' in bookAbbrev: bookAbbrevDict[bookAbbrev.replace(' ','',1)] = BBB # Duplicate entries without the first space (presumably between a number and a name like 1 Kings)
                if ' ' in bookName: bookNameDict[bookName.replace(' ','',1)] = BBB # Duplicate entries without the first space

        toWikiMediaGlobals = { "verseRef":'', "XRefNum":0, "FootnoteNum":0, "lastRef":'', "OneChapterOSISBookCodes":Globals.BibleBooksCodes.getOSISSingleChapterBooksList() } # These are our global variables

# TODO: Need to handle footnotes \f + \fr ref \fk key \ft text \f* 	becomes <ref><!--\fr ref \fk key \ft-->text</ref>
        def writeMWBook( writerObject, BBB, bkData ):
            """Writes a book to the MediaWiki writerObject."""

            def processXRefsAndFootnotes( verse, extras ):
                """Convert cross-references and footnotes and return the adjusted verse text."""

                def processXRef( USFMxref ):
                    """
                    Return the OSIS code for the processed cross-reference (xref).

                    NOTE: The parameter here already has the /x and /x* removed.

                    \\x - \\xo 2:2: \\xt Lib 19:9-10; Diy 24:19.\\xt*\\x* (Backslashes are shown doubled here)
                        gives
                    <note type="crossReference" n="1">2:2: <reference>Lib 19:9-10; Diy 24:19.</reference></note> (Crosswire -- invalid OSIS -- which then needs to be converted)
                    <note type="crossReference" osisRef="Ruth.2.2" osisID="Ruth.2.2!crossreference.1" n="-"><reference type="source" osisRef="Ruth.2.2">2:2: </reference><reference osisRef="-">Lib 19:9-10</reference>; <reference osisRef="Ruth.Diy.24!:19">Diy 24:19</reference>.</note> (Snowfall)
                    \\x - \\xo 3:5: a \\xt Rum 11:1; \\xo b \\xt Him 23:6; 26:5.\\xt*\\x* is more complex still.
                    """
                    nonlocal BBB
                    toWikiMediaGlobals["XRefNum"] += 1
                    OSISxref = '<note type="crossReference" osisRef="{}" osisID="{}!crossreference.{}">'.format( toWikiMediaGlobals["verseRef"], toWikiMediaGlobals["verseRef"], toWikiMediaGlobals["XRefNum"] )
                    for j,token in enumerate(USFMxref.split('\\')):
                        #print( "processXRef", j, "'"+token+"'", "from", '"'+USFMxref+'"' )
                        if j==0: # The first token (but the x has already been removed)
                            rest = token.strip()
                            if rest != '-': logging.warning( _("toMediaWiki: We got something else here other than hyphen (probably need to do something with it): {} '{}' from '{}'").format( chapterRef, token, text ) )
                        elif token.startswith('xo '): # xref reference follows
                            adjToken = token[3:].strip()
                            if adjToken.endswith(' a'): adjToken = adjToken[:-2] # Remove any 'a' suffix (occurs when a cross-reference has multiple (a and b) parts
                            if adjToken.endswith(':'): adjToken = adjToken[:-1] # Remove any final colon (this is a language dependent hack)
                            adjToken = getBookAbbreviationFunction(BBB) + ' ' + adjToken # Prepend the vernacular book abbreviation
                            osisRef = BRL.parseToOSIS( adjToken, toWikiMediaGlobals["verseRef"] )
                            if osisRef is not None:
                                OSISxref += '<reference type="source" osisRef="{}">{}</reference>'.format( osisRef,token[3:] )
                                if not BRL.containsReference( BBB, currentChapterNumberString, verseNumberString ):
                                    logging.error( _("toMediaWiki: Cross-reference at {} {}:{} seems to contain the wrong self-reference '{}'").format( BBB, currentChapterNumberString, verseNumberString, token ) )
                        elif token.startswith('xt '): # xref text follows
                            xrefText = token[3:]
                            finalPunct = ''
                            while xrefText[-1] in (' ,;.'): finalPunct = xrefText[-1] + finalPunct; xrefText = xrefText[:-1]
                            #adjString = xrefText[:-6] if xrefText.endswith( ' (LXX)' ) else xrefText # Sorry, this is a crude hack to avoid unnecessary error messages
                            osisRef = BRL.parseToOSIS( xrefText, toWikiMediaGlobals["verseRef"] )
                            if osisRef is not None:
                                OSISxref += '<reference type="source" osisRef="{}">{}</reference>'.format( osisRef, xrefText+finalPunct )
                        elif token.startswith('x '): # another whole xref entry follows
                            rest = token[2:].strip()
                            if rest != '-': logging.warning( _("toMediaWiki: We got something else here other than hyphen (probably need to do something with it): {} '{}' from '{}'").format( chapterRef, token, text ) )
                        elif token in ('xt*', 'x*'):
                            pass # We're being lazy here and not checking closing markers properly
                        else:
                            logging.warning( _("toMediaWiki: Unprocessed '{}' token in {} xref '{}'").format( token, toWikiMediaGlobals["verseRef"], USFMxref ) )
                    OSISxref += '</note>'
                    return OSISxref
                # end of toMediaWiki.processXRef

                def processFootnote( USFMfootnote ):
                    """
                    Return the OSIS code for the processed footnote.

                    NOTE: The parameter here already has the /f and /f* removed.

                    \\f + \\fr 1:20 \\ft Su ka kaluwasan te Nawumi ‘keupianan,’ piru ka kaluwasan te Mara ‘masakit se geyinawa.’\\f* (Backslashes are shown doubled here)
                        gives
                    <note n="1">1:20 Su ka kaluwasan te Nawumi ‘keupianan,’ piru ka kaluwasan te Mara ‘masakit se geyinawa.’</note> (Crosswire)
                    <note osisRef="Ruth.1.20" osisID="Ruth.1.20!footnote.1" n="+"><reference type="source" osisRef="Ruth.1.20">1:20 </reference>Su ka kaluwasan te Nawumi ‘keupianan,’ piru ka kaluwasan te Mara ‘masakit se geyinawa.’</note> (Snowfall)
                    """
                    toWikiMediaGlobals["FootnoteNum"] += 1
                    OSISfootnote = '<note osisRef="{}" osisID="{}!footnote.{}">'.format( toWikiMediaGlobals["verseRef"], toWikiMediaGlobals["verseRef"], toWikiMediaGlobals["FootnoteNum"] )
                    for j,token in enumerate(USFMfootnote.split('\\')):
                        #print( "processFootnote", j, token, USFMfootnote )
                        if j==0: continue # ignore the + for now
                        elif token.startswith('fr '): # footnote reference follows
                            adjToken = token[3:].strip()
                            if adjToken.endswith(':'): adjToken = adjToken[:-1] # Remove any final colon (this is a language dependent hack)
                            adjToken = getBookAbbreviationFunction(BBB) + ' ' + adjToken # Prepend the vernacular book abbreviation
                            osisRef = BRL.parseToOSIS( adjToken, toWikiMediaGlobals["verseRef"] )
                            if osisRef is not None:
                                OSISfootnote += '<reference osisRef="{}" type="source">{}</reference>'.format( osisRef, token[3:] )
                                if not BRL.containsReference( BBB, currentChapterNumberString, verseNumberString ):
                                    logging.error( _("toMediaWiki: Footnote at {} {}:{} seems to contain the wrong self-reference '{}'").format( BBB, currentChapterNumberString, verseNumberString, token ) )
                        elif token.startswith('ft '): # footnote text follows
                            OSISfootnote += token[3:]
                        elif token.startswith('fq ') or token.startswith('fqa '): # footnote quote follows -- NOTE: We also assume here that the next marker closes the fq field
                            OSISfootnote += '<catchWord>{}</catchWord>'.format( token[3:] ) # Note that the trailing space goes in the catchword here -- seems messy
                        elif token in ('ft*','ft* ','fq*','fq* ','fqa*','fqa* '):
                            pass # We're being lazy here and not checking closing markers properly
                        else:
                            logging.warning( _("toMediaWiki: Unprocessed '{}' token in {} footnote '{}'").format( token, toWikiMediaGlobals["verseRef"], USFMfootnote ) )
                    OSISfootnote += '</note>'
                    #print( '', OSISfootnote )
                    return OSISfootnote
                # end of toMediaWiki.processFootnote

                while '\\x ' in verse and '\\x*' in verse: # process cross-references (xrefs)
                    ix1 = verse.index('\\x ')
                    ix2 = verse.find('\\x* ') # Note the extra space here at the end
                    if ix2 == -1: # Didn't find it so must be no space after the asterisk
                        ix2 = verse.index('\\x*')
                        ix2b = ix2 + 3 # Where the xref ends
                        logging.warning( _("toMediaWiki: No space after xref entry in {}").format( toWikiMediaGlobals["verseRef"] ) )
                    else: ix2b = ix2 + 4
                    xref = verse[ix1+3:ix2]
                    osisXRef = processXRef( xref )
                    #print( osisXRef )
                    verse = verse[:ix1] + osisXRef + verse[ix2b:]
                while '\\f ' in verse and '\\f*' in verse: # process footnotes
                    ix1 = verse.index('\\f ')
                    ix2 = verse.find('\\f*')
#                    ix2 = verse.find('\\f* ') # Note the extra space here at the end -- doesn't always work if there's two footnotes within one verse!!!
#                    if ix2 == -1: # Didn't find it so must be no space after the asterisk
#                        ix2 = verse.index('\\f*')
#                        ix2b = ix2 + 3 # Where the footnote ends
#                        #logging.warning( 'toMediaWiki: No space after footnote entry in {}'.format(toWikiMediaGlobals["verseRef"] )
#                    else: ix2b = ix2 + 4
                    footnote = verse[ix1+3:ix2]
                    osisFootnote = processFootnote( footnote )
                    #print( osisFootnote )
                    verse = verse[:ix1] + osisFootnote + verse[ix2+3:]
#                    verse = verse[:ix1] + osisFootnote + verse[ix2b:]
                return verse
            # end of toMediaWiki.processXRefsAndFootnotes

            bookRef = Globals.BibleBooksCodes.getOSISAbbreviation( BBB ) # OSIS book name
            if bookRef is None:
                print( "Doesn't encode OSIS '{}' book yet".format( BBB ) )
                return
            bookName = None
            C = V = "0"
            verseText = '' # Do we really need this?
            #chapterNumberString = None
            for verseDataEntry in bkData._processedLines: # Process internal Bible data lines
                marker, text, extras = verseDataEntry.getMarker(), verseDataEntry.getAdjustedText(), verseDataEntry.getExtras()
                #print( "toMediaWiki:writeMWBook", BBB, bookRef, bookName, marker, text, extras )
                if marker in ('id','h','mt1','mt2','mt3','mt4',):
                    writerObject.writeLineComment( '\\{} {}'.format( marker, text ) )
                    bookName = text # in case there's no toc2 entry later
                elif marker == 'toc2':
                    bookName = text
                elif marker in oftenIgnoredIntroMarkers: pass # Just ignore these lines

                elif marker == 'li':
                    # :<!-- \li -->text
                    writerObject.writeLineText( ":" )
                    writerObject.writeLineComment( '\\li' )
                    writerObject.writeLineText( text )
                elif marker == 'c':
                    C, V = text, "0"
                    chapterNumberString = text
                    chapterRef = bookRef + '.' + chapterNumberString
                    # Bible:BookName_#
                    if bookName: writerObject.writeLineText( 'Bible:{}_{}'.format(bookName, chapterNumberString) )
                elif marker == 's1':
                    # === text ===
                    writerObject.writeLineText( '=== {} ==='.format(text) )
                elif marker == 'r':
                    # <span class="srefs">text</span>
                    if text: writerObject.writeLineOpenClose( 'span', text, ('class','srefs') )
                elif marker == 'p':
                    writerObject.writeNewLine( 2 );
                elif marker == 'v':
                    #if not chapterNumberString: # some single chapter books don't have a chapter number marker in them
                    #    if Globals.debugFlag: assert( BBB in Globals.BibleBooksCodes.getSingleChapterBooksList() )
                    #    chapterNumberString = '1'
                    #    chapterRef = bookRef + '.' + chapterNumberString
                    V = text
                    verseNumberString = text # Gets written with in the v~ line
                    # <span id="chapter#_#"><sup>#</sup> text</span>
                    #writerObject.writeLineOpenClose( 'span', '<sup>{}</sup> {}'.format(verseNumberString,adjText), ('id',"chapter{}_{}".format(chapterNumberString, verseNumberString) ), noTextCheck=True )
                elif marker == 'v~':
                    #print( "Oomph", marker, repr(text), chapterRef, verseNumberString )
                    assert( text or extras )
                    # TODO: We haven't stripped out character fields from within the verse -- not sure how MediaWiki handles them yet
                    if not text: # this is an empty (untranslated) verse
                        adjText = '- - -' # but we'll put in a filler
                    else: adjText = processXRefsAndFootnotes( text, extras )
                    # <span id="chapter#_#"><sup>#</sup> text</span>
                    writerObject.writeLineOpenClose( 'span', '<sup>{}</sup> {}'.format(verseNumberString,adjText), ('id',"chapter{}_{}".format(chapterNumberString, verseNumberString) ), noTextCheck=True )
                elif marker == 'p~':
                    #print( "Ouch", marker, repr(text), chapterRef, verseNumberString )
                    assert( text or extras )
                    # TODO: We haven't stripped out character fields from within the verse -- not sure how MediaWiki handles them yet
                    adjText = processXRefsAndFootnotes( text, extras )
                    writerObject.writeLineText( ':{}'.format(adjText, noTextCheck=True) ) # No check so it doesn't choke on embedded xref and footnote fields
                elif marker == 'q1':
                    adjText = processXRefsAndFootnotes( verseText, extras )
                    writerObject.writeLineText( ':{}'.format(adjText, noTextCheck=True) ) # No check so it doesn't choke on embedded xref and footnote fields
                elif marker == 'q2':
                    adjText = processXRefsAndFootnotes( verseText, extras )
                    writerObject.writeLineText( '::{}'.format(adjText, noTextCheck=True) )
                elif marker == 'm': # Margin/Flush-left paragraph
                    adjText = processXRefsAndFootnotes( verseText, extras )
                    writerObject.writeLineText( '::{}'.format(adjText, noTextCheck=True) )
                elif marker not in ('c#',): # These are the markers that we can safely ignore for this export
                    if text:
                        logging.error( "toMediaWiki: lost text in {} field in {} {}:{} {}".format( marker, BBB, C, V, repr(text) ) )
                        #if Globals.debugFlag: halt
                    if extras:
                        logging.error( "toMediaWiki: lost extras in {} field in {} {}:{}".format( marker, BBB, C, V ) )
                        #if Globals.debugFlag: halt
                    unhandledMarkers.add( marker )
                if extras and marker not in ('v~','p~',): logging.critical( "toMediaWiki: extras not handled for {} at {} {}:{}".format( marker, BBB, C, V ) )
        # end of toMediaWiki.writeMWBook

        # Set-up our Bible reference system
        if controlDict['PublicationCode'] == "GENERIC":
            BOS = self.genericBOS
            BRL = self.genericBRL
        else:
            BOS = BibleOrganizationalSystem( controlDict["PublicationCode"] )
            BRL = BibleReferenceList( BOS, BibleObject=None )

        if Globals.verbosityLevel > 2: print( _("  Exporting to MediaWiki format...") )
        filename = Globals.makeSafeFilename( controlDict["MediaWikiOutputFilename"] )
        xw = MLWriter( filename, outputFolder )
        xw.setHumanReadable()
        xw.start()
        for BBB,bookData in self.books.items():
            writeMWBook( xw, BBB, bookData )
        xw.close()

        if unhandledMarkers:
            logging.warning( "toMediaWiki: Unhandled markers were {}".format( unhandledMarkers ) )
            if Globals.verbosityLevel > 1:
                print( "  " + _("WARNING: Unhandled toMediaWiki markers were {}").format( unhandledMarkers ) )

        # Now create a zipped version
        filepath = os.path.join( outputFolder, filename )
        if Globals.verbosityLevel > 2: print( "  Zipping {} MediaWiki file...".format( filename ) )
        zf = zipfile.ZipFile( filepath+'.zip', 'w', compression=zipfile.ZIP_DEFLATED )
        zf.write( filepath, filename )
        zf.close()

        if validationSchema: return xw.validate( validationSchema )
        return True
    # end of BibleWriter.toMediaWiki



    def toZefaniaXML( self, outputFolder=None, controlDict=None, validationSchema=None ):
        """
        Using settings from the given control file,
            converts the USFM information to a UTF-8 Zefania XML file.

        This format is roughly documented at http://de.wikipedia.org/wiki/Zefania_XML
            but more fields can be discovered by looking at downloaded files.
        """
        if Globals.verbosityLevel > 1: print( "Running BibleWriter:toZefaniaXML..." )
        if Globals.debugFlag: assert( self.books )

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolder: outputFolder = "OutputFiles/BOS_Zefania_Export/"
        if not os.access( outputFolder, os.F_OK ): os.makedirs( outputFolder ) # Make the empty folder if there wasn't already one there
        if not controlDict:
            controlDict, defaultControlFilename = {}, "To_Zefania_controls.txt"
            try:
                ControlFiles.readControlFile( defaultControlFolder, defaultControlFilename, controlDict )
            except:
                logging.critical( "Unable to read control dict {} from {}".format( defaultControlFilename, defaultControlFolder ) )
        self.__adjustControlDict( controlDict )

        unhandledMarkers = set()

        def writeHeader( writerObject ):
            """Writes the Zefania header to the Zefania XML writerObject."""
            writerObject.writeLineOpen( 'INFORMATION' )
            if "ZefaniaTitle" in controlDict and controlDict["ZefaniaTitle"]: writerObject.writeLineOpenClose( 'title' , controlDict["ZefaniaTitle"] )
            if "ZefaniaSubject" in controlDict and controlDict["ZefaniaSubject"]: writerObject.writeLineOpenClose( 'subject', controlDict["ZefaniaSubject"] )
            if "ZefaniaDescription" in controlDict and controlDict["ZefaniaDescription"]: writerObject.writeLineOpenClose( 'description', controlDict["ZefaniaDescription"] )
            if "ZefaniaPublisher" in controlDict and controlDict["ZefaniaPublisher"]: writerObject.writeLineOpenClose( 'publisher', controlDict["ZefaniaPublisher"] )
            if "ZefaniaContributors" in controlDict and controlDict["ZefaniaContributors"]: writerObject.writeLineOpenClose( 'contributors', controlDict["ZefaniaContributors"] )
            if "ZefaniaIdentifier" in controlDict and controlDict["ZefaniaIdentifier"]: writerObject.writeLineOpenClose( 'identifier', controlDict["ZefaniaIdentifier"] )
            if "ZefaniaSource" in controlDict and controlDict["ZefaniaSource"]: writerObject.writeLineOpenClose( 'identifier', controlDict["ZefaniaSource"] )
            if "ZefaniaCoverage" in controlDict and controlDict["ZefaniaCoverage"]: writerObject.writeLineOpenClose( 'coverage', controlDict["ZefaniaCoverage"] )
            writerObject.writeLineOpenClose( 'format', 'Zefania XML Bible Markup Language' )
            writerObject.writeLineOpenClose( 'date', datetime.now().date().isoformat() )
            writerObject.writeLineOpenClose( 'creator', 'BibleWriter.py' )
            writerObject.writeLineOpenClose( 'type', 'bible text' )
            if "ZefaniaLanguage" in controlDict and controlDict["ZefaniaLanguage"]: writerObject.writeLineOpenClose( 'language', controlDict["ZefaniaLanguage"] )
            if "ZefaniaRights" in controlDict and controlDict["ZefaniaRights"]: writerObject.writeLineOpenClose( 'rights', controlDict["ZefaniaRights"] )
            writerObject.writeLineClose( 'INFORMATION' )
        # end of toZefaniaXML.writeHeader

        def writeZefBook( writerObject, BBB, bkData ):
            """Writes a book to the Zefania XML writerObject."""
            #print( 'BIBLEBOOK', [('bnumber',Globals.BibleBooksCodes.getReferenceNumber(BBB)), ('bname',Globals.BibleBooksCodes.getEnglishName_NR(BBB)), ('bsname',Globals.BibleBooksCodes.getOSISAbbreviation(BBB))] )
            OSISAbbrev = Globals.BibleBooksCodes.getOSISAbbreviation( BBB )
            if not OSISAbbrev:
                logging.error( "toZefania: Can't write {} Zefania book because no OSIS code available".format( BBB ) ); return
            writerObject.writeLineOpen( 'BIBLEBOOK', [('bnumber',Globals.BibleBooksCodes.getReferenceNumber(BBB)), ('bname',Globals.BibleBooksCodes.getEnglishName_NR(BBB)), ('bsname',OSISAbbrev)] )
            haveOpenChapter = False
            C = V = "0"
            for verseDataEntry in bkData._processedLines: # Process internal Bible data lines
                marker, text, extras = verseDataEntry.getMarker(), verseDataEntry.getFullText(), verseDataEntry.getExtras()
                if marker in ('id', 'ide', 'h', 'toc1','toc2','toc3', ): pass # Just ignore these metadata markers
                elif marker == 'c':
                    C, V = text, "0"
                    if haveOpenChapter:
                        writerObject.writeLineClose ( 'CHAPTER' )
                    writerObject.writeLineOpen ( 'CHAPTER', ('cnumber',text) )
                    haveOpenChapter = True
                elif marker == 'v':
                    V = text
                    #print( "Text '{}'".format( text ) )
                    if not text: logging.warning( "toZefaniaXML: Missing text for v" ); continue
                    verseNumberString = text.replace('<','').replace('>','').replace('"','') # Used below but remove anything that'll cause a big XML problem later
                    #writerObject.writeLineOpenClose ( 'VERS', verseText, ('vnumber',verseNumberString) )
                elif marker == 'v~':
                    if Globals.debugFlag: assert( text or extras )
                    #print( "Text '{}'".format( text ) )
                    if not text: logging.warning( "toZefaniaXML: Missing text for v~" ); continue
                    # TODO: We haven't stripped out character fields from within the verse -- not sure how Zefania handles them yet
                    if not text: # this is an empty (untranslated) verse
                        text = '- - -' # but we'll put in a filler
                    writerObject.writeLineOpenClose ( 'VERS', text, ('vnumber',verseNumberString) )
                elif marker == 'p~':
                    if Globals.debugFlag: assert( text or extras )
                    # TODO: We haven't stripped out character fields from within the verse -- not sure how Zefania handles them yet
                    if text: writerObject.writeLineOpenClose ( 'VERS', text )
                elif marker not in ('c#',): # These are the markers that we can safely ignore for this export
                    if text:
                        logging.error( "toZefania: lost text in {} field in {} {}:{} {}".format( marker, BBB, C, V, repr(text) ) )
                        #if Globals.debugFlag: halt
                    if extras:
                        logging.error( "toZefania: lost extras in {} field in {} {}:{}".format( marker, BBB, C, V ) )
                        #if Globals.debugFlag: halt
                    unhandledMarkers.add( marker )
                if extras and marker not in ('v~','p~',): logging.critical( "toZefania: extras not handled for {} at {} {}:{}".format( marker, BBB, C, V ) )
            if haveOpenChapter:
                writerObject.writeLineClose( 'CHAPTER' )
            writerObject.writeLineClose( 'BIBLEBOOK' )
        # end of toZefaniaXML.writeZefBook

        # Set-up our Bible reference system
        if controlDict['PublicationCode'] == "GENERIC":
            BOS = self.genericBOS
            BRL = self.genericBRL
        else:
            BOS = BibleOrganizationalSystem( controlDict["PublicationCode"] )
            BRL = BibleReferenceList( BOS, BibleObject=None )

        if Globals.verbosityLevel > 2: print( _("  Exporting to Zefania format...") )
        filename = Globals.makeSafeFilename( controlDict["ZefaniaOutputFilename"] )
        xw = MLWriter( filename, outputFolder )
        xw.setHumanReadable()
        xw.start()
# TODO: Some modules have <XMLBIBLE xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="zef2005.xsd" version="2.0.1.18" status='v' revision="1" type="x-bible" biblename="KJV+">
        xw.writeLineOpen( 'XMLBible', [('xmlns:xsi',"http://www.w3.org/2001/XMLSchema-instance"), ('type',"x-bible"), ('biblename',controlDict["ZefaniaBibleName"]) ] )
        if True: #if controlDict["ZefaniaFiles"]=="byBible":
            writeHeader( xw )
            for BBB,bookData in self.books.items():
                writeZefBook( xw, BBB, bookData )
        xw.writeLineClose( 'XMLBible' )
        xw.close()

        if unhandledMarkers:
            logging.warning( "toZefania: Unhandled markers were {}".format( unhandledMarkers ) )
            if Globals.verbosityLevel > 1:
                print( "  " + _("WARNING: Unhandled toZefania markers were {}").format( unhandledMarkers ) )

        # Now create a zipped version
        filepath = os.path.join( outputFolder, filename )
        if Globals.verbosityLevel > 2: print( "  Zipping {} pickle file...".format( filename ) )
        zf = zipfile.ZipFile( filepath+'.zip', 'w', compression=zipfile.ZIP_DEFLATED )
        zf.write( filepath, filename )
        zf.close()

        if validationSchema: return xw.validate( validationSchema )
        return True
    # end of BibleWriter.toZefaniaXML



    def toHaggaiXML( self, outputFolder=None, controlDict=None, validationSchema=None ):
        """
        Using settings from the given control file,
            converts the USFM information to a UTF-8 Haggai XML file.

        This format is roughly documented at http://de.wikipedia.org/wiki/Haggai_XML
            but more fields can be discovered by looking at downloaded files.
        """
        if Globals.verbosityLevel > 1: print( "Running BibleWriter:toHaggaiXML..." )
        if Globals.debugFlag: assert( self.books )

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolder: outputFolder = "OutputFiles/BOS_Haggai_Export/"
        if not os.access( outputFolder, os.F_OK ): os.makedirs( outputFolder ) # Make the empty folder if there wasn't already one there
        if not controlDict:
            controlDict, defaultControlFilename = {}, "To_Haggai_controls.txt"
            try:
                ControlFiles.readControlFile( defaultControlFolder, defaultControlFilename, controlDict )
            except:
                logging.critical( "Unable to read control dict {} from {}".format( defaultControlFilename, defaultControlFolder ) )
        self.__adjustControlDict( controlDict )

        unhandledMarkers = set()

        def writeHeader( writerObject ):
            """Writes the Haggai header to the Haggai XML writerObject."""
            writerObject.writeLineOpen( 'INFORMATION' )
            if "HaggaiTitle" in controlDict and controlDict["HaggaiTitle"]: writerObject.writeLineOpenClose( 'title' , controlDict["HaggaiTitle"] )
            if "HaggaiSubject" in controlDict and controlDict["HaggaiSubject"]: writerObject.writeLineOpenClose( 'subject', controlDict["HaggaiSubject"] )
            if "HaggaiDescription" in controlDict and controlDict["HaggaiDescription"]: writerObject.writeLineOpenClose( 'description', controlDict["HaggaiDescription"] )
            if "HaggaiPublisher" in controlDict and controlDict["HaggaiPublisher"]: writerObject.writeLineOpenClose( 'publisher', controlDict["HaggaiPublisher"] )
            if "HaggaiContributors" in controlDict and controlDict["HaggaiContributors"]: writerObject.writeLineOpenClose( 'contributors', controlDict["HaggaiContributors"] )
            if "HaggaiIdentifier" in controlDict and controlDict["HaggaiIdentifier"]: writerObject.writeLineOpenClose( 'identifier', controlDict["HaggaiIdentifier"] )
            if "HaggaiSource" in controlDict and controlDict["HaggaiSource"]: writerObject.writeLineOpenClose( 'identifier', controlDict["HaggaiSource"] )
            if "HaggaiCoverage" in controlDict and controlDict["HaggaiCoverage"]: writerObject.writeLineOpenClose( 'coverage', controlDict["HaggaiCoverage"] )
            writerObject.writeLineOpenClose( 'format', 'Haggai XML Bible Markup Language' )
            writerObject.writeLineOpenClose( 'date', datetime.now().date().isoformat() )
            writerObject.writeLineOpenClose( 'creator', 'BibleWriter.py' )
            writerObject.writeLineOpenClose( 'type', 'bible text' )
            if "HaggaiLanguage" in controlDict and controlDict["HaggaiLanguage"]: writerObject.writeLineOpenClose( 'language', controlDict["HaggaiLanguage"] )
            if "HaggaiRights" in controlDict and controlDict["HaggaiRights"]: writerObject.writeLineOpenClose( 'rights', controlDict["HaggaiRights"] )
            writerObject.writeLineClose( 'INFORMATION' )
        # end of toHaggaiXML.writeHeader

        def writeHagBook( writerObject, BBB, bkData ):
            """Writes a book to the Haggai XML writerObject."""
            #print( 'BIBLEBOOK', [('bnumber',Globals.BibleBooksCodes.getReferenceNumber(BBB)), ('bname',Globals.BibleBooksCodes.getEnglishName_NR(BBB)), ('bsname',Globals.BibleBooksCodes.getOSISAbbreviation(BBB))] )
            OSISAbbrev = Globals.BibleBooksCodes.getOSISAbbreviation( BBB )
            if not OSISAbbrev:
                logging.error( "toHaggai: Can't write {} Haggai book because no OSIS code available".format( BBB ) ); return
            writerObject.writeLineOpen( 'BIBLEBOOK', [('bnumber',Globals.BibleBooksCodes.getReferenceNumber(BBB)), ('bname',Globals.BibleBooksCodes.getEnglishName_NR(BBB)), ('bsname',OSISAbbrev)] )
            haveOpenChapter = haveOpenParagraph = False
            C = V = "0"
            for verseDataEntry in bkData._processedLines: # Process internal Bible data lines
                marker, text, extras = verseDataEntry.getMarker(), verseDataEntry.getFullText(), verseDataEntry.getExtras()
                if marker in ('id', 'ide', 'h', 'toc1','toc2','toc3', ): pass # Just ignore these metadata markers
                elif marker == 'c':
                    C, V = text, "0"
                    if haveOpenParagraph:
                        writerObject.writeLineClose ( 'PARAGRAPH' ); haveOpenParagraph = False
                    if haveOpenChapter:
                        writerObject.writeLineClose ( 'CHAPTER' )
                    writerObject.writeLineOpen ( 'CHAPTER', ('cnumber',text) )
                    haveOpenChapter = True
                elif marker == 'p':
                    if haveOpenParagraph:
                        writerObject.writeLineClose ( 'PARAGRAPH' )
                    writerObject.writeLineOpen ( 'PARAGRAPH' )
                    haveOpenParagraph = True
                elif marker == 'v':
                    V = text
                    #print( "Text '{}'".format( text ) )
                    if not text: logging.warning( "toHaggaiXML: Missing text for v" ); continue
                    verseNumberString = text.replace('<','').replace('>','').replace('"','') # Used below but remove anything that'll cause a big XML problem later
                    #writerObject.writeLineOpenClose ( 'VERS', verseText, ('vnumber',verseNumberString) )
                elif marker == 'v~':
                    if Globals.debugFlag: assert( text or extras )
                    #print( "Text '{}'".format( text ) )
                    if not text: logging.warning( "toHaggaiXML: Missing text for v~" ); continue
                    # TODO: We haven't stripped out character fields from within the verse -- not sure how Haggai handles them yet
                    if not text: # this is an empty (untranslated) verse
                        text = '- - -' # but we'll put in a filler
                    writerObject.writeLineOpenClose ( 'VERSE', text, ('vnumber',verseNumberString) )
                elif marker == 'p~':
                    if Globals.debugFlag: assert( text or extras )
                    # TODO: We haven't stripped out character fields from within the verse -- not sure how Haggai handles them yet
                    if text: writerObject.writeLineOpenClose ( 'VERSE', text )
                elif marker not in ('c#',): # These are the markers that we can safely ignore for this export
                    if text:
                        logging.error( "toHaggai: lost text in {} field in {} {}:{} {}".format( marker, BBB, C, V, repr(text) ) )
                        #if Globals.debugFlag: halt
                    if extras:
                        logging.error( "toHaggai: lost extras in {} field in {} {}:{}".format( marker, BBB, C, V ) )
                        #if Globals.debugFlag: halt
                    unhandledMarkers.add( marker )
                if extras and marker not in ('v~','p~',): logging.critical( "toHaggai: extras not handled for {} at {} {}:{}".format( marker, BBB, C, V ) )
            if haveOpenParagraph:
                writerObject.writeLineClose ( 'PARAGRAPH' )
            if haveOpenChapter:
                writerObject.writeLineClose( 'CHAPTER' )
            writerObject.writeLineClose( 'BIBLEBOOK' )
        # end of toHaggaiXML.writeHagBook

        # Set-up our Bible reference system
        if controlDict['PublicationCode'] == "GENERIC":
            BOS = self.genericBOS
            BRL = self.genericBRL
        else:
            BOS = BibleOrganizationalSystem( controlDict["PublicationCode"] )
            BRL = BibleReferenceList( BOS, BibleObject=None )

        if Globals.verbosityLevel > 2: print( _("  Exporting to Haggai format...") )
        filename = Globals.makeSafeFilename( controlDict["HaggaiOutputFilename"] )
        xw = MLWriter( filename, outputFolder )
        xw.setHumanReadable()
        xw.start()
# TODO: Some modules have <XMLBIBLE xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="zef2005.xsd" version="2.0.1.18" status='v' revision="1" type="x-bible" biblename="KJV+">
        xw.writeLineOpen( 'XMLBible', [('xmlns:xsi',"http://www.w3.org/2001/XMLSchema-instance"), ('type',"x-bible"), ('biblename',controlDict["HaggaiBibleName"]) ] )
        if True: #if controlDict["HaggaiFiles"]=="byBible":
            writeHeader( xw )
            for BBB,bookData in self.books.items():
                writeHagBook( xw, BBB, bookData )
        xw.writeLineClose( 'XMLBible' )
        xw.close()

        if unhandledMarkers:
            logging.warning( "toHaggai: Unhandled markers were {}".format( unhandledMarkers ) )
            if Globals.verbosityLevel > 1:
                print( "  " + _("WARNING: Unhandled toHaggai markers were {}").format( unhandledMarkers ) )

        # Now create a zipped version
        filepath = os.path.join( outputFolder, filename )
        if Globals.verbosityLevel > 2: print( "  Zipping {} pickle file...".format( filename ) )
        zf = zipfile.ZipFile( filepath+'.zip', 'w', compression=zipfile.ZIP_DEFLATED )
        zf.write( filepath, filename )
        zf.close()

        if validationSchema: return xw.validate( validationSchema )
        return True
    # end of BibleWriter.toHaggaiXML



    def toOpenSongXML( self, outputFolder=None, controlDict=None, validationSchema=None ):
        """
        Using settings from the given control file,
            converts the USFM information to a UTF-8 OpenSong XML file.

        This format is roughly documented at http://de.wikipedia.org/wiki/OpenSong_XML
            but more fields can be discovered by looking at downloaded files.
        """
        if Globals.verbosityLevel > 1: print( "Running BibleWriter:toOpenSongXML..." )
        if Globals.debugFlag: assert( self.books )

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolder: outputFolder = "OutputFiles/BOS_OpenSong_Export/"
        if not os.access( outputFolder, os.F_OK ): os.makedirs( outputFolder ) # Make the empty folder if there wasn't already one there
        if not controlDict:
            controlDict, defaultControlFilename = {}, "To_OpenSong_controls.txt"
            try:
                ControlFiles.readControlFile( defaultControlFolder, defaultControlFilename, controlDict )
            except:
                logging.critical( "Unable to read control dict {} from {}".format( defaultControlFilename, defaultControlFolder ) )
        self.__adjustControlDict( controlDict )

        unhandledMarkers = set()

        def writeOpenSongBook( writerObject, BBB, bkData ):
            """Writes a book to the OpenSong XML writerObject."""
            #print( 'BIBLEBOOK', [('bnumber',Globals.BibleBooksCodes.getReferenceNumber(BBB)), ('bname',Globals.BibleBooksCodes.getEnglishName_NR(BBB)), ('bsname',Globals.BibleBooksCodes.getOSISAbbreviation(BBB))] )
            OSISAbbrev = Globals.BibleBooksCodes.getOSISAbbreviation( BBB )
            if not OSISAbbrev:
                logging.error( "toOpenSong: Can't write {} OpenSong book because no OSIS code available".format( BBB ) ); return
            writerObject.writeLineOpen( 'b', ('n',bkData.getAssumedBookNames()[0]) )
            haveOpenChapter, startedFlag, accumulator = False, False, ""
            C = V = "0"
            for verseDataEntry in bkData._processedLines: # Process internal Bible data lines
                marker, text, extras = verseDataEntry.getMarker(), verseDataEntry.getCleanText(), verseDataEntry.getExtras()
                #print( marker, repr(text) )
                #if text: assert( text[0] != ' ' )
                if marker in oftenIgnoredIntroMarkers: pass # Just ignore these lines
                elif marker in ( 's1', 's2', 's3', 's4', ): pass # Just ignore these section headings
                elif marker in ( 'r', ): pass # Just ignore these reference fields
                elif marker in ( 'p', 'q1','q2','q3','q4', 'm', 'b', 'nb', 'li1','li2','li3','li4', ): pass # Just ignore these paragraph formatting fields
                elif marker in ('v~', 'p~'):
                    if Globals.debugFlag: assert( text or extras )
                    if not text: # this is an empty (untranslated) verse
                        text = '- - -' # but we'll put in a filler
                    if startedFlag: accumulator += (' ' if accumulator else '') + Globals.makeSafeXML( text )
                elif marker == 'c':
                    if accumulator:
                        writerObject.writeLineOpenClose ( 'v', accumulator, ('n',verseNumberString) )
                        accumulator = ""
                    if haveOpenChapter:
                        writerObject.writeLineClose ( 'c' )
                    C, V = text, "0"
                    writerObject.writeLineOpen ( 'c', ('n',text) )
                    haveOpenChapter = True
                elif marker == 'v':
                    V = text
                    startedFlag = True
                    if accumulator:
                        writerObject.writeLineOpenClose ( 'v', accumulator, ('n',verseNumberString) )
                        accumulator = ""
                    #print( "Text '{}'".format( text ) )
                    if not text: logging.warning( "toOpenSongXML: Missing text for v" ); continue
                    verseNumberString = text.replace('<','').replace('>','').replace('"','') # Used below but remove anything that'll cause a big XML problem later
                elif marker not in ('c#',): # These are the markers that we can safely ignore for this export
                    if text:
                        logging.warning( "toOpenSong: lost text in {} field in {} {}:{} {}".format( marker, BBB, C, V, repr(text) ) )
                        #if Globals.debugFlag: halt
                    if extras:
                        logging.warning( "toOpenSong: lost extras in {} field in {} {}:{}".format( marker, BBB, C, V ) )
                        #if Globals.debugFlag: halt
                    unhandledMarkers.add( marker )
                if extras and marker not in ('v~','p~',): logging.critical( "toOpenSong: extras not handled for {} at {} {}:{}".format( marker, BBB, C, V ) )
            if accumulator:
                writerObject.writeLineOpenClose ( 'v', accumulator, ('n',verseNumberString) )
            if haveOpenChapter:
                writerObject.writeLineClose ( 'c' )
            writerObject.writeLineClose( 'b' )
        # end of toOpenSongXML.writeOpenSongBook

        # Set-up our Bible reference system
        if controlDict['PublicationCode'] == "GENERIC":
            BOS = self.genericBOS
            BRL = self.genericBRL
        else:
            BOS = BibleOrganizationalSystem( controlDict["PublicationCode"] )
            BRL = BibleReferenceList( BOS, BibleObject=None )

        if Globals.verbosityLevel > 2: print( _("  Exporting to OpenSong format...") )
        filename = Globals.makeSafeFilename( controlDict["OpenSongOutputFilename"] )
        xw = MLWriter( filename, outputFolder )
        xw.setHumanReadable()
        xw.start()
        xw.writeLineOpen( 'Bible' )
        for BBB,bookData in self.books.items():
            writeOpenSongBook( xw, BBB, bookData )
        xw.writeLineClose( 'Bible' )
        xw.close()

        if unhandledMarkers:
            logging.warning( "toOpenSongXML: Unhandled markers were {}".format( unhandledMarkers ) )
            if Globals.verbosityLevel > 1:
                print( "  " + _("WARNING: Unhandled toOpenSong markers were {}").format( unhandledMarkers ) )

        # Now create a zipped version
        filepath = os.path.join( outputFolder, filename )
        if Globals.verbosityLevel > 2: print( "  Zipping {} pickle file...".format( filename ) )
        zf = zipfile.ZipFile( filepath+'.zip', 'w', compression=zipfile.ZIP_DEFLATED )
        zf.write( filepath, filename )
        zf.close()

        if validationSchema: return xw.validate( validationSchema )
        return True
    # end of BibleWriter.toOpenSongXML



    def toUSXXML( self, outputFolder=None, controlDict=None, validationSchema=None ):
        """
        Using settings from the given control file,
            converts the USFM information to UTF-8 USX XML files.

        If a schema is given (either a path or URL), the XML output files are validated.
        """
        if Globals.verbosityLevel > 1: print( "Running BibleWriter:toUSXXML..." )
        if Globals.debugFlag: assert( self.books )

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolder: outputFolder = "OutputFiles/BOS_USX_Export/"
        #if not os.access( outputFolder, os.F_OK ): os.makedirs( outputFolder ) # Make the empty folder if there wasn't already one there
        filesFolder = os.path.join( outputFolder, "USXFiles/" )
        if not os.access( filesFolder, os.F_OK ): os.makedirs( filesFolder ) # Make the empty folder if there wasn't already one there
        if not controlDict:
            controlDict, defaultControlFilename = {}, "To_USX_controls.txt"
            try:
                ControlFiles.readControlFile( defaultControlFolder, defaultControlFilename, controlDict )
            except:
                logging.critical( "Unable to read control dict {} from {}".format( defaultControlFilename, defaultControlFolder ) )
        self.__adjustControlDict( controlDict )

        unhandledMarkers = set()

        def writeUSXBook( BBB, bkData ):
            """ Writes a book to the filesFolder. """

            def handleInternalTextMarkersForUSX( originalText ):
                """
                Handles character formatting markers within the originalText.
                Tries to find pairs of markers and replaces them with html char segments.
                """
                if '\\' not in originalText: return originalText
                if Globals.debugFlag and debuggingThisModule: print( "toUSXXML:hITM4USX:", BBB, C, V, marker, "'"+originalText+"'" )
                markerList = sorted( Globals.USFMMarkers.getMarkerListFromText( originalText ),
                                            key=lambda s: -len(s[4])) # Sort by longest characterContext first (maximum nesting)
                for insideMarker, iMIndex, nextSignificantChar, fullMarker, characterContext, endIndex, markerField in markerList: # check for internal markers
                    pass

                # Old code
                adjText = originalText
                haveOpenChar = False
                for charMarker in allCharMarkers:
                    #print( "handleInternalTextMarkersForUSX", charMarker )
                    # Handle USFM character markers
                    fullCharMarker = '\\' + charMarker + ' '
                    if fullCharMarker in adjText:
                        if haveOpenChar:
                            adjText = adjText.replace( 'CLOSED_BIT', ' closed="false"' ) # Fix up closed bit since it wasn't closed
                            logging.info( "toUSXXML: USX export had to close automatically in {} {}:{} {}:'{}' now '{}'".format( BBB, C, V, marker, originalText, adjText ) ) # The last marker presumably only had optional closing (or else we just messed up nesting markers)
                        adjText = adjText.replace( fullCharMarker, '{}<char style="{}"CLOSED_BIT>'.format( '</char>' if haveOpenChar else '', charMarker ) )
                        haveOpenChar = True
                    endCharMarker = '\\' + charMarker + '*'
                    if endCharMarker in adjText:
                        if not haveOpenChar: # Then we must have a missing open marker (or extra closing marker)
                            logging.error( "toUSXXML: Ignored extra '{}' closing marker in {} {}:{} {}:'{}' now '{}'".format( charMarker, BBB, C, V, marker, originalText, adjText ) )
                            adjText = adjText.replace( endCharMarker, '' ) # Remove the unused marker
                        else: # looks good
                            adjText = adjText.replace( 'CLOSED_BIT', '' ) # Fix up closed bit since it was specifically closed
                            adjText = adjText.replace( endCharMarker, '</char>' )
                            haveOpenChar = False
                if haveOpenChar:
                    adjText = adjText.replace( 'CLOSED_BIT', ' closed="false"' ) # Fix up closed bit since it wasn't closed
                    adjText += '{}</char>'.format( '' if adjText[-1]==' ' else ' ')
                    logging.info( "toUSXXML: Had to close automatically in {} {}:{} {}:'{}' now '{}'".format( BBB, C, V, marker, originalText, adjText ) )
                if '\\' in adjText: logging.critical( "toUSXXML: Didn't handle a backslash in {} {}:{} {}:'{}' now '{}'".format( BBB, C, V, marker, originalText, adjText ) )
                return adjText
            # end of toUSXXML.handleInternalTextMarkersForUSX

            def handleNotes( text, extras ):
                """ Integrate notes into the text again. """

                def processXRef( USXxref ):
                    """
                    Return the USX XML for the processed cross-reference (xref).

                    NOTE: The parameter here already has the /x and /x* removed.

                    \\x - \\xo 2:2: \\xt Lib 19:9-10; Diy 24:19.\\xt*\\x* (Backslashes are shown doubled here)
                        gives
                    <note style="x" caller="-"><char style="xo" closed="false">1:3: </char><char style="xt">2Kur 4:6.</char></note>
                    """
                    USXxrefXML = '<note ' if version>=2 else '<note style="x" '
                    xoOpen = xtOpen = False
                    for j,token in enumerate(USXxref.split('\\')):
                        #print( "toUSXXML:processXRef", j, "'"+token+"'", "from", '"'+USXxref+'"', xoOpen, xtOpen )
                        lcToken = token.lower()
                        if j==0: # The first token (but the x has already been removed)
                            USXxrefXML += ('caller="{}" style="x">' if version>=2 else 'caller="{}">') \
                                .format( token.rstrip() )
                        elif lcToken.startswith('xo '): # xref reference follows
                            if xoOpen: # We have multiple xo fields one after the other (probably an encoding error)
                                if Globals.debugFlag: assert( not xtOpen )
                                USXxrefXML += ' closed="false">' + adjToken + '</char>'
                                xoOpen = False
                            if xtOpen: # if we have multiple cross-references one after the other
                                USXxrefXML += ' closed="false">' + adjToken + '</char>'
                                xtOpen = False
                            adjToken = token[3:]
                            USXxrefXML += '<char style="xo"'
                            xoOpen = True
                        elif lcToken.startswith('xo*'):
                            if Globals.debugFlag: assert( xoOpen and not xtOpen )
                            USXxrefXML += '>' + adjToken + '</char>'
                            xoOpen = False
                        elif lcToken.startswith('xt '): # xref text follows
                            if xtOpen: # Multiple xt's in a row
                                if Globals.debugFlag: assert( not xoOpen )
                                USXxrefXML += ' closed="false">' + adjToken + '</char>'
                            if xoOpen:
                                USXxrefXML += ' closed="false">' + adjToken + '</char>'
                                xoOpen = False
                            adjToken = token[3:]
                            USXxrefXML += '<char style="xt"'
                            xtOpen = True
                        elif lcToken.startswith('xt*'):
                            if Globals.debugFlag: assert( xtOpen and not xoOpen )
                            USXxrefXML += '>' + adjToken + '</char>'
                            xtOpen = False
                        #elif lcToken in ('xo*','xt*','x*',):
                        #    pass # We're being lazy here and not checking closing markers properly
                        else:
                            logging.warning( _("toUSXXML: Unprocessed '{}' token in {} {}:{} xref '{}'").format( token, BBB, C, V, USXxref ) )
                    if xoOpen:
                        if Globals.debugFlag: assert( not xtOpen )
                        USXxrefXML += ' closed="false">' + adjToken + '</char>'
                        xoOpen = False
                    if xtOpen:
                        USXxrefXML += ' closed="false">' + adjToken + '</char>'
                    USXxrefXML += '</note>'
                    return USXxrefXML
                # end of toUSXXML.processXRef

                def processFootnote( USXfootnote ):
                    """
                    Return the USX XML for the processed footnote.

                    NOTE: The parameter here already has the /f and /f* removed.

                    \\f + \\fr 1:20 \\ft Su ka kaluwasan te Nawumi ‘keupianan,’ piru ka kaluwasan te Mara ‘masakit se geyinawa.’\\f* (Backslashes are shown doubled here)
                        gives
                    <note style="f" caller="+"><char style="fr" closed="false">2:23 </char><char style="ft">Te Hibruwanen: bayew egpekegsahid ka ngaran te “malitan” wey “lukes.”</char></note>
                    """
                    USXfootnoteXML = '<note style="f" '
                    frOpen = fTextOpen = fCharOpen = False
                    for j,token in enumerate(USXfootnote.split('\\')):
                        #print( "USX processFootnote", j, "'"+token+"'", frOpen, fTextOpen, fCharOpen, USXfootnote )
                        lcToken = token.lower()
                        if j==0:
                            USXfootnoteXML += 'caller="{}">'.format( token.rstrip() )
                        elif lcToken.startswith('fr '): # footnote reference follows
                            if frOpen:
                                if Globals.debugFlag: assert( not fTextOpen )
                                logging.error( _("toUSXXML: Two consecutive fr fields in {} {}:{} footnote '{}'").format( token, BBB, C, V, USXfootnote ) )
                            if fTextOpen:
                                if Globals.debugFlag: assert( not frOpen )
                                USXfootnoteXML += ' closed="false">' + adjToken + '</char>'
                                fTextOpen = False
                            if Globals.debugFlag: assert( not fCharOpen )
                            adjToken = token[3:]
                            USXfootnoteXML += '<char style="fr"'
                            frOpen = True
                        elif lcToken.startswith('fr* '):
                            if Globals.debugFlag: assert( frOpen and not fTextOpen and not fCharOpen )
                            USXfootnoteXML += '>' + adjToken + '</char>'
                            frOpen = False
                        elif lcToken.startswith('ft ') or lcToken.startswith('fq ') or lcToken.startswith('fqa ') or lcToken.startswith('fv ') or lcToken.startswith('fk '):
                            if fCharOpen:
                                if Globals.debugFlag: assert( not frOpen )
                                USXfootnoteXML += '>' + adjToken + '</char>'
                                fCharOpen = False
                            if frOpen:
                                if Globals.debugFlag: assert( not fTextOpen )
                                USXfootnoteXML += ' closed="false">' + adjToken + '</char>'
                                frOpen = False
                            if fTextOpen:
                                USXfootnoteXML += ' closed="false">' + adjToken + '</char>'
                                fTextOpen = False
                            fMarker = lcToken.split()[0] # Get the bit before the space
                            USXfootnoteXML += '<char style="{}"'.format( fMarker )
                            adjToken = token[len(fMarker)+1:] # Get the bit after the space
                            #print( "'{}' '{}'".format( fMarker, adjToken ) )
                            fTextOpen = True
                        elif lcToken.startswith('ft*') or lcToken.startswith('fq*') or lcToken.startswith('fqa*') or lcToken.startswith('fv*') or lcToken.startswith('fk*'):
                            if Globals.debugFlag: assert( fTextOpen and not frOpen and not fCharOpen )
                            USXfootnoteXML += '>' + adjToken + '</char>'
                            fTextOpen = False
                        else: # Could be character formatting (or closing of character formatting)
                            subTokens = lcToken.split()
                            firstToken = subTokens[0]
                            #print( "ft", firstToken )
                            if firstToken in allCharMarkers: # Yes, confirmed
                                if fCharOpen: # assume that the last one is closed by this one
                                    if Globals.debugFlag: assert( not frOpen )
                                    USXfootnoteXML += '>' + adjToken + '</char>'
                                    fCharOpen = False
                                if frOpen:
                                    if Globals.debugFlag: assert( not fCharOpen )
                                    USXfootnoteXML += ' closed="false">' + adjToken + '</char>'
                                    frOpen = False
                                USXfootnoteXML += '<char style="{}"'.format( firstToken )
                                adjToken = token[len(firstToken)+1:] # Get the bit after the space
                                fCharOpen = firstToken
                            else: # The problem is that a closing marker doesn't have to be followed by a space
                                if firstToken[-1]=='*' and firstToken[:-1] in allCharMarkers: # it's a closing tag (that was followed by a space)
                                    if fCharOpen:
                                        if Globals.debugFlag: assert( not frOpen )
                                        if not firstToken.startswith( fCharOpen+'*' ): # It's not a matching tag
                                            logging.warning( _("toUSXXML: '{}' closing tag doesn't match '{}' in {} {}:{} footnote '{}'").format( firstToken, fCharOpen, BBB, C, V, USXfootnote ) )
                                        USXfootnoteXML += '>' + adjToken + '</char>'
                                        fCharOpen = False
                                    logging.warning( _("toUSXXML: '{}' closing tag doesn't match in {} {}:{} footnote '{}'").format( firstToken, BBB, C, V, USXfootnote ) )
                                else:
                                    ixAS = firstToken.find( '*' )
                                    #print( firstToken, ixAS, firstToken[:ixAS] if ixAS!=-1 else '' )
                                    if ixAS!=-1 and ixAS<4 and firstToken[:ixAS] in allCharMarkers: # it's a closing tag
                                        if fCharOpen:
                                            if Globals.debugFlag: assert( not frOpen )
                                            if not firstToken.startswith( fCharOpen+'*' ): # It's not a matching tag
                                                logging.warning( _("toUSXXML: '{}' closing tag doesn't match '{}' in {} {}:{} footnote '{}'").format( firstToken, fCharOpen, BBB, C, V, USXfootnote ) )
                                            USXfootnoteXML += '>' + adjToken + '</char>'
                                            fCharOpen = False
                                        logging.warning( _("toUSXXML: '{}' closing tag doesn't match in {} {}:{} footnote '{}'").format( firstToken, BBB, C, V, USXfootnote ) )
                                    else:
                                        logging.warning( _("toUSXXML: Unprocessed '{}' token in {} {}:{} footnote '{}'").format( firstToken, BBB, C, V, USXfootnote ) )
                                        #print( allCharMarkers )
                                        #halt
                    #print( "  ", frOpen, fCharOpen, fTextOpen )
                    if frOpen:
                        logging.warning( _("toUSXXML: Unclosed 'fr' token in {} {}:{} footnote '{}'").format( BBB, C, V, USXfootnote) )
                        if Globals.debugFlag: assert( not fCharOpen and not fTextOpen )
                        USXfootnoteXML += ' closed="false">' + adjToken + '</char>'
                    if fCharOpen: logging.warning( _("toUSXXML: Unclosed '{}' token in {} {}:{} footnote '{}'").format( fCharOpen, BBB, C, V, USXfootnote) )
                    if fTextOpen: USXfootnoteXML += ' closed="false">' + adjToken + '</char>'
                    USXfootnoteXML += '</note>'
                    #print( '', USXfootnote, USXfootnoteXML )
                    #if BBB=='EXO' and C=='17' and V=='7': halt
                    return USXfootnoteXML
                # end of toUSXXML.processFootnote


                adjText = text
                offset = 0
                for extraType, extraIndex, extraText, cleanExtraText in extras: # do any footnotes and cross-references
                    #print( "{} {}:{} Text='{}' eT={}, eI={}, eText='{}'".format( BBB, C, V, text, extraType, extraIndex, extraText ) )
                    adjIndex = extraIndex - offset
                    lenT = len( adjText )
                    if adjIndex > lenT: # This can happen if we have verse/space/notes at end (and the space was deleted after the note was separated off)
                        logging.warning( _("toUSXXML: Space before note at end of verse in {} {}:{} has been lost").format( BBB, C, V ) )
                        # No need to adjust adjIndex because the code below still works
                    elif adjIndex<0 or adjIndex>lenT: # The extras don't appear to fit correctly inside the text
                        print( "toUSXXML: Extras don't fit inside verse at {} {}:{}: eI={} o={} len={} aI={}".format( BBB, C, V, extraIndex, offset, len(text), adjIndex ) )
                        print( "  Verse='{}'".format( text ) )
                        print( "  Extras='{}'".format( extras ) )
                    #assert( 0 <= adjIndex <= len(verse) )
                    #adjText = checkText( extraText, checkLeftovers=False ) # do any general character formatting
                    #if adjText!=extraText: print( "processXRefsAndFootnotes: {}@{}-{}={} '{}' now '{}'".format( extraType, extraIndex, offset, adjIndex, extraText, adjText ) )
                    if extraType == 'fn':
                        extra = processFootnote( extraText )
                        #print( "fn got", extra )
                    elif extraType == 'xr':
                        extra = processXRef( extraText )
                        #print( "xr got", extra )
                    elif extraType == 'fig':
                        logging.critical( "USXXML figure not handled yet" )
                        extra = "" # temp
                        #extra = processFigure( extraText )
                        #print( "fig got", extra )
                    elif Globals.debugFlag and debuggingThisModule: print( extraType ); halt
                    #print( "was", verse )
                    adjText = adjText[:adjIndex] + extra + adjText[adjIndex:]
                    offset -= len( extra )
                    #print( "now", verse )
                return adjText
            # end of toUSXXML.handleNotes

            USXAbbrev = Globals.BibleBooksCodes.getUSFMAbbreviation( BBB ).upper()
            USXNumber = Globals.BibleBooksCodes.getUSXNumber( BBB )
            if not USXAbbrev: logging.error( "toUSXXML: Can't write {} USX book because no USFM code available".format( BBB ) ); return
            if not USXNumber: logging.error( "toUSXXML: Can't write {} USX book because no USX number available".format( BBB ) ); return

            version = 2
            xtra = ' ' if version<2 else ''
            C = V = '0'
            xw = MLWriter( Globals.makeSafeFilename( USXNumber+USXAbbrev+".usx" ), filesFolder )
            xw.setHumanReadable()
            xw.spaceBeforeSelfcloseTag = True
            xw.start( lineEndings='w', writeBOM=True ) # Try to imitate Paratext output as closely as possible
            xw.writeLineOpen( 'usx', ('version','2.0') ) if version>=2 else xw.writeLineOpen( 'usx' )
            haveOpenPara = paraJustOpened = False
            for verseDataEntry in bkData._processedLines: # Process internal Bible data lines
                marker, originalMarker, text, extras = verseDataEntry.getMarker(), verseDataEntry.getOriginalMarker(), verseDataEntry.getAdjustedText(), verseDataEntry.getExtras()
                markerShouldHaveContent = Globals.USFMMarkers.markerShouldHaveContent( marker )
                #print( BBB, C, V, marker, markerShouldHaveContent, haveOpenPara, paraJustOpened )
                adjText = handleNotes( text, extras )
                if marker == 'id':
                    if haveOpenPara: # This should never happen coz the ID line should have been the first line in the file
                        logging.error( "toUSXXML: Book {}{} has a id line inside an open paragraph: '{}'".format( BBB, " ({})".format(USXAbbrev) if USXAbbrev!=BBB else '', adjText ) )
                        xw.removeFinalNewline( True )
                        xw.writeLineClose( 'para' )
                        haveOpenPara = False
                    adjTxLen = len( adjText )
                    if adjTxLen<3 or (adjTxLen>3 and adjText[3]!=' '): # Doesn't seem to have a standard BBB at the beginning of the ID line
                        logging.warning( "toUSXXML: Book {}{} has a non-standard id line: '{}'".format( BBB, " ({})".format(USXAbbrev) if USXAbbrev!=BBB else '', adjText ) )
                    if adjText[0:3] != USXAbbrev:
                        logging.error( "toUSXXML: Book {}{} might be incorrect -- we got: '{}'".format( BBB, " ({})".format(USXAbbrev) if USXAbbrev!=BBB else '', adjText[0:3] ) )
                    adjText = adjText[4:] # Remove the book code from the ID line because it's put in as an attribute
                    if adjText: xw.writeLineOpenClose( 'book', handleInternalTextMarkersForUSX(adjText)+xtra, [('code',USXAbbrev),('style',marker)] )
                    elif not text: logging.error( "toUSXXML: {} {}:{} has a blank id line that was ignored".format( BBB, C, V ) )
                elif marker == 'c':
                    if haveOpenPara:
                        xw.removeFinalNewline( True )
                        xw.writeLineClose( 'para' )
                        haveOpenPara = False
                    #print( BBB, 'C', repr(text), repr(adjText) )
                    C = text # not adjText!
                    xw.writeLineOpenSelfclose ( 'chapter', [('number',C),('style','c')] )
                    if adjText != text:
                        logging.warning( "toUSXXML: Lost additional note text on c for {} {}".format( BBB, repr(C) ) )
                elif marker == 'c~': # Don't really know what this stuff is!!!
                    if not adjText: logging.warning( "toUSXXML: Missing text for c~" ); continue
                    # TODO: We haven't stripped out character fields from within the text -- not sure how USX handles them yet
                    xw.removeFinalNewline( True )
                    xw.writeLineText( handleInternalTextMarkersForUSX(adjText)+xtra, noTextCheck=True ) # no checks coz might already have embedded XML
                elif marker == 'c#': # Chapter number added for printing
                    pass # Just ignore it completely
                elif marker == 'v':
                    V = adjText.replace('<','').replace('>','').replace('"','') # Used below but remove anything that'll cause a big XML problem later
                    if paraJustOpened: paraJustOpened = False
                    else:
                        xw.removeFinalNewline( True )
                        if version>=2: xw._writeToBuffer( ' ' ) # Space between verses
                    xw.writeLineOpenSelfclose ( 'verse', [('number',V),('style','v')] )
                elif marker in ('v~','p~',):
                    if not adjText: logging.warning( "toUSXXML: Missing text for {}".format( marker ) ); continue
                    # TODO: We haven't stripped out character fields from within the verse -- not sure how USX handles them yet
                    xw.removeFinalNewline( True )
                    xw.writeLineText( handleInternalTextMarkersForUSX(adjText)+xtra, noTextCheck=True ) # no checks coz might already have embedded XML
                elif markerShouldHaveContent == 'N': # N = never, e.g., b, nb
                    if haveOpenPara:
                        xw.removeFinalNewline( True )
                        xw.writeLineClose( 'para' )
                        haveOpenPara = False
                    if adjText: logging.error( "toUSXXML: {} {}:{} has a {} line containing text ('{}') that was ignored".format( BBB, C, V, originalMarker, adjText ) )
                    xw.writeLineOpenSelfclose ( 'para', ('style',marker) )
                elif markerShouldHaveContent == 'S': # S = sometimes, e.g., p,pi,q,q1,q2,q3,q4,m
                    if haveOpenPara:
                        xw.removeFinalNewline( True )
                        xw.writeLineClose( 'para' )
                        haveOpenPara = False
                    if not adjText: xw.writeLineOpen( 'para', ('style',originalMarker) )
                    else: xw.writeLineOpenText( 'para', handleInternalTextMarkersForUSX(adjText)+xtra, ('style',originalMarker), noTextCheck=True ) # no checks coz might already have embedded XML
                    haveOpenPara = paraJustOpened = True
                else:
                    #assert( markerShouldHaveContent == 'A' ) # A = always, e.g.,  ide, mt, h, s, ip, etc.
                    if markerShouldHaveContent != 'A':
                        logging.debug( "BibleWriter.toUSXXML: ToProgrammer -- should be 'A': '{}' is '{}' Why?".format( marker, markerShouldHaveContent ) )
                    if haveOpenPara:
                        xw.removeFinalNewline( True )
                        xw.writeLineClose( 'para' )
                        haveOpenPara = False
                    if 1 or adjText: xw.writeLineOpenClose( 'para', handleInternalTextMarkersForUSX(adjText)+xtra, ('style',originalMarker), noTextCheck=True ) # no checks coz might already have embedded XML
                    else: logging.info( "toUSXXML: {} {}:{} has a blank {} line that was ignored".format( BBB, C, V, originalMarker ) )
            if haveOpenPara:
                xw.removeFinalNewline( True )
                xw.writeLineClose( 'para' )
            xw.writeLineClose( 'usx' )
            xw.close( writeFinalNL=True ) # Try to imitate Paratext output as closely as possible
            if validationSchema: return xw.validate( validationSchema )
        # end of toUSXXML.writeUSXBook

        # Set-up our Bible reference system
        if controlDict['PublicationCode'] == "GENERIC":
            BOS = self.genericBOS
            BRL = self.genericBRL
        else:
            BOS = BibleOrganizationalSystem( controlDict["PublicationCode"] )
            BRL = BibleReferenceList( BOS, BibleObject=None )

        if Globals.verbosityLevel > 2: print( _("  Exporting to USX format...") )
        #USXOutputFolder = os.path.join( "OutputFiles/", "USX output/" )
        #if not os.access( USXOutputFolder, os.F_OK ): os.mkdir( USXOutputFolder ) # Make the empty folder if there wasn't already one there

        validationResults = ( 0, '', '', ) # xmllint result code, program output, error output
        for BBB,bookData in self.books.items():
            bookResults = writeUSXBook( BBB, bookData )
            if validationSchema:
                if bookResults[0] > validationResults[0]: validationResults = ( bookResults[0], validationResults[1], validationResults[2], )
                if bookResults[1]: validationResults = ( validationResults[0], validationResults[1] + bookResults[1], validationResults[2], )
                if bookResults[2]: validationResults = ( validationResults[0], validationResults[1], validationResults[2] + bookResults[2], )
        if unhandledMarkers:
            logging.error( "toUSXXML: Unhandled markers were {}".format( unhandledMarkers ) )
            if Globals.verbosityLevel > 1:
                print( "  " + _("ERROR: Unhandled toUSX markers were {}").format( unhandledMarkers ) )

        # Now create a zipped collection
        if Globals.verbosityLevel > 2: print( "  Zipping USX files..." )
        zf = zipfile.ZipFile( os.path.join( outputFolder, 'AllUSXFiles.zip' ), 'w', compression=zipfile.ZIP_DEFLATED )
        for filename in os.listdir( filesFolder ):
            #if not filename.endswith( '.zip' ):
            filepath = os.path.join( filesFolder, filename )
            zf.write( filepath, filename ) # Save in the archive without the path
        zf.close()
        # Now create the gzipped file
        if Globals.verbosityLevel > 2: print( "  GZipping USX files..." )
        tar = tarfile.open( os.path.join( outputFolder, 'AllUSXFiles.qz' ), 'w:gz' )
        for filename in os.listdir( filesFolder ):
            filepath = os.path.join( filesFolder, filename )
            tar.add( filepath, filename )
        tar.close()

        if validationSchema: return validationResults
        return True
    # end of BibleWriter.toUSXXML



    def toUSFXXML( self, outputFolder=None, controlDict=None, validationSchema=None ):
        """
        Using settings from the given control file,
            converts the USFM information to UTF-8 USFX XML files.

        If a schema is given (either a path or URL), the XML output files are validated.
        """
        if Globals.verbosityLevel > 1: print( "Running BibleWriter:toUSFXXML..." )
        if Globals.debugFlag: assert( self.books )

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolder: outputFolder = "OutputFiles/BOS_USFX_Export/"
        if not os.access( outputFolder, os.F_OK ): os.makedirs( outputFolder ) # Make the empty folder if there wasn't already one there
        if not controlDict:
            controlDict, defaultControlFilename = {}, "To_USFX_controls.txt"
            try:
                ControlFiles.readControlFile( defaultControlFolder, defaultControlFilename, controlDict )
            except:
                logging.critical( "Unable to read control dict {} from {}".format( defaultControlFilename, defaultControlFolder ) )
        self.__adjustControlDict( controlDict )

        unhandledMarkers = set()

        def writeUSFXBook( xw, BBB, bkData ):
            """ Writes a book to the given USFX XML writerObject. """

            def handleInternalTextMarkersForUSFX( originalText ):
                """
                Handles character formatting markers within the originalText.
                Tries to find pairs of markers and replaces them with html char segments.
                """
                if '\\' not in originalText: return originalText
                if Globals.debugFlag and debuggingThisModule: print( "toUSFXXML:hITM4USFX:", BBB, C, V, marker, "'"+originalText+"'" )
                markerList = sorted( Globals.USFMMarkers.getMarkerListFromText( originalText ),
                                            key=lambda s: -len(s[4])) # Sort by longest characterContext first (maximum nesting)
                for insideMarker, iMIndex, nextSignificantChar, fullMarker, characterContext, endIndex, markerField in markerList: # check for internal markers
                    pass

                # Old code
                adjText = originalText
                haveOpenChar = False
                for charMarker in allCharMarkers:
                    #print( "handleInternalTextMarkersForUSFX", charMarker )
                    # Handle USFM character markers
                    fullCharMarker = '\\' + charMarker + ' '
                    if fullCharMarker in adjText:
                        if haveOpenChar:
                            adjText = adjText.replace( 'CLOSED_BIT', ' closed="false"' ) # Fix up closed bit since it wasn't closed
                            logging.info( "toUSFXXML: USFX export had to close automatically in {} {}:{} {}:'{}' now '{}'".format( BBB, C, V, marker, originalText, adjText ) ) # The last marker presumably only had optional closing (or else we just messed up nesting markers)
                        adjText = adjText.replace( fullCharMarker, '{}<char style="{}"CLOSED_BIT>'.format( '</char>' if haveOpenChar else '', charMarker ) )
                        haveOpenChar = True
                    endCharMarker = '\\' + charMarker + '*'
                    if endCharMarker in adjText:
                        if not haveOpenChar: # Then we must have a missing open marker (or extra closing marker)
                            logging.error( "toUSFXXML: Ignored extra '{}' closing marker in {} {}:{} {}:'{}' now '{}'".format( charMarker, BBB, C, V, marker, originalText, adjText ) )
                            adjText = adjText.replace( endCharMarker, '' ) # Remove the unused marker
                        else: # looks good
                            adjText = adjText.replace( 'CLOSED_BIT', '' ) # Fix up closed bit since it was specifically closed
                            adjText = adjText.replace( endCharMarker, '</char>' )
                            haveOpenChar = False
                if haveOpenChar:
                    adjText = adjText.replace( 'CLOSED_BIT', ' closed="false"' ) # Fix up closed bit since it wasn't closed
                    adjText += '{}</char>'.format( '' if adjText[-1]==' ' else ' ')
                    logging.info( "toUSFXXML: Had to close automatically in {} {}:{} {}:'{}' now '{}'".format( BBB, C, V, marker, originalText, adjText ) )
                if '\\' in adjText: logging.critical( "toUSFXXML: Didn't handle a backslash in {} {}:{} {}:'{}' now '{}'".format( BBB, C, V, marker, originalText, adjText ) )
                return adjText
            # end of toUSFXXML.handleInternalTextMarkersForUSFX

            def handleNotes( text, extras ):
                """ Integrate notes into the text again. """

                def processXRef( USFXxref ):
                    """
                    Return the USFX XML for the processed cross-reference (xref).

                    NOTE: The parameter here already has the /x and /x* removed.

                    \\x - \\xo 2:2: \\xt Lib 19:9-10; Diy 24:19.\\xt*\\x* (Backslashes are shown doubled here)
                        gives
                    <note style="x" caller="-"><char style="xo" closed="false">1:3: </char><char style="xt">2Kur 4:6.</char></note>
                    """
                    USFXxrefXML = '<x '
                    xoOpen = xtOpen = False
                    for j,token in enumerate(USFXxref.split('\\')):
                        #print( "toUSFXXML:processXRef", j, "'"+token+"'", "from", '"'+USFXxref+'"', xoOpen, xtOpen )
                        lcToken = token.lower()
                        if j==0: # The first token (but the x has already been removed)
                            USFXxrefXML += ('caller="{}" style="x">' if version>=2 else 'caller="{}">') \
                                .format( token.rstrip() )
                        elif lcToken.startswith('xo '): # xref reference follows
                            if xoOpen: # We have multiple xo fields one after the other (probably an encoding error)
                                if Globals.debugFlag: assert( not xtOpen )
                                USFXxrefXML += ' closed="false">' + adjToken + '</char>'
                                xoOpen = False
                            if xtOpen: # if we have multiple cross-references one after the other
                                USFXxrefXML += ' closed="false">' + adjToken + '</char>'
                                xtOpen = False
                            adjToken = token[3:]
                            USFXxrefXML += '<char style="xo"'
                            xoOpen = True
                        elif lcToken.startswith('xo*'):
                            if Globals.debugFlag: assert( xoOpen and not xtOpen )
                            USFXxrefXML += '>' + adjToken + '</char>'
                            xoOpen = False
                        elif lcToken.startswith('xt '): # xref text follows
                            if xtOpen: # Multiple xt's in a row
                                if Globals.debugFlag: assert( not xoOpen )
                                USFXxrefXML += ' closed="false">' + adjToken + '</char>'
                            if xoOpen:
                                USFXxrefXML += ' closed="false">' + adjToken + '</char>'
                                xoOpen = False
                            adjToken = token[3:]
                            USFXxrefXML += '<char style="xt"'
                            xtOpen = True
                        elif lcToken.startswith('xt*'):
                            if Globals.debugFlag: assert( xtOpen and not xoOpen )
                            USFXxrefXML += '>' + adjToken + '</char>'
                            xtOpen = False
                        #elif lcToken in ('xo*','xt*','x*',):
                        #    pass # We're being lazy here and not checking closing markers properly
                        else:
                            logging.warning( _("toUSFXXML: Unprocessed '{}' token in {} {}:{} xref '{}'").format( token, BBB, C, V, USFXxref ) )
                    if xoOpen:
                        if Globals.debugFlag: assert( not xtOpen )
                        USFXxrefXML += ' closed="false">' + adjToken + '</char>'
                        xoOpen = False
                    if xtOpen:
                        USFXxrefXML += ' closed="false">' + adjToken + '</char>'
                    USFXxrefXML += '</x>'
                    return USFXxrefXML
                # end of toUSFXXML.processXRef

                def processFootnote( USFXfootnote ):
                    """
                    Return the USFX XML for the processed footnote.

                    NOTE: The parameter here already has the /f and /f* removed.

                    \\f + \\fr 1:20 \\ft Su ka kaluwasan te Nawumi ‘keupianan,’ piru ka kaluwasan te Mara ‘masakit se geyinawa.’\\f* (Backslashes are shown doubled here)
                        gives
                    <note style="f" caller="+"><char style="fr" closed="false">2:23 </char><char style="ft">Te Hibruwanen: bayew egpekegsahid ka ngaran te “malitan” wey “lukes.”</char></note>
                    """
                    USFXfootnoteXML = '<f '
                    frOpen = fTextOpen = fCharOpen = False
                    for j,token in enumerate(USFXfootnote.split('\\')):
                        #print( "USFX processFootnote", j, "'"+token+"'", frOpen, fTextOpen, fCharOpen, USFXfootnote )
                        lcToken = token.lower()
                        if j==0:
                            USFXfootnoteXML += 'caller="{}">'.format( token.rstrip() )
                        elif lcToken.startswith('fr '): # footnote reference follows
                            if frOpen:
                                if Globals.debugFlag: assert( not fTextOpen )
                                logging.error( _("toUSFXXML: Two consecutive fr fields in {} {}:{} footnote '{}'").format( token, BBB, C, V, USFXfootnote ) )
                            if fTextOpen:
                                if Globals.debugFlag: assert( not frOpen )
                                USFXfootnoteXML += ' closed="false">' + adjToken + '</char>'
                                fTextOpen = False
                            if Globals.debugFlag: assert( not fCharOpen )
                            adjToken = token[3:]
                            USFXfootnoteXML += '<char style="fr"'
                            frOpen = True
                        elif lcToken.startswith('fr* '):
                            if Globals.debugFlag: assert( frOpen and not fTextOpen and not fCharOpen )
                            USFXfootnoteXML += '>' + adjToken + '</char>'
                            frOpen = False
                        elif lcToken.startswith('ft ') or lcToken.startswith('fq ') or lcToken.startswith('fqa ') or lcToken.startswith('fv ') or lcToken.startswith('fk '):
                            if fCharOpen:
                                if Globals.debugFlag: assert( not frOpen )
                                USFXfootnoteXML += '>' + adjToken + '</char>'
                                fCharOpen = False
                            if frOpen:
                                if Globals.debugFlag: assert( not fTextOpen )
                                USFXfootnoteXML += ' closed="false">' + adjToken + '</char>'
                                frOpen = False
                            if fTextOpen:
                                USFXfootnoteXML += ' closed="false">' + adjToken + '</char>'
                                fTextOpen = False
                            fMarker = lcToken.split()[0] # Get the bit before the space
                            USFXfootnoteXML += '<char style="{}"'.format( fMarker )
                            adjToken = token[len(fMarker)+1:] # Get the bit after the space
                            #print( "'{}' '{}'".format( fMarker, adjToken ) )
                            fTextOpen = True
                        elif lcToken.startswith('ft*') or lcToken.startswith('fq*') or lcToken.startswith('fqa*') or lcToken.startswith('fv*') or lcToken.startswith('fk*'):
                            if Globals.debugFlag: assert( fTextOpen and not frOpen and not fCharOpen )
                            USFXfootnoteXML += '>' + adjToken + '</char>'
                            fTextOpen = False
                        else: # Could be character formatting (or closing of character formatting)
                            subTokens = lcToken.split()
                            firstToken = subTokens[0]
                            #print( "ft", firstToken )
                            if firstToken in allCharMarkers: # Yes, confirmed
                                if fCharOpen: # assume that the last one is closed by this one
                                    if Globals.debugFlag: assert( not frOpen )
                                    USFXfootnoteXML += '>' + adjToken + '</char>'
                                    fCharOpen = False
                                if frOpen:
                                    if Globals.debugFlag: assert( not fCharOpen )
                                    USFXfootnoteXML += ' closed="false">' + adjToken + '</char>'
                                    frOpen = False
                                USFXfootnoteXML += '<char style="{}"'.format( firstToken )
                                adjToken = token[len(firstToken)+1:] # Get the bit after the space
                                fCharOpen = firstToken
                            else: # The problem is that a closing marker doesn't have to be followed by a space
                                if firstToken[-1]=='*' and firstToken[:-1] in allCharMarkers: # it's a closing tag (that was followed by a space)
                                    if fCharOpen:
                                        if Globals.debugFlag: assert( not frOpen )
                                        if not firstToken.startswith( fCharOpen+'*' ): # It's not a matching tag
                                            logging.warning( _("toUSFXXML: '{}' closing tag doesn't match '{}' in {} {}:{} footnote '{}'").format( firstToken, fCharOpen, BBB, C, V, USFXfootnote ) )
                                        USFXfootnoteXML += '>' + adjToken + '</char>'
                                        fCharOpen = False
                                    logging.warning( _("toUSFXXML: '{}' closing tag doesn't match in {} {}:{} footnote '{}'").format( firstToken, BBB, C, V, USFXfootnote ) )
                                else:
                                    ixAS = firstToken.find( '*' )
                                    #print( firstToken, ixAS, firstToken[:ixAS] if ixAS!=-1 else '' )
                                    if ixAS!=-1 and ixAS<4 and firstToken[:ixAS] in allCharMarkers: # it's a closing tag
                                        if fCharOpen:
                                            if Globals.debugFlag: assert( not frOpen )
                                            if not firstToken.startswith( fCharOpen+'*' ): # It's not a matching tag
                                                logging.warning( _("toUSFXXML: '{}' closing tag doesn't match '{}' in {} {}:{} footnote '{}'").format( firstToken, fCharOpen, BBB, C, V, USFXfootnote ) )
                                            USFXfootnoteXML += '>' + adjToken + '</char>'
                                            fCharOpen = False
                                        logging.warning( _("toUSFXXML: '{}' closing tag doesn't match in {} {}:{} footnote '{}'").format( firstToken, BBB, C, V, USFXfootnote ) )
                                    else:
                                        logging.warning( _("toUSFXXML: Unprocessed '{}' token in {} {}:{} footnote '{}'").format( firstToken, BBB, C, V, USFXfootnote ) )
                                        #print( allCharMarkers )
                                        #halt
                    #print( "  ", frOpen, fCharOpen, fTextOpen )
                    if frOpen:
                        logging.warning( _("toUSFXXML: Unclosed 'fr' token in {} {}:{} footnote '{}'").format( BBB, C, V, USFXfootnote) )
                        if Globals.debugFlag: assert( not fCharOpen and not fTextOpen )
                        USFXfootnoteXML += ' closed="false">' + adjToken + '</char>'
                    if fCharOpen: logging.warning( _("toUSFXXML: Unclosed '{}' token in {} {}:{} footnote '{}'").format( fCharOpen, BBB, C, V, USFXfootnote) )
                    if fTextOpen: USFXfootnoteXML += ' closed="false">' + adjToken + '</char>'
                    USFXfootnoteXML += '</f>'
                    #print( '', USFXfootnote, USFXfootnoteXML )
                    #if BBB=='EXO' and C=='17' and V=='7': halt
                    return USFXfootnoteXML
                # end of toUSFXXML.processFootnote


                adjText = text
                offset = 0
                for extraType, extraIndex, extraText, cleanExtraText in extras: # do any footnotes and cross-references
                    #print( "{} {}:{} Text='{}' eT={}, eI={}, eText='{}'".format( BBB, C, V, text, extraType, extraIndex, extraText ) )
                    adjIndex = extraIndex - offset
                    lenT = len( adjText )
                    if adjIndex > lenT: # This can happen if we have verse/space/notes at end (and the space was deleted after the note was separated off)
                        logging.warning( _("toUSFXXML: Space before note at end of verse in {} {}:{} has been lost").format( BBB, C, V ) )
                        # No need to adjust adjIndex because the code below still works
                    elif adjIndex<0 or adjIndex>lenT: # The extras don't appear to fit correctly inside the text
                        print( "toUSFXXML: Extras don't fit inside verse at {} {}:{}: eI={} o={} len={} aI={}".format( BBB, C, V, extraIndex, offset, len(text), adjIndex ) )
                        print( "  Verse='{}'".format( text ) )
                        print( "  Extras='{}'".format( extras ) )
                    #assert( 0 <= adjIndex <= len(verse) )
                    #adjText = checkText( extraText, checkLeftovers=False ) # do any general character formatting
                    #if adjText!=extraText: print( "processXRefsAndFootnotes: {}@{}-{}={} '{}' now '{}'".format( extraType, extraIndex, offset, adjIndex, extraText, adjText ) )
                    if extraType == 'fn':
                        extra = processFootnote( extraText )
                        #print( "fn got", extra )
                    elif extraType == 'xr':
                        extra = processXRef( extraText )
                        #print( "xr got", extra )
                    elif extraType == 'fig':
                        logging.critical( "USXFXML figure not handled yet" )
                        extra = "" # temp
                        #extra = processFigure( extraText )
                        #print( "fig got", extra )
                    elif Globals.debugFlag and debuggingThisModule: print( extraType ); halt
                    #print( "was", verse )
                    adjText = adjText[:adjIndex] + extra + adjText[adjIndex:]
                    offset -= len( extra )
                    #print( "now", verse )
                return adjText
            # end of toUSFXXML.handleNotes

            USFXAbbrev = Globals.BibleBooksCodes.getUSFMAbbreviation( BBB ).upper()
            #USFXNumber = Globals.BibleBooksCodes.getUSFMNumber( BBB )
            if not USFXAbbrev: logging.error( "toUSFXXML: Can't write {} USFX book because no USFM code available".format( BBB ) ); return
            #if not USFXNumber: logging.error( "toUSFXXML: Can't write {} USFX book because no USFX number available".format( BBB ) ); return

            version = 2
            xtra = ' ' if version<2 else ''
            C = V = '0'
            xw.writeLineOpen( 'book', ('id',USFXAbbrev) )
            haveOpenPara = paraJustOpened = False
            for verseDataEntry in bkData._processedLines: # Process internal Bible data lines
                marker, originalMarker, text, extras = verseDataEntry.getMarker(), verseDataEntry.getOriginalMarker(), verseDataEntry.getAdjustedText(), verseDataEntry.getExtras()
                markerShouldHaveContent = Globals.USFMMarkers.markerShouldHaveContent( marker )
                #print( BBB, C, V, marker, markerShouldHaveContent, haveOpenPara, paraJustOpened )
                adjText = handleNotes( text, extras )
                if marker == 'id':
                    if haveOpenPara: # This should never happen coz the ID line should have been the first line in the file
                        logging.error( "toUSFXXML: Book {}{} has a id line inside an open paragraph: '{}'".format( BBB, " ({})".format(USFXAbbrev) if USFXAbbrev!=BBB else '', adjText ) )
                        xw.removeFinalNewline( True )
                        xw.writeLineClose( 'p' )
                        haveOpenPara = False
                    adjTxLen = len( adjText )
                    if adjTxLen<3 or (adjTxLen>3 and adjText[3]!=' '): # Doesn't seem to have a standard BBB at the beginning of the ID line
                        logging.warning( "toUSFXXML: Book {}{} has a non-standard id line: '{}'".format( BBB, " ({})".format(USFXAbbrev) if USFXAbbrev!=BBB else '', adjText ) )
                    if adjText[0:3] != USFXAbbrev:
                        logging.error( "toUSFXXML: Book {}{} might be incorrect -- we got: '{}'".format( BBB, " ({})".format(USFXAbbrev) if USFXAbbrev!=BBB else '', adjText[0:3] ) )
                    adjText = adjText[4:] # Remove the book code from the ID line because it's put in as an attribute
                    if adjText: xw.writeLineOpenClose( 'id', handleInternalTextMarkersForUSFX(adjText)+xtra, ('code',USFXAbbrev) )
                    elif not text: logging.error( "toUSFXXML: {} {}:{} has a blank id line that was ignored".format( BBB, C, V ) )
                elif marker == 'c':
                    if haveOpenPara:
                        xw.removeFinalNewline( True )
                        xw.writeLineClose( 'p' )
                        haveOpenPara = False
                    #print( BBB, 'C', repr(text), repr(adjText) )
                    C = text # not adjText!
                    xw.writeLineOpenSelfclose ( 'c', ('id',C) )
                    if adjText != text:
                        logging.warning( "toUSFXXML: Lost additional note text on c for {} {}".format( BBB, repr(C) ) )
                elif marker == 'c~': # Don't really know what this stuff is!!!
                    if not adjText: logging.warning( "toUSFXXML: Missing text for c~" ); continue
                    # TODO: We haven't stripped out character fields from within the text -- not sure how USFX handles them yet
                    xw.removeFinalNewline( True )
                    xw.writeLineText( handleInternalTextMarkersForUSFX(adjText)+xtra, noTextCheck=True ) # no checks coz might already have embedded XML
                elif marker == 'c#': # Chapter number added for printing
                    pass # Just ignore it completely
                elif marker == 'v':
                    V = adjText.replace('<','').replace('>','').replace('"','') # Used below but remove anything that'll cause a big XML problem later
                    if paraJustOpened: paraJustOpened = False
                    else:
                        xw.removeFinalNewline( True )
                    xw.writeLineOpenSelfclose ( 'v', ('id',V) )
                elif marker in ('v~','p~',):
                    if not adjText: logging.warning( "toUSFXXML: Missing text for {}".format( marker ) ); continue
                    # TODO: We haven't stripped out character fields from within the verse -- not sure how USFX handles them yet
                    xw.removeFinalNewline( True )
                    xw.writeLineText( handleInternalTextMarkersForUSFX(adjText)+xtra, noTextCheck=True ) # no checks coz might already have embedded XML
                elif markerShouldHaveContent == 'N': # N = never, e.g., b, nb
                    if haveOpenPara:
                        xw.removeFinalNewline( True )
                        xw.writeLineClose( 'p' )
                        haveOpenPara = False
                    if adjText: logging.error( "toUSFXXML: {} {}:{} has a {} line containing text ('{}') that was ignored".format( BBB, C, V, originalMarker, adjText ) )
                    xw.writeLineOpenSelfclose ( marker )
                elif markerShouldHaveContent == 'S': # S = sometimes, e.g., p,pi,q,q1,q2,q3,q4,m
                    if haveOpenPara:
                        xw.removeFinalNewline( True )
                        xw.writeLineClose( 'p' )
                        haveOpenPara = False
                    if not adjText: xw.writeLineOpen( originalMarker )
                    else: xw.writeLineOpenText( originalMarker, handleInternalTextMarkersForUSFX(adjText)+xtra, noTextCheck=True ) # no checks coz might already have embedded XML
                    haveOpenPara = paraJustOpened = True
                else:
                    #assert( markerShouldHaveContent == 'A' ) # A = always, e.g.,  ide, mt, h, s, ip, etc.
                    if markerShouldHaveContent != 'A':
                        logging.debug( "BibleWriter.toUSFXXML: ToProgrammer -- should be 'A': '{}' is '{}' Why?".format( marker, markerShouldHaveContent ) )
                    if haveOpenPara:
                        xw.removeFinalNewline( True )
                        xw.writeLineClose( 'p' )
                        haveOpenPara = False
                    if 1 or adjText: xw.writeLineOpenClose( marker, handleInternalTextMarkersForUSFX(adjText)+xtra, noTextCheck=True ) # no checks coz might already have embedded XML
                    else: logging.info( "toUSFXXML: {} {}:{} has a blank {} line that was ignored".format( BBB, C, V, originalMarker ) )
            if haveOpenPara:
                xw.removeFinalNewline( True )
                xw.writeLineClose( 'p' )
            xw.writeLineClose( 'book' )
        # end of toUSFXXML.writeUSFXBook

        # Set-up our Bible reference system
        if controlDict['PublicationCode'] == "GENERIC":
            BOS = self.genericBOS
            BRL = self.genericBRL
        else:
            BOS = BibleOrganizationalSystem( controlDict["PublicationCode"] )
            BRL = BibleReferenceList( BOS, BibleObject=None )

        if Globals.verbosityLevel > 2: print( _("  Exporting to USFX XML format...") )
        #USFXOutputFolder = os.path.join( "OutputFiles/", "USFX output/" )
        #if not os.access( USFXOutputFolder, os.F_OK ): os.mkdir( USFXOutputFolder ) # Make the empty folder if there wasn't already one there

        filename = Globals.makeSafeFilename( controlDict["usfxOutputFilename"] )
        xw = MLWriter( filename, outputFolder )
        #xw = MLWriter( Globals.makeSafeFilename( USFXNumber+USFXAbbrev+"_usfx.xml" ), outputFolder )
        xw.setHumanReadable( 'All' ) # Can be set to 'All', 'Header', or 'None' -- one output file went from None/Header=4.7MB to All=5.7MB
        xw.spaceBeforeSelfcloseTag = True # Try to imitate Haiola output as closely as possible
        #xw.start( lineEndings='w', writeBOM=True ) # Try to imitate Haiola output as closely as possible
        xw.start()
        xw.writeLineOpen( 'usfx', [('xmlns:xsi',"http://eBible.org/usfx.xsd"), ('xsi:noNamespaceSchemaLocation',"usfx-2013-08-05.xsd")] )
        #print( self.ssfDict, self.settingsDict )
        languageCode = None
        if languageCode is None and 'Language' in self.settingsDict and len(self.settingsDict['Language'])==3:
            languageCode = self.settingsDict['Language']
        #if languageCode is None and 'Language' in self.ssfDict and len(self.ssfDict['Language'])==3:
            #languageCode = self.ssfDict['Language']
        if languageCode: xw.writeLineOpenClose( 'languageCode', languageCode )
        for BBB,bookData in self.books.items(): # Process each Bible book
            writeUSFXBook( xw, BBB, bookData )
        xw.writeLineClose( 'usfx' )
        xw.close()
        if validationSchema: validationResults = xw.validate( validationSchema )

        if unhandledMarkers:
            logging.warning( "toUSFXXML: Unhandled markers were {}".format( unhandledMarkers ) )
            if Globals.verbosityLevel > 1:
                print( "  " + _("WARNING: Unhandled toUSFX markers were {}").format( unhandledMarkers ) )

        # Now create a zipped version
        filepath = os.path.join( outputFolder, filename )
        if Globals.verbosityLevel > 2: print( "  Zipping {} pickle file...".format( filename ) )
        zf = zipfile.ZipFile( filepath+'.zip', 'w', compression=zipfile.ZIP_DEFLATED )
        zf.write( filepath, filename )
        zf.close()

        if validationSchema: return validationResults
        return True
    # end of BibleWriter.toUSFXXML



    def _writeSwordLocale( self, name, description, BibleOrganizationalSystem, getBookNameFunction, localeFilepath ):
        """
        Writes a UTF-8 Sword locale file containing the book names and abbreviations.
        """
        if Globals.verbosityLevel > 1: print( _("Writing Sword locale file {}...").format(localeFilepath) )

        with open( localeFilepath, 'wt' ) as SwLocFile:
            SwLocFile.write( '[Meta]\nName={}\n'.format( name ) )
            SwLocFile.write( 'Description={}\n'.format( description ) )
            SwLocFile.write( 'Encoding=UTF-8\n\n[Text]\n' )

            # This first section contains EnglishBookName=VernacularBookName
            bookList = []
            for BBB in BibleOrganizationalSystem.getBookList():
                if BBB in self.books:
                    vernacularName = getBookNameFunction(BBB)
                    SwLocFile.write( '{}={}\n'.format( Globals.BibleBooksCodes.getEnglishName_NR(BBB), vernacularName ) ) # Write the first English book name and the language book name
                    bookList.append( vernacularName )

            # This second section contains many VERNACULARABBREV=SwordBookAbbrev
            SwLocFile.write( '\n[Book Abbrevs]\n' )
            abbreviationList = []
            for BBB in BibleOrganizationalSystem.getBookList(): # First pass writes the full vernacular book names (with and without spaces removed)
                if BBB in self.books:
                    swordAbbrev = Globals.BibleBooksCodes.getSwordAbbreviation( BBB )
                    vernacularName = getBookNameFunction(BBB).upper()
                    #assert( vernacularName not in abbreviationList )
                    if vernacularName in abbreviationList:
                        if Globals.debugFlag:
                            print( "BibleWriter._writeSwordLocale: ToProgrammer -- vernacular name IS in abbreviationList -- what does this mean? Why? '{}' {}".format( vernacularName, abbreviationList ) )
                        logging.debug( "BibleWriter._writeSwordLocale: ToProgrammer -- vernacular name IS in abbreviationList -- what does this mean? Why? '{}' {}".format( vernacularName, abbreviationList ) )
                    SwLocFile.write( '{}={}\n'.format( vernacularName, swordAbbrev ) ) # Write the UPPER CASE language book name and the Sword abbreviation
                    abbreviationList.append( vernacularName )
                    if ' ' in vernacularName:
                        vernacularAbbrev = vernacularName.replace( ' ', '' )
                        if Globals.debugFlag and debuggingThisModule: assert( vernacularAbbrev not in abbreviationList )
                        SwLocFile.write( '{}={}\n'.format( vernacularAbbrev, swordAbbrev ) ) # Write the UPPER CASE language book name and the Sword abbreviation
                        abbreviationList.append( vernacularAbbrev )
            for BBB in BibleOrganizationalSystem.getBookList(): # Second pass writes the shorter vernacular book abbreviations
                if BBB in self.books:
                    swordAbbrev = Globals.BibleBooksCodes.getSwordAbbreviation( BBB )
                    vernacularName = getBookNameFunction(BBB).replace( ' ', '' ).upper()
                    vernacularAbbrev = vernacularName
                    if len(vernacularName)>4  or (len(vernacularName)>3 and not vernacularName[0].isdigit):
                        vernacularAbbrev = vernacularName[:4 if vernacularName[0].isdigit() else 3]
                        if vernacularAbbrev in abbreviationList:
                            if swordAbbrev == 'Philem':
                                vernacularAbbrev = vernacularName[:5]
                                if vernacularAbbrev not in abbreviationList:
                                    SwLocFile.write( '{}={}\n'.format( vernacularAbbrev, swordAbbrev ) ) # Write the UPPER CASE language book name and the Sword abbreviation
                                    abbreviationList.append( vernacularAbbrev )
                            else: logging.warning( "   Oops, shouldn't have written {} (also could be {}) to Sword locale file".format( vernacularAbbrev, swordAbbrev ) ) # Need to fix this
                        else:
                            SwLocFile.write( '{}={}\n'.format( vernacularAbbrev, swordAbbrev ) ) # Write the UPPER CASE language book name and the Sword abbreviation
                            abbreviationList.append( vernacularAbbrev )
                    changed = False
                    for somePunct in ( ".''̉΄" ): # Remove punctuation and glottals (all UPPER CASE here)
                        if somePunct in vernacularAbbrev:
                            vernacularAbbrev = vernacularAbbrev.replace( somePunct, '' )
                            changed = True
                    if changed:
                        if vernacularAbbrev in abbreviationList:
                            logging.warning( "   Oops, maybe shouldn't have written {} (also could be {}) to Sword locale file".format( vernacularAbbrev, swordAbbrev ) )
                        else:
                            SwLocFile.write( '{}={}\n'.format( vernacularAbbrev, swordAbbrev ) )
                            abbreviationList.append( vernacularAbbrev )
                        changed = False
                    for vowel in ( 'AΆÁÂÃÄÅEÈÉÊËIÌÍÎÏOÒÓÔÕÖUÙÚÛÜ' ): # Remove vowels (all UPPER CASE here)
                        if vowel in vernacularAbbrev:
                            vernacularAbbrev = vernacularAbbrev.replace( vowel, '' )
                            changed = True
                    if changed:
                        if vernacularAbbrev in abbreviationList:
                            logging.warning( "   Oops, maybe shouldn't have written {} (also could be {}) to Sword locale file".format( vernacularAbbrev, swordAbbrev ) )
                        else:
                            SwLocFile.write( '{}={}\n'.format( vernacularAbbrev, swordAbbrev ) )
                            abbreviationList.append( vernacularAbbrev )

        if Globals.verbosityLevel > 1: print( _("  Wrote {} book names and {} abbreviations.").format( len(bookList), len(abbreviationList) ) )
    # end of BibleWriter._writeSwordLocale



    def toOSISXML( self, outputFolder=None, controlDict=None, validationSchema=None ):
        """
        Using settings from the given control file,
            converts the USFM information to one or more UTF-8 OSIS XML files.

        If a schema is given (either a path or URL), the XML output file(s) is validated.

        TODO: We're not consistent about handling errors: sometimes we use assert, sometime raise (both of which abort the program), and sometimes log errors or warnings.
        """
        if Globals.verbosityLevel > 1: print( "Running BibleWriter:toOSISXML..." )
        if Globals.debugFlag: assert( self.books )

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolder: outputFolder = "OutputFiles/BOS_OSIS_Export/"
        if not os.access( outputFolder, os.F_OK ): os.makedirs( outputFolder ) # Make the empty folder if there wasn't already one there
        if not controlDict:
            controlDict, defaultControlFilename = {}, "To_OSIS_controls.txt"
            try:
                ControlFiles.readControlFile( defaultControlFolder, defaultControlFilename, controlDict )
            except:
                logging.critical( "Unable to read control dict {} from {}".format( defaultControlFilename, defaultControlFolder ) )
        self.__adjustControlDict( controlDict )

        # Set-up our Bible reference system
        #if Globals.debugFlag: print( "BibleWriter:toOSISXML publicationCode =", controlDict["PublicationCode"] )
        if controlDict['PublicationCode'] == "GENERIC":
            BOS = self.genericBOS
            BRL = self.genericBRL
        else:
            BOS = BibleOrganizationalSystem( controlDict["PublicationCode"] )
            BRL = BibleReferenceList( BOS, BibleObject=None )

        booksNamesSystemName = BOS.getOrganizationalSystemValue( 'booksNamesSystem' )
        if booksNamesSystemName and booksNamesSystemName!='None' and booksNamesSystemName!='Unknown': # default (if we know the book names system)
            getBookNameFunction = BOS.getBookName
            getBookAbbreviationFunction = BOS.getBookAbbreviation
        else: # else use our local functions from our deduced book names
            getBookNameFunction = self.getAssumedBookName # from USFMBible (which gets it from USFMBibleBook)
            getBookAbbreviationFunction = Globals.BibleBooksCodes.getOSISAbbreviation

        unhandledMarkers = set()

        # Let's write a Sword locale while we're at it -- might be useful if we make a Sword module from this OSIS file
        self._writeSwordLocale( controlDict["xmlLanguage"], controlDict["LanguageName"], BOS, getBookNameFunction, os.path.join( outputFolder, "SwLocale-utf8.conf" ) )
        #if Globals.verbosityLevel > 1: print( _("Writing Sword locale file {}...").format(SwLocFilepath) )
        #with open( SwLocFilepath, 'wt' ) as SwLocFile:
            #SwLocFile.write( '[Meta]\nName={}\n'.format(controlDict["xmlLanguage"]) )
            #SwLocFile.write( 'Description={}\n'.format(controlDict["LanguageName"]) )
            #SwLocFile.write( 'Encoding=UTF-8\n\n[Text]\n' )
            #for BBB in BOS.getBookList():
                #if BBB in self.books:
                    #SwLocFile.write( '{}={}\n'.format(Globals.BibleBooksCodes.getEnglishName_NR(BBB), getBookNameFunction(BBB) ) ) # Write the first English book name and the language book name
            #SwLocFile.write( '\n[Book Abbrevs]\n' )
            #for BBB in BOS.getBookList():
                #if BBB in self.books:
                    #SwLocFile.write( '{}={}\n'.format(Globals.BibleBooksCodes.getEnglishName_NR(BBB).upper(), Globals.BibleBooksCodes.getSwordAbbreviation(BBB) ) ) # Write the UPPER CASE language book name and the Sword abbreviation

        def writeHeader( writerObject ):
            """Writes the OSIS header to the OSIS XML writerObject."""
            writerObject.writeLineOpen( 'header' )
            writerObject.writeLineOpen( 'work', ('osisWork', controlDict["osisWork"]) )
            writerObject.writeLineOpenClose( 'title', controlDict["Title"] )
            writerObject.writeLineOpenClose( 'creator', "BibleWriter.py", ('role',"encoder") )
            writerObject.writeLineOpenClose( 'type',  "Bible", ('type',"OSIS") )
            writerObject.writeLineOpenClose( 'identifier', controlDict["Identifier"], ('type',"OSIS") )
            writerObject.writeLineOpenClose( 'scope', "dunno" )
            writerObject.writeLineOpenClose( 'refSystem', "Bible" )
            writerObject.writeLineClose( 'work' )
            # Snowfall software write two work entries ???
            writerObject.writeLineOpen( 'work', ('osisWork',"bible") )
            writerObject.writeLineOpenClose( 'creator', "BibleWriter.py", ('role',"encoder") )
            writerObject.writeLineOpenClose( 'type',  "Bible", ('type',"OSIS") )
            writerObject.writeLineOpenClose( 'refSystem', "Bible" )
            writerObject.writeLineClose( 'work' )
            writerObject.writeLineClose( 'header' )
        # end of toOSISXML.writeHeader

        toOSISGlobals = { "verseRef":'', "XRefNum":0, "FootnoteNum":0, "lastRef":'', "OneChapterOSISBookCodes":Globals.BibleBooksCodes.getOSISSingleChapterBooksList() } # These are our global variables


        def writeOSISBook( writerObject, BBB, bkData ):
            """Writes a book to the OSIS XML writerObject.
            """

            def checkText( textToCheck, checkLeftovers=True ):
                """Handle some general backslash codes and warn about any others still unprocessed."""

                def checkTextHelper( marker, helpText ):
                    """ Adjust the text to make the number of start and close markers equal. """
                    count1, count2 = helpText.count('\\'+marker+' '), helpText.count('\\'+marker+'*') # count open and close markers
                    while count1 < count2:
                        helpText = '\\'+marker+' ' + helpText
                        count1, count2 = helpText.count('\\'+marker+' '), helpText.count('\\'+marker+'*') # count open and close markers again
                    while count1 > count2:
                        helpText += '\\'+marker+'*'
                        count1, count2 = helpText.count('\\'+marker+' '), helpText.count('\\'+marker+'*') # count open and close markers again
                    if Globals.debugFlag: assert( count1 == count2 )
                    return helpText
                # end of checkTextHelper

                adjText = textToCheck
                if '<<' in adjText or '>>' in adjText:
                    logging.warning( _("toOSIS: Unexpected double angle brackets in {}: '{}' field is '{}'").format( toOSISGlobals["verseRef"], marker, textToCheck ) )
                    adjText = adjText.replace('<<','“' ).replace('>>','”' )
                if '\\bk ' in adjText: adjText = checkTextHelper('bk',adjText).replace('\\bk ','<reference type="x-bookName">').replace('\\bk*','</reference>')
                if '\\add ' in adjText: adjText = checkTextHelper('add',adjText).replace('\\add ','<i>').replace('\\add*','</i>') # temp XXXXXX ...
                if '\\nd ' in adjText: adjText = checkTextHelper('nd',adjText).replace('\\nd ','<divineName>').replace('\\nd*','</divineName>')
                if '\\wj ' in adjText: adjText = checkTextHelper('wj',adjText).replace('\\wj ','<hi type="bold">').replace('\\wj*','</hi>') # XXXXXX temp ....
                if '\\sig ' in adjText: adjText = checkTextHelper('sig',adjText).replace('\\sig ','<signed>').replace('\\sig*','</signed>')
                if '\\it ' in adjText: adjText = checkTextHelper('it',adjText).replace('\\it ','<hi type="italic">').replace('\\it*','</hi>')
                if '\\bd ' in adjText: adjText = checkTextHelper('bd',adjText).replace('\\bd ','<hi type="bold">').replace('\\bd*','</hi>')
                if '\\em ' in adjText: adjText = checkTextHelper('em',adjText).replace('\\em ','<hi type="bold">').replace('\\em*','</hi>')
                if '\\sc ' in adjText: adjText = checkTextHelper('sc',adjText).replace('\\sc ','<hi type="SMALLCAPS">').replace('\\sc*','</hi>') # XXXXXX temp ....
                if '\\ior ' in adjText: adjText = checkTextHelper('ior',adjText).replace('\\ior ','<reference>').replace('\\ior*','</reference>')
                if '\\fig ' in adjText: # Figure is not used in Sword modules so we'll remove it from the OSIS (for now at least)
                    ix1 = adjText.find( '\\fig ' )
                    ix2 = adjText.find( '\\fig*' )
                    if ix2 == -1: logging.error( _("toOSIS: Missing fig end marker for OSIS in {}: '{}' field is '{}'").format( toOSISGlobals["verseRef"], marker, textToCheck ) )
                    else:
                        if Globals.debugFlag: assert( ix2 > ix1 )
                        #print( "was '{}'".format( adjText ) )
                        adjText = adjText[:ix1] + adjText[ix2+5:] # Remove the \\fig..\\fig* field
                        #print( "now '{}'".format( adjText ) )
                        logging.warning( _("toOSIS: Figure reference removed for OSIS generation in {}: '{}' field").format( toOSISGlobals["verseRef"], marker ) )
                if checkLeftovers and '\\' in adjText:
                    logging.error( _("toOSIS: We still have some unprocessed backslashes for OSIS in {}: '{}' field is '{}'").format( toOSISGlobals["verseRef"], marker, textToCheck ) )
                    #print( _("toOSIS: We still have some unprocessed backslashes for OSIS in {}: '{}' field is '{}'").format( toOSISGlobals["verseRef"], marker, textToCheck ) )
                    adjText = adjText.replace('\\','ENCODING ERROR HERE ' )
                return adjText
            # end of toOSISXML.checkText

            def processXRefsAndFootnotes( verse, extras, offset=0 ):
                """Convert cross-references and footnotes and return the adjusted verse text."""

                def processXRef( USFMxref ):
                    """
                    Return the OSIS code for the processed cross-reference (xref).

                    NOTE: The parameter here already has the /x and /x* removed.

                    \\x - \\xo 2:2: \\xt Lib 19:9-10; Diy 24:19.\\xt*\\x* (Backslashes are shown doubled here)
                        gives
                    <note type="crossReference" n="1">2:2: <reference>Lib 19:9-10; Diy 24:19.</reference></note> (Crosswire -- invalid OSIS -- which then needs to be converted)
                    <note type="crossReference" osisRef="Ruth.2.2" osisID="Ruth.2.2!crossreference.1" n="-"><reference type="source" osisRef="Ruth.2.2">2:2: </reference><reference osisRef="-">Lib 19:9-10</reference>; <reference osisRef="Ruth.Diy.24!:19">Diy 24:19</reference>.</note> (Snowfall)
                    \\x - \\xo 3:5: a \\xt Rum 11:1; \\xo b \\xt Him 23:6; 26:5.\\xt*\\x* is more complex still.
                    """
                    #nonlocal BBB
                    toOSISGlobals["XRefNum"] += 1
                    OSISxref = '<note type="crossReference" osisRef="{}" osisID="{}!crossreference.{}">'.format( toOSISGlobals["verseRef"], toOSISGlobals["verseRef"], toOSISGlobals["XRefNum"] )
                    for j,token in enumerate(USFMxref.split('\\')):
                        #print( "toOSIS:processXRef", j, "'"+token+"'", "from", '"'+USFMxref+'"' )
                        lcToken = token.lower()
                        if j==0: # The first token (but the x has already been removed)
                            rest = token.strip()
                            if rest != '-': logging.warning( _("toOSIS: We got something else here other than hyphen (probably need to do something with it): {} '{}' from '{}'").format(chapterRef, token, text) )
                        elif lcToken.startswith('xo '): # xref reference follows
                            adjToken = token[3:].strip()
                            #print( "toOSIS:processXRef(xo)", j, "'"+token+"'", "'"+adjToken+"'", "from", '"'+USFMxref+'"' )
                            if j==1:
                                if len(adjToken)>2 and adjToken[-2]==' ' and adjToken[-1]=='a':
                                    suffixLetter = adjToken[-1]
                                    adjToken = adjToken[:-2] # Remove any suffix (occurs when a cross-reference has multiple (a and b) parts
                                if adjToken.endswith(':'): adjToken = adjToken[:-1] # Remove any final colon (this is a language dependent hack)
                                adjToken = getBookAbbreviationFunction(BBB) + ' ' + adjToken # Prepend a book abbreviation for the anchor (will be processed to an OSIS reference later)
                                selfReference = adjToken
                            else: # j > 1 -- this xo field may possibly only contain a letter suffix
                                if len(adjToken)==1 and adjToken in ('b','c','d','e','f','g','h',):
                                    adjToken = selfReference
                                else: # Could be another complete reference
                                    #print( "<<< Programming error here in toOSIS:processXRef for '{}' at {} {}:{}".format( USFMxref, BBB, currentChapterNumberString, verseNumberString )  )
                                    #print( "  '"+lcToken+"'", len(adjToken), "'"+adjToken+"'" )
                                    if len(adjToken)>2 and adjToken[-2]==' ' and adjToken[-1]=='a':
                                        suffixLetter = adjToken[-1]
                                        adjToken = adjToken[:-2] # Remove any suffix (occurs when a cross-reference has multiple (a and b) parts
                                    if adjToken.endswith(':'): adjToken = adjToken[:-1] # Remove any final colon (this is a language dependent hack)
                                    adjToken = getBookAbbreviationFunction(BBB) + ' ' + adjToken # Prepend a book abbreviation for the anchor (will be processed to an OSIS reference later)
                                    selfReference = adjToken
                            osisRef = BRL.parseToOSIS( adjToken, toOSISGlobals["verseRef"] )
                            if osisRef is not None:
                                #print( "  osisRef = {}".format( osisRef ) )
                                OSISxref += '<reference type="source" osisRef="{}">{}</reference>'.format(osisRef,token[3:])
                                if not BRL.containsReference( BBB, currentChapterNumberString, verseNumberString ):
                                    logging.error( _("toOSIS: Cross-reference at {} {}:{} seems to contain the wrong self-reference anchor '{}'").format(BBB,currentChapterNumberString,verseNumberString, token[3:].rstrip()) )
                        elif lcToken.startswith('xt '): # xref text follows
                            xrefText = token[3:]
                            finalPunct = ''
                            while xrefText[-1] in (' ,;.'): finalPunct = xrefText[-1] + finalPunct; xrefText = xrefText[:-1]
                            #adjString = xrefText[:-6] if xrefText.endswith( ' (LXX)' ) else xrefText # Sorry, this is a crude hack to avoid unnecessary error messages
                            osisRef = BRL.parseToOSIS( xrefText, toOSISGlobals["verseRef"] )
                            if osisRef is not None:
                                OSISxref += '<reference type="source" osisRef="{}">{}</reference>'.format(osisRef,xrefText+finalPunct)
                        elif lcToken.startswith('x '): # another whole xref entry follows
                            rest = token[2:].strip()
                            if rest != '-': logging.warning( _("toOSIS: We got something else here other than hyphen (probably need to do something with it): {} '{}' from '{}'").format(chapterRef, token, text) )
                        elif lcToken in ('xo*','xt*','x*',):
                            pass # We're being lazy here and not checking closing markers properly
                        else:
                            logging.warning( _("toOSIS: Unprocessed '{}' token in {} xref '{}'").format( token, toOSISGlobals["verseRef"], USFMxref ) )
                    OSISxref += '</note>'
                    return OSISxref
                # end of toOSISXML.processXRef

                def processFootnote( USFMfootnote ):
                    """
                    Return the OSIS code for the processed footnote.

                    NOTE: The parameter here already has the /f and /f* removed.

                    \\f + \\fr 1:20 \\ft Su ka kaluwasan te Nawumi ‘keupianan,’ piru ka kaluwasan te Mara ‘masakit se geyinawa.’\\f* (Backslashes are shown doubled here)
                        gives
                    <note n="1">1:20 Su ka kaluwasan te Nawumi ‘keupianan,’ piru ka kaluwasan te Mara ‘masakit se geyinawa.’</note> (Crosswire)
                    <note osisRef="Ruth.1.20" osisID="Ruth.1.20!footnote.1" n="+"><reference type="source" osisRef="Ruth.1.20">1:20 </reference>Su ka kaluwasan te Nawumi ‘keupianan,’ piru ka kaluwasan te Mara ‘masakit se geyinawa.’</note> (Snowfall)
                    """
                    toOSISGlobals["FootnoteNum"] += 1
                    OSISfootnote = '<note osisRef="{}" osisID="{}!footnote.{}">'.format( toOSISGlobals["verseRef"], toOSISGlobals["verseRef"], toOSISGlobals["FootnoteNum"] )
                    for j,token in enumerate(USFMfootnote.split('\\')):
                        #print( "processFootnote", j, token, USFMfootnote )
                        lcToken = token.lower()
                        if j==0: continue # ignore the + for now
                        elif lcToken.startswith('fr '): # footnote reference follows
                            adjToken = token[3:].strip()
                            if adjToken.endswith(':'): adjToken = adjToken[:-1] # Remove any final colon (this is a language dependent hack)
                            adjToken = getBookAbbreviationFunction(BBB) + ' ' + adjToken # Prepend a book abbreviation for the anchor (will be processed to an OSIS reference later)
                            osisRef = BRL.parseToOSIS( adjToken, toOSISGlobals["verseRef"] ) # Note that this may return None
                            if osisRef is not None:
                                OSISfootnote += '<reference type="source" osisRef="{}">{}</reference>'.format(osisRef,token[3:])
                                if not BRL.containsReference( BBB, currentChapterNumberString, verseNumberString ):
                                    logging.error( _("toOSIS: Footnote at {} {}:{} seems to contain the wrong self-reference anchor '{}'").format(BBB,currentChapterNumberString,verseNumberString, token[3:].rstrip()) )
                        elif lcToken.startswith('ft ') or lcToken.startswith('fr* '): # footnote text follows
                            OSISfootnote += token[3:]
                        elif lcToken.startswith('fq ') or token.startswith('fqa '): # footnote quote follows -- NOTE: We also assume here that the next marker closes the fq field
                            OSISfootnote += '<catchWord>{}</catchWord>'.format(token[3:]) # Note that the trailing space goes in the catchword here -- seems messy
                        elif lcToken in ('fr*','fr* ','ft*','ft* ','fq*','fq* ','fqa*','fqa* ',):
                            pass # We're being lazy here and not checking closing markers properly
                        else:
                            logging.warning( _("toOSIS: Unprocessed '{}' token in {} footnote '{}'").format(token, toOSISGlobals["verseRef"], USFMfootnote) )
                    OSISfootnote += '</note>'
                    #print( '', OSISfootnote )
                    #if currentChapterNumberString=='5' and verseNumberString=='29': halt
                    return OSISfootnote
                # end of toOSISXML.processFootnote

                #if extras: print( '\n', chapterRef )
                if Globals.debugFlag: assert( offset >= 0 )
                for extraType, extraIndex, extraText, cleanExtraText in extras: # do any footnotes and cross-references
                    adjIndex = extraIndex - offset
                    lenV = len( verse )
                    if adjIndex > lenV: # This can happen if we have verse/space/notes at end (and the space was deleted after the note was separated off)
                        logging.warning( _("toOSIS: Space before note at end of verse in {} has been lost").format( toOSISGlobals["verseRef"] ) )
                        # No need to adjust adjIndex because the code below still works
                    elif adjIndex<0 or adjIndex>lenV: # The extras don't appear to fit correctly inside the verse
                        print( "toOSIS: Extras don't fit inside verse at {}: eI={} o={} len={} aI={}".format( toOSISGlobals["verseRef"], extraIndex, offset, len(verse), adjIndex ) )
                        print( "  Verse='{}'".format( verse ) )
                        print( "  Extras='{}'".format( extras ) )
                    #assert( 0 <= adjIndex <= len(verse) )
                    adjText = checkText( extraText, checkLeftovers=False ) # do any general character formatting on the notes
                    #if adjText!=extraText: print( "processXRefsAndFootnotes: {}@{}-{}={} '{}' now '{}'".format( extraType, extraIndex, offset, adjIndex, extraText, adjText ) )
                    if extraType == 'fn':
                        extra = processFootnote( adjText )
                        #print( "fn got", extra )
                    elif extraType == 'xr':
                        extra = processXRef( adjText )
                        #print( "xr got", extra )
                    elif extraType == 'fig':
                        logging.critical( "OSISXML figure not handled yet" )
                        extra = "" # temp
                        #extra = processFigure( extraText )
                        #print( "fig got", extra )
                    elif Globals.debugFlag and debuggingThisModule: print( extraType ); halt
                    #print( "was", verse )
                    verse = verse[:adjIndex] + extra + verse[adjIndex:]
                    offset -= len( extra )
                    #print( "now", verse )
                return verse
            # end of toOSISXML.processXRefsAndFootnotes

            def writeVerseStart( writerObject, BBB, chapterRef, verseNumberText ):
                """
                Processes and writes a verse milestone to the OSIS XML writerObject.
                    <verse sID="Gen.1.31" osisID="Gen.1.31"/>
                    Ne nakita te Manama ka langun ne innimu rin wey natelesan amana sikandin. Ne nasagkup e wey napawe, ne seeye ka igkeen-em ne aldew.
                    <verse eID="Gen.1.31"/>

                Has to handle joined verses, e.g.,
                    <verse sID="Esth.9.16" osisID="Esth.9.16 Esth.9.17"/>text<verse eID="Esth.9.16"/> (Crosswire)
                    <verse sID="Esth.9.16-Esth.9.17" osisID="Esth.9.16 Esth.9.17" n="16-17"/>text<verse eID="Esth.9.16-Esth.9.17"/> (Snowfall)
                """
                nonlocal haveOpenVsID
                if haveOpenVsID != False: # Close the previous verse
                    writerObject.writeLineOpenSelfclose( 'verse', ('eID',haveOpenVsID) )
                #verseNumberString = text.split()[0] # Get the first token which is the first number
                #offset = len(verseNumberString) + 1 # Add one for the following space
                ##while offset<len(text): # Remove any additional leading spaces (this can easily happen if verse initial xrefs are followed by an extra space)
                ##    if text[offset]==' ': offset += 1
                ##    else: break
                #verseText = text[offset:] # Get the rest of the string which is the verse text
                if '-' in verseNumberString:
                    bits = verseNumberString.split('-')
                    if len(bits)!=2 or not bits[0].isdigit() or not bits[1].isdigit(): logging.critical( _("toOSIS: Doesn't handle verse number of form '{}' yet for {}").format(verseNumberString,chapterRef) )
                    toOSISGlobals["verseRef"]  = chapterRef + '.' + bits[0]
                    verseRef2 = chapterRef + '.' + bits[1]
                    sID    = toOSISGlobals["verseRef"] + '-' + verseRef2
                    osisID = toOSISGlobals["verseRef"] + ' ' + verseRef2
                elif ',' in verseNumberString:
                    bits = verseNumberString.split(',')
                    if len(bits)<2 or not bits[0].isdigit() or not bits[1].isdigit(): logging.critical( _("toOSIS: Doesn't handle verse number of form '{}' yet for {}").format(verseNumberString,chapterRef) )
                    sID = toOSISGlobals["verseRef"] = chapterRef + '.' + bits[0]
                    osisID = ''
                    for bit in bits: # Separate the OSIS ids by spaces
                        osisID += ' ' if osisID else ''
                        osisID += chapterRef + '.' + bit
                    #print( "Hey comma verses '{}' '{}'".format( sID, osisID ) )
                elif verseNumberString.isdigit():
                    sID = osisID = toOSISGlobals["verseRef"] = chapterRef + '.' + verseNumberString
                else:
                    logging.critical( _("toOSIS: Doesn't handle verse number of form '{}' yet for {}").format(verseNumberString,chapterRef) )
                    tempID = toOSISGlobals["verseRef"] = chapterRef + '.' + verseNumberString # Try it anyway
                    sID = osisID = tempID.replace('<','').replace('>','').replace('"','') # But remove anything that'll cause a big XML problem later
                #print( "here SID='{}' osisID='{}'".format( sID, osisID ) )
                writerObject.writeLineOpenSelfclose( 'verse', [('sID',sID), ('osisID',osisID)] ); haveOpenVsID = sID
                #adjText = processXRefsAndFootnotes( verseText, extras, offset )
                #writerObject.writeLineText( checkText(adjText), noTextCheck=True )
                ##writerObject.writeLineOpenSelfclose( 'verse', ('eID',sID) )
            # end of toOSISXML.writeVerseStart

            def closeAnyOpenMajorSection():
                """ Close a <div> if it's open. """
                nonlocal haveOpenMajorSection
                if haveOpenMajorSection:
                    writerObject.writeLineClose( 'div' )
                    haveOpenMajorSection = False
            # end of toOSISXML.closeAnyOpenMajorSection

            def closeAnyOpenSection():
                """ Close a <div> if it's open. """
                nonlocal haveOpenL, haveOpenLG, haveOpenParagraph, haveOpenSubsection
                nonlocal haveOpenSection
                if haveOpenL:
                    logging.error( "toOSIS: closeAnyOpenSection: Why was L open at {}?".format( toOSISGlobals["verseRef"] ) )
                    writerObject.writeLineClose( 'l' )
                    haveOpenL = False
                if haveOpenLG:
                    logging.error( "toOSIS: closeAnyOpenSection: Why was LG open at {}?".format( toOSISGlobals["verseRef"] ) )
                    writerObject.writeLineClose( 'lg' )
                    haveOpenLG = False
                if haveOpenParagraph:
                    logging.error( "toOSIS: closeAnyOpenSection: Why was paragraph open at {}?".format( toOSISGlobals["verseRef"] ) )
                    writerObject.writeLineClose( 'p' )
                    haveOpenParagraph = False
                if haveOpenSubsection:
                    logging.error( "toOSIS: closeAnyOpenSection: Why was subsection open at {}?".format( toOSISGlobals["verseRef"] ) )
                    writerObject.writeLineClose( 'div' )
                    haveOpenSubsection = False
                if haveOpenSection:
                    writerObject.writeLineClose( 'div' )
                    haveOpenSection = False
            # end of toOSISXML.closeAnyOpenSection

            def closeAnyOpenSubsection():
                """ Close a <div> if it's open. """
                nonlocal haveOpenSubsection
                if haveOpenSubsection:
                    writerObject.writeLineClose( 'div' )
                    haveOpenSubsection = False
            # end of toOSISXML.closeAnyOpenSubsection

            def closeAnyOpenParagraph():
                """ Close a <p> if it's open. """
                nonlocal haveOpenParagraph
                if haveOpenParagraph:
                    writerObject.writeLineClose( 'p' )
                    haveOpenParagraph = False
            # end of toOSISXML.closeAnyOpenParagraph

            def closeAnyOpenLG():
                """ Close a <lg> if it's open. """
                nonlocal haveOpenLG
                if haveOpenLG:
                    #print( "closeAnyOpenLG", toOSISGlobals["verseRef"] )
                    writerObject.writeLineClose( 'lg' )
                    haveOpenLG = False
            # end of toOSISXML.closeAnyOpenLG

            def closeAnyOpenL():
                """ Close a <l> if it's open. """
                nonlocal haveOpenL
                if haveOpenL:
                    writerObject.writeLineClose( 'l' )
                    haveOpenL = False
            # end of toOSISXML.closeAnyOpenL

            bookRef = Globals.BibleBooksCodes.getOSISAbbreviation( BBB ) # OSIS book name
            if not bookRef:
                logging.error( "toOSIS: Can't write {} OSIS book because no OSIS code available".format( BBB ) )
                return
            chapterRef = bookRef + '.0' # Not used by OSIS
            toOSISGlobals["verseRef"] = chapterRef + '.0' # Not used by OSIS
            writerObject.writeLineOpen( 'div', [('type',"book"), ('osisID',bookRef)] )
            haveOpenIntro = haveOpenOutline = haveOpenMajorSection = haveOpenSection = haveOpenSubsection = needChapterEID = haveOpenParagraph = haveOpenVsID = haveOpenLG = haveOpenL = False
            lastMarker = unprocessedMarker = ''
            C = V = "0"
            for verseDataEntry in bkData._processedLines: # Process internal Bible data lines
                marker, text, extras = verseDataEntry.getMarker(), verseDataEntry.getAdjustedText(), verseDataEntry.getExtras()
                #print( "toOSIS:", marker, originalMarker, text )
                if marker in oftenIgnoredIntroMarkers: continue # Just ignore these lines
                #if marker in ( 'id', 'ide', 'h', 'mt2' ): continue # We just ignore these markers
                elif marker=='mt1':
                    if text: writerObject.writeLineOpenClose( 'title', checkText(text) )
                elif marker=='mt2':
                    if text: writerObject.writeLineOpenClose( 'title', checkText(text) )
                elif marker=='is1' or marker=='imt1':
                    #print( marker, "'"+text+"'" )
                    if not haveOpenIntro:
                        writerObject.writeLineOpen( 'div', [('type',"introduction"),('canonical',"false")] )
                        haveOpenIntro = True
                    if text: writerObject.writeLineOpenClose( 'title', checkText(text) ) # Introduction heading
                    logging.error( _("toOSIS: {} Have a blank {} field—ignoring it").format( toOSISGlobals["verseRef"], marker ) )
                elif marker=='ip':
                    if not haveOpenIntro: # Shouldn't happen but we'll try our best
                        logging.error( _("toOSIS: {} Have an ip not in an introduction section—ignoring it").format( toOSISGlobals["verseRef"] ) )
                        writerObject.writeLineOpen( 'div', [('type',"introduction"),('canonical',"false")] )
                        haveOpenIntro = True
                    closeAnyOpenParagraph()
                    writerObject.writeLineOpenText( 'p', checkText(text), noTextCheck=True ) # Sometimes there's text
                    haveOpenParagraph = True
                elif marker=='iot':
                    if not haveOpenIntro: # Shouldn't happen but we'll try our best
                        logging.error( _("toOSIS: {} Have an iot not in an introduction section").format( toOSISGlobals["verseRef"] ) )
                        writerObject.writeLineOpen( 'div', [('type',"introduction"),('canonical',"false")] )
                        haveOpenIntro = True
                    if haveOpenSection or haveOpenOutline: logging.error( "toOSIS: Not handled yet iot in {} hOS={} hOO={}".format(BBB,haveOpenSection,haveOpenOutline) )
                    closeAnyOpenParagraph()
                    writerObject.writeLineOpen( 'div', ('type',"outline") )
                    if text: writerObject.writeLineOpenClose( 'title', checkText(text) )
                    writerObject.writeLineOpen( 'list' )
                    haveOpenOutline = True
                elif marker=='io1':
                    if not haveOpenIntro: # Shouldn't happen but we'll try our best
                        logging.error( _("toOSIS: {} Have an io1 not in an introduction section").format( toOSISGlobals["verseRef"] ) )
                        writerObject.writeLineOpen( 'div', [('type',"introduction"),('canonical',"false")] )
                        haveOpenIntro = True
                    if not haveOpenOutline: # Shouldn't happen but we'll try our best
                        logging.warning( _("toOSIS: {} Have an io1 not in an outline section").format( toOSISGlobals["verseRef"] ) )
                        closeAnyOpenParagraph()
                        writerObject.writeLineOpen( 'div', ('type',"outline") )
                        writerObject.writeLineOpen( 'list' )
                        haveOpenOutline = True
                    if text: writerObject.writeLineOpenClose( 'item', checkText(text) )
                elif marker=='io2':
                    if not haveOpenIntro:
                        logging.error( _("toOSIS: {} Have an io2 not in an introduction section").format( toOSISGlobals["verseRef"] ) )
                    if not haveOpenOutline:
                        logging.error( _("toOSIS: {} Have an io2 not in an outline section").format( toOSISGlobals["verseRef"] ) )
                    if text: writerObject.writeLineOpenClose( 'item', checkText(text) ) # TODO: Shouldn't this be different from an io1???
                elif marker=='c':
                    if haveOpenVsID != False: # Close the previous verse
                        writerObject.writeLineOpenSelfclose( 'verse', ('eID',haveOpenVsID) )
                        haveOpenVsID = False
                    if haveOpenOutline:
                        if text!='1' and not text.startswith('1 '): logging.error( _("toOSIS: {} This should normally be chapter 1 to close the introduction (got '{}')").format( toOSISGlobals["verseRef"], text ) )
                        writerObject.writeLineClose( 'list' )
                        writerObject.writeLineClose( 'div' )
                        haveOpenOutline = False
                    if haveOpenIntro:
                        if text!='1' and not text.startswith('1 '): logging.error( _("toOSIS: {} This should normally be chapter 1 to close the introduction (got '{}')").format( toOSISGlobals["verseRef"], text ) )
                        closeAnyOpenParagraph()
                        writerObject.writeLineClose( 'div' )
                        haveOpenIntro = False
                    closeAnyOpenLG()
                    if needChapterEID:
                        writerObject.writeLineOpenSelfclose( 'chapter', ('eID',chapterRef) ) # This is an end milestone marker
                    C, V = text, "0"
                    currentChapterNumberString, verseNumberString = text, '0'
                    if not currentChapterNumberString.isdigit(): logging.critical( _("toOSIS: Can't handle non-digit '{}' chapter number yet").format(text) )
                    chapterRef = bookRef + '.' + checkText(currentChapterNumberString)
                    writerObject.writeLineOpenSelfclose( 'chapter', [('sID',chapterRef), ('osisID',chapterRef)] ) # This is a milestone marker
                    needChapterEID = True
                elif marker=='c~':
                    adjText = processXRefsAndFootnotes( text, extras, 0 )
                    writerObject.writeLineText( checkText(adjText), noTextCheck=True )
                elif marker == 'c#': # Chapter number added for printing
                    pass # Just ignore it completely
                elif marker=='ms1':
                    if haveOpenParagraph:
                        closeAnyOpenLG()
                        closeAnyOpenParagraph()
                    closeAnyOpenSubsection()
                    closeAnyOpenSection()
                    closeAnyOpenMajorSection()
                    writerObject.writeLineOpen( 'div', ('type',"majorSection") )
                    haveOpenMajorSection = True
                    if text: writerObject.writeLineOpenClose( 'title', checkText(text) ) # Section heading
                    else:
                        logging.info( _("toOSIS: {} Blank ms1 section heading encountered").format( toOSISGlobals["verseRef"] ) )
                elif marker=='s1':
                    if haveOpenParagraph:
                        closeAnyOpenLG()
                        closeAnyOpenParagraph()
                    closeAnyOpenSubsection()
                    closeAnyOpenSection()
                    writerObject.writeLineOpen( 'div', ('type', "section") )
                    haveOpenSection = True
                    #print( "{} {}:{}".format( BBB, currentChapterNumberString, verseNumberString ) )
                    #print( "{} = '{}'".format( marker, text ) )
                    flag = False # Set this flag if the text already contains XML formatting
                    for format in ('\\nd ','\\bd ', '\\sc ', ):
                        if format in text: flag = True; break
                    if extras: flag = True
                    adjustedText = processXRefsAndFootnotes( text, extras )
                    if text: writerObject.writeLineOpenClose( 'title', checkText(adjustedText), noTextCheck=flag ) # Section heading
                    else:
                        logging.info( _("toOSIS: {} Blank s1 section heading encountered").format( toOSISGlobals["verseRef"] ) )
                elif marker=='s2':
                    if haveOpenParagraph:
                        closeAnyOpenLG()
                        closeAnyOpenParagraph()
                    closeAnyOpenSubsection()
                    writerObject.writeLineOpen( 'div', ('type', "subSection") )
                    haveOpenSubsection = True
                    if text: writerObject.writeLineOpenClose( 'title',checkText(text) ) # Section heading
                    else:
                        logging.info( _("toOSIS: {} Blank s2 section heading encountered").format( toOSISGlobals["verseRef"] ) )
                elif marker=='s3':
                    if haveOpenParagraph:
                        closeAnyOpenLG()
                        closeAnyOpenParagraph()
                    closeAnyOpenSubsection()
                    writerObject.writeLineOpen( 'div', ('type', "subSection") )
                    haveOpenSubsection = True
                    if text: writerObject.writeLineOpenClose( 'title',checkText(text) ) # Section heading
                    else:
                        logging.info( _("toOSIS: {} Blank s3 section heading encountered").format( toOSISGlobals["verseRef"] ) )
                elif marker=='s4':
                    if haveOpenParagraph:
                        closeAnyOpenLG()
                        closeAnyOpenParagraph()
                    closeAnyOpenSubsection()
                    writerObject.writeLineOpen( 'div', ('type', "subSection") )
                    haveOpenSubsection = True
                    if text: writerObject.writeLineOpenClose( 'title',checkText(text) ) # Section heading
                    else:
                        logging.info( _("toOSIS: {} Blank s4 section heading encountered").format( toOSISGlobals["verseRef"] ) )
                elif marker=='mr':
                    # Should only follow a ms1 I think
                    if haveOpenParagraph or haveOpenSection or not haveOpenMajorSection: logging.error( _("toOSIS: Didn't expect major reference 'mr' marker after {}").format(toOSISGlobals["verseRef"]) )
                    if text: writerObject.writeLineOpenClose( 'title', checkText(text), ('type',"parallel") ) # Section cross-reference
                elif marker=='r':
                    # Should only follow a s1 I think
                    if haveOpenParagraph or not haveOpenSection: logging.error( _("toOSIS: Didn't expect reference 'r' marker after {}").format(toOSISGlobals["verseRef"]) )
                    if text: writerObject.writeLineOpenClose( 'title', checkText(text), ('type',"parallel") ) # Section cross-reference
                elif marker=='p':
                    closeAnyOpenLG()
                    closeAnyOpenParagraph()
                    if not haveOpenSection:
                        writerObject.writeLineOpen( 'div', ('type', "section") )
                        haveOpenSection = True
                    adjustedText = processXRefsAndFootnotes( text, extras )
                    writerObject.writeLineOpenText( 'p', checkText(adjustedText), noTextCheck=True ) # Sometimes there's text
                    haveOpenParagraph = True
                elif marker=='v':
                    verseNumberString = text
                    if not haveOpenL: closeAnyOpenLG()
                    V = text
                    writeVerseStart( writerObject, BBB, chapterRef, verseNumberString )
                    closeAnyOpenL()
                elif marker in ('v~','p~',):
                    adjText = processXRefsAndFootnotes( text, extras, 0 )
                    writerObject.writeLineText( checkText(adjText), noTextCheck=True )
                elif marker in ('q1','q2','q3','q4',):
                    qLevel = marker[1] # The digit
                    closeAnyOpenL()
                    if not haveOpenLG:
                        writerObject.writeLineOpen( 'lg' )
                        haveOpenLG = True
                    if text:
                        adjustedText = processXRefsAndFootnotes( text, extras )
                        writerObject.writeLineOpenClose( 'l', checkText(adjustedText), ('level',qLevel), noTextCheck=True )
                    else: # No text -- this q1 applies to the next marker
                        writerObject.writeLineOpen( 'l', ('level',qLevel) )
                        haveOpenL = True
                elif marker=='m': # Margin/Flush-left paragraph
                    closeAnyOpenL()
                    closeAnyOpenLG()
                    if text: writerObject.writeLineText( checkText(text), noTextCheck=True )
                elif marker=='b': # Blank line
                        # Doesn't seem that OSIS has a way to encode this presentation element
                        writerObject.writeNewLine() # We'll do this for now
                else:
                    if text:
                        logging.critical( "toOSIS: lost text in {} field in {} {}:{} {}".format( marker, BBB, C, V, repr(text) ) )
                        #if Globals.debugFlag: halt
                    if extras:
                        logging.critical( "toOSIS: lost extras in {} field in {} {}:{}".format( marker, BBB, C, V ) )
                        #if Globals.debugFlag: halt
                    unhandledMarkers.add( marker )
                if marker not in ('v','v~','p','p~','q1','q2','q3','q4','s1',) and extras:
                    logging.critical( "toOSIS: Programming note: Didn't handle '{}' extras: {}".format( marker, extras ) )
                lastMarker = marker

            # At the end of everything
            if haveOpenVsID != False: # Close the last verse
                writerObject.writeLineOpenSelfclose( 'verse', ('eID',haveOpenVsID) )
                haveOpenVsID = False
            closeAnyOpenLG() # A file can easily end with a q1 field
            if haveOpenIntro or haveOpenOutline or haveOpenLG or haveOpenL or unprocessedMarker:
                logging.error( "toOSIS: a {} {} {} {} {}".format( haveOpenIntro, haveOpenOutline, haveOpenLG, haveOpenL, unprocessedMarker ) )
                logging.error( "toOSIS: b {} {}:{}".format( BBB, currentChapterNumberString, verseNumberString ) )
                logging.error( "toOSIS: c {} = '{}'".format( marker, text ) )
                logging.error( "toOSIS: d These shouldn't be open here" )
            if needChapterEID:
                writerObject.writeLineOpenSelfclose( 'chapter', ('eID',chapterRef) ) # This is an end milestone marker
            if haveOpenParagraph:
                closeAnyOpenLG()
                closeAnyOpenParagraph()
            closeAnyOpenSection()
            closeAnyOpenMajorSection()
            writerObject.writeLineClose( 'div' ) # Close book division
            writerObject.writeNewLine()
        # end of toOSISXML.writeOSISBook

        if controlDict["osisFiles"]=="byBook": # Write an individual XML file for each book
            if Globals.verbosityLevel > 2: print( _("  Exporting individually to OSIS XML format...") )
            validationResults = ( 0, '', '', ) # xmllint result code, program output, error output
            for BBB,bookData in self.books.items(): # Process each Bible book
                xw = MLWriter( Globals.makeSafeFilename( controlDict["osisOutputFilename"].replace('_Bible',"_Book-{}".format(BBB)) ), outputFolder )
                xw.setHumanReadable( 'All' ) # Can be set to 'All', 'Header', or 'None' -- one output file went from None/Header=4.7MB to All=5.7MB
                xw.start()
                xw.writeLineOpen( 'osis', [('xmlns',OSISNameSpace), ('xmlns:xsi',"http://www.w3.org/2001/XMLSchema-instance"), ('xsi:schemaLocation',OSISNameSpace+' '+OSISSchemaLocation)] )
                xw.writeLineOpen( 'osisText', [('osisRefWork',"Bible"), ('xml:lang',controlDict["xmlLanguage"]), ('osisIDWork',controlDict["osisIDWork"])] )
                xw.setSectionName( 'Header' )
                writeHeader( xw )
                xw.setSectionName( 'Main' )
                writeOSISBook( xw, BBB, bookData )
                xw.writeLineClose( 'osisText' )
                xw.writeLineClose( 'osis' )
                xw.close()
                if validationSchema:
                    bookResults = xw.validate( validationSchema )
                    if bookResults[0] > validationResults[0]: validationResults = ( bookResults[0], validationResults[1], validationResults[2], )
                    if bookResults[1]: validationResults = ( validationResults[0], validationResults[1] + bookResults[1], validationResults[2], )
                    if bookResults[2]: validationResults = ( validationResults[0], validationResults[1], validationResults[2] + bookResults[2], )
        elif controlDict["osisFiles"]=="byBible": # write all the books into a single file
            if Globals.verbosityLevel > 2: print( _("  Exporting to OSIS XML format...") )
            filename = Globals.makeSafeFilename( controlDict["osisOutputFilename"] )
            xw = MLWriter( filename, outputFolder )
            xw.setHumanReadable( 'All' ) # Can be set to 'All', 'Header', or 'None' -- one output file went from None/Header=4.7MB to All=5.7MB
            xw.start()
            xw.writeLineOpen( 'osis', [('xmlns',OSISNameSpace), ('xmlns:xsi',"http://www.w3.org/2001/XMLSchema-instance"), ('xsi:schemaLocation',OSISNameSpace+' '+OSISSchemaLocation)] )
            xw.writeLineOpen( 'osisText', [('osisRefWork',"Bible"), ('xml:lang',controlDict["xmlLanguage"]), ('osisIDWork',controlDict["osisIDWork"])] )
            xw.setSectionName( 'Header' )
            writeHeader( xw )
            xw.setSectionName( 'Main' )
            for BBB,bookData in self.books.items(): # Process each Bible book
                writeOSISBook( xw, BBB, bookData )
            xw.writeLineClose( 'osisText' )
            xw.writeLineClose( 'osis' )
            xw.close()
            # Now create a zipped version
            filepath = os.path.join( outputFolder, filename )
            if Globals.verbosityLevel > 2: print( "  Zipping {} pickle file...".format( filename ) )
            zf = zipfile.ZipFile( filepath+'.zip', 'w', compression=zipfile.ZIP_DEFLATED )
            zf.write( filepath, filename )
            zf.close()
            if validationSchema: validationResults = xw.validate( validationSchema )
        else:
            logging.critical( "Unrecognized toOSIS control \"osisFiles\" = '{}'".format( controlDict["osisFiles"] ) )
        if unhandledMarkers:
            logging.error( "toOSISXML: Unhandled markers were {}".format( unhandledMarkers ) )
            if Globals.verbosityLevel > 1:
                print( "  " + _("ERROR: Unhandled toOSIS markers were {}").format( unhandledMarkers ) )
        if Globals.verbosityLevel > 2:
            print( "Need to find and look at an example where a new chapter isn't a new <p> to see how chapter eIDs should be handled there" )
        if validationSchema: return validationResults
        return True
    # end of BibleWriter.toOSISXML



    def toSwordModule( self, outputFolder=None, controlDict=None, validationSchema=None ):
        """
        Using settings from the given control file,
            converts the USFM information to a UTF-8 OSIS-XML-based Sword module.
        """
        if Globals.verbosityLevel > 1: print( "Running BibleWriter:toSwordModule..." )
        if Globals.debugFlag: assert( self.books )

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolder: outputFolder = "OutputFiles/BOS_Sword_Export/"
        if not os.access( outputFolder, os.F_OK ): os.makedirs( outputFolder ) # Make the empty folder if there wasn't already one there
        if not controlDict:
            controlDict, defaultControlFilename = {}, "To_OSIS_controls.txt"
            try:
                ControlFiles.readControlFile( defaultControlFolder, defaultControlFilename, controlDict )
            except:
                logging.critical( "Unable to read control dict {} from {}".format( defaultControlFilename, defaultControlFolder ) )
        self.__adjustControlDict( controlDict )

        import struct
        if Globals.debugFlag: assert( struct.calcsize("IH") == 6 ) # Six-byte format

        # Set-up our Bible reference system
        if controlDict['PublicationCode'] == "GENERIC":
            BOS = self.genericBOS
            BRL = self.genericBRL
        else:
            BOS = BibleOrganizationalSystem( controlDict["PublicationCode"] )
            BRL = BibleReferenceList( BOS, BibleObject=None )

        booksNamesSystemName = BOS.getOrganizationalSystemValue( 'booksNamesSystem' )
        if booksNamesSystemName and booksNamesSystemName!='None' and booksNamesSystemName!='Unknown': # default (if we know the book names system)
            getBookNameFunction = BOS.getBookName
            getBookAbbreviationFunction = BOS.getBookAbbreviation
        else: # else use our local functions from our deduced book names
            getBookNameFunction = self.getAssumedBookName # from USFMBible (which gets it from USFMBibleBook)
            getBookAbbreviationFunction = Globals.BibleBooksCodes.getOSISAbbreviation

        if 0:
            bookAbbrevDict, bookNameDict, bookAbbrevNameDict = {}, {}, {}
            for BBB in Globals.BibleBooksCodes.getAllReferenceAbbreviations(): # Pre-process the language booknames
                if BBB in controlDict and controlDict[BBB]:
                    bits = controlDict[BBB].split(',')
                    if len(bits)!=2: logging.error( _("toSwordModule: Unrecognized language book abbreviation and name for {}: '{}'").format( BBB, controlDict[BBB] ) )
                    bookAbbrev = bits[0].strip().replace('"','') # Remove outside whitespace then the double quote marks
                    bookName = bits[1].strip().replace('"','') # Remove outside whitespace then the double quote marks
                    bookAbbrevDict[bookAbbrev], bookNameDict[bookName], bookAbbrevNameDict[BBB] = BBB, BBB, (bookAbbrev,bookName,)
                    if ' ' in bookAbbrev: bookAbbrevDict[bookAbbrev.replace(' ','',1)] = BBB # Duplicate entries without the first space (presumably between a number and a name like 1 Kings)
                    if ' ' in bookName: bookNameDict[bookName.replace(' ','',1)] = BBB # Duplicate entries without the first space

        unhandledMarkers = set()


        # Let's write a Sword locale while we're at it
        self._writeSwordLocale( controlDict["xmlLanguage"], controlDict["LanguageName"], BOS, getBookNameFunction, os.path.join( outputFolder, "SwLocale-utf8.conf" ) )
        #SwLocFilepath = os.path.join( outputFolder, "SwLocale-utf8.conf" )
        #if Globals.verbosityLevel > 1: print( _("Writing Sword locale file {}...").format(SwLocFilepath) )
        #with open( SwLocFilepath, 'wt' ) as SwLocFile:
            #SwLocFile.write( '[Meta]\nName={}\n'.format(controlDict["xmlLanguage"]) )
            #SwLocFile.write( 'Description={}\n'.format(controlDict["LanguageName"]) )
            #SwLocFile.write( 'Encoding=UTF-8\n\n[Text]\n' )
            #for BBB in BOS.getBookList():
                #if BBB in self.books:
                    #SwLocFile.write( '{}={}\n'.format(Globals.BibleBooksCodes.getEnglishName_NR(BBB), getBookNameFunction(BBB) ) ) # Write the first English book name and the vernacular book name
            #SwLocFile.write( '\n[Book Abbrevs]\n' )
            #for BBB in BOS.getBookList():
                #if BBB in self.books:
                    #SwLocFile.write( '{}={}\n'.format(Globals.BibleBooksCodes.getEnglishName_NR(BBB).upper(), Globals.BibleBooksCodes.getSwordAbbreviation(BBB) ) ) # Write the UPPER CASE language book name and the Sword abbreviation

        # Make our other folders if necessary
        modsdFolder = os.path.join( outputFolder, "mods.d" )
        if not os.access( modsdFolder, os.F_OK ): os.mkdir( modsdFolder ) # Make the empty folder if there wasn't already one there
        modulesFolder = os.path.join( outputFolder, "modules" )
        if not os.access( modulesFolder, os.F_OK ): os.mkdir( modulesFolder ) # Make the empty folder if there wasn't already one there
        textsFolder = os.path.join( modulesFolder, "texts" )
        if not os.access( textsFolder, os.F_OK ): os.mkdir( textsFolder ) # Make the empty folder if there wasn't already one there
        rawTextFolder = os.path.join( textsFolder, "rawtext" )
        if not os.access( rawTextFolder, os.F_OK ): os.mkdir( rawTextFolder ) # Make the empty folder if there wasn't already one there
        lgFolder = os.path.join( rawTextFolder, controlDict["osisWork"].lower() )
        if not os.access( lgFolder, os.F_OK ): os.mkdir( lgFolder ) # Make the empty folder if there wasn't already one there

        toSwordGlobals = { 'currentID':0, "idStack":[], "verseRef":'', "XRefNum":0, "FootnoteNum":0, "lastRef":'', 'offset':0, 'length':0, "OneChapterOSISBookCodes":Globals.BibleBooksCodes.getOSISSingleChapterBooksList() } # These are our global variables


        def makeConfFile( modsdFolder, compressedFlag ):
            """ Make a conf file for the Sword modules. """
            emailAddress = contactName = "Unknown"
            adjustedProjectName = self.projectName.lower().replace( ' ', '_' )

            # Read the default conf file
            with open( os.path.join( defaultControlFolder, 'SwordProject.conf' ) ) as myFile: confText = myFile.read()

            # Do common text replacements
            # Unfortunately, we can only really make wild guesses without more detailed metadata
            # Of course, version should be the TEXT version not the PROGRAM version
            confText = confText.replace( '__ADJUSTED_PROJECT_NAME__', adjustedProjectName ).replace( '__PROJECT_NAME__', self.projectName ) \
                                .replace( '__EMAIL__', emailAddress ) \
                                .replace( '__NAME__', contactName ).replace( '__VERSION__', ProgVersion )
            confText = confText.replace('rawtext','ztext').replace('RawText','zText') if compressedFlag \
                                else confText.replace('CompressType=ZIP\n','')

            # Do known language replacements
            pnUpper = self.projectName.upper()
            if "INDONESIA" in pnUpper:
                confText = confText.replace( '__LANGUAGE__', 'id' )

            # Do replacements from SSF file
            if self.settingsDict:
                #print( "  Given Project name is", projectName )
                #print( "  Given Email is", emailAddress )
                #print( "  Given Name is", projectName )
                #if 'FullName' in self.settingsDict:
                    #print( "  SSF Full name (unused) is", self.settingsDict['FullName'] )
                if 'Name' in self.settingsDict:
                    #print( "  SSF Name is", self.settingsDict['Name'] )
                    confText = confText.replace( '__ABBREVIATION__', self.settingsDict['Name'] )
                if 'Language' in self.settingsDict:
                    #print( "  SSF Language is", self.settingsDict['Language'] )
                    confText = confText.replace( '__LANGUAGE__', self.settingsDict['Language'] )
                #if 'productName' in self.settingsDict:
                    #print( "  SSF Product name (unused) is", self.settingsDict['productName'] )
                #if 'LanguageIsoCode' in self.settingsDict:
                    #print( "  SSF Language Iso Code (unused) is", self.settingsDict['LanguageIsoCode'] )

            # Do exasperated replacements if there's any unknown fields left (coz we have no better info)
            confText = confText.replace( '__ABBREVIATION__', 'NONE' )
            confText = confText.replace( '__LANGUAGE__', 'UNKNOWN' )

            # Write the new file
            confFilename = adjustedProjectName + '.conf'
            confFilepath = os.path.join( modsdFolder, confFilename )
            with open( confFilepath, 'wt' ) as myFile: myFile.write( confText )
        # end of makeConfFile


        def writeIndexEntry( writerObject, indexFile ):
            """ Writes a newline to the main file and an entry to the index file. """
            writerObject.writeNewLine()
            writerObject._writeToBuffer( "IDX " ) # temp ..... XXXXXXX
            indexFile.write( struct.pack( "IH", toSwordGlobals['offset'], toSwordGlobals['length'] ) )
            toSwordGlobals['offset'] = writerObject.getFilePosition() # Get the new offset
            toSwordGlobals['length'] = 0 # Reset
        # end of toSwordModule.writeIndexEntry

        def writeSwordBook( writerObject, ix, BBB, bkData ):
            """ Writes a Bible book to the output files. """

            def checkText( textToCheck ):
                """Handle some general backslash codes and warn about any others still unprocessed."""

                def checkTextHelper( marker, helpText ):
                    """ Adjust the text to make the number of start and close markers equal. """
                    count1, count2 = helpText.count('\\'+marker+' '), helpText.count('\\'+marker+'*') # count open and close markers
                    while count1 < count2:
                        helpText = '\\'+marker+' ' + helpText
                        count1, count2 = helpText.count('\\'+marker+' '), helpText.count('\\'+marker+'*') # count open and close markers again
                    while count1 > count2:
                        helpText += '\\'+marker+'*'
                        count1, count2 = helpText.count('\\'+marker+' '), helpText.count('\\'+marker+'*') # count open and close markers again
                    if Globals.debugFlag: assert( count1 == count2 )
                    return helpText
                # end of toSwordModule.checkTextHelper

                adjText = textToCheck
                if '<<' in adjText or '>>' in adjText:
                    logging.warning( _("toSwordModule: Unexpected double angle brackets in {}: '{}' field is '{}'").format(toOSISGlobals["verseRef"],marker,textToCheck) )
                    adjText = adjText.replace('<<','“' ).replace('>>','”' )
                if '\\bk ' in adjText: adjText = checkTextHelper('bk',adjText).replace('\\bk ','<reference type="x-bookName">').replace('\\bk*','</reference>')
                if '\\add ' in adjText: adjText = checkTextHelper('add',adjText).replace('\\add ','<i>').replace('\\add*','</i>') # temp XXXXXX ...
                if '\\nd ' in adjText: adjText = checkTextHelper('nd',adjText).replace('\\nd ','<divineName>').replace('\\nd*','</divineName>')
                if '\\wj ' in adjText: adjText = checkTextHelper('wj',adjText).replace('\\wj ','<hi type="bold">').replace('\\wj*','</hi>') # XXXXXX temp ....
                if '\\sig ' in adjText: adjText = checkTextHelper('sig',adjText).replace('\\sig ','<b>').replace('\\sig*','</b>') # temp... XXXXXXX
                if '\\it ' in adjText: adjText = checkTextHelper('it',adjText).replace('\\it ','<hi type="italic">').replace('\\it*','</hi>')
                if '\\bd ' in adjText: adjText = checkTextHelper('bd',adjText).replace('\\bd ','<hi type="bold">').replace('\\bd*','</hi>')
                if '\\em ' in adjText: adjText = checkTextHelper('em',adjText).replace('\\em ','<hi type="bold">').replace('\\em*','</hi>')
                if '\\sc ' in adjText: adjText = checkTextHelper('sc',adjText).replace('\\sc ','<hi type="SMALLCAPS">').replace('\\sc*','</hi>') # XXXXXX temp ....
                if '\\' in adjText:
                    logging.error( _("toSwordModule: We still have some unprocessed backslashes for Sword in {}: '{}' field is '{}'").format(toSwordGlobals["verseRef"],marker,textToCheck) )
                    adjText = adjText.replace('\\','ENCODING ERROR HERE ' )
                return adjText
            # end of toSwordModule.checkText

            def processXRefsAndFootnotes( verse, extras ):
                """Convert cross-references and footnotes and return the adjusted verse text."""

                def processXRef( USFMxref ):
                    """
                    Return the OSIS code for the processed cross-reference (xref).

                    NOTE: The parameter here already has the /x and /x* removed.

                    \\x - \\xo 2:2: \\xt Lib 19:9-10; Diy 24:19.\\xt*\\x* (Backslashes are shown doubled here)
                        gives
                    <note type="crossReference" n="1">2:2: <reference>Lib 19:9-10; Diy 24:19.</reference></note> (Crosswire -- invalid OSIS -- which then needs to be converted)
                    <note type="crossReference" osisRef="Ruth.2.2" osisID="Ruth.2.2!crossreference.1" n="-"><reference type="source" osisRef="Ruth.2.2">2:2: </reference><reference osisRef="-">Lib 19:9-10</reference>; <reference osisRef="Ruth.Diy.24!:19">Diy 24:19</reference>.</note> (Snowfall)
                    \\x - \\xo 3:5: a \\xt Rum 11:1; \\xo b \\xt Him 23:6; 26:5.\\xt*\\x* is more complex still.
                    """
                    nonlocal BBB
                    toSwordGlobals["XRefNum"] += 1
                    OSISxref = '<note type="crossReference" osisRef="{}" osisID="{}!crossreference.{}">'.format(toSwordGlobals["verseRef"],toSwordGlobals["verseRef"],toSwordGlobals["XRefNum"])
                    for j,token in enumerate(USFMxref.split('\\')):
                        #print( "processXRef", j, "'"+token+"'", "from", '"'+USFMxref+'"' )
                        if j==0: # The first token (but the x has already been removed)
                            rest = token.strip()
                            if rest != '-':
                                logging.warning( _("toSwordModule: We got something else here other than hyphen (probably need to do something with it): {} '{}' from '{}'").format(chapterRef, token, text) )
                        elif token.startswith('xo '): # xref reference follows
                            adjToken = token[3:].strip()
                            if adjToken.endswith(' a'): adjToken = adjToken[:-2] # Remove any 'a' suffix (occurs when a cross-reference has multiple (a and b) parts
                            if adjToken.endswith(':'): adjToken = adjToken[:-1] # Remove any final colon (this is a language dependent hack)
                            adjToken = getBookAbbreviationFunction(BBB) + ' ' + adjToken # Prepend the vernacular book abbreviation
                            osisRef = BRL.parseToOSIS( adjToken )
                            if osisRef is not None:
                                OSISxref += '<reference type="source" osisRef="{}">{}</reference>'.format(osisRef,token[3:])
                                if not BRL.containsReference( BBB, currentChapterNumberString, verseNumberString ):
                                    logging.error( _("toSwordModule: Cross-reference at {} {}:{} seems to contain the wrong self-reference '{}'").format(BBB,currentChapterNumberString,verseNumberString, token) )
                        elif token.startswith('xt '): # xref text follows
                            xrefText = token[3:]
                            finalPunct = ''
                            while xrefText[-1] in (' ,;.'): finalPunct = xrefText[-1] + finalPunct; xrefText = xrefText[:-1]
                            #adjString = xrefText[:-6] if xrefText.endswith( ' (LXX)' ) else xrefText # Sorry, this is a crude hack to avoid unnecessary error messages
                            osisRef = BRL.parseToOSIS( xrefText )
                            if osisRef is not None:
                                OSISxref += '<reference type="source" osisRef="{}">{}</reference>'.format(osisRef,xrefText+finalPunct)
                        elif token.startswith('x '): # another whole xref entry follows
                            rest = token[2:].strip()
                            if rest != '-':
                                logging.warning( _("toSwordModule: We got something else here other than hyphen (probably need to do something with it): {} '{}' from '{}'").format(chapterRef, token, text) )
                        elif token in ('xt*', 'x*'):
                            pass # We're being lazy here and not checking closing markers properly
                        else:
                            logging.warning( _("toSwordModule: Unprocessed '{}' token in {} xref '{}'").format(token, toSwordGlobals["verseRef"], USFMxref) )
                    OSISxref += '</note>'
                    return OSISxref
                # end of toSwordModule.processXRef

                def processFootnote( USFMfootnote ):
                    """
                    Return the OSIS code for the processed footnote.

                    NOTE: The parameter here already has the /f and /f* removed.

                    \\f + \\fr 1:20 \\ft Su ka kaluwasan te Nawumi ‘keupianan,’ piru ka kaluwasan te Mara ‘masakit se geyinawa.’\\f* (Backslashes are shown doubled here)
                        gives
                    <note n="1">1:20 Su ka kaluwasan te Nawumi ‘keupianan,’ piru ka kaluwasan te Mara ‘masakit se geyinawa.’</note> (Crosswire)
                    <note osisRef="Ruth.1.20" osisID="Ruth.1.20!footnote.1" n="+"><reference type="source" osisRef="Ruth.1.20">1:20 </reference>Su ka kaluwasan te Nawumi ‘keupianan,’ piru ka kaluwasan te Mara ‘masakit se geyinawa.’</note> (Snowfall)
                    """
                    toSwordGlobals["FootnoteNum"] += 1
                    OSISfootnote = '<note osisRef="{}" osisID="{}!footnote.{}">'.format(toSwordGlobals["verseRef"],toSwordGlobals["verseRef"],toSwordGlobals["FootnoteNum"])
                    for j,token in enumerate(USFMfootnote.split('\\')):
                        #print( "processFootnote", j, token, USFMfootnote )
                        if j==0: continue # ignore the + for now
                        elif token.startswith('fr '): # footnote reference follows
                            adjToken = token[3:].strip()
                            if adjToken.endswith(':'): adjToken = adjToken[:-1] # Remove any final colon (this is a language dependent hack)
                            adjToken = getBookAbbreviationFunction(BBB) + ' ' + adjToken # Prepend the vernacular book abbreviation
                            osisRef = BRL.parseToOSIS( adjToken )
                            if osisRef is not None:
                                OSISfootnote += '<reference osisRef="{}" type="source">{}</reference>'.format(osisRef,token[3:])
                                if not BRL.containsReference( BBB, currentChapterNumberString, verseNumberString ):
                                    logging.error( _("toSwordModule: Footnote at {} {}:{} seems to contain the wrong self-reference '{}'").format(BBB,currentChapterNumberString,verseNumberString, token) )
                        elif token.startswith('ft '): # footnote text follows
                            OSISfootnote += token[3:]
                        elif token.startswith('fq ') or token.startswith('fqa '): # footnote quote follows -- NOTE: We also assume here that the next marker closes the fq field
                            OSISfootnote += '<catchWord>{}</catchWord>'.format(token[3:]) # Note that the trailing space goes in the catchword here -- seems messy
                        elif token in ('ft*','ft* ','fq*','fq* ','fqa*','fqa* '):
                            pass # We're being lazy here and not checking closing markers properly
                        else:
                            logging.warning( _("toSwordModule: Unprocessed '{}' token in {} footnote '{}'").format(token, toSwordGlobals["verseRef"], USFMfootnote) )
                    OSISfootnote += '</note>'
                    #print( '', OSISfootnote )
                    return OSISfootnote
                # end of toSwordModule.processFootnote

                while '\\x ' in verse and '\\x*' in verse: # process cross-references (xrefs)
                    ix1 = verse.index('\\x ')
                    ix2 = verse.find('\\x* ') # Note the extra space here at the end
                    if ix2 == -1: # Didn't find it so must be no space after the asterisk
                        ix2 = verse.index('\\x*')
                        ix2b = ix2 + 3 # Where the xref ends
                        logging.warning( _("toSwordModule: No space after xref entry in {}").format(toSwordGlobals["verseRef"]) )
                    else: ix2b = ix2 + 4
                    xref = verse[ix1+3:ix2]
                    osisXRef = processXRef( xref )
                    #print( osisXRef )
                    verse = verse[:ix1] + osisXRef + verse[ix2b:]
                while '\\f ' in verse and '\\f*' in verse: # process footnotes
                    ix1 = verse.index('\\f ')
                    ix2 = verse.find('\\f*')
#                    ix2 = verse.find('\\f* ') # Note the extra space here at the end -- doesn't always work if there's two footnotes within one verse!!!
#                    if ix2 == -1: # Didn't find it so must be no space after the asterisk
#                        ix2 = verse.index('\\f*')
#                        ix2b = ix2 + 3 # Where the footnote ends
#                        #logging.warning( 'toSwordModule: No space after footnote entry in {}'.format(toSwordGlobals["verseRef"] )
#                    else: ix2b = ix2 + 4
                    footnote = verse[ix1+3:ix2]
                    osisFootnote = processFootnote( footnote )
                    #print( osisFootnote )
                    verse = verse[:ix1] + osisFootnote + verse[ix2+3:]
#                    verse = verse[:ix1] + osisFootnote + verse[ix2b:]
                return verse
            # end of toSwordModule.processXRefsAndFootnotes

            def writeVerseStart( writerObject, BBB, chapterRef, verseNumberString ):
                """
                Processes and writes a verse to the OSIS XML writerObject.
                    <verse sID="Gen.1.31" osisID="Gen.1.31"/>
                    Ne nakita te Manama ka langun ne innimu rin wey natelesan amana sikandin. Ne nasagkup e wey napawe, ne seeye ka igkeen-em ne aldew.
                    <verse eID="Gen.1.31"/>

                Has to handle joined verses, e.g.,
                    <verse sID="Esth.9.16" osisID="Esth.9.16 Esth.9.17"/>text<verse eID="Esth.9.16"/> (Crosswire)
                    <verse sID="Esth.9.16-Esth.9.17" osisID="Esth.9.16 Esth.9.17" n="16-17"/>text<verse eID="Esth.9.16-Esth.9.17"/> (Snowfall)
                """
                nonlocal haveOpenVsID
                osisID = sID = toSwordGlobals["verseRef"] # default
                if haveOpenVsID != False: # Close the previous verse
                    writerObject.writeLineOpenSelfclose( 'verse', ('eID',haveOpenVsID) )
                #verseNumberString = text.split()[0] # Get the first token which is the first number
                #verseText = text[len(verseNumberString)+1:].lstrip() # Get the rest of the string which is the verse text
                if '-' in verseNumberString:
                    bits = verseNumberString.split('-')
                    if (len(bits)!=2 or not bits[0].isdigit() or not bits[1].isdigit()):
                        logging.critical( _("toSwordModule: Doesn't handle verse number of form '{}' yet for {}").format(verseNumberString,chapterRef) )
                    toSwordGlobals["verseRef"]  = chapterRef + '.' + bits[0]
                    verseRef2 = chapterRef + '.' + bits[1]
                    sID    = toSwordGlobals["verseRef"] + '-' + verseRef2
                    osisID = toSwordGlobals["verseRef"] + ' ' + verseRef2
                elif ',' in verseNumberString:
                    bits = verseNumberString.split(',')
                    if (len(bits)<2 or not bits[0].isdigit() or not bits[1].isdigit()):
                        logging.critical( _("toSwordModule: Doesn't handle verse number of form '{}' yet for {}").format(verseNumberString,chapterRef) )
                    sID = toSwordGlobals["verseRef"] = chapterRef + '.' + bits[0]
                    osisID = ''
                    for bit in bits: # Separate the OSIS ids by spaces
                        osisID += ' ' if osisID else ''
                        osisID += chapterRef + '.' + bit
                    #print( "Hey comma verses '{}' '{}'".format( sID, osisID ) )
                elif verseNumberString.isdigit():
                    sID = osisID = toSwordGlobals["verseRef"] = chapterRef + '.' + verseNumberString
                else:
                    logging.critical( _("toSwordModule: Doesn't handle verse number of form '{}' yet for {}").format(verseNumberString,chapterRef) )
                writerObject.writeLineOpenSelfclose( 'verse', [('sID',sID), ('osisID',osisID)] ); haveOpenVsID = sID
                #adjText = processXRefsAndFootnotes( verseText, extras )
                #writerObject.writeLineText( checkText(adjText), noTextCheck=True )
                ##writerObject.writeLineOpenSelfclose( 'verse', ('eID',sID) )
                #writeIndexEntry( writerObject, indexFile )
            # end of toSwordModule.writeVerseStart

            def closeAnyOpenMajorSection():
                """ Close a <div> if it's open. """
                nonlocal haveOpenMajorSection
                if haveOpenMajorSection:
                    writerObject.writeLineClose( 'div' )
                    haveOpenMajorSection = False
            # end of toSwordModule.closeAnyOpenMajorSection

            def closeAnyOpenSection():
                """ Close a <div> if it's open. """
                nonlocal haveOpenSection
                if haveOpenSection:
                    writerObject.writeLineClose( 'div' )
                    haveOpenSection = False
            # end of toSwordModule.closeAnyOpenSection

            def closeAnyOpenSubsection():
                """ Close a <div> if it's open. """
                nonlocal haveOpenSubsection
                if haveOpenSubsection:
                    writerObject.writeLineClose( 'div' )
                    haveOpenSubsection = False
            # end of toSwordModule.closeAnyOpenSubsection

            def closeAnyOpenParagraph():
                """ Close a <p> if it's open. """
                nonlocal haveOpenParagraph
                if haveOpenParagraph:
                    writerObject.writeLineOpenSelfclose( 'div', [('eID',toSwordGlobals['idStack'].pop()), ('type',"paragraph")] )
                    haveOpenParagraph = False
            # end of toSwordModule.closeAnyOpenParagraph

            def closeAnyOpenLG():
                """ Close a <lg> if it's open. """
                nonlocal haveOpenLG
                if haveOpenLG:
                    writerObject.writeLineClose( 'lg' )
                    haveOpenLG = False
            # end of toSwordModule.closeAnyOpenLG

            def closeAnyOpenL():
                """ Close a <l> if it's open. """
                nonlocal haveOpenL
                if haveOpenL:
                    writerObject.writeLineClose( 'l' )
                    haveOpenL = False
            # end of toSwordModule.closeAnyOpenL

            def getNextID():
                """ Returns the next sID sequence code. """
                toSwordGlobals['currentID'] += 1
                return "gen{}".format(toSwordGlobals['currentID'])
            # end of toSwordModule.getNextID

            def getSID():
                """ Returns a tuple containing ('sID', getNextID() ). """
                ID = getNextID()
                toSwordGlobals['idStack'].append( ID )
                return ('sID', ID )
            # end of toSwordModule.getSID

            bookRef = Globals.BibleBooksCodes.getOSISAbbreviation( BBB ) # OSIS book name
            writerObject.writeLineOpen( 'div', [('osisID',bookRef), getSID(), ('type',"book")] )
            haveOpenIntro = haveOpenOutline = haveOpenMajorSection = haveOpenSection = haveOpenSubsection = needChapterEID = haveOpenParagraph = haveOpenVsID = haveOpenLG = haveOpenL = False
            lastMarker = unprocessedMarker = ''
            #chapterNumberString = None
            C = V = "0"
            for verseDataEntry in bkData._processedLines: # Process internal Bible data lines
                marker, text, extras = verseDataEntry.getMarker(), verseDataEntry.getAdjustedText(), verseDataEntry.getExtras()
                #print( BBB, marker, text )
                #print( " ", haveOpenIntro, haveOpenOutline, haveOpenMajorSection, haveOpenSection, haveOpenSubsection, needChapterEID, haveOpenParagraph, haveOpenVsID, haveOpenLG, haveOpenL )
                #print( toSwordGlobals['idStack'] )
                if marker in oftenIgnoredIntroMarkers: continue # Just ignore these lines
                #if marker in ( 'id', 'ide', 'h', 'mt2', 'c#', ): continue # We just ignore these markers
                elif marker=='mt1':
                    if text: writerObject.writeLineOpenClose( 'title', checkText(text) )
                elif marker=='mt2':
                    if text: writerObject.writeLineOpenClose( 'title', checkText(text) )
                elif marker=='is1' or marker=='imt1':
                    if haveOpenIntro: # already -- assume it's a second one
                        closeAnyOpenParagraph()
                        writerObject.writeLineOpenSelfclose( 'div', [('eID',toSwordGlobals['idStack'].pop()), ('type',"introduction")] )
                        haveOpenIntro = False
                    writerObject.writeLineOpen( 'div', [getSID(), ('type',"introduction")] )
                    if text: writerObject.writeLineOpenClose( 'title', checkText(text) ) # Introduction heading
                    else:
                        logging.error( _("toSwordModule: {} Have a blank {} field—ignoring it").format( toSwordGlobals["verseRef"], marker ) )
                    haveOpenIntro = True
                    chapterRef = bookRef + '.0' # Not used by OSIS
                    toSwordGlobals["verseRef"] = chapterRef + '.0' # Not used by OSIS
                elif marker=='ip':
                    if not haveOpenIntro: # Shouldn't happen but we'll try our best
                        logging.error( "toSwordModule: {} Have an ip not in an introduction section—opening an intro section".format( toSwordGlobals["verseRef"] ) )
                        writerObject.writeLineOpen( 'div', ('type',"introduction") )
                        haveOpenIntro = True
                    closeAnyOpenParagraph()
                    writerObject.writeLineOpenSelfclose( 'div', [getSID(), ('type',"paragraph")] )
                    writerObject.writeLineText( checkText(text), noTextCheck=True ) # Sometimes there's text
                    haveOpenParagraph = True
                elif marker=='iot':
                    if not haveOpenIntro: # Shouldn't happen but we'll try our best
                        logging.error( "toSwordModule: {} Have a iot not in an introduction section—opening an intro section".format( toSwordGlobals["verseRef"] ) )
                        writerObject.writeLineOpen( 'div', ('type',"introduction") )
                        haveOpenIntro = True
                    if haveOpenOutline:
                        writerObject.writeLineClose( 'list' )
                        writerObject.writeLineOpenSelfclose( 'div', [('eID',toSwordGlobals['idStack'].pop()), ('type',"outline")] )
                        haveOpenOutline = False
                    if haveOpenSection:
                        logging.error( "toSwordModule: {} Not handled yet iot".format( toSwordGlobals["verseRef"] ) )
                    closeAnyOpenParagraph()
                    writerObject.writeLineOpenSelfclose( 'div', [getSID(), ('type',"outline")] )
                    if text: writerObject.writeLineOpenClose( 'title', checkText(text) )
                    writerObject.writeLineOpen( 'list' )
                    haveOpenOutline = True
                elif marker=='io1':
                    #if haveOpenIntro:
                    #    closeAnyOpenParagraph()
                    #    writerObject.writeLineOpenSelfclose( 'div', [('eID',toSwordGlobals['idStack'].pop()), ('type',"introduction")] )
                    #    haveOpenIntro = False
                    if not haveOpenIntro: # Shouldn't happen but we'll try our best
                        logging.error( "toSwordModule: {} Have an io1 not in an introduction section—opening an intro section".format( toSwordGlobals["verseRef"] ) )
                        writerObject.writeLineOpen( 'div', ('type',"introduction") )
                        haveOpenIntro = True
                    if not haveOpenOutline: # Shouldn't happen but we'll try our best
                        logging.warning( _("toSwordModule: {} Have an io1 not in an outline section—opening an outline section".format(toSwordGlobals["verseRef"]) ) )
                        closeAnyOpenParagraph()
                        writerObject.writeLineOpenSelfclose( 'div', [getSID(), ('type',"outline")] )
                        writerObject.writeLineOpen( 'list' )
                        haveOpenOutline = True
                    if text: writerObject.writeLineOpenClose( 'item', checkText(text) )
                elif marker=='io2':
                    if not haveOpenIntro:
                        logging.error( _("toSwordModule: {} Have an io2 not in an introduction section").format( toSwordGlobals["verseRef"] ) )
                    if not haveOpenOutline:
                        logging.error( _("toSwordModule: {} Have an io2 not in an outline section").format( toSwordGlobals["verseRef"] ) )
                    if text: writerObject.writeLineOpenClose( 'item', checkText(text) ) # TODO: Shouldn't this be different from an io1???
                elif marker=='c':
                    if haveOpenOutline:
                        if text!='1' and not text.startswith('1 '):
                            logging.error( _("toSwordModule: {} This should normally be chapter 1 to close the introduction (got '{}')").format( toSwordGlobals["verseRef"], text ) )
                        writerObject.writeLineClose( 'list' )
                        writerObject.writeLineOpenSelfclose( 'div', [('eID',toSwordGlobals['idStack'].pop()), ('type',"outline")] )
                        haveOpenOutline = False
                    if haveOpenIntro:
                        if text!='1' and not text.startswith('1 '):
                            logging.error( _("toSwordModule: {} This should normally be chapter 1 to close the introduction (got '{}')").format( toSwordGlobals["verseRef"], text ) )
                        closeAnyOpenParagraph()
                        writerObject.writeLineOpenSelfclose( 'div', [('eID',toSwordGlobals['idStack'].pop()), ('type',"introduction")] )
                        haveOpenIntro = False
                    closeAnyOpenLG()
                    if needChapterEID:
                        writerObject.writeLineOpenSelfclose( 'chapter', ('eID',chapterRef) ) # This is an end milestone marker
                    writeIndexEntry( writerObject, ix )
                    C, V = text, "0"
                    currentChapterNumberString, verseNumberString = text, '0'
                    if not currentChapterNumberString.isdigit():
                        logging.critical( _("toSwordModule: Can't handle non-digit '{}' chapter number yet").format(text) )
                    chapterRef = bookRef + '.' + checkText(currentChapterNumberString)
                    writerObject.writeLineOpenSelfclose( 'chapter', [('osisID',chapterRef), ('sID',chapterRef)] ) # This is a milestone marker
                    needChapterEID = True
                    writeIndexEntry( writerObject, ix )
                elif marker == 'c#': # Chapter number added for printing
                    pass # Just ignore it completely
                elif marker=='ms1':
                    if haveOpenParagraph:
                        closeAnyOpenLG()
                        closeAnyOpenParagraph()
                    closeAnyOpenSubsection()
                    closeAnyOpenSection()
                    closeAnyOpenMajorSection()
                    writerObject.writeLineOpen( 'div', ('type',"majorSection") )
                    haveOpenMajorSection = True
                    if text: writerObject.writeLineOpenClose( 'title', checkText(text) ) # Section heading
                    else:
                        logging.info( _("toSwordModule: Blank ms1 section heading encountered after {}").format( toSwordGlobals["verseRef"] ) )
                elif marker=='s1':
                    if haveOpenParagraph:
                        closeAnyOpenLG()
                        closeAnyOpenParagraph()
                    closeAnyOpenSubsection()
                    closeAnyOpenSection()
                    writerObject.writeLineOpen( 'div', [getSID(), ('type',"section")] )
                    haveOpenSection = True
                    if text: writerObject.writeLineOpenClose( 'title', checkText(text) ) # Section heading
                    else:
                        logging.info( _("toSwordModule: Blank s1 section heading encountered after {}:{}").format( currentChapterNumberString, verseNumberString ) )
                elif marker=='s2':
                    if haveOpenParagraph:
                        closeAnyOpenLG()
                        closeAnyOpenParagraph()
                    closeAnyOpenSubsection()
                    writerObject.writeLineOpen( 'div', ('type', "subSection") )
                    haveOpenSubsection = True
                    if text: writerObject.writeLineOpenClose( 'title', checkText(text) ) # Section heading
                    else:
                        logging.info( _("toSwordModule: Blank s2 section heading encountered after {}:{}").format( currentChapterNumberString, verseNumberString ) )
                elif marker=='s3':
                    if haveOpenParagraph:
                        closeAnyOpenLG()
                        closeAnyOpenParagraph()
                    closeAnyOpenSubsection()
                    writerObject.writeLineOpen( 'div', ('type', "subSection") )
                    haveOpenSubsection = True
                    if text: writerObject.writeLineOpenClose( 'title', checkText(text) ) # Section heading
                    else:
                        logging.info( _("toSwordModule: Blank s3 section heading encountered after {}:{}").format( currentChapterNumberString, verseNumberString ) )
                elif marker=='s4':
                    if haveOpenParagraph:
                        closeAnyOpenLG()
                        closeAnyOpenParagraph()
                    closeAnyOpenSubsection()
                    writerObject.writeLineOpen( 'div', ('type', "subSection") )
                    haveOpenSubsection = True
                    if text: writerObject.writeLineOpenClose( 'title', checkText(text) ) # Section heading
                    else:
                        logging.info( _("toSwordModule: Blank s4 section heading encountered after {}:{}").format( currentChapterNumberString, verseNumberString ) )
                elif marker=='mr':
                    # Should only follow a ms1 I think
                    if haveOpenParagraph or haveOpenSection or not haveOpenMajorSection: logging.error( _("toSwordModule: Didn't expect major reference 'mr' marker after {}").format(toSwordGlobals["verseRef"]) )
                    if text: writerObject.writeLineOpenClose( 'title', checkText(text), ('type',"parallel") ) # Section cross-reference
                elif marker=='r':
                    # Should only follow a s1 I think
                    if haveOpenParagraph or not haveOpenSection: logging.error( _("toSwordModule: Didn't expect reference 'r' marker after {}").format(toSwordGlobals["verseRef"]) )
                    if text: writerObject.writeLineOpenClose( 'title', checkText(text), ('type',"parallel") ) # Section cross-reference
                elif marker=='p':
                    closeAnyOpenLG()
                    closeAnyOpenParagraph()
                    if not haveOpenSection:
                        writerObject.writeLineOpenSelfclose( 'div', [getSID(), ('type',"section")] )
                        haveOpenSection = True
                    adjustedText = processXRefsAndFootnotes( text, extras )
                    writerObject.writeLineOpenSelfclose( 'div', [getSID(), ('type',"paragraph")] )
                    writerObject.writeLineText( checkText(adjustedText), noTextCheck=True ) # Sometimes there's text
                    haveOpenParagraph = True
                elif marker=='v':
                    #if not chapterNumberString: # Some single chapter books don't have an explicit c marker
                    #    if Globals.debugFlag: assert( BBB in Globals.BibleBooksCodes.getSingleChapterBooksList() )
                    verseNumberString = text
                    if not haveOpenL: closeAnyOpenLG()
                    V = text
                    writeVerseStart( writerObject, BBB, chapterRef, verseNumberString )
                    #closeAnyOpenL()
                elif marker in ('v~','p~',):
                    #if not haveOpenL: closeAnyOpenLG()
                    #writeVerseStart( writerObject, ix, BBB, chapterRef, text )
                    adjText = processXRefsAndFootnotes( text, extras )
                    writerObject.writeLineText( checkText(adjText), noTextCheck=True )
                    #writerObject.writeLineOpenSelfclose( 'verse', ('eID',sID) )
                    writeIndexEntry( writerObject, ix )
                    closeAnyOpenL()
                elif marker in ('q1','q2','q3','q4',):
                    qLevel = marker[1]
                    if not haveOpenLG:
                        writerObject.writeLineOpen( 'lg' )
                        haveOpenLG = True
                    if text:
                        adjustedText = processXRefsAndFootnotes( text, extras )
                        writerObject.writeLineOpenClose( 'l', checkText(adjustedText), ('level',qLevel), noTextCheck=True )
                    else: # No text -- this q1 applies to the next marker
                        writerObject.writeLineOpen( 'l', ('level',qLevel) )
                        haveOpenL = True
                elif marker=='m': # Margin/Flush-left paragraph
                    closeAnyOpenL()
                    closeAnyOpenLG()
                    if text: writerObject.writeLineText( checkText(text) )
                elif marker=='b': # Blank line
                        # Doesn't seem that OSIS has a way to encode this presentation element
                        writerObject.writeNewLine() # We'll do this for now
                else:
                    if text:
                        logging.critical( "toSwordModule: lost text in {} field in {} {}:{} {}".format( marker, BBB, C, V, repr(text) ) )
                        #if Globals.debugFlag: halt
                    if extras:
                        logging.critical( "toSwordModule: lost extras in {} field in {} {}:{}".format( marker, BBB, C, V ) )
                        #if Globals.debugFlag: halt
                    unhandledMarkers.add( marker )
                if extras and marker not in ('v~','p~',): logging.critical( "toSwordModule: extras not handled for {} at {} {}:{}".format( marker, BBB, C, V ) )
                lastMarker = marker
            if (haveOpenIntro or haveOpenOutline or haveOpenLG or haveOpenL or unprocessedMarker):
                logging.error( "toSwordModule: a {} {} {} {} {}".format( haveOpenIntro, haveOpenOutline, haveOpenLG, haveOpenL, unprocessedMarker ) )
                logging.error( "toSwordModule: b {} {}:{}".format( BBB, currentChapterNumberString, verseNumberString ) )
                logging.error( "toSwordModule: c {} = '{}'".format( marker, text ) )
                logging.error( "toSwordModule: d These shouldn't be open here" )
            if needChapterEID:
                writerObject.writeLineOpenSelfclose( 'chapter', ('eID',chapterRef) ) # This is an end milestone marker
            if haveOpenParagraph:
                closeAnyOpenLG()
                closeAnyOpenParagraph()
            closeAnyOpenSection()
            closeAnyOpenMajorSection()
            writerObject.writeLineClose( 'div' ) # Close book division
            writerObject.writeNewLine()
        # end of toSwordModule.writeSwordBook

        # An uncompressed Sword module consists of a .conf file
        #   plus ot and nt XML files with binary indexes ot.vss and nt.vss (containing 6-byte chunks = 4-byte offset, 2-byte length)
        if Globals.verbosityLevel > 2: print( _("  Exporting to Sword modified-OSIS XML format...") )
        xwOT = MLWriter( 'ot', lgFolder )
        xwNT = MLWriter( 'nt', lgFolder )
        xwOT.setHumanReadable( 'NLSpace', indentSize=5 ) # Can be set to 'All', 'Header', or 'None'
        xwNT.setHumanReadable( 'NLSpace', indentSize=5 ) # Can be set to 'All', 'Header', or 'None'
        xwOT.start( noAutoXML=True ); xwNT.start( noAutoXML=True )
        toSwordGlobals['length'] = xwOT.writeLineOpenSelfclose( 'milestone', [('type',"x-importer"), ('subtype',"x-BibleWriter.py"), ('n',"${} $".format(ProgVersion))] )
        toSwordGlobals['length'] = xwNT.writeLineOpenSelfclose( 'milestone', [('type',"x-importer"), ('subtype',"x-BibleWriter.py"), ('n',"${} $".format(ProgVersion))] )
        xwOT.setSectionName( 'Main' ); xwNT.setSectionName( 'Main' )
        with open( os.path.join( lgFolder, 'ot.vss' ), 'wb' ) as ixOT, open( os.path.join( lgFolder, 'nt.vss' ), 'wb' ) as ixNT:
            ixOT.write( struct.pack( "IH", 0, 0 ) ) # Write the first dummy entry
            ixNT.write( struct.pack( "IH", 0, 0 ) ) # Write the first dummy entry
            writeIndexEntry( xwOT, ixOT ) # Write the second entry pointing to the opening milestone
            writeIndexEntry( xwNT, ixNT ) # Write the second entry pointing to the opening milestone
            for BBB,bookData in self.books.items(): # Process each Bible book
                if Globals.BibleBooksCodes.isOldTestament_NR( BBB ):
                    xw = xwOT; ix = ixOT
                elif Globals.BibleBooksCodes.isNewTestament_NR( BBB ):
                    xw = xwNT; ix = ixNT
                else:
                    logging.critical( _("toSwordModule: Sword module writer doesn't know how to encode {} book or appendix").format(BBB) )
                    continue
                writeSwordBook( xw, ix, BBB, bookData )
        xwOT.close(); xwNT.close()
        if unhandledMarkers:
            logging.error( "toSwordModule: Unhandled markers were {}".format( unhandledMarkers ) )
            if Globals.verbosityLevel > 1:
                print( "  " + _("ERROR: Unhandled toSwordModule markers were {}").format( unhandledMarkers ) )
        makeConfFile( modsdFolder, compressedFlag=False ) # Create the conf (settings) file
        if validationSchema:
            OTresults= xwOT.validate( validationSchema )
            NTresults= xwNT.validate( validationSchema )
            return OTresults and NTresults
        return True
    #end of BibleWriter.toSwordModule



    def totheWord( self, outputFolder=None, controlDict=None ):
        """
        Using settings from the given control file,
            converts the USFM information to a UTF-8 TheWord file.

        This format is roughly documented at http://www.theword.net/index.php?article.tools&l=english
        """
        from TheWordBible import theWordOTBookLines, theWordNTBookLines, theWordBookLines, resetTheWordMargins, theWordHandleIntroduction, theWordComposeVerseLine
        if Globals.verbosityLevel > 1: print( "Running BibleWriter:totheWord..." )
        if Globals.debugFlag: assert( self.books )

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolder: outputFolder = "OutputFiles/BOS_theWord_" + ("Reexport/" if self.objectTypeString=="theWord" else "Export/")
        if not os.access( outputFolder, os.F_OK ): os.makedirs( outputFolder ) # Make the empty folder if there wasn't already one there
        # ControlDict is not used (yet)
        if not controlDict:
            controlDict, defaultControlFilename = {}, "To_TheWord_controls.txt"
            try:
                ControlFiles.readControlFile( defaultControlFolder, defaultControlFilename, controlDict )
            except:
                pass
                #logging.critical( "Unable to read control dict {} from {}".format( defaultControlFilename, defaultControlFolder ) )
        #self.__adjustControlDict( controlDict )


        def writeTWBook( writerObject, BBB, ourGlobals ):
            """
            Writes a book to the theWord writerObject file.
            """
            nonlocal lineCount
            bkData = self.books[BBB] if BBB in self.books else None
            #print( bkData._processedLines )
            verseList = BOS.getNumVersesList( BBB )
            numC, numV = len(verseList), verseList[0]

            resetTheWordMargins( ourGlobals )
            if bkData: # write book headings (stuff before chapter 1)
                ourGlobals['line'] = theWordHandleIntroduction( BBB, bkData, ourGlobals )

            # Write the verses (whether or not they're populated)
            C = V = 1
            ourGlobals['lastLine'] = None
            while True:
                verseData, composedLine = None, ''
                if bkData:
                    try:
                        result = bkData.getCVRef( (BBB,str(C),str(V),) )
                        verseData, context = result
                    except KeyError: composedLine = '(-)' # assume it was a verse bridge (or something)
                    # Handle some common versification anomalies
                    if (BBB,C,V) == ('JN3',1,14): # Add text for v15 if it exists
                        try:
                            result15 = bkData.getCVRef( ('JN3','1','15',) )
                            verseData15, context15 = result15
                            verseData.extend( verseData15 )
                        except KeyError: pass #  just ignore it
                    elif (BBB,C,V) == ('REV',12,17): # Add text for v15 if it exists
                        try:
                            result18 = bkData.getCVRef( ('REV','12','18',) )
                            verseData18, context18 = result18
                            verseData.extend( verseData18 )
                        except KeyError: pass #  just ignore it
                if verseData: composedLine = theWordComposeVerseLine( BBB, C, V, verseData, ourGlobals )
                assert( '\n' not in composedLine ) # This would mess everything up
                #print( BBB, C, V, repr(composedLine) )
                if C!=1 or V!=1: # Stay one line behind (because paragraph indicators get appended to the previous line)
                    assert( '\n' not in ourGlobals['lastLine'] ) # This would mess everything up
                    writerObject.write( ourGlobals['lastLine'] + '\n' ) # Write it whether or not we got data
                    lineCount += 1
                ourGlobals['lastLine'] = composedLine
                V += 1
                if V > numV:
                    C += 1
                    if C > numC:
                        break
                    else: # next chapter only
                        numV = verseList[C-1]
                        V = 1
            # Write the last line of the file
            assert( '\n' not in ourGlobals['lastLine'] ) # This would mess everything up
            writerObject.write( ourGlobals['lastLine'] + '\n' ) # Write it whether or not we got data
            lineCount += 1
        # end of totheWord.writeTWBook


        # Set-up their Bible reference system
        BOS = BibleOrganizationalSystem( "GENERIC-KJV-66-ENG" )
        #BRL = BibleReferenceList( BOS, BibleObject=None )

        # Try to figure out if it's an OT/NT or what (allow for up to 6 extra books like FRT,GLO, etc.)
        if len(self) <= (39+6) and 'GEN' in self and 'MAT' not in self:
            testament, extension, startBBB, endBBB = 'OT', '.ot', 'GEN', 'MAL'
            booksExpected, textLineCountExpected, checkTotals = 39, 23145, theWordOTBookLines
        elif len(self) <= (27+6) and 'MAT' in self and 'GEN' not in self:
            testament, extension, startBBB, endBBB = 'NT', '.nt', 'MAT', 'REV'
            booksExpected, textLineCountExpected, checkTotals = 27, 7957, theWordNTBookLines
        else: # assume it's an entire Bible
            testament, extension, startBBB, endBBB = 'BOTH', '.ont', 'GEN', 'REV'
            booksExpected, textLineCountExpected, checkTotals = 66, 31102, theWordBookLines

        if Globals.verbosityLevel > 2: print( _("  Exporting to theWord format...") )
        mySettings = {}
        mySettings['unhandledMarkers'] = set()

        if 'TheWordOutputFilename' in controlDict: filename = controlDict["TheWordOutputFilename"]
        elif self.sourceFilename: filename = self.sourceFilename
        elif self.shortName: filename = self.shortName
        elif self.abbreviation: filename = self.abbreviation
        elif self.name: filename = self.name
        else: filename = "export"
        if not filename.endswith( extension ): filename += extension # Make sure that we have the right file extension
        filepath = os.path.join( outputFolder, Globals.makeSafeFilename( filename ) )
        if Globals.verbosityLevel > 2: print( "  " + _("Writing '{}'...").format( filepath ) )
        with open( filepath, 'wt' ) as myFile:
            myFile.write('\ufeff') # theWord needs the BOM
            BBB, bookCount, lineCount, checkCount = startBBB, 0, 0, 0
            while True: # Write each Bible book in the KJV order
                writeTWBook( myFile, BBB, mySettings )
                checkCount += checkTotals[bookCount]
                bookCount += 1
                if lineCount != checkCount:
                    logging.critical( "Wrong number of lines written: {} {} {} {}".format( bookCount, BBB, lineCount, checkCount ) )
                    if Globals.debugFlag: halt
                if BBB == endBBB: break
                BBB = BOS.getNextBookCode( BBB )

            # Now append the various settings if any
            written = []
            for key in self.settingsDict:
                if key.lower() in ('id','lang','charset','title','short.title','title.english','description','author',
                            'status','publish.date','version.date','isbn','r2l','font','font.size',
                           'version.major','version.minor','publisher','about','source','creator','keywords',
                           'verse.rule',) \
                and self.settingsDict[key]: # Copy non-blank exact matches
                    myFile.write( "{}={}\n".format( key.lower(), self.settingsDict[key] ) )
                    written.append( key.lower() )
                elif Globals.verbosityLevel > 2: print( "BibleWriter.totheWord: ignored '{}' setting ({})".format( key, self.settingsDict[key] ) )
            # Now do some adaptions
            key = 'short.title'
            if self.abbreviation and key not in written:
                myFile.write( "{}={}\n".format( key, self.abbreviation ) )
                written.append( key )
            if self.name and key not in written:
                myFile.write( "{}={}\n".format( key, self.name ) )
                written.append( key )
            # Anything useful in the settingsDict?
            for key, fieldName in (('title','FullName'),):
                if fieldName in self.settingsDict and key not in written:
                    myFile.write( "{}={}\n".format( key, self.settingsDict[fieldName] ) )
                    written.append( key )
            key = 'publish.date'
            if key not in written:
                myFile.write( "{}={}\n".format( key, datetime.now().strftime('%Y') ) )
                written.append( key )

        if mySettings['unhandledMarkers']:
            logging.warning( "BibleWriter.totheWord: Unhandled markers were {}".format( mySettings['unhandledMarkers'] ) )
            if Globals.verbosityLevel > 1:
                print( "  " + _("WARNING: Unhandled totheWord markers were {}").format( mySettings['unhandledMarkers'] ) )

        # Now create a zipped version
        if Globals.verbosityLevel > 2: print( "  Zipping {} theWord file...".format( filename ) )
        zf = zipfile.ZipFile( filepath+'.zip', 'w', compression=zipfile.ZIP_DEFLATED )
        zf.write( filepath, filename )
        zf.close()

        return True
    # end of BibleWriter.totheWord



    def toMySword( self, outputFolder=None, controlDict=None ):
        """
        Using settings from the given control file,
            converts the USFM information to a UTF-8 MySword file.

        This format is roughly documented at http://www.theword.net/index.php?article.tools&l=english
        """
        from TheWordBible import theWordOTBookLines, theWordNTBookLines, theWordBookLines, theWordHandleIntroduction, theWordComposeVerseLine
        if Globals.verbosityLevel > 1: print( "Running BibleWriter:toMySword..." )
        if Globals.debugFlag: assert( self.books )

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolder: outputFolder = "OutputFiles/BOS_MySword_" + ("Reexport/" if self.objectTypeString=="MySword" else "Export/")
        if not os.access( outputFolder, os.F_OK ): os.makedirs( outputFolder ) # Make the empty folder if there wasn't already one there
        # ControlDict is not used (yet)
        if not controlDict:
            controlDict, defaultControlFilename = {}, "To_MySword_controls.txt"
            try:
                ControlFiles.readControlFile( defaultControlFolder, defaultControlFilename, controlDict )
            except:
                pass
                #logging.critical( "Unable to read control dict {} from {}".format( defaultControlFilename, defaultControlFolder ) )
        #self.__adjustControlDict( controlDict )


        def writeMSBook( sqlObject, BBB, ourGlobals ):
            """
            Writes a book to the MySword sqlObject file.
            """
            nonlocal lineCount
            bkData = self.books[BBB] if BBB in self.books else None
            #print( bkData._processedLines )
            verseList = BOS.getNumVersesList( BBB )
            nBBB = Globals.BibleBooksCodes.getReferenceNumber( BBB )
            numC, numV = len(verseList), verseList[0]

            ourGlobals['line'], ourGlobals['lastLine'] = '', None
            ourGlobals['pi1'] = ourGlobals['pi2'] = ourGlobals['pi3'] = ourGlobals['pi4'] = ourGlobals['pi5'] = ourGlobals['pi6'] = ourGlobals['pi7'] = False
            if bkData:
                # Write book headings (stuff before chapter 1)
                ourGlobals['line'] = theWordHandleIntroduction( BBB, bkData, ourGlobals )

                # Write the verses
                C = V = 1
                ourGlobals['lastLine'] = ourGlobals['lastBCV'] = None
                while True:
                    verseData = None
                    if bkData:
                        try:
                            result = bkData.getCVRef( (BBB,str(C),str(V),) )
                            verseData, context = result
                        except KeyError: pass # Just ignore missing verses
                        # Handle some common versification anomalies
                        if (BBB,C,V) == ('JN3',1,14): # Add text for v15 if it exists
                            try:
                                result15 = bkData.getCVRef( ('JN3','1','15',) )
                                verseData15, context15 = result15
                                verseData.extend( verseData15 )
                            except KeyError: pass #  just ignore it
                        elif (BBB,C,V) == ('REV',12,17): # Add text for v15 if it exists
                            try:
                                result18 = bkData.getCVRef( ('REV','12','18',) )
                                verseData18, context18 = result18
                                verseData.extend( verseData18 )
                            except KeyError: pass #  just ignore it
                        composedLine = ''
                        if verseData:
                            composedLine = theWordComposeVerseLine( BBB, C, V, verseData, ourGlobals )
                            #if composedLine: # don't bother writing blank (unfinished?) verses
                                #print( "toMySword: Writing", BBB, nBBB, C, V, marker, repr(line) )
                                #sqlObject.execute( 'INSERT INTO "Bible" VALUES(?,?,?,?)', (nBBB,C,V,composedLine) )
                            # Stay one line behind (because paragraph indicators get appended to the previous line)
                            if ourGlobals['lastBCV'] is not None \
                            and ourGlobals['lastLine']: # don't bother writing blank (unfinished?) verses
                                sqlObject.execute( 'INSERT INTO "Bible" VALUES(?,?,?,?)', \
                                    (ourGlobals['lastBCV'][0],ourGlobals['lastBCV'][1],ourGlobals['lastBCV'][2],ourGlobals['lastLine']) )
                                lineCount += 1
                        ourGlobals['lastLine'] = composedLine
                    ourGlobals['lastBCV'] = (nBBB,C,V)
                    V += 1
                    if V > numV:
                        C += 1
                        if C > numC:
                            break
                        else: # next chapter only
                            numV = verseList[C-1]
                            V = 1
                #assert( not ourGlobals['line'] and not ourGlobals['lastLine'] ) #  We should have written everything

            # Write the last line of the file
            if ourGlobals['lastLine']: # don't bother writing blank (unfinished?) verses
                sqlObject.execute( 'INSERT INTO "Bible" VALUES(?,?,?,?)', \
                    (ourGlobals['lastBCV'][0],ourGlobals['lastBCV'][1],ourGlobals['lastBCV'][2],ourGlobals['lastLine']) )
                lineCount += 1
        # end of toMySword.writeMSBook


        # Set-up their Bible reference system
        BOS = BibleOrganizationalSystem( "GENERIC-KJV-66-ENG" )
        #BRL = BibleReferenceList( BOS, BibleObject=None )

        # Try to figure out if it's an OT/NT or what (allow for up to 4 extra books like FRT,GLO, etc.)
        if len(self) <= (39+4) and 'MAT' not in self:
            testament, startBBB, endBBB = 'OT', 'GEN', 'MAL'
            booksExpected, textLineCountExpected, checkTotals = 39, 23145, theWordOTBookLines
        elif len(self) <= (27+4) and 'GEN' not in self:
            testament, startBBB, endBBB = 'NT', 'MAT', 'REV'
            booksExpected, textLineCountExpected, checkTotals = 27, 7957, theWordNTBookLines
        else: # assume it's an entire Bible
            testament, startBBB, endBBB = 'BOTH', 'GEN', 'REV'
            booksExpected, textLineCountExpected, checkTotals = 66, 31102, theWordBookLines
        extension = '.bbl.mybible'

        if Globals.verbosityLevel > 2: print( _("  Exporting to MySword format...") )
        mySettings = {}
        mySettings['unhandledMarkers'] = set()

        if 'MySwordOutputFilename' in controlDict: filename = controlDict["MySwordOutputFilename"]
        elif self.sourceFilename: filename = self.sourceFilename
        elif self.shortName: filename = self.shortName
        elif self.abbreviation: filename = self.abbreviation
        elif self.name: filename = self.name
        else: filename = "export"
        if not filename.endswith( extension ): filename += extension # Make sure that we have the right file extension
        filepath = os.path.join( outputFolder, Globals.makeSafeFilename( filename ) )
        if os.path.exists( filepath ): os.remove( filepath )
        if Globals.verbosityLevel > 2: print( "  " + _("Writing '{}'...").format( filepath ) )
        conn = sqlite3.connect( filepath )
        cursor = conn.cursor()

        # First write the settings Details table
        exeStr = 'CREATE TABLE Details (Description NVARCHAR(255), Abbreviation NVARCHAR(50), Comments TEXT, Version TEXT, VersionDate DATETIME, PublishDate DATETIME, RightToLeft BOOL, OT BOOL, NT BOOL, Strong BOOL'
        if 'CustomCSS' in self.settingsDict: exeStr += ', CustomCSS TEXT'
        exeStr += ')'
        cursor.execute( exeStr )
        values = []
        value = ''
        if 'Description' in self.settingsDict: value = self.settingsDict['Description']
        elif 'description' in self.settingsDict: value = self.settingsDict['description']
        elif self.name: value = self.name
        values.append( value); value = ''
        if self.abbreviation: value = self.abbreviation
        elif 'WorkAbbreviation' in self.settingsDict: value = self.settingsDict['WorkAbbreviation']
        else: value = self.name[:3].upper()
        values.append( value ); value = ''
        if 'Comments' in self.settingsDict: value = self.settingsDict['Comments']
        values.append( value ); value = ''
        if 'Version' in self.settingsDict: value = self.settingsDict['Version']
        values.append( value ); value = ''
        if 'VersionDate' in self.settingsDict: value = self.settingsDict['VersionDate']
        values.append( value ); value = ''
        if 'PublishDate' in self.settingsDict: value = self.settingsDict['PublishDate']
        values.append( value ); value = False
        if 'RightToLeft' in self.settingsDict: value = self.settingsDict['RightToLeft']
        values.append( value ); value = False
        if testament=='OT' or testament=='BOTH': value = True
        values.append( value ); value = False
        if testament=='NT' or testament=='BOTH': value = True
        values.append( value ); value = False
        if 'Strong' in self.settingsDict: value = self.settingsDict['Strong']
        values.append( value ); value = ''
        if 'CustomCSS' in self.settingsDict: value = self.settingsDict['CustomCSS']
        exeStr = 'INSERT INTO "Details" VALUES(' + '?,'*(len(values)-1) + '?)'
        #print( exeStr, values )
        cursor.execute( exeStr, values )

        # Now create and fill the Bible table
        cursor.execute( 'CREATE TABLE Bible(Book INT, Chapter INT, Verse INT, Scripture TEXT, Primary Key(Book,Chapter,Verse))' )
        conn.commit() # save (commit) the changes
        BBB, lineCount = startBBB, 0
        while True: # Write each Bible book in the KJV order
            writeMSBook( cursor, BBB, mySettings )
            conn.commit() # save (commit) the changes
            if BBB == endBBB: break
            BBB = BOS.getNextBookCode( BBB )

        if mySettings['unhandledMarkers']:
            logging.warning( "BibleWriter.toMySword: Unhandled markers were {}".format( mySettings['unhandledMarkers'] ) )
            if Globals.verbosityLevel > 1:
                print( "  " + _("WARNING: Unhandled toMySword markers were {}").format( mySettings['unhandledMarkers'] ) )
        conn.commit() # save (commit) the changes
        cursor.close()

        # Now create the gzipped file
        if Globals.verbosityLevel > 2: print( "  Compressing {} MySword file...".format( filename ) )
        tar = tarfile.open( filepath+'.gz', 'w:gz' )
        tar.add( filepath )
        tar.close()

        return True
    # end of BibleWriter.toMySword



    def toESword( self, outputFolder=None, controlDict=None ):
        """
        Using settings from the given control file,
            converts the USFM information to a UTF-8 e-Sword file.

        This format is roughly documented at xxx
        """
        from TheWordBible import theWordOTBookLines, theWordNTBookLines, theWordBookLines, theWordIgnoredIntroMarkers
        if Globals.verbosityLevel > 1: print( "Running BibleWriter:toESword..." )
        if Globals.debugFlag: assert( self.books )

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolder: outputFolder = "OutputFiles/BOS_e-Sword_" + ("Reexport/" if self.objectTypeString=="e-Sword" else "Export/")
        if not os.access( outputFolder, os.F_OK ): os.makedirs( outputFolder ) # Make the empty folder if there wasn't already one there
        # ControlDict is not used (yet)
        if not controlDict:
            controlDict, defaultControlFilename = {}, "To_e-Sword_controls.txt"
            try:
                ControlFiles.readControlFile( defaultControlFolder, defaultControlFilename, controlDict )
            except:
                pass
                #logging.critical( "Unable to read control dict {} from {}".format( defaultControlFilename, defaultControlFolder ) )
        #self.__adjustControlDict( controlDict )


        def adjustLine( BBB, C, V, originalLine ):
            """
            Handle pseudo-USFM markers within the line (cross-references, footnotes, and character formatting).

            Parameters are the Scripture reference (for error messsages)
                and the line (string) containing the backslash codes.

            Returns a string with the backslash codes replaced by e-Sword RTF formatting codes.
            """
            line = originalLine # Keep a copy of the original line for error messages

            if '\\x' in line: # Remove cross-references completely (why???)
                #line = line.replace('\\x ','<RX>').replace('\\x*','<Rx>')
                line = removeUSFMCharacterField( 'x', line, closed=True ).lstrip() # Remove superfluous spaces

            if '\\f' in line: # Handle footnotes
                line = removeUSFMCharacterField( 'f', line, closed=True ).lstrip() # Remove superfluous spaces
                #for marker in ( 'fr', 'fm', ): # simply remove these whole field
                    #line = removeUSFMCharacterField( marker, line, closed=None )
                #for marker in ( 'fq', 'fqa', 'fl', 'fk', ): # italicise these ones
                    #while '\\'+marker+' ' in line:
                        ##print( BBB, C, V, marker, line.count('\\'+marker+' '), line )
                        ##print( "was", "'"+line+"'" )
                        #ix = line.find( '\\'+marker+' ' )
                        #assert( ix != -1 )
                        #ixEnd = line.find( '\\', ix+len(marker)+2 )
                        #if ixEnd == -1: # no following marker so assume field stops at the end of the line
                            #line = line.replace( '\\'+marker+' ', '<i>' ) + '</i>'
                        #elif line[ixEnd:].startswith( '\\'+marker+'*' ): # replace the end marker also
                            #line = line.replace( '\\'+marker+' ', '<i>' ).replace( '\\'+marker+'*', '</i>' )
                        #else: # leave the next marker in place
                            #line = line[:ixEnd].replace( '\\'+marker+' ', '<i>' ) + '</i>' + line[ixEnd:]
                #for marker in ( 'ft', ): # simply remove these markers (but leave behind the text field)
                    #line = line.replace( '\\'+marker+' ', '' ).replace( '\\'+marker+'*', '' )
                ##for caller in '+*abcdefghijklmnopqrstuvwxyz': line.replace('\\f '+caller+' ','<RF>') # Handle single-character callers
                #line = re.sub( r'(\\f [a-z+*]{1,3} )', '<RF>', line ) # Handle one to three character callers
                #line = line.replace('\\f ','<RF>').replace('\\f*','<Rf>') # Must be after the italicisation
                ##if '\\f' in originalLine:
                    ##print( "o", originalLine )
                    ##print( "n", line )
                    ##halt

            if '\\' in line: # Handle character formatting fields
                line = removeUSFMCharacterField( 'fig', line, closed=True ) # Remove figures
                replacements = (
                    ( ('add',), '~^~cf15~^~i','~^~cf0~^~i0' ),
                    ( ('qt',), '<FO>','<Fo>' ),
                    ( ('wj',), '<FR>','<Fr>' ),
                    ( ('bdit',), '<b><i>','</i></b>' ),
                    ( ('bd','em','k',), '<b>','</b>' ),
                    ( ('it','rq','bk','dc','qs','sig','sls','tl',), '<i>','</i>' ),
                    ( ('nd','sc',), '<font size=-1>','</font>' ),
                    )
                line = replaceUSFMCharacterFields( replacements, line ) # This function also handles USFM 2.4 nested character markers
                if '\\nd' not in originalLine and '\\+nd' not in originalLine:
                    line = line.replace('LORD', '<font size=-1>LORD</font>')
                    #line = line.replace('\\nd ','<font size=-1>',).replace('\\nd*','</font>').replace('\\+nd ','<font size=-1>',).replace('\\+nd*','</font>')
                #else:
                    #line = line.replace('LORD', '<font size=-1>LORD</font>')
                #line = line.replace('\\add ','<FI>').replace('\\add*','<Fi>').replace('\\+add ','<FI>').replace('\\+add*','<Fi>')
                #line = line.replace('\\qt ','<FO>').replace('\\qt*','<Fo>').replace('\\+qt ','<FO>').replace('\\+qt*','<Fo>')
                #line = line.replace('\\wj ','<FR>').replace('\\wj*','<Fr>').replace('\\+wj ','<FR>').replace('\\+wj*','<Fr>')

            #if '\\' in line: # Output simple HTML tags (with no semantic info)
                #line = line.replace('\\bdit ','<b><i>').replace('\\bdit*','</i></b>').replace('\\+bdit ','<b><i>').replace('\\+bdit*','</i></b>')
                #for marker in ( 'it', 'rq', 'bk', 'dc', 'qs', 'sig', 'sls', 'tl', ): # All these markers are just italicised
                    #line = line.replace('\\'+marker+' ','<i>').replace('\\'+marker+'*','</i>').replace('\\+'+marker+' ','<i>').replace('\\+'+marker+'*','</i>')
                #for marker in ( 'bd', 'em', 'k', ): # All these markers are just bolded
                    #line = line.replace('\\'+marker+' ','<b>').replace('\\'+marker+'*','</b>').replace('\\+'+marker+' ','<b>').replace('\\+'+marker+'*','</b>')
                #line = line.replace('\\sc ','<font size=-1>',).replace('\\sc*','</font>').replace('\\+sc ','<font size=-1>',).replace('\\+sc*','</font>')

            # Check what's left at the end
            if '\\' in line:
                logging.warning( "toESword.adjustLine: Doesn't handle formatted line yet: {} {}:{} '{}'".format( BBB, C, V, line ) )
                if Globals.debugFlag and debuggingThisModule:
                    print( "toESword.adjustLine: Doesn't handle formatted line yet: {} {}:{} '{}'".format( BBB, C, V, line ) )
                    halt
            return line
        # end of toESword.adjustLine


        def handleIntroduction( BBB, bookData, ourGlobals ):
            """
            Go through the book introduction (if any) and extract main titles for e-Sword export.

            Parameters are BBB (for error messages),
                the actual book data, and
                ourGlobals dictionary for persistent variables.

            Returns the information in a composed line string.
            """
            C = V = 0
            composedLine = ''
            while True:
                #print( "toESword.handleIntroduction", BBB, C, V )
                try: result = bookData.getCVRef( (BBB,'0',str(V),) ) # Currently this only gets one line
                except KeyError: break # Reached the end of the introduction
                verseData, context = result
                assert( len(verseData ) == 1 ) # in the introductory section
                marker, text = verseData[0].getMarker(), verseData[0].getFullText()
                if marker not in theWordIgnoredIntroMarkers:
                    if marker=='mt1': composedLine += '<TS1>'+adjustLine(BBB,C,V,text)+'<Ts>~^~line '
                    elif marker=='mt2': composedLine += '<TS2>'+adjustLine(BBB,C,V,text)+'<Ts>~^~line '
                    elif marker=='mt3': composedLine += '<TS3>'+adjustLine(BBB,C,V,text)+'<Ts>~^~line '
                    elif marker=='mt4': composedLine += '<TS3>'+adjustLine(BBB,C,V,text)+'<Ts>~^~line '
                    elif marker=='ms1': composedLine += '<TS2>'+adjustLine(BBB,C,V,text)+'<Ts>~^~line '
                    elif marker=='ms2': composedLine += '<TS3>'+adjustLine(BBB,C,V,text)+'<Ts>~^~line '
                    elif marker=='ms3': composedLine += '<TS3>'+adjustLine(BBB,C,V,text)+'<Ts>~^~line '
                    elif marker=='ms4': composedLine += '<TS3>'+adjustLine(BBB,C,V,text)+'<Ts>~^~line '
                    elif marker=='mr': composedLine += '<TS3>'+adjustLine(BBB,C,V,text)+'<Ts>~^~line '
                    else:
                        logging.warning( "toESword.handleIntroduction: doesn't handle {} '{}' yet".format( BBB, marker ) )
                        if Globals.debugFlag and debuggingThisModule:
                            print( "toESword.handleIntroduction: doesn't handle {} '{}' yet".format( BBB, marker ) )
                            halt
                        ourGlobals['unhandledMarkers'].add( marker + ' (in intro)' )
                V += 1 # Step to the next introductory section "verse"

            # Check what's left at the end
            if '\\' in composedLine:
                logging.warning( "toESword.handleIntroduction: Doesn't handle formatted line yet: {} '{}'".format( BBB, composedLine ) )
                if Globals.debugFlag and debuggingThisModule:
                    print( "toESword.handleIntroduction: Doesn't handle formatted line yet: {} '{}'".format( BBB, composedLine ) )
                    halt
            return composedLine.replace( '~^~', '\\' )
        # end of toESword.handleIntroduction


        def composeVerseLine( BBB, C, V, verseData, ourGlobals ):
            """
            Composes a single line representing a verse.

            Parameters are the Scripture reference (for error messages),
                the verseData (a list of InternalBibleEntries: pseudo-USFM markers and their contents),
                and a ourGlobals dictionary for holding persistent variables (between calls).

            This function handles the paragraph/new-line markers;
                adjustLine (above) is called to handle internal/character markers.

            Returns the composed line.
            """
            #print( "toESword.composeVerseLine( {} {}:{} {} {}".format( BBB, C, V, verseData, ourGlobals ) )
            composedLine = ourGlobals['line'] # We might already have some book headings to precede the text for this verse
            ourGlobals['line'] = '' # We've used them so we don't need them any more
            #marker = text = None

            vCount = 0
            lastMarker = None
            #if BBB=='MAT' and C==4 and 14<V<18: print( BBB, C, V, ourGlobals, verseData )
            for verseDataEntry in verseData:
                marker, text = verseDataEntry.getMarker(), verseDataEntry.getFullText()
                if marker in ('c','c#','cl','cp','rem',): lastMarker = marker; continue  # ignore all of these for this

                if marker == 'v': # handle versification differences here
                    vCount += 1
                    if vCount == 1: # Handle verse bridges
                        if text != str(V):
                            composedLine += '<sup>('+text+')</sup> ' # Put the additional verse number into the text in parenthesis
                    elif vCount > 1: # We have an additional verse number
                        assert( text != str(V) )
                        composedLine += ' <sup>('+text+')</sup>' # Put the additional verse number into the text in parenthesis
                    lastMarker = marker
                    continue

                #print( "toESword.composeVerseLine:", BBB, C, V, marker, text )
                if marker in theWordIgnoredIntroMarkers:
                    logging.error( "toESword.composeVerseLine: Found unexpected {} introduction marker at {} {}:{} {}".format( marker, BBB, C, V, repr(text) ) )
                    print( "toESword.composeVerseLine:", BBB, C, V, marker, text, verseData )
                    if Globals.debugFlag and debuggingThisModule: assert( marker not in theWordIgnoredIntroMarkers ) # these markers shouldn't occur in verses

                if marker == 's1':
                    if ourGlobals['lastLine'] is not None and not composedLine: # i.e., don't do it for the very first line
                        ourGlobals['lastLine'] = ourGlobals['lastLine'].rstrip() + '\\line ' # append the new paragraph marker to the previous line
                    composedLine += '~^~b~^~i~^~f0 '+adjustLine(BBB,C,V,text)+'~^~cf0~^~b0~^~i0~^~line '
                elif marker == 's2': composedLine += '~^~b~^~i~^~f0 '+adjustLine(BBB,C,V,text)+'~^~cf0~^~b0~^~i0~^~line '
                elif marker in ( 's3','s4', 'sr', 'd', ): composedLine += '~^~b~^~i~^~f0 '+adjustLine(BBB,C,V,text)+'~^~b~^~i~^~f0 '
                elif marker in ( 'qa', 'r', ):
                    if marker=='r' and text and text[0]!='(' and text[-1]!=')': # Put parenthesis around this if not already there
                        text = '(' + text + ')'
                    composedLine += '<TS3><i>'+adjustLine(BBB,C,V,text)+'</i><Ts>'
                elif marker in ( 'm', ):
                    assert( not text )
                    if ourGlobals['lastLine'] is not None and not composedLine: # i.e., don't do it for the very first line
                        ourGlobals['lastLine'] = ourGlobals['lastLine'].rstrip() + '\\line ' # append the new paragraph marker to the previous line
                    #if text:
                        #print( 'm', repr(text), verseData )
                        #composedLine += '~^~line '+adjustLine(BBB,C,V,text)
                        #if ourGlobals['pi1'] or ourGlobals['pi2'] or ourGlobals['pi3'] or ourGlobals['pi4'] or ourGlobals['pi5'] or ourGlobals['pi6'] or ourGlobals['pi7']:
                            #composedLine += '~^~line '
                        #else: composedLine += '~^~line '
                    #else: # there is text
                        #composedLine += '~^~line'+adjustLine(BBB,C,V,text)
                elif marker in ( 'p', 'b', ):
                    #print( marker, text )
                    assert( not text )
                    if ourGlobals['lastLine'] is not None and not composedLine: # i.e., don't do it for the very first line
                        ourGlobals['lastLine'] = ourGlobals['lastLine'].rstrip() + '\\line ' # append the new paragraph marker to the previous line
                    #else: composedLine += '~^~line '
                    #composedLine += adjustLine(BBB,C,V,text)
                elif marker in ( 'pi1', ):
                    assert( not text )
                elif marker in ( 'pi2', ):
                    assert( not text )
                elif marker in ( 'pi3', 'pmc', ):
                    assert( not text )
                elif marker in ( 'pi4', ):
                    assert( not text )
                elif marker in ( 'pc', ):
                    assert( not text )
                elif marker in ( 'pr', 'pmr', 'cls', ):
                    assert( not text )
                elif marker in ( 'b', 'mi', 'pm', 'pmo', ):
                    assert( not text )
                elif marker in ( 'q1', 'qm1', ):
                    assert( not text )
                    if ourGlobals['lastLine'] is not None and not composedLine: # i.e., don't do it for the very first line
                        ourGlobals['lastLine'] += '\\line ' # append the new quotation paragraph marker to the previous line
                    else: composedLine += '~^~line '
                    #composedLine += adjustLine(BBB,C,V,text)
                elif marker in ( 'q2', 'qm2', ):
                    assert( not text )
                    if ourGlobals['lastLine'] is not None and not composedLine: # i.e., don't do it for the very first line
                        ourGlobals['lastLine'] += '\\line ' # append the new quotation paragraph marker to the previous line
                    else: composedLine += '~^~line '
                    #composedLine += '~^~line<PI2>'+adjustLine(BBB,C,V,text)
                elif marker in ( 'q3', 'qm3', ):
                    assert( not text )
                    if ourGlobals['lastLine'] is not None and not composedLine: # i.e., don't do it for the very first line
                        ourGlobals['lastLine'] += '\\line ' # append the new quotation paragraph marker to the previous line
                    else: composedLine += '~^~line '
                    #composedLine += '~^~line<PI3>'+adjustLine(BBB,C,V,text)
                elif marker in ( 'q4', 'qm4', ):
                    assert( not text )
                    if ourGlobals['lastLine'] is not None and not composedLine: # i.e., don't do it for the very first line
                        ourGlobals['lastLine'] += '\\line ' # append the new quotation paragraph marker to the previous line
                    else: composedLine += '~^~line '
                    #composedLine += '~^~line<PI4>'+adjustLine(BBB,C,V,text)
                elif marker == 'li1': composedLine += '<PI>• '+adjustLine(BBB,C,V,text)
                elif marker == 'li2': composedLine += '<PI2>• '+adjustLine(BBB,C,V,text)
                elif marker == 'li3': composedLine += '<PI3>• '+adjustLine(BBB,C,V,text)
                elif marker == 'li4': composedLine += '<PI4>• '+adjustLine(BBB,C,V,text)
                elif marker in ( 'cd', 'sp', ): composedLine += '<i>'+adjustLine(BBB,C,V,text)+'</i>'
                elif marker in ( 'v~', 'p~', ):
                    #print( lastMarker )
                    if lastMarker == 'p': composedLine += '~^~line ' # We had a continuation paragraph
                    elif lastMarker == 'm': composedLine += '~^~line ' # We had a continuation paragraph
                    elif lastMarker in Globals.USFMParagraphMarkers: pass # Did we need to do anything here???
                    elif lastMarker != 'v':
                        print( BBB, C, V, marker, lastMarker, verseData )
                        composedLine += adjustLine(BBB,C,V, text )
                        if Globals.debugFlag and debuggingThisModule: halt # This should never happen -- probably a b marker with text
                    #if ourGlobals['pi1']: composedLine += '<PI>'
                    #elif ourGlobals['pi2']: composedLine += '<PI2>'
                    #elif ourGlobals['pi3']: composedLine += '<PI3>'
                    #elif ourGlobals['pi4']: composedLine += '<PI4>'
                    #elif ourGlobals['pi5']: composedLine += '<PI5>'
                    #elif ourGlobals['pi6']: composedLine += '<PI6>'
                    #elif ourGlobals['pi7']: composedLine += '<PI7>'
                    composedLine += adjustLine(BBB,C,V, text )
                else:
                    logging.warning( "toESword.composeVerseLine: doesn't handle '{}' yet".format( marker ) )
                    if Globals.debugFlag and debuggingThisModule:
                        print( "toESword.composeVerseLine: doesn't handle '{}' yet".format( marker ) )
                        halt
                    ourGlobals['unhandledMarkers'].add( marker )
                lastMarker = marker

            # Final clean-up
            #while '  ' in composedLine: # remove double spaces
                #composedLine = composedLine.replace( '  ', ' ' )

            # Check what's left at the end
            if '\\' in composedLine:
                logging.warning( "toESword.composeVerseLine: Doesn't handle formatted line yet: {} {}:{} '{}'".format( BBB, C, V, composedLine ) )
                if Globals.debugFlag and debuggingThisModule:
                    print( "toESword.composeVerseLine: Doesn't handle formatted line yet: {} {}:{} '{}'".format( BBB, C, V, composedLine ) )
                    halt
            return composedLine.replace( '~^~', '\\' ).rstrip()
        # end of toESword.composeVerseLine


        def writeESwordBook( sqlObject, BBB, ourGlobals ):
            """
            Writes a book to the e-Sword sqlObject file.
            """
            nonlocal lineCount
            bkData = self.books[BBB] if BBB in self.books else None
            #print( bkData._processedLines )
            verseList = BOS.getNumVersesList( BBB )
            nBBB = Globals.BibleBooksCodes.getReferenceNumber( BBB )
            numC, numV = len(verseList), verseList[0]

            ourGlobals['line'], ourGlobals['lastLine'] = '', None
            if bkData:
                # Write book headings (stuff before chapter 1)
                ourGlobals['line'] = handleIntroduction( BBB, bkData, ourGlobals )

                # Write the verses
                C = V = 1
                ourGlobals['lastLine'] = ourGlobals['lastBCV'] = None
                while True:
                    verseData = None
                    if bkData:
                        try:
                            result = bkData.getCVRef( (BBB,str(C),str(V),) )
                            verseData, context = result
                        except KeyError: pass # Just ignore missing verses
                        # Handle some common versification anomalies
                        if (BBB,C,V) == ('JN3',1,14): # Add text for v15 if it exists
                            try:
                                result15 = bkData.getCVRef( ('JN3','1','15',) )
                                verseData15, context15 = result15
                                verseData.extend( verseData15 )
                            except KeyError: pass #  just ignore it
                        elif (BBB,C,V) == ('REV',12,17): # Add text for v15 if it exists
                            try:
                                result18 = bkData.getCVRef( ('REV','12','18',) )
                                verseData18, context18 = result18
                                verseData.extend( verseData18 )
                            except KeyError: pass #  just ignore it
                        composedLine = ''
                        if verseData:
                            composedLine = composeVerseLine( BBB, C, V, verseData, ourGlobals )
                            #if composedLine: # don't bother writing blank (unfinished?) verses
                                #print( "toESword: Writing", BBB, nBBB, C, V, marker, repr(line) )
                                #sqlObject.execute( 'INSERT INTO "Bible" VALUES(?,?,?,?)', (nBBB,C,V,composedLine) )
                            # Stay one line behind (because paragraph indicators get appended to the previous line)
                            if ourGlobals['lastBCV'] is not None \
                            and ourGlobals['lastLine']: # don't bother writing blank (unfinished?) verses
                                sqlObject.execute( 'INSERT INTO "Bible" VALUES(?,?,?,?)', \
                                    (ourGlobals['lastBCV'][0],ourGlobals['lastBCV'][1],ourGlobals['lastBCV'][2],ourGlobals['lastLine']) )
                                lineCount += 1
                        ourGlobals['lastLine'] = composedLine
                    ourGlobals['lastBCV'] = (nBBB,C,V)
                    V += 1
                    if V > numV:
                        C += 1
                        if C > numC:
                            break
                        else: # next chapter only
                            numV = verseList[C-1]
                            V = 1
                #assert( not ourGlobals['line'] and not ourGlobals['lastLine'] ) #  We should have written everything

            # Write the last line of the file
            if ourGlobals['lastLine']: # don't bother writing blank (unfinished?) verses
                sqlObject.execute( 'INSERT INTO "Bible" VALUES(?,?,?,?)', \
                    (ourGlobals['lastBCV'][0],ourGlobals['lastBCV'][1],ourGlobals['lastBCV'][2],ourGlobals['lastLine']) )
                lineCount += 1
        # end of toESword.writeESwordBook


        # Set-up their Bible reference system
        BOS = BibleOrganizationalSystem( "GENERIC-KJV-66-ENG" )
        #BRL = BibleReferenceList( BOS, BibleObject=None )

        # Try to figure out if it's an OT/NT or what (allow for up to 4 extra books like FRT,GLO, etc.)
        if len(self) <= (39+4) and 'MAT' not in self:
            testament, startBBB, endBBB = 'OT', 'GEN', 'MAL'
            booksExpected, textLineCountExpected, checkTotals = 39, 23145, theWordOTBookLines
        elif len(self) <= (27+4) and 'GEN' not in self:
            testament, startBBB, endBBB = 'NT', 'MAT', 'REV'
            booksExpected, textLineCountExpected, checkTotals = 27, 7957, theWordNTBookLines
        else: # assume it's an entire Bible
            testament, startBBB, endBBB = 'BOTH', 'GEN', 'REV'
            booksExpected, textLineCountExpected, checkTotals = 66, 31102, theWordBookLines
        extension = '.bblx'

        if Globals.verbosityLevel > 2: print( _("  Exporting to e-Sword format...") )
        mySettings = {}
        mySettings['unhandledMarkers'] = set()

        if 'e-SwordOutputFilename' in controlDict: filename = controlDict["e-SwordOutputFilename"]
        elif self.sourceFilename: filename = self.sourceFilename
        elif self.shortName: filename = self.shortName
        elif self.abbreviation: filename = self.abbreviation
        elif self.name: filename = self.name
        else: filename = "export"
        if not filename.endswith( extension ): filename += extension # Make sure that we have the right file extension
        filepath = os.path.join( outputFolder, Globals.makeSafeFilename( filename ) )
        if os.path.exists( filepath ): os.remove( filepath )
        if Globals.verbosityLevel > 2: print( "  " + _("Writing '{}'...").format( filepath ) )
        conn = sqlite3.connect( filepath )
        cursor = conn.cursor()

        # First write the settings Details table
        exeStr = 'CREATE TABLE Details (Description NVARCHAR(255), Abbreviation NVARCHAR(50), Comments TEXT, Version TEXT, VersionDate DATETIME, PublishDate DATETIME, RightToLeft BOOL, OT BOOL, NT BOOL, Strong BOOL'
        if 'CustomCSS' in self.settingsDict: exeStr += ', CustomCSS TEXT'
        exeStr += ')'
        cursor.execute( exeStr )
        values = []
        value = ''
        if 'Description' in self.settingsDict: value = self.settingsDict['Description']
        elif 'description' in self.settingsDict: value = self.settingsDict['description']
        elif self.name: value = self.name
        values.append( value); value = ''
        if self.abbreviation: value = self.abbreviation
        elif 'WorkAbbreviation' in self.settingsDict: value = self.settingsDict['WorkAbbreviation']
        else: value = self.name[:3].upper()
        values.append( value ); value = ''
        if 'Comments' in self.settingsDict: value = self.settingsDict['Comments']
        values.append( value ); value = ''
        if 'Version' in self.settingsDict: value = self.settingsDict['Version']
        values.append( value ); value = ''
        if 'VersionDate' in self.settingsDict: value = self.settingsDict['VersionDate']
        values.append( value ); value = ''
        if 'PublishDate' in self.settingsDict: value = self.settingsDict['PublishDate']
        values.append( value ); value = False
        if 'RightToLeft' in self.settingsDict: value = self.settingsDict['RightToLeft']
        values.append( value ); value = False
        if testament=='OT' or testament=='BOTH': value = True
        values.append( value ); value = False
        if testament=='NT' or testament=='BOTH': value = True
        values.append( value ); value = False
        if 'Strong' in self.settingsDict: value = self.settingsDict['Strong']
        values.append( value ); value = ''
        if 'CustomCSS' in self.settingsDict: value = self.settingsDict['CustomCSS']
        exeStr = 'INSERT INTO "Details" VALUES(' + '?,'*(len(values)-1) + '?)'
        #print( exeStr, values )
        cursor.execute( exeStr, values )

        # Now create and fill the Bible table
        cursor.execute( 'CREATE TABLE Bible(Book INT, Chapter INT, Verse INT, Scripture TEXT)' )
        conn.commit() # save (commit) the changes
        BBB, lineCount = startBBB, 0
        while True: # Write each Bible book in the KJV order
            writeESwordBook( cursor, BBB, mySettings )
            conn.commit() # save (commit) the changes
            if BBB == endBBB: break
            BBB = BOS.getNextBookCode( BBB )

        # Now create the index
        cursor.execute( 'CREATE INDEX BookChapterVerseIndex ON Bible (Book, Chapter, Verse)' )
        conn.commit() # save (commit) the changes

        if mySettings['unhandledMarkers']:
            logging.warning( "BibleWriter.toESword: Unhandled markers were {}".format( mySettings['unhandledMarkers'] ) )
            if Globals.verbosityLevel > 1:
                print( "  " + _("WARNING: Unhandled toESword markers were {}").format( mySettings['unhandledMarkers'] ) )
        conn.commit() # save (commit) the changes
        cursor.close()

        # Now create a zipped version
        if Globals.verbosityLevel > 2: print( "  Zipping {} e-Sword file...".format( filename ) )
        zf = zipfile.ZipFile( filepath+'.zip', 'w', compression=zipfile.ZIP_DEFLATED )
        zf.write( filepath, filename )
        zf.close()

        return True
    # end of BibleWriter.toESword



    def toTeX( self, outputFolder=None ):
        """
        Write the pseudo USFM out into a TeX (typeset) format.
            The format varies, depending on whether or not there are paragraph markers in the text.
        """
        import subprocess
        if Globals.verbosityLevel > 1: print( "Running BibleWriter:toTeX..." )
        if Globals.debugFlag: assert( self.books )

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolder: outputFolder = "OutputFiles/BOS_TeX_Export/"
        if not os.access( outputFolder, os.F_OK ): os.makedirs( outputFolder ) # Make the empty folder if there wasn't already one there

        unhandledMarkers = set()

        # First determine our format
        #verseByVerse = True

        # Copy auxilliary XeTeX files to our output folder
        for filename in ( "lettrine.sty", ):
            filepath = os.path.join( defaultControlFolder, filename )
            try: shutil.copy( filepath, outputFolder )
            except FileNotFoundError: logging.warning( "Unable to find TeX control file: {}".format( filepath ) )
        pMarkerTranslate = { 'p':'P', 'pi':'PI', 'q1':'Q', 'q2':'QQ', 'q3':'QQQ', 'q4':'QQQQ',
                            'ip':'IP', }
        cMarkerTranslate = { 'bk':'BK', 'add':'ADD', 'nd':'ND', 'wj':'WJ', 'sig':'SIG',
                            'bdit':'BDIT', 'it':'IT', 'bd':'BD', 'em':'EM', 'sc':'SC',
                            'ior':'IOR', 'k':'KW', }
        mtMarkerTranslate = { 'mt1':'BibleMainTitle', 'mt2':'BibleTitleTwo', 'mt3':'BibleTitleThree', 'mt4':'BibleTitleFour' }

        def writeTeXHeader( writer ):
            """
            Write the XeTeX header data -- the file can be processed with xelatex
                I had to run "sudo apt-get install fonts-linuxlibertine" first.
            """
            for line in (
                "\\documentclass[a4paper]{Bible} % use our own Bible document class found in Bible.cls",
                "",
                #"\\usepackage{xltxtra} % Extra customizations for XeLaTeX;",
                #"% xltxtra automatically loads fontspec and xunicode, both of which you need",
                #"",
                #"\\setmainfont[Ligatures=TeX]{Charis SIL}",
                #"\\setromanfont[Mapping=tex-text]{Linux Libertine O}",
                #"\\setsansfont[Mapping=tex-text]{Myriad Pro}",
                #"\\setmonofont[Mapping=tex-text]{Courier New}",
                #"",
                #"\\usepackage{geometry}",
                #"\\geometry{a4paper}",
                #"",
                "\\begin{document}",
                #"\\maketitle",
                #"",
                #"\\section{Ligatures}",
                #"\\fontspec[Ligatures={Common, Historical}]{Linux Libertine O Italic}",
                #"Questo è strano assai!",
                #"",
                #"\\section{Numerals}",
                #"\\fontspec[Numbers={OldStyle}]{Linux Libertine O}Old style: 1234567\\",
                #"\\fontspec[Numbers={Lining}]{Linux Libertine O}Lining: 1234567",
                #"",
                ):
                writer.write( "{}\n".format( line ) )
        # end of toTeX.writeTeXHeader


        def texText( givenText ):
            """
            Given some text containing possible character formatting,
                convert it to TeX styles.
            """
            text = givenText

            if '\\fig ' in text: # handle figures
                #ix = text.find( '\\fig ' )
                #ixEnd = text.find( '\\fig*' )
                text = text.replace( '\\fig ', '~^~BibleFigure{' ).replace( '\\fig*', '}' ) # temp

            if '\\f ' in text: # handle footnotes
                #print( 'footnote', repr(givenText) )
                #ix = text.find( '\\f ' )
                #ixEnd = text.find( '\\f*' )
                text = text.replace( '\\f ', '~^~BibleFootnote{' ).replace( '\\f*', '}' ) # temp
                text = text.replace( '\\fr ', '~^~BibleFootnoteAnchor{' ).replace( '\\ft ', '}', 1 ) # temp assumes one fr followed by one ft
                text = text.replace( '\\fq ', '' ).replace( '\\ft ', '' ).replace( '\\fk ', '' ) # Just remove these ones

            if '\\x ' in text: # handle cross-references
                #print( 'xref', repr(givenText) )
                #ix = text.find( '\\x ' )
                #ixEnd = text.find( '\\x*' )
                text = text.replace( '\\x ', '~^~BibleCrossReference{' ).replace( '\\x*', '}' ) # temp
                text = text.replace( '\\xo ', '~^~BibleCrossReferenceAnchor{' ).replace( '\\xt ', '}' ) # temp assumes one xo followed by one xt

            # Handle regular character formatting -- this will cause TeX to fail if closing markers are not matched
            for charMarker in allCharMarkers:
                fullCharMarker = '\\' + charMarker + ' '
                if fullCharMarker in text:
                    endCharMarker = '\\' + charMarker + '*'
                    if charMarker in cMarkerTranslate:
                        text = text.replace( fullCharMarker, '~^~BibleCharacterStyle'+cMarkerTranslate[charMarker]+'{' ) \
                                .replace( endCharMarker, '}' )
                    else:
                        logging.warning( "toTeX: Don't know how to encode '{}' marker".format( charMarker ) )
                        text = text.replace( fullCharMarker, '' ).replace( endCharMarker, '' )

            if '\\' in text: # Catch any left-overs
                if Globals.debugFlag or Globals.verbosityLevel > 2:
                    print( "toTeX.texText: unprocessed code in {} from {}".format( repr(text), repr(givenText) ) )
                if Globals.debugFlag and debuggingThisModule: halt
            return text.replace( '~^~', '\\' )
        # end of toTeX:texText


        def makePDFs( BBB, texFilepath, timeout ):
            """
            Call xelatex to make the Bible PDF file(s) from the .tex file.
            """
            assert( texFilepath.endswith( '.tex' ) )
            mainFilepath = texFilepath[:-4] # Remove the .tex bit

            # Work through the various class files for different styles of Bible layouts
            for filenamePart in ( 'Bible1','Bible2', ):
                filepath = os.path.join( defaultControlFolder, filenamePart+'.cls' )
                try:
                    shutil.copy( filepath, outputFolder ) # Copy it under its own name
                    shutil.copy( filepath, os.path.join( outputFolder, "Bible.cls" ) ) # Copy it also under the generic name
                except FileNotFoundError: logging.warning( "Unable to find TeX control file: {}".format( filepath ) )

                # Now run xelatex (TeX -> PDF)
                parameters = ['/usr/bin/timeout', timeout, '/usr/bin/xelatex', '-interaction=batchmode', os.path.abspath(texFilepath) ]
                #print( "makeIndividualPDF (xelatex) parameters", parameters )
                os.chdir( outputFolder ) # So the paths for the Bible.cls file are correct
                myProcess = subprocess.Popen( parameters, stdout=subprocess.PIPE, stderr=subprocess.PIPE )
                programOutputBytes, programErrorOutputBytes = myProcess.communicate()
                os.chdir( cwdSave ) # Restore the path again
                if myProcess.returncode == 124: # it timed out
                    programErrorOutputBytes += "xelatex {}: Timed out after {}".format( BBB, timeout ).encode( 'utf-8' )
                # Process the output
                if programOutputBytes:
                    programOutputString = programOutputBytes.decode( encoding='utf-8', errors="replace" )
                    #programOutputString = programOutputString.replace( baseFolder + ('' if baseFolder[-1]=='/' else '/'), '' ) # Remove long file paths to make it easier for the user to read
                    #with open( os.path.join( outputFolder, "ScriptOutput.txt" ), 'wt' ) as myFile: myFile.write( programOutputString )
                    #print( "pOS", programOutputString )
                if programErrorOutputBytes:
                    programErrorOutputString = programErrorOutputBytes.decode( encoding='utf-8', errors="replace" )
                    #with open( os.path.join( outputFolder, "ScriptErrorOutput.txt" ), 'wt' ) as myFile: myFile.write( programErrorOutputString )
                    if Globals.debugFlag: print( "pEOS", programErrorOutputString )

                # Rename our PDF (and the log file) according to the style
                try: os.replace( mainFilepath+'.log', mainFilepath+'.'+filenamePart+'.log' )
                except FileNotFoundError: pass # That's fine
                try: os.replace( mainFilepath+'.pdf', mainFilepath+'.'+filenamePart+'.pdf' )
                except FileNotFoundError: pass # That's fine
        # end of toTeX.makePDFs


        # Write the plain text XeTeX file
        cwdSave = os.getcwd() # Save the current working directory before changing (below) to the output directory
        allFilename = "All-BOS-BWr.tex"
        allFilepath = os.path.join( outputFolder, Globals.makeSafeFilename( allFilename ) )
        if Globals.verbosityLevel > 2: print( "  " + _("Writing '{}'...").format( allFilepath ) )
        with open( allFilepath, 'wt' ) as allFile:
            writeTeXHeader( allFile )
            for BBB,bookObject in self.books.items():
                haveTitle = haveIntro = False
                filename = "BOS-BWr-{}.tex".format( BBB )
                filepath = os.path.join( outputFolder, Globals.makeSafeFilename( filename ) )
                if Globals.verbosityLevel > 2: print( "  " + _("Writing '{}'...").format( filepath ) )
                with open( filepath, 'wt' ) as bookFile:
                    writeTeXHeader( bookFile )
                    allFile.write( "\n\\BibleBook{{{}}}\n".format( bookObject.getAssumedBookNames()[0] ) )
                    bookFile.write( "\n\\BibleBook{{{}}}\n".format( bookObject.getAssumedBookNames()[0] ) )
                    bookFile.write( "\n\\BibleBookTableOfContents\n".format( bookObject.getAssumedBookNames()[0] ) )
                    C = V = "0"
                    for entry in bookObject._processedLines:
                        marker, text = entry.getMarker(), entry.getFullText()
                        if marker in oftenIgnoredIntroMarkers: pass # Just ignore these lines
                        elif marker in ('mt1','mt2','mt3','mt4',):
                            if not haveTitle:
                                allFile.write( "\n\\BibleTitlePage\n" )
                                bookFile.write( "\n\\BibleTitlePage\n" )
                                haveTitle = True
                            allFile.write( "\\{}{{{}}}\n".format( mtMarkerTranslate[marker], texText(text) ) )
                            bookFile.write( "\\{}{{{}}}\n".format( mtMarkerTranslate[marker], texText(text) ) )
                        elif marker=='ip':
                            if not haveIntro:
                                allFile.write( "\n\\BibleIntro\n" )
                                bookFile.write( "\n\\BibleIntro\n" )
                                haveIntro = True
                            allFile.write( "\\BibleParagraphStyle{}\n".format( pMarkerTranslate[marker] ) )
                            bookFile.write( "\\BibleParagraphStyle{}\n".format( pMarkerTranslate[marker] ) )
                            allFile.write( "{}\n".format( texText(text) ) )
                            bookFile.write( "{}\n".format( texText(text) ) )
                        elif marker=='c':
                            C, V = text, "0"
                            if text == '1': # Assume chapter 1 is the start of the actual Bible text
                                allFile.write( "\n\\BibleText\n" )
                                bookFile.write( "\n\\BibleText\n" )
                        elif marker=='c#':
                            allFile.write( "\\chapterNumber{{{}}}".format( texText(text) ) ) # no NL
                            bookFile.write( "\\chapterNumber{{{}}}".format( texText(text) ) ) # no NL
                        elif marker=='v':
                            V = text
                            if text != '1': # Don't write verse 1 number
                                allFile.write( "\\verseNumber{{{}}}".format( texText(text) ) ) # no NL
                                bookFile.write( "\\verseNumber{{{}}}".format( texText(text) ) ) # no NL
                        elif marker=='s1':
                            allFile.write( "\n\\BibleTextSection{{{}}}\n".format( texText(text) ) )
                            bookFile.write( "\n\\BibleTextSection{{{}}}\n".format( texText(text) ) )
                            bookFile.write( "\n\\addcontentsline{{toc}}{{toc}}{{{}}}\n".format( texText(text) ) )
                        elif marker=='r':
                            allFile.write( "\\BibleSectionCrossReference{{{}}}\n".format( texText(text) ) )
                            bookFile.write( "\\BibleSectionCrossReference{{{}}}\n".format( texText(text) ) )
                        elif marker in ('p','pi','q1','q2','q3','q4'):
                            assert( not text )
                            allFile.write( "\\BibleParagraphStyle{}\n".format( pMarkerTranslate[marker] ) )
                            bookFile.write( "\\BibleParagraphStyle{}\n".format( pMarkerTranslate[marker] ) )
                        elif marker in ('v~','p~'):
                            allFile.write( "{}\n".format( texText(text) ) )
                            bookFile.write( "{}\n".format( texText(text) ) )
                        else:
                            if text:
                                logging.error( "toTeX: lost text in {} field in {} {}:{} {}".format( marker, BBB, C, V, repr(text) ) )
                                #if Globals.debugFlag: halt
                            unhandledMarkers.add( marker )
                        #if extras and marker not in ('v~','p~',): logging.critical( "toHTML5: extras not handled for {} at {} {}:{}".format( marker, BBB, C, V ) )
                    allFile.write( "\\BibleBookEnd\n" )
                    bookFile.write( "\\BibleBookEnd\n" )
                    bookFile.write( "\\end{document}\n" )
                makePDFs( BBB, filepath, '30s' )
            allFile.write( "\\end{document}\n" )
        makePDFs( 'All', allFilepath, '3m' )
        if unhandledMarkers:
            logging.warning( "toTeX: Unhandled markers were {}".format( unhandledMarkers ) )
            if Globals.verbosityLevel > 1:
                print( "  " + _("WARNING: Unhandled toTeX markers were {}").format( unhandledMarkers ) )

        # Now create a zipped collection
        if Globals.verbosityLevel > 2: print( "  Zipping PDF files..." )
        zf = zipfile.ZipFile( os.path.join( outputFolder, 'AllBible1PDFFiles.zip' ), 'w', compression=zipfile.ZIP_DEFLATED )
        for filename in os.listdir( outputFolder ):
            if filename.endswith( '.Bible1.pdf' ):
                filepath = os.path.join( outputFolder, filename )
                zf.write( filepath, filename ) # Save in the archive without the path
        zf.close()
        zf = zipfile.ZipFile( os.path.join( outputFolder, 'AllBible2PDFFiles.zip' ), 'w', compression=zipfile.ZIP_DEFLATED )
        for filename in os.listdir( outputFolder ):
            if filename.endswith( '.Bible2.pdf' ):
                filepath = os.path.join( outputFolder, filename )
                zf.write( filepath, filename ) # Save in the archive without the path
        zf.close()

        return True
    # end of BibleWriter.toTeX



    def toSwordSearcher( self, outputFolder=None ):
        """
        Write the pseudo USFM out into the SwordSearcher pre-Forge format.
        """
        ssBookAbbrevDict = { 'GEN':'Ge', 'EXO':'Ex', 'LEV':'Le', 'NUM':'Nu', 'DEU':'De', 'JOS':'Jos', 'JDG':'Jg',
                            'RUT':'Ru', 'SA1':'1Sa', 'SA2':'2Sa', 'KI1':'1Ki', 'KI2':'2Ki', 'CH1':'1Ch', 'CH2':'2Ch',
                            'EZR':'Ezr', 'NEH':'Ne', 'EST':'Es', 'JOB':'Job', 'PSA':'Ps', 'PRO':'Pr', 'ECC':'Ec',
                            'SNG':'Song', 'ISA':'Isa', 'JER':'Jer', 'LAM':'La', 'EZK':'Eze', 'DAN':'Da', 'HOS':'Ho',
                            'JOL':'Joe', 'AMO':'Am', 'OBA':'Ob', 'JNA':'Jon', 'MIC':'Mic', 'NAH':'Na', 'HAB':'Hab',
                            'ZEP':'Zep', 'HAG':'Hag', 'ZEC':'Zec', 'MAL':'Mal',
                            'MAT':'Mt', 'MRK':'Mr', 'LUK':'Lu', 'JHN':'Joh', 'ACT':'Ac', 'ROM':'Ro',
                            'CO1':'1Co', 'CO2':'2Co', 'GAL':'Ga', 'EPH':'Eph', 'PHP':'Php', 'COL':'Col',
                            'TH1':'1Th', 'TH2':'2Th', 'TI1':'1Ti', 'TI2':'2Ti', 'TIT':'Tit', 'PHM':'Phm',
                            'HEB':'Heb', 'JAM':'Jas', 'PE1':'1Pe', 'PE2':'2Pe',
                            'JN1':'1Jo', 'JN2':'2Jo', 'JN3':'3Jo', 'JDE':'Jude', 'REV':'Re' }
        if Globals.verbosityLevel > 1: print( "Running BibleWriter:toSwordSearcher..." )
        if Globals.debugFlag: assert( self.books )

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolder: outputFolder = "OutputFiles/BOS_SwordSearcher_Export/"
        if not os.access( outputFolder, os.F_OK ): os.makedirs( outputFolder ) # Make the empty folder if there wasn't already one there

        unhandledMarkers = set()


        def writeSSHeader( writer ):
            """
            Write the header data
            """
            writer.write( "; TITLE: {}\n".format( self.name ) )
            if self.abbreviation: writer.write( "; ABBREVIATION: {}\n".format( self.abbreviation ) )
        # end of toSwordSearcher.writeSSHeader


        def writeSSBook( writer, BBB, bookObject ):
            """
            Convert the internal Bible data to SwordSearcher pre-Forge output.
            """
            try: bookCode = ssBookAbbrevDict[BBB]
            except:
                logging.warning( "toSwordSearcher: ignoring book: {}".format( BBB ) )
                return

            pseudoUSFMData = bookObject._processedLines
            started, accumulator = False, "" # Started flag ignores fields in the book introduction
            C = V = "0"
            for entry in pseudoUSFMData:
                marker, text = entry.getMarker(), entry.getCleanText()
                if marker in oftenIgnoredIntroMarkers: pass # Just ignore these lines
                elif marker == 'c': C, V = text, "0"
                elif marker == 'v':
                    V = text
                    started = True
                    if accumulator: writer.write( "{}\n".format( accumulator ) ); accumulator = ""
                    writer.write( "$$ {} {}:{}\n".format( bookCode, C, text ) )
                elif marker in ('v~', 'p~'):
                    if started: accumulator += (' ' if accumulator else '') + text
                elif marker not in ('c#',):
                    if text:
                        logging.error( "toSwordSearcher: lost text in {} field in {} {}:{} {}".format( marker, BBB, C, V, repr(text) ) )
                        #if Globals.debugFlag: halt
                    unhandledMarkers.add( marker )
                #if extras and marker not in ('v~','p~',): logging.critical( "toHTML5: extras not handled for {} at {} {}:{}".format( marker, BBB, C, V ) )
            if accumulator: writer.write( "{}\n".format( accumulator ) )
        # end of toSwordSearcher:writeSSBook


        if Globals.verbosityLevel > 2: print( _("  Exporting to SwordSearcher format...") )
        filename = "Bible.txt"
        filepath = os.path.join( outputFolder, Globals.makeSafeFilename( filename ) )
        if Globals.verbosityLevel > 2: print( "  " + _("Writing '{}'...").format( filepath ) )
        with open( filepath, 'wt' ) as myFile:
            writeSSHeader( myFile )
            for BBB,bookObject in self.books.items():
                if Globals.debugFlag: writeSSBook( myFile, BBB, bookObject ) # Halts on errors
                else:
                    try: writeSSBook( myFile, BBB, bookObject )
                    except: logging.critical( "BibleWriter.toSwordSearcher: Unable to output {}".format( BBB ) )

        if unhandledMarkers:
            logging.warning( "toSwordSearcher: Unhandled markers were {}".format( unhandledMarkers ) )
            if Globals.verbosityLevel > 1:
                print( "  " + _("WARNING: Unhandled toSwordSearcher markers were {}").format( unhandledMarkers ) )

        # Now create a zipped version
        if Globals.verbosityLevel > 2: print( "  Zipping {} SwordSearcher file...".format( filename ) )
        zf = zipfile.ZipFile( filepath+'.zip', 'w', compression=zipfile.ZIP_DEFLATED )
        zf.write( filepath )
        zf.close()

        return True
    # end of BibleWriter.toSwordSearcher



    def toDrupalBible( self, outputFolder=None ):
        """
        Write the pseudo USFM out into the DrupalBible format.
        """
        if Globals.verbosityLevel > 1: print( "Running BibleWriter:toDrupalBible..." )
        if Globals.debugFlag: assert( self.books )

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolder: outputFolder = "OutputFiles/BOS_DrupalBible_" + ("Reexport/" if self.objectTypeString=="DrupalBible" else "Export/")
        if not os.access( outputFolder, os.F_OK ): os.makedirs( outputFolder ) # Make the empty folder if there wasn't already one there

        unhandledMarkers = set()

        #print( 'status' in self ) # False
        #print( 'status' in dir(self) ) # True
        #print( '\nself', dir(self) )
        #print( '\nssf', dir(self.ssfDict) )
        #print( '\nsettings', dir(self.settingsDict) )


        def writeDrupalBibleHeader( writer ):
            """
            Write the header data
            """
            #writer.write( "\ufeff*Bible\n#shortname fullname language\n" ) # Starts with BOM
            writer.write( "*Bible\n#shortname fullname language\n" ) # No BOM
            shortName = self.shortName if self.shortName else self.name
            if self.abbreviation and len(shortName)>5: shortName = self.abbreviation
            shortName = shortName[:5] # Maximum of five characters
            writer.write( "{}|{}|{}\n\n".format( shortName, self.name, 'en' ) )
        # end of toDrupalBible.writeDrupalBibleHeader


        def writeDrupalBibleChapters( writer ):
            """
            Write the header data
            """
            writer.write( "*Chapter\n#book,fullname,shortname,chap-count\n" )
            for BBB,bookObject in self.books.items():
                numChapters = None
                try: bookCode = Globals.BibleBooksCodes.getDrupalBibleAbbreviation( BBB ).upper()
                except: # Don't know how to encode this book
                    logging.warning( "toDrupalBible: ignoring book: {}".format( BBB ) )
                    continue
                for entry in bookObject._processedLines:
                    marker = entry.getMarker()
                    if marker == 'c': numChapters = entry.getCleanText()
                if numChapters:
                    writer.write( "{}|{}|{}|{}\n".format( bookCode, bookObject.assumedBookName, bookCode, numChapters ) )
            writer.write( '\n*Context\n#Book,Chapter,Verse,LineMark,Context\n' )
        # end of toDrupalBible.writeDrupalBibleChapters


        def doDrupalTextFormat( givenTextField ):
            """
            """
            textField = givenTextField
            textField = textField.replace( ' ', ' ' ) # Replace non-breaking spaces (temp)
            while '  ' in textField: textField = textField.replace( '  ', ' ' ) # Remove multiple spaces
            textField = textField.replace( '\\it ', '<' ).replace( '\\it*', '>' ) \
                                        .replace( '\\add ', '<' ).replace( '\\add*', '>' )
            #print( repr(textField) )
            # These re's should really ensure that the USFM starts with a letter
            textField = re.sub( r'(\\[a-z0-9]{1,3} )', '', textField ) # Remove any remaining character fields, e.g., '\\s1 '
            textField = re.sub( r'(\\[a-z0-9]{1,3}\*)', '', textField ) # Remove any remaining character end fields, e.g., '\s1*'
            if '\\' in textField: # Catch any left-overs
                if Globals.debugFlag or Globals.verbosityLevel > 2:
                    print( "toDrupalBible.doDrupalTextFormat: unprocessed code in {} from {}".format( repr(textField), repr(givenTextField) ) )
                if Globals.debugFlag and debuggingThisModule: halt
            return textField
        # end of doDrupalTextFormat


        def writeDrupalBibleBook( writer, BBB, bookObject ):
            """
            Convert the internal Bible data to DrupalBible output.
            """
            try: bookCode = Globals.BibleBooksCodes.getDrupalBibleAbbreviation( BBB ).upper()
            except:
                logging.error( "writeDrupalBibleBook: don't know how to encode {}".format( BBB ) )
                return
            started, accumulator = False, "" # Started flag ignores fields in the book introduction
            linemark = ''
            C = V = "0"
            for entry in bookObject._processedLines:
                marker, text = entry.getMarker(), entry.getAdjustedText()
                if marker in oftenIgnoredIntroMarkers: pass # Just ignore these lines
                elif marker in ( 'mt1','mt2','mt3','mt4', ): pass # Just ignore these book heading fields
                elif marker in ( 'iot', 'io1', 'io2', 'ip', 'is1', ): pass # Just ignore these introduction fields
                elif marker in ( 'c#', ): pass # Just ignore these unneeded fields
                elif marker == 'c':
                    if accumulator:
                        writer.write( "{}|{}|{}|{}|{}\n".format( bookCode, C, V, linemark, doDrupalTextFormat( accumulator ) ) )
                        accumulator, linemark = "", ''
                    C, V = text, "0"
                elif marker == 'v':
                    started = True
                    if accumulator:
                        writer.write( "{}|{}|{}|{}|{}\n".format( bookCode, C, V, linemark, doDrupalTextFormat( accumulator ) ) )
                        accumulator, linemark = "", ''
                    V = text
                    if not V.isdigit(): # Remove verse bridges
                        #print( "toDrupalBible V was", repr(V) )
                        Vcopy, V = V, ''
                        for char in Vcopy:
                            if not char.isdigit(): break
                            V += char
                        #print( "toDrupalBible V is now", repr(V) )
                elif marker in ( 's1', 's2', 's3', 's4', ): pass # Just ignore these section headings
                elif marker in ( 'r', ): pass # Just ignore these reference fields
                elif marker in ( 'p', 'q1','q2','q3','q4', 'm', 'b', 'nb', 'li1','li2','li3','li4', ): pass # Just ignore these paragraph formatting fields
                elif marker in ('v~', 'p~'):
                    if started: accumulator += (' ' if accumulator else '') + text
                else:
                    if text:
                        logging.warning( "toDrupalBible: lost text in {} field in {} {}:{} {}".format( marker, BBB, C, V, repr(text) ) )
                        #if Globals.debugFlag: halt
                    unhandledMarkers.add( marker )
                #if extras and marker not in ('v~','p~',): logging.critical( "toHTML5: extras not handled for {} at {} {}:{}".format( marker, BBB, C, V ) )
            if accumulator: writer.write( "{}|{}|{}|{}|{}\n".format( bookCode, C, V, linemark, doDrupalTextFormat( accumulator ) ) )
        # end of toDrupalBible:writeDrupalBibleBook


        if Globals.verbosityLevel > 2: print( _("  Exporting to DrupalBible format...") )
        filename = "Bible.txt"
        filepath = os.path.join( outputFolder, Globals.makeSafeFilename( filename ) )
        if Globals.verbosityLevel > 2: print( "  " + _("Writing '{}'...").format( filepath ) )
        with open( filepath, 'wt' ) as myFile:
            writeDrupalBibleHeader( myFile )
            writeDrupalBibleChapters( myFile )
            for BBB,bookObject in self.books.items():
                if Globals.debugFlag: writeDrupalBibleBook( myFile, BBB, bookObject ) # Halts on errors
                else:
                    try: writeDrupalBibleBook( myFile, BBB, bookObject )
                    except: logging.critical( "BibleWriter.toDrupalBible: Unable to output {}".format( BBB ) )

        if unhandledMarkers:
            logging.warning( "toDrupalBible: Unhandled markers were {}".format( unhandledMarkers ) )
            if Globals.verbosityLevel > 1:
                print( "  " + _("WARNING: Unhandled toDrupalBible markers were {}").format( unhandledMarkers ) )

        # Now create a zipped version
        if Globals.verbosityLevel > 2: print( "  Zipping {} DrupalBible file...".format( filename ) )
        zf = zipfile.ZipFile( filepath+'.zip', 'w', compression=zipfile.ZIP_DEFLATED )
        zf.write( filepath )
        zf.close()

        return True
    # end of BibleWriter.toDrupalBible



    def toPickle( self, outputFolder=None ):
        """
        Saves this Python object as a pickle file (plus a zipped version for downloading).
        """
        if Globals.verbosityLevel > 1: print( "Running BibleWriter:toPickle..." )
        if not outputFolder: outputFolder = "OutputFiles/BOS_Bible_Object_Pickle/"
        if not os.access( outputFolder, os.F_OK ): os.makedirs( outputFolder ) # Make the empty folder if there wasn't already one there

        self.pickle( folder=outputFolder )

        # Now create a zipped version
        filename = (self.abbreviation if self.abbreviation else self.name) + '.pickle' # Same as in InternalBible.pickle()
        filepath = os.path.join( outputFolder, filename )
        if Globals.verbosityLevel > 2: print( "  Zipping {} pickle file...".format( filename ) )
        zf = zipfile.ZipFile( filepath+'.zip', 'w', compression=zipfile.ZIP_DEFLATED )
        zf.write( filepath, filename )
        zf.close()

        return True
    # end of BibleWriter.toPickle



    #def doExport( self, n ):
        #"""
        #Only used for multiprocessing.
        #"""
        #print( "BibleWriter.doExport( {} )".format( n ) )
        #if n==0: f = self.toUSFM
        #elif n==1: f = self.toMediaWiki
        #elif n==2: f = self.toZefaniaXML
        #elif n==3: f = self.toUSXXML
        #elif n==4: f = self.toOSISXML
        #elif n==5: f = self.toSwordModule
        #elif n==6: f = self.toHTML5
        #return f( self.__outputFolders[n] )
    ## end of BibleWriter.doExport


    def doAllExports( self, givenOutputFolderName=None, wantPhotoBible=False, wantPDFs=False ):
        """
        If the output folder is specified, it is expected that it's already created.
        Otherwise a new subfolder is created in the current folder.

        The two very processor intensive exports require explicit inclusion.
        """
        allWord = "all" if wantPhotoBible and wantPDFs else "most"
        if Globals.verbosityLevel > 1: print( "BibleWriter.doAllExports: " + _("Exporting {} ({}) to {} formats...").format( self.name, self.objectTypeString, allWord ) )

        if givenOutputFolderName == None:
            givenOutputFolderName = "OutputFiles/"
            if not os.access( givenOutputFolderName, os.F_OK ):
                if Globals.verbosityLevel > 2: print( "BibleWriter.doAllExports: " + _("creating '{}' output folder").format( givenOutputFolderName ) )
                os.makedirs( givenOutputFolderName ) # Make the empty folder if there wasn't already one there
        if Globals.debugFlag: assert( givenOutputFolderName and isinstance( givenOutputFolderName, str ) )
        if not os.access( givenOutputFolderName, os.W_OK ): # Then our output folder is not writeable!
            logging.critical( "BibleWriter.doAllExports: " + _("Given '{}' folder is unwritable").format( givenOutputFolderName ) )
            return False

        # Define our various output folders
        pickleOutputFolder = os.path.join( givenOutputFolderName, "BOS_Bible_Object_Pickle/" )
        listOutputFolder = os.path.join( givenOutputFolderName, "BOS_Lists/" )
        pseudoUSFMOutputFolder = os.path.join( givenOutputFolderName, "BOS_PseudoUSFM_" + "Export/" )
        USFMOutputFolder = os.path.join( givenOutputFolderName, "BOS_USFM_" + ("Reexport/" if self.objectTypeString=='USFM' else "Export/" ) )
        textOutputFolder = os.path.join( givenOutputFolderName, "BOS_PlainText_" + ("Reexport/" if self.objectTypeString=='Text' else "Export/" ) )
        htmlOutputFolder = os.path.join( givenOutputFolderName, "BOS_HTML5_" + "Export/" )
        CBOutputFolder = os.path.join( givenOutputFolderName, "BOS_CustomBible_" + "Export/" )
        TWOutputFolder = os.path.join( givenOutputFolderName, "BOS_theWord_" + ("Reexport/" if self.objectTypeString=='TheWord' else "Export/" ) )
        MySwOutputFolder = os.path.join( givenOutputFolderName, "BOS_MySword_" + ("Reexport/" if self.objectTypeString=='MySword' else "Export/" ) )
        ESwOutputFolder = os.path.join( givenOutputFolderName, "BOS_e-Sword_" + ("Reexport/" if self.objectTypeString=='e-Sword' else "Export/" ) )
        MWOutputFolder = os.path.join( givenOutputFolderName, "BOS_MediaWiki_" + ("Reexport/" if self.objectTypeString=='MediaWiki' else "Export/" ) )
        zefOutputFolder = os.path.join( givenOutputFolderName, "BOS_Zefania_" + ("Reexport/" if self.objectTypeString=='Zefania' else "Export/" ) )
        hagOutputFolder = os.path.join( givenOutputFolderName, "BOS_Haggai_" + ("Reexport/" if self.objectTypeString=='Haggia' else "Export/" ) )
        OSOutputFolder = os.path.join( givenOutputFolderName, "BOS_OpenSong_" + ("Reexport/" if self.objectTypeString=='OpenSong' else "Export/" ) )
        USXOutputFolder = os.path.join( givenOutputFolderName, "BOS_USX_" + ("Reexport/" if self.objectTypeString=='USX' else "Export/" ) )
        USFXOutputFolder = os.path.join( givenOutputFolderName, "BOS_USFX_" + ("Reexport/" if self.objectTypeString=='USFX' else "Export/" ) )
        OSISOutputFolder = os.path.join( givenOutputFolderName, "BOS_OSIS_" + ("Reexport/" if self.objectTypeString=='OSIS' else "Export/" ) )
        swOutputFolder = os.path.join( givenOutputFolderName, "BOS_Sword_" + ("Reexport/" if self.objectTypeString=='Sword' else "Export/" ) )
        SwSOutputFolder = os.path.join( givenOutputFolderName, "BOS_SwordSearcher_" + "Export/" )
        DrOutputFolder = os.path.join( givenOutputFolderName, "BOS_DrupalBible_" + ("Reexport/" if self.objectTypeString=='DrupalBible' else "Export/" ) )
        photoOutputFolder = os.path.join( givenOutputFolderName, "BOS_PhotoBible_Export/" )
        TeXOutputFolder = os.path.join( givenOutputFolderName, "BOS_TeX_" + "Export/" )

        if not wantPhotoBible:
            if Globals.verbosityLevel > 2: print( "BibleWriter.doAllExports: " + _("Skipping PhotoBible export") )
            PhotoBibleExportResult = None
        if not wantPDFs:
            if Globals.verbosityLevel > 2: print( "BibleWriter.doAllExports: " + _("Skipping TeX/PDF export") )
            TeXExportResult = None

        # Pickle this Bible object
        # NOTE: This must be done before self.__setupWriter is called
        #       because the BRL object has a recursive pointer to self and the pickle fails
        if Globals.debugFlag: pickleResult = self.toPickle( pickleOutputFolder ) # halts if fails
        else:
            try: pickleResult = self.toPickle( pickleOutputFolder )
            except:
                pickleResult = False
                print( "BibleWriter.doAllExports: pickle( {} ) failed.".format( pickleOutputFolder ) )

        if Globals.debugFlag:
            listOutputResult = self.makeLists( listOutputFolder )
            pseudoUSFMExportResult = self.toPseudoUSFM( pseudoUSFMOutputFolder )
            USFMExportResult = self.toUSFM( USFMOutputFolder )
            textExportResult = self.toText( textOutputFolder )
            htmlExportResult = self.toHTML5( htmlOutputFolder )
            CBExportResult = self.toCustomBible( CBOutputFolder )
            MWExportResult = self.toMediaWiki( MWOutputFolder )
            ZefExportResult = self.toZefaniaXML( zefOutputFolder )
            HagExportResult = self.toHaggaiXML( hagOutputFolder )
            OSExportResult = self.toOpenSongXML( OSOutputFolder )
            USXExportResult = self.toUSXXML( USXOutputFolder )
            USFXExportResult = self.toUSFXXML( USFXOutputFolder )
            OSISExportResult = self.toOSISXML( OSISOutputFolder )
            swExportResult = self.toSwordModule( swOutputFolder )
            TWExportResult = self.totheWord( TWOutputFolder )
            MySwExportResult = self.toMySword( MySwOutputFolder )
            ESwExportResult = self.toESword( ESwOutputFolder )
            SwSExportResult = self.toSwordSearcher( SwSOutputFolder )
            DrExportResult = self.toDrupalBible( DrOutputFolder )
            if wantPhotoBible: PhotoBibleExportResult = self.toPhotoBible( photoOutputFolder )
            if wantPDFs: TeXExportResult = self.toTeX( TeXOutputFolder ) # Put this last since it's slowest
        elif Globals.maxProcesses > 1: # Process all the exports with different threads
            # DON'T KNOW WHY THIS CAUSES A SEGFAULT
            self.__outputFolders = [USFMOutputFolder, CBOutputFolder, MWOutputFolder, zOutputFolder, USXOutputFolder, USFXOutputFolder,
                                    OSISOutputFolder, swOutputFolder, htmlOutputFolder]
            #self.__outputProcesses = [self.toUSFM, self.toCustomBible, self.toMediaWiki, self.toZefaniaXML, self.toUSXXML, self.toUSFXXML,
                                    #self.toOSISXML, self.toSwordModule, self.toHTML5]
            #assert( len(self.__outputFolders) == len(self.__outputProcesses) )
            print( "here1" )
            with multiprocessing.Pool( processes=Globals.maxProcesses ) as pool: # start worker processes
                print( "here2" )
                print( range( len(self.__outputFolders) ) )
                results = pool.map( self.doExport, range( len(self.__outputFolders) ) ) # have the pool do our loads
                print( "got results", len(results) )
                assert( len(results) == len(self.__outputFolders) )
                USFMExportResult = results[0]
                CBExportResult = results[0]
                MWExportResult = results[1]
                ZefExportResult = results[2]
                HagExportResult = results[2]
                OSExportResult = results[2]
                USXExportResult = results[3]
                USFXExportResult = results[3]
                OSISExportResult = results[4]
                swExportResult = results[5]
                htmlExportResult = results[6]
                SwSExportResult = results[6]
                DrExportResult = results[7]
                if wantPhotoBible: PhotoBibleExportResult = results[0]
                if wantPDFs: TeXExportResult = results[6]
        else: # Just single threaded and not debugging
            try: listOutputResult = self.makeLists( listOutputFolder )
            except Exception as err:
                listOutputResult = False
                print("BibleWriter.doAllExports.makeLists Unexpected error:", sys.exc_info()[0], err)
                logging.error( "BibleWriter.doAllExports.makeLists: Oops, failed!" )
            try: pseudoUSFMExportResult = self.toPseudoUSFM( pseudoUSFMOutputFolder )
            except Exception as err:
                pseudoUSFMExportResult = False
                print("BibleWriter.doAllExports.toPseudoUSFM Unexpected error:", sys.exc_info()[0], err)
                logging.error( "BibleWriter.doAllExports.toPseudoUSFM: Oops, failed!" )
            try: USFMExportResult = self.toUSFM( USFMOutputFolder )
            except Exception as err:
                USFMExportResult = False
                print("BibleWriter.doAllExports.toUSFM Unexpected error:", sys.exc_info()[0], err)
                logging.error( "BibleWriter.doAllExports.toUSFM: Oops, failed!" )
            try: textExportResult = self.toText( textOutputFolder )
            except Exception as err:
                textExportResult = False
                print("BibleWriter.doAllExports.toText Unexpected error:", sys.exc_info()[0], err)
                logging.error( "BibleWriter.doAllExports.toText: Oops, failed!" )
            try: htmlExportResult = self.toHTML5( htmlOutputFolder )
            except Exception as err:
                htmlExportResult = False
                print("BibleWriter.doAllExports.toHTML5 Unexpected error:", sys.exc_info()[0], err)
                logging.error( "BibleWriter.doAllExports.toHTML5: Oops, failed!" )
            try: CBExportResult = self.toCustomBible( CBOutputFolder )
            except Exception as err:
                CBExportResult = False
                print("BibleWriter.doAllExports.toCustomBible Unexpected error:", sys.exc_info()[0], err)
                logging.error( "BibleWriter.doAllExports.toCustomBible: Oops, failed!" )
            try: MWExportResult = self.toMediaWiki( MWOutputFolder )
            except Exception as err:
                MWExportResult = False
                print("BibleWriter.doAllExports.toMediaWiki Unexpected error:", sys.exc_info()[0], err)
                logging.error( "BibleWriter.doAllExports.toMediaWiki: Oops, failed!" )
            try: ZefExportResult = self.toZefaniaXML( zefOutputFolder )
            except Exception as err:
                ZefExportResult = False
                print("BibleWriter.doAllExports.toZefaniaXML Unexpected error:", sys.exc_info()[0], err)
                logging.error( "BibleWriter.doAllExports.toZefaniaXML: Oops, failed!" )
            try: HagExportResult = self.toHaggaiXML( hagOutputFolder )
            except Exception as err:
                HagExportResult = False
                print("BibleWriter.doAllExports.toHaggaiXML Unexpected error:", sys.exc_info()[0], err)
                logging.error( "BibleWriter.doAllExports.toHaggaiXML: Oops, failed!" )
            try: OSExportResult = self.toOpenSongXML( OSOutputFolder )
            except Exception as err:
                OSExportResult = False
                print("BibleWriter.doAllExports.toOpenSongXML Unexpected error:", sys.exc_info()[0], err)
                logging.error( "BibleWriter.doAllExports.toOpenSongXML: Oops, failed!" )
            try: USXExportResult = self.toUSXXML( USXOutputFolder )
            except Exception as err:
                USXExportResult = False
                print("BibleWriter.doAllExports.toUSXXML Unexpected error:", sys.exc_info()[0], err)
                logging.error( "BibleWriter.doAllExports.toUSXXML: Oops, failed!" )
            try: USFXExportResult = self.toUSFXXML( USFXOutputFolder )
            except Exception as err:
                USFXExportResult = False
                print("BibleWriter.doAllExports.toUSFXXML Unexpected error:", sys.exc_info()[0], err)
                logging.error( "BibleWriter.doAllExports.toUSFXXML: Oops, failed!" )
            try: OSISExportResult = self.toOSISXML( OSISOutputFolder )
            except Exception as err:
                OSISExportResult = False
                print("BibleWriter.doAllExports.toOSISXML Unexpected error:", sys.exc_info()[0], err)
                logging.error( "BibleWriter.doAllExports.toOSISXML: Oops, failed!" )
            try: swExportResult = self.toSwordModule( swOutputFolder )
            except Exception as err:
                swExportResult = False
                print("BibleWriter.doAllExports.toSwordModule Unexpected error:", sys.exc_info()[0], err)
                logging.error( "BibleWriter.doAllExports.toSwordModule: Oops, failed!" )
            try: TWExportResult = self.totheWord( TWOutputFolder )
            except Exception as err:
                TWExportResult = False
                print("BibleWriter.doAllExports.totheWord Unexpected error:", sys.exc_info()[0], err)
                logging.error( "BibleWriter.doAllExports.totheWord: Oops, failed!" )
            try: MySwExportResult = self.toMySword( MySwOutputFolder )
            except Exception as err:
                MySwExportResult = False
                print("BibleWriter.doAllExports.toMySword Unexpected error:", sys.exc_info()[0], err)
                logging.error( "BibleWriter.doAllExports.toMySword: Oops, failed!" )
            try: ESwExportResult = self.toESword( ESwOutputFolder )
            except Exception as err:
                ESwExportResult = False
                print("BibleWriter.doAllExports.toESword Unexpected error:", sys.exc_info()[0], err)
                logging.error( "BibleWriter.doAllExports.toESword: Oops, failed!" )
            try: SwSExportResult = self.toSwordSearcher( SwSOutputFolder )
            except Exception as err:
                SwSExportResult = False
                print("BibleWriter.doAllExports.toSwordSearcher Unexpected error:", sys.exc_info()[0], err)
                logging.error( "BibleWriter.doAllExports.toSwordSearcher: Oops, failed!" )
            try: DrExportResult = self.toDrupalBible( DrOutputFolder )
            except Exception as err:
                DrExportResult = False
                print("BibleWriter.doAllExports.toDrupalBible Unexpected error:", sys.exc_info()[0], err)
                logging.error( "BibleWriter.doAllExports.toDrupalBible: Oops, failed!" )
            if wantPhotoBible:
                try: PhotoBibleExportResult = self.toPhotoBible( photoOutputFolder )
                except Exception as err:
                    PhotoBibleExportResult = False
                    print("BibleWriter.doAllExports.toPhotoBible Unexpected error:", sys.exc_info()[0], err)
                    logging.error( "BibleWriter.doAllExports.toPhotoBible: Oops, failed!" )
            if wantPDFs: # Do TeX export last because it's slowest
                try: TeXExportResult = self.toTeX( TeXOutputFolder )
                except Exception as err:
                    TeXExportResult = False
                    print("BibleWriter.doAllExports.toTeX Unexpected error:", sys.exc_info()[0], err)
                    logging.error( "BibleWriter.doAllExports.toTeX: Oops, failed!" )

        if Globals.verbosityLevel > 1:
            if pickleResult and listOutputResult and pseudoUSFMExportResult and USFMExportResult and CBExportResult \
            and textExportResult and (PhotoBibleExportResult or not wantPhotoBible) \
            and TWExportResult and MySwExportResult and ESwExportResult and MWExportResult \
            and ZefExportResult and HagExportResult and OSExportResult and USXExportResult and USFXExportResult \
            and OSISExportResult and swExportResult and htmlExportResult and SwSExportResult and DrExportResult \
            and (TeXExportResult or not wantPDFs):
                print( "BibleWriter.doAllExports finished them all successfully!" )
            else: print( "BibleWriter.doAllExports finished:  Pck={}  Lst={}  PsUSFM={} USFM={}  CB={}  Tx={}  PB={} TW={} MySw={} eSw={}  MW={}  Zef={} Hag={} OS={} USX={} USFX={} OSIS={}  Sw={}  HTML={} TeX={} SwS={} Dr={}" \
                    .format( pickleResult, listOutputResult, pseudoUSFMExportResult, USFMExportResult, CBExportResult,
                                textExportResult, PhotoBibleExportResult, TWExportResult, MySwExportResult, ESwExportResult, MWExportResult,
                                ZefExportResult, HagExportResult, OSExportResult, USXExportResult, USFXExportResult,
                                OSISExportResult, swExportResult, htmlExportResult, TeXExportResult,
                                SwSExportResult, DrExportResult ) )
        return { 'Pickle':pickleResult,
                    'listOutput':listOutputResult, 'pseudoUSFMExport':pseudoUSFMExportResult, 'USFMExport':USFMExportResult,
                    'CustomBibleExport':CBExportResult,  'textExport':textExportResult, 'PhotoBibleExport':PhotoBibleExportResult,
                    'TWExport':TWExportResult, 'MySwExport':MySwExportResult, 'ESwExport':ESwExportResult,
                    'MWExport':MWExportResult, 'ZefExport':ZefExportResult, 'HagExport':HagExportResult, 'OSExport':OSExportResult,
                    'USXExport':USXExportResult, 'USFXExport':USFXExportResult, 'OSISExport':OSISExportResult, 'swExport':swExportResult,
                    'htmlExport':htmlExportResult, 'TeXExport':TeXExportResult, 'SwSExport':SwSExportResult,
                    'DrExport':DrExportResult, }
    # end of BibleWriter.doAllExports
# end of class BibleWriter



def demo():
    """
    Demonstrate reading and processing some Bible databases.
    """
    if Globals.verbosityLevel > 0: print( ProgNameVersion )

    # Since this is only designed to be a virtual base class, it can't actually do much at all
    BW = BibleWriter()
    BW.objectNameString = "Dummy test Bible Writer object"
    if Globals.verbosityLevel > 0: print( BW ); print()

    if 1: # Test reading and writing a USFM Bible
        from USFMBible import USFMBible
        from USFMFilenames import USFMFilenames
        testData = ( # name, abbreviation, folder for USFM files
                #("CustomTest", "Custom", ".../",),
                #("USFMTest1", "USFM1", "Tests/DataFilesForTests/USFMTest1/",),
                #("USFMTest2", "MBTV", "Tests/DataFilesForTests/USFMTest2/",),
                #("WEB", "WEB", "Tests/DataFilesForTests/USFM-WEB/",),
                ("Matigsalug", "MBTV", "../../../../../Data/Work/Matigsalug/Bible/MBTV/",),
                #("MS-BT", "MBTBT", "../../../../../Data/Work/Matigsalug/Bible/MBTBT/",),
                #("MS-Notes", "MBTBC", "../../../../../Data/Work/Matigsalug/Bible/MBTBC/",),
                #("MS-ABT", "MBTABT", "../../../../../Data/Work/Matigsalug/Bible/MBTABT/",),
                #("WEB", "WEB", "../../../../../Data/Work/Bibles/English translations/WEB (World English Bible)/2012-06-23 eng-web_usfm/",),
                #("WEB", "WEB", "../../../../../Data/Work/Bibles/From eBible/WEB/eng-web_usfm 2013-07-18/",),
                #("WEB", "WEB", "../../../../../Data/Work/Bibles/English translations/WEB (World English Bible)/2014-03-05 eng-web_usfm/",),
                #("WEB", "WEB", "../../../../../Data/Work/Bibles/English translations/WEB (World English Bible)/2014-04-23 eng-web_usfm/",),
                ) # You can put your USFM test folder here

        for j, (name, abbrev, testFolder) in enumerate( testData ):
            if os.access( testFolder, os.R_OK ):
                UB = USFMBible( testFolder, name, abbrev )
                UB.load()
                if Globals.verbosityLevel > 0: print( '\nBWr A'+str(j+1)+'/', UB )
                if Globals.strictCheckingFlag: UB.check()
                #UB.toPhotoBible(); halt
                doaResults = UB.doAllExports( wantPhotoBible=True, wantPDFs=True )
                if Globals.strictCheckingFlag: # Now compare the original and the derived USX XML files
                    outputFolder = "OutputFiles/BOS_USFM_Reexport/"
                    fN = USFMFilenames( testFolder )
                    f1 = os.listdir( testFolder ) # Originals
                    f2 = os.listdir( outputFolder ) # Derived
                    if Globals.verbosityLevel > 1: print( "\nComparing original and re-exported USFM files..." )
                    for j, (BBB,filename) in enumerate( fN.getMaximumPossibleFilenameTuples() ):
                        if filename in f1 and filename in f2:
                            #print( "\n{}: {} {}".format( j+1, BBB, filename ) )
                            result = Globals.fileCompare( filename, filename, testFolder, outputFolder )
                            if Globals.debugFlag:
                                if not result: halt
            else: print( "Sorry, test folder '{}' is not readable on this computer.".format( testFolder ) )


    if 0: # Test reading and writing a USX Bible
        from USXXMLBible import USXXMLBible
        from USXFilenames import USXFilenames
        testData = (
                #("Matigsalug", "../../../../../Data/Work/VirtualBox_Shared_Folder/PT7.3 Exports/USXExports/Projects/MBTV/",),
                ("MatigsalugUSX", "../../../../../Data/Work/VirtualBox_Shared_Folder/PT7.4 Exports/USX Exports/MBTV/",),
                ) # You can put your USX test folder here

        for j, (name, testFolder) in enumerate( testData ):
            if os.access( testFolder, os.R_OK ):
                UB = USXXMLBible( testFolder, name )
                UB.load()
                if Globals.verbosityLevel > 0: print( '\nBWr B'+str(j+1)+'/', UB )
                if Globals.strictCheckingFlag: UB.check()
                doaResults = UB.doAllExports( wantPhotoBible=True, wantPDFs=True )
                if Globals.strictCheckingFlag: # Now compare the original and the derived USX XML files
                    outputFolder = "OutputFiles/BOS_USX_Reexport/"
                    fN = USXFilenames( testFolder )
                    f1 = os.listdir( testFolder ) # Originals
                    f2 = os.listdir( outputFolder ) # Derived
                    if Globals.verbosityLevel > 1: print( "\nComparing original and re-exported USX files..." )
                    for j, (BBB,filename) in enumerate( fN.getPossibleFilenames() ):
                        if filename in f1 and filename in f2:
                            #print( "\n{}: {} {}".format( j+1, BBB, filename ) )
                            result = Globals.fileCompareXML( filename, filename, testFolder, outputFolder )
                            if Globals.debugFlag:
                                if not result: halt
            else: print( "Sorry, test folder '{}' is not readable on this computer.".format( testFolder ) )


    if 0: # Test reading USFM Bibles and exporting to theWord and MySword
        from USFMBible import USFMBible
        from TheWordBible import theWordFileCompare
        mainFolder = "Tests/DataFilesForTests/theWordRoundtripTestFiles/"
        testData = (
                ("aai", "Tests/DataFilesForTests/theWordRoundtripTestFiles/aai 2013-05-13/",),
                ("acc", "Tests/DataFilesForTests/theWordRoundtripTestFiles/accNT 2012-01-20/",),
                ("acf", "Tests/DataFilesForTests/theWordRoundtripTestFiles/acfDBL 2013-02-03/",),
                ("acr-n", "Tests/DataFilesForTests/theWordRoundtripTestFiles/acrNDBL 2013-03-08/",),
                ("acr-t", "Tests/DataFilesForTests/theWordRoundtripTestFiles/accTDBL 2013-03-08/",),
                ("agr", "Tests/DataFilesForTests/theWordRoundtripTestFiles/agrDBL 2013-03-08/",),
                ("agu", "Tests/DataFilesForTests/theWordRoundtripTestFiles/aguDBL 2013-03-08/",),
                ("ame", "Tests/DataFilesForTests/theWordRoundtripTestFiles/ameDBL 2013-02-13/",),
                ("amr", "Tests/DataFilesForTests/theWordRoundtripTestFiles/amrDBL 2013-02-13/",),
                ("apn", "Tests/DataFilesForTests/theWordRoundtripTestFiles/apnDBL 2013-02-13/",),
                ("apu", "Tests/DataFilesForTests/theWordRoundtripTestFiles/apuDBL 2013-02-14/",),
                ("apy", "Tests/DataFilesForTests/theWordRoundtripTestFiles/apyDBL 2013-02-15/",),
                ("arn", "Tests/DataFilesForTests/theWordRoundtripTestFiles/arnDBL 2013-03-08/",),
                ("auc", "Tests/DataFilesForTests/theWordRoundtripTestFiles/aucDBL 2013-02-26/",),
                ) # You can put your USFM test folder here

        for j, (name, testFolder) in enumerate( testData ):
            if os.access( testFolder, os.R_OK ):
                UB = USFMBible( testFolder, name )
                UB.load()
                if Globals.verbosityLevel > 0: print( '\nBWr C'+str(j+1)+'/', UB )
                #if Globals.strictCheckingFlag: UB.check()
                #result = UB.totheWord()
                doaResults = UB.doAllExports( wantPhotoBible=True, wantPDFs=True )
                if Globals.strictCheckingFlag: # Now compare the supplied and the exported theWord modules
                    outputFolder = "OutputFiles/BOS_theWord_Export/"
                    if os.path.exists( os.path.join( mainFolder, name + '.nt' ) ): ext = '.nt'
                    elif os.path.exists( os.path.join( mainFolder, name + '.ont' ) ): ext = '.ont'
                    elif os.path.exists( os.path.join( mainFolder, name + '.ot' ) ): ext = '.ot'
                    else: halt
                    fn1 = name + ext # Supplied
                    fn2 = name + ext # Created
                    if Globals.verbosityLevel > 1: print( "\nComparing supplied and exported theWord files..." )
                    result = theWordFileCompare( fn1, fn2, mainFolder, outputFolder, exitCount=10 )
                    if not result:
                        print( "theWord modules did NOT match" )
                        #if Globals.debugFlag: halt
            else: print( "Sorry, test folder '{}' is not readable on this computer.".format( testFolder ) )
# end of demo


if __name__ == '__main__':
    # Configure basic set-up
    parser = Globals.setup( ProgName, ProgVersion )
    Globals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    demo()

    Globals.closedown( ProgName, ProgVersion )
# end of BibleWriter.py