#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# USFMFilenames.py
#   Last modified: 2013-04-23 by RJH (also update versionString below)
#
# Module handling USFM Bible filenames
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
Module for creating and manipulating USFM filenames.
"""

progName = "USFM Bible filenames handler"
versionString = "0.57"


import os, logging
from gettext import gettext as _


import Globals


# The filenames produced by the Bibledit program seem to have a .usfm extension (Info below is from gtk/src/bookdata.cpp 2012-07-11)
BibleditFilenames = ( '1_Genesis', '2_Exodus', '3_Leviticus', '4_Numbers', '5_Deuteronomy', '6_Joshua', '7_Judges', '8_Ruth', '9_1_Samuel', '10_2_Samuel',
    '11_1_Kings', '12_2_Kings', '13_1_Chronicles', '14_2_Chronicles', '15_Ezra', '16_Nehemiah', '17_Esther', '18_Job', '19_Psalms', '20_Proverbs', '21_Ecclesiastes',
    '22_Song_of_Solomon', '23_Isaiah', '24_Jeremiah', '25_Lamentations', '26_Ezekiel', '27_Daniel', '28_Hosea', '29_Joel', '30_Amos', '31_Obadiah', '32_Jonah',
    '33_Micah', '34_Nahum', '35_Habakkuk', '36_Zephaniah', '37_Haggai', '38_Zechariah', '39_Malachi',
    '40_Matthew', '41_Mark', '42_Luke', '43_John', '44_Acts', '45_Romans', '46_1_Corinthians', '47_2_Corinthians', '48_Galatians', '49_Ephesians', '50_Philippians',
    '51_Colossians', '52_1_Thessalonians', '53_2_Thessalonians', '54_1_Timothy', '55_2_Timothy', '56_Titus', '57_Philemon',
    '58_Hebrews', '59_James', '60_1_Peter', '61_2_Peter', '62_1_John', '63_2_John', '64_3_John', '65_Jude', '66_Revelation',
    '67_Front_Matter', '68_Back_Matter', '69_Other_Material', '70_Tobit', '71_Judith', '72_Esther_(Greek)', '73_Wisdom_of_Solomon', '74_Sirach', '75_Baruch',
    '76_Letter_of_Jeremiah', '77_Song_of_the_Three_Children', '78_Susanna', '79_Bel_and_the_Dragon', '80_1_Maccabees', '81_2_Maccabees',
    '82_1_Esdras', '83_Prayer_of_Manasses', '84_Psalm_151', '85_3_Maccabees', '86_2_Esdras', '87_4_Maccabees', '88_Daniel_(Greek)' )

filenameEndingsToIgnore = ('.ZIP.GO', '.ZIP.DATA',) # Must be UPPERCASE
extensionsToIgnore = ('ZIP', 'BAK', 'LOG', 'HTM','HTML', 'XML', 'OSIS', 'USX', 'TXT', 'STY', 'LDS', 'SSF', 'VRS',) # Must be UPPERCASE



class USFMFilenames:
    """
    Class for creating and manipulating USFM filenames.

    Always returns lists of USFM filenames in the default rough sequence order from the BibleBooksCodes module.
    """

    def __init__( self, givenFolderName ):
        """Create the object by inspecting files in the given folder.

            Creates a self.pattern (Paratext template) for USFM filenames where
                nnn = language code (lower case) or NNN = language code (UPPER CASE)
                bbb = book code (lower case) or BBB = book code (UPPER CASE)
                dd = digits
        """
        #print( "USFMFilenames( {} )".format( givenFolderName ) )
        self.givenFolderName = givenFolderName
        self.pattern, self.fileExtension = '', ''
        self.fileList = [] # A list of all files in our folder (excluding folder names and backup filenames)
        self._fileDictionary = {} # The keys are 2-tuples of folder, filename, the values are all valid BBB values
        self._BBBDictionary = {} # The keys are valid BBB values, the values are all 2-tuples of folder, filename

        # Check that the given folder is readable
        if not os.access( self.givenFolderName, os.R_OK ):
            logging.critical( _("USFMFilenames: Given '{}' folder is unreadable").format( self.givenFolderName ) )
            return

        # Get the data tables that we need for proper checking
        self._USFMBooksCodes = Globals.BibleBooksCodes.getAllUSFMBooksCodes()
        self._USFMBooksCodesUpper = [x.upper() for x in self._USFMBooksCodes]
        self._USFMBooksCodeNumberTriples = Globals.BibleBooksCodes.getAllUSFMBooksCodeNumberTriples()
        self._BibleditBooksCodeNumberTriples = Globals.BibleBooksCodes.getAllBibleditBooksCodeNumberTriples()

        # Find how many files are in our folder
        self.lastTupleList = None
        for possibleFilename in os.listdir( self.givenFolderName ):
            pFUpper = possibleFilename.upper()
            pFUpperProper, pFUpperExt = os.path.splitext( pFUpper )
            ignore = False
            for ending in filenameEndingsToIgnore:
                if pFUpper.endswith( ending): ignore=True; break
            if ignore: continue
            if not pFUpperExt[1:] in extensionsToIgnore: # Compare without the first dot
                filepath = os.path.join( self.givenFolderName, possibleFilename )
                if os.path.isfile( filepath ): # It's a file not a folder
                        self.fileList.append( possibleFilename )
        #print( "fL", self.fileList )
        #if not self.fileList: logging.error( _("No files at all in given folder: '{}'").format( self.givenFolderName) ); return

        # See if we can find a pattern for these filenames
        matched = False
        for foundFilename in self.fileList:
            foundFileBit, foundExtBit = os.path.splitext( foundFilename )
            foundLength = len( foundFileBit )
            #print( foundFileBit, foundExtBit )
            matched = False
            if '_' in foundFileBit and foundExtBit and foundExtBit[0]=='.': # Check for possible Bibledit filenames first
                for USFMBookCode,BibleditDigits,bookReferenceCode in self._BibleditBooksCodeNumberTriples:
                    BibleditSignature = BibleditDigits + '_'
                    if BibleditSignature in foundFileBit and foundFileBit in BibleditFilenames and foundExtBit == '.usfm':
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
                if matched: break
            if matched: break
            # Didn't find a Bibledit filename -- maybe it's a Paratext style or some kind of freestyle
            containsDigits = False
            for char in foundFileBit:
                if char.isdigit():
                    containsDigits = True
                    break
            if containsDigits and foundExtBit and foundExtBit[0]=='.':
                for USFMBookCode,USFMDigits,bookReferenceCode in self._USFMBooksCodeNumberTriples:
                    if USFMDigits in foundFileBit and (USFMBookCode in foundFileBit or USFMBookCode.upper() in foundFileBit):
                        digitsIndex = foundFileBit.index( USFMDigits )
                        USFMBookCodeIndex = foundFileBit.index(USFMBookCode) if USFMBookCode in foundFileBit else foundFileBit.index(USFMBookCode.upper())
                        USFMBookCode = foundFileBit[USFMBookCodeIndex:USFMBookCodeIndex+3]
                        #print( digitsIndex, USFMBookCodeIndex, USFMBookCode )
                        if foundLength>=8 and digitsIndex==0 and USFMBookCodeIndex==2: # Found a form like 01GENlanguage.xyz
                            self.languageIndex = 5
                            self.languageCode = foundFileBit[self.languageIndex:self.languageIndex+foundLength-5]
                            self.digitsIndex = digitsIndex
                            self.USFMBookCodeIndex = USFMBookCodeIndex
                            self.pattern = "ddbbb" + 'l'*(foundLength-5)
                            matched = True
                        elif foundLength==8 and digitsIndex==3 and USFMBookCodeIndex==5: # Found a form like lng01GEN.xyz
                            self.languageIndex = 0
                            self.languageCode = foundFileBit[self.languageIndex:self.languageIndex+foundLength-5]
                            self.digitsIndex = digitsIndex
                            self.USFMBookCodeIndex = USFMBookCodeIndex
                            self.pattern = "lllddbbb"
                            matched = True
                        else: # we'll try to be more generic
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
                            if Globals.verbosityLevel > 2: print( "Pattern is '{}'".format( self.pattern ) )
                            if '*' not in self.pattern: matched = True
                            else: # we'll try to be even more generic
                                self.languageIndex = self.digitsIndex = None
                                self.languageCode = None
                                self.USFMBookCodeIndex = USFMBookCodeIndex
                                self.pattern = '*' * foundLength
                                self.pattern = self.pattern[:USFMBookCodeIndex] + 'bbb' + self.pattern[USFMBookCodeIndex+3:]
                                if Globals.verbosityLevel > 2: print( "More generic pattern is '{}'".format( self.pattern ) )
                                matched = True
                        if matched:
                            if self.languageCode and self.languageCode.isupper(): self.pattern = self.pattern.replace( 'l', 'L' )
                            if USFMBookCode.isupper(): self.pattern = self.pattern.replace( 'bbb', 'BBB' )
                            self.fileExtension = foundExtBit[1:]
                            break
                if matched: break
            if matched: break
        #if not matched: logging.info( _("Unable to recognize pattern of valid USFM files in ") + self.givenFolderName )
        #print( "USFMFilenames: pattern='{}' fileExtension='{}'".format( self.pattern, self.fileExtension ) )

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
        result = "USFM Filenames object"
        indent = 2
        if self.givenFolderName: result += ('\n' if result else '') + ' '*indent + _("Folder: {}").format( self.givenFolderName )
        if self.pattern: result += ('\n' if result else '') + ' '*indent + _("Filename pattern: {}").format( self.pattern )
        if self.fileExtension: result += ('\n' if result else '') + ' '*indent + _("File extension: {}").format( self.fileExtension )
        if self.fileList and Globals.verbosityLevel > 2: result += ('\n' if result else '') + ' '*indent + _("File list: {}").format( self.fileList )
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


    def getUSFMIDFromFile( self, folder, thisFilename, filepath ):
        """ Try to intelligently get the USFMId from the first line in the file (which should be the \\id line). """
        # Look for the USFM id in the ID line (which should be the first line in a USFM file)
        try:
            with open( filepath, 'rt' ) as possibleUSFMFile: # Automatically closes the file when done
                lineNumber = 0
                for line in possibleUSFMFile:
                    lineNumber += 1
                    if line[-1]=='\n': line = line[:-1] # Removing trailing newline character
                    #print( thisFilename, lineNumber, line )
                    if line.startswith( '\\id ' ):
                        if len(line)<5 and Globals.logErrorsFlag: logging.warning( "id line '{}' in {} is too short".format( line, filepath ) )
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
                        else: print( "But '{}' wasn't a valid USFM ID in {}!!!".format( UCToken0, thisFilename ) )
                        break
                    elif lineNumber == 1 and Globals.logErrorsFlag:
                        if line.startswith ( '\\' ):
                            logging.warning( "First line in {} in {} starts with a backslash but not an id line '{}'".format( thisFilename, folder, line ) )
                        elif not line:
                            logging.info( "First line in {} in {} appears to be blank".format( thisFilename, folder ) )
                    if lineNumber >= 2: break # We only look at the first one or two lines
        except UnicodeDecodeError:
            if thisFilename != 'usfm-color.sty': # Seems this file isn't UTF-8, but we don't need it here anyway so ignore it
                if Globals.logErrorsFlag: logging.warning( _("Seems we couldn't decode Unicode in '{}'").format( filepath ) ) # Could be binary or a different encoding
        return None
    # end of getUSFMIDFromFile


    def getUSFMIDsFromFiles( self, givenFolder ):
        """ Go through all the files in the given folder and see how many USFM IDs we can find.
                Populates the two dictionaries.
                Returns the number of files found. """
        # Empty the two dictionaries
        self._fileDictionary = {} # The keys are 2-tuples of folder, filename, the values are all valid BBB values
        self._BBBDictionary = {} # The keys are valid BBB values, the values are all 2-tuples of folder, filename
        folderFilenames = os.listdir( givenFolder )
        for possibleFilename in folderFilenames:
            pFUpper = possibleFilename.upper()
            pFUpperProper, pFUpperExt = os.path.splitext( pFUpper )
            ignore = False
            for ending in filenameEndingsToIgnore:
                if pFUpper.endswith( ending): ignore=True; break
            if ignore: continue
            if not pFUpperExt[1:] in extensionsToIgnore: # Compare without the first dot
                filepath = os.path.join( givenFolder, possibleFilename )
                if os.path.isfile( filepath ): # It's a file not a folder
                    USFMId = self.getUSFMIDFromFile( givenFolder, possibleFilename, filepath )
                    if USFMId:
                        assert( filepath not in self._fileDictionary )
                        BBB = Globals.BibleBooksCodes.getBBBFromUSFM( USFMId )
                        self._fileDictionary[(givenFolder,possibleFilename,)] = BBB
                        if BBB in self._BBBDictionary: logging.error( "getUSFMIDsFromFiles: Oops, already found '{}' in {}, now we have a duplicate in {}".format( BBB, self._BBBDictionary[BBB], possibleFilename ) )
                        self._BBBDictionary[BBB] = (givenFolder,possibleFilename,)
        if len(self._fileDictionary) != len(self._BBBDictionary):
            logging.warning( "getUSFMIDsFromFiles: Oops, something went wrong because dictionaries have {} and {} entries".format( len(self._fileDictionary), len(self._BBBDictionary) ) )
        #print( "fD2", self._fileDictionary )
        return len(self._fileDictionary)
    # end of getUSFMIDsFromFiles


    def getFilenameTemplate( self ):
        """ Returns a pattern/template for USFM filenames where
                lll = language code (lower case) or LLL = language code (UPPER CASE)
                bbb = book code (lower case) or BBB = book code (UPPER CASE)
                dd = Paratext digits (can actually include some letters) """
        return self.pattern
    # end of getFilenameTemplate


    def getAllFilenames( self ):
        """Return a list of all filenames in our folder.
            This excludes names of subfolders and backup files. """
        return self.fileList
    # end of getAllFilenames


    def doListAppend( self, BBB, filename, givenList, caller ):
        """ Check that BBB and filename are not in the givenList,
                then add them as a 2-tuple.
            If there is a duplicate, remove both (as we're obviously unsure). """
        assert( isinstance( BBB, str ) )
        assert( isinstance( filename, str ) )
        assert( isinstance( givenList, list ) )
        assert( isinstance( caller, str ) )
        removeBBB = removeFilename = None
        for existingBBB, existingFilename in givenList:
            if existingBBB == BBB:
                if Globals.verbosityLevel > 2: logging.warning( "{} tried to add duplicate {} {} when already had {} (removed both)".format( caller, BBB, filename, existingFilename ) )
                removeBBB, removeFilename = existingBBB, existingFilename
            if existingFilename == filename:
                if Globals.verbosityLevel > 2: logging.warning( "{} tried to add duplicate {} {} when already had {} (removed both)".format( caller, filename, BBB, existingBBB ) )
                removeBBB, removeFilename = existingBBB, existingFilename
        if removeFilename:givenList.remove( (removeBBB,removeFilename,) )
        else: givenList.append( (BBB,filename,) )
    # end of doListAppend


    def getDerivedFilenameTuples( self ):
        """Return a theoretical list of valid USFM filenames that match our filename template.
            The result is a list of 2-tuples in the default rough sequence order from the BibleBooksCodes module.
                Each tuple contains ( BBB, filename ) not including the folder path.
        """
        resultList = []
        if self.pattern and self.fileExtension.upper() not in extensionsToIgnore:
            if self.pattern == "Dd_BEName": # they are Bibledit style
                for USFMBookCode,BibleditDigits,bookReferenceCode in self._BibleditBooksCodeNumberTriples:
                    BibleditSignature = BibleditDigits + '_'
                    for BEFilename in BibleditFilenames: # this doesn't seem very efficient, but it does work
                        if BEFilename.startswith( BibleditSignature ):
                            resultList.append( (bookReferenceCode,BEFilename+'.'+self.fileExtension,) )
                            break
            else: # they are Paratext style
                for USFMBookCode,USFMDigits,bookReferenceCode in self._USFMBooksCodeNumberTriples:
                    filename = '*' * len(self.pattern)
                    if self.digitsIndex is not None: filename = filename[:self.digitsIndex] + USFMDigits + filename[self.digitsIndex+len(USFMDigits):]
                    filename = filename[:self.USFMBookCodeIndex] + ( USFMBookCode.upper() if 'BBB' in self.pattern else USFMBookCode ) + filename[self.USFMBookCodeIndex+len(USFMBookCode):]
                    if self.languageCode: filename = filename[:self.languageIndex] + self.languageCode + filename[self.languageIndex+len(self.languageCode):]
                    filename += '.' + self.fileExtension
                    for ix in range( 0, len(filename)): # See if there's any constant characters in the pattern that we need to grab
                        if filename[ix]=='*' and self.pattern[ix]!='*':
                            filename = filename[:ix] + self.pattern[ix] + filename[ix+1:]
                    self.doListAppend( bookReferenceCode, filename, resultList, "getDerivedFilenameTuples" )
        return Globals.BibleBooksCodes.getSequenceList( resultList )
    # end of getDerivedFilenameTuples


    def getConfirmedFilenameTuples( self, doubleCheck=False ):
        """ Starting with the theoretical list of filenames derived from the deduced template (if we have one),
                return a list of tuples of UPPER CASE book codes with actual (present and readable) USFM filenames.
            If the doubleCheck flag is set, the program also looks at the id lines inside the files.

            The result is a list of 2-tuples in the default rough sequence order from the BibleBooksCodes module.
                Each tuple contains ( BBB, filename ) not including the folder path.
        """
        resultList = []
        for bookReferenceCode,derivedFilename in self.getDerivedFilenameTuples():
            derivedFilepath = os.path.join( self.givenFolderName, derivedFilename )
            if Globals.verbosityLevel > 2: print( '  getConfirmedFilenameTuples: Checking for existence of: ' + derivedFilename )
            if os.access( derivedFilepath, os.R_OK ):
                if doubleCheck:
                    USFMId = self.getUSFMIDFromFile( self.givenFolderName, derivedFilename, derivedFilepath )
                    if USFMId is None:
                        logging.error( "getConfirmedFilenameTuples: internal USFM Id missing for {} in {}".format( bookReferenceCode, derivedFilename ) )
                        continue # so it doesn't get added
                    BBB = Globals.BibleBooksCodes.getBBBFromUSFM( USFMId )
                    if BBB != bookReferenceCode:
                        logging.error( "getConfirmedFilenameTuples: internal USFM Id ({}{}) doesn't match {} for {}".format( USFMId, '' if BBB==USFMId else " -> {}".format(BBB), bookReferenceCode, derivedFilename ) )
                        continue # so it doesn't get added
                self.doListAppend( bookReferenceCode, derivedFilename, resultList, "getConfirmedFilenameTuples" )
        self.lastTupleList = resultList
        return resultList # No need to sort these because the derived ones are sorted
    # end of getConfirmedFilenameTuples


    def getPossibleFilenameTuplesExt( self ):
        """ Return a list of filename tuples just derived from the list of files in the folder,
                i.e., look only external at the filenames.
            The result is a list of 2-tuples in the default rough sequence order from the BibleBooksCodes module.
                Each tuple contains ( BBB, filename ) not including the folder path.
        """
        resultList = []
        for possibleFilename in self.fileList:
            pFUpper = possibleFilename.upper()
            pFUpperProper, pFUpperExt = os.path.splitext( pFUpper )
            for USFMBookCode,USFMDigits,bookReferenceCode in self._USFMBooksCodeNumberTriples:
                ignore = False
                for ending in filenameEndingsToIgnore:
                    if pFUpper.endswith( ending): ignore=True; break
                if ignore: continue
                if USFMBookCode.upper() in pFUpperProper:
                    if not pFUpperExt[1:] in extensionsToIgnore: # Compare without the first dot
                        self.doListAppend( Globals.BibleBooksCodes.getBBBFromUSFM( USFMBookCode ), possibleFilename, resultList, "getPossibleFilenameTuplesExt" )
        self.lastTupleList = resultList
        return Globals.BibleBooksCodes.getSequenceList( resultList )
    # end of getPossibleFilenameTuplesExt


    def getPossibleFilenameTuplesInt( self ):
        """Return a list of filename tuples which contain book codes internally on the \\id line.
            The result is a list of 2-tuples in the default rough sequence order from the BibleBooksCodes module.
                Each tuple contains ( BBB, filename ) not including the folder path.
        """
        resultList = []
        if len( self._BBBDictionary) >= len( self._fileDictionary ): # Choose the longest one
            for BBB in self._BBBDictionary.keys():
                self.doListAppend( BBB, self._BBBDictionary[BBB][1], resultList, "getPossibleFilenameTuplesInt1" )
        else:
            for folder,filename in self._fileDictionary.keys():
                assert( folder == self.givenFolderName )
                #print( "getPossibleFilenameTuplesInt", folder, filename, self._fileDictionary )
                self.doListAppend( self._fileDictionary[(folder,filename,)], filename, resultList, "getPossibleFilenameTuplesInt2" )
        self.lastTupleList = resultList
        return Globals.BibleBooksCodes.getSequenceList( resultList )
    # end of getPossibleFilenameTuplesInt


    def getMaximumPossibleFilenameTuples( self ):
        """ Find the method that finds the maximum number of USFM Bible files.
            The result is a list of 2-tuples in the default rough sequence order from the BibleBooksCodes module.
                Each tuple contains ( BBB, filename ) not including the folder path.
        """
        resultString, resultList = "Confirmed", self.getConfirmedFilenameTuples()
        resultListExt = self.getPossibleFilenameTuplesExt()
        if len(resultListExt)>len(resultList):
            resultString, resultList = "External", resultListExt
        resultListInt = self.getPossibleFilenameTuplesInt()
        if len(resultListInt)>len(resultList):
            resultString, resultList = "Internal", resultListInt
        if Globals.verbosityLevel > 2: print( "getMaximumPossibleFilenameTuples: using {}".format( resultString ) )
        self.lastTupleList = resultList
        #print( "getMaximumPossibleFilenameTuples is returning", resultList )
        return resultList # No need to sort these, coz all the above calls produce sorted results
    # end of getMaximumPossibleFilenameTuples


    def getUnusedFilenames( self ):
        """ Return a list of filenames which didn't seem to be USFM files.
            NOTE: This list depends on which "find" routine above was run last!
            The order of the filenames in the list has no meaning. """
        folderFilenames = os.listdir( self.givenFolderName )
        if self.lastTupleList is None: return None # Not sure what list they're after here
        #print( len(self.lastTupleList), self.lastTupleList )
        for bookReferenceCode,actualFilename in self.lastTupleList:
            #print( bookReferenceCode, actualFilename )
            if actualFilename in folderFilenames: folderFilenames.remove( actualFilename ) # Sometimes it can be removed already if we had (invalid) duplicates in the lastTupleList
        return folderFilenames
    # end of getUnusedFilenames


    def getSSFFilenames( self, searchAbove=False, auto=True ):
        """ Return a list of full pathnames of .ssf files in the folder.
            NOTE: USFM projects don't usually have the .ssf files in the project folder,
                but 'backed-up' projects often do.
            If searchAbove is set to True and no ssf files are found in the given folder,
                this routine will attempt to search the next folder up the file hierarchy.
                Furthermore, unless auto is set to False,
                    it will try to find the correct one from multiple SSFs."""
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
                    if foundFileBit in self.givenFolderName: index = j; count += 1 # Take a guess that this might be the right one
                #print( count, index )
                if count==1 and index!=-1: filelist = [ filelist[index] ] # Found exactly one so reduce the list down to this one filepath
        return filelist
    # end of getSSFFilenames
# end of class USFMFiles


def demo():
    """ Demonstrate finding files in some USFM Bible folders. """
    # Configure basic logging
    logging.basicConfig( format='%(levelname)s: %(message)s', level=logging.INFO ) # Removes the unnecessary and unhelpful 'root:' part of the logged messages

    # Handle command line parameters
    from optparse import OptionParser
    parser = OptionParser( version="v{}".format( versionString ) )
    Globals.addStandardOptionsAndProcess( parser )

    if Globals.verbosityLevel > 0: print( "{} V{}".format( progName, versionString ) )

    # These are relative paths -- you can replace these with your test folder(s)
    testFolders = ("Tests/DataFilesForTests/USFMTest1/", "Tests/DataFilesForTests/USFMTest2/",
                   'Tests/DataFilesForTests/USXTest1/', 'Tests/DataFilesForTests/USXTest2/',
                   "../../../../../SSD/AutoProcesses/Processed/","../../../../../SSD/AutoProcesses/Processed/Test/",)
    for j, testFolder in enumerate( testFolders ):
        print( '\n{}'.format( j+1 ) )
        if os.access( testFolder, os.R_OK ):
            UFns = USFMFilenames( testFolder )
            print( UFns )
            result = UFns.getAllFilenames(); print( "\nAll:", len(result), result )
            result = UFns.getDerivedFilenameTuples(); print( "\nDerived:", UFns.getFilenameTemplate(), len(result), result )
            result = UFns.getConfirmedFilenameTuples(); print( "\nConfirmed:", UFns.getFilenameTemplate(), len(result), result )
            result = UFns.getUnusedFilenames(); print( "Unused:", len(result), result )
            result = UFns.getConfirmedFilenameTuples( doubleCheck=True ); print( "\nConfirmed (with double check):", UFns.getFilenameTemplate(), len(result), result )
            result = UFns.getUnusedFilenames(); print( "Unused:", len(result), result )
            result = UFns.getPossibleFilenameTuplesExt(); print( "\nPossibleExt:", len(result), result )
            result = UFns.getUnusedFilenames(); print( "Unused:", len(result), result )
            result = UFns.getPossibleFilenameTuplesInt(); print( "\nPossibleInt:", len(result), result )
            result = UFns.getUnusedFilenames(); print( "Unused:", len(result), result )
            result = UFns.getMaximumPossibleFilenameTuples(); print( "\nMaxPoss:", len(result), result )
            result = UFns.getUnusedFilenames(); print( "Unused:", len(result), result )
            result = UFns.getSSFFilenames(); print( "\nSSF:", len(result), result )
        else: print( "Sorry, test folder '{}' doesn't exist on this computer.".format( testFolder ) )

if __name__ == '__main__':
    demo()
# end of USFMFilenames.py