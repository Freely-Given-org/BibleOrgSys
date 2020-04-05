#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# USFMFilenames.py
#
# Module handling USFM Bible filenames
#
# Copyright (C) 2010-2019 Robert Hunt
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
Module for creating and manipulating USFM filenames.
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2019-12-13' # by RJH
SHORT_PROGRAM_NAME = "USFMFilenames"
PROGRAM_NAME = "USFM Bible filenames handler"
PROGRAM_VERSION = '0.68'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'
programNameVersionDate = f'{programNameVersion} {_("last modified")} {LAST_MODIFIED_DATE}'

debuggingThisModule = False


import os
import logging
from pathlib import Path

if __name__ == '__main__':
    import sys
    aboveAboveFolderPath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderPath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderPath )
from BibleOrgSys import BibleOrgSysGlobals



# The filenames produced by the Bibledit program seem to have a .usfm extension (Info below is from gtk/src/bookdata.cpp 2012-07-11)
BIBLEDIT_FILENAMES = ( '1_Genesis', '2_Exodus', '3_Leviticus', '4_Numbers', '5_Deuteronomy', '6_Joshua', '7_Judges', '8_Ruth', '9_1_Samuel', '10_2_Samuel',
    '11_1_Kings', '12_2_Kings', '13_1_Chronicles', '14_2_Chronicles', '15_Ezra', '16_Nehemiah', '17_Esther', '18_Job', '19_Psalms', '20_Proverbs', '21_Ecclesiastes',
    '22_Song_of_Solomon', '23_Isaiah', '24_Jeremiah', '25_Lamentations', '26_Ezekiel', '27_Daniel', '28_Hosea', '29_Joel', '30_Amos', '31_Obadiah', '32_Jonah',
    '33_Micah', '34_Nahum', '35_Habakkuk', '36_Zephaniah', '37_Haggai', '38_Zechariah', '39_Malachi',
    '40_Matthew', '41_Mark', '42_Luke', '43_John', '44_Acts', '45_Romans', '46_1_Corinthians', '47_2_Corinthians', '48_Galatians', '49_Ephesians', '50_Philippians',
    '51_Colossians', '52_1_Thessalonians', '53_2_Thessalonians', '54_1_Timothy', '55_2_Timothy', '56_Titus', '57_Philemon',
    '58_Hebrews', '59_James', '60_1_Peter', '61_2_Peter', '62_1_John', '63_2_John', '64_3_John', '65_Jude', '66_Revelation',
    '67_Front_Matter', '68_Back_Matter', '69_Other_Material', '70_Tobit', '71_Judith', '72_Esther_(Greek)', '73_Wisdom_of_Solomon', '74_Sirach', '75_Baruch',
    '76_Letter_of_Jeremiah', '77_Song_of_the_Three_Children', '78_Susanna', '79_Bel_and_the_Dragon', '80_1_Maccabees', '81_2_Maccabees',
    '82_1_Esdras', '83_Prayer_of_Manasses', '84_Psalm_151', '85_3_Maccabees', '86_2_Esdras', '87_4_Maccabees', '88_Daniel_(Greek)' )
ALTERNATE_FILENAMES = ( '01-Genesis', '02-Exodus', '03-Leviticus', '04-Numbers', '05-Deuteronomy', '06-Joshua', '07-Judges', '08-Ruth', '09-1 Samuel', '10-2 Samuel',
    '11-1 Kings', '12-2 Kings', '13-1 Chronicles', '14-2 Chronicles', '15-Ezra', '16-Nehemiah', '17-Esther', '18-Job', '19-Psalms', '20-Proverbs', '21-Ecclesiastes',
    '22-Song-of-Solomon', '23-Isaiah', '24-Jeremiah', '25-Lamentations', '26-Ezekiel', '27-Daniel', '28-Hosea', '29-Joel', '30-Amos', '31-Obadiah', '32-Jonah',
    '33-Micah', '34-Nahum', '35-Habakkuk', '36-Zephaniah', '37-Haggai', '38-Zechariah', '39-Malachi',
    '40-Matthew', '41-Mark', '42-Luke', '43-John', '44-Acts', '45-Romans', '46-1 Corinthians', '47-2 Corinthians', '48-Galatians', '49-Ephesians', '50-Philippians',
    '51-Colossians', '52-1 Thessalonians', '53-2 Thessalonians', '54-1 Timothy', '55-2 Timothy', '56-Titus', '57-Philemon',
    '58-Hebrews', '59-James', '60-1 Peter', '61-2 Peter', '62-1 John', '63-2 John', '64-3 John', '65-Jude', '66-Revelation',
    #'67-Front-Matter', '68-Back-Matter', '69-Other-Material', '70-Tobit', '71-Judith', '72-Esther-(Greek)', '73-Wisdom-of-Solomon', '74-Sirach', '75-Baruch',
    #'76-Letter-of-Jeremiah', '77-Song-of-the-Three-Children', '78-Susanna', '79-Bel-and-the-Dragon', '80-1 Maccabees', '81-2 Maccabees',
    #'82-1 Esdras', '83-Prayer-of-Manasses', '84-Psalm-151', '85 3-Maccabees', '86-2 Esdras', '87-4 Maccabees', '88-Daniel-(Greek)'
    )

# All of the following must be all UPPER CASE
FILENAMES_TO_IGNORE = ('AUTOCORRECT.TXT','HYPHENATEDWORDS.TXT','PRINTDRAFTCHANGES.TXT','README.TXT','BOOK_NAMES.TXT',) # Only needs to include names whose extensions are not listed below
FILENAME_ENDINGS_TO_IGNORE = ('.ZIP.GO', '.ZIP.DATA',) # Must begin with a dot
# NOTE: Extensions ending in ~ are also ignored
EXTENSIONS_TO_IGNORE = ( 'ASC', 'BAK', 'BAK2', 'BAK3', 'BAK4', 'BBLX', 'BC', 'CCT', 'CSS', 'DOC', 'DTS', 'HTM','HTML',
                    'JAR', 'LDS', 'LOG', 'MYBIBLE', 'NT','NTX', 'ODT', 'ONT','ONTX', 'OSIS', 'OT','OTX', 'PDB',
                    'SAV', 'SAVE', 'STY', 'SSF', 'USX', 'VRS', 'YET', 'XML', 'ZIP', ) # Must be UPPERCASE and NOT begin with a dot



class USFMFilenames:
    """
    Class for creating and manipulating USFM filenames.

    Always returns lists of USFM filenames in the default rough sequence order from the BibleBooksCodes module.
    """

    def __init__( self, givenFolderName ):
        """
        Create the object by inspecting files in the given folder.

            Creates a self.pattern (Paratext template) for USFM filenames where
                nnn = language code (lower case) or NNN = language code (UPPER CASE)
                bbb = book code (lower case) or BBB = book code (UPPER CASE)
                dd = digits
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( "USFMFilenames( {} )".format( givenFolderName ) )
        self.givenFolderName = givenFolderName
        self.pattern, self.fileExtension = '', ''
        self.fileList = [] # A list of all files in our folder (excluding folder names and backup filenames)
        self._fileDictionary = {} # The keys are 2-tuples of folder, filename, the values are all valid BBB values
        self._BBBDictionary = {} # The keys are valid BBB values, the values are all 2-tuples of folder, filename

        # Check that the given folder is readable
        if not os.access( self.givenFolderName, os.R_OK ):
            logging.critical( _("USFMFilenames: Given {!r} folder is unreadable").format( self.givenFolderName ) )
            return

        # Get the data tables that we need for proper checking
        self._USFMBooksCodes = BibleOrgSysGlobals.loadedBibleBooksCodes.getAllUSFMBooksCodes()
        self._USFMBooksCodesUpper = [x.upper() for x in self._USFMBooksCodes]
        self._USFMBooksCodeNumberTriples = BibleOrgSysGlobals.loadedBibleBooksCodes.getAllUSFMBooksCodeNumberTriples()
        self._BibleditBooksCodeNumberTriples = BibleOrgSysGlobals.loadedBibleBooksCodes.getAllBibleditBooksCodeNumberTriples()

        # Find how many files are in our folder
        self.lastTupleList = None
        for possibleFilename in os.listdir( self.givenFolderName ):
            pFUpper = possibleFilename.upper()
            if pFUpper in FILENAMES_TO_IGNORE: continue
            pFUpperProper, pFUpperExt = os.path.splitext( pFUpper )
            ignore = False
            for ending in FILENAME_ENDINGS_TO_IGNORE:
                if pFUpper.endswith( ending): ignore=True; break
            if ignore: continue
            if pFUpper[-1]!='~' and not pFUpperExt[1:] in EXTENSIONS_TO_IGNORE: # Compare without the first dot
                filepath = os.path.join( self.givenFolderName, possibleFilename )
                if os.path.isfile( filepath ): # It's a file not a folder
                    self.fileList.append( possibleFilename )
        #print( "fL", self.fileList )
        #if not self.fileList: logging.error( _("No files at all in given folder: {!r}").format( self.givenFolderName) ); return

        # See if we can find a pattern for these filenames
        matched = False
        for foundFilename in self.fileList:
            foundFileBit, foundExtBit = os.path.splitext( foundFilename )
            foundLength = len( foundFileBit )
            #print( foundFileBit, foundExtBit )
            matched = False
            if '_' in foundFileBit and foundExtBit and foundExtBit[0]=='.': # Check for possible Bibledit filenames first
                for USFMBookCode,BibleditDigits,BBB in self._BibleditBooksCodeNumberTriples:
                    BibleditSignature = BibleditDigits + '_'
                    if BibleditSignature in foundFileBit and foundFileBit in BIBLEDIT_FILENAMES and foundExtBit == '.usfm':
                        digitsIndex = foundFileBit.index( BibleditSignature )
                        if digitsIndex == 0:
                            self.languageIndex = None
                            self.languageCode = None
                            self.digitsIndex = digitsIndex
                            self.USFMBookCodeIndex = None
                            self.pattern = "Dd_BEName"
                            self.fileExtension = foundExtBit[1:]
                            matched = True
                            break
            elif '-' in foundFileBit and foundExtBit and foundExtBit[0]=='.': # Check for possible Bibledit filenames first
                for USFMBookCode,BibleditDigits,BBB in self._BibleditBooksCodeNumberTriples:
                    if foundFileBit in ALTERNATE_FILENAMES and foundExtBit == '.usfm':
                        if foundFilename[0:2].isdigit:
                            self.languageIndex = None
                            self.languageCode = None
                            self.digitsIndex = 0
                            self.USFMBookCodeIndex = None
                            self.pattern = "dd-OEBName"
                            self.fileExtension = foundExtBit[1:]
                            matched = True
                            break
                if matched: break
            if matched: break
            # Didn't find a Bibledit filename -- maybe it's a Paratext style or some kind of freestyle
            containsDigits = False
            for char in foundFileBit:
                if char.isdigit():
                    containsDigits = True
                    break
            if containsDigits and foundExtBit and foundExtBit[0]=='.':
                for USFMBookCode,USFMDigits,BBB in self._USFMBooksCodeNumberTriples:
                    if USFMDigits in foundFileBit and (USFMBookCode in foundFileBit or USFMBookCode.upper() in foundFileBit):
                        digitsIndex = foundFileBit.index( USFMDigits )
                        USFMBookCodeIndex = foundFileBit.index(USFMBookCode) if USFMBookCode in foundFileBit else foundFileBit.index(USFMBookCode.upper())
                        USFMBookCode = foundFileBit[USFMBookCodeIndex:USFMBookCodeIndex+3]
                        if debuggingThisModule:
                            print( f"USFMFilenames dI={digitsIndex} UBCI={USFMBookCodeIndex} UBC={USFMBookCode}" )
                        if foundLength>=8 and digitsIndex==0 and USFMBookCodeIndex==2: # Found a form like 01GENlanguage.xyz
                            if debuggingThisModule:
                                print( "USFMFilenames: Trying1…" )
                            self.languageIndex = 5
                            self.languageCode = foundFileBit[self.languageIndex:self.languageIndex+foundLength-5]
                            self.digitsIndex = digitsIndex
                            self.USFMBookCodeIndex = USFMBookCodeIndex
                            self.pattern = "ddbbb" + 'l'*(foundLength-5)
                            matched = True
                        elif foundLength==8 and digitsIndex==3 and USFMBookCodeIndex==5: # Found a form like lng01GEN.xyz
                            if debuggingThisModule:
                                print( "USFMFilenames: Trying2…" )
                            self.languageIndex = 0
                            self.languageCode = foundFileBit[self.languageIndex:self.languageIndex+foundLength-5]
                            self.digitsIndex = digitsIndex
                            self.USFMBookCodeIndex = USFMBookCodeIndex
                            self.pattern = "lllddbbb"
                            matched = True
                        else: # we'll try to be more generic
                            if debuggingThisModule:
                                print( "USFMFilenames: Trying generic…" )
                            self.languageIndex = None
                            self.languageCode = None
                            self.digitsIndex = digitsIndex
                            self.USFMBookCodeIndex = USFMBookCodeIndex
                            self.pattern = '*' * foundLength
                            self.pattern = self.pattern[:digitsIndex] + 'dd' + self.pattern[digitsIndex+2:]
                            self.pattern = self.pattern[:USFMBookCodeIndex] + 'bbb' + self.pattern[USFMBookCodeIndex+3:]
                            fillerSize = self.pattern.count( '*' )
                            fillerIndex = self.pattern.find( '*' )
                            if fillerIndex!=-1 and fillerSize==1: self.pattern = self.pattern[:fillerIndex] + foundFilename[fillerIndex] + self.pattern[fillerIndex+1:]
                            if BibleOrgSysGlobals.verbosityLevel > 2: print( "Pattern is {!r}".format( self.pattern ) )
                            if '*' not in self.pattern: matched = True
                            else: # we'll try to be even more generic
                                self.languageIndex = self.digitsIndex = None
                                self.languageCode = None
                                self.USFMBookCodeIndex = USFMBookCodeIndex
                                self.pattern = '*' * foundLength
                                self.pattern = self.pattern[:USFMBookCodeIndex] + 'bbb' + self.pattern[USFMBookCodeIndex+3:]
                                if BibleOrgSysGlobals.verbosityLevel > 2: print( "More generic pattern is {!r}".format( self.pattern ) )
                                matched = True
                        if matched:
                            if self.languageCode and self.languageCode.isupper(): self.pattern = self.pattern.replace( 'l', 'L' )
                            if USFMBookCode.isupper(): self.pattern = self.pattern.replace( 'bbb', 'BBB' )
                            self.fileExtension = foundExtBit[1:]
                            break
                if matched: break
            if matched: break
        #if not matched: logging.info( _("Unable to recognize pattern of valid USFM files in ") + self.givenFolderName )
        #print( "USFMFilenames: pattern={!r} fileExtension={!r}".format( self.pattern, self.fileExtension ) )

        # Also, try looking inside the files
        self.getUSFMIDsFromFiles( self.givenFolderName ) # Fill the above dictionaries
        #print( "fD", self._fileDictionary )
    # end of __init__


    def __str__( self ):
        """
        This method returns the string representation of an object.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = "USFM Filenames object:"
        indent = 2
        if self.givenFolderName: result += ('\n' if result else '') + ' '*indent + _("Folder: {}").format( self.givenFolderName )
        if self.pattern: result += ('\n' if result else '') + ' '*indent + _("Filename pattern: {}").format( self.pattern )
        if self.fileExtension: result += ('\n' if result else '') + ' '*indent + _("File extension: {}").format( self.fileExtension )
        if self.fileList and BibleOrgSysGlobals.verbosityLevel > 2: result += ('\n' if result else '') + ' '*indent + _("File list: ({}) {}").format( len(self.fileList), self.fileList )
        return result
    # end of __str___


    def __len__( self ):
        """
        This method returns the last number of files found.

        @return: None (if no search done) or else the last number of USFM files found
        @rtype: int
        """
        if self.lastTupleList is None: return 0
        return len( self.lastTupleList )
    # end of __len___


    def getUSFMIDFromFile( self, folder, thisFilename, filepath, encoding=None ):
        """
        Try to intelligently get the USFMId from the first line in the file (which should be the \\id line).
        """
        #print( "getUSFMIDFromFile( {} {} {} {} )".format( repr(folder), repr(thisFilename), repr(filepath), encoding ) )
        if encoding is None: encoding = 'utf-8'
        # Look for the USFM id in the ID line (which should be the first line in a USFM file)
        try:
            with open( filepath, 'rt', encoding=encoding ) as possibleUSFMFile: # Automatically closes the file when done
                lineNumber = 0
                for line in possibleUSFMFile:
                    lineNumber += 1
                    if line[-1]=='\n': line = line[:-1] # Removing trailing newline character
                    #print( thisFilename, lineNumber, line )
                    if line.startswith( '\\id ' ):
                        if len(line)<5: logging.warning( "id line {!r} in {} is too short".format( line, filepath ) )
                        idContent = line[4:]
                        tokens = idContent.split()
                        #print( "Have id tokens: {}".format( tokens ) )
                        UCToken0 = tokens[0].upper()
                        if UCToken0=='I': UCToken0 = '1'
                        if UCToken0=='II': UCToken0 = '2'
                        if UCToken0=='III': UCToken0 = '3'
                        if UCToken0=='IV': UCToken0 = '4'
                        if UCToken0=='V': UCToken0 = '5'
                        if UCToken0 in ('1','2','3','4','5',) and len(tokens)>=2: UCToken0 += tokens[1].upper() # Combine something like 1 Sa to 1SA
                        if UCToken0.startswith( 'JUDG' ): UCToken0 = UCToken0[0] + UCToken0[2:] # Remove the U because it gets confused with JUDE
                        if len(UCToken0)>2 and UCToken0[1] in ('_','-'): UCToken0 = UCToken0[0] + UCToken0[2:] # Change something like 1_SA to 1SA
                        if UCToken0 in self._USFMBooksCodesUpper: return UCToken0 # it's a valid one -- we have the most confidence in this one
                        elif UCToken0[:3] in self._USFMBooksCodesUpper: return UCToken0[:3] # perhaps an abbreviated version is valid (but could think Judges is JUD=Jude)
                        else: print( "But {!r} wasn't a valid USFM ID in {}!!!".format( UCToken0, thisFilename ) )
                        break
                    elif lineNumber == 1:
                        if line.startswith ( '\\' ):
                            logging.warning( "First line in {} in {} starts with a backslash but not an id line {!r}".format( thisFilename, folder, line ) )
                        elif not line:
                            logging.info( "First line in {} in {} appears to be blank".format( thisFilename, folder ) )
                    if lineNumber >= 2: break # We only look at the first one or two lines
        except UnicodeDecodeError:
            if thisFilename != 'usfm-color.sty': # Seems this file isn't UTF-8, but we don't need it here anyway so ignore it
                logging.warning( "getUSFMIDFromFile: Seems we couldn't decode Unicode in {!r}".format( filepath ) ) # Could be binary or a different encoding
        return None
    # end of getUSFMIDFromFile


    def getUSFMIDsFromFiles( self, givenFolder ):
        """
        Go through all the files in the given folder and see how many USFM IDs we can find.
                Populates the two dictionaries.
                Returns the number of files found.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( "getUSFMIDsFromFiles( {} )".format( repr(givenFolder) ) )

        # Empty the two dictionaries
        self._fileDictionary = {} # The keys are 2-tuples of folder, filename, the values are all valid BBB values
        self._BBBDictionary = {} # The keys are valid BBB values, the values are all 2-tuples of folder, filename

        folderFilenames = os.listdir( givenFolder )
        for possibleFilename in folderFilenames:
            pFUpper = possibleFilename.upper()
            if pFUpper in FILENAMES_TO_IGNORE: continue
            pFUpperProper, pFUpperExt = os.path.splitext( pFUpper )
            ignore = False
            for ending in FILENAME_ENDINGS_TO_IGNORE:
                if pFUpper.endswith( ending): ignore=True; break
            if ignore: continue
            if pFUpper[-1]!='~' and not pFUpperExt[1:] in EXTENSIONS_TO_IGNORE: # Compare without the first dot
                filepath = os.path.join( givenFolder, possibleFilename )
                if os.path.isfile( filepath ): # It's a file not a folder
                    USFMId = self.getUSFMIDFromFile( givenFolder, possibleFilename, filepath )
                    if USFMId:
                        assert filepath not in self._fileDictionary
                        BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromUSFMAbbreviation( USFMId )
                        self._fileDictionary[(givenFolder,possibleFilename,)] = BBB
                        if BBB in self._BBBDictionary: logging.error( "{}Oops, already found {!r} in {}, now we have a duplicate in {}".format( 'getUSFMIDsFromFiles: ' if BibleOrgSysGlobals.debugFlag else '', BBB, self._BBBDictionary[BBB], possibleFilename ) )
                        self._BBBDictionary[BBB] = (givenFolder,possibleFilename,)
        if len(self._fileDictionary) != len(self._BBBDictionary):
            logging.warning( "getUSFMIDsFromFiles: Oops, something went wrong because dictionaries have {} and {} entries".format( len(self._fileDictionary), len(self._BBBDictionary) ) )
        #print( "fD2", self._fileDictionary )
        return len(self._fileDictionary)
    # end of getUSFMIDsFromFiles


    def getFilenameTemplate( self ):
        """
        Returns a pattern/template for USFM filenames where
                lll = language code (lower case) or LLL = language code (UPPER CASE)
                bbb = book code (lower case) or BBB = book code (UPPER CASE)
                dd = Paratext digits (can actually include some letters)
        """
        return self.pattern
    # end of getFilenameTemplate


    def getAllFilenames( self ):
        """
        Return a list of all filenames in our folder.
            This excludes names of subfolders and backup files.
        """
        return self.fileList
    # end of getAllFilenames


    def doListAppend( self, BBB, filename, givenList, caller ):
        """
        Check that BBB and filename are not in the givenList,
                then add them as a 2-tuple.
            If there is a duplicate, remove both (as we're obviously unsure).
        """
        removeBBB = removeFilename = None
        for existingBBB, existingFilename in givenList:
            if existingBBB == BBB:
                if BibleOrgSysGlobals.verbosityLevel > 2: logging.warning( "{} tried to add duplicate {} {} when already had {} (removed both)".format( caller, BBB, filename, existingFilename ) )
                removeBBB, removeFilename = existingBBB, existingFilename
            if existingFilename == filename:
                if BibleOrgSysGlobals.verbosityLevel > 2: logging.warning( "{} tried to add duplicate {} {} when already had {} (removed both)".format( caller, filename, BBB, existingBBB ) )
                removeBBB, removeFilename = existingBBB, existingFilename
        if removeFilename:givenList.remove( (removeBBB,removeFilename,) )
        else: givenList.append( (BBB,filename,) )
    # end of doListAppend


    def getDerivedFilenameTuples( self ):
        """
        Return a theoretical list of valid USFM filenames that match our filename template.
            The result is a list of 2-tuples in the default rough sequence order from the BibleBooksCodes module.
                Each tuple contains ( BBB, filename ) not including the folder path.
        """
        resultList = []
        if self.pattern and self.fileExtension.upper() not in EXTENSIONS_TO_IGNORE:
            if self.pattern == "Dd_BEName": # they are Bibledit style
                for USFMBookCode,BibleditDigits,BBB in self._BibleditBooksCodeNumberTriples:
                    BibleditSignature = BibleditDigits + '_'
                    for BEFilename in BIBLEDIT_FILENAMES: # this doesn't seem very efficient, but it does work
                        if BEFilename.startswith( BibleditSignature ):
                            resultList.append( (BBB,BEFilename+'.'+self.fileExtension,) )
                            break
            elif self.pattern == "dd-OEBName":
                for AltFilename in ALTERNATE_FILENAMES:
                    BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromReferenceNumber( AltFilename[0:2] )
                    resultList.append( (BBB,AltFilename+'.'+self.fileExtension,) )
            else: # they are Paratext style
                for USFMBookCode,USFMDigits,BBB in self._USFMBooksCodeNumberTriples:
                    filename = '*' * len(self.pattern)
                    if self.digitsIndex is not None: filename = filename[:self.digitsIndex] + USFMDigits + filename[self.digitsIndex+len(USFMDigits):]
                    filename = filename[:self.USFMBookCodeIndex] + ( USFMBookCode.upper() if 'BBB' in self.pattern else USFMBookCode ) + filename[self.USFMBookCodeIndex+len(USFMBookCode):]
                    if self.languageCode: filename = filename[:self.languageIndex] + self.languageCode + filename[self.languageIndex+len(self.languageCode):]
                    filename += '.' + self.fileExtension
                    for ix in range( len(filename)): # See if there's any constant characters in the pattern that we need to grab
                        if filename[ix]=='*' and self.pattern[ix]!='*':
                            filename = filename[:ix] + self.pattern[ix] + filename[ix+1:]
                    self.doListAppend( BBB, filename, resultList, "getDerivedFilenameTuples" )
        return BibleOrgSysGlobals.loadedBibleBooksCodes.getSequenceList( resultList )
    # end of getDerivedFilenameTuples


    def getConfirmedFilenameTuples( self, strictCheck=False ):
        """
        Starting with the theoretical list of filenames derived from the deduced template (if we have one),
                return a list of tuples of UPPER CASE book codes with actual (present and readable) USFM filenames.
            If the strictCheck flag is set, the program also looks at the id lines inside the files.

            The result is a list of 2-tuples in the default rough sequence order from the BibleBooksCodes module.
                Each tuple contains ( BBB, filename ) not including the folder path.
        """
        resultList = []
        for BBB,derivedFilename in self.getDerivedFilenameTuples():
            derivedFilepath = os.path.join( self.givenFolderName, derivedFilename )
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( '  getConfirmedFilenameTuples: Checking for existence of: ' + derivedFilename )
            if os.access( derivedFilepath, os.R_OK ):
                if strictCheck:
                    USFMId = self.getUSFMIDFromFile( self.givenFolderName, derivedFilename, derivedFilepath )
                    if USFMId is None:
                        logging.error( "{}internal USFM Id missing for {} in {}".format( 'getConfirmedFilenameTuples: ' if BibleOrgSysGlobals.debugFlag else '', BBB, derivedFilename ) )
                        continue # so it doesn't get added
                    BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromUSFMAbbreviation( USFMId )
                    if BBB != BBB:
                        logging.error( "{}Internal USFM Id ({}{}) doesn't match {} for {}".format( 'getConfirmedFilenameTuples: ' if BibleOrgSysGlobals.debugFlag else '', USFMId, '' if BBB==USFMId else " -> {}".format(BBB), BBB, derivedFilename ) )
                        continue # so it doesn't get added
                self.doListAppend( BBB, derivedFilename, resultList, "getConfirmedFilenameTuples" )
        self.lastTupleList = resultList
        return resultList # No need to sort these because the derived ones are sorted
    # end of USFMFilenames.getConfirmedFilenameTuples


    def getPossibleFilenameTuplesExt( self ):
        """
        Return a list of filename tuples just derived from the list of files in the folder,
                i.e., look only externally at the filenames.
            The result is a list of 2-tuples in the default rough sequence order from the BibleBooksCodes module.
                Each tuple contains ( BBB, filename ) not including the folder path.
        """
        resultList = []
        for possibleFilename in self.fileList:
            pFUpper = possibleFilename.upper()
            if pFUpper in FILENAMES_TO_IGNORE: continue
            pFUpperProper, pFUpperExt = os.path.splitext( pFUpper )
            for USFMBookCode,USFMDigits,BBB in self._USFMBooksCodeNumberTriples:
                ignore = False
                for ending in FILENAME_ENDINGS_TO_IGNORE:
                    if pFUpper.endswith( ending): ignore=True; break
                if ignore: continue
                if USFMBookCode.upper() in pFUpperProper:
                    if pFUpper[-1]!='~' and not pFUpperExt[1:] in EXTENSIONS_TO_IGNORE: # Compare without the first dot
                        self.doListAppend( BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromUSFMAbbreviation( USFMBookCode ), possibleFilename, resultList, "getPossibleFilenameTuplesExt" )
        self.lastTupleList = resultList
        return BibleOrgSysGlobals.loadedBibleBooksCodes.getSequenceList( resultList )
    # end of USFMFilenames.getPossibleFilenameTuplesExt


    def getPossibleFilenameTuplesInt( self ):
        """
        Return a list of filename tuples which contain book codes internally on the \\id line.
            The result is a list of 2-tuples in the default rough sequence order from the BibleBooksCodes module.
                Each tuple contains ( BBB, filename ) not including the folder path.
        """
        resultList = []
        if len( self._BBBDictionary) >= len( self._fileDictionary ): # Choose the longest one
            for BBB in self._BBBDictionary.keys():
                self.doListAppend( BBB, self._BBBDictionary[BBB][1], resultList, "getPossibleFilenameTuplesInt1" )
        else:
            for folder,filename in self._fileDictionary.keys():
                assert folder == self.givenFolderName
                #print( "getPossibleFilenameTuplesInt", folder, filename, self._fileDictionary )
                self.doListAppend( self._fileDictionary[(folder,filename,)], filename, resultList, "getPossibleFilenameTuplesInt2" )
        self.lastTupleList = resultList
        return BibleOrgSysGlobals.loadedBibleBooksCodes.getSequenceList( resultList )
    # end of USFMFilenames.getPossibleFilenameTuplesInt


    def getMaximumPossibleFilenameTuples( self, strictCheck=False ):
        """
        Find the method that finds the maximum number of USFM Bible files.
            The result is a list of 2-tuples in the default rough sequence order from the BibleBooksCodes module.
                Each tuple contains ( BBB, filename ) not including the folder path.
        """
        #if BibleOrgSysGlobals.debugFlag: print( "getMaximumPossibleFilenameTuples( {} )".format( strictCheck ) )

        resultString, resultList = 'Confirmed', self.getConfirmedFilenameTuples()
        resultListExt = self.getPossibleFilenameTuplesExt()
        if len(resultListExt) > len(resultList):
            resultString, resultList = 'External', resultListExt
        resultListInt = self.getPossibleFilenameTuplesInt()
        if len(resultListInt) > len(resultList):
            resultString, resultList = 'Internal', resultListInt
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "getMaximumPossibleFilenameTuples: using {}".format( resultString ) )

        if strictCheck or BibleOrgSysGlobals.strictCheckingFlag:
            #if BibleOrgSysGlobals.debugFlag: print( "  getMaximumPossibleFilenameTuples doing strictCheck…" )
            for BBB,filename in resultList[:]:
                firstLine = BibleOrgSysGlobals.peekIntoFile( filename, self.givenFolderName )
                #print( 'UFN', repr(firstLine) )
                if firstLine is None: resultList.remove( (BBB,filename) ); continue # seems we couldn't decode the file
                if firstLine and firstLine[0]==chr(65279): #U+FEFF or \ufeff
                    logging.info( "USFMBibleFileCheck: Detected Unicode Byte Order Marker (BOM) in {}".format( filename ) )
                    firstLine = firstLine[1:] # Remove the Unicode Byte Order Marker (BOM)
                if not firstLine or firstLine[0] != '\\': # don't allow a blank first line and must start with a backslash
                    resultList.remove( (BBB,filename) )

        self.lastTupleList = resultList
        #print( "getMaximumPossibleFilenameTuples is returning", resultList )
        return resultList # No need to sort these, coz all the above calls produce sorted results
    # end of USFMFilenames.getMaximumPossibleFilenameTuples


    def getUnusedFilenames( self ):
        """
        Return a list of filenames which didn't seem to be USFM files.
            NOTE: This list depends on which "find" routine above was run last!
            The order of the filenames in the list has no meaning.
        """
        folderFilenames = os.listdir( self.givenFolderName )
        #print( len(folderFilenames), folderFilenames )
        if self.lastTupleList is None: return None # Not sure what list they're after here
        #print( len(self.lastTupleList), self.lastTupleList )
        for BBB,actualFilename in self.lastTupleList:
            #print( BBB, actualFilename )
            if actualFilename in folderFilenames: folderFilenames.remove( actualFilename ) # Sometimes it can be removed already if we had (invalid) duplicates in the lastTupleList
        return folderFilenames
    # end of getUnusedFilenames


    def getSSFFilenames( self, searchAbove=False, auto=True ):
        """
        Return a list of full pathnames of .ssf files in the folder.
            NOTE: USFM projects don't usually have the .ssf files in the project folder,
                but 'backed-up' projects often do.
            If searchAbove is set to True and no ssf files are found in the given folder,
                this routine will attempt to search the next folder up the file hierarchy.
                Furthermore, unless auto is set to False,
                    it will try to find the correct one from multiple SSFs.
        """
        def getSSFFilenamesHelper( folder ):
            resultPathlist = []
            files = os.listdir( folder )
            for foundFilename in files:
                if not foundFilename.endswith('~'): # Ignore backup files
                    foundFileBit, foundExtBit = os.path.splitext( foundFilename )
                    if foundExtBit.lower()=='.ssf':
                        resultPathlist.append( os.path.join( folder, foundFilename ) )
            return resultPathlist
        # end of getSSFFilenamesHelper

        filelist = getSSFFilenamesHelper( self.givenFolderName )
        if not filelist and searchAbove: # try the next level up
            filelist = getSSFFilenamesHelper( os.path.join( self.givenFolderName, '../' ) )
            if auto and len(filelist)>1: # See if we can help them by automatically choosing the right one
                count, index = 0, -1
                for j, filepath in enumerate(filelist): # Check if we can find a single matching ssf file
                    foundPathBit, foundExtBit = os.path.splitext( filepath )
                    foundPathBit, foundFileBit = os.path.split( foundPathBit )
                    #print( foundPathBit, foundFileBit, foundExtBit, self.givenFolderName )
                    if foundFileBit in str(self.givenFolderName):
                        index = j; count += 1 # Take a guess that this might be the right one
                #print( count, index )
                if count==1 and index!=-1: filelist = [ filelist[index] ] # Found exactly one so reduce the list down to this one filepath
        if debuggingThisModule:
            print( f"getSSFFilenames: returning filelist ({len(filelist)})={filelist}" )
        return filelist
    # end of getSSFFilenames
# end of class USFMFiles


def demo() -> None:
    """ Demonstrate finding files in some USFM Bible folders. """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( programNameVersion )

    # These are relative paths -- you can replace these with your test folder(s)
    testFolders = (BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMTest1/' ), BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMTest2/' ),
                   BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USXTest1/' ), BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USXTest2/' ),
                   BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFM-WEB/' ), BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFM-OEB/' ),
                   BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMErrorProject/' ),
                   Path( '/srv/AutoProcesses/Processed/' ),
                   Path( '/srv/AutoProcesses/Processed/Test/' ),
                   )
    for j, testFolder in enumerate( testFolders ):
        print( '\n{}'.format( j+1 ) )
        if os.access( testFolder, os.R_OK ):
            UFns = USFMFilenames( testFolder )
            print( UFns )
            result = UFns.getAllFilenames(); print( "\nAll:", len(result), result )
            result = UFns.getDerivedFilenameTuples(); print( "\nDerived:", UFns.getFilenameTemplate(), len(result), result )
            result = UFns.getConfirmedFilenameTuples(); print( "\nConfirmed:", UFns.getFilenameTemplate(), len(result), result )
            result = UFns.getUnusedFilenames(); print( "Unused:", len(result), result )
            result = UFns.getConfirmedFilenameTuples( strictCheck=True ); print( "\nConfirmed (with double check):", UFns.getFilenameTemplate(), len(result), result )
            result = UFns.getUnusedFilenames(); print( "Unused:", len(result), result )
            result = UFns.getPossibleFilenameTuplesExt(); print( "\nPossibleExt:", len(result), result )
            result = UFns.getUnusedFilenames(); print( "Unused:", len(result), result )
            result = UFns.getPossibleFilenameTuplesInt(); print( "\nPossibleInt:", len(result), result )
            result = UFns.getUnusedFilenames(); print( "Unused:", len(result), result )
            result = UFns.getMaximumPossibleFilenameTuples(); print( "\nMaxPoss:", len(result), result )
            result = UFns.getMaximumPossibleFilenameTuples( strictCheck=True ); print( "\nMaxPoss (strict):", len(result), result )
            result = UFns.getUnusedFilenames(); print( "Unused:", len(result), result )
            result = UFns.getSSFFilenames(); print( "\nSSF:", len(result), result )
        else: print( f"Sorry, test folder '{testFolder}' doesn't exist on this computer." )

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    demo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of USFMFilenames.py
