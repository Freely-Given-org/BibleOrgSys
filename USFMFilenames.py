#!/usr/bin/python3
#
# USFMFilenames.py
#
# Module handling USFM Bible filenames
#   Last modified: 2011-05-30 (also update versionString below)
#
# Copyright (C) 2010-2011 Robert Hunt
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
versionString = "0.51"


import os, logging
from gettext import gettext as _


import Globals
from BibleBooksCodes import BibleBooksCodes


class USFMFilenames:
    """
    Class for creating and manipulating USFM Filenames.
    """

    def __init__( self, folder ):
        """Create the object by inspecting files in the given folder."""
        # Get the data tables that we need for proper checking
        self.BibleBooksCodes = BibleBooksCodes().loadData()

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
                if foundLength>=8 and containsDigits and foundExtBit and foundExtBit[0]=='.':
                    for paratextBookCode,paratextDigits,bookReferenceCode in self.BibleBooksCodes.getAllParatextBooksCodeNumberTriples():
                        if paratextDigits in foundFileBit and (paratextBookCode in foundFileBit or paratextBookCode.upper() in foundFileBit):
                            digitsIndex = foundFileBit.index( paratextDigits )
                            paratextBookCodeIndex = foundFileBit.index(paratextBookCode) if paratextBookCode in foundFileBit else foundFileBit.index(paratextBookCode.upper())
                            paratextBookCode = foundFileBit[paratextBookCodeIndex:paratextBookCodeIndex+3]
                            #print( digitsIndex, paratextBookCodeIndex, paratextBookCode )
                            if digitsIndex==0 and paratextBookCodeIndex==2: # Found a form like 01GENlanguage.xyz
                                self.languageIndex = 5
                                self.languageCode = foundFileBit[self.languageIndex:self.languageIndex+foundLength-5]
                                self.digitsIndex = digitsIndex
                                self.paratextBookCodeIndex = paratextBookCodeIndex
                                self.pattern = "ddbbb" + 'n'*(foundLength-5)
                            elif foundLength==8 and digitsIndex==3 and paratextBookCodeIndex==5: # Found a form like lng01GEN.xyz
                                self.languageIndex = 0
                                self.languageCode = foundFileBit[self.languageIndex:self.languageIndex+foundLength-5]
                                self.digitsIndex = digitsIndex
                                self.paratextBookCodeIndex = paratextBookCodeIndex
                                self.pattern = "nnnddbbb"
                            else: logging.error( _("Unrecognized USFM filename template at ")+foundFileBit ); return
                            if self.languageCode.isupper(): self.pattern = self.pattern.replace( 'n', 'N' )
                            if paratextBookCode.isupper(): self.pattern = self.pattern.replace( 'bbb', 'BBB' )
                            self.fileExtension = foundExtBit[1:]
                            matched = True
                            break
                if matched: break
        if not matched: logging.info( _("Unable to recognize valid USFM files in ") + folder )
        #print( self.pattern, self.fileExtension )
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


    def getPossibleFilenames( self ):
        """Return a list of valid USFM filenames that match our filename template."""
        filelist = []
        if self.pattern:
            for paratextBookCode,paratextDigits,bookReferenceCode in self.BibleBooksCodes.getAllParatextBooksCodeNumberTriples():
                filename = "--------" # Eight characters
                filename = filename[:self.digitsIndex] + paratextDigits + filename[self.digitsIndex+len(paratextDigits):]
                filename = filename[:self.paratextBookCodeIndex] + paratextBookCode.upper() if 'BBB' in self.pattern else paratextBookCode + filename[self.paratextBookCodeIndex+len(paratextBookCode):]
                filename = filename[:self.languageIndex] + self.languageCode + filename[self.languageIndex+len(self.languageCode):]
                filename += '.' + self.fileExtension
                #print( filename )
                filelist.append( (bookReferenceCode,filename,) )
        return filelist
    # end of getPossibleFilenames


    def getActualFilenames( self ):
        """Return a list of tuples of UPPER CASE book codes with actual (present and readable) USFM filenames."""
        filelist = []
        for bookReferenceCode,possibleFilename in self.getPossibleFilenames():
            possibleFilepath = os.path.join( self.folder, possibleFilename )
            #print( '  Looking for: ' + possibleFilename )
            if os.access( possibleFilepath, os.R_OK ):
                #paratextBookCode = possibleFilename[self.paratextBookCodeIndex:self.paratextBookCodeIndex+3].upper()
                filelist.append( (bookReferenceCode, possibleFilename,) )
        return filelist
    # end of getActualFilenames


    def getSSFFilenames( self, searchAbove=False, auto=True ):
        """Return a list of full pathnames of .ssf files in the folder.
            NOTE: Paratext projects don't usually have the .ssf files in the project folder,
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

    testFolder = '/mnt/Data/Matigsalug/Scripture/MBTV/' # You can put your test folder here
    if os.access( testFolder, os.R_OK ):
        UFns = USFMFilenames( testFolder )
        print( UFns )
        result = UFns.getPossibleFilenames(); print( "Possible:", len(result), result )
        result = UFns.getActualFilenames(); print( "Actual:", len(result), result )
    else: print( "Sorry, test folder '{}' doesn't exist on this computer.".format( testFolder ) )

if __name__ == '__main__':
    demo()
# end of USFMFilenames.py
