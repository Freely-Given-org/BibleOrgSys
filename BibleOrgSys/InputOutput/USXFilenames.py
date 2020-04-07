#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# USXFilenames.py
#
# Module handling USX Bible filenames
#
# Copyright (C) 2012-2020 Robert Hunt
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
Module for creating and manipulating USX filenames.
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2020-04-06' # by RJH
SHORT_PROGRAM_NAME = "USXBible"
PROGRAM_NAME = "USX Bible filenames handler"
PROGRAM_VERSION = '0.54'
programNameVersion = f'{PROGRAM_NAME} v{PROGRAM_VERSION}'
programNameVersionDate = f'{programNameVersion} {_("last modified")} {LAST_MODIFIED_DATE}'

debuggingThisModule = False


from typing import List, Tuple
import os
import logging

if __name__ == '__main__':
    import sys
    aboveAboveFolderPath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderPath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderPath )
from BibleOrgSys import BibleOrgSysGlobals


# All of the following must be all UPPER CASE
filenamesToIgnore = ('AUTOCORRECT.TXT','HYPHENATEDWORDS.TXT','PRINTDRAFTCHANGES.TXT','README.TXT','BOOK_NAMES.TXT',) # Only needs to include names whose extensions are not listed below
filenameEndingsToIgnore = ('.ZIP.GO', '.ZIP.DATA',) # Must begin with a dot
# NOTE: Extensions ending in ~ are also ignored
extensionsToIgnore = ( 'ASC', 'BAK', 'BAK2', 'BAK3', 'BAK4', 'BBLX', 'BC', 'CCT', 'CSS', 'DOC', 'DTS', 'HTM','HTML',
                    'JAR', 'LDS', 'LOG', 'MYBIBLE', 'NT','NTX', 'ODT', 'ONT','ONTX', 'OSIS', 'OT','OTX', 'PDB',
                    'SAV', 'SAVE', 'STY', 'SSF', 'USFM', 'VRS', 'YET', 'XML', 'ZIP', ) # Must be UPPERCASE and NOT begin with a dot


class USXFilenames:
    """
    Class for creating and manipulating USX Filenames.
    """

    def __init__( self, givenFolderName ) -> None:
        """
        Create the object by inspecting files in the given folder.
        """
        self.givenFolderName = givenFolderName
        self.pattern, self.fileExtension = '', 'usx' # Pattern should end up as 'dddBBB'
        self.fileList = [] # A list of all files in our folder (excluding folder names and backup filenames)
        self.digitsIndex, self.USXBookCodeIndex = 0, 3

        # Get the data tables that we need for proper checking
        #self._USFMBooksCodes = BibleOrgSysGlobals.loadedBibleBooksCodes.getAllUSFMBooksCodes()
        #self._USFMBooksCodesUpper = [x.upper() for x in self._USFMBooksCodes]
        self._USFMBooksCodeNumberTriples = BibleOrgSysGlobals.loadedBibleBooksCodes.getAllUSFMBooksCodeNumberTriples()
        #self._BibleditBooksCodeNumberTriples = BibleOrgSysGlobals.loadedBibleBooksCodes.getAllBibleditBooksCodeNumberTriples()

        # Find how many files are in our folder
        for possibleFilename in os.listdir( self.givenFolderName ):
            #print( "possibleFilename", possibleFilename )
            pFUpper = possibleFilename.upper()
            if pFUpper in filenamesToIgnore: continue
            pFUpperProper, pFUpperExt = os.path.splitext( pFUpper )
            #print( pFUpperProper, pFUpperExt )
            ignore = False
            for ending in filenameEndingsToIgnore:
                if pFUpper.endswith( ending): ignore=True; break
            if ignore: continue
            if pFUpper[-1]!='~' and not pFUpperExt[1:] in extensionsToIgnore: # Compare without the first dot
                filepath = os.path.join( self.givenFolderName, possibleFilename )
                if os.path.isfile( filepath ): # It's a file not a folder
                    self.fileList.append( possibleFilename )
        #print( "fL", self.fileList )
        #if not self.fileList: logging.error( _("No files at all in given folder: {!r}").format( self.givenFolderName) ); return

        matched = False
        for foundFilename in self.fileList:
            #print( foundFilename )
            foundFileBit, foundExtBit = os.path.splitext( foundFilename )
            foundLength = len( foundFileBit )
            containsDigits = False
            for char in foundFilename:
                if char.isdigit():
                    containsDigits = True
                    break
            #matched = False
            #print( repr(foundFileBit), foundLength, containsDigits, repr(foundExtBit) )
            if foundLength>=6 and containsDigits and foundExtBit=='.'+self.fileExtension:
                for USXBookCode,USXDigits,BBB in BibleOrgSysGlobals.loadedBibleBooksCodes.getAllUSXBooksCodeNumberTriples():
                    #print( USXBookCode,USXDigits,BBB )
                    if USXDigits in foundFileBit and (USXBookCode in foundFileBit or USXBookCode.upper() in foundFileBit):
                        digitsIndex = foundFileBit.index( USXDigits )
                        USXBookCodeIndex = foundFileBit.index(USXBookCode) if USXBookCode in foundFileBit else foundFileBit.index(USXBookCode.upper())
                        USXBookCode = foundFileBit[USXBookCodeIndex:USXBookCodeIndex+3]
                        #print( foundLength, digitsIndex, containsDigits, USXBookCodeIndex )
                        if foundLength==6 and digitsIndex==0 and USXBookCodeIndex==3: # Found a form like 001GEN.usx
                            self.digitsIndex = digitsIndex
                            self.hyphenIndex = None
                            self.USXBookCodeIndex = USXBookCodeIndex
                            self.pattern = 'dddbbb'
                        else: logging.error( _("Unrecognized USX filename template at ")+foundFileBit ); return
                        if USXBookCode.isupper(): self.pattern = self.pattern.replace( 'bbb', 'BBB' )
                        self.fileExtension = foundExtBit[1:]
                        matched = True
                        break
                    elif USXDigits[1:] in foundFileBit and '-' in foundFileBit and (USXBookCode in foundFileBit or USXBookCode.upper() in foundFileBit):
                        digitsIndex = foundFileBit.index( USXDigits[1:] ) # Without the leading zero for the 66 books
                        hyphenIndex = foundFileBit.index( '-' )
                        USXBookCodeIndex = foundFileBit.index(USXBookCode) if USXBookCode in foundFileBit else foundFileBit.index(USXBookCode.upper())
                        USXBookCode = foundFileBit[USXBookCodeIndex:USXBookCodeIndex+3]
                        #print( foundLength, digitsIndex, containsDigits, hyphenIndex, USXBookCodeIndex )
                        if foundLength==6 and digitsIndex==0 and hyphenIndex==2 and USXBookCodeIndex==3: # Found a form like 001GEN.usx
                            self.digitsIndex = digitsIndex
                            self.hyphenIndex = hyphenIndex
                            self.USXBookCodeIndex = USXBookCodeIndex
                            self.pattern = 'dd-bbb'
                        else: logging.error( _("Unrecognized USX filename template at ")+foundFileBit ); return
                        if USXBookCode.isupper(): self.pattern = self.pattern.replace( 'bbb', 'BBB' )
                        self.fileExtension = foundExtBit[1:]
                        matched = True
                        break
            if matched: break
        #print( matched )
        if BibleOrgSysGlobals.verbosityLevel>2 and not matched:
            logging.info( _("Unable to recognize valid USX files in ") + str(self.givenFolderName) )
        #print( "USXFilenames: pattern={!r} fileExtension={!r}".format( self.pattern, self.fileExtension ) )
    # end of USXFilenames.__init__


    def __str__( self ) -> str:
        """
        This method returns the string representation of an object.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = "USX Filenames object"
        indent = 2
        if self.givenFolderName: result += ('\n' if result else '') + ' '*indent + _("Folder: {}").format( self.givenFolderName )
        if self.pattern: result += ('\n' if result else '') + ' '*indent + _("Filename pattern: {}").format( self.pattern )
        if self.fileExtension: result += ('\n' if result else '') + ' '*indent + _("File extension: {}").format( self.fileExtension )
        return result
    # end of USXFilenames.__str__


    def getFilenameTemplate( self ) -> str:
        """
        Returns a pattern/template for USX filenames where
                bbb = book code (lower case) or BBB = book code (UPPER CASE)
                ddd = digits
            It should be 'dddBBB' for USX files
        """
        return self.pattern
    # end of USXFilenames.getFilenameTemplate


    def doListAppend( self, BBB:str, filename, givenList, caller ) -> None:
        """
        Check that BBB and filename are not in the givenList,
                then add them as a 2-tuple.
            If there is a duplicate, remove both (as we're obviously unsure).
        """
        # print( f"doListAppend( {BBB}, {filename}, {givenList}, {caller} )" )
        removeBBB = removeFilename = None
        for existingBBB, existingFilename in givenList:
            if existingBBB == BBB:
                logging.warning( "{} tried to add duplicate {} {} when already had {} (removed both)".format( caller, BBB, filename, existingFilename ) )
                removeBBB, removeFilename = existingBBB, existingFilename
            if existingFilename == filename:
                logging.warning( "{} tried to add duplicate {} {} when already had {} (removed both)".format( caller, filename, BBB, existingBBB ) )
                removeBBB, removeFilename = existingBBB, existingFilename
        if removeFilename: givenList.remove( (removeBBB,removeFilename) )
        else: givenList.append( (BBB,filename) )
    # end of USXFilenames.doListAppend


    def getDerivedFilenameTuples( self ):
        """
        Return a list of valid USX filenames that match our filename template.
            The result is a list of 2-tuples in the default rough sequence order from the BibleBooksCodes module.
                Each tuple contains ( BBB, filename ) not including the folder path.
        """
        resultList = []
        if self.pattern:
            for USFMBookCode,USXDigits,BBB in BibleOrgSysGlobals.loadedBibleBooksCodes.getAllUSXBooksCodeNumberTriples():
                filename = "------" # Six characters
                if self.hyphenIndex is None:
                    filename = filename[:self.digitsIndex] + USXDigits + filename[self.digitsIndex+len(USXDigits):]
                else: # have a hyphen so assumeonly two digits
                    if USXDigits.isdigit():
                        USXInt = int( USXDigits )
                        if USXInt > 39:
                            USXDigits = str( USXInt + 1 )
                            USXDigits = '0'*(3-len(USXDigits)) + USXDigits
                            #print( repr(USXDigits) ); halt
                    filename = filename[:self.digitsIndex] + USXDigits[1:] + filename[self.digitsIndex+len(USXDigits)-1:]
                filename = filename[:self.USXBookCodeIndex] + ( USFMBookCode.upper() if 'BBB' in self.pattern else USFMBookCode ) + filename[self.USXBookCodeIndex+len(USFMBookCode):]
                filename += '.' + self.fileExtension
                #print( "getDerivedFilenames: Filename is {!r}".format( filename ) )
                resultList.append( (BBB,filename,) )
        return BibleOrgSysGlobals.loadedBibleBooksCodes.getSequenceList( resultList )
    # end of USXFilenames.getDerivedFilenameTuples


    def getConfirmedFilenameTuples( self, strictCheck:bool=False ):
        """
        Return a list of tuples of UPPER CASE book codes with actual (present and readable) USX filenames.
            If the strictCheck flag is set, the program also looks at the first line(s) inside the files.

            The result is a list of 2-tuples in the default rough sequence order from the BibleBooksCodes module.
                Each tuple contains ( BBB, filename ) not including the folder path.
        """
        resultList = []
        for BBB,possibleFilename in self.getDerivedFilenameTuples():
            possibleFilepath = os.path.join( self.givenFolderName, possibleFilename )
            #print( '  Looking for: ' + possibleFilename )
            if os.access( possibleFilepath, os.R_OK ):
                #print( "possibleFilepath", possibleFilepath )
                #USXBookCode = possibleFilename[self.USXBookCodeIndex:self.USXBookCodeIndex+3].upper()
                if strictCheck or BibleOrgSysGlobals.strictCheckingFlag:
                    firstLines = BibleOrgSysGlobals.peekIntoFile( possibleFilename, self.givenFolderName, numLines=3 )
                    #print( "firstLinesGCFT", firstLines )
                    if not firstLines or len(firstLines)<3: continue
                    if not ( firstLines[0].startswith( '<?xml version="1.0"' ) or firstLines[0].startswith( "<?xml version='1.0'" ) ) \
                    and not ( firstLines[0].startswith( '\ufeff<?xml version="1.0"' ) or firstLines[0].startswith( "\ufeff<?xml version='1.0'" ) ): # same but with BOM
                        if BibleOrgSysGlobals.verbosityLevel > 3: print( "USXB (unexpected) first line was {!r} in {}".format( firstLines, thisFilename ) )
                    if '<usx' not in firstLines[0] and '<usx' not in firstLines[1]:
                        continue # so it doesn't get added
                resultList.append( (BBB, possibleFilename,) )
        return resultList # No need to sort these, coz the above call produce sorted results
    # end of USXFilenames.getConfirmedFilenameTuples


    def getPossibleFilenameTuples( self, strictCheck:bool=False ) -> List[Tuple[str,str]]:
        """
        Return a list of filenames just derived from the list of files in the folder,
                i.e., look only externally at the filenames.
            If the strictCheck flag is set, the program also looks at the first line(s) inside the files.
        """
        #print( "getPossibleFilenameTuples()" )
        # print( "self.fileList", len(self.fileList), self.fileList )

        resultList = []
        for possibleFilename in self.fileList:
            # print( len(resultList), possibleFilename )
            pFUpper = possibleFilename.upper()
            if pFUpper in filenamesToIgnore: continue
            pFUpperProper, pFUpperExt = os.path.splitext( pFUpper )
            for USFMBookCode,USFMDigits,BBB in self._USFMBooksCodeNumberTriples:
                ignore = False
                for ending in filenameEndingsToIgnore:
                    if pFUpper.endswith( ending): ignore=True; break
                if ignore: continue
                checkString = pFUpperProper[3:] if self.pattern == 'dddBBB' else pFUpperProper
                # Otherwise 051COL.usx gets confused between 1Co and Col
                if USFMBookCode.upper() in checkString:
                    if pFUpper[-1]!='~' and not pFUpperExt[1:] in extensionsToIgnore: # Compare without the first dot
                        if strictCheck or BibleOrgSysGlobals.strictCheckingFlag:
                            firstLines = BibleOrgSysGlobals.peekIntoFile( possibleFilename, self.givenFolderName, numLines=3 )
                            if not firstLines or len(firstLines)<3:
                                continue
                            if not ( firstLines[0].startswith( '<?xml version="1.0"' ) or firstLines[0].startswith( "<?xml version='1.0'" ) ) \
                            and not ( firstLines[0].startswith( '\ufeff<?xml version="1.0"' ) or firstLines[0].startswith( "\ufeff<?xml version='1.0'" ) ): # same but with BOM
                                if BibleOrgSysGlobals.verbosityLevel > 3:
                                    print( "USXB (unexpected) first line was {!r} in {}".format( firstLines, thisFilename ) )
                            if '<usx' not in firstLines[0] and '<usx' not in firstLines[1]:
                                continue # so it doesn't get added
                        self.doListAppend( BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromUSFMAbbreviation( USFMBookCode ), possibleFilename, resultList, "getPossibleFilenameTuplesExt" )
        self.lastTupleList = resultList
        # print( "final resultList", len(resultList), resultList )
        return BibleOrgSysGlobals.loadedBibleBooksCodes.getSequenceList( resultList )
    # end of USXFilenames.getPossibleFilenameTuples


    def getUnusedFilenames( self ):
        """
        Return a list of filenames which didn't match the USFX template.
            The order of the filenames in the list has no meaning.
        """
        folderFilenames = os.listdir( self.givenFolderName )
        actualFilenames = self.getConfirmedFilenameTuples()
        filelist = []
        for BBB,actualFilename in actualFilenames:
            folderFilenames.remove( actualFilename )
        return folderFilenames
    # end of USXFilenames.getUnusedFilenames


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

    #    filelist = getSSFFilenamesHelper( self.givenFolderName )
    #    if not filelist and searchAbove: # try the next level up
    #        filelist = getSSFFilenamesHelper( os.path.join( self.givenFolderName, '../' ) )
    #        if auto and len(filelist)>1: # See if we can help them by automatically choosing the right one
    #            count, index = 0, -1
    #            for j, filepath in enumerate(filelist): # Check if we can find a single matching ssf file
    #                foundPathBit, foundExtBit = os.path.splitext( filepath )
    #                foundPathBit, foundFileBit = os.path.split( foundPathBit )
    #                #print( foundPathBit, foundFileBit, foundExtBit, self.givenFolderName )
    #                if foundFileBit in self.givenFolderName: index = j; count += 1 # Take a guess that this might be the right one
    #            #print( count, index )
    #            if count==1 and index!=-1: filelist = [ filelist[index] ] # Found exactly one so reduce the list down to this one filepath
    #    return filelist
    ## end of getSSFFilenames
# end of class USXFiles


def demo() -> None:
    """ 
    Demonstrate finding files in some USX Bible folders. 
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( programNameVersion )

    # These are relative paths -- you can replace these with your test folder(s)
    testFolders = (BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USXTest1/' ), BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USXTest2/' ),
                   BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMTest1/' ), BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMTest2/' ),)
    for testFolder in testFolders:
        print( '\n' )
        if os.access( testFolder, os.R_OK ):
            UFns = USXFilenames( testFolder )
            print( UFns )
            result = UFns.getDerivedFilenameTuples(); print( "\nPossible:", len(result), result )
            result = UFns.getConfirmedFilenameTuples(); print( "\nConfirmed:", len(result), result )
            result = UFns.getUnusedFilenames(); print( "\nOther:", len(result), result )
        else: print( f"Sorry, test folder '{testFolder}' doesn't exist on this computer." )
# end of demo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    demo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of USXFilenames.py
