#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# OSISXMLBible.py
#
# Module handling OSIS XML Bibles
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
Module handling the reading and import of OSIS XML Bibles.

Unfortunately, the OSIS specification (designed by committee for many different tasks)
    allows many different ways of encoding Bibles so the variations are very many.

This is a quickly updated version of an early module,
    and it's both ugly and fragile  :-(

Updated Sept 2013 to also handle Kahunapule's "modified OSIS".

NOTE: We could use multiprocessing in loadBooks()
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2019-02-04' # by RJH
SHORT_PROGRAM_NAME = "OSISBible"
PROGRAM_NAME = "OSIS XML Bible format handler"
PROGRAM_VERSION = '0.65'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'
programNameVersionDate = f'{programNameVersion} {_("last modified")} {LAST_MODIFIED_DATE}'

debuggingThisModule = False


import logging, os, sys
from xml.etree.ElementTree import ElementTree, ParseError

if __name__ == '__main__':
    aboveAboveFolderPath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderPath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderPath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.Reference.ISO_639_3_Languages import ISO_639_3_Languages
from BibleOrgSys.Reference.USFM3Markers import USFM_BIBLE_PARAGRAPH_MARKERS
from BibleOrgSys.Bible import Bible, BibleBook


FILENAME_ENDINGS_TO_IGNORE = ('.ZIP.GO', '.ZIP.DATA') # Must be UPPERCASE
EXTENSIONS_TO_IGNORE = ( 'ASC', 'BAK', 'BAK2', 'BAK3', 'BAK4', 'BBLX', 'BC', 'CCT', 'CSS', 'DOC', 'DTS', 'HTM','HTML',
                    'JAR', 'LDS', 'LOG', 'MYBIBLE', 'NT','NTX', 'ODT', 'ONT','ONTX', 'OSIS', 'OT','OTX', 'PDB',
                    'SAV', 'SAVE', 'STY', 'SSF', 'TXT', 'USFM', 'USX', 'VRS', 'YET', 'ZIP', ) # Must be UPPERCASE and NOT begin with a dot


# Get the data tables that we need for proper checking
ISOLanguages = ISO_639_3_Languages().loadData()



def OSISXMLBibleFileCheck( givenFolderName, strictCheck=True, autoLoad=False, autoLoadBooks=False ):
    """
    Given a folder, search for OSIS XML Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number found.

    if autoLoad is true and exactly one OSIS Bible is found,
        returns the loaded OSISXMLBible object.
    """
    if BibleOrgSysGlobals.verbosityLevel > 2: print( "OSISXMLBibleFileCheck( {}, {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad, autoLoadBooks ) )
    if BibleOrgSysGlobals.debugFlag: assert givenFolderName and isinstance( givenFolderName, str )
    if BibleOrgSysGlobals.debugFlag: assert autoLoad in (True,False)

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( _("OSISXMLBibleFileCheck: Given {!r} folder is unreadable").format( givenFolderName ) )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( _("OSISXMLBibleFileCheck: Given {!r} path is not a folder").format( givenFolderName ) )
        return False

    # Find all the files and folders in this folder
    # OSIS is tricky coz a whole Bible can be in one file (normally), or in lots of separate (book) files
    #   and we don't want to think that 66 book files are 66 different OSIS Bibles
    if BibleOrgSysGlobals.verbosityLevel > 3: print( " OSISXMLBibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
    foundFolders, foundFiles, foundBookFiles = [], [], []
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
            if not somethingUpperExt[1:] in EXTENSIONS_TO_IGNORE: # Compare without the first dot
                foundFiles.append( something )
                for osisBkCode in BibleOrgSysGlobals.loadedBibleBooksCodes.getAllOSISBooksCodes():
                    # osisBkCodes are all UPPERCASE
                    #print( 'obc', osisBkCode, upperFilename )
                    if osisBkCode in somethingUpper:
                        foundBookFiles.append( something ); break
    #print( 'ff', foundFiles, foundBookFiles )

    # See if there's an OSIS project here in this folder
    numFound = 0
    looksHopeful = False
    lastFilenameFound = None
    for thisFilename in sorted( foundFiles ):
        if strictCheck or BibleOrgSysGlobals.strictCheckingFlag:
            firstLines = BibleOrgSysGlobals.peekIntoFile( thisFilename, givenFolderName, numLines=3 )
            if not firstLines or len(firstLines)<2: continue
            if not ( firstLines[0].startswith( '<?xml version="1.0"' ) or firstLines[0].startswith( "<?xml version='1.0'" ) ) \
            and not ( firstLines[0].startswith( '\ufeff<?xml version="1.0"' ) or firstLines[0].startswith( "\ufeff<?xml version='1.0'" ) ): # same but with BOM
                if BibleOrgSysGlobals.verbosityLevel > 3: print( "OsisB (unexpected) first line was {!r} in {}".format( firstLines, thisFilename ) )
                continue
            if not (firstLines[1].startswith( '<osis ' ) or firstLines[2].startswith( '<osis ' )):
                continue
        lastFilenameFound = thisFilename
        numFound += 1
    if numFound>1 and numFound==len(foundBookFiles): # Assume they are all book files
        lastFilenameFound = None
        numFound = 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "OSISXMLBibleFileCheck got", numFound, givenFolderName, lastFilenameFound )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            ub = OSISXMLBible( givenFolderName, lastFilenameFound ) # lastFilenameFound can be None
            if autoLoadBooks: ub.loadBooks() # Load and process the file(s)
            return ub
        return numFound
    elif looksHopeful and BibleOrgSysGlobals.verbosityLevel > 2: print( "    Looked hopeful but no actual files found" )

    # Look one level down
    numFound = 0
    foundProjects = []
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
        if BibleOrgSysGlobals.verbosityLevel > 3: print( "    OSISXMLBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
        foundSubfolders, foundSubfiles, foundSubBookFiles = [], [], []
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
                if not somethingUpperExt[1:] in EXTENSIONS_TO_IGNORE: # Compare without the first dot
                    foundSubfiles.append( something )
                    for osisBkCode in BibleOrgSysGlobals.loadedBibleBooksCodes.getAllOSISBooksCodes():
                        # osisBkCodes are all UPPERCASE
                        #print( 'obc', osisBkCode, upperFilename )
                        if osisBkCode in somethingUpper:
                            foundSubBookFiles.append( something ); break
        #print( 'fsf', foundSubfiles, foundSubBookFiles )

        # See if there's an OSIS project here in this folder
        for thisFilename in sorted( foundSubfiles ):
            if strictCheck or BibleOrgSysGlobals.strictCheckingFlag:
                firstLines = BibleOrgSysGlobals.peekIntoFile( thisFilename, tryFolderName, numLines=2 )
                if not firstLines or len(firstLines)<2: continue
                if not ( firstLines[0].startswith( '<?xml version="1.0"' ) or firstLines[0].startswith( "<?xml version='1.0'" ) ) \
                and not ( firstLines[0].startswith( '\ufeff<?xml version="1.0"' ) or firstLines[0].startswith( "\ufeff<?xml version='1.0'" ) ): # same but with BOM
                    if BibleOrgSysGlobals.verbosityLevel > 3: print( "OsisB (unexpected) first line was {!r} in {}".format( firstLines, thisFilename ) )
                    continue
                if not firstLines[1].startswith( '<osis ' ):
                    continue
            foundProjects.append( (tryFolderName, thisFilename) )
            lastFilenameFound = thisFilename
            numFound += 1
    if numFound>1 and numFound==len(foundSubBookFiles): # Assume they are all book files
        lastFilenameFound = None
        numFound = 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "OSISXMLBibleFileCheck foundProjects", numFound, foundProjects )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            if BibleOrgSysGlobals.debugFlag: assert len(foundProjects) == 1
            ub = OSISXMLBible( foundProjects[0][0], foundProjects[0][1] ) # Folder and filename
            if autoLoadBooks: ub.loadBooks() # Load and process the file(s)
            return ub
        return numFound
# end of OSISXMLBibleFileCheck



def clean( elementText, loadErrors=None, location=None, verseMilestone=None ):
    """
    Given some text from an XML element text or tail field (which might be None)
        return a stripped value and with internal CRLF characters replaced by spaces.

    If the text is None, returns None
    """
    if elementText is None: return None
    # else it's not None

    info = ''
    if location: info += ' at ' + location
    if verseMilestone: info += ' at ' + verseMilestone

    result = elementText
    while result.endswith('\n') or result.endswith('\r'): result = result[:-1] # Drop off trailing newlines (assumed to be irrelevant)
    if '  ' in result:
        errorMsg = _("clean: found multiple spaces in {!r}{}").format( result, info )
        if debuggingThisModule: logging.warning( errorMsg )
        if loadErrors is not None: loadErrors.append( errorMsg )
    if '\t' in result:
        errorMsg = _("clean: found tab in {!r}{}").format( result, info )
        if debuggingThisModule: logging.warning( errorMsg )
        if loadErrors is not None: loadErrors.append( errorMsg )
        result = result.replace( '\t', ' ' )
    if '\n' in result or '\r' in result:
        errorMsg = _("clean: found CR or LF characters in {!r}{}").format( result, info )
        if debuggingThisModule: logging.error( errorMsg )
        if loadErrors is not None: loadErrors.append( errorMsg )
        result = result.replace( '\r\n', ' ' ).replace( '\n', ' ' ).replace( '\r', ' ' )
    while '  ' in result: result = result.replace( '  ', ' ' )
    return result
# end of clean



class OSISXMLBible( Bible ):
    """
    Class for reading, validating, and converting OSISXMLBible XML.
    This is only intended as a transitory class (used at start-up).
    The OSISXMLBible class has functions more generally useful.
    """
    filenameBase = 'OSISXMLBible'
    XMLNameSpace = '{http://www.w3.org/XML/1998/namespace}'
    #OSISNameSpace = '{http://ebible.org/2003/OSIS/namespace}'
    OSISNameSpace = '{http://www.bibletechnologies.net/2003/OSIS/namespace}'
    treeTag = OSISNameSpace + 'osis'
    textTag = OSISNameSpace + 'osisText'
    headerTag = OSISNameSpace + 'header'
    divTag = OSISNameSpace + 'div'


    def __init__( self, sourceFilepath, givenName=None, givenAbbreviation=None, encoding='utf-8' ):
        """
        Constructor: just sets up the OSIS Bible object.

        sourceFilepath can be a folder (esp. if each book is in a separate file)
            or the path of a specific file (probably containing the whole Bible -- most common)
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2 or debuggingThisModule:
            print( "OSISXMLBible.__init__( {}, {!r}, {!r}, {} )".format( sourceFilepath, givenName, givenAbbreviation, encoding ) )

         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = 'OSIS XML Bible object'
        self.objectTypeString = 'OSIS'

        # Now we can set our object variables
        self.sourceFilepath, self.givenName, self.givenAbbreviation, self.encoding  = sourceFilepath, givenName, givenAbbreviation, encoding


        self.title = self.version = self.date = self.source = None
        self.XMLTree = self.header = self.frontMatter = self.divs = self.divTypesString = None
        #self.bkData, self.USFMBooks = {}, {}
        self.lang = self.language = None


        # Do a preliminary check on the readability of our file(s)
        self.possibleFilenames = []
        self.possibleFilenameDict = {}
        if os.path.isdir( self.sourceFilepath ): # We've been given a folder -- see if we can find the files
            self.sourceFolder = self.sourceFilepath
            # There's no standard for OSIS xml file naming
            fileList = os.listdir( self.sourceFilepath )
            # First try looking for OSIS book names
            BBBList = []
            for filename in fileList:
                if 'VerseMap' in filename: continue # For WLC
                if filename.lower().endswith('.xml'):
                    self.sourceFilepath = os.path.join( self.sourceFolder, filename )
                    if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                        print( "Trying {}…".format( self.sourceFilepath ) )
                    if os.access( self.sourceFilepath, os.R_OK ): # we can read that file
                        self.possibleFilenames.append( filename )
                        foundBBB = None
                        upperFilename = filename.upper()
                        for osisBkCode in BibleOrgSysGlobals.loadedBibleBooksCodes.getAllOSISBooksCodes():
                            # osisBkCodes are all UPPERCASE
                            #print( 'obc', osisBkCode, upperFilename )
                            if osisBkCode in upperFilename:
                                #print( "OSISXMLBible.__init__ found {!r} in {!r}".format( osisBkCode, upperFilename ) )
                                if 'JONAH' in upperFilename and osisBkCode=='NAH': continue # Handle bad choice
                                if 'ZEPH' in upperFilename and osisBkCode=='EPH': continue # Handle bad choice
                                assert not foundBBB # Don't expect duplicates
                                foundBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromOSISAbbreviation( osisBkCode, strict=True )
                                #print( "  FoundBBB1 = {!r}".format( foundBBB ) )
                        if not foundBBB: # Could try a USFM/Paratext book code -- what writer creates these???
                            for bkCode in BibleOrgSysGlobals.loadedBibleBooksCodes.getAllUSFMBooksCodes( toUpper=True ):
                                # returned bkCodes are all UPPERCASE
                                #print( 'bc', bkCode, upperFilename )
                                if bkCode in upperFilename:
                                    #print( 'OSISXMLBible.__init__ ' + _("found {!r} in {!r}").format( bkCode, upperFilename ) )
                                    if foundBBB: # already -- don't expect doubles
                                        logging.warning( 'OSISXMLBible.__init__: ' + _("Found a second possible book abbreviation for {} in {}").format( foundBBB, filename ) )
                                    foundBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromUSFMAbbreviation( bkCode, strict=True )
                                    #print( "  FoundBBB2 = {!r}".format( foundBBB ) )
                        if foundBBB:
                            if isinstance( foundBBB, list ): foundBBB = foundBBB[0] # Take the first option
                            assert isinstance( foundBBB, str )
                            BBBList.append( foundBBB )
                            self.availableBBBs.add( foundBBB )
                            self.possibleFilenameDict[foundBBB] = filename
            # Now try to sort the booknames in self.possibleFilenames to a better order
            #print( "Was", len(self.possibleFilenames), self.possibleFilenames )
            #print( "  have", len(BBBList), BBBList )
            assert (len(BBBList)==0 and len(self.possibleFilenames)==1) \
                    or len(BBBList) == len(self.possibleFilenames) # Might be no book files (if all in one file)
            newCorrectlyOrderedList = []
            for BBB in BibleOrgSysGlobals.loadedBibleBooksCodes: # ordered by reference number
                #print( BBB )
                if BBB in BBBList:
                    ix = BBBList.index( BBB )
                    newCorrectlyOrderedList.append( self.possibleFilenames[ix] )
            self.possibleFilenames = newCorrectlyOrderedList
            #print( "Now", self.possibleFilenames ); halt
        else: # it's presumably a file name
            self.sourceFolder = os.path.dirname( self.sourceFilepath )
            if not os.access( self.sourceFilepath, os.R_OK ):
                logging.critical( 'OSISXMLBible: ' + _("File {!r} is unreadable").format( self.sourceFilepath ) )
                return # No use continuing
            if debuggingThisModule: print( "OSISXMLBible possibleFilenames: {}".format( self.possibleFilenames ) )

        self.name, self.abbreviation = self.givenName, self.givenAbbreviation
        self.workNames, self.workPrefixes = [], {}
        if self.suppliedMetadata is None: self.suppliedMetadata = {}
        self.suppliedMetadata['OSIS'] = {}
    # end of OSISXMLBible.__init__


    def loadBooks( self ):
        """
        Loads the OSIS XML file or files.

        NOTE: We could use multiprocessing here
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2 or debuggingThisModule:
            print( "OSISXMLBible.loadBooks()" )

        loadErrors = []
        if self.possibleFilenames: # then we possibly have multiple files, probably one for each book
            for filename in self.possibleFilenames:
                pathname = os.path.join( self.sourceFolder, filename )
                self.__loadFile( pathname, loadErrors )
        elif os.path.isfile( self.sourceFilepath ): # most often we have all the Bible books in one file
            self.__loadFile( self.sourceFilepath, loadErrors )
        else:
            logging.critical( "OSISXMLBible: Didn't find anything to load at {!r}".format( self.sourceFilepath ) )
            loadErrors.append( _("OSISXMLBible: Didn't find anything to load at {!r}").format( self.sourceFilepath ) )
        if loadErrors:
            self.errorDictionary['Load Errors'] = loadErrors
            #if BibleOrgSysGlobals.debugFlag: print( "loadErrors", len(loadErrors), loadErrors ); halt
        self.applySuppliedMetadata( 'OSIS' ) # Copy some to self.settingsDict
        self.doPostLoadProcessing()
    # end of OSISXMLBible.loadBooks

    def load( self ):
        self.loadBooks()


    def loadBook( self, BBB, filename=None ):
        """
        Load the requested book into self.books if it's not already loaded.

        #NOTE: You should ensure that preload() has been called first.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2 or debuggingThisModule:
            print( "OSISXMLBible.loadBook( {}, {} )".format( BBB, filename ) )
            #assert self.preloadDone

        if not self.possibleFilenames: # then the whole Bible was probably in one file
            if debuggingThisModule: print( "  Unable to load OSIS by book -- returning" )
            return # nothing to do here

        if BBB not in self.bookNeedsReloading or not self.bookNeedsReloading[BBB]:
            if BBB in self.books:
                if BibleOrgSysGlobals.debugFlag: print( "  {} is already loaded -- returning".format( BBB ) )
                return # Already loaded
            if BBB in self.triedLoadingBook:
                logging.warning( "We had already tried loading OSIS {} for {}".format( BBB, self.name ) )
                return # We've already attempted to load this book
        self.triedLoadingBook[BBB] = True

        if BibleOrgSysGlobals.verbosityLevel > 2 or BibleOrgSysGlobals.debugFlag:
            print( _("  OSISXMLBible: Loading {} from {} from {}…").format( BBB, self.name, self.sourceFolder ) )
        if filename is None and BBB in self.possibleFilenameDict: filename = self.possibleFilenameDict[BBB]
        if filename is None: raise FileNotFoundError( "OSISXMLBible.loadBook: Unable to find file for {}".format( BBB ) )
        #BB = BibleBook( self, BBB )
        #BB.load( filename, self.sourceFolder, self.encoding )
        #if BB._rawLines:
            #BB.validateMarkers() # Usually activates InternalBibleBook.processLines()
            #self.stashBook( BB )
        #else: logging.info( "OSIS book {} was completely blank".format( BBB ) )
        loadErrors = []
        pathname = os.path.join( self.sourceFolder, filename )
        self.__loadFile( pathname, loadErrors )
        self.bookNeedsReloading[BBB] = False
        if loadErrors:
            if 'Load Errors' not in self.errorDictionary: self.errorDictionary['Load Errors'] = []
            self.errorDictionary['Load Errors'].extend( loadErrors )
            #if BibleOrgSysGlobals.debugFlag: print( "loadErrors", len(loadErrors), loadErrors ); halt
        self.applySuppliedMetadata( 'OSIS' ) # Copy some to self.settingsDict
        #self.doPostLoadProcessing() # Should only be done after loading ALL books
    # end of OSISXMLBible.loadBook


    def __loadFile( self, OSISFilepath, loadErrors ):
        """
        Load a single source XML file and remove the header from the tree.
        Also, extracts some useful elements from the header element.
        """
        if BibleOrgSysGlobals.verbosityLevel > 2 or debuggingThisModule:
            print( _("  OSISXMLBible loading {}…").format( OSISFilepath ) )

        try: self.XMLTree = ElementTree().parse( OSISFilepath )
        except ParseError as err:
            logging.critical( _("Loader parse error in xml file {}: {} {}").format( OSISFilepath, sys.exc_info()[0], err ) )
            loadErrors.append( _("Loader parse error in xml file {}: {} {}").format( OSISFilepath, sys.exc_info()[0], err ) )
            return
        if BibleOrgSysGlobals.debugFlag: assert len( self.XMLTree ) # Fail here if we didn't load anything at all

        # Find the main (osis) container
        if self.XMLTree.tag == OSISXMLBible.treeTag:
            location = 'OSIS file'
            BibleOrgSysGlobals.checkXMLNoText( self.XMLTree, location, '4f6h', loadErrors )
            BibleOrgSysGlobals.checkXMLNoTail( self.XMLTree, location, '1wk8', loadErrors )
            # Process the attributes first
            self.schemaLocation = None
            for attrib,value in self.XMLTree.items():
                if attrib.endswith("schemaLocation"):
                    self.schemaLocation = value
                else:
                    logging.warning( "fv6g Unprocessed {} attribute ({}) in {}".format( attrib, value, location ) )
                    loadErrors.append( "Unprocessed {} attribute ({}) in {} (fv6g)".format( attrib, value, location ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt

            # Find the submain (osisText) container
            if len(self.XMLTree)==1 and (self.XMLTree[0].tag == OSISXMLBible.textTag or (not BibleOrgSysGlobals.strictCheckingFlag and self.XMLTree[0].tag == 'osisText')):
                sublocation = "osisText in " + location
                textElement = self.XMLTree[0]
                BibleOrgSysGlobals.checkXMLNoText( textElement, sublocation, '3b5g', loadErrors )
                BibleOrgSysGlobals.checkXMLNoTail( textElement, sublocation, '7h9k', loadErrors )
                # Process the attributes first
                self.osisIDWork = self.osisRefWork = canonical = None
                for attrib,value in textElement.items():
                    if attrib=='osisIDWork':
                        self.osisIDWork = value
                        if not self.name: self.name = value
                    elif attrib=='osisRefWork': self.osisRefWork = value
                    elif attrib=='canonical':
                        canonical = value
                        assert canonical in ('true','false')
                    elif attrib==OSISXMLBible.XMLNameSpace+'lang': self.lang = value
                    else:
                        logging.warning( "gb2d Unprocessed {} attribute ({}) in {}".format( attrib, value, sublocation ) )
                        loadErrors.append( "Unprocessed {} attribute ({}) in {} (gb2d)".format( attrib, value, sublocation ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                if self.osisRefWork:
                    if self.osisRefWork not in ('bible','Bible','defaultReferenceScheme'):
                        logging.warning( "New variety of osisRefWork: {!r}".format( self.osisRefWork ) )
                        loadErrors.append( "New variety of osisRefWork: {!r}".format( self.osisRefWork ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                if self.lang:
                    if self.lang in ('en','de','he'): # Only specifically recognise these ones so far (English, German, Hebrew)
                        if BibleOrgSysGlobals.verbosityLevel > 2: print( "    Language is {!r}".format( self.lang ) )
                    else:
                        logging.info( "Discovered unknown {!r} language".format( self.lang ) )
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "  osisIDWork is {!r}".format( self.osisIDWork ) )

                # Find (and move) the header container
                if textElement[0].tag == OSISXMLBible.headerTag:
                    self.header = textElement[0]
                    textElement.remove( self.header )
                    self.validateHeader( self.header, loadErrors )
                else:
                    logging.warning( "Missing header element (looking for {!r} tag)".format( OSISXMLBible.headerTag ) )
                    loadErrors.append( "Missing header element (looking for {!r} tag)".format( OSISXMLBible.headerTag ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt

                # Find (and move) the optional front matter (div) container
                if textElement[0].tag == OSISXMLBible.divTag or (not BibleOrgSysGlobals.strictCheckingFlag and textElement[0].tag == 'div'):
                    sub2location = "div of " + sublocation
                    # Process the attributes first
                    div0Type = div0OsisID = canonical = None
                    for attrib,value in textElement[0].items():
                        if attrib=='type': div0Type = value
                        elif attrib=='osisID': div0OsisID = value
                        elif attrib=='canonical':
                            assert canonical is None
                            canonical = value
                            assert canonical in ('true','false')
                        else:
                            logging.warning( "7j4d Unprocessed {} attribute ({}) in {}".format( attrib, value, sub2location ) )
                            loadErrors.append( "Unprocessed {} attribute ({}) in {} (7j4d)".format( attrib, value, sub2location ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    if div0Type == 'front':
                        self.frontMatter = textElement[0]
                        textElement.remove( self.frontMatter )
                        self.validateFrontMatter( self.frontMatter, loadErrors )
                    else: logging.info( "No front matter division" )

                self.divs, self.divTypesString = [], None
                for element in textElement:
                    if element.tag == OSISXMLBible.divTag or (not BibleOrgSysGlobals.strictCheckingFlag and element.tag == 'div'):
                        sub2location = "div in " + sublocation
                        BibleOrgSysGlobals.checkXMLNoText( element, sub2location, '3a2s', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( element, sub2location, '4k8a', loadErrors )
                        divType = element.get( 'type' )
                        if divType is None:
                            logging.error( "Missing div type in OSIS file" )
                            loadErrors.append( "Missing div type in OSIS file" )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                        if divType != self.divTypesString:
                            if not self.divTypesString: self.divTypesString = divType
                            else: self.divTypesString = 'MixedTypes'
                        self.validateAndExtractMainDiv( element, loadErrors )
                        self.divs.append( element )
                    else:
                        logging.error( "Expected to find {!r} but got {!r}".format( OSISXMLBible.divTag, element.tag ) )
                        loadErrors.append( "Expected to find {!r} but got {!r}".format( OSISXMLBible.divTag, element.tag ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
            else:
                logging.error( "Expected to find {!r} but got {!r}".format( OSISXMLBible.textTag, self.XMLTree[0].tag ) )
                loadErrors.append( "Expected to find {!r} but got {!r}".format( OSISXMLBible.textTag, self.XMLTree[0].tag ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
        else:
            logging.error( "Expected to load {!r} but got {!r}".format( OSISXMLBible.treeTag, self.XMLTree.tag ) )
            loadErrors.append( "Expected to load {!r} but got {!r}".format( OSISXMLBible.treeTag, self.XMLTree.tag ) )
            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
        if self.XMLTree.tail is not None and self.XMLTree.tail.strip():
            logging.error( "Unexpected {!r} tail data after {} element".format( self.XMLTree.tail, self.XMLTree.tag ) )
            loadErrors.append( "Unexpected {!r} tail data after {} element".format( self.XMLTree.tail, self.XMLTree.tag ) )
            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
    # end of OSISXMLBible.loadFile


    def validateDivineName( self, element, locationDescription, verseMilestone, loadErrors ):
        """
        """
        location = "validateDivineName: " + locationDescription
        BibleOrgSysGlobals.checkXMLNoAttributes( element, location+" at "+verseMilestone, '3f7h', loadErrors )
        self.thisBook.appendToLastLine( f'\\nd {clean(element.text)}' )
        for subelement in element:
            if subelement.tag == OSISXMLBible.OSISNameSpace+'w':
                sublocation = "w of " + location
                self.validateAndLoadWord( subelement, sublocation, verseMilestone, loadErrors )
            else:
                logging.error( "v4g7 Unprocessed {!r} subelement ({}) in {} at {}".format( subelement.tag, subelement.text, location, verseMilestone ) )
                loadErrors.append( "Unprocessed {!r} subelement ({}) in {} at {} (v4g7)".format( subelement.tag, subelement.text, location, verseMilestone ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
        self.thisBook.appendToLastLine( '\\nd*' )
        if element.tail and element.tail.strip(): self.thisBook.appendToLastLine( clean(element.tail) )
    # end of validateDivineName


    def validateAndLoadSEG( self, element, locationDescription, verseMilestone, loadErrors ):
        """
        Also handles the tail.

        Might be nested like:
            <hi type="bold"><hi type="italic">buk</hi></hi> tainoraun ämän
        Nesting doesn't currently work here.
        """
        #print( "validateAndLoadSEG( {}, {}, {} )".format( BibleOrgSysGlobals.elementStr(element), locationDescription, verseMilestone ) )
        location = 'validateAndLoadSEG: ' + locationDescription
        SegText = element.text

        # Process the attributes
        theType = None
        for attrib,value in element.items():
            if attrib=='type': theType = value
            else:
                logging.warning( "lj06 Unprocessed {!r} attribute ({}) in {} -element of {} at {}".format( attrib, value, element.tag, location, verseMilestone ) )
                loadErrors.append( "Unprocessed {!r} attribute ({}) in {} -element of {} at {} (lj06)".format( attrib, value, element.tag, location, verseMilestone ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt

        #if debuggingThisModule: print( "khf8", "Have", location, repr(element.text), repr(theType) )
        markerOpen = False
        if theType:
            if theType=='verseNumber': marker = 'fv'
            elif theType=='keyword': marker = 'fk'
            elif theType=='otPassage': marker = 'qt'
            elif theType in ('section',
                             'x-small','x-large','x-suspended',
                             'x-maqqef','x-sof-pasuq','x-pe','x-paseq','x-samekh','x-reversednun'):
                marker = theType # invented -- used below
            else:
                marker = 'x--' # Gets ignored below
                if BibleOrgSysGlobals.debugFlag: print(  theType, location, verseMilestone ); halt
        else: # What marker do we need ???
            marker = 'fv'
        if marker == 'section': # We don't have marker for this
            self.thisBook.appendToLastLine( ' ' + clean(SegText) + ' ' )
        elif marker.startswith( 'x-' ): # We don't have marker for this
            self.thisBook.appendToLastLine( clean(SegText) )
        else:
            self.thisBook.appendToLastLine( '\\{} {}'.format( marker, clean(SegText) ) )
            markerOpen = True
        for subelement in element:
            sublocation = element.tag + ' in ' + location
            if subelement.tag == OSISXMLBible.OSISNameSpace+'divineName':
                self.validateDivineName( subelement, sublocation, verseMilestone, loadErrors )
            else:
                logging.error( "8k1w Unprocessed {!r} sub-element ({}) in {} at {}".format( subelement.tag, subelement.text, sublocation, verseMilestone ) )
                loadErrors.append( "Unprocessed {!r} sub-element ({}) in {} at {} (8k3s)".format( subelement.tag, subelement.text, sublocation, verseMilestone ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
        if markerOpen: self.thisBook.appendToLastLine( '\\{}*'.format( marker ) )
        segTail = clean( element.tail, loadErrors, location, verseMilestone )
        if segTail: self.thisBook.appendToLastLine( segTail )
    # end of validateAndLoadSEG


    def validateAndLoadWord( self, element, location, verseMilestone, loadErrors ):
        """
        Handle a 'w' element and submit a string (which may include embedded Strongs' numbers, etc.).

        Nothing is returned.
        """
        #print(self.sourceFilepath)
        #print( "validateAndLoadWord( {}, {}, {}, … )".format( element, location, verseMilestone ) )

        sublocation = "validateAndLoadWord: w of " + location
        word = clean( element.text, loadErrors, sublocation, verseMilestone )
        #print( ' w', word )
        #if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag or debuggingThisModule:
            #assert word -- might be false, e.g., in <w lemma="strong:H03069"><divineName>God</divineName></w>
        self.thisBook.appendToLastLine( '\\w ' + (word if word else '' ) )

        # Process the sub-elements (formatted parts of the word) first
        #assert len(element) <= 1
        if len(element) > 1:
            logging.warning( "Unusual for word '{}' to have multiple ({}) sub-elements in {} at {} (bd52)".format( word, len(element), sublocation, verseMilestone ) )
        for subelement in element:
            #print('  st', subelement.tag )
            if subelement.tag == OSISXMLBible.OSISNameSpace+'divineName':
                self.validateDivineName( subelement, sublocation, verseMilestone, loadErrors )
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'seg':
                self.validateAndLoadSEG( subelement, sublocation, verseMilestone, loadErrors )
            else:
                logging.error( "8k3s Unprocessed {!r} sub-element ({}) in {} at {}".format( subelement.tag, subelement.text, sublocation, verseMilestone ) )
                loadErrors.append( "Unprocessed {!r} sub-element ({}) in {} at {} (8k3s)".format( subelement.tag, subelement.text, sublocation, verseMilestone ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt

        # Process the attributes
        lemma = morph = wType = src = gloss = n = None
        for attrib,value in element.items():
            #print( "{} {}={} @ {}".format( word, attrib, value, location ) )
            if attrib=='lemma':
                lemma = self.workPrefixes['w/@lemma']+':'+value if 'w/@lemma' in self.workPrefixes else value
            elif attrib=='morph':
                morph = self.workPrefixes['w/@morph']+':'+value if 'w/@morph' in self.workPrefixes else value
            elif attrib=='type': wType = value
            elif attrib=='src': src = value
            elif attrib=='gloss': gloss = value
            elif attrib=='n': n = value # Might be something like 1.1.1 (in morphhb/wlc)
            else:
                logging.warning( "2h6k Unprocessed {!r} attribute ({}) in {} at {}".format( attrib, value, sublocation, verseMilestone ) )
                loadErrors.append( "Unprocessed {!r} attribute ({}) in {} at {} (2h6k)".format( attrib, value, sublocation, verseMilestone ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
        if wType and (BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag or debuggingThisModule):
            assert wType.startswith( 'x-split-' ) # Followed by a number 1-10 or more

        attributeDict = {}
        if lemma \
        and ( lemma.startswith('strong:') or lemma.startswith('Strong:') ):
            if len(lemma)>7:
                lemma = lemma[7:]
                if lemma:
                    #self.thisBook.appendToLastLine( '\\str {}\\str*'.format( lemma ) )
                    attributeDict['strong'] = lemma
                    lemma = None # we've used it
        elif gloss and gloss.startswith('s:'):
            if len(gloss)>2:
                gloss = gloss[2:]
                if gloss:
                    self.thisBook.appendToLastLine( '\\str {}\\str*'.format( gloss ) )
                    attributeDict['strong'] = gloss
                    gloss = None # we've used it
        if lemma: attributeDict['lemma'] = lemma
        if morph: attributeDict['x-morph'] = morph
        if wType: attributeDict['x-wType'] = wType
        if src: attributeDict['x-src'] = src
        if gloss: attributeDict['x-gloss'] = gloss
        if n: attributeDict['x-cantillationLevel'] = n
        #if lemma or morph or wType or src or gloss:
            #logging.warning( "Losing lemma or morph or wType or src or gloss here at {} from {}".format( verseMilestone, BibleOrgSysGlobals.elementStr(element) ) )
            #loadErrors.append( "Losing lemma or morph or wType or src or gloss here at {}".format( verseMilestone ) )
            #if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
        if attributeDict:
            attributeString = '|'
            for attributeName,attributeValue in attributeDict.items():
                if len(attributeString) > 1: attributeString += ' '
                attributeString += '{}="{}"'.format( attributeName, attributeValue )
            #print( "attributeString", attributeString )
            self.thisBook.appendToLastLine( attributeString )
        self.thisBook.appendToLastLine( '\\w*')

        trailingPunctuation = clean( element.tail, loadErrors, sublocation, verseMilestone )
        if trailingPunctuation: self.thisBook.appendToLastLine( trailingPunctuation )
        #combinedWord = word + trailingPunctuation
        #return combinedWord
    # end of validateAndLoadWord


    def validateHighlight( self, element, locationDescription, verseMilestone, loadErrors ):
        """
        Also handles the tail.

        Might be nested like:
            <hi type="bold"><hi type="italic">buk</hi></hi> tainoraun ämän
        Nesting doesn't currently work here.
        """
        location = "validateHighlight: " + locationDescription
        #BibleOrgSysGlobals.checkXMLNoSubelements( element, location+" at "+verseMilestone, 'gb5g', loadErrors )
        highlightedText, highlightedTail = element.text, element.tail
        #if not highlightedText: print( "validateHighlight", repr(highlightedText), repr(highlightedTail), repr(location), repr(verseMilestone) )
        #if BibleOrgSysGlobals.debugFlag: assert highlightedText # No text if nested!
        highlightType = None
        for attrib,value in element.items():
            if attrib=='type':
                highlightType = value
            else:
                logging.warning( "7kj3 Unprocessed {!r} attribute ({}) in {} element of {} at {}".format( attrib, value, element.tag, location, verseMilestone ) )
                loadErrors.append( "Unprocessed {!r} attribute ({}) in {} element of {} at {} (7kj3)".format( attrib, value, element.tag, location, verseMilestone ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
        if highlightType == 'italic': marker = 'it'
        elif highlightType == 'bold': marker = 'bd'
        elif highlightType == 'emphasis': marker = 'em'
        elif highlightType == 'small-caps': marker = 'sc'
        elif highlightType == 'super': marker = 'ord'
        elif highlightType == 'normal': marker = 'no'
        elif BibleOrgSysGlobals.debugFlag:
            print( 'validateHighlight: highlightX', highlightType, locationDescription, verseMilestone )
            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag or debuggingThisModule: halt
        self.thisBook.appendToLastLine( '\\{} {}\\{}*'.format( marker, clean(highlightedText), marker ) )
        for subelement in element:
            if subelement.tag == OSISXMLBible.OSISNameSpace+'hi':
                sublocation = "hi of " + locationDescription
                self.validateHighlight( subelement, sublocation, verseMilestone, loadErrors ) # recursive call
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'note':
                sublocation = "note of " + locationDescription
                self.validateCrossReferenceOrFootnote( subelement, sublocation, verseMilestone, loadErrors )
            else:
                logging.error( "bdhj Unprocessed {!r} sub-element ({}) in {} at {}".format( subelement.tag, subelement.text, location, verseMilestone ) )
                loadErrors.append( "Unprocessed {!r} sub-element ({}) in {} at {} (bdhj)".format( subelement.tag, subelement.text, location, verseMilestone ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
        if highlightedTail and highlightedTail.strip(): self.thisBook.appendToLastLine( clean(highlightedTail) )
    # end of validateHighlight


    def validateRDG( self, element, locationDescription, verseMilestone, loadErrors ):
        """
        Also handles the tail.

        Might be nested like:
            <hi type="bold"><hi type="italic">buk</hi></hi> tainoraun ämän

        Doesn't currently add any pseudo-USFM markers for the reading XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        Nesting doesn't currently work here.
        """
        location = 'validateRDG: ' + locationDescription
        BibleOrgSysGlobals.checkXMLNoTail( element, location+" at "+verseMilestone, 'c54b', loadErrors )

        # Process the attributes first
        readingType = None
        for attrib,value in element.items():
            if attrib=='type':
                readingType = value
                #print( 'readingType', readingType )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag:
                    assert readingType in ('x-qere','x-accent')
            else:
                logging.warning( "2s3d Unprocessed {!r} attribute ({}) in {} sub2-element of {} at {}".format( attrib, value, element.tag, location, verseMilestone ) )
                loadErrors.append( "Unprocessed {!r} attribute ({}) in {} sub2-element of {} at {} (2s3d)".format( attrib, value, element.tag, location, verseMilestone ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt

        if element.text: self.thisBook.appendToLastLine( element.text )
        for subelement in element:
            if subelement.tag == OSISXMLBible.OSISNameSpace+'w': # cross-references ???
                sublocation = "validateRDG: w of rdg of " + locationDescription
                self.validateAndLoadWord( subelement, sublocation, verseMilestone, loadErrors )
                ##print( "  Have", sublocation, "6n83" )
                #rdgW = subelement.text
                #BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, 's2vb', loadErrors )
                #BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation+" at "+verseMilestone, '5b3f', loadErrors )
                ## Process the attributes
                #lemma = morph = n = None
                #for attrib,value in subelement.items():
                    ##print( "Attribute RDG1 {}={!r}".format( attrib, value ) )
                    #if attrib=='lemma': lemma = value # e.g., 'l/5649'
                    #elif attrib=='morph': morph = value # e.g., 'HC/Ncfdc'
                    #elif attrib=='n': n = value # e.g., '0.0'
                    #else:
                        #logging.warning( "6b8m Unprocessed {!r} attribute ({}) in {} sub2-element of {} at {}".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                        #loadErrors.append( "Unprocessed {!r} attribute ({}) in {} sub2-element of {} at {} (6b8m)".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                        #if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                #self.thisBook.appendToLastLine( rdgW )
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'seg': # cross-references ???
                sublocation = "validateRDG: seg of rdg of " + locationDescription
                self.validateAndLoadSEG( subelement, sublocation, verseMilestone, loadErrors )
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'hi':
                sublocation = "validateRDG: hi of rdg of " + locationDescription
                self.validateHighlight( subelement, sublocation, verseMilestone, loadErrors )
            else:
                logging.error( "3dxm Unprocessed {!r} subelement ({}) in {} at {}".format( subelement.tag, subelement.text, location, verseMilestone ) )
                loadErrors.append( "Unprocessed {!r} subelement ({}) in {} at {} (3dxm)".format( subelement.tag, subelement.text, location, verseMilestone ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
        if element.tail and element.tail.strip(): self.thisBook.appendToLastLine( clean(element.tail) )
    # end of validateRDG


    def validateProperName( self, element, locationDescription, verseMilestone, loadErrors ):
        """
        """
        location = "validateProperName: " + locationDescription
        BibleOrgSysGlobals.checkXMLNoAttributes( element, location+" at "+verseMilestone, 'hsd8', loadErrors )
        BibleOrgSysGlobals.checkXMLNoSubelements( element, location+" at "+verseMilestone, 'ks91', loadErrors )
        divineName = element.text
        self.thisBook.appendToLastLine( '\\pn {}\\pn*'.format( clean(divineName) ) )
        if element.tail and element.tail.strip(): self.thisBook.appendToLastLine( clean(element.tail) )
    # end of validateProperName


    def validateCrossReferenceOrFootnote( self, element, locationDescription, verseMilestone, loadErrors ):
        """
        Check/validate and process a cross-reference or footnote.
        """
        #print( "validateCrossReferenceOrFootnote at", locationDescription, verseMilestone )
        #print( "element tag={!r} text={!r} tail={!r} attr={} ch={}".format( element.tag, element.text, element.tail, element.items(), element ) )
        location = "validateCrossReferenceOrFootnote: " + locationDescription

        noteType = noteN = noteOsisRef = noteOsisID = notePlacement = noteResp = None
        for attrib,value in element.items():
            if attrib=='type': noteType = value # cross-reference or empty for a footnote
            elif attrib=='n': noteN = value
            elif attrib=='osisRef': noteOsisRef = value
            elif attrib=='osisID': noteOsisID = value
            elif attrib=='placement': notePlacement = value
            elif attrib=='resp': noteResp = value
            else:
                logging.warning( "2s4d Unprocessed {!r} attribute ({}) in {} sub-element of {} at {}".format( attrib, value, element.tag, location, verseMilestone ) )
                loadErrors.append( "Unprocessed {!r} attribute ({}) in {} sub-element of {} at {} (2s4d)".format( attrib, value, element.tag, location, verseMilestone ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
        #print( notePlacement )
        if notePlacement and BibleOrgSysGlobals.debugFlag: assert notePlacement in ('foot','inline')
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "  Note attributes: noteType={!r} noteN={!r} noteOsisRef={!r} noteOsisID={!r} at {}".format( noteType, noteN, noteOsisRef, noteOsisID, verseMilestone ) )

        guessed = False
        openFieldname = None
        if not noteType: # easier to handle later if we decide what it is now
            if not element.items(): # it's just a note with NO ATTRIBUTES at all
                noteType = 'footnote'
            else: # we have some attributes
                noteType = 'footnote' if noteN else 'crossReference'
            guessed = True
        #assert noteType and noteN
        if noteType == 'crossReference':
            #print( "  noteType =", noteType, "noteN =", noteN, "notePlacement =", notePlacement )
            if BibleOrgSysGlobals.debugFlag:
                if notePlacement: assert notePlacement == 'inline'
            if not noteN: noteN = '-'
            self.thisBook.appendToLastLine( '\\x {}'.format( noteN ) )
            openFieldname = 'x'
        elif noteType == 'footnote':
            #print( "  noteType =", noteType, "noteN =", noteN )
            if BibleOrgSysGlobals.debugFlag: assert not notePlacement
            if not noteN: noteN = '+'
            self.thisBook.appendToLastLine( '\\f {} '.format( noteN ) )
            openFieldname = 'f'
        elif noteType == 'study':
            #print( "  noteType =", noteType, "noteN =", noteN )
            if BibleOrgSysGlobals.debugFlag: assert not notePlacement
            if not noteN: noteN = '+'
            self.thisBook.appendToLastLine( '\\f {} '.format( noteN ) )
            openFieldname = 'f'
            #print( "study note1", location, "Type =", noteType, "N =", noteN, "Ref =", noteOsisRef, "ID =", noteOsisID, "p =", notePlacement ); halt
        elif noteType == 'translation':
            #print( "  noteType =", noteType, "noteN =", noteN, "notePlacement =", notePlacement )
            if BibleOrgSysGlobals.debugFlag:
                if notePlacement: assert notePlacement == 'foot'
            if not noteN: noteN = '+'
            self.thisBook.appendToLastLine( '\\f {} '.format( noteN ) )
            openFieldname = 'f'
            #print( "study note1", location, "Type =", noteType, "N =", noteN, "Ref =", noteOsisRef, "ID =", noteOsisID, "p =", notePlacement ); halt
        elif noteType == 'variant':
            #print( "  noteType =", noteType, "noteN =", noteN )
            if BibleOrgSysGlobals.debugFlag: assert not notePlacement
            # What do we do here ???? XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
            if not noteN: noteN = '+'
            self.thisBook.appendToLastLine( '\\f {} '.format( noteN ) )
            openFieldname = 'f'
        elif noteType == 'alternative':
            #print( "  noteType =", noteType, "noteN =", noteN )
            if BibleOrgSysGlobals.debugFlag: assert not notePlacement
            # What do we do here ???? XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
            if not noteN: noteN = '+'
            self.thisBook.appendToLastLine( '\\f {} '.format( noteN ) )
            openFieldname = 'f'
        elif noteType == 'exegesis':
            #print( "  noteType =", noteType, "noteN =", noteN )
            if BibleOrgSysGlobals.debugFlag: assert not notePlacement
            # What do we do here ???? XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
            if not noteN: noteN = '+'
            self.thisBook.appendToLastLine( '\\f {} '.format( noteN ) )
            openFieldname = 'f'
        elif noteType == 'x-index':
            #print( "  noteType =", noteType, "noteN =", noteN )
            if BibleOrgSysGlobals.debugFlag: assert notePlacement in ('inline',)
            if not noteN: noteN = '~'
            self.thisBook.appendToLastLine( '\\f {} '.format( noteN ) ) # Not sure what this is ???
            openFieldname = 'f'
        elif noteType == 'x-strongsMarkup':
            #print( "  noteType =", noteType, "noteN =", noteN, repr(notePlacement) )
            if BibleOrgSysGlobals.debugFlag: assert notePlacement is None
            if not noteN: noteN = '+ '
            self.thisBook.appendToLastLine( '\\str {} '.format( noteN ) )
            openFieldname = 'str'
        else:
            if debuggingThisModule: print( "validateCrossReferenceOrFootnote note1", repr(noteType) )
            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
        noteText = clean( element.text, loadErrors, location, verseMilestone )
        #if not noteText or noteText.isspace(): # Maybe we can infer the anchor reference
        #    if verseMilestone and verseMilestone.count('.')==2: # Something like Gen.1.3
        #        noteText = verseMilestone.split('.',1)[1] # Just get the verse reference like "1.3"
        #    else: noteText = ''
        if noteText and not noteText.isspace(): # In some OSIS files, this is the anchor reference (in others, that's put in the tail of an enclosed reference subelement)
            #print( "vm", verseMilestone, repr(noteText) ); halt
            #if verseMilestone.startswith( 'Matt.6'): halt
            #print( "  noteType = {}, noteText = {!r}".format( noteType, noteText ) )
            if noteType == 'crossReference': # This could be something like '1:6:' or '1:8: a'
                self.thisBook.appendToLastLine( '\\xt {}'.format( clean(noteText) ) )
            elif noteType == 'footnote': # This could be something like '4:3 In Greek: some note.' or it could just be random text
                #print( "  noteType =", noteType, "noteText =", noteText )
                if BibleOrgSysGlobals.debugFlag: assert noteText
                if ':' in noteText and noteText[0].isdigit(): # Let's roughly assume that it starts with a chapter:verse reference
                    bits = noteText.split( None, 1 )
                    if BibleOrgSysGlobals.debugFlag: assert len(bits) == 2
                    sourceText, footnoteText = bits
                    if BibleOrgSysGlobals.debugFlag: assert sourceText and footnoteText
                    #print( "  footnoteSource = {!r}, sourceText = {!r}".format( footnoteSource, sourceText ) )
                    if not sourceText[-1] == ' ': sourceText += ' '
                    self.thisBook.appendToLastLine( '\\fr {}'.format( sourceText ) )
                    self.thisBook.appendToLastLine( '\\ft {}'.format( footnoteText )  )
                else: # Let's assume it's a simple note
                    self.thisBook.appendToLastLine( '\\ft {}'.format( noteText ) )
            elif noteType == 'exegesis':
                #print( "Need to handle exegesis note properly here" ) # … xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
                self.thisBook.appendToLastLine( '\\ft {}'.format( clean(noteText) ) )
                #print( "exegesis note fl35", location, "Type =", noteType, "N =", repr(noteN), "Ref =", noteOsisRef, "ID =", noteOsisID, "p =", notePlacement )
            elif noteType == 'study':
                #print( "Need to handle study note properly here" ) # … xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
                self.thisBook.appendToLastLine( '\\ft {}'.format( clean(noteText) ) )
                #print( "study note dg32", location, "Type =", noteType, "N =", repr(noteN), "Ref =", noteOsisRef, "ID =", noteOsisID, "p =", notePlacement )
            elif noteType == 'translation':
                #print( "Need to handle translation note properly here" ) # … xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
                self.thisBook.appendToLastLine( '\\ft {}'.format( clean(noteText) ) )
                #print( "translation note fgd1", location, "Type =", noteType, "N =", noteN, "Ref =", noteOsisRef, "ID =", noteOsisID, "p =", notePlacement )
            elif noteType == 'x-index':
                #print( "Need to handle index note properly here" ) # … xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
                #self.thisBook.addLine( 'ix~', noteText )
                self.thisBook.appendToLastLine( '\\ft {}'.format( clean(noteText) ) )
            elif noteType == 'x-strongsMarkup':
                self.thisBook.appendToLastLine( '\\ft {}'.format( noteText ) )
            else:
                print( "note2", noteType )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
        for subelement in element:
            if subelement.tag == OSISXMLBible.OSISNameSpace+'reference': # cross-references
                sublocation = "validateCrossReferenceOrFootnote: reference of " + locationDescription
                #print( "  Have", sublocation, "7h3f" )
                referenceText = (subelement.text if subelement.text is not None else '').strip()
                referenceTail = (subelement.tail if subelement.tail is not None else '').strip()
                referenceOsisRef = referenceType = None
                for attrib,value in subelement.items():
                    if attrib=='osisRef': referenceOsisRef = value
                    elif attrib=='type': referenceType = value
                    else:
                        logging.warning( "1sc5 Unprocessed {!r} attribute ({}) in {} sub-element of {} at {}".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                        loadErrors.append( "Unprocessed {!r} attribute ({}) in {} sub-element of {} at {} (1sc5)".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                    print( "  reference attributes: noteType={!r}, referenceText={!r}, referenceOsisRef={!r}, referenceType={!r}, referenceTail={!r}". \
                                        format( noteType, referenceText, referenceOsisRef, referenceType, referenceTail ) )
                if referenceText and not referenceType: # Maybe we can infer the anchor reference
                    if verseMilestone and verseMilestone.count('.')==2: # Something like Gen.1.3
                        #print( 'vm', verseMilestone )
                        #print( 'ror', referenceOsisRef )
                        anchor = verseMilestone.split('.',1)[1] # Just get the verse reference like "1.3"
                        #referenceType = 'source' # so it works below for cross-references
                        #print( 'rt', referenceText )
                        if noteType=='crossReference':
                            #assert not noteText and not referenceTail
                            if noteText and not noteText.isspace():
                                #print( 'nt', repr(noteText) )
                                # The following code doesn't work great for bridged verses,
                                #   e.g., <verse sID="Rom.9.11" osisID="Rom.9.11 Rom.9.12"/> (bridge isn't in verseMilestone)
                                if anchor in noteText or anchor.replace('.',':') in noteText \
                                or ( noteText[0].isdigit() and (':' in noteText or '.' in noteText) and '-' in noteText ):
                                    anchor = noteText
                                else:
                                    logging.error( "What do we do here with the {!r} note at {}".format( noteText, verseMilestone ) )
                                    loadErrors.append( "What do we do here with the {!r} note at {}".format( noteText, verseMilestone ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning:
                                        print( "What do we do here with the {!r} note at {}".format( noteText, verseMilestone ) )
                                        halt
                            self.thisBook.appendToLastLine( '\\xo {}'.format( anchor ) )
                            continue
                        elif noteType=='footnote':
                            self.thisBook.addLine( 'v~', anchor ) # There's no USFM for this
                        else:
                            print( 'CATERPILLAR', sublocation, verseMilestone, noteType, referenceType, referenceText )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                if noteType=='crossReference' and referenceType=='source':
                    #assert not noteText and not referenceTail
                    if BibleOrgSysGlobals.debugFlag: assert not noteText or noteText.isspace()
                    self.thisBook.appendToLastLine( '\\xt {}'.format( referenceText ) )
                elif noteType=='crossReference' and not referenceType and referenceOsisRef is not None:
                    if 0 and USFMResults and USFMResults[-1][0]=='xt': # Combine multiple cross-references into one xt field
                        self.thisBook.appendToLastLine( '\\xt {}'.format( USFMResults.pop()[1]+referenceText ) )
                    else:
                        self.thisBook.appendToLastLine( '\\xt {}'.format( clean(referenceText) ) )
                elif noteType=='footnote' and referenceType=='source':
                    if BibleOrgSysGlobals.debugFlag: assert referenceText and not noteText
                    if not referenceText[-1] == ' ': referenceText += ' '
                    self.thisBook.appendToLastLine( '\\fr {}'.format( clean(referenceText) ) )
                elif noteType=='study' and referenceType=='source': # This bit needs fixing up properly …xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
                    #print( "rT={!r} nT={!r} rTail={!r}".format( referenceText, noteText, referenceTail ) )
                    if BibleOrgSysGlobals.debugFlag: assert referenceText and not noteText.strip()
                    if not referenceText[-1] == ' ': referenceText += ' '
                    #else: logging.warning( "How come there's no tail? rT={!r} nT={!r} rTail={!r}".format( referenceText, noteText, referenceTail ) )
                    #print( "study note3", location, "Type =", noteType, "N =", noteN, "Ref =", noteOsisRef, "ID =", noteOsisID, "p =", notePlacement ); halt
                elif noteType=='translation' and referenceType=='source': # This bit needs fixing up properly …xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
                    if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                        print( "{}: rT={!r} nT={!r} rTail={!r}".format( self.abbreviation, referenceText, noteText, referenceTail ) )
                        assert referenceText and not noteText
                    if not referenceText[-1] == ' ': referenceText += ' '
                    self.thisBook.appendToLastLine( '\\fr {}'.format( referenceText ) )
                elif noteType=='translation' and referenceType is None: # This bit needs fixing up properly …xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
                    if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                        print( "{}: rT={!r} nT={!r} rTail={!r}".format( self.abbreviation, referenceText, noteText, referenceTail ) )
                        #assert referenceText
                    if noteText:
                        self.thisBook.appendToLastLine( '\\fr {} \\ft {}'.format( referenceText, noteText ) )
                    else:
                        if referenceText and referenceText[-1]!=' ': referenceText += ' '
                        self.thisBook.appendToLastLine( '\\fr {}'.format( referenceText ) )
                else:
                    logging.critical( "Don't know how to handle notetype={!r} and referenceType={!r} yet".format( noteType, referenceType ) )
                    loadErrors.append( "Don't know how to handle notetype={!r} and referenceType={!r} yet".format( noteType, referenceType ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                for sub2element in subelement: # Can have nested references in some OSIS files
                    if sub2element.tag == OSISXMLBible.OSISNameSpace+'reference': # cross-references
                        sub2location = "validateCrossReferenceOrFootnote: reference of reference of " + locationDescription
                        #print( "  Have", sub2location, "w3r5" )
                        BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, sub2location+" at "+verseMilestone, '67t4', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2location+" at "+verseMilestone, '6hnm', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2location+" at "+verseMilestone, 'x3b7', loadErrors )
                        subreferenceText = sub2element.text
                        if BibleOrgSysGlobals.debugFlag: assert noteType == 'crossReference'
                        self.thisBook.appendToLastLine( '\\xo {}'.format( subreferenceText ) )
                    elif sub2element.tag == OSISXMLBible.OSISNameSpace+'foreign':
                        sub2location = "validateCrossReferenceOrFootnote: foreign of reference of " + locationDescription
                        BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, sub2location+" at "+verseMilestone, '67t4', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2location+" at "+verseMilestone, '6hnm', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2location+" at "+verseMilestone, 'x3b7', loadErrors )
                        subreferenceText = sub2element.text
                        self.thisBook.appendToLastLine( '\\tl {}\\tl*'.format( clean(subreferenceText) ) )
                    elif sub2element.tag == OSISXMLBible.OSISNameSpace+'seg':
                        sub2location = "validateCrossReferenceOrFootnote: seg of reference of " + locationDescription
                        self.validateAndLoadSEG( sub2element, sub2location, verseMilestone, loadErrors )
                    else:
                        logging.error( "7h45 Unprocessed {!r} sub2element ({}) in {} at {}".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                        loadErrors.append( "Unprocessed {!r} sub2element ({}) in {} at {} (7h45)".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                            print( self.abbreviation, sub2element.tag ); halt
                if referenceTail and referenceTail.strip():
                    self.thisBook.appendToLastLine( '\\{} {}'.format( ('xt' if noteType=='crossReference' else 'ft'), clean(referenceTail) ) )
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'q':
                sublocation = "validateCrossReferenceOrFootnote: q of " + locationDescription
                qWho = qReferenceType = qMarker = None
                for attrib,value in subelement.items():
                    #print( attrib, value )
                    if attrib=='who': qWho = value
                    elif attrib=='type': qReferenceType = value
                    elif attrib=='marker': qMarker = value # usually a quote character
                    else:
                        logging.warning( "3d4r Unprocessed {!r} attribute ({}) in {} sub-element of {} at {}".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                        loadErrors.append( "Unprocessed {!r} attribute ({}) in {} sub-element of {} at {} (3d4r)".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    if qReferenceType: assert qReferenceType in ('x-footnote',)
                    if qMarker:
                        assert qMarker in ( "'", '"', )
                        if BibleOrgSysGlobals.debugFlag: assert not (qWho or qReferenceType)
                #print( "noteType", repr(noteType) )
                if BibleOrgSysGlobals.debugFlag: assert noteType in ('footnote','translation','study')
                qText = subelement.text.strip() if subelement.text else ''
                qTail = subelement.tail
                #print( 'qText', repr(qText) )
                #if BibleOrgSysGlobals.debugFlag: assert qText
                if '\n' in qText: # why's this
                    qText = qText.replace( '\n', '\\fp ' )
                self.thisBook.appendToLastLine( '\\fq {}'.format( qText ) )
                for sub2element in subelement:
                    if sub2element.tag == OSISXMLBible.OSISNameSpace+'transChange':
                        #sub2location = "validateCrossReferenceOrFootnote: transChange of " + locationDescription
                        self.validateTransChange( sub2element, sublocation, verseMilestone, loadErrors ) # Also handles the tail
                    else:
                        logging.error( "gk23 Unprocessed {!r} sub-element ({}) in {} at {}".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                        loadErrors.append( "Unprocessed {!r} sub-element ({}) in {} at {} (gk23)".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                if qTail and qTail.strip():
                    #print( 'qTail', repr(qTail) )
                    self.thisBook.appendToLastLine( '\\ft {}'.format( clean(qTail) ) )
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'catchWord':
                sublocation = "validateCrossReferenceOrFootnote: catchWord of " + locationDescription
                BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation+" at "+verseMilestone, '2w43', loadErrors )
                catchWordText, catchWordTail = subelement.text, subelement.tail
                if noteType == 'footnote':
                    self.thisBook.appendToLastLine( '\\fq {}'.format( clean(catchWordText) ) )
                    for sub2element in subelement: # Can have nested catchWords in some (horrible) OSIS files)
                        if sub2element.tag == OSISXMLBible.OSISNameSpace+'catchWord': #
                            sub2location = "validateCrossReferenceOrFootnote: catchWord of catchWord of " + locationDescription
                            #print( "  Have", sub2location, "j2f6" )
                            BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, sub2location+" at "+verseMilestone, '2d4r', loadErrors )
                            BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2location+" at "+verseMilestone, '23c6', loadErrors )
                            BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2location+" at "+verseMilestone, 'c456n', loadErrors )
                            subCatchWordText = sub2element.text
                            if BibleOrgSysGlobals.debugFlag: assert noteType == 'footnote'
                            self.thisBook.appendToLastLine( '\\fq {}'.format( subCatchWordText ) )
                        else:
                            logging.error( "8j6g Unprocessed {!r} sub2element ({}) in {} at {}".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                            loadErrors.append( "Unprocessed {!r} sub2element ({}) in {} at {} (8j6g)".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                elif noteType == 'translation':
                    self.thisBook.appendToLastLine( '\\fq {}'.format( clean(catchWordText) ) )
                    BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, 'fh36', loadErrors )
                elif noteType == 'variant':
                    self.thisBook.appendToLastLine( '\\fq {}'.format( clean(catchWordText) ) )
                    BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, 'fh37', loadErrors )
                elif noteType == 'alternative':
                    self.thisBook.appendToLastLine( '\\fq {}'.format( clean(catchWordText) ) )
                    BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, 'fh38', loadErrors )
                else:
                    if debuggingThisModule: print( "{!r} note not handled FG35".format( noteType ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                if catchWordTail:
                    self.thisBook.appendToLastLine( '\\fq* {}'.format( clean(catchWordTail) ) ) # Do we need the space
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'hi':
                sublocation = "validateCrossReferenceOrFootnote: hi of " + locationDescription
                self.validateHighlight( subelement, sublocation, verseMilestone, loadErrors ) # Also handles the tail
                justFinishedLG = False
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'rdg':
                sublocation = "validateCrossReferenceOrFootnote: rdg of " + locationDescription
                self.validateRDG( subelement, sublocation, verseMilestone, loadErrors ) # Also handles the tail
                justFinishedLG = False
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'divineName':
                sublocation = "validateCrossReferenceOrFootnote: divineName of " + locationDescription
                self.validateDivineName( subelement, sublocation, verseMilestone, loadErrors )
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'name':
                sublocation = "validateCrossReferenceOrFootnote: name of " + locationDescription
                self.validateProperName( subelement, sublocation, verseMilestone, loadErrors )
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'seg': # cross-references
                sublocation = "validateCrossReferenceOrFootnote: seg of " + locationDescription
                self.validateAndLoadSEG( subelement, sublocation, verseMilestone, loadErrors ) # Also handles the tail
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'note':
                sublocation = "validateCrossReferenceOrFootnote: note of " + locationDescription
                noteText = subelement.text
                BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, 'vw24', loadErrors )
                BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation+" at "+verseMilestone, 'plq2', loadErrors )
                # Process the attributes
                notePlacement = noteOsisRef = noteOsisID = noteType = None
                for attrib,value in subelement.items():
                    if attrib=='type': noteType = value
                    elif attrib=='placement': notePlacement = value
                    elif attrib=='osisRef': noteOsisRef = value
                    elif attrib=='osisID': noteOsisID = value
                    else:
                        logging.warning( "f5j3 Unprocessed {!r} attribute ({}) in {} sub-element of {} at {}".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                        loadErrors.append( "Unprocessed {!r} attribute ({}) in {} sub-element of {} at {} (f5j3)".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                logging.error( "odf3 Unprocessed note: {} {} {} {} {}".format( repr(noteText), repr(noteType), repr(notePlacement), repr(noteOsisRef), repr(noteOsisID) ) )
                loadErrors.append( "Unprocessed note: {} {} {} {} {} (odf3)".format( repr(noteText), repr(noteType), repr(notePlacement), repr(noteOsisRef), repr(noteOsisID) ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'transChange':
                sublocation = "validateCrossReferenceOrFootnote: transChange of " + locationDescription
                self.validateTransChange( subelement, sublocation, verseMilestone, loadErrors ) # Also handles the tail
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'foreign':
                sublocation = "validateCrossReferenceOrFootnote: foreign of " + locationDescription
                fText = subelement.text
                BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, 'cbf6', loadErrors )
                BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation+" at "+verseMilestone, 'cbf4', loadErrors )
                # Process the attributes
                fN = None
                for attrib,value in subelement.items():
                    if attrib=='n': fN = value
                    else:
                        logging.warning( "h0j3 Unprocessed {!r} attribute ({}) in {} sub-element of {} at {}".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                        loadErrors.append( "Unprocessed {!r} attribute ({}) in {} sub-element of {} at {} (h0j3)".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                logging.error( "Unused {!r} foreign field at {}".format( fText, sublocation+" at "+verseMilestone ) )
                loadErrors.append( "Unused {!r} foreign field at {}".format( fText, sublocation+" at "+verseMilestone ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
            else:
                logging.error( "1d54 Unprocessed {!r} sub-element ({}) in {} at {}".format( subelement.tag, subelement.text, location, verseMilestone ) )
                loadErrors.append( "Unprocessed {!r} sub-element ({}) in {} at {} (1d54)".format( subelement.tag, subelement.text, location, verseMilestone ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
        if openFieldname: self.thisBook.appendToLastLine( '\\{}*'.format( openFieldname ) )
        #if element.tail and element.tail.strip(): self.thisBook.appendToLastLine( clean(element.tail) )
        noteTail = clean( element.tail, loadErrors, location, verseMilestone )
        if noteTail: self.thisBook.appendToLastLine( noteTail )
    # end of OSISXMLBible.validateCrossReferenceOrFootnote


    def validateTransChange( self, element, location, verseMilestone, loadErrors ):
        """
        Handle a transChange element and return a string.
        """
        sublocation = "validateTransChange: transChange of " + location
        # Process the attributes
        transchangeType = None
        for attrib,value in element.items():
            if attrib=='type': transchangeType = value
            else:
                logging.warning( "8q1k Unprocessed {!r} attribute ({}) in {} at {}".format( attrib, value, sublocation, verseMilestone ) )
                loadErrors.append( "Unprocessed {!r} attribute ({}) in {} at {} (8q1k)".format( attrib, value, sublocation, verseMilestone ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
        if BibleOrgSysGlobals.debugFlag: assert transchangeType in ('added',)
        tcText = clean(element.text) if element.text else ''
        self.thisBook.appendToLastLine( '\\add {}'.format( tcText ) )
        # Now process the subelements
        for subelement in element:
            if subelement.tag == OSISXMLBible.OSISNameSpace+'w':
                sublocation = "validateTransChange: w of transChange of " + location
                self.validateAndLoadWord( subelement, sublocation, verseMilestone, loadErrors )
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'divineName':
                sublocation = "validateTransChange: divineName of transChange of " + location
                self.validateDivineName( subelement, sublocation, verseMilestone, loadErrors )
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'name':
                sublocation = "validateTransChange: name of transChange of " + location
                self.validateProperName( subelement, sublocation, verseMilestone, loadErrors )
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'note':
                sublocation = "validateTransChange: note of transChange of " + location
                self.validateCrossReferenceOrFootnote( subelement, sublocation, verseMilestone, loadErrors )
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'seg':
                sublocation = "validateTransChange: seg of transChange of " + location
                self.validateAndLoadSEG( subelement, sublocation, verseMilestone, loadErrors )
            else:
                logging.error( "dfv3 Unprocessed {!r} sub-element ({}) in {} at {}".format( subelement.tag, subelement.text, sublocation, verseMilestone ) )
                loadErrors.append( "Unprocessed {!r} sub-element ({}) in {} at {} (dfv3)".format( subelement.tag, subelement.text, sublocation, verseMilestone ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
        tcTail = clean(element.tail) if element.tail else ''
        self.thisBook.appendToLastLine( '\\add*{}'.format( tcTail ) )
    # end of validateTransChange


    def validateVerseElement( self, element, verseMilestone, chapterMilestone, locationDescription, loadErrors ):
        """
        Check/validate and process a verse element.

        This currently handles three types of OSIS files:
            1/ Has verse start milestones and end milestones
            2/ Has verse start milestones but no end milestones
            3/ Verse elements are containers for the actual verse information

        Returns one of the following:
            OSIS verse ID string for a startMilestone
            '' for an endMilestone
            'verseContainer.' + verse number string for a container
            'verseContents#' + verse number string + '#' + verse contents for a verse contained within the <verse>…</verse> markers
        """
        #print( "OSISXMLBible.validateVerseElement at {} with {!r} and {!r}".format( locationDescription, chapterMilestone, verseMilestone ) )
        location = "validateVerseElement: " + locationDescription
        verseText = element.text
        #print( "vT", verseText )
        #BibleOrgSysGlobals.checkXMLNoText( element, location+" at "+verseMilestone, 'x2f5', loadErrors )
        OSISVerseID = sID = eID = n = None
        for attrib,value in element.items():
            if attrib=='osisID': OSISVerseID = value
            elif attrib=='sID': sID = value
            elif attrib=='eID': eID = value
            elif attrib=='n': n = value
            else:
                displayTag = element.tag[len(self.OSISNameSpace):] if element.tag.startswith(self.OSISNameSpace) else element.tag
                logging.warning( "8jh6 Unprocessed {!r} attribute ({}) in {} subelement of {}".format( attrib, value, displayTag, location ) )
                loadErrors.append( "Unprocessed {!r} attribute ({}) in {} subelement of {} (8jh6)".format( attrib, value, displayTag, location ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( " validateVerseElement attributes: OSISVerseID = {!r} sID = {!r} eID = {!r} n = {!r}".format( OSISVerseID, sID, eID, n ) )
        if sID and eID:
            logging.critical( _("Invalid combined sID and eID verse attributes in {}: {}").format( location, element.items() ) )
            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
        if sID and not OSISVerseID:
            logging.error( _("Missing verse attributes in {}: {}").format( location, element.items() ) )
            loadErrors.append( _("Missing verse attributes in {}: {}").format( location, element.items() ) )
            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt

        # See if this is a milestone or a verse container
        if len(element)==0 and ( sID or eID ): # it's a milestone (no sub-elements)
            if BibleOrgSysGlobals.debugFlag: assert not verseText
            if sID and OSISVerseID and not eID: # we have a start milestone
                if verseMilestone: # but we already have an open milestone
                    if self.haveEIDs:
                        logging.error( "Got a {} verse milestone while {} is still open at {}".format( sID, verseMilestone, location ) )
                        loadErrors.append( "Got a {} verse milestone while {} is still open at {}".format( sID, verseMilestone, location ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                verseMilestone = sID
                #for char in (' ','-'):
                #    if char in verseMilestone: # it contains a range like 'Mark.6.17 Mark.6.18' or 'Mark.6.17-Mark.6.18'
                #        chunks = verseMilestone.split( char )
                #        if BibleOrgSysGlobals.debugFlag: assert len(chunks) == 2
                #        verseMilestone = chunks[0] # Take the start of the range
                #if not verseMilestone.count('.')==2: logging.error( "validateVerseElement: {} verse milestone seems wrong format for {}".format( verseMilestone, OSISVerseID ) )
                vmBits, cmBits = verseMilestone.split( '.' ), chapterMilestone.split( '.' )
                #print( "cv milestone stuff", repr(verseMilestone), repr(chapterMilestone), vmBits, cmBits )
                if chapterMilestone.startswith( 'chapterContainer.' ): # The chapter is a container but the verse is a milestone!
                    if not verseMilestone.startswith( chapterMilestone[17:] ):
                        logging.error( "{!r} verse milestone seems wrong in {!r} chapter milestone at {}".format( verseMilestone, chapterMilestone, location ) )
                        loadErrors.append( "{!r} verse milestone seems wrong in {!r} chapter milestone at {}".format( verseMilestone, chapterMilestone, location ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                elif vmBits[0:2] != cmBits[0:2]:
                    logging.error( "This {!r} verse milestone seems wrong in {!r} chapter milestone at {}".format( verseMilestone, chapterMilestone, location ) )
                    loadErrors.append( "This {!r} verse milestone seems wrong in {!r} chapter milestone at {}".format( verseMilestone, chapterMilestone, location ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
            elif eID and not OSISVerseID and not sID: # we have an end milestone
                #print( "here", repr(verseMilestone), repr(OSISVerseID), repr(sID), repr(eID) )
                self.haveEIDs = True
                if verseMilestone:
                    if eID==verseMilestone: pass # Good -- the end milestone matched the open start milestone
                    else:
                        logging.error( "{!r} verse milestone end didn't match last end milestone {!r} at {}".format( verseMilestone, eID, location ) )
                        loadErrors.append( "{!r} verse milestone end didn't match last end milestone {!r} at {}".format( verseMilestone, eID, location ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                else:
                    logging.critical( "Have {!r} verse end milestone but no verse start milestone encountered at {}".format( eID, location ) )
                    loadErrors.append( "Have {!r} verse end milestone but no verse start milestone encountered at {}".format( eID, location ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                return '' # end milestone closes any open milestone
            else:
                logging.critical( "Unrecognized verse milestone in {}: {}".format( location, element.items() ) )
                print( " ", verseMilestone ); halt
                return '' # don't have any other way to handle this

            if verseMilestone: # have an open milestone
                #print( "'"+verseMilestone+"'" )
                if BibleOrgSysGlobals.debugFlag: assert ' ' not in verseMilestone
                if '-' in verseMilestone: # Something like Jas.1.7-Jas.1.8
                    chunks = verseMilestone.split( '-' )
                    if len(chunks) != 2:
                        logging.error( "Shouldn't have multiple hyphens in verse milestone {!r}".format( verseMilestone ) )
                        loadErrors.append( "Shouldn't have multiple hyphens in verse milestone {!r}".format( verseMilestone ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    bits1 = chunks[0].split( '.' )
                    if len(bits1) != 3:
                        logging.error( "Expected three components before hyphen in verse milestone {!r}".format( verseMilestone ) )
                        loadErrors.append( "Expected three components before hyphen in verse milestone {!r}".format( verseMilestone ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    bits2 = chunks[1].split( '.' )
                    if len(bits2) != 3:
                        logging.error( "Expected three components after hyphen in verse milestone {!r}".format( verseMilestone ) )
                        loadErrors.append( "Expected three components after hyphen in verse milestone {!r}".format( verseMilestone ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                        bits2 = [bits1[0],bits1[1],'999'] # Try to do something intelligent
                    self.thisBook.addLine( 'v', bits1[2]+'-'+bits2[2] )
                else: # no hyphen
                    bits = verseMilestone.split( '.' )
                    #print( "sdfssf", verseMilestone, bits )
                    if BibleOrgSysGlobals.debugFlag: assert len(bits) >= 3
                    self.thisBook.addLine( 'v', bits[2]+' ' )
                vTail = clean(element.tail) # Newlines and leading spaces are irrelevant to USFM formatting
                if vTail: # This is the main text of the verse (follows the verse milestone)
                    self.thisBook.appendToLastLine( vTail )
                return verseMilestone
            if BibleOrgSysGlobals.debugFlag: halt # Should not happen

        else: # not a milestone -- it's verse container
            BibleOrgSysGlobals.checkXMLNoTail( element, location+" at "+verseMilestone, 's2d4', loadErrors )
            bits = OSISVerseID.split('.')
            #print( "OSISXMLBible.validateVerseElement verse container bits", bits, 'vT', verseText )
            if BibleOrgSysGlobals.debugFlag: assert len(bits)==3 and bits[1].isdigit() and bits[2].isdigit()
            #print( "validateVerseElement: Have a verse container at", verseMilestone )
            if verseText and verseText.strip():
                if self.source == "ftp://unboundftp.biola.edu/pub/albanian_utf8.zip": # Do some special handling
                    #print( "here", "&amp;quot;" in verseText, "&quot;" in verseText )
                    verseText = verseText.lstrip().replace('&quot;','"').replace('&lt;','<').replace('&gt;','>') # Fix some encoding issues
                    if "&" in verseText: print( "Still have ampersand in {!r}".format( verseText ) )
                return 'verseContents#' + bits[2] + '#' + verseText
            else: # it's a container for subelements
                return 'verseContainer.' + bits[2]

        if BibleOrgSysGlobals.debugFlag: halt # Should never reach this point in the code
    # end of OSISXMLBible.validateVerseElement


    def validateTitle( self, element, locationDescription, chapterMilestone, verseMilestone, loadErrors ):
        """
        Check/validate and process a OSIS Bible paragraph, including all subfields.
        """
        location = "validateTitle: " + locationDescription
        #print( "validateTitle @ {} @ {}/{}".format( locationDescription, chapterMilestone, verseMilestone ) )

        BibleOrgSysGlobals.checkXMLNoTail( element, location+" at "+verseMilestone, 'c4vd', loadErrors )
        titleText = clean( element.text, loadErrors, location, verseMilestone )

        titleType = titleSubType = titleShort = titleLevel = titleCanonicalFlag = None
        for attrib,value in element.items():
            if attrib=='type':
                titleType = value
            elif attrib=='subType':
                titleSubType = value
            elif attrib=='short':
                titleShort = value
            elif attrib=='level':
                titleLevel = value
            elif attrib=='canonical':
                titleCanonicalFlag = value
                assert titleCanonicalFlag in ('true','false')
            else:
                logging.warning( "4b8e Unprocessed {!r} attribute ({}) in {} at {}".format( attrib, value, location, verseMilestone ) )
                loadErrors.append( "Unprocessed {!r} attribute ({}) in {} at {} (4b8e)".format( attrib, value, location, verseMilestone ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
        #print( 'vdq2', repr(titleType), repr(titleSubType), repr(titleText), titleLevel, titleCanonicalFlag )
        if BibleOrgSysGlobals.debugFlag:
            if titleType: assert titleType in ('main','chapter','psalm','scope','sub','parallel','acrostic')
            if titleSubType: assert titleSubType == 'x-preverse'
        if chapterMilestone:
            #print( 'title', verseMilestone, repr(titleText), repr(titleType), repr(titleSubType), repr(titleShort), repr(titleLevel) )
            if titleText:
                if not titleType and not titleShort and self.language=='ksw': # it's a Karen alternate chapter number
                    self.thisBook.addLine( 'cp', titleText )
                elif titleType == 'parallel':
                    self.thisBook.addLine( 'sr', titleText )
                elif titleCanonicalFlag=='true':
                    assert titleType == 'psalm'
                    self.thisBook.addLine( 'd', titleText )
                else: # let's guess that it's a section heading
                    if debuggingThisModule:
                        print( "title assumed to be section heading", verseMilestone, repr(titleText), repr(titleType), repr(titleSubType), repr(titleShort), repr(titleLevel) )
                    sfm = 's'
                    if titleLevel:
                        assert titleLevel in ('1','2','3')
                        sfm += titleLevel
                    self.thisBook.addLine( sfm, titleText )
        else: # must be in the introduction if it's before all chapter milestones
        #if self.haveBook:
            #assert titleText
            if titleText:
                #print( 'title', repr(titleText) )
                self.thisBook.addLine( 'imt', titleText ) # Could it also be 'is'?
        #else: # Must be a book group title
            #BibleOrgSysGlobals.checkXMLNoSubelements( element, location+" at book group", 'vcw5', loadErrors )
            #if BibleOrgSysGlobals.debugFlag: assert titleText
            #if titleText:
                #if BibleOrgSysGlobals.verbosityLevel > 2: print( "    Got book group title", repr(titleText) )
                #self.divisions[titleText] = []
                ##self.thisBook.addLine( 'bgt', titleText ) # Could it also be 'is'?
        for subelement in element:
            if subelement.tag == OSISXMLBible.OSISNameSpace+'title': # section reference(s)
                sublocation = "validateTitle: title of " + locationDescription
                BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation+" at "+verseMilestone, '21d5', loadErrors )
                titleText = clean( subelement.text, loadErrors, sublocation, verseMilestone )
                # Handle attributes
                titleType = titleLevel = None
                for attrib,value in subelement.items():
                    if attrib== 'type': titleType = value
                    elif attrib== 'level': titleLevel = value
                    else:
                        logging.warning( "56v3 Unprocessed {!r} attribute ({}) in {} sub2element of {} at {}".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                        loadErrors.append( "Unprocessed {!r} attribute ({}) in {} sub2element of {} at {} (56v3)".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                if titleText:
                    #print( repr(mainDivType), repr(titleType), repr(titleLevel), repr(chapterMilestone) )
                    if chapterMilestone: marker = 'sr'
                    else: marker = 'mt{}'.format( titleLevel if titleLevel else '' )
                    self.thisBook.addLine( marker, titleText )
                for sub2element in subelement:
                    if sub2element.tag == OSISXMLBible.OSISNameSpace+'reference':
                        sub2location = "reference of " + sublocation
                        BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2location+" at "+verseMilestone, 'f5g2', loadErrors )
                        referenceText = clean( sub2element.text, loadErrors, sub2location, verseMilestone )
                        referenceTail = clean( sub2element.tail, loadErrors, sub2location, verseMilestone )
                        referenceOsisRef = None
                        for attrib,value in sub2element.items():
                            if attrib=='osisRef':
                                referenceOsisRef = value
                            else:
                                logging.warning( "89n5 Unprocessed {!r} attribute ({}) in {} sub3element of {} at {}".format( attrib, value, sub2element.tag, sublocation, verseMilestone ) )
                                loadErrors.append( "Unprocessed {!r} attribute ({}) in {} sub3element of {} at {} (89n5)".format( attrib, value, sub2element.tag, sublocation, verseMilestone ) )
                                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                        if BibleOrgSysGlobals.debugFlag:
                            print( 'here bd02', repr(referenceText), repr(referenceOsisRef), repr(referenceTail) )
                        self.thisBook.addLine( 'r', referenceText+referenceTail )
                    else:
                        logging.error( "2d6h Unprocessed {!r} sub2element ({}) in {} at {}".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                        loadErrors.append( "Unprocessed {!r} sub2element ({}) in {} at {} (2d6h)".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'hi':
                sublocation = "validateTitle: hi of " + locationDescription
                self.validateHighlight( subelement, sublocation, verseMilestone, loadErrors ) # Also handles the tail
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'note':
                sublocation = "validateTitle: note of " + locationDescription
                self.validateCrossReferenceOrFootnote( subelement, sublocation, verseMilestone, loadErrors )
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'w': # Probably a canonical Psalm title
                sublocation = "validateTitle: w of " + locationDescription
                self.validateAndLoadWord( subelement, sublocation, verseMilestone, loadErrors )
                #if 0:
                    #word = subelement.text if subelement.text else ''
                    ## Handle attributes
                    #lemma = morph = None
                    #for attrib,value in subelement.items():
                        #if attrib=='lemma': lemma = value
                        #elif attrib=='morph': morph = value
                        #else:
                            #logging.warning( "dv42 Unprocessed {!r} attribute ({}) in {} at {}".format( attrib, value, sublocation, verseMilestone ) )
                            #loadErrors.append( "Unprocessed {!r} attribute ({}) in {} at {} (dv42)".format( attrib, value, sublocation, verseMilestone ) )
                    #if lemma and lemma.startswith('strong:'):
                        #word += "\\str {}\\str*".format( lemma[7:] )
                        #lemma = None # we've used it
                    #if lemma or morph:
                        #if BibleOrgSysGlobals.debugFlag: logging.info( "Losing lemma or morph here at {}".format( verseMilestone ) )
                        #loadErrors.append( "Losing lemma or morph here at {}".format( verseMilestone ) )
                    ## Handle sub-elements
                    #for sub2element in subelement:
                        #if sub2element.tag == OSISXMLBible.OSISNameSpace+'xyz':
                            #sub2location = "divineName of " + sublocation
                            #BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, sub2location+" at "+verseMilestone, 'fbf3', loadErrors )
                            #BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2location+" at "+verseMilestone, 'kje3', loadErrors )
                            #if BibleOrgSysGlobals.debugFlag: assert sub2element.text
                            ##print( "Here scw2", repr(sub2element.text) )
                            #word += "\\nd {}\\nd*".format( sub2element.text )
                            #if sub2element.tail: word += sub2element.tail
                        #else:
                            #logging.error( "kd92 Unprocessed {!r} sub2element ({}) in {} at {}".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                            #loadErrors.append( "Unprocessed {!r} sub2element ({}) in {} at {} (kd92)".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                            #if BibleOrgSysGlobals.debugFlag: halt
                    #if subelement.tail: word += subelement.tail
                    #self.thisBook.appendToLastLine( word )
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'abbr':
                sublocation = "validateTitle: abbr of " + locationDescription
                abbrText = subelement.text
                abbrTail = subelement.tail
                BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, 'gd56', loadErrors )
                # Handle attributes
                abbrExpansion = None
                for attrib,value in subelement.items():
                    if attrib== 'expansion': abbrExpansion = value
                    else:
                        logging.warning( "vsy3 Unprocessed {!r} attribute ({}) in {} sub2element of {} at {}".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                        loadErrors.append( "Unprocessed {!r} attribute ({}) in {} sub2element of {} at {} (vsy3)".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                #self.thisBook.appendToLastLine( '{}\\abbr {}\\abbr*{}'.format( abbrText, abbrExpansion, abbrTail ) )
                logging.warning( "Unused {}={} abbr field at {}".format( repr(abbrText), repr(abbrExpansion), sublocation+" at "+verseMilestone ) )
                loadErrors.append( "Unused {}={} abbr field at {}".format( repr(abbrText), repr(abbrExpansion), sublocation+" at "+verseMilestone ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning:
                    #print( "abbr in title: {!r} -> {!r}".format( abbrText, abbrExpansion ) )
                    pass
                    #halt
                self.thisBook.appendToLastLine( '{}{}'.format( abbrText, abbrTail ) )
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'transChange':
                sublocation = "validateTitle: transChange of " + locationDescription
                self.validateTransChange( subelement, sublocation, verseMilestone, loadErrors ) # Also handles the tail
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'foreign':
                sublocation = "validateTitle: foreign of " + locationDescription
                foreignText = subelement.text
                BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, 'cbf6', loadErrors )
                BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation+" at "+verseMilestone, 'cbf4', loadErrors )
                # Process the attributes
                foreignN = None
                for attrib,value in subelement.items():
                    if attrib=='n': foreignN = value # This can be a Hebrew letter/number in OS KJV
                    else:
                        logging.warning( "h0j3 Unprocessed {!r} attribute ({}) in {} sub-element of {} at {}".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                        loadErrors.append( "Unprocessed {!r} attribute ({}) in {} sub-element of {} at {} (h0j3)".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                if 'Ps' in verseMilestone: # or 'Lam' in verseMilestone:
                    # Assume it's an acrostic heading (but we don't use the foreignN field)
                    self.thisBook.addLine( 'qa', foreignText )
                else:
                    logging.error( "Unused {!r} foreign field at {}".format( foreignText, sublocation+" at "+verseMilestone ) )
                    loadErrors.append( "Unused {!r} foreign field at {}".format( foreignText, sublocation+" at "+verseMilestone ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'reference':
                sublocation = "validateTitle: reference of " + locationDescription
                rText = subelement.text
                BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation+" at "+verseMilestone, 'ld10', loadErrors )
                BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, 'js12', loadErrors )
                BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation+" at "+verseMilestone, 'jsv2', loadErrors )
                logging.error( "Unused {!r} reference field at {}".format( rText, sublocation+" at "+verseMilestone ) )
                loadErrors.append( "Unused {!r} reference field at {}".format( rText, sublocation+" at "+verseMilestone ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'verse':
                sublocation = "validateTitle: verse of " + locationDescription
                verseMilestone = self.validateVerseElement( subelement, verseMilestone, chapterMilestone, sublocation, loadErrors )
            elif subelement.tag == OSISXMLBible.OSISNameSpace+'seg':
                sublocation = "validateTitle: verse of " + locationDescription
                self.validateAndLoadSEG( subelement, sublocation, verseMilestone, loadErrors )
            else:
                logging.error( "jkd7 Unprocessed {!r} subelement ({}) in {} at {}".format( subelement.tag, subelement.text, locationDescription, verseMilestone ) )
                loadErrors.append( "Unprocessed {!r} subelement ({}) in {} at {} (jkd7)".format( subelement.tag, subelement.text, locationDescription, verseMilestone ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
        #titleTail = clean( element.tail, loadErrors, location, verseMilestone )
    # end of OSISXMLBible.validateTitle


    def validateHeader( self, header, loadErrors ):
        """
        Check/validate the given OSIS header record.
        """
        if BibleOrgSysGlobals.verbosityLevel > 3: print( _("Loading {}OSIS header…").format( self.abbreviation+' ' if self.abbreviation else '' ) )
        headerlocation = 'header'
        BibleOrgSysGlobals.checkXMLNoText( header, headerlocation, '2s90', loadErrors )
        BibleOrgSysGlobals.checkXMLNoAttributes( header, headerlocation, '4f6h', loadErrors )
        BibleOrgSysGlobals.checkXMLNoTail( header, headerlocation, '0k6l', loadErrors )

        for element in header:
            if element.tag == OSISXMLBible.OSISNameSpace+'revisionDesc':
                location = "revisionDesc of " + headerlocation
                BibleOrgSysGlobals.checkXMLNoText( header, location, '2t5y', loadErrors )
                BibleOrgSysGlobals.checkXMLNoAttributes( header, location, '6hj8', loadErrors )
                BibleOrgSysGlobals.checkXMLNoTail( header, location, '3a1l', loadErrors )
                # Process the attributes first
                resp = None
                for attrib,value in element.items():
                    if attrib=='resp': resp = value
                    else:
                        logging.warning( "4j6a Unprocessed {} attribute ({}) in {}".format( attrib, value, location ) )
                        loadErrors.append( "Unprocessed {} attribute ({}) in {} (4j6a)".format( attrib, value, location ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt

                # Now process the subelements
                for subelement in element:
                    BibleOrgSysGlobals.checkXMLNoSubelements( subelement, location, '4f3f', loadErrors )
                    if len(subelement):
                        logging.error( "Unexpected {} subelements in subelement {} in {} revisionDesc".format( len(subelement), subelement.tag, osisWork ) )
                        loadErrors.append( "Unexpected {} subelements in subelement {} in {} revisionDesc".format( len(subelement), subelement.tag, osisWork ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    if subelement.tag == OSISXMLBible.OSISNameSpace+'date':
                        sublocation = "date of " + location
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, '9hj5', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '6g3s', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '4sd2', loadErrors )
                        date = subelement.text
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'p':
                        sublocation = "p of " + location
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, '4f4s', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '3c5g', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '9k5a', loadErrors )
                        p = element.text
                    else:
                        logging.error( "6g4g Unprocessed {!r} sub-element ({}) in revisionDesc element".format( subelement.tag, subelement.text ) )
                        loadErrors.append( "Unprocessed {!r} sub-element ({}) in revisionDesc element (6g4g)".format( subelement.tag, subelement.text ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
            elif element.tag == OSISXMLBible.OSISNameSpace+'work':
                location = "work of " + headerlocation
                BibleOrgSysGlobals.checkXMLNoText( header, location, '5h9k', loadErrors )
                BibleOrgSysGlobals.checkXMLNoAttributes( header, location, '2s3d', loadErrors )
                BibleOrgSysGlobals.checkXMLNoTail( header, location, '1d4f', loadErrors )
                # Process the attributes first
                osisWorkName = lang = None
                for attrib,value in element.items():
                    if attrib=='osisWork':
                        osisWorkName = value
                        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Have a {!r} work".format( osisWorkName ) )
                    elif attrib==OSISXMLBible.XMLNameSpace+"lang": lang = value
                    else:
                        logging.warning( "2k5s Unprocessed {} attribute ({}) in work element".format( attrib, value ) )
                        loadErrors.append( "Unprocessed {} attribute ({}) in work element (2k5s)".format( attrib, value ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                assert osisWorkName
                # Now process the subelements
                for subelement in element:
                    if len(subelement):
                        logging.error( "hf54 Unexpected {} subelements in subelement {} in {} work".format( len(subelement), subelement.tag, osisWork ) )
                        loadErrors.append( "Unexpected {} subelements in subelement {} in {} work (hf54)".format( len(subelement), subelement.tag, osisWork ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    if subelement.tag == OSISXMLBible.OSISNameSpace+'title':
                        sublocation = "title of " + location
                        if 0: self.validateTitle( subelement, sublocation, chapterMilestone, verseMilestone, loadErrors )
                        else:
                            BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '0k5f', loadErrors )
                            BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '8k0k', loadErrors )
                            if not self.title: self.title = subelement.text # Take the first title
                            titleType = None
                            for attrib,value in subelement.items():
                                if attrib=='type': titleType = value
                                else:
                                    logging.warning( "8f83 Unprocessed {!r} attribute ({}) in {}".format( attrib, value, sublocation ) )
                                    loadErrors.append( "Unprocessed {!r} attribute ({}) in {} (8f83)".format( attrib, value, sublocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'version':
                        sublocation = "version of " + location
                        BibleOrgSysGlobals.checkXMLNoText( subelement, sublocation, '3g1h', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, '7h4f', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '2j9z', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '0k3d', loadErrors )
                        self.suppliedMetadata['OSIS']['Version'] = subelement.text
                        for attrib,value in subelement.items():
                            logging.warning( "93d2 Unprocessed {!r} attribute ({}) in {}".format( attrib, value, sublocation ) )
                            loadErrors.append( "Unprocessed {!r} attribute ({}) in {} (93d2)".format( attrib, value, sublocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'date':
                        sublocation = "date of " + location
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '4x5h', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '3f9j', loadErrors )
                        date = subelement.text
                        dateType = dateEvent = None
                        for attrib,value in subelement.items():
                            if attrib=='type': dateType = value
                            elif attrib=='event': dateEvent = value
                            else:
                                logging.warning( "2k4d Unprocessed {!r} attribute ({}) in {}".format( attrib, value, sublocation ) )
                                loadErrors.append( "Unprocessed {!r} attribute ({}) in {} (2k4d)".format( attrib, value, sublocation ) )
                                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                        if BibleOrgSysGlobals.debugFlag: assert dateType in (None,'Gregorian')
                        if BibleOrgSysGlobals.debugFlag: assert dateEvent in (None,'eversion')
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'creator':
                        sublocation = "creator of " + location
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '9n3z', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '3n5z', loadErrors )
                        self.suppliedMetadata['OSIS']['Creator'] = subelement.text
                        creatorRole = creatorType = None
                        for attrib,value in subelement.items():
                            if attrib=='role': creatorRole = value
                            elif attrib=='type': creatorType = value
                            else:
                                logging.warning( "9f2d Unprocessed {!r} attribute ({}) in {}".format( attrib, value, sublocation ) )
                                loadErrors.append( "Unprocessed {!r} attribute ({}) in {} (9f2d)".format( attrib, value, sublocation ) )
                                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                        if BibleOrgSysGlobals.verbosityLevel > 2:
                            print( "    Creator (role={!r}{}) was {!r}".format( creatorRole, ", type={!r}".format(creatorType) if creatorType else '', self.suppliedMetadata['OSIS']['Creator'] ) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'contributor':
                        sublocation = "contributor of " + location
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '2u5z', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '3z4o', loadErrors )
                        self.suppliedMetadata['OSIS']['Contributor'] = subelement.text
                        contributorRole = None
                        for attrib,value in subelement.items():
                            if attrib=='role': contributorRole = value
                            else:
                                logging.warning( "1s5g Unprocessed {!r} attribute ({}) in {}".format( attrib, value, sublocation ) )
                                loadErrors.append( "Unprocessed {!r} attribute ({}) in {} (1s5g)".format( attrib, value, sublocation ) )
                                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                        if BibleOrgSysGlobals.verbosityLevel > 2:
                            print( "    Contributor ({}) was {!r}".format( contributorRole, self.suppliedMetadata['OSIS']['Contributor'] ) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'subject':
                        sublocation = "subject of " + location
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, 'frg3', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, 'ft4g', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, 'c35g', loadErrors )
                        self.suppliedMetadata['OSIS']['Subject'] = subelement.text
                        if BibleOrgSysGlobals.verbosityLevel > 2:
                            print( "    Subject was {!r}".format( self.suppliedMetadata['OSIS']['Subject'] ) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'description':
                        sublocation = "description of " + location
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '4a7s', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '1j6z', loadErrors )
                        self.suppliedMetadata['OSIS']['Description'] = subelement.text
                        descriptionType = descriptionSubType = resp = None
                        for attrib,value in subelement.items():
                            if attrib=='type': descriptionType = value
                            elif attrib=='subType': descriptionSubType = value
                            elif attrib=='resp': resp = value
                            else:
                                logging.warning( "6f3d Unprocessed {!r} attribute ({}) in {}".format( attrib, value, sublocation ) )
                                loadErrors.append( "Unprocessed {!r} attribute ({}) in {} (6f3d)".format( attrib, value, sublocation ) )
                                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                        if descriptionType: assert descriptionType in ('usfm','x-english','x-lwc')
                        if self.suppliedMetadata['OSIS']['Description'] and BibleOrgSysGlobals.verbosityLevel > 2:
                            print( "    Description{} is {!r}".format( " ({})".format(descriptionType) if descriptionType else '', self.suppliedMetadata['OSIS']['Description'] ) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'format':
                        sublocation = "format of " + location
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '8v3x', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '5n3x', loadErrors )
                        self.suppliedMetadata['OSIS']['Format'] = subelement.text
                        formatType = None
                        for attrib,value in subelement.items():
                            if attrib=='type': formatType = value
                            else:
                                logging.warning( "2f5s Unprocessed {!r} attribute ({}) in {}".format( attrib, value, sublocation ) )
                                loadErrors.append( "Unprocessed {!r} attribute ({}) in {} (2f5s)".format( attrib, value, sublocation ) )
                                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                        if BibleOrgSysGlobals.debugFlag: assert formatType == 'x-MIME'
                        if BibleOrgSysGlobals.verbosityLevel > 2: print( "    Format ({}) is {!r}".format( formatType, self.suppliedMetadata['OSIS']['Format'] ) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'type':
                        sublocation = "type of " + location
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '8j8b', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '3b4z', loadErrors )
                        self.suppliedMetadata['OSIS']['Type'] = subelement.text
                        typeType = None
                        for attrib,value in subelement.items():
                            if attrib=='type': typeType = value
                            else:
                                logging.warning( "7j3f Unprocessed {!r} attribute ({}) in {}".format( attrib, value, sublocation ) )
                                loadErrors.append( "Unprocessed {!r} attribute ({}) in {} (7j3f)".format( attrib, value, sublocation ) )
                                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                        if BibleOrgSysGlobals.debugFlag: assert typeType == 'OSIS'
                        if BibleOrgSysGlobals.verbosityLevel > 2:
                            print( "    Type ({}) is {!r}".format( typeType, self.suppliedMetadata['OSIS']['Type'] ) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'identifier':
                        sublocation = "identifier of " + location
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '2x6e', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '5a2m', loadErrors )
                        identifier = subelement.text
                        identifierType = None
                        for attrib,value in subelement.items():
                            if attrib=='type': identifierType = value
                            else:
                                logging.warning( "2d5g Unprocessed {!r} attribute ({}) in {}".format( attrib, value, sublocation ) )
                                loadErrors.append( "Unprocessed {!r} attribute ({}) in {} (2d5g)".format( attrib, value, sublocation ) )
                                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                        #print( "id", repr(identifierType) )
                        if BibleOrgSysGlobals.debugFlag: assert identifierType in ('OSIS','URL','x-ebible-id')
                        if BibleOrgSysGlobals.verbosityLevel > 2:
                            print( "    Identifier ({}) is {!r}".format( identifierType, identifier ) )
                        #print( "Here vds1", repr(self.name), repr(self.abbreviation) )
                        if identifierType=='OSIS':
                            if not self.name: self.name = identifier
                            if identifier.startswith( 'Bible.' ) and not self.abbreviation:
                                self.abbreviation = identifier[6:]
                        self.suppliedMetadata['OSIS']['Identifier'] = identifier
                        #print( "Here vds2", repr(self.name), repr(self.abbreviation) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'source':
                        sublocation = "source of " + location
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, '4gh7', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '6p3a', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '1i8p', loadErrors )
                        self.suppliedMetadata['OSIS']['Source'] = subelement.text
                        sourceRole = None
                        for attrib,value in subelement.items():
                            if attrib=='role': sourceRole = value
                            else:
                                logging.warning( "6h7h Unprocessed {!r} attribute ({}) in {}".format( attrib, value, sublocation ) )
                                loadErrors.append( "Unprocessed {!r} attribute ({}) in {} (6h7h)".format( attrib, value, sublocation ) )
                                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                        if BibleOrgSysGlobals.verbosityLevel > 2:
                            print( "    Source{} was {!r}".format( " ({})".format(sourceRole) if sourceRole else '', self.suppliedMetadata['OSIS']['Source'] ) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'publisher':
                        sublocation = "publisher of " + location
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '8n3x', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '3z7g', loadErrors )
                        self.suppliedMetadata['OSIS']['Publisher'] = subelement.text.replace( '&amp;', '&' )
                        publisherType = None
                        for attrib,value in subelement.items():
                            if attrib=='type': publisherType = value
                            else:
                                logging.warning( "7g5g Unprocessed {!r} attribute ({}) in {}".format( attrib, value, sublocation ) )
                                loadErrors.append( "Unprocessed {!r} attribute ({}) in {} (7g5g)".format( attrib, value, sublocation ) )
                                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                        if BibleOrgSysGlobals.verbosityLevel > 2:
                            print( "    Publisher {}is/was {!r}".format( '({}) '.format(publisherType) if publisherType else '', self.suppliedMetadata['OSIS']['Publisher'] ) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'scope':
                        sublocation = "scope of " + location
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, '3d4d', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '2g5z', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '1z4i', loadErrors )
                        self.suppliedMetadata['OSIS']['Scope'] = subelement.text
                        if BibleOrgSysGlobals.verbosityLevel > 2: print( "    Scope is {!r}".format( self.suppliedMetadata['OSIS']['Scope'] ) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'coverage':
                        sublocation = "coverage of " + location
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, '3d6g', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '3a6p', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '9l2p', loadErrors )
                        self.suppliedMetadata['OSIS']['Coverage'] = subelement.text
                        if BibleOrgSysGlobals.verbosityLevel > 2: print( "    Coverage is {!r}".format( self.suppliedMetadata['OSIS']['Coverage'] ) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'refSystem':
                        sublocation = "refSystem of " + location
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, '2s4f', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '3mtp', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '3p65', loadErrors )
                        self.suppliedMetadata['OSIS']['RefSystem'] = subelement.text
                        if self.suppliedMetadata['OSIS']['RefSystem'] in ('Bible','Bible.KJV','Bible.NRSVA','Dict.Strongs','Dict.Robinsons','Dict.strongMorph'):
                            if BibleOrgSysGlobals.verbosityLevel > 2: print( "    Reference system is {!r}".format( self.suppliedMetadata['OSIS']['RefSystem'] ) )
                        else:
                            logging.info( "Discovered an unknown {!r} refSystem".format( self.suppliedMetadata['OSIS']['RefSystem'] ) )
                            loadErrors.append( "Discovered an unknown {!r} refSystem".format( self.suppliedMetadata['OSIS']['RefSystem'] ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'language':
                        sublocation = "language of " + location
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '8n34', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '4v2n', loadErrors )
                        self.suppliedMetadata['OSIS']['Language'] = subelement.text
                        languageType = None
                        for attrib,value in subelement.items():
                            if attrib=='type': languageType = value
                            else:
                                logging.warning( "6g4f Unprocessed {!r} attribute ({}) in {}".format( attrib, value, sublocation ) )
                                loadErrors.append( "Unprocessed {!r} attribute ({}) in {} (6g4f)".format( attrib, value, sublocation ) )
                                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                        if languageType in ('SIL','IETF','x-ethnologue','x-in-english','x-vernacular'):
                            if ISOLanguages.isValidLanguageCode( self.suppliedMetadata['OSIS']['Language'] ):
                                if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Language is: {}".format( ISOLanguages.getLanguageName( self.suppliedMetadata['OSIS']['Language'] ) ) )
                            elif BibleOrgSysGlobals.verbosityLevel>2: print( "Discovered an unknown {!r} language".format( self.suppliedMetadata['OSIS']['Language'] ) )
                        else: print( "Discovered an unknown {!r} languageType".format( languageType ) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'rights':
                        sublocation = "rights of " + location
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '6v2x', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '9l5b', loadErrors )
                        copyrightType = None
                        for attrib,value in subelement.items():
                            if attrib=='type': copyrightType = value
                            else:
                                logging.warning( "1s3d Unprocessed {!r} attribute ({}) in {}".format( attrib, value, sublocation ) )
                                loadErrors.append( "Unprocessed {!r} attribute ({}) in {} (1s3d)".format( attrib, value, sublocation ) )
                                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                        if debuggingThisModule: print( "copyrightType", copyrightType )
                        if BibleOrgSysGlobals.debugFlag:
                            assert copyrightType in (None,'x-copyright','x-license','x-license-url','x-BY-SA','x-BY','x-comments-to')
                        if BibleOrgSysGlobals.verbosityLevel > 2:
                            print( "    Rights{} are/were {!r}".format( " ({})".format(copyrightType) if copyrightType else '', subelement.text ) )
                        self.suppliedMetadata['OSIS']['Rights'] = subelement.text
                        if copyrightType: self.suppliedMetadata['OSIS']['CopyrightType'] = copyrightType
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'relation':
                        sublocation = "relation of " + location
                        BibleOrgSysGlobals.checkXMLNoText( subelement, sublocation, 'g4h2', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, 'd2fd', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, 's2fy', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, 'gh53', loadErrors )
                    else:
                        logging.error( "7h5g Unprocessed {!r} sub-element ({}) in {}".format( subelement.tag, subelement.text, location) )
                        loadErrors.append( "Unprocessed {!r} sub-element ({}) in {} (7h5g)".format( subelement.tag, subelement.text, location) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                #if element.find('date') is not None: self.date = element.find('date').text
                #if element.find('title') is not None: self.title = element.find('title').text
                self.workNames.append( osisWorkName )
            elif element.tag == OSISXMLBible.OSISNameSpace+'workPrefix':
                location = "workPrefix of " + headerlocation
                BibleOrgSysGlobals.checkXMLNoText( header, location, 'f5h8', loadErrors )
                BibleOrgSysGlobals.checkXMLNoAttributes( header, location, '6g4f', loadErrors )
                BibleOrgSysGlobals.checkXMLNoTail( header, location, 'f2g7', loadErrors )
                # Process the attributes first
                workPrefixPath = workPrefixWork = None
                for attrib,value in element.items():
                    if attrib=='path':
                        workPrefixPath = value
                        assert workPrefixPath.startswith( '//' )
                        assert '/@' in workPrefixPath
                        workPrefixPath = workPrefixPath[2:] # Remove two leading slashes
                        assert workPrefixPath in ( 'w/@lemma', 'w/@morph' ) # All we've discovered so far
                    elif attrib=='osisWork':
                        workPrefixWork = value
                        assert workPrefixWork in self.workNames
                    else:
                        logging.warning( "7yh4 Unprocessed {} attribute ({}) in workPrefix element".format( attrib, value ) )
                        loadErrors.append( "Unprocessed {} attribute ({}) in workPrefix element (7yh4)".format( attrib, value ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                assert workPrefixPath and workPrefixWork
                # Now process the subelements
                for subelement in element:
                    if subelement.tag == OSISXMLBible.OSISNameSpace+'revisionDesc':
                        sublocation = "revisionDesc of " + location
                        BibleOrgSysGlobals.checkXMLNoText( subelement, sublocation, 'c3t5', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, '2w3e', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, 'm5o0', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, 'z2f8', loadErrors )
                        #self.something = subelement.text
                        for attrib,value in subelement.items():
                            logging.warning( "3h6r Unprocessed {!r} attribute ({}) in {} subelement of workPrefix element".format( attrib, value, subelement.tag ) )
                            loadErrors.append( "Unprocessed {!r} attribute ({}) in {} subelement of workPrefix element (3h6r)".format( attrib, value, subelement.tag ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    else:
                        logging.error( "8h4g Unprocessed {!r} sub-element ({}) in workPrefix element".format( subelement.tag, subelement.text ) )
                        loadErrors.append( "Unprocessed {!r} sub-element ({}) in workPrefix element (8h4g)".format( subelement.tag, subelement.text ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                # NOTE: These subelements are not currently saved
                self.workPrefixes[workPrefixPath] = workPrefixWork
            else:
                logging.error( "Expected to load {!r} but got {!r}".format( OSISXMLBible.OSISNameSpace+'work', element.tag ) )
                loadErrors.append( "Expected to load {!r} but got {!r}".format( OSISXMLBible.OSISNameSpace+'work', element.tag ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
            if element.tail is not None and element.tail.strip():
                logging.error( "Unexpected {!r} tail data after {} element in header element".format( element.tail, element.tag ) )
                loadErrors.append( "Unexpected {!r} tail data after {} element in header element".format( element.tail, element.tag ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
        if not self.workNames:
            logging.warning( "OSIS header doesn't specify any work records." )
            loadErrors.append( "OSIS header doesn't specify any work records." )
            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
    # end of OSISXMLBible.validateHeader


    def validateFrontMatter( self, frontMatter, loadErrors ):
        """
        Check/validate the given OSIS front matter (div) record.
        """
        if BibleOrgSysGlobals.verbosityLevel > 3: print( _("Loading {}OSIS front matter…").format( self.abbreviation+' ' if self.abbreviation else '' ) )
        frontMatterLocation = "frontMatter"
        BibleOrgSysGlobals.checkXMLNoText( frontMatter, frontMatterLocation, 'c3a2', loadErrors )
        BibleOrgSysGlobals.checkXMLNoTail( frontMatter, frontMatterLocation, 'm7s9', loadErrors )
        # Process the attributes first
        for attrib,value in frontMatter.items():
            if attrib=='type':
                pass # We've already processed this
            else:
                logging.warning( "98h4 Unprocessed {} attribute ({}) in {}".format( attrib, value, frontMatterLocation ) )
                loadErrors.append( "Unprocessed {} attribute ({}) in {} (98h4)".format( attrib, value, frontMatterLocation ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt

        self.thisBook = BibleBook( self, 'FRT' )
        self.thisBook.objectNameString = 'OSIS XML Bible Book object'
        self.thisBook.objectTypeString = 'OSIS'
        self.haveBook = True

        chapterMilestone = verseMilestone = 'FrontMatter'
        for element in frontMatter:
            if element.tag == OSISXMLBible.OSISNameSpace+'titlePage':
                location = "titlePage of " + frontMatterLocation
                BibleOrgSysGlobals.checkXMLNoText( element, location, 'k9l3', loadErrors )
                BibleOrgSysGlobals.checkXMLNoAttributes( element, location, '1w34', loadErrors )
                BibleOrgSysGlobals.checkXMLNoTail( element, location, 'a3s4', loadErrors )
                # Process the attributes first
                for attrib,value in element.items():
                    if attrib=='type':
                        if BibleOrgSysGlobals.debugFlag: assert value == 'front' # We've already processed this in the calling routine
                    else:
                        logging.warning( "3f5d Unprocessed {} attribute ({}) in {}".format( attrib, value, location ) )
                        loadErrors.append( "Unprocessed {} attribute ({}) in {} (3f5d)".format( attrib, value, location ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt

                # Now process the subelements
                for subelement in element:
                    BibleOrgSysGlobals.checkXMLNoSubelements( subelement, location, 'dv61', loadErrors )
                    if subelement.tag == OSISXMLBible.OSISNameSpace+'p':
                        sublocation = "p of " + location
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, '5ygg', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '8j54', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, 'h3x5', loadErrors )
                        p = element.text
                    else:
                        logging.error( "1dc5 Unprocessed {!r} sub-element ({}) in {}".format( subelement.tag, subelement.text, location ) )
                        loadErrors.append( "Unprocessed {!r} sub-element ({}) in {} (1dc5)".format( subelement.tag, subelement.text, location ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
            elif element.tag == OSISXMLBible.OSISNameSpace+'div':
                location = "div of " + frontMatterLocation
                BibleOrgSysGlobals.checkXMLNoText( element, location, 'b3f4', loadErrors )
                BibleOrgSysGlobals.checkXMLNoTail( element, location, 'd3s2', loadErrors )
                # Process the attributes first
                divType = None
                for attrib,value in element.items():
                    if attrib=='type': divType = value
                    else:
                        logging.warning( "7h4g Unprocessed {} attribute ({}) in {}".format( attrib, value, location ) )
                        loadErrors.append( "Unprocessed {} attribute ({}) in {} (7h4g)".format( attrib, value, location ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                if BibleOrgSysGlobals.debugFlag: assert divType == 'x-license'

                # Now process the subelements
                for subelement in element:
                    if subelement.tag == OSISXMLBible.OSISNameSpace+'title':
                        sublocation = "title of " + location
                        self.validateTitle( subelement, sublocation, chapterMilestone, verseMilestone, loadErrors )
                        #if 0:
                            #BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, '48j6', loadErrors )
                            #BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, 'l0l0', loadErrors )
                            #BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, 'k8j8', loadErrors )
                            #date = subelement.text
                            #logging.warning( "sdh3 Not handled yet", subelement.text )
                            #loadErrors.append( "sdh3 Not handled yet", subelement.text )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'p':
                        sublocation = "p of " + location
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, '2de5', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, 'd4d4', loadErrors )
                        p = element.text
                        # Now process the subelements
                        for sub2element in subelement:
                            BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sublocation, 's3s3', loadErrors )
                            if sub2element.tag == OSISXMLBible.OSISNameSpace+'a':
                                sub2location = "a of " + sublocation
                                BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2location, 'j4h3', loadErrors )
                                aText, aTail = element.text, element.tail
                                # Process the attributes
                                href = None
                                for attrib,value in sub2element.items():
                                    if attrib=='href': href = value
                                    else:
                                        logging.warning( "7g4a Unprocessed {} attribute ({}) in {}".format( attrib, value, sub2location ) )
                                        loadErrors.append( "Unprocessed {} attribute ({}) in {} (7g4a)".format( attrib, value, sub2location ) )
                                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                            else:
                                logging.error( "3d45 Unprocessed {!r} sub2-element ({}) in {}".format( sub2element.tag, sub2element.text, sublocation ) )
                                loadErrors.append( "Unprocessed {!r} sub2-element ({}) in {} (3d45)".format( sub2element.tag, sub2element.text, sublocation ) )
                                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    else:
                        logging.error( "034f Unprocessed {!r} sub-element ({}) in {}".format( subelement.tag, subelement.text, location ) )
                        loadErrors.append( "Unprocessed {!r} sub-element ({}) in {} (034f)".format( subelement.tag, subelement.text, location ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
            else:
                logging.error( "2sd4 Unprocessed {!r} sub-element ({}) in {}".format( element.tag, element.text, frontMatterLocation ) )
                loadErrors.append( "Unprocessed {!r} sub-element ({}) in {} (2sd4)".format( element.tag, element.text, frontMatterLocation ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
            if element.tail is not None and element.tail.strip():
                logging.error( "Unexpected {!r} tail data after {} element in header element".format( element.tail, element.tag ) )
                loadErrors.append( "Unexpected {!r} tail data after {} element in header element".format( element.tail, element.tag ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt

        self.stashBook( self.thisBook )
        self.haveBook = True
    # end of OSISXMLBible.validateFrontMatter


    def validateAndExtractMainDiv( self, div, loadErrors ):
        """
        Check/validate and extract data from the given OSIS div record.
            This may be a book group, or directly into a book
        """

        if BibleOrgSysGlobals.verbosityLevel > 3: print( _("Loading {}OSIS main div…").format( self.abbreviation+' ' if self.abbreviation else '' ) )
        self.haveEIDs = False
        self.haveBook = False


        def validateGroupTitle( element, locationDescription ):
            """
            Check/validate and process a OSIS Bible paragraph, including all subfields.
            """
            location = "validateGroupTitle: " + locationDescription
            BibleOrgSysGlobals.checkXMLNoTail( element, location, 'c4vd', loadErrors )
            titleText = element.text
            titleType = titleSubType = titleShort = titleLevel = None
            for attrib,value in element.items():
                #if attrib=='type':
                    #titleType = value
                #elif attrib=='subType':
                    #titleSubType = value
                if attrib=='short':
                    titleShort = value
                #elif attrib=='level':
                    #titleLevel = value # Not used anywhere yet :(
                else:
                    logging.warning( "vdv3 Unprocessed {!r} attribute ({}) in {} at {}".format( attrib, value, location, verseMilestone ) )
                    loadErrors.append( "Unprocessed {!r} attribute ({}) in {} at {} (vdv3)".format( attrib, value, location, verseMilestone ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
            #if titleSubType: assert titleSubType == 'x-preverse'
            BibleOrgSysGlobals.checkXMLNoSubelements( element, location+" at book group", 'js21', loadErrors )
            if BibleOrgSysGlobals.debugFlag: assert titleText
            if titleText:
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "    Got book group title", repr(titleText) )
                self.divisions[titleText] = []
        # end of OSISXMLBible.validateGroupTitle


        # Process the div attributes first
        mainDivType = mainDivOsisID = mainDivCanonical = None
        BBB = USFMAbbreviation = USFMNumber = ''
        for attrib,value in div.items():
            if attrib=='type':
                mainDivType = value
                if mainDivOsisID and BibleOrgSysGlobals.verbosityLevel > 2: print( _("Loading {} {}…").format( mainDivOsisID, mainDivType ) )
            elif attrib=='osisID':
                mainDivOsisID = value
                if mainDivType and BibleOrgSysGlobals.verbosityLevel > 2: print( _("Loading {} {}…").format( mainDivOsisID, mainDivType ) )
            elif attrib=='canonical':
                mainDivCanonical = value
            else:
                logging.warning( "93f5 Unprocessed {!r} attribute ({}) in main div element".format( attrib, value ) )
                loadErrors.append( "Unprocessed {!r} attribute ({}) in main div element (93f5)".format( attrib, value ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
        if not mainDivType or not (mainDivOsisID or mainDivCanonical):
            logging.warning( "Incomplete mainDivType {!r} and mainDivOsisID {!r} attributes in main div element".format( mainDivType, mainDivOsisID ) )
            loadErrors.append( "Incomplete mainDivType {!r} and mainDivOsisID {!r} attributes in main div element".format( mainDivType, mainDivOsisID ) )
            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt

        if mainDivType == 'bookGroup': # this is all the books lumped in together into one big div
            if BibleOrgSysGlobals.debugFlag: assert mainDivCanonical == 'true'
            # We have to set BBB when we get a chapter reference
            if BibleOrgSysGlobals.verbosityLevel > 2: print( _("  Loading a book group…") )
            self.haveBook = False
            for element in div:
                if element.tag == OSISXMLBible.OSISNameSpace+'title':
                    location = "title of {} div".format( mainDivType )
                    validateGroupTitle( element, location )
                elif element.tag == OSISXMLBible.OSISNameSpace+'div': # Assume it's a book
                    self.validateAndExtractBookDiv( element, loadErrors )
                else:
                    logging.error( "hfs6 Unprocessed {!r} sub-element ({}) in {} div".format( element.tag, element.text, mainDivType ) )
                    loadErrors.append( "Unprocessed {!r} sub-element ({}) in {} div (hfs6)".format( element.tag, element.text, mainDivType ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
        elif mainDivType == 'book': # this is a single book (not in a group)
            self.validateAndExtractBookDiv( div, loadErrors )
        else:
            logging.critical( "What kind of OSIS book div is this? {} {} {}".format( repr(mainDivType), repr(mainDivOsisID), repr(mainDivCanonical) ) )
            loadErrors.append( "What kind of OSIS book div is this? {} {} {}".format( repr(mainDivType), repr(mainDivOsisID), repr(mainDivCanonical) ) )
            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
    # end of OSISXMLBible.validateAndExtractMainDiv


    def validateAndExtractBookDiv( self, div, loadErrors ):
        """
        Check/validate and extract data from the given OSIS div record.
            This should be a book division.
        """

        def validateChapterElement( element, chapterMilestone, verseMilestone, locationDescription ):
            """
            Check/validate and process a chapter element.

            Returns one of the following:
                OSIS chapter ID string for a startMilestone
                '' for an endMilestone
                'chapter' + chapter number string for a container
            """
            nonlocal BBB, USFMAbbreviation, USFMNumber #, bookResults, USFMResults
            #print( "validateChapterElement at {} with {} and {}".format( locationDescription, chapterMilestone, verseMilestone ) )
            location = "validateChapterElement: " + locationDescription
            BibleOrgSysGlobals.checkXMLNoText( element, location+" at "+verseMilestone, 's2a8', loadErrors )
            BibleOrgSysGlobals.checkXMLNoTail( element, location+" at "+verseMilestone, 'j9k7', loadErrors )
            OSISChapterID = sID = eID = chapterN = canonical = chapterTitle = None
            for attrib,value in element.items():
                if attrib=='osisID': OSISChapterID = value
                elif attrib=='sID': sID = value
                elif attrib=='eID': eID = value
                elif attrib=='n': chapterN = value
                elif attrib=='canonical': canonical = value
                elif attrib=='chapterTitle': chapterTitle = value
                else:
                    displayTag = element.tag[len(self.OSISNameSpace):] if element.tag.startswith(self.OSISNameSpace) else element.tag
                    logging.warning( _("5f3d Unprocessed {!r} attribute ({}) in {} subelement of {}").format( attrib, value, displayTag, location ) )
                    loadErrors.append( _("Unprocessed {!r} attribute ({}) in {} subelement of {} (5f3d)").format( attrib, value, displayTag, location ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
            if sID and not OSISChapterID:
                logging.error( _("Missing chapter ID attribute in {}: {}").format( location, element.items() ) )
                loadErrors.append( _("Missing chapter ID attribute in {}: {}").format( location, element.items() ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt

            if len(element)==0 and ( sID or eID or OSISChapterID): # it's a chapter milestone (no sub-elements)
                # No verse milestone should be open because verses can't cross chapter boundaries
                if verseMilestone:
                    if self.haveEIDs:
                        logging.error( _("Unexpected {} chapter milestone while {} verse milestone is still open at {}").format( element.items(), verseMilestone, location ) )
                        loadErrors.append( _("Unexpected {} chapter milestone while {} verse milestone is still open at {}").format( element.items(), verseMilestone, location ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt

                if OSISChapterID and sID and not eID:
                    chapterMilestone = sID
                    #if not chapterMilestone.count('.')==1: logging.warning( "{} chapter milestone seems wrong format for {} at {}".format( chapterMilestone, OSISChapterID, location ) )
                elif eID and not OSISChapterID and not sID:
                    if chapterMilestone and eID==chapterMilestone: chapterMilestone = ''
                    else:
                        logging.error( _("Chapter milestone {} end didn't match {} at {}").format( eID, chapterMilestone, location ) )
                        loadErrors.append( _("Chapter milestone {} end didn't match {} at {}").format( eID, chapterMilestone, location ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                elif OSISChapterID and not (sID or eID): # some OSIS formats use this
                    if BibleOrgSysGlobals.debugFlag: assert canonical == 'true'
                    chapterMilestone = OSISChapterID
                else:
                    print( 'SQUIGGLE', repr(OSISChapterID), repr(sID), repr(eID) )
                    logging.error( _("Unrecognized chapter milestone in {}: {} at {}").format( location, element.items(), location ) )
                    loadErrors.append( _("Unrecognized chapter milestone in {}: {} at {}").format( location, element.items(), location ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt

                if chapterMilestone: # Have a chapter milestone like Jas.1
                    if not OSISChapterID:
                        logging.error( "Missing chapter ID for {} at {}".format( chapterMilestone, location ) )
                        loadErrors.append( "Missing chapter ID for {} at {}".format( chapterMilestone, location ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    else:
                        if not OSISChapterID.count('.')==1:
                            logging.error( "{} chapter ID seems wrong format for {} at {}".format( OSISChapterID, chapterMilestone, location ) )
                            loadErrors.append( "{} chapter ID seems wrong format for {} at {}".format( OSISChapterID, chapterMilestone, location ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                        bits = OSISChapterID.split( '.' )
                        if BibleOrgSysGlobals.debugFlag: assert len(bits) == 2
                        cmBBB = None
                        try:
                            cmBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromOSISAbbreviation( bits[0] )
                        except KeyError:
                            logging.critical( _("{!r} is not a valid OSIS book identifier in chapter milestone {}").format( bits[0], OSISChapterID ) )
                            loadErrors.append( _("{!r} is not a valid OSIS book identifier in chapter milestone {}").format( bits[0], OSISChapterID ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                        if cmBBB and isinstance( cmBBB, list ): # There must be multiple alternatives for BBB from the OSIS one
                            if BibleOrgSysGlobals.verbosityLevel > 2: print( "Multiple alternatives for OSIS {!r}: {} (Choosing the first one)".format( mainDivOsisID, cmBBB ) )
                            cmBBB = cmBBB[0]
                        if cmBBB and cmBBB != BBB: # We've started on a new book
                            #if BBB and ( len(bookResults)>20 or len(USFMResults)>20 ): # Save the previous book
                            print( "here MAGIC", cmBBB, BBB, repr(chapterMilestone), len(self.thisBook._rawLines) )
                            if BBB and len(self.thisBook._rawLines) > 5: # Save the previous book
                                #print( verseMilestone )
                                if BibleOrgSysGlobals.verbosityLevel > 2: print( "Saving previous {}{} book into results…".format( self.abbreviation+' ' if self.abbreviation else '', BBB ) )
                                #print( mainDivOsisID, "results", BBB, bookResults[:10], "…" )
                                # Remove the last titles
                                #lastBookResult = bookResults.pop()
                                #if lastBookResult[0]!='sectionTitle':
                                    #lastBookResult = None
                                #lastUSFMResult = USFMResults.pop()
                                #if lastUSFMResult[0]!='s':
                                    #lastUSFMResult = None
                                lastLineTuple = self.thisBook._rawLines.pop()
                                if BibleOrgSysGlobals.debugFlag: assert len(lastLineTuple) == 2
                                if lastLineTuple[0] != 's':
                                    self.thisBook._rawLines.append( lastLineTuple ) # No good -- put it back
                                    lastLineTuple = None
                                #if bookResults: self.bkData[BBB] = bookResults
                                #if USFMResults: self.USFMBooks[BBB] = USFMResults
                                self.stashBook( self.thisBook )
                                #bookResults, USFMResults = [], []
                                #if lastBookResult:
                                    #lastBookResultList = list( lastBookResult )
                                    #lastBookResultList[0] = 'mainTitle'
                                    #adjBookResult = tuple( lastBookResultList )
                                    ##print( lastBookResultList )
                                #if lastUSFMResult:
                                    #lastUSFMResultList = list( lastUSFMResult )
                                    #lastUSFMResultList[0] = 'mt1'
                                    ##print( lastUSFMResultList )
                                    #adjSFMResult = tuple( lastUSFMResultList )
                                if lastLineTuple:
                                    self.thisBook.addLine( 'id', (USFMAbbreviation if USFMAbbreviation else mainDivOsisID).upper() + " converted to USFM from OSIS by {} V{}".format( PROGRAM_NAME, PROGRAM_VERSION ) )
                                    self.thisBook.addLine( 'h', USFMAbbreviation if USFMAbbreviation else mainDivOsisID )
                                    self.thisBook.addLine( 'mt1', lastLineTuple[1] ) # Change from s to mt1
                                chapterMilestone = verseMilestone = ''
                                foundH = False
                            BBB = cmBBB[0] if isinstance( cmBBB, list) else cmBBB # It can be a list like: ['EZR', 'EZN']
                            #print( "23f4 BBB is", BBB )
                            USFMAbbreviation = BibleOrgSysGlobals.loadedBibleBooksCodes.getUSFMAbbreviation( BBB )
                            USFMNumber = BibleOrgSysGlobals.loadedBibleBooksCodes.getUSFMNumber( BBB )
                            if BibleOrgSysGlobals.verbosityLevel > 2: print( _("  It seems we have {}…").format( BBB ) )
                            self.thisBook = BibleBook( self, BBB )
                            self.thisBook.objectNameString = 'OSIS XML Bible Book object'
                            self.thisBook.objectTypeString = 'OSIS'
                            self.haveBook = True
                        self.thisBook.addLine( 'c', bits[1] )

                #print( "validateChapterElement returning milestone:", chapterMilestone )
                return chapterMilestone

            else: # not a milestone -- it's a chapter container
                bits = OSISChapterID.split('.')
                if BibleOrgSysGlobals.debugFlag: assert len(bits)==2 and bits[1].isdigit()
                #print( "validateChapterElement returning data:", 'chapterContainer.' + OSISChapterID )
                return 'chapterContainer.' + OSISChapterID
        # end of OSISXMLBible.validateChapterElement


        def validateSigned( element, locationDescription, verseMilestone ):
            """
            """
            location = "validateSigned: " + locationDescription
            BibleOrgSysGlobals.checkXMLNoAttributes( element, location+" at "+verseMilestone, '9i6h', loadErrors )
            BibleOrgSysGlobals.checkXMLNoSubelements( element, location+" at "+verseMilestone, 'vd62', loadErrors )
            BibleOrgSysGlobals.checkXMLNoTail( element, location+" at "+verseMilestone, 'fc3v3', loadErrors )
            signedName = subelement.text
            if BibleOrgSysGlobals.debugFlag and subelement.tail: halt
            self.thisBook.appendToLastLine( '\\sg {}\\sg*'.format( clean(signedName) ) )
        # end of validateSigned


        def validateLB( element, locationDescription, verseMilestone ):
            """
            """
            location = "validateLB: " + locationDescription
            BibleOrgSysGlobals.checkXMLNoText( element, location+" at "+verseMilestone, 'cf4g', loadErrors )
            BibleOrgSysGlobals.checkXMLNoAttributes( element, location+" at "+verseMilestone, '5t3x', loadErrors )
            BibleOrgSysGlobals.checkXMLNoSubelements( element, location+" at "+verseMilestone, 'sn52', loadErrors )
            BibleOrgSysGlobals.checkXMLNoTail( element, location+" at "+verseMilestone, '3c5f', loadErrors )
            self.thisBook.addLine( 'm', '' )
        # end of OSISXMLBible.validateLB


        def validateLG( element, locationDescription, verseMilestone ):
            """
            Check/validate and process a OSIS Bible lg field, including all subfields.

            Returns a possibly updated verseMilestone.
            """
            #print( "validateLG at {} at {}".format( location, verseMilestone ) )
            location = "validateLG: " + locationDescription
            BibleOrgSysGlobals.checkXMLNoText( element, location+" at "+verseMilestone, '3f6v', loadErrors )
            BibleOrgSysGlobals.checkXMLNoAttributes( element, location+" at "+verseMilestone, 'vdj4', loadErrors )
            for subelement in element:
                if subelement.tag == OSISXMLBible.OSISNameSpace+'l':
                    sublocation = "validateLG l of " + locationDescription
                    BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation+" at "+verseMilestone, '3d56g', loadErrors )
                    lgLevel = None
                    for attrib,value in subelement.items():
                        if attrib=='level':
                            lgLevel = value
                        else:
                            logging.warning( "2xc4 Unprocessed {!r} attribute ({}) in {} sub-element of {} at {}".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                            loadErrors.append( "Unprocessed {!r} attribute ({}) in {} sub-element of {} at {} (2xc4)".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    if not lgLevel: # This is probably an OSIS formatting error
                        #print( "LG lgLevel problem", verseMilestone, repr(element.text), subelement.items() )
                        logging.warning( "No level attribute specified in {} at {}".format( sublocation, verseMilestone ) )
                        loadErrors.append( "No level attribute specified in {} at {}".format( sublocation, verseMilestone ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                        lgLevel = '1' # Dunno what we have here ???
                    if BibleOrgSysGlobals.debugFlag: assert lgLevel in ('1','2','3','4')
                    self.thisBook.addLine( 'q'+lgLevel, '' if subelement.text is None else clean(subelement.text) )
                    for sub2element in subelement:
                        if sub2element.tag == OSISXMLBible.OSISNameSpace+'verse':
                            sub2location = "validateLG: verse of l of " + locationDescription
                            verseMilestone = self.validateVerseElement( sub2element, verseMilestone, chapterMilestone, sub2location, loadErrors )
                        elif sub2element.tag == OSISXMLBible.OSISNameSpace+'note':
                            sub2location = "validateLG: note of l of " + locationDescription
                            self.validateCrossReferenceOrFootnote( sub2element, sub2location, verseMilestone, loadErrors )
                        elif sub2element.tag == OSISXMLBible.OSISNameSpace+'divineName':
                            sub2location = "validateLG: divineName of l of " + locationDescription
                            self.validateDivineName( sub2element, sub2location, verseMilestone, loadErrors )
                        elif sub2element.tag == OSISXMLBible.OSISNameSpace+'hi':
                            sub2location = "validateLG: hi of l of " + locationDescription
                            self.validateHighlight( sub2element, sub2location, verseMilestone, loadErrors ) # Also handles the tail
                        elif sub2element.tag == OSISXMLBible.OSISNameSpace+'w':
                            sub2location = "validateLG: w of l of " + locationDescription
                            self.validateAndLoadWord( sub2element, sub2location, verseMilestone, loadErrors )
                            #print( "wordStuff", repr(wordStuff), sublocation, verseMilestone, BibleOrgSysGlobals.elementStr(subelement) )
                            #if wordStuff: self.thisBook.appendToLastLine( wordStuff )
                        else:
                            logging.error( "4j12 Unprocessed {!r} sub2element ({}) in {} at {}".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                            loadErrors.append( "Unprocessed {!r} sub2element ({}) in {} at {} (4j12)".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'divineName':
                    sublocation = "validateLG divineName of " + locationDescription
                    self.validateDivineName( subelement, sublocation, verseMilestone, loadErrors )
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'verse':
                    sublocation = "validateLG verse of " + locationDescription
                    verseMilestone = self.validateVerseElement( subelement, verseMilestone, chapterMilestone, sublocation, loadErrors )
                else:
                    logging.error( "q2b6 Unprocessed {!r} sub-element ({}) in {} at {}".format( subelement.tag, subelement.text, location, verseMilestone ) )
                    loadErrors.append( "Unprocessed {!r} sub-element ({}) in {} at {} (q2b6)".format( subelement.tag, subelement.text, location, verseMilestone ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
            if element.tail: # and lgTail!='\n': # This is the main text of the verse (outside of the quotation indents)
                self.thisBook.addLine( 'm', clean(element.tail) )
            return verseMilestone
        # end of OSISXMLBible.validateLG


        def validateList( element, locationDescription, verseMilestone, level=None ):
            """
            Check/validate and process a OSIS Bible list field, including all subfields.

            Returns a possibly updated verseMilestone.
            """
            #print( "validateList for {} at {} at {}".format( self.name, locationDescription, verseMilestone ) )
            if level is None: level = 1
            location = "validateList: " + locationDescription

            BibleOrgSysGlobals.checkXMLNoText( element, location+" at "+verseMilestone, '2dx3', loadErrors )
            BibleOrgSysGlobals.checkXMLNoTail( element, location+" at "+verseMilestone, '2c5b', loadErrors )
            canonical = None
            for attrib,value in element.items():
                if attrib== 'canonical':
                    canonical = value
                    assert canonical == 'false'
                else:
                    logging.warning( "h2f5 Unprocessed {!r} attribute ({}) in {} element of {} at {}".format( attrib, value, element.tag, location, verseMilestone ) )
                    loadErrors.append( "Unprocessed {!r} attribute ({}) in {} element of {} at {} (h2f5)".format( attrib, value, element.tag, location, verseMilestone ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
            for subelement in element:
                if subelement.tag == OSISXMLBible.OSISNameSpace+'item':
                    sublocation = "item of " + location
                    itemText = subelement.text
                    #print( "itemText", repr(itemText) )
                    if chapterMilestone: marker = 'li' + str(level)
                    else: marker = 'io' + str(level) # No chapter so we're in the introduction
                    if itemText and itemText.strip(): self.thisBook.addLine( marker, clean(itemText) )
                    BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation+" at "+verseMilestone, 'xf52', loadErrors )
                    BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation+" at "+verseMilestone, 'ad36', loadErrors )
                    for sub2element in subelement:
                        if sub2element.tag == OSISXMLBible.OSISNameSpace+'verse':
                            sub2location = "verse of " + sublocation
                            verseMilestone = self.validateVerseElement( sub2element, verseMilestone, chapterMilestone, sub2location, loadErrors )
                            #verseTail = sub3element.tail
                            #print( "verseTail", repr(verseTail) )
                            #BibleOrgSysGlobals.checkXMLNoText( sub3element, sub3location+" at "+verseMilestone, 'cvf4', loadErrors )
                            #BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3location+" at "+verseMilestone, 'sdyg', loadErrors )
                            #osisID = verseSID = verseEID = verseN = None
                            #for attrib,value in sub3element.items():
                                #if attrib=='osisID':
                                    #osisID = value
                                #elif attrib=='sID':
                                    #verseSID = value
                                #elif attrib=='eID':
                                    #verseEID = value
                                #elif attrib=='n':
                                    #verseN = value
                                #else: logging.warning( "fghb Unprocessed {!r} attribute ({}) in {} sub3element of {} at {}".format( attrib, value, sub3element.tag, sub2location, verseMilestone ) )
                            #if osisID: assert verseSID and verseN and not verseEID
                            #elif verseEID: assert not verseSID and not verseN
                            #print( "verseStuff", repr(osisID), repr(verseSID), repr(verseN), repr(verseEID) )
                            ##self.thisBook.addLine( 'r~', referenceText+referenceTail )
                        elif sub2element.tag == OSISXMLBible.OSISNameSpace+'note':
                            sub2location = "note of " + sublocation
                            self.validateCrossReferenceOrFootnote( sub2element, sub2location, verseMilestone, loadErrors )
                        elif sub2element.tag == OSISXMLBible.OSISNameSpace+'hi':
                            sub2location = "hi of " + sublocation
                            self.validateHighlight( sub2element, sub2location, verseMilestone, loadErrors )
                        elif sub2element.tag == OSISXMLBible.OSISNameSpace+'list':
                            sub2location = "list of " + sublocation
                            verseMilestone = validateList( sub2element, sub2location, verseMilestone, level+1 )
                        else:
                            logging.error( "f153 Unprocessed {!r} sub3element ({}) in {} at {}".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                            loadErrors.append( "Unprocessed {!r} sub3element ({}) in {} at {} (f153)".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                else:
                    logging.error( "s154 Unprocessed {!r} subelement ({}) in {} at {}".format( subelement.tag, subelement.text, location, verseMilestone ) )
                    loadErrors.append( "Unprocessed {!r} subelement ({}) in {} at {} (s154)".format( subelement.tag, subelement.text, location, verseMilestone ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
            return verseMilestone

            ##print( 'list', divType, subDivType )
            #BibleOrgSysGlobals.checkXMLNoText( sub2element, sub2location+" at "+verseMilestone, '3x6g', loadErrors )
            #BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2location+" at "+verseMilestone, '8j4g' )
            #BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, sub2location+" at "+verseMilestone, '7tgf' )
            #for sub3element in sub2element:
                #if sub3element.tag == OSISXMLBible.OSISNameSpace+'item':
                    #sub3location = "item of " + sub2location
                    #BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3location+" at "+verseMilestone, '3d8n' )
                    #BibleOrgSysGlobals.checkXMLNoAttributes( sub3element, sub3location+" at "+verseMilestone, '4g7g' )
                    #item = sub3element.text
                    #if item and item.strip():
                        ##print( subDivType )
                        #if subDivType == 'outline':
                            #self.thisBook.addLine( 'io1', item.strip() )
                        #elif subDivType == 'section':
                            #self.thisBook.addLine( 'io1', item.strip() )
                        #elif BibleOrgSysGlobals.debugFlag: halt
                    #for sub4element in sub3element:
                        #if sub4element.tag == OSISXMLBible.OSISNameSpace+'list':
                            #sub4location = "list of " + sub3location
                            #BibleOrgSysGlobals.checkXMLNoText( sub4element, sub4location+" at "+verseMilestone, '5g3d' )
                            #BibleOrgSysGlobals.checkXMLNoTail( sub4element, sub4location+" at "+verseMilestone, '4w5x' )
                            #BibleOrgSysGlobals.checkXMLNoAttributes( sub4element, sub4location+" at "+verseMilestone, '3d45' )
                            #for sub5element in sub4element:
                                #if sub5element.tag == OSISXMLBible.OSISNameSpace+'item':
                                    #sub5location = "item of " + sub4location
                                    #BibleOrgSysGlobals.checkXMLNoTail( sub5element, sub5location+" at "+verseMilestone, '4c5t' )
                                    #BibleOrgSysGlobals.checkXMLNoAttributes( sub5element, sub5location+" at "+verseMilestone, '2sd1' )
                                    #BibleOrgSysGlobals.checkXMLNoSubelements( sub5element, sub5location+" at "+verseMilestone, '8j7n' )
                                    #subItem = sub5element.text
                                    #if subItem:
                                        #if subDivType == 'outline':
                                            #self.thisBook.addLine( 'io2', clean(subItem) )
                                        #elif subDivType == 'section':
                                            #self.thisBook.addLine( 'io2', clean(subItem) )
                                        #elif BibleOrgSysGlobals.debugFlag: print( subDivType ); halt
                                #else: logging.error( "3kt6 Unprocessed {!r} sub5element ({}) in {} at {}".format( sub5element.tag, sub5element.text, sub4location, verseMilestone ) )
                        #elif sub4element.tag == OSISXMLBible.OSISNameSpace+'verse':
                            #sub4location = "list of " + sub3location
                            #self.validateVerseElement( sub4element, verseMilestone, chapterMilestone, sub4location )
                        #else: logging.error( "2h4s Unprocessed {!r} sub4element ({}) in {} at {}".format( sub4element.tag, sub4element.text, sub3location, verseMilestone ) )
                #else: logging.error( "8k4j Unprocessed {!r} sub3element ({}) in {} at {}".format( sub3element.tag, sub3element.text, sub2location, verseMilestone ) )
        # end of OSISXMLBible.validateList


        def validateMilestone( subelement, location, verseMilestone ):
            """
            """
            sublocation = "milestone of " + location
            BibleOrgSysGlobals.checkXMLNoText( subelement, sublocation+" at "+verseMilestone, 'f9s5', loadErrors )
            BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, 'q9v5', loadErrors )
            milestoneType = milestoneMarker = milestoneSubtype = milestoneResp = None
            for attrib,value in subelement.items():
                if attrib=='type': milestoneType = value
                elif attrib=='marker': milestoneMarker = value
                elif attrib=='subType': milestoneSubtype = value
                elif attrib=='resp': milestoneResp = value
                else:
                    logging.warning( "8h6k Unprocessed {!r} attribute ({}) in {} at {}".format( attrib, value, sublocation, verseMilestone ) )
                    loadErrors.append( "Unprocessed {!r} attribute ({}) in {} at {} (8h6k)".format( attrib, value, sublocation, verseMilestone ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
            #print( "here bd63", repr(milestoneType) )
            if BibleOrgSysGlobals.debugFlag:
                assert milestoneType in ('x-p','x-extra-p','x-strongsMarkup')
                assert milestoneMarker in (None,'¶') # What are these?
                assert milestoneSubtype in (None,'x-added') # What are these?
            self.thisBook.addLine( 'p', '' )
            trailingText = subelement.tail
            if trailingText and trailingText.strip(): self.thisBook.appendToLastLine( clean(trailingText) )
            #return subelement.tail if subelement.tail else ''
        # end of validateMilestone


        def validateParagraph( element, locationDescription, verseMilestone ):
            """
            Check/validate and process a OSIS Bible paragraph, including all subfields.

            Returns a possibly updated verseMilestone.
            """
            nonlocal chapterMilestone
            #print( "validateParagraph at {} at {}".format( locationDescription, verseMilestone ) )
            location = "validateParagraph: " + locationDescription
            paragraphType = canonical = None
            for attrib,value in element.items():
                if attrib=='type':
                    paragraphType = value
                elif attrib=='canonical':
                    canonical = value
                    assert canonical in ('true','false')
                else:
                    logging.warning( "6g3f Unprocessed {!r} attribute ({}) in {} element of {} at {}".format( attrib, value, element.tag, location, verseMilestone ) )
                    loadErrors.append( "Unprocessed {!r} attribute ({}) in {} element of {} at {} (6g3f)".format( attrib, value, element.tag, location, verseMilestone ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
            paragraphCode = None
            if paragraphType:
                if BibleOrgSysGlobals.debugFlag:
                    assert paragraphType.startswith( 'x-')
                    if paragraphType not in  ('x-center','x-iex','x-mi','x-pc','x-ph','x-pm','x-pmr','x-qa','x-qc','x-qm','x-qr','x-sr'): print( paragraphType )
                    if debuggingThisModule:
                        assert paragraphType in ('x-center','x-iex','x-mi','x-pc','x-ph','x-pm','x-pmr','x-qa','x-qc','x-qm','x-qr','x-sr')
                paragraphCode = paragraphType[2:]
            justFinishedLG = False
            if not element.text: # A new paragraph starting
                pContents = None
            else: # A new paragraph in the middle of a verse, e.g., James 3:5b
                pContents = clean( element.text )
                #if pContents.isspace(): pContents = None # Ignore newlines and blank lines in the xml file
            if paragraphCode in USFM_BIBLE_PARAGRAPH_MARKERS:
                self.thisBook.addLine( paragraphCode, '' if pContents is None else pContents )
            elif chapterMilestone:
                self.thisBook.addLine( 'p', '' if pContents is None else pContents )
            else: # Must be in the introduction
                self.thisBook.addLine( 'ip', '' if pContents is None else pContents )
            for subelement in element:
                if subelement.tag == OSISXMLBible.OSISNameSpace+'chapter': # A chapter break within a paragraph (relatively rare)
                    sublocation = "validateParagraph: chapter of " + locationDescription
                    chapterMilestone = validateChapterElement( subelement, chapterMilestone, verseMilestone, sublocation )
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'verse':
                    sublocation = "validateParagraph: verse of " + locationDescription
                    if justFinishedLG: # Have a verse straight after a LG (without an intervening p)
                        self.thisBook.addLine( 'm', '' )
                        #print( "Added m" )
                    verseMilestone = self.validateVerseElement( subelement, verseMilestone, chapterMilestone, sublocation, loadErrors )
                    justFinishedLG = False
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'note':
                    sublocation = "validateParagraph: note of " + locationDescription
                    self.validateCrossReferenceOrFootnote( subelement, sublocation, verseMilestone, loadErrors )
                    justFinishedLG = False
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'lg':
                    sublocation = "validateParagraph: lg of " + locationDescription
                    verseMilestone = validateLG( subelement, sublocation, verseMilestone )
                    #if 0:
                        #BibleOrgSysGlobals.checkXMLNoText( subelement, sublocation+" at "+verseMilestone, '3ch6', loadErrors )
                        ##lgText = subelement.text
                        #lgTail = subelement.tail
                        #for attrib,value in subelement.items():
                            #if attrib=='type':
                                #halt
                            #elif attrib=='n':
                                #halt
                            #elif attrib=='osisRef':
                                #halt
                            #elif attrib=='osisID':
                                #halt
                            #else:
                                #logging.warning( "1s5g Unprocessed {!r} attribute ({}) in {} sub-element of {} at {}".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                                #loadErrors.append( "Unprocessed {!r} attribute ({}) in {} sub-element of {} at {} (1s5g)".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                        #for sub2element in subelement:
                            #if sub2element.tag == OSISXMLBible.OSISNameSpace+'l':
                                #sub2location = "l of " + sublocation
                                #BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2location+" at "+verseMilestone, '4vw3', loadErrors )
                                #lText = sub2element.text
                                #level3 = None
                                #for attrib,value in sub2element.items():
                                    #if attrib=='level':
                                        #level3 = value
                                    #else:
                                        #logging.warning( "9d3k Unprocessed {!r} attribute ({}) in {} sub-element of {} at {}".format( attrib, value, sub2element.tag, sub2location, verseMilestone ) )
                                        #loadErrors.append( "Unprocessed {!r} attribute ({}) in {} sub-element of {} at {} (9d3k)".format( attrib, value, sub2element.tag, sub2location, verseMilestone ) )
                                #if not level3:
                                    ##print( "level3 problem", verseMilestone, lText, sub2element.items() )
                                    #logging.warning( "validateParagraph: No level attribute specified in {} at {}".format( sub2location, verseMilestone ) )
                                    #loadErrors.append( "validateParagraph: No level attribute specified in {} at {}".format( sub2location, verseMilestone ) )
                                    #level3 = '1' # Dunno what we have here ???
                                #if BibleOrgSysGlobals.debugFlag: assert level3 in ('1','2','3')
                                #self.thisBook.addLine( 'q'+level3, lText )
                                #for sub3element in sub2element:
                                    #if sub3element.tag == OSISXMLBible.OSISNameSpace+'verse':
                                        #sub3location = "verse of " + sub2location
                                        #verseMilestone = validateVerseElement( sub3element, verseMilestone, chapterMilestone, sub3location )
                                    #elif sub3element.tag == OSISXMLBible.OSISNameSpace+'note':
                                        #sub3location = "note of " + sub2location
                                        #self.validateCrossReferenceOrFootnote( sub3element, sub3location, verseMilestone, loadErrors )
                                        #noteTail = sub3element.tail
                                        #if noteTail: # This is the main text of the verse (follows the inserted note)
                                            #bookResults.append( ('lverse+', noteTail) )
                                            #adjNoteTail = noteTail.replace('\n','') # XML line formatting is irrelevant to USFM
                                            #if adjNoteTail: USFMResults.append( ('v~',adjNoteTail) )
                                    #else:
                                        #logging.error( "32df Unprocessed {!r} sub3element ({}) in {} at {}".format( sub3element.tag, sub3element.text, sub2location, verseMilestone ) )
                                        #loadErrors.append( "Unprocessed {!r} sub3element ({}) in {} at {} (32df)".format( sub3element.tag, sub3element.text, sub2location, verseMilestone ) )
                            #else:
                                #logging.error( "5g1e Unprocessed {!r} sub2element ({}) in {} at {}".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                                #loadErrors.append( "Unprocessed {!r} sub2element ({}) in {} at {} (5g1e)".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                        #if lgTail and lgTail!='\n': # This is the main text of the verse (outside of the quotation indents)
                            #self.thisBook.addLine( 'm', lgTail )
                    justFinishedLG = True
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'reference':
                    sublocation = "validateParagraph: reference of " + locationDescription
                    BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, 'vbs4', loadErrors )
                    reference = subelement.text
                    theType = None
                    for attrib,value in subelement.items():
                        if attrib=='type':
                            theType = value
                        else:
                            logging.warning( "4f5f Unprocessed {!r} attribute ({}) in {} sub2-element of {} at {}".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                            loadErrors.append( "Unprocessed {!r} attribute ({}) in {} sub2-element of {} at {} (4f5f)".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    if theType:
                        if theType == 'x-bookName':
                            self.thisBook.appendToLastLine( '\\bk {}\\bk*'.format( clean(reference) ) )
                        elif BibleOrgSysGlobals.debugFlag: print( theType ); halt
                    pTail = subelement.tail
                    if pTail and pTail.strip(): # Just ignore XML spacing characters
                        self.thisBook.appendToLastLine( clean(pTail) )
                    justFinishedLG = False
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'hi':
                    sublocation = "validateParagraph: hi of " + locationDescription
                    self.validateHighlight( subelement, sublocation, verseMilestone, loadErrors ) # Also handles the tail
                    justFinishedLG = False
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'lb':
                    sublocation = "validateParagraph: lb of " + locationDescription
                    validateLB( subelement, sublocation, verseMilestone )
                    justFinishedLG = False
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'w':
                    sublocation = "validateParagraph: w of " + locationDescription
                    self.validateAndLoadWord( subelement, sublocation, verseMilestone, loadErrors )
                    #print( "wordStuff", repr(wordStuff), sublocation, verseMilestone, BibleOrgSysGlobals.elementStr(subelement) )
                    #if wordStuff: self.thisBook.appendToLastLine( wordStuff )
                    #BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation+" at "+verseMilestone, '3s5f', loadErrors )
                    #BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, 'f3v5', loadErrors )
                    #word, trailingPunctuation = subelement.text, subelement.tail
                    #if trailingPunctuation is None: trailingPunctuation = ''
                    #combined = word + trailingPunctuation
                    #self.thisBook.addLine( 'w~', combined )
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'signed':
                    sublocation = "validateParagraph: signed of " + locationDescription
                    validateSigned( subelement, sublocation, verseMilestone )
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'divineName':
                    sublocation = "validateParagraph: divineName of " + locationDescription
                    self.validateDivineName( subelement, sublocation, verseMilestone, loadErrors )
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'name':
                    sublocation = "validateParagraph: name of " + locationDescription
                    self.validateProperName( subelement, sublocation, verseMilestone, loadErrors )
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'seg':
                    sublocation = "validateParagraph: seg of " + locationDescription
                    self.validateAndLoadSEG( subelement, sublocation, verseMilestone, loadErrors )
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'transChange':
                    sublocation = "validateParagraph: transChange of " + locationDescription
                    self.validateTransChange( subelement, sublocation, verseMilestone, loadErrors )
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'foreign':
                    sublocation = "validateParagraph: foreign of reference of " + locationDescription
                    BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation+" at "+verseMilestone, 'kd02', loadErrors )
                    BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, 'kls2', loadErrors )
                    BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation+" at "+verseMilestone, 'ks10', loadErrors )
                    subreferenceText = subelement.text
                    self.thisBook.appendToLastLine( '\\tl {}\\tl*'.format( clean(subreferenceText) ) )
                else:
                    logging.error( "3kj6 Unprocessed {!r} sub-element ({}) in {} at {}".format( subelement.tag, subelement.text, location, verseMilestone ) )
                    loadErrors.append( "Unprocessed {!r} sub-element ({}) in {} at {} (3kj6)".format( subelement.tag, subelement.text, location, verseMilestone ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
            if element.tail and not element.tail.isspace(): # Just ignore XML spacing characters
                self.thisBook.appendToLastLine( clean(element.tail) )
            return verseMilestone
        # end of OSISXMLBible.validateParagraph


        def validateTable( element, locationDescription, verseMilestone ):
            """
            Check/validate and process a OSIS Bible table, including all subfields.

            Returns a possibly updated verseMilestone.
            """
            location = "validateTable: " + locationDescription
            self.thisBook.addLine( 'tr', ' ' )
            BibleOrgSysGlobals.checkXMLNoText( element, location+" at "+verseMilestone, 'kd20', loadErrors )
            BibleOrgSysGlobals.checkXMLNoAttributes( element, location+" at "+verseMilestone, 'kd21', loadErrors )
            BibleOrgSysGlobals.checkXMLNoSubelements( element, location+" at "+verseMilestone, 'ks20', loadErrors )
            BibleOrgSysGlobals.checkXMLNoTail( element, location+" at "+verseMilestone, 'so20', loadErrors )
            tableTail = clean(element.tail, loadErrors, location, verseMilestone )
            if tableTail: self.thisBook.appendToLastLine( tableTail )
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
            return verseMilestone
        # end of OSISXMLBible.validateTable



        # Main code for validateAndExtractBookDiv
        if BibleOrgSysGlobals.verbosityLevel > 3: print( _("Loading {}OSIS book div…").format( self.abbreviation+' ' if self.abbreviation else '' ) )
        self.haveEIDs = False
        self.haveBook = False

        # Process the div attributes first
        mainDivType = mainDivOsisID = mainDivCanonical = None
        BBB = USFMAbbreviation = USFMNumber = ''
        for attrib,value in div.items():
            if attrib=='type':
                mainDivType = value
                if mainDivOsisID and BibleOrgSysGlobals.verbosityLevel > 2: print( _("Loading {} {}…").format( mainDivOsisID, mainDivType ) )
            elif attrib=='osisID':
                mainDivOsisID = value
                if mainDivType and BibleOrgSysGlobals.verbosityLevel > 2: print( _("Loading {} {}…").format( mainDivOsisID, mainDivType ) )
            elif attrib=='canonical':
                mainDivCanonical = value
            else:
                logging.warning( "93f5 Unprocessed {!r} attribute ({}) in main div element".format( attrib, value ) )
                loadErrors.append( "Unprocessed {!r} attribute ({}) in main div element (93f5)".format( attrib, value ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
        if not mainDivType or not (mainDivOsisID or mainDivCanonical):
            logging.warning( "Incomplete mainDivType {!r} and mainDivOsisID {!r} attributes in main div element".format( mainDivType, mainDivOsisID ) )
            loadErrors.append( "Incomplete mainDivType {!r} and mainDivOsisID {!r} attributes in main div element".format( mainDivType, mainDivOsisID ) )
            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
        if mainDivType=='book':
            # This is a single book
            if len(mainDivOsisID)>3 and mainDivOsisID[-1] in ('1','2','3') and mainDivOsisID[-2]=='.': # Fix a bug in the Snowfall USFM to OSIS software
                logging.critical( "Fixing single-book bug in OSIS {!r} book ID".format( mainDivOsisID ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                mainDivOsisID = mainDivOsisID[:-2] # Change 1Kgs.1 to 1Kgs
            try:
                BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromOSISAbbreviation( mainDivOsisID )
            except KeyError:
                logging.critical( _("{!r} is not a valid OSIS book identifier in mainDiv").format( mainDivOsisID ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                for tryBBB in ( 'XXA', 'XXB', 'XXC', 'XXD', 'XXE' ):
                    if tryBBB not in self:
                        BBB = tryBBB; break
            if BBB:
                if isinstance( BBB, list ): # There must be multiple alternatives for BBB from the OSIS one
                    if BibleOrgSysGlobals.verbosityLevel > 2: print( "Multiple alternatives for OSIS {!r}: {} (Choosing the first one)".format( mainDivOsisID, BBB ) )
                    BBB = BBB[0]
                if BibleOrgSysGlobals.verbosityLevel > 2: print( _("  Loading {}{}…").format( self.abbreviation+' ' if self.abbreviation else '', BBB ) )
                USFMAbbreviation = BibleOrgSysGlobals.loadedBibleBooksCodes.getUSFMAbbreviation( BBB )
                USFMNumber = BibleOrgSysGlobals.loadedBibleBooksCodes.getUSFMNumber( BBB )
                self.thisBook = BibleBook( self, BBB )
                self.thisBook.objectNameString = 'OSIS XML Bible Book object'
                self.thisBook.objectTypeString = 'OSIS'
                self.haveBook = True
            self.thisBook.addLine( 'id', (USFMAbbreviation if USFMAbbreviation else mainDivOsisID).upper() + " converted to USFM from OSIS by {} V{}".format( PROGRAM_NAME, PROGRAM_VERSION ) )
            self.thisBook.addLine( 'h', USFMAbbreviation if USFMAbbreviation else mainDivOsisID )
        #elif mainDivType=='bookGroup':
            ## This is all the books lumped in together into one big div
            #if BibleOrgSysGlobals.debugFlag: assert mainDivCanonical == 'true'
            ## We have to set BBB when we get a chapter reference
            #if BibleOrgSysGlobals.verbosityLevel > 2: print( _("  Loading a book group…") )
            #self.haveBook = False
        else:
            logging.critical( "What kind of OSIS book div is this? {} {} {}".format( repr(mainDivType), repr(mainDivOsisID), repr(mainDivCanonical) ) )
            loadErrors.append( "What kind of OSIS book div is this? {} {} {}".format( repr(mainDivType), repr(mainDivOsisID), repr(mainDivCanonical) ) )
            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt

        chapterMilestone = verseMilestone = ''
        foundH = False
        for element in div:
########### Title -- could be a book title or (in some OSIS files) a section title (with no way to tell the difference)
#               or even worse still (in the Karen), an alternate chapter number
            if element.tag == OSISXMLBible.OSISNameSpace+'title':
                location = "title of {} div".format( mainDivType )
                self.validateTitle( element, location, chapterMilestone, verseMilestone, loadErrors )
########### Div (of the main div) -- most stuff would be expected to be inside a section div inside the book div
            elif element.tag == OSISXMLBible.OSISNameSpace+'div':
                location = "div of {} div".format( mainDivType )
                #if verseMilestone is None: print( location, chapterMilestone ); halt
                BibleOrgSysGlobals.checkXMLNoText( element, location+" at "+verseMilestone, '3f6h', loadErrors )
                BibleOrgSysGlobals.checkXMLNoTail( element, location+" at "+verseMilestone, '0j6h', loadErrors )
                # Process the attributes
                divType = divCanonical = divScope = osisID = None
                for attrib,value in element.items():
                    if attrib==OSISXMLBible.XMLNameSpace+'space':
                        divSpace = value
                    elif attrib=='type':
                        divType = value
                        location = value + ' ' + location
                    elif attrib=='canonical':
                        divCanonical = value
                        #assert divCanonical == 'false'
                    elif attrib=='scope': divScope = value
                    elif attrib=='osisID': osisID = value # Unused, e.g., "Rom.c" colophon div in OS KJV
                    else:
                        logging.warning( "2h56 Unprocessed {!r} attribute ({}) in {} at {}".format( attrib, value, location, verseMilestone ) )
                        loadErrors.append( "Unprocessed {!r} attribute ({}) in {} at {} (2h56)".format( attrib, value, location, verseMilestone ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning:
                            print( "Unprocessed {!r} attribute ({}) in {} at {} (2h56)".format( attrib, value, location, verseMilestone ) )
                            halt
                # Now process the subelements
                for subelement in element:
###                 ### chapter in div
                    if subelement.tag == OSISXMLBible.OSISNameSpace+'chapter':
                        sublocation = "chapter of " + location
                        chapterMilestone = validateChapterElement( subelement, chapterMilestone, verseMilestone, sublocation )
###                 ### verse in div
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'verse':
                        sublocation = "verse of " + location
                        verseMilestone = self.validateVerseElement( subelement, verseMilestone, chapterMilestone, sublocation, loadErrors )
###                 ### title in div
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'title':  # section heading
                        sublocation = "title of " + location
                        self.validateTitle( subelement, sublocation, chapterMilestone, verseMilestone, loadErrors )
                        #if 0:
                            #BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation+" at "+verseMilestone, '3d4f', loadErrors )
                            #sectionHeading = subelement.text
                            #titleType = None
                            #for attrib,value in subelement.items():
                                #if attrib=='type':
                                    #titleType = value
                                #else:
                                    #logging.warning( "4h2x Unprocessed {!r} attribute ({}) in {} at {}".format( attrib, value, sublocation, verseMilestone ) )
                                    #loadErrors.append( "Unprocessed {!r} attribute ({}) in {} at {} (4h2x)".format( attrib, value, sublocation, verseMilestone ) )
                            #if chapterMilestone:
                                #bookResults.append( ('title', titleType, sectionHeading) )
                                #USFMResults.append( ('s', sectionHeading) )
                            #else: # Must be in the introduction
                                #bookResults.append( ('title', titleType, sectionHeading) )
                                #USFMResults.append( ('is', sectionHeading) )
                            #for sub2element in subelement:
                                #if sub2element.tag == OSISXMLBible.OSISNameSpace+'title': # section reference(s)
                                    #sub2location = "title of " + sublocation
                                    #BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2location+" at "+verseMilestone, '3d5g', loadErrors )
                                    #sectionReference = sub2element.text
                                    #sectionReferenceType = None
                                    #for attrib,value in sub2element.items():
                                        #if attrib=='type':
                                            #sectionReferenceType = value
                                        #else:
                                            #logging.warning( "8h4d Unprocessed {!r} attribute ({}) in {} sub2element of {} at {}".format( attrib, value, sub2element.tag, sub2location, verseMilestone ) )
                                            #loadErrors.append( "Unprocessed {!r} attribute ({}) in {} sub2element of {} at {} (8h4d)".format( attrib, value, sub2element.tag, sub2location, verseMilestone ) )
                                    #if sectionReference:
                                        ##print( divType, self.subDivType, sectionReferenceType ); halt
                                        ##assert divType=='section' and self.subDivType in ('outline',) and sectionReferenceType=='parallel'
                                        #if BibleOrgSysGlobals.debugFlag: assert divType=='section' and sectionReferenceType=='parallel'
                                        #self.thisBook.addLine( 'sr', clean(sectionReference) )
                                    #for sub3element in sub2element:
                                        #if sub3element.tag == OSISXMLBible.OSISNameSpace+'reference':
                                            #sub3location = "reference of " + sub2location
                                            #BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3location+" at "+verseMilestone, '3d3d', loadErrors )
                                            #referenceText = sub3element.text
                                            #referenceTail = sub3element.tail
                                            #referenceOsisRef = None
                                            #for attrib,value in sub3element.items():
                                                #if attrib=='osisRef':
                                                    #referenceOsisRef = value
                                                #else:
                                                    #logging.warning( "7k43 Unprocessed {!r} attribute ({}) in {} sub3element of {} at {}".format( attrib, value, sub3element.tag, sub2location, verseMilestone ) )
                                                    #loadErrors.append( "Unprocessed {!r} attribute ({}) in {} sub3element of {} at {} (7k43)".format( attrib, value, sub3element.tag, sub2location, verseMilestone ) )
                                            ##print( referenceText, referenceOsisRef, referenceTail )
                                            #bookResults.append( ('reference',referenceText) )
                                            #USFMResults.append( ('r+',referenceText+referenceTail) )
                                        #else:
                                            #logging.error( "46g2 Unprocessed {!r} sub3element ({}) in {} at {}".format( sub3element.tag, sub3element.text, sub2location, verseMilestone ) )
                                            #loadErrors.append( "Unprocessed {!r} sub3element ({}) in {} at {} (46g2)".format( sub3element.tag, sub3element.text, sub2location, verseMilestone ) )
###                 ### p in div
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'p': # Most scripture data occurs in here
                        sublocation = "p of " + location
                        verseMilestone = validateParagraph( subelement, sublocation, verseMilestone )
###                 ### list in div
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'list':
                        sublocation = "list of " + location
                        verseMilestone = validateList( subelement, sublocation, verseMilestone )
###                 ### lg in div
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'lg':
                        sublocation = "lg of " + location
                        verseMilestone = validateLG( subelement, sublocation, verseMilestone )
###                 ### div in div
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'div':
                        sublocation = "div of " + location
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation+" at "+verseMilestone, '2c5bv', loadErrors )
                        subDivType = subDivScope = subDivSpace = canonical = None
                        for attrib,value in subelement.items():
                            if attrib=='type':
                                subDivType = value
                                sublocation = value + ' ' + sublocation
                            elif attrib=='scope':
                                subDivScope = value # Should be an OSIS verse range
                            elif attrib=='canonical':
                                canonical = value
                                assert canonical in ('true','false')
                            elif attrib==self.XMLNameSpace+"space":
                                subDivSpace = value
                                if BibleOrgSysGlobals.debugFlag: assert subDivSpace == 'preserve'
                            else:
                                logging.warning( "84kf Unprocessed {!r} attribute ({}) in {} at {}".format( attrib, value, sublocation, verseMilestone ) )
                                loadErrors.append( "Unprocessed {!r} attribute ({}) in {} at {} (84kf)".format( attrib, value, sublocation, verseMilestone ) )
                                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                        #print( "self.subDivType", self.subDivType )
                        for sub2element in subelement:
                            if sub2element.tag == OSISXMLBible.OSISNameSpace+'title':
                                sub2location = "title of " + sublocation
                                self.validateTitle( sub2element, sub2location, chapterMilestone, verseMilestone, loadErrors )
                                #if 0:
                                    #BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2location+" at "+verseMilestone, '4v5g', loadErrors )
                                    #titleText = clean( sub2element.text, loadErrors, sub2location, verseMilestone )
                                    #titleType = titleSubType = titleCanonicalFlag = None
                                    #for attrib,value in sub2element.items():
                                        #if attrib=='type': titleType = value
                                        #elif attrib=='subType': titleSubType = value
                                        #elif attrib=='canonical': titleCanonicalFlag = value
                                        #else:
                                            #logging.warning( "1d4r Unprocessed {!r} attribute ({}) in {} sub2element of {} at {}".format( attrib, value, sub2element.tag, sub2location, verseMilestone ) )
                                            #loadErrors.append( "Unprocessed {!r} attribute ({}) in {} sub2element of {} at {} (1d4r)".format( attrib, value, sub2element.tag, sub2location, verseMilestone ) )
                                    #if titleType: print( "titleType", titleType )
                                    #if BibleOrgSysGlobals.debugFlag:
                                        #if titleType: assert titleType in ('psalm','parallel','sub')
                                        #if titleSubType: assert titleSubType == 'x-preverse'
                                    #if titleText:
                                        ##print( divType, subDivType )
                                        #if titleCanonicalFlag=='true' and titleType=='psalm':
                                            #self.thisBook.addLine( 'd', titleText )
                                        #elif divType=='introduction' and subDivType in ('section','outline'):
                                            #self.thisBook.addLine( 'iot' if subDivType == 'outline' else 'is', titleText )
                                        #elif divType=='majorSection' and subDivType=='section':
                                            #self.thisBook.addLine( 'xxxx1' if subDivType == 'outline' else 's1', titleText )
                                        #elif divType=='majorSection' and subDivType=='subSection':
                                            #self.thisBook.addLine( 'xxxx1' if subDivType == 'outline' else 'ms1', titleText )
                                        #elif divType=='section' and subDivType=='subSection':
                                            #self.thisBook.addLine( 'xxxx3' if subDivType == 'outline' else 's', titleText )
                                        #elif divType=='section' and subDivType=='outline':
                                            #self.thisBook.addLine( 'iot', titleText )
                                        #else:
                                            #print( "What title?", divType, subDivType, repr(titleText), titleType, titleSubType, titleCanonicalFlag, verseMilestone )
                                            #if BibleOrgSysGlobals.debugFlag: halt
                                    #for sub3element in sub2element:
                                        #if sub3element.tag == OSISXMLBible.OSISNameSpace+'reference':
                                            #sub3location = "reference of " + sub2location
                                            #BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3location+" at "+verseMilestone, 'k6l3', loadErrors )
                                            #referenceText = clean( sub3element.text, loadErrors, sub3location, verseMilestone )
                                            #referenceTail = clean( sub3element.tail, loadErrors, sub3location, verseMilestone )
                                            #referenceOsisRef = None
                                            #for attrib,value in sub3element.items():
                                                #if attrib=='osisRef':
                                                    #referenceOsisRef = value
                                                #else:
                                                    #logging.warning( "nm46 Unprocessed {!r} attribute ({}) in {} sub3element of {} at {}".format( attrib, value, sub3element.tag, sub2location, verseMilestone ) )
                                                    #loadErrors.append( "Unprocessed {!r} attribute ({}) in {} sub3element of {} at {} (nm46)".format( attrib, value, sub3element.tag, sub2location, verseMilestone ) )
                                            #logging.error( "Unused {!r} reference field at {}".format( referenceText, sublocation+" at "+verseMilestone ) )
                                            #loadErrors.append( "Unused {!r} reference field at {}".format( referenceText, sublocation+" at "+verseMilestone ) )
                                            #if BibleOrgSysGlobals.debugFlag:
                                                #print( "What's this?", referenceText, referenceOsisRef, referenceTail )
                                                #if debuggingThisModule: halt
                                        #elif sub3element.tag == OSISXMLBible.OSISNameSpace+'note':
                                            #sub3location = "note of " + sub2location
                                            #self.validateCrossReferenceOrFootnote( sub3element, sub3location, verseMilestone, loadErrors )
                                        #elif sub3element.tag == OSISXMLBible.OSISNameSpace+'hi':
                                            #sub3location = "hi of " + sub2location
                                            #self.validateHighlight( sub3element, sub3location, verseMilestone, loadErrors ) # Also handles the tail
                                        #else:
                                            #logging.error( "m4g5 Unprocessed {!r} sub3element ({}) in {} at {}".format( sub3element.tag, sub3element.text, sub2location, verseMilestone ) )
                                            #loadErrors.append( "Unprocessed {!r} sub3element ({}) in {} at {} (m4g5)".format( sub3element.tag, sub3element.text, sub2location, verseMilestone ) )
                            elif sub2element.tag == OSISXMLBible.OSISNameSpace+'p':
                                sub2location = "p of " + sublocation
                                verseMilestone = validateParagraph( sub2element, sub2location, verseMilestone )
                            elif sub2element.tag == OSISXMLBible.OSISNameSpace+'lg':
                                sub2location = "lg of " + sublocation
                                verseMilestone = validateLG( sub2element, sub2location, verseMilestone )
                            elif sub2element.tag == OSISXMLBible.OSISNameSpace+'list':
                                sub2location = "list of " + sublocation
                                verseMilestone = validateList( sub2element, sub2location, verseMilestone )
                            elif sub2element.tag == OSISXMLBible.OSISNameSpace+'chapter':
                                sub2location = "chapter of " + sublocation
                                chapterMilestone = validateChapterElement( sub2element, chapterMilestone, verseMilestone, sub2location )
                            elif sub2element.tag == OSISXMLBible.OSISNameSpace+'verse':
                                sub2location = "verse of " + sublocation
                                verseMilestone = self.validateVerseElement( sub2element, verseMilestone, chapterMilestone, sub2location, loadErrors )
                            elif sub2element.tag == OSISXMLBible.OSISNameSpace+'hi':
                                sub2location = "hi of " + sublocation
                                self.validateHighlight( sub2element, sub2location, verseMilestone, loadErrors )
                            elif sub2element.tag == OSISXMLBible.OSISNameSpace+'lb':
                                sub2location = "lb of " + sublocation
                                validateLB( sub2element, sub2location, verseMilestone )
                            else:
                                logging.error( "14k5 Unprocessed {!r} sub2element ({}) in {} at {}".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                                loadErrors.append( "Unprocessed {!r} sub2element ({}) in {} at {} (14k5)".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
###                 ### lb in div
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'lb':
                        sublocation = "lb of " + location
                        validateLB( subelement, sublocation, verseMilestone )
###                 ### closer in div
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'closer':
                        sublocation = "closer of " + location
                        clsText = clean(subelement.text, loadErrors, sublocation, verseMilestone )
                        clsTail = clean(subelement.tail, loadErrors, sublocation, verseMilestone )
                        BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation+" at "+verseMilestone, 'js29', loadErrors )
                        self.thisBook.appendToLastLine( f'\\cls {clsText}' )
                        for sub2element in subelement:
                            if sub2element.tag == OSISXMLBible.OSISNameSpace+'p':
                                sub2location = "p of " + sublocation
                                verseMilestone = validateParagraph( sub2element, sub2location, verseMilestone )
                            else:
                                logging.error( "dc63 Unprocessed {!r} sub2element ({}) in {} at {}".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                                loadErrors.append( "Unprocessed {!r} sub2element ({}) in {} at {} (dc63)".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                        self.thisBook.appendToLastLine( f'\\cls*{clsTail if clsTail else ""}' )
###                 ### table in div
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'table': # not actually written yet! XXXXXXX ……
                        sublocation = 'table of ' + location
                        verseMilestone = validateTable( subelement, sublocation, verseMilestone )
###                 ### w in colophon div
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'w':
                        sublocation = 'w of ' + location
                        self.validateAndLoadWord( subelement, sublocation, verseMilestone, loadErrors )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'transChange':
                        sublocation = 'transChange of ' + location
                        self.validateTransChange( subelement, sublocation, verseMilestone, loadErrors ) # Also handles the tail
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'milestone':
                        sublocation = 'milestone of ' + location
                        validateMilestone( subelement, sublocation, verseMilestone )
                    else:
                        logging.error( "3f67 Unprocessed {!r} sub-element ({}) in {} at {}".format( subelement.tag, subelement.text, location, verseMilestone ) )
                        loadErrors.append( "Unprocessed {!r} sub-element ({}) in {} at {} (3f67)".format( subelement.tag, subelement.text, location, verseMilestone ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
########### P
            elif element.tag == OSISXMLBible.OSISNameSpace+'p':
                location = "p of {} div".format( mainDivType )
                verseMilestone = validateParagraph( element, location, verseMilestone )
########### Q
            elif element.tag == OSISXMLBible.OSISNameSpace+'q':
                location = "q of {} div".format( mainDivType )
                qText = element.text
                qTail = element.tail
                # Process the attributes
                sID = eID = level = marker = None
                for attrib,value in element.items():
                    if attrib=='sID': sID = value
                    elif attrib=='eID': eID = value
                    elif attrib=='level': level = value
                    elif attrib=='marker':
                        marker = value
                        if BibleOrgSysGlobals.debugFlag: assert len(marker) == 1
                    else:
                        logging.warning( "6j33 Unprocessed {!r} attribute ({}) in {} at {}".format( attrib, value, location, verseMilestone ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                # Now process the subelements
                for subelement in element:
                    if subelement.tag == OSISXMLBible.OSISNameSpace+'verse':
                        sublocation = "verse of " + location
                        verseMilestone = self.validateVerseElement( subelement, verseMilestone, chapterMilestone, sublocation, loadErrors )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'transChange':
                        sublocation = "transChange of " + location
                        self.validateTransChange( subelement, sublocation, verseMilestone, loadErrors ) # Also handles the tail
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'note':
                        sublocation = "note of " + location
                        self.validateCrossReferenceOrFootnote( subelement, sublocation, verseMilestone, loadErrors )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'w':
                        sublocation = "w of " + location
                        self.validateAndLoadWord( subelement, sublocation, verseMilestone, loadErrors )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'p':
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation+" at "+verseMilestone, '8h4g', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, '2k3m', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation+" at "+verseMilestone, '2s7z', loadErrors )
                        p = element.text
                        if p == '¶':
                            #bookResults.append( ('paragraph', None) )
                            #bookResults.append( ('p', None) )
                            self.thisBook.addLine( 'p', '' )

                        else:
                            # print( "p = {!r}".format( element.text ) ); halt
                            #bookResults.append( ('paragraph', p) )
                            #bookResults.append( ('p', p) )
                            self.thisBook.addLine( 'p', p )
                    else:
                        logging.error( "95k3 Unprocessed {!r} sub-element ({}) in {} at {}".format( subelement.tag, subelement.text, location, verseMilestone ) )
                        loadErrors.append( "Unprocessed {!r} sub-element ({}) in {} at {} (95k3)".format( subelement.tag, subelement.text, location, verseMilestone ) )
                        if BibleOrgSysGlobals.debugFlag: print( subelement.tag ); halt
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
########### Chapter
            elif element.tag == OSISXMLBible.OSISNameSpace+'chapter' or (not BibleOrgSysGlobals.strictCheckingFlag and element.tag=='chapter'):
                location = "chapter of {} div".format( mainDivType )
                chapterMilestone = validateChapterElement( element, chapterMilestone, verseMilestone, location )
                #print( "BBB is", BBB )
                if chapterMilestone and mainDivType=='bookGroup':
                    #print( "cm", chapterMilestone )
                    OSISBookID = chapterMilestone.split('.')[0]
                    try:
                        newBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromOSISAbbreviation( OSISBookID )
                    except KeyError:
                        logging.critical( _("{!r} is not a valid OSIS book identifier").format( OSISBookID ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    if newBBB and isinstance( newBBB, list ): # There must be multiple alternatives for BBB from the OSIS one
                        if BibleOrgSysGlobals.verbosityLevel > 2: print( "Multiple alternatives for OSIS {!r}: {} (Choosing the first one)".format( mainDivOsisID, newBBB ) )
                        newBBB = newBBB[0]
                    if newBBB != BBB:
                        BBB = newBBB
                        USFMAbbreviation = BibleOrgSysGlobals.loadedBibleBooksCodes.getUSFMAbbreviation( BBB )
                        USFMNumber = BibleOrgSysGlobals.loadedBibleBooksCodes.getUSFMNumber( BBB )
                        if BibleOrgSysGlobals.verbosityLevel > 1: print( _("  Loading {}{}…").format( self.abbreviation+' ' if self.abbreviation else '', BBB ) )
                if chapterMilestone.startswith('chapterContainer.'): # it must have been a container -- process the subelements
                    OSISChapterID = chapterMilestone[17:] # Remove the 'chapterContainer.' prefix
                    chapterBits = OSISChapterID.split( '.' )
                    if BibleOrgSysGlobals.debugFlag: assert len(chapterBits) == 2
                    if BibleOrgSysGlobals.debugFlag: assert chapterBits[1].isdigit()
                    self.thisBook.addLine( 'c', chapterBits[1] )
                    #sentence = ""
                    #self.thisBook.addLine( 'v~', '' ) # Start our line
                    for subelement in element:
                        if subelement.tag == OSISXMLBible.OSISNameSpace+'p': # Most scripture data occurs in here
                            #if sentence: self.thisBook.appendToLastLine( sentence ); sentence = ""
                            sublocation = 'p of ' + location
                            verseMilestone = validateParagraph( subelement, sublocation, verseMilestone )
                        elif subelement.tag == OSISXMLBible.OSISNameSpace+'title':  # section heading
                            #if sentence: self.thisBook.appendToLastLine( sentence ); sentence = ''
                            sublocation = 'title of ' + location
                            self.validateTitle( subelement, sublocation, chapterMilestone, verseMilestone, loadErrors )
                        elif subelement.tag == OSISXMLBible.OSISNameSpace+'w':
                            self.validateAndLoadWord( subelement, location, verseMilestone, loadErrors )
                        elif subelement.tag == OSISXMLBible.OSISNameSpace+'transChange':
                            self.validateTransChange( subelement, location, verseMilestone, loadErrors )
                        elif subelement.tag == OSISXMLBible.OSISNameSpace+'divineName':
                            self.validateDivineName( subelement, location, verseMilestone, loadErrors )
                        elif subelement.tag == OSISXMLBible.OSISNameSpace+'milestone':
                            #if sentence: self.thisBook.appendToLastLine( sentence ); sentence = ''
                            validateMilestone( subelement, location, verseMilestone )
                        elif subelement.tag == OSISXMLBible.OSISNameSpace+'q':
                            sublocation = 'q of ' + location
                            #words = ""
                            #if subelement.text: words += subelement.text
                            trailingPunctuation = subelement.tail if subelement.tail else ''
                            # Process the attributes
                            qWho = qMarker = None
                            for attrib,value in subelement.items():
                                if attrib=='who': qWho = value
                                elif attrib=='marker': qMarker = value
                                else:
                                    logging.warning( "zq1k Unprocessed {!r} attribute ({}) in {} at {}".format( attrib, value, sublocation, verseMilestone ) )
                                    loadErrors.append( "Unprocessed {!r} attribute ({}) in {} at {} (zq1k)".format( attrib, value, sublocation, verseMilestone ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                            #print( 'who', repr(qWho), 'marker', repr(qMarker) )
                            for sub2element in subelement:
                                if sub2element.tag == OSISXMLBible.OSISNameSpace+'w':
                                    self.validateAndLoadWord( sub2element, sublocation, verseMilestone, loadErrors )
                                elif sub2element.tag == OSISXMLBible.OSISNameSpace+'transChange':
                                    self.validateTransChange( sub2element, sublocation, verseMilestone, loadErrors )
                                elif sub2element.tag == OSISXMLBible.OSISNameSpace+'divineName':
                                    self.validateDivineName( sub2element, sublocation, verseMilestone, loadErrors )
                                elif sub2element.tag == OSISXMLBible.OSISNameSpace+'milestone':
                                    #sentence += words
                                    #if sentence: self.thisBook.appendToLastLine( sentence ); sentence = ""
                                    validateMilestone( sub2element, sublocation, verseMilestone )
                                elif sub2element.tag == OSISXMLBible.OSISNameSpace+'verse':
                                    #sentence += words
                                    #if sentence: self.thisBook.appendToLastLine( sentence ); sentence = ""
                                    sub2location = "verse of " + sublocation
                                    verseMilestone = self.validateVerseElement( sub2element, verseMilestone, chapterMilestone, sub2location, loadErrors )
                                elif sub2element.tag == OSISXMLBible.OSISNameSpace+'note':
                                    #sentence += words
                                    #if sentence: self.thisBook.appendToLastLine( sentence ); sentence = ""
                                    sub2location = "note of " + sublocation
                                    self.validateCrossReferenceOrFootnote( sub2element, sub2location, verseMilestone, loadErrors )
                                else:
                                    logging.error( "d33s Unprocessed {!r} sub-element ({}) in {} at {}".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                                    loadErrors.append( "Unprocessed {!r} sub-element ({}) in {} at {} (d33s)".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                            if 0 and qWho=="Jesus": sentence += "\\wj {}\\wj*{}".format( words, trailingPunctuation )
                            else:
                                logging.info( "qWho of {} unused".format( repr(qWho) ) )
                                #sentence += words + trailingPunctuation
                            self.thisBook.addLine( 'q1', '' )
                        elif subelement.tag == OSISXMLBible.OSISNameSpace+'note':
                            #if sentence: self.thisBook.appendToLastLine( sentence ); sentence = ""
                            sublocation = "note of " + location
                            self.validateCrossReferenceOrFootnote( subelement, sublocation, verseMilestone, loadErrors )
                        elif subelement.tag == OSISXMLBible.OSISNameSpace+'inscription':
                            #inscription = ""
                            sublocation = "inscription of " + location
                            self.thisBook.appendToLastLine( '\\sc ' )
                            BibleOrgSysGlobals.checkXMLNoText( subelement, sublocation+" at "+verseMilestone, 'r9s5', loadErrors )
                            BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation+" at "+verseMilestone, 'r9v5', loadErrors )
                            for sub2element in subelement:
                                if sub2element.tag == OSISXMLBible.OSISNameSpace+'w':
                                    self.validateAndLoadWord( sub2element, sublocation, verseMilestone, loadErrors )
                                else:
                                    logging.error( "4k3s Unprocessed {!r} sub-element ({}) in {} at {}".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                                    loadErrors.append( "Unprocessed {!r} sub-element ({}) in {} at {} (4k3s)".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                            self.thisBook.appendToLastLine( "\\sc*{}".format( clean(subelement.tail) ) )
                            #print( "Here 3c52", repr(sentence) )
                        elif subelement.tag == OSISXMLBible.OSISNameSpace+'verse' or (not BibleOrgSysGlobals.strictCheckingFlag and subelement.tag=='verse'):
                            #print( "here cx35", repr(sentence) )
                            #if sentence: self.thisBook.appendToLastLine( sentence ); sentence = ""
                            sublocation = "verse of " + location
                            verseMilestone = self.validateVerseElement( subelement, verseMilestone, chapterMilestone, sublocation, loadErrors )
                            #print( 'vM', verseMilestone ); halt
                            if verseMilestone and verseMilestone.startswith('verseContainer.'): # it must have been a container -- process the subelements
                                #print( "Yikes!" ) # Why??????????????
                                self.thisBook.addLine( 'v', verseMilestone[15:]+' ' ) # Remove the 'verseContainer.' prefix
                                for sub2element in subelement:
                                    if sub2element.tag == OSISXMLBible.OSISNameSpace+'w':
                                        sub2location = "w of " + sublocation
                                        self.validateAndLoadWord( sub2element, sub2location, verseMilestone, loadErrors )
                                        #BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2location+" at "+verseMilestone, '2k3c', loadErrors )
                                        #word = sub2element.text
                                        #if BibleOrgSysGlobals.debugFlag: assert word # That should be the actual word
                                        ## Process the attributes
                                        #lemma = morph = n = None
                                        #for attrib,value in sub2element.items():
                                            ##print( "Attribute w1 {}={!r}".format( attrib, value ) )
                                            #if attrib=='lemma': lemma = value # e.g., '7679'
                                            #elif attrib=='morph': morph = value
                                            #elif attrib=='n': n = value # e.g. '1.1'
                                            #else:
                                                #logging.warning( "2h54 Unprocessed {!r} attribute ({}) in {} at {}".format( attrib, value, sub2location, verseMilestone ) )
                                                #loadErrors.append( "Unprocessed {!r} attribute ({}) in {} at {} (2h54)".format( attrib, value, sub2location, verseMilestone ) )
                                                #if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                        ##print( "wlm", word, lemma, morph )
                                        #self.thisBook.appendToLastLine( "{} [{}]".format( word,lemma) )
                                        ## Now process the subelements
                                        #segText = segTail = segType = None
                                        #for sub3element in sub2element:
                                            #if sub3element.tag == OSISXMLBible.OSISNameSpace+'seg':
                                                #sub3location = "seg of " + sub2location
                                                #BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3location+" at "+verseMilestone, '43gx', loadErrors )
                                                #segText, segTail = sub3element.text, sub3element.tail # XXXxxxxxxxxxxxxxx unused …
                                                ## Process the attributes
                                                #segType = None
                                                #for attrib,value in sub3element.items():
                                                    #if attrib=='type': segType = value
                                                    #else:
                                                        #logging.warning( "963k Unprocessed {!r} attribute ({}) in {} at {}".format( attrib, value, sub3location, verseMilestone ) )
                                                        #loadErrors.append( "Unprocessed {!r} attribute ({}) in {} at {} (963k)".format( attrib, value, sub3location, verseMilestone ) )
                                                        #if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                        ##print( "segTTT", segText, segTail, segType )
                                    elif sub2element.tag == OSISXMLBible.OSISNameSpace+'seg':
                                        sub2location = "seg of " + sublocation
                                        self.validateAndLoadSEG( sub2element, sub2location, verseMilestone, loadErrors )
                                        #BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2location+" at "+verseMilestone, '9s8v', loadErrors )
                                        #BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2location+" at "+verseMilestone, '93dr', loadErrors )
                                        #seg = sub2element.text
                                        #if BibleOrgSysGlobals.debugFlag: assert seg # That should be the actual segment character
                                        ## Process the attributes first
                                        #for attrib,value in sub2element.items():
                                            #if attrib=='type':
                                                #segType = value
                                            #else:
                                                #logging.warning( "5jj2 Unprocessed {!r} attribute ({}) in {} at {}".format( attrib, value, sub2location, verseMilestone ) )
                                                #loadErrors.append( "Unprocessed {!r} attribute ({}) in {} at {} (5jj2)".format( attrib, value, sub2location, verseMilestone ) )
                                        #self.thisBook.addLine( 'segment', "{} [{}]".format( seg,segType) )
                                    elif sub2element.tag == OSISXMLBible.OSISNameSpace+'note':
                                        sub2location = "note of " + sublocation
                                        self.validateCrossReferenceOrFootnote( sub2element, sub2location, verseMilestone, loadErrors )
                                        #if 0:
                                            #noteTail = sub2element.tail
                                            #if noteTail: # This is the main text of the verse (follows the inserted note)
                                                #self.thisBook.appendToLastLine( clean(noteTail) )
                                            ## Now process the subelements
                                            #for sub3element in sub2element:
                                                #if sub3element.tag == OSISXMLBible.OSISNameSpace+'catchWord':
                                                    #sub3location = "catchword of " + sub2location
                                                    #BibleOrgSysGlobals.checkXMLNoAttributes( sub3element, sub3location+" at "+verseMilestone, '3d2a', loadErrors )
                                                    #BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3location+" at "+verseMilestone, '0o9i', loadErrors )
                                                    #BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3location+" at "+verseMilestone, '9k8j', loadErrors )
                                                    #catchWord = sub3element.text
                                                #elif sub3element.tag == OSISXMLBible.OSISNameSpace+'rdg':
                                                    #sub3location = "rdg of " + sub2location
                                                    #self.validateRDG( sub3element, sub3location, verseMilestone, loadErrors ) # Also handles the tail
                                                    ##if 0:
                                                        ##BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3location+" at "+verseMilestone, '8h7g', loadErrors )
                                                        ##rdg = sub3element.text
                                                        ### Process the attributes
                                                        ##rdgType = None
                                                        ##for attrib,value in sub3element.items():
                                                            ##if attrib=='type': rdgType = value
                                                            ##else:
                                                                ##logging.warning( "3hgh Unprocessed {!r} attribute ({}) in {} at {}".format( attrib, value, sub3location, verseMilestone ) )
                                                                ##loadErrors.append( "Unprocessed {!r} attribute ({}) in {} at {} (3hgh)".format( attrib, value, sub3location, verseMilestone ) )
                                                        ### Now process the subelements
                                                        ##for sub4element in sub3element:
                                                            ##if sub4element.tag == OSISXMLBible.OSISNameSpace+'w':
                                                                ##sub4location = "w of " + sub3location
                                                                ##BibleOrgSysGlobals.checkXMLNoTail( sub4element, sub4location+" at "+verseMilestone, '6g5d', loadErrors )
                                                                ##BibleOrgSysGlobals.checkXMLNoSubelements( sub4element, sub4location+" at "+verseMilestone, '5r4d', loadErrors )
                                                                ##word = sub4element.text
                                                                ### Process the attributes
                                                                ##lemma = None
                                                                ##for attrib,value in sub4element.items():
                                                                    ##if attrib=='lemma': lemma = value
                                                                    ##else:
                                                                        ##logging.warning( "85kd Unprocessed {!r} attribute ({}) in {} at {}".format( attrib, value, sub4location, verseMilestone ) )
                                                                        ##loadErrors.append( "Unprocessed {!r} attribute ({}) in {} at {} (85kd)".format( attrib, value, sub4location, verseMilestone ) )
                                                            ##elif sub4element.tag == OSISXMLBible.OSISNameSpace+'seg':
                                                                ##sub4location = "seg of " + sub3location
                                                                ##BibleOrgSysGlobals.checkXMLNoTail( sub4element, sub4location+" at "+verseMilestone, '5r4q', loadErrors )
                                                                ##BibleOrgSysGlobals.checkXMLNoSubelements( sub4element, sub4location+" at "+verseMilestone, '4s3a', loadErrors )
                                                                ##word = sub4element.text
                                                                ### Process the attributes
                                                                ##segType = None
                                                                ##for attrib,value in sub4element.items():
                                                                    ##if attrib=='type': segType = value
                                                                    ##else:
                                                                        ##logging.warning( "9r5j Unprocessed {!r} attribute ({}) in {} at {}".format( attrib, value, sub4location, verseMilestone ) )
                                                                        ##loadErrors.append( "Unprocessed {!r} attribute ({}) in {} at {} (9r5j)".format( attrib, value, sub4location, verseMilestone ) )
                                                            ##else:
                                                                ##logging.error( "7k3s Unprocessed {!r} sub-element ({}) in {} at {}".format( sub4element.tag, sub4element.text, sub3location, verseMilestone ) )
                                                                ##loadErrors.append( "Unprocessed {!r} sub-element ({}) in {} at {} (7k3s)".format( sub4element.tag, sub4element.text, sub3location, verseMilestone ) )
                                                                ##if BibleOrgSysGlobals.debugFlag: halt
                                                #else:
                                                    #logging.error( "9y5g Unprocessed {!r} sub-element ({}) in {} at {}".format( sub3element.tag, sub3element.text, sub2location, verseMilestone ) )
                                                    #loadErrors.append( "Unprocessed {!r} sub-element ({}) in {} at {} (9y5g)".format( sub3element.tag, sub3element.text, sub2location, verseMilestone ) )
                                                    #if BibleOrgSysGlobals.debugFlag: halt
                                    else:
                                        logging.error( "05kq Unprocessed {!r} sub-element {} in {} at {}".format( sub2element.tag, repr(sub2element.text), sublocation, verseMilestone ) )
                                        loadErrors.append( "Unprocessed {!r} sub-element {} in {} at {} (05kq)".format( sub2element.tag, repr(sub2element.text), sublocation, verseMilestone ) )
                                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                            elif verseMilestone and verseMilestone.startswith('verseContents#'): # it must have been a container -- process the string
                                #print( "verseContents", verseMilestone )
                                bits = verseMilestone.split( '#', 2 )
                                if BibleOrgSysGlobals.debugFlag: assert len(bits) == 3
                                if BibleOrgSysGlobals.debugFlag: assert bits[0] == 'verseContents'
                                if BibleOrgSysGlobals.debugFlag: assert bits[1].isdigit()
                                if BibleOrgSysGlobals.debugFlag: assert bits[2]
                                thisData = bits[1]
                                if bits[2].strip(): thisData += ' ' + bits[2].replace('\n','')
                                #assert bits[2].strip()
                                self.thisBook.addLine( 'v', thisData )
                                #print( USFMResults[-4:] )
                                #print( 'CHOCOLATE', self.thisBook._rawLines[-4:] )
                        else:
                            logging.error( "4s9j Unprocessed {!r} sub-element {} in {} at {}".format( subelement.tag, repr(subelement.text), location, verseMilestone ) )
                            loadErrors.append( "Unprocessed {!r} sub-element {} in {} at {} (4s9j)".format( subelement.tag, repr(subelement.text), location, verseMilestone ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
########### Verse
            elif element.tag == OSISXMLBible.OSISNameSpace+'verse': # Some OSIS Bibles have verse milestones directly in a bookgroup div
                location = "verse of {} div".format( mainDivType )
                verseMilestone = self.validateVerseElement( element, verseMilestone, chapterMilestone, location, loadErrors )
########### Lg
            elif element.tag == OSISXMLBible.OSISNameSpace+'lg':
                location = "lg of {} div".format( mainDivType )
                verseMilestone = validateLG( element, location, verseMilestone )
########### TransChange
            elif element.tag == OSISXMLBible.OSISNameSpace+'transChange':
                location = "transChange of {} div".format( mainDivType )
                self.validateTransChange( element, location, verseMilestone, loadErrors )
########### Note
            elif element.tag == OSISXMLBible.OSISNameSpace+'note':
                location = "note of {} div".format( mainDivType )
                self.validateCrossReferenceOrFootnote( element, location, verseMilestone, loadErrors )
########### LB
            elif element.tag == OSISXMLBible.OSISNameSpace+'lb':
                location = "lb of {} div".format( mainDivType )
                validateLB( element, location, verseMilestone )
########### List
            elif element.tag == OSISXMLBible.OSISNameSpace+'list':
                location = "list of {} div".format( mainDivType )
                verseMilestone = validateList( element, location, verseMilestone )
########### Table
            elif element.tag == OSISXMLBible.OSISNameSpace+'table':
                location = "table of {} div".format( mainDivType )
                verseMilestone = validateTable( element, location, verseMilestone )
########### W
            elif element.tag == OSISXMLBible.OSISNameSpace+'w':
                location = "w of {} div".format( mainDivType )
                self.validateAndLoadWord( element, location, verseMilestone, loadErrors )
########### Left-overs!
            else:
                logging.critical( "5ks1 Unprocessed {!r} sub-element ({}) in {} div at {}".format( element.tag, element.text, mainDivType, verseMilestone ) )
                loadErrors.append( "Unprocessed {!r} sub-element ({}) in {} div at {} (5ks1)".format( element.tag, element.text, mainDivType, verseMilestone ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
            #if element.tail is not None and element.tail.strip(): logging.error( "Unexpected left-over {!r} tail data after {} element in {} div at {}".format( element.tail, element.tag, mainDivType, verseMilestone ) )

        #print( "Done Validating", BBB, mainDivOsisID, mainDivType )
        #print( "bookResults", bookResults )
        if BBB:
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Saving {}{} book into results…".format( self.abbreviation+' ' if self.abbreviation else '', BBB ) )
            #print( mainDivOsisID, "results", BBB, bookResults[:10], "…" )
            #if bookResults: self.bkData[BBB] = bookResults
            #if USFMResults: self.USFMBooks[BBB] = USFMResults
            self.stashBook( self.thisBook )
    # end of OSISXMLBible.validateAndExtractBookDiv
# end of OSISXMLBible class


def demo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( programNameVersion )


    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        for standardTestFolder in (
                        BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'OSISTest1/' ),
                        BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'OSISTest2/' ),
                        BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( 'morphhb/wlc/' ),
                        BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMTest3/' ),
                        BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFM2AllMarkersProject/' ),
                        BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFM3AllMarkersProject/' ),
                        BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFMErrorProject/' ),
                        BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PTX7Test/' ),
                        BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PTX8Test1/' ),
                        BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'PTX8Test2/' ),
                        BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Matigsalug/Bible/MBTV/' ),
                        BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_USFM2_Export/' ),
                        BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_USFM2_Reexport/' ),
                        BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_USFM3_Export/' ),
                        BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_USFM3_Reexport/' ),
                        'MadeUpFolder/',
                        ):
            if BibleOrgSysGlobals.verbosityLevel > 0:
                print( "\nStandard testfolder is: {}".format( standardTestFolder ) )
            result1 = OSISXMLBibleFileCheck( standardTestFolder )
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "OSIS TestA1", result1 )
            result2 = OSISXMLBibleFileCheck( standardTestFolder, autoLoad=True )
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "OSIS TestA2", result2 )
            result3 = OSISXMLBibleFileCheck( standardTestFolder, autoLoadBooks=True )
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "OSIS TestA3", result3 )


    BiblesFolderpath = BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Bibles/' )
    if 1: # Test OSISXMLBible object
        testFilepaths = (
            BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'OSISTest1/' ), # Matigsalug test sample
            BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'OSISTest2/' ), # Full KJV from Crosswire
            BiblesFolderpath.joinpath( 'Original languages/SBLGNT/sblgnt.osis/SBLGNT.osis.xml' ),
            BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( 'morphhb/wlc/Ruth.xml' ),
            BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( 'morphhb/wlc/Dan.xml' ),
            BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( 'morphhb/wlc/' ), # Hebrew Ruth, Daniel, Bible
            BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( 'morphhb/wlc/1Sam.xml' ),
            BiblesFolderpath.joinpath( 'Formats/OSIS/Crosswire USFM-to-OSIS (Perl)/Matigsalug.osis.xml' ), # Entire Bible in one file 4.4MB
            '../../MatigsalugOSIS/OSIS-Output/MBTGEN.xml',
            '../../MatigsalugOSIS/OSIS-Output/MBTRUT.xml', # Single books
            '../../MatigsalugOSIS/OSIS-Output/MBTJAS.xml', # Single books
               '../../MatigsalugOSIS/OSIS-Output/MBTMRK.xml', '../../MatigsalugOSIS/OSIS-Output/MBTJAS.xml', # Single books
               '../../MatigsalugOSIS/OSIS-Output/MBT2PE.xml', # Single book
            '../../MatigsalugOSIS/OSIS-Output', # Entire folder of single books
            )
        justOne = ( testFilepaths[0], )

        # Demonstrate the OSIS Bible class
        #for j, testFilepath in enumerate( justOne ): # Choose testFilepaths or justOne
        for j, testFilepath in enumerate( testFilepaths ): # Choose testFilepaths or justOne
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nB/ OSIS {}/ Demonstrating the OSIS Bible class…".format( j+1 ) )
            if BibleOrgSysGlobals.verbosityLevel > 0: print( "  Test filepath is {!r}".format( testFilepath ) )
            oB = OSISXMLBible( testFilepath ) # Load and process the XML
            oB.load()
            if BibleOrgSysGlobals.verbosityLevel > 0: print( oB ) # Just print a summary

            if 1: # Test verse lookup
                from BibleOrgSys.Reference import VerseReferences
                for referenceTuple in (
                                    ('OT','GEN','1','1'), ('OT','GEN','1','3'),
                                    ('OT','RUT','1','1'), ('OT','RUT','3','3'),
                                    ('OT','SA1','1','1'),
                                    ('OT','PSA','3','0'), ('OT','PSA','3','1'),
                                    ('OT','DAN','1','21'),
                                    ('NT','MAT','3','5'), ('NT','JAM','1','6'),
                                    ('NT','JDE','1','4'), ('NT','REV','22','21'),
                                    ('DC','BAR','1','1'), ('DC','MA1','1','1'), ('DC','MA2','1','1'),
                                    ):
                    (t, b, c, v) = referenceTuple
                    if t=='OT' and len(oB)==27: continue # Don't bother with OT references if it's only a NT
                    if t=='NT' and len(oB)==39: continue # Don't bother with NT references if it's only a OT
                    if t=='DC' and len(oB)<=66: continue # Don't bother with DC references if it's too small
                    if BibleOrgSysGlobals.verbosityLevel > 0:
                        try:
                            svk = VerseReferences.SimpleVerseKey( b, c, v )
                            #print( svk, oB.getVerseDataList( svk ) )
                            print( "OSISXMLBible.demo:", svk, oB.getVerseText( svk ) )
                        except KeyError:
                            print( "OSISXMLBible.demo: {} {}:{} can't be found!".format( b, c, v ) )

            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag:
                oB.check()
            if BibleOrgSysGlobals.commandLineArguments.export:
                #oB.toODF(); halt
                oB.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
# end of demo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    demo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of OSISXMLBible.py
