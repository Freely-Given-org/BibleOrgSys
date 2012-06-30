#!/usr/bin/python3
#
# USFMFilenames.py
#   Last modified: 2012-06-30 by RJH (also update versionString below)
#
# Module handling USFM Bible filenames
#
# Copyright (C) 2010-2012 Robert Hunt
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
versionString = "0.54"


import os, logging
from gettext import gettext as _


import Globals
from BibleBooksCodes import BibleBooksCodes


class USFMFilenames:
    """
    Class for creating and manipulating USFM Filenames.
    """

    def __init__( self, folder ):
        """Create the object by inspecting files in the given folder.

            Creates a self.pattern (Paratext template) for USFM filenames where
                nnn = language code (lower case) or NNN = language code (UPPER CASE)
                bbb = book code (lower case) or BBB = book code (UPPER CASE)
                dd = digits
        """
        # Get the data tables that we need for proper checking
        self._BibleBooksCodes = BibleBooksCodes().loadData()
        self._USFMBooksCodes = self._BibleBooksCodes.getAllUSFMBooksCodes()
        self._USFMBooksCodesUpper = [x.upper() for x in self._USFMBooksCodes]
        self._USFMBooksCodeNumberTriples = self._BibleBooksCodes.getAllUSFMBooksCodeNumberTriples()

        # Find how many files are in our folder
        self.folder, self.lastTupleList = folder, None
        self.fileList = [] # A list of all files in our folder (excluding folder names and backup filenames)
        for possibleFilename in os.listdir( self.folder ):
            if not possibleFilename.endswith('~') and not possibleFilename.upper().endswith('.BAK'): # Ignore backup files
                filepath = os.path.join( self.folder, possibleFilename )
                if os.path.isfile( filepath ): # It's a file not a folder
                    self.fileList.append( possibleFilename )
        if not self.fileList: logging.error( _("No files at all in given folder: '{}'").format( self.folder) ); return

        # See if we can find a pattern for these filenames
        self.pattern, self.fileExtension = '', ''
        for foundFilename in self.fileList:
            foundFileBit, foundExtBit = os.path.splitext( foundFilename )
            foundLength = len( foundFileBit )
            #print( foundFileBit, foundExtBit )
            containsDigits = False
            for char in foundFilename:
                if char.isdigit():
                    containsDigits = True
                    break
            matched = False
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
        if not matched: logging.info( _("Unable to recognize pattern of valid USFM files in ") + folder )
        #print( "USFMFilenames: pattern='{}' fileExtension='{}'".format( self.pattern, self.fileExtension ) )

        # Also, try looking inside the files
        self.fileDictionary = {} # The keys are 2-tuples of folder, filename, the values are all valid BBB values
        self.BBBDictionary = {} # The keys are valid BBB values, the values are all 2-tuples of folder, filename
        self.getUSFMIDsFromFiles( self.folder ) # Fill the above dictionaries
    # end of __init__
        

    def __str__( self ):
        """
        This method returns the string representation of an object.
        
        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = "USFM Filenames object"
        indent = 2
        if self.folder: result += ('\n' if result else '') + ' '*indent + _("Folder: {}").format( self.folder )
        if self.pattern: result += ('\n' if result else '') + ' '*indent + _("Filename pattern: {}").format( self.pattern )
        if self.fileExtension: result += ('\n' if result else '') + ' '*indent + _("File extension: {}").format( self.fileExtension )
        if self.fileList and Globals.verbosityLevel > 2: result += ('\n' if result else '') + ' '*indent + _("File list: {}").format( self.fileList )
        return result
    # end of __str___


    def getUSFMIDFromFile( self, folder, thisFilename, filepath ):
        """ Try to intelligently get the USFMId from the first line in the file (which should be the \\id line). """
        # Look for the USFM id in the ID line (which should be the first line in a USFM file)
        with open( filepath ) as possibleUSFMFile: # Automatically closes the file when done
            lineNumber = 0
            for line in possibleUSFMFile:
                lineNumber += 1
                if line[-1]=='\n': line = line[:-1] # Removing trailing newline character
                if line.startswith( '\\id ' ):
                    if len(line)<5: logging.warning( "id line '{}' in {} is too short".format( line, filepath ) )
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
                    else: print( "But '{}' wasn't a valid USFM ID!!!".format( UCToken0 ) )
                    break
                elif lineNumber == 1:
                    if line.startswith ( '\\' ):
                        logging.warning( "First line in {} in {} starts with a backslash but not an id line '{}'".format( thisFilename, folder, line ) )
                    elif not line:
                        logging.info( "First line in {} in {} appears to be blank".format( thisFilename, folder ) )
                if lineNumber >= 2: break # We only look at the first one or two lines
        return None
    # end of getUSFMIDFromFile


    def getUSFMIDsFromFiles( self, givenFolder ):
        """ Go through all the files in the given folder and see how many USFM IDs we can find.
                Populates the two dictionaries.
                Returns the number of files found. """
        # Empty the two dictionaries
        self.fileDictionary = {} # The keys are 2-tuples of folder, filename, the values are all valid BBB values
        self.BBBDictionary = {} # The keys are valid BBB values, the values are all 2-tuples of folder, filename
        folderFilenames = os.listdir( givenFolder )
        for possibleFilename in folderFilenames:
            if not possibleFilename.endswith('~') and not possibleFilename.upper().endswith('.BAK'): # Ignore backup files
                filepath = os.path.join( givenFolder, possibleFilename )
                if os.path.isfile( filepath ): # It's a file not a folder
                    USFMId = self.getUSFMIDFromFile( givenFolder, possibleFilename, filepath )
                    if USFMId:
                        assert( filepath not in self.fileDictionary )
                        BBB = self._BibleBooksCodes.getBBBFromUSFM( USFMId )
                        self.fileDictionary[(givenFolder,possibleFilename,)] = BBB
                        if BBB in self.BBBDictionary: logging.error( "getUSFMIDsFromFiles: Oops, already found '{}' in {}, now we have a duplicate in {}".format( BBB, self.BBBDictionary[BBB], possibleFilename ) )
                        self.BBBDictionary[BBB] = (givenFolder,possibleFilename,)
        if len(self.fileDictionary) != len(self.BBBDictionary):
            logging.warning( "getUSFMIDsFromFiles: Oops, something went wrong because dictionaries have {} and {} entries".format( len(self.fileDictionary), len(self.BBBDictionary) ) )
        return len(self.fileDictionary)
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


    def getDerivedFilenameTuples( self ):
        """Return a theoretical list of valid USFM filenames that match our filename template."""
        resultList = []
        if self.pattern:
            for USFMBookCode,USFMDigits,bookReferenceCode in self._USFMBooksCodeNumberTriples:
                filename = '*' * len(self.pattern)
                if self.digitsIndex is not None: filename = filename[:self.digitsIndex] + USFMDigits + filename[self.digitsIndex+len(USFMDigits):]
                filename = filename[:self.USFMBookCodeIndex] + ( USFMBookCode.upper() if 'BBB' in self.pattern else USFMBookCode ) + filename[self.USFMBookCodeIndex+len(USFMBookCode):]
                if self.languageCode: filename = filename[:self.languageIndex] + self.languageCode + filename[self.languageIndex+len(self.languageCode):]
                filename += '.' + self.fileExtension
                for ix in range( 0, len(filename)): # See if there's any constant characters in the pattern that we need to grab
                    if filename[ix]=='*' and self.pattern[ix]!='*':
                        filename = filename[:ix] + self.pattern[ix] + filename[ix+1:]
                resultList.append( (bookReferenceCode,filename,) )
        return resultList
    # end of getDerivedFilenameTuples


    def getConfirmedFilenameTuples( self ):
        """ Starting with the theoretical list of filenames derived from the deduced template (if we have one),
                return a list of tuples of UPPER CASE book codes with actual (present and readable) USFM filenames."""
        resultList = []
        for bookReferenceCode,derivedFilename in self.getDerivedFilenameTuples():
            derivedFilepath = os.path.join( self.folder, derivedFilename )
            if Globals.verbosityLevel > 2: print( '  getConfirmedFilenameTuples: Checking for existence of: ' + derivedFilename )
            if os.access( derivedFilepath, os.R_OK ):
                resultList.append( (bookReferenceCode, derivedFilename,) )
        self.lastTupleList = resultList
        return resultList
    # end of getConfirmedFilenameTuples


    def getPossibleFilenameTuplesExt( self ):
        """Return a list of 2-tuples of BBB, filenames which contain book codes in the filenames (external)."""
        resultList = []
        for possibleFilename in self.fileList:
            for USFMBookCode,USFMDigits,bookReferenceCode in self._USFMBooksCodeNumberTriples:
                if USFMBookCode in possibleFilename or USFMBookCode.upper() in possibleFilename:
                    resultList.append( (self._BibleBooksCodes.getBBBFromUSFM( USFMBookCode ), possibleFilename,) )
        self.lastTupleList = resultList
        return resultList
    # end of getPossibleFilenameTuplesExt


    def getPossibleFilenameTuplesInt( self ):
        """Return a list of 2-tuples of BBB, filenames which contain book codes internally on the \\id line."""
        resultList = []
        if len( self.BBBDictionary) >= len( self.fileDictionary ): # Choose the longest one
            for BBB in self.BBBDictionary.keys():
                resultList.append( (BBB,self.BBBDictionary[BBB][1],) )
        else:
            for folder,filename in self.fileDictionary.keys():
                assert( folder == self.folder )
                resultList.append( self.fileDictionary( (folder,filename,), filename ) )
        self.lastTupleList = resultList
        return resultList
    # end of getPossibleFilenameTuplesInt


    def getMaximumPossibleFilenameTuples( self ):
        """ Find the method that finds the maximum number of USFM Bible files.
                Return a list of 2-tuples with BBB and the filename. """
        resultString, resultList = "Confirmed", self.getConfirmedFilenameTuples()
        resultListExt = self.getPossibleFilenameTuplesExt()
        if len(resultListExt)>len(resultList):
            resultString, resultList = "External", resultListExt
        resultListInt = self.getPossibleFilenameTuplesInt()
        if len(resultListInt)>len(resultList):
            resultString, resultList = "Internal", resultListInt
        if Globals.verbosityLevel > 2: print( "getMaximumPossibleFilenameTuples: using {}".format( resultString ) )
        self.lastTupleList = resultList
        return resultList
    # end of getMaximumPossibleFilenameTuples


    def getSSFFilenames( self, searchAbove=False, auto=True ):
        """Return a list of full pathnames of .ssf files in the folder.
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

        filelist = getSSFFilenamesHelper( self.folder )
        if not filelist and searchAbove: # try the next level up
            filelist = getSSFFilenamesHelper( os.path.join( self.folder, '../' ) )
            if auto and len(filelist)>1: # See if we can help them by automatically choosing the right one
                count, index = 0, -1
                for j, filepath in enumerate(filelist): # Check if we can find a single matching ssf file
                    foundPathBit, foundExtBit = os.path.splitext( filepath )
                    foundPathBit, foundFileBit = os.path.split( foundPathBit )
                    #print( foundPathBit, foundFileBit, foundExtBit, self.folder )
                    if foundFileBit in self.folder: index = j; count += 1 # Take a guess that this might be the right one
                #print( count, index )
                if count==1 and index!=-1: filelist = [ filelist[index] ] # Found exactly one so reduce the list down to this one filepath
        return filelist
    # end of getSSFFilenames


    def getUnusedFilenames( self ):
        """Return a list of filenames which didn't match the USFM template."""
        folderFilenames = os.listdir( self.folder )
        if self.lastTupleList is None: # Not sure what list they're after here
            return None
        for bookReferenceCode,actualFilename in self.lastTupleList:
            folderFilenames.remove( actualFilename )
        return folderFilenames
    # end of getUnusedFilenames
# end of class USFMFiles


def demo():
    """ Demonstrate finding files in some USFM Bible folders. """
    # Handle command line parameters
    from optparse import OptionParser
    parser = OptionParser( version="v{}".format( versionString ) )
    Globals.addStandardOptionsAndProcess( parser )

    if Globals.verbosityLevel > 0: print( "{} V{}".format( progName, versionString ) )

    testFolder = 'Tests/DataFilesForTests/USFMTest/' # This is a RELATIVE path
    #testFolder = '/home/myFolder' # You can put your test folder here
    name, encoding, testFolder = "WEB", "utf-8", "/mnt/Work/Bibles/English translations/WEB (World English Bible)/2012-06-23 eng-web_usfm/" # You can put your test folder here
    name, encoding, testFolder = "KS", "utf-8", "/mnt/Work/Bibles/Formats/USFM/PrivateUSFMTestData/KS/" # You can put your test folder here
    if os.access( testFolder, os.R_OK ):
        UFns = USFMFilenames( testFolder )
        print( UFns )
        result = UFns.getAllFilenames(); print( "\nAll:", len(result), result )
        result = UFns.getDerivedFilenameTuples(); print( "\nDerived:", UFns.getFilenameTemplate(), len(result), result )
        result = UFns.getConfirmedFilenameTuples(); print( "\nConfirmed:", UFns.getFilenameTemplate(), len(result), result )
        result = UFns.getUnusedFilenames(); print( "Other:", len(result), result )
        result = UFns.getPossibleFilenameTuplesExt(); print( "\nPossibleExt:", len(result), result )
        result = UFns.getUnusedFilenames(); print( "Other:", len(result), result )
        result = UFns.getPossibleFilenameTuplesInt(); print( "\nPossibleInt:", len(result), result )
        result = UFns.getUnusedFilenames(); print( "Other:", len(result), result )
        result = UFns.getMaximumPossibleFilenameTuples(); print( "\nMax:", len(result), result )
        result = UFns.getUnusedFilenames(); print( "Other:", len(result), result )
        result = UFns.getSSFFilenames(); print( "\nSSF:", len(result), result )
    else: print( "Sorry, test folder '{}' doesn't exist on this computer.".format( testFolder ) )

if __name__ == '__main__':
    demo()
# end of USFMFilenames.py
