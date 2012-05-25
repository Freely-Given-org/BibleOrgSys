#!/usr/bin/python3
#
# USXFilenames.py
#   Last modified: 2012-05-25 (also update versionString below)
#
# Module handling USX Bible filenames
#
# Copyright (C) 2012 Robert Hunt
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
Module for creating and manipulating USX filenames.
"""

progName = "USX Bible filenames handler"
versionString = "0.01"


import os, logging
from gettext import gettext as _


import Globals
from BibleBooksCodes import BibleBooksCodes


class USXFilenames:
    """
    Class for creating and manipulating USX Filenames.
    """

    def __init__( self, folder ):
        """Create the object by inspecting files in the given folder."""
        # Get the data tables that we need for proper checking
        self.BibleBooksCodes = BibleBooksCodes().loadData()

        self.folder = folder
        self.pattern, self.fileExtension = 'dddBBB', 'usx'
        self.digitsIndex, self.USXBookCodeIndex = 0, 3
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
                if foundLength>=6 and containsDigits and foundExtBit=='.'+self.fileExtension:
                    for USXBookCode,USXDigits,bookReferenceCode in self.BibleBooksCodes.getAllUSXBooksCodeNumberTriples():
                        if USXDigits in foundFileBit and (USXBookCode in foundFileBit or USXBookCode.upper() in foundFileBit):
                            digitsIndex = foundFileBit.index( USXDigits )
                            USXBookCodeIndex = foundFileBit.index(USXBookCode) if USXBookCode in foundFileBit else foundFileBit.index(USXBookCode.upper())
                            USXBookCode = foundFileBit[USXBookCodeIndex:USXBookCodeIndex+3]
                            #print( digitsIndex, USXBookCodeIndex, USXBookCode )
                            if digitsIndex==0 and USXBookCodeIndex==2: # Found a form like 01GENlanguage.xyz
                                self.digitsIndex = digitsIndex
                                self.USXBookCodeIndex = USXBookCodeIndex
                                self.pattern = "ddbbb" + 'n'*(foundLength-5)
                            elif foundLength==6 and digitsIndex==0 and USXBookCodeIndex==3: # Found a form like 001GEN.usx
                                self.digitsIndex = digitsIndex
                                self.USXBookCodeIndex = USXBookCodeIndex
                                self.pattern = "nnnddbbb"
                            else: logging.error( _("Unrecognized USX filename template at ")+foundFileBit ); return
                            if USXBookCode.isupper(): self.pattern = self.pattern.replace( 'bbb', 'BBB' )
                            self.fileExtension = foundExtBit[1:]
                            matched = True
                            break
                if matched: break
        if not matched: logging.info( _("Unable to recognize valid USX files in ") + folder )
        #print( "USXFilenames: pattern='{}' fileExtension='{}'".format( self.pattern, self.fileExtension ) )
    # end of __init__
        

    def __str__( self ):
        """
        This method returns the string representation of an object.
        
        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = "USX Filenames object"
        indent = 2
        if self.folder: result += ('\n' if result else '') + ' '*indent + _("Folder: {}").format( self.folder )
        if self.pattern: result += ('\n' if result else '') + ' '*indent + _("Filename pattern: {}").format( self.pattern )
        if self.fileExtension: result += ('\n' if result else '') + ' '*indent + _("File extension: {}").format( self.fileExtension )
        return result
    # end of __str___


    def getPossibleFilenames( self ):
        """Return a list of valid USX filenames that match our filename template."""
        filelist = []
        if self.pattern:
            for USFMBookCode,USXDigits,bookReferenceCode in self.BibleBooksCodes.getAllUSXBooksCodeNumberTriples():
                filename = "------" # Six characters
                filename = filename[:self.digitsIndex] + USXDigits + filename[self.digitsIndex+len(USXDigits):]
                filename = filename[:self.USXBookCodeIndex] + ( USFMBookCode.upper() if 'BBB' in self.pattern else USFMBookCode ) + filename[self.USXBookCodeIndex+len(USFMBookCode):]
                filename += '.' + self.fileExtension
                #print( "getPossibleFilenames: Filename is '{}'".format( filename ) )
                filelist.append( (bookReferenceCode,filename,) )
        return filelist
    # end of getPossibleFilenames


    def getActualFilenames( self ):
        """Return a list of tuples of UPPER CASE book codes with actual (present and readable) USX filenames."""
        filelist = []
        for bookReferenceCode,possibleFilename in self.getPossibleFilenames():
            possibleFilepath = os.path.join( self.folder, possibleFilename )
            #print( '  Looking for: ' + possibleFilename )
            if os.access( possibleFilepath, os.R_OK ):
                #USXBookCode = possibleFilename[self.USXBookCodeIndex:self.USXBookCodeIndex+3].upper()
                filelist.append( (bookReferenceCode, possibleFilename,) )
        return filelist
    # end of getActualFilenames


    def getUnusedFilenames( self ):
        """Return a list of filenames which didn't match the USFX template."""
        folderFilenames = os.listdir( self.folder )
        actualFilenames = self.getActualFilenames()
        filelist = []
        for bookReferenceCode,actualFilename in actualFilenames:
            folderFilenames.remove( actualFilename )
        return folderFilenames
    # end of getUnusedFilenames


    #def getSSFFilenames( self, searchAbove=False, auto=True ):
    #    """Return a list of full pathnames of .ssf files in the folder.
    #        NOTE: USX projects don't usually have the .ssf files in the project folder,
    #            but 'backed-up' projects often do.
    #        If searchAbove is set to True and no ssf files are found in the given folder,
    #            this routine will attempt to search the next folder up the file hierarchy.
    #            Furthermore, unless auto is set to False,
    #                it will try to find the correct one from multiple SSFs."""
    #    def getSSFFilenamesHelper( folder ):
    #        filelist = []
    #        files = os.listdir( folder )
    #        for foundFilename in files:
    #            if not foundFilename.endswith('~'): # Ignore backup files
    #                foundFileBit, foundExtBit = os.path.splitext( foundFilename )
    #                if foundExtBit.lower()=='.ssf':
    #                    filelist.append( os.path.join( folder, foundFilename ) )
    #        return filelist
    #    # end of getSSFFilenamesHelper

    #    filelist = getSSFFilenamesHelper( self.folder )
    #    if not filelist and searchAbove: # try the next level up
    #        filelist = getSSFFilenamesHelper( os.path.join( self.folder, '../' ) )
    #        if auto and len(filelist)>1: # See if we can help them by automatically choosing the right one
    #            count, index = 0, -1
    #            for j, filepath in enumerate(filelist): # Check if we can find a single matching ssf file
    #                foundPathBit, foundExtBit = os.path.splitext( filepath )
    #                foundPathBit, foundFileBit = os.path.split( foundPathBit )
    #                #print( foundPathBit, foundFileBit, foundExtBit, self.folder )
    #                if foundFileBit in self.folder: index = j; count += 1 # Take a guess that this might be the right one
    #            #print( count, index )
    #            if count==1 and index!=-1: filelist = [ filelist[index] ] # Found exactly one so reduce the list down to this one filepath
    #    return filelist
    ## end of getSSFFilenames
# end of class USXFiles


def demo():
    """ Demonstrate finding files in some USX Bible folders. """
    # Handle command line parameters
    from optparse import OptionParser
    parser = OptionParser( version="v{}".format( versionString ) )
    Globals.addStandardOptionsAndProcess( parser )

    if Globals.verbosityLevel > 0: print( "{} V{}".format( progName, versionString ) )

    testFolder = '/mnt/Work/VirtualBox_Shared_Folder/USX exports/Projects/MBTV/' # You can put your test folder here
    if os.access( testFolder, os.R_OK ):
        UFns = USXFilenames( testFolder )
        print( UFns )
        result = UFns.getPossibleFilenames(); print( "Possible:", len(result), result )
        result = UFns.getActualFilenames(); print( "\nActual:", len(result), result )
        result = UFns.getUnusedFilenames(); print( "\Other:", len(result), result )
    else: print( "Sorry, test folder '{}' doesn't exist on this computer.".format( testFolder ) )

    baseFolder = '/mnt/Work/VirtualBox_Shared_Folder/USX exports'
    for thisGroup in ( 'Versions', 'Projects', 'Notes' ):
        groupFolders = os.listdir( os.path.join( baseFolder, thisGroup ) )
        for thisFolder in groupFolders:
            testFolder = os.path.join( baseFolder, thisGroup, thisFolder )
            if os.access( testFolder, os.R_OK ):
                UFns = USXFilenames( testFolder )
                #result = UFns.getPossibleFilenames(); print( "Possible:", len(result), result )
                #result = UFns.getActualFilenames(); print( "\nActual:", len(result), result )
                result = UFns.getUnusedFilenames();
                if result:
                    print( UFns )
                    print( "Unused:", len(result), result )
            else: print( "Sorry, test folder '{}' doesn't exist on this computer.".format( testFolder ) )

if __name__ == '__main__':
    demo()
# end of USXFilenames.py
