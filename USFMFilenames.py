#!/usr/bin/python3
#
# USFMFilenames.py
#   Last modified: 2012-06-06 (also update versionString below)
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
versionString = "0.53"


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

            Creates a self.pattern (template) for USFM filenames where
                nnn = language code (lower case) or NNN = language code (UPPER CASE)
                bbb = book code (lower case) or BBB = book code (UPPER CASE)
                dd = digits
        """
        # Get the data tables that we need for proper checking
        self._BibleBooksCodes = BibleBooksCodes().loadData()
        self._USFMBooksCodes = self._BibleBooksCodes.getAllUSFMBooksCodes()
        self._USFMBooksCodesUpper = [x.upper() for x in self._USFMBooksCodes]
        self._USFMBooksCodeNumberTriples = self._BibleBooksCodes.getAllUSFMBooksCodeNumberTriples()

        self.folder = folder
        self.pattern, self.fileExtension = '', ''
        files = os.listdir( self.folder )
        if not files: logging.error( _("No files at all in given folder: '{}'").format( self.folder) ); return
        for foundFilename in files:
            if not foundFilename.endswith('~'): # Ignore backup files
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
                                print( "Pattern is '{}'".format( self.pattern ) )
                                if '*' not in self.pattern: matched = True
                                else: # we'll try to be even more generic
                                    self.languageIndex = self.digitsIndex = None
                                    self.languageCode = None
                                    self.USFMBookCodeIndex = USFMBookCodeIndex
                                    self.pattern = '*' * foundLength
                                    self.pattern = self.pattern[:USFMBookCodeIndex] + 'bbb' + self.pattern[USFMBookCodeIndex+3:]
                                    print( "Pattern is '{}'".format( self.pattern ) )
                                    matched = True
                            if matched:
                                if self.languageCode and self.languageCode.isupper(): self.pattern = self.pattern.replace( 'l', 'L' )
                                if USFMBookCode.isupper(): self.pattern = self.pattern.replace( 'bbb', 'BBB' )
                                self.fileExtension = foundExtBit[1:]
                                break
                    if matched: break
            if matched: break
        if not matched: logging.info( _("Unable to recognize valid USFM files in ") + folder )
        #print( "USFMFilenames: pattern='{}' fileExtension='{}'".format( self.pattern, self.fileExtension ) )
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
        return result
    # end of __str___


    def getFilenameTemplate( self ):
        """ Returns a pattern/template for USFM filenames where
                lll = language code (lower case) or LLL = language code (UPPER CASE)
                bbb = book code (lower case) or BBB = book code (UPPER CASE)
                dd = Paratext digits (can actually include some letters) """
        return self.pattern


    def getAllFilenames( self ):
        """Return a list of all filenames in our folder."""
        filelist = os.listdir( self.folder )
        return filelist
    # end of getAllFilenames


    def getDerivedFilenames( self ):
        """Return a list of valid USFM filenames that match our filename template."""
        filelist = []
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
                filelist.append( (bookReferenceCode,filename,) )
        return filelist
    # end of getDerivedFilenames


    def getUSFMIDFromFile( self, filepath ):
        """ Try to get the BBB from the first line in the file (which should be the \\id line). """
        if os.path.isfile( filepath ): # We'll assume it's a USFM file but what is BBB?
            # Look for BBB in the ID line (which should be the first line in a USFM file)
            with open( filepath ) as possibleUSFMFile: # Automatically closes the file when done
                for line in possibleUSFMFile:
                    if line.startswith( '\\id ' ) and line[7]in (' ','\n',):
                        USFMId = line[4:].strip()[:3] # Take the first three non-blank characters after the space after id
                        #print( "Have possible USFM ID '{}'".format( USFMId ) )
                        if USFMId.upper() in self._USFMBooksCodesUpper: return USFMId # it's a valid one
                        else: print( "But '{}' wasn't a valid USFM ID!!!".format( USFMId ) )
                    break # We only look at the first line
        return None
    # end of getUSFMIDFromFile


    def getConfirmedFilenames( self ):
        """Return a list of tuples of UPPER CASE book codes with actual (present and readable) USFM filenames."""
        filelist = []
        for bookReferenceCode,derivedFilename in self.getDerivedFilenames():
            derivedFilepath = os.path.join( self.folder, derivedFilename )
            if Globals.verbosityLevel > 2: print( '  Looking for: ' + derivedFilename )
            if os.access( derivedFilepath, os.R_OK ):
                #USFMBookCode = possibleFilename[self.USFMBookCodeIndex:self.USFMBookCodeIndex+3].upper()
                filelist.append( (bookReferenceCode, derivedFilename,) )
        return filelist
    # end of getConfirmedFilenames


    def getUnusedFilenames( self ):
        """Return a list of filenames which didn't match the USFM template."""
        folderFilenames = os.listdir( self.folder )
        actualFilenames = self.getConfirmedFilenames()
        for bookReferenceCode,actualFilename in actualFilenames:
            folderFilenames.remove( actualFilename )
        return folderFilenames
    # end of getUnusedFilenames


    def getPossibleFilenames1( self ):
        """Return a list of filenames which contain book codes."""
        filelist = []
        folderFilenames = os.listdir( self.folder )
        for possibleFilename in folderFilenames:
            if not possibleFilename.endswith('~') and not possibleFilename.upper().endswith('.BAK'): # Ignore backup files
                for USFMBookCode,USFMDigits,bookReferenceCode in self._USFMBooksCodeNumberTriples:
                    if USFMBookCode in possibleFilename or USFMBookCode.upper() in possibleFilename:
                        filelist.append( possibleFilename )
        return filelist
    # end of getPossibleFilenames1


    def getPossibleFilenames2( self ):
        """Return a list of filenames which contain book codes."""
        filelist = []
        folderFilenames = os.listdir( self.folder )
        for possibleFilename in folderFilenames:
            if not possibleFilename.endswith('~') and not possibleFilename.upper().endswith('.BAK'): # Ignore backup files
                if self.getUSFMIDFromFile( os.path.join( self.folder, possibleFilename ) ):
                    filelist.append( possibleFilename )
        return filelist
    # end of getPossibleFilenames2


    def getSSFFilenames( self, searchAbove=False, auto=True ):
        """Return a list of full pathnames of .ssf files in the folder.
            NOTE: USFM projects don't usually have the .ssf files in the project folder,
                but 'backed-up' projects often do.
            If searchAbove is set to True and no ssf files are found in the given folder,
                this routine will attempt to search the next folder up the file hierarchy.
                Furthermore, unless auto is set to False,
                    it will try to find the correct one from multiple SSFs."""
        def getSSFFilenamesHelper( folder ):
            filelist = []
            files = os.listdir( folder )
            for foundFilename in files:
                if not foundFilename.endswith('~'): # Ignore backup files
                    foundFileBit, foundExtBit = os.path.splitext( foundFilename )
                    if foundExtBit.lower()=='.ssf':
                        filelist.append( os.path.join( folder, foundFilename ) )
            return filelist
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
    name, encoding, testFolder = "WEB", "utf-8", "/mnt/Work/Bibles/English translations/WEB (World English Bible)/eng-web_usfm/" # You can put your test folder here
    if os.access( testFolder, os.R_OK ):
        UFns = USFMFilenames( testFolder )
        print( UFns )
        result = UFns.getAllFilenames(); print( "\nAll:", len(result), result )
        result = UFns.getDerivedFilenames(); print( "\nDerived:", len(result), result )
        result = UFns.getConfirmedFilenames(); print( "\nConfirmed:", len(result), result )
        result = UFns.getUnusedFilenames(); print( "\nOther:", len(result), result )
        result = UFns.getSSFFilenames(); print( "\nSSF:", len(result), result )
        result = UFns.getPossibleFilenames1(); print( "\nPossible1:", len(result), result )
        result = UFns.getPossibleFilenames2(); print( "\nPossible2:", len(result), result )
    else: print( "Sorry, test folder '{}' doesn't exist on this computer.".format( testFolder ) )

if __name__ == '__main__':
    demo()
# end of USFMFilenames.py
