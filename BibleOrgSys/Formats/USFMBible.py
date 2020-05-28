#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# USFMBible.py
#
# Module handling compilations of USFM Bible books
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
Module for defining and manipulating complete or partial USFM Bibles.

NOTE: If it has a .SSF file, then it should be considered a PTX7Bible.
    Or if it has a Settings.XML file, then it should be considered a PTX8Bible.
"""
from gettext import gettext as _
from pathlib import Path
import os
import logging
import re
import multiprocessing

if __name__ == '__main__':
    import sys
    aboveAboveFolderpath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderpath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderpath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys.InputOutput.USFMFilenames import USFMFilenames
from BibleOrgSys.Formats.USFMBibleBook import USFMBibleBook
from BibleOrgSys.Bible import Bible



LAST_MODIFIED_DATE = '2020-05-19' # by RJH
SHORT_PROGRAM_NAME = "USFMBible"
PROGRAM_NAME = "USFM Bible handler"
PROGRAM_VERSION = '0.78'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

debuggingThisModule = False


filenameEndingsToIgnore = ('.ZIP.GO', '.ZIP.DATA',) # Must be UPPERCASE
extensionsToIgnore = ( 'ASC', 'BAK', 'BAK2', 'BAK3', 'BAK4', 'BBLX', 'BC', 'CCT', 'CSS', 'DOC', 'DTS', 'ESFM', 'HTM','HTML',
                    'JAR', 'LDS', 'LOG', 'MYBIBLE', 'NT','NTX', 'ODT', 'ONT','ONTX', 'OSIS', 'OT','OTX', 'PDB',
                    'SAV', 'SAVE', 'STY', 'SSF', 'USFX', 'USX', 'VRS', 'YET', 'XML', 'ZIP', ) # Must be UPPERCASE and NOT begin with a dot



def USFMBibleFileCheck( givenFolderName, strictCheck=True, autoLoad=False, autoLoadBooks=False, discountSSF=True ):
    """
    Given a folder, search for USFM Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number of Bibles found.

    if autoLoad is true and exactly one USFM Bible is found,
        returns the loaded USFMBible object.

    if discountSSF is set, finding a SSF file prevents a True result.
    """
    fnPrint( debuggingThisModule, "USFMBibleFileCheck( {}, {}, {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad, autoLoadBooks, discountSSF ) )
    if BibleOrgSysGlobals.debugFlag or debuggingThisModule:
        assert givenFolderName and isinstance( givenFolderName, (str,Path) )
        assert autoLoad in (True,False,) and autoLoadBooks in (True,False,)

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( _("USFMBibleFileCheck: Given {!r} folder is unreadable").format( givenFolderName ) )
        vPrint( 'Never', debuggingThisModule, "  USFM returningA1", False )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( _("USFMBibleFileCheck: Given {!r} path is not a folder").format( givenFolderName ) )
        vPrint( 'Never', debuggingThisModule, "  USFM returningA2", False )
        return False

    # Find all the files and folders in this folder
    vPrint( 'Verbose', debuggingThisModule, " USFMBibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
    foundFolders, foundFiles = [], []
    for something in os.listdir( givenFolderName ):
        somepath = os.path.join( givenFolderName, something )
        if os.path.isdir( somepath ):
            if something in BibleOrgSysGlobals.COMMONLY_IGNORED_FOLDERS:
                continue # don't visit these directories
            foundFolders.append( something )
        #elif os.path.isfile( somepath ):
            #somethingUpper = something.upper()
            #somethingUpperProper, somethingUpperExt = os.path.splitext( somethingUpper )
            #ignore = False
            #for ending in filenameEndingsToIgnore:
                #if somethingUpper.endswith( ending): ignore=True; break
            #if ignore: continue
            #if somethingUpperExt[1:] in extensionsToIgnore: continue # Compare without the first dot
            #if strictCheck or BibleOrgSysGlobals.strictCheckingFlag:
                #firstLine = BibleOrgSysGlobals.peekIntoFile( something, givenFolderName )
                ##dPrint( 'Quiet', debuggingThisModule, 'U1', repr(firstLine) )
                #if firstLine is None: continue # seems we couldn't decode the file
                #if firstLine and firstLine[0]==chr(65279): #U+FEFF or \ufeff
                    #logging.info( "USFMBibleFileCheck: Detected Unicode Byte Order Marker (BOM) in {}".format( something ) )
                    #firstLine = firstLine[1:] # Remove the Unicode Byte Order Marker (BOM)
                #if not firstLine: continue # don't allow a blank first line
                #if firstLine[0] != '\\': continue # Must start with a backslash
            #foundFiles.append( something )

    # See if there's an USFMBible project here in this given folder
    numFound = 0
    UFns = USFMFilenames( givenFolderName ) # Assuming they have standard Paratext style filenames
    vPrint( 'Info', debuggingThisModule, UFns )
    filenameTuples = UFns.getMaximumPossibleFilenameTuples( strictCheck=strictCheck ) # Returns (BBB,filename) 2-tuples
    vPrint( 'Verbose', debuggingThisModule, "  Maximum:", len(filenameTuples), filenameTuples )
    # Check they are USFM3 (not 2)
    goodIndexList = []
    for n,(BBB,filename) in enumerate(filenameTuples):
        try:
            for line in BibleOrgSysGlobals.peekIntoFile( filename, givenFolderName, numLines=4 ):
                if line.lower().startswith('\\usfm 3') or line.lower().startswith('\\usfm3'):
                    goodIndexList.append(n); break # Can't delete it yet
        except TypeError: pass # If file is empty peekIntoFile returns None
    if BibleOrgSysGlobals.verbosityLevel > 2 and filenameTuples and goodIndexList:
        vPrint( 'Quiet', debuggingThisModule, "  Found {} USFM3 file{}.".format( len(filenameTuples), '' if len(filenameTuples)==1 else 's' ) )
    if filenameTuples and goodIndexList:
        SSFs = UFns.getSSFFilenames()
        if SSFs:
            vPrint( 'Info', debuggingThisModule, "Got USFM3 SSFs: ({}) {}".format( len(SSFs), SSFs ) )
            ssfFilepath = os.path.join( givenFolderName, SSFs[0] )
            if not discountSSF:
                # if there's an SSF, we won't accept it as a USFM Bible, because it should be opened as a PTX7 Bible
                numFound += 1
        else: numFound += 1
    if numFound:
        vPrint( 'Info', debuggingThisModule, _("USFMBibleFileCheck got {} in {}").format( numFound, givenFolderName ) )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            uB = USFMBible( givenFolderName )
            if autoLoad or autoLoadBooks: uB.preload()
            if autoLoadBooks: uB.loadBooks() # Load and process the book files
            vPrint( 'Never', debuggingThisModule, "  USFM3 returningB1", uB )
            return uB
        vPrint( 'Never', debuggingThisModule, "  USFM3 returningB2", numFound )
        return numFound

    # Look one level down
    numFound = 0
    foundProjects = []
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
        if not os.access( tryFolderName, os.R_OK ): # The subfolder is not readable
            logging.warning( _("USFMBibleFileCheck: {!r} subfolder is unreadable").format( tryFolderName ) )
            continue
        #if 0:
            #dPrint( 'Verbose', debuggingThisModule, "    USFMBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
            #foundSubfolders, foundSubfiles = [], []
            #for something in os.listdir( tryFolderName ):
                #somepath = os.path.join( givenFolderName, thisFolderName, something )
                #if os.path.isdir( somepath ): foundSubfolders.append( something )
                #elif os.path.isfile( somepath ):
                    #somethingUpper = something.upper()
                    #somethingUpperProper, somethingUpperExt = os.path.splitext( somethingUpper )
                    #ignore = False
                    #for ending in filenameEndingsToIgnore:
                        #if somethingUpper.endswith( ending): ignore=True; break
                    #if ignore: continue
                    #if somethingUpperExt[1:] in extensionsToIgnore: continue # Compare without the first dot
                    #if strictCheck or BibleOrgSysGlobals.strictCheckingFlag:
                        #firstLine = BibleOrgSysGlobals.peekIntoFile( something, tryFolderName )
                        ##dPrint( 'Quiet', debuggingThisModule, 'U2', repr(firstLine) )
                        #if firstLine is None: continue # seems we couldn't decode the file
                        #if firstLine and firstLine[0]==chr(65279): #U+FEFF or \ufeff
                            #logging.info( "USFMBibleFileCheck: Detected Unicode Byte Order Marker (BOM) in {}".format( something ) )
                            #firstLine = firstLine[1:] # Remove the Unicode Byte Order Marker (BOM)
                        #if not firstLine: continue # don't allow a blank first line
                        #if firstLine[0] != '\\': continue # Must start with a backslash
                    #foundSubfiles.append( something )

        # See if there's an USFM Bible here in this folder
        UFns = USFMFilenames( tryFolderName ) # Assuming they have standard Paratext style filenames
        vPrint( 'Info', debuggingThisModule, UFns )
        filenameTuples = UFns.getMaximumPossibleFilenameTuples( strictCheck=strictCheck ) # Returns (BBB,filename) 2-tuples
        vPrint( 'Verbose', debuggingThisModule, "  Maximum:", len(filenameTuples), filenameTuples )
        # Check they are USFM3 (not 2)
        goodIndexList = []
        for n,(BBB,filename) in enumerate(filenameTuples):
            try:
                for line in BibleOrgSysGlobals.peekIntoFile( filename, tryFolderName, numLines=4 ):
                    if line.lower().startswith('\\usfm 3') or line.lower().startswith('\\usfm3'):
                        goodIndexList.append(n); break # Can't delete it yet
            except TypeError: pass # If file is empty peekIntoFile returns None
        if BibleOrgSysGlobals.verbosityLevel > 2 and filenameTuples and goodIndexList:
            vPrint( 'Quiet', debuggingThisModule, "  Found {} USFM3 files: {}".format( len(filenameTuples), filenameTuples ) )
        elif BibleOrgSysGlobals.verbosityLevel > 1 and filenameTuples and goodIndexList and debuggingThisModule:
            vPrint( 'Quiet', debuggingThisModule, "  Found {} USFM3 file{}".format( len(filenameTuples), '' if len(filenameTuples)==1 else 's' ) )
        if filenameTuples and goodIndexList:
            SSFs = UFns.getSSFFilenames( searchAbove=True )
            if SSFs:
                vPrint( 'Info', debuggingThisModule, "Got USFM3 SSFs: ({}) {}".format( len(SSFs), SSFs ) )
                ssfFilepath = os.path.join( thisFolderName, SSFs[0] )
                if not discountSSF:
                    # if there's an SSF, we won't accept it as a USFM Bible, because it should be opened as a PTX7 Bible
                    foundProjects.append( tryFolderName )
                    numFound += 1
            else:
                foundProjects.append( tryFolderName )
                numFound += 1
    if numFound:
        vPrint( 'Info', debuggingThisModule, _("USFMBibleFileCheck foundProjects {} {}").format( numFound, foundProjects ) )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            uB = USFMBible( foundProjects[0] )
            if autoLoad or autoLoadBooks: uB.preload()
            if autoLoadBooks: uB.loadBooks() # Load and process the book files
            vPrint( 'Never', debuggingThisModule, "  USFM3 returningC1", uB )
            return uB
        vPrint( 'Never', debuggingThisModule, "  USFM3 returningC2", numFound )
        return numFound
    vPrint( 'Never', debuggingThisModule, "  USFM3 returningN", None )
# end of USFMBibleFileCheck



def findReplaceText( self, optionsDict, confirmCallback ):
    """
    Search the Bible book files for the given text which is contained in a dictionary of options.
        Find string must be in optionsDict['findText'].
        (We add default options for any missing ones as well as updating the 'findHistoryList'.)
    Then go through and replace.

    "self" in this case is either a USFMBible or a PTX 7 or 8 Bible object.

    The confirmCallback function must be a function that takes
        6 parameters: ref, contextBefore, ourFindText, contextAfter, willBeText, haveUndosFlag
    and returns a single UPPERCASE character
        'N' (no), 'Y' (yes), 'A' (all), or 'S' (stop).

    Note that this function works on actual text files.
        If the text files are loaded into a Bible object,
            after replacing, the Bible object will need to be reloaded.
    If it's called from an edit window, it's essential that all editing changes
        are saved to the file first.

    NOTE: We currently handle undo, by caching all files which need to be saved to disk.
        We might need to make this more efficient, e.g., save under a temp filename.
    """
    fnPrint( debuggingThisModule, _("findReplaceText( {}, {}, … )").format( self, optionsDict ) )
    if BibleOrgSysGlobals.debugFlag:
        if debuggingThisModule:
            assert 'findText' in optionsDict
            assert 'replaceText' in optionsDict

    optionsList = ( 'parentWindow', 'parentBox', 'givenBible', 'workName',
            'findText', 'replaceText', 'findHistoryList', 'replaceHistoryList', 'wordMode',
            #'caselessFlag', 'ignoreDiacriticsFlag', 'includeIntroFlag', 'includeMainTextFlag',
            #'includeMarkerTextFlag', 'includeExtrasFlag', 'markerList', 'chapterList',
            'contextLength', 'bookList', 'regexFlag', 'currentBCV', 'doBackups', )
    for someKey in optionsDict:
        if someKey not in optionsList:
            vPrint( 'Quiet', debuggingThisModule, "findReplaceText warning: unexpected {!r} option = {!r}".format( someKey, optionsDict[someKey] ) )
            if debuggingThisModule: halt

    # Go through all the given options
    if 'workName' not in optionsDict: optionsDict['workName'] = self.abbreviation if self.abbreviation else self.name
    if 'findHistoryList' not in optionsDict: optionsDict['findHistoryList'] = [] # Oldest first
    if 'wordMode' not in optionsDict: optionsDict['wordMode'] = 'Any' # or 'Whole' or 'EndsWord' or 'Begins' or 'EndsLine'
    #if 'caselessFlag' not in optionsDict: optionsDict['caselessFlag'] = True
    #if 'ignoreDiacriticsFlag' not in optionsDict: optionsDict['ignoreDiacriticsFlag'] = False
    #if 'includeIntroFlag' not in optionsDict: optionsDict['includeIntroFlag'] = True
    #if 'includeMainTextFlag' not in optionsDict: optionsDict['includeMainTextFlag'] = True
    #if 'includeMarkerTextFlag' not in optionsDict: optionsDict['includeMarkerTextFlag'] = False
    #if 'includeExtrasFlag' not in optionsDict: optionsDict['includeExtrasFlag'] = False
    if 'contextLength' not in optionsDict: optionsDict['contextLength'] = 60 # each side
    if 'bookList' not in optionsDict: optionsDict['bookList'] = 'ALL' # or BBB or a list
    #if 'chapterList' not in optionsDict: optionsDict['chapterList'] = None
    #if 'markerList' not in optionsDict: optionsDict['markerList'] = None
    if 'doBackups' not in optionsDict: optionsDict['doBackups'] = True
    optionsDict['regexFlag'] = False

    if BibleOrgSysGlobals.debugFlag:
        if optionsDict['chapterList']: assert optionsDict['bookList'] is None or len(optionsDict['bookList']) == 1 \
                            or optionsDict['chapterList'] == [0] # Only combinations that make sense
        assert '\r' not in optionsDict['findText'] and '\n' not in optionsDict['findText']
        assert optionsDict['wordMode'] in ( 'Any', 'Whole', 'Begins', 'EndsWord', 'EndsLine', )
        if optionsDict['wordMode'] != 'Any': assert ' ' not in optionsDict['findText']
        #if optionsDict['markerList']:
            #assert isinstance( markerList, list )
            #assert not optionsDict['includeIntroFlag']
            #assert not optionsDict['includeMainTextFlag']
            #assert not optionsDict['includeMarkerTextFlag']
            #assert not optionsDict['includeExtrasFlag']

    #ourMarkerList = []
    #if optionsDict['markerList']:
        #for marker in optionsDict['markerList']:
            #ourMarkerList.append( BibleOrgSysGlobals.loadedUSFMMarkers.toStandardMarker( marker ) )

    resultDict = { 'numFinds':0, 'numReplaces':0, 'searchedBookList':[], 'foundBookList':[], 'replacedBookList':[], 'aborted':False, }

    ourFindText = optionsDict['findText']
    # Save the search history (with the 'regex:' text still prefixed if applicable)
    try: optionsDict['findHistoryList'].remove( ourFindText )
    except ValueError: pass
    optionsDict['findHistoryList'].append( ourFindText ) # Make sure it goes on the end

    ourReplaceText = optionsDict['replaceText']
    try: optionsDict['replaceHistoryList'].remove( ourReplaceText )
    except ValueError: pass
    optionsDict['replaceHistoryList'].append( ourReplaceText ) # Make sure it goes on the end

    if ourFindText.lower().startswith( 'regex:' ):
        resultDict['hadRegexError'] = False
        optionsDict['regexFlag'] = True
        ourFindText = ourFindText[6:]
        compiledFindText = re.compile( ourFindText )
    else:
        replaceLen = len( ourReplaceText )
        #diffLen = replaceLen - searchLen
    #if optionsDict['ignoreDiacriticsFlag']: ourFindText = BibleOrgSysGlobals.removeAccents( ourFindText )
    #if optionsDict['caselessFlag']: ourFindText = ourFindText.lower()
    searchLen = len( ourFindText )
    if BibleOrgSysGlobals.debugFlag: assert searchLen
    #dPrint( 'Quiet', debuggingThisModule, "  Searching for {!r} in {} loaded books".format( ourFindText, len(self) ) )

    if not self.preloadDone: self.preload()

    # The first entry in the result list is a dictionary containing the parameters
    #   Following entries are SimpleVerseKey objects
    encoding = self.encoding
    if encoding is None: encoding = 'utf-8'

    replaceAllFlag = stopFlag = undoFlag = False
    filesToSave = {}
    if self.maximumPossibleFilenameTuples:
        for BBB,filename in self.maximumPossibleFilenameTuples:
            if optionsDict['bookList'] is None or optionsDict['bookList']=='ALL' or BBB in optionsDict['bookList']:
                #dPrint( 'Quiet', debuggingThisModule, _("findReplaceText: will search book {}").format( BBB ) )
                bookFilepath = os.path.join( self.sourceFolder, filename )
                with open( bookFilepath, 'rt', encoding=encoding ) as bookFile:
                    bookText = bookFile.read()
                resultDict['searchedBookList'].append( BBB )

                #C, V = '-1', '0'
                if optionsDict['regexFlag']: # ignores wordMode flag
                    ix = 0
                    while True:
                        match = compiledFindText.search( bookText, ix )
                        if not match: break # none / no more found
                        ix, ixAfter = match.span()
                        regexFoundText = bookText[ix:ixAfter]
                        try: regexReplacementText = compiledFindText.sub( ourReplaceText, regexFoundText, count=1 )
                        except re.error as err:
                            vPrint( 'Quiet', debuggingThisModule, "Search/Replace regex error: {}".format( err ) )
                            resultDict['hadRegexError'] = True
                            stopFlag = True; break
                        #dPrint( 'Quiet', debuggingThisModule, "Found regex {!r} at {:,} in {}".format( ourFindText, ix, BBB ) )
                        #dPrint( 'Quiet', debuggingThisModule, "  Found text was {!r}, replacement will be {!r}".format( regexFoundText, regexReplacementText ) )
                        resultDict['numFinds'] += 1
                        if BBB not in resultDict['foundBookList']: resultDict['foundBookList'].append( BBB )

                        if optionsDict['contextLength']: # Find the context in the original (fully-cased) string
                            contextBefore = bookText[max(0,ix-optionsDict['contextLength']):ix]
                            contextAfter = bookText[ixAfter:ixAfter+optionsDict['contextLength']]
                        else: contextBefore = contextAfter = None
                        #dPrint( 'Quiet', debuggingThisModule, "  After  {!r}".format( contextBefore ) )
                        #dPrint( 'Quiet', debuggingThisModule, "  Before {!r}".format( contextAfter ) )

                        result = None
                        if not replaceAllFlag:
                            ref = BBB
                            willBeText = contextBefore + regexReplacementText + contextAfter
                            result = confirmCallback( ref, contextBefore, regexFoundText, contextAfter, willBeText, resultDict['numReplaces']>0 )
                            #dPrint( 'Quiet', debuggingThisModule, "findReplaceText got", result )
                            assert result in 'YNASU'
                            if result == 'A': replaceAllFlag = True
                            elif result == 'S': stopFlag = True; break
                            elif result == 'U': undoFlag = True; break
                        if replaceAllFlag or result == 'Y':
                            #dPrint( 'Quiet', debuggingThisModule, "  ix={:,}, ixAfter={:,}, diffLen={}".format( ix, ixAfter, diffLen ) )
                            bookText = bookText[:ix] + regexReplacementText + bookText[ixAfter:]
                            ix += len( regexReplacementText ) # Start searching after the replacement
                            #dPrint( 'Quiet', debuggingThisModule, "  ix={:,}, ixAfter={:,}, now={!r}".format( ix, ixAfter, bookText ) )
                            resultDict['numReplaces'] += 1
                            if BBB not in resultDict['replacedBookList']: resultDict['replacedBookList'].append( BBB )
                            filesToSave[BBB] = (bookFilepath,bookText)
                        else: ix += 1 # So don't keep repeating the same find
                else: # not regExp
                    ix = 0
                    while True:
                        ix = bookText.find( ourFindText, ix )
                        if ix == -1: break # none / no more found
                        #dPrint( 'Quiet', debuggingThisModule, "Found {!r} at {:,} in {}".format( ourFindText, ix, BBB ) )
                        resultDict['numFinds'] += 1
                        if BBB not in resultDict['foundBookList']: resultDict['foundBookList'].append( BBB )

                        ixAfter = ix + searchLen
                        if optionsDict['wordMode'] == 'Whole':
                            #dPrint( 'Quiet', debuggingThisModule, "BF", repr(bookText[ix-1]) )
                            #dPrint( 'Quiet', debuggingThisModule, "AF", repr(bookText[ixAfter]) )
                            if ix>0 and bookText[ix-1].isalpha(): ix+=1; continue
                            if ixAfter<len(bookText) and bookText[ixAfter].isalpha(): ix+=1; continue
                        elif optionsDict['wordMode'] == 'Begins':
                            if ix>0 and bookText[ix-1].isalpha(): ix+=1; continue
                        elif optionsDict['wordMode'] == 'EndsWord':
                            if ixAfter<len(bookText) and bookText[ixAfter].isalpha(): ix+=1; continue
                        elif optionsDict['wordMode'] == 'EndsLine':
                            if ixAfter<len(bookText): ix+=1; continue

                        if optionsDict['contextLength']: # Find the context in the original (fully-cased) string
                            contextBefore = bookText[max(0,ix-optionsDict['contextLength']):ix]
                            contextAfter = bookText[ixAfter:ixAfter+optionsDict['contextLength']]
                        else: contextBefore = contextAfter = None
                        #dPrint( 'Quiet', debuggingThisModule, "  After  {!r}".format( contextBefore ) )
                        #dPrint( 'Quiet', debuggingThisModule, "  Before {!r}".format( contextAfter ) )

                        result = None
                        if not replaceAllFlag:
                            ref = BBB
                            willBeText = contextBefore + ourReplaceText + contextAfter
                            result = confirmCallback( ref, contextBefore, ourFindText, contextAfter, willBeText, resultDict['numReplaces']>0 )
                            #dPrint( 'Quiet', debuggingThisModule, "findReplaceText got", result )
                            assert result in 'YNASU'
                            if result == 'A': replaceAllFlag = True
                            elif result == 'S': stopFlag = True; break
                            elif result == 'U': undoFlag = True; break
                        if replaceAllFlag or result == 'Y':
                            #dPrint( 'Quiet', debuggingThisModule, "  ix={:,}, ixAfter={:,}, diffLen={}".format( ix, ixAfter, diffLen ) )
                            bookText = bookText[:ix] + ourReplaceText + bookText[ixAfter:]
                            ix += replaceLen # Start searching after the replacement
                            #dPrint( 'Quiet', debuggingThisModule, "  ix={:,}, ixAfter={:,}, now={!r}".format( ix, ixAfter, bookText ) )
                            resultDict['numReplaces'] += 1
                            if BBB not in resultDict['replacedBookList']: resultDict['replacedBookList'].append( BBB )
                            filesToSave[BBB] = (bookFilepath,bookText)
                        else: ix += 1 # So don't keep repeating the same find

            if stopFlag:
                vPrint( 'Info', debuggingThisModule, "Search/Replace was aborted in {} after {} replaces.".format( BBB, resultDict['numReplaces'] ) )
                resultDict['aborted'] = True
                break
            if undoFlag:
                if resultDict['numReplaces']>0:
                      vPrint( 'Info', debuggingThisModule, "Search/Replace was aborted in {} for undo in {} books.".format( BBB, len(resultDict['replacedBookList']) ) )
                elif BibleOrgSysGlobals.verbosityLevel > 2:
                    vPrint( 'Quiet', debuggingThisModule, "Search/Replace was aborted (by undo) in {}.".format( BBB ) )
                filesToSave = {}
                resultDict['replacedBookList'] = []
                resultDict['numReplaces'] = 0
                resultDict['aborted'] = True
                break

    else:
        logging.critical( _("No book files to search/replace in {}!").format( self.sourceFolder ) )

    for BBB,(filepath,fileText) in filesToSave.items():
        if optionsDict['doBackups']:
            vPrint( 'Info', debuggingThisModule, "Making backup copy of {} file: {}…".format( BBB, filepath ) )
            BibleOrgSysGlobals.backupAnyExistingFile( filepath, numBackups=5 )
        if BibleOrgSysGlobals.verbosityLevel > 2:
            vPrint( 'Quiet', debuggingThisModule, "Writing {:,} bytes for {} to {}…".format( len(fileText), BBB, filepath ) )
        elif BibleOrgSysGlobals.verbosityLevel > 1:
            vPrint( 'Quiet', debuggingThisModule, "Saving {} with {} encoding".format( filepath, encoding ) )
        with open( filepath, 'wt', encoding=encoding, newline='\r\n' ) as bookFile:
            bookFile.write( fileText )
        self.bookNeedsReloading[BBB] = True

    #dPrint( 'Quiet', debuggingThisModule, _("findReplaceText: returning {}/{}  {}/{}/{} books  {}").format( resultDict['numReplaces'], resultDict['numFinds'], len(resultDict['replacedBookList']), len(resultDict['foundBookList']), len(resultDict['searchedBookList']), optionsDict ) )
    return optionsDict, resultDict
# end of findReplaceText



class USFMBible( Bible ):
    """
    Class to load and manipulate USFM Bibles.

    """
    def __init__( self, sourceFolder, givenName=None, givenAbbreviation=None, encoding=None ):
        """
        Create the internal USFM Bible object.

        Note that sourceFolder can be None if we don't know that yet.
        """
        fnPrint( debuggingThisModule, f"USFMBible.__init__( '{sourceFolder}', gN='{givenName}', gA='{givenAbbreviation}', e='{encoding}' )" )
        assert givenName != 'utf-8'
        assert givenAbbreviation != 'utf-8'

         # Setup and initialise the base class first
        super().__init__()
        self.objectNameString = 'USFM Bible object'
        self.objectTypeString = 'USFM'

        # Now we can set our object variables
        self.sourceFolder, self.givenName, self.abbreviation, self.encoding = sourceFolder, givenName, givenAbbreviation, encoding
        if self.givenName and not self.name:
            self.name = self.givenName
    # end of USFMBible.__init_


    def preload( self ):
        """
        Tries to determine USFM filename pattern.
        """
        fnPrint( debuggingThisModule, f"preload() from {self.sourceFolder}" )
        if BibleOrgSysGlobals.debugFlag or debuggingThisModule:
            assert not self.preloadDone
            assert self.sourceFolder is not None

        # Do a preliminary check on the contents of our folder
        foundFiles, foundFolders = [], []
        for something in os.listdir( self.sourceFolder ):
            #dPrint( 'Quiet', debuggingThisModule, repr(something) )
            somepath = os.path.join( self.sourceFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )
            else: logging.error( _("preload: Not sure what {!r} is in {}!").format( somepath, self.sourceFolder ) )
        if foundFolders:
            unexpectedFolders = []
            for folderName in foundFolders:
                if folderName.startswith( 'Interlinear_'): continue
                if folderName in BibleOrgSysGlobals.COMMONLY_IGNORED_FOLDERS:
                    continue
                unexpectedFolders.append( folderName )
            if unexpectedFolders:
                logging.info( _("USFM preload: Surprised to see subfolders in {!r}: {}").format( self.sourceFolder, unexpectedFolders ) )
        if not foundFiles:
            vPrint( 'Quiet', debuggingThisModule, _("preload: Couldn't find any files in {!r}").format( self.sourceFolder ) )
            raise FileNotFoundError # No use continuing

        self.USFMFilenamesObject = USFMFilenames( self.sourceFolder )
        if BibleOrgSysGlobals.verbosityLevel > 3 or (BibleOrgSysGlobals.debugFlag and debuggingThisModule):
            vPrint( 'Quiet', debuggingThisModule, "USFMFilenamesObject", self.USFMFilenamesObject )

        if self.suppliedMetadata is None: self.suppliedMetadata = {}
        #if self.ssfFilepath is None: # it might have been loaded first
            ## Attempt to load the SSF file
            ##self.suppliedMetadata, self.settingsDict = {}, {}
            #ssfFilepathList = self.USFMFilenamesObject.getSSFFilenames( searchAbove=True, auto=True )
            ##dPrint( 'Quiet', debuggingThisModule, "ssfFilepathList", ssfFilepathList )
            #if len(ssfFilepathList) > 1:
                #logging.error( _("preload: Found multiple possible SSF files -- using first one: {}").format( ssfFilepathList ) )
            #if len(ssfFilepathList) >= 1: # Seems we found the right one
                #from BibleOrgSys.Formats.PTX7Bible import loadPTX7ProjectData
                #PTXSettingsDict = loadPTX7ProjectData( self, ssfFilepathList[0] )
                #if PTXSettingsDict:
                    #if self.suppliedMetadata is None: self.suppliedMetadata = {}
                    #if 'PTX7' not in self.suppliedMetadata: self.suppliedMetadata['PTX7'] = {}
                    #self.suppliedMetadata['PTX7']['SSF'] = PTXSettingsDict
                    #self.applySuppliedMetadata( 'SSF' ) # Copy some to BibleObject.settingsDict

        # Find the filenames of all our books
        self.maximumPossibleFilenameTuples = self.USFMFilenamesObject.getMaximumPossibleFilenameTuples() # Returns (BBB,filename) 2-tuples
        self.possibleFilenameDict = {}
        for BBB, filename in self.maximumPossibleFilenameTuples:
            self.availableBBBs.add( BBB )
            self.possibleFilenameDict[BBB] = filename

        self.preloadDone = True
    # end of USFMBible.preload


    def loadBook( self, BBB:str, filename=None ):
        """
        Load the requested book into self.books if it's not already loaded.

        NOTE: You should ensure that preload() has been called first.
        """
        fnPrint( debuggingThisModule, f"USFMBible.loadBook( {BBB}, {filename} )" )
        # dPrint( 'Info', debuggingThisModule, debuggingThisModule, f"USFMBible.loadBook( {BBB}, {filename} )", id(self) )
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            assert self.preloadDone

        if BBB not in self.bookNeedsReloading or not self.bookNeedsReloading[BBB]:
            if BBB in self.books:
                dPrint( 'Quiet', debuggingThisModule, "  {} is already loaded -- returning".format( BBB ) )
                return # Already loaded
            if BBB in self.triedLoadingBook:
                logging.warning( "We had already tried loading USFM {} for {}".format( BBB, self.name ) )
                return # We've already attempted to load this book
        self.triedLoadingBook[BBB] = True

        if BibleOrgSysGlobals.verbosityLevel > 2 or BibleOrgSysGlobals.debugFlag:
            vPrint( 'Quiet', debuggingThisModule, _("  USFMBible: Loading {} from {} from {}…").format( BBB, self.name, self.sourceFolder ) )
        try:
            if filename is None and BBB in self.possibleFilenameDict:
                filename = self.possibleFilenameDict[BBB]
        except AttributeError as e:
            logging.critical( "Was a preload() done on this USFMBible?" )
            raise e
        if filename is None: raise FileNotFoundError( "USFMBible.loadBook: Unable to find file for {}".format( BBB ) )
        UBB = USFMBibleBook( self, BBB )
        UBB.load( filename, self.sourceFolder, self.encoding )
        if UBB._rawLines:
            UBB.validateMarkers() # Usually activates InternalBibleBook.processLines()
            self.stashBook( UBB )
        else: logging.info( "USFM book {} was completely blank".format( BBB ) )
        self.bookNeedsReloading[BBB] = False
    # end of USFMBible.loadBook


    def _loadBookMP( self, BBB_Filename_duple ) -> USFMBibleBook:
        """
        Multiprocessing version!
        Load the requested book if it's not already loaded (but doesn't save it as that is not safe for multiprocessing)

        Parameter is a 2-tuple containing BBB and the filename.
        Note that self here might not be the original USFMBibleBook class instance!

        Returns the book info.
        """
        fnPrint( debuggingThisModule, f"USFMBible._loadBookMP( {BBB_Filename_duple} )" )
        # dPrint( 'Info', debuggingThisModule, f"USFMBible._loadBookMP( {BBB_Filename_duple} )", id(self) )

        BBB, filename = BBB_Filename_duple
        if BBB in self.books:
            dPrint( 'Quiet', debuggingThisModule, "  {} is already loaded -- returning".format( BBB ) )
            return self.books[BBB] # Already loaded
        #if BBB in self.triedLoadingBook:
            #logging.warning( "We had already tried loading USFM {} for {}".format( BBB, self.name ) )
            #return # We've already attempted to load this book
        self.triedLoadingBook[BBB] = True
        self.bookNeedsReloading[BBB] = False
        if BibleOrgSysGlobals.verbosityLevel > 2 or BibleOrgSysGlobals.debugFlag:
            vPrint( 'Quiet', debuggingThisModule, '  ' + _("Loading {} from {} from {}…").format( BBB, self.name, self.sourceFolder ) )
        UBB = USFMBibleBook( self, BBB ) # Ensure that we point back to the original instance
        UBB.load( self.possibleFilenameDict[BBB], self.sourceFolder, self.encoding )
        UBB.validateMarkers() # Usually activates InternalBibleBook.processLines()
        if BibleOrgSysGlobals.verbosityLevel > 2 or BibleOrgSysGlobals.debugFlag: vPrint( 'Quiet', debuggingThisModule, _("    Finishing loading USFM book {}.").format( BBB ) )
        return UBB
    # end of USFMBible._loadBookMP


    def loadBooks( self ):
        """
        Load all the Bible books.
        """
        fnPrint( debuggingThisModule, f"Loading {self.getAName()} from {self.sourceFolder}" )

        if not self.preloadDone: self.preload()

        if self.maximumPossibleFilenameTuples:
            if BibleOrgSysGlobals.maxProcesses > 1 \
            and not BibleOrgSysGlobals.alreadyMultiprocessing: # Get our subprocesses ready and waiting for work
                # Load all the books as quickly as possible
                #parameters = [BBB for BBB,filename in self.maximumPossibleFilenameTuples] # Can only pass a single parameter to map
                if BibleOrgSysGlobals.verbosityLevel > 1:
                    vPrint( 'Quiet', debuggingThisModule, _("Loading {} USFM books using {} processes…").format( len(self.maximumPossibleFilenameTuples), BibleOrgSysGlobals.maxProcesses ) )
                    vPrint( 'Quiet', debuggingThisModule, _("  NOTE: Outputs (including error and warning messages) from loading various books may be interspersed.") )
                BibleOrgSysGlobals.alreadyMultiprocessing = True
                with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                    results = pool.map( self._loadBookMP, self.maximumPossibleFilenameTuples ) # have the pool do our loads
                    assert len(results) == len(self.maximumPossibleFilenameTuples)
                    for bBook in results:
                        # dPrint( 'Info', debuggingThisModule, f"Stashing {bBook.BBB} {id(bBook)} with {id(bBook.containerBibleObject)}" )
                        bBook.containerBibleObject = self # Because the pickling and unpickling messes this up
                        self.stashBook( bBook ) # Saves them in the correct order
                BibleOrgSysGlobals.alreadyMultiprocessing = False
            else: # Just single threaded
                # Load the books one by one -- assuming that they have regular Paratext style filenames
                for BBB,filename in self.maximumPossibleFilenameTuples:
                    #if BibleOrgSysGlobals.verbosityLevel>1 or BibleOrgSysGlobals.debugFlag:
                        #dPrint( 'Quiet', debuggingThisModule, _("  USFMBible: Loading {} from {} from {}…").format( BBB, self.name, self.sourceFolder ) )
                    #loadedBook = self.loadBook( BBB, filename ) # also saves it
                    self.loadBook( BBB, filename ) # also saves it
        else:
            logging.critical( "USFMBible: " + _("No books to load in folder '{}'!").format( self.sourceFolder ) )
        #dPrint( 'Quiet', debuggingThisModule, self.getBookList() )
        self.doPostLoadProcessing()

        # for BBB,bookObject in self.books.items():
        #     print( "USFMBible.loadBooks", id(self), BBB, id(bookObject), id(bookObject.containerBibleObject) )
    # end of USFMBible.loadBooks

    def load( self ):
        self.loadBooks()
# end of class USFMBible



def briefDemo() -> None:
    """
    Demonstrate reading and checking some Bible databases.
    """
    import random

    BibleOrgSysGlobals.introduceProgram( __name__, programNameVersion, LAST_MODIFIED_DATE )

    if 0: # demo the file checking code -- first with the whole folder and then with only one folder
        for j,testFolder in enumerate( (
                            BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMTest1/' ),
                            BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMTest2/' ),
                            BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMTest3/' ),
                            BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFM2AllMarkersProject/' ),
                            BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFM3AllMarkersProject/' ),
                            BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMErrorProject/' ),
                            BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PTX7Test/' ),
                            BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_USFM2_Export/' ),
                            BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_USFM2_Reexport/' ),
                            BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_USFM3_Export/' ),
                            BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_USFM3_Reexport/' ),
                            'MadeUpFolder/',
                            ) ):
            vPrint( 'Quiet', debuggingThisModule, "\nUSFM A{} testfolder is: {}".format( j+1, testFolder ) )
            result1 = USFMBibleFileCheck( testFolder )
            vPrint( 'Normal', debuggingThisModule, "USFM TestAa", result1 )
            result2 = USFMBibleFileCheck( testFolder, autoLoad=True )
            vPrint( 'Normal', debuggingThisModule, "USFM TestAb", result2 )
            result3 = USFMBibleFileCheck( testFolder, autoLoadBooks=True )
            vPrint( 'Normal', debuggingThisModule, "USFM TestAc", result3 )
            if isinstance( result3, Bible ):
                if BibleOrgSysGlobals.strictCheckingFlag:
                    result3.check()
                    #dPrint( 'Quiet', debuggingThisModule, result3.books['GEN']._processedLines[0:40] )
                    UsfmBErrors = result3.getCheckResults()
                    # dPrint( 'Quiet', debuggingThisModule, UBErrors )
                if BibleOrgSysGlobals.commandLineArguments.export:
                    result3.pickle()
                    ##result3.toDrupalBible()
                    result3.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )

    BiblesFolderpath = Path( '/mnt/SSDs/Bibles/' )
    if 1: # Load and process some of our test versions
        name, encoding, testFolder = random.choice( (
                        ('ULT', 'utf-8', BiblesFolderpath.joinpath( 'English translations/unfoldingWordVersions/en_ult/' ) ),
                        ('UST', 'utf-8', BiblesFolderpath.joinpath( 'English translations/unfoldingWordVersions/en_ust/' ) ),
                        #('ULT', 'utf-8', BibleOrgSysGlobals.DEFAULT_WRITEABLE_DOWNLOADED_RESOURCES_FOLDERPATH.joinpath( 'Door43ContentServiceOnline/unfoldingWord--en_ult/en_ult/' ) ),
                        #('UST', 'utf-8', BibleOrgSysGlobals.DEFAULT_WRITEABLE_DOWNLOADED_RESOURCES_FOLDERPATH.joinpath( 'Door43ContentServiceOnline/unfoldingWord--en_ust/en_ust/' ) ),
                        #("Matigsalug", 'utf-8', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMTest1/') ),
                        #("Matigsalug", 'utf-8', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMTest2/') ),
                        #("Matigsalug", 'utf-8', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMTest3/') ),
                        #("USFM2", 'utf-8', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFM2AllMarkersProject/') ),
                        #("USFM3", 'utf-8', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFM3AllMarkersProject/') ),
                        #("UEP", 'utf-8', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMErrorProject/') ),
                        #("Exported2", 'utf-8', BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_USFM2_Export/') ),
                        #("Exported3", 'utf-8', BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_USFM3_Export/') ),
                        ) )
        if os.access( testFolder, os.R_OK ):
            vPrint( 'Quiet', debuggingThisModule, "\nUSFM B/" )
            UsfmB = USFMBible( testFolder, name, encoding=encoding )
            UsfmB.abbreviation = name
            if name in ('ULT','UST'): UsfmB.uWaligned = True
            UsfmB.load()
            if BibleOrgSysGlobals.verbosityLevel > 1:
                vPrint( 'Quiet', debuggingThisModule, "Gen assumed book name:", repr( UsfmB.getAssumedBookName( 'GEN' ) ) )
                vPrint( 'Quiet', debuggingThisModule, "Gen long TOC book name:", repr( UsfmB.getLongTOCName( 'GEN' ) ) )
                vPrint( 'Quiet', debuggingThisModule, "Gen short TOC book name:", repr( UsfmB.getShortTOCName( 'GEN' ) ) )
                vPrint( 'Quiet', debuggingThisModule, "Gen book abbreviation:", repr( UsfmB.getBooknameAbbreviation( 'GEN' ) ) )
            vPrint( 'Quiet', debuggingThisModule, UsfmB )
            UsfmB.analyseUWalignments()
            if BibleOrgSysGlobals.strictCheckingFlag:
                UsfmB.check()
                #dPrint( 'Quiet', debuggingThisModule, UsfmB.books['GEN']._processedLines[0:40] )
                UsfmBErrors = UsfmB.getCheckResults()
                # dPrint( 'Quiet', debuggingThisModule, UBErrors )
            if BibleOrgSysGlobals.commandLineArguments.export:
                UsfmB.pickle()
                ##UsfmB.toDrupalBible()
                UsfmB.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
                newObj = BibleOrgSysGlobals.unpickleObject( BibleOrgSysGlobals.makeSafeFilename(name) + '.pickle', os.path.join( "BOSOutputFiles/", "BOS_Bible_Object_Pickle/" ) )
                vPrint( 'Quiet', debuggingThisModule, "newObj is", newObj )
            if 0:
                from BibleOrgSys.Reference.VerseReferences import SimpleVerseKey
                from BibleOrgSys.Internals.InternalBibleInternals import InternalBibleEntry
                if BibleOrgSysGlobals.verbosityLevel > 0:
                    vPrint( 'Quiet', debuggingThisModule, "Displaying text from some given references…")
                for BBB,C,V in ( ('MAT','1','1'),('MAT','1','2'),('MAT','1','3'),('MAT','1','4'),('MAT','1','5'),('MAT','1','6'),('MAT','1','7'),('MAT','1','8') ):
                    svk = SimpleVerseKey( BBB, C, V )
                    shortText = svk.getShortText()
                    verseDataList = UsfmB.getVerseDataList( svk )
                    if BibleOrgSysGlobals.verbosityLevel > 0:
                        vPrint( 'Quiet', debuggingThisModule, "\n{}\n{}".format( shortText, verseDataList ) )
                    if verseDataList is None: continue
                    for verseDataEntry in verseDataList:
                        # This loop is used for several types of data
                        assert isinstance( verseDataEntry, InternalBibleEntry )
                        marker, cleanText, extras = verseDataEntry.getMarker(), verseDataEntry.getCleanText(), verseDataEntry.getExtras()
                        adjustedText, originalText = verseDataEntry.getAdjustedText(), verseDataEntry.getOriginalText()
                        fullText = verseDataEntry.getFullText()
                        if BibleOrgSysGlobals.verbosityLevel > 0:
                            vPrint( 'Quiet', debuggingThisModule, "marker={} cleanText={!r}{}".format( marker, cleanText,
                                                    " extras={}".format( extras ) if extras else '' ) )
                            if adjustedText and adjustedText!=cleanText:
                                vPrint( 'Quiet', debuggingThisModule, ' '*(len(marker)+4), "adjustedText={!r}".format( adjustedText ) )
                            if fullText and fullText!=cleanText:
                                vPrint( 'Quiet', debuggingThisModule, ' '*(len(marker)+4), "fullText={!r}".format( fullText ) )
                            if originalText and originalText!=cleanText:
                                vPrint( 'Quiet', debuggingThisModule, ' '*(len(marker)+4), "originalText={!r}".format( originalText ) )
        elif BibleOrgSysGlobals.verbosityLevel > 0:
            vPrint( 'Quiet', debuggingThisModule, f"\nSorry, test folder '{testFolder}' is not readable on this computer." )


    if 0: # Test a whole folder full of folders of USFM Bibles
        testBaseFolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'theWordRoundtripTestFiles/' )

        def findInfo( somepath ):
            """ Find out info about the project from the included copyright.htm file """
            cFilepath = os.path.join( somepath, "copyright.htm" )
            if not os.path.exists( cFilepath ): return
            with open( cFilepath ) as myFile: # Automatically closes the file when done
                lastLine, lineCount = None, 0
                title, nameDict = None, {}
                for line in myFile:
                    lineCount += 1
                    if lineCount==1:
                        if line[0]==chr(65279): #U+FEFF
                            logging.info( "USFMBible.findInfo1: Detected Unicode Byte Order Marker (BOM) in {}".format( "copyright.htm" ) )
                            line = line[1:] # Remove the UTF-16 Unicode Byte Order Marker (BOM)
                        elif line[:3] == 'ï»¿': # 0xEF,0xBB,0xBF
                            logging.info( "USFMBible.findInfo2: Detected Unicode Byte Order Marker (BOM) in {}".format( "copyright.htm" ) )
                            line = line[3:] # Remove the UTF-8 Unicode Byte Order Marker (BOM)
                    if line and line[-1]=='\n': line = line[:-1] # Removing trailing newline character
                    if not line: continue # Just discard blank lines
                    lastLine = line
                    if line.startswith("<title>"): title = line.replace("<title>","").replace("</title>","").strip()
                    if line.startswith('<option value="'):
                        adjLine = line.replace('<option value="','').replace('</option>','')
                        USFM_BBB, name = adjLine[:3], adjLine[11:]
                        BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromUSFMAbbreviation( USFM_BBB )
                        #dPrint( 'Quiet', debuggingThisModule, USFM_BBB, BBB, name )
                        nameDict[BBB] = name
            return title, nameDict
        # end of findInfo


        count = totalBooks = 0
        if os.access( testBaseFolder, os.R_OK ): # check that we can read the test data
            for something in sorted( os.listdir( testBaseFolder ) ):
                somepath = os.path.join( testBaseFolder, something )
                if os.path.isfile( somepath ): vPrint( 'Quiet', debuggingThisModule, "Ignoring file {!r} in {!r}".format( something, testBaseFolder ) )
                elif os.path.isdir( somepath ): # Let's assume that it's a folder containing a USFM (partial) Bible
                    #if not something.startswith( 'ssx' ): continue # This line is used for debugging only specific modules
                    count += 1
                    title = None
                    findInfoResult = findInfo( somepath )
                    if findInfoResult: title, bookNameDict = findInfoResult
                    if title is None: title = something[:-5] if something.endswith("_usfm") else something
                    name, encoding, testFolder = title, 'utf-8', somepath
                    if os.access( testFolder, os.R_OK ):
                        vPrint( 'Quiet', debuggingThisModule, "\nUSFM C{}/".format( count ) )
                        UsfmB = USFMBible( testFolder, name, encoding=encoding )
                        UsfmB.load()
                        vPrint( 'Quiet', debuggingThisModule, UsfmB )
                        if BibleOrgSysGlobals.strictCheckingFlag:
                            UsfmB.check()
                            UsfmBErrors = UsfmB.getCheckResults()
                            #dPrint( 'Quiet', debuggingThisModule, UsfmBErrors )
                        if BibleOrgSysGlobals.commandLineArguments.export:
                            UsfmB.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
                    else: vPrint( 'Quiet', debuggingThisModule, f"\nSorry, test folder '{testFolder}' is not readable on this computer." )
            if count: vPrint( 'Quiet', debuggingThisModule, f"\n{count} total USFM (partial) Bibles processed." )
            if totalBooks: vPrint( 'Quiet', debuggingThisModule, f"{totalBooks} total books ({round(totalBooks/count)} average per folder)" )
        elif BibleOrgSysGlobals.verbosityLevel > 0:
            vPrint( 'Quiet', debuggingThisModule, f"\nSorry, test folder '{testBaseFolder}' is not readable on this computer." )
#end of USFMBible.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, programNameVersion, LAST_MODIFIED_DATE )

    if 0: # demo the file checking code -- first with the whole folder and then with only one folder
        for j,testFolder in enumerate( (
                            BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMTest1/' ),
                            BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMTest2/' ),
                            BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMTest3/' ),
                            BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFM2AllMarkersProject/' ),
                            BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFM3AllMarkersProject/' ),
                            BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMErrorProject/' ),
                            BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PTX7Test/' ),
                            BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_USFM2_Export/' ),
                            BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_USFM2_Reexport/' ),
                            BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_USFM3_Export/' ),
                            BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_USFM3_Reexport/' ),
                            'MadeUpFolder/',
                            ) ):
            vPrint( 'Quiet', debuggingThisModule, "\nUSFM A{} testfolder is: {}".format( j+1, testFolder ) )
            result1 = USFMBibleFileCheck( testFolder )
            vPrint( 'Normal', debuggingThisModule, "USFM TestAa", result1 )
            result2 = USFMBibleFileCheck( testFolder, autoLoad=True )
            vPrint( 'Normal', debuggingThisModule, "USFM TestAb", result2 )
            result3 = USFMBibleFileCheck( testFolder, autoLoadBooks=True )
            vPrint( 'Normal', debuggingThisModule, "USFM TestAc", result3 )
            if isinstance( result3, Bible ):
                if BibleOrgSysGlobals.strictCheckingFlag:
                    result3.check()
                    #dPrint( 'Quiet', debuggingThisModule, result3.books['GEN']._processedLines[0:40] )
                    UsfmBErrors = result3.getCheckResults()
                    # dPrint( 'Quiet', debuggingThisModule, UBErrors )
                if BibleOrgSysGlobals.commandLineArguments.export:
                    result3.pickle()
                    ##result3.toDrupalBible()
                    result3.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )

    BiblesFolderpath = Path( '/mnt/SSDs/Bibles/' )
    if 1: # Load and process some of our test versions
        for j,(name, encoding, testFolder) in enumerate( (
                        ('ULT', 'utf-8', BiblesFolderpath.joinpath( 'English translations/unfoldingWordVersions/en_ult/' ) ),
                        ('UST', 'utf-8', BiblesFolderpath.joinpath( 'English translations/unfoldingWordVersions/en_ust/' ) ),
                        #('ULT', 'utf-8', BibleOrgSysGlobals.DEFAULT_WRITEABLE_DOWNLOADED_RESOURCES_FOLDERPATH.joinpath( 'Door43ContentServiceOnline/unfoldingWord--en_ult/en_ult/' ) ),
                        #('UST', 'utf-8', BibleOrgSysGlobals.DEFAULT_WRITEABLE_DOWNLOADED_RESOURCES_FOLDERPATH.joinpath( 'Door43ContentServiceOnline/unfoldingWord--en_ust/en_ust/' ) ),
                        #("Matigsalug", 'utf-8', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMTest1/') ),
                        #("Matigsalug", 'utf-8', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMTest2/') ),
                        #("Matigsalug", 'utf-8', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMTest3/') ),
                        #("USFM2", 'utf-8', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFM2AllMarkersProject/') ),
                        #("USFM3", 'utf-8', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFM3AllMarkersProject/') ),
                        #("UEP", 'utf-8', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMErrorProject/') ),
                        #("Exported2", 'utf-8', BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_USFM2_Export/') ),
                        #("Exported3", 'utf-8', BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_USFM3_Export/') ),
                        ) ):
            if os.access( testFolder, os.R_OK ):
                vPrint( 'Quiet', debuggingThisModule, "\nUSFM B{}/".format( j+1 ) )
                UsfmB = USFMBible( testFolder, name, encoding=encoding )
                UsfmB.abbreviation = name
                if name in ('ULT','UST'): UsfmB.uWaligned = True
                UsfmB.load()
                if BibleOrgSysGlobals.verbosityLevel > 1:
                    vPrint( 'Quiet', debuggingThisModule, "Gen assumed book name:", repr( UsfmB.getAssumedBookName( 'GEN' ) ) )
                    vPrint( 'Quiet', debuggingThisModule, "Gen long TOC book name:", repr( UsfmB.getLongTOCName( 'GEN' ) ) )
                    vPrint( 'Quiet', debuggingThisModule, "Gen short TOC book name:", repr( UsfmB.getShortTOCName( 'GEN' ) ) )
                    vPrint( 'Quiet', debuggingThisModule, "Gen book abbreviation:", repr( UsfmB.getBooknameAbbreviation( 'GEN' ) ) )
                vPrint( 'Quiet', debuggingThisModule, UsfmB )
                UsfmB.analyseUWalignments()
                if BibleOrgSysGlobals.strictCheckingFlag:
                    UsfmB.check()
                    #dPrint( 'Quiet', debuggingThisModule, UsfmB.books['GEN']._processedLines[0:40] )
                    UsfmBErrors = UsfmB.getCheckResults()
                    # dPrint( 'Quiet', debuggingThisModule, UBErrors )
                if BibleOrgSysGlobals.commandLineArguments.export:
                    UsfmB.pickle()
                    ##UsfmB.toDrupalBible()
                    UsfmB.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
                    newObj = BibleOrgSysGlobals.unpickleObject( BibleOrgSysGlobals.makeSafeFilename(name) + '.pickle', os.path.join( "BOSOutputFiles/", "BOS_Bible_Object_Pickle/" ) )
                    vPrint( 'Quiet', debuggingThisModule, "newObj is", newObj )
                if 0:
                    from BibleOrgSys.Reference.VerseReferences import SimpleVerseKey
                    from BibleOrgSys.Internals.InternalBibleInternals import InternalBibleEntry
                    if BibleOrgSysGlobals.verbosityLevel > 0:
                        vPrint( 'Quiet', debuggingThisModule, "Displaying text from some given references…")
                    for BBB,C,V in ( ('MAT','1','1'),('MAT','1','2'),('MAT','1','3'),('MAT','1','4'),('MAT','1','5'),('MAT','1','6'),('MAT','1','7'),('MAT','1','8') ):
                        svk = SimpleVerseKey( BBB, C, V )
                        shortText = svk.getShortText()
                        verseDataList = UsfmB.getVerseDataList( svk )
                        if BibleOrgSysGlobals.verbosityLevel > 0:
                            vPrint( 'Quiet', debuggingThisModule, "\n{}\n{}".format( shortText, verseDataList ) )
                        if verseDataList is None: continue
                        for verseDataEntry in verseDataList:
                            # This loop is used for several types of data
                            assert isinstance( verseDataEntry, InternalBibleEntry )
                            marker, cleanText, extras = verseDataEntry.getMarker(), verseDataEntry.getCleanText(), verseDataEntry.getExtras()
                            adjustedText, originalText = verseDataEntry.getAdjustedText(), verseDataEntry.getOriginalText()
                            fullText = verseDataEntry.getFullText()
                            if BibleOrgSysGlobals.verbosityLevel > 0:
                                vPrint( 'Quiet', debuggingThisModule, "marker={} cleanText={!r}{}".format( marker, cleanText,
                                                        " extras={}".format( extras ) if extras else '' ) )
                                if adjustedText and adjustedText!=cleanText:
                                    vPrint( 'Quiet', debuggingThisModule, ' '*(len(marker)+4), "adjustedText={!r}".format( adjustedText ) )
                                if fullText and fullText!=cleanText:
                                    vPrint( 'Quiet', debuggingThisModule, ' '*(len(marker)+4), "fullText={!r}".format( fullText ) )
                                if originalText and originalText!=cleanText:
                                    vPrint( 'Quiet', debuggingThisModule, ' '*(len(marker)+4), "originalText={!r}".format( originalText ) )
            elif BibleOrgSysGlobals.verbosityLevel > 0:
                vPrint( 'Quiet', debuggingThisModule, f"\nSorry, test folder '{testFolder}' is not readable on this computer." )


    if 0: # Test a whole folder full of folders of USFM Bibles
        testBaseFolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'theWordRoundtripTestFiles/' )

        def findInfo( somepath ):
            """ Find out info about the project from the included copyright.htm file """
            cFilepath = os.path.join( somepath, "copyright.htm" )
            if not os.path.exists( cFilepath ): return
            with open( cFilepath ) as myFile: # Automatically closes the file when done
                lastLine, lineCount = None, 0
                title, nameDict = None, {}
                for line in myFile:
                    lineCount += 1
                    if lineCount==1:
                        if line[0]==chr(65279): #U+FEFF
                            logging.info( "USFMBible.findInfo1: Detected Unicode Byte Order Marker (BOM) in {}".format( "copyright.htm" ) )
                            line = line[1:] # Remove the UTF-16 Unicode Byte Order Marker (BOM)
                        elif line[:3] == 'ï»¿': # 0xEF,0xBB,0xBF
                            logging.info( "USFMBible.findInfo2: Detected Unicode Byte Order Marker (BOM) in {}".format( "copyright.htm" ) )
                            line = line[3:] # Remove the UTF-8 Unicode Byte Order Marker (BOM)
                    if line and line[-1]=='\n': line = line[:-1] # Removing trailing newline character
                    if not line: continue # Just discard blank lines
                    lastLine = line
                    if line.startswith("<title>"): title = line.replace("<title>","").replace("</title>","").strip()
                    if line.startswith('<option value="'):
                        adjLine = line.replace('<option value="','').replace('</option>','')
                        USFM_BBB, name = adjLine[:3], adjLine[11:]
                        BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromUSFMAbbreviation( USFM_BBB )
                        #dPrint( 'Quiet', debuggingThisModule, USFM_BBB, BBB, name )
                        nameDict[BBB] = name
            return title, nameDict
        # end of findInfo


        count = totalBooks = 0
        if os.access( testBaseFolder, os.R_OK ): # check that we can read the test data
            for something in sorted( os.listdir( testBaseFolder ) ):
                somepath = os.path.join( testBaseFolder, something )
                if os.path.isfile( somepath ): vPrint( 'Quiet', debuggingThisModule, "Ignoring file {!r} in {!r}".format( something, testBaseFolder ) )
                elif os.path.isdir( somepath ): # Let's assume that it's a folder containing a USFM (partial) Bible
                    #if not something.startswith( 'ssx' ): continue # This line is used for debugging only specific modules
                    count += 1
                    title = None
                    findInfoResult = findInfo( somepath )
                    if findInfoResult: title, bookNameDict = findInfoResult
                    if title is None: title = something[:-5] if something.endswith("_usfm") else something
                    name, encoding, testFolder = title, 'utf-8', somepath
                    if os.access( testFolder, os.R_OK ):
                        vPrint( 'Quiet', debuggingThisModule, "\nUSFM C{}/".format( count ) )
                        UsfmB = USFMBible( testFolder, name, encoding=encoding )
                        UsfmB.load()
                        vPrint( 'Quiet', debuggingThisModule, UsfmB )
                        if BibleOrgSysGlobals.strictCheckingFlag:
                            UsfmB.check()
                            UsfmBErrors = UsfmB.getCheckResults()
                            #dPrint( 'Quiet', debuggingThisModule, UsfmBErrors )
                        if BibleOrgSysGlobals.commandLineArguments.export:
                            UsfmB.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
                    else: vPrint( 'Quiet', debuggingThisModule, f"\nSorry, test folder '{testFolder}' is not readable on this computer." )
            if count: vPrint( 'Quiet', debuggingThisModule, f"\n{count} total USFM (partial) Bibles processed." )
            if totalBooks: vPrint( 'Quiet', debuggingThisModule, f"{totalBooks} total books ({round(totalBooks/count)} average per folder)" )
        elif BibleOrgSysGlobals.verbosityLevel > 0:
            vPrint( 'Quiet', debuggingThisModule, f"\nSorry, test folder '{testBaseFolder}' is not readable on this computer." )
# end of USFMBible.fullDemo

if __name__ == '__main__':
    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    fullDemo()

    BibleOrgSysGlobals.closedown( SHORT_PROGRAM_NAME, PROGRAM_VERSION )
# end of USFMBible.py
