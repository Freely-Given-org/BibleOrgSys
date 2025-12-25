#!/usr/bin/env python3
# -\*- coding: utf-8 -\*-
# SPDX-License-Identifier: GPL-3.0-or-later
#
# CSVBible.py
#
# Module handling comma-separated-values and tab-separated_values text Bible files
#
# Copyright (C) 2014-2025 Robert Hunt
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
#   along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
Module reading and loading comma-separated-values (CSV) and tab-separated_values (TSV) text Bible files.

e.g.,
    "Book","Chapter","Verse","Scripture"
    "1","1","1","Cuando Dios, en el principio, creó* los cielos y la tierra,"
    "1","1","2","la tierra era una masa caótica* y las tinieblas cubrían el abismo, mientras un viento impetuoso sacudía la superficie de las aguas."
    "1","1","3","Entonces dijo Dios: — ¡Que exista la luz! Y la luz existió."
    …
    "66","22","19","Si suprime algo del mensaje profético del libro, Dios lo desgajará del árbol de la vida y lo excluirá de la ciudad santa descritos en este libro."
    "66","22","20","El que da fe de todo esto proclama: — Sí, estoy a punto de llegar. ¡Amén! ¡Ven, Señor Jesús!"
    "66","22","21","Que la gracia de Jesús, el Señor, esté con todos. Amén."

Note: CSV can also be used for a generic term and include tab-separated values
        or include separators other than commas. (Modified May 2022)
e.g.,
    Book|Chapter|Verse|Text
    Gen|1|1|<pb/>In the beginning when God created <f>[1]</f> the heavens and the earth,
    Gen|1|2|the earth was a formless void and darkness covered the face of the deep, while a wind from God <f>[2]</f> swept over the face of the waters.
    Gen|1|3|Then God said, ‘Let there be light’; and there was light.

CHANGELOG:
    2023-02-01 Allowed for multiple files as well as one single file for the whole Bible
                TODO: It hasn't been fully tested, and filecheck has not yet been updated to reflect this
    2023-05-30 Allow for a filepath to be given to the class (as well as a folderpath)
    2025-09-02 Handle CSV folder with books in separate files
    2025-09-27 Added (exported) BibleHub TSV spreadsheet/table format
    2025-11-20 Added our wordtables for BibleHub TSV spreadsheet/table format
"""
from gettext import gettext as _
from pathlib import Path
import logging
import os
import re
import multiprocessing

# BibleOrgSys imports
if __name__ == '__main__':
    import sys
    aboveAboveFolderpath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderpath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderpath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys.Bible import Bible, BibleBook
from BibleOrgSys.OriginalLanguages import Hebrew, Greek


LAST_MODIFIED_DATE = '2025-12-09' # by RJH
SHORT_PROGRAM_NAME = "CSVBible"
PROGRAM_NAME = "CSV Bible format handler"
PROGRAM_VERSION = '0.48'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False


FILENAME_ENDINGS_TO_IGNORE = ('.ZIP.GO', '.ZIP.DATA',) # Must be UPPERCASE
EXTENSION_TO_IGNORE = ('ZIP', 'BAK', 'BAK2', 'BAK3', 'BAK4', 'LOG', 'HTM','HTML', 'XML', 'OSIS', 'USX',
                      'STY', 'LDS', 'SSF', 'VRS', 'ASC', 'CSS', 'ODT','DOC', 'JAR', 'SAVE', 'SAV' ) # Must be UPPERCASE



def CSVBibleFileCheck( givenFolderName, strictCheck:bool=True, autoLoad:bool=False, autoLoadBooks:bool=False ):
    """
    Given a folder, search for CSV or TSV Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number of Bibles found.

    if autoLoad is true and exactly one CSV Bible is found,
        returns the loaded CSVBible object.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"CSVBibleFileCheck( {givenFolderName}, {strictCheck}, {autoLoad}, {autoLoadBooks} )" )
    if BibleOrgSysGlobals.debugFlag:
        assert givenFolderName and isinstance( givenFolderName, (str,Path) )
        assert autoLoad in (True,False,) and autoLoadBooks in (True,False,)

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( _("CSVBibleFileCheck: Given {!r} folder is unreadable").format( givenFolderName ) )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( _("CSVBibleFileCheck: Given {!r} path is not a folder").format( givenFolderName ) )
        return False

    # Find all the files and folders in this folder
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, " CSVBibleFileCheck: Looking for files in given {!r}".format( givenFolderName ) )
    foundFolders, foundFiles = [], []
    for something in os.listdir( givenFolderName ):
        somepath = os.path.join( givenFolderName, something )
        if os.path.isdir( somepath ):
            if something in BibleOrgSysGlobals.COMMONLY_IGNORED_FOLDERS:
                continue # don't visit these directories
            foundFolders.append( something )
        elif os.path.isfile( somepath ):
            somethingUpper = something.upper()
            somethingUpperProper, somethingUpperExt = os.path.splitext( somethingUpper )
            ignore = False
            for ending in FILENAME_ENDINGS_TO_IGNORE:
                if somethingUpper.endswith( ending): ignore=True; break
            if ignore: continue
            if not somethingUpperExt[1:] in EXTENSION_TO_IGNORE: # Compare without the first dot
                foundFiles.append( something )

    # See if there's an CSV or TSV Bible here in this given folder
    numFound = 0
    looksHopeful = False
    lastFilenameFound = None
    for thisFilename in sorted( foundFiles ):
        if thisFilename in ('book_names.txt','Readme.txt' ): looksHopeful = True
        elif thisFilename.endswith( '.csv' ) or thisFilename.endswith( '.tsv' ) or thisFilename.endswith( '.txt' ):
            if strictCheck or BibleOrgSysGlobals.strictCheckingFlag:
                firstLine = BibleOrgSysGlobals.peekIntoFile( thisFilename, givenFolderName )
                if firstLine is None: continue # seems we couldn't decode the file
                if not firstLine.startswith( '"Book","Chapter","Verse",' ) and not firstLine.startswith( '"1","1","1",') \
                and not firstLine.startswith( 'Book,Chapter,Verse,' ) and not firstLine.startswith( '1,1,1,') \
                and not firstLine.startswith( 'Book|Chapter|Verse|' ) \
                and not '\tBSB Sort\t' in firstLine and not '\tMSB Sort\t' in firstLine:
                    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, "CSVBibleFileCheck: (unexpected) first line was {!r} in {}".format( firstLine, thisFilename ) )
                    continue
            lastFilenameFound = thisFilename
            numFound += 1
    if numFound:
        vPrint( 'Info', DEBUGGING_THIS_MODULE, "CSVBibleFileCheck got", numFound, givenFolderName, lastFilenameFound )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            uB = CSVBible( givenFolderName, lastFilenameFound[:-4] ) # Remove the end of the actual filename ".txt"
            if autoLoadBooks: uB.load() # Load and process the file
            return uB
        return numFound
    elif looksHopeful and BibleOrgSysGlobals.verbosityLevel > 2: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "    Looked hopeful but no actual files found" )

    # Look one level down
    numFound = 0
    foundProjects = []
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
        if not os.access( tryFolderName, os.R_OK ): # The subfolder is not readable
            logging.warning( _("CSVBibleFileCheck: {!r} subfolder is unreadable").format( tryFolderName ) )
            continue
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, "    CSVBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
        foundSubfolders, foundSubfiles = [], []
        try:
            for something in os.listdir( tryFolderName ):
                somepath = os.path.join( givenFolderName, thisFolderName, something )
                if os.path.isdir( somepath ): foundSubfolders.append( something )
                elif os.path.isfile( somepath ):
                    somethingUpper = something.upper()
                    somethingUpperProper, somethingUpperExt = os.path.splitext( somethingUpper )
                    ignore = False
                    for ending in FILENAME_ENDINGS_TO_IGNORE:
                        if somethingUpper.endswith( ending): ignore=True; break
                    if ignore: continue
                    if not somethingUpperExt[1:] in EXTENSION_TO_IGNORE: # Compare without the first dot
                        foundSubfiles.append( something )
        except PermissionError: pass # can't read folder, e.g., system folder

        # See if there's an CSV Bible here in this folder
        for thisFilename in sorted( foundSubfiles ):
            if thisFilename.endswith( '.csv' ) or thisFilename.endswith( '.txt' ):
                if strictCheck or BibleOrgSysGlobals.strictCheckingFlag:
                    firstLine = BibleOrgSysGlobals.peekIntoFile( thisFilename, tryFolderName )
                    if firstLine is None: continue # seems we couldn't decode the file
                    if not firstLine.startswith( '"Book","Chapter","Verse",' ) and not firstLine.startswith( '"1","1","1",') \
                    and not firstLine.startswith( 'Book,Chapter,Verse,' ) and not firstLine.startswith( '1,1,1,') \
                    and not firstLine.startswith( 'Book|Chapter|Verse|' ):
                        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, "CSVBibleFileCheck: (unexpected) first line was {!r} in {}".format( firstLine, thisFilename ) )
                        if DEBUGGING_THIS_MODULE: halt
                        continue
                foundProjects.append( (tryFolderName, thisFilename,) )
                lastFilenameFound = thisFilename
                numFound += 1
    if numFound:
        vPrint( 'Info', DEBUGGING_THIS_MODULE, "CSVBibleFileCheck foundProjects", numFound, foundProjects )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            if BibleOrgSysGlobals.debugFlag: assert len(foundProjects) == 1
            uB = CSVBible( foundProjects[0][0], foundProjects[0][1][:-4] ) # Remove the end of the actual filename ".txt"
            if autoLoadBooks: uB.load() # Load and process the file
            return uB
        return numFound
# end of CSVBibleFileCheck



class CSVBible( Bible ):
    """
    Class for reading, validating, and converting CSV or TSV Bible files.
    """
    def __init__( self, sourceFileOrFolder, givenName:str, givenAbbreviation:str|None=None, encoding:str|None=None ) -> None:
        """
        Constructor: just sets up the Bible object.
        """
        fnPrint( DEBUGGING_THIS_MODULE, f"CSVBible.__init__( '{sourceFileOrFolder}', gN='{givenName}', gA='{givenAbbreviation}', e='{encoding}' )" )
        # self.doExtraChecking = DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag
        assert givenName != 'utf-8'
        assert givenAbbreviation != 'utf-8'

         # Setup and initialise the base class first
        super().__init__()
        self.objectNameString = 'CSV Bible object'
        self.objectTypeString = 'CSV'

        # Now we can set our object variables
        self.givenName, self.abbreviation, self.encoding = givenName, givenAbbreviation, encoding
        if self.givenName and not self.name:
            self.name = self.givenName
        self.sourceBookFileExtension = None
        if os.path.isfile( sourceFileOrFolder ):
            self.sourceFilepath = Path( sourceFileOrFolder )
            self.sourceFolder = self.sourceFilepath.parent
            self.sourceFilename = self.sourceFilepath.name
        elif os.path.isdir( sourceFileOrFolder ):
            self.sourceFolder = sourceFileOrFolder
            # NOTE: The following loop assumes one file for the entire work
            #           but load() can also handle one file per book
            for self.sourceFilename in (f'{self.givenName}.csv',f'{self.givenName}.CSV',
                                        f'{self.givenName}.tsv',f'{self.givenName}.TSV',
                                        f'{self.givenName}.txt',f'{self.givenName}.TXT',
                                        self.givenName,
                                        f'{self.abbreviation}.csv',f'{self.abbreviation}.CSV', f'{self.abbreviation.lower()}.csv',f'{self.abbreviation.lower()}.CSV',
                                        f'{self.abbreviation}.tsv',f'{self.abbreviation}.TSV', f'{self.abbreviation.lower()}.tsv',f'{self.abbreviation.lower()}.TSV',
                                        f'{self.abbreviation}.txt',f'{self.abbreviation}.TXT', f'{self.abbreviation.lower()}.txt',f'{self.abbreviation.lower()}.TXT',
                                        self.abbreviation,
                                        ):
                self.sourceFilepath =  os.path.join( self.sourceFolder, self.sourceFilename )
                # Do a preliminary check on the readability of our file
                if os.access( self.sourceFilepath, os.R_OK ): # great -- found it
                    break
            else: # no whole Bible files found -- might be a folder of separate book files
                self.sourceFilename = self.sourceFilepath = None
                bookFileCount = 0
                for filename in os.listdir( sourceFileOrFolder ):
                    # dPrint( 'Info', DEBUGGING_THIS_MODULE, f"{filename=}" )
                    filepath = os.path.join( self.sourceFolder, filename )
                    if os.path.isfile( filepath ) \
                    and ( filename.lower().endswith( '.csv' ) or filename.lower().endswith( '.tsv' ) or filename.lower().endswith( '.txt' ) ):
                        for Uuu in BibleOrgSysGlobals.loadedBibleBooksCodes.getAllUSFMBooksCodes():
                            # dPrint( 'Info', DEBUGGING_THIS_MODULE, f"{Uuu=}" )
                            if Uuu in filename or Uuu.upper() in filename or Uuu.lower() in filename:
                                bookFileCount += 1
                                break
                        if bookFileCount > 5: # Found enough to be pretty sure
                            self.sourceBookFileExtension = filename[-3:]
                            break
                else: # no files found
                    logging.critical( _("CSVBible: Unable to discover a single filename in {}".format( self.sourceFolder )) )
    # end of CSVBible.__init__


    def _loadFile( self, filepath:Path|str, temporaryBookStore:dict|None=None ) -> Bible:
        """
        Does the work of loading a CSV file into memory.

        Parameter 'temporaryBookStore' is optionally used to save the books
            (because we don't always load them in the correct order)
        """
        fnPrint( DEBUGGING_THIS_MODULE, f"CSVBible._loadFile( {filepath}, {temporaryBookStore} )")
        vPrint( 'Info', DEBUGGING_THIS_MODULE, _("  Loading {}…").format( filepath ) )

        haveBereanWordSpreadsheet = False
        separator = numColumns = quoted = BBB = None # Empty defaults
        lastLine, lineCount = '', 0
        bookNumber = lastBookNumber = lastChapterNumber = lastVerseNumber = -1
        lastVText = ''
        with open( filepath, encoding=self.encoding ) as myFile: # Automatically closes the file when done
            for line in myFile:
                lineCount += 1
                #if lineCount==1 and self.encoding.lower()=='utf-8' and line[0]==BibleOrgSysGlobals.BOM:
                    #logging.info( "      CSVBible.load: Detected Unicode Byte Order Marker (BOM)" )
                    #line = line[1:] # Remove the Unicode Byte Order Marker (BOM)
                if line and line[-1]=='\n': line=line[:-1] # Removing trailing newline character
                if not line: continue # Just discard blank lines
                if line==' ': continue # Handle special case which has blanks on every second line -- HACK
                lastLine = line
                dPrint( 'Info', DEBUGGING_THIS_MODULE, "CSV file line {} is {!r}".format( lineCount, line ) )
                if line[0]=='#': continue # Just discard comment lines
                if not separator and lineCount < 4:
                    if line.startswith( '"Book",' ):
                        separator, quoted, numColumns = ',', True, 4
                        continue # Just discard header line
                    elif line.startswith( 'Book,' ):
                        separator, quoted, numColumns = ',', False, 4
                        continue # Just discard header line
                    elif line.startswith( '"Book"|' ):
                        separator, quoted, numColumns = '|', True, 4
                        continue # Just discard header line
                    elif line.startswith( 'Book|' ):
                        separator, quoted, numColumns = '|', False, 4
                        continue # Just discard header line
                    elif line.startswith( 'chapter,' ):
                        separator, quoted, numColumns = ',', False, 3
                        continue # Just discard header line
                    elif '\t' in line:
                        separator = '\t'
                        numColumns = line.count( '\t' ) + 1
                    elif ',' in line:
                        separator = ','
                        numColumns = line.count( ',' ) + 1 # Might be wrong if text is quoted
                    if not separator: continue # keep searching
                if lineCount <= 3: dPrint( 'Info', DEBUGGING_THIS_MODULE, f"{lineCount}: {separator=} {numColumns=} {quoted=} {BBB=}" )

                bits = line.split( separator, numColumns-1 )
                dPrint( 'Info', DEBUGGING_THIS_MODULE, lineCount, self.givenName, BBB, bits )
                if len(bits) == 4:
                    booknameString, chapterNumberString, verseNumberString, vText = bits
                    dPrint( 'Info', DEBUGGING_THIS_MODULE, f"{booknameString=}, {chapterNumberString=}, {verseNumberString=}, {vText=}" )
                elif len(bits) == 3:
                    chapterNumberString, verseNumberString, vText = bits
                    dPrint( 'Info', DEBUGGING_THIS_MODULE, f"{chapterNumberString=}, {verseNumberString=}, {vText=}" )
                    booknameString = ''
                elif len(bits) == 2:
                    refString, vText = bits
                    if BBB is None and refString.count(':') != 1:
                        dPrint( 'Info', DEBUGGING_THIS_MODULE, f"Skipping the rest of 2-bit line because no BBB yet: {lineCount}: {bits} '{line}'" )
                        continue # Still in header lines ???
                    booknameString, CV = refString.rsplit( ' ', 1) # e.g., Genesis 1:1, 3 John 1:2, Song of Songs 2:3
                    assert 0 <= booknameString.count( ' ' ) <= 3, f"{booknameString=}"
                    assert CV.count( ':' ) == 1
                    chapterNumberString, verseNumberString = CV.split( ':' )
                elif len(bits) >= 20 and 'Hdg' in bits and 'Crossref' in bits and 'Par' in bits and ('Pnc' in bits or 'pnc' in bits):
                    dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Have a likely Berean word table with {self.givenName=} {numColumns=}: {lineCount}: {bits} '{line}'" )
                    haveBereanWordSpreadsheet = True
                    break # We'll use a separate function for this
                else:
                    logging.critical( f"Unexpected number of {'CSV' if separator==',' else 'TSV'} bits {self.givenName=} {BBB=} {line=} ({len(bits)}) {bits=}" )

                # Remove quote marks from these strings
                if 1 or quoted:
                    if len(booknameString)>=2 and booknameString[0]==booknameString[-1] and booknameString[0] in '"\'': booknameString = booknameString[1:-1]
                    if len(chapterNumberString)>=2 and chapterNumberString[0]==chapterNumberString[-1] and chapterNumberString[0] in '"\'': chapterNumberString = chapterNumberString[1:-1]
                    if len(verseNumberString)>=2 and verseNumberString[0]==verseNumberString[-1] and verseNumberString[0] in '"\'': verseNumberString = verseNumberString[1:-1]
                    if len(vText)>=2 and vText[0]==vText[-1] and vText[0] in '"\'': vText = vText[1:-1]
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "bString, chapterNumberString, verseNumberString, vText", bString, chapterNumberString, verseNumberString, vText )

                #if not bookCode and not chapterNumberString and not verseNumberString:
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Skipping empty line in {} {} {} {}:{}".format( self.givenName, BBB, bookCode, chapterNumberString, verseNumberString ) )
                    #continue
                #if BibleOrgSysGlobals.debugFlag: assert 2  <= len(bookCode) <= 4
                #if BibleOrgSysGlobals.debugFlag: assert chapterNumberString.isdigit()
                #if BibleOrgSysGlobals.debugFlag: assert verseNumberString.isdigit()
                dPrint( 'Never', DEBUGGING_THIS_MODULE, f"  Now have {lineCount}: {booknameString=} {chapterNumberString=} {verseNumberString=}" )
                if booknameString:
                    try: bookNumber = int( booknameString )
                    except ValueError: # Assume it's a book code of some sort or a book name
                        BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromEnglishText( booknameString )
                        if BBB:
                            bookNumber = BibleOrgSysGlobals.loadedBibleBooksCodes.getReferenceNumber( BBB )
                elif not BBB: # Try the filename
                    thisFilepath = Path(filepath) if isinstance( filepath, str ) else filepath
                    filename = thisFilepath.stem
                    dPrint( 'Info', DEBUGGING_THIS_MODULE, f"{filename=}" )
                    try: BBB = {'AC':'ACT', 'JOH':'JHN', 'MT':'MAT', 'JUDE':'JDE', '1JO':'JN1','2JO':'JN2','3JO':'JN3'}[filename]
                    except KeyError: pass # no problem
                    if not BBB:
                        if len(filename) == 3:
                            for tryBBB in BibleOrgSysGlobals.loadedBibleBooksCodes:
                                if filename.upper() == tryBBB:
                                    BBB = tryBBB
                                    break
                            if not BBB:
                                for Uuu in BibleOrgSysGlobals.loadedBibleBooksCodes.getAllUSFMBooksCodes():
                                    if filename.upper() == Uuu.upper():
                                        BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromUSFMAbbreviation( Uuu )
                                        break
                        elif len(filename) == 2:
                            for tryBBB in BibleOrgSysGlobals.loadedBibleBooksCodes:
                                if tryBBB.startswith( filename.upper() ):
                                    BBB = tryBBB
                                    break
                            if not BBB:
                                for Uuu in BibleOrgSysGlobals.loadedBibleBooksCodes.getAllUSFMBooksCodes():
                                    if Uuu.upper().startswith( filename.upper ):
                                        BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromUSFMAbbreviation( Uuu )
                                        break
                    if BBB:
                        dPrint( 'Info', DEBUGGING_THIS_MODULE, f"Got {BBB=}" )
                        bookNumber = BibleOrgSysGlobals.loadedBibleBooksCodes.getReferenceNumber( BBB )
                        dPrint( 'Info', DEBUGGING_THIS_MODULE, f"Got {bookNumber=}" )
                    else:
                        dPrint( 'Info', DEBUGGING_THIS_MODULE, f"Got {filename=} {booknameString=} {BBB=} {bookNumber=}" )
                        halt

                if lastBookNumber==-1 and not BBB:
                    dPrint( 'Never', DEBUGGING_THIS_MODULE, f"Skipping the rest of (introductory?) line because no BBB yet: {lineCount}: '{line}'" )
                    continue

                chapterNumber = int( chapterNumberString )
                verseNumber = int( verseNumberString )
                dPrint( 'Never', DEBUGGING_THIS_MODULE, f"    which gives: {bookNumber=} {BBB=} {chapterNumber=} {verseNumber=}" )

                if bookNumber != lastBookNumber: # We've started a new book
                    if lastBookNumber != -1: # Better save the last book
                        dPrint( 'Info', DEBUGGING_THIS_MODULE, f"Stashing previous {self.abbreviation} book: {thisBook.BBB=}…" )
                        if temporaryBookStore is not None: temporaryBookStore[thisBook.BBB] = thisBook
                        else: self.stashBook( thisBook )
                        dPrint( 'Info', DEBUGGING_THIS_MODULE, f"    Now have {len(temporaryBookStore)=} books: {temporaryBookStore.keys()=}." )
                    BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromReferenceNumber( bookNumber )  # Try to guess
                    assert BBB
                    thisBook = BibleBook( self, BBB )
                    thisBook.objectNameString = 'CSV Bible Book object'
                    thisBook.objectTypeString = 'CSV'
                    lastBookNumber = bookNumber
                    lastChapterNumber = lastVerseNumber = -1
                if chapterNumber != lastChapterNumber: # We've started a new chapter
                    if BibleOrgSysGlobals.debugFlag: assert chapterNumber > lastChapterNumber or BBB=='ESG' # Esther Greek might be an exception
                    if chapterNumber == 0:
                        logging.info( "Have chapter zero in {} {} {} {}:{}".format( self.givenName, BBB, bookNumber, chapterNumberString, verseNumberString ) )
                    thisBook.addLine( 'c', chapterNumberString )
                    lastChapterNumber = chapterNumber
                    lastVerseNumber = -1

                # Now we have to convert any possible RTF codes to our internal codes
                vTextOriginal = vText
                # First do special characters
                vText = vText.replace( '\\ldblquote', '“' ).replace( '\\rdblquote', '”' ).replace( '\\lquote', '‘' ).replace( '\\rquote', '’' )
                vText = vText.replace( '\\emdash', '—' ).replace( '\\endash', '–' )
                # Now do Unicode characters
                while True: # Find patterns like \\'d3
                    match = re.search( r"\\'[0-9a-f][0-9a-f]", vText )
                    if not match: break
                    i = int( vText[match.start()+2:match.end()], 16 ) # Convert two hex characters to decimal
                    vText = vText[:match.start()] + chr( i ) + vText[match.end():]
                while True: # Find patterns like \\u253?
                    match = re.search( r"\\u[1-2][0-9][0-9]\?", vText )
                    if not match: break
                    i = int( vText[match.start()+2:match.end()-1] ) # Convert three digits to decimal
                    vText = vText[:match.start()] + chr( i ) + vText[match.end():]
                #if vText != vTextOriginal: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, repr(vTextOriginal) ); vPrint( 'Quiet', DEBUGGING_THIS_MODULE, repr(vText) )

                ## Handle special formatting
                ##   [brackets] are for Italicized words
                ##   <brackets> are for the Words of Christ in Red
                ##   «brackets»  are for the Titles in the Book  of Psalms.
                #vText = vText.replace( '[', '\\add ' ).replace( ']', '\\add*' ) \
                    #.replace( '<', '\\wj ' ).replace( '>', '\\wj*' )
                #if vText and vText[0]=='«':
                    #assert BBB=='PSA' and verseNumberString=='1'
                    #vBits = vText[1:].split( '»' )
                    ##dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "vBits", vBits )
                    #thisBook.addLine( 'd', vBits[0] ) # Psalm title
                    #vText = vBits[1].lstrip()

                # Handle the verse info
                if verseNumber==lastVerseNumber and vText==lastVText:
                    logging.warning( _("Ignored duplicate verse line in {} {} {} {}:{}").format( self.givenName, BBB, bookNumber, chapterNumberString, verseNumberString ) )
                    continue
                if BBB=='PSA' and verseNumberString=='1' and vText.startswith('&lt;') and self.givenName=='basic_english':
                    # Move Psalm titles to verse zero
                    verseNumber = 0
                if verseNumber < lastVerseNumber:
                    logging.warning( _("Ignored receding verse number (from {} to {}) in {} {} {} {}:{}").format( lastVerseNumber, verseNumber, self.givenName, BBB, bookNumber, chapterNumberString, verseNumberString ) )
                elif verseNumber == lastVerseNumber:
                    if vText == lastVText:
                        logging.warning( _("Ignored duplicated {} verse in {} {} {} {}:{}").format( verseNumber, self.givenName, BBB, bookNumber, chapterNumberString, verseNumberString ) )
                    else:
                        logging.warning( _("Ignored duplicated {} verse number in {} {} {} {}:{}").format( verseNumber, self.givenName, BBB, bookNumber, chapterNumberString, verseNumberString ) )
                thisBook.addLine( 'v', verseNumberString + ' ' + vText )
                lastVText = vText
                lastVerseNumber = verseNumber

        if haveBereanWordSpreadsheet:
            return self._loadBereanSpreadsheetTable( filepath ) # Use a separate loading function
        
        # Save the final book
        dPrint( 'Info', DEBUGGING_THIS_MODULE, f"Stashing final {self.abbreviation} book: {thisBook.BBB=}…" )
        if temporaryBookStore is None: self.stashBook( thisBook )
        else: temporaryBookStore[thisBook.BBB] = thisBook
        dPrint( 'Info', DEBUGGING_THIS_MODULE, f"    Now have {len(temporaryBookStore)=} books: {temporaryBookStore.keys()=}." )
    # end of CSVBible._loadFile


    def _loadBereanSpreadsheetTable( self, filepath:Path ) -> Bible:
        """
        Does the work of loading a Berean word table TSV (exported from a downloaded Excel spreadsheet) file into memory.
        """
        from csv import DictReader
        from BibleOrgSys.Formats.ESFMBibleBook import ESFMBibleBook

        fnPrint( DEBUGGING_THIS_MODULE, f"CSVBible._loadBereanSpreadsheetTable( {filepath} )")
        vPrint( 'Info', DEBUGGING_THIS_MODULE, _("  Loading Berean word table from {}…").format( filepath ) )

        WORD_TABLE_FILENAMES = ('OET-LV_OT_word_table.tsv', 'OET-LV_NT_word_table.tsv')
        self.ESFMWordTables, self.ESFMColumnNameList = {}, {}

        def removeHebrewAccents( hebText:str ) -> str:
            """
            Return the text with cantillation marks and Meteg removed.
            """
            h = Hebrew.Hebrew( hebText )
            return h.removeCantillationMarks( removeMetegOrSiluq=True )
        # end of apply_Clear_Macula_OT_glosses.removeHebrewAccents

        def removeGreekAccents( grkText:str ) -> str:
            """
            Return the text with accents removed.
            """
            h = Greek.Greek( grkText )
            return h.removeAccents()
        # end of apply_Clear_Macula_OT_glosses.removeHebrewAccents

        # def removeHebrewMarks( text:str ) -> str:
        #     """
        #     Return the text with accents removed.
        #     """
        #     h = Hebrew.Hebrew( text )
        #     # resultA = h.removeCantillationMarks( removeMetegOrSiluq=True )
        #     return h.removeOtherMarks( removeSinShinDots=False )
        # # end of apply_Clear_Macula_OT_glosses.removeHebrewMarks

        def _loadPossibleWordTables( folderpath:Path ) -> int:
            """
            Some code copied from ESFMBible.py loadESFMWordFile()

            Returns the number of tables loaded
            """
            fnPrint( DEBUGGING_THIS_MODULE, f"CSVBible._loadBereanSpreadsheetTable._loadPossibleWordTables( {folderpath} )")

            # loadedWordTable = []
            self.abbreviatedWordTables = {}
            for filename in WORD_TABLE_FILENAMES:
                filepath = folderpath.joinpath( filename )
                print( f"_loadPossibleWordTables looking for {filepath}…" )
                with open(filepath, 'rt', encoding='utf-8') as wordFile:
                    wordFileText = wordFile.read()

                # Remove any BOM
                if wordFileText.startswith( BibleOrgSysGlobals.BOM ):
                    logging.info( f"CSVBible._loadBereanSpreadsheetTable._loadPossibleWordTables: Detected UTF-16 Byte Order Marker in {filename}" )
                    wordFileText = wordFileText[1:] # Remove the Unicode Byte Order Marker (BOM)

                self.ESFMWordTables[filename] = wordFileText.rstrip( '\n' ).split( '\n' ) # Remove any blank line at the end then split
                # Uses less memory to keep the rows as single strings, rather than separating the columns at the tabs now
                vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"CSVBible._loadBereanSpreadsheetTable._loadPossibleWordTables for {self.abbreviation} loaded {len(self.ESFMWordTables[filename]):,} total rows from {filename}" )
                self.ESFMColumnNameList[filename] = self.ESFMWordTables[filename][0].split( '\t' )
                dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"CSVBible._loadBereanSpreadsheetTable._loadPossibleWordTables for {self.abbreviation} loaded column names were: ({len(self.ESFMColumnNameList[filename])}) {self.ESFMColumnNameList[filename]}" )

                self.abbreviatedWordTables[filename] = []
                for tableRow in self.ESFMWordTables[filename]:
                    bits = tableRow.split( '\t' )
                    
                    selectedBits = (bits[0],removeHebrewAccents(bits[6].replace(',',''))) \
                                        if '_OT_' in filename else \
                                   (bits[0],removeGreekAccents(bits[1]))
                    self.abbreviatedWordTables[filename].append( selectedBits )

            #     # Get the headers before we start
            #     tsv_column_headers = [header for header in tsv_lines[0].strip().split('\t')]
            #     dPrint('Info', DEBUGGING_THIS_MODULE, f"Column headers: ({len(tsv_column_headers)}): {tsv_column_headers}")
            #     assert len(tsv_column_headers) == 19 if 'OT' in filename else 12

            #     dict_reader = DictReader( tsv_lines, delimiter='\t' )
            #     for n, row in enumerate( dict_reader, start=1 ):
            #         # print( f"\n{n}: {row=}")
            #         loadedWordTable.append( (n, row['Ref'], row['NoCantillations'] if 'OT' in filename else row['GreekWord']) )

            # vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"_loadBereanSpreadsheetTable._loadPossibleWordTables loaded {len(loadedWordTable):,} word entries.")
            return 2
        # end of _loadBereanSpreadsheetTable._loadPossibleWordTables

        _loadPossibleWordTables( filepath.parent )
        # Make a BCV index to the word tables
        word_table_indexes = {}
        for wordTableFilename in WORD_TABLE_FILENAMES:
            word_table_indexes[wordTableFilename] = {}
            lastBCVref = None
            startIx = 1
            for n, columns_string in enumerate( self.ESFMWordTables[wordTableFilename][1:], start=1 ):
                # print( f"ZZZ {n} {columns_string}" )
                wordRef = columns_string.split( '\t', 1 )[0] # Something like 'MAT_1:1w1'
                BCVref = wordRef.split( 'w', 1 )[0] # Something like 'MAT_1:1'
                if BCVref != lastBCVref:
                    if lastBCVref is not None:
                        # print( f"   Adding {lastBCVref} = ({startIx},{n-1})" ); halt
                        word_table_indexes[wordTableFilename][lastBCVref] = (startIx,n-1)
                    startIx = n
                    lastBCVref = BCVref
            word_table_indexes[wordTableFilename][lastBCVref] = (startIx,n) # Save the final one
        for somefilename in word_table_indexes:
            print( f"\nHave {len(word_table_indexes[somefilename]):,} items in {somefilename} word table index" )

        with open(filepath, 'rt', encoding='utf-8') as tsv_file:
            tsv_lines = tsv_file.readlines()

        # Remove any BOM
        if tsv_lines[0].startswith("\ufeff"):
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, "  Handling Byte Order Marker (BOM) at start of our tsv file…")
            tsv_lines[0] = tsv_lines[0][1:]

        # Get the headers before we start
        tsv_column_headers = [header for header in tsv_lines[0].strip().split('\t')]
        dPrint('Info', DEBUGGING_THIS_MODULE, f"Column headers: ({len(tsv_column_headers)}): {tsv_column_headers}")
        assert len(tsv_column_headers) >= 20

        lastMarker = lastText = None
        def addLine( marker:str, text:str, ref:str, bookObject):
            """
            """
            nonlocal lastMarker, lastText
            # if ref.startswith( 'GEN_1:' ):
            #     print( f"{ref} addLine( {marker=}, {text=} )" )
            assert '  ' not in text, f"{ref} addLine( {marker=}, {text=} )"
            bookObject.addLine( marker, text )
            lastMarker, lastText = marker, text
            if marker=='v' and text.rstrip().isdigit(): # no text
                lastText = None # To force appendToLastLine() to do an lstrip()
            # if ref.startswith( 'MAT_1:3' ): halt
        # end of addLine
            
        def appendToLastLine( extraText:str, ref:str, bookObject):
            """
            """
            nonlocal lastText
            if not lastText: extraText = extraText.lstrip()
            # if ref.startswith( 'GEN_1:' ):
            #     print( f"{ref} {lastMarker=} appendToLastLine( {extraText=} ) with {lastText=}" )
            assert '  ' not in extraText, f"{ref} appendToLastLine( {extraText=} )"
            bookObject.appendToLastLine( extraText )
            lastText = extraText
        # end of addLine
            
        def cleanAndCheckVerseText( originalVerseText:str ) -> str:
            thisVerseText = originalVerseText.replace( '{}', '' ).replace( '[]', '' ) # Remove superfluous empty fields
            if includeADDfields: # Seems printed BSB doesn't distinguish added fields
                assert '{}' not in thisVerseText and '[]' not in thisVerseText, f"{fgRef} {thisVerseText=}"
                thisVerseText = thisVerseText.replace( '[', '\\add ').replace( ']', '\\add*').replace( '{', '\\add ').replace( '}', '\\add*')
            if not includeWJfield:
                thisVerseText = thisVerseText.replace( '\\wj ', '' ).replace( '\\wj*', '' ) # wj is too troublesome and not particularly desired anyway
            # Now clean up the line
            thisVerseText = ( thisVerseText
                                .replace( '“', ' “' ).replace( '‘', ' ‘' )
                                # Haven't figured out yet what the following two fields are supposed to mean
                                .replace( 'vvv', '' ) # Sometimes we have something like ' vvv him' (Gen 35:18) so it gets in this far
                                .replace( '...', '…' )
                                .replace( '. . .', '' ) # Sometimes we have something like ' . . . 40,500' (Num 26:18) so it gets in this far
                                .replace( ' - ', ' ' ).replace( ' -', ' ' )
            # )
            # if not thisVerseText.startswith(' \\qs '):
            #     thisVerseText = thisVerseText.strip()
            # thisVerseText = ( thisVerseText
                            .replace( '    ', ' ' ).replace( '   ', ' ' ).replace( '  ', ' ' )
                            .replace( '“ ', '“' ).replace( '‘ ', '‘' ).replace( ' ”', '”' ).replace( ' ’', '’' )
                            .replace( ' \\f ', '\\f ' ).replace( ' \\f*', '\\f*' ).replace( ' \\x ', '\\x ' ).replace( ' \\x*', '\\x*' )
                            .replace( ' \\add*', '\\add*' ).replace( ' \\wj*', '\\wj*' ).replace( ' \\qs*', '\\qs*' ).replace( ' \\it*', '\\it*' )
                            .replace( ' —', '—' ).replace( '— ', '—' )
                                .replace( '\\+it—', '\\+it —' ) # Repairs the above
                            # .replace( '\\qs\\qs* His loving devotion endures forever.', '\\qs His loving devotion endures forever.\\qs*' ) # Response in Psa 136
                            )
            if '\\qs\\qs* His¦' in thisVerseText and thisVerseText.endswith('.') and thisVerseText.count('.')==1:
                thisVerseText = thisVerseText.replace( '\\qs\\qs* His¦', '\\qs His¦').replace( '.', '.\\qs*' )
            for punctuation in ',.?!;:':
                thisVerseText = thisVerseText.replace( f' {punctuation}', punctuation )
            # thisVerseText = thisVerseText.replace( '\\ft.', '\\ft .' ) # Fix an overzealous correction from the above loop at 1Chr 17:19 footnote with '...'

            # Final checks
            # print( f"  {fgRef} {thisVerseText=}")
            for htmlCode in ('<i>','</i>','<b>','<em>'):
                assert htmlCode not in thisVerseText, f"{fgRef} Illegal {htmlCode=} in {thisVerseText=}"
            for errorSequence in ('  ', ',“', '“ ', '‘ ', ' ”', ' ’', ' \\f ', ' \\f*', ' \\x ', ' \\x*'):
                assert errorSequence not in thisVerseText, f"{fgRef} Illegal {errorSequence=} in {thisVerseText=}"
            for warningSequence in ('{', '}'):
                if warningSequence in thisVerseText: logging.warning( f"{fgRef} {warningSequence=} in {thisVerseText=}" )
            for charMarker in ( 'add', 'wj', 'qs', 'it','em','bd','bdit', 'f','x'):
                assert thisVerseText.count( f'\\{charMarker} ' ) == thisVerseText.count( f'\\{charMarker}*' ), f"{fgRef} {charMarker=} {thisVerseText.count( f'\\{charMarker} ' )} {thisVerseText.count( f'\\{charMarker}*' )} in {thisVerseText=} from {originalVerseText=}"
                assert thisVerseText.count( f'\\+{charMarker} ' ) == thisVerseText.count( f'\\+{charMarker}*' ), f"{fgRef} +{charMarker=} {thisVerseText.count( f'\\+{charMarker} ' )} {thisVerseText.count( f'\\+{charMarker}*' )} in {thisVerseText=} from {originalVerseText=}"
            # assert thisVerseText.strip() == thisVerseText, f"Strip failed on {fgRef} {thisVerseText=}"
            assert '|' not in thisVerseText and '<' not in thisVerseText and '>' not in thisVerseText, f"{fgRef} {thisVerseText=}"
            assert '{}' not in thisVerseText and '[]' not in thisVerseText, f"{fgRef} {thisVerseText=}"
            assert '. .' not in thisVerseText and 'vvv' not in thisVerseText, f"{fgRef} {thisVerseText=}"
            assert ' ¦' not in thisVerseText and ',¦' not in thisVerseText, f"{fgRef} {thisVerseText=}"
            # print( f"cleanAndCheckVerseText is returning {thisVerseText=}" )
            return thisVerseText
        # end of cleanAndCheckVerseText

        def appendWordNumber( fgWRef:str, originalLanguageWord:str, text:str ) -> str:
            """
            Also uses word_table_filename
            """
            # print( f"  appendWordNumber( {fgWRef=} {originalLanguageWord=} {text=} ) for {self.abbreviation}" )
            assert fgWRef and fgWRef.count('w')==1, f"appendWordNumber( {fgWRef=} {originalLanguageWord=} {text=} )"
            assert originalLanguageWord and originalLanguageWord.strip()==originalLanguageWord, f"appendWordNumber( {fgWRef=} {originalLanguageWord=} {text=} )"
            # return '' # Uncomment this line to disable word numbers

            if text in (' . . .',' -',' vvv',' ( -',' ( vvv'): # this word is untranslated so don't bother with a word number
                return text
            if not text.strip(): # Nothing to do for an empty field (occurs in MSB NT)
                return text
            
            adjustedOriginalLanguageWord = removeHebrewAccents( originalLanguageWord.removesuffix('־').removesuffix('פ').removesuffix('ס').removesuffix('׀') ) \
                                            if isOT else \
                                           removeGreekAccents( originalLanguageWord.replace('’','ʼ') )

            text = ( text.replace( ' ”', '”' ).replace( ' ,', ',' ).replace( ' [,', '[,' ).replace( ' — ', '—' ).replace( ' —', '—' ).replace( '‘ ', '‘' ) # Remove extra space
                         .replace( '1 ,700', '1,700' ) # Jdg 8:26 w7
                         .replace( '. . .', '' ) # Sometimes we have something like ' . . . 40,500' (Num 26:18) so it gets in this far
                         .replace( 'vvv', '' )
                         .replace( '...', '…' )
                         .replace( '  ', ' ' )
                )
            assert text and not text.endswith(' '), f"{fgWRef} {originalLanguageWord=} {text=}"
            
            # if isNT: print( f"{fgWRef} {originalLanguageWord=} got {text=}")
            try: startIndex,count = word_table_indexes[word_table_filename][fgRef]
            except KeyError:
                logging.critical( f"Why couldn't Berean {self.abbreviation} appendWordNumber( {fgWRef}, {originalLanguageWord=} ) find a table entry ???" )
                return text
            # This code was too slow and inefficient
            # for n,tableRow in enumerate( self.ESFMWordTables[word_table_filename][startIndex:startIndex+count] ):
            #     print( f"  {n} {tableRow=}" )
            #     bits = tableRow.split( '\t' )
            #     print( f"    {bits=}")
            #     if fgWRef==bits[0] and (originalLanguageWord==bits[6].replace(',','') or originalLanguageWord==bits[7].replace(',','')):
            #         return f'¦{startIndex+n}'
            #         break
            fgwRefWordNumber = int( fgWRef.split('w')[1] )
            # print( f"{fgWRef=} {fgwRefWordNumber=} {originalLanguageWord=}" )
            for n,tableRowBits in enumerate( self.abbreviatedWordTables[word_table_filename][startIndex:startIndex+count] ):
                # print( f"    {startIndex=} {count=} {n=} {tableRowBits=}")
                if fgWRef==tableRowBits[0]:
                    if adjustedOriginalLanguageWord==tableRowBits[1] \
                    or (isOT and adjustedOriginalLanguageWord==tableRowBits[1].removesuffix('ס')) \
                    or (isNT and adjustedOriginalLanguageWord.lower() == tableRowBits[1].lower()):
                        # We have to insert one or more word numbers into the text
                        result = text
                        insertionIndex = len(result)
                        while insertionIndex > 0:
                            insertionIndex -= 1
                            if insertionIndex < 1: break
                            # print( f"        {insertionIndex=} {result[insertionIndex]=} from ({len(result)}) {result=}")
                            if insertionIndex==len(result)-1: # it's the final character of the string
                                if result[insertionIndex] in ']}': # then it's an added word and we don't want a word number on it
                                    continue
                                if result[insertionIndex] in ',.?!’)—': # then it's a final punctuation
                                    insertionIndex -= 1
                                if result[insertionIndex] in ']}': # then it's an added word and we don't want a word number on it
                                    continue
                                assert result[insertionIndex].isalpha() or result[insertionIndex].isdigit()
                                result = f'{result[:insertionIndex+1]}¦{startIndex+n}{result[insertionIndex+1:]}'
                            # Else we're not at the final character of the string
                            elif not result[insertionIndex].isalpha() and not result[insertionIndex].isdigit():
                                if result[insertionIndex] in '[{(“‘': # then it's an opening punctuation and we don't want a word number on it
                                    continue
                                insertionIndex -= 1
                                if result[insertionIndex] in ']}[{': # then it's an added word or a free-standing opening bracket and we don't want a word number on it
                                    continue
                                while result[insertionIndex] in ',.?!’”[(-…': # then it's word-ending punctuation character(s) or stand=alone punctuation
                                    insertionIndex -= 1
                                if result[insertionIndex] in ']}) ': # then it's an added word or stand-alone punctuation (with space), and we don't want a word number on it
                                    continue
                                assert result[insertionIndex].isalpha() or result[insertionIndex].isdigit()
                                result = f'{result[:insertionIndex+1]}¦{startIndex+n}{result[insertionIndex+1:]}'
                        # if fgRef.startswith( 'MAT_1:'):
                        #     print( f"    Found {startIndex+n} for {text=} so returning {result=}" )
                        return result
                    else: # didn't match
                        print( f"    Failed comparing {self.abbreviation} {fgWRef} {originalLanguageWord=} {adjustedOriginalLanguageWord=} with {tableRowBits[1]=}")
                if 'w' in tableRowBits[0]:
                    thisWordNumber = int( tableRowBits[0].split('w')[1] )
                    # print( f"    {thisWordNumber}/{fgwRefWordNumber} {tableRowBits=}")
                    if thisWordNumber >  fgwRefWordNumber:
                        # print( "  Gone too far" )
                        break
            logging.error( f"appendWordNumber() {self.abbreviation} failed to match {fgWRef=} {originalLanguageWord=} {text=}" )
            return text
        # end of appendWordNumber


        # Read each row and convert groups of rows into our pseudo-USFM internal format
        includeADDfields, includeWJfield = False, False # These tables use [] for added words (but there's MANY mistakes e.g., using { or } sometimes)
        BBB = lastBBB = thisVerseText = None
        wordBSBOffset = 0 # Used to calculate word numbers within a verse
        fgRef = C = V = vStr = None
        wJ = qs = False
        dict_reader = DictReader( tsv_lines, delimiter='\t' )
        for n, row in enumerate( dict_reader, start=1 ):
            # if fgRef and fgRef.startswith( 'GEN_1:' ):
            # print( f"\n{n}: {row}" )
            # if fgRef == 'GEN_1:2': halt

            try: # BSB
                if row['WLC / Nestle Base TR RP WH NE NA SBL']:
                    originalLanguageWord = row['WLC / Nestle Base TR RP WH NE NA SBL'].replace('׃','')
                else: # it's one of those nine blank rows between each verse
                    try: wordBSBOffset = int( row['Heb Sort' if isOT else 'Greek Sort'] ) + (1 if isNT else 0)
                    except ValueError: wordBSBOffset = int( float( row['Heb Sort' if isOT else 'Greek Sort'] ) )
            except KeyError: # Must be MSB NT
                if row['MT']:
                    originalLanguageWord = row['MT']
                else: # it's one of those nine blank rows between each verse
                    wordBSBOffset = int( row['Greek Sort'] )

            if qs and thisVerseText: # Close the last verse
                # thisBook.appendToLastLine( '\\qs*' )
                thisVerseText = f'{thisVerseText}\\qs*'
                qs = False

            if row['Verse']: # Occurs on the first word in the verse
                if vStr: # Write the last verse number
                    addLine( 'v', f'{vStr.strip()} ', fgRef, thisBook )
                    vStr = None
                if thisVerseText: # Write the last verse text
                    # thisBook.appendToLastLine( cleanAndCheckVerseText( thisVerseText ) )
                    appendToLastLine( cleanAndCheckVerseText( thisVerseText ), fgRef, thisBook )
                # if fgRef == 'JHN_3:13': halt
                thisVerseText = ''

                bits = row['Verse'].split( ' ' )
                bookName, CV = ' '.join( bits[:-1] ), bits[-1]
                C, V = CV.split( ':', 1 )
                vStr = V # Tells us that we need to print it
                BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromEnglishText( bookName )
                # print( f"  {BBB} {C}:{V}")
                assert BBB, f"{n} {row['Verse']=}"
                fgRef = f'{BBB}_{C}:{V}'
                if fgRef == 'MAT_1:1': wordBSBOffset = 0 # Special case for start of NT
                chapterNumber, verseNumber = int(C), int(V)
                isOT = BibleOrgSysGlobals.loadedBibleBooksCodes.isOldTestament_NR( BBB )
                isDC = BibleOrgSysGlobals.loadedBibleBooksCodes.isDeuterocanon_NR( BBB )
                isNT = BibleOrgSysGlobals.loadedBibleBooksCodes.isNewTestament_NR( BBB )
                assert not isDC
                word_table_filename = WORD_TABLE_FILENAMES[0 if isOT else 1]
                # print( f"\n\n\n{fgRef} {word_table_filename=} {word_table_indexes[word_table_filename][fgRef]=}" )

                if BBB != lastBBB: # We've started a new book
                    if lastBBB: # Better save the last book
                        dPrint( 'Info', DEBUGGING_THIS_MODULE, f"Stashing previous {self.abbreviation} book: {thisBook.BBB=}…" )
                        self.stashBook( thisBook )
                    thisBook = (ESFMBibleBook if self.ESFMWordTables else BibleBook)( self, BBB )
                    # thisBook.objectNameString = 'CSV Bible Book object'
                    # thisBook.objectTypeString = 'CSV'
                    # lastBookNumber = bookNumber
                    lastChapterNumber = lastVerseNumber = -1
                    lastBBB = BBB
                    if self.ESFMWordTables:
                        addLine( 'rem', f'ESFM v0.6 {BBB}', fgRef, thisBook )
                        wordTableFilename = f"OET-LV_{'OT' if isOT else 'NT'}_word_table.tsv"
                        addLine( 'rem', f'WORDTABLE {wordTableFilename}', fgRef, thisBook )
                        thisBook.ESFMWordTableFilename = wordTableFilename
                    addLine( 'h', bookName, fgRef, thisBook )
                    addLine( 'toc1', bookName, fgRef, thisBook )
                    addLine( 'toc2', bookName, fgRef, thisBook )
                    addLine( 'mt1', bookName, fgRef, thisBook )
                    
                if chapterNumber != lastChapterNumber: # We've started a new chapter
                    if BibleOrgSysGlobals.debugFlag: assert chapterNumber > lastChapterNumber or BBB=='ESG' # Esther Greek might be an exception
                    if chapterNumber == 0:
                        logging.info( f"Have chapter zero in {self.givenName} {BBB} {C}:{V}" )
                    addLine( 'c', C, fgRef, thisBook )
                    lastChapterNumber = chapterNumber
                    lastVerseNumber = -1

            if row['Hdg']:
                # print( f"  {n} {row['Hdg']=}" )
                if vStr and thisVerseText: # Write the last verse number
                    addLine( 'v', f'{vStr.strip()} ', fgRef, thisBook )
                    vStr = None
                if thisVerseText: # Write the last verse or the previous part of the verse
                    # thisBook.appendToLastLine( cleanAndCheckVerseText( thisVerseText ) )
                    appendToLastLine( cleanAndCheckVerseText( thisVerseText ), fgRef, thisBook )
                    thisVerseText = ''
                    lastMarker = None
                # Easier to process these next ones by hand rather than trying to divide them up programmatically
                if row['Hdg'] == '<p class=|suphdg|>BOOK I <p class=|pshdg|>Psalms 1–41 <p class=|hdg|>The Two Paths':
                    addLine( 'ms1', 'BOOK I', fgRef, thisBook )
                    addLine( 'mr', 'Psalms 1–41', fgRef, thisBook )
                    addLine( 's1', 'The Two Paths', fgRef, thisBook )
                elif row['Hdg'] == '<p class=|suphdg|>BOOK II <p class=|pshdg|>Psalms 42–72 <p class=|hdg|>As the Deer Pants for the Water':
                    addLine( 'ms1', 'BOOK II', fgRef, thisBook )
                    addLine( 'mr', 'Psalms 42–72', fgRef, thisBook )
                    addLine( 's1', 'As the Deer Pants for the Water', fgRef, thisBook )
                elif row['Hdg'] == '<p class=|suphdg|>BOOK III <p class=|pshdg|>Psalms 73–89 <p class=|hdg|>Surely God Is Good to Israel':
                    addLine( 'ms1', 'BOOK III', fgRef, thisBook )
                    addLine( 'mr', 'Psalms 73–89', fgRef, thisBook )
                    addLine( 's1', 'Surely God Is Good to Israel', fgRef, thisBook )
                elif row['Hdg'] == '<p class=|suphdg|>BOOK IV <p class=|pshdg|>Psalms 90–106 <p class=|hdg|>From Everlasting to Everlasting':
                    addLine( 'ms1', 'BOOK IV', fgRef, thisBook )
                    addLine( 'mr', 'Psalms 90–106', fgRef, thisBook )
                    addLine( 's1', 'From Everlasting to Everlasting', fgRef, thisBook )
                elif row['Hdg'] == '<p class=|suphdg|>BOOK V <p class=|pshdg|>Psalms 107–150 <p class=|hdg|>Thanksgiving for Deliverance':
                    addLine( 'ms1', 'BOOK V', fgRef, thisBook )
                    addLine( 'mr', 'Psalms 107–150', fgRef, thisBook )
                    addLine( 's1', 'Thanksgiving for Deliverance', fgRef, thisBook )
                elif row['Hdg'] == '<p class=|hdg|>Your Word Is a Lamp to My Feet<p class=|acrostic|>&#1488;<br> ALEPH':
                    addLine( 's1', 'Your Word Is a Lamp to My Feet', fgRef, thisBook )
                    addLine( 'qa', '&#1488 ALEPH', fgRef, thisBook )
                elif row['Hdg'] == '<p class=|hdg|>Thirty Sayings of the Wise<p class=|subhdg|>Saying 1':
                    addLine( 's1', 'Thirty Sayings of the Wise', fgRef, thisBook )
                    addLine( 's2', 'Saying 1', fgRef, thisBook )
                elif row['Hdg'] == '<p class=|hdg|>Do Not Envy<p class=|indent1stline|><p class=|subhdg|>Saying 20':
                    addLine( 's1', 'Do Not Envy', fgRef, thisBook )
                    addLine( 's2', 'Saying 20', fgRef, thisBook )
                    addLine( 'q1', '', fgRef, thisBook )
                elif row['Hdg'] == '<p class=|hdg|>The Bride’s Admiration<p class=|ihdg|>The Bride':
                    addLine( 's1', 'The Bride’s Admiration', fgRef, thisBook )
                    addLine( 'sp', 'The Bride', fgRef, thisBook )
                elif row['Hdg'] == '<p class=|hdg|>Solomon Admires His Bride<p class=|ihdg|>The Bridegroom':
                    addLine( 's1', 'Solomon Admires His Bride', fgRef, thisBook )
                    addLine( 'sp', 'The Bridegroom', fgRef, thisBook )
                elif row['Hdg'] == '<p class=|hdg|>The Bride and Her Beloved<p class=|ihdg|>The Bridegroom':
                    addLine( 's1', 'The Bride and Her Beloved', fgRef, thisBook )
                    addLine( 'sp', 'The Bridegroom', fgRef, thisBook )
                elif row['Hdg'] == '<p class=|hdg|>Together in the Garden<p class=|ihdg|>The Friends':
                    addLine( 's1', 'Together in the Garden', fgRef, thisBook )
                    addLine( 'sp', 'The Friends', fgRef, thisBook )

                elif row['Hdg'].startswith( '<p class=|hdg|>' ):
                    headingText = row['Hdg'][15:]
                    assert '|' not in headingText and '<' not in headingText and '>' not in headingText
                    addLine( 's1', headingText.lstrip(), fgRef, thisBook )
                elif row['Hdg'].startswith( '<p class=|subhdg|>' ):
                    headingText = row['Hdg'][18:]
                    assert '|' not in headingText and '<' not in headingText and '>' not in headingText
                    addLine( 's2', headingText.lstrip(), fgRef, thisBook )
                elif row['Hdg'].startswith( '<p class=|ihdg|>' ):
                    headingText = row['Hdg'][16:]
                    assert '|' not in headingText and '<' not in headingText and '>' not in headingText
                    addLine( 'sp', headingText.lstrip(), fgRef, thisBook )
                elif row['Hdg'].startswith( '<p class=|acrostic|>' ): # &#1489;<br> BETH'
                    headingText = row['Hdg'][20:].replace( ';<br>', '' )
                    assert '|' not in headingText and '<' not in headingText and '>' not in headingText
                    addLine( 'qa', headingText.lstrip(), fgRef, thisBook )
                elif row['Hdg'].startswith( '<p class=|pshdg|>' ): # Hab 3:19
                    headingText = row['Hdg'][17:]
                    assert '|' not in headingText and '<' not in headingText and '>' not in headingText
                    addLine( 'pc', headingText.lstrip(), fgRef, thisBook  )

                elif row['Hdg'] == '<p class=|list2|>': # Seems to be in the WRONG COLUMN at 1Chr 1:5
                    addLine( 'li2', '', fgRef, thisBook )
                elif row['Hdg'] == '<p class=|tab1stline|>': # Seems to be in the WRONG COLUMN at Psa 72:20
                    addLine( 'pmo', '', fgRef, thisBook )
                elif row['Hdg'] == '<span class=|red|>': # Seems to be in the WRONG COLUMN at Mat 27:63
                    wJ = True
                else: raise ValueError( f"Bad Hdg: {row}")

            if row['Crossref']:
                if row['Crossref'].startswith( '<br /><span class=|cross|>' ):
                    sectionCrossRef = row['Crossref'][26:].replace( '</span>', '' ).replace( '</a>', '' )
                    link_REGEX = re.compile( '<a href =\\|[^|]+?\\|>' )
                    sectionCrossRef = link_REGEX.sub( '', sectionCrossRef ) # Remove the HTML anchors
                    # thisBook.addLine( 'r', sectionCrossRef )
                    addLine( 'r', sectionCrossRef.lstrip(), fgRef, thisBook )
                elif row['Crossref'] == '<p class=|indent1|>': # Seems to be in the WRONG COLUMN at Pro 26:24
                    addLine( 'q1', '', fgRef, thisBook )
                elif row['Crossref'] == '<p class=|reg|>': # Seems to be in the WRONG COLUMN at Jer 38:7
                    addLine( 'm', '', fgRef, thisBook )
                elif row['Crossref'] == '<p class=|red|>': # Seems to be in the WRONG COLUMN at Mat 25:16
                    addLine( 'm', '', fgRef, thisBook )
                    wJ = True
                else: raise ValueError( f"Bad Crossref: {row}")

            if row['Par'] and row['Par'] != ' ': # Eze 40:49
                if vStr and thisVerseText and lastMarker not in ('d',): # Write the last verse number
                    addLine( 'v', f'{vStr.strip()} ', fgRef, thisBook )
                    vStr = None
                if thisVerseText: # Write the last verse or the previous part of the verse
                    # thisBook.appendToLastLine( cleanAndCheckVerseText( thisVerseText ) )
                    appendToLastLine( cleanAndCheckVerseText( thisVerseText ), fgRef, thisBook )
                    thisVerseText = ''
                    lastMarker = None
                if row['Par'] == '<p class=|subhdg|>Saying 7<p class=|indent1stline|>':
                    addLine( 's2', 'Saying 7', fgRef, thisBook )
                    addLine( 'q1', '', fgRef, thisBook )
                elif row['Par'].endswith( '<p class=|reg|>' ): # lstrip needed at Num 4:21 and endswith needed at Num 24:20
                    # thisBook.addLine( 'm', '' )
                    addLine( 'm', '', fgRef, thisBook )
                elif row['Par'] == '<p class=|tab1stline|>':
                    addLine( 'pmo', '', fgRef, thisBook )
                elif row['Par'] == '<p class=|tab1|>': # First one at 1 Kings 5:4
                    addLine( 'pmo', '', fgRef, thisBook )
                elif row['Par'] == '<p class=|indent1stline|>' or row['Par'] == '<p class=|indent1stline|> ': # Isa 1:2
                    addLine( 'q1', '', fgRef, thisBook )
                elif row['Par'] == '<p class=|indent1|>':
                    addLine( 'q1', '', fgRef, thisBook )
                elif row['Par'] == '<p class=|indent2|>':
                    addLine( 'q2', '', fgRef, thisBook )
                elif row['Par'] == '<p class=|list1stline|>':
                    addLine( 'li1', '', fgRef, thisBook )
                elif row['Par'] == '<p class=|list1|>':
                    addLine( 'li1', '', fgRef, thisBook )
                elif row['Par'] == '<p class=|list2|>':
                    addLine( 'li2', '', fgRef, thisBook )
                elif row['Par'] == '<p class=|inscrip|>':
                    addLine( 'pc', '', fgRef, thisBook )
                elif row['Par'] == '<p class=|reg|><div class=|inscrip|>': # Mat 27:37
                    addLine( 'b', '', fgRef, thisBook )
                    addLine( 'pc', '', fgRef, thisBook )
                elif row['Par'] == '<br />':
                    assert fgRef in ('MAT_27:37', 'JHN_19:19', 'REV_17:5')
                    addLine( 'pc', '', fgRef, thisBook )
                elif row['Par'] == '<p class=|selah|>':
                    # thisBook.appendToLastLine( '\\qs ' )
                    thisVerseText = f'{thisVerseText} \\qs '
                    qs = True
                elif row['Par'] == '<p class=|pshdg|>':
                    addLine( 'd', '', fgRef, thisBook  )
                elif row['Par'] == '<p class=|reg|><span class=|red|>':
                    addLine( 'm', '', fgRef, thisBook )
                    wJ = True
                elif row['Par'] == '<p class=|indent1stlinered|>' or row['Par'] == '<p class=|indentred1|>':
                    addLine( 'q1', '', fgRef, thisBook )
                    wJ = True
                elif row['Par'] == '<p class=|indentred2|>':
                    addLine( 'q2', '', fgRef, thisBook )
                    wJ = True
                elif row['Par'] == '<p class=|tab1stlinered|>': # Rev 2:1
                    addLine( 'pmo', '', fgRef, thisBook )
                    wJ = True
                elif row['Par'] == '<p class=|red|>':
                    addLine( 'm', '', fgRef, thisBook )
                    wJ = True
                elif row['Par'] == '<span class=|red|>':
                    wJ = True
                else: raise ValueError( f"Bad Par: {row['Par']=} from {row}")

            if ' BSB version ' in row and row[' BSB version ']:
                # We'll remove this other stuff later, coz we sometimes need the final punctuation after them
                # and row[' BSB version '] != ' . . . ' and row[' BSB version '] != ' - ' and row[' BSB version '] != ' vvv ':
                try: thisSortNumber = int(row['Heb Sort' if isOT else 'Greek Sort'])
                except ValueError: thisSortNumber = int( float( row['Heb Sort' if isOT else 'Greek Sort'] ) )
                wordNumberInVerse = thisSortNumber - wordBSBOffset
                if fgRef not in ('NUM_26:1','SA1_21:15','NEH_7:68',
                                ) and BBB not in ('MAT','MRK','LUK','JHN','ACT','ROM','GAL','EPH'):
                                #  'MAT_7:20','MAT_12:48','MAT_17:22','MAT_17:26','MAT_18:12','MAT_23:15',
                                #  'MRK_1:14','MRK_3:4','MRK_7:17','MRK_9:8','MRK_9:45','MRK_9:47','MRK_10:24',
                                #  'LUK_2:48','ACT_8:38','ROM_16:25','GAL_1:1'):
                    assert wordNumberInVerse >= 1, f"From {fgRef} {thisSortNumber=} ({wordBSBOffset=}) got {wordNumberInVerse=} for {originalText=}"
                originalText = row[' BSB version ']
                # print( f"From {thisSortNumber=} ({wordBSBOffset=}) got {wordNumberInVerse=} for {originalLanguageWord=} {originalText=}" )
                assert originalText.count( '[' ) == originalText.count( ']' ), f"    {n} {BBB} {C}:{V} {originalText=}"
                assert originalText.count( '<i>' ) == originalText.count( '</i>' ), f"    {n} {BBB} {C}:{V} {originalText=}"
                # print( f"    {n} {BBB} {C}:{V}w{wordNumberInVerse} {originalText=}" ); halt
                fgWRef = f'{fgRef}w{wordNumberInVerse}'
                if '<' in originalText: # e.g., a q2 in the middle of a verse
                    for tt, textBit in enumerate( originalText.split( '<' ) ):
                        # print( f"      {n} {BBB} {C}:{V} {tt} {textBit=}" )
                        text = textBit.rstrip()
                        if text.startswith( 'p class=|indent2|>' ):
                            thisBook.addLine( 'q2', '' )
                            text = text[18:]
                        elif text.startswith( 'p class=|list2|>' ):
                            thisBook.addLine( 'li2', '' )
                            text = text[18:]
                        if wJ and text.endswith('</span>'): text = text[:-7]
                        assert '|' not in text and '<' not in text and '>' not in text and '/' not in text
                        textWithWordNumber = appendWordNumber( fgWRef, originalLanguageWord, text )
                        textEntry = f"{'\\wj ' if wJ and row['“'] else ''}{row['“']}{textWithWordNumber}{row['pnc']}{row['”']}{'\\wj*' if wJ and row['”'] else ''}"
                        assert '|' not in textEntry and '<' not in textEntry and '>' not in textEntry and '/' not in textEntry
                        # print( f"      {n} {BBB} {C}:{V} {textEntry=}" )
                        if textEntry:
                            thisVerseText = f'{thisVerseText} {textEntry.lstrip()}'
                            # thisBook.appendToLastLine( textEntry )
                    if '\\wj*' in textEntry:
                        wJ = False
                    footnoteText = row['footnotes'].replace('<i>','\\+it ').replace('</i>','\\+it*') \
                                        .replace( '<span class=|fnv|>', '\\xt ', ).replace( '</span>', '\\ft ', )
                    assert '|' not in footnoteText and '<' not in footnoteText and '>' not in footnoteText and '/' not in footnoteText, f"{BBB} {C}:{V} {footnoteText=}\n from {row['footnotes']}"
                    footnote = f'\\f + \\fr {C}:{V} \\ft {footnoteText}\\f*' if row['footnotes'] else ''
                    assert '|' not in footnote and '<' not in footnote and '>' not in footnote and '/' not in footnote, f"{BBB} {C}:{V} {footnote=} from {row['footnotes']}"
                    textEntry = f"{footnote}{row['End text']}"
                    if textEntry:
                        assert '|' not in textEntry and '<' not in textEntry and '>' not in textEntry and '/' not in textEntry
                        # print( f"      {n} {fgWRef} appended (without html now) {textEntry=}" )
                        thisVerseText = f'{thisVerseText} {textEntry.lstrip()}'
                        # thisBook.appendToLastLine( textEntry )
                else: # should be just a simple text string (without any HTML)
                    text = originalText.rstrip()
                    assert '|' not in text and '<' not in text and '>' not in text and '/' not in text

                    footnoteText = row['footnotes'].replace('<i>','\\+it ').replace('</i>','\\+it*') \
                                        .replace( '<span class=|fnv|>', '\\xt ', ).replace( '</span>', '\\ft ', )
                    assert '|' not in footnoteText and '<' not in footnoteText and '>' not in footnoteText, f"{BBB} {C}:{V} {footnoteText=}\n from {row['footnotes']}"
                    footnote = f'\\f + \\fr {C}:{V} \\ft {footnoteText}\\f*' if row['footnotes'] else ''
                    assert '|' not in footnote and '<' not in footnote and '>' not in footnote, f"{BBB} {C}:{V} {footnote=} from {row['footnotes']}"
                    if row['“'].startswith( '<span class=|reftext|><a href=|#|><b>' ) and row['“'].endswith( '</b></a></span>' ): # A verse number after a d in PSA
                        assert BBB == 'PSA'
                        row['“'] = ''
                    if '</span>' in row['pnc']: # Mat 17:20
                        assert BBB in ('MAT','MRK','LUK','JHN','CO1')
                        assert wJ
                        row['pnc'] = row['pnc'].replace( '</span>', '\\wj*' )
                    if '</span>' in row['”']: # Luk 17:14
                        assert BBB in ('LUK','JHN')
                        assert wJ
                        row['”'] = row['”'].replace( '</span>', '\\wj*' )
                    if '</span>' in row['End text']: # Mat 3:14
                        assert BBB in ('MAT','MRK','LUK','JHN','ACT','CO1','CO2','HEB','REV')
                        # assert wJ # Do we have this wrong then at Mat 19:6 ????
                        row['End text'] = row['End text'].replace( '</span>', '' if footnote else '\\wj*' )
                    elif row['End text'] == '</div>': # Mat 27:37
                        assert fgRef in ('MAT_27:37','MRK_15:26','LUK_23:38','JHN_19:19','ACT_17:23','REV_17:5','REV_19:16') # inscriptions
                        row['End text'] = ''
                    textWithWordNumber = appendWordNumber( fgWRef, originalLanguageWord, text )
                    textEntry = f"{'\\wj ' if wJ and row['“'] else ''}{row['“']}{textWithWordNumber}{row['pnc']}{row['”']}{'\\wj*' if wJ and row['”'] else ''}{footnote}{row['End text']}"
                    # print( f"      {n} {BBB} {C}:{V} whole {textEntry=}" )
                    if textEntry:
                        assert '|' not in textEntry and '<' not in textEntry and '>' not in textEntry, f"{BBB} {C}:{V} {textEntry=}\n from {row}"
                        # print( f"      {n} {fgWRef} appended {textEntry=}" )
                        thisVerseText = f'{thisVerseText} {textEntry.lstrip()}'
                        # thisBook.appendToLastLine( textEntry )
                    if '\\wj*' in textEntry:
                        wJ = False
            elif 'MSB' in row and row['MSB'] and row['MSB'] != ' ': # and row['MSB'] != ' . . . ' and row['MSB'] != ' - ' and row['MSB'] != ' vvv ':
                thisSortNumber = int( row['Greek Sort'] )
                wordNumberInVerse = thisSortNumber - wordBSBOffset
                assert wordNumberInVerse >= 1, f"From {fgRef} {thisSortNumber=} ({wordBSBOffset=}) got {wordNumberInVerse=} for {originalText=}"
                originalText = row['MSB']
                assert originalText.count( '[' ) == originalText.count( ']' ), f"    {n} {BBB} {C}:{V} {originalText=}"
                assert originalText.count( '<i>' ) == originalText.count( '</i>' ), f"    {n} {BBB} {C}:{V} {originalText=}"
                # print( f"    {n} {BBB} {C}:{V} {originalText=}" )
                fgWRef = f'{fgRef}w{wordNumberInVerse}'
                if '<' in originalText: # e.g., a q2 in the middle of a verse
                    halt
                    for tt, textBit in enumerate( originalText.split( '<' ) ):
                        # print( f"      {n} {BBB} {C}:{V} {tt} {textBit=}" )
                        text = textBit.rstrip()
                        if text.startswith( 'p class=|indent2|>' ):
                            thisBook.addLine( 'q2', '' )
                            text = text[18:]
                        elif text.startswith( 'p class=|list2|>' ):
                            thisBook.addLine( 'li2', '' )
                            text = text[18:]
                        if wJ and text.endswith('</span>'): text = text[:-7]
                        assert '|' not in text and '<' not in text and '>' not in text and '/' not in text
                        textWithWordNumber = appendWordNumber( fgWRef, originalLanguageWord, text )
                        textEntry = f"{'\\wj ' if wJ and row['“'] else ''}{row['“']}{textWithWordNumber}{row['Pnc']}{row['”']}{'\\wj*' if wJ and row['”'] else ''}"
                        assert '|' not in textEntry and '<' not in textEntry and '>' not in textEntry and '/' not in textEntry
                        # print( f"      {n} {BBB} {C}:{V} {textEntry=}" )
                        if textEntry:
                            thisVerseText = f'{thisVerseText} {textEntry.lstrip()}'
                            # thisBook.appendToLastLine( textEntry )
                    if '\\wj*' in textEntry:
                        wJ = False
                    footnoteText = row['Footnotes'].replace('<i>','\\+it ').replace('</i>','\\+it*') \
                                        .replace( '<span class=|fnv|>', '\\xt ', ).replace( '</span>', '\\ft ', )
                    assert '|' not in footnoteText and '<' not in footnoteText and '>' not in footnoteText and '/' not in footnoteText, f"{BBB} {C}:{V} {footnoteText=}\n from {row['Footnotes']}"
                    footnote = f'\\f + \\fr {C}:{V} \\ft {footnoteText}\\f*' if row['Footnotes'] else ''
                    assert '|' not in footnote and '<' not in footnote and '>' not in footnote and '/' not in footnote, f"{BBB} {C}:{V} {footnote=} from {row['Footnotes']}"
                    textEntry = f"{footnote}{row['End text']}"
                    if textEntry:
                        assert '|' not in textEntry and '<' not in textEntry and '>' not in textEntry and '/' not in textEntry
                        # print( f"      {n} {BBB} {C}:{V} appended {textEntry=}" )
                        thisVerseText = f'{thisVerseText} {textEntry.lstrip()}'
                        # thisBook.appendToLastLine( textEntry )
                else: # should be just a simple text string (without any HTML)
                    text = originalText.rstrip()
                    assert '|' not in text and '<' not in text and '>' not in text and '/' not in text
                    footnoteText = row['Footnotes'].replace('<i>','\\+it ').replace('</i>','\\+it*') \
                                        .replace( '<span class=|fnv|>', '\\xt ', ).replace( '</span>', '\\ft ', )
                    assert '|' not in footnoteText and '<' not in footnoteText and '>' not in footnoteText, f"{BBB} {C}:{V} {footnoteText=}\n from {row['Footnotes']}"
                    footnote = f'\\f + \\fr {C}:{V} \\ft {footnoteText}\\f*' if row['Footnotes'] else ''
                    assert '|' not in footnote and '<' not in footnote and '>' not in footnote, f"{BBB} {C}:{V} {footnote=} from {row['Footnotes']}"
                    if '</span>' in row['Pnc']: # Mat 18:23
                        assert BBB in ('MAT','MRK','LUK','JHN','CO1')
                        assert wJ
                        row['Pnc'] = row['Pnc'].replace( '</span>', '\\wj*' )
                    if '</span>' in row['”']: # Mat 17:21
                        assert BBB in ('MAT','MRK','LUK','JHN')
                        assert wJ
                        row['”'] = row['”'].replace( '</span>', '\\wj*' )
                    if '</span>' in row['End text']: # Mat 3:15
                        assert BBB in ('MAT','MRK','LUK','JHN','ACT','CO1','CO2','HEB','REV')
                        # assert wJ # Do we have this wrong then at Mat 19:6 ????
                        row['End text'] = row['End text'].replace( '</span>', '' if footnote else '\\wj*' )
                    elif row['End text'] == '</div>': # Mat 27:37
                        assert fgRef in ('MAT_27:37','MRK_15:26','LUK_23:38','JHN_19:19','ACT_17:23','REV_17:5','REV_19:16') # inscriptions
                        row['End text'] = ''
                    textWithWordNumber = appendWordNumber( fgWRef, originalLanguageWord, text )
                    textEntry = f"{'\\wj ' if wJ and row['“'] else ''}{row['“']}{textWithWordNumber}{row['Pnc']}{row['”']}{'\\wj*' if wJ and row['”'] else ''}{footnote}{row['End text']}"
                    # print( f"      {n} {BBB} {C}:{V} whole {textEntry=}" )
                    if textEntry:
                        assert '|' not in textEntry and '<' not in textEntry and '>' not in textEntry
                        thisVerseText = f'{thisVerseText} {textEntry.lstrip()}'
                        # thisBook.appendToLastLine( textEntry )
                    if '\\wj*' in textEntry:
                        wJ = False

        if lastBBB: # Save the final book
            dPrint( 'Info', DEBUGGING_THIS_MODULE, f"Stashing final {self.abbreviation} book: {thisBook.BBB=}…" )
            self.stashBook( thisBook )
    # end of CSVBible._loadBereanWoordTable

    def load( self ):
        """
        Assumes self.sourceFilepath is set
            (If not, use loadBooks() instead.)

        Load a single source file and load book elements.
        """
        vPrint( 'Info', DEBUGGING_THIS_MODULE, _("CSVBible: Loading {}…").format( self.sourceFilepath ) )
        assert self.sourceFilepath is not None

        self._loadFile( self.sourceFilepath )
        self.doPostLoadProcessing()
    # end of CSVBible.load


    def loadBooks( self ):
        """
        Assumes self.sourceFilepath is not set
            (If not, use load() instead.)

        Finds and loads multiple source files and load book elements.
        """
        if self.sourceFilepath:
            return self.load()
        # else: # we have a folder
        assert self.sourceBookFileExtension
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, _("Loading books from {}…").format( self.sourceFolder ) )

        tempBookStore = {}
        for filename in os.listdir( self.sourceFolder ):
            # dPrint( 'Info', DEBUGGING_THIS_MODULE, f"  {filename=}" )
            if filename.endswith( f'.{self.sourceBookFileExtension}' ):
                filenameStart = filename[:-4]
                if filenameStart == 'AC24': # from RP-GNT
                    continue # Not sure what this is
                if filenameStart == 'PA': # from RP-GNT
                    continue # Not sure what this is
                BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromEnglishText( filenameStart )
                dPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Got {BBB=} from {filenameStart=}")
                self._loadFile( os.path.join( self.sourceFolder, filename ), tempBookStore )

        dPrint( 'Info', DEBUGGING_THIS_MODULE, f"{len(tempBookStore)}" )

        # Now save the books in the right Biblical order
        for BBB in BibleOrgSysGlobals.loadedBibleBooksCodes:
            if BBB in tempBookStore:
                self.vBook( tempBookStore[BBB] )

        self.doPostLoadProcessing()
    # end of VPLBible.loadBooks
# end of CSVBible class



def testCSV( CSVfolder ):
    # Crudely demonstrate the CSV Bible class
    from BibleOrgSys.Reference import VerseReferences

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, _("Demonstrating the CSV Bible class…") )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  Test folder is {!r}".format( CSVfolder ) )
    vb = CSVBible( CSVfolder, "demo" )
    vb.load() # Load and process the file
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, vb ) # Just print a summary
    if BibleOrgSysGlobals.strictCheckingFlag:
        vb.check()
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, UsfmB.books['GEN']._processedLines[0:40] )
        vBErrors = vb.getCheckResults()
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, vBErrors )
    if BibleOrgSysGlobals.commandLineArguments.export:
        ##vb.toDrupalBible()
        vb.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
    for reference in ( ('OT','GEN','1','1'), ('OT','GEN','1','3'), ('OT','PSA','3','0'), ('OT','PSA','3','1'), \
                        ('OT','DAN','1','21'),
                        ('NT','MAT','3','5'), ('NT','JDE','1','4'), ('NT','REV','22','21'), \
                        ('DC','BAR','1','1'), ('DC','MA1','1','1'), ('DC','MA2','1','1',), ):
        (t, b, c, v) = reference
        if t=='OT' and len(vb)==27: continue # Don't bother with OT references if it's only a NT
        if t=='NT' and len(vb)==39: continue # Don't bother with NT references if it's only a OT
        if t=='DC' and len(vb)<=66: continue # Don't bother with DC references if it's too small
        svk = VerseReferences.SimpleVerseKey( b, c, v )
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, svk, ob.getVerseDataList( reference ) )
        shortText = svk.getShortText()
        try:
            verseText = vb.getVerseText( svk )
        except KeyError:
            verseText = "Verse not available!"
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, reference, shortText, verseText )
# end of testCSV


def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    import random

    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    testFolders =  ( BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'CSVTest1/'),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'CSVTest2/') )


    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        testFolder = random.choice( testFolders )
        result1 = CSVBibleFileCheck( testFolder )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "CSV TestA1", result1 )

        result2 = CSVBibleFileCheck( testFolder, autoLoad=True )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "CSV TestA2", result2 )

        result3 = CSVBibleFileCheck( testFolder, autoLoadBooks=True )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "CSV TestA3", result3 )
        #result3.loadMetadataFile( os.path.join( testFolder, "BooknamesMetadata.txt" ) )

        if BibleOrgSysGlobals.strictCheckingFlag:
            result3.check()
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, UsfmB.books['GEN']._processedLines[0:40] )
            vBErrors = result3.getCheckResults()
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, vBErrors )
        if BibleOrgSysGlobals.commandLineArguments.export:
            ##result3.toDrupalBible()
            result3.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )


    if 0: # all discovered modules in the test folder
        foundFolders, foundFiles = [], []
        for something in os.listdir( testFolder ):
            somepath = os.path.join( testFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )

        if BibleOrgSysGlobals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, "\nTrying all {} discovered modules…".format( len(foundFolders) ) )
            parameters = [folderName for folderName in sorted(foundFolders)]
            BibleOrgSysGlobals.alreadyMultiprocessing = True
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.map( testCSV, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            for j, someFolder in enumerate( sorted( foundFolders ) ):
                vPrint( 'Normal', DEBUGGING_THIS_MODULE, "\nCSV D{}/ Trying {}".format( j+1, someFolder ) )
                #myTestFolder = os.path.join( testFolder, someFolder+'/' )
                testCSV( someFolder )
# end of CSVBible.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    testFolders =  ( BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'CSVTest1/'),
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'CSVTest2/') )


    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        for testFolder in testFolders:
            result1 = CSVBibleFileCheck( testFolder )
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, "CSV TestA1", result1 )

            result2 = CSVBibleFileCheck( testFolder, autoLoad=True )
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, "CSV TestA2", result2 )

            result3 = CSVBibleFileCheck( testFolder, autoLoadBooks=True )
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, "CSV TestA3", result3 )
            #result3.loadMetadataFile( os.path.join( testFolder, "BooknamesMetadata.txt" ) )

            if BibleOrgSysGlobals.strictCheckingFlag:
                result3.check()
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, UsfmB.books['GEN']._processedLines[0:40] )
                vBErrors = result3.getCheckResults()
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, vBErrors )
            if BibleOrgSysGlobals.commandLineArguments.export:
                ##result3.toDrupalBible()
                result3.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )


    if 0: # all discovered modules in the test folder
        foundFolders, foundFiles = [], []
        for something in os.listdir( testFolder ):
            somepath = os.path.join( testFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )

        if BibleOrgSysGlobals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, "\nTrying all {} discovered modules…".format( len(foundFolders) ) )
            parameters = [folderName for folderName in sorted(foundFolders)]
            BibleOrgSysGlobals.alreadyMultiprocessing = True
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.map( testCSV, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            for j, someFolder in enumerate( sorted( foundFolders ) ):
                vPrint( 'Normal', DEBUGGING_THIS_MODULE, "\nCSV D{}/ Trying {}".format( j+1, someFolder ) )
                #myTestFolder = os.path.join( testFolder, someFolder+'/' )
                testCSV( someFolder )
# end of CSVBible.fullDemo

if __name__ == '__main__':
    from multiprocessing import set_start_method, freeze_support
    set_start_method('fork') # The default was changed on POSIX systems from 'fork' to 'forkserver' in Python3.14
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of CSVBible.py
