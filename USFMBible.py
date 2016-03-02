#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# USFMBible.py
#
# Module handling compilations of USFM Bible books
#
# Copyright (C) 2010-2016 Robert Hunt
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
Module for defining and manipulating complete or partial USFM Bibles.
"""

from gettext import gettext as _

LastModifiedDate = '2016-03-01' # by RJH
ShortProgName = "USFMBible"
ProgName = "USFM Bible handler"
ProgVersion = '0.69'
ProgNameVersion = '{} v{}'.format( ShortProgName, ProgVersion )
ProgNameVersionDate = '{} {} {}'.format( ProgNameVersion, _("last modified"), LastModifiedDate )

debuggingThisModule = False


import os, logging
import multiprocessing

import BibleOrgSysGlobals
from USFMFilenames import USFMFilenames
from USFMBibleBook import USFMBibleBook
from Bible import Bible


filenameEndingsToIgnore = ('.ZIP.GO', '.ZIP.DATA',) # Must be UPPERCASE
extensionsToIgnore = ( 'ASC', 'BAK', 'BBLX', 'BC', 'CCT', 'CSS', 'DOC', 'DTS', 'ESFM', 'HTM','HTML', 'JAR',
                    'LDS', 'LOG', 'MYBIBLE', 'NT','NTX', 'ODT', 'ONT','ONTX', 'OSIS', 'OT','OTX', 'PDB',
                    'STY', 'SSF', 'USFX', 'USX', 'VRS', 'YET', 'XML', 'ZIP', ) # Must be UPPERCASE and NOT begin with a dot


def exp( messageString ):
    """
    Expands the message string in debug mode.
    Prepends the module name to a error or warning message string
        if we are in debug mode.
    Returns the new string.
    """
    try: nameBit, errorBit = messageString.split( ': ', 1 )
    except ValueError: nameBit, errorBit = '', messageString
    if BibleOrgSysGlobals.debugFlag or debuggingThisModule:
        nameBit = '{}{}{}: '.format( ShortProgName, '.' if nameBit else '', nameBit )
    return '{}{}'.format( nameBit+': ' if nameBit else '', _(errorBit) )
# end of exp



#def removeUnwantedTupleExtensions( fnTuples ):
    #"""
    #Given a container of (BBB,filename) 2-tuples,
        #results a list without any of the above file extensions.
    #"""
    #resultList = []
    #for BBB,filename in fnTuples:
        #ignoreFlag = False
        #for ignoreExtension in extensionsToIgnore:
            #if filename.upper().endswith( ignoreExtension ): ignoreFlag = True; break
        #if not ignoreFlag: resultList.append( (BBB,filename) )
    #return resultList
## end of removeUnwantedTupleExtensions


def USFMBibleFileCheck( givenFolderName, strictCheck=True, autoLoad=False, autoLoadBooks=False ):
    """
    Given a folder, search for USFM Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number of Bibles found.

    if autoLoad is true and exactly one USFM Bible is found,
        returns the loaded USFMBible object.
    """
    if BibleOrgSysGlobals.verbosityLevel > 2: print( "USFMBibleFileCheck( {}, {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad, autoLoadBooks ) )
    if BibleOrgSysGlobals.debugFlag: assert givenFolderName and isinstance( givenFolderName, str )
    if BibleOrgSysGlobals.debugFlag: assert autoLoad in (True,False,) and autoLoadBooks in (True,False,)

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( exp("USFMBibleFileCheck: Given {!r} folder is unreadable").format( givenFolderName ) )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( exp("USFMBibleFileCheck: Given {!r} path is not a folder").format( givenFolderName ) )
        return False

    # Find all the files and folders in this folder
    if BibleOrgSysGlobals.verbosityLevel > 3: print( " USFMBibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
    foundFolders, foundFiles = [], []
    for something in os.listdir( givenFolderName ):
        somepath = os.path.join( givenFolderName, something )
        if os.path.isdir( somepath ): foundFolders.append( something )
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
                ##print( 'U1', repr(firstLine) )
                #if firstLine is None: continue # seems we couldn't decode the file
                #if firstLine and firstLine[0]==chr(65279): #U+FEFF or \ufeff
                    #logging.info( "USFMBibleFileCheck: Detected Unicode Byte Order Marker (BOM) in {}".format( something ) )
                    #firstLine = firstLine[1:] # Remove the Unicode Byte Order Marker (BOM)
                #if not firstLine: continue # don't allow a blank first line
                #if firstLine[0] != '\\': continue # Must start with a backslash
            #foundFiles.append( something )
    if '__MACOSX' in foundFolders:
        foundFolders.remove( '__MACOSX' )  # don't visit these directories

    # See if there's an USFMBible project here in this given folder
    numFound = 0
    UFns = USFMFilenames( givenFolderName ) # Assuming they have standard Paratext style filenames
    if BibleOrgSysGlobals.verbosityLevel > 2: print( UFns )
    filenameTuples = UFns.getMaximumPossibleFilenameTuples( strictCheck=strictCheck ) # Returns (BBB,filename) 2-tuples
    if BibleOrgSysGlobals.verbosityLevel > 3: print( "  Confirmed:", len(filenameTuples), filenameTuples )
    if BibleOrgSysGlobals.verbosityLevel > 2 and filenameTuples:
        print( "  Found {} USFM file{}.".format( len(filenameTuples), '' if len(filenameTuples)==1 else 's' ) )
    if filenameTuples:
        SSFs = UFns.getSSFFilenames()
        if SSFs:
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "Got SSFs:", SSFs )
            ssfFilepath = os.path.join( givenFolderName, SSFs[0] )
        numFound += 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( exp("USFMBibleFileCheck got {} in {}").format( numFound, givenFolderName ) )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            uB = USFMBible( givenFolderName )
            if autoLoad or autoLoadBooks: uB.preload() # Load the SSF file
            if autoLoadBooks: uB.loadBooks() # Load and process the book files
            return uB
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
            #if BibleOrgSysGlobals.verbosityLevel > 3: print( "    USFMBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
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
                        ##print( 'U2', repr(firstLine) )
                        #if firstLine is None: continue # seems we couldn't decode the file
                        #if firstLine and firstLine[0]==chr(65279): #U+FEFF or \ufeff
                            #logging.info( "USFMBibleFileCheck: Detected Unicode Byte Order Marker (BOM) in {}".format( something ) )
                            #firstLine = firstLine[1:] # Remove the Unicode Byte Order Marker (BOM)
                        #if not firstLine: continue # don't allow a blank first line
                        #if firstLine[0] != '\\': continue # Must start with a backslash
                    #foundSubfiles.append( something )

        # See if there's an USFM Bible here in this folder
        UFns = USFMFilenames( tryFolderName ) # Assuming they have standard Paratext style filenames
        if BibleOrgSysGlobals.verbosityLevel > 2: print( UFns )
        filenameTuples = UFns.getMaximumPossibleFilenameTuples( strictCheck=strictCheck ) # Returns (BBB,filename) 2-tuples
        if BibleOrgSysGlobals.verbosityLevel > 3: print( "  Confirmed:", len(filenameTuples), filenameTuples )
        if BibleOrgSysGlobals.verbosityLevel > 2 and filenameTuples:
            print( "  Found {} USFM files: {}".format( len(filenameTuples), filenameTuples ) )
        elif BibleOrgSysGlobals.verbosityLevel > 1 and filenameTuples and debuggingThisModule:
            print( "  Found {} USFM file{}".format( len(filenameTuples), '' if len(filenameTuples)==1 else 's' ) )
        if filenameTuples:
            SSFs = UFns.getSSFFilenames( searchAbove=True )
            if SSFs:
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "Got SSFs:", SSFs )
                ssfFilepath = os.path.join( thisFolderName, SSFs[0] )
            foundProjects.append( tryFolderName )
            numFound += 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( exp("USFMBibleFileCheck foundProjects {} {}").format( numFound, foundProjects ) )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            uB = USFMBible( foundProjects[0] )
            if autoLoad or autoLoadBooks: uB.preload() # Load the SSF file
            if autoLoadBooks: uB.loadBooks() # Load and process the book files
            return uB
        return numFound
# end of USFMBibleFileCheck



class USFMBible( Bible ):
    """
    Class to load and manipulate USFM Bibles.

    """
    def __init__( self, sourceFolder, givenName=None, givenAbbreviation=None, encoding=None ):
        """
        Create the internal USFM Bible object.

        Note that sourceFolder can be None if we don't know that yet.
        """
         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = 'USFM Bible object'
        self.objectTypeString = 'USFM'

        # Now we can set our object variables
        self.sourceFolder, self.givenName, self.abbreviation, self.encoding = sourceFolder, givenName, givenAbbreviation, encoding

        self.ssfFilepath = None
    # end of USFMBible.__init_


    def preload( self ):
        """
        Loads the SSF file if it can be found.
        Tries to determine USFM filename pattern.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( exp("preload() from {}").format( self.sourceFolder ) )
        assert self.sourceFolder is not None

        # Do a preliminary check on the contents of our folder
        foundFiles, foundFolders = [], []
        for something in os.listdir( self.sourceFolder ):
            #print( repr(something) )
            somepath = os.path.join( self.sourceFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )
            else: logging.error( exp("preload: Not sure what {!r} is in {}!").format( somepath, self.sourceFolder ) )
        if foundFolders:
            unexpectedFolders = []
            for folderName in foundFolders:
                if folderName.startswith( 'Interlinear_'): continue
                if folderName in ('__MACOSX',): continue
                unexpectedFolders.append( folderName )
            if unexpectedFolders:
                logging.info( exp("preload: Surprised to see subfolders in {!r}: {}").format( self.sourceFolder, unexpectedFolders ) )
        if not foundFiles:
            if BibleOrgSysGlobals.verbosityLevel > 0: print( exp("preload: Couldn't find any files in {!r}").format( self.sourceFolder ) )
            raise FileNotFoundError # No use continuing

        self.USFMFilenamesObject = USFMFilenames( self.sourceFolder )
        if BibleOrgSysGlobals.verbosityLevel > 3 or (BibleOrgSysGlobals.debugFlag and debuggingThisModule):
            print( "USFMFilenamesObject", self.USFMFilenamesObject )

        if self.suppliedMetadata is None: self.suppliedMetadata = {}
        if self.ssfFilepath is None: # it might have been loaded first
            # Attempt to load the SSF file
            #self.suppliedMetadata, self.settingsDict = {}, {}
            ssfFilepathList = self.USFMFilenamesObject.getSSFFilenames( searchAbove=True, auto=True )
            #print( "ssfFilepathList", ssfFilepathList )
            if len(ssfFilepathList) > 1:
                logging.error( exp("preload: Found multiple possible SSF files -- using first one: {}").format( ssfFilepathList ) )
            if len(ssfFilepathList) >= 1: # Seems we found the right one
                from PTXBible import loadPTXSSFData
                SSFDict = loadPTXSSFData( self, ssfFilepathList[0] )
                if SSFDict:
                    if self.suppliedMetadata is None: self.suppliedMetadata = {}
                    if 'PTX' not in self.suppliedMetadata: self.suppliedMetadata['PTX'] = {}
                    self.suppliedMetadata['PTX']['SSF'] = SSFDict
                    self.applySuppliedMetadata( 'SSF' ) # Copy some to BibleObject.settingsDict

        #self.name = self.givenName
        #if self.name is None:
            #for field in ('FullName','Name',):
                #if field in self.settingsDict: self.name = self.settingsDict[field]; break
        #if not self.name: self.name = os.path.basename( self.sourceFolder )
        #if not self.name: self.name = os.path.basename( self.sourceFolder[:-1] ) # Remove the final slash
        #if not self.name: self.name = "USFM Bible"

        # Find the filenames of all our books
        self.maximumPossibleFilenameTuples = self.USFMFilenamesObject.getMaximumPossibleFilenameTuples() # Returns (BBB,filename) 2-tuples
        self.possibleFilenameDict = {}
        for BBB, filename in self.maximumPossibleFilenameTuples:
            self.possibleFilenameDict[BBB] = filename

        self.preloadDone = True
    # end of USFMBible.preload


    def loadBook( self, BBB, filename=None ):
        """
        Load the requested book into self.books if it's not already loaded.

        NOTE: You should ensure that preload() has been called first.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2: print( "USFMBible.loadBook( {}, {} )".format( BBB, filename ) )
        if BBB in self.books:
            if BibleOrgSysGlobals.debugFlag: print( "  {} is already loaded -- returning".format( BBB ) )
            return # Already loaded
        if BBB in self.triedLoadingBook:
            logging.warning( "We had already tried loading USFM {} for {}".format( BBB, self.name ) )
            return # We've already attempted to load this book
        self.triedLoadingBook[BBB] = True
        self.bookNeedsReloading[BBB] = False
        if BibleOrgSysGlobals.verbosityLevel > 2 or BibleOrgSysGlobals.debugFlag: print( _("  USFMBible: Loading {} from {} from {}...").format( BBB, self.name, self.sourceFolder ) )
        if filename is None and BBB in self.possibleFilenameDict: filename = self.possibleFilenameDict[BBB]
        if filename is None: raise FileNotFoundError( "USFMBible.loadBook: Unable to find file for {}".format( BBB ) )
        UBB = USFMBibleBook( self, BBB )
        UBB.load( filename, self.sourceFolder, self.encoding )
        if UBB._rawLines:
            UBB.validateMarkers() # Usually activates InternalBibleBook.processLines()
            self.saveBook( UBB )
        else: logging.info( "USFM book {} was completely blank".format( BBB ) )
    # end of USFMBible.loadBook


    def _loadBookMP( self, BBB_Filename_tuple ):
        """
        Multiprocessing version!
        Load the requested book if it's not already loaded (but doesn't save it as that is not safe for multiprocessing)

        Parameter is a 2-tuple containing BBB and the filename.
        """
        if BibleOrgSysGlobals.verbosityLevel > 3: print( exp("loadBookMP( {} )").format( BBB_Filename_tuple ) )
        BBB, filename = BBB_Filename_tuple
        assert BBB not in self.books
        self.triedLoadingBook[BBB] = True
        self.bookNeedsReloading[BBB] = False
        if BibleOrgSysGlobals.verbosityLevel > 2 or BibleOrgSysGlobals.debugFlag:
            print( '  ' + exp("Loading {} from {} from {}...").format( BBB, self.name, self.sourceFolder ) )
        UBB = USFMBibleBook( self, BBB )
        UBB.load( self.possibleFilenameDict[BBB], self.sourceFolder, self.encoding )
        UBB.validateMarkers() # Usually activates InternalBibleBook.processLines()
        if BibleOrgSysGlobals.verbosityLevel > 2 or BibleOrgSysGlobals.debugFlag: print( _("    Finishing loading USFM book {}.").format( BBB ) )
        return UBB
    # end of USFMBible.loadBookMP


    def loadBooks( self ):
        """
        Load all the Bible books.
        """
        if BibleOrgSysGlobals.verbosityLevel > 1: print( exp("Loading {} from {}...").format( self.name, self.sourceFolder ) )

        if not self.preloadDone: self.preload()

        if self.maximumPossibleFilenameTuples:
            if BibleOrgSysGlobals.maxProcesses > 1: # Load all the books as quickly as possible
                #parameters = [BBB for BBB,filename in self.maximumPossibleFilenameTuples] # Can only pass a single parameter to map
                if BibleOrgSysGlobals.verbosityLevel > 1:
                    print( exp("Loading {} USFM books using {} CPUs...").format( len(self.maximumPossibleFilenameTuples), BibleOrgSysGlobals.maxProcesses ) )
                    print( "  NOTE: Outputs (including error and warning messages) from loading various books may be interspersed." )
                with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                    results = pool.map( self._loadBookMP, self.maximumPossibleFilenameTuples ) # have the pool do our loads
                    assert len(results) == len(self.maximumPossibleFilenameTuples)
                    for bBook in results: self.saveBook( bBook ) # Saves them in the correct order
            else: # Just single threaded
                # Load the books one by one -- assuming that they have regular Paratext style filenames
                for BBB,filename in self.maximumPossibleFilenameTuples:
                    #if BibleOrgSysGlobals.verbosityLevel>1 or BibleOrgSysGlobals.debugFlag:
                        #print( _("  USFMBible: Loading {} from {} from {}...").format( BBB, self.name, self.sourceFolder ) )
                    loadedBook = self.loadBook( BBB, filename ) # also saves it
        else:
            logging.critical( exp("No books to load in {}!").format( self.sourceFolder ) )
        #print( self.getBookList() )
        self.doPostLoadProcessing()
    # end of USFMBible.loadBooks

    def load( self ):
        self.loadBooks()
# end of class USFMBible



def demo():
    """
    Demonstrate reading and checking some Bible databases.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( ProgNameVersion )


    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        for j,testFolder in enumerate( ("Tests/DataFilesForTests/USFMTest1/",
                            "Tests/DataFilesForTests/USFMTest2/",
                            "Tests/DataFilesForTests/USFMTest3/",
                            "Tests/DataFilesForTests/USFMAllMarkersProject/",
                            "Tests/DataFilesForTests/USFMErrorProject/",
                            "Tests/DataFilesForTests/PTXTest/",
                            "OutputFiles/BOS_USFM_Export/",
                            "OutputFiles/BOS_USFM_Reexport/",
                            "MadeUpFolder/",
                            ) ):
            print( "\nUSFM A{} testfolder is: {}".format( j+1, testFolder ) )
            result1 = USFMBibleFileCheck( testFolder )
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "USFM TestAa", result1 )
            result2 = USFMBibleFileCheck( testFolder, autoLoad=True )
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "USFM TestAb", result2 )
            result3 = USFMBibleFileCheck( testFolder, autoLoadBooks=True )
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "USFM TestAc", result3 )
            if isinstance( result3, Bible ):
                if BibleOrgSysGlobals.strictCheckingFlag:
                    result3.check()
                    #print( UsfmB.books['GEN']._processedLines[0:40] )
                    UsfmBErrors = UsfmB.getErrors()
                    # print( UBErrors )
                if BibleOrgSysGlobals.commandLineArguments.export:
                    result3.pickle()
                    ##UsfmB.toDrupalBible()
                    result3.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )


    if 1: # Load and process some of our test versions
        for j,(name, encoding, testFolder) in enumerate( (
                                        ("Matigsalug", "utf-8", "Tests/DataFilesForTests/USFMTest1/"),
                                        ("Matigsalug", "utf-8", "Tests/DataFilesForTests/USFMTest2/"),
                                        ("Matigsalug", "utf-8", "Tests/DataFilesForTests/USFMTest3/"),
                                        ("WEB+", "utf-8", "Tests/DataFilesForTests/USFMAllMarkersProject/"),
                                        ("UEP", "utf-8", "Tests/DataFilesForTests/USFMErrorProject/"),
                                        ("Exported", "utf-8", "Tests/BOS_USFM_Export/"),
                                        ) ):
            if os.access( testFolder, os.R_OK ):
                if BibleOrgSysGlobals.verbosityLevel > 0: print( "\nUSFM B{}/".format( j+1 ) )
                UsfmB = USFMBible( testFolder, name, encoding=encoding )
                UsfmB.load()
                if BibleOrgSysGlobals.verbosityLevel > 1:
                    print( "Gen assumed book name:", repr( UsfmB.getAssumedBookName( 'GEN' ) ) )
                    print( "Gen long TOC book name:", repr( UsfmB.getLongTOCName( 'GEN' ) ) )
                    print( "Gen short TOC book name:", repr( UsfmB.getShortTOCName( 'GEN' ) ) )
                    print( "Gen book abbreviation:", repr( UsfmB.getBooknameAbbreviation( 'GEN' ) ) )
                if BibleOrgSysGlobals.verbosityLevel > 0: print( UsfmB )
                if BibleOrgSysGlobals.strictCheckingFlag:
                    UsfmB.check()
                    #print( UsfmB.books['GEN']._processedLines[0:40] )
                    UsfmBErrors = UsfmB.getErrors()
                    # print( UBErrors )
                if BibleOrgSysGlobals.commandLineArguments.export:
                    UsfmB.pickle()
                    ##UsfmB.toDrupalBible()
                    UsfmB.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
                    newObj = BibleOrgSysGlobals.unpickleObject( BibleOrgSysGlobals.makeSafeFilename(name) + '.pickle', os.path.join( "OutputFiles/", "BOS_Bible_Object_Pickle/" ) )
                    if BibleOrgSysGlobals.verbosityLevel > 0: print( "newObj is", newObj )
            elif BibleOrgSysGlobals.verbosityLevel > 0:
                print( "\nSorry, test folder {!r} is not readable on this computer.".format( testFolder ) )


    if 0: # Test a whole folder full of folders of USFM Bibles
        testBaseFolder = "Tests/DataFilesForTests/theWordRoundtripTestFiles/"

        def findInfo( somepath ):
            """ Find out info about the project from the included copyright.htm file """
            cFilepath = os.path.join( somepath, "copyright.htm" )
            if not os.path.exists( cFilepath ): return
            with open( cFilepath ) as myFile: # Automatically closes the file when done
                lastLine, lineCount = None, 0
                title, nameDict = None, {}
                for line in myFile:
                    lineCount += 1
                    if lineCount==1 and line and line[0]==chr(65279): #U+FEFF
                        logging.info( "USFMBible: Detected Unicode Byte Order Marker (BOM) in copyright.htm file" )
                        line = line[1:] # Remove the Unicode Byte Order Marker (BOM)
                    if line[-1]=='\n': line = line[:-1] # Removing trailing newline character
                    if not line: continue # Just discard blank lines
                    lastLine = line
                    if line.startswith("<title>"): title = line.replace("<title>","").replace("</title>","").strip()
                    if line.startswith('<option value="'):
                        adjLine = line.replace('<option value="','').replace('</option>','')
                        USFM_BBB, name = adjLine[:3], adjLine[11:]
                        BBB = BibleOrgSysGlobals.BibleBooksCodes.getBBBFromUSFM( USFM_BBB )
                        #print( USFM_BBB, BBB, name )
                        nameDict[BBB] = name
            return title, nameDict
        # end of findInfo


        count = totalBooks = 0
        if os.access( testBaseFolder, os.R_OK ): # check that we can read the test data
            for something in sorted( os.listdir( testBaseFolder ) ):
                somepath = os.path.join( testBaseFolder, something )
                if os.path.isfile( somepath ): print( "Ignoring file {!r} in {!r}".format( something, testBaseFolder ) )
                elif os.path.isdir( somepath ): # Let's assume that it's a folder containing a USFM (partial) Bible
                    #if not something.startswith( 'ssx' ): continue # This line is used for debugging only specific modules
                    count += 1
                    title = None
                    findInfoResult = findInfo( somepath )
                    if findInfoResult: title, bookNameDict = findInfoResult
                    if title is None: title = something[:-5] if something.endswith("_usfm") else something
                    name, encoding, testFolder = title, "utf-8", somepath
                    if os.access( testFolder, os.R_OK ):
                        if BibleOrgSysGlobals.verbosityLevel > 0: print( "\nUSFM C{}/".format( count ) )
                        UsfmB = USFMBible( testFolder, name, encoding=encoding )
                        UsfmB.load()
                        if BibleOrgSysGlobals.verbosityLevel > 0: print( UsfmB )
                        if BibleOrgSysGlobals.strictCheckingFlag:
                            UsfmB.check()
                            UsfmBErrors = UsfmB.getErrors()
                            #print( UsfmBErrors )
                        if BibleOrgSysGlobals.commandLineArguments.export:
                            UsfmB.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
                    else: print( "\nSorry, test folder {!r} is not readable on this computer.".format( testFolder ) )
            if count: print( "\n{} total USFM (partial) Bibles processed.".format( count ) )
            if totalBooks: print( "{} total books ({} average per folder)".format( totalBooks, round(totalBooks/count) ) )
        elif BibleOrgSysGlobals.verbosityLevel > 0:
            print( "\nSorry, test folder {!r} is not readable on this computer.".format( testBaseFolder ) )
#end of demo

if __name__ == '__main__':
    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( ShortProgName, ProgVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    demo()

    BibleOrgSysGlobals.closedown( ShortProgName, ProgVersion )
# end of USFMBible.py