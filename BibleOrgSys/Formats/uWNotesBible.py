#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# uWNotesBible.py
#
# Module handling unfoldingWord Bible Notes stored in TSV tables.
#
# Copyright (C) 2020 Robert Hunt
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
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Module for defining and manipulating complete or partial uW Notes Bibles.

Note that we squeeze the TSV format into pseudo-USFM.
We only save non-blank fields.
    SupportReference    m
    OrigQuote           q1
    Occurrence (digit)  pi (if non-zero and not '1')
    GLQuote             q2
    OccurrenceNote      p (Saved as markdown containing <br> fields for newLines)
There might be some intro versions of the above fields before chapter 1.
There might be some verse 0 fields for chapter introductions.
There might be several notes for one verse.
Some verses might have no notes.
"""
from gettext import gettext as _
from typing import Dict, List, Any, Optional
import os
from pathlib import Path
import logging
import multiprocessing
import re

if __name__ == '__main__':
    import sys
    aboveAboveFolderpath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderpath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderpath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import vPrint
from BibleOrgSys.Bible import Bible, BibleBook
from BibleOrgSys.Internals.InternalBibleInternals import InternalBibleEntryList, InternalBibleEntry


LAST_MODIFIED_DATE = '2020-05-12' # by RJH
SHORT_PROGRAM_NAME = "uWNotesBible"
PROGRAM_NAME = "unfoldingWord Bible Notes handler"
PROGRAM_VERSION = '0.03'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

debuggingThisModule = False


filenameEndingsToIgnore = ('.ZIP.GO', '.ZIP.DATA',) # Must be UPPERCASE
extensionsToIgnore = ( 'ASC', 'BAK', 'BAK2', 'BAK3', 'BAK4', 'BBLX', 'BC', 'CCT', 'CSS', 'DOC', 'DTS', 'ESFM', 'HTM','HTML',
                    'JAR', 'LDS', 'LOG', 'MYBIBLE', 'NT','NTX', 'ODT', 'ONT','ONTX', 'OSIS', 'OT','OTX', 'PDB',
                    'SAV', 'SAVE', 'STY', 'SSF', 'USFX', 'USX', 'VRS', 'YET', 'XML', 'ZIP', ) # Must be UPPERCASE and NOT begin with a dot

METADATA_FILENAME = 'manifest.yaml'


def loadYAML( YAMLFilepath ) -> Dict[str,Any]:
    """
    Load the given YAML file
        and return the settings dict.
    """
    debuggingThisFunction = False
    vPrint( 'Never', debuggingThisModule or debuggingThisFunction, f"uWNotesBible.loadYAML( {YAMLFilepath} )…" )

    # import yaml
    # yamlDict = yaml.safe_load( YAMLFilepath )
    # print( f"yaml.load got ({len(yamlDict)}) {yamlDict!r}"); halt

    dataDict = {}
    key1 = key2 = None
    if YAMLFilepath and os.path.isfile( YAMLFilepath ) and os.access( YAMLFilepath, os.R_OK ):
        with open( YAMLFilepath, 'rt' ) as yamlFile:
            state = None
            indent = 2 # TODO: Really should deduce this number from the file
            for j, line in enumerate( yamlFile, start=1 ):
                line = line.rstrip( '\n\r ' )
                if not line: continue
                if line.startswith( '#' ): continue # comment line
                if line == '---': state = 0; continue # start of table
                numLeadingSpaces = len(line) - len( line.lstrip( ' ' ) )
                if debuggingThisFunction:
                    print( f"\nResult dict ({len(dataDict)}) = {dataDict}")
                    print( f'Line {j}  State={state}  k1={key1!r} k2={key2!r}  numLS={numLeadingSpaces}: {line!r}' )

                # Check if we need to go back a level
                if numLeadingSpaces==0:
                    if debuggingThisFunction and state and state>0: print( f"S-0: No leading spaces so returned to 0 from {state}" )
                    key1 = key2 = None
                    state = 0
                if numLeadingSpaces==indent and line[indent] != '-':
                    if debuggingThisFunction and state>1: print( f"S-1: Returned to 1 from {state}" )
                    key2= None
                    state = 1

                if state == 0:
                    match = re.match( r'''([^ :]+?): ?['"](.+?)['"]$''', line )
                    if match:
                        if debuggingThisFunction: print( f"0-0: 1={match.group(1)}' 2='{match.group(2)}'" )
                        dataDict[match.group(1)] = match.group(2); continue
                    match = re.match( r"([^ :]+?): ?(\d+?)$", line )
                    if match:
                        if debuggingThisFunction: print( f"0-1: 1={match.group(1)}' 2='{match.group(2)}'" )
                        dataDict[match.group(1)] = int(match.group(2)); continue
                    match = re.match( r"([^ :]+?):$", line )
                    if match:
                        if debuggingThisFunction: print( f"0-2: 1={match.group(1)!r} => 1" )
                        key1 = match.group(1)
                        state = 1; continue

                elif state == 1:
                    assert key1
                    if line == f"{' '*indent}-":
                        if debuggingThisFunction: print( f"1-0: {line!r} with k1={key1!r} => 3" )
                        if key1 not in dataDict: dataDict[key1] = [{}]
                        else:
                            assert isinstance( dataDict[key1], list )
                            assert isinstance( dataDict[key1][-1], dict )
                            dataDict[key1].append( {} )
                        state = 3; continue
                    match = re.match( rf'''{' '*indent}([^ :]+?): ?['"](.+?)['"]$''', line )
                    if match:
                        if debuggingThisFunction: print( f"1-1: 1={match.group(1)}' 2='{match.group(2)}'" )
                        if key1 not in dataDict: dataDict[key1] = {}
                        else: assert isinstance( dataDict[key1], dict )
                        dataDict[key1][match.group(1)] = match.group(2); continue
                    match = re.match( rf"{' '*indent}([^ :]+?): ?(\d+?)$", line )
                    if match:
                        if debuggingThisFunction: print( f"1-2: 1={match.group(1)}' 2='{match.group(2)}'" )
                        if key1 not in dataDict: dataDict[key1] = {}
                        else: assert isinstance( dataDict[key1], dict )
                        dataDict[key1][match.group(1)] = int(match.group(2)); continue

                    match = re.match( rf"{' '*indent}([^ :]+?):$", line )
                    if match:
                        if debuggingThisFunction: print( f"1-3: 1={match.group(1)}'" )
                        if key1 not in dataDict: dataDict[key1] = {}
                        key2 = match.group(1); state = 2; continue

                    match = re.match( rf'''{' '*indent}- ([^ :]+?): ?['"](.+?)['"]$''', line )
                    if match:
                        if debuggingThisFunction: print( f"1-4: k1={key1!r} k2={key2!r} mg1={match.group(1)!r} mg2={match.group(2)!r} => 3" )
                        if key2:
                            if key2 not in dataDict[key1]:
                                dataDict[key1][key2] = []
                            dataDict[key1][key2].append( {} )
                            dataDict[key1][key2][-1][match.group(1)] = match.group(2)
                            state = 3; continue
                        else:
                            if key1 not in dataDict: dataDict[key1] = []
                            else: assert isinstance( dataDict[key1], list )
                            dataDict[key1].append( {} )
                            dataDict[key1][-1][match.group(1)] = match.group(2)
                            state = 3; continue

                elif state == 2:
                    assert key1
                    assert key2
                    if line == f"{' '*2*indent}-":
                        if debuggingThisFunction: print( f"2-0: '{line}' with k1={key1!r} k2={key2!r}" )
                        if key2 not in dataDict[key1]:
                            dataDict[key1][key2] = [{}]
                        else:
                            assert isinstance( dataDict[key1][key2], list )
                            assert isinstance( dataDict[key1][key2][-1], dict )
                            dataDict[key1][key2].append( {} )
                        state = 4; continue
                    match = re.match( rf'''{' '*indent}- ['"]([^:'"]+?)['"]$''', line )
                    if match:
                        if debuggingThisFunction: print( f"2-1: k1={key1!r} k2={key2!r} 1={match.group(1)}'" )
                        if key2 not in dataDict[key1]: dataDict[key1][key2] = []
                        else: assert isinstance( dataDict[key1][key2], list )
                        dataDict[key1][key2].append( match.group(1) ); continue
                    match = re.match( rf'''{' '*2*indent}([^ :]+?): ?['"](.+?)['"]$''', line )
                    if match:
                        if debuggingThisFunction: print( f"2-2: 1={match.group(1)}' 2='{match.group(2)}'" )
                        if key2 not in dataDict[key1]: dataDict[key1][key2] = {}
                        else: assert isinstance( dataDict[key1][key2], dict )
                        dataDict[key1][key2][match.group(1)] = match.group(2); continue
                    match = re.match( rf"{' '*2*indent}([^ :]+?): ?(\d+?)$", line )
                    if match:
                        if debuggingThisFunction: print( f"2-3: 1={match.group(1)}' 2='{match.group(2)}'" )
                        if key2 not in dataDict[key1]: dataDict[key1][key2] = {}
                        else: assert isinstance( dataDict[key1][key2], dict )
                        dataDict[key1][key2][match.group(1)] = int(match.group(2)); continue
                    match = re.match( rf'''{' '*2*indent}- ['"](.+?)['"]$''', line )
                    if match:
                        if debuggingThisFunction: print( f"2-4: 1={match.group(1)}'" )
                        if key2 not in dataDict[key1]: dataDict[key1][key2] = []
                        else: assert isinstance( dataDict[key1][key2], list )
                        dataDict[key1][key2].append( match.group(1) ); continue

                elif state == 3:
                    assert key1
                    if line == f"{' '*indent}-":
                        if debuggingThisFunction: print( f"3-0: '{line}' with k1={key1!r}" )
                        assert isinstance( dataDict[key1], list )
                        assert isinstance( dataDict[key1][-1], dict )
                        dataDict[key1].append( {} )
                        continue
                    match = re.match( rf'''{' '*2*indent}([^ :]+?): ?['"](.+?)['"]$''', line )
                    if match:
                        if debuggingThisFunction: print( f"3-1: k1={key1!r} k2={key2!r} mg1={match.group(1)}' mg2='{match.group(2)}'" )
                        if key1 not in dataDict: dataDict[key1] = [{}]
                        else: assert isinstance( dataDict[key1], list )
                        dataDict[key1][-1][match.group(1)] = match.group(2); continue
                    match = re.match( rf'''{' '*2*indent}([^ :]+?): ?(.+?)$''', line )
                    if match:
                        if debuggingThisFunction: print( f"3-2: 1={match.group(1)}' 2='{match.group(2)}'" )
                        if key1 not in dataDict: dataDict[key1] = [{}]
                        else: assert isinstance( dataDict[key1], list )
                        dataDict[key1][-1][match.group(1)] = match.group(2); continue

                elif state == 4:
                    assert key1
                    assert key2
                    if line == f"{' '*2*indent}-":
                        if debuggingThisFunction: print( f"4-0: '{line}' with k1={key1!r} k2={key2!r}" )
                        assert isinstance( dataDict[key1][key2], list )
                        assert isinstance( dataDict[key1][key2][-1], dict )
                        dataDict[key1][key2].append( {} )
                        continue
                    match = re.match( rf'''{' '*3*indent}([^ :]+?): ?['"](.+?)['"]$''', line )
                    if match:
                        if debuggingThisFunction: print( f"4-1: 1={match.group(1)}' 2='{match.group(2)}'" )
                        if key2 not in dataDict[key1]: dataDict[key1][key2] = [{}]
                        else: assert isinstance( dataDict[key1][key2], list )
                        dataDict[key1][key2][-1][match.group(1)] = match.group(2); continue
    else:
        logging.critical( f"loadYAML: Unable to load and YAML from {YAMLFilepath}" )
        return None

    # print( "\nSettings", len(dataDict), dataDict.keys() )
    if debuggingThisFunction or BibleOrgSysGlobals.debugFlag and debuggingThisModule:
        for j, (section,value) in enumerate( dataDict.items(), start=1 ):
            vPrint( 'Normal', debuggingThisModule, f"  loadYAML.load {j}: {section} = {value!r}" )

    return dataDict
# end of loadYAML function



def uWNotesBibleFileCheck( givenFolderName, strictCheck:bool=True, autoLoad:bool=False, autoLoadBooks:bool=False ):
    """
    Given a folder, search for uW Notes Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number of Bibles found.

    if autoLoad is true and exactly one uW Notes Bible is found,
        returns the loaded uWNotesBible object.
    """
    vPrint( 'Info', debuggingThisModule, "uWNotesBibleFileCheck( {}, {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad, autoLoadBooks ) )
    if BibleOrgSysGlobals.debugFlag: assert givenFolderName
    if BibleOrgSysGlobals.debugFlag: assert autoLoad in (True,False,) and autoLoadBooks in (True,False,)

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( "uWNotesBibleFileCheck: Given {!r} folder is unreadable".format( givenFolderName ) )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( "uWNotesBibleFileCheck: Given {!r} path is not a folder".format( givenFolderName ) )
        return False

    # Find all the files and folders in this folder
    vPrint( 'Verbose', debuggingThisModule, " uWNotesBibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
    foundFolders, foundFiles = [], []
    for something in os.listdir( givenFolderName ):
        somepath = os.path.join( givenFolderName, something )
        if os.path.isdir( somepath ):
            if something not in BibleOrgSysGlobals.COMMONLY_IGNORED_FOLDERS:
                foundFolders.append( something )
        elif os.path.isfile( somepath ):
            somethingUpper = something.upper()
            somethingUpperProper, somethingUpperExt = os.path.splitext( somethingUpper )
            ignore = False
            for ending in filenameEndingsToIgnore:
                if somethingUpper.endswith( ending): ignore=True; break
            if ignore: continue
            if not somethingUpperExt[1:] in extensionsToIgnore: # Compare without the first dot
                foundFiles.append( something )

    # See if there's an uWNotesBible project here in this given folder
    numFound = 0
    if METADATA_FILENAME in foundFiles:
        numFound += 1
        if strictCheck:
            for folderName in foundFolders:
                vPrint( 'Quiet', debuggingThisModule, "uWNotesBibleFileCheck: Suprised to find folder:", folderName )
    if numFound:
        vPrint( 'Info', debuggingThisModule, "uWNotesBibleFileCheck got {} in {}".format( numFound, givenFolderName ) )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            uWnB = uWNotesBible( givenFolderName )
            if autoLoad: uWnB.preload()
            if autoLoadBooks: uWnB.loadBooks() # Load and process the file
            return uWnB
        return numFound

    # Look one level down
    numFound = 0
    foundProjects = []
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
        if not os.access( tryFolderName, os.R_OK ): # The subfolder is not readable
            logging.warning( _("uWNotesBibleFileCheck: {!r} subfolder is unreadable").format( tryFolderName ) )
            continue
        vPrint( 'Verbose', debuggingThisModule, "    uWNotesBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
        foundSubfolders, foundSubfiles = [], []
        try:
            for something in os.listdir( tryFolderName ):
                somepath = os.path.join( givenFolderName, thisFolderName, something )
                if os.path.isdir( somepath ):
                    if something not in BibleOrgSysGlobals.COMMONLY_IGNORED_FOLDERS:
                        foundSubfolders.append( something )
                elif os.path.isfile( somepath ):
                    somethingUpper = something.upper()
                    somethingUpperProper, somethingUpperExt = os.path.splitext( somethingUpper )
                    ignore = False
                    for ending in filenameEndingsToIgnore:
                        if somethingUpper.endswith( ending): ignore=True; break
                    if ignore: continue
                    if not somethingUpperExt[1:] in extensionsToIgnore: # Compare without the first dot
                        foundSubfiles.append( something )
        except PermissionError: pass # can't read folder, e.g., system folder

        # See if there's an uW Notes Bible here in this folder
        if METADATA_FILENAME in foundSubfiles:
            numFound += 1
            if strictCheck:
                for folderName in foundSubfolders:
                    vPrint( 'Quiet', debuggingThisModule, "uWNotesBibleFileCheckSuprised to find folder:", folderName )
    if numFound:
        vPrint( 'Info', debuggingThisModule, "uWNotesBibleFileCheck foundProjects {} {}".format( numFound, foundProjects ) )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            uWnB = uWNotesBible( foundProjects[0] )
            if autoLoad: uWnB.preload()
            if autoLoadBooks: uWnB.loadBooks() # Load and process the file
            return uWnB
        return numFound
# end of uWNotesBibleFileCheck



class uWNotesBible( Bible ):
    """
    Class to load and manipulate uW Notes Bibles.

    """
    def __init__( self, sourceFolder, givenName:Optional[str]=None, givenAbbreviation:Optional[str]=None, encoding:Optional[str]=None ) -> None:
        """
        Create the internal uW Notes Bible object.

        Note that sourceFolder can be None if we don't know that yet.
        """
         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = 'uW Notes Bible object'
        self.objectTypeString = 'uW Notes'

        # Now we can set our object variables
        self.sourceFolder, self.givenName, self.abbreviation, self.encoding = sourceFolder, givenName, givenAbbreviation, encoding
    # end of uWNotesBible.__init_


    def preload( self ) -> None:
        """
        Loads the Metadata file if it can be found.
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            vPrint( 'Quiet', debuggingThisModule, _("preload() from {}").format( self.sourceFolder ) )

        # Do a preliminary check on the contents of our folder
        foundFiles, foundFolders = [], []
        for something in os.listdir( self.sourceFolder ):
            somepath = os.path.join( self.sourceFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )
            else: logging.error( _("uWNotesBible.preload: Not sure what {!r} is in {}!").format( somepath, self.sourceFolder ) )
        if foundFolders:
            unexpectedFolders = []
            for folderName in foundFolders:
                if folderName in BibleOrgSysGlobals.COMMONLY_IGNORED_FOLDERS:
                    continue
                unexpectedFolders.append( folderName )
            if unexpectedFolders:
                logging.info( _("uWNotesBible.preload: Surprised to see subfolders in {!r}: {}").format( self.sourceFolder, unexpectedFolders ) )
        if not foundFiles:
            vPrint( 'Quiet', debuggingThisModule, _("uWNotesBible.preload: Couldn't find any files in {!r}").format( self.sourceFolder ) )
            raise FileNotFoundError # No use continuing

        #if self.metadataFilepath is None: # it might have been loaded first
        # Attempt to load the metadata file
        self.loadMetadata( os.path.join( self.sourceFolder, METADATA_FILENAME ) )
        if isinstance( self.givenBookList, list ):
            self.availableBBBs.update( self.givenBookList )

        #self.name = self.givenName
        #if self.name is None:
            #for field in ('FullName','Name',):
                #if field in self.settingsDict: self.name = self.settingsDict[field]; break
        #if not self.name: self.name = os.path.basename( self.sourceFolder )
        #if not self.name: self.name = os.path.basename( self.sourceFolder[:-1] ) # Remove the final slash
        #if not self.name: self.name = "uW Notes Bible"

        self.preloadDone = True
    # end of uWNotesBible.preload


    def loadMetadata( self, metadataFilepath ) -> None:
        """
        Process the metadata from the given filepath.

        Sets some class variables and puts a dictionary into self.settingsDict.
        """
        vPrint( 'Never', debuggingThisModule, "Loading metadata from {!r}".format( metadataFilepath ) )
        self.metadataFilepath = metadataFilepath
        if self.suppliedMetadata is None: self.suppliedMetadata = {}
        if 'uW' not in self.suppliedMetadata: self.suppliedMetadata['uW'] = {}
        self.suppliedMetadata['uW']['Manifest'] = loadYAML( metadataFilepath )
        vPrint( 'Never', debuggingThisModule, f"\ns.sM: {self.suppliedMetadata}" )

        if self.suppliedMetadata['uW']['Manifest']:
            self.applySuppliedMetadata( 'uW' ) # Copy some to self.settingsDict
            vPrint( 'Never', debuggingThisModule, f"\ns.sD: {self.settingsDict}" )
    # end of uWNotesBible.loadMetadata


    def loadBook( self, BBB:str ) -> None:
        """
        Load the requested book into self.books if it's not already loaded.

        NOTE: You should ensure that preload() has been called first.
        """
        vPrint( 'Info', debuggingThisModule, "uWNotesBible.loadBook( {} )".format( BBB ) )
        if BBB in self.books: return # Already loaded
        if BBB in self.triedLoadingBook:
            logging.warning( "We had already tried loading uW Notes {} for {}".format( BBB, self.name ) )
            return # We've already attempted to load this book
        self.triedLoadingBook[BBB] = True
        if BBB in self.givenBookList:
            vPrint( 'Verbose', debuggingThisModule, _("  uWNotesBible: Loading {} from {} from {}…").format( BBB, self.name, self.sourceFolder ) )
            bcvBB = uWNotesBibleBook( self, BBB )
            bcvBB.load( self.possibleFilenameDict[BBB] )
            if bcvBB._rawLines:
                self.stashBook( bcvBB )
                bcvBB.validateMarkers()
            else: logging.info( "uW Notes book {} was completely blank".format( BBB ) )
            self.availableBBBs.add( BBB )
        else: logging.info( "uW Notes book {} is not listed as being available".format( BBB ) )
    # end of uWNotesBible.loadBook


    def _loadBookMP( self, BBB:str ) -> Optional[BibleBook]:
        """
        Multiprocessing version!
        Load the requested book if it's not already loaded (but doesn't save it as that is not safe for multiprocessing)

        Parameter is a 2-tuple containing BBB and the filename.
        """
        vPrint( 'Verbose', debuggingThisModule, _("loadBookMP( {} )").format( BBB ) )
        assert BBB not in self.books
        self.triedLoadingBook[BBB] = True
        if BBB in self.givenBookList:
            if BibleOrgSysGlobals.verbosityLevel > 2 or BibleOrgSysGlobals.debugFlag:
                vPrint( 'Quiet', debuggingThisModule, '  ' + "Loading {} from {} from {}…".format( BBB, self.name, self.sourceFolder ) )
            bcvBB = uWNotesBibleBook( self, BBB )
            bcvBB.load( self.possibleFilenameDict[BBB] )
            bcvBB.validateMarkers()
            if BibleOrgSysGlobals.verbosityLevel > 2 or BibleOrgSysGlobals.debugFlag: vPrint( 'Quiet', debuggingThisModule, _("    Finishing loading uW Notes book {}.").format( BBB ) )
            return bcvBB
        else: logging.info( "uW Notes book {} is not listed as being available".format( BBB ) )
    # end of uWNotesBible.loadBookMP


    def loadBooks( self ) -> None:
        """
        Load all the books.
        """
        vPrint( 'Normal', debuggingThisModule, f"Loading '{self.name}' from {self.sourceFolder}…" )

        if not self.preloadDone: self.preload()

        if self.givenBookList:
            if BibleOrgSysGlobals.maxProcesses > 1: # Load all the books as quickly as possible
                if BibleOrgSysGlobals.verbosityLevel > 1:
                    vPrint( 'Quiet', debuggingThisModule, "Loading {} uW Notes books using {} processes…".format( len(self.givenBookList), BibleOrgSysGlobals.maxProcesses ) )
                    vPrint( 'Quiet', debuggingThisModule, "  NOTE: Outputs (including error and warning messages) from loading various books may be interspersed." )
                BibleOrgSysGlobals.alreadyMultiprocessing = True
                with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                    results = pool.map( self._loadBookMP, self.givenBookList ) # have the pool do our loads
                    assert len(results) == len(self.givenBookList)
                    for bBook in results: self.stashBook( bBook ) # Saves them in the correct order
                BibleOrgSysGlobals.alreadyMultiprocessing = False
            else: # Just single threaded
                # Load the books one by one -- assuming that they have regular Paratext style filenames
                for BBB in self.givenBookList:
                    #if BibleOrgSysGlobals.verbosityLevel>1 or BibleOrgSysGlobals.debugFlag:
                        #vPrint( 'Quiet', debuggingThisModule, _("  uWNotesBible: Loading {} from {} from {}…").format( BBB, self.name, self.sourceFolder ) )
                    self.loadBook( BBB ) # also saves it
        else:
            logging.critical( "uWNotesBible: " + _("No books to load in folder '{}'!").format( self.sourceFolder ) )
        #vPrint( 'Quiet', debuggingThisModule, self.getBookList() )
        self.doPostLoadProcessing()
    # end of uWNotesBible.load
# end of class uWNotesBible



class uWNotesBibleBook( BibleBook ):
    """
    Class to load and manipulate a single uW Notes file / book.
    """

    def __init__( self, containerBibleObject:Bible, BBB:str ) -> None:
        """
        Create the uW Notes Bible book object.
        """
        BibleBook.__init__( self, containerBibleObject, BBB ) # Initialise the base class
        self.objectNameString = 'uW Notes Bible Book object'
        self.objectTypeString = 'uW Notes'
    # end of uWNotesBibleBook.__init__


    def load( self, filename:str ) -> None:
        """
        Load the uW Notes Bible book from a file.

        Tries to standardise by combining physical lines into logical lines,
            i.e., so that all lines begin with a uW Notes paragraph marker.

        Uses the addLine function of the base class to save the lines.

        Note: the base class later on will try to break apart lines with a paragraph marker in the middle --
                we don't need to worry about that here.
        """
        vPrint( 'Info', debuggingThisModule, "  " + _("Loading {} from {}…").format( self.BBB, filename ) )
        self.sourceFolder = self.containerBibleObject.sourceFolder
        self.filename = filename
        self.filepath = os.path.join( self.sourceFolder, filename )


        def doAddLine( originalMarker:str, originalText:str ) -> None:
            """
            Check for newLine markers within the line (if so, break the line) and save the information in our database.

            Also convert ~ to a proper non-break space.
            """
            vPrint( 'Never', debuggingThisModule, "doAddLine( {}, {} )".format( repr(originalMarker), repr(originalText) ) )
            self.addLine( originalMarker, originalText ) # Call the function in the base class to save the line (or the remainder of the line if we split it above)
            # marker, text = originalMarker, originalText.replace( '~', ' ' )
            # if '\\' in text: # Check markers inside the lines
            #     markerList = BibleOrgSysGlobals.BCVMarkers.getMarkerListFromText( text )
            #     ix = 0
            #     for insideMarker, iMIndex, nextSignificantChar, fullMarker, characterContext, endIndex, markerField in markerList: # check paragraph markers
            #         if insideMarker == '\\': # it's a free-standing backspace
            #             loadErrors.append( _("{} {}:{} Improper free-standing backspace character within line in \\{}: {!r}").format( self.BBB, C, V, marker, text ) )
            #             logging.error( _("Improper free-standing backspace character within line after {} {}:{} in \\{}: {!r}").format( self.BBB, C, V, marker, text ) ) # Only log the first error in the line
            #             self.addPriorityError( 100, C, V, _("Improper free-standing backspace character inside a line") )
            #         elif BibleOrgSysGlobals.BCVMarkers.isNewlineMarker(insideMarker): # Need to split the line for everything else to work properly
            #             if ix==0:
            #                 loadErrors.append( _("{} {}:{} NewLine marker {!r} shouldn't appear within line in \\{}: {!r}").format( self.BBB, C, V, insideMarker, marker, text ) )
            #                 logging.error( _("NewLine marker {!r} shouldn't appear within line after {} {}:{} in \\{}: {!r}").format( insideMarker, self.BBB, C, V, marker, text ) ) # Only log the first error in the line
            #                 self.addPriorityError( 96, C, V, _("NewLine marker \\{} shouldn't be inside a line").format( insideMarker ) )
            #             thisText = text[ix:iMIndex].rstrip()
            #             self.addLine( marker, thisText )
            #             ix = iMIndex + 1 + len(insideMarker) + len(nextSignificantChar) # Get the start of the next text -- the 1 is for the backslash
            #             #vPrint( 'Quiet', debuggingThisModule, "Did a split from {}:{!r} to {}:{!r} leaving {}:{!r}".format( originalMarker, originalText, marker, thisText, insideMarker, text[ix:] ) )
            #             marker = insideMarker # setup for the next line
            #     if ix != 0: # We must have separated multiple lines
            #         text = text[ix:] # Get the final bit of the line
            # self.addLine( marker, text ) # Call the function in the base class to save the line (or the remainder of the line if we split it above)
        # end of doAddLine


        fixErrors = []
        lineCount = 0
        lastC, lastV = '-1', '0'
        with open( os.path.join( self.filepath ), 'rt', encoding='utf-8' ) as myFile: # Automatically closes the file when done
            for line in myFile:
                line = line.rstrip( '\n\r' )
                lineCount += 1
                if lineCount==1 and line and line[0]==chr(65279): #U+FEFF
                    logging.info( "loaduWNotesBibleBook: Detected Unicode Byte Order Marker (BOM) in {}".format( metadataFilepath ) )
                    line = line[1:] # Remove the Byte Order Marker (BOM)
                #vPrint( 'Quiet', debuggingThisModule, CV, "line", line )
                assert line.count( '\t' )  == 8 # 9 fields
                if lineCount == 1: # Heading line
                    if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
                        assert line == 'Book\tChapter\tVerse\tID\tSupportReference\tOrigQuote\tOccurrence\tGLQuote\tOccurrenceNote'
                    continue
                fields = line.split( '\t' )
                assert len(fields) == 9
                bkCode, C, V, fieldID, supportReference, origQuote, occurrence, GLQuote, occurrenceNote = fields
                if debuggingThisModule or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
                    BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromUSFMAbbreviation( bkCode )
                    assert BBB == self.BBB
                if C=='front': C = '-1'
                if C != lastC: doAddLine( 'c', C )
                try: intC = int(C)
                except ValueError: intC = -999
                if (V != lastV or C != lastC) and intC > 0:
                    doAddLine( 'v', '0' if V=='intro' else V )
                # NOTE: We don't save the ID field (nor the BBB field, of course)
                if supportReference: doAddLine( 'm' if intC>0 else 'im', supportReference )
                if origQuote: doAddLine( 'q1' if intC>0 else 'iq1', origQuote )
                if occurrence and occurrence not in ('0','1'):
                    doAddLine( 'pi' if intC>0 else 'ipi', occurrence )
                if GLQuote: doAddLine( 'q2' if intC>0 else 'iq2', GLQuote )
                if occurrenceNote: doAddLine( 'p' if intC>0 else 'ip', occurrenceNote )

                lastC, lastV = C, V
            #if loadErrors: self.checkResultsDictionary['Load Errors'] = loadErrors
            #if debugging: vPrint( 'Quiet', debuggingThisModule, self._rawLines ); halt
        if fixErrors: self.checkResultsDictionary['Fix Text Errors'] = fixErrors
    # end of load
# end of class uWNotesBibleBook



def briefDemo() -> None:
    """
    Demonstrate reading and checking some Bible databases.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, programNameVersion, LAST_MODIFIED_DATE )

    testFolderpath = Path( '/mnt/SSDs/Bibles/unfoldingWordHelps/en_tn/' )


    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        vPrint( 'Quiet', debuggingThisModule, "\nuW Notes TestA1" )
        result1 = uWNotesBibleFileCheck( testFolderpath )
        vPrint( 'Normal', debuggingThisModule, "uW Notes TestA1", result1 )

        vPrint( 'Quiet', debuggingThisModule, "\nuW Notes TestA2" )
        result2 = uWNotesBibleFileCheck( testFolderpath, autoLoad=True ) # But doesn't preload books
        vPrint( 'Normal', debuggingThisModule, "uW Notes TestA2", result2 )
        #result2.loadMetadataFile( os.path.join( testFolderpath, "BooknamesMetadata.txt" ) )
        if BibleOrgSysGlobals.strictCheckingFlag:
            result2.check()
            #vPrint( 'Quiet', debuggingThisModule, UsfmB.books['GEN']._processedLines[0:40] )
            bibleErrors = result2.getCheckResults()
            # vPrint( 'Quiet', debuggingThisModule, bibleErrors )
        #if BibleOrgSysGlobals.commandLineArguments.export:
            ###result2.toDrupalBible()
            #result2.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )

        vPrint( 'Quiet', debuggingThisModule, "\nuW Notes TestA3" )
        result3 = uWNotesBibleFileCheck( testFolderpath, autoLoad=True, autoLoadBooks=True )
        vPrint( 'Normal', debuggingThisModule, "uW Notes TestA3", result3 )
        #result3.loadMetadataFile( os.path.join( testFolderpath, "BooknamesMetadata.txt" ) )
        if BibleOrgSysGlobals.strictCheckingFlag:
            result3.check()
            #vPrint( 'Quiet', debuggingThisModule, UsfmB.books['GEN']._processedLines[0:40] )
            bibleErrors = result3.getCheckResults()
            # vPrint( 'Quiet', debuggingThisModule, bibleErrors )
        if BibleOrgSysGlobals.commandLineArguments.export:
            ##result3.toDrupalBible()
            result3.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )


    if 0: # all discovered modules in the test folder
        foundFolders, foundFiles = [], []
        for something in os.listdir( testFolderpath ):
            somepath = os.path.join( testFolderpath, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )

        if BibleOrgSysGlobals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
            vPrint( 'Normal', debuggingThisModule, "\nTrying all {} discovered modules…".format( len(foundFolders) ) )
            parameters = [folderName for folderName in sorted(foundFolders)]
            BibleOrgSysGlobals.alreadyMultiprocessing = True
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.map( testBCV, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            for j, someFolder in enumerate( sorted( foundFolders ) ):
                vPrint( 'Normal', debuggingThisModule, "\nuW Notes D{}/ Trying {}".format( j+1, someFolder ) )
                #myTestFolder = os.path.join( testFolderpath, someFolder+'/' )
                testBCV( someFolder )


    if 0: # Load and process some of our test versions
        count = 0
        for name, encoding, testFolder in (
                                        ("Matigsalug", 'utf-8', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'BCVTest1/')),
                                        ("Matigsalug", 'utf-8', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'BCVTest2/')),
                                        ("Exported", 'utf-8', "Tests/BOS_BCV_Export/"),
                                        ):
            count += 1
            if os.access( testFolder, os.R_OK ):
                vPrint( 'Quiet', debuggingThisModule, "\nuW Notes A{}/".format( count ) )
                uWnB = uWNotesBible( testFolder, name, encoding=encoding )
                uWnB.load()
                if BibleOrgSysGlobals.verbosityLevel > 1:
                    vPrint( 'Quiet', debuggingThisModule, "Gen assumed book name:", repr( uWnB.getAssumedBookName( 'GEN' ) ) )
                    vPrint( 'Quiet', debuggingThisModule, "Gen long TOC book name:", repr( uWnB.getLongTOCName( 'GEN' ) ) )
                    vPrint( 'Quiet', debuggingThisModule, "Gen short TOC book name:", repr( uWnB.getShortTOCName( 'GEN' ) ) )
                    vPrint( 'Quiet', debuggingThisModule, "Gen book abbreviation:", repr( uWnB.getBooknameAbbreviation( 'GEN' ) ) )
                vPrint( 'Quiet', debuggingThisModule, uWnB )
                if BibleOrgSysGlobals.strictCheckingFlag:
                    uWnB.check()
                    #vPrint( 'Quiet', debuggingThisModule, UsfmB.books['GEN']._processedLines[0:40] )
                    bcbibleErrors = uWnB.getCheckResults()
                    # vPrint( 'Quiet', debuggingThisModule, bcbibleErrors )
                if BibleOrgSysGlobals.commandLineArguments.export:
                    ##uWnB.toDrupalBible()
                    uWnB.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
                    newObj = BibleOrgSysGlobals.unpickleObject( BibleOrgSysGlobals.makeSafeFilename(name) + '.pickle', os.path.join( "BOSOutputFiles/", "BOS_Bible_Object_Pickle/" ) )
                    vPrint( 'Quiet', debuggingThisModule, "newObj is", newObj )
            else: vPrint( 'Quiet', debuggingThisModule, f"\nSorry, test folder '{testFolder}' is not readable on this computer." )
#end of uWNotesBible.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, programNameVersion, LAST_MODIFIED_DATE )

    testFolderpath = Path( '/mnt/SSDs/Bibles/unfoldingWordHelps/en_tn/' )

    # Demo our YAML loading
    for j, testFilepath in enumerate( (
                        '/mnt/SSDs/Bibles/Original languages/UHB/manifest.yaml',
                        '/mnt/SSDs/Bibles/Original languages/UGNT/manifest.yaml',
                        '/mnt/SSDs/Bibles/unfoldingWordHelps/en_ta/manifest.yaml',
                        '/mnt/SSDs/Bibles/unfoldingWordHelps/en_ta/intro/toc.yaml',
                        '/mnt/SSDs/Bibles/unfoldingWordHelps/en_ta/intro/config.yaml',
                        '/mnt/SSDs/Bibles/unfoldingWordHelps/en_tn/manifest.yaml',
                        '/mnt/SSDs/Bibles/unfoldingWordHelps/en_tw/manifest.yaml',
                        '/mnt/SSDs/Bibles/English translations/unfoldingWordVersions/en_ult/manifest.yaml',
                        '/mnt/SSDs/Bibles/English translations/unfoldingWordVersions/en_ult/media.yaml',
                        '/mnt/SSDs/Bibles/English translations/unfoldingWordVersions/en_ust/manifest.yaml',
                        '/mnt/SSDs/Bibles/English translations/unfoldingWordVersions/en_ust/media.yaml',
                        '/mnt/SSDs/Bibles/unfoldingWordLexicons/en_ugl/manifest.yaml',
                        '/mnt/SSDs/Bibles/unfoldingWordLexicons/en_uhal/manifest.yaml',
                        ), start=1 ):
        yamlResult = loadYAML( testFilepath )
        vPrint( 'Quiet', debuggingThisModule, f"Y{j}/ {testFilepath} gave ({len(yamlResult)}) {yamlResult.keys()}")


    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        vPrint( 'Quiet', debuggingThisModule, "\nuW Notes TestA1" )
        result1 = uWNotesBibleFileCheck( testFolderpath )
        vPrint( 'Normal', debuggingThisModule, "uW Notes TestA1", result1 )

        vPrint( 'Quiet', debuggingThisModule, "\nuW Notes TestA2" )
        result2 = uWNotesBibleFileCheck( testFolderpath, autoLoad=True ) # But doesn't preload books
        vPrint( 'Normal', debuggingThisModule, "uW Notes TestA2", result2 )
        #result2.loadMetadataFile( os.path.join( testFolderpath, "BooknamesMetadata.txt" ) )
        if BibleOrgSysGlobals.strictCheckingFlag:
            result2.check()
            #vPrint( 'Quiet', debuggingThisModule, UsfmB.books['GEN']._processedLines[0:40] )
            bibleErrors = result2.getCheckResults()
            # vPrint( 'Quiet', debuggingThisModule, bibleErrors )
        #if BibleOrgSysGlobals.commandLineArguments.export:
            ###result2.toDrupalBible()
            #result2.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )

        vPrint( 'Quiet', debuggingThisModule, "\nuW Notes TestA3" )
        result3 = uWNotesBibleFileCheck( testFolderpath, autoLoad=True, autoLoadBooks=True )
        vPrint( 'Normal', debuggingThisModule, "uW Notes TestA3", result3 )
        #result3.loadMetadataFile( os.path.join( testFolderpath, "BooknamesMetadata.txt" ) )
        for BBB in ('GEN','RUT','JN3'):
            vPrint( 'Quiet', debuggingThisModule, f"{BBB} 1:1 gCVD", result3.getContextVerseData( (BBB,'1','1','') ) )
            vPrint( 'Quiet', debuggingThisModule, f"{BBB} 1:1 gVDL", result3.getVerseDataList( (BBB,'1','1','') ) )
            vPrint( 'Quiet', debuggingThisModule, f"{BBB} 1:1 gVT", result3.getVerseText( (BBB,'1','1','') ) )
        if BibleOrgSysGlobals.strictCheckingFlag:
            result3.check()
            #vPrint( 'Quiet', debuggingThisModule, UsfmB.books['GEN']._processedLines[0:40] )
            bibleErrors = result3.getCheckResults()
            # vPrint( 'Quiet', debuggingThisModule, bibleErrors )
        if BibleOrgSysGlobals.commandLineArguments.export:
            ##result3.toDrupalBible()
            result3.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )


    if 0: # all discovered modules in the test folder
        foundFolders, foundFiles = [], []
        for something in os.listdir( testFolderpath ):
            somepath = os.path.join( testFolderpath, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )

        if BibleOrgSysGlobals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
            vPrint( 'Normal', debuggingThisModule, "\nTrying all {} discovered modules…".format( len(foundFolders) ) )
            parameters = [folderName for folderName in sorted(foundFolders)]
            BibleOrgSysGlobals.alreadyMultiprocessing = True
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.map( testBCV, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            for j, someFolder in enumerate( sorted( foundFolders ) ):
                vPrint( 'Normal', debuggingThisModule, "\nuW Notes D{}/ Trying {}".format( j+1, someFolder ) )
                #myTestFolder = os.path.join( testFolderpath, someFolder+'/' )
                testBCV( someFolder )


    if 0: # Load and process some of our test versions
        count = 0
        for name, encoding, testFolder in (
                                        ("Matigsalug", 'utf-8', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'BCVTest1/')),
                                        ("Matigsalug", 'utf-8', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'BCVTest2/')),
                                        ("Exported", 'utf-8', "Tests/BOS_BCV_Export/"),
                                        ):
            count += 1
            if os.access( testFolder, os.R_OK ):
                vPrint( 'Quiet', debuggingThisModule, "\nuW Notes A{}/".format( count ) )
                uWnB = uWNotesBible( testFolder, name, encoding=encoding )
                uWnB.load()
                if BibleOrgSysGlobals.verbosityLevel > 1:
                    vPrint( 'Quiet', debuggingThisModule, "Gen assumed book name:", repr( uWnB.getAssumedBookName( 'GEN' ) ) )
                    vPrint( 'Quiet', debuggingThisModule, "Gen long TOC book name:", repr( uWnB.getLongTOCName( 'GEN' ) ) )
                    vPrint( 'Quiet', debuggingThisModule, "Gen short TOC book name:", repr( uWnB.getShortTOCName( 'GEN' ) ) )
                    vPrint( 'Quiet', debuggingThisModule, "Gen book abbreviation:", repr( uWnB.getBooknameAbbreviation( 'GEN' ) ) )
                vPrint( 'Quiet', debuggingThisModule, uWnB )
                if BibleOrgSysGlobals.strictCheckingFlag:
                    uWnB.check()
                    #vPrint( 'Quiet', debuggingThisModule, UsfmB.books['GEN']._processedLines[0:40] )
                    bcbibleErrors = uWnB.getCheckResults()
                    # vPrint( 'Quiet', debuggingThisModule, bcbibleErrors )
                if BibleOrgSysGlobals.commandLineArguments.export:
                    ##uWnB.toDrupalBible()
                    uWnB.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
                    newObj = BibleOrgSysGlobals.unpickleObject( BibleOrgSysGlobals.makeSafeFilename(name) + '.pickle', os.path.join( "BOSOutputFiles/", "BOS_Bible_Object_Pickle/" ) )
                    vPrint( 'Quiet', debuggingThisModule, "newObj is", newObj )
            else: vPrint( 'Quiet', debuggingThisModule, f"\nSorry, test folder '{testFolder}' is not readable on this computer." )
# end of uWNotesBible.fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of uWNotesBible.py
