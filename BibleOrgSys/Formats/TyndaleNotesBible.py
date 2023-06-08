#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# TyndaleNotesBible.py
#
# Module handling Tyndale Open Study Notes stored in XML files.
#
# Copyright (C) 2023 Robert Hunt
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
#   along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
Module for defining and manipulating complete or partial Tyndale Notes Bibles.

Current is able to read StudyNotes and ThemeNotes.

Note that we squeeze the XML format into pseudo-USFM.
There might be some intro versions of the above fields before chapter 1.
There might be some verse 0 fields for chapter introductions.
There might be several notes for one verse.
Some verses might have no notes.

CHANGELOG:
"""
from gettext import gettext as _
from typing import Dict, List, Any, Optional
import os
from pathlib import Path
import logging
from xml.etree.ElementTree import ElementTree, ParseError

if __name__ == '__main__':
    import sys
    aboveAboveFolderpath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderpath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderpath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys.Bible import Bible, BibleBook


LAST_MODIFIED_DATE = '2023-06-08' # by RJH
SHORT_PROGRAM_NAME = "TyndaleNotesBible"
PROGRAM_NAME = "Tyndale Bible Notes handler"
PROGRAM_VERSION = '0.20'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False


# filenameEndingsToIgnore = ('.ZIP.GO', '.ZIP.DATA',) # Must be UPPERCASE
# extensionsToIgnore = ( 'ASC', 'BAK', 'BAK2', 'BAK3', 'BAK4', 'BBLX', 'BC', 'CCT', 'CSS', 'DOC', 'DTS', 'ESFM', 'HTM','HTML',
#                     'JAR', 'LDS', 'LOG', 'MYBIBLE', 'NT','NTX', 'ODT', 'ONT','ONTX', 'OSIS', 'OT','OTX', 'PDB',
#                     'SAV', 'SAVE', 'STY', 'SSF', 'USFM', 'USFX', 'USX', 'VRS', 'YET', 'ZIP', ) # Must be UPPERCASE and NOT begin with a dot


# def TyndaleNotesBibleFileCheck( givenFolderName, strictCheck:bool=True, autoLoad:bool=False, autoLoadBooks:bool=False ):
#     """
#     Given a folder, search for Tyndale Notes Bible files or folders in the folder and in the next level down.

#     Returns False if an error is found.

#     if autoLoad is false (default)
#         returns None, or the number of Bibles found.

#     if autoLoad is true and exactly one Tyndale Notes Bible is found,
#         returns the loaded TyndaleNotesBible object.
#     """
#     fnPrint( DEBUGGING_THIS_MODULE, "TyndaleNotesBibleFileCheck( {}, {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad, autoLoadBooks ) )
#     if BibleOrgSysGlobals.debugFlag: assert givenFolderName
#     if BibleOrgSysGlobals.debugFlag: assert autoLoad in (True,False,) and autoLoadBooks in (True,False,)

#     # Check that the given folder is readable
#     if not os.access( givenFolderName, os.R_OK ):
#         logging.critical( "TyndaleNotesBibleFileCheck: Given {!r} folder is unreadable".format( givenFolderName ) )
#         return False
#     if not os.path.isdir( givenFolderName ):
#         logging.critical( "TyndaleNotesBibleFileCheck: Given {!r} path is not a folder".format( givenFolderName ) )
#         return False

#     # Find all the files and folders in this folder
#     vPrint( 'Verbose', DEBUGGING_THIS_MODULE, " TyndaleNotesBibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
#     foundFolders, foundFiles = [], []
#     for something in os.listdir( givenFolderName ):
#         somepath = os.path.join( givenFolderName, something )
#         if os.path.isdir( somepath ):
#             if something not in BibleOrgSysGlobals.COMMONLY_IGNORED_FOLDERS:
#                 foundFolders.append( something )
#         elif os.path.isfile( somepath ):
#             somethingUpper = something.upper()
#             somethingUpperProper, somethingUpperExt = os.path.splitext( somethingUpper )
#             ignore = False
#             for ending in filenameEndingsToIgnore:
#                 if somethingUpper.endswith( ending): ignore=True; break
#             if ignore: continue
#             if not somethingUpperExt[1:] in extensionsToIgnore: # Compare without the first dot
#                 foundFiles.append( something )

#     # See if there's an TyndaleNotesBible project here in this given folder
#     numFound = 0
#     # if METADATA_FILENAME in foundFiles:
#     #     numFound += 1
#     #     if strictCheck:
#     #         for folderName in foundFolders:
#     #             vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "TyndaleNotesBibleFileCheck: Suprised to find folder:", folderName )
#     if numFound:
#         vPrint( 'Info', DEBUGGING_THIS_MODULE, "TyndaleNotesBibleFileCheck got {} in {}".format( numFound, givenFolderName ) )
#         if numFound == 1 and (autoLoad or autoLoadBooks):
#             tnB = TyndaleNotesBible( givenFolderName )
#             if autoLoad: tnB.preload()
#             if autoLoadBooks: tnB.loadBooks() # Load and process the file
#             return tnB
#         return numFound

#     # Look one level down
#     numFound = 0
#     foundProjects = []
#     for thisFolderName in sorted( foundFolders ):
#         tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
#         if not os.access( tryFolderName, os.R_OK ): # The subfolder is not readable
#             logging.warning( _("TyndaleNotesBibleFileCheck: {!r} subfolder is unreadable").format( tryFolderName ) )
#             continue
#         vPrint( 'Verbose', DEBUGGING_THIS_MODULE, "    TyndaleNotesBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
#         foundSubfolders, foundSubfiles = [], []
#         try:
#             for something in os.listdir( tryFolderName ):
#                 somepath = os.path.join( givenFolderName, thisFolderName, something )
#                 if os.path.isdir( somepath ):
#                     if something not in BibleOrgSysGlobals.COMMONLY_IGNORED_FOLDERS:
#                         foundSubfolders.append( something )
#                 elif os.path.isfile( somepath ):
#                     somethingUpper = something.upper()
#                     somethingUpperProper, somethingUpperExt = os.path.splitext( somethingUpper )
#                     ignore = False
#                     for ending in filenameEndingsToIgnore:
#                         if somethingUpper.endswith( ending): ignore=True; break
#                     if ignore: continue
#                     if not somethingUpperExt[1:] in extensionsToIgnore: # Compare without the first dot
#                         foundSubfiles.append( something )
#         except PermissionError: pass # can't read folder, e.g., system folder

#         # See if there's an Tyndale Notes Bible here in this folder
#         # if METADATA_FILENAME in foundSubfiles:
#         #     numFound += 1
#         #     if strictCheck:
#         #         for folderName in foundSubfolders:
#         #             vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "TyndaleNotesBibleFileCheckSuprised to find folder:", folderName )
#     if numFound:
#         vPrint( 'Info', DEBUGGING_THIS_MODULE, "TyndaleNotesBibleFileCheck foundProjects {} {}".format( numFound, foundProjects ) )
#         if numFound == 1 and (autoLoad or autoLoadBooks):
#             tnB = TyndaleNotesBible( foundProjects[0] )
#             if autoLoad: tnB.preload()
#             if autoLoadBooks: tnB.loadBooks() # Load and process the file
#             return tnB
#         return numFound
# # end of TyndaleNotesBibleFileCheck



class TyndaleNotesBible( Bible ):
    """
    Class to load and manipulate Tyndale Notes Bibles.

    """
    def __init__( self, sourceFilepath, givenName:Optional[str]=None, givenAbbreviation:Optional[str]=None, encoding:Optional[str]=None ) -> None:
        """
        Create the internal Tyndale Notes Bible object.

        Note that sourceFilepath can be None if we don't know that yet.
        """
         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = 'Tyndale Notes Bible object'
        self.objectTypeString = 'Tyndale Notes'

        # Now we can set our object variables
        self.givenName, self.abbreviation, self.encoding = givenName, givenAbbreviation, encoding
        if self.givenName and not self.name:
            self.name = self.givenName
        if os.path.isfile( sourceFilepath ):
            self.sourceFilepath = Path( sourceFilepath )
            self.sourceFolder = self.sourceFilepath.parent
            self.sourceFilename = self.sourceFilepath.name
        else:
            logging.critical( _("TyndaleNotesBible: Unable to discover a single filename in {}".format( sourceFilepath )) )
            self.sourceFilename = self.sourceFilepath = None
    # end of TyndaleNotesBible.__init_


    def preload( self ) -> None:
        """
        """
        fnPrint( DEBUGGING_THIS_MODULE, f"preload() from {self.sourceFilepath}" )

        assert os.path.isfile( self.sourceFilepath )

        self.preloadDone = True
    # end of TyndaleNotesBible.preload


    def loadBooks( self ) -> None:
        """
        Load all the books from the XML file.
        """
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Loading '{self.name}' from {self.sourceFolder}…" )

        if not self.preloadDone: self.preload()

        bookList:List[Tuple[BibleBook,List[str]]] = []
        loadErrors:List[str] = []
        lastBBB = None
        self.XMLTree = ElementTree().parse( self.sourceFilepath )
        if self.XMLTree.tag == 'items':
            topLocation = 'TSN file'
            BibleOrgSysGlobals.checkXMLNoText( self.XMLTree, topLocation, '4f6h', loadErrors )
            BibleOrgSysGlobals.checkXMLNoTail( self.XMLTree, topLocation, '1wk8', loadErrors )
            # Process the attributes first
            self.schemaLocation = None
            for attrib,value in self.XMLTree.items():
                if attrib == 'release':
                    self.releaseVersion = value
                else:
                    logging.warning( "fv6g Unprocessed {} attribute ({}) in {}".format( attrib, value, topLocation ) )
                    loadErrors.append( "Unprocessed {} attribute ({}) in {} (fv6g)".format( attrib, value, topLocation ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt

            for element in self.XMLTree:
                location = f"{topLocation}-{element.tag}"
                dPrint( 'Info', DEBUGGING_THIS_MODULE, f"{element} {element.text=}" )
                BibleOrgSysGlobals.checkXMLNoTail( element, location, '1wk8', loadErrors )
                assert element.tag == 'item'
                # Process the attributes first
                name = None
                for attrib,value in element.items():
                    if attrib == 'name':
                        name = value
                    elif attrib == 'typename':
                        assert value in ('StudyNote','ThemeNote','Profile'), f"{name=} {value=}"
                        # 'Profile' only occurs in TTN at Eph.1.22-23
                    elif attrib == 'product':
                        assert value == 'TyndaleOpenStudyNotes'
                    else:
                        logging.warning( "fv6g Unprocessed {} attribute ({}) in {}".format( attrib, value, topLocation ) )
                        loadErrors.append( "Unprocessed {} attribute ({}) in {} (fv6g)".format( attrib, value, topLocation ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                assert name
                if self.abbreviation == 'TSN':
                    ref = name
                    assert ref.count('.') >= 1 # Usually 2, but could be 'Psalm.142'
                    # NOTE: ref can be something like 'IISam.7.22'

                # Now work thru each item
                stateCounter = 0
                title = None
                for subelement in element:
                    dPrint( 'Info', DEBUGGING_THIS_MODULE, f"{subelement} {subelement.text=}" )
                    sublocation = f"{location}-{subelement.tag}"
                    BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, '1wk8', loadErrors )
                    BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '1wk8', loadErrors )
                    if stateCounter == 0 and self.abbreviation=='TTN':
                        assert subelement.tag == 'title'
                        title = subelement.text
                        assert title
                        stateCounter += 1
                    elif ( stateCounter == 0 and self.abbreviation=='TSN' ) \
                    or ( stateCounter == 1 and self.abbreviation=='TTN'): # these have the extra title field
                        assert subelement.tag == 'refs'
                        refs = subelement.text
                        assert refs
                        # assert refs == ref, f"{refs=} {ref=}" # Hmmh, not sure why some differ e.g., Gen.4.25-26 vs Gen.4.25-5.32
                        firstRef = refs.split('-')[0] if '-' in refs and refs.count('.')>2 else refs
                        if firstRef.count('.') == 2:
                            firstOSISBkCode, firstC, firstVs = firstRef.split( '.' )
                        else:
                            firstOSISBkCode, firstC = firstRef.split( '.' )
                            firstVs = '0'
                        if firstOSISBkCode.endswith('Thes'):
                            firstOSISBkCode += 's' # TODO: getBBBFromText should handle '1Thes'
                        BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromText( firstOSISBkCode )
                        # try: BBB2 = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromOSISAbbreviation( firstOSISBkCode )
                        # except KeyError: BBB2 = None
                        # assert BBB, f"{firstOSISBkCode=} {BBB=} {BBB2=}"
                        # if isinstance( BBB2, list ): BBB2 = BBB2[0] # Just take the first one (that's the best guess)
                        # if BBB2: assert BBB2 == BBB, f"{firstOSISBkCode} {BBB=} {BBB2=}"
                        if BBB != lastBBB: # We're into a new book
                            if lastBBB is not None: # We need to save the previous book
                                dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  Saving {lastBBB} book…")
                                self.stashBook( thisBook )
                            dPrint( 'Info', DEBUGGING_THIS_MODULE, f"Creating {BBB} book…")
                            thisBook = BibleBook( self, BBB )
                            thisBook.objectNameString = 'Tyndale Study Notes Book object'
                            thisBook.objectTypeString = 'TyndaleStudyNotes'
                            UUU = BibleOrgSysGlobals.loadedBibleBooksCodes.getUSFMAbbreviation( BBB )
                            thisBook.addLine( 'id', UUU )
                            thisBook.addLine( 'usfm', '3.0' )
                            thisBook.addLine( 'ide', 'utf-8' )
                            C = V = None
                            lastBBB = BBB
                        if firstC != C:
                            assert firstC.isdigit()
                            thisBook.addLine( 'c', firstC )
                            C = firstC
                        if title:
                            thisBook.addLine( 's1', title )
                            title = None
                        if firstVs != V: # Can be a range
                            thisBook.addLine( 'v', firstVs )
                            V = firstVs
                        stateCounter += 1
                    elif ( stateCounter == 1 and self.abbreviation=='TSN' ) \
                    or ( stateCounter == 2 and self.abbreviation=='TTN'): # these have the extra title field
                        assert subelement.tag == 'body'
                        BibleOrgSysGlobals.checkXMLNoText( subelement, sublocation, '1wk8', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, '1wk8', loadErrors )
                        pCount = 0
                        for bodyelement in subelement:
                            bodyLocation = f'{sublocation}-{bodyelement.tag}-{pCount}'
                            # print( f"{bodyelement} {bodyelement.text=}")
                            assert bodyelement.tag == 'p'
                            # Process the attributes first
                            pClass = ts = None
                            for attrib,value in bodyelement.items():
                                if attrib == 'class':
                                    pClass = value
                                    if self.abbreviation == 'TSN':
                                        # The list ones only occur at Rom.2.6-11
                                        assert pClass in ('sn-text','sn-list-1','sn-list-2','sn-list-3'), f"{refs} {pClass=} {bodyLocation}"
                                    elif self.abbreviation == 'TTN':
                                        assert pClass in ('theme-title','theme-body','theme-body-fl','theme-body-sp','theme-body-fl-sp','theme-refs-title','theme-refs','theme-list-sp','theme-list','theme-h2'), f"{refs} {pClass=} {bodyLocation}"
                                    else: halt
                                elif attrib == 'ts': # Not exactly sure what this is
                                    ts = value # Things like 'sn-text -1v -5'
                                    # TODO: We're losing this whatever it is
                                else:
                                    logging.warning( "fv6g Unprocessed {} attribute ({}) in {}".format( attrib, value, bodyLocation ) )
                                    loadErrors.append( "Unprocessed {} attribute ({}) in {} (fv6g)".format( attrib, value, bodyLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                            # So we want to extract this as an HTML paragraph
                            htmlSegment = BibleOrgSysGlobals.getFlattenedXML( bodyelement, bodyLocation )
                            # NOTE: the above doesn't have the <p class="sn-text">...</p> around it -- only the guts of the p
                            # if '<a' in htmlSegment:
                            # if BBB=='RUT' and C=='1' and V=='4':
                            #     print( f"{BBB} {C}:{V} {htmlSegment=}")
                            #     halt
                            assert '\\' not in htmlSegment
                            if self.abbreviation == 'TSN':
                                if pClass == 'sn-text':
                                    htmlSegment = htmlSegment.replace( '"sn-excerpt-divine-name"', '"sn-excerpt nd"' ).replace( '"divine-name"', '"nd"' )
                                    thisBook.appendToLastLine( f' {htmlSegment}' )
                                elif pClass.startswith( 'sn-list-' ):
                                    # TODO: We're losing the list number here
                                    thisBook.addLine( 'li', htmlSegment )
                                else: halt
                            elif self.abbreviation == 'TTN':
                                if pClass == 'theme-title':
                                    assert pCount == 0
                                    # it's the same as the title above already saved
                                elif pClass == 'theme-body':
                                    thisBook.addLine( 'p', htmlSegment )
                                elif pClass == 'theme-body-sp':
                                    thisBook.addLine( 'b', '' )
                                    thisBook.addLine( 'p', htmlSegment )
                                elif pClass == 'theme-body-fl':
                                    thisBook.addLine( 'pi', htmlSegment )
                                elif pClass == 'theme-body-fl-sp':
                                    thisBook.addLine( 'b', '' )
                                    thisBook.addLine( 'pi', htmlSegment )
                                elif pClass == 'theme-refs-title':
                                    thisBook.addLine( 's2', htmlSegment )
                                elif pClass == 'theme-h2':
                                    thisBook.addLine( 's3', htmlSegment )
                                elif pClass == 'theme-refs':
                                    thisBook.addLine( 'pi2', htmlSegment )
                                elif pClass == 'theme-list-sp':
                                    # thisBook.addLine( 'b', '' ) # Not needed before an HTML list
                                    thisBook.addLine( 'li', htmlSegment )
                                elif pClass == 'theme-list':
                                    thisBook.addLine( 'li', htmlSegment )
                                else:
                                    print( f"{pClass=} {htmlSegment=}" )
                                    halt
                            else: halt
                            pCount += 1
                            # assert pCount == 1
                        stateCounter += 1
                    else: halt

        if lastBBB is not None: # We need to save the previous book
            dPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"  Saving {lastBBB} book…")
            self.stashBook( thisBook )

        # dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"{self.getBookList()=}" )
        self.doPostLoadProcessing()
    # end of TyndaleNotesBible.load
# end of class TyndaleNotesBible



def briefDemo() -> None:
    """
    Demonstrate reading and checking some Bible databases.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    testFolderpath = Path( '/mnt/SSDs/Bibles/TyndaleHelps/en_tn/' )


    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\nTyndale Notes TestA1" )
        result1 = TyndaleNotesBibleFileCheck( testFolderpath )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "Tyndale Notes TestA1", result1 )

        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\nTyndale Notes TestA2" )
        result2 = TyndaleNotesBibleFileCheck( testFolderpath, autoLoad=True ) # But doesn't preload books
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "Tyndale Notes TestA2", result2 )
        #result2.loadMetadataFile( os.path.join( testFolderpath, "BooknamesMetadata.txt" ) )
        if BibleOrgSysGlobals.strictCheckingFlag:
            result2.check()
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, UsfmB.books['GEN']._processedLines[0:40] )
            bibleErrors = result2.getCheckResults()
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, bibleErrors )
        #if BibleOrgSysGlobals.commandLineArguments.export:
            ###result2.toDrupalBible()
            #result2.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )

        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\nTyndale Notes TestA3" )
        result3 = TyndaleNotesBibleFileCheck( testFolderpath, autoLoad=True, autoLoadBooks=True )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "Tyndale Notes TestA3", result3 )
        #result3.loadMetadataFile( os.path.join( testFolderpath, "BooknamesMetadata.txt" ) )
        if BibleOrgSysGlobals.strictCheckingFlag:
            result3.check()
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, UsfmB.books['GEN']._processedLines[0:40] )
            bibleErrors = result3.getCheckResults()
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, bibleErrors )
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
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, "\nTrying all {} discovered modules…".format( len(foundFolders) ) )
            parameters = [folderName for folderName in sorted(foundFolders)]
            BibleOrgSysGlobals.alreadyMultiprocessing = True
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.map( testBCV, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            for j, someFolder in enumerate( sorted( foundFolders ) ):
                vPrint( 'Normal', DEBUGGING_THIS_MODULE, "\nTyndale Notes D{}/ Trying {}".format( j+1, someFolder ) )
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
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\nTyndale Notes A{}/".format( count ) )
                tnB = TyndaleNotesBible( testFolder, name, encoding=encoding )
                tnB.load()
                if BibleOrgSysGlobals.verbosityLevel > 1:
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Gen assumed book name:", repr( tnB.getAssumedBookName( 'GEN' ) ) )
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Gen long TOC book name:", repr( tnB.getLongTOCName( 'GEN' ) ) )
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Gen short TOC book name:", repr( tnB.getShortTOCName( 'GEN' ) ) )
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Gen book abbreviation:", repr( tnB.getBooknameAbbreviation( 'GEN' ) ) )
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, tnB )
                if BibleOrgSysGlobals.strictCheckingFlag:
                    tnB.check()
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, UsfmB.books['GEN']._processedLines[0:40] )
                    bcbibleErrors = tnB.getCheckResults()
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, bcbibleErrors )
                if BibleOrgSysGlobals.commandLineArguments.export:
                    ##tnB.toDrupalBible()
                    tnB.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
                    newObj = BibleOrgSysGlobals.unpickleObject( BibleOrgSysGlobals.makeSafeFilename(name) + '.pickle', os.path.join( "BOSOutputFiles/", "BOS_Bible_Object_Pickle/" ) )
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "newObj is", newObj )
            else: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nSorry, test folder '{testFolder}' is not readable on this computer." )
#end of TyndaleNotesBible.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    testFolderpath = Path( '/mnt/SSDs/Bibles/DataSets/Tyndale Open Study Notes/' )

    if 0: # demo the file checking code -- first with the whole folder and then with only one folder
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\nTyndale Notes TestA1" )
        result1 = TyndaleNotesBibleFileCheck( testFolderpath )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "Tyndale Notes TestA1", result1 )

        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\nTyndale Notes TestA2" )
        result2 = TyndaleNotesBibleFileCheck( testFolderpath, autoLoad=True ) # But doesn't preload books
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "Tyndale Notes TestA2", result2 )
        #result2.loadMetadataFile( os.path.join( testFolderpath, "BooknamesMetadata.txt" ) )
        if BibleOrgSysGlobals.strictCheckingFlag:
            result2.check()
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, UsfmB.books['GEN']._processedLines[0:40] )
            bibleErrors = result2.getCheckResults()
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, bibleErrors )
        #if BibleOrgSysGlobals.commandLineArguments.export:
            ###result2.toDrupalBible()
            #result2.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )

        # vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\nTyndale Notes TestA3" )
        # result3 = TyndaleNotesBibleFileCheck( testFolderpath, autoLoad=True, autoLoadBooks=True )
        # vPrint( 'Normal', DEBUGGING_THIS_MODULE, "Tyndale Notes TestA3", result3 )
        # #result3.loadMetadataFile( os.path.join( testFolderpath, "BooknamesMetadata.txt" ) )
        # for BBB in ('GEN','RUT','JN3'):
        #     vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"{BBB} 1:1 gCVD", result3.getContextVerseData( (BBB,'1','1','') ) )
        #     vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"{BBB} 1:1 gVDL", result3.getVerseDataList( (BBB,'1','1','') ) )
        #     vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"{BBB} 1:1 gVT", result3.getVerseText( (BBB,'1','1','') ) )
        # if BibleOrgSysGlobals.strictCheckingFlag:
        #     result3.check()
        #     #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, UsfmB.books['GEN']._processedLines[0:40] )
        #     bibleErrors = result3.getCheckResults()
        #     #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, bibleErrors )
        # if BibleOrgSysGlobals.commandLineArguments.export:
        #     ##result3.toDrupalBible()
        #     result3.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )


    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\nTyndale Notes TestB" )
    result = TyndaleNotesBible( testFolderpath )
    print( f"A {result}\n" )
    result.loadBooks()
    print( f"B {result}\n" )
    return 

    if 0: # all discovered modules in the test folder
        foundFolders, foundFiles = [], []
        for something in os.listdir( testFolderpath ):
            somepath = os.path.join( testFolderpath, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )

        if BibleOrgSysGlobals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, "\nTrying all {} discovered modules…".format( len(foundFolders) ) )
            parameters = [folderName for folderName in sorted(foundFolders)]
            BibleOrgSysGlobals.alreadyMultiprocessing = True
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.map( testBCV, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            for j, someFolder in enumerate( sorted( foundFolders ) ):
                vPrint( 'Normal', DEBUGGING_THIS_MODULE, "\nTyndale Notes D{}/ Trying {}".format( j+1, someFolder ) )
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
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "\nTyndale Notes A{}/".format( count ) )
                tnB = TyndaleNotesBible( testFolder, name, encoding=encoding )
                tnB.load()
                if BibleOrgSysGlobals.verbosityLevel > 1:
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Gen assumed book name:", repr( tnB.getAssumedBookName( 'GEN' ) ) )
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Gen long TOC book name:", repr( tnB.getLongTOCName( 'GEN' ) ) )
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Gen short TOC book name:", repr( tnB.getShortTOCName( 'GEN' ) ) )
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Gen book abbreviation:", repr( tnB.getBooknameAbbreviation( 'GEN' ) ) )
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, tnB )
                if BibleOrgSysGlobals.strictCheckingFlag:
                    tnB.check()
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, UsfmB.books['GEN']._processedLines[0:40] )
                    bcbibleErrors = tnB.getCheckResults()
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, bcbibleErrors )
                if BibleOrgSysGlobals.commandLineArguments.export:
                    ##tnB.toDrupalBible()
                    tnB.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
                    newObj = BibleOrgSysGlobals.unpickleObject( BibleOrgSysGlobals.makeSafeFilename(name) + '.pickle', os.path.join( "BOSOutputFiles/", "BOS_Bible_Object_Pickle/" ) )
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "newObj is", newObj )
            else: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\nSorry, test folder '{testFolder}' is not readable on this computer." )
# end of TyndaleNotesBible.fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of TyndaleNotesBible.py
