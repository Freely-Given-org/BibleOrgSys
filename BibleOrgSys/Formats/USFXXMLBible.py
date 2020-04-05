#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# USFXXMLBible.py
#
# Module handling USFX XML Bibles
#
# Copyright (C) 2013-2019 Robert Hunt
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
Module for defining and manipulating complete or partial USFX Bibles.
    <?xml version="1.0" encoding="utf-8"?><usfx xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="usfx.xsd"><languageCode>zia</languageCode><book id="MAT"><id id="MAT">NT0018.MT
    </id><h>MATIU
    </h><toc level="1">BOWI IWAING MATIU MENE GAENA
    </toc><toc level="2">MATIU
    </toc><toc level="3">Mt
    </toc><p sfm="mt">BOWI IWAING MATIU MENE GAENA
    </p><p sfm="ip"><it>Matiu, nung Yesura buro-mani 12 auna zo. Yazo nuna zo Lewi. Nung Yesura ungwe Yuda emo otao mani nuna eno gaena, arare nung porofetera ge gayao witao awiya ge nuna-una susuuno gaena. Awiya Yesu nung Yuda emora Mesia me awiya gipai gaese sero ayero yena ara.
    </it>
    </p><c id="1"/>
    <s>Yesu Kristora aya-ewowo auna yazo.
    </s><p sfm="r"><ref tgt="LUK.3.23">Lu 3:23-38</ref>
    </p><p><v id="1" bcv="MAT.1.1"/>Emo kasa yero butunawe duwa Yesu Kristo nung Abrahamto Dawidira saisibuna nunato zo mene kasa yena, auna ungwe.
    <ve/></p><p sfm="li"><v id="2" bcv="MAT.1.2"/>Abraham nung Isakara mfaung.
    </p><p sfm="li">Isaka nung Yakobora maung. Yakobo nung Yuda meta maingne auna maung.
    <ve/></p><p sfm="li"><v id="3" bcv="MAT.1.3"/>Yuda nung Pereseto Zerara maung. Ai nunato awiya Tema.
    <ve/></p><p sfm="li"><v id="4" bcv="MAT.1.4"/>Ramu nung Aminadapra maung. Aminadap nung Nasonna maung.
    <ve/></p><p sfm="li"><v id="5" bcv="MAT.1.5"/>Salamon nung Boasira maung. Boasira ai awiya Rehap.
    <ve/></p><p sfm="li"><v id="6" bcv="MAT.1.6"/>Zesi nung emo tuwa Dawidi auna maung. Dawidi nung
    </p><p sfm="li">Solomonna maung. Solomonna ai awiya Yurayara bauno noi.
    …
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2019-02-04' # by RJH
SHORT_PROGRAM_NAME = "USFXBible"
PROGRAM_NAME = "USFX XML Bible handler"
PROGRAM_VERSION = '0.33'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'
programNameVersionDate = f'{programNameVersion} {_("last modified")} {LAST_MODIFIED_DATE}'

debuggingThisModule = False


import os, sys, logging, multiprocessing
from xml.etree.ElementTree import ElementTree, ParseError

if __name__ == '__main__':
    import sys
    aboveAboveFolderPath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderPath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderPath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.Bible import Bible, BibleBook



filenameEndingsToIgnore = ('.ZIP.GO', '.ZIP.DATA',) # Must be UPPERCASE
extensionsToIgnore = ( 'ASC', 'BAK', 'BAK2', 'BAK3', 'BAK4', 'BBLX', 'BC', 'CCT', 'CSS', 'DOC', 'DTS', 'HTM','HTML',
                    'JAR', 'LDS', 'LOG', 'MYBIBLE', 'NT','NTX', 'ODT', 'ONT','ONTX', 'OSIS', 'OT','OTX', 'PDB',
                    'SAV', 'SAVE', 'STY', 'SSF', 'TXT', 'USFM', 'USX', 'VRS', 'YET', 'ZIP', ) # Must be UPPERCASE and NOT begin with a dot



def USFXXMLBibleFileCheck( sourceFolder, strictCheck=True, autoLoad=False, autoLoadBooks=False ):
    """
    Given a folder, search for USFX XML Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number found.

    if autoLoad is true and exactly one USFX Bible is found,
        returns the loaded USFXXMLBible object.
    """
    if BibleOrgSysGlobals.verbosityLevel > 2: print( "USFXXMLBibleFileCheck( {}, {}, {}, {} )".format( sourceFolder, strictCheck, autoLoad, autoLoadBooks ) )
    if BibleOrgSysGlobals.debugFlag: assert sourceFolder and isinstance( sourceFolder, str )
    if BibleOrgSysGlobals.debugFlag: assert autoLoad in (True,False,)

    # Check that the given folder is readable
    if not os.access( sourceFolder, os.R_OK ):
        logging.critical( _("USFXXMLBibleFileCheck: Given {!r} folder is unreadable").format( sourceFolder ) )
        return False
    if not os.path.isdir( sourceFolder ):
        logging.critical( _("USFXXMLBibleFileCheck: Given {!r} path is not a folder").format( sourceFolder ) )
        return False

    # Find all the files and folders in this folder
    if BibleOrgSysGlobals.verbosityLevel > 3: print( " USFXXMLBibleFileCheck: Looking for files in given {}".format( sourceFolder ) )
    foundFolders, foundFiles = [], []
    for something in os.listdir( sourceFolder ):
        somepath = os.path.join( sourceFolder, something )
        if os.path.isdir( somepath ):
            if something in BibleOrgSysGlobals.COMMONLY_IGNORED_FOLDERS:
                continue # don't visit these directories
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
    #print( 'ff', foundFiles )

    # See if there's a USFX project here in this folder
    numFound = 0
    looksHopeful = False
    lastFilenameFound = None
    for thisFilename in sorted( foundFiles ):
        if strictCheck or BibleOrgSysGlobals.strictCheckingFlag:
            firstLines = BibleOrgSysGlobals.peekIntoFile( thisFilename, sourceFolder, numLines=3 )
            if not firstLines or len(firstLines)<2: continue
            if not ( firstLines[0].startswith( '<?xml version="1.0"' ) or firstLines[0].startswith( "<?xml version='1.0'" ) ) \
            and not ( firstLines[0].startswith( '\ufeff<?xml version="1.0"' ) or firstLines[0].startswith( "\ufeff<?xml version='1.0'" ) ): # same but with BOM
                if BibleOrgSysGlobals.verbosityLevel > 3: print( "USFXB (unexpected) first line was {!r} in {}".format( firstLines, thisFilename ) )
                continue
            if '<usfx ' not in firstLines[0] and '<usfx ' not in firstLines[1]:
                continue
        lastFilenameFound = thisFilename
        numFound += 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "USFXXMLBibleFileCheck got", numFound, sourceFolder, lastFilenameFound )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            ub = USFXXMLBible( sourceFolder, lastFilenameFound )
            if autoLoadBooks: ub.load() # Load and process the file
            return ub
        return numFound
    elif looksHopeful and BibleOrgSysGlobals.verbosityLevel > 2: print( "    Looked hopeful but no actual files found" )

    # Look one level down
    numFound = 0
    foundProjects = []
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( sourceFolder, thisFolderName+'/' )
        if BibleOrgSysGlobals.verbosityLevel > 3: print( "    USFXXMLBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
        foundSubfolders, foundSubfiles = [], []
        for something in os.listdir( tryFolderName ):
            somepath = os.path.join( sourceFolder, thisFolderName, something )
            if os.path.isdir( somepath ): foundSubfolders.append( something )
            elif os.path.isfile( somepath ):
                somethingUpper = something.upper()
                somethingUpperProper, somethingUpperExt = os.path.splitext( somethingUpper )
                ignore = False
                for ending in filenameEndingsToIgnore:
                    if somethingUpper.endswith( ending): ignore=True; break
                if ignore: continue
                if not somethingUpperExt[1:] in extensionsToIgnore: # Compare without the first dot
                    foundSubfiles.append( something )
        #print( 'fsf', foundSubfiles )

        # See if there's a USFX project here in this folder
        for thisFilename in sorted( foundSubfiles ):
            if strictCheck or BibleOrgSysGlobals.strictCheckingFlag:
                firstLines = BibleOrgSysGlobals.peekIntoFile( thisFilename, tryFolderName, numLines=2 )
                if not firstLines or len(firstLines)<2: continue
                if not ( firstLines[0].startswith( '<?xml version="1.0"' ) or firstLines[0].startswith( "<?xml version='1.0'" ) ) \
                and not ( firstLines[0].startswith( '\ufeff<?xml version="1.0"' ) or firstLines[0].startswith( "\ufeff<?xml version='1.0'" ) ): # same but with BOM
                    if BibleOrgSysGlobals.verbosityLevel > 3: print( "USFXB (unexpected) first line was {!r} in {}".format( firstLines, thisFilename ) )
                    continue
                if '<usfx ' not in firstLines[0] and '<usfx ' not in firstLines[1]:
                    continue
            foundProjects.append( (tryFolderName, thisFilename,) )
            lastFilenameFound = thisFilename
            numFound += 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "USFXXMLBibleFileCheck foundProjects", numFound, foundProjects )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            if BibleOrgSysGlobals.debugFlag: assert len(foundProjects) == 1
            ub = USFXXMLBible( foundProjects[0][0], foundProjects[0][1] ) # Folder and filename
            if autoLoadBooks: ub.load() # Load and process the file
            return ub
        return numFound
# end of USFXXMLBibleFileCheck



def clean( elementText ):
    """
    Given some text from an XML element (which might be None)
        return a stripped value and with internal CRLF characters replaced by spaces.
    """
    if elementText is not None:
        return elementText.strip().replace( '\r\n', ' ' ).replace( '\n', ' ' ).replace( '\r', ' ' )
# end of clean



class USFXXMLBible( Bible ):
    """
    Class to load and manipulate USFX Bibles.

    """
    def __init__( self, sourceFolder, givenName=None, encoding='utf-8' ):
        """
        Create the internal USFX Bible object.
        """
         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = 'USFX XML Bible object'
        self.objectTypeString = 'USFX'

        self.sourceFolder, self.givenName, self.encoding = sourceFolder, givenName, encoding # Remember our parameters

        # Now we can set our object variables
        self.name = self.givenName
        if not self.name: self.name = os.path.basename( self.sourceFolder )
        if not self.name: self.name = os.path.basename( self.sourceFolder[:-1] ) # Remove the final slash
        if not self.name: self.name = "USFX Bible"
        if self.name.endswith( '_usfx' ): self.name = self.name[:-5] # Remove end of name for Haiola projects

        # Do a preliminary check on the readability of our folder
        if not os.access( self.sourceFolder, os.R_OK ):
            logging.error( "USFXXMLBible: Folder {!r} is unreadable".format( self.sourceFolder ) )

        # Do a preliminary check on the contents of our folder
        self.sourceFilename = self.sourceFilepath = None
        foundFiles, foundFolders = [], []
        for something in os.listdir( self.sourceFolder ):
            somepath = os.path.join( self.sourceFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ):
                somethingUpper = something.upper()
                somethingUpperProper, somethingUpperExt = os.path.splitext( somethingUpper )
                ignore = False
                for ending in filenameEndingsToIgnore:
                    if somethingUpper.endswith( ending): ignore=True; break
                if ignore: continue
                if not somethingUpperExt[1:] in extensionsToIgnore: # Compare without the first dot
                    foundFiles.append( something )
            else:
                logging.error( "Not sure what {!r} is in {}!".format( somepath, self.sourceFolder ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
        if foundFolders: logging.info( "USFXXMLBible: Surprised to see subfolders in {!r}: {}".format( self.sourceFolder, foundFolders ) )
        if not foundFiles:
            if BibleOrgSysGlobals.verbosityLevel > 0: print( "USFXXMLBible: Couldn't find any files in {!r}".format( self.sourceFolder ) )
            return # No use continuing

        #print( self.sourceFolder, foundFolders, len(foundFiles), foundFiles )
        numFound = 0
        for thisFilename in sorted( foundFiles ):
            firstLines = BibleOrgSysGlobals.peekIntoFile( thisFilename, sourceFolder, numLines=3 )
            if not firstLines or len(firstLines)<2: continue
            if not ( firstLines[0].startswith( '<?xml version="1.0"' ) or firstLines[0].startswith( "<?xml version='1.0'" ) ) \
            and not ( firstLines[0].startswith( '\ufeff<?xml version="1.0"' ) or firstLines[0].startswith( "\ufeff<?xml version='1.0'" ) ): # same but with BOM
                if BibleOrgSysGlobals.verbosityLevel > 3: print( "USFXB (unexpected) first line was {!r} in {}".format( firstLines, thisFilename ) )
                continue
            if '<usfx ' not in firstLines[0] and '<usfx ' not in firstLines[1]:
                continue
            lastFilenameFound = thisFilename
            numFound += 1
        if numFound:
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "USFXXMLBible got", numFound, sourceFolder, lastFilenameFound )
            if numFound == 1:
                self.sourceFilename = lastFilenameFound
                self.sourceFilepath = os.path.join( self.sourceFolder, self.sourceFilename )
        elif BibleOrgSysGlobals.verbosityLevel > 2: print( "    Looked hopeful but no actual files found" )
    # end of USFXXMLBible.__init_


    def load( self ):
        """
        Load the XML data file -- we should already know the filepath.
        """
        if BibleOrgSysGlobals.verbosityLevel > 1:
            print( _("USFXXMLBible.load: Loading {!r} from {!r}…").format( self.name, self.sourceFilepath ) )

        try: self.XMLTree = ElementTree().parse( self.sourceFilepath )
        except ParseError:
            errorString = sys.exc_info()[1]
            logging.critical( "USFXXMLBible.load: failed loading the xml file {}: {!r}.".format( self.sourceFilepath, errorString ) )
            return
        if BibleOrgSysGlobals.debugFlag: assert len( self.XMLTree ) # Fail here if we didn't load anything at all

        # Find the main (osis) container
        prefix = self.XMLTree.tag[:-4] if self.XMLTree.tag[0]=='{' and self.XMLTree.tag[-5]=='}' else ''
        if self.XMLTree.tag == prefix + 'usfx':
            location = 'USFX file'
            BibleOrgSysGlobals.checkXMLNoText( self.XMLTree, location, '4f6h' )
            BibleOrgSysGlobals.checkXMLNoTail( self.XMLTree, location, '1wk8' )
            # Process the attributes first
            self.schemaLocation = None
            for attrib,value in self.XMLTree.items():
                #print( "attrib", repr(attrib), repr(value) )
                if attrib.endswith("SchemaLocation"):
                    self.schemaLocation = value
                else:
                    logging.warning( "fv6g Unprocessed {} attribute ({}) in {}".format( attrib, value, location ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
            BBB = C = V = None
            for element in self.XMLTree:
                #print( "element", repr(element.tag) )
                sublocation = element.tag + " " + location
                if element.tag == 'languageCode':
                    self.languageCode = element.text
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation, 'cff3' )
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation, 'des1' )
                    BibleOrgSysGlobals.checkXMLNoSubelements( element, sublocation, 'dwf2' )
                elif element.tag == 'book':
                    self.loadBook( element )
                    ##BibleOrgSysGlobals.checkXMLNoSubelements( element, sublocation, '54f2' )
                    #BibleOrgSysGlobals.checkXMLNoTail( element, sublocation, 'hd35' )
                    ## Process the attributes
                    #idField = bookStyle = None
                    #for attrib,value in element.items():
                        #if attrib=='id' or attrib=='code':
                            #idField = value # Should be USFM bookcode (not like BBB which is BibleOrgSys BBB bookcode)
                            ##if idField != BBB:
                            ##    logging.warning( _("Unexpected book code ({}) in {}").format( idField, sublocation ) )
                        #elif attrib=='style':
                            #bookStyle = value
                        #else:
                            #logging.warning( _("gfw2 Unprocessed {} attribute ({}) in {}").format( attrib, value, sublocation ) )
                else:
                    logging.warning( _("dbw1 Unprocessed {} element after {} {}:{} in {}").format( element.tag, BBB, C, V, sublocation ) )
                    #self.addPriorityError( 1, c, v, _("Unprocessed {} element").format( element.tag ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt

        if not self.books: # Didn't successfully load any regularly named books -- maybe the files have weird names??? -- try to be intelligent here
            if BibleOrgSysGlobals.verbosityLevel > 2:
                print( "USFXXMLBible.load: Didn't find any regularly named USFX files in {!r}".format( self.sourceFolder ) )
            #foundFiles = []
            #for something in os.listdir( self.sourceFolder ):
                #somepath = os.path.join( self.sourceFolder, something )
                #if os.path.isfile( somepath ):
                    #somethingUpper = something.upper()
                    #somethingUpperProper, somethingUpperExt = os.path.splitext( somethingUpper )
                    #ignore = False
                    #for ending in filenameEndingsToIgnore:
                        #if somethingUpper.endswith( ending): ignore=True; break
                    #if ignore: continue
                    #if not somethingUpperExt[1:] in extensionsToIgnore: # Compare without the first dot
                        #foundFiles.append( something )
            #for thisFilename in foundFiles:
                ## Look for BBB in the ID line (which should be the first line in a USFX file)
                #isUSFX = False
                #thisPath = os.path.join( self.sourceFolder, thisFilename )
                #with open( thisPath ) as possibleUSXFile: # Automatically closes the file when done
                    #for line in possibleUSXFile:
                        #if line.startswith( '\\id ' ):
                            #USXId = line[4:].strip()[:3] # Take the first three non-blank characters after the space after id
                            #if BibleOrgSysGlobals.verbosityLevel > 2: print( "Have possible USFX ID {!r}".format( USXId ) )
                            #BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromUSFMAbbreviation( USXId )
                            #if BibleOrgSysGlobals.verbosityLevel > 2: print( "BBB is {!r}".format( BBB ) )
                            #isUSFX = True
                        #break # We only look at the first line
                #if isUSFX:
                    #UBB = USFXXMLBibleBook( self, BBB )
                    #UBB.load( self.sourceFolder, thisFilename, self.encoding )
                    #UBB.validateMarkers()
                    #print( UBB )
                    #self.books[BBB] = UBB
                    ## Make up our book name dictionaries while we're at it
                    #assumedBookNames = UBB.getAssumedBookNames()
                    #for assumedBookName in assumedBookNames:
                        #self.BBBToNameDict[BBB] = assumedBookName
                        #assumedBookNameLower = assumedBookName.lower()
                        #self.bookNameDict[assumedBookNameLower] = BBB # Store the deduced book name (just lower case)
                        #self.combinedBookNameDict[assumedBookNameLower] = BBB # Store the deduced book name (just lower case)
                        #if ' ' in assumedBookNameLower: self.combinedBookNameDict[assumedBookNameLower.replace(' ','')] = BBB # Store the deduced book name (lower case without spaces)
            #if self.books: print( "USFXXMLBible.load: Found {} irregularly named USFX files".format( len(self.books) ) )

        self.doPostLoadProcessing()
    # end of USFXXMLBible.load


    def loadBook( self, bookElement ):
        """
        Load the book container from the XML data file.
        """
        if BibleOrgSysGlobals.verbosityLevel > 3:
            print( _("USFXXMLBible.loadBook: Loading {} from {}…").format( self.name, self.sourceFolder ) )
        assert bookElement.tag == 'book'
        mainLocation = self.name + " USFX book"

        # Process the attributes first
        bookCode = None
        for attrib,value in bookElement.items():
            if attrib == 'id':
                bookCode = value
            else:
                logging.warning( "bce3 Unprocessed {} attribute ({}) in {}".format( attrib, value, mainLocation ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
        BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromUSFMAbbreviation( bookCode )
        mainLocation = "{} USFX {} book".format( self.name, BBB )
        if BibleOrgSysGlobals.verbosityLevel > 2:
            print( _("USFXXMLBible.loadBook: Loading {} from {}…").format( BBB, self.name ) )
        BibleOrgSysGlobals.checkXMLNoText( self.XMLTree, mainLocation, '4f6h' )
        BibleOrgSysGlobals.checkXMLNoTail( self.XMLTree, mainLocation, '1wk8' )

        # Now create our actual book
        self.thisBook = BibleBook( self, BBB )
        self.thisBook.objectNameString = 'USFX XML Bible Book object'
        self.thisBook.objectTypeString = 'USFX'

        C, V = '-1', '-1' # So first/id line starts at -1:0
        for element in bookElement:
            #print( "element", repr(element.tag) )
            location = "{} of {} {}:{}".format( element.tag, mainLocation, BBB, C, V )
            if element.tag == 'id':
                idText = clean( element.text )
                BibleOrgSysGlobals.checkXMLNoTail( element, location, 'vsg3' )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, location, 'ksq2' )
                for attrib,value in element.items():
                    if attrib == 'id':
                        assert value == bookCode
                    else:
                        logging.warning( _("vsg4 Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                self.thisBook.addLine( 'id', bookCode + ((' '+idText) if idText else '') )
            elif element.tag == 'ide':
                ideText = clean( element.text )
                BibleOrgSysGlobals.checkXMLNoTail( element, location, 'jsa0' )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, location, 'ls01' )
                charset = None
                for attrib,value in element.items():
                    if attrib == 'charset': charset = value
                    else:
                        logging.warning( _("jx53 Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                if charset: self.thisBook.addLine( 'ide', charset + ((' '+ideText) if ideText else '') )
                else:
                    logging.critical( _("cx53 Empty charset in {}").format( location ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
            elif element.tag == 'h':
                hText = element.text
                BibleOrgSysGlobals.checkXMLNoTail( element, location, 'dj35' )
                BibleOrgSysGlobals.checkXMLNoAttributes( element, location, 'hs35' )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, location, 'hs32' )
                self.thisBook.addLine( 'h', clean(hText) )
            elif element.tag == 'toc':
                tocText = element.text
                BibleOrgSysGlobals.checkXMLNoTail( element, location, 'ss13' )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, location, 'js13' )
                level = None
                for attrib,value in element.items():
                    if attrib == 'level': # Seems compulsory
                        level = value
                    else:
                        logging.warning( _("dg36 Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                self.thisBook.addLine( 'toc'+level, clean(tocText) )
            elif element.tag == 'c':
                BibleOrgSysGlobals.checkXMLNoText( element, location, 'ks35' )
                BibleOrgSysGlobals.checkXMLNoTail( element, location, 'gs35' )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, location, 'kdr3' ) # This is a milestone
                for attrib,value in element.items():
                    if attrib == 'id':
                        C, V = value, '0'
                    else:
                        logging.warning( _("hj52 Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                self.thisBook.addLine( 'c', C )
            elif element.tag == 's':
                sText = clean( element.text )
                BibleOrgSysGlobals.checkXMLNoTail( element, location, 'wxg0' )
                level = None
                for attrib,value in element.items():
                    if attrib == 'level': # Seems optional
                        level = value
                    else:
                        logging.warning( _("bdy6 Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                marker = 's'
                if level: marker += level
                #print( "loadBook cd536", repr(marker), repr(sText) )
                self.thisBook.addLine( marker, '' if sText is None else sText )
                for subelement in element:
                    #print( "subelement", repr(subelement.tag) )
                    sublocation = subelement.tag + " of " + location
                    if subelement.tag == 'f':
                        self.loadFootnote( subelement, sublocation, BBB, C, V )
                    elif subelement.tag == 'x':
                        self.loadCrossreference( subelement, sublocation )
                    elif subelement.tag == 'fig':
                        self.loadFigure( subelement, sublocation )
                    elif subelement.tag == 'table':
                        self.loadTable( subelement, sublocation, BBB, C, V )
                    elif subelement.tag in ('add','it','bd','bdit','sc','nd',):
                        self.loadCharacterFormatting( subelement, sublocation, BBB, C, V )
                    elif subelement.tag == 'optionalLineBreak':
                        self.thisBook.appendToLastLine( '//' )
                    else:
                        logging.warning( _("jx9q Unprocessed {} element after {} {}:{} in {}").format( subelement.tag, BBB, C, V, sublocation ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
            elif element.tag in ('p','q','d',):
                V = self.loadParagraph( element, location, BBB, C )
            elif element.tag == 'v': # verse milestone outside of a paragraph
                vTail = clean( element.tail ) # Main verse text
                BibleOrgSysGlobals.checkXMLNoText( element, location, 'djf3' )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, location, 'jsh2' )
                lastV, V = V, None
                for attrib,value in element.items():
                    if attrib == 'id':
                        V = value
                    else:
                        logging.warning( _("sjx9 Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                assert V is not None
                assert V
                self.thisBook.addLine( 'v', V + ((' '+vTail) if vTail else '' ) )
            elif element.tag == 'b':
                BibleOrgSysGlobals.checkXMLNoText( element, location, 'ks35' )
                BibleOrgSysGlobals.checkXMLNoTail( element, location, 'gs35' )
                BibleOrgSysGlobals.checkXMLNoAttributes( element, location, 'nd04' )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, location, 'kdr3' )
                self.thisBook.addLine( 'b', '' )
            elif element.tag == 'rem':
                BibleOrgSysGlobals.checkXMLNoTail( element, location, 'fs53' )
                BibleOrgSysGlobals.checkXMLNoAttributes( element, location, 'as24' )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, location, 'kas2' )
                self.thisBook.addLine( 'rem', clean(element.text) )
            elif element.tag in ('cl','cp'): # Simple single-line paragraph-level markers
                marker, text = element.tag, clean(element.text)
                BibleOrgSysGlobals.checkXMLNoTail( element, location, 'od01' )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, location, 'gd92' )
                idField = None
                for attrib,value in element.items():
                    if attrib == 'id': idField = value
                    else:
                        logging.warning( _("dv35 Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                if idField and text is None:
                    text = idField
                elif text and idField is None and element.tag=='cl' and C=='-1':
                    # Contains text for chapter field
                    pass
                else:
                    logging.warning( _("dve4 Unprocessed idField ({}) with '{}' in {}").format( idField, text, location ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                if text is None:
                    logging.critical( "Why is {} empty at {}".format( marker, location ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                assert text is not None
                self.thisBook.addLine( marker, text )
            elif element.tag == 'table':
                self.loadTable( element, location, BBB, C, V )
            elif element.tag == 've': # Verse end in Psalms: <c id="4" /><ve /><d>For the Chief Musician; on stringed instruments. A Psalm of David.</d>
                BibleOrgSysGlobals.checkXMLNoText( element, location, 'kds3' )
                BibleOrgSysGlobals.checkXMLNoTail( element, location, 'ks29' )
                BibleOrgSysGlobals.checkXMLNoAttributes( element, location, 'kj24' )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, location, 'js91' )
                #self.thisBook.addLine( 'b', '' )
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "Ignoring 've' field", BBB, C, V )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
            elif element.tag == 'periph':
                BibleOrgSysGlobals.checkXMLNoTail( element, location, 'ws29' )
                BibleOrgSysGlobals.checkXMLNoAttributes( element, location, 'wj24' )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, location, 'ws91' )
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "Ignoring 'periph' field", BBB, C, V )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
            else:
                logging.critical( _("caf2 Unprocessed {} element after {} {}:{} in {}").format( element.tag, BBB, C, V, location ) )
                #self.addPriorityError( 1, c, v, _("Unprocessed {} element").format( element.tag ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
        self.stashBook( self.thisBook )
    # end of USFXXMLBible.loadBook


    def loadParagraph( self, paragraphElement, paragraphLocation, BBB, C ):
        """
        Load the paragraph (p or q) container from the XML data file.
        """
        #if BibleOrgSysGlobals.verbosityLevel > 3:
            #print( _("USFXXMLBible.loadParagraph: Loading {} from {}…").format( self.name, self.sourceFolder ) )

        V = None
        pTag, pText = paragraphElement.tag, clean(paragraphElement.text)
        BibleOrgSysGlobals.checkXMLNoTail( paragraphElement, paragraphLocation, 'vsg7' )

        # Process the attributes first
        sfm = level = style = None
        for attrib,value in paragraphElement.items():
            if attrib == 'sfm': sfm = value
            elif attrib == 'level': level = value
            elif attrib == 'style': style = value
            else:
                logging.warning( "vfh4 Unprocessed {} attribute ({}) in {}".format( attrib, value, paragraphLocation ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt

        if sfm:
            assert pTag == 'p'
            pTag = sfm
        if level:
            #assert pTag == 'q' # Could also be mt, etc.
            pTag += level
        if style:
            #print( repr(pTag), repr(pText), repr(style) )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "Ignoring {!r} style".format( style ) )

        self.thisBook.addLine( pTag, '' if pText is None else pText )

        for element in paragraphElement:
            location = element.tag + " of " + paragraphLocation
            #print( "element", repr(element.tag) )
            if element.tag == 'v': # verse milestone
                vTail = clean( element.tail ) # Main verse text
                BibleOrgSysGlobals.checkXMLNoText( element, location, 'crc2' )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, location, 'lct3' )
                lastV, V = V, None
                bcv = None
                for attrib,value in element.items():
                    if attrib == 'id': V = value
                    elif attrib == 'bcv': bcv = value # This is an BCV reference string with periods, e.g., 'MAT.1.11'
                    else:
                        logging.warning( _("cbs2 Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                assert V is not None
                assert V
                self.thisBook.addLine( 'v', V + ((' '+vTail) if vTail else '' ) )
            elif element.tag == 've': # verse end milestone -- we can just ignore this
                BibleOrgSysGlobals.checkXMLNoText( element, location, 'lsc3' )
                BibleOrgSysGlobals.checkXMLNoTail( element, location, 'mfy4' )
                BibleOrgSysGlobals.checkXMLNoAttributes( element, location, 'bd24' )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, location, 'ks35' )
            elif element.tag == 'fig':
                self.loadFigure( element, location )
            elif element.tag == 'table':
                self.loadTable( element, location, BBB, C, V )
            elif element.tag == 'f':
                #print( "USFX.loadParagraph Found footnote at", paragraphLocation, C, V, repr(element.text) )
                self.loadFootnote( element, location, BBB, C, V )
            elif element.tag == 'x':
                #print( "USFX.loadParagraph Found xref at", paragraphLocation, C, V, repr(element.text) )
                self.loadCrossreference( element, location )
            elif element.tag == 'w':
                self.loadWordFormatting( element, location, BBB, C, V )
            elif element.tag in ('add','nd','wj','rq','sig','sls','bk','k','tl','vp','pn','qs','qt','em','it','bd','bdit','sc','no',): # character formatting
                self.loadCharacterFormatting( element, location, BBB, C, V )
            elif element.tag == 'cs': # character style -- seems like a USFX hack
                text, tail = clean(element.text), clean(element.tail)
                BibleOrgSysGlobals.checkXMLNoSubelements( element, location, 'kf92' )
                sfm = None
                for attrib,value in element.items():
                    if attrib == 'sfm': sfm = value
                    else:
                        logging.warning( _("sh29 Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                if sfm not in ('w','ior',): print( "cs sfm got", repr(sfm) )
                self.thisBook.appendToLastLine( ' \\{} {}\\{}*{}'.format( sfm, text, sfm, (' '+tail) if tail else '' ) )
            elif element.tag in ('cp',): # Simple single-line paragraph-level markers
                marker, text = element.tag, clean(element.text)
                BibleOrgSysGlobals.checkXMLNoTail( element, location, 'kdf0' )
                BibleOrgSysGlobals.checkXMLNoAttributes( element, location, 'lkj1' )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, location, 'da13' )
                self.thisBook.addLine( marker, text )
            elif element.tag == 'ref': # encoded reference -- seems like a USFX hack
                text, tail = clean(element.text), clean(element.tail)
                BibleOrgSysGlobals.checkXMLNoSubelements( element, location, 'bd83' )
                target = None
                for attrib,value in element.items():
                    if attrib == 'tgt': target = value
                    else:
                        logging.warning( _("be83 Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                #if target not in ('w','ior',): print( "ref sfm got", repr(sfm) )
                self.thisBook.appendToLastLine( ' \\{} {}\\{}*{}{}'.format( element.tag, target, element.tag, text, (' '+tail) if tail else '' ) )
                #print( "Saved", '\\{} {}\\{}*{}{}'.format( element.tag, target, element.tag, text, (' '+tail) if tail else '' ) )
            elif element.tag == 'optionalLineBreak':
                self.thisBook.appendToLastLine( '//' )
            elif element.tag == 'milestone': # e.g., <milestone sfm="pb" attribute=""/> (pb = explicit page break)
                BibleOrgSysGlobals.checkXMLNoText( element, location, 'jzx2' )
                BibleOrgSysGlobals.checkXMLNoTail( element, location, 'ms23' )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, location, 'dw24' )
                sfm = attribute = None
                for attrib,value in element.items():
                    if attrib == 'sfm': sfm = value
                    elif attrib == 'attribute': attribute = value
                    else:
                        logging.warning( _("mcd2 Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                if sfm not in ('bl','pb',):
                    print( "milestone sfm got", repr(sfm) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                if sfm=='bl': sfm = 'b'
                self.thisBook.addLine( sfm, '' )
            elif element.tag == 'gw': # e.g., <gw sfm="w" root="Vivivirei ma Viaiaina; Aiaii">vovivirei</gw> glossary word
                BibleOrgSysGlobals.checkXMLNoSubelements( element, location, 'gw24' )
                text, tail = clean(element.text), clean(element.tail)
                sfm = root = None
                for attrib,value in element.items():
                    if attrib == 'sfm': sfm = value
                    elif attrib == 'root': root = value
                    else:
                        logging.warning( _("gcd2 Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                self.thisBook.appendToLastLine( ' \\{} {}\\{}* {}'.format( sfm, text, sfm, tail ) )
                logging.error( "What should we do with the gw root value: {!r} ?".format( root ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
            elif element.tag == 'xt' and BBB == 'GLS':
                logging.warning("No code for handling GLS xt field yet!!!")
                BibleOrgSysGlobals.checkXMLNoAttributes( element, location, 'bd34' )
                BibleOrgSysGlobals.checkXMLNoText( element, location, 'kz32' )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, location, 'ka81' )
                BibleOrgSysGlobals.checkXMLNoTail( element, location, 'ka16' )
            else:
                logging.warning( _("df45 Unprocessed {} element after {} {}:{} in {}").format( repr(element.tag), self.thisBook.BBB, C, V, location ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
        return V
    # end of USFXXMLBible.loadParagraph


    def loadWordFormatting( self, element, location, BBB, C, V ):
        """
        """
        marker, text, tail = element.tag, clean(element.text), clean(element.tail)
        assert marker == 'w'
        BibleOrgSysGlobals.checkXMLNoSubelements( element, location, 'bs62' )
        self.thisBook.appendToLastLine( ' \\{}'.format( marker ) )
        strongs = None
        for attrib,value in element.items():
            if attrib == 's':
                strongs = value
            else:
                logging.warning( _("dj75 Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
        if strongs:
            assert marker == 'w'
            self.thisBook.appendToLastLine( ' \\str {}\\str*'.format( strongs ) )
        self.thisBook.appendToLastLine( ' {}'.format( text ) )
        for subelement in element:
            sublocation = subelement.tag + " of " + location
            #print( "element", repr(element.tag) )
            if subelement.tag == 'f':
                #print( "USFX.loadParagraph Found footnote at", sublocation, C, V, repr(subelement.text) )
                self.loadFootnote( subelement, sublocation, BBB, C, V )
            else:
                logging.warning( _("sh61 Unprocessed {} element after {} {}:{} in {}").format( repr(subelement.tag), self.thisBook.BBB, C, V, location ) )
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
        self.thisBook.appendToLastLine( '\\{}*{}'.format( marker, (' '+tail) if tail else '' ) )


    def loadCharacterFormatting( self, element, location, BBB, C, V ):
        """
        """
        marker, text, tail = element.tag, clean(element.text), clean(element.tail)
        BibleOrgSysGlobals.checkXMLNoAttributes( element, location, 'cb25' )
        self.thisBook.appendToLastLine( ' \\{} {}'.format( marker, text ) )
        for subelement in element:
            sublocation = subelement.tag + " of " + location
            #print( "element", repr(element.tag) )
            if subelement.tag == 'f':
                #print( "USFX.loadParagraph Found footnote at", sublocation, C, V, repr(subelement.text) )
                self.loadFootnote( subelement, sublocation, BBB, C, V )
            elif subelement.tag == 'w':
                self.loadWordFormatting( subelement, sublocation, BBB, C, V )
            else:
                logging.warning( _("sf31 Unprocessed {} element after {} {}:{} in {}").format( repr(subelement.tag), self.thisBook.BBB, C, V, location ) )
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
        self.thisBook.appendToLastLine( '\\{}*{}'.format( marker, (' '+tail) if tail else '' ) )
    # end of USFXXMLBible.loadCharacterFormatting


    def loadFigure( self, element, location ):
        """
        """
        BibleOrgSysGlobals.checkXMLNoText( element, location, 'ff36' )
        BibleOrgSysGlobals.checkXMLNoAttributes( element, location, 'cf35' )
        figDict = { 'description':'', 'catalog':'', 'size':'', 'location':'', 'copyright':'', 'caption':'', 'reference':'' }
        for subelement in element:
            sublocation = subelement.tag + " of " + location
            figTag, figText = subelement.tag, clean(subelement.text)
            assert figTag in figDict
            figDict[figTag] = '' if figText is None else figText
            BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, 'jkf5' )
            BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, 'ld18' )
            BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, 'hb46' )
        newString = ''
        for j,tag in enumerate( ('description', 'catalog', 'size', 'location', 'copyright', 'caption', 'reference',) ):
            newString += ('' if j==0 else '|') + figDict[tag]
        figTail = clean( element.tail )
        self.thisBook.appendToLastLine( ' \\fig {}\\fig*{}'.format( newString, (' '+figTail) if figTail else '' ) )
    # end of USFXXMLBible.loadFigure


    def loadTable( self, element, location, BBB, C, V ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "\nUSFXXMLBible.loadTable( {}, {} )".format( BibleOrgSysGlobals.elementStr( element ), location ) )

        BibleOrgSysGlobals.checkXMLNoText( element, location, 'kg92' )
        BibleOrgSysGlobals.checkXMLNoTail( element, location, 'ka92' )
        BibleOrgSysGlobals.checkXMLNoAttributes( element, location, 'ks63' )
        for subelement in element:
            sublocation = subelement.tag + " of " + location
            print( "  subelement is {} at {}".format( BibleOrgSysGlobals.elementStr( subelement ), sublocation ) )
            if subelement.tag == 'tr':
                #print( "table", sublocation )
                self.thisBook.addLine( 'tr', '' )
                BibleOrgSysGlobals.checkXMLNoText( subelement, sublocation, 'sg32' )
                BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, 'dh82' )
                BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, 'mniq' )
                for sub2element in subelement:
                    sub2location = sub2element.tag + " of " + sublocation
                    tag, text = sub2element.tag, clean(sub2element.text)
                    if debuggingThisModule:
                        print( "  loadTable: tag={!r}, text={!r} at {}".format( tag, text, sub2location ) )
                        print( "    sub2element is {}".format( BibleOrgSysGlobals.elementStr( sub2element ) ) )
                    if tag not in ('th', 'thr', 'tc', 'tcr',):
                        logging.warning( _("loadTable: unexpected {!r} inside 'tr' in table at {}").format( tag, sublocation ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                    BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2location, 'ah82' )
                    level = None
                    for attrib,value in sub2element.items():
                        if attrib == 'level': level = value
                        else:
                            logging.warning( _("vx25 Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    marker = tag + (level if level else '')
                    for sub3element in sub2element:
                        sub3location = sub3element.tag + " of " + sub2location
                        BibleOrgSysGlobals.checkXMLNoText( sub3element, sub3location, 'bf35' )
                        BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3location, 'ls01' )
                        BibleOrgSysGlobals.checkXMLNoAttributes( sub3element, sub3location, 'xc40' )
                        for sub4element in sub3element:
                            sub4location = sub4element.tag + " of " + sub3location
                            BibleOrgSysGlobals.checkXMLNoText( sub4element, sub4location, 'aq41' )
                            BibleOrgSysGlobals.checkXMLNoTail( sub4element, sub4location, 'fo20' )
                            BibleOrgSysGlobals.checkXMLNoAttributes( sub4element, sub4location, 'ls42' )
                            BibleOrgSysGlobals.checkXMLNoSubelements( sub4element, sub4location, 'vl35' )
                    self.thisBook.appendToLastLine( ' \\{} {}'.format( marker, text ) )
            else:
                logging.warning( _("kv64 Unprocessed {} element after {} {}:{} in {}").format( subelement.tag, BBB, C, V, sublocation ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
    # end of USFXXMLBible.loadTable


    def loadFootnote( self, element, location, BBB, C, V ):
        """
        Handles footnote fields, including xt field.
        """
        text, tail = clean(element.text), clean(element.tail)
        caller = None
        for attrib,value in element.items():
            if attrib == 'caller':
                caller = value
            else:
                logging.warning( _("dg35 Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
        self.thisBook.appendToLastLine( ' \\f {}{}'.format( caller, (' '+text) if text else '' ) )
        for subelement in element:
            sublocation = subelement.tag + " of " + location
            marker, fText, fTail = subelement.tag, clean(subelement.text), clean(subelement.tail)
            #print( "USFX.loadFootnote", repr(caller), repr(text), repr(tail), repr(marker), repr(fText), repr(fTail) )
            if BibleOrgSysGlobals.verbosityLevel > 0 and marker not in ('ref','fr','ft','fq','fv','fk','fqa','it','bd','rq','w'):
                logging.warning( "USFX.loadFootnote found {!r} {!r} {!r} {!r}".format( caller, marker, fText, fTail ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag:
                assert marker in ('ref','fr','ft','fq','fv','fk','fqa','it','bd','rq','xt','w')
            if marker=='ref':
                if not fText:
                    logging.error("Expected text in footnote ref field at {} {}:{}".format( BBB, C, V ) )
                BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, 'ls13' )
                target = None
                for attrib,value in subelement.items():
                    if attrib == 'tgt': target = value
                    else:
                        logging.warning( _("gs35 Unprocessed {} attribute ({}) in {}").format( attrib, value, sublocation ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                if target:
                    self.thisBook.appendToLastLine( ' \\{} {}\\{}*{}'.format( marker, target, marker, fText ) )
                else: halt
            elif marker=='w':
                self.loadWordFormatting( subelement, sublocation, BBB, C, V )
            else:
                BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, 'dq54' )
                self.thisBook.appendToLastLine( ' \\{} {}'.format( marker, fText ) )
                if marker=='xt' or marker[0]=='f': # Starts with f, e.g., fr, ft
                    for sub2element in subelement:
                        sub2location = sub2element.tag + " of " + sublocation
                        marker2, fText2, fTail2 = sub2element.tag, clean(sub2element.text), clean(sub2element.tail)
                        BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2location, 'js72' ) # Wrong! has bd XXXXXXXXXX
                        if marker2 == 'ref':
                            #print( sub2location )
                            if fText2:
                                #print( 'ft2', marker2, repr(fText2), repr(fTail2), sub2location )
                                self.thisBook.appendToLastLine( fText2 )
                            target = None
                            for attrib,value in sub2element.items():
                                if attrib == 'tgt': target = value # OSIS style reference, e.g., '1SA.27.8'
                                else:
                                    logging.warning( _("hd52 Unprocessed {} attribute ({}) in {}").format( attrib, value, sub2location ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                            if target:
                                #print( 'tg', marker2, repr(target) )
                                self.thisBook.appendToLastLine( ' \\{} {}'.format( marker2, target ) )
                            else:
                                if debuggingThisModule: halt
                        elif marker2 == 'w':
                            self.loadWordFormatting( sub2element, sub2location, BBB, C, V )
                        elif marker2 in ('add','nd','wj','rq','sig','sls','bk','k','tl','vp','pn','qs','qt','em','it','bd','bdit','sc','no',): # character formatting
                            self.loadCharacterFormatting( sub2element, sub2location, BBB, C, V )
                        else:
                            print( 'Ignored marker2', repr(marker2), BBB, C, V )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                        if fTail2: self.thisBook.appendToLastLine( fTail2 )
                elif marker == 'w':
                    self.loadWordFormatting( subelement, sublocation, BBB, C, V )
                elif marker in ('add','nd','wj','rq','sig','sls','bk','k','tl','vp','pn','qs','qt','em','it','bd','bdit','sc','no',): # character formatting
                    self.loadCharacterFormatting( subelement, sublocation, BBB, C, V )
                else:
                    print( 'Ignored marker', repr(marker), BBB, C, V )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
            if fTail:
                self.thisBook.appendToLastLine( '\\{}*{}'.format( marker, fTail ) )
        self.thisBook.appendToLastLine( '\\f*{}'.format( (' '+tail) if tail else '' ) )
    # end of USFXXMLBible.loadFootnote


    def loadCrossreference( self, element, location ):
        """
        Has to handle: <x caller="+"><ref tgt="EXO.30.12">Exodus 30:12</ref></x>
        """
        text, tail = clean(element.text), clean(element.tail)
        caller = None
        for attrib,value in element.items():
            if attrib == 'caller':
                caller = value
            else:
                logging.warning( _("fhj2 Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
        self.thisBook.appendToLastLine( ' \\x {}'.format( caller ) )
        for subelement in element:
            sublocation = subelement.tag + " of " + location
            marker, xText, xTail = subelement.tag, clean(subelement.text), clean(subelement.tail)
            #print( "USFX.loadCrossreference", repr(caller), repr(text), repr(tail), repr(marker), repr(xText), repr(xTail) )
            #if BibleOrgSysGlobals.verbosityLevel > 0 and marker not in ('ref','xo','xt',):
                #print( "USFX.loadCrossreference found", repr(caller), repr(marker), repr(xText), repr(xTail) )
            if BibleOrgSysGlobals.debugFlag: assert marker in ('ref','xo','xt',)
            if marker=='ref':
                assert xText
                BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, 's1sd' )
                target = None
                for attrib,value in subelement.items():
                    if attrib == 'tgt': target = value
                    else:
                        logging.warning( _("aj41 Unprocessed {} attribute ({}) in {}").format( attrib, value, sublocation ) )
                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                if target:
                    self.thisBook.appendToLastLine( ' \\{} {}\\{}*{}'.format( marker, target, marker, xText ) )
                else: halt
            else: # xo or xt
                BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, 'sc35' )
                self.thisBook.appendToLastLine( ' \\{} {}'.format( marker, xText ) )
                if marker[0] == 'x': # Starts with x, e.g., xo, xt
                    for sub2element in subelement:
                        sub2location = sub2element.tag + " of " + sublocation
                        marker2, xText2, xTail2 = sub2element.tag, clean(sub2element.text), clean(sub2element.tail)
                        BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2location, 'fs63' )
                        if marker2=='ref':
                            if xText2:
                                #print( 'xt2', marker2, repr(xText2), repr(xTail2), sub2location )
                                self.thisBook.appendToLastLine( xText2 )
                            target = None
                            for attrib,value in sub2element.items():
                                if attrib == 'tgt': target = value
                                else:
                                    logging.warning( _("USFXXMLBible.loadCrossreference: gs34 Unprocessed {} attribute ({}) in {}").format( attrib, value, sub2location ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                            if target: self.thisBook.appendToLastLine( ' \\{} {}'.format( marker2, target ) )
                            else: halt
                        else: # Why do we get xt's embedded inside other xt's???
                            if debuggingThisModule: print( "USFXXMLBible.loadCrossreference: m={!r} xTxt={!r} m2={!r} xTxt2={!r} xTl2={!r} at {}".format( marker, xText, marker2, xText2, xTail2, sub2location ) )
                            logging.critical( _("USFXXMLBible.loadCrossreference: Bad nesting of xt:"), "m={!r} xTxt={!r} m2={!r} xTxt2={!r} xTl2={!r} at {}".format( marker, xText, marker2, xText2, xTail2, sub2location ) )
                        if xTail2: self.thisBook.appendToLastLine( xTail2 )
                else: halt
            if xTail:
                self.thisBook.appendToLastLine( '\\{}*{}'.format( marker, xTail ) )
        self.thisBook.appendToLastLine( '\\x*{}'.format( (' '+tail) if tail else '' ) )
    #end of USFXXMLBible.loadCrossreference
# end of class USFXXMLBible



def demo() -> None:
    """
    Demonstrate reading and checking some Bible databases.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0:
        print( programNameVersionDate if BibleOrgSysGlobals.verbosityLevel > 1 else programNameVersion )
        if __name__ == '__main__' and BibleOrgSysGlobals.verbosityLevel > 1:
            latestPythonModificationDate = BibleOrgSysGlobals.getLatestPythonModificationDate()
            if latestPythonModificationDate != LAST_MODIFIED_DATE:
                print( f"  (Last BibleOrgSys code update was {latestPythonModificationDate})" )

    if 0: # demo the file checking code -- first with the whole folder and then with only one folder
        testFolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFXTest1/' )
        resultA1 = USFXXMLBibleFileCheck( testFolder )
        if BibleOrgSysGlobals.verbosityLevel > 0: print( "TestA1", resultA1 )
        resultA2 = USFXXMLBibleFileCheck( testFolder, autoLoad=True )
        if BibleOrgSysGlobals.verbosityLevel > 0: print( "TestA2", resultA2 )
        resultA3 = USFXXMLBibleFileCheck( testFolder, autoLoadBooks=True )
        if BibleOrgSysGlobals.verbosityLevel > 0: print( "TestA3", resultA3 )

        #testSubfolder = os.path.join( testFolder, 'nrsv_update/' )
        #resultB1 = USFXXMLBibleFileCheck( testSubfolder )
        #if BibleOrgSysGlobals.verbosityLevel > 0: print( "TestB1", resultB1 )
        #resultB2 = USFXXMLBibleFileCheck( testSubfolder, autoLoad=True, autoLoadBooks=True )
        #if BibleOrgSysGlobals.verbosityLevel > 0: print( "TestB2", resultB2 )


    BiblesFolderpath = BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Bibles/' )
    if 1:
        testData = (
                    ('GLW', BiblesFolderpath.joinpath( '/USFX Bibles/Haiola USFX test versions/eng-glw_usfx/') ),
                    ('ASV', BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'USFXTest1/') ),
                    ('Tst', BiblesFolderpath.joinpath( 'Formats/USFX/') ,),
                    ('AGM', BiblesFolderpath.joinpath( 'USFX Bibles/Haiola USFX test versions/agm_usfx/'),),
                    ('HBO', BiblesFolderpath.joinpath( 'USFX Bibles/Haiola USFX test versions/hbo_usfx/'),),
                    ('ZIA', BiblesFolderpath.joinpath( 'USFX Bibles/Haiola USFX test versions/zia_usfx/'),),
                    ) # You can put your USFX test folder here

        for name, testFolder in testData:
            if os.access( testFolder, os.R_OK ):
                UsfxB = USFXXMLBible( testFolder, name )
                UsfxB.load()
                if BibleOrgSysGlobals.verbosityLevel > 0: print( UsfxB )
                if BibleOrgSysGlobals.strictCheckingFlag: UsfxB.check()
                if BibleOrgSysGlobals.commandLineArguments.export: UsfxB.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
                #UsfxBErrors = UsfxB.getErrors()
                # print( UsfxBErrors )
                #print( UsfxB.getVersification() )
                #print( UsfxB.getAddedUnits() )
                #for ref in ('GEN','Genesis','GeNeSiS','Gen','MrK','mt','Prv','Xyz',):
                    ##print( "Looking for", ref )
                    #print( "Tried finding {!r} in {!r}: got {!r}".format( ref, name, UsfxB.getXRefBBB( ref ) ) )
            else: print( f"Sorry, test folder '{testFolder}' is not readable on this computer." )
# end of demo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    demo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of USFXXMLBible.py
