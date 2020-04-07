#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# BibleWriter.py
#
# Module writing out InternalBibles in various formats.
#
# Copyright (C) 2010-2020 Robert Hunt
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
EARLY PROTOTYPE ONLY AT THIS STAGE! (Developmental code not very well structured yet.)

TODO: Check handling of chapter -1 == introduction
TODO: Rewrite some of the loops to take advantage of 'v=' entries.
TODO: Go through all unhandled fields and find out how they should be handled.

Module for exporting Bibles in various formats listed below.

A class which extends InternalBible to add Bible export functions.

Contains functions:
    toPickleObject( self, outputFolderpath:Optional[Path]=None )
    toPickledBible( self, outputFolderpath:Optional[Path]=None )
    toBOSJSONBible( self, outputFolderpath:Optional[Path]=None )
    makeLists( outputFolderpath:Optional[Path]=None )
    toBOSBCV( self, outputFolderpath:Optional[Path]=None ) — one file per verse using our internal Bible format
    toPseudoUSFM( outputFolderpath:Optional[Path]=None ) — this is our internal Bible format — exportable for debugging purposes
            For more details see InternalBible.py, InternalBibleBook.py, InternalBibleInternals.py
    toUSFM2( outputFolderpath:Optional[Path]=None. removeVerseBridges=False )
    toUSFM3( outputFolderpath:Optional[Path]=None. removeVerseBridges=False )
    toESFM( outputFolderpath:Optional[Path]=None )
    toText( outputFolderpath:Optional[Path]=None )
    toVPL( outputFolderpath:Optional[Path]=None )
    toMarkdown( outputFolderpath:Optional[Path]=None )
    #toDoor43( outputFolderpath:Optional[Path]=None, controlDict=None, validationSchema=None )
    toHTML5( outputFolderpath:Optional[Path]=None, controlDict=None, validationSchema=None, humanReadable=True )
    toBibleDoor( outputFolderpath:Optional[Path]=None, removeVerseBridges=False )
    toUSX2XML( outputFolderpath:Optional[Path]=None, controlDict=None, validationSchema=None )
    toUSX3XML( outputFolderpath:Optional[Path]=None, controlDict=None, validationSchema=None )
    toUSFXXML( outputFolderpath:Optional[Path]=None, controlDict=None, validationSchema=None )
    toOSISXML( outputFolderpath:Optional[Path]=None, controlDict=None, validationSchema=None )
    toZefaniaXML( outputFolderpath:Optional[Path]=None, controlDict=None, validationSchema=None )
    toHaggaiXML( outputFolderpath:Optional[Path]=None, controlDict=None, validationSchema=None )
    toOpenSongXML( outputFolderpath:Optional[Path]=None, controlDict=None, validationSchema=None )
    toSwordModule( outputFolderpath:Optional[Path]=None, controlDict=None, validationSchema=None )
    totheWord( outputFolderpath:Optional[Path]=None )
    toMySword( outputFolderpath:Optional[Path]=None )
    toESword( outputFolderpath:Optional[Path]=None )
    toMyBible( outputFolderpath:Optional[Path]=None )
    toSwordSearcher( outputFolderpath:Optional[Path]=None )
    toDrupalBible( outputFolderpath:Optional[Path]=None )
    toPhotoBible( outputFolderpath:Optional[Path]=None )
    toODF( outputFolderpath:Optional[Path]=None ) for LibreOffice/OpenOffice exports
    toTeX( outputFolderpath:Optional[Path]=None ) and thence to PDF
    doAllExports( givenOutputFolderName=None, wantPhotoBible=False, wantODFs=False, wantPDFs=False )
        (doAllExports supports multiprocessing — it shares the exports out amongst available processes)

Note that not all exports export all books.
    Some formats only handle subsets of books (or markers/fields),
        e.g. may not handle front or back matter, glossaries, or deuterocanonical books.
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2020-04-07' # by RJH
SHORT_PROGRAM_NAME = "BibleWriter"
PROGRAM_NAME = "Bible writer"
PROGRAM_VERSION = '0.96'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'
programNameVersionDate = f'{programNameVersion} {_("last modified")} {LAST_MODIFIED_DATE}'

debuggingThisModule = False

OSISNameSpace = 'http://www.bibletechnologies.net/2003/OSIS/namespace'
OSISSchemaLocation = 'http://www.bibletechnologies.net/osisCore.2.1.1.xsd'


from typing import Dict, List, Tuple, Optional, Any
import sys
import os, shutil, logging
from pathlib import Path
from datetime import datetime
import re, json, pickle
import zipfile, tarfile
import subprocess, multiprocessing
import signal

if __name__ == '__main__':
    aboveFolderPath = os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) )
    if aboveFolderPath not in sys.path:
        sys.path.insert( 0, aboveFolderPath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.InputOutput import ControlFiles
from BibleOrgSys.InputOutput.MLWriter import MLWriter
from BibleOrgSys.Internals.InternalBibleInternals import BOS_ADDED_NESTING_MARKERS, BOS_NESTING_MARKERS
from BibleOrgSys.Internals.InternalBible import InternalBible
from BibleOrgSys.Reference.BibleOrganisationalSystems import BibleOrganisationalSystem
from BibleOrgSys.Reference.BibleReferences import BibleReferenceList
from BibleOrgSys.Reference.USFM3Markers import OFTEN_IGNORED_USFM_HEADER_MARKERS, USFM_ALL_TITLE_MARKERS, \
                            USFM_ALL_INTRODUCTION_MARKERS, USFM_PRECHAPTER_MARKERS, \
                            USFM_ALL_SECTION_HEADING_MARKERS, \
                            USFM_BIBLE_PARAGRAPH_MARKERS, USFM_ALL_BIBLE_PARAGRAPH_MARKERS
from BibleOrgSys.Misc.NoisyReplaceFunctions import noisyRegExDeleteAll



logger = logging.getLogger( SHORT_PROGRAM_NAME )



defaultControlFolderpath = Path( 'ControlFiles/' ) # Relative to the current working directory
def setDefaultControlFolderpath( newFolderName:Path ) -> None:
    """
    Set the global default folder for control files.
    """
    global defaultControlFolderpath
    if BibleOrgSysGlobals.verbosityLevel > 1:
        print( f"defaultControlFolderpath changed from {defaultControlFolderpath} to {newFolderName}" )

    defaultControlFolderpath = newFolderName
# end of BibleWriter.setDefaultControlFolderpath



ALL_CHAR_MARKERS = None
# The following are used by both toHTML5 and toBibleDoor
ipHTMLClassDict = {'ip':'introductionParagraph', 'ipi':'introductionParagraphIndented',
                    'ipq':'introductionQuoteParagraph', 'ipr':'introductionRightAlignedParagraph',
                    'im':'introductionFlushLeftParagraph', 'imi':'introductionIndentedFlushLeftParagraph',
                    'imq':'introductionFlushLeftQuoteParagraph',
                    'iq1':'introductionPoetryParagraph1','iq2':'introductionPoetryParagraph2','iq3':'introductionPoetryParagraph3','iq4':'introductionPoetryParagraph4',
                    'iex':'introductionExplanation', }
pqHTMLClassDict = {'p':'proseParagraph', 'm':'flushLeftParagraph',
                    'pmo':'embeddedOpeningParagraph', 'pm':'embeddedParagraph', 'pmc':'embeddedClosingParagraph',
                    'pmr':'embeddedRefrainParagraph',
                    'pi1':'indentedProseParagraph1','pi2':'indentedProseParagraph2','pi3':'indentedProseParagraph3','pi4':'indentedProseParagraph4',
                    'mi':'indentedFlushLeftParagraph', 'cls':'closureParagraph',
                    'pc':'centeredProseParagraph', 'pr':'rightAlignedProseParagraph',
                    'ph1':'hangingProseParagraph1','ph2':'hangingProseParagraph2','ph3':'hangingProseParagraph3','ph4':'hangingProseParagraph4',

                    'q1':'poetryParagraph1','q2':'poetryParagraph2','q3':'poetryParagraph3','q4':'poetryParagraph4',
                    'qr':'rightAlignedPoetryParagraph', 'qc':'centeredPoetryParagraph',
                    'qm1':'embeddedPoetryParagraph1','qm2':'embeddedPoetryParagraph2','qm3':'embeddedPoetryParagraph3','qm4':'embeddedPoetryParagraph4', }



def killLibreOfficeServiceManager() -> None:
    """
    Doesn't work in Windows.
    """
    if debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 2:
        print( "Killing LibreOffice ServiceManager…" )

    p = subprocess.Popen(['ps', 'xa'], stdout=subprocess.PIPE) # NOTE: Linux-only code!!!
    out, err = p.communicate()
    for lineBytes in out.splitlines():
        line = bytes.decode( lineBytes )
        #print( "line", repr(line) )
        if 'libreoffice' in line and "ServiceManager" in line:
            pid = int( line.split(None, 1)[0] )
            #print( "pid", pid )
            if BibleOrgSysGlobals.verbosityLevel > 1: logger.info( "  Killing {!r}".format( line ) )
            try: os.kill( pid, signal.SIGKILL )
            except PermissionError: # it must belong to another user
                logger.error( "Don't have permission to kill LibreOffice ServiceManager" )
# end of killLibreOfficeServiceManager


class BibleWriter( InternalBible ):
    """
    Class to export Bibles.

    The Bible class is based on this class.
    """
    def __init__( self ) -> None:
        """
        #    Create the object.
        #    """
        InternalBible.__init__( self  ) # Initialise the base class
        self.doneSetupGeneric = False

        global ALL_CHAR_MARKERS
        if ALL_CHAR_MARKERS is None:
            ALL_CHAR_MARKERS = BibleOrgSysGlobals.loadedUSFMMarkers.getCharacterMarkersList( expandNumberableMarkers=True )
    # end of BibleWriter.__init_


    def toPickleObject( self, outputFolderpath:Optional[Path]=None ) -> bool:
        """
        Saves this Python object as a pickle file (plus a zipped version for downloading).
        """
        if BibleOrgSysGlobals.debugFlag: print( "toPickleObject( {}, {} )".format( self.abbreviation, outputFolderpath ) )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Running BibleWriter:toPickleObject…" )
        if not outputFolderpath: outputFolderpath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_Bible_Object_Pickle/' )
        if not os.access( outputFolderpath, os.F_OK ): os.makedirs( outputFolderpath ) # Make the empty folder if there wasn't already one there

        result = self.pickle( folder=outputFolderpath )

        if result: # now create a zipped version
            filename = self.getAName( abbrevFirst=True )
            if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert filename
            filename = BibleOrgSysGlobals.makeSafeFilename( f'{filename}.pickle' ) # Same as in InternalBible.pickle()
            filepath = Path( outputFolderpath ).joinpath( filename )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( f"  Zipping {filename} pickle file…" )
            zf = zipfile.ZipFile( f'{filepath}.zip', 'w', compression=zipfile.ZIP_DEFLATED )
            zf.write( filepath, filename )
            zf.close()

            if BibleOrgSysGlobals.verbosityLevel > 0 and BibleOrgSysGlobals.maxProcesses > 1:
                print( "  BibleWriter.toPickleObject finished successfully." )
            return True
        else:
            print( "  BibleWriter.toPickleObject failed." )
            return False
    # end of BibleWriter.toPickleObject



    def toPickledBible( self, outputFolderpath:Optional[Path]=None,
                            metadataDict:Optional[Dict[str,Any]]=None, dataLevel=None, zipOnly:bool=False ):
        """
        Saves the Python book objects as pickle files
            then the Bible object (less books)
            and a version info file
            plus a zipped version of everthing for downloading.

        dataLevel:  1 = absolute minimal data saved (default)
                    2 = small amount saved
                    3 = all saved except BOS object

        Note: This can add up to a couple of GB if discovery data and everything else is included!

        We don't include all fields — these files are intended to be read-only only,
            i.e., not a full editable version.
        """
        from BibleOrgSys.Formats.PickledBible import createPickledBible

        if BibleOrgSysGlobals.debugFlag:
            print( "toPickledBible( {}, {}, {}, {} )".format( outputFolderpath, metadataDict, dataLevel, zipOnly ) )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Running BibleWriter:toPickledBible" )

        if not outputFolderpath: outputFolderpath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_PickledBible_Export/' )
        if not os.access( outputFolderpath, os.F_OK ): os.makedirs( outputFolderpath ) # Make the empty folder if there wasn't already one there

        return createPickledBible( self, outputFolderpath, metadataDict, dataLevel, zipOnly )
    # end of BibleWriter.toPickledBible



    def toBOSJSONBible( self, outputFolderpath:Optional[Path]=None, sourceURL:Optional[str]=None,
                                                                licenceString:Optional[str]=None ):
        """
        Saves the Python book objects as json files
            then the Bible object (less books)
            and a version info file
            plus a zipped version of everthing for downloading.

        Note: This can add up to a couple of GB if discovery data is included!
        """
        from BibleOrgSys.Formats.JSONBible import createBOSJSONBible
        if BibleOrgSysGlobals.debugFlag: print( "toBOSJSONBible( {}, {}, {} )".format( outputFolderpath, sourceURL, licenceString ) )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Running BibleWriter:toBOSJSONBible" )
        if not outputFolderpath: outputFolderpath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_JSONBible_Export/' )
        if not os.access( outputFolderpath, os.F_OK ): os.makedirs( outputFolderpath ) # Make the empty folder if there wasn't already one there

        if sourceURL is None: sourceURL = "Source: (unknown)"
        if licenceString is None: licenceString = "Licence: (unknown)"
        controlDict = {}

        return createBOSJSONBible( self, outputFolderpath, controlDict )
    # end of BibleWriter.toBOSJSONBible



    def __setupWriter( self ) -> None:
        """
        Do some generic system setting up.

        Unfortunately, I don't know how to do this in the _init__ function
            coz it uses self (which isn't actualised yet in init).
        """
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not self.doneSetupGeneric
        #if 'discoveryResults' not in self.__dict__: self.discover()
        if not self.doneSetupGeneric:
            self.genericBOS = BibleOrganisationalSystem( 'GENERIC' )
            self.genericBRL = BibleReferenceList( self.genericBOS, BibleObject=self ) # this prevents pickling!
                # because unfortunately it causes a recursive linking of objects
            self.doneSetupGeneric = True
    # end of BibleWriter.__setupWriter


    def __adjustControlDict( self, existingControlDict ):
        """
        Do some global name replacements in the given control dictionary.
        """
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert isinstance( existingControlDict, dict )
        if not existingControlDict: logger.warning( "adjustControlDict: The control dictionary is empty!" )
        for entry in existingControlDict:
            existingControlDict[entry] = existingControlDict[entry] \
                .replace( '__PROJECT_NAME__', self.projectName ) \
                .replace( '__PROJECT_ABBREVIATION__', self.getAName( abbrevFirst=True ) )
                #.replace( '__PROJECT_NAME__', BibleOrgSysGlobals.makeSafeFilename( self.projectName.replace( ' ', '_' ) ) )
            #print( entry, repr(existingControlDict[entry]) )
    # end of BibleWriter.__adjustControlDict



    def makeLists( self, outputFolderpath:Optional[Path]=None ):
        """
        Write the pseudo USFM out directly (for debugging, etc.).
            May write the rawLines 2-tuples to .rSFM files (if _rawLines still exists)
            Always writes the processed 5-tuples to .pSFM files (from _processedLines).
        """
        from BibleOrgSys.Internals import InternalBibleBook
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Running BibleWriter:makeLists…" )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert self.books

        if not self.doneSetupGeneric: self.__setupWriter()
        if 'discoveryResults' not in self.__dict__: self.discover()
        if not outputFolderpath: outputFolderpath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_Lists/' )
        if not os.access( outputFolderpath, os.F_OK ): os.makedirs( outputFolderpath ) # Make the empty folder if there wasn't already one there

        # Create separate sub-folders
        txtOutputFolder = os.path.join( outputFolderpath, 'TXT/' )
        if not os.access( txtOutputFolder, os.F_OK ): os.makedirs( txtOutputFolder ) # Make the empty folder if there wasn't already one there
        csvOutputFolder = os.path.join( outputFolderpath, 'CSV/' )
        if not os.access( csvOutputFolder, os.F_OK ): os.makedirs( csvOutputFolder ) # Make the empty folder if there wasn't already one there
        xmlOutputFolder = os.path.join( outputFolderpath, 'XML/' )
        if not os.access( xmlOutputFolder, os.F_OK ): os.makedirs( xmlOutputFolder ) # Make the empty folder if there wasn't already one there
        htmlOutputFolder = os.path.join( outputFolderpath, 'HTML/' )
        if not os.access( htmlOutputFolder, os.F_OK ): os.makedirs( htmlOutputFolder ) # Make the empty folder if there wasn't already one there

        #def countWords( marker, segment, location ):
            #""" Breaks the segment into words and counts them.
            #"""
            #def stripWordPunctuation( word ):
                #"""Removes leading and trailing punctuation from a word.
                    #Returns the "clean" word."""
                #while word and word[0] in InternalBibleBook.LEADING_WORD_PUNCT_CHARS:
                    #word = word[1:] # Remove leading punctuation
                #while word and word[-1] in InternalBibleBook.TRAILING_WORD_PUNCT_CHARS:
                    #word = word[:-1] # Remove trailing punctuation
                #if  '<' in word or '>' in word or '"' in word: print( "BibleWriter.makeLists: Need to escape HTML chars here 3s42", BBB, C, V, repr(word) )
                #return word
            ## end of stripWordPunctuation

            #words = segment.replace('—',' ').replace('–',' ').split() # Treat em-dash and en-dash as word break characters
            #for j,rawWord in enumerate(words):
                #if marker=='c' or marker=='v' and j==1 and rawWord.isdigit(): continue # Ignore the chapter and verse numbers (except ones like 6a)
                #word = rawWord
                #for internalMarker in InternalBibleBook.INTERNAL_SFMS_TO_REMOVE: word = word.replace( internalMarker, '' )
                #word = stripWordPunctuation( word )
                #if word and not word[0].isalnum():
                    ##print( word, stripWordPunctuation( word ) )
                    #if len(word) > 1:
                        #if BibleOrgSysGlobals.debugFlag: print( "BibleWriter.makeLists: {} {}:{} ".format( BBB, C, V ) + _("Have unexpected character starting word {!r}").format( word ) )
                        #word = word[1:]
                #if word: # There's still some characters remaining after all that stripping
                    #if BibleOrgSysGlobals.verbosityLevel > 3: # why???
                        #for k,char in enumerate(word):
                            #if not char.isalnum() and (k==0 or k==len(word)-1 or char not in InternalBibleBook.MEDIAL_WORD_PUNCT_CHARS):
                                #if BibleOrgSysGlobals.debugFlag: print( "BibleWriter.makeLists: {} {}:{} ".format( BBB, C, V ) + _("Have unexpected {!r} in word {!r}").format( char, word ) )
                    #lcWord = word.lower()
                    #isAReferenceOrNumber = True
                    #for char in word:
                        #if not char.isdigit() and char not in ':-,.': isAReferenceOrNumber = False; break
                    #if not isAReferenceOrNumber:
                        #allWordCounts[word] = 1 if word not in allWordCounts else allWordCounts[word] + 1
                        #allCaseInsensitiveWordCounts[lcWord] = 1 if lcWord not in allCaseInsensitiveWordCounts else allCaseInsensitiveWordCounts[lcWord] + 1
                        #if location == "main":
                            #mainTextWordCounts[word] = 1 if word not in mainTextWordCounts else mainTextWordCounts[word] + 1
                            #mainTextCaseInsensitiveWordCounts[lcWord] = 1 if lcWord not in mainTextCaseInsensitiveWordCounts else mainTextCaseInsensitiveWordCounts[lcWord] + 1
                    ##else: print( "excluded reference or number", word )
        ## end of countWords


        def printWordCounts( typeString, dictionary ):
            """ Given a description and a dictionary,
                    sorts and writes the word count data to text, csv, and xml files. """
            title = BibleOrgSysGlobals.makeSafeXML( typeString.replace('_',' ') + " sorted by word" )
            filenamePortion = BibleOrgSysGlobals.makeSafeFilename( typeString + "_sorted_by_word." )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "  " + _("Writing '{}*'…").format( filenamePortion ) )
            sortedWords = sorted(dictionary)
            with open( os.path.join( txtOutputFolder, filenamePortion )+'txt', 'wt', encoding='utf-8' ) as txtFile, \
                 open( os.path.join( csvOutputFolder, filenamePortion )+'csv', 'wt', encoding='utf-8' ) as csvFile, \
                 open( os.path.join( xmlOutputFolder, filenamePortion )+'xml', 'wt', encoding='utf-8' ) as xmlFile, \
                 open( os.path.join( htmlOutputFolder, filenamePortion )+'html', 'wt', encoding='utf-8' ) as htmlFile:
                    xmlFile.write( '<?xml version="1.0" encoding="utf-8"?>\n' ) # Write the xml header
                    xmlFile.write( '<entries>\n' ) # root element
                    htmlFile.write( '<html><header><title>{}</title></header>\n'.format( title ) ) # Write the html header
                    htmlFile.write( '<body><h1>{}</h1>\n'.format( title ) ) # Write the header
                    htmlFile.write( '<table><tr><th>Word</th><th>Count</th></tr>\n' )
                    for word in sortedWords:
                        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert ' ' not in word
                        txtFile.write( "{} {}\n".format( word, dictionary[word] ) )
                        csvFile.write( "{},{}\n".format( repr(word) if ',' in word else word, dictionary[word] ) )
                        #if  '<' in word or '>' in word or '"' in word: print( "BibleWriter.makeLists: Here 3g5d", repr(word) )
                        #if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert '<' not in word and '>' not in word and '"' not in word
                        xmlFile.write( "<entry><word>{}</word><count>{}</count></entry>\n".format( BibleOrgSysGlobals.makeSafeXML(word), dictionary[word] ) )
                        htmlFile.write( "<tr><td>{}</td><td>{}</td></tr>\n".format( BibleOrgSysGlobals.makeSafeXML(word), dictionary[word] ) )
                    xmlFile.write( '</entries>' ) # close root element
                    htmlFile.write( '</table></body></html>' ) # close open elements
            title = BibleOrgSysGlobals.makeSafeXML( typeString.replace('_',' ') + " sorted by count" )
            filenamePortion = BibleOrgSysGlobals.makeSafeFilename( typeString + "_sorted_by_count." )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "  " + _("Writing '{}*'…").format( filenamePortion ) )
            with open( os.path.join( txtOutputFolder, filenamePortion )+'txt', 'wt', encoding='utf-8' ) as txtFile, \
                 open( os.path.join( csvOutputFolder, filenamePortion )+'csv', 'wt', encoding='utf-8' ) as csvFile, \
                 open( os.path.join( xmlOutputFolder, filenamePortion )+'xml', 'wt', encoding='utf-8' ) as xmlFile, \
                 open( os.path.join( htmlOutputFolder, filenamePortion )+'html', 'wt', encoding='utf-8' ) as htmlFile:
                    xmlFile.write( '<?xml version="1.0" encoding="utf-8"?>\n' ) # Write the xml header
                    xmlFile.write( '<entries>\n' ) # root element
                    htmlFile.write( '<html><header><title>{}</title></header>\n'.format( title ) ) # Write the html header
                    htmlFile.write( '<body><h1>{}</h1>\n'.format( title ) ) # Write the header
                    htmlFile.write( '<table><tr><th>Word</th><th>Count</th></tr>\n' )
                    for word in sorted(sortedWords, key=dictionary.get):
                        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert ' ' not in word
                        txtFile.write( "{} {}\n".format( word, dictionary[word] ) )
                        csvFile.write( "{},{}\n".format( repr(word) if ',' in word else word, dictionary[word] ) )
                        #if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert '<' not in word and '>' not in word and '"' not in word
                        xmlFile.write( "<entry><word>{}</word><count>{}</count></entry>\n".format( BibleOrgSysGlobals.makeSafeXML(word), dictionary[word] ) )
                        htmlFile.write( "<tr><td>{}</td><td>{}</td></tr>\n".format( BibleOrgSysGlobals.makeSafeXML(word), dictionary[word] ) )
                    xmlFile.write( '</entries>' ) # close root element
                    htmlFile.write( '</table></body></html>' ) # close open elements
        # end of printWordCounts


        ## Initialise all our counters
        #allWordCounts, allCaseInsensitiveWordCounts = {}, {}
        #mainTextWordCounts, mainTextCaseInsensitiveWordCounts = {}, {}


        ## Determine all the counts
        #for BBB,bookObject in self.books.items():
            #C, V = '-1', '0' # Just for error messages
            #for entry in bookObject._processedLines:
                #marker, text, cleanText, extras = entry.getMarker(), entry.getText(), entry.getCleanText(), entry.getExtras()
                #if '¬' in marker or marker in BOS_ADDED_NESTING_MARKERS or marker=='v=':
                    #continue # Just ignore added markers — not needed here

                ## Keep track of where we are for more helpful error messages
                #if marker=='c' and text: C, V = text.split()[0], '0'
                #elif marker=='v' and text: V = text.split()[0]

                #if text and BibleOrgSysGlobals.loadedUSFMMarkers.isPrinted(marker): # process this main text
                    #countWords( marker, cleanText, "main" )

                #if extras:
                    #for extra in extras: # do any footnotes and cross-references
                        #extraType, extraIndex, extraText, cleanExtraText = extra
                        #if BibleOrgSysGlobals.debugFlag:
                            #assert extraText # Shouldn't be blank
                            ##assert extraText[0] != '\\' # Shouldn't start with backslash code
                            #assert extraText[-1] != '\\' # Shouldn't end with backslash code
                            ##print( extraType, extraIndex, len(text), "'"+extraText+"'", "'"+cleanExtraText+"'" )
                            #assert extraIndex >= 0
                            ##assert 0 <= extraIndex <= len(text)+3
                            ##assert extraType in ('fn','xr',)
                            #assert '\\f ' not in extraText and '\\f*' not in extraText and '\\x ' not in extraText and '\\x*' not in extraText # Only the contents of these fields should be in extras
                        #countWords( extraType, cleanExtraText, "notes" )

        # Now sort the lists and write them each twice (sorted by word and sorted by count)
        try: printWordCounts( "All_wordcounts", self.discoveryResults['ALL']['allWordCounts'] )
        except KeyError: pass # Why is there no 'allWordCounts' field ???
        try: printWordCounts( "Main_text_wordcounts", self.discoveryResults['ALL']['mainTextWordCounts'] )
        except KeyError: pass # Why is there no 'mainTextWordCounts' field ???
        try: printWordCounts( "All_wordcounts_case_insensitive", self.discoveryResults['ALL']['allCaseInsensitiveWordCounts'] )
        except KeyError: pass # Why is there no 'allCaseInsensitiveWordCounts' field ???
        try: printWordCounts( "Main_text_wordcounts_case_insensitive", self.discoveryResults['ALL']['mainTextCaseInsensitiveWordCounts'] )
        except KeyError: pass # Why is there no 'mainTextCaseInsensitiveWordCounts' field ???

        if BibleOrgSysGlobals.verbosityLevel > 0 and BibleOrgSysGlobals.maxProcesses > 1:
            print( "  BibleWriter.makeLists finished successfully." )
        return True
    # end of BibleWriter.makeLists


    def toBOSBCV( self, outputFolderpath:Optional[Path]=None ):
        """
        Write the internal pseudoUSFM out directly with one file per verse.
        """
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Running BibleWriter:toBOSBCV…" )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert self.books

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolderpath: outputFolderpath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_BCV_Export/' )
        if os.access( outputFolderpath, os.F_OK ): # We need to delete it
            shutil.rmtree( outputFolderpath, ignore_errors=True )
        os.makedirs( outputFolderpath ) # Make the empty folder

        self.writeBOSBCVFiles( outputFolderpath ) # This function is part of InternalBible

        # Now create a zipped collection (for easier download)
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Zipping BCV files…" )
        zf = zipfile.ZipFile( os.path.join( outputFolderpath, 'AllFiles.zip' ), 'w', compression=zipfile.ZIP_DEFLATED )
        for filename in os.listdir( outputFolderpath ):
            if not filename.endswith( '.zip' ):
                filepath = os.path.join( outputFolderpath, filename )
                zf.write( filepath, filename ) # Save in the archive without the path
        zf.close()

        if BibleOrgSysGlobals.verbosityLevel > 0 and BibleOrgSysGlobals.maxProcesses > 1:
            print( "  BibleWriter.toBOSBCV finished successfully." )
        return True
    # end of BibleWriter.toBOSBCV



    def toPseudoUSFM( self, outputFolderpath:Optional[Path]=None ):
        """
        Write the pseudo USFM out directly (for debugging, etc.).
            May write the rawLines 2-tuples to .rSFM files (if _rawLines still exists)
            Always writes the processed 5-tuples to .pSFM files (from _processedLines).
        """
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Running BibleWriter:toPseudoUSFM…" )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert self.books

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolderpath: outputFolderpath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_PseudoUSFM_Export/' )
        if not os.access( outputFolderpath, os.F_OK ): os.makedirs( outputFolderpath ) # Make the empty folder if there wasn't already one there

        NUM_INDENT_SPACES = 3
        INDENT_SPACES = ' ' * NUM_INDENT_SPACES

        # Write the raw and pseudo-USFM files
        for j, (BBB,bookObject) in enumerate( self.books.items() ):
            try: rawUSFMData = bookObject._rawLines
            except AttributeError: rawUSFMData = None # it's been deleted  :-(
            if rawUSFMData:
                #print( "\ninternalBibleBookData", internalBibleBookData[:50] ); halt
                #USFMAbbreviation = BibleOrgSysGlobals.loadedBibleBooksCodes.getUSFMAbbreviation( BBB )
                #USFMNumber = BibleOrgSysGlobals.loadedBibleBooksCodes.getUSFMNumber( BBB )

                filename = "{:02}_{}_BibleWriter.rSFM".format( j, BBB )
                filepath = os.path.join( outputFolderpath, BibleOrgSysGlobals.makeSafeFilename( filename ) )
                if BibleOrgSysGlobals.verbosityLevel > 2: print( '  toPseudoUSFM: ' + _("Writing {!r}…").format( filepath ) )
                with open( filepath, 'wt', encoding='utf-8' ) as myFile:
                    for marker,text in rawUSFMData:
                        myFile.write( "{}: {!r}\n".format( marker, text ) )

            internalBibleBookData = bookObject._processedLines
            #print( "\ninternalBibleBookData", internalBibleBookData[:50] ); halt
            USFMAbbreviation = BibleOrgSysGlobals.loadedBibleBooksCodes.getUSFMAbbreviation( BBB )
            USFMNumber = BibleOrgSysGlobals.loadedBibleBooksCodes.getUSFMNumber( BBB )

            filename = "{:02}_{}_BibleWriter.pSFM".format( j, BBB )
            filepath = os.path.join( outputFolderpath, BibleOrgSysGlobals.makeSafeFilename( filename ) )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( '  toPseudoUSFM: ' + _("Writing {!r}…").format( filepath ) )
            indentLevel = 0
            C, V = '-1', '-1' # So first/id line starts at -1:0
            with open( filepath, 'wt', encoding='utf-8' ) as myFile:
                for entry in internalBibleBookData:
                    marker, adjText, cleanText, extras = entry.getMarker(), entry.getAdjustedText(), entry.getCleanText(), entry.getExtras()
                    #print( repr(marker), repr(cleanText), repr(adjText) )
                    if marker in USFM_PRECHAPTER_MARKERS:
                        if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
                            assert C=='-1' or marker=='rem' or marker.startswith('mte')
                        V = str( int(V) + 1 )
                    if marker == 'c': C, V = adjText, '0'
                    elif marker == 'v': V = adjText

                    myFile.write( "{}{}{} = {} {} {}\n" \
                            .format( INDENT_SPACES*indentLevel,
                                ' ' if len(marker)<2 and marker not in ('h',) else '',
                                marker,
                                repr(adjText) if adjText is not None else '',
                                repr(cleanText) if cleanText and cleanText!=adjText else '',
                                entry.getExtras().fullSummary() if extras else '' ) )

                    if marker in BOS_NESTING_MARKERS:
                        indentLevel += 1
                    elif indentLevel and marker[0]=='¬': indentLevel -= 1
                    if indentLevel > 7: print( "BibleWriter.toPseudoUSFM: {} {}:{} indentLevel={} marker={}".format( BBB, C, V,
                                                                                                                    Level, marker ) )
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert indentLevel <= 7 # Should only be 7: e.g., chapters c s1 p v list li1
            if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert indentLevel == 0

        # Now create a zipped collection
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Zipping PseudoUSFM files…" )
        zf = zipfile.ZipFile( os.path.join( outputFolderpath, 'AllFiles.zip' ), 'w', compression=zipfile.ZIP_DEFLATED )
        for filename in os.listdir( outputFolderpath ):
            if not filename.endswith( '.zip' ):
                filepath = os.path.join( outputFolderpath, filename )
                zf.write( filepath, filename ) # Save in the archive without the path
        zf.close()

        if BibleOrgSysGlobals.verbosityLevel > 0 and BibleOrgSysGlobals.maxProcesses > 1:
            print( "  BibleWriter.toPseudoUSFM finished successfully." )
        return True
    # end of BibleWriter.toPseudoUSFM



    def toUSFM2( self, outputFolderpath:Optional[Path]=None, removeVerseBridges=False ):
        """
        Adjust the pseudo USFM and write the USFM2 files.

        NOTE: We use utf-8 encoding and Windows \r\n line endings for writing USFM files.
        """
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Running BibleWriter:toUSFM2…" )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert self.books
        includeEmptyVersesFlag = True

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolderpath:
            outputFolderpath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_USFM2_' + ('Reexport/' if self.objectTypeString in ('USFM2','PTX7')
                                                else 'Export/') )
        if not os.access( outputFolderpath, os.F_OK ): os.makedirs( outputFolderpath ) # Make the empty folder if there wasn't already one there
        #if not controlDict: controlDict = {}; ControlFiles.readControlFile( 'ControlFiles', "To_XXX_controls.txt", controlDict )
        #assert controlDict and isinstance( controlDict, dict )

        ignoredMarkers = set()

        # Adjust the extracted outputs
        for BBB,bookObject in self.books.items():
            internalBibleBookData = bookObject._processedLines
            #print( "\ninternalBibleBookData", internalBibleBookData[:50] ); halt
            USFMAbbreviation = BibleOrgSysGlobals.loadedBibleBooksCodes.getUSFMAbbreviation( BBB )
            USFMNumber = BibleOrgSysGlobals.loadedBibleBooksCodes.getUSFMNumber( BBB )

            if includeEmptyVersesFlag:
                try:
                    verseList = self.genericBOS.getNumVersesList( BBB )
                    numC, numV = len(verseList), verseList[0]
                except KeyError:
                    #print( "toUSFM2: {} {} has no verse data for {}".format( self.getAName(), self.genericBOS.getOrganisationalSystemName(), BBB ) )
                    if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
                        assert BBB in ('FRT','BAK','GLS','XXA','XXB','XXC','XXD','XXE','XXF')
                    numC = numV = 0

            bookUSFM = ''
            # Prepend any important missing (header/title) fields
            if internalBibleBookData.contains( 'id', 1 ) is None:
                bookUSFM += '\\id {} — BibleOrgSys USFM2 export v{}'.format( USFMAbbreviation.upper(), PROGRAM_VERSION )
                if internalBibleBookData.contains( 'h', 8 ) is None:
                    try:
                        h = self.suppliedMetadata['File'][BBB+'ShortName']
                        if h: bookUSFM += '\n\\h {}'.format( h )
                    except (KeyError,TypeError): pass # ok, we've got nothing to add
                if internalBibleBookData.contains( 'mt1', 12 ) is None:
                    try:
                        mt = self.suppliedMetadata['File'][BBB+'LongName']
                        if mt: bookUSFM += '\n\\mt1 {}'.format( mt )
                    except (KeyError,TypeError): pass # ok, we've got nothing to add
            inField = None
            vBridgeStartInt = vBridgeEndInt = None # For printing missing (bridged) verse numbers
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "  " + _("Adjusting USFM2 output…" ) )
            for processedBibleEntry in internalBibleBookData:
                pseudoMarker, fullText = processedBibleEntry.getMarker(), processedBibleEntry.getFullText()
                #print( BBB, pseudoMarker, repr(fullText) )
                #if (not bookUSFM) and pseudoMarker!='id': # We need to create an initial id line
                    #bookUSFM += '\\id {} — BibleOrgSys USFM2 export v{}'.format( USFMAbbreviation.upper(), PROGRAM_VERSION )
                if '¬' in pseudoMarker or pseudoMarker in BOS_ADDED_NESTING_MARKERS or pseudoMarker=='v=':
                    continue # Just ignore added markers — not needed here
                if pseudoMarker in ('c#','vp#',):
                    ignoredMarkers.add( pseudoMarker )
                    continue
                #fullText = cleanText # (temp)
                #if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( "toUSFM: pseudoMarker = {!r} fullText = {!r}".format( pseudoMarker, fullText ) )
                if removeVerseBridges and pseudoMarker in ('v','c',):
                    if vBridgeStartInt and vBridgeEndInt:
                        for vNum in range( vBridgeStartInt+1, vBridgeEndInt+1 ): # Fill in missing verse numbers
                            bookUSFM += '\n\\v {}'.format( vNum )
                    vBridgeStartInt = vBridgeEndInt = None

                if pseudoMarker in ('v','f','fr','x','xo',): # These fields should always end with a space but the processing will have removed them
                    #if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert fullText
                    if pseudoMarker=='v' and removeVerseBridges:
                        vString = fullText
                        for bridgeChar in ('-', '–', '—'): # hyphen, endash, emdash
                            ix = vString.find( bridgeChar )
                            if ix != -1:
                                fullText = vString[:ix] # Remove verse bridges
                                vEnd = vString[ix+1:]
                                #print( BBB, repr(fullText), repr(vEnd) )
                                try: vBridgeStartInt, vBridgeEndInt = int( fullText ), int( vEnd )
                                except ValueError:
                                    print( "toUSFM2: bridge doesn't seem to be integers in {} {!r}".format( BBB, vString ) )
                                    vBridgeStartInt = vBridgeEndInt = None # One of them isn't an integer
                                #print( ' ', BBB, repr(vBridgeStartInt), repr(vBridgeEndInt) )
                                break
                    if fullText and fullText[-1]!=' ': fullText += ' ' # Append a space since it didn't have one
                elif pseudoMarker[-1]=='~' or BibleOrgSysGlobals.loadedUSFMMarkers.isNewlineMarker(pseudoMarker): # Have a continuation field
                    if inField is not None:
                        bookUSFM += '\\{}*'.format( inField ) # Do a close marker for footnotes and cross-references
                        inField = None

                if pseudoMarker[-1] == '~':
                    #print( "psMarker ends with squiggle: {!r}={!r}".format( pseudoMarker, fullText ) )
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert pseudoMarker[:-1] in ('v','p','c')
                    bookUSFM += (' ' if bookUSFM and bookUSFM[-1]!=' ' else '') + fullText
                else: # not a continuation marker
                    adjValue = fullText
                    #if pseudoMarker in ('it','bk','ca','nd',): # Character markers to be closed — had to remove ft and xt from this list for complex footnotes with f fr fq ft fq ft f*
                    if pseudoMarker in ALL_CHAR_MARKERS: # Character markers to be closed
                        #if (bookUSFM[-2]=='\\' or bookUSFM[-3]=='\\') and bookUSFM[-1]!=' ':
                        if bookUSFM[-1] != ' ':
                            bookUSFM += ' ' # Separate markers by a space e.g., \p\bk Revelation
                            if BibleOrgSysGlobals.debugFlag: print( "toUSFM2: Added space to {!r} before {!r}".format( bookUSFM[-2], pseudoMarker ) )
                        adjValue += '\\{}*'.format( pseudoMarker ) # Do a close marker
                    elif pseudoMarker in ('f','x',): inField = pseudoMarker # Remember these so we can close them later
                    elif pseudoMarker in ('fr','fq','ft','xo',): bookUSFM += ' ' # These go on the same line just separated by spaces and don't get closed
                    elif bookUSFM: bookUSFM += '\n' # paragraph markers go on a new line
                    if not fullText: bookUSFM += '\\{}'.format( pseudoMarker )
                    else: bookUSFM += '\\{} {}'.format( pseudoMarker,adjValue )
                #print( pseudoMarker, bookUSFM[-200:] )

            # Adjust the bookUSFM output
            bookUSFM = noisyRegExDeleteAll( bookUSFM, '\\\\str .+?\\\str\\*' )
            if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
                assert '\\str' not in bookUSFM
                assert '&quot;' not in bookUSFM
                assert '&amp;' not in bookUSFM
                assert '&lt;' not in bookUSFM and '&gt;' not in bookUSFM

            # Write the bookUSFM output
            #print( "\nUSFM", bookUSFM[:3000] )
            filename = "{}{}BibleWriter.usfm".format( USFMNumber, USFMAbbreviation.upper() ) # This seems to be the undocumented standard filename format even though it's so ugly with digits running into each other, e.g., 102SA…
            #if not os.path.exists( USFMOutputFolder ): os.makedirs( USFMOutputFolder )
            filepath = os.path.join( outputFolderpath, BibleOrgSysGlobals.makeSafeFilename( filename ) )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( '  toUSFM2: ' + _("Writing {!r}…").format( filepath ) )
            with open( filepath, 'wt', newline='\r\n', encoding='utf-8' ) as myFile: # Use Windows newline endings for bookUSFM
                myFile.write( bookUSFM )

        if ignoredMarkers:
            logger.info( "toUSFM: Ignored markers were {}".format( ignoredMarkers ) )
            if BibleOrgSysGlobals.verbosityLevel > 2:
                print( "  " + _("WARNING: Ignored toUSFM2 markers were {}").format( ignoredMarkers ) )

        # Now create a zipped collection
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Zipping USFM2 files…" )
        zf = zipfile.ZipFile( os.path.join( outputFolderpath, 'AllUSFM2Files.zip' ), 'w', compression=zipfile.ZIP_DEFLATED )
        for filename in os.listdir( outputFolderpath ):
            if not filename.endswith( '.zip' ):
                filepath = os.path.join( outputFolderpath, filename )
                zf.write( filepath, filename ) # Save in the archive without the path
        zf.close()
        # Now create the gzipped file
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  GZipping USFM2 files…" )
        tar = tarfile.open( os.path.join( outputFolderpath, 'AllUSFM2Files.gzip' ), 'w:gz' )
        for filename in os.listdir( outputFolderpath ):
            if filename.endswith( '.usfm' ):
                filepath = os.path.join( outputFolderpath, filename )
                tar.add( filepath, arcname=filename, recursive=False )
        tar.close()
        # Now create the bz2 file
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  BZipping USFM2 files…" )
        tar = tarfile.open( os.path.join( outputFolderpath, 'AllUSFM2Files.bz2' ), 'w:bz2' )
        for filename in os.listdir( outputFolderpath ):
            if filename.endswith( '.usfm' ):
                filepath = os.path.join( outputFolderpath, filename )
                tar.add( filepath, arcname=filename, recursive=False )
        tar.close()

        if BibleOrgSysGlobals.verbosityLevel > 0 and BibleOrgSysGlobals.maxProcesses > 1:
            print( "  BibleWriter.toUSFM2 finished successfully." )
        return True
    # end of BibleWriter.toUSFM2



    def toUSFM3( self, outputFolderpath:Optional[Path]=None, removeVerseBridges=False ):
        """
        Adjust the pseudo USFM and write the USFM3 files.

        NOTE: We use utf-8 encoding and Windows \r\n line endings for writing USFM files.
        """
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Running BibleWriter:toUSFM3…" )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert self.books
        includeEmptyVersesFlag = True

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolderpath: outputFolderpath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_USFM3_' + ('Reexport/' if self.objectTypeString=='USFM3' else 'Export/') )
        if not os.access( outputFolderpath, os.F_OK ): os.makedirs( outputFolderpath ) # Make the empty folder if there wasn't already one there
        #if not controlDict: controlDict = {}; ControlFiles.readControlFile( 'ControlFiles', "To_XXX_controls.txt", controlDict )
        #assert controlDict and isinstance( controlDict, dict )

        ignoredMarkers = set()
        addedUSFMfield = False

        # Adjust the extracted outputs
        for BBB,bookObject in self.books.items():
            internalBibleBookData = bookObject._processedLines
            #print( "\ninternalBibleBookData", internalBibleBookData[:50] ); halt
            USFMAbbreviation = BibleOrgSysGlobals.loadedBibleBooksCodes.getUSFMAbbreviation( BBB )
            USFMNumber = BibleOrgSysGlobals.loadedBibleBooksCodes.getUSFMNumber( BBB )

            if includeEmptyVersesFlag:
                try:
                    verseList = self.genericBOS.getNumVersesList( BBB )
                    numC, numV = len(verseList), verseList[0]
                except KeyError:
                    if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
                        assert BBB in ('FRT','BAK','GLS','XXA','XXB','XXC','XXD','XXE','XXF')
                    numC = numV = 0

            bookUSFM = ''
            # Prepend any important missing (header/title) fields
            if internalBibleBookData.contains( 'id', 1 ) is None:
                bookUSFM += '\\id {} — BibleOrgSys USFM3 export v{}'.format( USFMAbbreviation.upper(), PROGRAM_VERSION )
                bookUSFM += '\n\\usfm 3.0'
                addedUSFMfield = True
                if internalBibleBookData.contains( 'h', 8 ) is None:
                    try:
                        h = self.suppliedMetadata['File'][BBB+'ShortName']
                        if h: bookUSFM += '\n\\h {}'.format( h )
                    except (KeyError,TypeError): pass # ok, we've got nothing to add
                if internalBibleBookData.contains( 'mt1', 12 ) is None:
                    try:
                        mt = self.suppliedMetadata['File'][BBB+'LongName']
                        if mt: bookUSFM += '\n\\mt1 {}'.format( mt )
                    except (KeyError,TypeError): pass # ok, we've got nothing to add
            inField = None
            vBridgeStartInt = vBridgeEndInt = None # For printing missing (bridged) verse numbers
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "  " + _("Adjusting USFM3 output…" ) )
            for processedBibleEntry in internalBibleBookData:
                pseudoMarker, fullText = processedBibleEntry.getMarker(), processedBibleEntry.getFullText()
                #print( BBB, pseudoMarker, repr(fullText) )
                #if (not bookUSFM) and pseudoMarker!='id': # We need to create an initial id line
                    #bookUSFM += '\\id {} — BibleOrgSys USFM3 export v{}'.format( USFMAbbreviation.upper(), PROGRAM_VERSION )
                if '¬' in pseudoMarker or pseudoMarker in BOS_ADDED_NESTING_MARKERS or pseudoMarker=='v=':
                    continue # Just ignore added markers — not needed here
                if pseudoMarker in ('c#','vp#',):
                    ignoredMarkers.add( pseudoMarker )
                    continue
                if pseudoMarker not in ('id','usfm') and not addedUSFMfield:
                    bookUSFM += '\n\\usfm 3.0'
                    addedUSFMfield = True

                #fullText = cleanText # (temp)
                #if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( "toUSFM: pseudoMarker = {!r} fullText = {!r}".format( pseudoMarker, fullText ) )
                if removeVerseBridges and pseudoMarker in ('v','c',):
                    if vBridgeStartInt and vBridgeEndInt:
                        for vNum in range( vBridgeStartInt+1, vBridgeEndInt+1 ): # Fill in missing verse numbers
                            bookUSFM += '\n\\v {}'.format( vNum )
                    vBridgeStartInt = vBridgeEndInt = None

                if pseudoMarker in ('v','f','fr','x','xo',): # These fields should always end with a space but the processing will have removed them
                    #if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert fullText
                    if pseudoMarker=='v' and removeVerseBridges:
                        vString = fullText
                        for bridgeChar in ('-', '–', '—'): # hyphen, endash, emdash
                            ix = vString.find( bridgeChar )
                            if ix != -1:
                                fullText = vString[:ix] # Remove verse bridges
                                vEnd = vString[ix+1:]
                                #print( BBB, repr(fullText), repr(vEnd) )
                                try: vBridgeStartInt, vBridgeEndInt = int( fullText ), int( vEnd )
                                except ValueError:
                                    print( "toUSFM3: bridge doesn't seem to be integers in {} {!r}".format( BBB, vString ) )
                                    vBridgeStartInt = vBridgeEndInt = None # One of them isn't an integer
                                #print( ' ', BBB, repr(vBridgeStartInt), repr(vBridgeEndInt) )
                                break
                    if fullText and fullText[-1]!=' ': fullText += ' ' # Append a space since it didn't have one
                elif pseudoMarker[-1]=='~' or BibleOrgSysGlobals.loadedUSFMMarkers.isNewlineMarker(pseudoMarker): # Have a continuation field
                    if inField is not None:
                        bookUSFM += '\\{}*'.format( inField ) # Do a close marker for footnotes and cross-references
                        inField = None

                if pseudoMarker[-1] == '~':
                    #print( "psMarker ends with squiggle: {!r}={!r}".format( pseudoMarker, fullText ) )
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert pseudoMarker[:-1] in ('v','p','c')
                    bookUSFM += (' ' if bookUSFM and bookUSFM[-1]!=' ' else '') + fullText
                else: # not a continuation marker
                    adjValue = fullText
                    #if pseudoMarker in ('it','bk','ca','nd',): # Character markers to be closed — had to remove ft and xt from this list for complex footnotes with f fr fq ft fq ft f*
                    if pseudoMarker in ALL_CHAR_MARKERS: # Character markers to be closed
                        #if (bookUSFM[-2]=='\\' or bookUSFM[-3]=='\\') and bookUSFM[-1]!=' ':
                        if bookUSFM[-1] != ' ':
                            bookUSFM += ' ' # Separate markers by a space e.g., \p\bk Revelation
                            if BibleOrgSysGlobals.debugFlag: print( "toUSFM3: Added space to {!r} before {!r}".format( bookUSFM[-2], pseudoMarker ) )
                        adjValue += '\\{}*'.format( pseudoMarker ) # Do a close marker
                    elif pseudoMarker in ('f','x',): inField = pseudoMarker # Remember these so we can close them later
                    elif pseudoMarker in ('fr','fq','ft','xo',): bookUSFM += ' ' # These go on the same line just separated by spaces and don't get closed
                    elif bookUSFM: bookUSFM += '\n' # paragraph markers go on a new line
                    if not fullText: bookUSFM += '\\{}'.format( pseudoMarker )
                    else: bookUSFM += '\\{} {}'.format( pseudoMarker,adjValue )
                #print( pseudoMarker, bookUSFM[-200:] )

            # Adjust the bookUSFM output
            bookUSFM = noisyRegExDeleteAll( bookUSFM, '\\\\str .+?\\\str\\*' )
            if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
                assert '\\str' not in bookUSFM
                assert '&quot;' not in bookUSFM
                assert '&amp;' not in bookUSFM
                assert '&lt;' not in bookUSFM and '&gt;' not in bookUSFM

            # Write the bookUSFM output
            #print( "\nUSFM", bookUSFM[:3000] )
            filename = "{}{}BibleWriter.usfm".format( USFMNumber, USFMAbbreviation.upper() ) # This seems to be the undocumented standard filename format even though it's so ugly with digits running into each other, e.g., 102SA…
            #if not os.path.exists( USFMOutputFolder ): os.makedirs( USFMOutputFolder )
            filepath = os.path.join( outputFolderpath, BibleOrgSysGlobals.makeSafeFilename( filename ) )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( '  toUSFM3: ' + _("Writing {!r}…").format( filepath ) )
            with open( filepath, 'wt', newline='\r\n', encoding='utf-8' ) as myFile: # Use Windows newline endings for bookUSFM
                myFile.write( bookUSFM )

        if ignoredMarkers:
            logger.info( "toUSFM: Ignored markers were {}".format( ignoredMarkers ) )
            if BibleOrgSysGlobals.verbosityLevel > 2:
                print( "  " + _("WARNING: Ignored toUSFM3 markers were {}").format( ignoredMarkers ) )

        # Now create a zipped collection
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Zipping USFM3 files…" )
        zf = zipfile.ZipFile( os.path.join( outputFolderpath, 'AllUSFM3Files.zip' ), 'w', compression=zipfile.ZIP_DEFLATED )
        for filename in os.listdir( outputFolderpath ):
            if filename.endswith( '.usfm' ):
                filepath = os.path.join( outputFolderpath, filename )
                zf.write( filepath, filename ) # Save in the archive without the path
        zf.close()
        # Now create the gzipped file
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  GZipping USFM3 files…" )
        tar = tarfile.open( os.path.join( outputFolderpath, 'AllUSFM3Files.gzip' ), 'w:gz' )
        for filename in os.listdir( outputFolderpath ):
            if filename.endswith( '.usfm' ):
                filepath = os.path.join( outputFolderpath, filename )
                tar.add( filepath, arcname=filename, recursive=False )
        tar.close()
        # Now create the bz2 file
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  BZipping USFM3 files…" )
        tar = tarfile.open( os.path.join( outputFolderpath, 'AllUSFM3Files.bz2' ), 'w:bz2' )
        for filename in os.listdir( outputFolderpath ):
            if filename.endswith( '.usfm' ):
                filepath = os.path.join( outputFolderpath, filename )
                tar.add( filepath, arcname=filename, recursive=False )
        tar.close()

        if BibleOrgSysGlobals.verbosityLevel > 0 and BibleOrgSysGlobals.maxProcesses > 1:
            print( "  BibleWriter.toUSFM3 finished successfully." )
        return True
    # end of BibleWriter.toUSFM3



    def toESFM( self, outputFolderpath:Optional[Path]=None ): #, removeVerseBridges=False ):
        """
        Adjust the pseudo ESFM and write the ESFM files.
        """
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Running BibleWriter:toESFM…" )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert self.books

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolderpath: outputFolderpath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_ESFM_' + ('Reexport/' if self.objectTypeString=="ESFM" else 'Export/') )
        if not os.access( outputFolderpath, os.F_OK ): os.makedirs( outputFolderpath ) # Make the empty folder if there wasn't already one there
        #if not controlDict: controlDict = {}; ControlFiles.readControlFile( 'ControlFiles', "To_XXX_controls.txt", controlDict )
        #assert controlDict and isinstance( controlDict, dict )

        ignoredMarkers = set()

        # Adjust the extracted outputs
        for BBB,bookObject in self.books.items():
            internalBibleBookData = bookObject._processedLines
            #print( "\ninternalBibleBookData", internalBibleBookData[:50] ); halt
            USFMAbbreviation = BibleOrgSysGlobals.loadedBibleBooksCodes.getUSFMAbbreviation( BBB )
            USFMNumber = BibleOrgSysGlobals.loadedBibleBooksCodes.getUSFMNumber( BBB )

            filename = "{}{}BibleWriter.ESFM".format( USFMNumber, USFMAbbreviation.upper() )
            #if not os.path.exists( ESFMOutputFolder ): os.makedirs( ESFMOutputFolder )
            filepath = os.path.join( outputFolderpath, BibleOrgSysGlobals.makeSafeFilename( filename ) )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( '  toESFM: ' + _("Writing {!r}…").format( filepath ) )
            indentLevel, indentSize =  0, 2
            inField = None
            vBridgeStartInt = vBridgeEndInt = None # For printing missing (bridged) verse numbers
            initialMarkers = [processedBibleEntry.getMarker() for processedBibleEntry in internalBibleBookData[:4]]
            #print( BBB, initialMarkers )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "  " + _("Adjusting ESFM output…" ) )
            with open( filepath, 'wt', encoding='utf-8' ) as myFile:
                if 'id' not in initialMarkers:
                    #print( "Write ID" )
                    myFile.write( '\\id {} — BibleOrgSys ESFM export v{}\n'.format( USFMAbbreviation.upper(), PROGRAM_VERSION ) )
                if 'ide' not in initialMarkers:
                    #print( "Write IDE" )
                    myFile.write( '\\ide UTF-8\n' )
                    if 'rem' not in initialMarkers:
                        #print( "Write REM" )
                        myFile.write( '\\rem ESFM v0.5 {}\n'.format( BBB ) )
                for j, processedBibleEntry in enumerate( internalBibleBookData ):
                    pseudoMarker, value = processedBibleEntry.getMarker(), processedBibleEntry.getFullText()
                    if debuggingThisModule: print( "writeESFM", indentLevel, "now", BBB, j, pseudoMarker, repr(value) )
                    if j==1 and pseudoMarker=='ide':
                        #print( "Write IDE 1" )
                        myFile.write( '\\ide UTF-8\n' )
                        if 'rem' not in initialMarkers:
                            #print( "Write REM 2" )
                            myFile.write( '\\rem ESFM v0.5 {}\n'.format( BBB ) )
                        ESFMLine = ''
                    elif j==2 and pseudoMarker=='rem':
                        #print( "Write REM 3" )
                        if value != 'ESFM v0.5 {}'.format( BBB ):
                            logger.info( "Updating {} ESFM rem line from {!r} to v0.5".format( BBB, value ) )
                        ESFMLine = '\\rem ESFM v0.5 {}'.format( BBB )
                    else:
                        if '¬' in pseudoMarker:
                            if indentLevel > 0:
                                indentLevel -= 1
                            else:
                                logger.error( "toESFM: Indent level can't go negative at {} {} {} {!r}".format( BBB, j, pseudoMarker, value ) )
                                if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                                    print( "toESFM: Indent level can't go negative at {} {} {} {!r}".format( BBB, j, pseudoMarker, value ) )
                                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag: halt
                        ESFMLine = ' ' * indentLevel * indentSize

                        if pseudoMarker in ('c#','vp#',):
                            ignoredMarkers.add( pseudoMarker )
                            continue

                        #value = cleanText # (temp)
                        #if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( "toESFM: pseudoMarker = {!r} value = {!r}".format( pseudoMarker, value ) )
                        if 0 and removeVerseBridges and pseudoMarker in ('v','c',):
                            if vBridgeStartInt and vBridgeEndInt:
                                for vNum in range( vBridgeStartInt+1, vBridgeEndInt+1 ): # Fill in missing verse numbers
                                    ESFMLine += '\n\\v {}'.format( vNum )
                            vBridgeStartInt = vBridgeEndInt = None

                        if pseudoMarker == 'vp#': continue
                        elif pseudoMarker in ('v','f','fr','x','xo',): # These fields should always end with a space but the processing will have removed them
                            #if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert value
                            if pseudoMarker=='v' and 0 and removeVerseBridges:
                                vString = value
                                for bridgeChar in ('-', '–', '—'): # hyphen, endash, emdash
                                    ix = vString.find( bridgeChar )
                                    if ix != -1:
                                        value = vString[:ix] # Remove verse bridges
                                        vEnd = vString[ix+1:]
                                        #print( BBB, repr(value), repr(vEnd) )
                                        try: vBridgeStartInt, vBridgeEndInt = int( value ), int( vEnd )
                                        except ValueError:
                                            logger.warning( "toESFM: bridge doesn't seem to be integers in {} {!r}".format( BBB, vString ) )
                                            vBridgeStartInt = vBridgeEndInt = None # One of them isn't an integer
                                        #print( ' ', BBB, repr(vBridgeStartInt), repr(vBridgeEndInt) )
                                        break
                            if value and value[-1] != ' ': value += ' ' # Append a space since it didn't have one
                        elif pseudoMarker[-1]=='~' or BibleOrgSysGlobals.loadedUSFMMarkers.isNewlineMarker(pseudoMarker): # Have a continuation field
                            if inField is not None:
                                ESFMLine += '\\{}*'.format( inField ) # Do a close marker for footnotes and cross-references
                                inField = None

                        if pseudoMarker[-1] == '~':
                            #print( "psMarker ends with squiggle: {!r}={!r}".format( pseudoMarker, value ) )
                            if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert pseudoMarker[:-1] in ('v','p','c')
                            ESFMLine += (' ' if ESFMLine and ESFMLine[-1]!=' ' else '') + value
                        else: # not a continuation marker
                            adjValue = value
                            #if pseudoMarker in ('it','bk','ca','nd',): # Character markers to be closed — had to remove ft and xt from this list for complex footnotes with f fr fq ft fq ft f*
                            if pseudoMarker in ALL_CHAR_MARKERS: # Character markers to be closed
                                #if (ESFMLine[-2]=='\\' or ESFMLine[-3]=='\\') and ESFMLine[-1]!=' ':
                                if ESFMLine[-1] != ' ':
                                    ESFMLine += ' ' # Separate markers by a space e.g., \p\bk Revelation
                                    if BibleOrgSysGlobals.debugFlag: print( "toESFM: Added space to {!r} before {!r}".format( ESFMLine[-2], pseudoMarker ) )
                                adjValue += '\\{}*'.format( pseudoMarker ) # Do a close marker
                            elif pseudoMarker in ('f','x',): inField = pseudoMarker # Remember these so we can close them later
                            elif pseudoMarker in ('fr','fq','ft','xo',): ESFMLine += ' ' # These go on the same line just separated by spaces and don't get closed
                            #elif ESFMLine: ESFMLine += '\n' # paragraph markers go on a new line
                            if not value: ESFMLine += '\\{}'.format( pseudoMarker )
                            else: ESFMLine += '\\{} {}'.format( pseudoMarker,adjValue )

                    #print( BBB, pseudoMarker, repr(ESFMLine) )
                    #if BBB=='GEN' and j > 20: halt
                    if ESFMLine: myFile.write( '{}\n'.format( ESFMLine ) )
                    if pseudoMarker in BOS_NESTING_MARKERS:
                        indentLevel += 1
                        #print( pseudoMarker, indentLevel )
            if indentLevel !=  0:
                logger.error( "toESFM: Ended with wrong indent level of {} for {}".format( indentLevel, BBB ) );  halt

        if ignoredMarkers:
            logger.info( "toESFM: Ignored markers were {}".format( ignoredMarkers ) )
            if BibleOrgSysGlobals.verbosityLevel > 2:
                print( "  " + _("WARNING: Ignored toESFM markers were {}").format( ignoredMarkers ) )

        # Now create a zipped collection
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Zipping ESFM files…" )
        zf = zipfile.ZipFile( os.path.join( outputFolderpath, 'AllESFMFiles.zip' ), 'w', compression=zipfile.ZIP_DEFLATED )
        for filename in os.listdir( outputFolderpath ):
            if not filename.endswith( '.zip' ):
                filepath = os.path.join( outputFolderpath, filename )
                zf.write( filepath, filename ) # Save in the archive without the path
        zf.close()

        if BibleOrgSysGlobals.verbosityLevel > 0 and BibleOrgSysGlobals.maxProcesses > 1:
            print( "  BibleWriter.toESFM finished successfully." )
        return True
    # end of BibleWriter.toESFM



    def toText( self, outputFolderpath:Optional[Path]=None ):
        """
        Write the pseudo USFM out into a simple plain-text format.
            The format varies, depending on whether or not there are paragraph markers in the text.
            Introductions and several other fields are ignored.
        """
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Running BibleWriter:toText…" )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert self.books

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolderpath: outputFolderpath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_PlainText_Export/' )
        if not os.access( outputFolderpath, os.F_OK ): os.makedirs( outputFolderpath ) # Make the empty folder if there wasn't already one there
        outputFolder2 = os.path.join( outputFolderpath, 'Without_ByteOrderMarker' )
        if not os.access( outputFolder2, os.F_OK ): os.makedirs( outputFolder2 ) # Make the empty folder if there wasn't already one there

        ignoredMarkers = set()

        # First determine our format
        columnWidth = 80
        #verseByVerse = True


        def writeTextFile( BBB, internalBibleBookData, columnWidth, wtfOutputFolder, withBOMFlag ):
            """
            Helper function to write the actual text file
            """
            filename = "BOS-BibleWriter-{}.txt".format( BBB )
            filepath = os.path.join( wtfOutputFolder, BibleOrgSysGlobals.makeSafeFilename( filename ) )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( '  toText: ' + _("Writing {!r}…").format( filepath ) )
            textBuffer = ''
            with open( filepath, 'wt', encoding='utf-8' ) as myFile:
                if withBOMFlag:
                    try: myFile.write('\ufeff')
                    except UnicodeEncodeError: # why does this fail on Windows???
                        logger.critical( "toText.writeTextFile: Unable to write BOM to file" )
                gotVP = None
                for entry in internalBibleBookData:
                    marker, text = entry.getMarker(), entry.getCleanText() # Clean text has no notes or character formatting
                    if marker.startswith('¬') or marker in ('c#','v='):
                        continue # silent ignore some of our added markers
                    if marker in OFTEN_IGNORED_USFM_HEADER_MARKERS or marker in ('r','d','sp','cp','ie'):
                        ignoredMarkers.add( marker ) # Just ignore these lines
                    elif marker == 'h':
                        if textBuffer: myFile.write( "{}".format( textBuffer ) ); textBuffer = ''
                        myFile.write( "{}\n\n".format( text ) )
                    elif marker in USFM_ALL_INTRODUCTION_MARKERS: # Drop the introduction
                        ignoredMarkers.add( marker )
                    elif marker in ('mt1','mt2','mt3','mt4', 'imt1','imt2','imt3','imt4',):
                        if textBuffer: myFile.write( "{}".format( textBuffer ) ); textBuffer = ''
                        myFile.write( "\n{}{}\n".format( ' '*((columnWidth-len(text))//2), text ) )
                    elif marker in ('mte1','mte2','mte3','mte4', 'imte1','imte2','imte3','imte4',):
                        if textBuffer: myFile.write( "{}".format( textBuffer ) ); textBuffer = ''
                        myFile.write( "\n{}{}\n\n".format( ' '*((columnWidth-len(text))//2), text ) )
                    elif marker == 'c':
                        C = text
                        if textBuffer: myFile.write( "{}".format( textBuffer ) ); textBuffer = ''
                        myFile.write( "\n\nChapter {}".format( text ) )
                    elif marker == 'vp#': # This precedes a v field and has the verse number to be printed
                        gotVP = text # Just remember it for now
                    elif marker == 'v':
                        V = text
                        if gotVP: # this is the verse number to be published
                            text = gotVP
                            gotVP = None
                        if textBuffer: myFile.write( "{}".format( textBuffer ) ); textBuffer = ''
                        myFile.write( "\n{} ".format( text ) )
                    elif marker in ('p','pi1','pi2','pi3','pi4', 's1','s2','s3','s4', 'ms1','ms2','ms3','ms4',): # Drop out these fields
                        ignoredMarkers.add( marker )
                    elif text:
                        #if marker not in ('p~','v~'): # The most common ones
                            #print( "toText.writeTextFile: Using marker {!r}:{!r}".format( marker, text ) )
                        textBuffer += (' ' if textBuffer else '') + text
                if textBuffer: myFile.write( "{}\n".format( textBuffer ) ) # Write the last bit

                    #if verseByVerse:
                        #myFile.write( "{} ({}): {!r} {!r} {}\n" \
                            #.format( entry.getMarker(), entry.getOriginalMarker(), entry.getAdjustedText(), entry.getCleanText(), entry.getExtras() ) )

            # Now create a zipped collection
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Zipping text files…" )
            zf = zipfile.ZipFile( os.path.join( wtfOutputFolder, 'AllTextFiles.zip' ), 'w', compression=zipfile.ZIP_DEFLATED )
            for filename in os.listdir( wtfOutputFolder ):
                if not filename.endswith( '.zip' ):
                    filepath = os.path.join( wtfOutputFolder, filename )
                    zf.write( filepath, filename ) # Save in the archive without the path
            zf.close()

        # Main code for toText()
        # Write the plain text files
        for BBB,bookObject in self.books.items():
            # NOTE: We currently write ALL books, even though some books (e.g., FRT,GLS,XXA,… may end up blank)
            writeTextFile( BBB, bookObject._processedLines, columnWidth, outputFolderpath, withBOMFlag=True )
            writeTextFile( BBB, bookObject._processedLines, columnWidth, outputFolder2, withBOMFlag=False )

        if ignoredMarkers:
            logger.info( "toText: Ignored markers were {}".format( ignoredMarkers ) )
            if BibleOrgSysGlobals.verbosityLevel > 2:
                print( "  " + _("WARNING: Ignored toText markers were {}").format( ignoredMarkers ) )

        if BibleOrgSysGlobals.verbosityLevel > 0 and BibleOrgSysGlobals.maxProcesses > 1:
            print( "  BibleWriter.toText finished successfully." )
        return True
    # end of BibleWriter.toText



    def toVPL( self, outputFolderpath:Optional[Path]=None ):
        """
        Write the pseudo USFM out into some simple verse-per-line formats.
        """
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Running BibleWriter:toVPL…" )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert self.books

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolderpath: outputFolderpath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_VersePerLine_Export/' )
        if not os.access( outputFolderpath, os.F_OK ): os.makedirs( outputFolderpath ) # Make the empty folder if there wasn't already one there

        ignoredMarkers = set()

        # First determine our format
        for VPLFormat in ('Forge',):
            thisOutputFolder = os.path.join( outputFolderpath, VPLFormat+'/' )
            if not os.access( thisOutputFolder, os.F_OK ): os.makedirs( thisOutputFolder ) # Make the empty folder if there wasn't already one there

            #print( 'VPL', repr(self.name), repr(self.shortName), repr(self.projectName), repr(self.abbreviation) )
            abbreviation = self.abbreviation if self.abbreviation else 'Unknown'
            title = self.getAName()

            ForgeBookNames = { 'GEN':'Ge', 'LEV':'Le', 'LAM':'La',
                              'MAT':'Mt', 'JDE':'Jude' }

            # Write the plain text files
            for BBB,bookObject in self.books.items():
                bookName = ForgeBookNames[BBB] if BBB in ForgeBookNames else BBB
                internalBibleBookData = bookObject._processedLines

                filename = "BOS-BibleWriter-{}.txt".format( bookName )
                filepath = os.path.join( thisOutputFolder, BibleOrgSysGlobals.makeSafeFilename( filename ) )
                if BibleOrgSysGlobals.verbosityLevel > 2: print( '  toVPL: ' + _("Writing {!r}…").format( filepath ) )
                textBuffer = ''
                with open( filepath, 'wt', encoding='utf-8' ) as myFile:
                    #try: myFile.write('\ufeff') # VPL needs the BOM
                    #except UnicodeEncodeError: # why does this fail on Windows???
                        #logger.critical( "toVPL: Unable to write BOM to file" )

                    # Write the intro stuff
                    myFile.write( '; TITLE: {}\n'.format( title ) )
                    myFile.write( '; ABBREVIATION: {}\n'.format( abbreviation ) )
                    myFile.write( '; HAS ITALICS\n' )
                    myFile.write( '; HAS FOOTNOTES\n' )
                    myFile.write( '; HAS REDLETTER\n' )

                    gotVP = None
                    haveP = False
                    for entry in internalBibleBookData:
                        marker, text = entry.getMarker(), entry.getCleanText()
                        if '¬' in marker or marker in BOS_ADDED_NESTING_MARKERS or marker=='v=':
                            continue # Just ignore added markers — not needed here
                        if marker in ('c#','vp#',):
                            ignoredMarkers.add( marker )
                            continue
                        if marker in OFTEN_IGNORED_USFM_HEADER_MARKERS or marker in ('ie',): # Just ignore these lines
                            ignoredMarkers.add( marker )
                        elif marker == 'h':
                            ignoredMarkers.add( marker )
                            #if textBuffer: myFile.write( "{}".format( textBuffer ) ); textBuffer = ''
                            #myFile.write( "{}\n\n".format( text ) )
                        elif marker in USFM_ALL_INTRODUCTION_MARKERS: # Drop the introduction
                            ignoredMarkers.add( marker )
                        elif marker in ('mt1','mt2','mt3','mt4', 'imt1','imt2','imt3','imt4',):
                            ignoredMarkers.add( marker )
                            #if textBuffer: myFile.write( "{}".format( textBuffer ) ); textBuffer = ''
                            #myFile.write( "\n{}{}\n".format( ' '*((columnWidth-len(text))//2), text ) )
                        elif marker in ('mte1','mte2','mte3','mte4', 'imte1','imte2','imte3','imte4',):
                            ignoredMarkers.add( marker )
                            #if textBuffer: myFile.write( "{}".format( textBuffer ) ); textBuffer = ''
                            #myFile.write( "\n{}{}\n\n".format( ' '*((columnWidth-len(text))//2), text ) )
                        elif marker == 'c':
                            if textBuffer: myFile.write( "{}\n".format( textBuffer ) ); textBuffer = ''
                            C = text
                        elif marker == 'vp#': # This precedes a v field and has the verse number to be printed
                            gotVP = text # Just remember it for now
                        elif marker == 'v':
                            V = text
                            if gotVP: # this is the verse number to be published
                                text = gotVP
                                gotVP = None
                            if textBuffer: myFile.write( "{}\n".format( textBuffer ) ); textBuffer = ''
                            myFile.write( "\n$$ {} {}:{}\n".format( bookName, C, V ) )
                            if haveP: textBuffer = '¶'; haveP = False
                        elif marker == 'p':
                            haveP = True
                        elif marker in ('pi1','pi2','pi3','pi4', 's1','s2','s3','s4', 'ms1','ms2','ms3','ms4',): # Drop out these fields
                            ignoredMarkers.add( marker )
                        elif text:
                            #print( "do Marker", repr(marker), repr(text) )
                            textBuffer += (' ' if textBuffer else '') + text
                    if textBuffer: myFile.write( "{}\n".format( textBuffer ) ) # Write the last bit

                        #if verseByVerse:
                            #myFile.write( "{} ({}): {!r} {!r} {}\n" \
                                #.format( entry.getMarker(), entry.getOriginalMarker(), entry.getAdjustedText(), entry.getCleanText(), entry.getExtras() ) )

            if ignoredMarkers:
                #print( "Ignored", ignoredMarkers )
                logger.info( "toVPL: Ignored markers were {}".format( ignoredMarkers ) )
                if BibleOrgSysGlobals.verbosityLevel > 2:
                    print( "  " + _("WARNING: Ignored toVPL markers were {}").format( ignoredMarkers ) )

            # Now create a zipped collection
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Zipping VPL text files…" )
            zf = zipfile.ZipFile( os.path.join( thisOutputFolder, 'AllVPLTextFiles.zip' ), 'w', compression=zipfile.ZIP_DEFLATED )
            for filename in os.listdir( thisOutputFolder ):
                if not filename.endswith( '.zip' ):
                    filepath = os.path.join( thisOutputFolder, filename )
                    zf.write( filepath, filename ) # Save in the archive without the path
            zf.close()

        if BibleOrgSysGlobals.verbosityLevel > 0 and BibleOrgSysGlobals.maxProcesses > 1:
            print( "  BibleWriter.toVPL finished successfully." )
        return True
    # end of BibleWriter.toVPL



    def toMarkdown( self, outputFolderpath:Optional[Path]=None ):
        """
        Write the Bible data out into GFM markdown format.
            The format varies, depending on whether or not there are paragraph markers in the text.
        """
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Running BibleWriter:toMarkdown…" )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert self.books

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolderpath: outputFolderpath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_Markdown_Export/' )
        if not os.access( outputFolderpath, os.F_OK ): os.makedirs( outputFolderpath ) # Make the empty folder if there wasn't already one there

        ignoredMarkers = set()

        def __formatMarkdownVerseText( BBB, C, V, givenText, extras ):
            """
            Format character codes within the text into Markdown
            """
            #print( "__formatMarkdownVerseText( {}, {}, {} )".format( repr(givenText), len(extras), ourGlobals.keys() ) )
            if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert givenText or extras

            def handleExtras( text, extras ):
                """
                Returns the MD text with footnotes and xrefs processed.
                It also accumulates MD in ourGlobals for the end notes.
                """
                def liveCV( CV ):
                    """
                    Given a CV text (in the same book), make it live
                        e.g., given 1:3 return #C1V3
                            given 17:4-9 return #C17V4
                            given 1:1-3:19 return #C1V1
                    """
                    #print( "formatMarkdownVerseText.liveCV( {} )".format( repr(CV) ) )
                    if len(CV) < 3: return ''
                    if CV and CV[-1]==':': CV = CV[:-1]

                    result = 'C' + CV.strip().replace( ':', 'V')
                    for bridgeChar in ('-', '–', '—'): # hyphen, endash, emdash
                        ix = result.find( bridgeChar )
                        if ix != -1: result = result[:ix] # Remove verse bridges
                    #print( " returns", result )
                    if result.count('C')>1 or result.count('V')>1:
                        logger.critical( "toMarkdown.liveCV created a bad link: {!r} at {} {}:{}".format( result, BBB, C, V ) )
                        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
                    return '#' + result
                # end of liveCV


                def processNote( rawFootnoteContents, noteType ):
                    """
                    Return the MD for the processed footnote or endnote.
                    It also accumulates MD in ourGlobals for the end notes.

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
                    assert noteType in ('footnote','endnote',)
                    markerList = BibleOrgSysGlobals.loadedUSFMMarkers.getMarkerListFromText( rawFootnoteContents, includeInitialText=True )
                    #print( "formatMarkdownVerseText.processFootnote( {}, {} ) found {}".format( repr(rawFootnoteContents), ourGlobals, markerList ) )
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
                                logger.error( "formatMarkdownVerseText.processNote didn't handle {} {}:{} {} marker: {}".format( BBB, C, V, noteType, marker ) )
                                fnText += txt
                                fnTitle += txt
                        if spanOpen: fnText += '</span>'; spanOpen = False
                    else: # no internal markers found
                        bits = rawFootnoteContents.split( ' ', 1 )
                        if len(bits)==2: # assume the caller is the first bit
                            caller = bits[0]
                            if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert len(caller) == 1 # Normally a +
                            fnText = fnTitle = bits[1]
                        else: # no idea really what the format was
                            fnText = fnTitle = rawFootnoteContents

                    idName = "{}{}".format( 'FNote' if noteType=='footnote' else 'ENote', fnIndex )
                    noteMD = '[fn{}]({})'.format( noteType, idName )

                    endMD = '<p id="{}" class="{}">'.format( idName, noteType )
                    if originCV:
                        endMD += '<a class="{}Origin" title="Go back up to {} in the text" href="{}">{}</a> ' \
                                                            .format( noteType, originCV, liveCV(originCV), origin )
                    endMD += '<span class="{}Entry">{}</span>'.format( noteType, fnText )
                    endMD += '</p>'

                    #print( "noteMD", BBB, noteMD )
                    #print( "endMD", endMD )
                    ourGlobals['footnoteMD' if noteType=='footnote' else 'endnoteMD'].append( endMD )
                    #if fnIndex > 2: halt

                    return noteMD
                # end of __formatMarkdownVerseText.processNote


                def processXRef( MDxref ):
                    """
                    Return the MD for the processed cross-reference (xref).
                    It also accumulates MD in ourGlobals for the end notes.

                    NOTE: The parameter here already has the /x and /x* removed.

                    \\x - \\xo 2:2: \\xt Lib 19:9-10; Diy 24:19.\\xt*\\x* (Backslashes are shown doubled here)
                        gives
                    <a title="Lib 19:9-10; Diy 24:19" href="#XRef0"><span class="XRefLinkSymbol"><sup>[xr]</sup></span></a>
                    <a title="Lib 25:25" href="#XRef1"><span class="XRefLinkSymbol"><sup>[xr]</sup></span></a>
                    <a title="Rut 2:20" href="#XRef2"><span class="XRefLinkSymbol"><sup>[xr]</sup></span></a>
                        plus
                    <p id="XRef0" class="XRef"><a title="Go back up to 2:2 in the text" href="#C2V2"><span class="ChapterVerse">2:2</span></a> <span class="VernacularCrossReference">Lib 19:9&#x2011;10</span>; <span class="VernacularCrossReference">Diy 24:19</span></p>
                    """
                    markerList = BibleOrgSysGlobals.loadedUSFMMarkers.getMarkerListFromText( MDxref, includeInitialText=True )
                    #print( "\nformatMarkdownVerseText.processXRef( {}, {} ) gives {}".format( repr(MDxref), "…", markerList ) )
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
                                logger.error( "formatMarkdownVerseText.processXRef didn't handle {} {}:{} xref marker: {}".format( BBB, C, V, marker ) )
                                xrefText += txt
                    else: # there's no USFM markers at all in the xref — presumably a caller and then straight text
                        if MDxref.startswith('+ ') or MDxref.startswith('- '):
                            caller = MDxref[0]
                            xrefText = MDxref[2:].strip()
                        else: # don't really know what it is — assume it's all just text
                            xrefText = MDxref.strip()

                    xrefMD = '[xr{}]({})'.format( xrefIndex, xrefText )

                    endMD = '<p id="XRef{}" class="xref">'.format( xrefIndex )
                    if not origin: # we'll try to make one
                        originCV = "{}:{}".format( C, V )
                    if originCV: # This only handles CV separator of : so far
                        endMD += '<a class="xrefOrigin" title="Go back up to {} in the text" href="{}">{}</a> ' \
                                                            .format( originCV, liveCV(originCV), originCV )
                    endMD += '<span class="xrefEntry">{}</span>'.format( xrefText )
                    endMD += '</p>'

                    #print( "xrefMD", BBB, xrefMD )
                    #print( "endMD", endMD )
                    ourGlobals['xrefMD'].append( endMD )
                    #if xrefIndex > 2: halt

                    return xrefMD
                # end of __formatMarkdownVerseText.processXRef


                def processFigure( MDfigure ):
                    """
                    Return the MD for the processed figure.

                    NOTE: The parameter here already has the /fig and /fig* removed.
                    """
                    logger.critical( "toMD: figure not handled yet at {} {}:{} {!r}".format( BBB, C, V, MDfigure ) )
                    figureMD = ''
                    #footnoteMD = '<a class="footnoteLinkSymbol" title="{}" href="#FNote{}">[fn]</a>' \
                                    #.format( fnTitle, fnIndex )

                    #endMD = '<p id="FNote{}" class="footnote">'.format( fnIndex )
                    #if originCV: # This only handles CV separator of : so far
                        #endMD += '<a class="footnoteOrigin" title="Go back up to {} in the text" href="{}">{}</a> ' \
                                                            #.format( originCV, liveCV(originCV), origin )
                    #endMD += '<span class="footnoteEntry">{}</span>'.format( fnText )
                    #endMD += '</p>'

                    ##print( "footnoteMD", BBB, footnoteMD )
                    ##print( "endMD", endMD )
                    #ourGlobals['footnoteMD'].append( endMD )
                    ##if fnIndex > 2: halt

                    return figureMD
                # end of __formatMarkdownVerseText.processFigure


                adjText = text
                if extras:
                    offset = 0
                    for extra in extras: # do any footnotes and cross-references
                        extraType, extraIndex, extraText, cleanExtraText = extra
                        #print( "{} {}:{} Text={!r} eT={}, eI={}, eText={!r}".format( BBB, C, V, text, extraType, extraIndex, extraText ) )
                        adjIndex = extraIndex - offset
                        lenT = len( adjText )
                        if adjIndex > lenT: # This can happen if we have verse/space/notes at end (and the space was deleted after the note was separated off)
                            logger.warning( _("formatMarkdownVerseText: Space before note at end of verse in {} {}:{} has been lost").format( BBB, C, V ) )
                            # No need to adjust adjIndex because the code below still works
                        elif adjIndex<0 or adjIndex>lenT: # The extras don't appear to fit correctly inside the text
                            print( "formatMarkdownVerseText: Extras don't fit inside verse at {} {}:{}: eI={} o={} len={} aI={}".format( BBB, C, V, extraIndex, offset, len(text), adjIndex ) )
                            print( "  Verse={!r}".format( text ) )
                            print( "  Extras={!r}".format( extras ) )
                        #assert 0 <= adjIndex <= len(verse)
                        #adjText = checkText( extraText, checkLeftovers=False ) # do any general character formatting
                        #if adjText!=extraText: print( "processXRefsAndFootnotes: {}@{}-{}={} {!r} now {!r}".format( extraType, extraIndex, offset, adjIndex, extraText, adjText ) )
                        if extraType == 'fn':
                            extra = processNote( extraText, 'footnote' )
                            #print( "fn got", extra )
                        elif extraType == 'en':
                            extra = processNote( extraText, 'endnote' )
                            #print( "en got", extra )
                        elif extraType == 'xr':
                            extra = processXRef( extraText )
                            #print( "xr got", extra )
                        elif extraType == 'fig':
                            extra = processFigure( extraText )
                            #print( "fig got", extra )
                        elif extraType == 'str':
                            extra = ''
                        elif extraType == 'sem':
                            extra = ''
                        elif extraType == 'vp':
                            extra = "\\vp {}\\vp*".format( extraText ) # Will be handled later
                        elif BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( 'eT', extraType ); halt
                        #print( "was", verse )
                        if extra:
                            adjText = adjText[:adjIndex] + str(extra) + adjText[adjIndex:]
                            offset -= len( extra )
                        #print( "now", verse )
                return adjText
            # end of __formatMarkdownVerseText.handleExtras


            # __formatMarkdownVerseText main code
            text = handleExtras( givenText, extras )

            # Semantic stuff
            text = text.replace( '\\ior ', '[' ).replace( '\\ior*', ']' )
            text = text.replace( '\\bk ', '_' ).replace( '\\bk*', '_' )
            text = text.replace( '\\iqt ', '_' ).replace( '\\iqt*', '_' )

            text = text.replace( '\\add ', '_' ).replace( '\\add*', '_' )
            text = text.replace( '\\nd ', '' ).replace( '\\nd*', '' )
            text = text.replace( '\\+nd ', '' ).replace( '\\+nd*', '' )
            text = text.replace( '\\wj ', '' ).replace( '\\wj*', '' )
            text = text.replace( '\\sig ', '' ).replace( '\\sig*', '' )
            if BBB in ('GLS',): # it's a glossary keyword entry
                text = text.replace( '\\k ', '' ).replace( '\\k*', '' )
            else: # it's a keyword in context
                text = text.replace( '\\k ', '' ).replace( '\\k*', '' )
            text = text.replace( '\\w ', '_' ).replace( '\\w*', '_' )
            text = text.replace( '\\rq ', '' ).replace( '\\rq*', '' )
            text = text.replace( '\\qs ', '' ).replace( '\\qs*', '' )
            text = text.replace( '\\va ', '(' ).replace( '\\va*', ')' )

            # Direct formatting
            text = text.replace( '\\bdit ', '*_' ).replace( '\\bdit*', '_*' )
            text = text.replace( '\\it ', '_' ).replace( '\\it*', '_' )
            text = text.replace( '\\bd ', '*' ).replace( '\\bd*', '*' )
            text = text.replace( '\\sc ', '' ).replace( '\\sc*', '' )

            if '\\' in text or '<' in text or '>' in text:
                logger.error( "formatMarkdownVerseText programming error: unprocessed code in {!r} from {!r} at {} {}:{}".format( text, givenText, BBB, C, V ) )
                if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
                    print( "formatMarkdownVerseText: unprocessed code in {!r} from {!r} at {} {}:{}".format( text, givenText, BBB, C, V ) )
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
            return text
        # end of __formatMarkdownVerseText


        # First determine our format
        verseByVerse = True

        # Write the formatted text files
        for BBB,bookObject in self.books.items():
            internalBibleBookData = bookObject._processedLines

            filename = "BOS-BibleWriter-{}.md".format( BBB )
            filepath = os.path.join( outputFolderpath, BibleOrgSysGlobals.makeSafeFilename( filename ) )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( '  toMarkdown: ' + _("Writing {!r}…").format( filepath ) )
            ourGlobals = {}
            ourGlobals['nextFootnoteIndex'] = ourGlobals['nextEndnoteIndex'] = ourGlobals['nextXRefIndex'] = 0
            ourGlobals['footnoteMD'], ourGlobals['endnoteMD'], ourGlobals['xrefMD'] = [], [], []
            C, V = '-1', '-1' # So first/id line starts at -1:0
            textBuffer = ''
            with open( filepath, 'wt', encoding='utf-8' ) as myFile:
                gotVP = None
                for entry in internalBibleBookData:
                    marker, adjText, extras = entry.getMarker(), entry.getAdjustedText(), entry.getExtras()
                    if marker in USFM_PRECHAPTER_MARKERS:
                        if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
                            assert C=='-1' or marker=='rem' or marker.startswith('mte')
                        V = str( int(V) + 1 )

                    if marker in OFTEN_IGNORED_USFM_HEADER_MARKERS or marker in ('ie',): # Just ignore these lines
                        ignoredMarkers.add( marker )
                    elif marker in ('mt1','mt2','mt3','mt4', 'imt1','imt2','imt3','imt4',):
                        if textBuffer: myFile.write( "{}".format( textBuffer ) ); textBuffer = ''
                        level = int( marker[-1] )
                        myFile.write( "\n{} {}\n".format( '#'*level, adjText ) )
                    elif marker in ('mte1','mte2','mte3','mte4', 'imte1','imte2','imte3','imte4',):
                        if textBuffer: myFile.write( "{}".format( textBuffer ) ); textBuffer = ''
                        level = int( marker[-1] )
                        myFile.write( "\n{} {}\n\n".format( '#'*level, adjText ) )
                    elif marker in ('s1','s2','s3','s4', 'is1','is2','is3','is4', 'ms1','ms2','ms3','ms4', ):
                        if textBuffer: myFile.write( "{}".format( textBuffer ) ); textBuffer = ''
                        level = int( marker[-1] ) + 2 # so s1 becomes header #3
                        myFile.write( "\n{} {}\n".format( '#'*level, adjText ) )
                    elif marker == 'c':
                        C, V = adjText, '0'
                        if textBuffer: myFile.write( "{}".format( textBuffer ) ); textBuffer = ''
                        myFile.write( "\n\nChapter {}".format( adjText ) )
                    elif marker == 'vp#': # This precedes a v field and has the verse number to be printed
                        gotVP = adjText # Just remember it for now
                    elif marker == 'v':
                        V = adjText
                        if gotVP: # this is the verse number to be published
                            adjText = gotVP
                            gotVP = None
                        if textBuffer: myFile.write( "{}".format( textBuffer ) ); textBuffer = ''
                        myFile.write( "\n{} ".format( adjText ) )
                    elif marker in ('p',): # Drop out these fields
                        ignoredMarkers.add( marker )
                    elif adjText:
                        textBuffer += (' ' if textBuffer else '') + __formatMarkdownVerseText( BBB, C, V, adjText, extras )
                if textBuffer: myFile.write( "{}\n".format( textBuffer ) ) # Write the last bit

                    #if verseByVerse:
                        #myFile.write( "{} ({}): {!r} {!r} {}\n" \
                            #.format( entry.getMarker(), entry.getOriginalMarker(), entry.getAdjustedText(), entry.getCleanText(), entry.getExtras() ) )

        if ignoredMarkers:
            logger.info( "toMarkdown: Ignored markers were {}".format( ignoredMarkers ) )
            if BibleOrgSysGlobals.verbosityLevel > 2:
                print( "  " + _("WARNING: Ignored toMarkdown markers were {}").format( ignoredMarkers ) )

        # Now create a zipped collection
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Zipping markdown files…" )
        zf = zipfile.ZipFile( os.path.join( outputFolderpath, 'AllMarkdownFiles.zip' ), 'w', compression=zipfile.ZIP_DEFLATED )
        for filename in os.listdir( outputFolderpath ):
            if not filename.endswith( '.zip' ):
                filepath = os.path.join( outputFolderpath, filename )
                zf.write( filepath, filename ) # Save in the archive without the path
        zf.close()

        if BibleOrgSysGlobals.verbosityLevel > 0 and BibleOrgSysGlobals.maxProcesses > 1:
            print( "  BibleWriter.toMarkdown finished successfully." )
        return True
    # end of BibleWriter.toMarkdown



    def __formatHTMLVerseText( BBB:str, C:str, V:str, givenText:str, extras, ourGlobals:dict ):
        """
        Format character codes within the text into HTML

        Called by toHTML5 and toBibleDoor

        NOTE: This is actually a function not a method (i.e., no self argument).
        """
        #print( "__formatHTMLVerseText( {}, {}, {} )".format( repr(givenText), len(extras), ourGlobals.keys() ) )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert givenText or extras

        def handleExtras( text:str, extras, ourGlobals:dict ):
            """
            Returns the HTML5 text with footnotes and xrefs processed.
            It also accumulates HTML5 in ourGlobals for the end notes.
            """
            def liveCV( CV:str ) -> str:
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
                if BibleOrgSysGlobals.debugFlag and (result.count('C')>1 or result.count('V')>1):
                    print( "formatHTMLVerseText.liveCV: programming error: Didn't handle reference correctly: {!r} -> {!r}".format( CV, result ) )
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
                assert noteType in ('footnote','endnote',)
                markerList = BibleOrgSysGlobals.loadedUSFMMarkers.getMarkerListFromText( rawFootnoteContents, includeInitialText=True )
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
                            logger.error( "formatHTMLVerseText.processNote didn't handle {} {}:{} {} marker: {}".format( BBB, C, V, noteType, marker ) )
                            fnText += txt
                            fnTitle += txt
                    if spanOpen: fnText += '</span>'; spanOpen = False
                else: # no internal markers found
                    bits = rawFootnoteContents.split( ' ', 1 )
                    if len(bits)==2: # assume the caller is the first bit
                        caller = bits[0]
                        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert len(caller) == 1 # Normally a +
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
                markerList = BibleOrgSysGlobals.loadedUSFMMarkers.getMarkerListFromText( HTML5xref, includeInitialText=True )
                #print( "\nformatHTMLVerseText.processXRef( {}, {} ) gives {}".format( repr(HTML5xref), "…", markerList ) )
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
                            logger.error( "formatHTMLVerseText.processXRef didn't handle {} {}:{} xref marker: {}".format( BBB, C, V, marker ) )
                            xrefText += txt
                else: # there's no USFM markers at all in the xref — presumably a caller and then straight text
                    if HTML5xref.startswith('+ ') or HTML5xref.startswith('- '):
                        caller = HTML5xref[0]
                        xrefText = HTML5xref[2:].strip()
                    else: # don't really know what it is — assume it's all just text
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
                logger.critical( "toHTML5: figure not handled yet at {} {}:{} {!r}".format( BBB, C, V, HTML5figure ) )
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
            for extra in extras: # do any footnotes and cross-references
                extraType, extraIndex, extraText, cleanExtraText = extra
                #print( "{} {}:{} Text={!r} eT={}, eI={}, eText={!r}".format( BBB, C, V, text, extraType, extraIndex, extraText ) )
                adjIndex = extraIndex - offset
                lenT = len( adjText )
                if adjIndex > lenT: # This can happen if we have verse/space/notes at end (and the space was deleted after the note was separated off)
                    logger.warning( _("formatHTMLVerseText: Space before note at end of verse in {} {}:{} has been lost").format( BBB, C, V ) )
                    # No need to adjust adjIndex because the code below still works
                elif adjIndex<0 or adjIndex>lenT: # The extras don't appear to fit correctly inside the text
                    print( "formatHTMLVerseText: Extras don't fit inside verse at {} {}:{}: eI={} o={} len={} aI={}".format( BBB, C, V, extraIndex, offset, len(text), adjIndex ) )
                    print( "  Verse={!r}".format( text ) )
                    print( "  Extras={!r}".format( extras ) )
                #assert 0 <= adjIndex <= len(verse)
                #adjText = checkText( extraText, checkLeftovers=False ) # do any general character formatting
                #if adjText!=extraText: print( "processXRefsAndFootnotes: {}@{}-{}={} {!r} now {!r}".format( extraType, extraIndex, offset, adjIndex, extraText, adjText ) )
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
                elif extraType == 'str':
                    extra = ''
                elif extraType == 'sem':
                    extra = ''
                elif extraType == 'vp':
                    extra = "\\vp {}\\vp*".format( extraText ) # Will be handled later
                elif BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( 'eT', extraType ); halt
                #print( "was", verse )
                adjText = adjText[:adjIndex] + str(extra) + adjText[adjIndex:]
                offset -= len( extra )
                #print( "now", verse )
            return adjText
        # end of __formatHTMLVerseText.handleExtras


        # __formatHTMLVerseText main code
        text = handleExtras( givenText, extras, ourGlobals )

        # Semantic stuff
        text = text.replace( '\\ior ', '<span class="outlineReferenceRange">' ).replace( '\\ior*', '</span>' )
        text = text.replace( '\\bk ', '<span class="bookName">' ).replace( '\\bk*', '</span>' )
        text = text.replace( '\\iqt ', '<span class="introductionQuotedText">' ).replace( '\\iqt*', '</span>' )

        text = text.replace( '\\add ', '<span class="addedText">' ).replace( '\\add*', '</span>' )
        text = text.replace( '\\nd ', '<span class="divineName">' ).replace( '\\nd*', '</span>' )
        text = text.replace( '\\+nd ', '<span class="divineName">' ).replace( '\\+nd*', '</span>' )
        text = text.replace( '\\wj ', '<span class="wordsOfJesus">' ).replace( '\\wj*', '</span>' )
        text = text.replace( '\\sig ', '<span class="signature">' ).replace( '\\sig*', '</span>' )
        if BBB in ('GLS',): # it's a glossary keyword entry
            text = text.replace( '\\k ', '<span class="glossaryKeyword">' ).replace( '\\k*', '</span>' )
        else: # it's a keyword in context
            text = text.replace( '\\k ', '<span class="keyword">' ).replace( '\\k*', '</span>' )
        text = text.replace( '\\w ', '<span class="wordlistEntry">' ).replace( '\\w*', '</span>' )
        text = text.replace( '\\rq ', '<span class="quotationReference">' ).replace( '\\rq*', '</span>' )
        text = text.replace( '\\qs ', '<span class="Selah">' ).replace( '\\qs*', '</span>' )
        text = text.replace( '\\ca ', '<span class="alternativeChapterNumber">(' ).replace( '\\ca*', ')</span>' )
        text = text.replace( '\\va ', '<span class="alternativeVerseNumber">(' ).replace( '\\va*', ')</span>' )

        # Direct formatting
        text = text.replace( '\\bdit ', '<span class="boldItalic">' ).replace( '\\bdit*', '</span>' )
        text = text.replace( '\\it ', '<span class="italic">' ).replace( '\\it*', '</span>' )
        text = text.replace( '\\bd ', '<span class="bold">' ).replace( '\\bd*', '</span>' )
        text = text.replace( '\\sc ', '<span class="smallCaps">' ).replace( '\\sc*', '</span>' )

        if '\\' in text:
            logger.error( "formatHTMLVerseText programming error: unprocessed code in {!r} from {!r} at {} {}:{}".format( text, givenText, BBB, C, V ) )
            if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
                print( "formatHTMLVerseText: unprocessed code in {!r} from {!r} at {} {}:{}".format( text, givenText, BBB, C, V ) )
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
        return text
    # end of __formatHTMLVerseText


    def toHTML5( self, outputFolderpath:Optional[Path]=None, controlDict=None, validationSchema=None, humanReadable=True ):
        """
        Using settings from the given control file,
            converts the USFM information to UTF-8 HTML files.
        """
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Running BibleWriter:toHTML5…" )
        if BibleOrgSysGlobals.debugFlag:
            #print( self )
            assert self.books
            #assert self.name

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolderpath: outputFolderpath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_HTML5_Export/' )
        WEBoutputFolder = os.path.join( outputFolderpath, 'Website/' )
        if not os.access( outputFolderpath, os.F_OK ): os.makedirs( WEBoutputFolder ) # Make the empty folder if there wasn't already one there

        if not controlDict:
            controlDict, defaultControlFilename = {}, "To_HTML5_controls.txt"
            try: ControlFiles.readControlFile( defaultControlFolderpath, defaultControlFilename, controlDict )
            except FileNotFoundError:
                logger.critical( "Unable to read control dict {} from {}".format( defaultControlFilename, defaultControlFolderpath ) )
        self.__adjustControlDict( controlDict )

        # Copy across our css style files
        for filenamePart in ( 'BibleBook', ):
            filepath = os.path.join( defaultControlFolderpath, filenamePart+'.css' )
            try:
                shutil.copy( filepath, WEBoutputFolder ) # Copy it under its own name
                #shutil.copy( filepath, os.path.join( WEBoutputFolder, 'Bible.css" ) ) # Copy it also under the generic name
            except FileNotFoundError: logger.error( "Unable to find CSS style file: {}".format( filepath ) )

        ignoredMarkers, unhandledMarkers = set(), set()


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
            #if 'HTML5Subject' in controlDict and controlDict['HTML5Subject']: writerObject.writeLineOpenClose( 'subject', controlDict['HTML5Subject'] )
            #if 'HTML5Description' in controlDict and controlDict['HTML5Description']: writerObject.writeLineOpenClose( 'description', controlDict['HTML5Description'] )
            #if 'HTML5Publisher' in controlDict and controlDict['HTML5Publisher']: writerObject.writeLineOpenClose( 'publisher', controlDict['HTML5Publisher'] )
            #if 'HTML5Contributors' in controlDict and controlDict['HTML5Contributors']: writerObject.writeLineOpenClose( 'contributors', controlDict['HTML5Contributors'] )
            #if 'HTML5Identifier' in controlDict and controlDict['HTML5Identifier']: writerObject.writeLineOpenClose( 'identifier', controlDict['HTML5Identifier'] )
            #if 'HTML5Source' in controlDict and controlDict['HTML5Source']: writerObject.writeLineOpenClose( 'identifier', controlDict['HTML5Source'] )
            #if 'HTML5Coverage' in controlDict and controlDict['HTML5Coverage']: writerObject.writeLineOpenClose( 'coverage', controlDict['HTML5Coverage'] )
            #writerObject.writeLineOpenClose( 'format', 'HTML5 markup language' )
            #writerObject.writeLineOpenClose( 'date', datetime.now().date().isoformat() )
            #writerObject.writeLineOpenClose( 'creator', 'BibleWriter.py' )
            #writerObject.writeLineOpenClose( 'type', 'bible text' )
            #if 'HTML5Language' in controlDict and controlDict['HTML5Language']: writerObject.writeLineOpenClose( 'language', controlDict['HTML5Language'] )
            #if 'HTML5Rights' in controlDict and controlDict['HTML5Rights']: writerObject.writeLineOpenClose( 'rights', controlDict['HTML5Rights'] )
            writerObject.writeLineClose( 'head' )

            writerObject.writeLineOpen( 'body' )

            writerObject.writeLineOpen( 'header' )
            if myBBB == 'home': writerObject.writeLineOpenClose( 'p', 'Home', ('class','homeNonlink') )
            else: writerObject.writeLineOpenClose( 'a', 'Home', [('href','index.html'),('class','homeLink')] )
            if myBBB == 'about': writerObject.writeLineOpenClose( 'p', 'About', ('class','homeNonlink') )
            else: writerObject.writeLineOpenClose( 'a', 'About', [('href','about.html'),('class','aboutLink')] )
            writerObject.writeLineOpenClose( 'h1', self.name if self.name else 'Unknown', ('class','mainHeader') )
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
                BBB = bkData.BBB
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
            writerObject.writeLineText( "This page automatically created {} by {} v{}".format( datetime.today().strftime("%d-%b-%Y"), PROGRAM_NAME, PROGRAM_VERSION ) )
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
            assert refTuple and len(refTuple)==4
            assert refTuple[0] is None or ( refTuple[0] and len(refTuple[0])==3 ) #BBB
            if refTuple[0] in filenameDict:
                return '{}#C{}V{}'.format( filenameDict[refTuple[0]], refTuple[1], refTuple[2] )
            else: logger.error( "toHTML5.convertToPageReference can't find book: {!r}".format( refTuple[0] ) )
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
            #print( "toHTML5.createSectionCrossReference: {!r}".format( givenRef ) )
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
                    analysis = BRL.getFirstReference( ref, "section cross-reference {!r} from {!r}".format( ref, givenRef ) )
                    #print( "a", analysis )
                    link = convertToPageReference(analysis) if analysis else None
                    result += '<a class="sectionCrossReferenceLink" href="{}">{}</a>'.format( link, originalRef ) if link else originalRef
            #print( "  Returning {!r}".format( result + bracket ) )
            return result + bracket
        # end of toHTML5.createSectionCrossReference


        def writeHomePage():
            if BibleOrgSysGlobals.verbosityLevel > 1: print( _("    Creating HTML5 home/index page…") )
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
            if BibleOrgSysGlobals.verbosityLevel > 1: print( _("    Creating HTML5 about page…") )
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
            """
            Writes a book to the HTML5 writerObject.
            """

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
            html5Globals['nextFootnoteIndex'] = html5Globals['nextEndnoteIndex'] = html5Globals['nextXRefIndex'] = 0
            html5Globals['footnoteHTML5'], html5Globals['endnoteHTML5'], html5Globals['xrefHTML5'] = [], [], []
            gotVP = None
            C, V = '-1', '-1' # So first/id line starts at -1:0
            for processedBibleEntry in bkData._processedLines: # Process internal Bible data lines
                marker, text, extras = processedBibleEntry.getMarker(), processedBibleEntry.getAdjustedText(), processedBibleEntry.getExtras()
                haveExtraFormatting = True if extras else False
                if text != processedBibleEntry.getCleanText(): haveExtraFormatting = True
                #if BBB=='MRK': print( "writeHTML5Book", marker, text )
                #print( "toHTML5.writeHTML5Book: {} {}:{} {}={}".format( BBB, C, V, marker, repr(text) ) )
                if '¬' in marker or marker in BOS_ADDED_NESTING_MARKERS or marker=='v=':
                    continue # Just ignore added markers — not needed here
                if marker in USFM_PRECHAPTER_MARKERS:
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
                        assert C=='-1' or marker=='rem' or marker.startswith('mte')
                    V = str( int(V) + 1 )

                # Markers usually only found in the introduction
                if marker in OFTEN_IGNORED_USFM_HEADER_MARKERS or marker in ('ie',): # Just ignore these lines
                    ignoredMarkers.add( marker )
                elif marker in ('mt1','mt2','mt3','mt4', 'imt1','imt2','imt3','imt4',):
                    if haveOpenParagraph:
                        logger.error( "toHTML5: didn't expect {} field with paragraph still open at {} {}:{}".format( marker, BBB, C, V ) )
                        writerObject.writeLineClose( 'p' ); haveOpenParagraph = False
                    tClass = 'mainTitle' if marker in ('mt1','mt2','mt3','mt4',) else 'introductionMainTitle'
                    if text: writerObject.writeLineOpenClose( 'h1', text, ('class',tClass+marker[2]) )
                elif marker in ('is1','is2','is3','is4',):
                    if haveOpenParagraph: writerObject.writeLineClose( 'p' ); haveOpenParagraph = False
                    #if not haveOpenParagraph:
                        #logger.warning( "toHTML5: Have {} introduction section heading {} outside a paragraph in {}".format( marker, text, BBB ) )
                        #writerObject.writeLineOpen( 'p', ('class','unknownParagraph') ); haveOpenParagraph = True
                    if text: writerObject.writeLineOpenClose( 'h3', text, ('class','introductionSectionHeading'+marker[2]) )
                elif marker in ('ip','ipi','ipq','ipr', 'im','imi','imq', 'iq1','iq2','iq3','iq4', 'iex', ):
                    if haveOpenParagraph:
                        logger.error( "toHTML5: didn't expect {} field with paragraph still open at {} {}:{}".format( marker, BBB, C, V ) )
                        writerObject.writeLineClose( 'p' ); haveOpenParagraph = False
                    #if haveOpenParagraph: writerObject.writeLineClose( 'p' ); haveOpenParagraph = False
                    if not haveOpenSection:
                        writerObject.writeLineOpen( 'section', ('class','regularSection') ); haveOpenSection = True
                    if text or extras:
                        writerObject.writeLineOpenClose( 'p', BibleWriter.__formatHTMLVerseText( BBB, C, V, text, extras, ourGlobals ), ('class',ipHTMLClassDict[marker]), noTextCheck=haveExtraFormatting )
                        #writerObject.writeLineText( BibleWriter.__formatHTMLVerseText( BBB, C, V, text, extras, ourGlobals ), noTextCheck=True )
                elif marker == 'iot':
                    if haveOpenParagraph:
                        logger.error( "toHTML5: didn't expect {} field with paragraph still open at {} {}:{}".format( marker, BBB, C, V ) )
                        writerObject.writeLineClose( 'p' ); haveOpenParagraph = False
                    #if haveOpenParagraph: writerObject.writeLineClose( 'p' ); haveOpenParagraph = False
                    if text: writerObject.writeLineOpenClose( 'h3', text, ('class','introductionOutlineTitle') )
                elif marker in ('io1','io2','io3','io4',):
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not haveOpenParagraph
                    #if haveOpenParagraph: writerObject.writeLineClose( 'p' ); haveOpenParagraph = False
                    if text: writerObject.writeLineOpenClose( 'p', liveLocal(text), ('class','introductionOutlineEntry'+marker[2]), noTextCheck=True )
                elif marker == 'ib':
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not text and not extras
                    writerObject.writeLineOpenClose( 'p', ' ', ('class','introductionBlankParagraph') )
                elif marker == 'periph':
                    if haveOpenParagraph: writerObject.writeLineClose( 'p' ); haveOpenParagraph = False
                    if BibleOrgSysGlobals.debugFlag:
                        assert BBB in ('FRT','INT','BAK','OTH',)
                        assert text and not extras
                    writerObject.writeLineOpenClose( 'p', ' ', ('class','peripheralContent') )
                elif marker in ('mte1','mte2','mte3','mte4', 'imte1','imte2','imte3','imte4',):
                    if haveOpenParagraph: writerObject.writeLineClose( 'p' ); haveOpenParagraph = False
                    if text: writerObject.writeLineOpenClose( 'h1', text, ('class','endTitle'+marker[3]) )

                # Now markers in the main text
                elif marker == 'c':
                    V = '0'
                    if haveOpenVerse: writerObject.writeLineClose( 'span' ); haveOpenVerse = False
                    if extras: print( "toHTML5: have extras at c at",BBB,C)
                    # What should we put in here — we don't need/want to display it, but it's a place to jump to
                    writerObject.writeLineOpenClose( 'span', ' ', [('class','chapterStart'),('id','CS'+text)] )
                elif marker == 'cp': # ignore this for now… XXXXXXXXXXXXXXXXXXXXXXXXX
                    ignoredMarkers.add( marker )
                elif marker == 'c#':
                    if extras: print( "toHTML5: have extras at c# at",BBB,C)
                    C = text
                    if not haveOpenParagraph:
                        #logger.warning( "toHTML5: Have chapter number {} outside a paragraph in {} {}:{}".format( text, BBB, C, V ) )
                        writerObject.writeLineOpen( 'p', ('class','unknownParagraph') ); haveOpenParagraph = True
                    # Put verse 1 id here on the chapter number (since we don't output a v1 number)
                    writerObject.writeLineOpenClose( 'span', text, [('class','chapterNumber'),('id','CT'+text)] )
                    writerObject.writeLineOpenClose( 'span', '&nbsp;', ('class','chapterNumberPostspace') )
                elif marker == 'vp#': # This precedes a v field and has the verse number to be printed
                    gotVP = text # Just remember it for now
                elif marker == 'v':
                    if haveOpenVerse: writerObject.writeLineClose( 'span' ); haveOpenVerse = False
                    V = text
                    if gotVP: # this is the verse number to be published
                        text = gotVP
                        gotVP = None
                    if not haveOpenParagraph:
                        logger.warning( "toHTML5: Have verse number {} outside a paragraph in {} {}:{}".format( text, BBB, C, V ) )
                    writerObject.writeLineOpen( 'span', [('class','verse'),('id','C'+C+'V'+V)] ); haveOpenVerse = True
                    if V == '1': # Different treatment for verse 1
                        writerObject.writeLineOpenClose( 'span', ' ', ('class','verseOnePrespace') )
                        writerObject.writeLineOpenClose( 'span', V, ('class','verseOneNumber') )
                        writerObject.writeLineOpenClose( 'span', '&nbsp;', ('class','verseOnePostspace') )
                    elif V: # not verse one and not blank
                        writerObject.writeLineOpenClose( 'span', ' ', ('class','verseNumberPrespace') )
                        writerObject.writeLineOpenClose( 'span', V, ('class','verseNumber') )
                        writerObject.writeLineOpenClose( 'span', '&nbsp;', ('class','verseNumberPostspace') )

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
                    if text or extras: writerObject.writeLineOpenClose( 'h3', BibleWriter.__formatHTMLVerseText( BBB, C, V, text, extras, ourGlobals ), ('class','sectionHeading'+marker[1]), noTextCheck=haveExtraFormatting )
                elif marker in ('r', 'sr', 'mr',):
                    if BibleOrgSysGlobals.strictCheckingFlag and (debuggingThisModule or BibleOrgSysGlobals.debugFlag): assert not haveOpenVerse
                    if haveOpenVerse: writerObject.writeLineClose( 'span' ); haveOpenVerse = False
                    if haveOpenParagraph: writerObject.writeLineClose( 'p' ); haveOpenParagraph = False
                    if not haveOpenSection:
                        logger.warning( "toHTML5: Have {} section reference {} outside a section in {} {}:{}".format( marker, text, BBB, C, V ) )
                        writerObject.writeLineOpen( 'section', ('class','regularSection') ); haveOpenSection = True

                    if marker == 'r': rClass = 'sectionCrossReference'
                    elif marker == 'sr': rClass = 'sectionReferenceRange'
                    elif marker == 'mr': rClass = 'majorSectionReferenceRange'
                    if text: writerObject.writeLineOpenClose( 'p', createSectionCrossReference(text), ('class',rClass), noTextCheck=True )
                elif marker == 'd': # descriptive title or Hebrew subtitle
                    if text or extras: writerObject.writeLineOpenClose( 'p', BibleWriter.__formatHTMLVerseText( BBB, C, V, text, extras, ourGlobals ), ('class','descriptiveTitle'), noTextCheck=haveExtraFormatting )
                elif marker == 'sp': # speaker
                    if text: writerObject.writeLineOpenClose( 'p', text, ('class','speaker') )
                elif marker in ('p','m','pmo','pm','pmc','pmr','pi1','pi2','pi3','pi4','mi','cls','pc','pr','ph1','ph2','ph3','ph4',) \
                or marker in ('q1','q2','q3','q4','qr','qc','qm1','qm2','qm3','qm4',):
                    if haveOpenListItem: writerObject.writeLineClose( 'span' ); haveOpenListItem = False
                    if haveOpenList:
                        for lx in ('4','3','2','1',): # Close any open lists
                            if lx in haveOpenList and haveOpenList[lx]: writerObject.writeLineClose( 'p' ); del haveOpenList[lx]
                    if haveOpenVerse: writerObject.writeLineClose( 'span' ); haveOpenVerse = False
                    if haveOpenParagraph: writerObject.writeLineClose( 'p' ); haveOpenParagraph = False
                    writerObject.writeLineOpen( 'p', ('class',pqHTMLClassDict[marker]) ); haveOpenParagraph = True
                    if text and BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
                elif marker in ('li1','li2','li3','li4','ili1','ili2','ili3','ili4',):
                    if marker.startswith('li'): m, pClass, iClass = marker[2], 'list'+marker[2], 'listItem'+marker[2]
                    else: m, pClass, iClass = marker[3], 'introductionList'+marker[3], 'introductionListItem'+marker[3]
                    if not haveOpenList or m not in haveOpenList or not haveOpenList[m]:
                        writerObject.writeLineOpen( 'p', ('class',pClass) ); haveOpenList[m] = True
                    if marker.startswith('li'):
                        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not text
                        writerObject.writeLineOpen( 'span', ('class',iClass) ); haveOpenListItem = True
                    elif text: writerObject.writeLineOpenClose( 'span', BibleWriter.__formatHTMLVerseText( BBB, C, V, text, extras, ourGlobals ), ('class',iClass) )
                elif marker == 'b':
                    if haveOpenVerse: writerObject.writeLineClose( 'span' ); haveOpenVerse = False
                    if haveOpenParagraph: writerObject.writeLineClose( 'p' ); haveOpenParagraph = False
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not text and not extras
                    writerObject.writeLineOpenClose( 'p', ' ', ('class','blankParagraph') )

                # Character markers
                elif marker in ('v~','p~',):
                    #if BibleOrgSysGlobals.debugFlag and marker=='v~': assert haveOpenVerse
                    if not haveOpenParagraph:
                        logger.warning( "toHTML5: Have verse text {} outside a paragraph in {} {}:{}".format( text, BBB, C, V ) )
                        writerObject.writeLineOpen( 'p', ('class','unknownParagraph') ); haveOpenParagraph = True
                    if not haveOpenVerse:
                        writerObject.writeLineOpen( 'span', ('class','verse') ); haveOpenVerse = True
                    if text or extras:
                        writerObject.writeLineOpenClose( 'span', BibleWriter.__formatHTMLVerseText( BBB, C, V, text, extras, ourGlobals ), ('class','verseText'), noTextCheck=True )

                elif marker in ('nb','cl','vp#',): # These are the markers that we can safely ignore for this export
                    if BibleOrgSysGlobals.debugFlag and marker=='nb': assert not text and not extras
                    ignoredMarkers.add( marker )
                else:
                    if text:
                        logger.critical( "toHTML5: {} lost text in {} field in {} {}:{} {!r}".format( self.abbreviation, marker, BBB, C, V, text ) )
                        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
                    if extras:
                        logger.critical( "toHTML5: {} lost extras in {} field in {} {}:{}".format( self.abbreviation, marker, BBB, C, V ) )
                        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
                    unhandledMarkers.add( marker )
                if extras and marker not in ('v~','p~','s1','s2','s3','s4','d', 'ip','ipi','ipq','ipr', 'im','imi','imq', 'iq1','iq2','iq3','iq4', 'iex',):
                    logger.critical( "toHTML5: extras not handled for {} at {} {}:{}".format( marker, BBB, C, V ) )
                    if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt

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
        if 'PublicationCode' not in controlDict or controlDict['PublicationCode'] == 'GENERIC':
            BOS = self.genericBOS
            BRL = self.genericBRL
        else:
            BOS = BibleOrganisationalSystem( controlDict['PublicationCode'] )
            BRL = BibleReferenceList( BOS, BibleObject=None )

        if BibleOrgSysGlobals.verbosityLevel > 2: print( _("  Exporting to HTML5 format…") )
        suffix = controlDict['HTML5Suffix'] if 'HTML5Suffix' in controlDict else 'html'
        filenameDict = {}
        for BBB in self.books: # Make a list of filenames
            try: filename = controlDict['HTML5OutputFilenameTemplate'].replace('__BOOKCODE__',BBB ).replace('__SUFFIX__',suffix)
            except KeyError: filename = BBB + '.html'
            filenameDict[BBB] = BibleOrgSysGlobals.makeSafeFilename( filename.replace( ' ', '_' ) )

        html5Globals = {}
        if 'HTML5Files' not in controlDict or controlDict['HTML5Files']=='byBook':
            for BBB,bookData in self.books.items(): # Now export the books
                if BibleOrgSysGlobals.verbosityLevel > 2: print( _("    Exporting {} to HTML5 format…").format( BBB ) )
                xw = MLWriter( filenameDict[BBB], WEBoutputFolder, 'HTML' )
                xw.setHumanReadable()
                xw.start( noAutoXML=True )
                xw.writeLineText( '<!DOCTYPE html>', noTextCheck=True )
                xw.writeLineOpen( 'html' )
                if BibleOrgSysGlobals.debugFlag: writeHTML5Book( xw, BBB, bookData, html5Globals ) # Halts on errors
                else:
                    try: writeHTML5Book( xw, BBB, bookData, html5Globals )
                    except Exception as err:
                        print( BBB, "Unexpected error:", sys.exc_info()[0], err)
                        logger.error( "toHTML5: Oops, creating {} failed!".format( BBB ) )
                xw.writeLineClose( 'html' )
                xw.close()
            writeHomePage()
            writeAboutPage()
        elif BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt # not done yet

        if ignoredMarkers:
            logger.info( "toHTML5: Ignored markers were {}".format( ignoredMarkers ) )
            if BibleOrgSysGlobals.verbosityLevel > 2:
                print( "  " + _("WARNING: Ignored toHTML5 markers were {}").format( ignoredMarkers ) )
        if unhandledMarkers:
            logger.warning( "toHTML5: Unhandled markers were {}".format( unhandledMarkers ) )
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print( "  " + _("WARNING: Unhandled toHTML5 markers were {}").format( unhandledMarkers ) )

        # Now create a zipped collection
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Zipping HTML5 files…" )
        zf = zipfile.ZipFile( os.path.join( outputFolderpath, 'AllWebFiles.zip' ), 'w', compression=zipfile.ZIP_DEFLATED )
        for filename in os.listdir( WEBoutputFolder ):
            if not filename.endswith( '.zip' ):
                filepath = os.path.join( WEBoutputFolder, filename )
                zf.write( filepath, filename ) # Save in the archive without the path
        zf.close()

        if validationSchema: validationResult = xw.validate( validationSchema ) # Returns a 3-tuple: intCode, logString, errorLogString
        if BibleOrgSysGlobals.verbosityLevel > 0 and BibleOrgSysGlobals.maxProcesses > 1:
            print( "  BibleWriter.toHTML5 finished successfully." )
        if validationSchema: return validationResult # Returns a 3-tuple: intCode, logString, errorLogString
        return True
    # end of BibleWriter.toHTML5



    def _toBibleDoorText( self, outputFolderpath:Optional[Path]=None ) -> bool:
        """
        Adjust the pseudo USFM and write the text and index files (by book) to be used by the BibleDoor app.
            (This is a newer format than the older CHTML format used by the MS-Bible app.

        Text is chunked into sections if possible, else chapters.

        Each section is broken into paragraphs if possible, else verses.
        Paragraph markers (without backslashes) are placed at the beginning of each chunk
                followed by an equals sign.
            Note: some markers (like 'b') don't have any text after the equals sign.
            Also, uncompleted Bibles might have blank fields (or maybe just a series of verse markers).
            Hopefully each line in the output file will start with a paragraph marker and equals sign.
        Chapter and verse numbers are placed inline in {} fields at the display position, e.g., {c1}{v1}.
        USFM footnote and character formatting remains unchanged
            (because they already have both start and END markers for easy parsing)

        The output format looks like this (with backslashes escaped here but not in the file):
            mt2=Ka igkarangeb ne sulat ni
            mt1=Huwan
            is1=Igpewun-a
            ip=Seini ka igkarangeb ne sulat ni Apustul Huwan ne sabeka te me hibateen ni Hisus. Impeendiye din ka seini ne sulat te malitan ne in-alam te Manama wey diye degma te me anak din. Ne kema ke punduk buwa te migmalintutuu ka igpasabut din kayi. Seini se malepet ne sulat, mighangyu te keilangan ne eg-ikul te kamalehetan wey egpaheyinaweey ka tagse sabeka, wey migpaney-paney degma seini meyitenged te me etew ne migpanulu ne ware kun migpekeetew si Hisu Kristu.
            iot=Ka nenasulat te seini ne baseen
            io1=Pegpangemusta \\ior 1-3\\ior*
            io1=Ka kamalehetan wey ka geyinawa \\ior 4-6\\ior*
            io1=Pegpaney-paney meyitenged te kene ne malehet ne pegpanulu \\ior 7-11\\ior*
            io1=Ka katammanan \\ior 12-13\\ior*
            p={c1}{v1}Sikeddiey si Huwan ka igbuyag te migmalintutuu ka migpeuyan te seini ne sulat. Egpangemusta a te malitan\\f + \\fr 1:1 \\ft Iyan buwa igpasabut te “malitan” ka sabeka ne punduk te migmalintutuu.\\f* ne in-alam te Manama wey diye degma te me anak din. Miggeyinawaan ku sikaniyu langun due te kamalehetan, ne kene ne sikeddiey re, ke kene, ka langun degma ne nakataha te kamalehetan,{v2}tenged su kayid e te pusung ta ka kamalehetan wey kenad e egkaawe te minsan ken-u.
            p={v3}Ka keupiya, keyid-u, wey keupianan ne egpuun te Manama ne Amey wey te Anak din ne si Hisu Kristu, egkaangken niyu. Igbehey sika te Manama te seeye se egdawat te kamalehetan wey te geyinawa.
            s1=Ka kamalehetan wey ka geyinawa
            p={v4}Amana a nahale te pegkanengnengi ku ne due me anak nu ne mig-ikul te kamalehetan, sumale te insuhu kanta te Amey.{v5}\\x + \\xo 5: \\xt Huw 13:34; 15:12,17.\\x*Ne kuntee, eghangyuen ku sikeykew atebey, ne paheyinaweey ki ka tagse sabeka. Kene ne iyam sika ne suhu, ke kene, tapey e sika puun pad te bunsuranan.{v6}Egkakita ka geyinawa ne egkahiyen ku pinaahi te pegtuman ta te me suhu din. Tapey niyud e ne narineg ka sika ne suhu puun pad te bunsuranan, ne keilangan ne egbatasanen niyu ka peggeyinawa.
            b=
            p={v7}Masulug ka nanginguma kayi te kalibutan ne eg-akal te me etew. Kene egpalintutuu sikandan ne migpekeetew si Hisu Kristu. Ka me etew ne iling due, talag-akal wey kuntere ni Kristu!{v8}Bantey kew ne kene egkalaag ka ingkalasey ta su eyew kene egkasalinan ka dasag ne egkarawat niyu.
            p={v9}Ka minsan hentew ne ware mig-ikul te impanulu ni Kristu piru nasi migtimul kayi, ware diye te kandin ka Manama. Piru ka minsan hentew ne mig-ikul te impanulu ni Kristu, due te kandin ka Amey wey ka Anak degma.{v10}Ke due eggendue te kaniyu ne kene egpanulu te impanulu ni Kristu, kene niyu sikandin palasura diye te baley niyu, wey kene niyu banasali.{v11}Su seeye se egbanasal kandin, egpakaruma te mareet ne himu rin.
            s1=Ka pegpanaha-taha
            p={v12}Masulug pad perem ka iglalag ku kaniyu, piru kena a egkeupian ne igsulat ku pad seini. Igkeupii ku ne egpakapanumbaley e pad kaniyu wey egpakiglalag iya kaniyu su eyew amana ki egkahale.
            p={v13}Egpangemusta degma keykew ka me anak te suled nu\\f + \\fr 1:13 \\ft Iyan buwa igpasabut te “anak te suled nu ne malitan” ka me sakup te lein ne punduk te migmalintutuu.\\f* ne in-alam degma te Manama.

        with a separate index entry (by section) like this:
            index {('Iv0'): 742, ('1v0'): 1412, ('1v3'): 2665, …}

        """
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Running BibleWriter:_toBibleDoorText…" )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert self.books

        BDDataFormatVersion = 1 # Increment this when the data files / arrays change
        jsonIndent = 1 # Keep files small for small phones
        paragraphDelimiter = '='

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolderpath: outputFolderpath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_BDText_Export/' )
        if not os.access( outputFolderpath, os.F_OK ): os.makedirs( outputFolderpath ) # Make the empty folder if there wasn't already one there
        #if not controlDict: controlDict = {}; ControlFiles.readControlFile( 'ControlFiles', "To_XXX_controls.txt", controlDict )
        #assert controlDict and isinstance( controlDict, dict )
        bookOutputFolder = os.path.join( outputFolderpath, 'ByBook.{}.BDTXT/'.format( BDDataFormatVersion ) )
        if not os.access( bookOutputFolder, os.F_OK ): os.makedirs( bookOutputFolder ) # Make the empty folder if there wasn't already one there

        ignoredMarkers, unhandledMarkers = set(), set()


        def savePreviousSection() -> None:
            """
            Updates bookIndexDict, bookIndexList
                and the bookText (concatenated sections of text)
                plus various variables ready for the next section.
            """
            nonlocal bookText, savedC, savedV, savedText, currentText, sectionCV

            if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
                print( f"After {self.abbreviation} {BBB} {C}:{V} '{pseudoMarker}': saving index entry {savedC}:{savedV}—{lastC}:{lastV} @ {len(bookText):,} with sectionCV={sectionCV}" )
                for j,line in enumerate( currentText.splitlines() ):
                    #print( f"  {j+1}/ {line}" )
                    assert line.index(paragraphDelimiter) <= 5 # Should start with a paragraph marker, e.g., imte1
                if savedText: assert len(savedText) > 30 # Can be a short ms1=xxx entry
                #print( f"currentText ({len(currentText)}) = '{currentText}'" )
                assert len(currentText) > 50 or 'ms1=' in currentText # Can be as short as one verse at Neh 1:1
            if BibleOrgSysGlobals.strictCheckingFlag:
                assert sectionCV not in bookIndexDict
            elif sectionCV in bookIndexDict:
                logger.critical( f"toBibleDoorText at {BBB} {savedC}:{savedV}—{lastC}:{lastV} is overwriting a section: {sectionCV} currentCV={C}:{V}" )
                logger.critical( f"  savedText={savedText!r}" )
                logger.critical( f"  currentText={currentText!r}" )
            bookIndexDict[sectionCV] = len(bookText)
            bookIndexList.append( (savedC,savedV, lastC,lastV, len(bookText),len(currentText)) )
            bookText += currentText
            savedC, savedV, savedText = C, V, currentText
            currentText = currentParagraphMarker = ''
            sectionCV = f'{C}v{V}'
        # end of _toBibleDoorText.savePreviousSection


        # Main loop for _toBibleDoorText
        # Adjust the extracted outputs
        paragraphMarkers = USFM_ALL_TITLE_MARKERS + USFM_ALL_SECTION_HEADING_MARKERS \
                                + USFM_ALL_BIBLE_PARAGRAPH_MARKERS \
                                + ('r','d','ms1','mr','sr','sp','ib','b','nb','cl¤','tr')
        for BBB,bookObject in self.books.items():
            try: haveSectionHeadingsForBook = self.discoveryResults[BBB]['haveSectionHeadings']
            except AttributeError: haveSectionHeadingsForBook = False
            #print( "\nhaveSectionHeadingsForBook", BBB, haveSectionHeadingsForBook ) #, self.discoveryResults[BBB] )
            needToSaveByChapter = not haveSectionHeadingsForBook \
                                  or not BibleOrgSysGlobals.loadedBibleBooksCodes.continuesThroughChapters(BBB)
            #print( f"{BBB} needToSaveByChapter={needToSaveByChapter} haveSectionHeadingsForBook={haveSectionHeadingsForBook} continuesThroughChapters={BibleOrgSysGlobals.loadedBibleBooksCodes.continuesThroughChapters(BBB)}" )

            internalBibleBookData = bookObject._processedLines
            #print( "\ninternalBibleBookData", internalBibleBookData[:50] ); halt

            # TODO: This code is HORRIFIC — rewrite!!!
            bookText, bookIndexDict, bookIndexList = '', {}, []
            inField = None
            C, V = 'I', '-1' # So first/id line starts at I:0
            lastC = savedC = C
            lastV = savedV = '1'
            sectionCV = '{}v{}'.format( C, V )
            currentText = savedText = currentParagraphMarker = ''
            for processedBibleEntry in internalBibleBookData:
                pseudoMarker, fullText, cleanText = processedBibleEntry.getMarker(), processedBibleEntry.getFullText(), processedBibleEntry.getCleanText()
                if '¬' in pseudoMarker or pseudoMarker in BOS_ADDED_NESTING_MARKERS: continue # Just ignore most added markers — not needed here
                #print( f"{C}:{V} {pseudoMarker}={cleanText}" )
                if pseudoMarker in USFM_PRECHAPTER_MARKERS \
                or C == 'I': # This second part also copes with misuse of
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
                        assert C=='I' or pseudoMarker=='rem' or pseudoMarker.startswith('mte')
                    V = str( int(V) + 1 )
                    lastV = V
                if pseudoMarker in ('id','ide','h','toc1','toc2','toc3','rem','ie'): continue # don't need these
                #print( "_toBibleDoorText processing {!r} {!r} {}".format( self.abbreviation, pseudoMarker, fullText[:60]+('…' if len(fullText)>60 else '') ) )
                if pseudoMarker in ('vp#',):
                    ignoredMarkers.add( pseudoMarker )
                    continue
                #fullText = cleanText # (temp)
                #if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( "toUSFM: pseudoMarker = {!r} fullText = {!r}".format( pseudoMarker, fullText ) )
                #print( 'BDText2', BBB, pseudoMarker, repr(fullText) )

                if (BBB=='FRT' and pseudoMarker=='is1') \
                or pseudoMarker == 's1' \
                or (pseudoMarker == 'c' \
                    and ((C == 'I' or needToSaveByChapter) \
                        or (BBB=='PRO' and cleanText in ('11','12','13','14','15','16','17','18','19','20','21','22','26','27','28','29')))
                    ):
                    if currentText: # start a new section
                        if pseudoMarker=='s1':
                            assert haveSectionHeadingsForBook
                            if debuggingThisModule: print( "Saving at s1 section heading" )
                        elif pseudoMarker=='c':
                            assert C=='I' or needToSaveByChapter or BBB=='PRO'
                            if debuggingThisModule:
                                if C=='I': print( "Saving at first chapter after intro" )
                                elif needToSaveByChapter: print( "Saving by chapter" )
                                elif BBB=='PRO': print( "Saving PROVERBS chapter" )
                                else: halt
                            assert cleanText.isdigit() # Chapter number only
                            C = cleanText
                            V = '1' # Catch up on the chapter number
                            #if savedV == '0': savedV = '1' # Assume no intro so get a more likely verse number
                        savePreviousSection()
                    else:
                        logger.critical( f"toBibleDoorText {self.abbreviation} skipped making an index entry for blank text around {BBB} {C}:{V}" )

                if pseudoMarker == 'c':
                    assert cleanText.isdigit() # Chapter number only
                    C, V = cleanText, '1' # doesn't handle footnotes on chapter numbers
                    if C in ('0', '1'):
                        #print( f"currentText={currentText}" )
                        assert not currentText
                        savedC, savedV = C, V
                        sectionCV = f'{C}v{V}'
                elif pseudoMarker == 'c#':
                    if currentParagraphMarker in ('','s1','r'):
                        logger.critical( f"toBibleDoorText {self.abbreviation} {BBB} encountered a paragraph error"
                                         f" with a verse following {currentParagraphMarker!r} around {C}:{V}" )
                        currentText += 'm{}'.format( paragraphDelimiter ) # Put in a margin paragraph
                    currentText += f'{{c{cleanText}}}'
                elif pseudoMarker in ('v=','v'): # v= precedes the following section heading, etc.
                    if C=='I': C = '1' # Some single chapter books don't have a chapter one marker
                    V = cleanText
                    if '-' in V: V = V[:V.index('-')]
                    elif '–' in V: V = V[:V.index('–')] # en dash
                    if pseudoMarker == 'v': # only (not v=)
                        lastC, lastV = C, V
                        currentText += '{{v{}}}'.format( cleanText ) # ignores footnotes on verse numbers
                elif pseudoMarker in paragraphMarkers:
                    if pseudoMarker == 's1':
                        assert not currentText
                        savedC, savedV = C, V
                        sectionCV = '{}v{}'.format( C, V )
                    if currentText: currentText += '\n'
                    currentText += '{}{}{}'.format( pseudoMarker, paragraphDelimiter, fullText )
                    currentParagraphMarker = pseudoMarker
                elif pseudoMarker == 'v~':
                    #print( "Ooops {!r} {!r} {!r}".format( pseudoMarker, currentText[-4:], currentParagraphMarker ) )
                    assert currentText[-1] == '}' # Verse marker
                    if currentParagraphMarker in ('','s1','r'):
                        logger.warning( "_toBibleDoorText {} {} encountered a paragraph error with a verse following {!r} around {}:{}" \
                                                    .format( self.abbreviation, BBB, currentParagraphMarker, C, V ) )
                        currentText += 'm{}'.format( paragraphDelimiter ) # Put in a margin paragraph
                    currentText += fullText
                elif pseudoMarker == 'p~':
                    #print( "Ooops", repr(currentText[-4:]) )
                    assert currentText[-1] == paragraphDelimiter
                    assert currentParagraphMarker not in ('','s1','r')
                    currentText += fullText
                else:
                    #print( 'BDText3 remainder!', BBB, pseudoMarker, repr(fullText) )
                    unhandledMarkers.add( pseudoMarker )

            if len(currentText) > 0: # save the final index entry
                if not haveSectionHeadingsForBook: savedC, V = C, '1' # Catch up on the chapter number
                savePreviousSection()
                #if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
                    #print( f"At {BBB} {C}:{V} '{pseudoMarker}': saving final index entry {savedC}:{savedV} @ {len(bookText):,} with sectionCV={sectionCV}" )
                    #for j,line in enumerate( currentText.splitlines() ):
                        ##print( f"  {j+1}/ {line}" )
                        #assert line.index(paragraphDelimiter) <= 5 # Should start with a paragraph marker, e.g., imte1
                #assert sectionCV not in bookIndexDict
                #bookIndexDict[sectionCV] = len(bookText)
                #bookIndexList.append( (savedC,savedV, lastC,lastV, len(bookText),len(currentText)) )
                #bookText += currentText

            ## Adjust the bookText output
            #bookText = noisyRegExDeleteAll( bookText, '\\\\str .+?\\\str\\*' )
            #if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
                #assert '\\str' not in bookText
                #assert '&quot;' not in bookText
                #assert '&amp;' not in bookText
                #assert '&lt;' not in bookText and '&gt;' not in bookText

            # Write the bookText output
            #print( "BDText", bookText[:4000] )
            filename = f'{BBB}.{BDDataFormatVersion}.bd.txt'
            filepath = os.path.join( bookOutputFolder, BibleOrgSysGlobals.makeSafeFilename( filename ) )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( '  toBDText: ' + _("Writing {!r}…").format( filepath ) )
            with open( filepath, 'wt', encoding='utf-8' ) as myFile:
                myFile.write( bookText )

            ## Write the index dict
            ##print( "index", bookIndex )
            #filename = "{}.{}.bd.d.idx".format( BBB, BDDataFormatVersion )
            #filepath = os.path.join( bookOutputFolder, BibleOrgSysGlobals.makeSafeFilename( filename ) )
            #if BibleOrgSysGlobals.verbosityLevel > 2: print( '  toBDText: ' + _("Writing {!r}…").format( filepath ) )
            #outputBytes = json.dumps( bookIndexDict, ensure_ascii=False, indent=jsonIndent ).encode( 'utf-8' )
            #with open( filepath, 'wb' ) as jsonFile:
                #jsonFile.write( outputBytes )

            # Write the index list
            newBookIndexList = []
            for startC,startV,endC,endV,fileOffset,length in bookIndexList: # Convert strings to integers for the JSON index
                if startC=='I': startC = -1
                if endC=='I': endC = -1
                intStartC, intStartV = int( startC ), int( startV )
                intEndC, intEndV = int( endC ), int( endV )
                if intEndC==intStartC: newBookIndexList.append( (intStartC,intStartV, fileOffset,length, intEndV) )
                else: newBookIndexList.append( (intStartC,intStartV, fileOffset,length, intEndV,intEndC) )
            if C != 'I': # Check the index list
                #logger.info( f"_toBibleDoorText: Found {C!r} chapters in {BBB}" )
                numChapters = int(C)
                #logger.info( f"_toBibleDoorText: Found {numChapters!r} chapters in {BBB}" )
                if len(newBookIndexList) < numChapters: # something went wrong
                    logger.critical( f"_toBibleDoorText: Why did {BBB} ({'with' if haveSectionHeadingsForBook else 'without'} section headings) with {numChapters} chapters only have {len(newBookIndexList)} sections???" )
            # Write the index list
            #print( "index", bookIndex )
            filename = f'{BBB}.{BDDataFormatVersion}.bd.idx'
            filepath = os.path.join( bookOutputFolder, BibleOrgSysGlobals.makeSafeFilename( filename ) )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( '  toBDText: ' + _(f"Writing {filepath!r}…") )
            outputBytes = json.dumps( newBookIndexList, ensure_ascii=False, indent=jsonIndent ).encode( 'utf-8' )
            with open( filepath, 'wb' ) as jsonFile:
                jsonFile.write( outputBytes )

        if ignoredMarkers:
            logger.info( "_toBibleDoorText: Ignored markers were {}".format( ignoredMarkers ) )
            if BibleOrgSysGlobals.verbosityLevel > 2:
                print( "  " + _("WARNING: Ignored _toBibleDoorText markers were {}").format( ignoredMarkers ) )
        if unhandledMarkers:
            logger.error( f"_toBibleDoorText: Unhandled markers were {unhandledMarkers}" )
            if BibleOrgSysGlobals.verbosityLevel > 2:
                print( "  " + _(f"WARNING: Unhandled _toBibleDoorText markers were {unhandledMarkers}") )

        # Now create the bz2 file
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  BZipping BDText files…" )
        tar = tarfile.open( os.path.join( bookOutputFolder, 'AllBDTextFiles.bz2' ), 'w:bz2' )
        for filename in os.listdir( bookOutputFolder ):
            if filename.endswith( '.bd.txt' ) or filename.endswith( '.bd.idx' ):
                filepath = os.path.join( bookOutputFolder, filename )
                tar.add( filepath, arcname=filename, recursive=False )
        tar.close()

        if BibleOrgSysGlobals.verbosityLevel > 0 and BibleOrgSysGlobals.maxProcesses > 1:
            print( "  BibleWriter._toBibleDoorText finished successfully." )
        return True
    # end of BibleWriter._toBibleDoorText



    def _toBibleDoorJSONCHTML( self, outputFolderpath:Optional[Path]=None ) -> bool:
        """
        Write the now deprecated JSON and CHTML compressed HTML files used by the MS-Bible (Android) app.
        """
        import hashlib

        BDDataFormatVersion = 1 # Increment this when the data files / arrays change
        jsonIndent = 1 # Keep files small for small phones

        bookOutputFolderJSON = os.path.join( outputFolderpath, 'ByBook.{}.JSON/'.format( BDDataFormatVersion ) )
        if not os.access( bookOutputFolderJSON, os.F_OK ): os.makedirs( bookOutputFolderJSON ) # Make the empty folder if there wasn't already one there
        chapterOutputFolderJSON = os.path.join( outputFolderpath, 'ByChapter.{}.JSON/'.format( BDDataFormatVersion ) )
        if not os.access( chapterOutputFolderJSON, os.F_OK ): os.makedirs( chapterOutputFolderJSON ) # Make the empty folder if there wasn't already one there
        bookOutputFolderCHTML = os.path.join( outputFolderpath, 'BySection.{}.CHTML/'.format( BDDataFormatVersion ) )
        if not os.access( bookOutputFolderCHTML, os.F_OK ): os.makedirs( bookOutputFolderCHTML ) # Make the empty folder if there wasn't already one there
        bookOutputFolderZippedHTML = os.path.join( outputFolderpath, 'BySection.{}.HTML.zip/'.format( BDDataFormatVersion ) )
        if not os.access( bookOutputFolderZippedHTML, os.F_OK ): os.makedirs( bookOutputFolderZippedHTML ) # Make the empty folder if there wasn't already one there
        if BibleOrgSysGlobals.debugFlag: # Write HTML sections uncompressed in a separate folder (for debugging)
            debugBookOutputFolderHTML = os.path.join( outputFolderpath, 'BySection.{}.debug.HTML/'.format( BDDataFormatVersion ) )
            if not os.access( debugBookOutputFolderHTML, os.F_OK ): os.makedirs( debugBookOutputFolderHTML ) # Make the empty folder if there wasn't already one there

        headerFilename = 'BDHeader.json'
        headerFilepath = os.path.join( outputFolderpath, headerFilename )
        checksumFilepath = os.path.join( outputFolderpath, 'BDChecksums.{}.json'.format( BDDataFormatVersion ) )
        divisionNamesFilename = 'BDDivisionNames.{}.json'.format( BDDataFormatVersion )
        divisionNamesFilepath = os.path.join( outputFolderpath, divisionNamesFilename )
        bookNamesFilename = 'BDBookNames.{}.json'.format( BDDataFormatVersion )
        bookNamesFilepath = os.path.join( outputFolderpath, bookNamesFilename )
        compressionDictFilename = 'BDCmprnDict.{}.json'.format( BDDataFormatVersion )
        compressionDictFilepath = os.path.join( bookOutputFolderCHTML, compressionDictFilename )
        compressedIndexFilename = 'BD-BCV-CHTML-Index.{}.json'.format( BDDataFormatVersion )
        compressedIndexFilepath = os.path.join( bookOutputFolderCHTML, compressedIndexFilename )
        uncompressedIndexFilename = 'BD-BCV-ZHTML-Index.{}.json'.format( BDDataFormatVersion )
        uncompressedIndexFilepath = os.path.join( bookOutputFolderZippedHTML, uncompressedIndexFilename )
        destinationCHTMLFilenameTemplate = 'BDBook.{}.{}.chtml'.format( '{}', BDDataFormatVersion ) # Missing the BBB
        destinationCHTMLFilepathTemplate = os.path.join( bookOutputFolderCHTML, destinationCHTMLFilenameTemplate ) # Missing the BBB
        destinationZippedHTMLFilenameTemplate = 'BDBook.{}.{}.html'.format( '{}', BDDataFormatVersion ) # Missing the BBB
        destinationZippedHTMLFilepathTemplate = os.path.join( bookOutputFolderZippedHTML, destinationZippedHTMLFilenameTemplate+'.zip' ) # Missing the BBB
        if BibleOrgSysGlobals.debugFlag: # Write HTML sections uncompressed in a separate folder (for debugging)
            debugDestinationHTMLFilepathTemplate = os.path.join( debugBookOutputFolderHTML, 'BDBook.{}C{}V{}.{}.html'.format( '{}', '{}', '{}', BDDataFormatVersion ) ) # Missing the BBB, C, V

        checksums = {}
        ignoredMarkers, unhandledMarkers = set(), set()

        BDCompressions = (
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
        for shortString, longString in BDCompressions:
            usageCount[shortString] = 0
            if shortString in codeSet: # check for duplicates
                logger.critical( "Duplicate {!r} in compression dict".format( shortString ) )
                print( shortString, codeSet )
                halt
            codeSet.append( shortString )
            if longString in dataSet: # check for duplicates
                logger.critical( "Duplicate {!r} in compression dict".format( longString ) )
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
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print( "  Writing compression entries…" )
            #filepath = os.path.join( outputFolderpath, 'BDHeader.json' )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "    toBibleDoor " +  _("Exporting index to {}…").format( compressionDictFilepath ) )
            outputBytes = json.dumps( BDCompressions, ensure_ascii=False, indent=jsonIndent ).encode( 'utf-8' )
            with open( compressionDictFilepath, 'wb' ) as jsonFile:
                jsonFile.write( outputBytes )
            checksums[compressionDictFilename] = hashlib.md5(outputBytes).hexdigest()
            if BibleOrgSysGlobals.verbosityLevel > 2:
                print( "    {} compression entries written.".format( len(BDCompressions) ) )
        # end of _toBibleDoorJSONCHTML.writeCompressions


        bytesRaw = bytesCompressed = 0
        def compress( entry:str ) -> str:
            """
            entry is a string

            Returns a compressed string
                but has side-effects as updates the two above byte variables
            """
            nonlocal bytesRaw, bytesCompressed
            #print( '\nBDCompress', repr(entry) )
            #if C=='4': halt
            bytesRaw += len( entry.encode('UTF8') )
            result = entry
            if '@' in result:
                #print( 'have@', entry )
                result = result.replace( '@', '~~' )
                usageCount['~~'] += 1
            if '^' in result:
                print( 'have^', entry )
                halt # BibleDoor compression will fail!
            for longString, shortString in reversedCompressions:
                if longString in result:
                    result = result.replace( longString, shortString )
                    usageCount[shortString] += 1
            bytesCompressed += len( result.encode('UTF8') )
            return result
        # end of _toBibleDoorJSONCHTML.compress


        def decompress( entry:str ) -> str:
            """
            entry is a string

            Returns a decompressed string
            """
            #print( '\nBDDecompress', repr(entry) )
            result = entry
            for shortString, longString in BDCompressions:
                result = result.replace( shortString, longString )
            return result
        # end of _toBibleDoorJSONCHTML.decompress


        def writeBDHeader() -> None:
            """
            """
            headerDict = {}
            headerDict['Data format version'] = BDDataFormatVersion
            headerDict['Conversion date'] = datetime.today().strftime("%Y-%m-%d")
            headerDict['Conversion program'] = programNameVersion
            workTitle = self.getSetting( 'WorkTitle' )
            headerDict['Version name'] = workTitle if workTitle else self.name
            workAbbreviation = self.getSetting( 'WorkAbbreviation' )
            headerDict['Version abbreviation'] = workAbbreviation if workAbbreviation else self.abbreviation
            headerDict['Has section headings'] = haveAnySectionHeadings
            #print( headerDict )

            if BibleOrgSysGlobals.verbosityLevel > 2: print( "  " +  _("Exporting BD header to {}…").format( headerFilepath ) )
            outputBytes = json.dumps( headerDict, ensure_ascii=False, indent=jsonIndent ).encode( 'utf-8' )
            with open( headerFilepath, 'wb' ) as jsonFile:
                jsonFile.write( outputBytes )
            checksums[headerFilename] = hashlib.md5(outputBytes).hexdigest()
        # end of _toBibleDoorJSONCHTML.writeBDHeader


        def writeChecksums() -> None:
            """
            After we've written all the other files,
                we write a json dictionary/map of md5 checksums (written as 32 hex characters in a string)
            """
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "  " +  _("Exporting BD checksums to {}…").format( checksumFilepath ) )
            with open( checksumFilepath, 'wt', encoding='utf-8' ) as jsonFile:
                json.dump( checksums, jsonFile, ensure_ascii=False, indent=jsonIndent )
        # end of _toBibleDoorJSONCHTML.writeChecksums


        def writeBDBookNames() -> None:
            """
            Writes the two files:
                list of division names
                list of book names and abbreviations
            """
            def getDivisionName( BBB:str, doneAny=None, doneBooks=None ):
                """ Given a book code, return the division name. """
                result = ''
                if BibleOrgSysGlobals.loadedBibleBooksCodes.isOldTestament_NR( BBB ) or BBB == 'PS2':
                    result = self.getSetting( 'OldTestamentName' )
                    if not result: result = _("Old Testament")
                elif BibleOrgSysGlobals.loadedBibleBooksCodes.isNewTestament_NR( BBB ):
                    result = self.getSetting( 'NewTestamentName' )
                    if not result: result = _("New Testament")
                elif BibleOrgSysGlobals.loadedBibleBooksCodes.isDeuterocanon_NR( BBB ) or BBB in ('MA3','MA4'):
                    result = self.getSetting( 'DeuterocanonName' )
                    if not result: result = _("Deuterocanon")
                elif doneAny == False:
                    result = self.getSetting( 'FrontMatterName' )
                    if not result: result = _("Front Matter")
                elif doneBooks == True:
                    result = self.getSetting( 'BackMatterName' )
                    if not result: result = _("Back Matter")
                return result
            # end of writeBDBookNames.getDivisionName

            # Main code for _toBibleDoorJSONCHTML.writeBDBookNames
            # Make a list of division names and write them to a very small JSON file
            divisionData = []
            doneAny = doneBooks = False
            for BBB,bookObject in self.books.items():
                divisionName = getDivisionName( BBB, doneAny, doneBooks )
                if divisionName and divisionName not in divisionData:
                    divisionData.append( divisionName )
                if BibleOrgSysGlobals.loadedBibleBooksCodes.isOldTestament_NR(BBB) or BibleOrgSysGlobals.loadedBibleBooksCodes.isNewTestament_NR(BBB) or BibleOrgSysGlobals.loadedBibleBooksCodes.isDeuterocanon_NR(BBB):
                    doneAny = doneBooks = True
            #print( divisionData )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "  " + _("Exporting division names to {}…").format( divisionNamesFilepath ) )
            outputBytes = json.dumps( divisionData, ensure_ascii=False, indent=jsonIndent ).encode( 'utf-8' )
            with open( divisionNamesFilepath, 'wb' ) as jsonFile:
                jsonFile.write( outputBytes )
            checksums[divisionNamesFilename] = hashlib.md5(outputBytes).hexdigest()

            # Make a list of book data including names and abbreviations and write them to a JSON file
            bkData = []
            doneAny = doneBooks = False
            for BBB,bookObject in self.books.items():
                abbreviation = self.getBooknameAbbreviation( BBB )
                if not abbreviation: abbreviation = BBB
                shortName = self.getShortTOCName( BBB )
                longName = self.getAssumedBookName( BBB )
                if not shortName: shortName = longName
                if not longName: longName = shortName # to be safe
                divisionNumber = divisionData.index( getDivisionName( BBB, doneAny, doneBooks ) )
                #except: divisionNumber = -1
                numChapters = ''
                for dataLine in bookObject._processedLines:
                    if dataLine.getMarker() == 'c':
                        numChapters = dataLine.getCleanText()
                try: intNumChapters = int( numChapters )
                except ValueError:
                    logger.error( "toBibleDoor: no chapters in {}".format( BBB ) )
                    intNumChapters = 0
                bkData.append( (BBB,abbreviation,shortName,longName,intNumChapters,numSectionsDict[BBB],divisionNumber) )
                if BibleOrgSysGlobals.loadedBibleBooksCodes.isOldTestament_NR(BBB) or BibleOrgSysGlobals.loadedBibleBooksCodes.isNewTestament_NR(BBB) or BibleOrgSysGlobals.loadedBibleBooksCodes.isDeuterocanon_NR(BBB):
                    doneAny = doneBooks = True
            #print( bkData )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "  " + _("Exporting book names to {}…").format( bookNamesFilepath ) )
            outputBytes = json.dumps( bkData, ensure_ascii=False, indent=jsonIndent ).encode( 'utf-8' )
            with open( bookNamesFilepath, 'wb' ) as jsonFile:
                jsonFile.write( outputBytes )
            checksums[bookNamesFilename] = hashlib.md5(outputBytes).hexdigest()
        # end of _toBibleDoorJSONCHTML.writeBDBookNames


        def writeBDBookAsJSON( BBB:str, bookData ) -> None:
            """
            Creates json data files for the entire book in one folder,
                and for each chapter (for RAM challenged devices) in another folder.
            """
            def writeBDChapter( BBB:str, chapter:str, cData ) -> None:
                """
                """
                filepath = os.path.join( chapterOutputFolderJSON, '{}_{}.{}.json'.format( BBB, chapter, BDDataFormatVersion ) )
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "  " + _("Exporting {}_{} chapter to {}…").format( BBB, chapter, filepath ) )
                with open( filepath, 'wt', encoding='utf-8' ) as jsonFile:
                    json.dump( cData, jsonFile, ensure_ascii=False, indent=jsonIndent )
            # end of writeBDChapter

            outputData, chapterOutputData = [], []
            lastC = '0'
            for dataLine in bookData:
                marker, text, extras = dataLine.getMarker(), dataLine.getAdjustedText(), dataLine.getExtras()
                marker = marker.replace( '¬', '~' ) # Encodes cleaner in JSON
                if marker == 'c':
                    C = text
                    writeBDChapter( BBB, lastC, chapterOutputData ) # Write the previous chapter (if any)
                    chapterOutputData = [] # Start afresh
                    lastC = C
                extrasList = []
                if extras:
                    for extra in extras:
                        extrasList.append( (extra.getType(),extra.getIndex(),extra.getText()) )
                        #print( extra )
                if extrasList:
                    chapterOutputData.append( (marker,text,extrasList) )
                    outputData.append( (marker,text,extrasList) )
                elif text is None: # Try to keep filesizes down for mobile devices by omitting this often empty field
                    chapterOutputData.append( (marker,) )
                    outputData.append( (marker,) )
                else:
                    chapterOutputData.append( (marker,text) )
                    outputData.append( (marker,text) )
                #print( outputData )
            writeBDChapter( BBB, lastC, chapterOutputData ) # Write the last chapter

            filename = '{}.{}.json'.format( BBB, BDDataFormatVersion )
            filepath = os.path.join( bookOutputFolderJSON, filename )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "  " + _("Exporting {} book to {}…").format( BBB, filepath ) )
            outputBytes = json.dumps( outputData, ensure_ascii=False, indent=jsonIndent ).encode( 'utf-8' )
            with open( filepath, 'wb' ) as jsonFile:
                jsonFile.write( outputBytes )
            checksums[filename] = hashlib.md5(outputBytes).hexdigest()
        # end of _toBibleDoorJSONCHTML.writeBDBookAsJSON


        def writeBDBookAsHTML( BBB:str, bookData, currentUncompressedIndex, currentCompressedIndex ) -> None:
            """
            If the book has section headings, breaks it by section
                otherwise breaks the book by chapter.

            Returns the number of sections written.
            """
            numBDSections = 0
            BDGlobals = {}
            BDGlobals['nextFootnoteIndex'] = BDGlobals['nextEndnoteIndex'] = BDGlobals['nextXRefIndex'] = 0
            BDGlobals['footnoteHTML5'], BDGlobals['endnoteHTML5'], BDGlobals['xrefHTML5'] = [], [], []

            def handleBDSection( BCV, sectionHTML, outputCHTMLFile ) -> None:
                """
                First 3-tuple parameter contains BBB,C,V variables representing the first verse in this section.
                Next parameter is the HTML5 segment for the section

                XXXReturns the number of bytes written.
                """
                nonlocal numBDSections, BDHash, uncompressedFileOffset, compressedFileOffset
                #print( "  toBibleDoor.handleBDSection() {} haveAnySectionHeadings={}".format( BBB, haveAnySectionHeadings ) )
                assert BCV
                assert sectionHTML

                sectionBBB, sectionC, sectionV = BCV
                numBDSections += 1
                #if BBB == 'GLS': print( BBB, sectionHTML ); halt
                if '\\' in sectionHTML: # shouldn't happen
                    ix = sectionHTML.index( '\\' )
                    segment = sectionHTML[ix-10 if ix>10 else 0 : ix+30]
                    logger.error( "toBibleDoor programming error: unprocessed backslash code in {} {}:{} section: …{!r}…".format( sectionBBB, sectionC, sectionV, segment ) )
                    if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
                        print( "toBibleDoor: unprocessed backslash code in {} {}:{} section: …{!r}…".format( sectionBBB, sectionC, sectionV, segment ) )
                    if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
                HTMLSections.append( sectionHTML )
                indexEntry1 = sectionBCV[0],sectionBCV[1],sectionBCV[2],lastC,lastV,uncompressedFileOffset,len(sectionHTML)
                currentUncompressedIndex.append( indexEntry1 )
                uncompressedFileOffset += len(sectionHTML)

                compressedHTML = compress( sectionHTML )
                if BibleOrgSysGlobals.debugFlag: # Write this HTML section uncompressed in a separate folder (for debugging)
                    with open( debugDestinationHTMLFilepathTemplate.format( sectionBBB, sectionC, sectionV ), 'wt', encoding='utf-8' ) as debugOutputFile:
                        debugOutputFile.write( '<html><head>' \
                                               '<meta http-equiv="Content-Type" content="text/html;charset=utf-8">' \
                                               '<meta name="viewport" content="width=device-width, initial-scale=1.0">' \
                                               '<link rel="stylesheet" type="text/css" href="BibleBook.css">' \
                                               '<title>Bible Section</title></head><body>' \
                                            + sectionHTML + '</body></html>' )
                    checkHTML = decompress( compressedHTML )
                    if checkHTML != sectionHTML:
                        print( "\noriginal: {} {!r}".format( len(sectionHTML), sectionHTML ) )
                        print( "\ndecompressed: {} {!r}".format( len(checkHTML), checkHTML ) )
                        for ix in range( min( len(sectionHTML), len(checkHTML) ) ):
                            if checkHTML[ix] != sectionHTML[ix]:
                                if ix > 10: print( '\n', repr(sectionHTML[ix-10:ix+2]), '\n', repr(checkHTML[ix-10:ix+2]) )
                                print( ix, repr(sectionHTML[ix]), repr(checkHTML[ix]) ); break
                        halt
                    #compressedHTML = sectionHTML # Leave it uncompressed so we can easily look at it
                    compressedHTML += '\n'
                bytesToWrite = compressedHTML.encode('UTF8')
                BDHash.update( bytesToWrite )
                numBytesWritten = outputCHTMLFile.write( bytesToWrite )
                #return numBytesWritten
                indexEntry2 = sectionBCV[0],sectionBCV[1],sectionBCV[2],lastC,lastV,compressedFileOffset,numBytesWritten
                currentCompressedIndex.append( indexEntry2 )
                compressedFileOffset += numBytesWritten
            # end of writeBDBookAsHTML.handleBDSection


            # Main code for _toBibleDoorJSONCHTML.writeBDBookAsHTML
            HTMLSections = []
            chtmlFile = open( destinationCHTMLFilepathTemplate.format( BBB ), 'wb' ) # Note: binary not text
            uncompressedFileOffset = compressedFileOffset = 0
            BDHash = hashlib.md5()

            lastHTML = sectionHTML = outputHTML = ''
            lastMarker = gotVP = None
            C, V = '-1', '-1' # So first/id line starts at -1:0
            lastC, lastV = '0', '999' # For introduction section
            overallChapterLabel = None
            sOpen = sJustOpened = pOpen = vOpen = tableOpen = False
            listOpen = {}
            sectionBCV = (BBB,'0','0')
            for dataLine in bookData:
                thisHTML = ''
                marker, text, extras = dataLine.getMarker(), dataLine.getAdjustedText(), dataLine.getExtras()
                #print( " toBD: {} {}:{} {}:{!r}".format( BBB, C, V, marker, text ) )
                #print( "   sectionBCV", sectionBCV )
                if '¬' in marker or marker in BOS_ADDED_NESTING_MARKERS or marker in ('usfm','v='):
                    continue # Just ignore added markers — not needed here
                if marker in USFM_PRECHAPTER_MARKERS:
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
                        assert C=='-1' or marker=='rem' or marker.startswith('mte')
                    V = str( int(V) + 1 )

                # Markers usually only found in the introduction
                if marker in OFTEN_IGNORED_USFM_HEADER_MARKERS or marker in ('ie','v='): # Just ignore these lines
                    ignoredMarkers.add( marker )
                elif marker in ('mt1','mt2','mt3','mt4', 'imt1','imt2','imt3','imt4',):
                    if pOpen:
                        logger.warning( "toBibleDoor: didn't expect {} field with paragraph still open at {} {}:{}".format( marker, BBB, C, V ) )
                        thisHTML += '</p>'; pOpen = False
                        if BibleOrgSysGlobals.debugFlag: thisHTML += '\n'
                    if not sOpen:
                        thisHTML += '<section class="introSection">'
                        sOpen = sJustOpened = True
                        sectionBCV = (BBB,C,V)
                    tClass = 'mainTitle' if marker in ('mt1','mt2','mt3','mt4',) else 'introductionMainTitle'
                    thisHTML += '<h1 class="{}{}">{}</h1>'.format( tClass, marker[2], text )
                elif marker in ('is1','is2','is3','is4',):
                    if pOpen:
                        logger.warning( "toBibleDoor: didn't expect {} field with paragraph still open at {} {}:{}".format( marker, BBB, C, V ) )
                        thisHTML += '</p>'; pOpen = False
                        if BibleOrgSysGlobals.debugFlag: thisHTML += '\n'
                    if BBB == 'FRT' and marker == 'is1':
                        if sOpen: lastHTML += '</section>'; sOpen = False
                        if lastHTML or sectionHTML:
                            sectionHTML += lastHTML
                            lastHTML = ''
                            handleBDSection( sectionBCV, sectionHTML, chtmlFile )
                            sectionHTML = ''
                            #indexEntry = sectionBCV[0],sectionBCV[1],sectionBCV[2],lastC,lastV,compressedFileOffset,bytesWritten
                            #currentCompressedIndex.append( indexEntry )
                            #compressedFileOffset += bytesWritten
                    if not sOpen:
                        thisHTML += '<section class="introSection">'
                        sOpen = sJustOpened = True
                        sectionBCV = (BBB,C,V)
                    thisHTML += '<h2 class="introductionSectionHeading{}">{}</h2>'.format( marker[2], text )
                elif marker in ('ip','ipi','ipq','ipr', 'im','imi','imq', 'iq1','iq2','iq3','iq4', 'iex', ):
                    for lx in ('4','3','2','1'): # Close any open lists
                        if listOpen and lx in listOpen and listOpen[lx]: thisHTML += '</p>'; del listOpen[lx]
                    if pOpen:
                        logger.warning( "toBibleDoor: didn't expect {} field with paragraph still open at {} {}:{}".format( marker, BBB, C, V ) )
                        thisHTML += '</p>'; pOpen = False
                        if BibleOrgSysGlobals.debugFlag: thisHTML += '\n'
                    if not sOpen:
                        thisHTML += '<section class="introSection">'
                        sOpen = sJustOpened = True
                        sectionBCV = (BBB,C,V)
                    #if not text and not extras: print( "{} at {} {}:{} has nothing!".format( marker, BBB, C, V ) );halt
                    if text or extras:
                        thisHTML += '<p class="{}">{}</p>'.format( ipHTMLClassDict[marker], BibleWriter.__formatHTMLVerseText( BBB, C, V, text, extras, BDGlobals ) )
                elif marker == 'iot':
                    if pOpen:
                        logger.warning( "toBibleDoor: didn't expect {} field with paragraph still open at {} {}:{}".format( marker, BBB, C, V ) )
                        thisHTML += '</p>'; pOpen = False
                        if BibleOrgSysGlobals.debugFlag: thisHTML += '\n'
                    if not sOpen:
                        thisHTML += '<section class="introSection">'
                        sOpen = sJustOpened = True
                        sectionBCV = (BBB,C,V)
                    thisHTML += '<h3 class="outlineTitle">{}</h3>'.format( text )
                elif marker in ('io1','io2','io3','io4',):
                    if pOpen:
                        logger.warning( "toBibleDoor: didn't expect {} field with paragraph still open at {} {}:{}".format( marker, BBB, C, V ) )
                        thisHTML += '</p>'; pOpen = False
                        if BibleOrgSysGlobals.debugFlag: thisHTML += '\n'
                    if not sOpen:
                        thisHTML += '<section class="introSection">'
                        sOpen = sJustOpened = True
                        sectionBCV = (BBB,C,V)
                    if text or extras:
                        thisHTML += '<p class="introductionOutlineEntry{}">{}</p>'.format( marker[2], BibleWriter.__formatHTMLVerseText( BBB, C, V, text, extras, BDGlobals ) )
                elif marker == 'ib':
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not text and not extras
                    thisHTML += '<p class="introductionBlankParagraph"></p>'
                elif marker == 'periph':
                    if pOpen:
                        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert sOpen
                        thisHTML += '</p>'; pOpen = False
                        if BibleOrgSysGlobals.debugFlag: thisHTML += '\n'
                    if BibleOrgSysGlobals.debugFlag:
                        assert BBB in ('FRT','INT','BAK','OTH',)
                        assert text and not extras
                    thisHTML += '<p class="peripheralContent">{}</p>'.format( text )
                elif marker in ('mte1','mte2','mte3','mte4', 'imte1','imte2','imte3','imte4',):
                    if pOpen:
                        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert sOpen
                        thisHTML += '</p>'; pOpen = False
                        if BibleOrgSysGlobals.debugFlag: thisHTML += '\n'
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert sOpen
                    thisHTML += '<h1 class="endTitle{}">{}</h1>'.format( marker[3], text )

                # Now markers in the main text
                elif marker == 'c':
                    if vOpen: lastHTML += '</span>'; vOpen = False
                    #if extras: print( "have extras at c at",BBB,C); halt
                    C, V = text, '0'
                    chapterLabel = None
                    if not haveAnySectionHeadings: # Treat each chapter as a new section
                        if pOpen: lastHTML += '</p>'; pOpen = False
                        if sOpen: lastHTML += '</section>'; sOpen = False
                        if lastHTML or sectionHTML:
                            sectionHTML += lastHTML
                            lastHTML = ''
                            handleBDSection( sectionBCV, sectionHTML, chtmlFile )
                            sectionHTML = ''
                            #indexEntry = sectionBCV[0],sectionBCV[1],sectionBCV[2],lastC,lastV,compressedFileOffset,bytesWritten
                            #currentCompressedIndex.append( indexEntry )
                            #compressedFileOffset += bytesWritten
                        thisHTML += '<section class="chapterSection">'
                        sOpen = sJustOpened = True
                        sectionBCV = (BBB,C,V)
                    elif C=='1': # Must be the end of the introduction — so close that section
                        if pOpen: lastHTML += '</p>'; pOpen = False
                        if sOpen: lastHTML += '</section>'; sOpen = False
                    # What should we put in here — we don't need/want to display it, but it's a place to jump to
                    # NOTE: If we include the next line, it usually goes at the end of a section where it's no use
                    if overallChapterLabel is not None: # a general chapter label for this book
                        thisHTML += '<p class="chapterLabel" id="{}">{} {}</p>'.format( 'CT'+C, overallChapterLabel, C )
                    else: # must be an ordinary chapter number
                        thisHTML += '<span class="chapterStart" id="{}"></span>'.format( 'CT'+C )
                elif marker == 'cp': # ignore this for now
                    ignoredMarkers.add( marker )
                elif marker == 'cl': # a specific chapter label for this chapter
                    chapterLabel = text
                    thisHTML += '<p class="chapterLabel" id="{}">{}</p>'.format( 'CS'+C, chapterLabel )
                elif marker == 'c#':
                    #if extras: print( "have extras at c# at",BBB,C); halt
                    if chapterLabel is None and overallChapterLabel is None: # must be an ordinary chapter number
                        thisHTML += '<span class="chapterNumber" id="{}">{}</span>'.format( 'CS'+C, text )
                        #thisHTML += '<span class="chapterNumber">{}</span>'.format( text )
                        thisHTML += '<span class="chapterNumberPostspace">&nbsp;</span>'
                elif marker == 'vp#': # This precedes a v field and has the verse number to be printed
                    gotVP = text # Just remember it for now
                elif marker == 'v':
                    if vOpen: lastHTML += '</span>'; vOpen = False
                    V = text
                    if gotVP: # this is a replacement verse number for publishing
                        text = gotVP
                        gotVP = None
                    if sJustOpened: sectionBCV = (BBB,C,V)
                    thisHTML += '<span class="verse" id="{}">'.format( 'C'+C+'V'+V ); vOpen = True
                    if V == '1': # Different treatment for verse 1
                        if not sectionBCV:
                            sectionBCV = (BBB,C,V) # Normally a section heading would have caused sectionBCV to be set
                        thisHTML += '<span class="verseOnePrespace"> </span>'
                        thisHTML += '<span class="verseOneNumber">{}</span>'.format( text )
                        thisHTML += '<span class="verseOnePostspace">&nbsp;</span>'
                    else: # not verse one
                        thisHTML += '<span class="verseNumberPrespace"> </span>'
                        thisHTML += '<span class="verseNumber">{}</span>'.format( text )
                        thisHTML += '<span class="verseNumberPostspace">&nbsp;</span>'
                    sJustOpened = False
                    lastC, lastV = C, V

                elif marker in ('ms1','ms2','ms3','ms4',):
                    if vOpen: lastHTML += '</span>'; vOpen = False
                    if pOpen: lastHTML += '</p>'; pOpen = False
                    if sOpen: lastHTML += '</section>'; sOpen = False
                    if lastHTML or sectionHTML:
                        sectionHTML += lastHTML
                        lastHTML = ''
                        handleBDSection( sectionBCV, sectionHTML, chtmlFile )
                        sectionHTML = ''
                        #indexEntry = sectionBCV[0],sectionBCV[1],sectionBCV[2],lastC,lastV,compressedFileOffset,bytesWritten
                        #currentCompressedIndex.append( indexEntry )
                        #compressedFileOffset += bytesWritten
                    thisHTML += '<h2 class="majorSectionHeading{}">{}</h2>'.format( marker[2], text )
                elif marker in ('s1','s2','s3','s4'):
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert haveAnySectionHeadings
                    if vOpen: lastHTML += '</span>'; vOpen = False
                    if marker == 's1':
                        if pOpen: lastHTML += '</p>'; pOpen = False
                        if sOpen: lastHTML += '</section>'; sOpen = False
                        if lastHTML or sectionHTML:
                            sectionHTML += lastHTML
                            lastHTML = ''
                            handleBDSection( sectionBCV, sectionHTML, chtmlFile )
                            sectionHTML = ''
                            #indexEntry = sectionBCV[0],sectionBCV[1],sectionBCV[2],lastC,lastV,compressedFileOffset,bytesWritten
                            #currentCompressedIndex.append( indexEntry )
                            #compressedFileOffset += bytesWritten
                        thisHTML += '<section class="regularSection">'
                        sOpen = sJustOpened = True
                        sectionBCV = (BBB,C,V)
                    if text or extras:
                        thisHTML += '<h3 class="sectionHeading{}">{}</h3>'.format( marker[1], BibleWriter.__formatHTMLVerseText( BBB, C, V, text, extras, BDGlobals ) )
                        if BibleOrgSysGlobals.debugFlag: thisHTML += '\n'
                elif marker in ('r', 'sr', 'mr',):
                    if BibleOrgSysGlobals.strictCheckingFlag and (debuggingThisModule or BibleOrgSysGlobals.debugFlag): assert not vOpen
                    if vOpen: lastHTML += '</span>'; vOpen = False
                    if pOpen: lastHTML += '</p>'; pOpen = False
                    if not sOpen:
                        logger.warning( "toBibleDoor: Have {} section reference {} outside a section in {} {}:{}".format( marker, text, BBB, C, V ) )
                        thisHTML += '<section class="regularSection">'
                        sOpen = sJustOpened = True
                        sectionBCV = (BBB,C,V)
                    if marker == 'r': rClass = 'sectionCrossReference'
                    elif marker == 'sr': rClass = 'sectionReferenceRange'
                    elif marker == 'mr': rClass = 'majorSectionReferenceRange'
                    thisHTML += '<p class="{}">{}</p>'.format( rClass, text )
                elif marker == 'd': # descriptive title or Hebrew subtitle
                    if text or extras:
                        thisHTML = '<p class="descriptiveTitle">{}</p>'.format( BibleWriter.__formatHTMLVerseText( BBB, C, V, text, extras, BDGlobals ) )
                elif marker == 'sp': # speaker
                    thisHTML = '<p class="speaker">{}</p>'.format( text )

                elif marker in ('p','m','pmo','pm','pmc','pmr','pi1','pi2','pi3','pi4','mi','cls','pc','pr','ph1','ph2','ph3','ph4',) \
                or marker in ('q1','q2','q3','q4','qr','qc','qm1','qm2','qm3','qm4',):
                    for lx in ('4','3','2','1'): # Close any open lists
                        if listOpen and lx in listOpen and listOpen[lx]: thisHTML += '</p>'; del listOpen[lx]
                    if vOpen: lastHTML += '</span>'; vOpen = False
                    if tableOpen: lastHTML += '</table>'; tableOpen = False
                    if pOpen:
                        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert sOpen
                        thisHTML += '</p>'; pOpen = False
                        if BibleOrgSysGlobals.debugFlag: thisHTML += '\n'
                    elif not sOpen:
                        if lastHTML or sectionHTML:
                            sectionHTML += lastHTML
                            lastHTML = ''
                            handleBDSection( sectionBCV, sectionHTML, chtmlFile )
                            sectionHTML = ''
                            #indexEntry = sectionBCV[0],sectionBCV[1],sectionBCV[2],lastC,lastV,compressedFileOffset,bytesWritten
                            #currentCompressedIndex.append( indexEntry )
                            #compressedFileOffset += bytesWritten
                            sectionBCV = (BBB,C,V)
                        thisHTML += '<section class="regularSection">'
                        sOpen = sJustOpened = True
                        sectionBCV = (BBB,C,V)
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not text
                    thisHTML += '<p class="{}">'.format( pqHTMLClassDict[marker] )
                    pOpen = True
                elif marker in ('v~','p~',):
                    #if BibleOrgSysGlobals.debugFlag and marker=='v~': assert vOpen
                    if text or extras:
                        if not vOpen:
                            thisHTML += '<span class="verse" id="{}">'.format( 'C'+C+'V'+V+'b' ); vOpen = True
                        thisHTML += '<span class="verseText">{}</span>'.format( BibleWriter.__formatHTMLVerseText( BBB, C, V, text, extras, BDGlobals ) )
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
                        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not text
                        thisHTML += '<span class="{}">'.format( iClass )
                    elif text: thisHTML += '<span class="{}">{}</span>'.format( iClass, BibleWriter.__formatHTMLVerseText( BBB, C, V, text, extras, BDGlobals ) )
                    sJustOpened = False
                elif marker == 'tr':
                    if vOpen: lastHTML += '</span>'; vOpen = False
                    if pOpen:
                        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert sOpen
                        thisHTML += '</p>'; pOpen = False
                        if BibleOrgSysGlobals.debugFlag: thisHTML += '\n'
                    if not tableOpen:
                        thisHTML += '<table>'; tableOpen = True
                    # TODO: Finish this e.g., '\th1 Me kabuhalan \th2 Me pangulu \tc3 Kasuluhan' '\tc1 Huda \tc2 Naasun \tc3 74,600'
                    thisHTML += f'<tr><tc>{text}</tc></tr>'
                elif marker == 'b':
                    if vOpen: lastHTML += '</span>'; vOpen = False
                    if tableOpen: lastHTML += '</table>'; tableOpen = False
                    if pOpen:
                        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert sOpen
                        thisHTML += '</p>'; pOpen = False
                        if BibleOrgSysGlobals.debugFlag: thisHTML += '\n'
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not text and not extras
                    thisHTML += '<p class="blankParagraph"></p>'

                elif marker in ('nb','cl',): # These are the markers that we can safely ignore for this export
                    if (BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag) and marker=='nb':
                        assert not text and not extras
                else:
                    if text:
                        logger.critical( f"toBibleDoor: {self.abbreviation} lost text in '{marker}' field in {BBB} {C}:{V} '{text}'" )
                        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
                    if extras:
                        logger.critical( "toBibleDoor: {} lost extras in {} field in {} {}:{}".format( self.abbreviation, marker, BBB, C, V ) )
                        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
                    unhandledMarkers.add( marker )
                if extras and marker not in ('v~','p~','s1','s2','s3','s4','d', 'ip','ipi','ipq','ipr', 'im','imi','imq', 'iq1','iq2','iq3','iq4', 'iex',):
                    logger.critical( "toBibleDoor: extras not handled for {} at {} {}:{}".format( marker, BBB, C, V ) )
                    if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt

                sectionHTML += lastHTML
                lastMarker, lastHTML = marker, thisHTML

            for lx in ('4','3','2','1'): # Close any open lists
                if listOpen and lx in listOpen and listOpen[lx]: lastHTML += '</p>'; del listOpen[lx]
            if vOpen: lastHTML += '</span>'
            if pOpen: lastHTML += '</p>'
            if sOpen: lastHTML += '</section>'
            sectionHTML += lastHTML
            if sectionHTML:
                handleBDSection( sectionBCV, sectionHTML, chtmlFile )
                #indexEntry = sectionBCV[0],sectionBCV[1],sectionBCV[2],lastC,lastV,compressedFileOffset,bytesWritten
                #currentCompressedIndex.append( indexEntry )

            chtmlFile.close()
            checksums[destinationCHTMLFilenameTemplate.format( BBB )] = BDHash.hexdigest()

            # Write the zipped version
            completeHTMLString = ''
            for sectionHTML in HTMLSections:
                completeHTMLString += sectionHTML
            filename = destinationZippedHTMLFilenameTemplate.format( BBB )
            filepath = destinationZippedHTMLFilepathTemplate.format( BBB )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Zipping {} HTML file…".format( filename ) )
            zf = zipfile.ZipFile( filepath, 'w', compression=zipfile.ZIP_DEFLATED )
            zf.writestr( filename, completeHTMLString )
            zf.close()

            return numBDSections
            #if BibleOrgSysGlobals.verbosityLevel > 2 or BibleOrgSysGlobals.debugFlag:
                #for key,count in usageCount.items():
                    #if count == 0: logger.error( "Compression code {} is unused".format( key ) )
                    #elif count < 20: logger.warning( "Compression code {} is rarely used".format( key ) )
                    #elif count < 100: logger.warning( "Compression code {} is under-used".format( key ) )

                #if bytesRaw and BibleOrgSysGlobals.verbosityLevel > 2:
                    #print( "  {} compression ratio: {}".format( BBB, round( bytesCompressed / bytesRaw, 3 ) ) )
                    #if BibleOrgSysGlobals.verbosityLevel > 2:
                        #print( "    {} raw bytes: {}".format( BBB, bytesRaw ) )
                        #print( "    {} compressed bytes: {}".format( BBB, bytesCompressed ) )
            #if BibleOrgSysGlobals.debugFlag: print( "Finished", BBB ); halt
        # end of _toBibleDoorJSONCHTML.writeBDBookAsHTML


        # Start of main code for _toBibleDoorJSONCHTML
        try: haveAnySectionHeadings = True if self.discoveryResults['ALL']['haveSectionHeadings']>0 else False
        except AttributeError: haveAnySectionHeadings = False
        #print( haveAnySectionHeadings, BBB ) #, self.discoveryResults[BBB] )
        writeBDHeader()

        # Write the books
        uncompressedHTMLIndex, compressedHTMLIndex = [], []
        numSectionsDict = {}
        for BBB,bookObject in self.books.items():
            internalBibleBookData = bookObject._processedLines
            writeBDBookAsJSON( BBB, internalBibleBookData )
            numSections = writeBDBookAsHTML( BBB, internalBibleBookData, uncompressedHTMLIndex, compressedHTMLIndex )
            numSectionsDict[BBB] = numSections

        writeBDBookNames()

        if uncompressedHTMLIndex: # Sort the main uncompressed index and write it
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print( "  Fixing and writing main uncompressed index…" )

            def toInt( CVstring ):
                try: return int( CVstring )
                except ValueError:
                    #if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert CVstring
                    newCV = '0'
                    for char in CVstring:
                        if char.isdigit(): newCV += char
                        else: break
                    return int( newCV )
            # end of toInt

            newHTMLIndex = []
            for B,C1,V1,C2,V2,fO,rL in uncompressedHTMLIndex: # Convert strings to integers for the JSON index
                intC1, intC2 = toInt( C1 ), toInt( C2 )
                intV1, intV2 = toInt( V1 ), toInt( V2 )
                newHTMLIndex.append( (B,intC1,intV1,intC2,intV2,fO,rL) )
            #compressedHTMLIndex = sorted(compressedHTMLIndex)
            #print( "    toBibleDoor: {} index entries created.".format( len(newHTMLIndex) ) )
            #filepath = os.path.join( outputFolderpath, 'BDHeader.json' )
            if BibleOrgSysGlobals.verbosityLevel > 2:
                print( "    toBibleDoor: " +  _("Exporting uncompressed index to {}…").format( uncompressedIndexFilepath ) )
            outputBytes = json.dumps( newHTMLIndex, ensure_ascii=False, indent=jsonIndent ).encode( 'utf-8' )
            with open( uncompressedIndexFilepath, 'wb' ) as jsonFile:
                jsonFile.write( outputBytes )
            checksums[uncompressedIndexFilename] = hashlib.md5(outputBytes).hexdigest()

        if compressedHTMLIndex: # Sort the main uncompressed index and write it
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print( "  Fixing and writing main compressed index…" )

            def toInt( CVstring ):
                try: return int( CVstring )
                except ValueError:
                    #if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert CVstring
                    newCV = '0'
                    for char in CVstring:
                        if char.isdigit(): newCV += char
                        else: break
                    return int( newCV )
            # end of toInt

            newHTMLIndex = []
            for B,C1,V1,C2,V2,fO,rL in compressedHTMLIndex: # Convert strings to integers for the JSON index
                intC1, intC2 = toInt( C1 ), toInt( C2 )
                intV1, intV2 = toInt( V1 ), toInt( V2 )
                newHTMLIndex.append( (B,intC1,intV1,intC2,intV2,fO,rL) )
            #compressedHTMLIndex = sorted(compressedHTMLIndex)
            #print( "    toBibleDoor: {} index entries created.".format( len(newHTMLIndex) ) )
            #filepath = os.path.join( outputFolderpath, 'BDHeader.json' )
            if BibleOrgSysGlobals.verbosityLevel > 2:
                print( "    toBibleDoor: " +  _("Exporting compressed index to {}…").format( compressedIndexFilepath ) )
            outputBytes = json.dumps( newHTMLIndex, ensure_ascii=False, indent=jsonIndent ).encode( 'utf-8' )
            with open( compressedIndexFilepath, 'wb' ) as jsonFile:
                jsonFile.write( outputBytes )
            checksums[compressedIndexFilename] = hashlib.md5(outputBytes).hexdigest()
            writeCompressions()

        writeChecksums()

        if ignoredMarkers:
            logger.info( "toBibleDoor: Ignored markers were {}".format( ignoredMarkers ) )
            if BibleOrgSysGlobals.verbosityLevel > 2:
                print( "  " + _("WARNING: Ignored toBibleDoor markers were {}").format( ignoredMarkers ) )
        if unhandledMarkers:
            logger.warning( "toBibleDoor: Unhandled markers were {}".format( unhandledMarkers ) )
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print( "  " + _("WARNING: Unhandled toBibleDoor markers were {}").format( unhandledMarkers ) )

        # Display compression info
        if BibleOrgSysGlobals.verbosityLevel > 2 or BibleOrgSysGlobals.debugFlag:
            for key,count in usageCount.items():
                if count == 0: logger.error( "Compression code {} is unused".format( key ) )
                elif count < 20: logger.warning( "Compression code {} is rarely used".format( key ) )
                elif count < 100: logger.warning( "Compression code {} is under-used".format( key ) )
            if bytesRaw and BibleOrgSysGlobals.verbosityLevel > 2:
                print( "  Compression ratio: {}".format( round( bytesCompressed / bytesRaw, 3 ) ) )
                if BibleOrgSysGlobals.verbosityLevel > 2:
                    print( f"    Raw bytes: {bytesRaw:,}" )
                    print( f"    Compressed bytes: {bytesCompressed:,}" )

        ## Now create a zipped collection
        #if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Zipping BibleDoor files…" )
        #zf = zipfile.ZipFile( os.path.join( outputFolderpath, 'AllBDUSFMFiles.zip' ), 'w', compression=zipfile.ZIP_DEFLATED )
        #for filename in os.listdir( outputFolderpath ):
            #if not filename.endswith( '.zip' ):
                #filepath = os.path.join( outputFolderpath, filename )
                #zf.write( filepath, filename ) # Save in the archive without the path
        #zf.close()
    # end of BibleWriter_toBibleDoorJSONCHTML


    def toBibleDoor( self, outputFolderpath:Optional[Path]=None, removeVerseBridges:bool=False ) -> bool:
        """
        Adjust the pseudo USFM and write the customized USFM files for the BibleDoor (Android) app.
        """
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Running BibleWriter:toBibleDoor…" )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert self.books

        if not self.doneSetupGeneric: self.__setupWriter()
        if 'discoveryResults' not in self.__dict__: self.discover()
        if not outputFolderpath: outputFolderpath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_BibleDoor_' + ('Reexport/' if self.objectTypeString=='BibleDoor' else 'Export/') )
        if not os.access( outputFolderpath, os.F_OK ): os.makedirs( outputFolderpath ) # Make the empty folder if there wasn't already one there
        #if not controlDict: controlDict = {}; ControlFiles.readControlFile( 'ControlFiles', 'To_XXX_controls.txt', controlDict )
        #assert controlDict and isinstance( controlDict, dict )

        self._toBibleDoorJSONCHTML( outputFolderpath ) # Do the older JSON and compressed HTML outputs (used by the MS-Bible app)
        self._toBibleDoorText( outputFolderpath ) # Do our newer customised text outputs (used by the BibleDoor app)

        if BibleOrgSysGlobals.verbosityLevel > 0 and BibleOrgSysGlobals.maxProcesses > 1:
            print( "  BibleWriter.toBibleDoor finished successfully." )
        return True
    # end of BibleWriter.toBibleDoor



    def toEasyWorshipBible( self, outputFolderpath:Optional[Path]=None ) -> bool:
        """
        Write the pseudo USFM out into the compressed EasyWorship format.

        Since we don't have a specification for the format,
            and since we don't know the meaning of all the binary pieces of the file,
            we can't be certain yet that this output will actually work. :-(
        """
        from BibleOrgSys.Formats.EasyWorshipBible import createEasyWorshipBible

        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Running BibleWriter:toEasyWorshipBible…" )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert self.books

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolderpath: outputFolderpath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_EasyWorshipBible_Export/' )
        if not os.access( outputFolderpath, os.F_OK ): os.makedirs( outputFolderpath ) # Make the empty folder if there wasn't already one there

        return createEasyWorshipBible( self, outputFolderpath )
    # end of BibleWriter.toEasyWorshipBible



    def toUSX2XML( self, outputFolderpath:Optional[Path]=None, controlDict=None, validationSchema=None ):
        """
        Using settings from the given control file,
            converts the USFM information to UTF-8 USX XML files.

        If a schema is given (either a path or URL), the XML output files are validated.
        """
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Running BibleWriter:toUSX2XML…" )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert self.books

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolderpath: outputFolderpath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_USX2_Export/' )
        #if not os.access( outputFolderpath, os.F_OK ): os.makedirs( outputFolderpath ) # Make the empty folder if there wasn't already one there
        filesFolder = os.path.join( outputFolderpath, 'USX2Files/' )
        if not os.access( filesFolder, os.F_OK ): os.makedirs( filesFolder ) # Make the empty folder if there wasn't already one there
        if not controlDict:
            controlDict, defaultControlFilename = {}, "To_USX_controls.txt"
            try: ControlFiles.readControlFile( defaultControlFolderpath, defaultControlFilename, controlDict )
            except FileNotFoundError:
                logger.critical( "Unable to read control dict {} from {}".format( defaultControlFilename, defaultControlFolderpath ) )
        self.__adjustControlDict( controlDict )
        if not validationSchema: # We'll use our copy
            rncFilepath = 'ExternalSchemas/DerivedFiles/usx_2.6.rng'
            if os.path.exists( rncFilepath ): validationSchema = rncFilepath

        ignoredMarkers, unhandledMarkers, unhandledBooks = set(), set(), []

        def writeUSXBook( BBB, bkData ):
            """ Writes a book to the filesFolder. """

            def handleInternalTextMarkersForUSX2( originalText ):
                """
                Handles character formatting markers within the originalText.
                Tries to find pairs of markers and replaces them with html char segments.
                """
                if not originalText: return ''
                if '\\' not in originalText: return originalText
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( "toUSX2XML:hITM4USX:", BBB, C, V, marker, "'"+originalText+"'" )
                markerList = sorted( BibleOrgSysGlobals.loadedUSFMMarkers.getMarkerListFromText( originalText ),
                                            key=lambda s: -len(s[4])) # Sort by longest characterContext first (maximum nesting)
                for insideMarker, iMIndex, nextSignificantChar, fullMarker, characterContext, endIndex, markerField in markerList: # check for internal markers
                    pass

                # Old code
                adjText = originalText
                haveOpenChar = False
                for charMarker in ALL_CHAR_MARKERS:
                    #print( "handleInternalTextMarkersForUSX2", charMarker )
                    # Handle USFM character markers
                    fullCharMarker = '\\' + charMarker + ' '
                    if fullCharMarker in adjText:
                        if haveOpenChar:
                            adjText = adjText.replace( 'CLOSED_BIT', ' closed="false"' ) # Fix up closed bit since it wasn't closed
                            logger.info( "toUSX2XML: USX export had to close automatically in {} {}:{} {}:{!r} now {!r}".format( BBB, C, V, marker, originalText, adjText ) ) # The last marker presumably only had optional closing (or else we just messed up nesting markers)
                        adjText = adjText.replace( fullCharMarker, f'{"</char>" if haveOpenChar else ""}<char style="{charMarker}"CLOSED_BIT>' )
                        haveOpenChar = True
                    endCharMarker = '\\' + charMarker + '*'
                    if endCharMarker in adjText:
                        if not haveOpenChar: # Then we must have a missing open marker (or extra closing marker)
                            logger.error( "toUSX2XML: Ignored extra {!r} closing marker in {} {}:{} {}:{!r} now {!r}".format( charMarker, BBB, C, V, marker, originalText, adjText ) )
                            adjText = adjText.replace( endCharMarker, '' ) # Remove the unused marker
                        else: # looks good
                            adjText = adjText.replace( 'CLOSED_BIT', '' ) # Fix up closed bit since it was specifically closed
                            adjText = adjText.replace( endCharMarker, '</char>' )
                            haveOpenChar = False
                if '\\z' in adjText:
                    # Handle custom (character) markers
                    while True:
                        matchOpen = re.search( r'\\z([\w\d]+?) ', adjText )
                        if not matchOpen: break
                        #print( f"Matched custom marker open '{matchOpen.group(0)}'" )
                        adjText = adjText[:matchOpen.start(0)] + f'<char style="z{matchOpen.group(1)}"CLOSED_BIT>' + adjText[matchOpen.end(0):]
                        haveOpenChar = True
                        #print( "adjText", adjText )
                        matchClose = re.search( r'\\z{}\*'.format( matchOpen.group(1) ), adjText )
                        if matchClose:
                            #print( f"Matched custom marker close '{matchClose.group(0)}'" )
                            adjText = adjText[:matchClose.start(0)] + '</char>' + adjText[matchClose.end(0):]
                            if haveOpenChar:
                                adjText = adjText.replace( 'CLOSED_BIT', '' ) # Fix up closed bit since it was specifically closed
                                haveOpenChar = False
                            #print( "adjText", adjText )
                if haveOpenChar:
                    adjText = adjText.replace( 'CLOSED_BIT', ' closed="false"' ) # Fix up closed bit since it wasn't closed
                    adjText += '{}</char>'.format( '' if adjText[-1]==' ' else ' ')
                    logger.info( "toUSX2XML: Had to close automatically in {} {}:{} {}:{!r} now {!r}".format( BBB, C, V, marker, originalText, adjText ) )
                if '\\' in adjText:
                    logger.critical( "toUSX2XML: Didn't handle a backslash in {} {}:{} {}:{!r} now {!r}".format( BBB, C, V, marker, originalText, adjText ) )
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag \
                    or BibleOrgSysGlobals.strictCheckingFlag:
                        halt
                if 'CLOSED_BIT' in adjText:
                    logger.critical( "toUSX2XML: Didn't handle a character style correctly in {} {}:{} {}:{!r} now {!r}".format( BBB, C, V, marker, originalText, adjText ) )
                return adjText
            # end of toUSX2XML.handleInternalTextMarkersForUSX2

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
                        #print( "toUSX2XML:processXRef", j, "'"+token+"'", "from", '"'+USXxref+'"', xoOpen, xtOpen )
                        lcToken = token.lower()
                        if j==0: # The first token (but the x has already been removed)
                            USXxrefXML += ('caller="{}" style="x">' if version>=2 else 'caller="{}">') \
                                .format( token.rstrip() )
                        elif lcToken.startswith('xo '): # xref reference follows
                            if xoOpen: # We have multiple xo fields one after the other (probably an encoding error)
                                if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not xtOpen
                                USXxrefXML += ' closed="false">' + adjToken + '</char>'
                                xoOpen = False
                            if xtOpen: # if we have multiple cross-references one after the other
                                USXxrefXML += ' closed="false">' + adjToken + '</char>'
                                xtOpen = False
                            adjToken = token[3:]
                            USXxrefXML += '<char style="xo"'
                            xoOpen = True
                        elif lcToken.startswith('xo*'):
                            if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert xoOpen and not xtOpen
                            USXxrefXML += '>' + adjToken + '</char>'
                            xoOpen = False
                        elif lcToken.startswith('xt '): # xref text follows
                            if xtOpen: # Multiple xt's in a row
                                if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not xoOpen
                                USXxrefXML += ' closed="false">' + adjToken + '</char>'
                            if xoOpen:
                                USXxrefXML += ' closed="false">' + adjToken + '</char>'
                                xoOpen = False
                            adjToken = token[3:]
                            USXxrefXML += '<char style="xt"'
                            xtOpen = True
                        elif lcToken.startswith('xt*'):
                            if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert xtOpen and not xoOpen
                            USXxrefXML += '>' + adjToken + '</char>'
                            xtOpen = False
                        #elif lcToken in ('xo*','xt*','x*',):
                        #    pass # We're being lazy here and not checking closing markers properly
                        else:
                            logger.warning( _("toUSX2XML: Unprocessed {!r} token in {} {}:{} xref {!r}").format( token, BBB, C, V, USXxref ) )
                    if xoOpen:
                        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not xtOpen
                        USXxrefXML += ' closed="false">' + adjToken + '</char>'
                        xoOpen = False
                    if xtOpen:
                        USXxrefXML += ' closed="false">' + adjToken + '</char>'
                    USXxrefXML += '</note>'
                    return USXxrefXML
                # end of toUSX2XML.processXRef

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
                        #print( f"USX processFootnote {j}: '{token}'  {frOpen} {fTextOpen} {fCharOpen}  '{USXfootnote}'" )
                        lcToken = token.lower()
                        if j==0:
                            USXfootnoteXML += f'caller="{token.rstrip()}">'
                        elif lcToken.startswith('fr '): # footnote reference follows
                            if frOpen:
                                if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not fTextOpen
                                logger.error( _("toUSX2XML: Two consecutive fr fields in {} {}:{} footnote {!r}").format( token, BBB, C, V, USXfootnote ) )
                                USXfootnoteXML += f' closed="false">{adjToken}</char>'
                                frOpen = False
                            if fTextOpen:
                                if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not frOpen
                                USXfootnoteXML += f' closed="false">{adjToken}</char>'
                                fTextOpen = False
                            if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not fCharOpen
                            adjToken = token[3:]
                            USXfootnoteXML += '<char style="fr"'
                            frOpen = True
                        elif lcToken.startswith('fr* '):
                            if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert frOpen and not fTextOpen and not fCharOpen
                            USXfootnoteXML += f'>{adjToken}</char>'
                            frOpen = False
                        elif lcToken.startswith('ft ') or lcToken.startswith('fq ') or lcToken.startswith('fqa ') or lcToken.startswith('fv ') or lcToken.startswith('fk '):
                            if fCharOpen:
                                if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not frOpen
                                USXfootnoteXML += f'>{adjToken}</char>'
                                fCharOpen = False
                            if frOpen:
                                if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not fTextOpen
                                USXfootnoteXML += f' closed="false">{adjToken}</char>'
                                frOpen = False
                            if fTextOpen:
                                USXfootnoteXML += f' closed="false">{adjToken}</char>'
                                fTextOpen = False
                            fMarker = lcToken.split()[0] # Get the bit before the space
                            USXfootnoteXML += f'<char style="{fMarker}"'
                            adjToken = token[len(fMarker)+1:] # Get the bit after the space
                            #print( "{!r} {!r}".format( fMarker, adjToken ) )
                            fTextOpen = True
                        elif lcToken.startswith('ft*') or lcToken.startswith('fq*') or lcToken.startswith('fqa*') or lcToken.startswith('fv*') or lcToken.startswith('fk*'):
                            #if BibleOrgSysGlobals.debugFlag:
                                #print( "toUSX2XML.processFootnote: Problem with {} {} {} in {} {}:{} footnote {!r} part {!r}".format( fTextOpen, frOpen, fCharOpen, BBB, C, V, USXfootnote, lcToken ) )
                                #assert fTextOpen and not frOpen and not fCharOpen
                            if frOpen or fCharOpen or not fTextOpen:
                                logger.error( "toUSX2XML.processFootnote: Closing problem at {} {}:{} in footnote {!r}".format( BBB, C, V, USXfootnote ) )
                            USXfootnoteXML += f'>{adjToken}</char>'
                            fTextOpen = False
                        elif lcToken.startswith('z'):
                            #print( f"USX processFootnote {j} custom: '{token}'  {frOpen} {fTextOpen} {fCharOpen}  '{USXfootnote}'" )
                            ixSpace = lcToken.find( ' ' )
                            if ixSpace == -1: ixSpace = 9999
                            ixAsterisk = lcToken.find( '*' )
                            if ixAsterisk == -1: ixAsterisk = 9999
                            if ixSpace < ixAsterisk: # Must be an opening marker
                                if fCharOpen:
                                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not frOpen
                                    USXfootnoteXML += f'>{adjToken}</char>'
                                    fCharOpen = False
                                if frOpen:
                                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not fTextOpen
                                    USXfootnoteXML += f' closed="false">{adjToken}</char>'
                                    frOpen = False
                                if fTextOpen:
                                    USXfootnoteXML += f' closed="false">{adjToken}</char>'
                                    fTextOpen = False
                                marker = lcToken[:ixSpace]
                                USXfootnoteXML += f'<char style="{marker}"'
                                adjToken = token[len(marker)+1:] # Get the bit after the space
                                fCharOpen = marker
                            elif ixAsterisk < ixSpace: # Must be an closing marker
                                if not fCharOpen:
                                    logger.error( "toUSX2XML.processFootnote: Closing problem at {} {}:{} in custom footnote {!r}".format( BBB, C, V, USXfootnote ) )
                                USXfootnoteXML += f'>{adjToken}</char>'
                                fCharOpen = False
                            else:
                                logger.error( "toUSX2XML.processFootnote: Marker roblem at {} {}:{} in custom footnote {!r}".format( BBB, C, V, USXfootnote ) )
                        else: # Could be character formatting (or closing of character formatting)
                            subTokens = lcToken.split()
                            firstToken = subTokens[0]
                            #print( "ft", firstToken )
                            if firstToken in ALL_CHAR_MARKERS: # Yes, confirmed
                                if fCharOpen: # assume that the last one is closed by this one
                                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not frOpen
                                    USXfootnoteXML += f'>{adjToken}</char>'
                                    fCharOpen = False
                                if frOpen:
                                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not fCharOpen
                                    USXfootnoteXML += f' closed="false">{adjToken}</char>'
                                    frOpen = False
                                USXfootnoteXML += f'<char style="{firstToken}"'
                                adjToken = token[len(firstToken)+1:] # Get the bit after the space
                                fCharOpen = firstToken
                            else: # The problem is that a closing marker doesn't have to be followed by a space
                                if firstToken[-1]=='*' and firstToken[:-1] in ALL_CHAR_MARKERS: # it's a closing tag (that was followed by a space)
                                    if fCharOpen:
                                        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not frOpen
                                        if not firstToken.startswith( fCharOpen+'*' ): # It's not a matching tag
                                            logger.warning( _("toUSX2XML: {!r} closing tag doesn't match {!r} in {} {}:{} footnote {!r}").format( firstToken, fCharOpen, BBB, C, V, USXfootnote ) )
                                        USXfootnoteXML += f'>{adjToken}</char>'
                                        fCharOpen = False
                                    logger.warning( _("toUSX2XML: {!r} closing tag doesn't match in {} {}:{} footnote {!r}").format( firstToken, BBB, C, V, USXfootnote ) )
                                else:
                                    ixAS = firstToken.find( '*' )
                                    #print( firstToken, ixAS, firstToken[:ixAS] if ixAS!=-1 else '' )
                                    if ixAS!=-1 and ixAS<4 and firstToken[:ixAS] in ALL_CHAR_MARKERS: # it's a closing tag
                                        if fCharOpen:
                                            if debuggingThisModule or BibleOrgSysGlobals.debugFlag:
                                                assert not frOpen
                                            if not firstToken.startswith( fCharOpen+'*' ): # It's not a matching tag
                                                logger.warning( _("toUSX2XML: {!r} closing tag doesn't match {!r} in {} {}:{} footnote {!r}").format( firstToken, fCharOpen, BBB, C, V, USXfootnote ) )
                                            USXfootnoteXML += f'>{adjToken}</char>'
                                            fCharOpen = False
                                        logger.warning( _("toUSX2XML: {!r} closing tag doesn't match in {} {}:{} footnote {!r}").format( firstToken, BBB, C, V, USXfootnote ) )
                                    else:
                                        logger.warning( _("toUSX2XML: Unprocessed {!r} token in {} {}:{} footnote {!r}").format( firstToken, BBB, C, V, USXfootnote ) )
                                        print( ALL_CHAR_MARKERS )
                                        if debuggingThisModule or BibleOrgSysGlobals.debugFlag \
                                        or BibleOrgSysGlobals.strictCheckingFlag:
                                            halt
                    #print( "  ", frOpen, fCharOpen, fTextOpen )
                    if frOpen:
                        logger.warning( _("toUSX2XML: Unclosed 'fr' token in {} {}:{} footnote {!r}").format( BBB, C, V, USXfootnote) )
                        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not fCharOpen and not fTextOpen
                        USXfootnoteXML += f' closed="false">{adjToken}</char>'
                    if fCharOpen:
                        logger.info( _("toUSX2XML: Unclosed {!r} token in {} {}:{} footnote {!r}").format( fCharOpen, BBB, C, V, USXfootnote) )
                    if fTextOpen or fCharOpen:
                        USXfootnoteXML += f' closed="false">{adjToken}</char>'
                    USXfootnoteXML += '</note>'
                    #print( '', USXfootnote, USXfootnoteXML )
                    return USXfootnoteXML
                # end of toUSX2XML.processFootnote


                adjText = text
                if extras:
                    offset = 0
                    for extra in extras: # do any footnotes and cross-references
                        extraType, extraIndex, extraText, cleanExtraText = extra
                        #print( "{} {}:{} Text={!r} eT={}, eI={}, eText={!r}".format( BBB, C, V, text, extraType, extraIndex, extraText ) )
                        adjIndex = extraIndex - offset
                        lenT = len( adjText )
                        if adjIndex > lenT: # This can happen if we have verse/space/notes at end (and the space was deleted after the note was separated off)
                            logger.warning( _("toUSX2XML: Space before note at end of verse in {} {}:{} has been lost").format( BBB, C, V ) )
                            # No need to adjust adjIndex because the code below still works
                        elif adjIndex<0 or adjIndex>lenT: # The extras don't appear to fit correctly inside the text
                            print( "toUSX2XML: Extras don't fit inside verse at {} {}:{}: eI={} o={} len={} aI={}".format( BBB, C, V, extraIndex, offset, len(text), adjIndex ) )
                            print( "  Verse={!r}".format( text ) )
                            print( "  Extras={!r}".format( extras ) )
                        #assert 0 <= adjIndex <= len(verse)
                        #adjText = checkText( extraText, checkLeftovers=False ) # do any general character formatting
                        #if adjText!=extraText: print( "processXRefsAndFootnotes: {}@{}-{}={} {!r} now {!r}".format( extraType, extraIndex, offset, adjIndex, extraText, adjText ) )
                        if extraType == 'fn':
                            extra = processFootnote( extraText )
                            #print( "fn got", extra )
                        elif extraType == 'xr':
                            extra = processXRef( extraText )
                            #print( "xr got", extra )
                        elif extraType == 'fig':
                            logger.critical( "USXXML figure not handled yet" )
                            extra = '' # temp
                            #extra = processFigure( extraText )
                            #print( "fig got", extra )
                        elif extraType == 'str':
                            extra = '' # temp
                        elif extraType == 'sem':
                            extra = '' # temp
                        elif extraType == 'vp':
                            extra = "\\vp {}\\vp*".format( extraText ) # Will be handled later
                        elif BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( extraType ); halt
                        #print( "was", verse )
                        adjText = adjText[:adjIndex] + str(extra) + adjText[adjIndex:]
                        offset -= len( extra )
                        #print( "now", verse )
                return adjText
            # end of toUSX2XML.handleNotes

            USXAbbrev = BibleOrgSysGlobals.loadedBibleBooksCodes.getUSFMAbbreviation( BBB ).upper()
            USXNumber = BibleOrgSysGlobals.loadedBibleBooksCodes.getUSXNumber( BBB )
            if not USXAbbrev:
                logger.error( "toUSX2XML: Can't write {} USX book because no USFM code available".format( BBB ) )
                unhandledBooks.append( BBB )
                return
            if not USXNumber:
                logger.error( "toUSX2XML: Can't write {} USX book because no USX number available".format( BBB ) )
                unhandledBooks.append( BBB )
                return

            version = 2.6
            xtra = ' ' if version<2 else ''
            C, V = '-1', '-1' # So first/id line starts at -1:0
            xw = MLWriter( BibleOrgSysGlobals.makeSafeFilename( USXNumber+USXAbbrev+'.usx' ), filesFolder )
            xw.setHumanReadable()
            xw.spaceBeforeSelfcloseTag = True
            xw.start( lineEndings='w', writeBOM=True ) # Try to imitate Paratext output as closely as possible
            xw.writeLineOpen( 'usx', (('version','2.6') if version>=2 else None ) )
            haveOpenPara = paraJustOpened = False
            gotVP = None
            for processedBibleEntry in bkData._processedLines: # Process internal Bible data lines
                marker, originalMarker, text, extras = processedBibleEntry.getMarker(), processedBibleEntry.getOriginalMarker(), processedBibleEntry.getAdjustedText(), processedBibleEntry.getExtras()
                if '¬' in marker or marker in BOS_ADDED_NESTING_MARKERS or marker=='v=':
                    continue # Just ignore added markers — not needed here
                if marker in USFM_PRECHAPTER_MARKERS:
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
                        assert C=='-1' or marker=='rem' or marker.startswith('mte')
                    V = str( int(V) + 1 )
                getMarkerContentType = BibleOrgSysGlobals.loadedUSFMMarkers.getMarkerContentType( marker )
                #print( BBB, C, V, marker, getMarkerContentType, haveOpenPara, paraJustOpened )

                adjText = handleNotes( text, extras )
                if marker == 'id':
                    if haveOpenPara: # This should never happen coz the ID line should have been the first line in the file
                        logger.error( "toUSX2XML: Book {}{} has a id line inside an open paragraph: {!r}".format( BBB, " ({})".format(USXAbbrev) if USXAbbrev!=BBB else '', adjText ) )
                        xw.removeFinalNewline( True )
                        xw.writeLineClose( 'para' )
                        haveOpenPara = False
                    adjTxLen = len( adjText )
                    if adjTxLen<3 or (adjTxLen>3 and adjText[3]!=' '): # Doesn't seem to have a standard BBB at the beginning of the ID line
                        logger.warning( "toUSX2XML: Book {}{} has a non-standard id line: {!r}".format( BBB, " ({})".format(USXAbbrev) if USXAbbrev!=BBB else '', adjText ) )
                        #halt
                    if adjText[0:3] != USXAbbrev:
                        logger.error( "toUSX2XML: Book {}{} might have incorrect code on id line — we got: {!r}".format( BBB, " ({})".format(USXAbbrev) if USXAbbrev!=BBB else '', adjText[0:3] ) )
                        #halt
                    adjText = adjText[4:] # Remove the book code from the ID line because it's put in as an attribute
                    if adjText: xw.writeLineOpenClose( 'book', handleInternalTextMarkersForUSX2(adjText)+xtra, [('code',USXAbbrev),('style',marker)] )
                    else: xw.writeLineOpenSelfclose( 'book', [('code',USXAbbrev),('style',marker)] )
                    #elif not text: logger.error( "toUSX2XML: {} {}:{} has a blank id line that was ignored".format( BBB, C, V ) )

                elif marker == 'c':
                    if haveOpenPara:
                        xw.removeFinalNewline( True )
                        xw.writeLineClose( 'para' )
                        haveOpenPara = False
                    #print( BBB, 'C', repr(text), repr(adjText) )
                    C, V = text, '0' # not adjText!
                    xw.writeLineOpenSelfclose ( 'chapter', [('number',C),('style','c')] )
                    if adjText != text:
                        logger.warning( "toUSX2XML: Lost additional note text on c for {} {!r}".format( BBB, C ) )
                elif marker == 'c~': # Don't really know what this stuff is!!!
                    if not adjText: logger.warning( "toUSX2XML: Missing text for c~" ); continue
                    # TODO: We haven't stripped out character fields from within the text — not sure how USX handles them yet
                    xw.removeFinalNewline( True )
                    xw.writeLineText( handleInternalTextMarkersForUSX2(adjText)+xtra, noTextCheck=True ) # no checks coz might already have embedded XML
                elif marker == 'c#': # Chapter number added for printing
                    ignoredMarkers.add( marker ) # Just ignore it completely
                elif marker == 'vp#': # This precedes a v field and has the verse number to be printed
                    gotVP = adjText # Just remember it for now
                elif marker == 'v':
                    V = adjText
                    if gotVP: # this is the verse number to be published
                        adjText = gotVP
                        gotVP = None
                    if paraJustOpened: paraJustOpened = False
                    else:
                        xw.removeFinalNewline( True )
                        if version>=2: xw._writeToBuffer( ' ' ) # Space between verses
                     # Remove anything that'll cause a big XML problem later
                    if adjText:
                        xw.writeLineOpenSelfclose ( 'verse', [('number',adjText.replace('<','').replace('>','').replace('"','')),('style','v')] )

                elif marker in ('v~','p~',):
                    if not adjText: logger.warning( "toUSX2XML: Missing text for {}".format( marker ) ); continue
                    # TODO: We haven't stripped out character fields from within the verse — not sure how USX handles them yet
                    xw.removeFinalNewline( True )
                    xw.writeLineText( handleInternalTextMarkersForUSX2(adjText)+xtra, noTextCheck=True ) # no checks coz might already have embedded XML
                elif getMarkerContentType == 'N': # N = never, e.g., b, nb
                    if haveOpenPara:
                        xw.removeFinalNewline( True )
                        xw.writeLineClose( 'para' )
                        haveOpenPara = False
                    if adjText:
                        logger.error( "toUSX2XML: {} {}:{} has a {} line containing text ({!r}) that was ignored".format( BBB, C, V, originalMarker, adjText ) )
                    xw.writeLineOpenSelfclose ( 'para', ('style',marker) )
                elif getMarkerContentType == 'S': # S = sometimes, e.g., p,pi,q,q1,q2,q3,q4,m
                    if haveOpenPara:
                        xw.removeFinalNewline( True )
                        xw.writeLineClose( 'para' )
                        haveOpenPara = False
                    if not adjText: xw.writeLineOpen( 'para', ('style',originalMarker) )
                    else:
                        xw.writeLineOpenText( 'para', handleInternalTextMarkersForUSX2(adjText)+xtra, ('style',originalMarker), noTextCheck=True ) # no checks coz might already have embedded XML
                    haveOpenPara = paraJustOpened = True
                else:
                    #assert getMarkerContentType == 'A' # A = always, e.g.,  ide, mt, h, s, ip, etc.
                    if getMarkerContentType != 'A':
                        logger.error( "BibleWriter.toUSX2XML: ToProgrammer — should be 'A': {!r} is {!r} Why?".format( marker, getMarkerContentType ) )
                    if haveOpenPara:
                        xw.removeFinalNewline( True )
                        xw.writeLineClose( 'para' )
                        haveOpenPara = False
                    xw.writeLineOpenClose( 'para', handleInternalTextMarkersForUSX2(adjText)+xtra, ('style',originalMarker if originalMarker else marker), noTextCheck=True ) # no checks coz might already have embedded XML
            if haveOpenPara:
                xw.removeFinalNewline( True )
                xw.writeLineClose( 'para' )
            xw.writeLineClose( 'usx' )
            xw.close( writeFinalNL=True ) # Try to imitate Paratext output as closely as possible
            if validationSchema: return xw.validate( validationSchema ) # Returns a 3-tuple: intCode, logString, errorLogString
        # end of toUSX2XML.writeUSXBook

        # Set-up our Bible reference system
        if 'PublicationCode' not in controlDict or controlDict['PublicationCode'] == 'GENERIC':
            BOS = self.genericBOS
            BRL = self.genericBRL
        else:
            BOS = BibleOrganisationalSystem( controlDict['PublicationCode'] )
            BRL = BibleReferenceList( BOS, BibleObject=None )

        if BibleOrgSysGlobals.verbosityLevel > 2: print( _("  Exporting to USX format…") )
        #USXOutputFolder = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( "USX output/' )
        #if not os.access( USXOutputFolder, os.F_OK ): os.mkdir( USXOutputFolder ) # Make the empty folder if there wasn't already one there

        validationResults = ( 0, '', '', ) # xmllint result code, program output, error output
        for BBB,bookData in self.books.items():
            bookResults = writeUSXBook( BBB, bookData )
            if validationSchema:
                if bookResults[0] > validationResults[0]: validationResults = ( bookResults[0], validationResults[1], validationResults[2], )
                if bookResults[1]: validationResults = ( validationResults[0], validationResults[1] + bookResults[1], validationResults[2], )
                if bookResults[2]: validationResults = ( validationResults[0], validationResults[1], validationResults[2] + bookResults[2], )
        if validationSchema:
            if validationResults[0] > 0:
                with open( os.path.join( outputFolderpath, 'ValidationErrors.txt' ), 'wt', encoding='utf-8' ) as veFile:
                    if validationResults[1]: veFile.write( validationResults[1] + '\n\n\n' ) # Normally empty
                    if validationResults[2]: veFile.write( validationResults[2] )

        if ignoredMarkers:
            logger.info( "toUSX2XML: Ignored markers were {}".format( ignoredMarkers ) )
            if BibleOrgSysGlobals.verbosityLevel > 2:
                print( "  " + _("ERROR: Ignored toUSX2XML markers were {}").format( ignoredMarkers ) )
        if unhandledMarkers:
            logger.error( "toUSX2XML: Unhandled markers were {}".format( unhandledMarkers ) )
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print( "  " + _("ERROR: Unhandled toUSX2XML markers were {}").format( unhandledMarkers ) )
        if unhandledBooks:
            logger.warning( "toUSX2XML: Unhandled books were {}".format( unhandledBooks ) )
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print( "  " + _("WARNING: Unhandled toUSX2XML books were {}").format( unhandledBooks ) )

        # Now create a zipped collection
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Zipping USX2 files…" )
        zf = zipfile.ZipFile( os.path.join( outputFolderpath, 'AllUSX2Files.zip' ), 'w', compression=zipfile.ZIP_DEFLATED )
        for filename in os.listdir( filesFolder ):
            #if not filename.endswith( '.zip' ):
            filepath = os.path.join( filesFolder, filename )
            zf.write( filepath, filename ) # Save in the archive without the path
        zf.close()
        # Now create the gzipped file
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  GZipping USX2 files…" )
        tar = tarfile.open( os.path.join( outputFolderpath, 'AllUSX2Files.gzip' ), 'w:gz' )
        for filename in os.listdir( filesFolder ):
            if filename.endswith( '.usx' ):
                filepath = os.path.join( filesFolder, filename )
                tar.add( filepath, arcname=filename, recursive=False )
        tar.close()
        # Now create the bz2 file
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  BZipping USX2 files…" )
        tar = tarfile.open( os.path.join( outputFolderpath, 'AllUSX2Files.bz2' ), 'w:bz2' )
        for filename in os.listdir( filesFolder ):
            if filename.endswith( '.usx' ):
                filepath = os.path.join( filesFolder, filename )
                tar.add( filepath, arcname=filename, recursive=False )
        tar.close()

        if BibleOrgSysGlobals.verbosityLevel > 0 and BibleOrgSysGlobals.maxProcesses > 1:
            print( "  BibleWriter.toUSX2XML finished successfully." )
        if validationSchema: return validationResults
        return True
    # end of BibleWriter.toUSX2XML



    def toUSX3XML( self, outputFolderpath:Optional[Path]=None, controlDict=None, validationSchema=None ):
        """
        Using settings from the given control file,
            converts the USFM information to UTF-8 USX XML files.

        If a schema is given (either a path or URL), the XML output files are validated.
        """
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Running BibleWriter:toUSX3XML…" )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert self.books

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolderpath: outputFolderpath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_USX3_Export/' )
        #if not os.access( outputFolderpath, os.F_OK ): os.makedirs( outputFolderpath ) # Make the empty folder if there wasn't already one there
        filesFolder = os.path.join( outputFolderpath, 'USX3Files/' )
        if not os.access( filesFolder, os.F_OK ): os.makedirs( filesFolder ) # Make the empty folder if there wasn't already one there
        if not controlDict:
            controlDict, defaultControlFilename = {}, "To_USX_controls.txt"
            try: ControlFiles.readControlFile( defaultControlFolderpath, defaultControlFilename, controlDict )
            except FileNotFoundError:
                logger.critical( "Unable to read control dict {} from {}".format( defaultControlFilename, defaultControlFolderpath ) )
        self.__adjustControlDict( controlDict )
        if not validationSchema: # We'll use our copy
            rncFilepath = 'ExternalSchemas/DerivedFiles/usx_3.0.rng'
            if os.path.exists( rncFilepath ): validationSchema = rncFilepath

        ignoredMarkers, unhandledMarkers, unhandledBooks = set(), set(), []

        def writeUSXBook( BBB, bkData ):
            """ Writes a book to the filesFolder. """

            def handleInternalTextMarkersForUSX3( originalText ):
                """
                Handles character formatting markers within the originalText.
                Tries to find pairs of markers and replaces them with html char segments.
                """
                if not originalText: return ''
                if '\\' not in originalText: return originalText
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( "toUSX3XML:hITM4USX:", BBB, C, V, marker, "'"+originalText+"'" )
                markerList = sorted( BibleOrgSysGlobals.loadedUSFMMarkers.getMarkerListFromText( originalText ),
                                            key=lambda s: -len(s[4])) # Sort by longest characterContext first (maximum nesting)
                for insideMarker, iMIndex, nextSignificantChar, fullMarker, characterContext, endIndex, markerField in markerList: # check for internal markers
                    pass

                # Old code
                adjText = originalText
                haveOpenChar = False
                for charMarker in ALL_CHAR_MARKERS:
                    #print( "handleInternalTextMarkersForUSX3", charMarker )
                    # Handle USFM character markers
                    fullCharMarker = '\\' + charMarker + ' '
                    if fullCharMarker in adjText:
                        if haveOpenChar:
                            adjText = adjText.replace( 'CLOSED_BIT', ' closed="false"' ) # Fix up closed bit since it wasn't closed
                            logger.info( "toUSX3XML: USX export had to close automatically in {} {}:{} {}:{!r} now {!r}".format( BBB, C, V, marker, originalText, adjText ) ) # The last marker presumably only had optional closing (or else we just messed up nesting markers)
                        adjText = adjText.replace( fullCharMarker, f'{"</char>" if haveOpenChar else ""}<char style="{charMarker}"CLOSED_BIT>' )
                        haveOpenChar = True
                    endCharMarker = '\\' + charMarker + '*'
                    if endCharMarker in adjText:
                        if not haveOpenChar: # Then we must have a missing open marker (or extra closing marker)
                            logger.error( "toUSX3XML: Ignored extra {!r} closing marker in {} {}:{} {}:{!r} now {!r}".format( charMarker, BBB, C, V, marker, originalText, adjText ) )
                            adjText = adjText.replace( endCharMarker, '' ) # Remove the unused marker
                        else: # looks good
                            adjText = adjText.replace( 'CLOSED_BIT', '' ) # Fix up closed bit since it was specifically closed
                            adjText = adjText.replace( endCharMarker, '</char>' )
                            haveOpenChar = False
                if '\\z' in adjText:
                    # Handle custom (character) markers
                    while True:
                        matchOpen = re.search( r'\\z([\w\d]+?) ', adjText )
                        if not matchOpen: break
                        #print( f"Matched custom marker open '{matchOpen.group(0)}'" )
                        adjText = adjText[:matchOpen.start(0)] + f'<char style="z{matchOpen.group(1)}"CLOSED_BIT>' + adjText[matchOpen.end(0):]
                        haveOpenChar = True
                        #print( "adjText", adjText )
                        matchClose = re.search( r'\\z{}\*'.format( matchOpen.group(1) ), adjText )
                        if matchClose:
                            #print( f"Matched custom marker close '{matchClose.group(0)}'" )
                            adjText = adjText[:matchClose.start(0)] + '</char>' + adjText[matchClose.end(0):]
                            if haveOpenChar:
                                adjText = adjText.replace( 'CLOSED_BIT', '' ) # Fix up closed bit since it was specifically closed
                                haveOpenChar = False
                            #print( "adjText", adjText )
                if haveOpenChar:
                    adjText = adjText.replace( 'CLOSED_BIT', ' closed="false"' ) # Fix up closed bit since it wasn't closed
                    adjText += '{}</char>'.format( '' if adjText[-1]==' ' else ' ')
                    logger.info( "toUSX3XML: Had to close automatically in {} {}:{} {}:{!r} now {!r}".format( BBB, C, V, marker, originalText, adjText ) )
                if '\\' in adjText:
                    logger.critical( "toUSX3XML: Didn't handle a backslash in {} {}:{} {}:{!r} now {!r}".format( BBB, C, V, marker, originalText, adjText ) )
                    halt
                if 'CLOSED_BIT' in adjText:
                    logger.critical( "toUSX3XML: Didn't handle a character style correctly in {} {}:{} {}:{!r} now {!r}".format( BBB, C, V, marker, originalText, adjText ) )
                return adjText
            # end of toUSX3XML.handleInternalTextMarkersForUSX3


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
                    USXxrefXML = '<note '
                    xoOpen = xtOpen = False
                    for j,token in enumerate(USXxref.split('\\')):
                        #print( "toUSX3XML:processXRef", j, "'"+token+"'", "from", '"'+USXxref+'"', xoOpen, xtOpen )
                        lcToken = token.lower()
                        if j==0: # The first token (but the x has already been removed)
                            USXxrefXML += ('caller="{}" style="x">' if version>=2 else 'caller="{}">') \
                                .format( token.rstrip() )
                        elif lcToken.startswith('xo '): # xref reference follows
                            if xoOpen: # We have multiple xo fields one after the other (probably an encoding error)
                                if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not xtOpen
                                USXxrefXML += ' closed="false">' + adjToken + '</char>'
                                xoOpen = False
                            if xtOpen: # if we have multiple cross-references one after the other
                                USXxrefXML += ' closed="false">' + adjToken + '</char>'
                                xtOpen = False
                            adjToken = token[3:]
                            USXxrefXML += '<char style="xo"'
                            xoOpen = True
                        elif lcToken.startswith('xo*'):
                            if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert xoOpen and not xtOpen
                            USXxrefXML += '>' + adjToken + '</char>'
                            xoOpen = False
                        elif lcToken.startswith('xt '): # xref text follows
                            if xtOpen: # Multiple xt's in a row
                                if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not xoOpen
                                USXxrefXML += ' closed="false">' + adjToken + '</char>'
                            if xoOpen:
                                USXxrefXML += ' closed="false">' + adjToken + '</char>'
                                xoOpen = False
                            adjToken = token[3:]
                            USXxrefXML += '<char style="xt"'
                            xtOpen = True
                        elif lcToken.startswith('xt*'):
                            if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert xtOpen and not xoOpen
                            USXxrefXML += '>' + adjToken + '</char>'
                            xtOpen = False
                        #elif lcToken in ('xo*','xt*','x*',):
                        #    pass # We're being lazy here and not checking closing markers properly
                        else:
                            logger.warning( _("toUSX3XML: Unprocessed {!r} token in {} {}:{} xref {!r}").format( token, BBB, C, V, USXxref ) )
                    if xoOpen:
                        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not xtOpen
                        USXxrefXML += ' closed="false">' + adjToken + '</char>'
                        xoOpen = False
                    if xtOpen:
                        USXxrefXML += ' closed="false">' + adjToken + '</char>'
                    USXxrefXML += '</note>'
                    return USXxrefXML
                # end of toUSX3XML.processXRef

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
                        #print( f"USX processFootnote {j}: '{token}'  {frOpen} {fTextOpen} {fCharOpen}  '{USXfootnote}'" )
                        lcToken = token.lower()
                        if j==0:
                            USXfootnoteXML += f'caller="{token.rstrip()}">'
                        elif lcToken.startswith('fr '): # footnote reference follows
                            if frOpen:
                                if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not fTextOpen
                                logger.error( _("toUSX3XML: Two consecutive fr fields in {} {}:{} footnote {!r}").format( token, BBB, C, V, USXfootnote ) )
                                USXfootnoteXML += f' closed="false">{adjToken}</char>'
                                frOpen = False
                            if fTextOpen:
                                if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not frOpen
                                USXfootnoteXML += f' closed="false">{adjToken}</char>'
                                fTextOpen = False
                            if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not fCharOpen
                            adjToken = token[3:]
                            USXfootnoteXML += '<char style="fr"'
                            frOpen = True
                        elif lcToken.startswith('fr* '):
                            if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert frOpen and not fTextOpen and not fCharOpen
                            USXfootnoteXML += f'>{adjToken}</char>'
                            frOpen = False
                        elif lcToken.startswith('ft ') or lcToken.startswith('fq ') or lcToken.startswith('fqa ') or lcToken.startswith('fv ') or lcToken.startswith('fk '):
                            if fCharOpen:
                                if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not frOpen
                                USXfootnoteXML += f'>{adjToken}</char>'
                                fCharOpen = False
                            if frOpen:
                                if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not fTextOpen
                                USXfootnoteXML += f' closed="false">{adjToken}</char>'
                                frOpen = False
                            if fTextOpen:
                                USXfootnoteXML += f' closed="false">{adjToken}</char>'
                                fTextOpen = False
                            fMarker = lcToken.split()[0] # Get the bit before the space
                            USXfootnoteXML += f'<char style="{fMarker}"'
                            adjToken = token[len(fMarker)+1:] # Get the bit after the space
                            #print( "{!r} {!r}".format( fMarker, adjToken ) )
                            fTextOpen = True
                        elif lcToken.startswith('ft*') or lcToken.startswith('fq*') or lcToken.startswith('fqa*') or lcToken.startswith('fv*') or lcToken.startswith('fk*'):
                            #if BibleOrgSysGlobals.debugFlag:
                                #print( "toUSX3XML.processFootnote: Problem with {} {} {} in {} {}:{} footnote {!r} part {!r}".format( fTextOpen, frOpen, fCharOpen, BBB, C, V, USXfootnote, lcToken ) )
                                #assert fTextOpen and not frOpen and not fCharOpen
                            if frOpen or fCharOpen or not fTextOpen:
                                logger.error( "toUSX3XML.processFootnote: Closing problem at {} {}:{} in footnote {!r}".format( BBB, C, V, USXfootnote ) )
                            USXfootnoteXML += f'>{adjToken}</char>'
                            fTextOpen = False
                        elif lcToken.startswith('z'):
                            #print( f"USX processFootnote {j} custom: '{token}'  {frOpen} {fTextOpen} {fCharOpen}  '{USXfootnote}'" )
                            ixSpace = lcToken.find( ' ' )
                            if ixSpace == -1: ixSpace = 9999
                            ixAsterisk = lcToken.find( '*' )
                            if ixAsterisk == -1: ixAsterisk = 9999
                            if ixSpace < ixAsterisk: # Must be an opening marker
                                if fCharOpen:
                                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not frOpen
                                    USXfootnoteXML += f'>{adjToken}</char>'
                                    fCharOpen = False
                                if frOpen:
                                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not fTextOpen
                                    USXfootnoteXML += f' closed="false">{adjToken}</char>'
                                    frOpen = False
                                if fTextOpen:
                                    USXfootnoteXML += f' closed="false">{adjToken}</char>'
                                    fTextOpen = False
                                marker = lcToken[:ixSpace]
                                USXfootnoteXML += f'<char style="{marker}"'
                                adjToken = token[len(marker)+1:] # Get the bit after the space
                                fCharOpen = marker
                            elif ixAsterisk < ixSpace: # Must be an closing marker
                                if not fCharOpen:
                                    logger.error( "toUSX3XML.processFootnote: Closing problem at {} {}:{} in custom footnote {!r}".format( BBB, C, V, USXfootnote ) )
                                USXfootnoteXML += f'>{adjToken}</char>'
                                fCharOpen = False
                            else:
                                logger.error( "toUSX3XML.processFootnote: Marker roblem at {} {}:{} in custom footnote {!r}".format( BBB, C, V, USXfootnote ) )
                        else: # Could be character formatting (or closing of character formatting)
                            subTokens = lcToken.split()
                            firstToken = subTokens[0]
                            #print( "ft", firstToken )
                            if firstToken in ALL_CHAR_MARKERS: # Yes, confirmed
                                if fCharOpen: # assume that the last one is closed by this one
                                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not frOpen
                                    USXfootnoteXML += f'>{adjToken}</char>'
                                    fCharOpen = False
                                if frOpen:
                                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not fCharOpen
                                    USXfootnoteXML += f' closed="false">{adjToken}</char>'
                                    frOpen = False
                                USXfootnoteXML += f'<char style="{firstToken}"'
                                adjToken = token[len(firstToken)+1:] # Get the bit after the space
                                fCharOpen = firstToken
                            else: # The problem is that a closing marker doesn't have to be followed by a space
                                if firstToken[-1]=='*' and firstToken[:-1] in ALL_CHAR_MARKERS: # it's a closing tag (that was followed by a space)
                                    if fCharOpen:
                                        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not frOpen
                                        if not firstToken.startswith( fCharOpen+'*' ): # It's not a matching tag
                                            logger.warning( _("toUSX3XML: {!r} closing tag doesn't match {!r} in {} {}:{} footnote {!r}").format( firstToken, fCharOpen, BBB, C, V, USXfootnote ) )
                                        USXfootnoteXML += f'>{adjToken}</char>'
                                        fCharOpen = False
                                    logger.warning( _("toUSX3XML: {!r} closing tag doesn't match in {} {}:{} footnote {!r}").format( firstToken, BBB, C, V, USXfootnote ) )
                                else:
                                    ixAS = firstToken.find( '*' )
                                    #print( firstToken, ixAS, firstToken[:ixAS] if ixAS!=-1 else '' )
                                    if ixAS!=-1 and ixAS<4 and firstToken[:ixAS] in ALL_CHAR_MARKERS: # it's a closing tag
                                        if fCharOpen:
                                            if debuggingThisModule or BibleOrgSysGlobals.debugFlag:
                                                assert not frOpen
                                            if not firstToken.startswith( fCharOpen+'*' ): # It's not a matching tag
                                                logger.warning( _("toUSX3XML: {!r} closing tag doesn't match {!r} in {} {}:{} footnote {!r}").format( firstToken, fCharOpen, BBB, C, V, USXfootnote ) )
                                            USXfootnoteXML += f'>{adjToken}</char>'
                                            fCharOpen = False
                                        logger.warning( _("toUSX3XML: {!r} closing tag doesn't match in {} {}:{} footnote {!r}").format( firstToken, BBB, C, V, USXfootnote ) )
                                    else:
                                        logger.warning( _("toUSX3XML: Unprocessed {!r} token in {} {}:{} footnote {!r}").format( firstToken, BBB, C, V, USXfootnote ) )
                                        print( "ALL_CHAR_MARKERS", ALL_CHAR_MARKERS )
                                        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: halt
                    #print( "  ", frOpen, fCharOpen, fTextOpen )
                    if frOpen:
                        logger.warning( _("toUSX3XML: Unclosed 'fr' token in {} {}:{} footnote {!r}").format( BBB, C, V, USXfootnote) )
                        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not fCharOpen and not fTextOpen
                        USXfootnoteXML += f' closed="false">{adjToken}</char>'
                    if fCharOpen:
                        logger.info( _("toUSX3XML: Unclosed {!r} token in {} {}:{} footnote {!r}").format( fCharOpen, BBB, C, V, USXfootnote) )
                    if fTextOpen or fCharOpen:
                        USXfootnoteXML += f' closed="false">{adjToken}</char>'
                    USXfootnoteXML += '</note>'
                    #print( '', USXfootnote, USXfootnoteXML )
                    return USXfootnoteXML
                # end of toUSX3XML.processFootnote


                adjText = text
                if extras:
                    offset = 0
                    for extra in extras: # do any footnotes and cross-references
                        extraType, extraIndex, extraText, cleanExtraText = extra
                        #print( "{} {}:{} Text={!r} eT={}, eI={}, eText={!r}".format( BBB, C, V, text, extraType, extraIndex, extraText ) )
                        adjIndex = extraIndex - offset
                        lenT = len( adjText )
                        if adjIndex > lenT: # This can happen if we have verse/space/notes at end (and the space was deleted after the note was separated off)
                            logger.warning( _("toUSX3XML: Space before note at end of verse in {} {}:{} has been lost").format( BBB, C, V ) )
                            # No need to adjust adjIndex because the code below still works
                        elif adjIndex<0 or adjIndex>lenT: # The extras don't appear to fit correctly inside the text
                            print( "toUSX3XML: Extras don't fit inside verse at {} {}:{}: eI={} o={} len={} aI={}".format( BBB, C, V, extraIndex, offset, len(text), adjIndex ) )
                            print( "  Verse={!r}".format( text ) )
                            print( "  Extras={!r}".format( extras ) )
                        #assert 0 <= adjIndex <= len(verse)
                        #adjText = checkText( extraText, checkLeftovers=False ) # do any general character formatting
                        #if adjText!=extraText: print( "processXRefsAndFootnotes: {}@{}-{}={} {!r} now {!r}".format( extraType, extraIndex, offset, adjIndex, extraText, adjText ) )
                        if extraType == 'fn':
                            extra = processFootnote( extraText )
                            #print( "fn got", extra )
                        elif extraType == 'xr':
                            extra = processXRef( extraText )
                            #print( "xr got", extra )
                        elif extraType == 'fig':
                            logger.critical( "USXXML figure not handled yet" )
                            extra = '' # temp
                            #extra = processFigure( extraText )
                            #print( "fig got", extra )
                        elif extraType == 'str':
                            extra = '' # temp
                        elif extraType == 'sem':
                            extra = '' # temp
                        elif extraType == 'vp':
                            extra = "\\vp {}\\vp*".format( extraText ) # Will be handled later
                        elif BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( extraType ); halt
                        #print( "was", verse )
                        adjText = adjText[:adjIndex] + str(extra) + adjText[adjIndex:]
                        offset -= len( extra )
                        #print( "now", verse )
                return adjText
            # end of toUSX3XML.handleNotes

            USXAbbrev = BibleOrgSysGlobals.loadedBibleBooksCodes.getUSFMAbbreviation( BBB ).upper()
            USXNumber = BibleOrgSysGlobals.loadedBibleBooksCodes.getUSXNumber( BBB )
            if not USXAbbrev:
                logger.error( "toUSX3XML: Can't write {} USX book because no USFM code available".format( BBB ) )
                unhandledBooks.append( BBB )
                return
            if not USXNumber:
                logger.error( "toUSX3XML: Can't write {} USX book because no USX number available".format( BBB ) )
                unhandledBooks.append( BBB )
                return

            version = 3.0
            C, V = '-1', '-1' # So first/id line starts at -1:0
            xw = MLWriter( BibleOrgSysGlobals.makeSafeFilename( USXNumber+USXAbbrev+'.usx' ), filesFolder )
            xw.setHumanReadable()
            xw.spaceBeforeSelfcloseTag = True
            xw.start( lineEndings='w', writeBOM=True ) # Try to imitate Paratext output as closely as possible
            xw.writeLineOpen( 'usx', (('version','2.6') if version>=2 else None ) )
            haveOpenPara = paraJustOpened = False
            gotVP = None
            for processedBibleEntry in bkData._processedLines: # Process internal Bible data lines
                marker, originalMarker, text, extras = processedBibleEntry.getMarker(), processedBibleEntry.getOriginalMarker(), processedBibleEntry.getAdjustedText(), processedBibleEntry.getExtras()
                if '¬' in marker or marker in BOS_ADDED_NESTING_MARKERS or marker=='v=':
                    continue # Just ignore added markers — not needed here
                if marker in USFM_PRECHAPTER_MARKERS:
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
                        assert C=='-1' or marker=='rem' or marker.startswith('mte')
                    V = str( int(V) + 1 )
                getMarkerContentType = BibleOrgSysGlobals.loadedUSFMMarkers.getMarkerContentType( marker )
                #print( BBB, C, V, marker, getMarkerContentType, haveOpenPara, paraJustOpened )

                adjText = handleNotes( text, extras )
                if marker == 'id':
                    if haveOpenPara: # This should never happen coz the ID line should have been the first line in the file
                        logger.error( "toUSX3XML: Book {}{} has a id line inside an open paragraph: {!r}".format( BBB, " ({})".format(USXAbbrev) if USXAbbrev!=BBB else '', adjText ) )
                        xw.removeFinalNewline( True )
                        xw.writeLineClose( 'para' )
                        haveOpenPara = False
                    adjTxLen = len( adjText )
                    if adjTxLen<3 or (adjTxLen>3 and adjText[3]!=' '): # Doesn't seem to have a standard BBB at the beginning of the ID line
                        logger.warning( "toUSX3XML: Book {}{} has a non-standard id line: {!r}".format( BBB, " ({})".format(USXAbbrev) if USXAbbrev!=BBB else '', adjText ) )
                    if adjText[0:3] != USXAbbrev:
                        logger.error( "toUSX3XML: Book {}{} might have incorrect code on id line — we got: {!r}".format( BBB, " ({})".format(USXAbbrev) if USXAbbrev!=BBB else '', adjText[0:3] ) )
                    adjText = adjText[4:] # Remove the book code from the ID line because it's put in as an attribute
                    if adjText: xw.writeLineOpenClose( 'book', handleInternalTextMarkersForUSX3(adjText), [('code',USXAbbrev),('style',marker)] )
                    else: xw.writeLineOpenSelfclose( 'book', [('code',USXAbbrev),('style',marker)] )
                    #elif not text: logger.error( "toUSX3XML: {} {}:{} has a blank id line that was ignored".format( BBB, C, V ) )

                elif marker == 'c':
                    if haveOpenPara:
                        xw.removeFinalNewline( True )
                        xw.writeLineClose( 'para' )
                        haveOpenPara = False
                    #print( BBB, 'C', repr(text), repr(adjText) )
                    C, V = text, '0' # not adjText!
                    xw.writeLineOpenSelfclose ( 'chapter', [('number',C),('style','c')] )
                    if adjText != text:
                        logger.warning( "toUSX3XML: Lost additional note text on c for {} {!r}".format( BBB, C ) )
                elif marker == 'c~': # Don't really know what this stuff is!!!
                    if not adjText: logger.warning( "toUSX3XML: Missing text for c~" ); continue
                    # TODO: We haven't stripped out character fields from within the text — not sure how USX handles them yet
                    xw.removeFinalNewline( True )
                    xw.writeLineText( handleInternalTextMarkersForUSX3(adjText), noTextCheck=True ) # no checks coz might already have embedded XML
                elif marker == 'c#': # Chapter number added for printing
                    ignoredMarkers.add( marker ) # Just ignore it completely
                elif marker == 'vp#': # This precedes a v field and has the verse number to be printed
                    gotVP = adjText # Just remember it for now
                elif marker == 'v':
                    V = adjText
                    if gotVP: # this is the verse number to be published
                        adjText = gotVP
                        gotVP = None
                    if paraJustOpened: paraJustOpened = False
                    else:
                        xw.removeFinalNewline( True )
                        if version>=2: xw._writeToBuffer( ' ' ) # Space between verses
                     # Remove anything that'll cause a big XML problem later
                    if adjText:
                        xw.writeLineOpenSelfclose ( 'verse', [('number',adjText.replace('<','').replace('>','').replace('"','')),('style','v')] )

                elif marker in ('v~','p~',):
                    if not adjText: logger.warning( "toUSX3XML: Missing text for {}".format( marker ) ); continue
                    # TODO: We haven't stripped out character fields from within the verse — not sure how USX handles them yet
                    xw.removeFinalNewline( True )
                    xw.writeLineText( handleInternalTextMarkersForUSX3(adjText), noTextCheck=True ) # no checks coz might already have embedded XML
                elif getMarkerContentType == 'N': # N = never, e.g., b, nb
                    if haveOpenPara:
                        xw.removeFinalNewline( True )
                        xw.writeLineClose( 'para' )
                        haveOpenPara = False
                    if adjText:
                        logger.error( "toUSX3XML: {} {}:{} has a {} line containing text ({!r}) that was ignored".format( BBB, C, V, originalMarker, adjText ) )
                    xw.writeLineOpenSelfclose ( 'para', ('style',marker) )
                elif getMarkerContentType == 'S': # S = sometimes, e.g., p,pi,q,q1,q2,q3,q4,m
                    if haveOpenPara:
                        xw.removeFinalNewline( True )
                        xw.writeLineClose( 'para' )
                        haveOpenPara = False
                    if not adjText: xw.writeLineOpen( 'para', ('style',originalMarker) )
                    else:
                        xw.writeLineOpenText( 'para', handleInternalTextMarkersForUSX3(adjText), ('style',originalMarker), noTextCheck=True ) # no checks coz might already have embedded XML
                    haveOpenPara = paraJustOpened = True
                else:
                    #assert getMarkerContentType == 'A' # A = always, e.g.,  ide, mt, h, s, ip, etc.
                    if getMarkerContentType != 'A':
                        logger.error( "BibleWriter.toUSX3XML: ToProgrammer — should be 'A': {!r} is {!r} Why?".format( marker, getMarkerContentType ) )
                    if haveOpenPara:
                        xw.removeFinalNewline( True )
                        xw.writeLineClose( 'para' )
                        haveOpenPara = False
                    xw.writeLineOpenClose( 'para', handleInternalTextMarkersForUSX3(adjText), ('style',originalMarker if originalMarker else marker), noTextCheck=True ) # no checks coz might already have embedded XML
            if haveOpenPara:
                xw.removeFinalNewline( True )
                xw.writeLineClose( 'para' )
            xw.writeLineClose( 'usx' )
            xw.close( writeFinalNL=True ) # Try to imitate Paratext output as closely as possible
            if validationSchema: return xw.validate( validationSchema ) # Returns a 3-tuple: intCode, logString, errorLogString
        # end of toUSX3XML.writeUSXBook

        # Set-up our Bible reference system
        if 'PublicationCode' not in controlDict or controlDict['PublicationCode'] == 'GENERIC':
            BOS = self.genericBOS
            BRL = self.genericBRL
        else:
            BOS = BibleOrganisationalSystem( controlDict['PublicationCode'] )
            BRL = BibleReferenceList( BOS, BibleObject=None )

        if BibleOrgSysGlobals.verbosityLevel > 2: print( _("  Exporting to USX format…") )
        #USXOutputFolder = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( "USX output/' )
        #if not os.access( USXOutputFolder, os.F_OK ): os.mkdir( USXOutputFolder ) # Make the empty folder if there wasn't already one there

        validationResults = ( 0, '', '', ) # xmllint result code, program output, error output
        for BBB,bookData in self.books.items():
            bookResults = writeUSXBook( BBB, bookData )
            if validationSchema:
                if bookResults[0] > validationResults[0]: validationResults = ( bookResults[0], validationResults[1], validationResults[2], )
                if bookResults[1]: validationResults = ( validationResults[0], validationResults[1] + bookResults[1], validationResults[2], )
                if bookResults[2]: validationResults = ( validationResults[0], validationResults[1], validationResults[2] + bookResults[2], )
        if validationSchema:
            if validationResults[0] > 0:
                with open( os.path.join( outputFolderpath, 'ValidationErrors.txt' ), 'wt', encoding='utf-8' ) as veFile:
                    if validationResults[1]: veFile.write( validationResults[1] + '\n\n\n' ) # Normally empty
                    if validationResults[2]: veFile.write( validationResults[2] )

        if ignoredMarkers:
            logger.info( "toUSX3XML: Ignored markers were {}".format( ignoredMarkers ) )
            if BibleOrgSysGlobals.verbosityLevel > 2:
                print( "  " + _("ERROR: Ignored toUSX3XML markers were {}").format( ignoredMarkers ) )
        if unhandledMarkers:
            logger.error( "toUSX3XML: Unhandled markers were {}".format( unhandledMarkers ) )
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print( "  " + _("ERROR: Unhandled toUSX3XML markers were {}").format( unhandledMarkers ) )
        if unhandledBooks:
            logger.warning( "toUSX3XML: Unhandled books were {}".format( unhandledBooks ) )
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print( "  " + _("WARNING: Unhandled toUSX3XML books were {}").format( unhandledBooks ) )

        # Now create a zipped collection
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Zipping USX3 files…" )
        zf = zipfile.ZipFile( os.path.join( outputFolderpath, 'AllUSX3Files.zip' ), 'w', compression=zipfile.ZIP_DEFLATED )
        for filename in os.listdir( filesFolder ):
            #if not filename.endswith( '.zip' ):
            filepath = os.path.join( filesFolder, filename )
            zf.write( filepath, filename ) # Save in the archive without the path
        zf.close()
        # Now create the gzipped file
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  GZipping USX3 files…" )
        tar = tarfile.open( os.path.join( outputFolderpath, 'AllUSX3Files.gzip' ), 'w:gz' )
        for filename in os.listdir( filesFolder ):
            if filename.endswith( '.usx' ):
                filepath = os.path.join( filesFolder, filename )
                tar.add( filepath, arcname=filename, recursive=False )
        tar.close()
        # Now create the bz2 file
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  BZipping USX3 files…" )
        tar = tarfile.open( os.path.join( outputFolderpath, 'AllUSX3Files.bz2' ), 'w:bz2' )
        for filename in os.listdir( filesFolder ):
            if filename.endswith( '.usx' ):
                filepath = os.path.join( filesFolder, filename )
                tar.add( filepath, arcname=filename, recursive=False )
        tar.close()

        if BibleOrgSysGlobals.verbosityLevel > 0 and BibleOrgSysGlobals.maxProcesses > 1:
            print( "  BibleWriter.toUSX3XML finished successfully." )
        if validationSchema: return validationResults
        return True
    # end of BibleWriter.toUSX3XML



    def toUSFXXML( self, outputFolderpath:Optional[Path]=None, controlDict=None, validationSchema=None ):
        """
        Using settings from the given control file,
            converts the USFM information to UTF-8 USFX XML files.

        If a schema is given (either a path or URL), the XML output files are validated.
        """
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Running BibleWriter:toUSFXXML…" )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert self.books

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolderpath: outputFolderpath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_USFX_Export/' )
        if not os.access( outputFolderpath, os.F_OK ): os.makedirs( outputFolderpath ) # Make the empty folder if there wasn't already one there
        if not controlDict:
            controlDict, defaultControlFilename = {}, "To_USFX_controls.txt"
            try: ControlFiles.readControlFile( defaultControlFolderpath, defaultControlFilename, controlDict )
            except FileNotFoundError:
                logger.critical( "Unable to read control dict {} from {}".format( defaultControlFilename, defaultControlFolderpath ) )
        self.__adjustControlDict( controlDict )
        if not validationSchema: # We'll use our copy
            xsdFilepath = 'ExternalSchemas/usfx.xsd'
            if os.path.exists( xsdFilepath ): validationSchema = xsdFilepath

        ignoredMarkers, unhandledMarkers, unhandledBooks = set(), set(), []

        def writeUSFXBook( xw, BBB, bkData ):
            """ Writes a book to the given USFX XML writerObject. """

            def handleInternalTextMarkersForUSFX( originalText ):
                """
                Handles character formatting markers within the originalText.
                Tries to find pairs of markers and replaces them with html char segments.
                """
                if not originalText: return ''
                if '\\' not in originalText: return originalText
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( "toUSFXXML:hITM4USFX:", BBB, C, V, marker, "'"+originalText+"'" )
                markerList = sorted( BibleOrgSysGlobals.loadedUSFMMarkers.getMarkerListFromText( originalText ),
                                            key=lambda s: -len(s[4])) # Sort by longest characterContext first (maximum nesting)
                for insideMarker, iMIndex, nextSignificantChar, fullMarker, characterContext, endIndex, markerField in markerList: # check for internal markers
                    pass

                # Old code
                adjText = originalText
                haveOpenChar = False
                for charMarker in ALL_CHAR_MARKERS:
                    #print( "handleInternalTextMarkersForUSFX", charMarker )
                    # Handle USFM character markers
                    fullCharMarker = '\\' + charMarker + ' '
                    if fullCharMarker in adjText:
                        if haveOpenChar:
                            adjText = adjText.replace( 'CLOSED_BIT', ' closed="false"' ) # Fix up closed bit since it wasn't closed
                            logger.info( "toUSFXXML: USFX export had to close automatically in {} {}:{} {}:{!r} now {!r}".format( BBB, C, V, marker, originalText, adjText ) ) # The last marker presumably only had optional closing (or else we just messed up nesting markers)
                        adjText = adjText.replace( fullCharMarker, '{}<char style="{}"CLOSED_BIT>'.format( '</char>' if haveOpenChar else '', charMarker ) )
                        haveOpenChar = True
                    endCharMarker = '\\' + charMarker + '*'
                    if endCharMarker in adjText:
                        if not haveOpenChar: # Then we must have a missing open marker (or extra closing marker)
                            logger.error( "toUSFXXML: Ignored extra {!r} closing marker in {} {}:{} {}:{!r} now {!r}".format( charMarker, BBB, C, V, marker, originalText, adjText ) )
                            adjText = adjText.replace( endCharMarker, '' ) # Remove the unused marker
                        else: # looks good
                            adjText = adjText.replace( 'CLOSED_BIT', '' ) # Fix up closed bit since it was specifically closed
                            adjText = adjText.replace( endCharMarker, '</char>' )
                            haveOpenChar = False
                if haveOpenChar:
                    adjText = adjText.replace( 'CLOSED_BIT', ' closed="false"' ) # Fix up closed bit since it wasn't closed
                    adjText += '{}</char>'.format( '' if adjText[-1]==' ' else ' ')
                    logger.info( "toUSFXXML: Had to close automatically in {} {}:{} {}:{!r} now {!r}".format( BBB, C, V, marker, originalText, adjText ) )
                if '\\' in adjText: logger.critical( "toUSFXXML: Didn't handle a backslash in {} {}:{} {}:{!r} now {!r}".format( BBB, C, V, marker, originalText, adjText ) )
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
                                if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not xtOpen
                                USFXxrefXML += ' closed="false">' + adjToken + '</char>'
                                xoOpen = False
                            if xtOpen: # if we have multiple cross-references one after the other
                                USFXxrefXML += ' closed="false">' + adjToken + '</char>'
                                xtOpen = False
                            adjToken = token[3:]
                            USFXxrefXML += '<char style="xo"'
                            xoOpen = True
                        elif lcToken.startswith('xo*'):
                            if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert xoOpen and not xtOpen
                            USFXxrefXML += '>' + adjToken + '</char>'
                            xoOpen = False
                        elif lcToken.startswith('xt '): # xref text follows
                            if xtOpen: # Multiple xt's in a row
                                if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not xoOpen
                                USFXxrefXML += ' closed="false">' + adjToken + '</char>'
                            if xoOpen:
                                USFXxrefXML += ' closed="false">' + adjToken + '</char>'
                                xoOpen = False
                            adjToken = token[3:]
                            USFXxrefXML += '<char style="xt"'
                            xtOpen = True
                        elif lcToken.startswith('xt*'):
                            if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert xtOpen and not xoOpen
                            USFXxrefXML += '>' + adjToken + '</char>'
                            xtOpen = False
                        #elif lcToken in ('xo*','xt*','x*',):
                        #    pass # We're being lazy here and not checking closing markers properly
                        else:
                            logger.warning( _("toUSFXXML: Unprocessed {!r} token in {} {}:{} xref {!r}").format( token, BBB, C, V, USFXxref ) )
                    if xoOpen:
                        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not xtOpen
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
                                if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not fTextOpen
                                logger.error( _("toUSFXXML: Two consecutive fr fields in {} {}:{} footnote {!r}").format( token, BBB, C, V, USFXfootnote ) )
                            if fTextOpen:
                                if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not frOpen
                                USFXfootnoteXML += ' closed="false">' + adjToken + '</char>'
                                fTextOpen = False
                            if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not fCharOpen
                            adjToken = token[3:]
                            USFXfootnoteXML += '<char style="fr"'
                            frOpen = True
                        elif lcToken.startswith('fr* '):
                            if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert frOpen and not fTextOpen and not fCharOpen
                            USFXfootnoteXML += '>' + adjToken + '</char>'
                            frOpen = False
                        elif lcToken.startswith('ft ') or lcToken.startswith('fq ') or lcToken.startswith('fqa ') or lcToken.startswith('fv ') or lcToken.startswith('fk '):
                            if fCharOpen:
                                if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not frOpen
                                USFXfootnoteXML += '>' + adjToken + '</char>'
                                fCharOpen = False
                            if frOpen:
                                if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not fTextOpen
                                USFXfootnoteXML += ' closed="false">' + adjToken + '</char>'
                                frOpen = False
                            if fTextOpen:
                                USFXfootnoteXML += ' closed="false">' + adjToken + '</char>'
                                fTextOpen = False
                            fMarker = lcToken.split()[0] # Get the bit before the space
                            USFXfootnoteXML += '<char style="{}"'.format( fMarker )
                            adjToken = token[len(fMarker)+1:] # Get the bit after the space
                            #print( "{!r} {!r}".format( fMarker, adjToken ) )
                            fTextOpen = True
                        elif lcToken.startswith('ft*') or lcToken.startswith('fq*') or lcToken.startswith('fqa*') or lcToken.startswith('fv*') or lcToken.startswith('fk*'):
                            #if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert fTextOpen and not frOpen and not fCharOpen
                            if frOpen or fCharOpen or not fTextOpen:
                                logger.error( "toUSFXXML.processFootnote: Problem at {} {}:{} in footnote {!r}".format( BBB, C, V, USFXfootnote ) )
                            USFXfootnoteXML += '>' + adjToken + '</char>'
                            fTextOpen = False
                        else: # Could be character formatting (or closing of character formatting)
                            subTokens = lcToken.split()
                            firstToken = subTokens[0]
                            #print( "ft", firstToken )
                            if firstToken in ALL_CHAR_MARKERS: # Yes, confirmed
                                if fCharOpen: # assume that the last one is closed by this one
                                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not frOpen
                                    USFXfootnoteXML += '>' + adjToken + '</char>'
                                    fCharOpen = False
                                if frOpen:
                                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not fCharOpen
                                    USFXfootnoteXML += ' closed="false">' + adjToken + '</char>'
                                    frOpen = False
                                USFXfootnoteXML += '<char style="{}"'.format( firstToken )
                                adjToken = token[len(firstToken)+1:] # Get the bit after the space
                                fCharOpen = firstToken
                            else: # The problem is that a closing marker doesn't have to be followed by a space
                                if firstToken[-1]=='*' and firstToken[:-1] in ALL_CHAR_MARKERS: # it's a closing tag (that was followed by a space)
                                    if fCharOpen:
                                        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not frOpen
                                        if not firstToken.startswith( fCharOpen+'*' ): # It's not a matching tag
                                            logger.warning( _("toUSFXXML: {!r} closing tag doesn't match {!r} in {} {}:{} footnote {!r}").format( firstToken, fCharOpen, BBB, C, V, USFXfootnote ) )
                                        USFXfootnoteXML += '>' + adjToken + '</char>'
                                        fCharOpen = False
                                    logger.warning( _("toUSFXXML: {!r} closing tag doesn't match in {} {}:{} footnote {!r}").format( firstToken, BBB, C, V, USFXfootnote ) )
                                else:
                                    ixAS = firstToken.find( '*' )
                                    #print( firstToken, ixAS, firstToken[:ixAS] if ixAS!=-1 else '' )
                                    if ixAS!=-1 and ixAS<4 and firstToken[:ixAS] in ALL_CHAR_MARKERS: # it's a closing tag
                                        if fCharOpen:
                                            if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not frOpen
                                            if not firstToken.startswith( fCharOpen+'*' ): # It's not a matching tag
                                                logger.warning( _("toUSFXXML: {!r} closing tag doesn't match {!r} in {} {}:{} footnote {!r}").format( firstToken, fCharOpen, BBB, C, V, USFXfootnote ) )
                                            USFXfootnoteXML += '>' + adjToken + '</char>'
                                            fCharOpen = False
                                        logger.warning( _("toUSFXXML: {!r} closing tag doesn't match in {} {}:{} footnote {!r}").format( firstToken, BBB, C, V, USFXfootnote ) )
                                    else:
                                        logger.warning( _("toUSFXXML: Unprocessed {!r} token in {} {}:{} footnote {!r}").format( firstToken, BBB, C, V, USFXfootnote ) )
                                        #print( ALL_CHAR_MARKERS )
                                        #halt
                    #print( "  ", frOpen, fCharOpen, fTextOpen )
                    if frOpen:
                        logger.warning( _("toUSFXXML: Unclosed 'fr' token in {} {}:{} footnote {!r}").format( BBB, C, V, USFXfootnote) )
                        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not fCharOpen and not fTextOpen
                        USFXfootnoteXML += ' closed="false">' + adjToken + '</char>'
                    if fCharOpen: logger.warning( _("toUSFXXML: Unclosed {!r} token in {} {}:{} footnote {!r}").format( fCharOpen, BBB, C, V, USFXfootnote) )
                    if fTextOpen: USFXfootnoteXML += ' closed="false">' + adjToken + '</char>'
                    USFXfootnoteXML += '</f>'
                    #print( '', USFXfootnote, USFXfootnoteXML )
                    return USFXfootnoteXML
                # end of toUSFXXML.processFootnote


                adjText = text
                if extras:
                    offset = 0
                    for extra in extras: # do any footnotes and cross-references
                        extraType, extraIndex, extraText, cleanExtraText = extra
                        #print( "{} {}:{} Text={!r} eT={}, eI={}, eText={!r}".format( BBB, C, V, text, extraType, extraIndex, extraText ) )
                        adjIndex = extraIndex - offset
                        lenT = len( adjText )
                        if adjIndex > lenT: # This can happen if we have verse/space/notes at end (and the space was deleted after the note was separated off)
                            logger.warning( _("toUSFXXML: Space before note at end of verse in {} {}:{} has been lost").format( BBB, C, V ) )
                            # No need to adjust adjIndex because the code below still works
                        elif adjIndex<0 or adjIndex>lenT: # The extras don't appear to fit correctly inside the text
                            print( "toUSFXXML: Extras don't fit inside verse at {} {}:{}: eI={} o={} len={} aI={}".format( BBB, C, V, extraIndex, offset, len(text), adjIndex ) )
                            print( "  Verse={!r}".format( text ) )
                            print( "  Extras={!r}".format( extras ) )
                        #assert 0 <= adjIndex <= len(verse)
                        #adjText = checkText( extraText, checkLeftovers=False ) # do any general character formatting
                        #if adjText!=extraText: print( "processXRefsAndFootnotes: {}@{}-{}={} {!r} now {!r}".format( extraType, extraIndex, offset, adjIndex, extraText, adjText ) )
                        if extraType == 'fn':
                            extra = processFootnote( extraText )
                            #print( "fn got", extra )
                        elif extraType == 'xr':
                            extra = processXRef( extraText )
                            #print( "xr got", extra )
                        elif extraType == 'fig':
                            logger.critical( "USXFXML figure not handled yet" )
                            extra = '' # temp
                            #extra = processFigure( extraText )
                            #print( "fig got", extra )
                        elif extraType == 'str':
                            extra = '' # temp
                        elif extraType == 'sem':
                            extra = '' # temp
                        elif extraType == 'vp':
                            extra = "\\vp {}\\vp*".format( extraText ) # Will be handled later
                        elif BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( extraType ); halt
                        #print( "was", verse )
                        adjText = adjText[:adjIndex] + str(extra) + adjText[adjIndex:]
                        offset -= len( extra )
                        #print( "now", verse )
                return adjText
            # end of toUSFXXML.handleNotes

            USFXAbbrev = BibleOrgSysGlobals.loadedBibleBooksCodes.getUSFMAbbreviation( BBB ).upper()
            if not USFXAbbrev:
                logger.error( "toUSFXXML: Can't write {} USFX book because no USFM code available".format( BBB ) )
                unhandledBooks.append( BBB )
                return

            version = 2
            xtra = ' ' if version<2 else ''
            C, V = '-1', '-1' # So first/id line starts at -1:0
            xw.writeLineOpen( 'book', ('id',USFXAbbrev) )
            haveOpenPara = paraJustOpened = False
            gotVP = None
            for processedBibleEntry in bkData._processedLines: # Process internal Bible data lines
                marker, originalMarker, text, extras = processedBibleEntry.getMarker(), processedBibleEntry.getOriginalMarker(), processedBibleEntry.getAdjustedText(), processedBibleEntry.getExtras()
                if '¬' in marker or marker in BOS_ADDED_NESTING_MARKERS or marker=='v=':
                    continue # Just ignore added markers — not needed here
                if marker in USFM_PRECHAPTER_MARKERS:
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
                        assert C=='-1' or marker=='rem' or marker.startswith('mte')
                    V = str( int(V) + 1 )
                getMarkerContentType = BibleOrgSysGlobals.loadedUSFMMarkers.getMarkerContentType( marker )
                #print( BBB, C, V, marker, getMarkerContentType, haveOpenPara, paraJustOpened )

                adjText = handleNotes( text, extras )
                if marker == 'id':
                    if haveOpenPara: # This should never happen coz the ID line should have been the first line in the file
                        logger.error( "toUSFXXML: Book {}{} has a id line inside an open paragraph: {!r}".format( BBB, " ({})".format(USFXAbbrev) if USFXAbbrev!=BBB else '', adjText ) )
                        xw.removeFinalNewline( True )
                        xw.writeLineClose( 'p' )
                        haveOpenPara = False
                    adjTxLen = len( adjText )
                    if adjTxLen<3 or (adjTxLen>3 and adjText[3]!=' '): # Doesn't seem to have a standard BBB at the beginning of the ID line
                        logger.warning( "toUSFXXML: Book {}{} has a non-standard id line: {!r}".format( BBB, " ({})".format(USFXAbbrev) if USFXAbbrev!=BBB else '', adjText ) )
                    if adjText[0:3] != USFXAbbrev:
                        logger.error( "toUSFXXML: Book {}{} might be incorrect — we got: {!r}".format( BBB, " ({})".format(USFXAbbrev) if USFXAbbrev!=BBB else '', adjText[0:3] ) )
                    adjText = adjText[4:] # Remove the book code from the ID line because it's put in as an attribute
                    if adjText: xw.writeLineOpenClose( 'id', handleInternalTextMarkersForUSFX(adjText)+xtra, ('code',USFXAbbrev) )
                    elif not text: logger.error( "toUSFXXML: {} {}:{} has a blank id line that was ignored".format( BBB, C, V ) )

                elif marker == 'c':
                    if haveOpenPara:
                        xw.removeFinalNewline( True )
                        xw.writeLineClose( 'p' )
                        haveOpenPara = False
                    #print( BBB, 'C', repr(text), repr(adjText) )
                    C, V = text, '0' # not adjText!
                    xw.writeLineOpenSelfclose ( 'c', ('id',C) )
                    if adjText != text:
                        logger.warning( "toUSFXXML: Lost additional note text on c for {} {!r}".format( BBB, C ) )
                elif marker == 'c~': # Don't really know what this stuff is!!!
                    if not adjText: logger.warning( "toUSFXXML: Missing text for c~" ); continue
                    # TODO: We haven't stripped out character fields from within the text — not sure how USFX handles them yet
                    xw.removeFinalNewline( True )
                    xw.writeLineText( handleInternalTextMarkersForUSFX(adjText)+xtra, noTextCheck=True ) # no checks coz might already have embedded XML
                elif marker == 'c#': # Chapter number added for printing
                    ignoredMarkers.add( marker ) # Just ignore it completely
                elif marker == 'vp#': # This precedes a v field and has the verse number to be printed
                    gotVP = adjText # Just remember it for now
                elif marker == 'v':
                    V = adjText
                    if gotVP: # this is the verse number to be published
                        adjText = gotVP
                        gotVP = None
                    if paraJustOpened: paraJustOpened = False
                    else:
                        xw.removeFinalNewline( True )
                     # Remove anything that'll cause a big XML problem later
                    if adjText:
                        xw.writeLineOpenSelfclose ( 'v', ('id',adjText.replace('<','').replace('>','').replace('"','')) )

                elif marker in ('v~','p~',):
                    if not adjText: logger.warning( "toUSFXXML: Missing text for {}".format( marker ) ); continue
                    # TODO: We haven't stripped out character fields from within the verse — not sure how USFX handles them yet
                    xw.removeFinalNewline( True )
                    xw.writeLineText( handleInternalTextMarkersForUSFX(adjText)+xtra, noTextCheck=True ) # no checks coz might already have embedded XML
                elif getMarkerContentType == 'N': # N = never, e.g., b, nb
                    if haveOpenPara:
                        xw.removeFinalNewline( True )
                        xw.writeLineClose( 'p' )
                        haveOpenPara = False
                    if adjText:
                        logger.error( "toUSFXXML: {} {}:{} has a {} line containing text ({!r}) that was ignored".format( BBB, C, V, originalMarker, adjText ) )
                    xw.writeLineOpenSelfclose ( marker )
                elif getMarkerContentType == 'S': # S = sometimes, e.g., p,pi,q,q1,q2,q3,q4,m
                    if haveOpenPara:
                        xw.removeFinalNewline( True )
                        xw.writeLineClose( 'p' )
                        haveOpenPara = False
                    if not adjText: xw.writeLineOpen( originalMarker )
                    else:
                        xw.writeLineOpenText( originalMarker, handleInternalTextMarkersForUSFX(adjText)+xtra, noTextCheck=True ) # no checks coz might already have embedded XML
                    haveOpenPara = paraJustOpened = True
                else:
                    #assert getMarkerContentType == 'A' # A = always, e.g.,  ide, mt, h, s, ip, etc.
                    if getMarkerContentType != 'A':
                        logger.debug( "BibleWriter.toUSFXXML: ToProgrammer — should be 'A': {!r} is {!r} Why?".format( marker, getMarkerContentType ) )
                    if haveOpenPara:
                        xw.removeFinalNewline( True )
                        xw.writeLineClose( 'p' )
                        haveOpenPara = False
                    xw.writeLineOpenClose( marker, handleInternalTextMarkersForUSFX(adjText)+xtra, noTextCheck=True ) # no checks coz might already have embedded XML
            if haveOpenPara:
                xw.removeFinalNewline( True )
                xw.writeLineClose( 'p' )
            xw.writeLineClose( 'book' )
        # end of toUSFXXML.writeUSFXBook

        # Set-up our Bible reference system
        if 'PublicationCode' not in controlDict or controlDict['PublicationCode'] == 'GENERIC':
            BOS = self.genericBOS
            BRL = self.genericBRL
        else:
            BOS = BibleOrganisationalSystem( controlDict['PublicationCode'] )
            BRL = BibleReferenceList( BOS, BibleObject=None )

        if BibleOrgSysGlobals.verbosityLevel > 2: print( _("  Exporting to USFX XML format…") )
        #USFXOutputFolder = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( "USFX output/' )
        #if not os.access( USFXOutputFolder, os.F_OK ): os.mkdir( USFXOutputFolder ) # Make the empty folder if there wasn't already one there

        try: filename = BibleOrgSysGlobals.makeSafeFilename( controlDict['usfxOutputFilename'] )
        except KeyError: filename = 'Bible.usfx'
        xw = MLWriter( filename, outputFolderpath )
        #xw = MLWriter( BibleOrgSysGlobals.makeSafeFilename( USFXNumber+USFXAbbrev+"_usfx.xml" ), outputFolderpath )
        xw.setHumanReadable( 'All' ) # Can be set to 'All', 'Header', or 'None' — one output file went from None/Header=4.7MB to All=5.7MB
        xw.spaceBeforeSelfcloseTag = True # Try to imitate Haiola output as closely as possible
        #xw.start( lineEndings='w', writeBOM=True ) # Try to imitate Haiola output as closely as possible
        xw.start()
        xw.writeLineOpen( 'usfx', [('xmlns:xsi',"http://eBible.org/usfx.xsd"), ('xsi:noNamespaceSchemaLocation',"usfx-2013-08-05.xsd")] )
        languageCode = self.getSetting( 'ISOLanguageCode' )
        #if languageCode is None and 'Language' in self.settingsDict and len(self.settingsDict['Language'])==3:
            #languageCode = self.settingsDict['Language']
        if languageCode: xw.writeLineOpenClose( 'languageCode', languageCode )
        for BBB,bookData in self.books.items(): # Process each Bible book
            writeUSFXBook( xw, BBB, bookData )
        xw.writeLineClose( 'usfx' )
        xw.close()
        if validationSchema: validationResults = xw.validate( validationSchema ) # Returns a 3-tuple: intCode, logString, errorLogString

        if ignoredMarkers:
            logger.info( "toUSFXXML: Ignored markers were {}".format( ignoredMarkers ) )
            if BibleOrgSysGlobals.verbosityLevel > 2:
                print( "  " + _("WARNING: Ignored toUSFXXML markers were {}").format( ignoredMarkers ) )
        if unhandledMarkers:
            logger.warning( "toUSFXXML: Unhandled markers were {}".format( unhandledMarkers ) )
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print( "  " + _("WARNING: Unhandled toUSFXXML markers were {}").format( unhandledMarkers ) )
        if unhandledBooks:
            logger.warning( "toUSFXXML: Unhandled books were {}".format( unhandledBooks ) )
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print( "  " + _("WARNING: Unhandled toUSFXXML books were {}").format( unhandledBooks ) )

        # Now create a zipped version
        filepath = os.path.join( outputFolderpath, filename )
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Zipping {} USFX file…".format( filename ) )
        zf = zipfile.ZipFile( filepath+'.zip', 'w', compression=zipfile.ZIP_DEFLATED )
        zf.write( filepath, filename )
        zf.close()

        if BibleOrgSysGlobals.verbosityLevel > 0 and BibleOrgSysGlobals.maxProcesses > 1:
            print( "  BibleWriter.toUSFXXML finished successfully." )
        if validationSchema: return validationResults # Returns a 3-tuple: intCode, logString, errorLogString
        return True
    # end of BibleWriter.toUSFXXML



    def _writeSwordLocale( self, name, description, BibleOrganisationalSystem, getBookNameFunction, localeFilepath ):
        """
        Writes a UTF-8 Sword locale file containing the book names and abbreviations.
        """
        if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Writing Sword locale file {}…").format(localeFilepath) )

        with open( localeFilepath, 'wt', encoding='utf-8' ) as SwLocFile:
            SwLocFile.write( '[Meta]\nName={}\n'.format( name ) )
            SwLocFile.write( 'Description={}\n'.format( description ) )
            SwLocFile.write( 'Encoding=UTF-8\n\n[Text]\n' )

            # This first section contains EnglishBookName=VernacularBookName
            bookList = []
            for BBB in BibleOrganisationalSystem.getBookList():
                if BBB in self.books:
                    vernacularName = getBookNameFunction(BBB)
                    SwLocFile.write( '{}={}\n'.format( BibleOrgSysGlobals.loadedBibleBooksCodes.getEnglishName_NR(BBB), vernacularName ) ) # Write the first English book name and the language book name
                    bookList.append( vernacularName )

            # This second section contains many VERNACULARABBREV=SwordBookAbbrev
            SwLocFile.write( '\n[Book Abbrevs]\n' )
            abbreviationList = []
            for BBB in BibleOrganisationalSystem.getBookList(): # First pass writes the full vernacular book names (with and without spaces removed)
                if BBB in self.books:
                    swordAbbrev = BibleOrgSysGlobals.loadedBibleBooksCodes.getSwordAbbreviation( BBB )
                    vernacularName = getBookNameFunction(BBB).upper()
                    #assert vernacularName not in abbreviationList
                    if vernacularName in abbreviationList:
                        if BibleOrgSysGlobals.debugFlag:
                            print( "BibleWriter._writeSwordLocale: ToProgrammer — vernacular name IS in abbreviationList — what does this mean? Why? {!r} {}".format( vernacularName, abbreviationList ) )
                        logger.debug( "BibleWriter._writeSwordLocale: ToProgrammer — vernacular name IS in abbreviationList — what does this mean? Why? {!r} {}".format( vernacularName, abbreviationList ) )
                    SwLocFile.write( '{}={}\n'.format( vernacularName, swordAbbrev ) ) # Write the UPPER CASE language book name and the Sword abbreviation
                    abbreviationList.append( vernacularName )
                    if ' ' in vernacularName:
                        vernacularAbbrev = vernacularName.replace( ' ', '' )
                        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: assert vernacularAbbrev not in abbreviationList
                        SwLocFile.write( '{}={}\n'.format( vernacularAbbrev, swordAbbrev ) ) # Write the UPPER CASE language book name and the Sword abbreviation
                        abbreviationList.append( vernacularAbbrev )
            for BBB in BibleOrganisationalSystem.getBookList(): # Second pass writes the shorter vernacular book abbreviations
                if BBB in self.books:
                    swordAbbrev = BibleOrgSysGlobals.loadedBibleBooksCodes.getSwordAbbreviation( BBB )
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
                            else: logger.warning( "   Oops, shouldn't have written {} (also could be {}) to Sword locale file".format( vernacularAbbrev, swordAbbrev ) ) # Need to fix this
                        else:
                            SwLocFile.write( '{}={}\n'.format( vernacularAbbrev, swordAbbrev ) ) # Write the UPPER CASE language book name and the Sword abbreviation
                            abbreviationList.append( vernacularAbbrev )
                    changed = False
                    for somePunct in ".''̉΄": # Remove punctuation and glottals (all UPPER CASE here)
                        if somePunct in vernacularAbbrev:
                            vernacularAbbrev = vernacularAbbrev.replace( somePunct, '' )
                            changed = True
                    if changed:
                        if vernacularAbbrev in abbreviationList:
                            logger.warning( "   Oops, maybe shouldn't have written {} (also could be {}) to Sword locale file".format( vernacularAbbrev, swordAbbrev ) )
                        else:
                            SwLocFile.write( '{}={}\n'.format( vernacularAbbrev, swordAbbrev ) )
                            abbreviationList.append( vernacularAbbrev )
                        changed = False
                    for vowel in 'AΆÁÂÃÄÅEÈÉÊËIÌÍÎÏOÒÓÔÕÖUÙÚÛÜ': # Remove vowels (all UPPER CASE here)
                        if vowel in vernacularAbbrev:
                            vernacularAbbrev = vernacularAbbrev.replace( vowel, '' )
                            changed = True
                    if changed:
                        if vernacularAbbrev in abbreviationList:
                            logger.warning( "   Oops, maybe shouldn't have written {} (also could be {}) to Sword locale file".format( vernacularAbbrev, swordAbbrev ) )
                        else:
                            SwLocFile.write( '{}={}\n'.format( vernacularAbbrev, swordAbbrev ) )
                            abbreviationList.append( vernacularAbbrev )

        if BibleOrgSysGlobals.verbosityLevel > 1: print( _("  Wrote {} book names and {} abbreviations.").format( len(bookList), len(abbreviationList) ) )
    # end of BibleWriter._writeSwordLocale



    def toOSISXML( self, outputFolderpath:Optional[Path]=None, controlDict=None, validationSchema=None ):
        """
        Using settings from the given control file,
            converts the USFM information to one or more UTF-8 OSIS XML files.

        If a schema is given (either a path or URL), the XML output file(s) is validated.

        TODO: We're not consistent about handling errors: sometimes we use assert, sometime raise (both of which abort the program), and sometimes log errors or warnings.
        """
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Running BibleWriter:toOSISXML…" )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert self.books

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolderpath: outputFolderpath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_OSIS_Export/' )
        if not os.access( outputFolderpath, os.F_OK ): os.makedirs( outputFolderpath ) # Make the empty folder if there wasn't already one there
        if not controlDict:
            controlDict, defaultControlFilename = {}, "To_OSIS_controls.txt"
            try: ControlFiles.readControlFile( defaultControlFolderpath, defaultControlFilename, controlDict )
            except FileNotFoundError:
                logger.critical( "Unable to read control dict {} from {}".format( defaultControlFilename, defaultControlFolderpath ) )
        self.__adjustControlDict( controlDict )
        if not validationSchema: # We'll use our copy
            xsdFilepath = 'ExternalSchemas/osisCore.2.1.1.xsd'
            if os.path.exists( xsdFilepath ): validationSchema = xsdFilepath

        # Set-up our Bible reference system
        #if BibleOrgSysGlobals.debugFlag: print( "BibleWriter:toOSISXML publicationCode =", controlDict['PublicationCode'] )
        if 'PublicationCode' not in controlDict or controlDict['PublicationCode'] == 'GENERIC':
            BOS = self.genericBOS
            BRL = self.genericBRL
        else:
            BOS = BibleOrganisationalSystem( controlDict['PublicationCode'] )
            BRL = BibleReferenceList( BOS, BibleObject=None )

        booksNamesSystemName = BOS.getOrganisationalSystemValue( 'booksNamesSystem' )
        if booksNamesSystemName and booksNamesSystemName!='None' and booksNamesSystemName!='Unknown': # default (if we know the book names system)
            getBookNameFunction = BOS.getBookName
            getBookAbbreviationFunction = BOS.getBookAbbreviation
        else: # else use our local functions from our deduced book names
            getBookNameFunction = self.getAssumedBookName # from BibleOrgSys.Formats.USFMBible (which gets it from BibleOrgSys.Formats.USFMBibleBook)
            getBookAbbreviationFunction = BibleOrgSysGlobals.loadedBibleBooksCodes.getOSISAbbreviation

        ignoredMarkers, unhandledMarkers, unhandledBooks = set(), set(), []

        # Let's write a Sword locale while we're at it — might be useful if we make a Sword module from this OSIS file
        try: xlg = controlDict['xmlLanguage']
        except KeyError: xlg = 'eng'
        try: ln = controlDict['LanguageName']
        except KeyError: ln = 'eng'
        self._writeSwordLocale( xlg, ln, BOS, getBookNameFunction, os.path.join( outputFolderpath, 'SwLocale-utf8.conf' ) )
        #if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Writing Sword locale file {}…").format(SwLocFilepath) )
        #with open( SwLocFilepath, 'wt', encoding='utf-8' ) as SwLocFile:
            #SwLocFile.write( '[Meta]\nName={}\n'.format(controlDict['xmlLanguage']) )
            #SwLocFile.write( 'Description={}\n'.format(controlDict['LanguageName']) )
            #SwLocFile.write( 'Encoding=UTF-8\n\n[Text]\n' )
            #for BBB in BOS.getBookList():
                #if BBB in self.books:
                    #SwLocFile.write( '{}={}\n'.format(BibleOrgSysGlobals.loadedBibleBooksCodes.getEnglishName_NR(BBB), getBookNameFunction(BBB) ) ) # Write the first English book name and the language book name
            #SwLocFile.write( '\n[Book Abbrevs]\n' )
            #for BBB in BOS.getBookList():
                #if BBB in self.books:
                    #SwLocFile.write( '{}={}\n'.format(BibleOrgSysGlobals.loadedBibleBooksCodes.getEnglishName_NR(BBB).upper(), BibleOrgSysGlobals.loadedBibleBooksCodes.getSwordAbbreviation(BBB) ) ) # Write the UPPER CASE language book name and the Sword abbreviation

        def writeHeader( writerObject ):
            """
            Writes the OSIS header to the OSIS XML writerObject.
            """
            writerObject.writeLineOpen( 'header' )
            try: ow = controlDict['osisWork']
            except KeyError: ow = 'Bible'
            writerObject.writeLineOpen( 'work', ('osisWork', ow) )
            try: tit = controlDict['Title']
            except KeyError: tit = 'Bible'
            writerObject.writeLineOpenClose( 'title', tit )
            writerObject.writeLineOpenClose( 'creator', "BibleWriter.py", ('role',"encoder") )
            writerObject.writeLineOpenClose( 'type',  "Bible", ('type',"OSIS") )
            try: idr = controlDict['Identifier']
            except KeyError: idr = 'XXX'
            writerObject.writeLineOpenClose( 'identifier', idr, ('type',"OSIS") )
            writerObject.writeLineOpenClose( 'scope', "dunno" )
            writerObject.writeLineOpenClose( 'refSystem', "Bible" )
            writerObject.writeLineClose( 'work' )
            # Snowfall software write two work entries ???
            writerObject.writeLineOpen( 'work', ('osisWork',"bible" ) )
            writerObject.writeLineOpenClose( 'creator', "BibleWriter.py", ('role',"encoder") )
            writerObject.writeLineOpenClose( 'type',  "Bible", ('type',"OSIS") )
            writerObject.writeLineOpenClose( 'refSystem', "Bible" )
            writerObject.writeLineClose( 'work' )
            writerObject.writeLineClose( 'header' )
        # end of toOSISXML.writeHeader

        toOSISGlobals = { "verseRef":'', "XRefNum":0, "FootnoteNum":0, "lastRef":'', "OneChapterOSISBookCodes":BibleOrgSysGlobals.loadedBibleBooksCodes.getOSISSingleChapterBooksList() } # These are our global variables


        def writeOSISBook( writerObject, BBB, bkData ):
            """
            Writes a book to the OSIS XML writerObject.
            """

            def checkOSISText( textToCheck, checkLeftovers=True ):
                """
                Handle some general backslash codes and warn about any others still unprocessed.
                """

                def checkOSISTextHelper( marker, helpText ):
                    """ Adjust the text to make the number of start and close markers equal. """
                    count1, count2 = helpText.count('\\'+marker+' '), helpText.count('\\'+marker+'*') # count open and close markers
                    while count1 < count2:
                        helpText = '\\'+marker+' ' + helpText
                        count1, count2 = helpText.count('\\'+marker+' '), helpText.count('\\'+marker+'*') # count open and close markers again
                    while count1 > count2:
                        helpText += '\\'+marker+'*'
                        count1, count2 = helpText.count('\\'+marker+' '), helpText.count('\\'+marker+'*') # count open and close markers again
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert count1 == count2
                    return helpText
                # end of checkOSISTextHelper

                adjText = textToCheck
                if '<<' in adjText or '>>' in adjText:
                    logger.warning( _("toOSIS: Unexpected double angle brackets in {}: {!r} field is {!r}").format( toOSISGlobals['verseRef'], marker, textToCheck ) )
                    adjText = adjText.replace('<<','“' ).replace('>>','”' )
                if '\\bk ' in adjText: adjText = checkOSISTextHelper('bk',adjText).replace('\\bk ','<reference type="x-bookName">').replace('\\bk*','</reference>')
                if '\\ior ' in adjText: adjText = checkOSISTextHelper('ior',adjText).replace('\\ior ','<reference>').replace('\\ior*','</reference>')
                if '\\add ' in adjText: adjText = checkOSISTextHelper('add',adjText).replace('\\add ','<transChange type="added">').replace('\\add*','</transChange>')
                if '\\nd ' in adjText: adjText = checkOSISTextHelper('nd',adjText).replace('\\nd ','<divineName>').replace('\\nd*','</divineName>')
                if '\\wj ' in adjText: adjText = checkOSISTextHelper('wj',adjText).replace('\\wj ','<q who="Jesus" marker="">').replace('\\wj*','</q>')
                if '\\sig ' in adjText: adjText = checkOSISTextHelper('sig',adjText).replace('\\sig ','<signed>').replace('\\sig*','</signed>')
                if '\\it ' in adjText: adjText = checkOSISTextHelper('it',adjText).replace('\\it ','<hi type="italic">').replace('\\it*','</hi>')
                if '\\bd ' in adjText: adjText = checkOSISTextHelper('bd',adjText).replace('\\bd ','<hi type="bold">').replace('\\bd*','</hi>')
                if '\\em ' in adjText: adjText = checkOSISTextHelper('em',adjText).replace('\\em ','<hi type="bold">').replace('\\em*','</hi>')
                if '\\sc ' in adjText: adjText = checkOSISTextHelper('sc',adjText).replace('\\sc ','<hi type="SMALLCAPS">').replace('\\sc*','</hi>') # XXXXXX temp …
                if '\\fig ' in adjText: # Figure is not used in Sword modules so we'll remove it from the OSIS (for now at least)
                    ix1 = adjText.find( '\\fig ' )
                    ix2 = adjText.find( '\\fig*' )
                    if ix2 == -1: logger.error( _("toOSIS: Missing fig end marker for OSIS in {}: {!r} field is {!r}").format( toOSISGlobals['verseRef'], marker, textToCheck ) )
                    else:
                        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert ix2 > ix1
                        #print( "was {!r}".format( adjText ) )
                        adjText = adjText[:ix1] + adjText[ix2+5:] # Remove the \\fig..\\fig* field
                        #print( "now {!r}".format( adjText ) )
                        logger.warning( _("toOSIS: Figure reference removed for OSIS generation in {}: {!r} field").format( toOSISGlobals['verseRef'], marker ) )
                if checkLeftovers and '\\' in adjText:
                    logger.error( _("toOSIS: We still have some unprocessed backslashes for OSIS in {}: {!r} field is {!r}").format( toOSISGlobals['verseRef'], marker, textToCheck ) )
                    #print( _("toOSIS: We still have some unprocessed backslashes for OSIS in {}: {!r} field is {!r}").format( toOSISGlobals['verseRef'], marker, textToCheck ) )
                    adjText = adjText.replace('\\','ENCODING ERROR HERE ' )
                return adjText
            # end of toOSISXML.checkOSISText

            def processXRefsAndFootnotes( verse, extras, offset=0 ):
                """
                Convert cross-references and footnotes and return the adjusted verse text.
                """

                def processXRef( USFMxref ):
                    """
                    Return the OSIS code for the processed cross-reference (xref).

                    NOTE: The parameter here already has the /x and /x* removed.

                    \\x - \\xo 2:2: \\xt Lib 19:9-10; Diy 24:19.\\xt*\\x* (Backslashes are shown doubled here)
                        gives
                    <note type="crossReference" n="1">2:2: <reference>Lib 19:9-10; Diy 24:19.</reference></note> (Crosswire — invalid OSIS — which then needs to be converted)
                    <note type="crossReference" osisRef="Ruth.2.2" osisID="Ruth.2.2!crossreference.1" n="-"><reference type="source" osisRef="Ruth.2.2">2:2: </reference><reference osisRef="-">Lib 19:9-10</reference>; <reference osisRef="Ruth.Diy.24!:19">Diy 24:19</reference>.</note> (Snowfall)
                    \\x - \\xo 3:5: a \\xt Rum 11:1; \\xo b \\xt Him 23:6; 26:5.\\xt*\\x* is more complex still.
                    """
                    #nonlocal BBB
                    toOSISGlobals["XRefNum"] += 1
                    OSISxref = '<note type="crossReference" osisRef="{}" osisID="{}!crossreference.{}">'.format( toOSISGlobals['verseRef'], toOSISGlobals['verseRef'], toOSISGlobals["XRefNum"] )
                    for j,token in enumerate(USFMxref.split('\\')):
                        #print( "toOSIS:processXRef", j, "'"+token+"'", "from", '"'+USFMxref+'"' )
                        lcToken = token.lower()
                        if j==0: # The first token (but the x has already been removed)
                            rest = token.strip()
                            if rest != '+':
                                logger.warning( _("toOSIS1: We got something else here other than plus (probably need to do something with it): {} {!r} from {!r}").format(chapterRef, token, text) )
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
                            else: # j > 1 — this xo field may possibly only contain a letter suffix
                                if len(adjToken)==1 and adjToken in ('b','c','d','e','f','g','h',):
                                    adjToken = selfReference
                                else: # Could be another complete reference
                                    #print( "<<< Programming error here in toOSIS:processXRef for {!r} at {} {}:{}".format( USFMxref, BBB, currentChapterNumberString, verseNumberString )  )
                                    #print( "  '"+lcToken+"'", len(adjToken), "'"+adjToken+"'" )
                                    if len(adjToken)>2 and adjToken[-2]==' ' and adjToken[-1]=='a':
                                        suffixLetter = adjToken[-1]
                                        adjToken = adjToken[:-2] # Remove any suffix (occurs when a cross-reference has multiple (a and b) parts
                                    if adjToken.endswith(':'): adjToken = adjToken[:-1] # Remove any final colon (this is a language dependent hack)
                                    adjToken = getBookAbbreviationFunction(BBB) + ' ' + adjToken # Prepend a book abbreviation for the anchor (will be processed to an OSIS reference later)
                                    selfReference = adjToken
                            osisRef = BRL.parseToOSIS( adjToken, toOSISGlobals['verseRef'] )
                            if osisRef is not None:
                                #print( "  osisRef = {}".format( osisRef ) )
                                OSISxref += '<reference type="source" osisRef="{}">{}</reference>'.format(osisRef,token[3:])
                                if not BRL.containsReference( BBB, currentChapterNumberString, verseNumberString ):
                                    logger.error( _("toOSIS: Cross-reference at {} {}:{} seems to contain the wrong self-reference anchor {!r}").format(BBB,currentChapterNumberString,verseNumberString, token[3:].rstrip()) )
                        elif lcToken.startswith('xt '): # xref text follows
                            xrefText = token[3:]
                            finalPunct = ''
                            while xrefText[-1] in ' ,;.': finalPunct = xrefText[-1] + finalPunct; xrefText = xrefText[:-1]
                            #adjString = xrefText[:-6] if xrefText.endswith( ' (LXX)' ) else xrefText # Sorry, this is a crude hack to avoid unnecessary error messages
                            osisRef = BRL.parseToOSIS( xrefText, toOSISGlobals['verseRef'] )
                            if osisRef is not None:
                                OSISxref += '<reference type="source" osisRef="{}">{}</reference>'.format(osisRef,xrefText+finalPunct)
                        elif lcToken.startswith('x '): # another whole xref entry follows
                            rest = token[2:].strip()
                            if rest != '+':
                                logger.warning( _("toOSIS2: We got something else here other than plus (probably need to do something with it): {} {!r} from {!r}").format(chapterRef, token, text) )
                        elif lcToken in ('xo*','xt*','x*',):
                            pass # We're being lazy here and not checking closing markers properly
                        else:
                            logger.warning( _("toOSIS: Unprocessed {!r} token in {} xref {!r}").format( token, toOSISGlobals['verseRef'], USFMxref ) )
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
                    OSISfootnote = '<note osisRef="{}" osisID="{}!footnote.{}">'.format( toOSISGlobals['verseRef'], toOSISGlobals['verseRef'], toOSISGlobals["FootnoteNum"] )
                    for j,token in enumerate(USFMfootnote.split('\\')):
                        #print( "processFootnote", j, token, USFMfootnote )
                        lcToken = token.lower()
                        if j==0: continue # ignore the + for now
                        elif lcToken.startswith('fr '): # footnote reference follows
                            adjToken = token[3:].strip()
                            if adjToken.endswith(':'): adjToken = adjToken[:-1] # Remove any final colon (this is a language dependent hack)
                            adjToken = getBookAbbreviationFunction(BBB) + ' ' + adjToken # Prepend a book abbreviation for the anchor (will be processed to an OSIS reference later)
                            osisRef = BRL.parseToOSIS( adjToken, toOSISGlobals['verseRef'] ) # Note that this may return None
                            if osisRef is not None:
                                OSISfootnote += '<reference type="source" osisRef="{}">{}</reference>'.format(osisRef,token[3:])
                                if not BRL.containsReference( BBB, currentChapterNumberString, verseNumberString ):
                                    logger.error( _("toOSIS: Footnote at {} {}:{} seems to contain the wrong self-reference anchor {!r}").format(BBB,currentChapterNumberString,verseNumberString, token[3:].rstrip()) )
                        elif lcToken.startswith('ft ') or lcToken.startswith('fr* '): # footnote text follows
                            OSISfootnote += token[3:]
                        elif lcToken.startswith('fq ') or token.startswith('fqa '): # footnote quote follows — NOTE: We also assume here that the next marker closes the fq field
                            OSISfootnote += '<catchWord>{}</catchWord>'.format(token[3:]) # Note that the trailing space goes in the catchword here — seems messy
                        elif lcToken in ('fr*','fr* ','ft*','ft* ','fq*','fq* ','fqa*','fqa* ',):
                            pass # We're being lazy here and not checking closing markers properly
                        else:
                            logger.warning( _("toOSIS: Unprocessed {!r} token in {} footnote {!r}").format(token, toOSISGlobals['verseRef'], USFMfootnote) )
                    OSISfootnote += '</note>'
                    #print( '', OSISfootnote )
                    #if currentChapterNumberString=='5' and verseNumberString=='29': halt
                    return OSISfootnote
                # end of toOSISXML.processFootnote

                if extras:
                    #print( '\n', chapterRef )
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert offset >= 0
                    for extra in extras: # do any footnotes and cross-references
                        extraType, extraIndex, extraText, cleanExtraText = extra
                        adjIndex = extraIndex - offset
                        lenV = len( verse )
                        if adjIndex > lenV: # This can happen if we have verse/space/notes at end (and the space was deleted after the note was separated off)
                            logger.warning( _("toOSIS: Space before note at end of verse in {} has been lost").format( toOSISGlobals['verseRef'] ) )
                            # No need to adjust adjIndex because the code below still works
                        elif adjIndex<0 or adjIndex>lenV: # The extras don't appear to fit correctly inside the verse
                            print( "toOSIS: Extras don't fit inside verse at {}: eI={} o={} len={} aI={}".format( toOSISGlobals['verseRef'], extraIndex, offset, len(verse), adjIndex ) )
                            print( "  Verse={!r}".format( verse ) )
                            print( "  Extras={!r}".format( extras ) )
                        #assert 0 <= adjIndex <= len(verse)
                        adjText = checkOSISText( extraText, checkLeftovers=False ) # do any general character formatting on the notes
                        #if adjText!=extraText: print( "processXRefsAndFootnotes: {}@{}-{}={} {!r} now {!r}".format( extraType, extraIndex, offset, adjIndex, extraText, adjText ) )
                        if extraType == 'fn':
                            extra = processFootnote( adjText )
                            #print( "fn got", extra )
                        elif extraType == 'xr':
                            extra = processXRef( adjText )
                            #print( "xr got", extra )
                        elif extraType == 'fig':
                            logger.critical( "OSISXML figure not handled yet" )
                            extra = '' # temp
                            #extra = processFigure( extraText )
                            #print( "fig got", extra )
                        elif extraType == 'str':
                            extra = '' # temp
                        elif extraType == 'sem':
                            extra = '' # temp
                        elif extraType == 'vp':
                            extra = "\\vp {}\\vp*".format( extraText ) # Will be handled later
                        elif BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( extraType ); halt
                        #print( "was", verse )
                        verse = verse[:adjIndex] + str(extra) + verse[adjIndex:]
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
                    if len(bits)!=2 or not bits[0].isdigit() or not bits[1].isdigit(): logger.critical( _("toOSIS: {} doesn't handle verse number of form {!r} yet for {}").format(self.abbreviation, verseNumberString,chapterRef) )
                    toOSISGlobals['verseRef']  = chapterRef + '.' + bits[0]
                    verseRef2 = chapterRef + '.' + bits[1]
                    sID    = toOSISGlobals['verseRef'] + '-' + verseRef2
                    osisID = toOSISGlobals['verseRef'] + ' ' + verseRef2
                elif ',' in verseNumberString:
                    bits = verseNumberString.split(',')
                    if len(bits)<2 or not bits[0].isdigit() or not bits[1].isdigit(): logger.critical( _("toOSIS: {} doesn't handle verse number of form {!r} yet for {}").format(self.abbreviation, verseNumberString,chapterRef) )
                    sID = toOSISGlobals['verseRef'] = chapterRef + '.' + bits[0]
                    osisID = ''
                    for bit in bits: # Separate the OSIS ids by spaces
                        osisID += ' ' if osisID else ''
                        osisID += chapterRef + '.' + bit
                    #print( "Hey comma verses {!r} {!r}".format( sID, osisID ) )
                elif verseNumberString.isdigit():
                    sID = osisID = toOSISGlobals['verseRef'] = chapterRef + '.' + verseNumberString
                else:
                    logger.critical( _("toOSIS: {} doesn't handle verse number of form {!r} yet for {}").format(self.abbreviation, verseNumberString,chapterRef) )
                    tempID = toOSISGlobals['verseRef'] = chapterRef + '.' + verseNumberString # Try it anyway
                    sID = osisID = tempID.replace('<','').replace('>','').replace('"','') # But remove anything that'll cause a big XML problem later
                #print( "here SID={!r} osisID={!r}".format( sID, osisID ) )
                writerObject.writeLineOpenSelfclose( 'verse', [('sID',sID), ('osisID',osisID)] ); haveOpenVsID = sID
                #adjText = processXRefsAndFootnotes( verseText, extras, offset )
                #writerObject.writeLineText( checkOSISText(adjText), noTextCheck=True )
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
                    logger.error( "toOSIS: closeAnyOpenSection: Why was L open at {}?".format( toOSISGlobals['verseRef'] ) )
                    writerObject.writeLineClose( 'l' )
                    haveOpenL = False
                if haveOpenLG:
                    logger.error( "toOSIS: closeAnyOpenSection: Why was LG open at {}?".format( toOSISGlobals['verseRef'] ) )
                    writerObject.writeLineClose( 'lg' )
                    haveOpenLG = False
                if haveOpenParagraph:
                    logger.error( "toOSIS: closeAnyOpenSection: Why was paragraph open at {}?".format( toOSISGlobals['verseRef'] ) )
                    writerObject.writeLineClose( 'p' )
                    haveOpenParagraph = False
                if haveOpenSubsection:
                    logger.error( "toOSIS: closeAnyOpenSection: Why was subsection open at {}?".format( toOSISGlobals['verseRef'] ) )
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
                    #print( "closeAnyOpenLG", toOSISGlobals['verseRef'] )
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


            # Main code for toOSISXML.writeOSISBook
            bookRef = BibleOrgSysGlobals.loadedBibleBooksCodes.getOSISAbbreviation( BBB ) # OSIS book name
            if not bookRef:
                logger.error( "toOSIS: Can't write {} OSIS book because no OSIS code available".format( BBB ) )
                unhandledBooks.append( BBB )
                return
            chapterRef = bookRef + '.0' # Not used by OSIS
            toOSISGlobals['verseRef'] = chapterRef + '.0' # Not used by OSIS
            writerObject.writeLineOpen( 'div', [('type',"book"), ('osisID',bookRef)] )
            haveOpenIntro = haveOpenOutline = haveOpenMajorSection = haveOpenSection = haveOpenSubsection = False
            needChapterEID = haveOpenParagraph = haveOpenVsID = haveOpenLG = haveOpenL = haveOpenList = False
            lastMarker = unprocessedMarker = ''
            gotVP = None
            C, V = '-1', '-1' # So first/id line starts at -1:0
            for processedBibleEntry in bkData._processedLines: # Process internal Bible data lines
                marker, text, extras = processedBibleEntry.getMarker(), processedBibleEntry.getAdjustedText(), processedBibleEntry.getExtras()
                if '¬' in marker or marker in BOS_ADDED_NESTING_MARKERS or marker=='v=':
                    continue # Just ignore added markers — not needed here
                if marker in USFM_PRECHAPTER_MARKERS:
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
                        assert C=='-1' or marker=='rem' or marker.startswith('mte')
                    V = str( int(V) + 1 )
                #print( "BibleWriter.toOSIS: {} {}:{} {}={}{}".format( BBB, C, V, marker, repr(text), " + extras" if extras else "" ) )

                if haveOpenList and marker not in ('li1','li2','li3','li4', 'ili1','ili2','ili3','ili4',):
                    writerObject.writeLineClose( 'list' )
                    haveOpenList = False

                if marker in OFTEN_IGNORED_USFM_HEADER_MARKERS or marker in ('ie',):
                    ignoredMarkers.add( marker )
                    continue # Just ignore these lines
                elif marker in ('mt1','mt2','mt3','mt4', 'mte1','mte2','mte3','mte4',):
                    if text: writerObject.writeLineOpenClose( 'title', checkOSISText(text), [('type','main'),('level',marker[-1]),('canonical',"false")] )
                elif marker in ('is1','is2','is3','is4', 'imt1','imt2','imt3','imt4', 'imte1','imte2','imte3','imte4', ):
                    #print( marker, "'"+text+"'" )
                    if not haveOpenIntro:
                        writerObject.writeLineOpen( 'div', [('type',"introduction"),('canonical',"false")] )
                        haveOpenIntro = True
                    if text: writerObject.writeLineOpenClose( 'title', checkOSISText(text),('level',marker[-1]) ) # Introduction heading
                    logger.error( _("toOSIS: {} Have a blank {} field—ignoring it").format( toOSISGlobals['verseRef'], marker ) )
                elif marker=='ip':
                    if not haveOpenIntro: # Shouldn't happen but we'll try our best
                        logger.error( _("toOSIS: {} Have an ip not in an introduction section—ignoring it").format( toOSISGlobals['verseRef'] ) )
                        writerObject.writeLineOpen( 'div', [('type',"introduction"),('canonical',"false")] )
                        haveOpenIntro = True
                    closeAnyOpenParagraph()
                    writerObject.writeLineOpenText( 'p', checkOSISText(text), noTextCheck=True ) # Sometimes there's text
                    haveOpenParagraph = True
                elif marker=='iot':
                    if not haveOpenIntro: # Shouldn't happen but we'll try our best
                        logger.error( _("toOSIS: {} Have an iot not in an introduction section").format( toOSISGlobals['verseRef'] ) )
                        writerObject.writeLineOpen( 'div', [('type',"introduction"),('canonical',"false")] )
                        haveOpenIntro = True
                    if haveOpenSection or haveOpenOutline: logger.error( "toOSIS: Not handled yet iot in {} hOS={} hOO={}".format(BBB,haveOpenSection,haveOpenOutline) )
                    closeAnyOpenParagraph()
                    writerObject.writeLineOpen( 'div', ('type',"outline") )
                    if text: writerObject.writeLineOpenClose( 'title', checkOSISText(text) )
                    writerObject.writeLineOpen( 'list' )
                    haveOpenOutline = True
                elif marker in ('io1','io2','io3','io4',):
                    if not haveOpenIntro: # Shouldn't happen but we'll try our best
                        logger.error( _("toOSIS: {} Have an {} not in an introduction section").format( toOSISGlobals['verseRef'], marker ) )
                        writerObject.writeLineOpen( 'div', [('type',"introduction"),('canonical',"false")] )
                        haveOpenIntro = True
                    if not haveOpenOutline: # Shouldn't happen but we'll try our best
                        logger.warning( _("toOSIS: {} Have an {} not in an outline section").format( toOSISGlobals['verseRef'], marker ) )
                        closeAnyOpenParagraph()
                        writerObject.writeLineOpen( 'div', ('type',"outline") )
                        writerObject.writeLineOpen( 'list' )
                        haveOpenOutline = True
                    if text: writerObject.writeLineOpenClose( 'item', checkOSISText(text), noTextCheck='\\' in text )

                elif marker=='c':
                    if haveOpenVsID != False: # Close the previous verse
                        writerObject.writeLineOpenSelfclose( 'verse', ('eID',haveOpenVsID) )
                        haveOpenVsID = False
                    if haveOpenOutline:
                        if text!='1' and not text.startswith('1 '): logger.error( _("toOSIS: {} This should normally be chapter 1 to close the introduction (got {!r})").format( toOSISGlobals['verseRef'], text ) )
                        writerObject.writeLineClose( 'list' )
                        writerObject.writeLineClose( 'div' )
                        haveOpenOutline = False
                    if haveOpenIntro:
                        if text!='1' and not text.startswith('1 '): logger.error( _("toOSIS: {} This should normally be chapter 1 to close the introduction (got {!r})").format( toOSISGlobals['verseRef'], text ) )
                        closeAnyOpenParagraph()
                        writerObject.writeLineClose( 'div' )
                        haveOpenIntro = False
                    closeAnyOpenLG()
                    if needChapterEID:
                        writerObject.writeLineOpenSelfclose( 'chapter', ('eID',chapterRef) ) # This is an end milestone marker
                    C, V = text, '0'
                    currentChapterNumberString, verseNumberString = text, '0'
                    if not currentChapterNumberString.isdigit(): logger.critical( _("toOSIS: Can't handle non-digit {!r} chapter number yet").format(text) )
                    chapterRef = bookRef + '.' + checkOSISText(currentChapterNumberString)
                    writerObject.writeLineOpenSelfclose( 'chapter', [('sID',chapterRef), ('osisID',chapterRef)] ) # This is a milestone marker
                    needChapterEID = True
                elif marker=='c~':
                    adjText = processXRefsAndFootnotes( text, extras, 0 )
                    writerObject.writeLineText( checkOSISText(adjText), noTextCheck=True )
                elif marker == 'c#': # Chapter number added for printing
                    ignoredMarkers.add( marker ) # Just ignore it completely
                elif marker == 'vp#': # This precedes a v field and has the verse number to be printed
                    gotVP = text # Just remember it for now
                elif marker=='v':
                    if gotVP: # this is the verse number to be published
                        text = gotVP
                        gotVP = None
                    verseNumberString = text
                    if not haveOpenL: closeAnyOpenLG()
                    V = text
                    writeVerseStart( writerObject, BBB, chapterRef, verseNumberString )
                    closeAnyOpenL()

                elif marker in ('ms1','ms2','ms3','ms4',):
                    if haveOpenParagraph:
                        closeAnyOpenLG()
                        closeAnyOpenParagraph()
                    closeAnyOpenSubsection()
                    closeAnyOpenSection()
                    closeAnyOpenMajorSection()
                    writerObject.writeLineOpen( 'div', ('type',"majorSection") )
                    haveOpenMajorSection = True
                    if text: writerObject.writeLineOpenClose( 'title', checkOSISText(text) ) # Section heading
                    else:
                        logger.info( _("toOSIS: {} Blank ms1 section heading encountered").format( toOSISGlobals['verseRef'] ) )
                elif marker=='mr':
                    # Should only follow a ms1 I think
                    if haveOpenParagraph or haveOpenSection or not haveOpenMajorSection: logger.error( _("toOSIS: Didn't expect major reference 'mr' marker after {}").format(toOSISGlobals['verseRef']) )
                    if text: writerObject.writeLineOpenClose( 'title', checkOSISText(text), ('type',"scope") )
                elif marker == 'd':
                    #if BibleOrgSysGlobals.debugFlag:
                        #pass
                    flag = '\\' in text or extras # Set this flag if the text already contains XML formatting
                    adjustedText = processXRefsAndFootnotes( text, extras )
                    if adjustedText:
                        #print( BBB, C, V, repr(adjustedText) )
                        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert BBB in ('PSA','PS2',)
                        writerObject.writeLineOpenClose( 'title', checkOSISText(adjustedText), [('canonical','true'),('type','psalm')], noTextCheck=flag )
                elif marker in ('s1','s2','s3','s4',):
                    if haveOpenParagraph:
                        closeAnyOpenLG()
                        closeAnyOpenParagraph()
                    closeAnyOpenSubsection()
                    closeAnyOpenSection()
                    writerObject.writeLineOpen( 'div', ('type', "section") )
                    haveOpenSection = True
                    #print( "{} {}:{}".format( BBB, currentChapterNumberString, verseNumberString ) )
                    #print( "{} = {!r}".format( marker, text ) )
                    flag = '\\' in text or extras # Set this flag if the text already contains XML formatting
                    adjustedText = processXRefsAndFootnotes( text, extras )
                    if adjustedText:
                        writerObject.writeLineOpenClose( 'title', checkOSISText(adjustedText), noTextCheck=flag ) # Section heading
                elif marker=='r':
                    # Should only follow a s1 I think
                    if haveOpenParagraph or not haveOpenSection: logger.error( _("toOSIS: Didn't expect reference 'r' marker after {}").format(toOSISGlobals['verseRef']) )
                    if text: writerObject.writeLineOpenClose( 'title', checkOSISText(text), ('type',"parallel") ) # Section cross-reference
                elif marker=='sr':
                    # Should only follow a s1 I think
                    if haveOpenParagraph or not haveOpenSection: logger.error( _("toOSIS: Didn't expect reference 'sr' marker after {}").format(toOSISGlobals['verseRef']) )
                    if text:
                        writerObject.writeLineOpen( 'title', ('type','scope') )
                        writerObject.writeLineOpenClose( 'reference', checkOSISText(text) )
                        writerObject.writeLineClose( 'title' )
                elif marker == 'sp':
                    if text: writerObject.writeLineOpenClose( 'speaker', checkOSISText(text) )
                elif marker == 'p':
                    closeAnyOpenLG()
                    closeAnyOpenParagraph()
                    if not haveOpenSection:
                        writerObject.writeLineOpen( 'div', ('type', "section") )
                        haveOpenSection = True
                    adjustedText = processXRefsAndFootnotes( text, extras )
                    writerObject.writeLineOpenText( 'p', checkOSISText(adjustedText), noTextCheck=True ) # Sometimes there's text
                    haveOpenParagraph = True
                elif marker in ('li1','li2','li3','li4', 'ili1','ili2','ili3','ili4',):
                    if not haveOpenList:
                        writerObject.writeLineOpen( 'list' )
                        haveOpenList = True
                    adjustedText = processXRefsAndFootnotes( text, extras, 0 )
                    writerObject.writeLineOpenClose( 'item', checkOSISText(adjustedText), ('type','x-indent-'+marker[-1]), noTextCheck=True )
                elif marker in ('v~','p~',):
                    adjText = processXRefsAndFootnotes( text, extras, 0 )
                    writerObject.writeLineText( checkOSISText(adjText), noTextCheck=True )
                elif marker in ('q1','q2','q3','q4',):
                    qLevel = marker[1] # The digit
                    closeAnyOpenL()
                    if not haveOpenLG:
                        writerObject.writeLineOpen( 'lg' )
                        haveOpenLG = True
                    if text:
                        adjustedText = processXRefsAndFootnotes( text, extras )
                        writerObject.writeLineOpenClose( 'l', checkOSISText(adjustedText), ('level',qLevel), noTextCheck=True )
                    else: # No text — this q1 applies to the next marker
                        writerObject.writeLineOpen( 'l', ('level',qLevel) )
                        haveOpenL = True
                elif marker=='m': # Margin/Flush-left paragraph
                    closeAnyOpenL()
                    closeAnyOpenLG()
                    if text: writerObject.writeLineText( checkOSISText(text), noTextCheck=True )
                elif marker in ('b','ib'): # Blank line
                    #print( 'b', BBB, C, V )
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not text and not extras
                    # Doesn't seem that OSIS has a way to encode this presentation element
                    writerObject.writeNewLine() # We'll do this for now
                elif marker=='nb': # No-break
                    #print( 'nb', BBB, C, V ); halt
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not text and not extras
                    ignoredMarkers.add( marker )
                else:
                    if text:
                        logger.critical( "toOSIS: {} lost text in {} field in {} {}:{} {!r}".format( self.abbreviation, marker, BBB, C, V, text ) )
                        #if BibleOrgSysGlobals.debugFlag: halt
                    if extras:
                        logger.critical( "toOSIS: {} lost extras in {} field in {} {}:{}".format( self.abbreviation, marker, BBB, C, V ) )
                        #if BibleOrgSysGlobals.debugFlag: halt
                    unhandledMarkers.add( marker )
                if marker not in ('v','v~','p','p~','q1','q2','q3','q4','s1','s2','s3','s4','d',) and extras:
                    logger.critical( "toOSIS: Programming note: Didn't handle {!r} extras: {}".format( marker, extras ) )
                lastMarker = marker

            # At the end of everything
            if haveOpenVsID != False: # Close the last verse
                writerObject.writeLineOpenSelfclose( 'verse', ('eID',haveOpenVsID) )
                haveOpenVsID = False
            closeAnyOpenLG() # A file can easily end with a q1 field
            if haveOpenIntro or haveOpenOutline or haveOpenLG or haveOpenL or unprocessedMarker:
                logger.error( "toOSIS: a {} {} {} {} {}".format( haveOpenIntro, haveOpenOutline, haveOpenLG, haveOpenL, unprocessedMarker ) )
                logger.error( "toOSIS: b {} {}:{}".format( BBB, currentChapterNumberString, verseNumberString ) )
                logger.error( "toOSIS: c {} = {!r}".format( marker, text ) )
                logger.error( "toOSIS: d These shouldn't be open here" )
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


        # Start of main toOSIS code
        if 'osisFiles' not in controlDict or controlDict['osisFiles']=='byBook': # Write an individual XML file for each book
            if BibleOrgSysGlobals.verbosityLevel > 2: print( _("  Exporting individually to OSIS XML format…") )
            validationResults = ( 0, '', '', ) # xmllint result code, program output, error output
            for BBB,bookData in self.books.items(): # Process each Bible book
                try: fn = controlDict['osisOutputFilename'].replace( '_Bible', "_Book-{}".format(BBB) )
                except KeyError: fn = 'Book-{}.osis'.format( BBB )
                xw = MLWriter( BibleOrgSysGlobals.makeSafeFilename( fn ), outputFolderpath )
                xw.setHumanReadable( 'All' ) # Can be set to 'All', 'Header', or 'None' — one output file went from None/Header=4.7MB to All=5.7MB
                xw.start()
                xw.writeLineOpen( 'osis', [('xmlns',OSISNameSpace), ('xmlns:xsi',"http://www.w3.org/2001/XMLSchema-instance"), ('xsi:schemaLocation',OSISNameSpace+' '+OSISSchemaLocation)] )
                try: xlg = controlDict['xmlLanguage']
                except KeyError: xlg = 'eng'
                try: oIDw = controlDict['osisIDWork'].replace( ' ', '_' ).replace( '(', '' ).replace( ')', '' ).replace( "'", '' )
                except KeyError: oIDw = 'Bible'
                xw.writeLineOpen( 'osisText', [('osisRefWork','Bible' ), ('xml:lang',xlg), ('osisIDWork',oIDw)] )
                xw.setSectionName( 'Header' )
                writeHeader( xw )
                xw.setSectionName( 'Main' )
                writeOSISBook( xw, BBB, bookData )
                xw.writeLineClose( 'osisText' )
                xw.writeLineClose( 'osis' )
                xw.close()
                if validationSchema:
                    bookResults = xw.validate( validationSchema ) # Returns a 3-tuple: intCode, logString, errorLogString
                    if bookResults[0] > validationResults[0]: validationResults = ( bookResults[0], validationResults[1], validationResults[2], )
                    if bookResults[1]: validationResults = ( validationResults[0], validationResults[1] + bookResults[1], validationResults[2], )
                    if bookResults[2]: validationResults = ( validationResults[0], validationResults[1], validationResults[2] + bookResults[2], )
            if validationSchema:
                if validationResults[0] > 0:
                    with open( os.path.join( outputFolderpath, 'ValidationErrors.txt' ), 'wt', encoding='utf-8' ) as veFile:
                        if validationResults[1]: veFile.write( validationResults[1] + '\n\n\n' ) # Normally empty
                        if validationResults[2]: veFile.write( validationResults[2] )
        elif controlDict['osisFiles']=='byBible': # write all the books into a single file
            if BibleOrgSysGlobals.verbosityLevel > 2: print( _("  Exporting to OSIS XML format…") )
            filename = BibleOrgSysGlobals.makeSafeFilename( controlDict['osisOutputFilename'] )
            xw = MLWriter( filename, outputFolderpath )
            xw.setHumanReadable( 'All' ) # Can be set to 'All', 'Header', or 'None' — one output file went from None/Header=4.7MB to All=5.7MB
            xw.start()
            xw.writeLineOpen( 'osis', [('xmlns',OSISNameSpace), ('xmlns:xsi',"http://www.w3.org/2001/XMLSchema-instance"), ('xsi:schemaLocation',OSISNameSpace+' '+OSISSchemaLocation)] )
            xw.writeLineOpen( 'osisText', [('osisRefWork',"Bible" ), ('xml:lang',controlDict['xmlLanguage']), ('osisIDWork',controlDict['osisIDWork'])] )
            xw.setSectionName( 'Header' )
            writeHeader( xw )
            xw.setSectionName( 'Main' )
            for BBB,bookData in self.books.items(): # Process each Bible book
                writeOSISBook( xw, BBB, bookData )
            xw.writeLineClose( 'osisText' )
            xw.writeLineClose( 'osis' )
            xw.close()
            # Now create a zipped version
            filepath = os.path.join( outputFolderpath, filename )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Zipping {} OSIS file…".format( filename ) )
            zf = zipfile.ZipFile( filepath+'.zip', 'w', compression=zipfile.ZIP_DEFLATED )
            zf.write( filepath, filename )
            zf.close()
            if validationSchema: validationResults = xw.validate( validationSchema ) # Returns a 3-tuple: intCode, logString, errorLogString
        else:
            logger.critical( "Unrecognized toOSIS control \"osisFiles\" = {!r}".format( controlDict['osisFiles'] ) )

        if ignoredMarkers:
            logger.info( "toOSISXML: Ignored markers were {}".format( ignoredMarkers ) )
            if BibleOrgSysGlobals.verbosityLevel > 2:
                print( "  " + _("ERROR: Ignored toOSISXML markers were {}").format( ignoredMarkers ) )
        if unhandledMarkers:
            logger.error( "toOSISXML: Unhandled markers were {}".format( unhandledMarkers ) )
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print( "  " + _("ERROR: Unhandled toOSISXML markers were {}").format( unhandledMarkers ) )
        if unhandledBooks:
            logger.warning( "toOSISXML: Unhandled books were {}".format( unhandledBooks ) )
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print( "  " + _("WARNING: Unhandled toOSISXML books were {}").format( unhandledBooks ) )
        if BibleOrgSysGlobals.verbosityLevel > 2:
            print( "Need to find and look at an example where a new chapter isn't a new <p> to see how chapter eIDs should be handled there" )
        if BibleOrgSysGlobals.verbosityLevel > 0 and BibleOrgSysGlobals.maxProcesses > 1:
            print( "  BibleWriter.toOSISXML finished successfully." )
        if validationSchema: return validationResults
        return True
    # end of BibleWriter.toOSISXML



    def toZefaniaXML( self, outputFolderpath:Optional[Path]=None, controlDict=None, validationSchema=None ):
        """
        Using settings from the given control file,
            converts the USFM information to a UTF-8 Zefania XML file.

        This format is roughly documented at http://de.wikipedia.org/wiki/Zefania_XML
            and at http://www.bgfdb.de/zefaniaxml/bml/
            but more fields can be discovered by looking at downloaded files.
        """
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Running BibleWriter:toZefaniaXML…" )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert self.books

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolderpath: outputFolderpath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_Zefania_Export/' )
        if not os.access( outputFolderpath, os.F_OK ): os.makedirs( outputFolderpath ) # Make the empty folder if there wasn't already one there
        if not controlDict:
            controlDict, defaultControlFilename = {}, "To_Zefania_controls.txt"
            try: ControlFiles.readControlFile( defaultControlFolderpath, defaultControlFilename, controlDict )
            except FileNotFoundError:
                logger.critical( "Unable to read control dict {} from {}".format( defaultControlFilename, defaultControlFolderpath ) )
        self.__adjustControlDict( controlDict )
        if not validationSchema: # We'll use our copy
            xsdFilepath = 'ExternalSchemas/zef2014.xsd'
            if os.path.exists( xsdFilepath ): validationSchema = xsdFilepath

        # Set-up our Bible reference system
        #if BibleOrgSysGlobals.debugFlag: print( "BibleWriter:toOSISXML publicationCode =", controlDict['PublicationCode'] )
        if 'PublicationCode' not in controlDict or controlDict['PublicationCode'] == 'GENERIC':
            BOS = self.genericBOS
            BRL = self.genericBRL
        else:
            BOS = BibleOrganisationalSystem( controlDict['PublicationCode'] )
            BRL = BibleReferenceList( BOS, BibleObject=None )

        booksNamesSystemName = BOS.getOrganisationalSystemValue( 'booksNamesSystem' )
        if booksNamesSystemName and booksNamesSystemName!='None' and booksNamesSystemName!='Unknown': # default (if we know the book names system)
            getBookNameFunction = BOS.getBookName
            getBookAbbreviationFunction = BOS.getBookAbbreviation
        else: # else use our local functions from our deduced book names
            getBookNameFunction = self.getAssumedBookName # from BibleOrgSys.Formats.USFMBible (which gets it from BibleOrgSys.Formats.USFMBibleBook)
            getBookAbbreviationFunction = BibleOrgSysGlobals.loadedBibleBooksCodes.getOSISAbbreviation

        ignoredMarkers, unhandledMarkers, unhandledBooks = set(), set(), []

        def writeHeader( writerObject ):
            """
            Writes the Zefania header to the Zefania XML writerObject.
            """
            writerObject.writeLineOpen( 'INFORMATION' )
            if 'ZefaniaTitle' in controlDict and controlDict['ZefaniaTitle']: writerObject.writeLineOpenClose( 'title' , controlDict['ZefaniaTitle'] )
            if 'ZefaniaSubject' in controlDict and controlDict['ZefaniaSubject']: writerObject.writeLineOpenClose( 'subject', controlDict['ZefaniaSubject'] )
            if 'ZefaniaDescription' in controlDict and controlDict['ZefaniaDescription']: writerObject.writeLineOpenClose( 'description', controlDict['ZefaniaDescription'] )
            if 'ZefaniaPublisher' in controlDict and controlDict['ZefaniaPublisher']: writerObject.writeLineOpenClose( 'publisher', controlDict['ZefaniaPublisher'] )
            if 'ZefaniaContributors' in controlDict and controlDict['ZefaniaContributors']: writerObject.writeLineOpenClose( 'contributors', controlDict['ZefaniaContributors'] )
            if 'ZefaniaIdentifier' in controlDict and controlDict['ZefaniaIdentifier']: writerObject.writeLineOpenClose( 'identifier', controlDict['ZefaniaIdentifier'] )
            if 'ZefaniaSource' in controlDict and controlDict['ZefaniaSource']: writerObject.writeLineOpenClose( 'identifier', controlDict['ZefaniaSource'] )
            if 'ZefaniaCoverage' in controlDict and controlDict['ZefaniaCoverage']: writerObject.writeLineOpenClose( 'coverage', controlDict['ZefaniaCoverage'] )
            writerObject.writeLineOpenClose( 'format', 'Zefania XML Bible Markup Language' )
            writerObject.writeLineOpenClose( 'date', datetime.now().date().isoformat() )
            writerObject.writeLineOpenClose( 'creator', 'BibleWriter.py' )
            writerObject.writeLineOpenClose( 'type', 'bible text' )
            if 'ZefaniaLanguage' in controlDict and controlDict['ZefaniaLanguage']: writerObject.writeLineOpenClose( 'language', controlDict['ZefaniaLanguage'] )
            if 'ZefaniaRights' in controlDict and controlDict['ZefaniaRights']: writerObject.writeLineOpenClose( 'rights', controlDict['ZefaniaRights'] )
            writerObject.writeLineClose( 'INFORMATION' )
        # end of toZefaniaXML.writeHeader

        toZefGlobals = { 'verseRef':'', 'XRefNum':0, 'FootnoteNum':0, 'lastRef':'', 'OneChapterOSISBookCodes':BibleOrgSysGlobals.loadedBibleBooksCodes.getOSISSingleChapterBooksList() } # These are our global variables

        def writeZefBook( writerObject, BBB, bkData ):
            """
            Writes a book to the Zefania XML writerObject.
            """
            #print( 'BIBLEBOOK', [('bnumber',BibleOrgSysGlobals.loadedBibleBooksCodes.getReferenceNumber(BBB)), ('bname',BibleOrgSysGlobals.loadedBibleBooksCodes.getEnglishName_NR(BBB)), ('bsname',BibleOrgSysGlobals.loadedBibleBooksCodes.getOSISAbbreviation(BBB))] )
            OSISAbbrev = BibleOrgSysGlobals.loadedBibleBooksCodes.getOSISAbbreviation( BBB )
            if not OSISAbbrev:
                logger.error( "toZefania: Can't write {} Zefania book because no OSIS code available".format( BBB ) )
                unhandledBooks.append( BBB )
                return

            def handleVerseNumber( BBB, C, V, givenText ):
                """
                Given verse text, return two strings to be used later.
                """
                endVerseNumberString = None
                if givenText.isdigit():
                    verseNumberString = givenText
                else:
                    verseNumberString  = givenText.replace('<','').replace('>','').replace('"','') # Used below but remove anything that'll cause a big XML problem later
                    for bridgeChar in ('-', '–', '—'): # hyphen, endash, emdash
                        ix = verseNumberString.find( bridgeChar )
                        if ix != -1:
                            value = verseNumberString[:ix] # Remove verse bridges
                            vEnd = verseNumberString[ix+1:]
                            #print( BBB, repr(value), repr(vEnd) )
                            try: vBridgeStartInt = int( value )
                            except ValueError: # Not an integer
                                print( "toZefaniaXML1: bridge doesn't seem to be integers in {} {!r}".format( BBB, verseNumberString ) )
                                vBridgeStartInt = value
                            try: vBridgeEndInt = int( vEnd )
                            except ValueError: # Not an integer
                                print( "toZefaniaXML1: bridge doesn't seem to be integers in {} {!r}".format( BBB, verseNumberString ) )
                                vBridgeEndInt = vEnd
                            #print( ' Z-VB {} {}:{} {!r} {!r}'.format( BBB, C, V, vBridgeStartInt, vBridgeEndInt ) )
                            return vBridgeStartInt, vBridgeEndInt
                return verseNumberString, endVerseNumberString
            # end of toZefaniaXML.handleVerseNumber

            def checkZefaniaText( textToCheck, checkLeftovers=True ):
                """
                Handle some general backslash codes and warn about any others still unprocessed.
                """

                def checkZefaniaTextHelper( marker, helpText ):
                    """
                    Adjust the text to make the number of start and close markers equal.
                    """
                    count1, count2 = helpText.count('\\'+marker+' '), helpText.count('\\'+marker+'*') # count open and close markers
                    while count1 < count2:
                        helpText = '\\'+marker+' ' + helpText
                        count1, count2 = helpText.count('\\'+marker+' '), helpText.count('\\'+marker+'*') # count open and close markers again
                    while count1 > count2:
                        helpText += '\\'+marker+'*'
                        count1, count2 = helpText.count('\\'+marker+' '), helpText.count('\\'+marker+'*') # count open and close markers again
                    if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
                        assert count1 == count2
                    return helpText
                # end of checkZefaniaTextHelper

                # Main code for checkZefaniaText
                adjText = textToCheck
                if '<<' in adjText or '>>' in adjText:
                    logger.warning( _("toZefania: Unexpected double angle brackets in {}: {!r} field is {!r}").format( toZefGlobals['verseRef'], marker, textToCheck ) )
                    adjText = adjText.replace('<<','“' ).replace('>>','”' )
                #if '\\bk ' in adjText: adjText = checkZefaniaTextHelper('bk',adjText).replace('\\bk ','<reference type="x-bookName">').replace('\\bk*','</reference>')
                #if '\\ior ' in adjText: adjText = checkZefaniaTextHelper('ior',adjText).replace('\\ior ','<reference>').replace('\\ior*','</reference>')
                if '\\add ' in adjText: adjText = checkZefaniaTextHelper('add',adjText).replace('\\add ','<STYLE fs="italic">').replace('\\add*','</STYLE>') # ???
                if '\\nd ' in adjText: adjText = checkZefaniaTextHelper('nd',adjText).replace('\\nd ','<STYLE fs="divineName">').replace('\\nd*','</STYLE>')
                if '\\wj ' in adjText: adjText = checkZefaniaTextHelper('wj',adjText).replace('\\wj ','<STYLE fs="illuminated">').replace('\\wj*','</STYLE>') # Try this (not sure what it means)
                if '\\sig ' in adjText: adjText = checkZefaniaTextHelper('sig',adjText).replace('\\sig ','<STYLE fs="italic">').replace('\\sig*','</STYLE>') # ???
                if '\\it ' in adjText: adjText = checkZefaniaTextHelper('it',adjText).replace('\\it ','<STYLE fs="italic">').replace('\\it*','</STYLE>')
                if '\\bd ' in adjText: adjText = checkZefaniaTextHelper('bd',adjText).replace('\\bd ','<STYLE fs="bold">').replace('\\bd*','</STYLE>')
                if '\\em ' in adjText: adjText = checkZefaniaTextHelper('em',adjText).replace('\\em ','<STYLE fs="bold">').replace('\\em*','</STYLE>') # ???
                if '\\sc ' in adjText: adjText = checkZefaniaTextHelper('sc',adjText).replace('\\sc ','<STYLE fs="small-caps">').replace('\\sc*','</STYLE>')
                if '\\fig ' in adjText: # Figure is not used in Sword modules so we'll remove it from the Zefania (for now at least)
                    ix1 = adjText.find( '\\fig ' )
                    ix2 = adjText.find( '\\fig*' )
                    if ix2 == -1: logger.error( _("toZefania: Missing fig end marker for Zefania in {}: {!r} field is {!r}").format( toZefGlobals['verseRef'], marker, textToCheck ) )
                    else:
                        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert ix2 > ix1
                        #print( "was {!r}".format( adjText ) )
                        adjText = adjText[:ix1] + adjText[ix2+5:] # Remove the \\fig..\\fig* field
                        #print( "now {!r}".format( adjText ) )
                        logger.warning( _("toZefania: Figure reference removed for Zefania generation in {}: {!r} field").format( toZefGlobals['verseRef'], marker ) )
                if checkLeftovers and '\\' in adjText:
                    logger.error( _("toZefania: We still have some unprocessed backslashes for Zefania in {}: {!r} field is {!r}").format( toZefGlobals['verseRef'], marker, textToCheck ) )
                    #print( _("toZefania: We still have some unprocessed backslashes for Zefania in {}: {!r} field is {!r}").format( toZefGlobals['verseRef'], marker, textToCheck ) )
                    adjText = adjText.replace('\\','ENCODING ERROR HERE ' )
                return adjText
            # end of toZefaniaXML.checkZefaniaText

            #def convertInternals( BBB, C, V, givenText ):
                #"""
                #Do formatting of character styles and footnotes/cross-references, etc.

                #Returns the adjusted text.
                #"""
                #newText = givenText
                #newText = newText.replace( '\\nd ', '<STYLE fs="divineName">' ).replace( '\\nd*', '</STYLE>' )
                #newText = newText.replace( '\\bd ', '<STYLE fs="bold">' ).replace( '\\bd*', '</STYLE>' )
                #newText = newText.replace( '\\it ', '<STYLE fs="italic">' ).replace( '\\it*', '</STYLE>' )
                #newText = newText.replace( '\\sc ', '<STYLE fs="small-caps">' ).replace( '\\sc*', '</STYLE>' )
                #return newText
            ## end of toZefaniaXML.convertInternals

            def processZefXRefsAndFootnotes( verse, extras, offset=0 ):
                """
                Convert cross-references and footnotes and return the adjusted verse text.
                """

                def processXRef( USFMxref ):
                    """
                    Return the OSIS code for the processed cross-reference (xref).

                    NOTE: The parameter here already has the /x and /x* removed.

                    \\x - \\xo 2:2: \\xt Lib 19:9-10; Diy 24:19.\\xt*\\x* (Backslashes are shown doubled here)
                        gives
                    <note type="crossReference" n="1">2:2: <reference>Lib 19:9-10; Diy 24:19.</reference></note> (Crosswire — invalid OSIS — which then needs to be converted)
                    <note type="crossReference" osisRef="Ruth.2.2" osisID="Ruth.2.2!crossreference.1" n="-"><reference type="source" osisRef="Ruth.2.2">2:2: </reference><reference osisRef="-">Lib 19:9-10</reference>; <reference osisRef="Ruth.Diy.24!:19">Diy 24:19</reference>.</note> (Snowfall)
                    \\x - \\xo 3:5: a \\xt Rum 11:1; \\xo b \\xt Him 23:6; 26:5.\\xt*\\x* is more complex still.
                    """
                    toZefGlobals["XRefNum"] += 1
                    ZefXref = '' #'<XREF>'
                    for j,token in enumerate(USFMxref.split('\\')):
                        #print( "\ntoZefania:processXRef", j, "'"+token+"'", "from", '"'+USFMxref+'"' )
                        lcToken = token.lower()
                        if j==0: # The first token (but the x has already been removed)
                            rest = token.strip()
                            if rest != '+':
                                logger.warning( _("toZefania1: We got something else here other than plus (probably need to do something with it): {} {}:{} {!r} from {!r} from {!r}").format( BBB,C,V, rest, token, text) )
                        elif lcToken.startswith('xo '): # xref reference follows
                            adjToken = token[3:].strip()
                            #print( "toZefania:processXRef(xo)", j, "'"+token+"'", "'"+adjToken+"'", "from", '"'+USFMxref+'"' )
                            if j==1:
                                if len(adjToken)>2 and adjToken[-2]==' ' and adjToken[-1]=='a':
                                    suffixLetter = adjToken[-1]
                                    adjToken = adjToken[:-2] # Remove any suffix (occurs when a cross-reference has multiple (a and b) parts
                                if adjToken.endswith(':'): adjToken = adjToken[:-1] # Remove any final colon (this is a language dependent hack)
                                adjToken = getBookAbbreviationFunction(BBB) + ' ' + adjToken # Prepend a book abbreviation for the anchor (will be processed to an OSIS reference later)
                                selfReference = adjToken
                            else: # j > 1 — this xo field may possibly only contain a letter suffix
                                if len(adjToken)==1 and adjToken in ('b','c','d','e','f','g','h',):
                                    adjToken = selfReference
                                else: # Could be another complete reference
                                    #print( "<<< Programming error here in toZefaniaXML:processXRef for {!r} at {} {}:{}".format( USFMxref, BBB, currentChapterNumberString, verseNumberString )  )
                                    #print( "  '"+lcToken+"'", len(adjToken), "'"+adjToken+"'" )
                                    if len(adjToken)>2 and adjToken[-2]==' ' and adjToken[-1]=='a':
                                        suffixLetter = adjToken[-1]
                                        adjToken = adjToken[:-2] # Remove any suffix (occurs when a cross-reference has multiple (a and b) parts
                                    if adjToken.endswith(':'): adjToken = adjToken[:-1] # Remove any final colon (this is a language dependent hack)
                                    adjToken = getBookAbbreviationFunction(BBB) + ' ' + adjToken # Prepend a book abbreviation for the anchor (will be processed to an OSIS reference later)
                                    selfReference = adjToken
                            osisRef = BRL.parseToOSIS( adjToken, toZefGlobals['verseRef'] )
                            if osisRef is not None:
                                #print( "  osisRef = {}".format( osisRef ) )
                                if not ZefXref: ZefXref = '<XREF '
                                ZefXref += 'vref="{}">'.format( V )
# Temp disabled
#                                if not BRL.containsReference( BBB, currentChapterNumberString, verseNumberString ):
#                                    logger.error( _("toZefania: Cross-reference at {} {}:{} seems to contain the wrong self-reference anchor {!r}").format(BBB,currentChapterNumberString,verseNumberString, token[3:].rstrip()) )
                        elif lcToken.startswith('xt '): # xref text follows
                            xrefText = token[3:]
                            finalPunct = ''
                            while xrefText[-1] in ' ,;.': finalPunct = xrefText[-1] + finalPunct; xrefText = xrefText[:-1]
                            #adjString = xrefText[:-6] if xrefText.endswith( ' (LXX)' ) else xrefText # Sorry, this is a crude hack to avoid unnecessary error messages
                            #osisRef = BRL.parseToOSIS( xrefText, toZefGlobals['verseRef'] )
                            if not ZefXref: ZefXref = '<XREF>'
                            ZefXref += xrefText
                        elif lcToken.startswith('x '): # another whole xref entry follows
                            rest = token[2:].strip()
                            if rest != '+':
                                logger.warning( _("toZefania2: We got something else here other than plus (probably need to do something with it): {} {}:{} {!r} from {!r} from {!r}").format( BBB,C,V, rest, token, text) )
                        elif lcToken in ('xo*','xt*','x*',):
                            pass # We're being lazy here and not checking closing markers properly
                        else:
                            logger.warning( _("toZefania: Unprocessed {!r} token in {} xref {!r}").format( token, toZefGlobals['verseRef'], USFMxref ) )
                    ZefXref += '</XREF>'
                    #print( ' ZefXref gave {!r} from {!r}'.format( ZefXref, USFMxref ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag or debuggingThisModule:
                        assert '<XREF' in ZefXref
                    return ZefXref
                # end of toZefaniaXML.processXRef

                def processFootnote( USFMfootnote ):
                    """
                    Return the OSIS code for the processed footnote.

                    NOTE: The parameter here already has the /f and /f* removed.

                    \\f + \\fr 1:20 \\ft Su ka kaluwasan te Nawumi ‘keupianan,’ piru ka kaluwasan te Mara ‘masakit se geyinawa.’\\f* (Backslashes are shown doubled here)
                        gives
                    <note n="1">1:20 Su ka kaluwasan te Nawumi ‘keupianan,’ piru ka kaluwasan te Mara ‘masakit se geyinawa.’</note> (Crosswire)
                    <note osisRef="Ruth.1.20" osisID="Ruth.1.20!footnote.1" n="+"><reference type="source" osisRef="Ruth.1.20">1:20 </reference>Su ka kaluwasan te Nawumi ‘keupianan,’ piru ka kaluwasan te Mara ‘masakit se geyinawa.’</note> (Snowfall)
                    """
                    toZefGlobals["FootnoteNum"] += 1
                    ZefFootnote = '' #<NOTE osisRef="{}" osisID="{}!footnote.{}">'.format( toZefGlobals['verseRef'], toZefGlobals['verseRef'], toZefGlobals["FootnoteNum"] )
                    for j,token in enumerate(USFMfootnote.split('\\')):
                        #print( "processFootnote", j, token, USFMfootnote )
                        lcToken = token.lower()
                        if j==0: continue # ignore the + for now
                        elif lcToken.startswith('fr '): # footnote reference follows
                            adjToken = token[3:].strip()
                            if adjToken.endswith(':'): adjToken = adjToken[:-1] # Remove any final colon (this is a language dependent hack)
                            adjToken = getBookAbbreviationFunction(BBB) + ' ' + adjToken # Prepend a book abbreviation for the anchor (will be processed to an OSIS reference later)
                            #print( "  adjToken", repr(adjToken) )
                            osisRef = BRL.parseToOSIS( adjToken, toZefGlobals['verseRef'] ) # Note that this may return None
                            #print( "  osisRef", repr(osisRef) )
                            if osisRef is None: # something's wrong, but do our best
                                if not ZefFootnote: ZefFootnote = '<NOTE>'
                                ZefFootnote += adjToken
                            else:
                                if not ZefFootnote: ZefFootnote = '<NOTE '
                                #print( repr(osisRef), repr(token[3:]) )
                                ZefFootnote += 'ref="{}">'.format( osisRef.replace('.',',') )
# Temp disabled
#                                if not BRL.containsReference( BBB, currentChapterNumberString, verseNumberString ):
#                                    logger.error( _("toZefania: Footnote at {} {}:{} seems to contain the wrong self-reference anchor {!r}").format(BBB,currentChapterNumberString,verseNumberString, token[3:].rstrip()) )
                        elif lcToken.startswith('ft ') or lcToken.startswith('fr* '): # footnote text follows
                            if not ZefFootnote: ZefFootnote = '<NOTE>'
                            ZefFootnote += token[3:]
                        elif lcToken.startswith('fq ') or token.startswith('fqa '): # footnote quote follows — NOTE: We also assume here that the next marker closes the fq field
                            if not ZefFootnote: ZefFootnote = '<NOTE>'
                            ZefFootnote += '<STYLE fs="italic">{}</STYLE>'.format(token[3:]) # Note that the trailing space goes in the catchword here — seems messy
                        elif lcToken.startswith('fk '): # footnote keyword(s) follows — NOTE: We also assume here that the next marker closes the fq field
                            if not ZefFootnote: ZefFootnote = '<NOTE>'
                            ZefFootnote += '<STYLE fs="bold">{}</STYLE>'.format(token[3:]) # Note that the trailing space goes in the catchword here — seems messy
                        elif lcToken in ('fr*','fr* ', 'ft*','ft* ', 'fq*','fq* ', 'fqa*','fqa* ', 'fk*','fk* ',):
                            pass # We're being lazy here and not checking closing markers properly
                        else:
                            logger.warning( _("toZefania: Unprocessed {!r} token in {} footnote {!r}").format(token, toZefGlobals['verseRef'], USFMfootnote) )
                            ZefFootnote += token # put it in (including the markers)
                    ZefFootnote += '</NOTE>'
                    #print( ' ZefFootnote', repr(ZefFootnote) )
                    #if currentChapterNumberString=='5' and verseNumberString=='29': halt
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag or debuggingThisModule:
                        assert '<NOTE' in ZefFootnote
                    return ZefFootnote
                # end of toZefaniaXML.processFootnote

                # Main code for toZefaniaXML.processZefXRefsAndFootnotes
                if extras:
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert offset >= 0
                    for extra in extras: # do any footnotes and cross-references
                        extraType, extraIndex, extraText, cleanExtraText = extra
                        adjIndex = extraIndex - offset
                        lenV = len( verse )
                        if adjIndex > lenV: # This can happen if we have verse/space/notes at end (and the space was deleted after the note was separated off)
                            logger.warning( _("toZefania: Space before note at end of verse in {} has been lost").format( toZefGlobals['verseRef'] ) )
                            # No need to adjust adjIndex because the code below still works
                        elif adjIndex<0 or adjIndex>lenV: # The extras don't appear to fit correctly inside the verse
                            print( "toZefania: Extras don't fit inside verse at {}: eI={} o={} len={} aI={}".format( toZefGlobals['verseRef'], extraIndex, offset, len(verse), adjIndex ) )
                            print( "  Verse={!r}".format( verse ) )
                            print( "  Extras={!r}".format( extras ) )
                        #assert 0 <= adjIndex <= len(verse)
                        adjText = checkZefaniaText( extraText, checkLeftovers=False ) # do any general character formatting on the notes
                        #if adjText!=extraText: print( "processZefXRefsAndFootnotes: {}@{}-{}={} {!r} now {!r}".format( extraType, extraIndex, offset, adjIndex, extraText, adjText ) )
                        if extraType == 'fn':
                            extra = processFootnote( adjText )
                            #print( "fn got", extra )
                        elif extraType == 'xr':
                            extra = processXRef( adjText )
                            #print( "xr got", extra )
                        elif extraType == 'fig':
                            logger.critical( "OSISXML figure not handled yet" )
                            extra = '' # temp
                            #extra = processFigure( extraText )
                            #print( "fig got", extra )
                        elif extraType == 'str':
                            extra = '' # temp
                        elif extraType == 'sem':
                            extra = '' # temp
                        elif extraType == 'vp':
                            extra = "\\vp {}\\vp*".format( extraText ) # Will be handled later
                        elif BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( extraType ); halt
                        #print( "was", verse )
                        verse = verse[:adjIndex] + str(extra) + verse[adjIndex:]
                        offset -= len( extra )
                        #print( "now", verse )
                return verse
            # end of toZefaniaXML.processZefXRefsAndFootnotes


            # Main code for toZefaniaXML.writeZefBook
            writerObject.writeLineOpen( 'BIBLEBOOK', [('bnumber',BibleOrgSysGlobals.loadedBibleBooksCodes.getReferenceNumber(BBB)), ('bname',BibleOrgSysGlobals.loadedBibleBooksCodes.getEnglishName_NR(BBB)), ('bsname',OSISAbbrev)] )
            haveOpenChapter, gotVP = False, None
            C, V = '-1', '-1' # So first/id line starts at -1:0
            for processedBibleEntry in bkData._processedLines: # Process internal Bible data lines
                haveNotesFlag = False
                marker, text, extras = processedBibleEntry.getMarker(), processedBibleEntry.getAdjustedText(), processedBibleEntry.getExtras()
                #if marker in ('id', 'ide', 'h', 'toc1','toc2','toc3', ): pass # Just ignore these metadata markers
                if '¬' in marker or marker in BOS_ADDED_NESTING_MARKERS or marker=='v=':
                    continue # Just ignore added markers — not needed here
                if marker in USFM_PRECHAPTER_MARKERS:
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
                        assert C=='-1' or marker=='rem' or marker.startswith('mte')
                    V = str( int(V) + 1 )

                if marker in OFTEN_IGNORED_USFM_HEADER_MARKERS or marker in ('ie',): # Just ignore these lines
                    ignoredMarkers.add( marker )
                elif marker == 'c':
                    C, V = text, '0'
                    toZefGlobals['verseRef'] = '{},{},{}'.format( BBB, C, V )
                    if haveOpenChapter:
                        writerObject.writeLineClose ( 'CHAPTER' )
                    writerObject.writeLineOpen ( 'CHAPTER', ('cnumber',text) )
                    haveOpenChapter = True
                elif marker == 'c#': # These are the markers that we can safely ignore for this export
                    ignoredMarkers.add( marker )
                elif marker == 'vp#': # This precedes a v field and has the verse number to be printed
                    gotVP = text # Just remember it for now
                elif marker == 'v':
                    V = text
                    toZefGlobals['verseRef'] = '{},{},{}'.format( BBB, C, V )
                    if gotVP: # this is the verse number to be published
                        text = gotVP
                        gotVP = None
                    #print( "Text {!r}".format( text ) )
                    if not text: logger.warning( "toZefania: Missing text for v" ); continue
                    verseNumberString, endVerseNumberString = handleVerseNumber( BBB, C, V, text )
                    #writerObject.writeLineOpenClose ( 'VERS', verseText, ('vnumber',verseNumberString) )

                elif marker in ('mt1','mt2','mt3','mt4', 'mte1','mte2','mte3','mte4', 'ms1','ms2','ms3','ms4',) \
                or marker in USFM_ALL_INTRODUCTION_MARKERS \
                or marker in ('s1','s2','s3','s4', 'r','sr','mr', 'd','sp','cd', 'cl','lit', ):
                    ignoredMarkers.add( marker )
                elif marker in USFM_BIBLE_PARAGRAPH_MARKERS:
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not text and not extras
                    ignoredMarkers.add( marker )
                elif marker in ('b', 'nb', 'ib', ):
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not text and not extras
                    ignoredMarkers.add( marker )
                elif marker == 'v~':
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert text or extras
                    #print( "Text {!r}".format( text ) )
                    if not text: # this is an empty (untranslated) verse
                         #logger.warning( "toZefania: Missing text for v~" )
                        text = '- - -' # but we'll put in a filler
                    else:
                        text = processZefXRefsAndFootnotes( text, extras )
                        text = checkZefaniaText( text, checkLeftovers=BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag or debuggingThisModule )
                        #if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag or debuggingThisModule:
                            #if '\\' in text: print( "toZefaniaX: {} {}:{} {!r}".format( BBB,C,V, text ) )
                            #assert '\\' not in text
                        if '<NOTE' in text or '<XREF' in text: haveNotesFlag = True
                    writerObject.writeLineOpenClose ( 'VERS', text,
                            ('vnumber',verseNumberString) if endVerseNumberString is None else [('vnumber',verseNumberString),('enumber',endVerseNumberString)],
                            noTextCheck=haveNotesFlag )
                elif marker == 'p~':
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert text or extras
                    text = processZefXRefsAndFootnotes( text, extras )
                    text = checkZefaniaText( text, checkLeftovers=BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag or debuggingThisModule )
                    #if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag or debuggingThisModule:
                        #if '\\' in text: print( "toZefaniaY: {} {}:{} {!r}".format( BBB,C,V, text ) )
                        #assert '\\' not in text
                    if '<NOTE' in text or '<XREF' in text: haveNotesFlag = True
                    if text: writerObject.writeLineOpenClose ( 'VERS', text, noTextCheck=haveNotesFlag )
                else:
                    if text:
                        logger.error( "toZefania: {} lost text in {} field in {} {}:{} {!r}".format( self.abbreviation, marker, BBB, C, V, text ) )
                        #if BibleOrgSysGlobals.debugFlag: halt
                    if extras:
                        logger.error( "toZefania: {} lost extras in {} field in {} {}:{}".format( self.abbreviation, marker, BBB, C, V ) )
                        #if BibleOrgSysGlobals.debugFlag: halt
                    unhandledMarkers.add( marker )
                if extras and marker not in ('v~','p~',) and marker not in ignoredMarkers:
                    logger.critical( "toZefania: extras not handled for {} at {} {}:{}".format( marker, BBB, C, V ) )
            if haveOpenChapter:
                writerObject.writeLineClose( 'CHAPTER' )
            writerObject.writeLineClose( 'BIBLEBOOK' )
        # end of toZefaniaXML.writeZefBook

        # Set-up our Bible reference system
        if 'PublicationCode' not in controlDict or controlDict['PublicationCode'] == 'GENERIC':
            BOS = self.genericBOS
            BRL = self.genericBRL
        else:
            BOS = BibleOrganisationalSystem( controlDict['PublicationCode'] )
            BRL = BibleReferenceList( BOS, BibleObject=None )

        if BibleOrgSysGlobals.verbosityLevel > 2: print( _("  Exporting to Zefania format…") )
        try: zOFn = controlDict['ZefaniaOutputFilename']
        except KeyError: zOFn = 'Bible.zef'
        filename = BibleOrgSysGlobals.makeSafeFilename( zOFn )
        xw = MLWriter( filename, outputFolderpath )
        xw.setHumanReadable()
        xw.start()
# TODO: Some modules have <XMLBIBLE xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="zef2005.xsd" version="2.0.1.18" status='v' revision="1" type="x-bible" biblename="KJV+">
        try: zBN = controlDict['ZefaniaBibleName']
        except KeyError: zBN = 'ExportedBible'
        xw.writeLineOpen( 'XMLBIBLE', [('xmlns:xsi',"http://www.w3.org/2001/XMLSchema-instance"), ('type','x-bible' ), ('biblename',zBN) ] )
        if True: #if controlDict['ZefaniaFiles']=="byBible":
            writeHeader( xw )
            for BBB,bookData in self.books.items():
                writeZefBook( xw, BBB, bookData )
        xw.writeLineClose( 'XMLBIBLE' )
        xw.close()

        if ignoredMarkers:
            logger.info( "toZefania: Ignored markers were {}".format( ignoredMarkers ) )
            if BibleOrgSysGlobals.verbosityLevel > 2:
                print( "  " + _("WARNING: Ignored toZefania markers were {}").format( ignoredMarkers ) )
        if unhandledMarkers:
            logger.warning( "toZefania: Unhandled markers were {}".format( unhandledMarkers ) )
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print( "  " + _("WARNING: Unhandled toZefania markers were {}").format( unhandledMarkers ) )
        if unhandledBooks:
            logger.warning( "toZefania: Unhandled books were {}".format( unhandledBooks ) )
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print( "  " + _("WARNING: Unhandled toZefania books were {}").format( unhandledBooks ) )

        # Now create a zipped version
        filepath = os.path.join( outputFolderpath, filename )
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Zipping {} Zefania file…".format( filename ) )
        zf = zipfile.ZipFile( filepath+'.zip', 'w', compression=zipfile.ZIP_DEFLATED )
        zf.write( filepath, filename )
        zf.close()

        if validationSchema: validationResult = xw.validate( validationSchema ) # Returns a 3-tuple: intCode, logString, errorLogString
        if BibleOrgSysGlobals.verbosityLevel > 0 and BibleOrgSysGlobals.maxProcesses > 1:
            print( "  BibleWriter.toZefaniaXML finished successfully." )
        if validationSchema: return validationResult # Returns a 3-tuple: intCode, logString, errorLogString
        return True
    # end of BibleWriter.toZefaniaXML



    def toHaggaiXML( self, outputFolderpath:Optional[Path]=None, controlDict=None, validationSchema=None ):
        """
        Using settings from the given control file,
            converts the USFM information to a UTF-8 Haggai XML file.

        This format is roughly documented at http://de.wikipedia.org/wiki/Haggai_XML
            but more fields can be discovered by looking at downloaded files.
        """
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Running BibleWriter:toHaggaiXML…" )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert self.books

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolderpath: outputFolderpath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_Haggai_Export/' )
        if not os.access( outputFolderpath, os.F_OK ): os.makedirs( outputFolderpath ) # Make the empty folder if there wasn't already one there
        if not controlDict:
            controlDict, defaultControlFilename = {}, "To_Haggai_controls.txt"
            try: ControlFiles.readControlFile( defaultControlFolderpath, defaultControlFilename, controlDict )
            except FileNotFoundError:
                logger.critical( "Unable to read control dict {} from {}".format( defaultControlFilename, defaultControlFolderpath ) )
        self.__adjustControlDict( controlDict )
        if not validationSchema: # We'll use our copy
            xsdFilepath = 'ExternalSchemas/haggai_20130620.xsd'
            if os.path.exists( xsdFilepath ): validationSchema = xsdFilepath

        ignoredMarkers, unhandledMarkers, unhandledBooks = set(), set(), []

        def writeHeader( writerObject ):
            """
            Writes the Haggai header to the Haggai XML writerObject.
            """
            writerObject.writeLineOpen( 'INFORMATION' )
            if 'HaggaiTitle' in controlDict and controlDict['HaggaiTitle']: writerObject.writeLineOpenClose( 'title' , controlDict['HaggaiTitle'] )
            if 'HaggaiSubject' in controlDict and controlDict['HaggaiSubject']: writerObject.writeLineOpenClose( 'subject', controlDict['HaggaiSubject'] )
            if 'HaggaiDescription' in controlDict and controlDict['HaggaiDescription']: writerObject.writeLineOpenClose( 'description', controlDict['HaggaiDescription'] )
            if 'HaggaiPublisher' in controlDict and controlDict['HaggaiPublisher']: writerObject.writeLineOpenClose( 'publisher', controlDict['HaggaiPublisher'] )
            if 'HaggaiContributors' in controlDict and controlDict['HaggaiContributors']: writerObject.writeLineOpenClose( 'contributors', controlDict['HaggaiContributors'] )
            if 'HaggaiIdentifier' in controlDict and controlDict['HaggaiIdentifier']: writerObject.writeLineOpenClose( 'identifier', controlDict['HaggaiIdentifier'] )
            if 'HaggaiSource' in controlDict and controlDict['HaggaiSource']: writerObject.writeLineOpenClose( 'identifier', controlDict['HaggaiSource'] )
            if 'HaggaiCoverage' in controlDict and controlDict['HaggaiCoverage']: writerObject.writeLineOpenClose( 'coverage', controlDict['HaggaiCoverage'] )
            writerObject.writeLineOpenClose( 'format', 'Haggai XML Bible Markup Language' )
            writerObject.writeLineOpenClose( 'date', datetime.now().date().isoformat() )
            writerObject.writeLineOpenClose( 'creator', 'BibleWriter.py' )
            writerObject.writeLineOpenClose( 'type', 'bible text' )
            if 'HaggaiLanguage' in controlDict and controlDict['HaggaiLanguage']: writerObject.writeLineOpenClose( 'language', controlDict['HaggaiLanguage'] )
            if 'HaggaiRights' in controlDict and controlDict['HaggaiRights']: writerObject.writeLineOpenClose( 'rights', controlDict['HaggaiRights'] )
            writerObject.writeLineClose( 'INFORMATION' )
        # end of toHaggaiXML.writeHeader

        def writeHagBook( writerObject, BBB, bkData ):
            """
            Writes a book to the Haggai XML writerObject.
            """
            #print( 'BIBLEBOOK', [('bnumber',BibleOrgSysGlobals.loadedBibleBooksCodes.getReferenceNumber(BBB)), ('bname',BibleOrgSysGlobals.loadedBibleBooksCodes.getEnglishName_NR(BBB)), ('bsname',BibleOrgSysGlobals.loadedBibleBooksCodes.getOSISAbbreviation(BBB))] )
            OSISAbbrev = BibleOrgSysGlobals.loadedBibleBooksCodes.getOSISAbbreviation( BBB )
            if not OSISAbbrev:
                logger.error( "toHaggai: Can't write {} Haggai book because no OSIS code available".format( BBB ) )
                unhandledBooks.append( BBB )
                return
            writerObject.writeLineOpen( 'BIBLEBOOK', [('bnumber',BibleOrgSysGlobals.loadedBibleBooksCodes.getReferenceNumber(BBB)), ('bname',BibleOrgSysGlobals.loadedBibleBooksCodes.getEnglishName_NR(BBB)), ('bsname',OSISAbbrev)] )
            haveOpenChapter = haveOpenParagraph = False
            gotVP = None
            C, V = '-1', '-1' # So first/id line starts at -1:0
            for processedBibleEntry in bkData._processedLines: # Process internal Bible data lines
                marker, text, extras = processedBibleEntry.getMarker(), processedBibleEntry.getAdjustedText(), processedBibleEntry.getExtras()
                #if marker in ('id', 'ide', 'h', 'toc1','toc2','toc3', ): pass # Just ignore these metadata markers
                if '¬' in marker or marker in BOS_ADDED_NESTING_MARKERS or marker=='v=':
                    continue # Just ignore added markers — not needed here
                if marker in USFM_PRECHAPTER_MARKERS:
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
                        assert C=='-1' or marker=='rem' or marker.startswith('mte')
                    V = str( int(V) + 1 )

                if marker in OFTEN_IGNORED_USFM_HEADER_MARKERS or marker in ('ie',): # Just ignore these lines
                    ignoredMarkers.add( marker )
                elif marker == 'c':
                    C, V = text, '0'
                    if haveOpenParagraph:
                        writerObject.writeLineClose ( 'PARAGRAPH' ); haveOpenParagraph = False
                    if haveOpenChapter:
                        writerObject.writeLineClose ( 'CHAPTER' )
                    writerObject.writeLineOpen ( 'CHAPTER', ('cnumber',text) )
                    haveOpenChapter = True
                elif marker in ('c#',): # These are the markers that we can safely ignore for this export
                    ignoredMarkers.add( marker )
                elif marker == 'vp#': # This precedes a v field and has the verse number to be printed
                    gotVP = text # Just remember it for now
                elif marker == 'v':
                    V = text
                    if gotVP: # this is the verse number to be published
                        text = gotVP
                        gotVP = None
                    #print( "Text {!r}".format( text ) )
                    if not text: logger.warning( "toHaggaiXML: Missing text for v" ); continue
                    verseNumberString = text.replace('<','').replace('>','').replace('"','') # Used below but remove anything that'll cause a big XML problem later
                    #writerObject.writeLineOpenClose ( 'VERS', verseText, ('vnumber',verseNumberString) )

                elif marker in ('p', 'pi1','pi2','pi3','pi4', ):
                    if haveOpenParagraph:
                        writerObject.writeLineClose ( 'PARAGRAPH' )
                    writerObject.writeLineOpen ( 'PARAGRAPH' )
                    haveOpenParagraph = True
                elif marker in ('mt1','mt2','mt3','mt4', 'mte1','mte2','mte3','mte4', 'ms1','ms2','ms3','ms4', ) \
                or marker in USFM_ALL_INTRODUCTION_MARKERS \
                or marker in ('s1','s2','s3','s4', 'r','sr','mr', 'd','sp','cd', 'cl','lit', ):
                    ignoredMarkers.add( marker )
                elif marker in USFM_BIBLE_PARAGRAPH_MARKERS:
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not text and not extras
                    ignoredMarkers.add( marker )
                elif marker in ('b', 'nb', 'ib', ):
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not text and not extras
                    ignoredMarkers.add( marker )
                elif marker == 'v~':
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert text or extras
                    #print( "Text {!r}".format( text ) )
                    if not text: logger.warning( "toHaggaiXML: Missing text for v~" ); continue
                    # TODO: We haven't stripped out character fields from within the verse — not sure how Haggai handles them yet
                    if not text: # this is an empty (untranslated) verse
                        text = '- - -' # but we'll put in a filler
                    writerObject.writeLineOpenClose ( 'VERSE', text, ('vnumber',verseNumberString) )
                elif marker == 'p~':
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert text or extras
                    # TODO: We haven't stripped out character fields from within the verse — not sure how Haggai handles them yet
                    if text: writerObject.writeLineOpenClose ( 'VERSE', text )
                else:
                    if text:
                        logger.error( "toHaggai: {} lost text in {} field in {} {}:{} {!r}".format( self.abbreviation, marker, BBB, C, V, text ) )
                        #if BibleOrgSysGlobals.debugFlag: halt
                    if extras:
                        logger.error( "toHaggai: {} lost extras in {} field in {} {}:{}".format( self.abbreviation, marker, BBB, C, V ) )
                        #if BibleOrgSysGlobals.debugFlag: halt
                    unhandledMarkers.add( marker )
                if extras and marker not in ('v~','p~',) and marker not in ignoredMarkers:
                    logger.critical( "toHaggai: extras not handled for {} at {} {}:{}".format( marker, BBB, C, V ) )
            if haveOpenParagraph:
                writerObject.writeLineClose ( 'PARAGRAPH' )
            if haveOpenChapter:
                writerObject.writeLineClose( 'CHAPTER' )
            writerObject.writeLineClose( 'BIBLEBOOK' )
        # end of toHaggaiXML.writeHagBook

        # Set-up our Bible reference system
        if 'PublicationCode' not in controlDict or controlDict['PublicationCode'] == 'GENERIC':
            BOS = self.genericBOS
            BRL = self.genericBRL
        else:
            BOS = BibleOrganisationalSystem( controlDict['PublicationCode'] )
            BRL = BibleReferenceList( BOS, BibleObject=None )

        if BibleOrgSysGlobals.verbosityLevel > 2: print( _("  Exporting to Haggai format…") )
        try: hOFn = controlDict['HaggaiOutputFilename']
        except KeyError: hOFn = 'Bible.hag'
        filename = BibleOrgSysGlobals.makeSafeFilename( hOFn )
        xw = MLWriter( filename, outputFolderpath )
        xw.setHumanReadable()
        xw.start()
# TODO: Some modules have <XMLBIBLE xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="zef2005.xsd" version="2.0.1.18" status='v' revision="1" type="x-bible" biblename="KJV+">
        try: hBN = controlDict['HaggaiBibleName']
        except KeyError: hBN = 'ExportedBible'
        xw.writeLineOpen( 'XMLBible', [('xmlns:xsi',"http://www.w3.org/2001/XMLSchema-instance"), ('type',"x-bible" ), ('biblename',hBN) ] )
        if True: #if controlDict['HaggaiFiles']=='byBible':
            writeHeader( xw )
            for BBB,bookData in self.books.items():
                writeHagBook( xw, BBB, bookData )
        xw.writeLineClose( 'XMLBible' )
        xw.close()

        if ignoredMarkers:
            logger.info( "toHaggai: Ignored markers were {}".format( ignoredMarkers ) )
            if BibleOrgSysGlobals.verbosityLevel > 2:
                print( "  " + _("WARNING: Ignored toHaggai markers were {}").format( ignoredMarkers ) )
        if unhandledMarkers:
            logger.warning( "toHaggai: Unhandled markers were {}".format( unhandledMarkers ) )
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print( "  " + _("WARNING: Unhandled toHaggai markers were {}").format( unhandledMarkers ) )
        if unhandledBooks:
            logger.warning( "toHaggai: Unhandled books were {}".format( unhandledBooks ) )
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print( "  " + _("WARNING: Unhandled toHaggai books were {}").format( unhandledBooks ) )

        # Now create a zipped version
        filepath = os.path.join( outputFolderpath, filename )
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Zipping {} Haggai file…".format( filename ) )
        zf = zipfile.ZipFile( filepath+'.zip', 'w', compression=zipfile.ZIP_DEFLATED )
        zf.write( filepath, filename )
        zf.close()

        if validationSchema: validationResult = xw.validate( validationSchema ) # Returns a 3-tuple: intCode, logString, errorLogString
        if BibleOrgSysGlobals.verbosityLevel > 0 and BibleOrgSysGlobals.maxProcesses > 1:
            print( "  BibleWriter.toHaggaiXML finished successfully." )
        if validationSchema: return validationResult # Returns a 3-tuple: intCode, logString, errorLogString
        return True
    # end of BibleWriter.toHaggaiXML



    def toOpenSongXML( self, outputFolderpath:Optional[Path]=None, controlDict=None, validationSchema=None ):
        """
        Using settings from the given control file,
            converts the USFM information to a UTF-8 OpenSong XML file.

        This format is roughly documented at http://de.wikipedia.org/wiki/OpenSong_XML
            but more fields can be discovered by looking at downloaded files.
        """
        from BibleOrgSys.Formats.OpenSongXMLBible import createOpenSongXML

        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Running BibleWriter:toOpenSongXML…" )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert self.books

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolderpath: outputFolderpath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_OpenSong_Export/' )
        if not os.access( outputFolderpath, os.F_OK ): os.makedirs( outputFolderpath ) # Make the empty folder if there wasn't already one there
        if not controlDict:
            controlDict, defaultControlFilename = {}, "To_OpenSong_controls.txt"
            try: ControlFiles.readControlFile( defaultControlFolderpath, defaultControlFilename, controlDict )
            except FileNotFoundError:
                logger.critical( "Unable to read control dict {} from {}".format( defaultControlFilename, defaultControlFolderpath ) )
        self.__adjustControlDict( controlDict )

        return createOpenSongXML( self, outputFolderpath, controlDict, validationSchema )
    # end of BibleWriter.toOpenSongXML



    def toSwordModule( self, outputFolderpath:Optional[Path]=None, controlDict=None, validationSchema=None ):
        """
        Using settings from the given control file,
            converts the USFM information to a UTF-8 OSIS-XML-based Sword module.
        """
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Running BibleWriter:toSwordModule…" )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert self.books

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolderpath: outputFolderpath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_Sword_Export/' )
        if not os.access( outputFolderpath, os.F_OK ): os.makedirs( outputFolderpath ) # Make the empty folder if there wasn't already one there
        if not controlDict:
            controlDict, defaultControlFilename = {}, "To_OSIS_controls.txt"
            try: ControlFiles.readControlFile( defaultControlFolderpath, defaultControlFilename, controlDict )
            except FileNotFoundError:
                logger.critical( "Unable to read control dict {} from {}".format( defaultControlFilename, defaultControlFolderpath ) )
        self.__adjustControlDict( controlDict )

        import struct
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert struct.calcsize("IH") == 6 # Six-byte format

        # Set-up our Bible reference system
        if 'PublicationCode' not in controlDict or controlDict['PublicationCode'] == 'GENERIC':
            BOS = self.genericBOS
            BRL = self.genericBRL
        else:
            BOS = BibleOrganisationalSystem( controlDict['PublicationCode'] )
            BRL = BibleReferenceList( BOS, BibleObject=None )

        booksNamesSystemName = BOS.getOrganisationalSystemValue( 'booksNamesSystem' )
        if booksNamesSystemName and booksNamesSystemName!='None' and booksNamesSystemName!='Unknown': # default (if we know the book names system)
            getBookNameFunction = BOS.getBookName
            getBookAbbreviationFunction = BOS.getBookAbbreviation
        else: # else use our local functions from our deduced book names
            getBookNameFunction = self.getAssumedBookName # from BibleOrgSys.Formats.USFMBible (which gets it from BibleOrgSys.Formats.USFMBibleBook)
            getBookAbbreviationFunction = BibleOrgSysGlobals.loadedBibleBooksCodes.getOSISAbbreviation

        if 0:
            bookAbbrevDict, bookNameDict, bookAbbrevNameDict = {}, {}, {}
            for BBB in BibleOrgSysGlobals.loadedBibleBooksCodes.getAllReferenceAbbreviations(): # Pre-process the language booknames
                if BBB in controlDict and controlDict[BBB]:
                    bits = controlDict[BBB].split(',')
                    if len(bits)!=2: logger.error( _("toSwordModule: Unrecognized language book abbreviation and name for {}: {!r}").format( BBB, controlDict[BBB] ) )
                    bookAbbrev = bits[0].strip().replace('"','') # Remove outside whitespace then the double quote marks
                    bookName = bits[1].strip().replace('"','') # Remove outside whitespace then the double quote marks
                    bookAbbrevDict[bookAbbrev], bookNameDict[bookName], bookAbbrevNameDict[BBB] = BBB, BBB, (bookAbbrev,bookName,)
                    if ' ' in bookAbbrev: bookAbbrevDict[bookAbbrev.replace(' ','',1)] = BBB # Duplicate entries without the first space (presumably between a number and a name like 1 Kings)
                    if ' ' in bookName: bookNameDict[bookName.replace(' ','',1)] = BBB # Duplicate entries without the first space

        ignoredMarkers, unhandledMarkers, unhandledBooks = set(), set(), []


        # Let's write a Sword locale while we're at it
        try: xL = controlDict['xmlLanguage']
        except KeyError: xL = 'eng'
        try: lN = controlDict['LanguageName']
        except KeyError: lN = 'eng'
        self._writeSwordLocale( xL, lN, BOS, getBookNameFunction, os.path.join( outputFolderpath, 'SwLocale-utf8.conf' ) )
        #SwLocFilepath = os.path.join( outputFolderpath, 'SwLocale-utf8.conf" )
        #if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Writing Sword locale file {}…").format(SwLocFilepath) )
        #with open( SwLocFilepath, 'wt', encoding='utf-8' ) as SwLocFile:
            #SwLocFile.write( '[Meta]\nName={}\n'.format(controlDict['xmlLanguage']) )
            #SwLocFile.write( 'Description={}\n'.format(controlDict['LanguageName']) )
            #SwLocFile.write( 'Encoding=UTF-8\n\n[Text]\n' )
            #for BBB in BOS.getBookList():
                #if BBB in self.books:
                    #SwLocFile.write( '{}={}\n'.format(BibleOrgSysGlobals.loadedBibleBooksCodes.getEnglishName_NR(BBB), getBookNameFunction(BBB) ) ) # Write the first English book name and the vernacular book name
            #SwLocFile.write( '\n[Book Abbrevs]\n' )
            #for BBB in BOS.getBookList():
                #if BBB in self.books:
                    #SwLocFile.write( '{}={}\n'.format(BibleOrgSysGlobals.loadedBibleBooksCodes.getEnglishName_NR(BBB).upper(), BibleOrgSysGlobals.loadedBibleBooksCodes.getSwordAbbreviation(BBB) ) ) # Write the UPPER CASE language book name and the Sword abbreviation

        # Make our other folders if necessary
        modsdFolder = os.path.join( outputFolderpath, 'mods.d' )
        if not os.access( modsdFolder, os.F_OK ): os.mkdir( modsdFolder ) # Make the empty folder if there wasn't already one there
        modulesFolder = os.path.join( outputFolderpath, 'modules' )
        if not os.access( modulesFolder, os.F_OK ): os.mkdir( modulesFolder ) # Make the empty folder if there wasn't already one there
        textsFolder = os.path.join( modulesFolder, 'texts' )
        if not os.access( textsFolder, os.F_OK ): os.mkdir( textsFolder ) # Make the empty folder if there wasn't already one there
        rawTextFolder = os.path.join( textsFolder, 'rawtext' )
        if not os.access( rawTextFolder, os.F_OK ): os.mkdir( rawTextFolder ) # Make the empty folder if there wasn't already one there
        try: oW = controlDict['osisWork'].lower()
        except KeyError: oW = 'Bible'
        lgFolder = os.path.join( rawTextFolder, BibleOrgSysGlobals.makeSafeFilename( oW ) )
        if not os.access( lgFolder, os.F_OK ): os.mkdir( lgFolder ) # Make the empty folder if there wasn't already one there

        toSwordGlobals = { 'currentID':0, "idStack":[], "verseRef":'', "XRefNum":0, "FootnoteNum":0, "lastRef":'', 'offset':0, 'length':0, "OneChapterOSISBookCodes":BibleOrgSysGlobals.loadedBibleBooksCodes.getOSISSingleChapterBooksList() } # These are our global variables


        def makeConfFile( modsdFolder, compressedFlag ):
            """ Make a conf file for the Sword modules. """
            emailAddress = contactName = "Unknown"
            adjustedProjectName = self.projectName.lower().replace( ' ', '_' )

            # Read the default conf file
            try:
                with open( os.path.join( defaultControlFolderpath, 'SwordProject.conf' ) ) as myFile: confText = myFile.read()
            except FileNotFoundError:
                print( "dCF", defaultControlFolderpath )
                logger.critical( "toSwordModule: Unable to read sample conf file SwordProject.conf" )
                confText = ''
            # Do common text replacements
            # Unfortunately, we can only really make wild guesses without more detailed metadata
            # Of course, version should be the TEXT version not the PROGRAM version
            confText = confText.replace( '__ADJUSTED_PROJECT_NAME__', adjustedProjectName ).replace( '__PROJECT_NAME__', self.projectName ) \
                                .replace( '__EMAIL__', emailAddress ) \
                                .replace( '__NAME__', contactName ).replace( '__VERSION__', PROGRAM_VERSION )
            confText = confText.replace('rawtext','ztext').replace('RawText','zText') if compressedFlag \
                                else confText.replace('CompressType=ZIP\n','')

            # Do known language replacements
            pnUpper = self.projectName.upper()
            if "INDONESIA" in pnUpper:
                confText = confText.replace( '__LANGUAGE__', 'id' )

            # Do replacements from metadata
            #print( "  Given Project name is", projectName )
            #print( "  Given Email is", emailAddress )
            #print( "  Given Name is", projectName )
            #if 'FullName' in self.settingsDict:
                #print( "  SSF Full name (unused) is", self.settingsDict['FullName'] )
            name = self.getSetting( 'Name' )
            if name:
            #if 'Name' in self.settingsDict:
                #print( "  SSF Name is", self.settingsDict['Name'] )
                confText = confText.replace( '__ABBREVIATION__', name )
            language = self.getSetting( 'Language' )
            if language:
            #if 'Language' in self.settingsDict:
                #print( "  SSF Language is", self.settingsDict['Language'] )
                confText = confText.replace( '__LANGUAGE__', language )
            #if 'productName' in self.settingsDict:
                #print( "  SSF Product name (unused) is", self.settingsDict['productName'] )
            #if 'LanguageIsoCode' in self.settingsDict:
                #print( "  SSF Language Iso Code (unused) is", self.settingsDict['LanguageIsoCode'] )

            # Do exasperated replacements if there's any unknown fields left (coz we have no better info)
            confText = confText.replace( '__ABBREVIATION__', 'NONE' )
            confText = confText.replace( '__LANGUAGE__', 'UNKNOWN' )

            # Write the new file
            confFilename = BibleOrgSysGlobals.makeSafeFilename( adjustedProjectName + '.conf' )
            confFilepath = os.path.join( modsdFolder, confFilename )
            with open( confFilepath, 'wt', encoding='utf-8' ) as myFile:
                myFile.write( confText )
        # end of makeConfFile


        def writeIndexEntry( writerObject, indexFile ):
            """ Writes a newline to the main file and an entry to the index file. """
            writerObject.writeNewLine()
            writerObject._writeToBuffer( "IDX " ) # temp … XXXXXXX
            indexFile.write( struct.pack( "IH", toSwordGlobals['offset'], toSwordGlobals['length'] ) )
            toSwordGlobals['offset'] = writerObject.getFilePosition() # Get the new offset
            toSwordGlobals['length'] = 0 # Reset
        # end of toSwordModule.writeIndexEntry

        def writeSwordBook( writerObject, ix, BBB, bkData ):
            """ Writes a Bible book to the output files. """

            def checkSwordText( textToCheck ):
                """Handle some general backslash codes and warn about any others still unprocessed."""

                def checkSwordTextHelper( marker, helpText ):
                    """ Adjust the text to make the number of start and close markers equal. """
                    count1, count2 = helpText.count('\\'+marker+' '), helpText.count('\\'+marker+'*') # count open and close markers
                    while count1 < count2:
                        helpText = '\\'+marker+' ' + helpText
                        count1, count2 = helpText.count('\\'+marker+' '), helpText.count('\\'+marker+'*') # count open and close markers again
                    while count1 > count2:
                        helpText += '\\'+marker+'*'
                        count1, count2 = helpText.count('\\'+marker+' '), helpText.count('\\'+marker+'*') # count open and close markers again
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert count1 == count2
                    return helpText
                # end of toSwordModule.checkSwordTextHelper

                adjText = textToCheck
                if '<<' in adjText or '>>' in adjText:
                    logger.warning( _("toSwordModule: Unexpected double angle brackets in {}: {!r} field is {!r}").format(toSwordGlobals['verseRef'],marker,textToCheck) )
                    adjText = adjText.replace('<<','“' ).replace('>>','”' )
                if '\\bk ' in adjText: adjText = checkSwordTextHelper('bk',adjText).replace('\\bk ','<reference type="x-bookName">').replace('\\bk*','</reference>')
                if '\\ior ' in adjText: adjText = checkSwordTextHelper('ior',adjText).replace('\\ior ','<reference>').replace('\\ior*','</reference>')
                if '\\add ' in adjText: adjText = checkSwordTextHelper('add',adjText).replace('\\add ','<i>').replace('\\add*','</i>') # temp XXXXXX …
                if '\\nd ' in adjText: adjText = checkSwordTextHelper('nd',adjText).replace('\\nd ','<divineName>').replace('\\nd*','</divineName>')
                if '\\wj ' in adjText: adjText = checkSwordTextHelper('wj',adjText).replace('\\wj ','<hi type="bold">').replace('\\wj*','</hi>') # XXXXXX temp …
                if '\\sig ' in adjText: adjText = checkSwordTextHelper('sig',adjText).replace('\\sig ','<b>').replace('\\sig*','</b>') # temp…… XXXXXXX
                if '\\it ' in adjText: adjText = checkSwordTextHelper('it',adjText).replace('\\it ','<hi type="italic">').replace('\\it*','</hi>')
                if '\\bd ' in adjText: adjText = checkSwordTextHelper('bd',adjText).replace('\\bd ','<hi type="bold">').replace('\\bd*','</hi>')
                if '\\em ' in adjText: adjText = checkSwordTextHelper('em',adjText).replace('\\em ','<hi type="bold">').replace('\\em*','</hi>')
                if '\\sc ' in adjText: adjText = checkSwordTextHelper('sc',adjText).replace('\\sc ','<hi type="SMALLCAPS">').replace('\\sc*','</hi>') # XXXXXX temp …
                if '\\' in adjText:
                    logger.error( _("toSwordModule: We still have some unprocessed backslashes for Sword in {}: {!r} field is {!r}").format(toSwordGlobals['verseRef'],marker,textToCheck) )
                    adjText = adjText.replace('\\','ENCODING ERROR HERE ' )
                return adjText
            # end of toSwordModule.checkSwordText

            def processXRefsAndFootnotes( verse, extras ):
                """
                Convert cross-references and footnotes and return the adjusted verse text.
                """

                def processXRef( USFMxref ):
                    """
                    Return the OSIS code for the processed cross-reference (xref).

                    NOTE: The parameter here already has the /x and /x* removed.

                    \\x - \\xo 2:2: \\xt Lib 19:9-10; Diy 24:19.\\xt*\\x* (Backslashes are shown doubled here)
                        gives
                    <note type="crossReference" n="1">2:2: <reference>Lib 19:9-10; Diy 24:19.</reference></note> (Crosswire — invalid OSIS — which then needs to be converted)
                    <note type="crossReference" osisRef="Ruth.2.2" osisID="Ruth.2.2!crossreference.1" n="-"><reference type="source" osisRef="Ruth.2.2">2:2: </reference><reference osisRef="-">Lib 19:9-10</reference>; <reference osisRef="Ruth.Diy.24!:19">Diy 24:19</reference>.</note> (Snowfall)
                    \\x - \\xo 3:5: a \\xt Rum 11:1; \\xo b \\xt Him 23:6; 26:5.\\xt*\\x* is more complex still.
                    """
                    nonlocal BBB
                    toSwordGlobals["XRefNum"] += 1
                    OSISxref = '<note type="crossReference" osisRef="{}" osisID="{}!crossreference.{}">'.format(toSwordGlobals['verseRef'],toSwordGlobals['verseRef'],toSwordGlobals["XRefNum"])
                    for j,token in enumerate(USFMxref.split('\\')):
                        #print( "processXRef", j, "'"+token+"'", "from", '"'+USFMxref+'"' )
                        if j==0: # The first token (but the x has already been removed)
                            rest = token.strip()
                            if rest != '+':
                                logger.warning( _("toSwordModule1: We got something else here other than plus (probably need to do something with it): {} {!r} from {!r}").format(chapterRef, token, text) )
                        elif token.startswith('xo '): # xref reference follows
                            adjToken = token[3:].strip()
                            if adjToken.endswith(' a'): adjToken = adjToken[:-2] # Remove any 'a' suffix (occurs when a cross-reference has multiple (a and b) parts
                            if adjToken.endswith(':'): adjToken = adjToken[:-1] # Remove any final colon (this is a language dependent hack)
                            adjToken = getBookAbbreviationFunction(BBB) + ' ' + adjToken # Prepend the vernacular book abbreviation
                            osisRef = BRL.parseToOSIS( adjToken )
                            if osisRef is not None:
                                OSISxref += '<reference type="source" osisRef="{}">{}</reference>'.format(osisRef,token[3:])
                                if not BRL.containsReference( BBB, currentChapterNumberString, verseNumberString ):
                                    logger.error( _("toSwordModule: Cross-reference at {} {}:{} seems to contain the wrong self-reference {!r}").format(BBB,currentChapterNumberString,verseNumberString, token) )
                        elif token.startswith('xt '): # xref text follows
                            xrefText = token[3:]
                            finalPunct = ''
                            while xrefText[-1] in ' ,;.': finalPunct = xrefText[-1] + finalPunct; xrefText = xrefText[:-1]
                            #adjString = xrefText[:-6] if xrefText.endswith( ' (LXX)' ) else xrefText # Sorry, this is a crude hack to avoid unnecessary error messages
                            osisRef = BRL.parseToOSIS( xrefText )
                            if osisRef is not None:
                                OSISxref += '<reference type="source" osisRef="{}">{}</reference>'.format(osisRef,xrefText+finalPunct)
                        elif token.startswith('x '): # another whole xref entry follows
                            rest = token[2:].strip()
                            if rest != '+':
                                logger.warning( _("toSwordModule2: We got something else here other than plus (probably need to do something with it): {} {!r} from {!r}").format(chapterRef, token, text) )
                        elif token in ('xt*', 'x*'):
                            pass # We're being lazy here and not checking closing markers properly
                        else:
                            logger.warning( _("toSwordModule: Unprocessed {!r} token in {} xref {!r}").format(token, toSwordGlobals['verseRef'], USFMxref) )
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
                    OSISfootnote = '<note osisRef="{}" osisID="{}!footnote.{}">'.format(toSwordGlobals['verseRef'],toSwordGlobals['verseRef'],toSwordGlobals["FootnoteNum"])
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
                                    logger.error( _("toSwordModule: Footnote at {} {}:{} seems to contain the wrong self-reference {!r}").format(BBB,currentChapterNumberString,verseNumberString, token) )
                        elif token.startswith('ft '): # footnote text follows
                            OSISfootnote += token[3:]
                        elif token.startswith('fq ') or token.startswith('fqa '): # footnote quote follows — NOTE: We also assume here that the next marker closes the fq field
                            OSISfootnote += '<catchWord>{}</catchWord>'.format(token[3:]) # Note that the trailing space goes in the catchword here — seems messy
                        elif token in ('ft*','ft* ','fq*','fq* ','fqa*','fqa* '):
                            pass # We're being lazy here and not checking closing markers properly
                        else:
                            logger.warning( _("toSwordModule: Unprocessed {!r} token in {} footnote {!r}").format(token, toSwordGlobals['verseRef'], USFMfootnote) )
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
                        logger.warning( _("toSwordModule: No space after xref entry in {}").format(toSwordGlobals['verseRef']) )
                    else: ix2b = ix2 + 4
                    xref = verse[ix1+3:ix2]
                    osisXRef = processXRef( xref )
                    #print( osisXRef )
                    verse = verse[:ix1] + osisXRef + verse[ix2b:]
                while '\\f ' in verse and '\\f*' in verse: # process footnotes
                    ix1 = verse.index('\\f ')
                    ix2 = verse.find('\\f*')
#                    ix2 = verse.find('\\f* ') # Note the extra space here at the end — doesn't always work if there's two footnotes within one verse!!!
#                    if ix2 == -1: # Didn't find it so must be no space after the asterisk
#                        ix2 = verse.index('\\f*')
#                        ix2b = ix2 + 3 # Where the footnote ends
#                        #logger.warning( 'toSwordModule: No space after footnote entry in {}'.format(toSwordGlobals['verseRef'] )
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
                osisID = sID = toSwordGlobals['verseRef'] # default
                if haveOpenVsID != False: # Close the previous verse
                    writerObject.writeLineOpenSelfclose( 'verse', ('eID',haveOpenVsID) )
                #verseNumberString = text.split()[0] # Get the first token which is the first number
                #verseText = text[len(verseNumberString)+1:].lstrip() # Get the rest of the string which is the verse text
                if '-' in verseNumberString:
                    bits = verseNumberString.split('-')
                    if len(bits)!=2 or not bits[0].isdigit() or not bits[1].isdigit():
                        logger.critical( _("toSwordModule: {} doesn't handle verse number of form {!r} yet for {}").format(self.abbreviation, verseNumberString,chapterRef) )
                    toSwordGlobals['verseRef']  = chapterRef + '.' + bits[0]
                    verseRef2 = chapterRef + '.' + bits[1]
                    sID    = toSwordGlobals['verseRef'] + '-' + verseRef2
                    osisID = toSwordGlobals['verseRef'] + ' ' + verseRef2
                elif ',' in verseNumberString:
                    bits = verseNumberString.split(',')
                    if len(bits)<2 or not bits[0].isdigit() or not bits[1].isdigit():
                        logger.critical( _("toSwordModule: {} doesn't handle verse number of form {!r} yet for {}").format(self.abbreviation, verseNumberString,chapterRef) )
                    sID = toSwordGlobals['verseRef'] = chapterRef + '.' + bits[0]
                    osisID = ''
                    for bit in bits: # Separate the OSIS ids by spaces
                        osisID += ' ' if osisID else ''
                        osisID += chapterRef + '.' + bit
                    #print( "Hey comma verses {!r} {!r}".format( sID, osisID ) )
                elif verseNumberString.isdigit():
                    sID = osisID = toSwordGlobals['verseRef'] = chapterRef + '.' + verseNumberString
                else:
                    logger.critical( _("toSwordModule: {} doesn't handle verse number of form {!r} yet for {}").format(self.abbreviation, verseNumberString,chapterRef) )
                writerObject.writeLineOpenSelfclose( 'verse', [('sID',sID), ('osisID',osisID)] ); haveOpenVsID = sID
                #adjText = processXRefsAndFootnotes( verseText, extras )
                #writerObject.writeLineText( checkSwordText(adjText), noTextCheck=True )
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


            # Main code for toSwordModule.writeSwordBook
            bookRef = BibleOrgSysGlobals.loadedBibleBooksCodes.getOSISAbbreviation( BBB ) # OSIS book name
            writerObject.writeLineOpen( 'div', [('osisID',bookRef), getSID(), ('type',"book")] )
            haveOpenIntro = haveOpenOutline = haveOpenMajorSection = haveOpenSection = haveOpenSubsection = False
            needChapterEID = haveOpenParagraph = haveOpenVsID = haveOpenLG = haveOpenL = haveOpenList = False
            lastMarker = unprocessedMarker = ''
            gotVP = None
            C, V = '-1', '-1' # So first/id line starts at -1:0
            chapterRef = bookRef + '.0'
            for processedBibleEntry in bkData._processedLines: # Process internal Bible data lines
                marker, text, extras = processedBibleEntry.getMarker(), processedBibleEntry.getAdjustedText(), processedBibleEntry.getExtras()
                if '¬' in marker or marker in BOS_ADDED_NESTING_MARKERS or marker=='v=':
                    continue # Just ignore added markers — not needed here
                if marker in USFM_PRECHAPTER_MARKERS:
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
                        assert C=='-1' or marker=='rem' or marker.startswith('mte')
                    V = str( int(V) + 1 )
                #print( BBB, marker, text )
                #print( " ", haveOpenIntro, haveOpenOutline, haveOpenMajorSection, haveOpenSection, haveOpenSubsection, needChapterEID, haveOpenParagraph, haveOpenVsID, haveOpenLG, haveOpenL )
                #print( toSwordGlobals['idStack'] )

                if haveOpenList and marker not in ('li1','li2','li3','li4', 'ili1','ili2','ili3','ili4',):
                    writerObject.writeLineClose( 'list' )
                    haveOpenList = False

                if marker in OFTEN_IGNORED_USFM_HEADER_MARKERS or marker in ('ie',): # Just ignore these lines
                    ignoredMarkers.add( marker )
                elif marker in ('mt1','mt2','mt3','mt4', 'mte1','mte2','mte3','mte4',):
                    if text: writerObject.writeLineOpenClose( 'title', checkSwordText(text), ('canonical',"false") )
                elif marker in ('is1','is2','is3','is4', 'imt1','imt2','imt3','imt4', 'imte1','imte2','imte3','imte4', ):
                    if haveOpenIntro: # already — assume it's a second one
                        closeAnyOpenParagraph()
                        writerObject.writeLineOpenSelfclose( 'div', [('eID',toSwordGlobals['idStack'].pop()), ('type',"introduction")] )
                        haveOpenIntro = False
                    writerObject.writeLineOpen( 'div', [getSID(), ('type',"introduction")] )
                    if text: writerObject.writeLineOpenClose( 'title', checkSwordText(text), ('level',marker[-1]) ) # Introduction heading
                    else:
                        logger.error( _("toSwordModule: {} Have a blank {} field—ignoring it").format( toSwordGlobals['verseRef'], marker ) )
                    haveOpenIntro = True
                    chapterRef = bookRef + '.0' # Not used by Sword
                    toSwordGlobals['verseRef'] = chapterRef + '.0' # Not used by Sword
                elif marker=='ip':
                    if not haveOpenIntro: # Shouldn't happen but we'll try our best
                        logger.error( "toSwordModule: {} Have an ip not in an introduction section—opening an intro section".format( toSwordGlobals['verseRef'] ) )
                        writerObject.writeLineOpen( 'div', ('type',"introduction") )
                        haveOpenIntro = True
                    closeAnyOpenParagraph()
                    writerObject.writeLineOpenSelfclose( 'div', [getSID(), ('type',"paragraph")] )
                    writerObject.writeLineText( checkSwordText(text), noTextCheck=True ) # Sometimes there's text
                    haveOpenParagraph = True
                elif marker=='iot':
                    if not haveOpenIntro: # Shouldn't happen but we'll try our best
                        logger.error( "toSwordModule: {} Have a iot not in an introduction section—opening an intro section".format( toSwordGlobals['verseRef'] ) )
                        writerObject.writeLineOpen( 'div', ('type',"introduction") )
                        haveOpenIntro = True
                    if haveOpenOutline:
                        writerObject.writeLineClose( 'list' )
                        writerObject.writeLineOpenSelfclose( 'div', [('eID',toSwordGlobals['idStack'].pop()), ('type',"outline")] )
                        haveOpenOutline = False
                    if haveOpenSection:
                        logger.error( "toSwordModule: {} Not handled yet iot".format( toSwordGlobals['verseRef'] ) )
                    closeAnyOpenParagraph()
                    writerObject.writeLineOpenSelfclose( 'div', [getSID(), ('type',"outline")] )
                    if text: writerObject.writeLineOpenClose( 'title', checkSwordText(text) )
                    writerObject.writeLineOpen( 'list' )
                    haveOpenOutline = True
                elif marker in ('io1','io2','io3','io4',):
                    #if haveOpenIntro:
                    #    closeAnyOpenParagraph()
                    #    writerObject.writeLineOpenSelfclose( 'div', [('eID',toSwordGlobals['idStack'].pop()), ('type',"introduction")] )
                    #    haveOpenIntro = False
                    if not haveOpenIntro: # Shouldn't happen but we'll try our best
                        logger.error( "toSwordModule: {} Have an {} not in an introduction section—opening an intro section".format( toSwordGlobals['verseRef'], marker ) )
                        writerObject.writeLineOpen( 'div', ('type',"introduction") )
                        haveOpenIntro = True
                    if not haveOpenOutline: # Shouldn't happen but we'll try our best
                        logger.warning( _("toSwordModule: {} Have an {} not in an outline section—opening an outline section".format( toSwordGlobals['verseRef'], marker ) ) )
                        closeAnyOpenParagraph()
                        writerObject.writeLineOpenSelfclose( 'div', [getSID(), ('type',"outline")] )
                        writerObject.writeLineOpen( 'list' )
                        haveOpenOutline = True
                    if text: writerObject.writeLineOpenClose( 'item', checkSwordText(text), noTextCheck='\\' in text )

                elif marker=='c':
                    if haveOpenOutline:
                        if text!='1' and not text.startswith('1 '):
                            logger.error( _("toSwordModule: {} This should normally be chapter 1 to close the introduction (got {!r})").format( toSwordGlobals['verseRef'], text ) )
                        writerObject.writeLineClose( 'list' )
                        writerObject.writeLineOpenSelfclose( 'div', [('eID',toSwordGlobals['idStack'].pop()), ('type',"outline")] )
                        haveOpenOutline = False
                    if haveOpenIntro:
                        if text!='1' and not text.startswith('1 '):
                            logger.error( _("toSwordModule: {} This should normally be chapter 1 to close the introduction (got {!r})").format( toSwordGlobals['verseRef'], text ) )
                        closeAnyOpenParagraph()
                        writerObject.writeLineOpenSelfclose( 'div', [('eID',toSwordGlobals['idStack'].pop()), ('type',"introduction")] )
                        haveOpenIntro = False
                    closeAnyOpenLG()
                    if needChapterEID:
                        writerObject.writeLineOpenSelfclose( 'chapter', ('eID',chapterRef) ) # This is an end milestone marker
                    writeIndexEntry( writerObject, ix )
                    C, V = text, '0'
                    currentChapterNumberString, verseNumberString = text, '0'
                    if not currentChapterNumberString.isdigit():
                        logger.critical( _("toSwordModule: Can't handle non-digit {!r} chapter number yet").format(text) )
                    chapterRef = bookRef + '.' + checkSwordText(currentChapterNumberString)
                    writerObject.writeLineOpenSelfclose( 'chapter', [('osisID',chapterRef), ('sID',chapterRef)] ) # This is a milestone marker
                    needChapterEID = True
                    writeIndexEntry( writerObject, ix )
                elif marker == 'c#': # Chapter number added for printing
                    ignoredMarkers.add( marker ) # Just ignore it completely
                elif marker == 'vp#': # This precedes a v field and has the verse number to be printed
                    gotVP = text # Just remember it for now
                elif marker=='v':
                    if gotVP: # this is the verse number to be published
                        text = gotVP
                        gotVP = None
                    #if not chapterNumberString: # Some single chapter books don't have an explicit c marker
                    #    if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert BBB in BibleOrgSysGlobals.loadedBibleBooksCodes.getSingleChapterBooksList()
                    verseNumberString = text
                    if not haveOpenL: closeAnyOpenLG()
                    V = text
                    writeVerseStart( writerObject, BBB, chapterRef, verseNumberString )
                    #closeAnyOpenL()

                elif marker in ('ms1','ms2','ms3','ms4',):
                    if haveOpenParagraph:
                        closeAnyOpenLG()
                        closeAnyOpenParagraph()
                    closeAnyOpenSubsection()
                    closeAnyOpenSection()
                    closeAnyOpenMajorSection()
                    writerObject.writeLineOpen( 'div', ('type',"majorSection") )
                    haveOpenMajorSection = True
                    if text: writerObject.writeLineOpenClose( 'title', checkSwordText(text) ) # Major section heading
                    else:
                        logger.info( _("toSwordModule: {} Blank ms1 section heading encountered").format( toSwordGlobals['verseRef'] ) )
                elif marker=='mr':
                    # Should only follow a ms1 I think
                    if haveOpenParagraph or haveOpenSection or not haveOpenMajorSection: logger.error( _("toSwordModule: Didn't expect major reference 'mr' marker after {}").format(toSwordGlobals['verseRef']) )
                    if text: writerObject.writeLineOpenClose( 'title', checkSwordText(text), ('type',"scope") )
                elif marker == 'd':
                    #if BibleOrgSysGlobals.debugFlag:
                        #pass
                    flag = '\\' in text or extras # Set this flag if the text already contains XML formatting
                    adjustedText = processXRefsAndFootnotes( text, extras )
                    if adjustedText:
                        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert BBB in ('PSA','PS2',)
                        writerObject.writeLineOpenClose( 'title', checkSwordText(adjustedText), [('canonical','true'),('type','psalm')], noTextCheck=flag )
                elif marker in ('s1','s2','s3','s4'):
                    if haveOpenParagraph:
                        closeAnyOpenLG()
                        closeAnyOpenParagraph()
                    closeAnyOpenSubsection()
                    closeAnyOpenSection()
                    writerObject.writeLineOpen( 'div', [getSID(), ('type',"section")] )
                    haveOpenSection = True
                    flag = False # Set this flag if the text already contains XML formatting
                    for format in ('\\nd ','\\bd ', '\\sc ', ):
                        if format in text: flag = True; break
                    if extras: flag = True
                    adjustedText = processXRefsAndFootnotes( text, extras )
                    if text: writerObject.writeLineOpenClose( 'title', checkSwordText(adjustedText), noTextCheck=flag ) # Section heading
                elif marker=='r':
                    # Should only follow a s1 I think
                    if haveOpenParagraph or not haveOpenSection: logger.error( _("toSwordModule: Didn't expect reference 'r' marker after {}").format(toSwordGlobals['verseRef']) )
                    if text: writerObject.writeLineOpenClose( 'title', checkSwordText(text), ('type',"parallel") ) # Section cross-reference
                elif marker=='sr':
                    # Should only follow a s1 I think
                    if haveOpenParagraph or not haveOpenSection: logger.error( _("toSwordModule: Didn't expect reference 'sr' marker after {}").format(toSwordGlobals['verseRef']) )
                    if text:
                        writerObject.writeLineOpen( 'title', ('type','scope') )
                        writerObject.writeLineOpenClose( 'reference', checkSwordText(text) )
                        writerObject.writeLineClose( 'title' )
                elif marker == 'sp':
                    if text: writerObject.writeLineOpenClose( 'speaker', checkSwordText(text) )
                elif marker=='p':
                    closeAnyOpenLG()
                    closeAnyOpenParagraph()
                    if not haveOpenSection:
                        writerObject.writeLineOpenSelfclose( 'div', [getSID(), ('type',"section")] )
                        haveOpenSection = True
                    adjustedText = processXRefsAndFootnotes( text, extras )
                    writerObject.writeLineOpenSelfclose( 'div', [getSID(), ('type',"paragraph")] )
                    writerObject.writeLineText( checkSwordText(adjustedText), noTextCheck=True ) # Sometimes there's text
                    haveOpenParagraph = True
                elif marker in ('li1','li2','li3','li4', 'ili1','ili2','ili3','ili4',):
                    if not haveOpenList:
                        writerObject.writeLineOpen( 'list' )
                        haveOpenList = True
                    adjustedText = processXRefsAndFootnotes( text, extras )
                    writerObject.writeLineOpenClose( 'item', checkSwordText(adjustedText), ('type','x-indent-'+marker[-1]), noTextCheck=True )
                elif marker in ('v~','p~',):
                    #if not haveOpenL: closeAnyOpenLG()
                    #writeVerseStart( writerObject, ix, BBB, chapterRef, text )
                    adjText = processXRefsAndFootnotes( text, extras )
                    writerObject.writeLineText( checkSwordText(adjText), noTextCheck=True )
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
                        writerObject.writeLineOpenClose( 'l', checkSwordText(adjustedText), ('level',qLevel), noTextCheck=True )
                    else: # No text — this q1 applies to the next marker
                        writerObject.writeLineOpen( 'l', ('level',qLevel) )
                        haveOpenL = True
                elif marker=='m': # Margin/Flush-left paragraph
                    closeAnyOpenL()
                    closeAnyOpenLG()
                    if text: writerObject.writeLineText( checkSwordText(text) )
                elif marker in ('b','ib'): # Blank line
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not text and not extras
                    # Doesn't seem that OSIS has a way to encode this presentation element
                    writerObject.writeNewLine() # We'll do this for now
                elif marker=='nb': # No-break
                    #print( 'nb', BBB, C, V ); halt
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not text and not extras
                    ignoredMarkers.add( marker )
                else:
                    if text:
                        logger.critical( "toSwordModule: {} lost text in {} field in {} {}:{} {!r}".format( self.abbreviation, marker, BBB, C, V, text ) )
                        #if BibleOrgSysGlobals.debugFlag: halt
                    if extras:
                        logger.critical( "toSwordModule: {} lost extras in {} field in {} {}:{}".format( self.abbreviation, marker, BBB, C, V ) )
                        #if BibleOrgSysGlobals.debugFlag: halt
                    unhandledMarkers.add( marker )
                if extras and marker not in ('v~','p~','s1','s2','s3','s4', 'd', ): logger.critical( "toSwordModule: extras not handled for {} at {} {}:{}".format( marker, BBB, C, V ) )
                lastMarker = marker
            if haveOpenIntro or haveOpenOutline or haveOpenLG or haveOpenL or unprocessedMarker:
                logger.error( "toSwordModule: a {} {} {} {} {}".format( haveOpenIntro, haveOpenOutline, haveOpenLG, haveOpenL, unprocessedMarker ) )
                logger.error( "toSwordModule: b {} {}:{}".format( BBB, currentChapterNumberString, verseNumberString ) )
                logger.error( "toSwordModule: c {} = {!r}".format( marker, text ) )
                logger.error( "toSwordModule: d These shouldn't be open here" )
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
        if BibleOrgSysGlobals.verbosityLevel > 2: print( _("  Exporting to Sword modified-OSIS XML format…") )
        xwOT = MLWriter( 'ot', lgFolder )
        xwNT = MLWriter( 'nt', lgFolder )
        xwOT.setHumanReadable( 'NLSpace', indentSize=5 ) # Can be set to 'All', 'Header', or 'None'
        xwNT.setHumanReadable( 'NLSpace', indentSize=5 ) # Can be set to 'All', 'Header', or 'None'
        xwOT.start( noAutoXML=True ); xwNT.start( noAutoXML=True )
        toSwordGlobals['length'] = xwOT.writeLineOpenSelfclose( 'milestone', [('type',"x-importer"), ('subtype',"x-BibleWriter.py"), ('n',"${} $".format(PROGRAM_VERSION))] )
        toSwordGlobals['length'] = xwNT.writeLineOpenSelfclose( 'milestone', [('type',"x-importer"), ('subtype',"x-BibleWriter.py"), ('n',"${} $".format(PROGRAM_VERSION))] )
        xwOT.setSectionName( 'Main' ); xwNT.setSectionName( 'Main' )
        with open( os.path.join( lgFolder, 'ot.vss' ), 'wb' ) as ixOT, \
             open( os.path.join( lgFolder, 'nt.vss' ), 'wb' ) as ixNT:
            ixOT.write( struct.pack( "IH", 0, 0 ) ) # Write the first dummy entry
            ixNT.write( struct.pack( "IH", 0, 0 ) ) # Write the first dummy entry
            writeIndexEntry( xwOT, ixOT ) # Write the second entry pointing to the opening milestone
            writeIndexEntry( xwNT, ixNT ) # Write the second entry pointing to the opening milestone
            for BBB,bookData in self.books.items(): # Process each Bible book
                if BibleOrgSysGlobals.loadedBibleBooksCodes.isOldTestament_NR( BBB ):
                    xw = xwOT; ix = ixOT
                elif BibleOrgSysGlobals.loadedBibleBooksCodes.isNewTestament_NR( BBB ):
                    xw = xwNT; ix = ixNT
                else:
                    logger.error( _("toSwordModule: Sword module writer doesn't know how to encode {} book or appendix").format(BBB) )
                    unhandledBooks.append( BBB )
                    continue
                writeSwordBook( xw, ix, BBB, bookData )
        xwOT.close(); xwNT.close()

        if ignoredMarkers:
            logger.info( "toSwordModule: Ignored markers were {}".format( ignoredMarkers ) )
            if BibleOrgSysGlobals.verbosityLevel > 2:
                print( "  " + _("ERROR: Ignored toSwordModule markers were {}").format( ignoredMarkers ) )
        if unhandledMarkers:
            logger.error( "toSwordModule: Unhandled markers were {}".format( unhandledMarkers ) )
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print( "  " + _("ERROR: Unhandled toSwordModule markers were {}").format( unhandledMarkers ) )
        if unhandledBooks:
            logger.warning( "toSwordModule: Unhandled books were {}".format( unhandledBooks ) )
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print( "  " + _("WARNING: Unhandled toSwordModule books were {}").format( unhandledBooks ) )
        makeConfFile( modsdFolder, compressedFlag=False ) # Create the conf (settings) file
        if validationSchema:
            OTresults= xwOT.validate( validationSchema ) # Returns a 3-tuple: intCode, logString, errorLogString
            NTresults= xwNT.validate( validationSchema ) # Returns a 3-tuple: intCode, logString, errorLogString
            return OTresults and NTresults
        if BibleOrgSysGlobals.verbosityLevel > 0 and BibleOrgSysGlobals.maxProcesses > 1:
            print( "  BibleWriter.toSwordModule finished successfully." )
        return True
    #end of BibleWriter.toSwordModule



    def totheWord( self, outputFolderpath:Optional[Path]=None, controlDict=None ):
        """
        Using settings from the given control file,
            converts the USFM information to a UTF-8 theWord file.

        This format is roughly documented at http://www.theword.net/index.php?article.tools&l=english
        """
        from BibleOrgSys.Formats.theWordBible import createTheWordModule

        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Running BibleWriter:totheWord…" )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert self.books

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolderpath: outputFolderpath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_theWord_' + ('Reexport/' if self.objectTypeString=="theWord" else 'Export/') )
        if not os.access( outputFolderpath, os.F_OK ): os.makedirs( outputFolderpath ) # Make the empty folder if there wasn't already one there
        # ControlDict is not used (yet)
        if not controlDict:
            controlDict, defaultControlFilename = {}, "To_theWord_controls.txt"
            try: ControlFiles.readControlFile( defaultControlFolderpath, defaultControlFilename, controlDict )
            except FileNotFoundError:
                pass
                #logger.critical( "Unable to read control dict {} from {}".format( defaultControlFilename, defaultControlFolderpath ) )
        #self.__adjustControlDict( controlDict )

        return createTheWordModule( self, outputFolderpath, controlDict )
    # end of BibleWriter.totheWord



    def toMySword( self, outputFolderpath:Optional[Path]=None, controlDict=None ):
        """
        Using settings from the given control file,
            converts the USFM information to a UTF-8 MySword file.

        This format is roughly documented at http://www.theword.net/index.php?article.tools&l=english
        """
        from BibleOrgSys.Formats.MySwordBible import createMySwordModule

        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Running BibleWriter:toMySword…" )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert self.books

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolderpath: outputFolderpath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_MySword_' + ('Reexport/' if self.objectTypeString=="MySword" else 'Export/') )
        if not os.access( outputFolderpath, os.F_OK ): os.makedirs( outputFolderpath ) # Make the empty folder if there wasn't already one there
        # ControlDict is not used (yet)
        if not controlDict:
            controlDict, defaultControlFilename = {}, "To_MySword_controls.txt"
            try: ControlFiles.readControlFile( defaultControlFolderpath, defaultControlFilename, controlDict )
            except FileNotFoundError:
                pass
                #logger.critical( "Unable to read control dict {} from {}".format( defaultControlFilename, defaultControlFolderpath ) )
        #self.__adjustControlDict( controlDict )

        return createMySwordModule( self, outputFolderpath, controlDict )
    # end of BibleWriter.toMySword



    def toESword( self, outputFolderpath:Optional[Path]=None, controlDict=None ):
        """
        Using settings from the given control file,
            converts the USFM information to a UTF-8 e-Sword file.

        This format is roughly documented at xxx
        """
        from BibleOrgSys.Formats.ESwordBible import createESwordBibleModule

        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Running BibleWriter:toESword…" )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert self.books

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolderpath: outputFolderpath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_e-Sword_' + ('Reexport/' if self.objectTypeString=="e-Sword" else 'Export/') )
        if not os.access( outputFolderpath, os.F_OK ): os.makedirs( outputFolderpath ) # Make the empty folder if there wasn't already one there
        # ControlDict is not used (yet)
        if not controlDict:
            controlDict, defaultControlFilename = {}, "To_e-Sword_controls.txt"
            try: ControlFiles.readControlFile( defaultControlFolderpath, defaultControlFilename, controlDict )
            except FileNotFoundError:
                pass
                #logger.critical( "Unable to read control dict {} from {}".format( defaultControlFilename, defaultControlFolderpath ) )
        #self.__adjustControlDict( controlDict )

        return createESwordBibleModule( self, outputFolderpath, controlDict )
    # end of BibleWriter.toESword



    def toMyBible( self, outputFolderpath:Optional[Path]=None, controlDict=None ):
        """
        Using settings from the given control file,
            converts the internal Bible information to a UTF-8 MyBible SQLite3 database file
            for the MyBible Android app.

        This format is roughly documented at http://mybible.zone/creat-eng.php
        """
        from BibleOrgSys.Formats.MyBibleBible import createMyBibleModule

        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Running BibleWriter:toMyBible…" )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert self.books

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolderpath: outputFolderpath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_MyBible_' + ('Reexport/' if self.objectTypeString=="MyBible" else 'Export/') )
        if not os.access( outputFolderpath, os.F_OK ): os.makedirs( outputFolderpath ) # Make the empty folder if there wasn't already one there
        # ControlDict is not used (yet)
        if not controlDict:
            controlDict, defaultControlFilename = {}, "To_MyBible_controls.txt"
            try: ControlFiles.readControlFile( defaultControlFolderpath, defaultControlFilename, controlDict )
            except FileNotFoundError:
                pass
                #logger.critical( "Unable to read control dict {} from {}".format( defaultControlFilename, defaultControlFolderpath ) )
        #self.__adjustControlDict( controlDict )

        return createMyBibleModule( self, outputFolderpath, controlDict )
    # end of BibleWriter.toMyBible



    def toSwordSearcher( self, outputFolderpath:Optional[Path]=None ):
        """
        Write the pseudo USFM out into the SwordSearcher pre-Forge format.
        """
        ssBookAbbrevDict = { 'GEN':'Ge', 'EXO':'Ex', 'LEV':'Le', 'NUM':'Nu', 'DEU':'De', 'JOS':'Jos', 'JDG':'Jg',
                            'RUT':'Ru', 'SA1':'1Sa', 'SA2':'2Sa', 'KI1':'1Ki', 'KI2':'2Ki', 'CH1':'1Ch', 'CH2':'2Ch',
                            'EZR':'Ezr', 'NEH':'Ne', 'EST':'Es', 'JOB':'Job', 'PSA':'Ps', 'PRO':'Pr', 'ECC':'Ec',
                            'SNG':'Song', 'ISA':'Isa', 'JER':'Jer', 'LAM':'La', 'EZE':'Eze', 'DAN':'Da', 'HOS':'Ho',
                            'JOL':'Joe', 'AMO':'Am', 'OBA':'Ob', 'JNA':'Jon', 'MIC':'Mic', 'NAH':'Na', 'HAB':'Hab',
                            'ZEP':'Zep', 'HAG':'Hag', 'ZEC':'Zec', 'MAL':'Mal',
                            'MAT':'Mt', 'MRK':'Mr', 'LUK':'Lu', 'JHN':'Joh', 'ACT':'Ac', 'ROM':'Ro',
                            'CO1':'1Co', 'CO2':'2Co', 'GAL':'Ga', 'EPH':'Eph', 'PHP':'Php', 'COL':'Col',
                            'TH1':'1Th', 'TH2':'2Th', 'TI1':'1Ti', 'TI2':'2Ti', 'TIT':'Tit', 'PHM':'Phm',
                            'HEB':'Heb', 'JAM':'Jas', 'PE1':'1Pe', 'PE2':'2Pe',
                            'JN1':'1Jo', 'JN2':'2Jo', 'JN3':'3Jo', 'JDE':'Jude', 'REV':'Re' }
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Running BibleWriter:toSwordSearcher…" )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert self.books

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolderpath: outputFolderpath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_SwordSearcher_Export/' )
        if not os.access( outputFolderpath, os.F_OK ): os.makedirs( outputFolderpath ) # Make the empty folder if there wasn't already one there

        ignoredMarkers, unhandledMarkers, unhandledBooks = set(), set(), []


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
            except KeyError:
                logger.warning( "toSwordSearcher: don't know how to encode book: {}".format( BBB ) )
                unhandledBooks.append( BBB )
                return

            internalBibleBookData = bookObject._processedLines
            started, gotVP, accumulator = False, None, "" # Started flag ignores fields in the book introduction
            C, V = '-1', '-1' # So first/id line starts at -1:0
            for entry in internalBibleBookData:
                marker, text = entry.getMarker(), entry.getCleanText()
                if '¬' in marker or marker in BOS_ADDED_NESTING_MARKERS or marker=='v=':
                    continue # Just ignore added markers — not needed here
                if marker in USFM_PRECHAPTER_MARKERS:
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
                        assert C=='-1' or marker=='rem' or marker.startswith('mte')
                    V = str( int(V) + 1 )

                if marker in OFTEN_IGNORED_USFM_HEADER_MARKERS or marker in ('ie',): # Just ignore these lines
                    ignoredMarkers.add( marker )
                elif marker == 'c': C, V = text, '0'
                elif marker in ('c#',):
                    ignoredMarkers.add( marker )
                elif marker == 'vp#': # This precedes a v field and has the verse number to be printed
                    gotVP = text # Just remember it for now
                elif marker == 'v':
                    V = text
                    if gotVP: # this is the verse number to be published
                        text = gotVP
                        gotVP = None
                    started = True
                    if accumulator: writer.write( "{}\n".format( accumulator ) ); accumulator = ''
                    writer.write( "$$ {} {}:{}\n".format( bookCode, C, text ) )

                elif marker in ('mt1','mt2','mt3','mt4', 'mte1','mte2','mte3','mte4', 'ms1','ms2','ms3','ms4', ) \
                or marker in USFM_ALL_INTRODUCTION_MARKERS \
                or marker in ('s1','s2','s3','s4', 'r','sr','mr', 'd','sp','cd', 'cl','lit', ):
                    ignoredMarkers.add( marker )
                elif marker in USFM_BIBLE_PARAGRAPH_MARKERS:
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not text
                    ignoredMarkers.add( marker )
                elif marker in ('b', 'nb', 'ib', ):
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not text
                    ignoredMarkers.add( marker )
                elif marker in ('v~', 'p~',):
                    if started: accumulator += (' ' if accumulator else '') + text
                else:
                    if text:
                        logger.error( "toSwordSearcher: {} lost text in {} field in {} {}:{} {!r}".format( self.abbreviation, marker, BBB, C, V, text ) )
                        #if BibleOrgSysGlobals.debugFlag: halt
                    unhandledMarkers.add( marker )
                #if extras and marker not in ('v~','p~',): logger.critical( "toSwordSearcher: extras not handled for {} at {} {}:{}".format( marker, BBB, C, V ) )
            if accumulator: writer.write( "{}\n".format( accumulator ) )
        # end of toSwordSearcher:writeSSBook


        if BibleOrgSysGlobals.verbosityLevel > 2: print( _("  Exporting to SwordSearcher format…") )
        filename = 'Bible.txt'
        filepath = os.path.join( outputFolderpath, BibleOrgSysGlobals.makeSafeFilename( filename ) )
        if BibleOrgSysGlobals.verbosityLevel > 2: print( '  toSwordSearcher: ' + _("Writing {!r}…").format( filepath ) )
        with open( filepath, 'wt', encoding='utf-8' ) as myFile:
            try: myFile.write('\ufeff') # Forge for SwordSearcher needs the BOM
            except UnicodeEncodeError: # why does this fail on Windows???
                logger.critical( "toForgeForSwordSearcher: Unable to write BOM to file" )
            writeSSHeader( myFile )
            for BBB,bookObject in self.books.items():
                if BibleOrgSysGlobals.debugFlag: writeSSBook( myFile, BBB, bookObject ) # Halts on errors
                else:
                    try: writeSSBook( myFile, BBB, bookObject )
                    except IOError: logger.critical( "BibleWriter.toSwordSearcher: Unable to output {}".format( BBB ) )

        if ignoredMarkers:
            logger.info( "toSwordSearcher: Ignored markers were {}".format( ignoredMarkers ) )
            if BibleOrgSysGlobals.verbosityLevel > 2:
                print( "  " + _("WARNING: Ignored toSwordSearcher markers were {}").format( ignoredMarkers ) )
        if unhandledMarkers:
            logger.warning( "toSwordSearcher: Unhandled markers were {}".format( unhandledMarkers ) )
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print( "  " + _("WARNING: Unhandled toSwordSearcher markers were {}").format( unhandledMarkers ) )
        if unhandledBooks:
            logger.warning( "toSwordSearcher: Unhandled books were {}".format( unhandledBooks ) )
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print( "  " + _("WARNING: Unhandled toSwordSearcher books were {}").format( unhandledBooks ) )

        # Now create a zipped version
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Zipping {} SwordSearcher file…".format( filename ) )
        zf = zipfile.ZipFile( filepath+'.zip', 'w', compression=zipfile.ZIP_DEFLATED )
        zf.write( filepath )
        zf.close()

        if BibleOrgSysGlobals.verbosityLevel > 0 and BibleOrgSysGlobals.maxProcesses > 1:
            print( "  BibleWriter.toSwordSearcher finished successfully." )
        return True
    # end of BibleWriter.toSwordSearcher



    def toDrupalBible( self, outputFolderpath:Optional[Path]=None ):
        """
        Write the pseudo USFM out into the DrupalBible format.
        """
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Running BibleWriter:toDrupalBible…" )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert self.books

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolderpath: outputFolderpath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_DrupalBible_' + ('Reexport/' if self.objectTypeString=="DrupalBible" else 'Export/') )
        if not os.access( outputFolderpath, os.F_OK ): os.makedirs( outputFolderpath ) # Make the empty folder if there wasn't already one there

        ignoredMarkers, unhandledMarkers, unhandledBooks = set(), set(), []

        #print( 'status' in self ) # False
        #print( 'status' in self.__dict__ ) # True
        #print( '\nself', dir(self) )
        #print( '\nsettings', dir(self.settingsDict) )


        def writeDrupalBibleHeader( writer ):
            """
            Write the header data
            """
            #writer.write( "\ufeff*Bible\n#shortname fullname language\n" ) # Starts with BOM
            writer.write( "*Bible\n#shortname fullname language\n" ) # No BOM
            shortName = self.shortName if self.shortName else self.name
            if shortName is None \
            or self.abbreviation and len(shortName)>5:
                shortName = self.abbreviation
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
                try: bookCode = BibleOrgSysGlobals.loadedBibleBooksCodes.getDrupalBibleAbbreviation( BBB ).upper()
                except AttributeError: # Don't know how to encode this book
                    logger.warning( "toDrupalBible: ignoring book: {}".format( BBB ) )
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
            #textField = re.sub( r'(\\[a-z][a-z0-9]{0,3} )', '', textField ) # Remove any remaining character fields, e.g., '\tcr1 '
            #textField = re.sub( r'(\\[a-z][a-z0-9]{0,3}\*)', '', textField ) # Remove any remaining character end fields, e.g., '\tcr1*'
            #textField = re.sub( r'(\\\+?[a-z][a-z0-9]{0,3} )', '', textField ) # Remove any remaining character fields, e.g., '\+add '
            textField = re.sub( r'(\\\+?[a-z][a-z0-9]{0,3}[ \*])', '', textField ) # Remove any remaining character end fields, e.g., '\+add*'
            if '\\' in textField: # Catch any left-overs
                if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
                    print( "toDrupalBible.doDrupalTextFormat: unprocessed code in {!r} from {!r}".format( textField, givenTextField ) )
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
            return textField
        # end of doDrupalTextFormat


        def writeDrupalBibleBook( writer, BBB, bookObject ):
            """
            Convert the internal Bible data to DrupalBible output.
            """
            try: bookCode = BibleOrgSysGlobals.loadedBibleBooksCodes.getDrupalBibleAbbreviation( BBB ).upper()
            except AttributeError:
                logger.warning( "writeDrupalBibleBook: " + _("don't know how to encode {} — ignored").format( BBB ) )
                unhandledBooks.append( BBB )
                return
            started, gotVP, accumulator = False, None, "" # Started flag ignores fields in the book introduction
            linemark = ''
            C, V = '-1', '-1' # So first/id line starts at -1:0
            for entry in bookObject._processedLines:
                marker, text = entry.getMarker(), entry.getAdjustedText()
                if '¬' in marker or marker in BOS_ADDED_NESTING_MARKERS or marker=='v=':
                    continue # Just ignore added markers — not needed here
                if marker in USFM_PRECHAPTER_MARKERS:
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
                        assert C=='-1' or marker=='rem' or marker.startswith('mte')
                    V = str( int(V) + 1 )

                if marker in OFTEN_IGNORED_USFM_HEADER_MARKERS or marker in ('ie',): # Just ignore these lines
                    ignoredMarkers.add( marker )
                elif marker == 'c':
                    if accumulator:
                        writer.write( "{}|{}|{}|{}|{}\n".format( bookCode, C, V, linemark, doDrupalTextFormat( accumulator ) ) )
                        accumulator, linemark = '', ''
                    C, V = text, '0'
                elif marker in ( 'c#', ): # Just ignore these unneeded fields
                    ignoredMarkers.add( marker )
                elif marker == 'vp#': # This precedes a v field and has the verse number to be printed
                    gotVP = text # Just remember it for now
                elif marker == 'v':
                    started = True
                    if accumulator:
                        writer.write( "{}|{}|{}|{}|{}\n".format( bookCode, C, V, linemark, doDrupalTextFormat( accumulator ) ) )
                        accumulator, linemark = '', ''
                    V = text
                    if gotVP: # this is the verse number to be published
                        V = gotVP
                        gotVP = None
                    if not V.isdigit(): # Remove verse bridges
                        #print( "toDrupalBible V was", repr(V) )
                        Vcopy, V = V, ''
                        for char in Vcopy:
                            if not char.isdigit(): break
                            V += char
                        #print( "toDrupalBible V is now", repr(V) )

                elif marker in ('mt1','mt2','mt3','mt4', 'mte1','mte2','mte3','mte4', 'ms1','ms2','ms3','ms4', ) \
                or marker in USFM_ALL_INTRODUCTION_MARKERS \
                or marker in ('s1','s2','s3','s4', 'r','sr','mr', 'd','sp','cd', 'cl','lit', ):
                    ignoredMarkers.add( marker )
                elif marker in USFM_BIBLE_PARAGRAPH_MARKERS:
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not text
                    ignoredMarkers.add( marker )
                elif marker in ('b', 'nb', 'ib', ):
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not text
                    ignoredMarkers.add( marker )
                elif marker in ('v~', 'p~', 'tr',):
                    if started: accumulator += (' ' if accumulator else '') + text
                else:
                    if text:
                        logger.warning( "toDrupalBible: {} lost text in {} field in {} {}:{} {!r}".format( self.abbreviation, marker, BBB, C, V, text ) )
                        #if BibleOrgSysGlobals.debugFlag: halt
                    unhandledMarkers.add( marker )
                #if extras and marker not in ('v~','p~',): logger.critical( "toDrupalBible: extras not handled for {} at {} {}:{}".format( marker, BBB, C, V ) )
            if accumulator: writer.write( "{}|{}|{}|{}|{}\n".format( bookCode, C, V, linemark, doDrupalTextFormat( accumulator ) ) )
        # end of toDrupalBible:writeDrupalBibleBook


        if BibleOrgSysGlobals.verbosityLevel > 2: print( _("  Exporting to DrupalBible format…") )
        filename = "Bible.txt"
        filepath = os.path.join( outputFolderpath, BibleOrgSysGlobals.makeSafeFilename( filename ) )
        if BibleOrgSysGlobals.verbosityLevel > 2: print( '  toDrupalBible: ' + _("Writing {!r}…").format( filepath ) )
        with open( filepath, 'wt', encoding='utf-8' ) as myFile:
            writeDrupalBibleHeader( myFile )
            writeDrupalBibleChapters( myFile )
            for BBB,bookObject in self.books.items():
                if BibleOrgSysGlobals.debugFlag: writeDrupalBibleBook( myFile, BBB, bookObject ) # halts on errors
                else:
                    writeDrupalBibleBook( myFile, BBB, bookObject )
                    #except: logger.critical( "BibleWriter.toDrupalBible: Unable to output {}".format( BBB ) )

        if ignoredMarkers:
            logger.info( "toDrupalBible: Ignored markers were {}".format( ignoredMarkers ) )
            if BibleOrgSysGlobals.verbosityLevel > 2:
                print( "  " + _("WARNING: Ignored toDrupalBible markers were {}").format( ignoredMarkers ) )
        if unhandledMarkers:
            logger.warning( "toDrupalBible: Unhandled markers were {}".format( unhandledMarkers ) )
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print( "  " + _("WARNING: Unhandled toDrupalBible markers were {}").format( unhandledMarkers ) )
        if unhandledBooks:
            logger.warning( "toDrupalBible: Unhandled books were {}".format( unhandledBooks ) )
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print( "  " + _("WARNING: Unhandled toDrupalBible books were {}").format( unhandledBooks ) )

        # Now create a zipped version
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Zipping {} DrupalBible file…".format( filename ) )
        zf = zipfile.ZipFile( filepath+'.zip', 'w', compression=zipfile.ZIP_DEFLATED )
        zf.write( filepath )
        zf.close()

        if BibleOrgSysGlobals.verbosityLevel > 0 and BibleOrgSysGlobals.maxProcesses > 1:
            print( "  BibleWriter.toDrupalBible finished successfully." )
        return True
    # end of BibleWriter.toDrupalBible



    def toPhotoBible( self, outputFolderpath:Optional[Path]=None ):
        """
        Write the internal Bible format out into small JPEG (photo) files
            that can be downloaded into a cheap (non-Java) camera phone.
        The folders have to be numbered to also sort in a sensible order and be easily navigable.

        The current format is 320x240 pixels.
            I need to see a page showing 26-32 characters per line and 13-14 lines per page

        Although this code could be made to handle different fonts,
            ImageMagick convert is unable to handle complex scripts.  :(
        """
        import unicodedata
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Running BibleWriter:toPhotoBible… {}".format( datetime.now().strftime('%H:%M') ) )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert self.books

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolderpath: outputFolderpath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_PhotoBible_Export/' )
        if not os.access( outputFolderpath, os.F_OK ): os.makedirs( outputFolderpath ) # Make the empty folder if there wasn't already one there

        ignoredMarkers, unhandledMarkers = set(), set()

        # First determine our frame and line sizes
        pixelWidth, pixelHeight = 240, 320
        pixelWidthManualSetting = self.getSetting( 'PBPixelWidth' )
        if pixelWidthManualSetting: pixelWidth = int( pixelWidthManualSetting )
        pixelHeightManualSetting = self.getSetting( 'PBPixelHeight' )
        if pixelHeightManualSetting: pixelWidth = int( pixelHeightManualSetting )
        assert 240 <= pixelWidth <= 1080
        assert 320 <= pixelHeight <= 1920
        #blankFilepath = os.path.join( defaultControlFolderpath, "blank-240x320.jpg" )
        # Used: convert -fill khaki1 -draw 'rectangle 0,0 240,24' blank-240x320.jpg.jpg yblank-240x320.jpg
        #       Available colors are at http://www.imagemagick.org/script/color.php
        if (pixelWidth, pixelHeight) == (240, 320):
            blankFilepath = os.path.join( defaultControlFolderpath, "yblank-240x320.jpg" )
        else:
            logger.critical( "toPhotoBible needs a blank jpg file for {}x{} image".format( pixelWidth, pixelHeight ) )
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
            return False
        leftPadding = 1
        defaultFontSize, defaultLeadingRatio = 20, 1.2
        defaultLineSize = int( defaultLeadingRatio * defaultFontSize )
        maxLineCharacters, maxLines = 23, 12 # Reduced from 26 to 23 for SIL fonts
        maxLineCharactersManualSetting = self.getSetting( 'PBMaxChars' )
        if maxLineCharactersManualSetting: maxLineCharacters = int( maxLineCharactersManualSetting )
        maxLinesManualSetting = self.getSetting( 'PBMaxLines' )
        if maxLinesManualSetting: maxLines = int( maxLinesManualSetting )
        assert 20 <= maxLineCharacters <= 40
        assert 10 <= maxLines <= 20
        maxBooknameLetters = 12 # For the header line — the chapter number is appended to this
        maxDown = pixelHeight-1 - defaultLineSize - 3 # Be sure to leave one blank line at the bottom
        if BibleOrgSysGlobals.verbosityLevel > 2:
            print( "toPhotoBible -> {}x{} pixel JPEG frames".format( pixelWidth, pixelHeight ) )
            print( "  {} chars per line with {} fontsize and {} pixel(s) left padding".format( maxLineCharacters, defaultFontSize, leftPadding ) )
            print( "  {} lines with {} leading -> {} pixels".format( maxLines, defaultLeadingRatio, defaultLineSize ) )

        # Now determine our fonts
        # Use "identify -list font" or "convert -list font" to see all fonts on the system (use the Font field, not the family field)
        # We need to choose fonts that can handle special characters well
        #if sys.platform.startswith( 'win' ):
            #defaultTextFontname, defaultHeadingFontname = "Times-New-Roman", "Liberation-Sans-Bold"
        #else:
            #defaultTextFontname, defaultHeadingFontname = "Times-New-Roman-Regular", "FreeSans-Bold"
        defaultTextFontname = self.getSetting( 'PBTextFont' )
        if not defaultTextFontname: defaultTextFontname = 'Charis-SIL'
        defaultHeadingFontname = self.getSetting( 'PBHeadingFont' )
        if not defaultHeadingFontname: defaultHeadingFontname = 'Andika'

        topLineColor = 'opaque'
        defaultMainHeadingFontcolor, defaultSectionHeadingFontcolor, defaultSectionCrossReferenceFontcolor = 'indigo', 'red1', 'royalBlue'
        #defaultVerseNumberFontcolor = 'DarkOrange1'
        namingFormat = 'Short' # 'Short' or 'Long' — affects folder and filenames
        colorVerseNumbersFlag = False
        #digitSpace = chr(8199) # '\u2007'
        verseDigitSubstitutions = { '0':'⁰', '1':'¹', '2':'²', '3':'³', '4':'⁴', '5':'⁵', '6':'⁶', '7':'⁷', '8':'⁸', '9':'⁹', }


        def renderCommands( commandList, jpegFilepath ):
            """
            Given a list of commands, apply them to the existing JPEG file.

            Returns an errorcode.
            """
            #print( "renderCommands: {} on {}".format( commandList, jpegFilepath ) )

            # Run the script on our data
            if sys.platform.startswith( 'win' ): parameters = [ 'imconvert.exe' ]
            else: parameters = ['/usr/bin/timeout', '10s', '/usr/bin/convert' ]
            parameters.extend( commandList )
            parameters.append( jpegFilepath ) # input file
            parameters.append( jpegFilepath ) # output file
            #print( "Parameters", repr(parameters) )
            myProcess = subprocess.Popen( parameters, stdout=subprocess.PIPE, stderr=subprocess.PIPE )
            programOutputBytes, programErrorOutputBytes = myProcess.communicate()
            returnCode = myProcess.returncode

            # Process the output
            if programOutputBytes:
                programOutputString = programOutputBytes.decode( encoding='utf-8', errors='replace' )
                logger.critical( "renderCommands: " + programOutputString )
                #with open( os.path.join( outputFolderpath, 'UncompressedScriptOutput.txt" ), 'wt', encoding='utf-8' ) as myFile: myFile.write( programOutputString )
            if programErrorOutputBytes:
                programErrorOutputString = programErrorOutputBytes.decode( encoding='utf-8', errors='replace' )
                logger.critical( "renderE: " + programErrorOutputString )
                #with open( os.path.join( outputFolderpath, 'UncompressedScriptErrorOutput.txt" ), 'wt', encoding='utf-8' ) as myFile: myFile.write( programErrorOutputString )

            return returnCode
        # end of toPhotoBible.renderCommands


        lastFontcolor = lastFontsize = lastFontname = None # We keep track of these to avoid unnecessary duplicates
        def renderLine( across, down, text, fontsize, fontname, fontcolor ):
            """
            Returns a list of commands to render the given text in a line.
            Tries to avoid including superfluous font and other commands.

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
            commands.append( 'text {},{} {!r}'.format( across, down, text ) )
            return commands
        # end of toPhotoBible.renderLine


        #def renderVerseNumbers( givenAcross, down, vnInfo, fontsize, fontname, fontcolor ):
            #"""
            #Failed experiment. A space is narrower than a digit. The Unicode digitSpace doesn't work in ImageMagick.

            #Overprint the verse numbers (in a different colour) onto a line
                #where spaces have been left in the first text pass.
            #"""
            #vnLineBuffer = ''
            #vnCommands = []
            #for posn,vn in vnInfo:
                ##print( posn, repr(vn) )
                #vnLineBuffer += ' ' * (posn - len(vnLineBuffer) ) + vn # Space is too narrow
                #print( repr(vnLineBuffer), vnInfo )

                #across = givenAcross + posn * fontsize * 3 / 10
                #vnCommands.extend( renderLine( across, down, vn, fontsize, fontname, fontcolor ) )
            #return vnCommands
        ## end of toPhotoBible.renderVerseNumbers


        def renderPage( BBB, C, bookName, text, jpegFilepath, fontsize=None ):
            """
            Creates a "blank" JPEG file
                and then writes lines across the top of the background image.

            Returns any left-over text.

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
            heading = '{}{}'.format( bookName, '' if C=='-1' else ' '+C )
            totalCommands = renderLine( across, down, heading, fontsize, defaultHeadingFontname, topLineColor )
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
                fontcolor = 'opaque' # gives black as default

                # extraLineIndent is used for indented text
                indenter, extraLineIndent = '', 0
                if '_I1_' in line: indenter, extraLineIndent = '_I1_', 1; line = line.replace( '_I1_', '', 1 )
                elif '_I2_' in line: indenter, extraLineIndent = '_I2_', 2; line = line.replace( '_I2_', '', 1 )
                elif '_I3_' in line: indenter, extraLineIndent = '_I3_', 3; line = line.replace( '_I3_', '', 1 )
                elif '_I4_' in line: indenter, extraLineIndent = '_I4_', 4; line = line.replace( '_I4_', '', 1 )
                if BibleOrgSysGlobals.debugFlag: # Should only be one
                    assert '_I1_' not in line and '_I2_' not in line and '_I3_' not in line and '_I4_' not in line

                #verseNumberList = [] # Contains a list of 2-tuples indicating where verse numbers should go

                if down >= maxDown - leading \
                or outputLineCount == maxLines - 1:
                    lastLine = True
                if down >= maxDown: break # We're finished
                #print( BBB, C, textLineCount, outputLineCount, down, maxDown, lastLine, repr(line) )

                isMainHeading = isSectionHeading = isSectionCrossReference = False
                if line.startswith('HhH'):
                    if lastLine:
                        #print( BBB, C, "Don't start main heading on last line", repr(line) )
                        break # Don't print headings on the last line
                    line = line[3:] # Remove the heading marker
                    #print( "Got main heading:", BBB, C, repr(line) )
                    isMainHeading = True
                    fontcolor = defaultMainHeadingFontcolor
                elif line.startswith('SsS'):
                    if lastLine:
                        #print( BBB, C, "Don't start section heading on last line", repr(line) )
                        break # Don't print headings on the last line
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
                #isVerseNumber = False
                words = [] # Just in case the line is blank
                if line:
                    verseNumberLast = False
                    words = line.split(' ')
                    #print( textWordCount, "words", words )
                    for w,originalWord in enumerate( words ):
                        word = originalWord.replace( ' ', ' ' ) # Put back normal spaces (now that the split has been done)

                        isVerseNumber = False
                        vix = word.find( 'VvV' )
                        if vix != -1: # This must be a verse number (perhaps preceded by some spaces)
                            isVerseNumber = True # this word is the verse number
                            word = word[:vix]+word[vix+3:]
                            for digit,newDigit in verseDigitSubstitutions.items():
                                word = word.replace( digit, newDigit )
                        #assert 'VvV' not in word

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
                        capsCount = combiningCount = 0
                        for letter in potentialString:
                            if unicodedata.combining(letter): combiningCount += 1
                            elif letter.isupper(): capsCount += 1

                        offset += (potentialStringLower.count('m') + potentialStringLower.count('w') \
                                    + potentialStringLower.count('ɖ') + potentialStringLower.count('—') + capsCount ) / 3
                        offset -= (potentialStringLower.count(' ') + potentialStringLower.count('i') \
                                    + potentialString.count('l') + potentialString.count('t') ) / 4 + combiningCount
                        #if offset != 1:
                            #print( "Adjusted offset to", offset, "from", repr(potentialString) )

                        potentialLength = len(lineBuffer) + len(word) + offset
                        if lastLine and isVerseNumber: # We would have to include the next word also
                            if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert w < len(words)-1
                            potentialLength += len(words[w+1]) + 1
                            for letter in words[w+1]:
                                if unicodedata.combining(letter): potentialLength -= 1
                            #print( "Adjusted pL for", BBB, C, repr(word), repr(words[w+1]) )
                        if potentialLength  >= maxLineCharacters:
                            # Print this line as we've already got it coz it would be too long if we added the word
                            totalCommands.extend( renderLine( across, down, lineBuffer, fontsize, defaultTextFontname, fontcolor ) )
                            #if verseNumberList:
                                #print( repr(lineBuffer) )
                                #totalCommands.extend( renderVerseNumbers( across, down, verseNumberList, fontsize, defaultTextFontname, defaultVerseNumberFontcolor ) )
                                #verseNumberList = []
                            down += leading
                            outputLineCount += 1
                            lineBuffer = ' ' * extraLineIndent # Handle indented paragraphs
                            #print( outputLineCount, maxLines, outputLineCount>=maxLines )
                            if outputLineCount >= maxLines: break
                            if down >= maxDown: break # We're finished

                        # Add the word to the line (with preceding space as necessary)
                        space = '' if verseNumberLast else ' ' # Use a narrow space after verse numbers (didn't work so use nothing)
                        lineBuffer += (space if lineBuffer.lstrip() else '')
                        #if isVerseNumber and colorVerseNumbersFlag:
                            #verseNumberList.append( (len(lineBuffer),word,) )
                            #lineBuffer += ' ' * int( 1.6 * len(word) ) # Just put spaces in for place holders for the present
                        #else: lineBuffer += word
                        lineBuffer += word
                        textWordCount += 1
                        verseNumberLast = isVerseNumber

                    # Words in this source text line are all processed
                    if lineBuffer.lstrip(): # do the last line
                        totalCommands.extend( renderLine( across, down, lineBuffer, fontsize, defaultTextFontname, fontcolor ) )
                        #if verseNumberList:
                            #print( repr(lineBuffer) )
                            #totalCommands.extend( renderVerseNumbers( across, down, verseNumberList, fontsize, defaultTextFontname, defaultVerseNumberFontcolor ) )
                            #verseNumberList = []
                        down += leading
                        outputLineCount += 1
                elif textLineCount!=1: # it's a blank line (but not the first line on the page)
                    down += defaultFontSize / 3 # Leave a blank 1/3 line
                    outputLineCount += 0.4
                #print( outputLineCount, maxLines, outputLineCount>=maxLines )
                if outputLineCount >= maxLines: break

            # Now render all those commands at once
            renderCommands( totalCommands, jpegFilepath ) # Do all the rendering at once

            # Find the left-over text
            leftoverText = ''
            #print( "textWordCount was", textWordCount, len(words) )
            #print( "textLineCount was", textLineCount, len(lines) )
            leftoverText += ' '.join( words[textWordCount:] )
            if textLineCount < len(lines):
                leftoverText += '\n' + '\n'.join( lines[textLineCount:] )


            #print( "leftoverText was", repr(leftoverText) )
            return indenter+leftoverText if leftoverText else ''
        # end of toPhotoBible.renderPage


        def renderChapterText( BBB, BBBnum, bookName, bookAbbrev, C, intC, maxChapters, numVerses, text, bookFolderName, fontsize=None ):
            """
            Creates as many JPEG image files as needed to display the chapter
                and puts them in an appropriate (created) folder.
            """
            #print( "\nrenderChapterText( {}, {}, {}, {}, {}, {}, {} )".format( BBB, C, repr(text), jpegFoldername, fontsize, fontcolor, leading ) )

            #intC = int( C )
            if namingFormat == 'Short':
                if maxChapters < 10: chapterFoldernameTemplate = '{:01}-{}/'
                elif maxChapters < 100: chapterFoldernameTemplate = '{:02}-{}/'
                else: chapterFoldernameTemplate = '{:03}-{}/'
                chapterFolderName = chapterFoldernameTemplate.format( intC, bookAbbrev )
                filenameTemplate = '{:02}.jpg' if numVerses < 80 else '{:03}.jpg' # Might go over 99 pages for the chapter
            elif namingFormat == 'Long':
                if BBBnum < 100:
                    if maxChapters < 10:
                        chapterFoldernameTemplate, filenameTemplate = '{:02}-{:01}-{}/', '{:02}-{:01}-{:02}-{}.jpg'
                    elif maxChapters < 100:
                        chapterFoldernameTemplate, filenameTemplate = '{:02}-{:02}-{}/', '{:02}-{:02}-{:02}-{}.jpg'
                    else:
                        chapterFoldernameTemplate, filenameTemplate = '{:02}-{:03}-{}/', '{:02}-{:03}-{:02}-{}.jpg'
                else: # not normally expected
                    if maxChapters < 10:
                        chapterFoldernameTemplate, filenameTemplate = '{:03}-{:01}-{}/', '{:03}-{:01}-{:02}-{}.jpg'
                    elif maxChapters < 100:
                        chapterFoldernameTemplate, filenameTemplate = '{:03}-{:02}-{}/', '{:03}-{:02}-{:02}-{}.jpg'
                    else:
                        chapterFoldernameTemplate, filenameTemplate = '{:03}-{:03}-{}/', '{:03}-{:03}-{:02}-{}.jpg'
                chapterFolderName = chapterFoldernameTemplate.format( BibleOrgSysGlobals.loadedBibleBooksCodes.getReferenceNumber( BBB ), intC, BBB )
                if numVerses > 80: filenameTemplate = filenameTemplate.replace( '{:02}-{}', '{:03}-{}' )
            else: halt

            chapterFolderPath = os.path.join( bookFolderName, chapterFolderName )
            if not os.access( chapterFolderPath, os.F_OK ): os.makedirs( chapterFolderPath ) # Make the empty folder if there wasn't already one there

            pagesWritten = 0
            leftoverText = text
            while leftoverText:
                if namingFormat == 'Short':
                    jpegOutputFilepath = os.path.join( chapterFolderPath, filenameTemplate.format( pagesWritten ) )
                elif namingFormat == 'Long':
                    jpegOutputFilepath = os.path.join( chapterFolderPath, filenameTemplate.format( BBBnum, intC, pagesWritten, BBB ) )
                leftoverText = renderPage( BBB, C, bookName, leftoverText, jpegOutputFilepath )
                pagesWritten += 1
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule and BBB not in ('FRT','GLS',) and pagesWritten>99 and numVerses<65: halt # Template is probably bad

            #print( "pagesWritten were", pagesWritten )
            return pagesWritten
        # end of toPhotoBible.renderChapterText


        # This is the main code of toPhotoBible
        # Write the JPG files in the appropriate folders
        for BBB,bookObject in self.books.items(): # BBB is our three-character book code
            internalBibleBookData = bookObject._processedLines

            # Find a suitable bookname
            #bookName = self.getAssumedBookName( BBB )
            for bookName in (self.getAssumedBookName(BBB), self.getLongTOCName(BBB), self.getShortTOCName(BBB), self.getBooknameAbbreviation(BBB), ):
                #print( "Tried bookName:", repr(bookName) )
                if bookName is not None and len(bookName)<=maxBooknameLetters: break
            bookAbbrev = self.getBooknameAbbreviation( BBB )
            bookAbbrev = BBB if not bookAbbrev else BibleOrgSysGlobals.makeSafeFilename( bookAbbrev.replace( ' ', '' ) )

            BBBnum = BibleOrgSysGlobals.loadedBibleBooksCodes.getReferenceNumber( BBB )
            maxChapters = BibleOrgSysGlobals.loadedBibleBooksCodes.getMaxChapters( BBB )

            # Find a suitable folder name and make the necessary folder(s)
            if BibleOrgSysGlobals.loadedBibleBooksCodes.isOldTestament_NR( BBB ):
                subfolderName = 'OT/'
            elif BibleOrgSysGlobals.loadedBibleBooksCodes.isNewTestament_NR( BBB ):
                subfolderName = 'NT/'
            else:
                subfolderName = 'Other/'
            if BBBnum < 100: bookFolderName = '{:02}-{}/'.format( BBBnum, bookAbbrev )
            else: bookFolderName = '{:03}-{}/'.format( BBBnum, bookAbbrev ) # Should rarely happen
            bookFolderPath = os.path.join( outputFolderpath, subfolderName, bookFolderName )
            if not os.access( bookFolderPath, os.F_OK ): os.makedirs( bookFolderPath ) # Make the empty folder if there wasn't already one there

            # First of all, get the text (by chapter) into textBuffer
            C, V = '-1', '-1' # So first/id line starts at -1:0
            intC, numVerses = -1, 0
            lastMarker = gotVP = None
            textBuffer = ''
            for entry in internalBibleBookData:
                marker, cleanText = entry.getMarker(), entry.getCleanText() # Clean text completely ignores formatting and footnotes, cross-references, etc.
                #print( BBB, C, V, marker, repr(cleanText) )
                if '¬' in marker or marker in BOS_ADDED_NESTING_MARKERS or marker=='v=':
                    continue # Just ignore added markers — not needed here
                if marker in USFM_PRECHAPTER_MARKERS:
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
                        assert C=='-1' or marker=='rem' or marker.startswith('mte')
                    V = str( int(V) + 1 )

                if marker in OFTEN_IGNORED_USFM_HEADER_MARKERS or marker in ('ie',): # Just ignore these lines
                    ignoredMarkers.add( marker )
                elif marker in ('mt1','mt2','mt3','mt4','mte1','mte2','mte3','mte4',
                                'imt1','imt2','imt3','imt4', 'imte1','imte2','imte3','imte4', 'periph',): # Simple headings
                    #if textBuffer: textBuffer += '\n'
                    textBuffer += '\n\nHhH' + cleanText + '\n'
                elif marker in ('s1','s2','s3','s4', 'is1','is2','is3','is4', 'ms1','ms2','ms3','ms4', 'sr',): # Simple headings
                    #if textBuffer: textBuffer += '\n'
                    textBuffer += '\n\nSsS' + cleanText + '\n'
                elif marker in USFM_ALL_INTRODUCTION_MARKERS: # Drop the introduction
                    ignoredMarkers.add( marker )

                elif marker in ('c','cp',): # cp should follow (and thus override) c
                    if textBuffer: renderChapterText( BBB, BBBnum, bookName, bookAbbrev, C, intC, maxChapters, numVerses, textBuffer, bookFolderPath ); textBuffer = ''
                    C, V = cleanText, '0'
                    if marker == 'c':
                        try: intC = int( C ) # But cp text might not be an integer
                        except ValueError: logger.critical( "toPhotoBible: will overwrite chapter {} of {} (couldn't process {!r})".format( intC, BBB, C ) )
                    numVerses = 0
                elif marker == 'cl': # specific chapter label
                    textBuffer += '\n' + cleanText
                elif marker in ('c#',): # These are the markers that we can safely ignore for this export
                    ignoredMarkers.add( marker )
                elif marker == 'vp#': # This precedes a v field and has the verse number to be printed
                    gotVP = cleanText # Just remember it for now
                elif marker == 'v':
                    V = cleanText
                    if gotVP: # this is a replacement verse number for publishing
                        cleanText = gotVP
                        gotVP = None
                    textBuffer += (' ' if textBuffer and textBuffer[-1]!='\n' else '') + 'VvV' + cleanText + ' '
                    numVerses += 1

                elif marker in ('d','sp','cd', 'lit',):
                    #assert cleanText or extras
                    textBuffer += '\n' + cleanText
                elif marker in ('r','sr','mr',):
                    #numSpaces = ( maxLineCharacters - len(cleanText) ) // 2
                    #print( BBB, C, len(cleanText), "numSpaces:", numSpaces, repr(cleanText) )
                    #textBuffer += '\n' + ' '*numSpaces + cleanText # Roughly centred
                    if lastMarker not in ('s1','s2','s3','s4',): textBuffer += '\n' # Section headings already have one at the end
                    textBuffer += 'RrR' + ' '*((maxLineCharacters+1-len(cleanText))//2) + cleanText + '\n' # Roughly centred
                elif marker in ('p', 'pi1','pi2','pi3','pi4', 'q1','q2','q3','q4', 'm','mi','im','imi', 'ph1','ph2','ph3','ph4','pc',
                                'li1','li2','li3','li4', 'ip','ipi', 'ili1','ili2','ili3','ili4', 'iex',):
                    # Just put it on a new line
                    textBuffer += '\n'
                    if marker not in ('m','mi','im','imi','ph1','ph2','ph3','ph4',): textBuffer += '  ' # Non-break spaces won't be lost later
                    if marker in ('li1','li2','li3','li4', 'ili1','ili2','ili3','ili4',): textBuffer += '• '
                    if marker in ('ipi','pi1','q1','ph1','mi','imi','li1','ili1',): textBuffer += '_I1_'
                    elif marker in ('pi2','q2','ph2','li2','ili2',): textBuffer += '_I2_'
                    elif marker in ('pi3','q3','ph3','li3','ili3',): textBuffer += '_I3_'
                    elif marker in ('pi4','q4','ph4','li4','ili4',): textBuffer += '_I4_'
                    #if marker == 'q2': textBuffer += ' '
                    #elif marker == 'q3': textBuffer += '  '
                    if marker in ('ip','ipi','ili1','ili2','ili3','ili4',): textBuffer += cleanText
                    elif BibleOrgSysGlobals.debugFlag: assert not cleanText
                elif marker == 'tr':
                    #assert cleanText or extras
                    textBuffer += '\n' + cleanText
                elif marker in ('v~','p~',):
                    #assert cleanText or extras
                    textBuffer += cleanText
                elif marker in ('b','nb','ib',):
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not cleanText
                    textBuffer += '\n'
                    textBuffer += '\n'
                else:
                    if cleanText:
                        logger.error( "toPhotoBible: {} lost text in {} field in {} {}:{} {!r}".format( self.abbreviation, marker, BBB, C, V, cleanText ) )
                        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
                    unhandledMarkers.add( marker )
                #if extras and marker not in ('v~','p~',):
                    #logger.critical( "toPhotoBible: extras not handled for {} at {} {}:{}".format( marker, BBB, C, V ) )
                    #if BibleOrgSysGlobals.debugFlag: halt
                lastMarker = marker
            if textBuffer: renderChapterText( BBB, BBBnum, bookName, bookAbbrev, C, intC, maxChapters, numVerses, textBuffer, bookFolderPath ) # Write the last bit

                    #if verseByVerse:
                        #myFile.write( "{} ({}): {!r} {!r} {}\n" \
                            #.format( entry.getMarker(), entry.getOriginalMarker(), entry.getAdjustedText(), entry.getCleanText(), entry.getExtras() ) )

        if ignoredMarkers:
            logger.info( "toPhotoBible: Ignored markers were {}".format( ignoredMarkers ) )
            if BibleOrgSysGlobals.verbosityLevel > 2:
                print( "  " + _("WARNING: Ignored toPhotoBible markers were {}").format( ignoredMarkers ) )
        if unhandledMarkers:
            logger.warning( "toPhotoBible: Unhandled markers were {}".format( unhandledMarkers ) )
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print( "  " + _("WARNING: Unhandled toPhotoBible markers were {}").format( unhandledMarkers ) )

        # Now create some zipped collections (for easier downloads)
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Zipping PhotoBible files…" )
        for subset in ('OT','NT','Other','All'):
            loadFolder = outputFolderpath if subset=='All' else os.path.join( outputFolderpath, subset+'/' )
            #print( repr(subset), "Load folder =", repr(loadFolder) )
            if os.path.exists( loadFolder ):
                zf = zipfile.ZipFile( os.path.join( outputFolderpath, subset+'PhotoBible.zip' ), 'w', compression=zipfile.ZIP_DEFLATED )
                for root, dirs, files in os.walk( loadFolder ):
                    for filename in files:
                        if not filename.endswith( '.zip' ):
                            #print( repr(loadFolder), repr(root), repr(dirs), repr(files) )
                            #print( repr(os.path.relpath(os.path.join(root, filename))), repr(os.path.join(loadFolder, '..')) )
                            #print( os.path.join(root,filename), os.path.relpath(os.path.join(root, filename), os.path.join(loadFolder, '..')) ) # Save in the archive without the path
                            #  Save in the archive without the path —
                            #   parameters are filename to compress, archive name (relative path) to save as
                            zf.write( os.path.join(root,filename), os.path.relpath(os.path.join(root, filename), os.path.join(loadFolder, '..')) ) # Save in the archive without the path
                            #zf.write( filepath, filename ) # Save in the archive without the path
                zf.close()
        #if self.abbreviation in ('MBTV','WEB','OEB',): # Do a special zip file of just Matthew as a test download
        if 'MAT' in self: # Do a zip file of just Matthew as a smaller download for testers
            zf = zipfile.ZipFile( os.path.join( outputFolderpath, 'MatthewPhotoBible.zip' ), 'w', compression=zipfile.ZIP_DEFLATED )
            loadFolder = os.path.join( outputFolderpath, 'NT/' )
            for root, dirs, files in os.walk( loadFolder ):
                for filename in files:
                    if '40-Mat' in root and not filename.endswith( '.zip' ): #  Save in the archive without the path —
                        #   parameters are filename to compress, archive name (relative path) to save as
                        zf.write( os.path.join(root,filename), os.path.relpath(os.path.join(root, filename), os.path.join(loadFolder, '..')) ) # Save in the archive without the path
            zf.close()

        if BibleOrgSysGlobals.verbosityLevel > 0 and BibleOrgSysGlobals.maxProcesses > 1:
            print( "  BibleWriter.toPhotoBible finished successfully at {}".format( datetime.now().strftime('%H:%M') ) )
        return True
    # end of BibleWriter.toPhotoBible


    def toODF( self, outputFolderpath:Optional[Path]=None ):
        """
        Write the internal Bible format out into Open Document Format (ODF)
            suitable for opening in LibreOffice or OpenOffice.

        This function hasn't been tested in Windows
            and probably won't work.
        """
        import uno
        from com.sun.star.lang import IllegalArgumentException
        from time import sleep

        if BibleOrgSysGlobals.verbosityLevel > 1:
            print( "Running BibleWriter:toODF… {}".format( datetime.now().strftime('%H:%M') ) )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert self.books

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolderpath: outputFolderpath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_ODF_Export/' )
        if not os.access( outputFolderpath, os.F_OK ): os.makedirs( outputFolderpath ) # Make the empty folder if there wasn't already one there
        os.chmod( outputFolderpath, 0o777 ) # Allow all users to write to this folder (ServiceManager might run as a different user)

        weStartedLibreOffice = False
        DEFAULT_OPENOFFICE_PORT = 2002
        startWithTemplate = True # Start with template (all styles already built) or just a blank document (much slower)

        ODF_PARAGRAPH_BREAK = uno.getConstantByName( "com.sun.star.text.ControlCharacter.PARAGRAPH_BREAK" )
        ODF_LINE_BREAK = uno.getConstantByName( "com.sun.star.text.ControlCharacter.LINE_BREAK" )
        #ODF_HARD_HYPHEN = uno.getConstantByName( "com.sun.star.text.ControlCharacter.HARD_HYPHEN" )
        #ODF_SOFT_HYPHEN = uno.getConstantByName( "com.sun.star.text.ControlCharacter.SOFT_HYPHEN" )
        #ODF_HARD_SPACE = uno.getConstantByName( "com.sun.star.text.ControlCharacter.HARD_SPACE" )
        #ODF_APPEND_PARAGRAPH = uno.getConstantByName( "com.sun.star.text.ControlCharacter.APPEND_PARAGRAPH" )

        def isServiceManagerRunning():
            """
            Checks to see if the LibreOffice ServiceManager is in the list of running tasks
            """
            for pid in os.listdir('/proc'):
                try:
                    procInfoBytes = open(os.path.join('/proc', pid, 'cmdline'), 'rb').read()
                    if b'StarOffice.ServiceManager' in procInfoBytes: return True
                except IOError: # proc has already terminated
                    continue
            return False
        # end of isServiceManagerRunning

        def startLibreOfficeServiceManager():
            """
            """
            if debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 1:
                print( "Starting LibreOffice ServiceManager…" )
            # Start LibreOffice
            #       Either: /usr/bin/libreoffice --accept="socket,host=localhost,port=2002;urp;StarOffice.ServiceManager"
            #       Or: /usr/bin/libreoffice --accept="socket,host=localhost,port=2002;urp;StarOffice.ServiceManager" --norestore --nologo --headless
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                os.system( '/usr/bin/libreoffice --accept="socket,host=localhost,port={};urp;StarOffice.ServiceManager" &'.format( DEFAULT_OPENOFFICE_PORT ) )
            else: # run LibreOffice headless
                os.system( '/usr/bin/libreoffice --accept="socket,host=localhost,port={};urp;StarOffice.ServiceManager" --norestore --nologo --headless &'.format( DEFAULT_OPENOFFICE_PORT ) )
            weStartedLibreOffice = True
            if 0:
                parameters = ['/usr/bin/libreoffice', '--accept="socket,host=localhost,port={};urp;StarOffice.ServiceManager"'.format( DEFAULT_OPENOFFICE_PORT ),'--norestore','--nologo','--headless']
                print( "Parameters", repr(parameters) )
                myProcess = subprocess.Popen( parameters, stdout=subprocess.PIPE, stderr=subprocess.PIPE )
                sleep( 5 ) # Wait
                #programOutputBytes, programErrorOutputBytes = myProcess.communicate()
                #returnCode = myProcess.returncode
                #print( "returnCode", returnCode )
                # Why does this give:
                #   context = resolver.resolve("uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext")
                #   BibleWriter.NoConnectException: Connector : couldn't connect to socket (Success)
            sleep( 1 ) # Wait a second to get sure that LibreOffice has time to start up
        # end of startLibreOfficeServiceManager

        restartLOSMForEachBook = True # Restart LibreOffice ServiceManager for each book
        #   We restart for each book coz sometimes it seems to lock-up and then lots of books don't get created
        if not restartLOSMForEachBook:
            if isServiceManagerRunning(): killLibreOfficeServiceManager() # Seems safer to always do this
            #assert not isServiceManagerRunning() # could be running in another user
            startLibreOfficeServiceManager()
            weStartedLibreOffice = True

            # Set-up LibreOffice
            localContext = uno.getComponentContext()
            urlResolver = localContext.ServiceManager.createInstanceWithContext( "com.sun.star.bridge.UnoUrlResolver", localContext )
            componentContext = urlResolver.resolve( "uno:socket,host=localhost,port={};urp;StarOffice.ComponentContext".format( DEFAULT_OPENOFFICE_PORT ) )
            serviceManager = componentContext.ServiceManager
            frameDesktop = serviceManager.createInstanceWithContext( "com.sun.star.frame.Desktop", componentContext )
            #model = frameDesktop.getCurrentComponent()

            # Locate our empty template file (with all the styles there already) that we'll start from
            templateFilepath = os.path.join( os.getcwd(), defaultControlFolderpath, "BibleBook.ott" )
            sourceURL = "file://{}".format( templateFilepath ) if startWithTemplate else "private:factory/swriter"

        ignoredMarkers, unhandledMarkers = set(), set()

        titleODFStyleDict = {'imt1':'Introduction Major Title 1', 'imt2':'Introduction Major Title 2', 'imt3':'Introduction Major Title 3', 'imt4':'Introduction Major Title 4',
                          'imte1':'Introduction Major Title at Ending 1','imte2':'Introduction Major Title at Ending 2', 'imte3':'Introduction Major Title at Ending 3', 'imte4':'Introduction Major Title at Ending 4',
                          'mt1':'Major Title 1','mt2':'Major Title 2', 'mt3':'Major Title 3', 'mt4':'Major Title 4',
                          'mte1':'Major Title at Ending 1','mte2':'Major Title at Ending 2', 'mte3':'Major Title at Ending 3', 'mte4':'Major Title at Ending 4', }
        ipODFStyleDict = {'ip':'Introduction Paragraph', 'ipi':'Introduction Paragraph Indented', 'ipr':'Introduction Right Aligned Paragraph',
                        'im':'Introduction Flush Left Paragraph', 'imi':'Introduction Indented Flush Left Paragraph',
                        'iex':'Introduction Explanation', 'iot':'Introduction Outline Title',
                        'io1':'Introduction Outline Entry 1', 'io2':'Introduction Outline Entry 2', 'io3':'Introduction Outline Entry 3', 'io4':'Introduction Outline Entry 4',
                        'iq1':'Introduction Poetry Paragraph 1','iq2':'Introduction Poetry Paragraph 2','iq3':'Introduction Poetry Paragraph 3','iq4':'Introduction Poetry Paragraph 4',
                        'ipq':'Introduction Quote Paragraph', 'imq':'Introduction Flush Left Quote Paragraph', }

        pqODFStyleDict = {'p':'Prose Paragraph', 'm':'Flush Left Paragraph',
                        'pmo':'Embedded Opening Paragraph', 'pm':'Embedded Paragraph', 'pmc':'Embedded Closing Paragraph',
                        'pmr':'Embedded Refrain Paragraph',
                        'pi1':'Indented Prose Paragraph 1','pi2':'Indented Prose Paragraph 2','pi3':'Indented Prose Paragraph 3','pi4':'Indented Prose Paragraph 4',
                        'mi':'Indented Flush Left Paragraph', 'cls':'Closure Paragraph',
                        'pc':'Centered Prose Paragraph', 'pr':'Right Aligned Prose Paragraph',
                        'ph1':'Hanging Prose Paragraph 1','ph2':'Hanging Prose Paragraph 2','ph3':'Hanging Prose Paragraph 3','ph4':'Hanging Prose Paragraph 4',

                        'q1':'Poetry Paragraph 1','q2':'Poetry Paragraph 2','q3':'Poetry Paragraph 3','q4':'Poetry Paragraph 4',
                        'qr':'Right Aligned Poetry Paragraph', 'qc':'Centered Poetry Paragraph',
                        'qm1':'Embedded Poetry Paragraph 1','qm2':'Embedded Poetry Paragraph 2','qm3':'Embedded Poetry Paragraph 3','qm4':'Embedded Poetry Paragraph 4'}

        miscODFStyleDict = {'d':'Descriptive Title', 'sp':'Speaker Identification', 'cl':'Chapter Label', }

        charODFStyleDict = {'bk':'Book Name', 'ior':'Introduction Outline Reference',
                            'add':'Added Words', 'nd':'Divine Name', 'wj':'Words of Jesus', 'sig':'Author Signature',
                            'rq':'Inline Quotation Reference', 'qs':'Selah Text',
                            'w':'Wordlist Entry', 'iqt':'Introduction Quoted Text',
                            'em':'Emphasis Text', 'bd':'Bold Text', 'it':'Italic Text', 'bdit':'Bold Italic Text', 'sc':'Small Caps Text', }


        def setupStyles( styleFamilies ):
            """
            Defines new styles that are not in the template (yet).

            Or it can create our hierarchical styles from scratch if startWithTemplate is not set
                (but we don't know how to make superscripts or how to put custom fields into the running header).

            But if everything is going well/normally, this function does absolutely nothing.
            """
            if 0: # This is how we add new styles to the existing template
                paragraphStyles = styleFamilies.getByName('ParagraphStyles')
                CENTER_PARAGRAPH = uno.Enum( 'com.sun.star.style.ParagraphAdjust', 'CENTER' )
                RIGHT_PARAGRAPH = uno.Enum( 'com.sun.star.style.ParagraphAdjust', 'RIGHT' )

                #style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                #style.setParentStyle( 'Bible Heading' )
                #style.setPropertyValue( 'CharHeight', 20 )
                #style.setPropertyValue( 'CharWeight', 150 ) # bold
                #style.setPropertyValue( 'ParaAdjust', CENTER_PARAGRAPH )
                #style.setPropertyValue( 'ParaKeepTogether', True )
                #paragraphStyles.insertByName( 'Major Title', style ) # Base style only

                #style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                #style.setParentStyle( 'Bible Paragraph' )
                #style.setPropertyValue( 'ParaKeepTogether', True )
                #paragraphStyles.insertByName( 'Temp Rubbish', style )

                characterStyles = styleFamilies.getByName( 'CharacterStyles' )
                ITALIC_TEXT_POSTURE = uno.Enum( 'com.sun.star.awt.FontSlant', 'ITALIC' )

                #style = document.createInstance( 'com.sun.star.style.CharacterStyle' )
                #style.setPropertyValue( 'CharBackColor', 0x00E0E0E0 ) # alpha/R/G/B = light gray
                #characterStyles.insertByName( 'Wordlist Entry', style )

                #style = document.createInstance( 'com.sun.star.style.CharacterStyle' )
                #style.setPropertyValue('CharPosture', ITALIC_TEXT_POSTURE )
                #characterStyles.insertByName( 'Introduction Quoted Text', style )

                #style = document.createInstance( 'com.sun.star.style.CharacterStyle' )
                #style.setPropertyValue('CharPosture', ITALIC_TEXT_POSTURE )
                #characterStyles.insertByName( 'Alternative Chapter Number', style )

                #style = document.createInstance( 'com.sun.star.style.CharacterStyle' )
                #style.setPropertyValue('CharPosture', ITALIC_TEXT_POSTURE )
                #characterStyles.insertByName( 'Alternative Verse Number', style )


            if not startWithTemplate: # Create initial styles (not required or allowed if we use the template)

                ## PAGE STYLES
                #pageStyles = styleFamilies.getByName( 'PageStyles' )
                #pageStyles = styleFamilies.getByName( 'PageStyles' )
                #defaultPageStyle = pageStyles.getByName( 'Default Style' )
                #defaultPageStyle.setPropertyValue( 'HeaderIsOn', True )
                #defaultPageStyle.setPropertyValue( 'FooterIsOn', True )

                #leftPageStyle = pageStyles.getByName( 'Left Page' )
                #rightPageStyle= pageStyles.getByName( 'Right Page' )
                #leftPageStyle.setPropertyValue( 'HeaderIsOn', True )
                #rightPageStyle.setPropertyValue( 'HeaderIsOn', True )
                #leftPageStyle.setPropertyValue( 'FooterIsOn', True )
                #rightPageStyle.setPropertyValue( 'FooterIsOn', True )
                #leftPageStyle = pageStyles.getByName( 'Left Page' )
                #leftPageStyle.FollowStyle = ( 'Right Page' )
                #rightPageStyle= pageStyles.getByName( 'Right Page' )
                #rightPageStyle.FollowStyle = ( 'Left Page' )
                #headerTextRight = rightPageStyle.getPropertyValue( 'HeaderTextRight' )
                #headerTextLeft = leftPageStyle.getPropertyValue( 'HeaderTextLeft' )
                #headerCursorRight = headerTextRight.createTextCursor()
                #headerCursorLeft = headerTextLeft.createTextCursor()

                #PN = doc.createInstance('com.sun.star.text.textfield.PageNumber')
                #PC = doc.createInstance('com.sun.star.text.textfield.PageCount')
                #PN.NumberingType=4
                #PN.SubType='CURRENT'
                #PC.NumberingType=4
                #Logo_OO=doc.createInstance( 'com.sun.star.text.TextGraphicObject' )
                #Logo_OO.AnchorType = 'AT_PARAGRAPH'
                #Logo_OO.GraphicURL = 'file:///home/beranger/Documents/FE_Rapport/logo_OO.png'
                #Logo_OO.HoriOrient=3
                #Logo_OO.SurroundAnchorOnly = False

                #headerTextRight.insertString(headerCursorRight,"Un truc à inclure dans le header Right", False)
                #headerTextLeft.insertString(headerCursorLeft,"Un truc à inclure dans le header left", False)

                #FooterTextRight.insertTextContent(FooterCursorRight, Logo_OO, False )

                #FooterTextLeft.insertTextContent(FooterCursorLeft,PN, False)
                #FooterTextLeft.insertString(FooterCursorLeft,'/', False)
                #FooterTextLeft.insertTextContent(FooterCursorLeft,PC, False)


                # PARAGRAPH STYLES
                paragraphStyles = styleFamilies.getByName('ParagraphStyles')
                CENTER_PARAGRAPH = uno.Enum( 'com.sun.star.style.ParagraphAdjust', 'CENTER' )
                RIGHT_PARAGRAPH = uno.Enum( 'com.sun.star.style.ParagraphAdjust', 'RIGHT' )

                # Main base paragraph styles
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                paragraphStyles.insertByName( 'Bible Paragraph', style ) # Main base style only

                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Heading' )
                style.setPropertyValue( 'CharWeight', 150 ) # bold
                style.setPropertyValue( 'ParaAdjust', CENTER_PARAGRAPH )
                style.setPropertyValue( 'ParaKeepTogether', True )
                paragraphStyles.insertByName( 'Bible Heading', style ) # Main base style only

                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Header' )
                paragraphStyles.insertByName( 'BibleHeader', style ) # Main base style only

                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Footer' )
                paragraphStyles.insertByName( 'BibleFooter', style ) # Main base style only

                # Other base paragraph styles
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Bible Paragraph' )
                paragraphStyles.insertByName( 'Prose Paragraph', style ) # Base and actual style

                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Bible Paragraph' )
                paragraphStyles.insertByName( 'Poetry Paragraph', style ) # Base style only

                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Bible Paragraph' )
                paragraphStyles.insertByName( 'Introduction Paragraph', style ) # Base and actual style

                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Bible Paragraph' )
                paragraphStyles.insertByName( 'Introduction Poetry Paragraph', style ) # Base style only

                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Bible Heading' )
                style.setPropertyValue( 'CharHeight', 20 )
                paragraphStyles.insertByName( 'Major Title', style ) # Base style only

                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Bible Heading' )
                style.setPropertyValue( 'CharHeight', 20 )
                paragraphStyles.insertByName( 'Introduction Major Title', style ) # Base style only

                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Bible Heading' )
                paragraphStyles.insertByName( 'Major Section Heading', style ) # Base style only

                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Bible Heading' )
                paragraphStyles.insertByName( 'Section Heading', style ) # Base style only

                # Title paragraph styles
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Major Title' )
                paragraphStyles.insertByName( 'Major Title 1', style )
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Major Title' )
                style.setPropertyValue( 'CharDiffHeight', -2 )
                paragraphStyles.insertByName( 'Major Title 2', style )
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Major Title' )
                style.setPropertyValue( 'CharDiffHeight', -2 )
                paragraphStyles.insertByName( 'Major Title 3', style )
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Major Title' )
                style.setPropertyValue( 'CharDiffHeight', -1 )
                paragraphStyles.insertByName( 'Major Title 4', style )

                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Major Title' )
                paragraphStyles.insertByName( 'Major Title at Ending', style ) # Base style only
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Major Title at Ending' )
                paragraphStyles.insertByName( 'Major Title at Ending 1', style )
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Major Title at Ending' )
                style.setPropertyValue( 'CharDiffHeight', -2 )
                paragraphStyles.insertByName( 'Major Title at Ending 2', style )
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Major Title at Ending' )
                style.setPropertyValue( 'CharDiffHeight', -2 )
                paragraphStyles.insertByName( 'Major Title at Ending 3', style )
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Major Title at Ending' )
                style.setPropertyValue( 'CharDiffHeight', -1 )
                paragraphStyles.insertByName( 'Major Title at Ending 4', style )

                # Section heading paragraph styles
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Major Section Heading' )
                paragraphStyles.insertByName( 'Major Section Heading 1', style )
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Major Section Heading' )
                paragraphStyles.insertByName( 'Major Section Heading 2', style )
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Major Section Heading' )
                paragraphStyles.insertByName( 'Major Section Heading 3', style )
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Major Section Heading' )
                paragraphStyles.insertByName( 'Major Section Heading 4', style )

                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Section Heading' )
                paragraphStyles.insertByName( 'Section Heading 1', style )
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Section Heading' )
                paragraphStyles.insertByName( 'Section Heading 2', style )
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Section Heading' )
                paragraphStyles.insertByName( 'Section Heading 3', style )
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Section Heading' )
                paragraphStyles.insertByName( 'Section Heading 4', style )

                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Bible Paragraph' )
                style.setPropertyValue( 'ParaAdjust', CENTER_PARAGRAPH )
                style.setPropertyValue( 'ParaKeepTogether', True )
                paragraphStyles.insertByName( 'Section CrossReference', style )

                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Bible Paragraph' )
                style.setPropertyValue( 'ParaAdjust', CENTER_PARAGRAPH )
                paragraphStyles.insertByName( 'Section Reference Range', style )

                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Bible Paragraph' )
                style.setPropertyValue( 'ParaAdjust', CENTER_PARAGRAPH )
                paragraphStyles.insertByName( 'Major Section Reference Range', style )

                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Prose Paragraph' )
                paragraphStyles.insertByName( 'Descriptive Title', style )
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Prose Paragraph' )
                paragraphStyles.insertByName( 'Speaker Identification', style )

                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Section Heading' )
                paragraphStyles.insertByName( 'Chapter Label', style )

                # Prose paragraph styles
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Prose Paragraph' )
                paragraphStyles.insertByName( 'Flush Left Paragraph', style )

                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Prose Paragraph' )
                paragraphStyles.insertByName( 'Embedded Opening Paragraph', style )

                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Prose Paragraph' )
                paragraphStyles.insertByName( 'Embedded Paragraph', style )

                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Prose Paragraph' )
                paragraphStyles.insertByName( 'Embedded Closing Paragraph', style )

                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Prose Paragraph' )
                paragraphStyles.insertByName( 'Embedded Refrain Paragraph', style )

                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Prose Paragraph' )
                paragraphStyles.insertByName( 'Indented Prose Paragraph', style ) # Base style only
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Indented Prose Paragraph' )
                paragraphStyles.insertByName( 'Indented Prose Paragraph 1', style )
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Indented Prose Paragraph' )
                paragraphStyles.insertByName( 'Indented Prose Paragraph 2', style )
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Indented Prose Paragraph' )
                paragraphStyles.insertByName( 'Indented Prose Paragraph 3', style )
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Indented Prose Paragraph' )
                paragraphStyles.insertByName( 'Indented Prose Paragraph 4', style )

                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Prose Paragraph' )
                paragraphStyles.insertByName( 'Indented Flush Left Paragraph', style )

                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Prose Paragraph' )
                style.setPropertyValue( 'ParaAdjust', CENTER_PARAGRAPH )
                paragraphStyles.insertByName( 'Centered Prose Paragraph', style )

                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Prose Paragraph' )
                style.setPropertyValue( 'ParaAdjust', RIGHT_PARAGRAPH )
                paragraphStyles.insertByName( 'Right Aligned Prose Paragraph', style )

                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Prose Paragraph' )
                paragraphStyles.insertByName( 'Hanging Prose Paragraph', style ) # Base style only
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Hanging Prose Paragraph' )
                paragraphStyles.insertByName( 'Hanging Prose Paragraph 1', style )
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Hanging Prose Paragraph' )
                paragraphStyles.insertByName( 'Hanging Prose Paragraph 2', style )
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Hanging Prose Paragraph' )
                paragraphStyles.insertByName( 'Hanging Prose Paragraph 3', style )
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Hanging Prose Paragraph' )
                paragraphStyles.insertByName( 'Hanging Prose Paragraph 4', style )

                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Prose Paragraph' )
                paragraphStyles.insertByName( 'Blank Line Paragraph', style )

                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Prose Paragraph' )
                paragraphStyles.insertByName( 'Closure Paragraph', style )

                # Poetry paragraph styles
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Poetry Paragraph' )
                paragraphStyles.insertByName( 'Poetry Paragraph 1', style )
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Poetry Paragraph' )
                paragraphStyles.insertByName( 'Poetry Paragraph 2', style )
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Poetry Paragraph' )
                paragraphStyles.insertByName( 'Poetry Paragraph 3', style )
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Poetry Paragraph' )
                paragraphStyles.insertByName( 'Poetry Paragraph 4', style )

                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Poetry Paragraph' )
                style.setPropertyValue( 'ParaAdjust', RIGHT_PARAGRAPH )
                paragraphStyles.insertByName( 'Right Aligned Poetry Paragraph', style )

                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Poetry Paragraph' )
                style.setPropertyValue( 'ParaAdjust', CENTER_PARAGRAPH )
                paragraphStyles.insertByName( 'Centered Poetry Paragraph', style )

                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Poetry Paragraph' )
                paragraphStyles.insertByName( 'Embedded Poetry Paragraph', style ) # Base style only
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Embedded Poetry Paragraph' )
                paragraphStyles.insertByName( 'Embedded Poetry Paragraph 1', style )
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Embedded Poetry Paragraph' )
                paragraphStyles.insertByName( 'Embedded Poetry Paragraph 2', style )
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Embedded Poetry Paragraph' )
                paragraphStyles.insertByName( 'Embedded Poetry Paragraph 3', style )
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Embedded Poetry Paragraph' )
                paragraphStyles.insertByName( 'Embedded Poetry Paragraph 4', style )

                # List styles
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Prose Paragraph' )
                paragraphStyles.insertByName( 'List Item', style ) #Base style only
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'List Item' )
                paragraphStyles.insertByName( 'List Item 1', style )
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'List Item' )
                paragraphStyles.insertByName( 'List Item 2', style )
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'List Item' )
                paragraphStyles.insertByName( 'List Item 3', style )
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'List Item' )
                paragraphStyles.insertByName( 'List Item 4', style )

                # Note styles
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Footnote' )
                paragraphStyles.insertByName( 'Bible Footnote', style )

                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Endnote' )
                paragraphStyles.insertByName( 'Bible Endnote', style )

                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Footnote' )
                paragraphStyles.insertByName( 'Verse Cross Reference', style )

                # Introduction styles
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Introduction Major Title' )
                paragraphStyles.insertByName( 'Introduction Major Title 1', style )
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Introduction Major Title' )
                style.setPropertyValue( 'CharDiffHeight', -2 )
                paragraphStyles.insertByName( 'Introduction Major Title 2', style )
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Introduction Major Title' )
                style.setPropertyValue( 'CharDiffHeight', -2 )
                paragraphStyles.insertByName( 'Introduction Major Title 3', style )
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Introduction Major Title' )
                style.setPropertyValue( 'CharDiffHeight', -1 )
                paragraphStyles.insertByName( 'Introduction Major Title 4', style )

                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Introduction Major Title' )
                paragraphStyles.insertByName( 'Introduction Major Title at Ending', style ) # Base style only
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Introduction Major Title at Ending' )
                paragraphStyles.insertByName( 'Introduction Major Title at Ending 1', style )
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Introduction Major Title at Ending' )
                style.setPropertyValue( 'CharDiffHeight', -2 )
                paragraphStyles.insertByName( 'Introduction Major Title at Ending 2', style )
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Introduction Major Title at Ending' )
                style.setPropertyValue( 'CharDiffHeight', -2 )
                paragraphStyles.insertByName( 'Introduction Major Title at Ending 3', style )
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Introduction Major Title at Ending' )
                style.setPropertyValue( 'CharDiffHeight', -1 )
                paragraphStyles.insertByName( 'Introduction Major Title at Ending 4', style )

                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Bible Heading' )
                paragraphStyles.insertByName( 'Introduction Section Heading', style ) # Base style only
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Introduction Section Heading' )
                paragraphStyles.insertByName( 'Introduction Section Heading 1', style )
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Introduction Section Heading' )
                paragraphStyles.insertByName( 'Introduction Section Heading 2', style )
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Introduction Section Heading' )
                paragraphStyles.insertByName( 'Introduction Section Heading 3', style )
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Introduction Section Heading' )
                paragraphStyles.insertByName( 'Introduction Section Heading 4', style )

                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Introduction Paragraph' )
                paragraphStyles.insertByName( 'Introduction Paragraph Indented', style )
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Introduction Paragraph' )
                paragraphStyles.insertByName( 'Introduction Flush Left Paragraph', style )
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Introduction Paragraph' )
                paragraphStyles.insertByName( 'Introduction Indented Flush Left Paragraph', style )

                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Introduction Poetry Paragraph' )
                paragraphStyles.insertByName( 'Introduction Poetry Paragraph 1', style )
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Introduction Poetry Paragraph' )
                paragraphStyles.insertByName( 'Introduction Poetry Paragraph 2', style )
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Introduction Poetry Paragraph' )
                paragraphStyles.insertByName( 'Introduction Poetry Paragraph 3', style )
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Introduction Poetry Paragraph' )
                paragraphStyles.insertByName( 'Introduction Poetry Paragraph 4', style )

                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Introduction Paragraph' )
                paragraphStyles.insertByName( 'Introduction Quote Paragraph', style )

                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Introduction Paragraph' )
                paragraphStyles.insertByName( 'Introduction Flush Left Quote Paragraph', style )

                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Introduction Paragraph' )
                paragraphStyles.insertByName( 'Introduction Right Aligned Paragraph', style )

                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Introduction Paragraph' )
                paragraphStyles.insertByName( 'Introduction Explanation', style )

                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Introduction Paragraph' )
                paragraphStyles.insertByName( 'Introduction Blank Line Paragraph', style )

                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Introduction Paragraph' )
                style.setPropertyValue( 'CharWeight', 150 ) # bold
                style.setPropertyValue( 'ParaKeepTogether', True )
                paragraphStyles.insertByName( 'Introduction Outline Title', style )

                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Introduction Paragraph' )
                paragraphStyles.insertByName( 'Introduction Outline Entry', style ) # Base style only
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Introduction Outline Entry' )
                paragraphStyles.insertByName( 'Introduction Outline Entry 1', style )
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Introduction Outline Entry' )
                paragraphStyles.insertByName( 'Introduction Outline Entry 2', style )
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Introduction Outline Entry' )
                paragraphStyles.insertByName( 'Introduction Outline Entry 3', style )
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Introduction Outline Entry' )
                paragraphStyles.insertByName( 'Introduction Outline Entry 4', style )

                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Introduction Paragraph' )
                paragraphStyles.insertByName( 'Introduction List Item', style ) #Base style only
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Introduction List Item' )
                paragraphStyles.insertByName( 'Introduction List Item 1', style )
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Introduction List Item' )
                paragraphStyles.insertByName( 'Introduction List Item 2', style )
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Introduction List Item' )
                paragraphStyles.insertByName( 'Introduction List Item 3', style )
                style = document.createInstance( 'com.sun.star.style.ParagraphStyle' )
                style.setParentStyle( 'Introduction List Item' )
                paragraphStyles.insertByName( 'Introduction List Item 4', style )


                # CHARACTER STYLES
                characterStyles = styleFamilies.getByName('CharacterStyles')
                ITALIC_TEXT_POSTURE = uno.Enum( 'com.sun.star.awt.FontSlant', 'ITALIC' )

                style = document.createInstance( 'com.sun.star.style.CharacterStyle' )
                style.setPropertyValue( 'CharHeight', 16 )
                style.setPropertyValue( 'CharWeight', 150 ) # bold
                style.setPropertyValue( 'CharColor', 0x00000080 ) # alpha/R/G/B = navy blue
                characterStyles.insertByName( 'Chapter Number', style )
                style = document.createInstance( 'com.sun.star.style.CharacterStyle' )
                characterStyles.insertByName( 'Chapter Number Postspace', style )
                style = document.createInstance( 'com.sun.star.style.CharacterStyle' )
                characterStyles.insertByName( 'Verse Number Prespace', style )
                style = document.createInstance( 'com.sun.star.style.CharacterStyle' )
                characterStyles.insertByName( 'Verse Number', style )
                style.setPropertyValue( 'CharColor', 0x00808000 ) # alpha/R/G/B = olive
                style = document.createInstance( 'com.sun.star.style.CharacterStyle' )
                characterStyles.insertByName( 'Verse Number Postspace', style )
                style = document.createInstance( 'com.sun.star.style.CharacterStyle' )
                characterStyles.insertByName( 'Verse Text', style )

                style = document.createInstance( 'com.sun.star.style.CharacterStyle' )
                style.setPropertyValue('CharPosture', ITALIC_TEXT_POSTURE )
                characterStyles.insertByName( 'Book Name', style )
                style = document.createInstance( 'com.sun.star.style.CharacterStyle' )
                characterStyles.insertByName( 'Introduction Outline Reference', style )
                style = document.createInstance( 'com.sun.star.style.CharacterStyle' )
                characterStyles.insertByName( 'Added Words', style )
                style = document.createInstance( 'com.sun.star.style.CharacterStyle' )
                characterStyles.insertByName( 'Divine Name', style )
                style = document.createInstance( 'com.sun.star.style.CharacterStyle' )
                characterStyles.insertByName( 'Words of Jesus', style )

                style = document.createInstance( 'com.sun.star.style.CharacterStyle' )
                characterStyles.insertByName( 'Inline Quotation Reference', style )
                style = document.createInstance( 'com.sun.star.style.CharacterStyle' )
                characterStyles.insertByName( 'Author Signature', style )
                style = document.createInstance( 'com.sun.star.style.CharacterStyle' )
                characterStyles.insertByName( 'Selah Text', style )

                style = document.createInstance( 'com.sun.star.style.CharacterStyle' )
                characterStyles.insertByName( 'Keyword Text', style ) # in Bible text
                style = document.createInstance( 'com.sun.star.style.CharacterStyle' )
                characterStyles.insertByName( 'Main Entry Keyword', style ) # in glossary

                style = document.createInstance( 'com.sun.star.style.CharacterStyle' )
                style.setPropertyValue( 'CharBackColor', 0x00E0E0E0 ) # alpha/R/G/B = light gray
                characterStyles.insertByName( 'Wordlist Entry', style )

                style = document.createInstance( 'com.sun.star.style.CharacterStyle' )
                style.setPropertyValue('CharPosture', ITALIC_TEXT_POSTURE )
                characterStyles.insertByName( 'Introduction Quoted Text', style )

                style = document.createInstance( 'com.sun.star.style.CharacterStyle' )
                style.setPropertyValue('CharPosture', ITALIC_TEXT_POSTURE )
                characterStyles.insertByName( 'Alternative Chapter Number', style )

                style = document.createInstance( 'com.sun.star.style.CharacterStyle' )
                style.setPropertyValue('CharPosture', ITALIC_TEXT_POSTURE )
                characterStyles.insertByName( 'Alternative Verse Number', style )

                # Footnotes
                style = document.createInstance( 'com.sun.star.style.CharacterStyle' )
                style.setPropertyValue( 'CharWeight', 150 ) # bold
                style.setPropertyValue( 'CharBackColor', 0x00FFFF00 ) # alpha/R/G/B = yellow
                characterStyles.insertByName( 'Footnote Origin', style )
                style = document.createInstance( 'com.sun.star.style.CharacterStyle' )
                style.setPropertyValue('CharPosture', ITALIC_TEXT_POSTURE )
                characterStyles.insertByName( 'Footnote Keyword', style )
                style = document.createInstance( 'com.sun.star.style.CharacterStyle' )
                style.setPropertyValue('CharPosture', ITALIC_TEXT_POSTURE )
                characterStyles.insertByName( 'Footnote Quotation', style )
                style = document.createInstance( 'com.sun.star.style.CharacterStyle' )
                style.setPropertyValue('CharPosture', ITALIC_TEXT_POSTURE )
                characterStyles.insertByName( 'Footnote Alternate Translation', style )
                style = document.createInstance( 'com.sun.star.style.CharacterStyle' )
                style.setPropertyValue('CharPosture', ITALIC_TEXT_POSTURE )
                characterStyles.insertByName( 'Footnote Label', style )
                style = document.createInstance( 'com.sun.star.style.CharacterStyle' )
                characterStyles.insertByName( 'Footnote Paragraph', style )
                style = document.createInstance( 'com.sun.star.style.CharacterStyle' )
                characterStyles.insertByName( 'Footnote Verse Number', style )
                style = document.createInstance( 'com.sun.star.style.CharacterStyle' )
                characterStyles.insertByName( 'Footnote Text', style )
                style = document.createInstance( 'com.sun.star.style.CharacterStyle' )
                characterStyles.insertByName( 'Footnote Deuterocanonical', style )
                style = document.createInstance( 'com.sun.star.style.CharacterStyle' )
                style.setPropertyValue('CharPosture', ITALIC_TEXT_POSTURE )
                characterStyles.insertByName( 'Footnote Mark', style )

                # Cross references
                style = document.createInstance( 'com.sun.star.style.CharacterStyle' )
                style.setPropertyValue( 'CharWeight', 150 ) # bold
                style.setPropertyValue( 'CharBackColor', 0x0000FF00 ) # alpha/R/G/B = green
                characterStyles.insertByName( 'Cross Reference Origin', style )
                style = document.createInstance( 'com.sun.star.style.CharacterStyle' )
                style.setPropertyValue('CharPosture', ITALIC_TEXT_POSTURE )
                characterStyles.insertByName( 'Cross Reference Keyword', style )
                style = document.createInstance( 'com.sun.star.style.CharacterStyle' )
                style.setPropertyValue('CharPosture', ITALIC_TEXT_POSTURE )
                characterStyles.insertByName( 'Cross Reference Quotation', style )
                style = document.createInstance( 'com.sun.star.style.CharacterStyle' )
                characterStyles.insertByName( 'Cross Reference Target', style )
                style = document.createInstance( 'com.sun.star.style.CharacterStyle' )
                style.setParentStyle( 'Cross Reference Target' )
                characterStyles.insertByName( 'Cross Reference OT Target', style )
                style = document.createInstance( 'com.sun.star.style.CharacterStyle' )
                style.setParentStyle( 'Cross Reference Target' )
                characterStyles.insertByName( 'Cross Reference NT Target', style )
                style = document.createInstance( 'com.sun.star.style.CharacterStyle' )
                style.setParentStyle( 'Cross Reference Target' )
                characterStyles.insertByName( 'Cross Reference Deuterocanon Target', style )

                # "Hard" formatting
                style = document.createInstance( 'com.sun.star.style.CharacterStyle' )
                characterStyles.insertByName( 'Emphasis Text', style )
                style = document.createInstance( 'com.sun.star.style.CharacterStyle' )
                style.setPropertyValue( 'CharWeight', 150 ) # bold
                characterStyles.insertByName( 'Bold Text', style )
                style = document.createInstance( 'com.sun.star.style.CharacterStyle' )
                style.setPropertyValue('CharPosture', ITALIC_TEXT_POSTURE )
                characterStyles.insertByName( 'Italic Text', style )
                style = document.createInstance( 'com.sun.star.style.CharacterStyle' )
                style.setPropertyValue('CharWeight', 150) # bold
                style.setPropertyValue('CharPosture', ITALIC_TEXT_POSTURE )
                characterStyles.insertByName( 'Bold Italic Text', style )
                style = document.createInstance( 'com.sun.star.style.CharacterStyle' )
                characterStyles.insertByName( 'Small Caps Text', style )

            ## Setup PAGE STYLES
            #pageStyles = styleFamilies.getByName( 'PageStyles' )
            #defaultPageStyle = pageStyles.getByName( 'Default Style' )
            #defaultPageStyle.setPropertyValue( 'HeaderIsOn', True )
            #defaultPageStyle.setPropertyValue( 'FooterIsOn', True )

            #headerTextRight = rightPageStyle.getPropertyValue( 'HeaderTextRight' )
            #headerTextLeft = leftPageStyle.getPropertyValue( 'HeaderTextLeft' )
            #headerCursorRight = headerTextRight.createTextCursor()
            #headerCursorLeft = headerTextLeft.createTextCursor()
        # end of toODF.setupStyles


        def insertFormattedODFText( BBB, C, V, givenText, extras, document, textCursor, defaultCharacterStyleName ):
            """
            Format character codes within the text into ODF
            """
            #print( "insertFormattedODFText( {}, {}, {} )".format( repr(givenText), len(extras), ourGlobals.keys() ) )
            if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert givenText or extras

            def handleExtras( text, extras ):
                """
                Returns the MD text with footnotes and xrefs processed.
                It also accumulates MD in ourGlobals for the end notes.
                """
                def liveCV( CV ):
                    """
                    Given a CV text (in the same book), make it live
                        e.g., given 1:3 return #C1V3
                            given 17:4-9 return #C17V4
                            given 1:1-3:19 return #C1V1
                    """
                    #print( "formatODFVerseText.liveCV( {} )".format( repr(CV) ) )
                    if len(CV) < 3: return ''
                    if CV and CV[-1]==':': CV = CV[:-1]

                    result = 'C' + CV.strip().replace( ':', 'V')
                    for bridgeChar in ('-', '–', '—'): # hyphen, endash, emdash
                        ix = result.find( bridgeChar )
                        if ix != -1: result = result[:ix] # Remove verse bridges
                    #print( " returns", result )
                    if BibleOrgSysGlobals.debugFlag and (result.count('C')>1 or result.count('V')>1): halt
                    return '#' + result
                # end of insertFormattedODFText.liveCV


            def processNote( noteType, rawFootnoteContents, document, textCursor ):
                """
                Inserts the footnote or endnote into the ODF document.

                NOTE: The first parameter here already has the /f or (/fe) and /f* (or /fe*) removed.

                \\f + \\fr 1:20 \\ft Su ka kaluwasan te Nawumi ‘keupianan,’ piru ka kaluwasan te Mara ‘masakit se geyinawa.’\\f* (Backslashes are shown doubled here)
                """
                assert noteType in ('fn','en',)
                markerList = BibleOrgSysGlobals.loadedUSFMMarkers.getMarkerListFromText( rawFootnoteContents, includeInitialText=True )
                #print( "formatODFVerseText.processFootnote( {}, {} ) found {}".format( repr(rawFootnoteContents), ourGlobals, markerList ) )
                note = document.createInstance( "com.sun.star.text.Footnote" if noteType=='fn' else "com.sun.star.text.Endnote" )
                document.Text.insertTextContent( textCursor, note, False )
                noteCursor = note.Text.createTextCursor()
                noteCursor.setPropertyValue( 'ParaStyleName', "Bible Footnote" if noteType=='fn' else "Bible Endnote" )

                noteStyleDict = { 'fr':'Footnote Origin', 'fk':'Footnote Keyword', 'fq':'Footnote Quotation',
                                'fqa':'Footnote Alternate Translation', 'fl':'Footnote Label',
                                'fp':'Footnote Paragraph', 'fv':'Footnote Verse Number',
                                'ft':'Footnote Text', 'fdc':'Footnote Deuterocanonical',
                                'fm':'Footnote Mark' }

                caller = origin = originCV = fnText = fnTitle = '' # Probably no longer needed
                if markerList: # We found some internal footnote markers
                    for marker, ixBS, nextSignificantChar, fullMarkerText, context, ixEnd, txt in markerList:
                        if marker is None:
                            #if txt not in '-+': # just a caller
                            caller = txt
                        elif marker in noteStyleDict:
                            noteCursor.setPropertyValue( "CharStyleName", noteStyleDict[marker] )
                            note.insertString( noteCursor, txt,  False )
                        else:
                            logger.error( "formatODFVerseText.processNote didn't handle {} {}:{} {} marker: {}".format( BBB, C, V, noteType, marker ) )
                else: # no internal markers found
                    noteCursor.setPropertyValue( "CharStyleName", "Footnote Text" )
                    bits = rawFootnoteContents.split( ' ', 1 )
                    if len(bits)==2: # assume the caller is the first bit
                        caller = bits[0]
                        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert len(caller) == 1 # Normally a +
                        note.insertString( noteCursor, bits[1],  False )
                    else: # no idea really what the format was
                        note.insertString( noteCursor, rawFootnoteContents,  False )
            # end of insertFormattedODFText.processNote


            def processCrossReference( rawXRef, document, textCursor ):
                """
                Inserts the cross-reference into the ODF document as a footnote.

                NOTE: The parameter here already has the /x and /x* removed.

                \\x - \\xo 2:2: \\xt Lib 19:9-10; Diy 24:19.\\xt*\\x* (Backslashes are shown doubled here)
                """
                markerList = BibleOrgSysGlobals.loadedUSFMMarkers.getMarkerListFromText( rawXRef, includeInitialText=True )
                #print( "\nformatODFVerseText.processCrossReference( {}, {} ) gives {}".format( repr(rawXRef), "…", markerList ) )

                xrefNote = document.createInstance( "com.sun.star.text.Footnote" )
                document.Text.insertTextContent( textCursor, xrefNote, False )
                noteCursor = xrefNote.Text.createTextCursor()
                noteCursor.setPropertyValue( 'ParaStyleName', "Verse Cross Reference" )

                xrefStyleDict = { 'xo':'Cross Reference Origin', 'xk':'Cross Reference Keyword',
                                 'xq':'Cross Reference Quotation', 'xt':'Cross Reference Target',
                                 'xot':'Cross Reference OT Target', 'xnt':'Cross Reference NT Target',
                                 'xdc':'Cross Reference Deuterocanon Target' }

                caller = origin = originCV = xrefText = '' # Probably no longer needed
                if markerList:
                    for marker, ixBS, nextSignificantChar, fullMarkerText, context, ixEnd, txt in markerList:
                        if marker is None:
                            #if txt not in '-+': # just a caller
                            caller = txt
                        elif marker in xrefStyleDict:
                            noteCursor.setPropertyValue( "CharStyleName", xrefStyleDict[marker] )
                            xrefNote.insertString( noteCursor, txt,  False )
                        else:
                            logger.error( "formatODFVerseText.processCrossReference didn't handle {} {}:{} xref marker: {}".format( BBB, C, V, marker ) )
                else: # there's no USFM markers at all in the xref —  presumably a caller and then straight text
                    if rawXRef.startswith('+ ') or rawXRef.startswith('- '):
                        caller = rawXRef[0]
                        xrefText = rawXRef[2:].strip()
                    else: # don't really know what it is — assume it's all just text
                        xrefText = rawXRef.strip()
                    noteCursor.setPropertyValue( "CharStyleName", "Footnote Text" )
                    xrefNote.insertString( noteCursor, xrefText,  False )
            # end of insertFormattedODFText.processCrossReference


            def processFigure( extraText, document, textCursor ):
                """
                Inserts the figure into the ODF document.

                NOTE: The parameter here already has the /fig and /fig* removed.
                """
                logger.critical( "toODF: figure not handled yet at {} {}:{} {!r}".format( BBB, C, V, extraText ) )
                figureMD = ''
                #footnoteMD = '<a class="footnoteLinkSymbol" title="{}" href="#FNote{}">[fn]</a>' \
                                #.format( fnTitle, fnIndex )

                #endMD = '<p id="FNote{}" class="footnote">'.format( fnIndex )
                #if originCV: # This only handles CV separator of : so far
                    #endMD += '<a class="footnoteOrigin" title="Go back up to {} in the text" href="{}">{}</a> ' \
                                                        #.format( originCV, liveCV(originCV), origin )
                #endMD += '<span class="footnoteEntry">{}</span>'.format( fnText )
                #endMD += '</p>'

                ##print( "footnoteMD", BBB, footnoteMD )
                ##print( "endMD", endMD )
                #ourGlobals['footnoteMD'].append( endMD )
                ##if fnIndex > 2: halt
            # end of insertFormattedODFText.processFigure


            def handleTextSubsegment( textSegment ):
                """
                Insert a text segment, complete with the correct character styles if any.
                """
                #print( "BibleWriter.toODF.handleTextSubsegment( {} ) for {} {}:{}".format( repr(textSegment), BBB, C, V ) )
                markerList = BibleOrgSysGlobals.loadedUSFMMarkers.getMarkerListFromText( textSegment, includeInitialText=True )
                if markerList: # we found character formatting within the text
                    #print( BBB, C, V, "toODF.insertFormattedODFText: {} found {}".format( repr(textSegment), markerList ) )
                    for marker, ixBS, nextSignificantChar, fullMarkerText, context, ixEnd, txt in markerList:
                        #print( "loop", marker, ixBS, repr(nextSignificantChar), repr(fullMarkerText), context, ixEnd, repr(txt) )
                        if marker in charODFStyleDict and nextSignificantChar in (' ','+'): # it's an opening marker
                            #print( "  BibleWriter.toODF: 3dc1", BBB, C, V, charODFStyleDict[marker], repr(txt) )
                            textCursor.setPropertyValue( "CharStyleName", charODFStyleDict[marker] )
                            document.Text.insertString( textCursor, txt, 0 )
                        elif marker == 'k' and nextSignificantChar in (' ','+'):
                            #print( "  BibleWriter.toODF: 3dc2", BBB, C, V, repr(txt) )
                            textCursor.setPropertyValue( "CharStyleName", 'Main Entry Keyword' if BBB in ('GLS',) else 'Keyword Text' )
                            document.Text.insertString( textCursor, txt, 0 )
                        elif marker in charODFStyleDict and nextSignificantChar=='-': # it's a closing nesting marker
                            assertcontext
                            #print( "  BibleWriter.toODF: 3dc3", BBB, C, V, charODFStyleDict[marker], repr(txt) )
                            textCursor.setPropertyValue( "CharStyleName", charODFStyleDict[context[0]] )
                            document.Text.insertString( textCursor, txt, 0 )
                        elif marker is None or (marker=='no' and nextSignificantChar==' ') or not context:
                            # Normal text
                            #print( "  BibleWriter.toODF: 3dc4", BBB, C, V, defaultCharacterStyleName, repr(txt) )
                            textCursor.setPropertyValue( "CharStyleName", defaultCharacterStyleName )
                            document.Text.insertString( textCursor, txt, 0 )
                        elif marker in ('ca','va',) and nextSignificantChar in (' ','+'): # it's an opening marker
                            csn = 'Alternative Chapter Number' if marker=='ca' else 'Alternative Verse Number'
                            try: textCursor.setPropertyValue( "CharStyleName", csn )
                            except IllegalArgumentException:
                                logger.critical( "toODF: {!r} character style doesn't seem to exist".format( csn ) )
                            document.Text.insertString( textCursor, '('+txt+')', 0 )
                        elif marker in charODFStyleDict and not nextSignificantChar: # it's at the end of a line
                            assert not txt
                            logger.warning( "toODF: ignored blank {} field at end of line in {} {}:{}".format( marker, BBB, C, V ) )
                        else:
                            logger.critical( "toODF: {} lost text in {} field in {} {}:{} {!r}".format( self.abbreviation, marker, BBB, C, V, textSegment ) )
                            unhandledMarkers.add( "{} (char)".format( marker ) )
                            if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
                elif textSegment: # No character formatting here
                    #print( "BibleWriter.toODF: 3dc5", BBB, C, V, repr(textSegment) )
                    document.Text.insertString( textCursor, textSegment, 0 )
            # end of insertFormattedODFText.handleTextSubsegment

            def handleTextSegment( textSegment ):
                """
                Insert a text segment, complete with the correct character styles if any.
                """
                #print( "BibleWriter.toODF.handleTextSegment( {} ) for {} {}:{}".format( repr(textSegment), BBB, C, V ) )
                if '//' in textSegment: # indicates a manual new line marker
                    sx = 0
                    ix = textSegment.find( '//' )
                    while ix != -1:
                        handleTextSubsegment( textSegment[sx:ix] )
                        document.Text.insertControlCharacter( textCursor, ODF_LINE_BREAK, False )
                        lx = ix + 2
                        ix = textSegment.find( '//', lx )
                    handleTextSubsegment( textSegment[lx:] )
                else: # no manual line breaks
                    handleTextSubsegment( textSegment )
            # end of insertFormattedODFText.handleTextSegment

            # insertFormattedODFText main code
            if extras:
                haveUsefulExtras = False
                for extra in extras: # find any footnotes and cross-references
                    extraType, extraIndex, extraText, cleanExtraText = extra
                    # We don't care about str and vp fields here
                    if extraType in ('fn','en','xr','fig',): haveUsefulExtras = True; break
                if haveUsefulExtras:
                    lastIndex = 0
                    for extra in extras: # find any footnotes and cross-references
                        extraType, extraIndex, extraText, cleanExtraText = extra
                        handleTextSegment( givenText[lastIndex:extraIndex] )
                        if extraType in ('fn','en',): processNote( extraType, extraText, document, textCursor )
                        elif extraType == 'xr': processCrossReference( extraText, document, textCursor )
                        elif extraType == 'fig': processFigure( extraText, document, textCursor )
                        elif extraType == 'str': pass # don't know how to encode this yet
                        elif extraType == 'sem': pass # don't know how to encode this yet
                        elif extraType == 'vp': pass # it's already been converted to a newline field
                        else: halt
                        lastIndex = extraIndex
                    handleTextSegment( givenText[lastIndex:] )
                else: # no useful extras like footnotes, etc.
                    handleTextSegment( givenText )
            else: # no extras at all like footnotes, etc.
                handleTextSegment( givenText )
        # end of toODF.insertFormattedODFText


        def createODFBook( bookNum, BBB, bookObject ):
            """
            Returns a True/False result
            """
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Creating ODF file for {}…".format( BBB ) )
            elif BibleOrgSysGlobals.verbosityLevel > 1: # Very basic progress bar
                print( "{}-{}…".format( BBB, datetime.now().strftime('%H:%M') ), end='', flush=True )
            internalBibleBookData = bookObject._processedLines

            # Create the blank document
            filename = "{:02}-{}_BOS-BibleWriter.odt".format( bookNum, BBB )
            filepath = os.path.join( os.getcwd(), outputFolderpath, BibleOrgSysGlobals.makeSafeFilename( filename ) )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "  " + _("Creating {!r}…").format( filename ) )
            document = frameDesktop.loadComponentFromURL( sourceURL, "_blank", 0, () )
            try: documentText = document.Text
            except AttributeError: # no Text? = no blank/outline ODF text available
                logger.critical( "toODF: Cannot access blank ODF document for {}".format( BBB ) )
                return False # can't do anything here
            initialTextCursor = documentText.createTextCursor()
            textCursor = initialTextCursor

            styleFamilies = document.StyleFamilies
            setupStyles( styleFamilies )

            #pageStyles = styleFamilies.getByName( "PageStyles" )
            #defaultPageStyle = pageStyles.getByName( 'Default Style' )
            #headerText = defaultPageStyle.getPropertyValue( "HeaderText" )
            #headerCursor = headerText.createTextCursor()
            runningHeaderField = None
            if startWithTemplate:
                try: runningHeaderField = document.TextFieldMasters.getByName( "com.sun.star.text.FieldMaster.User.BookHeader" )
                except IllegalArgumentException: logger.critical( "toODF: Can't set up running header user text field" )
            else: logger.critical( "toODF: Don't know how to set up running header user text field programmatically yet" )

            firstEverParagraphFlag = True
            def insertODFParagraph( BBB, C, V, paragraphStyleName, text, extras, document, textCursor, defaultCharacterStyleName ):
                """
                Given some text and the paragraph stylename (and the default character stylename)
                    start a new paragraph and insert the text.
                """
                nonlocal firstEverParagraphFlag
                #print( "toODF.insertODFParagraph( {} {}:{}, {}, {} …)".format( BBB, C, V, repr(paragraphStyleName), repr(text) ) )
                if not firstEverParagraphFlag: # Don't want a blank paragraph at the start of the document
                    document.Text.insertControlCharacter( textCursor, ODF_PARAGRAPH_BREAK, False )
                try: textCursor.setPropertyValue( 'ParaStyleName', paragraphStyleName )
                except IllegalArgumentException:
                    logger.critical( "toODF: {!r} paragraph style doesn't seem to exist".format( paragraphStyleName ) )
                if adjText or extras:
                    insertFormattedODFText( BBB, C, V, text, extras, document, textCursor, defaultCharacterStyleName )
                firstEverParagraphFlag = False
            # end of insertODFParagraph


            # Main code for createODFBook
            try: headerField = bookObject.longTOCName
            except AttributeError: headerField = bookObject.assumedBookName
            startingNewParagraphFlag = True
            inTextParagraph = False
            lastMarker = gotVP = None
            C, V = '-1', '-1' # So first/id line starts at -1:0
            for entry in internalBibleBookData:
                marker, adjText, extras = entry.getMarker(), entry.getAdjustedText(), entry.getExtras()
                #print( "toODF:", bookNum, BBB, C, V, marker, repr(adjText) )
                if '¬' in marker or marker in BOS_ADDED_NESTING_MARKERS or marker=='v=':
                    continue # Just ignore added markers — not needed here
                if marker in USFM_PRECHAPTER_MARKERS:
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
                        assert C=='-1' or marker=='rem' or marker.startswith('mte')
                    V = str( int(V) + 1 )

                if marker in OFTEN_IGNORED_USFM_HEADER_MARKERS or marker in ('ie',): # Just ignore these lines
                    ignoredMarkers.add( marker )
                elif marker == 'c':
                    document.storeAsURL( 'file://{}'.format( filepath ), () ) # Save a copy of the file at each chapter mark
                    if C == '-1' and runningHeaderField:
                        runningHeaderField.setPropertyValue( 'Content', headerField )
                    C, V = adjText, '0'
                    if C == '1': # It's the beginning of the actual Bible text — make a new double-column section
                        #document.storeAsURL( 'file://{}'.format( filepath ), () ) # Save a preliminary copy of the file

                        if not firstEverParagraphFlag: # leave a space between the introduction and the chapter text
                            documentText.insertControlCharacter( textCursor, ODF_PARAGRAPH_BREAK, False )
                            textCursor.setPropertyValue( 'ParaStyleName', 'Blank Line Paragraph' )
                            documentText.insertControlCharacter( textCursor, ODF_PARAGRAPH_BREAK, False )

                        # Create a new text section and insert it into the document
                        chapterSection = document.createInstance( 'com.sun.star.text.TextSection' )
                        documentText.insertTextContent( initialTextCursor, chapterSection, False )

                        # Create a column object with two columns
                        columns = document.createInstance( 'com.sun.star.text.TextColumns' )
                        columns.setColumnCount( 2 )
                        columns.setPropertyValue( 'AutomaticDistance', 300 ) # Not sure of the unit here

                        # Insert columns into the text section
                        chapterSection.setPropertyValue( 'TextColumns', columns )
                        #chapterSection.setPropertyValue( "DontBalanceTextColumns", True )

                        anchor = chapterSection.getAnchor()
                        columnCursor = documentText.createTextCursorByRange( anchor )

                        textCursor = columnCursor # So that future inserts go in here
                        startingNewParagraphFlag = firstEverParagraphFlag = True
                    # Put in our running header — WHY DOESN'T THIS WORK PROPERLY IN LIBREOFFICE???
                    #runningHeaderField.setPropertyValue( "Content", "{} {}".format( headerField, C ) )
                elif marker == 'c#':
                    if not inTextParagraph: # Not all translations have paragraph markers
                        documentText.insertControlCharacter( textCursor, ODF_PARAGRAPH_BREAK, False )
                        textCursor.setPropertyValue( 'ParaStyleName', "Prose Paragraph" )
                        inTextParagraph = startingNewParagraphFlag = True
                    textCursor.setPropertyValue( "CharStyleName", "Chapter Number" )
                    documentText.insertString( textCursor, C, False )
                    textCursor.setPropertyValue( "CharStyleName", "Chapter Number Postspace" )
                    documentText.insertString( textCursor, " ", False )
                    textCursor.setPropertyValue( "CharStyleName", "Verse Text" )
                elif marker == 'vp#': # This precedes a v field and has the verse number to be printed
                    gotVP = adjText # Just remember it for now
                elif marker == 'v':
                    V = adjText
                    if gotVP: # this is the verse number to be published
                        adjText = gotVP
                        gotVP = None
                    if not inTextParagraph: # Not all translations have paragraph markers
                    #if lastMarker == 's1': # hack for OEB which has some empty s fields immediately followed by v fields
                        documentText.insertControlCharacter( textCursor, ODF_PARAGRAPH_BREAK, False )
                        textCursor.setPropertyValue( 'ParaStyleName', 'Prose Paragraph' )
                        inTextParagraph = startingNewParagraphFlag = True
                    if V != '1':
                        if not startingNewParagraphFlag:
                            textCursor.setPropertyValue( 'CharStyleName', 'Verse Number Prespace' )
                            documentText.insertString( textCursor, ' ', False )
                        textCursor.setPropertyValue( 'CharStyleName', 'Verse Number' )
                        documentText.insertString( textCursor, adjText, False )
                        textCursor.setPropertyValue( 'CharStyleName', 'Verse Number Postspace' )
                        documentText.insertString( textCursor, ' ', False )
                        textCursor.setPropertyValue( 'CharStyleName', 'Verse Text' )
                        startingNewParagraphFlag = False

                elif marker in titleODFStyleDict:
                    styleName = titleODFStyleDict[marker]
                    insertODFParagraph( BBB, C, V, styleName, adjText, extras, document, textCursor, 'Default Style' )
                elif marker in ('ms1','ms2','ms3','ms4',):
                    styleName = 'Major Section Heading {}'.format( marker[-1] )
                    insertODFParagraph( BBB, C, V, styleName, adjText, extras, document, textCursor, 'Major Section Heading' )
                    inTextParagraph = False
                elif marker in ipODFStyleDict:
                    styleName = ipODFStyleDict[marker]
                    insertODFParagraph( BBB, C, V, styleName, adjText, extras, document, textCursor, 'Default Style' )
                elif marker in ('s1','s2','s3','s4', 'is1','is2','is3','is4', 'qa'):
                    if adjText or extras: #OEB has blank s fields
                        if marker=='qa': styleName == 'Acrostic Heading'
                        else:
                            styleName = 'Introduction ' if marker[0]=='i' else ''
                            styleName += 'Section Heading {}'.format( marker[-1] )
                        insertODFParagraph( BBB, C, V, styleName, adjText, extras, document, textCursor, 'Section Heading' )
                    inTextParagraph = False
                elif marker in ('r','sr','mr',):
                    if marker == 'r': styleName = 'Section CrossReference'
                    elif marker == 'sr': styleName = 'Section Reference Range'
                    elif marker == 'mr': styleName = 'Major Section Reference Range'
                    insertODFParagraph( BBB, C, V, styleName, adjText, extras, document, textCursor, 'Default Style' )
                    inTextParagraph = False
                elif marker in miscODFStyleDict: # things like d, sp, cl that have text
                    styleName = miscODFStyleDict[marker]
                    insertODFParagraph( BBB, C, V, styleName, adjText, extras, document, textCursor, 'Default Style' )
                    inTextParagraph = False
                elif marker in pqODFStyleDict: # things like p, q1 that don't have text
                    startingNewParagraphFlag = True
                    styleName = pqODFStyleDict[marker]
                    insertODFParagraph( BBB, C, V, styleName, adjText, extras, document, textCursor, 'Default Style' )
                    inTextParagraph = True
                elif marker in ('li1','li2','li3','li4', 'ili1','ili2','ili3','ili4',):
                    styleName = "Introduction " if marker[0]=='i' else ""
                    styleName += "List Item {}".format( marker[-1] )
                    insertODFParagraph( BBB, C, V, styleName, adjText, extras, document, textCursor, 'Default Style' )
                elif marker in ('v~','p~',):
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert inTextParagraph
                    if adjText or extras:
                        insertFormattedODFText( BBB, C, V, adjText, extras, document, textCursor, 'Default Style' )
                    startingNewParagraphFlag = False
                elif marker in ( 'b', 'ib', ):
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not adjText and not extras
                    documentText.insertControlCharacter( textCursor, ODF_PARAGRAPH_BREAK, False )
                    textCursor.setPropertyValue( 'ParaStyleName', 'Blank Line Paragraph' if marker=='b' else 'Introduction Blank Line Paragraph' )
                elif marker == 'nb': # no-break with previous paragraph — I don't think we have to do anything here
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert not adjText and not extras
                    ignoredMarkers.add( marker )
                elif marker in ('cp',): # We can safely ignore these markers for the ODF export
                    ignoredMarkers.add( marker )
                else:
                    if adjText:
                        logger.error( "toODF: {} lost text in {} field in {} {}:{} {!r}".format( self.abbreviation, marker, BBB, C, V, adjText ) )
                        #if BibleOrgSysGlobals.debugFlag: halt
                    if extras:
                        logger.error( "toODF: {} lost extras in {} field in {} {}:{}".format( self.abbreviation, marker, BBB, C, V ) )
                        #if BibleOrgSysGlobals.debugFlag: halt
                    unhandledMarkers.add( marker )
                lastMarker = marker

            # Save the created document
            document.storeAsURL( 'file://{}'.format( filepath ), () )
            document.dispose() # Close the document (even though it might be a headless server anyway)
            if debuggingThisModule: print( "Finished {}".format( BBB ) )
            return True
        # end of toODF.createODFBook


        # Main code (continued) for toODF()
        # Create and save the ODF files
        createCount = 0
        for j, (BBB,bookObject) in enumerate( self.books.items() ):
            #if createODFBook( j, BBB, bookObject ):
                #createCount += 1

            if restartLOSMForEachBook:
                if isServiceManagerRunning(): killLibreOfficeServiceManager() # Seems safer to always do this
                #assert not isServiceManagerRunning() # could be running in another user
                startLibreOfficeServiceManager()
                weStartedLibreOffice = True

                # Set-up LibreOffice
                localContext = uno.getComponentContext()
                urlResolver = localContext.ServiceManager.createInstanceWithContext( "com.sun.star.bridge.UnoUrlResolver", localContext )
                componentContext = urlResolver.resolve( "uno:socket,host=localhost,port={};urp;StarOffice.ComponentContext".format( DEFAULT_OPENOFFICE_PORT ) )
                serviceManager = componentContext.ServiceManager
                frameDesktop = serviceManager.createInstanceWithContext( "com.sun.star.frame.Desktop", componentContext )
                #model = frameDesktop.getCurrentComponent()

                # Locate our empty template file (with all the styles there already) that we'll start from
                templateFilepath = os.path.join( os.getcwd(), defaultControlFolderpath, "BibleBook.ott" )
                sourceURL = "file://{}".format( templateFilepath ) if startWithTemplate else "private:factory/swriter"

            if BibleOrgSysGlobals.alreadyMultiprocessing or 'win' in sys.platform: # SIGALRM doesn't work
                try:
                    if createODFBook( j, BBB, bookObject ):
                        createCount += 1
                except Exception as err:
                    print("BibleWriter.doAllExports.toODF {} Unexpected error:".format( BBB ), sys.exc_info()[0], err)
                    killLibreOfficeServiceManager()
                    logger.error( "BibleWriter.doAllExports.toODF: Oops, {} failed!".format( BBB ) )
                    break
            else: # *nix system hopefully
                if 0: # Signal doesn't time out when LOSM locks up :-(
                    timeoutSeconds = max( 20, len(bookObject._processedLines)//40 ) # But depends on footnotes, etc. as well
                    print( "Timeout for {} is {}s".format( BBB, timeoutSeconds ) )
                    class ODFTimeoutException( Exception ): pass
                    def TimeoutHandler( signum, frame ):
                        logger.critical( _("createODFBook( {} ) went too long!").format( BBB ) )
                        raise ODFTimeoutException( "ODF writer timed out on {}".format( BBB ) )
                    # end of TimeoutHandler
                    signal.signal( signal.SIGALRM, TimeoutHandler )
                    signal.alarm( timeoutSeconds )
                    try:
                        if createODFBook( j, BBB, bookObject ):
                            createCount += 1
                        signal.alarm( 0 ) # Disable timeout
                    except ODFTimeoutException as err:
                        print("BibleWriter.doAllExports.toODF {} Timeout error:".format( BBB ), sys.exc_info()[0], err)
                        logger.critical( "BibleWriter.doAllExports.toODF: Oops, {} timed out. Aborting!".format( BBB ) )
                        killLibreOfficeServiceManager() # Shut down the locked-up  process
                        if not restartLOSMForEachBook: break # No real point in continuing with locked-up system
                else: # try something else # NOTE: Linux-only code!!!
                    # NOTE: This shell script must be findable in the current working directory
                    timeoutFilepath = './BOS_LOSM_Timeout.sh'
                    if os.path.exists( timeoutFilepath ):
                        proc = subprocess.Popen( [timeoutFilepath] ) # Does a 150s timeout then kills
                        try:
                            if createODFBook( j, BBB, bookObject ):
                                createCount += 1
                            proc.terminate() # Will hopefully terminate the timeout before the shell script kills the LO ServiceManager
                        except KeyboardInterrupt:
                            killLibreOfficeServiceManager() # Shut down the locked-up  process
                            raise KeyboardInterrupt
                        except Exception as err: # BibleWriter.DisposedException (where does BibleWriter.com.sun.star.lang.DisposedException come from???)
                            print("BibleWriter.doAllExports.toODF {} Timeout error:".format( BBB ), sys.exc_info()[0], err)
                            logger.critical( "BibleWriter.doAllExports.toODF: Oops, {} timed out. Aborting!".format( BBB ) )
                            killLibreOfficeServiceManager() # Shut down the locked-up  process
                            if not restartLOSMForEachBook: break # No real point in continuing with locked-up system
                    else:
                        if createODFBook( j, BBB, bookObject ):
                            createCount += 1

        if weStartedLibreOffice and not BibleOrgSysGlobals.debugFlag: # Now kill our LibreOffice server
            killLibreOfficeServiceManager()

        if ignoredMarkers:
            logger.info( "toODF: Ignored markers were {}".format( ignoredMarkers ) )
            if BibleOrgSysGlobals.verbosityLevel > 2:
                print( "  " + _("WARNING: Ignored toODF markers were {}").format( ignoredMarkers ) )
        if unhandledMarkers:
            logger.warning( "toODF: Unhandled markers were {}".format( unhandledMarkers ) )
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print( "  " + _("WARNING: Unhandled toODF markers were {}").format( unhandledMarkers ) )

        # Now create a zipped collection
        if createCount > 0:
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Zipping ODF files…" )
            zf = zipfile.ZipFile( os.path.join( outputFolderpath, 'AllODFFiles.zip' ), 'w', compression=zipfile.ZIP_DEFLATED )
            for filename in os.listdir( outputFolderpath ):
                if not filename.endswith( '.zip' ):
                    filepath = os.path.join( outputFolderpath, filename )
                    zf.write( filepath, filename ) # Save in the archive without the path
            zf.close()

            if BibleOrgSysGlobals.verbosityLevel > 0 and BibleOrgSysGlobals.maxProcesses > 1:
                print( "  BibleWriter.toODF finished successfully ({} files) at {}".format( createCount, datetime.now().strftime('%H:%M') ) )
            return True
        # else
        logger.critical( "BibleWriter.toODF produced no files!" )
        return False
    # end of BibleWriter.toODF



    def toTeX( self, outputFolderpath:Optional[str]=None ) -> bool:
        """
        Write the pseudo USFM out into a TeX (typeset) format.
            The format varies, depending on whether or not there are paragraph markers in the text.
        """
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Running BibleWriter:toTeX… {}".format( datetime.now().strftime('%H:%M') ) )
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag: assert self.books

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolderpath: outputFolderpath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_TeX_Export/' )
        if not os.access( outputFolderpath, os.F_OK ): os.makedirs( outputFolderpath ) # Make the empty folder if there wasn't already one there

        ignoredMarkers, unhandledMarkers = set(), set()

        # First determine our format
        #verseByVerse = True

        # Copy auxilliary XeTeX files to our output folder
        for filename in ( "lettrine.sty", ):
            filepath = os.path.join( defaultControlFolderpath, filename )
            try: shutil.copy( filepath, outputFolderpath )
            except FileNotFoundError: logger.warning( "Unable to find TeX control file: {}".format( filepath ) )
        ipMarkerTranslate = { 'ip':'IP','ipi':'IPI', 'im':'IM','imi':'IMI', 'ipq':'IPQ','imq':'IMQ','ipr':'IPR',
                            'iq1':'IQ','iq2':'IQQ','iq3':'IQQQ','iq4':'IQQQQ',
                            'iot':'IOT', 'io1':'IO', 'io2':'IOO', 'io3':'IOOO', 'io4':'IOOOO',
                            'iex':'IEX', }
        ipListMarkerTranslate = { 'ili1':'ILI','ili2':'ILII','ili3':'ILIII','ili4':'ILIIII', }
        listMarkerTranslate = { 'li1':'LI','li2':'LII','li3':'LIII','li4':'LIIII', }
        pMarkerTranslate = { 'p':'P','pc':'PC','pr':'PR', 'm':'M','mi':'MI',
                            'pmo':'PMO','pmc':'PMC','pmr':'PMR',
                            'pi1':'PI','pi2':'PII','pi3':'PIII','pi4':'PIIII', 'ph1':'PH','ph2':'PHH','ph3':'PHHH','ph4':'PHHHH',
                            'q1':'Q','q2':'QQ','q3':'QQQ','q4':'QQQQ',
                            'cls':'CLS', }
        cMarkerTranslate = { 'bk':'BK', 'add':'ADD', 'nd':'ND', 'wj':'WJ', 'sig':'SIG',
                            'bdit':'BDIT', 'it':'IT', 'bd':'BD', 'em':'EM', 'sc':'SC',
                            'ior':'IOR', 'k':'KW', }
        imtMarkerTranslate = { 'imt1':'BibleIntroTitle', 'imt2':'BibleIntroTitleTwo', 'imt3':'BibleIntroTitleThree', 'imt4':'BibleIntroTitleFour',
                               'imte1':'BibleIntroMainEndTitle', 'imte2':'BibleIntroEndTitleTwo', 'imte3':'BibleIntroEndTitleThree', 'imte4':'BibleIntroEndTitleFour', }
        mtMarkerTranslate = { 'mt1':'BibleMainTitle', 'mt2':'BibleTitleTwo', 'mt3':'BibleTitleThree', 'mt4':'BibleTitleFour',
                              'mte1':'BibleMainEndTitle', 'mte2':'BibleEndTitleTwo', 'mte3':'BibleEndTitleThree', 'mte4':'BibleEndTitleFour', }
        sMarkerTranslate = { 'ms1':'BibleMainSectionHeading', 'ms2':'BibleMainSectionHeadingTwo', 'ms3':'BibleMainSectionHeadingThree', 'ms4':'BibleMainSectionHeadingFour',
                             's1':'BibleSectionHeading', 's2':'BibleSectionHeadingTwo', 's3':'BibleSectionHeadingThree', 's4':'BibleSectionHeadingFour',
                             'is1':'BibleIntroSectionHeading', 'is2':'BibleIntroSectionHeadingTwo', 'is3':'BibleIntroSectionHeadingThree', 'is4':'BibleIntroSectionHeadingFour', }

        def writeTeXHeader( writer ):
            """
            Write the XeTeX header data — the file can be processed with xelatex
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
            nonlocal unhandledMarkers

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

            # Handle regular character formatting — this will cause TeX to fail if closing markers are not matched
            for charMarker in ALL_CHAR_MARKERS:
                fullCharMarker = '\\' + charMarker + ' '
                if fullCharMarker in text:
                    endCharMarker = '\\' + charMarker + '*'
                    if charMarker in cMarkerTranslate:
                        text = text.replace( fullCharMarker, '~^~BibleCharacterStyle'+cMarkerTranslate[charMarker]+'{' ) \
                                .replace( endCharMarker, '}' )
                    else:
                        logger.warning( "toTeX: Don't know how to encode {!r} marker".format( charMarker ) )
                        unhandledMarkers.add( charMarker )
                        text = text.replace( fullCharMarker, '' ).replace( endCharMarker, '' )

            if '\\' in text: # Catch any left-overs
                if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
                    print( "toTeX.texText: unprocessed code in {!r} from {!r}".format( text, givenText ) )
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
            return text.replace( '~^~', '\\' )
        # end of toTeX:texText


        def makePDFs( BBB, texFilepath, timeout ):
            """
            Call xelatex to make the Bible PDF file(s) from the .tex file.
            """
            assert texFilepath.endswith( '.tex' )
            mainFilepath = texFilepath[:-4] # Remove the .tex bit

            # Work through the various class files for different styles of Bible layouts
            for filenamePart in ( 'Bible1','Bible2', ):
                filepath = os.path.join( defaultControlFolderpath, filenamePart+'.cls' )
                try:
                    shutil.copy( filepath, outputFolderpath ) # Copy it under its own name
                    shutil.copy( filepath, os.path.join( outputFolderpath, 'Bible.cls' ) ) # Copy it also under the generic name
                except FileNotFoundError: logger.warning( "Unable to find TeX control file: {}".format( filepath ) )

                # Now run xelatex (TeX -> PDF)
                parameters = ['/usr/bin/timeout', timeout, '/usr/bin/xelatex', '-interaction=batchmode', os.path.abspath(texFilepath) ]
                #print( "makeIndividualPDF (xelatex) parameters", parameters )
                os.chdir( outputFolderpath ) # So the paths for the Bible.cls file are correct
                myProcess = subprocess.Popen( parameters, stdout=subprocess.PIPE, stderr=subprocess.PIPE )
                programOutputBytes, programErrorOutputBytes = myProcess.communicate()
                os.chdir( cwdSave ) # Restore the path again
                if myProcess.returncode == 124: # it timed out
                    programErrorOutputBytes += "xelatex {}: Timed out after {}".format( BBB, timeout ).encode( 'utf-8' )
                # Process the output
                if programOutputBytes:
                    programOutputString = programOutputBytes.decode( encoding='utf-8', errors='replace' )
                    #programOutputString = programOutputString.replace( baseFolder + ('' if baseFolder[-1]=='/' else '/'), '' ) # Remove long file paths to make it easier for the user to read
                    #with open( os.path.join( outputFolderpath, 'ScriptOutput.txt" ), 'wt', encoding='utf-8' ) as myFile: myFile.write( programOutputString )
                    #print( "pOS", programOutputString )
                if programErrorOutputBytes:
                    programErrorOutputString = programErrorOutputBytes.decode( encoding='utf-8', errors='replace' )
                    #with open( os.path.join( outputFolderpath, 'ScriptErrorOutput.txt" ), 'wt', encoding='utf-8' ) as myFile: myFile.write( programErrorOutputString )
                    if BibleOrgSysGlobals.debugFlag: print( "pEOS", programErrorOutputString )

                # Rename our PDF (and the log file) according to the style
                try: os.replace( mainFilepath+'.log', mainFilepath+'.'+filenamePart+'.log' )
                except FileNotFoundError: pass # That's fine
                try: os.replace( mainFilepath+'.pdf', mainFilepath+'.'+filenamePart+'.pdf' )
                except FileNotFoundError: pass # That's fine
        # end of toTeX.makePDFs


        # Write the plain text XeTeX file
        cwdSave = os.getcwd() # Save the current working directory before changing (below) to the output directory
        allFilename = "All-BOS-BibleWriter.tex"
        allFilepath = os.path.join( outputFolderpath, BibleOrgSysGlobals.makeSafeFilename( allFilename ) )
        if BibleOrgSysGlobals.verbosityLevel > 2: print( '  toTeX: ' + _("Writing {!r}…").format( allFilepath ) )
        with open( allFilepath, 'wt', encoding='utf-8' ) as allFile:
            writeTeXHeader( allFile )
            for j, (BBB,bookObject) in enumerate( self.books.items() ):
                haveTitle = haveIntro = False
                filename = "{:02}-{}_BOS-BibleWriter.tex".format( j, BBB )
                filepath = os.path.join( outputFolderpath, BibleOrgSysGlobals.makeSafeFilename( filename ) )
                if BibleOrgSysGlobals.verbosityLevel > 2: print( '  toTeX: ' + _("Writing {!r}…").format( filepath ) )
                with open( filepath, 'wt', encoding='utf-8' ) as bookFile:
                    writeTeXHeader( bookFile )
                    allFile.write( "\n\\BibleBook{{{}}}\n".format( bookObject.getAssumedBookNames()[0] ) )
                    bookFile.write( "\n\\BibleBook{{{}}}\n".format( bookObject.getAssumedBookNames()[0] ) )
                    bookFile.write( "\n\\BibleBookTableOfContents\n".format( bookObject.getAssumedBookNames()[0] ) )
                    gotVP = None
                    C, V = '-1', '-1' # So first/id line starts at -1:0
                    for entry in bookObject._processedLines:
                        marker, text = entry.getMarker(), entry.getFullText()
                        if '¬' in marker or marker in BOS_ADDED_NESTING_MARKERS or marker=='v=':
                            continue # Just ignore added markers — not needed here
                        if marker in USFM_PRECHAPTER_MARKERS:
                            if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
                                assert C=='-1' or marker=='rem' or marker.startswith('mte')
                            V = str( int(V) + 1 )

                        if marker in OFTEN_IGNORED_USFM_HEADER_MARKERS or marker in ('ie',): # Just ignore these lines
                            ignoredMarkers.add( marker )
                        elif marker in mtMarkerTranslate:
                            if not haveTitle:
                                allFile.write( "\n\\BibleTitlePage\n" )
                                bookFile.write( "\n\\BibleTitlePage\n" )
                                haveTitle = True
                            allFile.write( "\\{}{{{}}}\n".format( mtMarkerTranslate[marker], texText(text) ) )
                            bookFile.write( "\\{}{{{}}}\n".format( mtMarkerTranslate[marker], texText(text) ) )
                        elif marker in imtMarkerTranslate:
                            if not haveIntro:
                                allFile.write( "\n\\BibleIntro\n" )
                                bookFile.write( "\n\\BibleIntro\n" )
                                haveIntro = True
                            allFile.write( "\\{}{{{}}}\n".format( imtMarkerTranslate[marker], texText(text) ) )
                            bookFile.write( "\\{}{{{}}}\n".format( imtMarkerTranslate[marker], texText(text) ) )
                        elif marker in ipMarkerTranslate:
                            if not haveIntro:
                                allFile.write( "\n\\BibleIntro\n" )
                                bookFile.write( "\n\\BibleIntro\n" )
                                haveIntro = True
                            allFile.write( "\\BibleParagraphStyle{}\n".format( ipMarkerTranslate[marker] ) )
                            bookFile.write( "\\BibleParagraphStyle{}\n".format( ipMarkerTranslate[marker] ) )
                            allFile.write( "{}\n".format( texText(text) ) )
                            bookFile.write( "{}\n".format( texText(text) ) )
                        elif marker in ipListMarkerTranslate:
                            if not haveIntro:
                                allFile.write( "\n\\BibleIntro\n" )
                                bookFile.write( "\n\\BibleIntro\n" )
                                haveIntro = True
                            allFile.write( "\\BibleParagraphStyle{}\n".format( ipListMarkerTranslate[marker] ) )
                            bookFile.write( "\\BibleParagraphStyle{}\n".format( ipListMarkerTranslate[marker] ) )
                            allFile.write( "{}\n".format( texText(text) ) )
                            bookFile.write( "{}\n".format( texText(text) ) )

                        elif marker=='c':
                            C, V = text, '0'
                            if text == '1': # Assume chapter 1 is the start of the actual Bible text
                                allFile.write( "\n\\BibleText\n" )
                                bookFile.write( "\n\\BibleText\n" )
                        elif marker=='c#':
                            allFile.write( "\\chapterNumber{{{}}}".format( texText(text) ) ) # no NL
                            bookFile.write( "\\chapterNumber{{{}}}".format( texText(text) ) ) # no NL
                        elif marker == 'vp#': # This precedes a v field and has the verse number to be printed
                            gotVP = text # Just remember it for now
                        elif marker=='v':
                            V = text
                            if gotVP: # this is the verse number to be published
                                text = gotVP
                                gotVP = None
                            if text != '1': # Don't write verse 1 number
                                allFile.write( "\\verseNumber{{{}}}".format( texText(text) ) ) # no NL
                                bookFile.write( "\\verseNumber{{{}}}".format( texText(text) ) ) # no NL

                        elif marker in sMarkerTranslate:
                            allFile.write( "\n\\{}{{{}}}\n".format( sMarkerTranslate[marker], texText(text) ) )
                            bookFile.write( "\n\\{}{{{}}}\n".format( sMarkerTranslate[marker], texText(text) ) )
                            bookFile.write( "\n\\addcontentsline{{toc}}{{toc}}{{{}}}\n".format( texText(text) ) )
                        elif marker=='r':
                            allFile.write( "\\BibleSectionCrossReference{{{}}}\n".format( texText(text) ) )
                            bookFile.write( "\\BibleSectionCrossReference{{{}}}\n".format( texText(text) ) )
                        elif marker in pMarkerTranslate:
                            assert not text
                            allFile.write( "\\BibleParagraphStyle{}\n".format( pMarkerTranslate[marker] ) )
                            bookFile.write( "\\BibleParagraphStyle{}\n".format( pMarkerTranslate[marker] ) )
                        elif marker in listMarkerTranslate:
                            assert not text
                            allFile.write( "\\BibleParagraphStyle{}\n".format( listMarkerTranslate[marker] ) )
                            bookFile.write( "\\BibleParagraphStyle{}\n".format( listMarkerTranslate[marker] ) )
                        elif marker in ('v~','p~',):
                            allFile.write( "{}\n".format( texText(text) ) )
                            bookFile.write( "{}\n".format( texText(text) ) )
                        else:
                            if text:
                                logger.error( "toTeX: {} lost text in {} field in {} {}:{} {!r}".format( self.abbreviation, marker, BBB, C, V, text ) )
                                #if BibleOrgSysGlobals.debugFlag: halt
                            unhandledMarkers.add( marker )
                        #if extras and marker not in ('v~','p~',): logger.critical( "toTeX: extras not handled for {} at {} {}:{}".format( marker, BBB, C, V ) )
                    allFile.write( "\\BibleBookEnd\n" )
                    bookFile.write( "\\BibleBookEnd\n" )
                    bookFile.write( "\\end{document}\n" )
                makePDFs( BBB, filepath, '30s' )
            allFile.write( "\\end{document}\n" )
        makePDFs( 'All', allFilepath, '3m' )

        if ignoredMarkers:
            logger.info( "toTeX: Ignored markers were {}".format( ignoredMarkers ) )
            if BibleOrgSysGlobals.verbosityLevel > 2:
                print( "  " + _("WARNING: Ignored toTeX markers were {}").format( ignoredMarkers ) )
        if unhandledMarkers:
            logger.warning( "toTeX: Unhandled markers were {}".format( unhandledMarkers ) )
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print( "  " + _("WARNING: Unhandled toTeX markers were {}").format( unhandledMarkers ) )

        # Now create a zipped collection
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Zipping PDF files…" )
        zf = zipfile.ZipFile( os.path.join( outputFolderpath, 'AllBible1PDFFiles.zip' ), 'w', compression=zipfile.ZIP_DEFLATED )
        for filename in os.listdir( outputFolderpath ):
            if filename.endswith( '.Bible1.pdf' ):
                filepath = os.path.join( outputFolderpath, filename )
                zf.write( filepath, filename ) # Save in the archive without the path
        zf.close()
        zf = zipfile.ZipFile( os.path.join( outputFolderpath, 'AllBible2PDFFiles.zip' ), 'w', compression=zipfile.ZIP_DEFLATED )
        for filename in os.listdir( outputFolderpath ):
            if filename.endswith( '.Bible2.pdf' ):
                filepath = os.path.join( outputFolderpath, filename )
                zf.write( filepath, filename ) # Save in the archive without the path
        zf.close()

        if BibleOrgSysGlobals.verbosityLevel > 0 and BibleOrgSysGlobals.maxProcesses > 1:
            print( "  BibleWriter.toTeX finished successfully at {}".format( datetime.now().strftime('%H:%M') ) )
        return True
    # end of BibleWriter.toTeX



    def doExportHelper( self, ff ):
        """
        Only used in doAllExports for multiprocessing.

        Parameter ff is a 2-tuple containing the function to run, and the folder parameter to pass

        TODO: Could be a function rather than a method (self is not used).
        """
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "BibleWriter.doExportHelper( {} )".format( ff ) )
        function, folder = ff
        if function is None: return None # Some exports are not always requested

        try: result = function( folder )
        except Exception as err: # Got to catch and report the exceptions here
            print( "BibleWriter.doExportHelper: Unexpected error in {} using {}:".format( function, folder ), sys.exc_info()[0], err)
            result = False
        return result
    # end of BibleWriter.doExportHelper


    def doAllExports( self, givenOutputFolderName=None, wantPhotoBible=None, wantODFs=None, wantPDFs=None ) -> Dict[str,bool]:
        """
        If the output folder is specified, it is expected that it's already created.
        Otherwise a new subfolder is created in the current folder.

        The three very processor intensive exports require explicit inclusion.

        Returns a dictionary of result flags.
        """
        allWord = _("all") if wantPhotoBible and wantODFs and wantPDFs else _("most")
        if BibleOrgSysGlobals.verbosityLevel > 1:
            print( "BibleWriterV{}.doAllExports: ".format(PROGRAM_VERSION) + _("Exporting {} ({}) to {} formats… {}").format( self.name, self.objectTypeString, allWord, datetime.now().strftime('%H:%M') ) )

        if not self.projectName: self.projectName = self.getAName() # Seems no post-processing was done???

        if givenOutputFolderName == None:
            givenOutputFolderName = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH
            if not os.access( givenOutputFolderName, os.F_OK ):
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "BibleWriter.doAllExports: " + _("creating {!r} output folder").format( givenOutputFolderName ) )
                os.makedirs( givenOutputFolderName ) # Make the empty folder if there wasn't already one there
        if debuggingThisModule or BibleOrgSysGlobals.debugFlag:
            assert givenOutputFolderName and isinstance( givenOutputFolderName, (str,Path) )
        if not os.access( givenOutputFolderName, os.W_OK ): # Then our output folder is not writeable!
            logger.critical( "BibleWriter.doAllExports: " + _("Given {!r} folder is unwritable" ).format( givenOutputFolderName ) )
            return False

        # Define our various output folders
        pickleOutputFolder = os.path.join( givenOutputFolderName, 'BOS_Bible_Object_Pickle/' )
        pickledBibleOutputFolder = os.path.join( givenOutputFolderName, 'BOS_PickledBible_Export/' )
        listOutputFolder = os.path.join( givenOutputFolderName, 'BOS_Lists/' )
        BCVOutputFolder = os.path.join( givenOutputFolderName, 'BOS_BCV_Export/' )
        pseudoUSFMOutputFolder = os.path.join( givenOutputFolderName, 'BOS_PseudoUSFM_Export/' )
        USFM2OutputFolder = os.path.join( givenOutputFolderName, 'BOS_USFM2_' + ('Reexport/' if self.objectTypeString in ('USFM2','PTX7') else 'Export/' ) )
        USFM3OutputFolder = os.path.join( givenOutputFolderName, 'BOS_USFM3_' + ('Reexport/' if self.objectTypeString=='USFM3' else 'Export/' ) )
        ESFMOutputFolder = os.path.join( givenOutputFolderName, 'BOS_ESFM_' + ('Reexport/' if self.objectTypeString=='ESFM' else 'Export/' ) )
        textOutputFolder = os.path.join( givenOutputFolderName, 'BOS_PlainText_' + ('Reexport/' if self.objectTypeString=='Text' else 'Export/' ) )
        VPLOutputFolder = os.path.join( givenOutputFolderName, 'BOS_VersePerLine_' + ('Reexport/' if self.objectTypeString=='VPL' else 'Export/' ) )
        markdownOutputFolder = os.path.join( givenOutputFolderName, 'BOS_Markdown_Export/' )
        #D43OutputFolder = os.path.join( givenOutputFolderName, 'BOS_Door43_' + ('Reexport/' if self.objectTypeString=='Door43' else 'Export/' ) )
        htmlOutputFolder = os.path.join( givenOutputFolderName, 'BOS_HTML5_Export/' )
        BDOutputFolder = os.path.join( givenOutputFolderName, 'BOS_BibleDoor_' + 'Export/' )
        EWBOutputFolder = os.path.join( givenOutputFolderName, 'BOS_EasyWorshipBible_' + 'Export/' )
        USX2OutputFolder = os.path.join( givenOutputFolderName, 'BOS_USX2_' + ('Reexport/' if self.objectTypeString=='USX' else 'Export/' ) )
        USX3OutputFolder = os.path.join( givenOutputFolderName, 'BOS_USX3_' + ('Reexport/' if self.objectTypeString=='USX3' else 'Export/' ) )
        USFXOutputFolder = os.path.join( givenOutputFolderName, 'BOS_USFX_' + ('Reexport/' if self.objectTypeString=='USFX' else 'Export/' ) )
        OSISOutputFolder = os.path.join( givenOutputFolderName, 'BOS_OSIS_' + ('Reexport/' if self.objectTypeString=='OSIS' else 'Export/' ) )
        zefOutputFolder = os.path.join( givenOutputFolderName, 'BOS_Zefania_' + ('Reexport/' if self.objectTypeString=='Zefania' else 'Export/' ) )
        hagOutputFolder = os.path.join( givenOutputFolderName, 'BOS_Haggai_' + ('Reexport/' if self.objectTypeString=='Haggia' else 'Export/' ) )
        OSOutputFolder = os.path.join( givenOutputFolderName, 'BOS_OpenSong_' + ('Reexport/' if self.objectTypeString=='OpenSong' else 'Export/' ) )
        swOutputFolder = os.path.join( givenOutputFolderName, 'BOS_Sword_' + ('Reexport/' if self.objectTypeString in ('Sword','CrosswireSword') else 'Export/' ) )
        tWOutputFolder = os.path.join( givenOutputFolderName, 'BOS_theWord_' + ('Reexport/' if self.objectTypeString=='theWord' else 'Export/' ) )
        MySwOutputFolder = os.path.join( givenOutputFolderName, 'BOS_MySword_' + ('Reexport/' if self.objectTypeString=='MySword' else 'Export/' ) )
        ESwOutputFolder = os.path.join( givenOutputFolderName, 'BOS_e-Sword_' + ('Reexport/' if self.objectTypeString=='e-Sword-Bible' else 'Export/' ) )
        MyBOutputFolder = os.path.join( givenOutputFolderName, 'BOS_MyBible_' + ('Reexport/' if self.objectTypeString=='MyBible' else 'Export/' ) )
        SwSOutputFolder = os.path.join( givenOutputFolderName, 'BOS_SwordSearcher_Export/' )
        DrOutputFolder = os.path.join( givenOutputFolderName, 'BOS_DrupalBible_' + ('Reexport/' if self.objectTypeString=='DrupalBible' else 'Export/' ) )
        photoOutputFolder = os.path.join( givenOutputFolderName, 'BOS_PhotoBible_Export/' )
        ODFOutputFolder = os.path.join( givenOutputFolderName, 'BOS_ODF_Export/' )
        TeXOutputFolder = os.path.join( givenOutputFolderName, 'BOS_TeX_Export/' )

        if not wantPhotoBible:
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "BibleWriter.doAllExports: " + _("Skipping PhotoBible export") )
            PhotoBibleExportResult = None
        if not wantODFs:
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "BibleWriter.doAllExports: " + _("Skipping ODF export") )
            ODFExportResult = None
        if not wantPDFs:
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "BibleWriter.doAllExports: " + _("Skipping TeX/PDF export") )
            TeXExportResult = None

        # Pickle this Bible object
        # NOTE: This must be done before self.__setupWriter is called
        #       because the BRL object has a recursive pointer to self and the pickle fails
        if BibleOrgSysGlobals.debugFlag: pickleResult = self.toPickleObject( pickleOutputFolder ) # halts if fails
        else:
            try: pickleResult = self.toPickleObject( pickleOutputFolder )
            except (IOError,TypeError):
                pickleResult = False
                print( "BibleWriter.doAllExports: pickle( {} ) failed.".format( pickleOutputFolder ) )
        if not self.doneSetupGeneric: self.__setupWriter()
        if 'discoveryResults' not in self.__dict__: self.discover()

        if debuggingThisModule or BibleOrgSysGlobals.debugFlag:
            # no try/except calls so it halts on errors rather than continuing
            pickledBibleOutputResult = self.toPickledBible( pickledBibleOutputFolder )
            listOutputResult = self.makeLists( listOutputFolder )
            BCVExportResult = self.toBOSBCV( BCVOutputFolder )
            pseudoUSFMExportResult = self.toPseudoUSFM( pseudoUSFMOutputFolder )
            USFM2ExportResult = self.toUSFM2( USFM2OutputFolder )
            USFM3ExportResult = self.toUSFM3( USFM3OutputFolder )
            ESFMExportResult = self.toESFM( ESFMOutputFolder )
            textExportResult = self.toText( textOutputFolder )
            VPLExportResult = self.toVPL( VPLOutputFolder )
            markdownExportResult = self.toMarkdown( markdownOutputFolder )
            #D43ExportResult = self.toDoor43( D43OutputFolder )
            htmlExportResult = self.toHTML5( htmlOutputFolder )
            BDExportResult = self.toBibleDoor( BDOutputFolder )
            EWBExportResult = self.toEasyWorshipBible( EWBOutputFolder )
            USX2ExportResult = self.toUSX2XML( USX2OutputFolder )
            USX3ExportResult = self.toUSX3XML( USX3OutputFolder )
            USFXExportResult = self.toUSFXXML( USFXOutputFolder )
            OSISExportResult = self.toOSISXML( OSISOutputFolder )
            ZefExportResult = self.toZefaniaXML( zefOutputFolder )
            HagExportResult = self.toHaggaiXML( hagOutputFolder )
            OSExportResult = self.toOpenSongXML( OSOutputFolder )
            swExportResult = self.toSwordModule( swOutputFolder )
            tWExportResult = self.totheWord( tWOutputFolder )
            MySwExportResult = self.toMySword( MySwOutputFolder )
            ESwExportResult = self.toESword( ESwOutputFolder )
            MyBExportResult = self.toMyBible( MyBOutputFolder )
            SwSExportResult = self.toSwordSearcher( SwSOutputFolder )
            DrExportResult = self.toDrupalBible( DrOutputFolder )
            if wantPhotoBible: PhotoBibleExportResult = self.toPhotoBible( photoOutputFolder )
            if wantODFs: ODFExportResult = self.toODF( ODFOutputFolder )
            if wantPDFs: TeXExportResult = self.toTeX( TeXOutputFolder ) # Put this last since it's slowest

        # NOTE: We can't pickle sqlite3.Cursor objects so can not use multiprocessing here for e-Sword Bibles or commentaries
        elif self.objectTypeString not in ('CrosswireSword','e-Sword-Bible','e-Sword-Commentary','MyBible') \
        and BibleOrgSysGlobals.maxProcesses > 1 \
        and not BibleOrgSysGlobals.alreadyMultiprocessing: # Process all the exports with different threads
            # We move the three longest processes to the top here,
            #   so they start first to help us get finished quicker on multiCPU systems.
            self.__outputProcesses = [self.toPhotoBible if wantPhotoBible else None,
                                    #self.toODF if wantODFs else None,
                                    self.toTeX if wantPDFs else None,
                                    self.toPickledBible, self.makeLists,
                                    self.toBOSBCV, self.toPseudoUSFM,
                                    self.toUSFM2, self.toUSFM3, self.toESFM, self.toText, self.toVPL,
                                    self.toMarkdown, #self.toDoor43,
                                    self.toHTML5,
                                    self.toBibleDoor, self.toEasyWorshipBible,
                                    self.toUSX2XML, self.toUSX3XML, self.toUSFXXML, self.toOSISXML,
                                    self.toZefaniaXML, self.toHaggaiXML, self.toOpenSongXML,
                                    self.toSwordModule, self.totheWord, self.toMySword, self.toESword, self.toMyBible,
                                    self.toSwordSearcher, self.toDrupalBible, ]
            self.__outputFolders = [photoOutputFolder, #ODFOutputFolder,
                                    TeXOutputFolder,
                                    pickledBibleOutputFolder, listOutputFolder,
                                    BCVOutputFolder, pseudoUSFMOutputFolder,
                                    USFM2OutputFolder, USFM3OutputFolder, ESFMOutputFolder,
                                    textOutputFolder, VPLOutputFolder,
                                    markdownOutputFolder, #D43OutputFolder,
                                    htmlOutputFolder, BDOutputFolder, EWBOutputFolder,
                                    USX2OutputFolder, USX3OutputFolder, USFXOutputFolder, OSISOutputFolder,
                                    zefOutputFolder, hagOutputFolder, OSOutputFolder,
                                    swOutputFolder, tWOutputFolder, MySwOutputFolder, ESwOutputFolder, MyBOutputFolder,
                                    SwSOutputFolder, DrOutputFolder, ]
            assert len(self.__outputFolders) == len(self.__outputProcesses)
            if BibleOrgSysGlobals.verbosityLevel > 0:
                print( "BibleWriter.doAllExports: Running {} exports on {} CPUs".format( len(self.__outputProcesses), BibleOrgSysGlobals.maxProcesses ) )
                if BibleOrgSysGlobals.verbosityLevel > 1:
                    print( "  NOTE: Outputs (including error and warning messages) from various exports may be interspersed." )
            BibleOrgSysGlobals.alreadyMultiprocessing = True
            # With no timeout safeguard
            #with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                #results = pool.map( self.doExportHelper, zip(self.__outputProcesses,self.__outputFolders) ) # have the pool do our loads
                #if BibleOrgSysGlobals.verbosityLevel > 0: print( "BibleWriter.doAllExports: Got {} results".format( len(results) ) )
                #assert len(results) == len(self.__outputFolders)
                #PhotoBibleExportResult, ODFExportResult, TeXExportResult, \
                    #listOutputResult, BCVExportResult, pseudoUSFMExportResult, \
                    #USFM2ExportResult, ESFMExportResult, textExportResult, \
                    #markdownExportResult, D43ExportResult, htmlExportResult, BDExportResult, EWBExportResult, \
                    #USX2ExportResult, USX3ExportResult, USFXExportResult, OSISExportResult, ZefExportResult, HagExportResult, OSExportResult, \
                    #swExportResult, tWExportResult, MySwExportResult, ESwExportResult, MyBExportResult, SwSExportResult, DrExportResult, \
                        #= results
            # With safety timeout — more complex
            # timeoutFactors are average seconds per book
            timeoutFactor = 6 # Quicker exports — 2 minutes for 68 books — factor of 5 would allow almost 6 minutes
            if wantPhotoBible: timeoutFactor +=  40 # 30 minutes for 68 books (Feb2018) = 27
            #if wantODFs: timeoutFactor = max( timeoutFactor, 100 ) # Over a minute for longer books with LO v5.4 on my system
            if wantPDFs: timeoutFactor += 12 # seems about 2 minutes for 68 books
            processorFactor = 1.0 # Make bigger for a slower CPU, or can make smaller for a fast one
            timeoutSeconds = max( 60, int(timeoutFactor*len(self.books)*processorFactor) ) # (was 1200s=20m but failed for projects with > 66 books)
            pool = multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses )
            asyncResultObject = pool.map_async( self.doExportHelper, zip(self.__outputProcesses,self.__outputFolders) ) # have the pool do our loads
            #print( "async results1 are", asyncResultObject )
            pool.close() # Can't add more workers to the pool now
            asyncResultObject.wait( timeoutSeconds ) # Wait for every worker to finish
            # Once the timeout has finished we can try to get the results
            if asyncResultObject.ready():
                results = asyncResultObject.get()
            else:
                print( "BibleWriter.doAllExports: Got a timeout after {} seconds".format( timeoutSeconds ) )
                pool.terminate() # No results available now
                #pool.join()
                #results = asyncResultObject.get() # Should work now
                result = timeoutSeconds # Will count as True yet be different
                results = [result if wantPhotoBible else None, # Just have to assume everything worked
                                    #result if wantODFs else None,
                                    result if wantPDFs else None,
                                    result, result, result, result, result, result, result, result, result, result, result, result,
                                    result, result, result, result, result, result, result, result, result, result, result, ]
            #print( "async results2 are", results )
            BibleOrgSysGlobals.alreadyMultiprocessing = False
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "BibleWriter.doAllExports: Multiprocessing got {} results".format( len(results) ) )
            assert len(results) == len(self.__outputFolders)
            ( PhotoBibleExportResult, #ODFExportResult,
                TeXExportResult,
                pickledBibleOutputResult, listOutputResult, BCVExportResult, pseudoUSFMExportResult,
                USFM2ExportResult, USFM3ExportResult, ESFMExportResult, textExportResult, VPLExportResult,
                markdownExportResult, #D43ExportResult,
                htmlExportResult, BDExportResult, EWBExportResult,
                USX2ExportResult, USX3ExportResult, USFXExportResult, OSISExportResult, ZefExportResult, HagExportResult, OSExportResult,
                swExportResult, tWExportResult, MySwExportResult, ESwExportResult, MyBExportResult, SwSExportResult,
                DrExportResult ) = results
            if wantODFs: # Do this one separately (coz it's so much longer, plus often locks up)
                # Timeout is now done per book inside the toODF function
                #if BibleOrgSysGlobals.alreadyMultiprocessing or 'win' in sys.platform: # SIGALRM doesn't work
                try: ODFExportResult = self.toODF( ODFOutputFolder )
                except Exception as err:
                    ODFExportResult = False
                    print("BibleWriter.doAllExports.toODF Unexpected error:", sys.exc_info()[0], err)
                    killLibreOfficeServiceManager()
                    logger.error( "BibleWriter.doAllExports.toODF: Oops, failed!" )
                #else: # *nix system hopefully
                    #timeoutSeconds = int(60*len(self.books)*processorFactor) # (was 1200s=20m but failed for projects with > 66 books)
                    #def TimeoutHandler( signum, frame ):
                        #logger.critical( _("A task went too long!") )
                        #raise Exception( "Timed out" )

                    #signal.signal( signal.SIGALRM, TimeoutHandler )
                    #signal.alarm( timeoutSeconds )
                    #try: ODFExportResult = self.toODF( ODFOutputFolder )
                    #except Exception as err:
                        #ODFExportResult = False
                        #print("BibleWriter.doAllExports.toODF Unexpected error:", sys.exc_info()[0], err)
                        #killLibreOfficeServiceManager()
                        #logger.error( "BibleWriter.doAllExports.toODF: Oops, failed!" )

        else: # Just single threaded and not debugging
            try: pickledBibleOutputResult = self.toPickledBible( pickledBibleOutputFolder )
            except Exception as err:
                pickledBibleOutputResult = False
                print("BibleWriter.doAllExports.toPickledBible Unexpected error:", sys.exc_info()[0], err)
                logger.error( "BibleWriter.doAllExports.toPickledBible: Oops, failed!" )
            try: listOutputResult = self.makeLists( listOutputFolder )
            except Exception as err:
                listOutputResult = False
                print("BibleWriter.doAllExports.makeLists Unexpected error:", sys.exc_info()[0], err)
                logger.error( "BibleWriter.doAllExports.makeLists: Oops, failed!" )
            try: BCVExportResult = self.toBOSBCV( BCVOutputFolder )
            except Exception as err:
                BCVExportResult = False
                print("BibleWriter.doAllExports.toBOSBCV Unexpected error:", sys.exc_info()[0], err)
                logger.error( "BibleWriter.doAllExports.toBOSBCV: Oops, failed!" )
            try: pseudoUSFMExportResult = self.toPseudoUSFM( pseudoUSFMOutputFolder )
            except Exception as err:
                pseudoUSFMExportResult = False
                print("BibleWriter.doAllExports.toPseudoUSFM Unexpected error:", sys.exc_info()[0], err)
                logger.error( "BibleWriter.doAllExports.toPseudoUSFM: Oops, failed!" )
            try: USFM2ExportResult = self.toUSFM2( USFM2OutputFolder )
            except Exception as err:
                USFM2ExportResult = False
                print("BibleWriter.doAllExports.toUSFM2 Unexpected error:", sys.exc_info()[0], err)
                logger.error( "BibleWriter.doAllExports.toUSFM2: Oops, failed!" )
            try: USFM3ExportResult = self.toUSFM3( USFM3OutputFolder )
            except Exception as err:
                USFM3ExportResult = False
                print("BibleWriter.doAllExports.toUSFM3 Unexpected error:", sys.exc_info()[0], err)
                logger.error( "BibleWriter.doAllExports.toUSFM3: Oops, failed!" )
            try: ESFMExportResult = self.toESFM( ESFMOutputFolder )
            except Exception as err:
                ESFMExportResult = False
                print("BibleWriter.doAllExports.toESFM Unexpected error:", sys.exc_info()[0], err)
                logger.error( "BibleWriter.doAllExports.toESFM: Oops, failed!" )
            try: textExportResult = self.toText( textOutputFolder )
            except Exception as err:
                textExportResult = False
                print("BibleWriter.doAllExports.toText Unexpected error:", sys.exc_info()[0], err)
                logger.error( "BibleWriter.doAllExports.toText: Oops, failed!" )
            try: VPLExportResult = self.toVPL( VPLOutputFolder )
            except Exception as err:
                VPLExportResult = False
                print("BibleWriter.doAllExports.toVPL Unexpected error:", sys.exc_info()[0], err)
                logger.error( "BibleWriter.doAllExports.toVPL: Oops, failed!" )
            try: markdownExportResult = self.toMarkdown( markdownOutputFolder )
            except Exception as err:
                markdownExportResult = False
                print("BibleWriter.doAllExports.toMarkdown Unexpected error:", sys.exc_info()[0], err)
                logger.error( "BibleWriter.doAllExports.toMarkdown: Oops, failed!" )
            #try: D43ExportResult = self.toDoor43( D43OutputFolder )
            #except Exception as err:
                #D43ExportResult = False
                #print("BibleWriter.doAllExports.toDoor43 Unexpected error:", sys.exc_info()[0], err)
                #logger.error( "BibleWriter.doAllExports.toDoor43: Oops, failed!" )
            try: htmlExportResult = self.toHTML5( htmlOutputFolder )
            except Exception as err:
                htmlExportResult = False
                print("BibleWriter.doAllExports.toHTML5 Unexpected error:", sys.exc_info()[0], err)
                logger.error( "BibleWriter.doAllExports.toHTML5: Oops, failed!" )
            try: BDExportResult = self.toBibleDoor( BDOutputFolder )
            except Exception as err:
                BDExportResult = False
                print("BibleWriter.doAllExports.toBibleDoor Unexpected error:", sys.exc_info()[0], err)
                logger.error( "BibleWriter.doAllExports.toBibleDoor: Oops, failed!" )
            try: EWBExportResult = self.toEasyWorshipBible( EWBOutputFolder )
            except Exception as err:
                EWBExportResult = False
                print("BibleWriter.doAllExports.toEasyWorshipBible Unexpected error:", sys.exc_info()[0], err)
                logger.error( "BibleWriter.doAllExports.toEasyWorshipBible: Oops, failed!" )
            try: USX2ExportResult = self.toUSX2XML( USX2OutputFolder )
            except Exception as err:
                USX2ExportResult = False
                print("BibleWriter.doAllExports.toUSX2XML Unexpected error:", sys.exc_info()[0], err)
                logger.error( "BibleWriter.doAllExports.toUSX2XML: Oops, failed!" )
            try: USX3ExportResult = self.toUSX3XML( USX3OutputFolder )
            except Exception as err:
                USX3ExportResult = False
                print("BibleWriter.doAllExports.toUSX3XML Unexpected error:", sys.exc_info()[0], err)
                logger.error( "BibleWriter.doAllExports.toUSX3XML: Oops, failed!" )
            try: USFXExportResult = self.toUSFXXML( USFXOutputFolder )
            except Exception as err:
                USFXExportResult = False
                print("BibleWriter.doAllExports.toUSFXXML Unexpected error:", sys.exc_info()[0], err)
                logger.error( "BibleWriter.doAllExports.toUSFXXML: Oops, failed!" )
            try: OSISExportResult = self.toOSISXML( OSISOutputFolder )
            except Exception as err:
                OSISExportResult = False
                print("BibleWriter.doAllExports.toOSISXML Unexpected error:", sys.exc_info()[0], err)
                logger.error( "BibleWriter.doAllExports.toOSISXML: Oops, failed!" )
            try: ZefExportResult = self.toZefaniaXML( zefOutputFolder )
            except Exception as err:
                ZefExportResult = False
                print("BibleWriter.doAllExports.toZefaniaXML Unexpected error:", sys.exc_info()[0], err)
                logger.error( "BibleWriter.doAllExports.toZefaniaXML: Oops, failed!" )
            try: HagExportResult = self.toHaggaiXML( hagOutputFolder )
            except Exception as err:
                HagExportResult = False
                print("BibleWriter.doAllExports.toHaggaiXML Unexpected error:", sys.exc_info()[0], err)
                logger.error( "BibleWriter.doAllExports.toHaggaiXML: Oops, failed!" )
            try: OSExportResult = self.toOpenSongXML( OSOutputFolder )
            except Exception as err:
                OSExportResult = False
                print("BibleWriter.doAllExports.toOpenSongXML Unexpected error:", sys.exc_info()[0], err)
                logger.error( "BibleWriter.doAllExports.toOpenSongXML: Oops, failed!" )
            try: swExportResult = self.toSwordModule( swOutputFolder )
            except Exception as err:
                swExportResult = False
                print("BibleWriter.doAllExports.toSwordModule Unexpected error:", sys.exc_info()[0], err)
                logger.error( "BibleWriter.doAllExports.toSwordModule: Oops, failed!" )
            try: tWExportResult = self.totheWord( tWOutputFolder )
            except Exception as err:
                tWExportResult = False
                print("BibleWriter.doAllExports.totheWord Unexpected error:", sys.exc_info()[0], err)
                logger.error( "BibleWriter.doAllExports.totheWord: Oops, failed!" )
            try: MySwExportResult = self.toMySword( MySwOutputFolder )
            except Exception as err:
                MySwExportResult = False
                print("BibleWriter.doAllExports.toMySword Unexpected error:", sys.exc_info()[0], err)
                logger.error( "BibleWriter.doAllExports.toMySword: Oops, failed!" )
            try: ESwExportResult = self.toESword( ESwOutputFolder )
            except Exception as err:
                ESwExportResult = False
                print("BibleWriter.doAllExports.toESword Unexpected error:", sys.exc_info()[0], err)
                logger.error( "BibleWriter.doAllExports.toESword: Oops, failed!" )
            try: MyBExportResult = self.toMyBible( MyBOutputFolder )
            except Exception as err:
                MyBExportResult = False
                print("BibleWriter.doAllExports.toMyBible Unexpected error:", sys.exc_info()[0], err)
                logger.error( "BibleWriter.doAllExports.toMyBible: Oops, failed!" )
            try: SwSExportResult = self.toSwordSearcher( SwSOutputFolder )
            except Exception as err:
                SwSExportResult = False
                print("BibleWriter.doAllExports.toSwordSearcher Unexpected error:", sys.exc_info()[0], err)
                logger.error( "BibleWriter.doAllExports.toSwordSearcher: Oops, failed!" )
            try: DrExportResult = self.toDrupalBible( DrOutputFolder )
            except Exception as err:
                DrExportResult = False
                print("BibleWriter.doAllExports.toDrupalBible Unexpected error:", sys.exc_info()[0], err)
                logger.error( "BibleWriter.doAllExports.toDrupalBible: Oops, failed!" )
            if wantPhotoBible:
                try: PhotoBibleExportResult = self.toPhotoBible( photoOutputFolder )
                except Exception as err:
                    PhotoBibleExportResult = False
                    print("BibleWriter.doAllExports.toPhotoBible Unexpected error:", sys.exc_info()[0], err)
                    logger.error( "BibleWriter.doAllExports.toPhotoBible: Oops, failed!" )
            if wantODFs:
                try: ODFExportResult = self.toODF( ODFOutputFolder )
                except Exception as err:
                    ODFExportResult = False
                    print("BibleWriter.doAllExports.toODF Unexpected error:", sys.exc_info()[0], err)
                    killLibreOfficeServiceManager()
                    logger.error( "BibleWriter.doAllExports.toODF: Oops, failed!" )
            if wantPDFs: # Do TeX export last because it's slowest
                try: TeXExportResult = self.toTeX( TeXOutputFolder )
                except Exception as err:
                    TeXExportResult = False
                    print("BibleWriter.doAllExports.toTeX Unexpected error:", sys.exc_info()[0], err)
                    logger.error( "BibleWriter.doAllExports.toTeX: Oops, failed!" )

        if BibleOrgSysGlobals.verbosityLevel > 1:
            finishString = "BibleWriter.doAllExports finished:  Pck={}  Lst={}  BCV={} PsUSFM={} USFM2={} USFM3={} ESFM={} Tx={} VPL={}  md={}  " \
                            "HTML={} BD={} EWB={}  USX2={} USX3={}  USFX={} OSIS={}  Zef={} Hag={} OS={}  Sw={}  " \
                            "tW={} MySw={} eSw={} MyB={}  SwS={} Dr={}  PB={} ODF={} TeX={} {}" \
                .format( pickleResult, listOutputResult, BCVExportResult,
                    pseudoUSFMExportResult, USFM2ExportResult, USFM3ExportResult, ESFMExportResult,
                    textExportResult, VPLExportResult,
                    markdownExportResult, #D43ExportResult,
                    htmlExportResult,
                    BDExportResult, EWBExportResult,
                    USX2ExportResult, USX3ExportResult, USFXExportResult, OSISExportResult,
                    ZefExportResult, HagExportResult, OSExportResult,
                    swExportResult, tWExportResult, MySwExportResult, ESwExportResult, MyBExportResult,
                    SwSExportResult, DrExportResult,
                    PhotoBibleExportResult, ODFExportResult, TeXExportResult,
                    datetime.now().strftime('%H:%M') )
            trueCount  = finishString.count( 'True' )
            falseCount = finishString.count( 'False' )
            noneCount  = finishString.count( 'None' )

            #if pickleResult and listOutputResult and BCVExportResult \
            #and pseudoUSFMExportResult and USFM2ExportResult and ESFMExportResult and textExportResult \
            #and VPLExportResult and markdownExportResult and D43ExportResult and htmlExportResult \
            #and BDExportResult and EWBExportResult \
            #and USX2ExportResult and USX3ExportResult and USFXExportResult and OSISExportResult \
            #and ZefExportResult and HagExportResult and OSExportResult \
            #and swExportResult and tWExportResult and MySwExportResult and ESwExportResult and MyBExportResult \
            #and SwSExportResult and DrExportResult \
            #and (PhotoBibleExportResult or not wantPhotoBible) and (ODFExportResult or not wantODFs) and (TeXExportResult or not wantPDFs):
            if falseCount == 0:
                print( "BibleWriter.doAllExports finished all requested (which was {}/30) exports successfully!".format( trueCount ) )
            else:
                print( "{} ({} True, {} False, {} None)".format( finishString, trueCount, falseCount, noneCount ) )
        return { 'Pickle':pickleResult, 'listOutput':listOutputResult, 'BCVOutput':BCVExportResult,
                'pseudoUSFMExport':pseudoUSFMExportResult, 'USFM2Export':USFM2ExportResult, 'USFM3Export':USFM3ExportResult, 'ESFMExport':ESFMExportResult,
                'textExport':textExportResult, 'VPLExport':VPLExportResult,
                'markdownExport':markdownExportResult, #'D43Export':D43ExportResult,
                'htmlExport':htmlExportResult,
                'BibleDoorExport':BDExportResult, 'EasyWorshipBibleExport':EWBExportResult,
                'USX2Export':USX2ExportResult, 'USX3Export':USX3ExportResult, 'USFXExport':USFXExportResult, 'OSISExport':OSISExportResult,
                'ZefExport':ZefExportResult, 'HagExport':HagExportResult, 'OSExport':OSExportResult,
                'swExport':swExportResult,
                'tWExport':tWExportResult, 'MySwExport':MySwExportResult, 'ESwExport':ESwExportResult, 'MyBExport':MyBExportResult,
                'SwSExport':SwSExportResult, 'DrExport':DrExportResult,
                'PhotoBibleExport':PhotoBibleExportResult, 'ODFExport':ODFExportResult, 'TeXExport':TeXExportResult, }
    # end of BibleWriter.doAllExports
# end of class BibleWriter



def demo() -> None:
    """
    Demonstrate reading and processing some Bible databases.
    """
    from BibleOrgSys.Formats.USFMBible import USFMBible
    from BibleOrgSys.InputOutput.USFMFilenames import USFMFilenames

    if BibleOrgSysGlobals.verbosityLevel > 0: print( programNameVersion )
    BiblesFolderpath = BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Bibles/' )

    # Since this is only designed to be a virtual base class, it can't actually do much at all
    BW = BibleWriter()
    BW.objectNameString = 'Dummy test Bible Writer object'
    if BibleOrgSysGlobals.verbosityLevel > 0: print( BW )


    if 0: # Test reading and writing a (shortish) USFM Bible (with ALL exports so it's SLOW)
        testData = ( # name, abbreviation, folder for USFM files
                ("USFM2-AllMarkers", 'USFM2-All', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFM2AllMarkersProject/') ),
                ("USFM3-AllMarkers", 'USFM3-All', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFM3AllMarkersProject/') ),
                ("UEP", 'utf-8', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMErrorProject/') ),
                ("OEB", 'OEB', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFM-OEB/') ),
                ("OSISTest1", 'OSIS1', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'OSISTest1/') ),
                ) # You can put your USFM test folder here

        for j, (name, abbrev, testFolder) in enumerate( testData ):
            if BibleOrgSysGlobals.verbosityLevel > 0: print( f"\nBibleWriter A{j+1}/…" )
            if os.access( testFolder, os.R_OK ):
                UB = USFMBible( testFolder, name, abbrev )
                UB.load()
                if BibleOrgSysGlobals.verbosityLevel > 0: print( ' ', UB )
                if BibleOrgSysGlobals.strictCheckingFlag: UB.check()
                if UB.books:
                    #result = UB.toBibleDoor(); print( f"{result[0]} {result[1]!r}\n{result[2]}" ); halt
                    doaResults = UB.doAllExports( wantPhotoBible=True, wantODFs=True, wantPDFs=True )
                    if BibleOrgSysGlobals.strictCheckingFlag: # Now compare the original and the exported USFM files
                        outputFolderpath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_USFM2_Reexport/' )
                        fN = USFMFilenames( testFolder )
                        folderContents1 = os.listdir( testFolder ) # Originals
                        folderContents2 = os.listdir( outputFolderpath ) # Derived
                        if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nComparing original and re-exported USFM files…" )
                        for jj, (BBB,filename1) in enumerate( fN.getMaximumPossibleFilenameTuples() ):
                            #print( jj, BBB, filename1 )
                            UUU, nn = BibleOrgSysGlobals.loadedBibleBooksCodes.getUSFMAbbreviation( BBB ).upper(), BibleOrgSysGlobals.loadedBibleBooksCodes.getUSFMNumber( BBB )
                            #print( jj, BBB, filename1, UUU )
                            filename2 = None
                            for fn in folderContents2:
                                if nn in fn and UUU in fn: filename2 = fn; break
                            if filename1 in folderContents1 and filename2 in folderContents2:
                                if BibleOrgSysGlobals.verbosityLevel > 2:
                                    print( "\nAbout to compare {}: {} {} with {}…".format( jj+1, BBB, filename1, filename2 ) )
                                result = BibleOrgSysGlobals.fileCompareUSFM( filename1, filename2, testFolder, outputFolderpath )
                                if result and BibleOrgSysGlobals.verbosityLevel > 2: print( "  Matched." )
                                #print( "  result", result )
                                #if BibleOrgSysGlobals.debugFlag:
                                    #if not result: halt
                            else:
                                if filename1 not in folderContents1: logger.warning( "  1/ Couldn't find {} ({}) in {}".format( filename1, BBB, folderContents1 ) )
                                if filename2 not in folderContents2: logger.warning( "  2/ Couldn't find {} ({}) in {}".format( filename2, UUU, folderContents2 ) )
                else: logger.error( "Sorry, test folder {!r} has no loadable books.".format( testFolder ) )
            else: logger.error( f"Sorry, test folder '{testFolder}' is not readable on this computer." )


    if 1: # Test reading and writing a USFM Bible (with MOST exports — unless debugging)
        testData = ( # name, abbreviation, folder for USFM files
                #("CustomTest", 'Custom', '../'),
                #("USFMTest1", 'USFM1', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMTest1/'),
                #("USFMTest2", 'MBTV', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMTest2/'),
                #("ESFMTest1-LV", 'ESFM1', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'ESFMTest1/'),
                #("ESFMTest2-RV", 'ESFM2', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'ESFMTest2/'),
                #("WEB", 'WEB', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFM-WEB/'),
                ("Matigsalug", 'MBTV', BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Matigsalug/Bible/MBTV/') ),
                #("MS-BT", 'MBTBT', BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Matigsalug/Bible/MBTBT/') ),
                #("MS-ABT", 'MBTABT', BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Matigsalug/Bible/MBTABT/') ),
                #("WEB2", 'WEB', BiblesFolderpath.joinpath( 'English translations/WEB (World English Bible)/2012-06-23 eng-web_usfm/') ),
                #("WEB3", 'WEB', BiblesFolderpath.joinpath( 'From eBible/WEB/eng-web_usfm 2013-07-18/'),
                #("WEB4", 'WEB', BiblesFolderpath.joinpath( 'English translations/WEB (World English Bible)/2014-03-05 eng-web_usfm/') ),
                #("WEB5", 'WEB', BiblesFolderpath.joinpath( 'English translations/WEB (World English Bible)/2014-04-23 eng-web_usfm/') ),
                #("WEB6", 'WEB', BiblesFolderpath.joinpath( 'English translations/WEB (World English Bible)/2017-08-22 eng-web_usfm') ),
                #("WEBLatest", 'WEB', BiblesFolderpath.joinpath( 'USFM Bibles/Haiola USFM test versions/eng-web_usfm/') ),
                #('ULT','ULT',BiblesFolderpath.joinpath( 'English translations/unfoldingWordVersions/en_ult/') ),
                #('UST','UST',BiblesFolderpath.joinpath( 'English translations/unfoldingWordVersions/en_ust/') ),
                #('UEB','UEB',BiblesFolderpath.joinpath( 'English translations/Door43Versions/UEB/en_ueb/') ),
                #('ULB','ULB',BiblesFolderpath.joinpath( 'English translations/Door43Versions/ULB/en_ulb/') ),
                #('UDB','UDB',BiblesFolderpath.joinpath( 'English translations/Door43Versions/UDB/en_udb/') ),
                ) # You can put your USFM test folder here

        for j, (name, abbrev, testFolder) in enumerate( testData ):
            if BibleOrgSysGlobals.verbosityLevel > 0: print( f"\nBibleWriter B{j+1}/ {abbrev} from {testFolder}…" )
            if os.access( testFolder, os.R_OK ):
                UB = USFMBible( testFolder, name, abbrev )
                UB.load()
                if BibleOrgSysGlobals.verbosityLevel > 0: print( ' ', UB )
                if BibleOrgSysGlobals.strictCheckingFlag: UB.check()
                if UB.books:
                    if debuggingThisModule:
                        result = UB.toBibleDoor(); print( f"result={result}" ); halt
                    myFlag = debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 3
                    doaResults = UB.doAllExports( wantPhotoBible=myFlag, wantODFs=myFlag, wantPDFs=myFlag )
                    if BibleOrgSysGlobals.strictCheckingFlag: # Now compare the original and the exported USFM files
                        outputFolderpath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_USFM2_Reexport/' )
                        fN = USFMFilenames( testFolder )
                        folderContents1 = os.listdir( testFolder ) # Originals
                        folderContents2 = os.listdir( outputFolderpath ) # Derived
                        if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nComparing original and re-exported USFM files…" )
                        for jj, (BBB,filename1) in enumerate( fN.getMaximumPossibleFilenameTuples() ):
                            #print( jj, BBB, filename1 )
                            UUU, nn = BibleOrgSysGlobals.loadedBibleBooksCodes.getUSFMAbbreviation( BBB ).upper(), BibleOrgSysGlobals.loadedBibleBooksCodes.getUSFMNumber( BBB )
                            #print( jj, BBB, filename1, UUU )
                            filename2 = None
                            for fn in folderContents2:
                                if nn in fn and UUU in fn: filename2 = fn; break
                            if filename1 in folderContents1 and filename2 in folderContents2:
                                if BibleOrgSysGlobals.verbosityLevel > 2:
                                    print( f"\nAbout to compare {jj+1}: {BBB} {filename1} with {filename2}…" )
                                result = BibleOrgSysGlobals.fileCompareUSFM( filename1, filename2, testFolder, outputFolderpath )
                                if result and BibleOrgSysGlobals.verbosityLevel > 2: print( "  Matched." )
                                #print( "  result", result )
                                #if BibleOrgSysGlobals.debugFlag:
                                    #if not result: halt
                            else:
                                if filename1 not in folderContents1: logger.warning( "  1/Couldn't find {} ({}) in {}".format( filename1, BBB, folderContents1 ) )
                                if filename2 not in folderContents2: logger.warning( "  2/Couldn't find {} ({}) in {}".format( filename2, UUU, folderContents2 ) )
                else: logger.error( "Sorry, test folder {!r} has no loadable books.".format( testFolder ) )
            else: logger.error( f"Sorry, test folder '{testFolder}' is not readable on this computer." )


    if 0: # Test reading and writing any Bible
        from BibleOrgSys.UnknownBible import UnknownBible
        from BibleOrgSys.Bible import Bible
        testData = ( # name, abbreviation, folder for USFM files
                #('USFM2-AllMarkers', 'USFM2-All', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFM2AllMarkersProject/'),
                #('USFM3-AllMarkers', 'USFM3-All', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFM3AllMarkersProject/'),
                #('CustomTest', 'Custom', '../'),
                #('USFMTest1', 'USFM1', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMTest1/'),
                #('USFMTest2', 'MBTV', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMTest2/'),
                #('ESFMTest1', 'ESFM1', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'ESFMTest1/'),
                #('ESFMTest2', 'ESFM2', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'ESFMTest2/'),
                #('WEB', 'WEB', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFM-WEB/'),
                #('OEB', 'OEB', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFM-OEB/'),
                #('Matigsalug', 'MBTV', BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Matigsalug/Bible/MBTV/') ),
                #('MS-BT', 'MBTBT', BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Matigsalug/Bible/MBTBT/') ),
                #('MS-ABT', 'MBTABT', BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Matigsalug/Bible/MBTABT/') ),
                #('WEB', 'WEB', BiblesFolderpath.joinpath( 'English translations/WEB (World English Bible)/2012-06-23 eng-web_usfm/') ),
                #('WEB', 'WEB', BiblesFolderpath.joinpath( 'From eBible/WEB/eng-web_usfm 2013-07-18/') ),
                #('WEB', 'WEB', BiblesFolderpath.joinpath( 'English translations/WEB (World English Bible)/2014-03-05 eng-web_usfm/') ),
                #('WEB', 'WEB', BiblesFolderpath.joinpath( 'English translations/WEB (World English Bible)/2014-04-23 eng-web_usfm/') ),
                #('OSISTest1', 'OSIS1', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'OSISTest1/'),
                ) # You can put your test folder here

        for j, (name, abbrev, testFolder) in enumerate( testData ):
            if BibleOrgSysGlobals.verbosityLevel > 0: print( '\nBibleWriter C'+str(j+1)+'/…' )
            if os.access( testFolder, os.R_OK ):
                UnkB = UnknownBible( testFolder )
                result = UnkB.search( autoLoadAlways=True, autoLoadBooks=True )
                if BibleOrgSysGlobals.verbosityLevel > 1: print( "Bible loaded", result )
                if isinstance( result, Bible ):
                    thisBible = result
                    if BibleOrgSysGlobals.verbosityLevel > 0: print( ' ', thisBible )
                    if BibleOrgSysGlobals.strictCheckingFlag: thisBible.check()
                    thisBible.toBibleDoor(); halt
                    myFlag = debuggingThisModule or BibleOrgSysGlobals.verbosityLevel > 3
                    doaResults = thisBible.doAllExports( wantPhotoBible=myFlag, wantODFs=myFlag, wantPDFs=myFlag )
                    if BibleOrgSysGlobals.strictCheckingFlag: # Now compare the original and the exported USFM files
                        outputFolderpath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_USFM2_Reexport/' )
                        fN = USFMFilenames( testFolder )
                        folderContents1 = os.listdir( testFolder ) # Originals
                        folderContents2 = os.listdir( outputFolderpath ) # Derived
                        if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nComparing original and re-exported USFM files…" )
                        for jj, (BBB,filename1) in enumerate( fN.getMaximumPossibleFilenameTuples() ):
                            #print( jj, BBB, filename1 )
                            UUU, nn = BibleOrgSysGlobals.loadedBibleBooksCodes.getUSFMAbbreviation( BBB ).upper(), BibleOrgSysGlobals.loadedBibleBooksCodes.getUSFMNumber( BBB )
                            #print( jj, BBB, filename1, UUU )
                            filename2 = None
                            for fn in folderContents2:
                                if nn in fn and UUU in fn: filename2 = fn; break
                            if filename1 in folderContents1 and filename2 in folderContents2:
                                if BibleOrgSysGlobals.verbosityLevel > 2:
                                    print( "\nAbout to compare {}: {} {} with {}…".format( jj+1, BBB, filename1, filename2 ) )
                                result = BibleOrgSysGlobals.fileCompareUSFM( filename1, filename2, testFolder, outputFolderpath )
                                if result and BibleOrgSysGlobals.verbosityLevel > 2: print( "  Matched." )
                                #print( "  result", result )
                                #if BibleOrgSysGlobals.debugFlag:
                                    #if not result: halt
                            else:
                                if filename1 not in folderContents1: logger.warning( "  1/ Couldn't find {} ({}) in {}".format( filename1, BBB, folderContents1 ) )
                                if filename2 not in folderContents2: logger.warning( "  2/ Couldn't find {} ({}) in {}".format( filename2, UUU, folderContents2 ) )
                else:
                    logger.critical( "Unable to load {} Bible from {!r}—aborting".format( abbrev, testFolder ) )
            else: logger.error( f"Sorry, test folder '{testFolder}' is not readable on this computer." )


    if 0: # Test reading and writing a USX Bible
        from BibleOrgSys.Formats.USXXMLBible import USXXMLBible
        from BibleOrgSys.Formats.USXFilenames import USXFilenames
        testData = (
                #('Matigsalug', BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../Data/Work/VirtualBox_Shared_Folder/PT7.3 Exports/USXExports/Projects/MBTV/') ),
                ('MatigsalugUSX', BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../Data/Work/VirtualBox_Shared_Folder/PT7.4 Exports/USX Exports/MBTV/') ),
                ) # You can put your USX test folder here

        for j, (name, testFolder) in enumerate( testData ):
            if BibleOrgSysGlobals.verbosityLevel > 0: print( '\nBibleWriter D'+str(j+1)+'/…' )
            if os.access( testFolder, os.R_OK ):
                UB = USXXMLBible( testFolder, name )
                UB.load()
                if BibleOrgSysGlobals.verbosityLevel > 0: print( ' ', UB )
                if BibleOrgSysGlobals.strictCheckingFlag: UB.check()
                doaResults = UB.doAllExports( wantPhotoBible=True, wantODFs=False, wantPDFs=False )
                if BibleOrgSysGlobals.strictCheckingFlag: # Now compare the original and the derived USX XML files
                    outputFolderpath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_USX_Reexport/' )
                    fN = USXFilenames( testFolder )
                    folderContents1 = os.listdir( testFolder ) # Originals
                    folderContents2 = os.listdir( outputFolderpath ) # Derived
                    if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nComparing original and re-exported USX files…" )
                    for jj, (BBB,filename) in enumerate( fN.getPossibleFilenameTuples() ):
                        if filename in folderContents1 and filename in folderContents2:
                            #print( "\n{}: {} {}".format( jj+1, BBB, filename ) )
                            result = BibleOrgSysGlobals.fileCompareXML( filename, filename, testFolder, outputFolderpath )
                            if BibleOrgSysGlobals.debugFlag:
                                if not result: halt
            else: print( f"Sorry, test folder '{testFolder}' is not readable on this computer." )


    if 0: # Test reading USFM Bibles and exporting to theWord and MySword
        from BibleOrgSys.Formats.USFMBible import USFMBible
        from BibleOrgSys.Formats.theWordBible import theWordFileCompare
        mainFolderpath = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'theWordRoundtripTestFiles/' )
        testData = (
                ('aai', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'theWordRoundtripTestFiles/aai 2013-05-13/') ),
                ('acc', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'theWordRoundtripTestFiles/accNT 2012-01-20/') ),
                ('acf', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'theWordRoundtripTestFiles/acfDBL 2013-02-03/') ),
                ('acr-n', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'theWordRoundtripTestFiles/acrNDBL 2013-03-08/') ),
                ('acr-t', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'theWordRoundtripTestFiles/accTDBL 2013-03-08/') ),
                ('agr', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'theWordRoundtripTestFiles/agrDBL 2013-03-08/') ),
                ('agu', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'theWordRoundtripTestFiles/aguDBL 2013-03-08/') ),
                ('ame', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'theWordRoundtripTestFiles/ameDBL 2013-02-13/') ),
                ('amr', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'theWordRoundtripTestFiles/amrDBL 2013-02-13/') ),
                ('apn', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'theWordRoundtripTestFiles/apnDBL 2013-02-13/') ),
                ('apu', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'theWordRoundtripTestFiles/apuDBL 2013-02-14/') ),
                ('apy', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'theWordRoundtripTestFiles/apyDBL 2013-02-15/') ),
                ('arn', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'theWordRoundtripTestFiles/arnDBL 2013-03-08/') ),
                ('auc', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'theWordRoundtripTestFiles/aucDBL 2013-02-26/') ),
                ) # You can put your USFM test folder here

        for j, (name, testFolder) in enumerate( testData ):
            if os.access( testFolder, os.R_OK ):
                UB = USFMBible( testFolder, name )
                UB.load()
                if BibleOrgSysGlobals.verbosityLevel > 0: print( '\nBibleWriter E'+str(j+1)+'/', UB )
                #if BibleOrgSysGlobals.strictCheckingFlag: UB.check()
                #result = UB.totheWord()
                doaResults = UB.doAllExports( wantPhotoBible=True, wantODFs=True, wantPDFs=True )
                if BibleOrgSysGlobals.strictCheckingFlag: # Now compare the supplied and the exported theWord modules
                    outputFolderpath = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_theWord_Export/' )
                    if os.path.exists( mainFolderpath.joinpath( name + '.nt' ) ): ext = '.nt'
                    elif os.path.exists( mainFolderpath.joinpath( name + '.ont' ) ): ext = '.ont'
                    elif os.path.exists( mainFolderpath.joinpath( name + '.ot' ) ): ext = '.ot'
                    else: halt
                    fn1 = name + ext # Supplied
                    fn2 = name + ext # Created
                    if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nComparing supplied and exported theWord files…" )
                    result = theWordFileCompare( fn1, fn2, mainFolderpath, outputFolderpath, exitCount=10 )
                    if not result:
                        print( "theWord modules did NOT match" )
                        #if BibleOrgSysGlobals.debugFlag: halt
            else: print( f"Sorry, test folder '{testFolder}' is not readable on this computer." )
# end of demo


if __name__ == '__main__':
    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    demo()

    BibleOrgSysGlobals.closedown( SHORT_PROGRAM_NAME, PROGRAM_VERSION )
# end of BibleWriter.py
