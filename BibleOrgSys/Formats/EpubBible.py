#!/usr/bin/env -S uv run
# -\*- coding: utf-8 -\*-
# SPDX-License-Identifier: GPL-3.0-or-later
#
# EpubBible.py
#
# Module handling EPub Bible files
#
# Copyright (C) 2025 Robert Hunt
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
Module reading and loading eBible.org EPub Bible (zipped XML) files --
    see Open Container Format (OCF) spec at https://www.w3.org/TR/epub/.

OEBPS = Open eBook Publication Structure

Filenames usually end with .epub and are zip files.
"""
import logging
import os.path
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET
import multiprocessing

from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys.Bible import Bible, BibleBook
from BibleOrgSys.Internals.InternalBibleBook import BOS_CUSTOM_NESTING_MARKERS
from BibleOrgSys.Reference.BibleOrganisationalSystems import BibleOrganisationalSystem
import bos_books_codes_py


LAST_MODIFIED_DATE = '2025-07-07' # by RJH
SHORT_PROGRAM_NAME = "EpubBible"
PROGRAM_NAME = "EPub Bible format handler"
PROGRAM_VERSION = '0.02'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False


FILENAME_ENDING = '.EPUB' # Must be UPPERCASE



def EpubBibleFileCheck( givenFolderName, strictCheck:bool=True, autoLoad:bool=False, autoLoadBooks:bool=False ):
    """
    Given a folder, search for EPub Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number of Bibles found.

    if autoLoad is true and exactly one EPub Bible is found,
        returns the loaded EpubBible object.
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"EpubBibleFileCheck( {givenFolderName}, {strictCheck}, {autoLoad}, {autoLoadBooks} )" )
    if BibleOrgSysGlobals.debugFlag: assert givenFolderName and isinstance( givenFolderName, (str,Path) )
    if BibleOrgSysGlobals.debugFlag: assert autoLoad in (True,False,)

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( f"EpubBibleFileCheck: Given {givenFolderName!r} folder is unreadable" )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( f"EpubBibleFileCheck: Given {givenFolderName!r} path is not a folder" )
        return False

    # Find all the files and folders in this folder
    vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f" EpubBibleFileCheck: Looking for files in given {givenFolderName}" )
    foundFolders, foundFiles = [], []
    numFound = foundFileCount = 0
    for something in os.listdir( givenFolderName ):
        somepath = os.path.join( givenFolderName, something )
        if os.path.isdir( somepath ):
            if something in BibleOrgSysGlobals.COMMONLY_IGNORED_FOLDERS:
                continue # don't visit these directories
            foundFolders.append( something )
        elif os.path.isfile( somepath ):
            somethingUpper = something.upper()
            if somethingUpper.endswith( FILENAME_ENDING ):
                foundFiles.append( something )
                numFound += 1
    #if foundFileCount >= len(compulsoryFiles):
        #numFound = 1
    if numFound:
        vPrint( 'Info', DEBUGGING_THIS_MODULE, "EpubBibleFileCheck got", numFound, givenFolderName )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            oB = EpubBible( givenFolderName, foundFiles[0] )
            if autoLoadBooks: oB.load() # Load and process the file
            return oB
        return numFound
    elif foundFileCount and BibleOrgSysGlobals.verbosityLevel > 2: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "    Looked hopeful but no actual files found" )

    # Look one level down
    numFound = 0
    foundProjects = []
    numFound = foundFileCount = 0
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
        if not os.access( tryFolderName, os.R_OK ): # The subfolder is not readable
            logging.warning( f"EpubBibleFileCheck: {tryFolderName!r} subfolder is unreadable" )
            continue
        vPrint( 'Verbose', DEBUGGING_THIS_MODULE, f"    EpubBibleFileCheck: Looking for files in {tryFolderName}" )
        foundSubfolders, foundSubfiles = [], []
        try:
            for something in os.listdir( tryFolderName ):
                somepath = os.path.join( givenFolderName, thisFolderName, something )
                if os.path.isdir( somepath ): foundSubfolders.append( something )
                elif os.path.isfile( somepath ):
                    somethingUpper = something.upper()
                    if somethingUpper.endswith( FILENAME_ENDING ):
                        foundProjects.append( (tryFolderName,something) )
                        numFound += 1
        except PermissionError: pass # can't read folder, e.g., system folder
        #if foundFileCount >= len(compulsoryFiles):
            #foundProjects.append( tryFolderName )
            #numFound += 1
    if numFound:
        vPrint( 'Info', DEBUGGING_THIS_MODULE, "EpubBibleFileCheck foundProjects", numFound, foundProjects )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            if BibleOrgSysGlobals.debugFlag: assert len(foundProjects) == 1
            oB = EpubBible( foundProjects[0][0], foundProjects[0][1] )
            if autoLoadBooks: oB.load() # Load and process the file
            return oB
        return numFound
# end of EpubBibleFileCheck



def createEpubBible( BibleObject, outputFolder=None ):
    """
    Write the pseudo USFM out into the compressed EPub format.

    Since we don't have a specification for the format,
        and since we don't know the meaning of all the binary pieces of the file,
        we can't be certain yet that this output will actually work. :-(
    """
    # It seems 7-9 give the correct two header bytes
    ZLIB_COMPRESSION_LEVEL = 9 #  -1=default(=6), 0=none, 1=fastest…9=highest compression level

    vPrint( 'Normal', DEBUGGING_THIS_MODULE, "Running createEpubBible…" )
    if BibleOrgSysGlobals.debugFlag: assert BibleObject.books

    if not BibleObject.doneSetupGeneric: BibleObject.__setupWriter()
    if not outputFolder: outputFolder = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_EpubBible_Export/' )
    if not os.access( outputFolder, os.F_OK ): os.makedirs( outputFolder ) # Make the empty folder if there wasn't already one there

    # Set-up their Bible reference system
    BOS = BibleOrganisationalSystem( 'GENERIC-KJV-66-ENG' )

    ignoredMarkers = set()

    # Before we write the file, let's compress all our books
    # Books are written as C:V verseText with double-spaced lines
    compressedDictionary = {}
    for BBB,bookObject in BibleObject.books.items():
        if not bos_books_codes_py.is_chapter_verse_book( BBB ):
            continue # Ignore these books
        pseudoESFMData = bookObject._processedLines

        textBuffer = ''
        vBridgeStartInt = vBridgeEndInt = None # For printing missing (bridged) verse numbers
        for entry in pseudoESFMData:
            marker, text = entry.getMarker(), entry.getCleanText()
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, BBB, marker, text )
            if '¬' in marker or marker in BOS_CUSTOM_NESTING_MARKERS: continue # Just ignore added markers -- not needed here
            elif marker == 'c':
                C = int( text ) # Just so we get an error if we have something different
                V = lastVWritten = '0'
            elif marker == 'v':
                #V = text.replace( '–', '-' ).replace( '—', '-' ) # Replace endash, emdash with hyphen
                V = text
            elif marker == 'v~':
                try:
                    if int(V) <= int(lastVWritten):
                        # TODO: Not sure what level the following should be? info/warning/error/critical ????
                        logging.warning( f'createEpubBible: Maybe duplicating {BBB} {C}:{V} after {lastVWritten} with {text}' )
                        #continue
                except ValueError: pass # had a verse bridge
                if vBridgeStartInt and vBridgeEndInt: # We had a verse bridge
                    if DEBUGGING_THIS_MODULE or BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>2:
                        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"createEpubBible: handling verse bridge in {BibleObject.abbreviation} at {BBB} {C}:{vBridgeStartInt}-{vBridgeEndInt}" )
                    if 1: # new code -- copies the bridged text to all verses
                        for vNum in range( vBridgeStartInt, vBridgeEndInt+1 ): # Fill in missing verse numbers
                            textBuffer += ('\r\n\r\n' if textBuffer else '') + f'{C}:{vNum} ({VBridgedText}) {text}'
                    else: # old code
                        textBuffer += ('\r\n\r\n' if textBuffer else '') + f'{C}:{vBridgeStartInt} ({vBridgeEndInt}) {text}'
                        for vNum in range( vBridgeStartInt+1, vBridgeEndInt+1 ): # Fill in missing verse numbers
                            textBuffer += f'\r\n\r\n{C}:{vNum} (-)'
                    lastVWritten = str( vBridgeEndInt )
                    vBridgeStartInt = vBridgeEndInt = None
                else:
                    lastVWritten = V
            # elif marker == 'XXXp~':
            #     if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
            #         assert textBuffer # This is a continued part of the verse -- failed with this bad source USFM:
            #                             #     \c 1 \v 1 \p These events happened…
            #     textBuffer += f' {text}' # continuation of the same verse
            else:
                ignoredMarkers.add( marker )
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, BBB, textBuffer )
        textBuffer = textBuffer \
                        .replace( '“', '"' ).replace( '”', '"' ) \
                        .replace( "‘", "'" ).replace( "’", "'" ) \
                        .replace( '–', '--' ).replace( '—', '--' )
        bookBytes = zlib.compress( textBuffer.encode( 'utf8' ), ZLIB_COMPRESSION_LEVEL )

    if ignoredMarkers:
        logging.info( f"createEpubBible: Ignored markers were {ignoredMarkers}" )
    vPrint( 'Info', DEBUGGING_THIS_MODULE, "  " + f"WARNING: Ignored createEpubBible markers were {ignoredMarkers}" )

    # Now create a zipped version
    filepath = os.path.join( outputFolder, filename )
    vPrint( 'Info', DEBUGGING_THIS_MODULE, f"  Zipping {filename} EWB file…" )
    zf = zipfile.ZipFile( filepath+'.zip', 'w', compression=zipfile.ZIP_DEFLATED )
    zf.write( filepath, filename )
    zf.close()

    if BibleOrgSysGlobals.verbosityLevel > 0 and BibleOrgSysGlobals.maxProcesses > 1:
        vPrint( 'Quiet', DEBUGGING_THIS_MODULE, "  BibleWriter.createEpubBible finished successfully." )
    return True
# end of createEpubBible



BOS = None

class EpubBible( Bible ):
    """
    Class for reading, validating, and converting EpubBible files.

    KJV OT has 23,145 verses = 5A69 in 39 = 27 books
        NT has  7,957 verses = 1F15 in 27 = 1B books
        Total  31,102 verses = 797E in 66 = 42 books
    """
    def __init__( self, sourceFolder, sourceFilename ) -> None:
        """
        Constructor: just sets up the Bible object.
        """
        fnPrint( DEBUGGING_THIS_MODULE, f"EpubBible.__init__( {sourceFolder}, {sourceFilename} )" )
         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = 'EPub Bible object'
        self.objectTypeString = 'EWB'

        # Now we can set our object variables
        self.sourceFolder, self.sourceFilename = sourceFolder, sourceFilename
        self.sourceFilepath =  os.path.join( self.sourceFolder, self.sourceFilename )

        # Do a preliminary check on the readability of our file
        if not os.access( self.sourceFilepath, os.R_OK ):
            logging.critical( f"EpubBible: File {self.sourceFilepath!r} is unreadable" )

        global BOS
        if BOS is None: BOS = BibleOrganisationalSystem( 'GENERIC-KJV-66-ENG' )

        assert FILENAME_ENDING in self.sourceFilename.upper()
        self.abbreviation = os.path.splitext( self.sourceFilename)[0] # Remove file extension
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, self.sourceFilename, self.abbreviation )

        self.preloaded = False
    # end of EpubBible.__init__


    def preload( self ):
        """
        Load the compressed data file and import book objects.
        """
        fnPrint( DEBUGGING_THIS_MODULE, "EpubBible.preload()" )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nLoading {self.sourceFilepath}…" )

        self.inputZipfile = ZipFile( self.sourceFilepath )
        zipFileNameList = self.inputZipfile.namelist()
        # dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Got filelist ({len(zipFileNameList)}) {zipFileNameList} from {self.sourceFilepath}" )

        assert 'mimetype' in zipFileNameList
        mimetypeStr = self.inputZipfile.read( 'mimetype' ).decode( 'utf-8' )
        # dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Got mimetype ({len(mimetypeStr)}) {mimetypeStr=}" )
        assert mimetypeStr == 'application/epub+zip'

        metafileList = [f for f in zipFileNameList if f.startswith( 'META-INF/' )]
        dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Got metafile list ({len(metafileList)}) {metafileList}" )
        assert 'META-INF/container.xml' in metafileList
        containerXML = self.inputZipfile.read( 'META-INF/container.xml' ).decode( 'utf-8' )
        # dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Got container XML ({len(containerXML)}) {containerXML}" )
        ixStart = containerXML.index( '<rootfile full-path="' )
        ixEnd = containerXML.index( '"', ixStart+21+1 )
        rootFilepath = containerXML[ixStart+21:ixEnd]
        dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Got {rootFilepath=}" )
        # assert rootFilepath.endswith( 'content.opf' )
        assert rootFilepath == 'OEBPS/content.opf' # OEBPS = Open eBook Publication Structure

        contentOPF = self.inputZipfile.read( rootFilepath ).decode( 'utf-8' )
        # dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Got content OPF XML ({len(contentOPF)}) {contentOPF}" )
        contentTree = ET.fromstring( contentOPF )
        # XMLNameSpace = "{http://www.idpf.org/2007/opf}"
        location = 'ePub contents'
        manifestDict = {}
        spineEntries = []
        for element in contentTree:
            # dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Got element {element.tag} ({len(element)}) {element}" )
            # tag = element.tag[len(XMLNameSpace):]
            BibleOrgSysGlobals.checkXMLNoText( element, location, '5g78' )
            BibleOrgSysGlobals.checkXMLNoTail( element, location, 'al1d' )
            location = f'{location}-{element.tag}'
            if element.tag.endswith( '}metadata' ):
                BibleOrgSysGlobals.checkXMLNoAttributes( element, location, 'ks01' )
                for subelement in element:
                    sublocation = f'{location}-metadata'
                    # dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Got metadata element {subelement.tag} ({len(subelement)}) {subelement}" )
                    if subelement.tag.endswith( '}title' ):
                        # dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Got spine subelement {subelement.tag} ({len(subelement)}) {subelement}" )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, 'cdb2' )
                        # BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, '9s2d' ) # id=title
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, 'kxs1' )
                        dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Title = {subelement.text}" )
                    elif subelement.tag.endswith( '}language' ):
                        # dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Got spine subelement {subelement.tag} ({len(subelement)}) {subelement}" )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, 'dkv3' )
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, 'kk32' )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, 'll23' )
                        dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Language = {subelement.text}" )
                    elif subelement.tag.endswith( '}identifier' ):
                        # dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Got spine subelement {subelement.tag} ({len(subelement)}) {subelement}" )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, 'z02l' )
                        # BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, 'las0' ) # id=uid
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, 'ks10' )
                        dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Identifier = {subelement.text}" )
                    elif subelement.tag.endswith( '}rights' ):
                        # dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Got spine subelement {subelement.tag} ({len(subelement)}) {subelement}" )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, 'z02l' )
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, 'las0' )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, 'ks10' )
                        dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Rights = {subelement.text}" )
                    elif subelement.tag.endswith( '}meta' ):
                        dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Got spine subelement {subelement.tag} ({len(subelement)}) {subelement}" )
                        BibleOrgSysGlobals.checkXMLNoText( subelement, sublocation, 'ls02' )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, 'kas1' )
                        # BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, 'kas4' )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, 'kgf0' )
                        dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Rights = {subelement.text}" )
                    else: raise ValueError( f"Unexpected EPub content metadata frame: {subelement.tag}" )
            elif element.tag.endswith( '}manifest' ): # gives a unordered list of books
                BibleOrgSysGlobals.checkXMLNoAttributes( element, location, 'j3jd' )
                for subelement in element:
                    sublocation = f'{location}-manifest'
                    # dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Got manifest element {subelement.tag} ({len(subelement)}) {subelement}" )
                    if subelement.tag.endswith( '}item' ):
                        # dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Got spine subelement {subelement.tag} ({len(subelement)}) {subelement}" )
                        BibleOrgSysGlobals.checkXMLNoText( subelement, sublocation, 'xv3d' )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, 'kjs2' )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, 'ks2f' )
                        href = itemID = mediaType = None
                        for attrib,value in subelement.items():
                            if attrib=='href': href = value
                            elif attrib=="id": itemID = value
                            elif attrib=="media-type": mediaType = value
                            else: logging.warning( f"Unprocessed '{attrib}' attribute ({value}) in content subelement" )
                        manifestDict[itemID] = href
                    else: raise ValueError( f"Unexpected EPub content manifest frame: {subelement.tag}" )
                dPrint( 'Info', DEBUGGING_THIS_MODULE, f"Got manifest entries ({len(manifestDict)}) {manifestDict}" )
            elif element.tag.endswith( '}spine' ): # tells us the book order
                toc = None
                for attrib,value in element.items():
                    if attrib=='toc': toc = value
                    else: logging.warning( f"Unprocessed '{attrib}' attribute ({value}) in spine element" )
                assert toc == 'ncx'
                for subelement in element:
                    sublocation = f'{location}-spine'
                    # dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Got spine element {subelement.tag} ({len(subelement)}) {subelement}" )
                    if subelement.tag.endswith( '}itemref' ):
                        # dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Got spine subelement {subelement.tag} ({len(subelement)}) {subelement}" )
                        BibleOrgSysGlobals.checkXMLNoText( subelement, sublocation, '5w78' )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, 'alpd' )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, 'g2jd' )
                        idref = linear = None
                        for attrib,value in subelement.items():
                            if attrib=='idref': idref = value
                            elif attrib=="linear": linear = value
                            else: logging.warning( f"Unprocessed '{attrib}' attribute ({value}) in spine subelement" )
                        assert idref in manifestDict
                        spineEntries.append( (idref,linear) )
                    else: raise ValueError( f"Unexpected EPub content spine frame: {subelement.tag}" )
                dPrint( 'Info', DEBUGGING_THIS_MODULE, f"Got spine entries ({len(spineEntries)}) {spineEntries}" )
            else: raise ValueError( f"Unexpected EPub content frame: {element.tag}" )

        self.ePubBookDict = {(idref[1:] if idref[0]=='x' and len(idref)==4 else idref):manifestDict[idref] for idref,_linear in spineEntries}
        dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Got ePubBookDict entries ({len(self.ePubBookDict)}) {self.ePubBookDict}" )
        self.preloaded = True
    # end of EpubBible.preload

    NAME_SPACE = '{http://www.w3.org/1999/xhtml}'
    def loadBook( self, BBB ):
        """
        Load the requested book out of the zipped container.
        """
        fnPrint( DEBUGGING_THIS_MODULE, f"EpubBible.loadBook( {BBB} )" )
        if not self.preloaded: self.preload()

        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Loading {BBB}…" )
        UUU = bos_books_codes_py.bos_book_code_to_usfm_abbrev( BBB )
        uuu = UUU.lower()
        bookFilename = self.ePubBookDict[uuu]
        bookXMLContent = self.inputZipfile.read( f'OEBPS/{bookFilename}' ).decode( 'utf-8' )
        # dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Got {BBB} XML ({len(bookXMLContent)}) {bookXMLContent}" )
        bookTree = ET.fromstring( bookXMLContent )

        # Firstly, we have to get the footnotes (if any) from the end of the file
        notes = {}
        for body in bookTree.findall( '{http://www.w3.org/1999/xhtml}body' ):
            # print( f"Got {BBB} {body=}" )
            for div1 in body.findall( '{http://www.w3.org/1999/xhtml}div' ):
                # print( f" Got {BBB} {div1=}" )
                for div2 in div1.findall( '{http://www.w3.org/1999/xhtml}div' ):
                    # print( f"  Got {BBB} {div2=}" )
                    for aside in div2.findall( '{http://www.w3.org/1999/xhtml}aside' ):
                        print( f"   Got {BBB} {aside=}" )
                        asideType = asideID = None
                        for attrib,value in aside.items():
                            if attrib=='id': asideID = value
                            elif attrib=='{http://www.idpf.org/2007/ops}type': asideType = value
                            else: logging.warning( f"Unprocessed '{attrib}' attribute ({value}) in aside" )
                        assert asideType == 'footnote'
                        asideStr = BibleOrgSysGlobals.elementStr(aside)
                        print( f"{asideStr=}" )
                        ft = asideStr.split( "'ft' Text='", 1 )[-1]
                        ft = ft.replace( "',SubSubElement '{http://www.w3.org/1999/xhtml}span': Attribs: class='fqa' Text='", '\\fqa ' ) \
                               .replace( "',SubSubElement '{http://www.w3.org/1999/xhtml}span': Attribs: class='ft' Text='", '\\ft ' ) \
                               .replace( "' Tail='\\n\\n'", '' ).replace( "' Tail='\\n'", '' )
                        assert 'Sub' not in ft and 'Attribs' not in ft and 'Text=' not in ft
                        print( f"{ft=}" )
                        assert asideID not in notes
                        notes[asideID] = ft

        thisBook = BibleBook( self, BBB )
        thisBook.objectNameString = 'ePub Bible Book object'
        thisBook.objectTypeString = 'ePub'

        # loadErrors:list[str] = []
        location = f'{BBB} book contents'
        lastC = None
        for element in bookTree:
            dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"loadBook got element {element.tag} ({len(element)})" )
            elementTag = element.tag[len(self.NAME_SPACE):]
            location = f'{location}-{elementTag}'
            BibleOrgSysGlobals.checkXMLNoText( element, location, 'bf03' )
            BibleOrgSysGlobals.checkXMLNoTail( element, location, 'zf23' )
            BibleOrgSysGlobals.checkXMLNoAttributes( element, location, 'm4d2' )
            if elementTag == 'head':
                pass # Don't need any of this yet
            elif elementTag == 'body':
                BibleOrgSysGlobals.checkXMLNoText( element, location, 'k874' )
                BibleOrgSysGlobals.checkXMLNoTail( element, location, 'dj69' )
                BibleOrgSysGlobals.checkXMLNoAttributes( element, location, 'j8jf' )
                for subelement in element:
                    dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"loadBook got subelement {subelement.tag} ({len(subelement)})" )
                    subelementTag = subelement.tag[len(self.NAME_SPACE):]
                    sublocation = f'{location}-{subelementTag}'
                    BibleOrgSysGlobals.checkXMLNoText( subelement, sublocation, '4gfd' )
                    BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '65hg' )
                    if subelementTag == 'ul':
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, '7hf4' )
                        pass
                    elif subelementTag == 'div':
                        divClass = None
                        for attrib,value in subelement.items():
                            if attrib=='class': divClass = value
                            # elif attrib=="id": itemID = value
                            # elif attrib=="media-type": mediaType = value
                            else: logging.warning( f"Unprocessed '{attrib}' attribute ({value}) in div subelement" )
                        for sub2element in subelement:
                            # dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"loadBook got sub2element {sub2element.tag} ({len(sub2element)})" )
                            sub2elementTag = sub2element.tag[len(self.NAME_SPACE):]
                            sub2location = f'{sublocation}-{sub2elementTag}'
                            BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2location, '2hdf' )
                            # BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, sub2location, '0d92' )
                            if sub2elementTag == 'div':
                                div2Class = div2ID = None
                                for attrib,value in sub2element.items():
                                    if attrib=='class': div2Class = value
                                    elif attrib=='div2ID': div2ID = value
                                    else: logging.warning( f"Unprocessed '{attrib}' attribute ({value}) in div2 subelement" )
                                if div2Class in ('mt','mt1','mt2'):
                                    BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2location, '6d42' )
                                    thisBook.addLine( div2Class, sub2element.text.rstrip() )
                                elif div2Class == 'b':
                                    BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2location, 'kh85' )
                                    assert sub2element.text == ' \xa0 ', f"{sub2element.text=}" # NBSP
                                    thisBook.addLine( 'b', '' )
                                elif div2Class in ('p','q','q1','q2'):
                                    # BibleOrgSysGlobals.checkXMLNoText( sub2element, sub2location, 'bbde' )
                                    text = sub2element.text.rstrip( '\n' ) if sub2element.text else ''
                                    thisBook.addLine( div2Class, text )
                                    for sub3element in sub2element:
                                        # dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"loadBook got sub3element {sub3element.tag} ({len(sub3element)})" )
                                        sub3elementTag = sub3element.tag[len(self.NAME_SPACE):]
                                        sub3location = f'{sub2location}-{sub3elementTag}'
                                        # BibleOrgSysGlobals.checkXMLNoText( sub3element, sub3location, 'jk84' )
                                        # BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3location, '4dk7' )
                                        # BibleOrgSysGlobals.checkXMLNoAttributes( sub3element, sublocation, 'sf92' )
                                        BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3location, 'sfg6' )
                                        tail = sub3element.tail.rstrip( '\n' ) if sub3element.tail else ''
                                        if sub3elementTag == 'span': # Contains the verse number
                                            # BibleOrgSysGlobals.checkXMLNoText( sub3element, sub3location, 'mhj9' )
                                            # BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3location, 'mnb2' )
                                            # BibleOrgSysGlobals.checkXMLNoAttributes( sub3element, sublocation, 'mw9w' )
                                            BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3location, 'ad20' )
                                            spanClass = spanID = None
                                            for attrib,value in sub3element.items():
                                                if attrib=='class': spanClass = value
                                                elif attrib=="id": spanID = value
                                                # elif attrib=="media-type": mediaType = value
                                                else: logging.warning( f"Unprocessed '{attrib}' attribute ({value}) in p-span sub3element" )
                                            if spanClass == 'verse':
                                                # print( f"{spanClass=} {spanID=}" )
                                                C, V = spanID[2:].split( '_' )
                                                c, v = int(C), int(V)
                                                # print( f"{BBB} {C}:{V}" )
                                                if C != lastC:
                                                    thisBook.addLine( 'c', C )
                                                    lastC = C
                                                thisBook.addLine( 'v', f'{V} {tail}')
                                            elif spanClass == 'add':
                                                assert spanID is None
                                                thisBook.appendToLastLine( f'\\add {sub3element.text}\\add*{tail}')
                                            else: raise ValueError( f"Unknown EPub {BBB} div2-p-span frame: {sub3elementTag} {spanClass=} {spanID=}" )
                                        elif sub3elementTag == 'div': # When a paragraph crosses a chapter boundary
                                            # BibleOrgSysGlobals.checkXMLNoText( sub3element, sub3location, 'mhj9' )
                                            BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3location, 'mnb2' )
                                            # BibleOrgSysGlobals.checkXMLNoAttributes( sub3element, sublocation, 'mw9w' )
                                            BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3location, 'ad20' )
                                            divClass = divID = None
                                            for attrib,value in sub3element.items():
                                                if attrib=='class': divClass = value
                                                elif attrib=="id": divID = value
                                                else: logging.warning( f"Unprocessed '{attrib}' attribute ({value}) in p-div sub3element" )
                                            if divClass == 'psalmlabel':
                                                # print( f"{spanClass=} {spanID=}" )
                                                C, V = divID[2:].split( '_' )
                                                assert V == '0'
                                                c, v = int(C), int(V)
                                                # print( f"{BBB} {C}:{V}" )
                                                if C != lastC:
                                                    thisBook.addLine( 'c', C )
                                                    lastC = C
                                            else: raise ValueError( f"Unknown EPub {BBB} div2-p-span frame: {sub3elementTag} {spanClass=} {spanID=}" )
                                        elif sub3elementTag == 'a': # Used for footnotes
                                            # BibleOrgSysGlobals.checkXMLNoText( sub3element, sub3location, 'mhj9' )
                                            BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3location, 'mnb2' )
                                            # BibleOrgSysGlobals.checkXMLNoAttributes( sub3element, sublocation, 'mw9w' )
                                            BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3location, 'ad20' )
                                            aHref = aType = aClass = None
                                            for attrib,value in sub3element.items():
                                                if attrib=='href': aHref = value
                                                elif attrib=='{http://www.idpf.org/2007/ops}type': aType = value
                                                elif attrib=='class': aClass = value
                                                else: logging.warning( f"Unprocessed '{attrib}' attribute ({value}) in p-div sub3element" )
                                            aKey = aHref[1:]
                                            if aClass == 'noteref':
                                                thisBook.appendToLastLine( '\\f + \\fr {C}:{V} \\ft {notes[aKey]}\\f*' )
                                            else: raise ValueError( f"Unknown EPub {BBB} div2-p-span frame: {sub3elementTag} {spanClass=} {spanID=}" )
                                        else: raise ValueError( f"Unexpected EPub {BBB} div2-p frame: {sub3elementTag}" )
                                else:
                                    # print( f"{div2Class=}" )
                                    # BibleOrgSysGlobals.checkXMLNoText( sub2element, sub2location, '6df2' ) # Ignore the verse number
                                    for sub3element in sub2element:
                                        dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"loadBook got sub3element {sub3element.tag} ({len(sub3element)})" )
                                        sub3elementTag = sub3element.tag[len(self.NAME_SPACE):]
                                        sub3location = f'{sub2location}-{sub3elementTag}'
                                        # BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3location, '4dk7' )
                                        if sub3elementTag == 'span':
                                            BibleOrgSysGlobals.checkXMLNoText( sub3element, sub3location, '9glk' )
                                            BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3location, 'af7k' )
                                            BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3location, 'f25g' )
                                            spanClass = None
                                            for attrib,value in subelement.items():
                                                if attrib=='class': spanClass = value
                                                # elif attrib=="id": itemID = value
                                                # elif attrib=="media-type": mediaType = value
                                                else: logging.warning( f"Unprocessed '{attrib}' attribute ({value}) in span sub3element" )
                                        elif sub3elementTag == 'hr':
                                            BibleOrgSysGlobals.checkXMLNoText( sub3element, sub3location, '8dk3' )
                                            BibleOrgSysGlobals.checkXMLNoAttributes( sub3element, sublocation, 'lp85' )
                                            BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3location, '98d3' )
                                            pass # Ignore
                                        elif sub3elementTag == 'aside':
                                            BibleOrgSysGlobals.checkXMLNoText( sub3element, sub3location, '8dk4' )
                                            pass # Already processed above
                                        else: raise ValueError( f"Unexpected EPub {BBB} div2 frame: {sub3elementTag}" )
                            else: raise ValueError( f"Unexpected EPub {BBB} div frame: {sub2elementTag}" )
                    else: raise ValueError( f"Unexpected EPub {BBB} body frame: {subelementTag}" )
            else: raise ValueError( f"Unexpected EPub {BBB} book frame: {elementTag}" )
        self.stashBook( thisBook )
    # end of EpubBible.load


    def load( self ):
        """
        Load all the books out of the zipped container.
        """
        fnPrint( DEBUGGING_THIS_MODULE, "EpubBible.load()" )
        if not self.preloaded: self.preload()

        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Loading ePub books from {self.sourceFilepath}…" )
        loadErrors:list[str] = []

        for idref,_bookPath in self.ePubBookDict.items():
            # dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"{idref=} {_bookPath=}" )
            if len(idref)==3:
                BBB = bos_books_codes_py.usfm_abbrev_to_bos_book_code( idref.upper() )
                self.loadBook( BBB )
    # end of EpubBible.load
# end of EpubBible class



def testEPub( TEWBfilename ):
    # Crudely demonstrate the EPub Bible class
    from BibleOrgSys.Reference import VerseReferences
    BiblesFolderpath = Path( '/srv/Bibles/' )
    #testFolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'EpubBible/' )
    testFolder = BiblesFolderpath.joinpath( 'EPub Bibles/' )
    testFolder = BiblesFolderpath.joinpath( 'EPub Bibles/Haiola EPub3 versions/' )

    #TEWBfolder = os.path.join( testFolder, TEWBfilename+'/' )
    TEWBfolder = testFolder
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, "Demonstrating the EPub Bible class…" )
    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"  Test folder is {TEWBfolder!r} {TEWBfilename!r}" )
    ePub = EpubBible( TEWBfolder, TEWBfilename )
    keep = ePub.load() # Load and process the file
    vPrint( 'Normal', DEBUGGING_THIS_MODULE, ePub ) # Just print a summary
    if BibleOrgSysGlobals.strictCheckingFlag:
        ePub.check()
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, UsfmB.books['GEN']._processedLines[0:40] )
        ewbErrors = ePub.getCheckResults()
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, ewbErrors )
    if BibleOrgSysGlobals.commandLineArguments.export:
        ##ewb.toDrupalBible()
        ePub.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
    for reference in ( ('OT','GEN','1','1'), ('OT','GEN','1','3'), ('OT','PSA','3','0'), ('OT','PSA','3','1'), \
                        ('OT','DAN','1','21'),
                        ('OT','ZEC','2','6'),('OT','ZEC','2','7'), # Bridged in MBTV and GNT
                        ('NT','MAT','3','5'), ('NT','JDE','1','4'), ('NT','REV','22','21'), \
                        ('DC','BAR','1','1'), ('DC','MA1','1','1'), ('DC','MA2','1','1',), ):
        (t, b, c, v) = reference
        if t=='OT' and len(ePub)==27: continue # Don't bother with OT references if it's only a NT
        if t=='NT' and len(ePub)==39: continue # Don't bother with NT references if it's only a OT
        if t=='DC' and len(ePub)<=66: continue # Don't bother with DC references if it's too small
        svk = VerseReferences.SimpleVerseKey( b, c, v )
        #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, svk, ewb.getVerseDataList( reference ) )
        shortText = svk.getShortText()
        try:
            verseText = ePub.getVerseText( svk )
            fullVerseText = ePub.getVerseText( svk, fullTextFlag=True )
        except KeyError:
            verseText = fullVerseText = "Verse not available!"
        if BibleOrgSysGlobals.verbosityLevel > 1:
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, reference, shortText, verseText )
            dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f'  {fullVerseText}' )
    return keep
# end of testEPub


def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    BiblesFolderpath = Path( '/srv/Bibles/' )
    testFolder = BiblesFolderpath.joinpath( 'EPub Bibles/Haiola EPub3 versions/' )


# end of EpubBible.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    BiblesFolderpath = Path( '/srv/Bibles/' )
    testFolder = BiblesFolderpath.joinpath( 'EPub Bibles/Haiola EPub3 versions/' )


    if 0: # demo the file checking code -- first with the whole folder and then with only one folder
        result1 = EpubBibleFileCheck( testFolder )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "EPub TestA1", result1 )
        result2 = EpubBibleFileCheck( testFolder, autoLoad=True )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "EPub TestA2", result2 )
        result3 = EpubBibleFileCheck( testFolder, autoLoadBooks=True )
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, "EPub TestA3", result3 )

        #testSubfolder = os.path.join( testFolder, 'AV/' )
        #result3 = EpubBibleFileCheck( testSubfolder )
        #dPrint( 'Normal', DEBUGGING_THIS_MODULE, "EPub TestB1", result3 )
        #result4 = EpubBibleFileCheck( testSubfolder, autoLoad=True )
        #dPrint( 'Normal', DEBUGGING_THIS_MODULE, "EPub TestB2", result4 )
        #result5 = EpubBibleFileCheck( testSubfolder, autoLoadBooks=True )
        #dPrint( 'Normal', DEBUGGING_THIS_MODULE, "EPub TestB3", result5 )

    if 1: # specified module
        singleModule = 'eng-asv.epub'
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nEPub C/ Trying {singleModule}" )
        #myTestFolder = os.path.join( testFolder, singleModule+'/' )
        #testFilepath = os.path.join( testFolder, singleModule+'/', singleModule+'_utf8.txt' )
        testEPub( singleModule )

    if 0: # specified modules
        allModulesKeepDict = {}
        one = ( 'asv.ewb', )
        good = ( 'alb.ewb','amp.ewb','asv.ewb','bbe.ewb','cei.ewb','darby.ewb',
                'dn1933.ewb','dnb1930.ewb','drv.ewb',
                'esv.ewb','esv.ewb_0','esv.ewb_2',
                'fn1938.ewb', 'hcv.ewb','kar.ewb','kjv.ewb',
                'lsg.ewb','luth1545.ewb', 'maori.ewb', 'mbtv.ewb',
                'nasb.ewb','niv.ewb','nkjv.ewb', 'sv1917.ewb', 'TB.ewb',
                'vul.ewb', 'wb.ewb', 'ylt.ewb' )
        nonEnglish = (  )
        bad = ( 'aa.ewb','gkm.ewb','gnt.ewb','hcsb.ewb','msg.ewb','rsv.ewb' )
        allModules = good + bad
        for j, testFilename in enumerate( good ): # Choose one of the above: good, nonEnglish, bad, allModules
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nEPub D{j+1}/ Trying {testFilename}" )
            #myTestFolder = os.path.join( testFolder, testFilename+'/' )
            #testFilepath = os.path.join( testFolder, testFilename+'/', testFilename+'_utf8.txt' )
            allModulesKeepDict[testFilename] = testEPub( testFilename )
        if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE and len(allModulesKeepDict)>1:
            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"\n\nCollected data blocks from all {len(allModulesKeepDict)} processed versions:" )
            # Print the various binary blocks together by block number
            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, allModulesKeepDict['alb.ewb'].keys() )
            #for blockName in ('introBlock','moduleNameBlock','byte84','workNameBlock','workName','bookDataStartIndex','block0080','endBytes'):
            for blockName in allModulesKeepDict['alb.ewb'].keys():
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, '' )
                for moduleFilename,stuff in allModulesKeepDict.items():
                    if blockName in stuff:
                        index,result = stuff[blockName]
                        if blockName == 'introBlock': # Nice and consistent (32-bytes)
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, blockName, index, len(result), hexlify(result), result, moduleFilename, )
                            assert index == 0
                            assert result == b'EPub Bible Text\x1a\x02<\x00\x00\x00\xe0\x00\x00\x00'
                        elif blockName == 'moduleNameBlock':
                            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, blockName, index, len(result), hexlify(result), result, moduleFilename, )
                        elif blockName == 'byte84': # revision number or something ???
                            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, blockName, index, result, moduleFilename, )
                        #elif blockName in ('bookInfoBlock-1','bookInfoBlock-66'):
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, blockName, index, len(result), hexlify(result), result, moduleFilename, )
                        elif blockName == 'workNameBlock':
                            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, blockName, index, len(result), hexlify(result), result, moduleFilename, )
                        elif blockName == 'length3':
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, blockName, index, result, moduleFilename, )
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, result )
                            assert 26 <= result <= 32
                        elif blockName == 'workName':
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, blockName, index, len(result), result, moduleFilename )
                            assert index == 14876
                        elif blockName == 'workNameAppendage': # Nice and consistent (4-bytes)
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, blockName, index, len(result), hexlify(result), result, moduleFilename, )
                            assert len(result) == 6
                            assert result[:4] == b'QK\x03\x04'
                            assert result[4] < 16 # Length of uncompressed work name
                            assert result[5:] == b'\x00'
                        elif blockName == 'block0080': # Nice and consistent (4-bytes)
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, blockName, index, len(result), hexlify(result), result, moduleFilename, )
                            assert result == b'\x00\x00\x08\x00'
                        elif blockName == 'bookDataStartIndex':
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, blockName, index, result, moduleFilename, )
                            assert 14902 <= result <= 14908
                        elif blockName == 'endBytes': # Nice and consistent (16-bytes)
                            #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, blockName, index, len(result), hexlify(result), result, moduleFilename, )
                            assert result == b'\x18:\x00\x00\x00\x00\x00\x00ezwBible' # b'183a000000000000657a774269626c65'
                        elif not blockName.startswith( 'bookInfoBlock-' ) \
                        and not blockName.startswith( 'bookExtra-' ):
                            # Shouldn't get here
                            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, blockName, index, len(result), hexlify(result), result, moduleFilename, )
                            if DEBUGGING_THIS_MODULE: assert False, "We want to stop here"


    if 0: # all discovered modules in the test folder
        foundFolders, foundFiles = [], []
        for something in os.listdir( testFolder ):
            somepath = os.path.join( testFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )

        if BibleOrgSysGlobals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nTrying all {len(foundFolders)} discovered modules…" )
            parameters = [folderName for folderName in sorted(foundFolders)]
            BibleOrgSysGlobals.alreadyMultiprocessing = True
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.map( testEPub, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            for j, someFolder in enumerate( sorted( foundFolders ) ):
                vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nEPub E{j+1}/ Trying {someFolder}" )
                #myTestFolder = os.path.join( testFolder, someFolder+'/' )
                testEPub( someFolder )
# end of EpubBible.fullDemo

if __name__ == '__main__':
    multiprocessing.set_start_method('fork') # The default was changed on POSIX systems from 'fork' to 'forkserver' in Python3.14
    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of EpubBible.py
