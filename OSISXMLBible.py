#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# OSISXMLBible.py
#   Last modified: 2013-07-19 by RJH (also update ProgVersion below)
#
# Module handling OSIS XML Bibles
#
# Copyright (C) 2010-2013 Robert Hunt
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
Module handling the reading and import of OSIS XML Bibles.

Unfortunately, the OSIS specification (designed by committee for many different tasks)
    allows many different ways of encoding Bibles so the variations are very many.

This is a quickly updated version of an early module,
    and it's both ugly and fragile  :-(
"""

ProgName = "OSIS XML Bible format handler"
ProgVersion = "0.25"
ProgNameVersion = "{} v{}".format( ProgName, ProgVersion )

debuggingThisModule = False


import logging, os
from gettext import gettext as _
#from collections import OrderedDict
from xml.etree.ElementTree import ElementTree

import Globals
from ISO_639_3_Languages import ISO_639_3_Languages
from Bible import Bible, BibleBook


filenameEndingsToIgnore = ('.ZIP.GO', '.ZIP.DATA',) # Must be UPPERCASE
extensionsToIgnore = ('ZIP', 'BAK', 'LOG', 'HTM','HTML', 'USX', 'TXT', 'STY', 'LDS', 'SSF', 'VRS',) # Must be UPPERCASE



def OSISXMLBibleFileCheck( givenFolderName, strictCheck=True, autoLoad=False ):
    """
    Given a folder, search for OSIS XML Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number found.

    if autoLoad is true and exactly one OSIS Bible is found,
        returns the loaded OSISXMLBible object.
    """
    if Globals.verbosityLevel > 2: print( "OSISXMLBibleFileCheck( {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad ) )
    if Globals.debugFlag: assert( givenFolderName and isinstance( givenFolderName, str ) )
    if Globals.debugFlag: assert( autoLoad in (True,False,) )

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( _("OSISXMLBibleFileCheck: Given '{}' folder is unreadable").format( givenFolderName ) )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( _("OSISXMLBibleFileCheck: Given '{}' path is not a folder").format( givenFolderName ) )
        return False

    # Find all the files and folders in this folder
    if Globals.verbosityLevel > 3: print( " OSISXMLBibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
    foundFolders, foundFiles = [], []
    for something in os.listdir( givenFolderName ):
        somepath = os.path.join( givenFolderName, something )
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
    if '__MACOSX' in foundFolders:
        foundFolders.remove( '__MACOSX' )  # don't visit these directories
    #print( 'ff', foundFiles )

    # See if there's an OpenSong project here in this folder
    numFound = 0
    looksHopeful = False
    lastFilenameFound = None
    for thisFilename in sorted( foundFiles ):
        if strictCheck or Globals.strictCheckingFlag:
            firstLines = Globals.peekIntoFile( thisFilename, givenFolderName, numLines=3 )
            if not firstLines or len(firstLines)<2: continue
            if not firstLines[0].startswith( '<?xml version="1.0"' ) \
            and not firstLines[0].startswith( '\ufeff<?xml version="1.0"' ): # same but with BOM
                if Globals.verbosityLevel > 2: print( "OB (unexpected) first line was '{}' in {}".format( firstLines, thisFilename ) )
                continue
            if not (firstLines[1].startswith( '<osis ' ) or firstLines[2].startswith( '<osis ' )):
                continue
        lastFilenameFound = thisFilename
        numFound += 1
    if numFound:
        if Globals.verbosityLevel > 2: print( "OSISXMLBibleFileCheck got", numFound, givenFolderName, lastFilenameFound )
        if numFound == 1 and autoLoad:
            ub = OSISXMLBible( givenFolderName, lastFilenameFound )
            ub.load() # Load and process the file
            return ub
        return numFound
    elif looksHopeful and Globals.verbosityLevel > 2: print( "    Looked hopeful but no actual files found" )

    # Look one level down
    numFound = 0
    foundProjects = []
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
        if Globals.verbosityLevel > 3: print( "    OSISXMLBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
        foundSubfolders, foundSubfiles = [], []
        for something in os.listdir( tryFolderName ):
            somepath = os.path.join( givenFolderName, thisFolderName, something )
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

        # See if there's an OS project here in this folder
        for thisFilename in sorted( foundSubfiles ):
            if strictCheck or Globals.strictCheckingFlag:
                firstLines = Globals.peekIntoFile( thisFilename, tryFolderName, numLines=2 )
                if not firstLines or len(firstLines)<2: continue
                if not firstLines[0].startswith( '<?xml version="1.0"' ) \
                and not firstLines[0].startswith( '\ufeff<?xml version="1.0"' ): # same but with BOM
                    if Globals.verbosityLevel > 2: print( "OB (unexpected) first line was '{}' in {}".format( firstLines, thisFilename ) )
                    continue
                if not firstLines[1].startswith( '<osis ' ):
                    continue
            foundProjects.append( (tryFolderName, thisFilename,) )
            lastFilenameFound = thisFilename
            numFound += 1
    if numFound:
        if Globals.verbosityLevel > 2: print( "OSISXMLBibleFileCheck foundProjects", numFound, foundProjects )
        if numFound == 1 and autoLoad:
            if Globals.debugFlag: assert( len(foundProjects) == 1 )
            ub = OSISXMLBible( foundProjects[0][0], foundProjects[0][1] ) # Folder and filename
            ub.load() # Load and process the file
            return ub
        return numFound
# end of OSISXMLBibleFileCheck



class OSISXMLBible( Bible ):
    """
    Class for reading, validating, and converting OSISXMLBible XML.
    This is only intended as a transitory class (used at start-up).
    The OSISXMLBible class has functions more generally useful.
    """
    filenameBase = "OSISXMLBible"
    XMLNameSpace = "{http://www.w3.org/XML/1998/namespace}"
    OSISNameSpace = "{http://www.bibletechnologies.net/2003/OSIS/namespace}"
    treeTag = OSISNameSpace + "osis"
    textTag = OSISNameSpace + "osisText"
    headerTag = OSISNameSpace + "header"
    divTag = OSISNameSpace + "div"


    def __init__( self, sourceFilepath, givenName=None, encoding='utf-8' ):
        """
        Constructor: just sets up the OSIS Bible object.
        """
         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = "OSIS XML Bible object"
        self.objectTypeString = "OSIS"

        # Now we can set our object variables
        self.sourceFilepath, self.givenName, self.encoding  = sourceFilepath, givenName, encoding


        self.title = self.version = self.date = None
        self.tree = self.header = self.frontMatter = self.divs = self.divTypesString = None
        #self.bkData, self.USFMBooks = OrderedDict(), OrderedDict()
        self.lang = self.language = None


        # Do a preliminary check on the readability of our file(s)
        self.possibleFilenames = []
        if os.path.isdir( self.sourceFilepath ): # We've been given a folder -- see if we can find the files
            # There's no standard for OSIS xml file naming
            fileList = os.listdir( self.sourceFilepath )
            #print( len(fileList), fileList )
            # First try looking for OSIS book names
            for filename in fileList:
                if filename.lower().endswith('.xml'):
                    thisFilepath = os.path.join( self.sourceFilepath, filename )
                    if Globals.debugFlag: print( "Trying {}...".format( thisFilepath ) )
                    if os.access( thisFilepath, os.R_OK ): # we can read that file
                        self.possibleFilenames.append( filename )
        elif not os.access( self.sourceFilepath, os.R_OK ):
            logging.critical( "OSISXMLBible: File '{}' is unreadable".format( self.sourceFilepath ) )
            return # No use continuing

        self.name = self.givenName
        #if self.name is None:
            #pass

        # Get the data tables that we need for proper checking
        self.ISOLanguages = ISO_639_3_Languages().loadData()
    # end of OSISXMLBible.__init__
    #def x__init__( self, XMLFilepath ):
        #"""
        #Constructor: expects the filepath of the source XML file.
        #Loads (and crudely validates the XML file(s)) into an element tree(s).
        #"""

        #def processFile( filepath ):
            #""" Load and convert an OSIS Bible file. """
            #obc = OSISXMLBible() # Create the empty object
            #thisBook Data, thisUSFMData = obc.loadValidateExtract( filepath ) # Load the XML
            #for BBB in thisBook Data:
                #if BBB in self.bkData: logging.warning( _("Have multiple {} OSIS book data").format( BBB ) )
                #self.bkData[BBB] = thisBook Data[BBB]
            #for BBB in thisUSFMData:
                #if BBB in self.USFMData: logging.warning( _("Have multiple {} OSIS USFM book data").format( BBB ) )
                #self.USFMData[BBB] = thisUSFMData[BBB]
            ##result = obc.importDataToPython() # not finished yet ................. XXXXXXXXXXXXXXXXXXXXXX
            ##for BBB in result:
            ##    if BBB in self.books: logging.warning( _("Have multiple {} OSIS books").format( BBB ) )
            ##    self.books[BBB] = result[BBB]
        ## end of processFile

        ##self.books = {}
        #self.bkData, self.USFMData = OrderedDict(), OrderedDict()
        #if os.path.isdir( XMLFilepath ): # We've been given a folder -- see if we can find the files
            ## There's no standard for OSIS xml file naming
            #files = os.listdir( XMLFilepath )
            #print( len(files), files )
            ## First try looking for OSIS book names
            #if 1: # new code
                #for filename in files:
                    #if filename.lower().endswith('.xml'):
                        #thisFilepath = os.path.join( XMLFilepath, filename )
                        #if Globals.debugFlag: print( "Trying {}...".format( thisFilepath ) )
                        #if os.access( thisFilepath, os.R_OK ): # we can read that file
                            #processFile( thisFilepath )
            #else: # old code
                #print( len(Globals.BibleBooksCodes.getAllOSISBooksCodes()), Globals.BibleBooksCodes.getAllOSISBooksCodes() )
                #for OSISCode in Globals.BibleBooksCodes.getAllOSISBooksCodes(): # Not necessarily in any useful order
                    #possibleFilepath = os.path.join( XMLFilepath, OSISCode + '.xml' )
                    #if Globals.debugFlag: print( "Looking for {}...".format( possibleFilepath ) )
                    #for filename in files:
                        #if filename.lower() == (OSISCode + '.xml').lower():
                            #thisFilepath = os.path.join( XMLFilepath, filename )
                            #if os.access( thisFilepath, os.R_OK ): # we can read that file
                                #processFile( thisFilepath )
                #if not self.USFMData: # Try looking for any .xml files
                    #for filename in files:
                        #if filename.lower().endswith('.xml'):
                            #thisFilepath = os.path.join( XMLFilepath, filename )
                            #if Globals.debugFlag: print( "Trying {}...".format( thisFilepath ) )
                            #if os.access( thisFilepath, os.R_OK ): # we can read that file
                                #processFile( thisFilepath )
        #else: # it must have been a single filename (but it might contain a single book or multiple books)
            #processFile( XMLFilepath )
            ##obc = OSISXMLBible() # Create the empty object
            ##obc.loadValidateExtract( XMLFilepath ) # Load the XML
            ##self.books = obc.importDataToPython()
    ## end of __init__



    #def x__str__( self ):
        #"""
        #This method returns the string representation of a OSIS Bible converter object.

        #@return: the name of a OSIS Bible converter object formatted as a string
        #@rtype: string
        #"""
        #result = "OSIS Bible File Converter object"
        #if self.title: result += ('\n' if result else '') + "  " + self.title
        #if self.version: result += ('\n' if result else '') + "  " + _("Version: {} ").format( self.version )
        #if self.date: result += ('\n' if result else '') + "  " + _("Date: {}").format( self.date )
        #result += ('\n' if result else '') + "  " + _("Number of '{}' entries = {}").format( self.divTypesString, len(self.divs) )
        #return result
    ## end of __str__
    #def x__str__( self ):
        #"""
        #This method returns the string representation of an OSIS Bible.

        #@return: the name of a Bible object formatted as a string
        #@rtype: string
        #"""
        #result = "OSIS Bible object"
        ##if self.title: result += ('\n' if result else '') + self.title
        ##if self.version: result += ('\n' if result else '') + "Version: {} ".format( self.version )
        ##if self.date: result += ('\n' if result else '') + "Date: {}".format( self.date )
        ##useThis = self.books
        #useThis = self.bkData
        #if len(useThis)==1:
            #for BBB in useThis: break # Just get the first one
            #result += ('\n' if result else '') + "  " + _("Contains one book: {}").format( BBB )
        #else: result += ('\n' if result else '') + "  " + _("Number of books = {}").format( len(useThis) )
        #return result
    ## end of __str__


    def load( self ):
        """
        Loads the OSIS XML file or files.
        """
        if self.possibleFilenames: # then we possibly have multiple files, probably one for each book
            for filename in self.possibleFilenames:
                pathname = os.path.join( self.sourceFilepath, filename )
                self.loadFile( pathname )
        else: # most often we have all the Bible books in one file
            self.loadFile( self.sourceFilepath )

        #def processFile( filepath ):
            #""" Load and convert an OSIS Bible file. """
            #obc = OSISXMLBible() # Create the empty object
            #thisBook Data, thisUSFMData = obc.loadValidateExtract( filepath ) # Load the XML
            #for BBB in thisBook Data:
                #if BBB in self.books: logging.warning( _("Have multiple {} OSIS book data").format( BBB ) )
                #self.books[BBB] = thisBook Data[BBB]
            #for BBB in thisUSFMData:
                #if BBB in self.USFMData: logging.warning( _("Have multiple {} OSIS USFM book data").format( BBB ) )
                #self.USFMData[BBB] = thisUSFMData[BBB]
    # end of OSISXMLBible.load


    def loadFile( self, OSISFilepath ):
        """
        Load a single source XML file and remove the header from the tree.
        Also, extracts some useful elements from the header element.
        """
        if Globals.verbosityLevel > 2: print( _("Loading {}...").format( OSISFilepath ) )
        self.tree = ElementTree().parse( OSISFilepath )
        if Globals.debugFlag: assert( len ( self.tree ) ) # Fail here if we didn't load anything at all

        # Find the main (osis) container
        if self.tree.tag == OSISXMLBible.treeTag:
            location = "OSIS file"
            Globals.checkXMLNoText( self.tree, location, '4f6h' )
            Globals.checkXMLNoTail( self.tree, location, '1wk8' )
            # Process the attributes first
            self.schemaLocation = None
            for attrib,value in self.tree.items():
                if attrib.endswith("schemaLocation"):
                    self.schemaLocation = value
                else:
                    logging.warning( "fv6g Unprocessed {} attribute ({}) in {}".format( attrib, value, location ) )

            # Find the submain (osisText) container
            if len(self.tree)==1 and self.tree[0].tag == OSISXMLBible.textTag:
                sublocation = "osisText in " + location
                textElement = self.tree[0]
                Globals.checkXMLNoText( textElement, sublocation, '3b5g' )
                Globals.checkXMLNoTail( textElement, sublocation, '7h9k' )
                # Process the attributes first
                self.osisIDWork = self.osisRefWork = None
                for attrib,value in textElement.items():
                    if attrib=='osisIDWork':
                        self.osisIDWork = value
                    elif attrib=='osisRefWork':
                        self.osisRefWork = value
                    elif attrib==OSISXMLBible.XMLNameSpace+'lang':
                        self.lang = value
                    else:
                        logging.warning( "gb2d Unprocessed {} attribute ({}) in {}".format( attrib, value, sublocation ) )
                if self.osisRefWork:
                    if self.osisRefWork not in ('bible','Bible','defaultReferenceScheme',):
                        logging.warning( "New variety of osisRefWork: '{}'".format( self.osisRefWork ) )
                if self.lang:
                    if self.lang in ('en','he','my',): # Only had these ones so far (English, Hebrew, my??)
                        if Globals.verbosityLevel > 2: print( "    Language is '{}'".format( self.lang ) )
                    else:
                        logging.warning( "Discovered an unknown '{}' language".format( self.lang ) )
                if Globals.verbosityLevel > 2: print( "  osisIDWork is '{}'".format( self.osisIDWork ) )

                # Find (and move) the header container
                if textElement[0].tag == OSISXMLBible.headerTag:
                    self.header = textElement[0]
                    textElement.remove( self.header )
                    self.validateHeader( self.header )
                else:
                    logging.warning( "Missing header element (looking for '{}' tag)".format( OSISXMLBible.headerTag ) )

                # Find (and move) the optional front matter (div) container
                if textElement[0].tag == OSISXMLBible.OSISNameSpace + "div":
                    sub2location = "div of " + sublocation
                    # Process the attributes first
                    div0Type = div0OsisID = None
                    for attrib,value in textElement[0].items():
                        if attrib=='type':
                            div0Type = value
                        elif attrib=='osisID':
                            div0OsisID = value
                        else:
                            logging.warning( "7j4d Unprocessed {} attribute ({}) in {}".format( attrib, value, sub2location ) )
                    if div0Type == 'front':
                        self.frontMatter = textElement[0]
                        textElement.remove( self.frontMatter )
                        self.validateFrontMatter( self.frontMatter )
                    else:
                        logging.info( "Missing front matter division" )

                self.divs, self.divTypesString = [], None
                for element in textElement:
                    if element.tag == OSISXMLBible.divTag:
                        sub2location = "div in " + sublocation
                        Globals.checkXMLNoText( element, sub2location, '3a2s' )
                        Globals.checkXMLNoTail( element, sub2location, '4k8a' )
                        divType = element.get( "type" )
                        if divType is None:
                            logging.error( "Missing div type in OSIS file" )
                        if divType != self.divTypesString:
                            if not self.divTypesString: self.divTypesString = divType
                            else: self.divTypesString = 'MixedTypes'
                        self.validateAndExtractMainDiv( element )
                        self.divs.append( element )
                    else:
                        logging.error( "Expected to find '{}' but got '{}'".format( OSISXMLBible.divTag, element.tag ) )
            else:
                logging.error( "Expected to find '{}' but got '{}'".format( OSISXMLBible.textTag, self.tree[0].tag ) )
        else:
            logging.error( "Expected to load '{}' but got '{}'".format( OSISXMLBible.treeTag, self.tree.tag ) )
        if self.tree.tail is not None and self.tree.tail.strip():
            logging.error( "Unexpected '{}' tail data after {} element".format( self.tree.tail, self.tree.tag ) )

        #if Globals.commandLineOptions.export: self.exportUSFM()
        #return self.bkData, self.USFMBooks
    # end of OSISXMLBible.loadFile


    def validateHeader( self, header ):
        """
        Check/validate the given OSIS header record.
        """
        if Globals.verbosityLevel > 3: print( _("Validating OSIS header...") )
        headerlocation = "header"
        Globals.checkXMLNoText( header, headerlocation, '2s90' )
        Globals.checkXMLNoTail( header, headerlocation, '0k6l' )
        Globals.checkXMLNoAttributes( header, headerlocation, '4f6h' )

        numWorks = 0
        for element in header:
            if element.tag == OSISXMLBible.OSISNameSpace+"revisionDesc":
                location = "revisionDesc of " + headerlocation
                Globals.checkXMLNoText( header, location, '2t5y' )
                Globals.checkXMLNoTail( header, location, '3a1l' )
                Globals.checkXMLNoAttributes( header, location, '6hj8' )
                # Process the attributes first
                resp = None
                for attrib,value in element.items():
                    if attrib=="resp":
                        resp = value
                    else: logging.warning( "4j6a Unprocessed {} attribute ({}) in {}".format( attrib, value, location ) )

                # Now process the subelements
                for subelement in element.getchildren():
                    Globals.checkXMLNoSubelements( subelement, location, '4f3f' )
                    if len(subelement): logging.warning( "Unexpected {} subelements in subelement {} in {} revisionDesc".format( len(subelement), subelement.tag, osisWork ) )
                    if subelement.tag == OSISXMLBible.OSISNameSpace+"date":
                        sublocation = "date of " + location
                        Globals.checkXMLNoTail( subelement, sublocation, '4sd2' )
                        Globals.checkXMLNoAttributes( subelement, sublocation, '9hj5' )
                        Globals.checkXMLNoSubelements( subelement, sublocation, '6g3s' )
                        date = subelement.text
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+"p":
                        sublocation = "p of " + location
                        Globals.checkXMLNoTail( subelement, sublocation, '9k5a' )
                        Globals.checkXMLNoAttributes( subelement, sublocation, '4f4s' )
                        Globals.checkXMLNoSubelements( subelement, sublocation, '3c5g' )
                        p = element.text
                    else: logging.warning( "6g4g Unprocessed '{}' sub-element ({}) in revisionDesc element".format( subelement.tag, subelement.text ) )
            elif element.tag == OSISXMLBible.OSISNameSpace+"work":
                location = "work of " + headerlocation
                Globals.checkXMLNoText( header, location, '5h9k' )
                Globals.checkXMLNoTail( header, location, '1d4f' )
                Globals.checkXMLNoAttributes( header, location, '2s3d' )
                # Process the attributes first
                osisWork = lang = None
                for attrib,value in element.items():
                    if attrib=="osisWork":
                        osisWork = value
                        if Globals.verbosityLevel > 2: print( "  Have a '{}' work".format( osisWork ) )
                    elif attrib==OSISXMLBible.XMLNameSpace+"lang":
                        lang = value
                    else: logging.warning( "2k5s Unprocessed {} attribute ({}) in work element".format( attrib, value ) )
                # Now process the subelements
                for subelement in element.getchildren():
                    if len(subelement): logging.warning( "Unexpected {} subelements in subelement {} in {} work".format( len(subelement), subelement.tag, osisWork ) )
                    if subelement.tag == OSISXMLBible.OSISNameSpace+"title":
                        sublocation = "title of " + location
                        Globals.checkXMLNoTail( subelement, sublocation, '8k0k' )
                        Globals.checkXMLNoSubelements( subelement, sublocation, '0k5f' )
                        if not self.title: self.title = subelement.text # Take the first title
                        titleType = None
                        for attrib,value in subelement.items():
                            if attrib=="type":
                                titleType = value
                            else: logging.warning( "8f83 Unprocessed '{}' attribute ({}) in {}".format( attrib, value, sublocation ) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+"version":
                        sublocation = "version of " + location
                        Globals.checkXMLNoText( subelement, sublocation, '3g1h' )
                        Globals.checkXMLNoTail( subelement, sublocation, '0k3d' )
                        Globals.checkXMLNoAttributes( subelement, sublocation, '7h4f' )
                        Globals.checkXMLNoSubelements( subelement, sublocation, '2j9z' )
                        self.version = subelement.text
                        for attrib,value in subelement.items():
                            logging.warning( "93d2 Unprocessed '{}' attribute ({}) in {}".format( attrib, value, sublocation ) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+"date":
                        sublocation = "date of " + location
                        Globals.checkXMLNoTail( subelement, sublocation, '3f9j' )
                        Globals.checkXMLNoSubelements( subelement, sublocation, '4x5h' )
                        date = subelement.text
                        dateType = dateEvent = None
                        for attrib,value in subelement.items():
                            if attrib=="type":
                                dateType = value
                            elif attrib=="event":
                                dateEvent = value
                            else: logging.warning( "2k4d Unprocessed '{}' attribute ({}) in {}".format( attrib, value, sublocation ) )
                        if Globals.debugFlag: assert( dateType in (None,'Gregorian',) )
                        if Globals.debugFlag: assert( dateEvent in (None,'eversion',) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+"creator":
                        sublocation = "creator of " + location
                        Globals.checkXMLNoTail( subelement, sublocation, '3n5z' )
                        Globals.checkXMLNoSubelements( subelement, sublocation, '9n3z' )
                        self.creator = subelement.text
                        creatorRole = creatorType = None
                        for attrib,value in subelement.items():
                            if attrib=="role":
                                creatorRole = value
                            elif attrib=="type":
                                creatorType = value
                            else: logging.warning( "9f2d Unprocessed '{}' attribute ({}) in {}".format( attrib, value, sublocation ) )
                        if Globals.verbosityLevel > 2: print( "    Creator (role='{}'{}) was '{}'".format( creatorRole, ", type='{}'".format(creatorType) if creatorType else '', self.creator ) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+"contributor":
                        sublocation = "contributor of " + location
                        Globals.checkXMLNoTail( subelement, sublocation, '3z4o' )
                        Globals.checkXMLNoSubelements( subelement, sublocation, '2u5z' )
                        self.contributor = subelement.text
                        contributorRole = None
                        for attrib,value in subelement.items():
                            if attrib=="role":
                                contributorRole = value
                            else: logging.warning( "1s5g Unprocessed '{}' attribute ({}) in {}".format( attrib, value, sublocation ) )
                        if Globals.verbosityLevel > 2: print( "    Contributor ({}) was '{}'".format( contributorRole, self.contributor ) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+"subject":
                        sublocation = "subject of " + location
                        Globals.checkXMLNoTail( subelement, sublocation, 'c35g' )
                        Globals.checkXMLNoAttributes( subelement, sublocation, 'frg3' )
                        Globals.checkXMLNoSubelements( subelement, sublocation, 'ft4g' )
                        self.subject = subelement.text
                        if Globals.verbosityLevel > 2: print( "    Subject was '{}'".format( self.subject ) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+"description":
                        sublocation = "description of " + location
                        Globals.checkXMLNoTail( subelement, sublocation, '1j6z' )
                        Globals.checkXMLNoSubelements( subelement, sublocation, '4a7s' )
                        self.description = subelement.text
                        descriptionType = descriptionSubType = resp = None
                        for attrib,value in subelement.items():
                            if attrib=="type":
                                descriptionType = value
                            elif attrib=="subType":
                                descriptionSubType = value
                            elif attrib=="resp":
                                resp = value
                            else: logging.warning( "6f3d Unprocessed '{}' attribute ({}) in {}".format( attrib, value, sublocation ) )
                        if descriptionType: assert( descriptionType == 'usfm' )
                        if descriptionType or self.description and Globals.verbosityLevel > 2: print( "    Description{} is '{}'".format( " ({})".format(descriptionType) if descriptionType else '', self.description ) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+"format":
                        sublocation = "format of " + location
                        Globals.checkXMLNoTail( subelement, sublocation, '5n3x' )
                        Globals.checkXMLNoSubelements( subelement, sublocation, '8v3x' )
                        self.format = subelement.text
                        formatType = None
                        for attrib,value in subelement.items():
                            if attrib=="type":
                                formatType = value
                            else: logging.warning( "2f5s Unprocessed '{}' attribute ({}) in {}".format( attrib, value, sublocation ) )
                        if Globals.debugFlag: assert( formatType == 'x-MIME' )
                        if Globals.verbosityLevel > 2: print( "    Format ({}) is '{}'".format( formatType, self.format ) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+"type":
                        sublocation = "type of " + location
                        Globals.checkXMLNoTail( subelement, sublocation, '3b4z' )
                        Globals.checkXMLNoSubelements( subelement, sublocation, '8j8b' )
                        self.type = subelement.text
                        typeType = None
                        for attrib,value in subelement.items():
                            if attrib=="type":
                                typeType = value
                            else: logging.warning( "7j3f Unprocessed '{}' attribute ({}) in {}".format( attrib, value, sublocation ) )
                        if Globals.debugFlag: assert( typeType == 'OSIS' )
                        if Globals.verbosityLevel > 2: print( "    Type ({}) is '{}'".format( typeType, self.type ) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+"identifier":
                        sublocation = "identifier of " + location
                        Globals.checkXMLNoTail( subelement, sublocation, '5a2m' )
                        Globals.checkXMLNoSubelements( subelement, sublocation, '2x6e' )
                        self.identifier = subelement.text
                        identifierType = None
                        for attrib,value in subelement.items():
                            if attrib=="type":
                                identifierType = value
                            else: logging.warning( "2d5g Unprocessed '{}' attribute ({}) in {}".format( attrib, value, sublocation ) )
                        #print( identifierType )
                        if Globals.debugFlag: assert( identifierType in ('OSIS','URL') )
                        if Globals.verbosityLevel > 2: print( "    Identifier ({}) is '{}'".format( identifierType, self.identifier ) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+"source":
                        sublocation = "source of " + location
                        Globals.checkXMLNoTail( subelement, sublocation, '1i8p' )
                        Globals.checkXMLNoAttributes( subelement, sublocation, '4gh7' )
                        Globals.checkXMLNoSubelements( subelement, sublocation, '6p3a' )
                        self.source = subelement.text
                        sourceRole = None
                        for attrib,value in subelement.items():
                            if attrib=="role":
                                sourceRole = value
                            else: logging.warning( "6h7h Unprocessed '{}' attribute ({}) in {}".format( attrib, value, sublocation ) )
                        if Globals.verbosityLevel > 2: print( "    Source{} was '{}'".format( " ({})".format(sourceRole) if sourceRole else '', self.source ) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+"publisher":
                        sublocation = "publisher of " + location
                        Globals.checkXMLNoTail( subelement, sublocation, '3z7g' )
                        Globals.checkXMLNoAttributes( subelement, sublocation, '2d56' )
                        Globals.checkXMLNoSubelements( subelement, sublocation, '8n3x' )
                        self.publisher = subelement.text.replace( '&amp;', '&' )
                        for attrib,value in subelement.items():
                            if attrib=="xxxrole":
                                pass
                            else: logging.warning( "7g5g Unprocessed '{}' attribute ({}) in {}".format( attrib, value, sublocation ) )
                        if Globals.verbosityLevel > 2: print( "    Publisher is/was '{}'".format( self.publisher ) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+"scope":
                        sublocation = "scope of " + location
                        Globals.checkXMLNoTail( subelement, sublocation, '1z4i' )
                        Globals.checkXMLNoAttributes( subelement, sublocation, '3d4d' )
                        Globals.checkXMLNoSubelements( subelement, sublocation, '2g5z' )
                        self.scope = subelement.text
                        if Globals.verbosityLevel > 2: print( "    Scope is '{}'".format( self.scope ) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+"coverage":
                        sublocation = "coverage of " + location
                        Globals.checkXMLNoTail( subelement, sublocation, '9l2p' )
                        Globals.checkXMLNoAttributes( subelement, sublocation, '3d6g' )
                        Globals.checkXMLNoSubelements( subelement, sublocation, '3a6p' )
                        self.coverage = subelement.text
                        if Globals.verbosityLevel > 2: print( "    Coverage is '{}'".format( self.coverage ) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+"refSystem":
                        sublocation = "refSystem of " + location
                        Globals.checkXMLNoTail( subelement, sublocation, '3p65' )
                        Globals.checkXMLNoAttributes( subelement, sublocation, '2s4f' )
                        Globals.checkXMLNoSubelements( subelement, sublocation, '3mtp' )
                        self.refSystem = subelement.text
                        if self.refSystem in ('Bible','Bible.KJV','Bible.NRSVA','Dict.Strongs','Dict.Robinsons','Dict.strongMorph',):
                            if Globals.verbosityLevel > 2: print( "    Reference system is '{}'".format( self.refSystem ) )
                        else: print( "Discovered an unknown '{}' refSystem".format( self.refSystem ) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+"language":
                        sublocation = "language of " + location
                        Globals.checkXMLNoTail( subelement, sublocation, '4v2n' )
                        Globals.checkXMLNoSubelements( subelement, sublocation, '8n34' )
                        self.language = subelement.text
                        languageType = None
                        for attrib,value in subelement.items():
                            if attrib=="type":
                                languageType = value
                            else: logging.warning( "6g4f Unprocessed '{}' attribute ({}) in {}".format( attrib, value, sublocation ) )
                        if languageType in ('SIL','IETF',):
                            if self.ISOLanguages.isValidLanguageCode( self.language ):
                                if Globals.verbosityLevel > 2: print( "  Language is: {}".format( self.ISOLanguages.getLanguageName( self.language ) ) )
                            else: print( "Discovered an unknown '{}' language".format( self.language ) )
                        else: print( "Discovered an unknown '{}' languageType".format( languageType ) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+"rights":
                        sublocation = "rights of " + location
                        Globals.checkXMLNoTail( subelement, sublocation, '6v2x' )
                        Globals.checkXMLNoSubelements( subelement, sublocation, '9l5b' )
                        self.rights = subelement.text
                        copyrightType = None
                        for attrib,value in subelement.items():
                            if attrib=="type":
                                copyrightType = value
                            else: logging.warning( "1s3d Unprocessed '{}' attribute ({}) in {}".format( attrib, value, sublocation ) )
                        if Globals.debugFlag: assert( copyrightType in (None,'x-copyright','x-license','x-license-url',) )
                        if Globals.verbosityLevel > 2: print( "    Rights{} are/were '{}'".format( " ({})".format(copyrightType) if copyrightType else '', self.rights ) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+"relation":
                        sublocation = "relation of " + location
                        Globals.checkXMLNoText( subelement, sublocation, 'g4h2' )
                        Globals.checkXMLNoTail( subelement, sublocation, 'gh53' )
                        Globals.checkXMLNoAttributes( subelement, sublocation, 'd2fd' )
                        Globals.checkXMLNoSubelements( subelement, sublocation, 's2fy' )
                    else: logging.warning( "7h5g Unprocessed '{}' sub-element ({}) in {}".format( subelement.tag, subelement.text, location) )
                #if element.find("date") is not None: self.date = element.find("date").text
                #if element.find("title") is not None: self.title = element.find("title").text
                numWorks += 1
            elif element.tag == OSISXMLBible.OSISNameSpace+"workPrefix":
                location = "workPrefix of " + headerlocation
                Globals.checkXMLNoText( header, location, 'f5h8' )
                Globals.checkXMLNoTail( header, location, 'f2g7' )
                Globals.checkXMLNoAttributes( header, location, '6g4f' )
                # Process the attributes first
                for attrib,value in element.items():
                    if attrib=="path":
                        pass
                    elif attrib=="osisWork":
                        pass
                    else: logging.warning( "7yh4 Unprocessed {} attribute ({}) in workPrefix element".format( attrib, value ) )
                # Now process the subelements
                for subelement in element.getchildren():
                    if subelement.tag == OSISXMLBible.OSISNameSpace+"revisionDesc":
                        sublocation = "revisionDesc of " + location
                        Globals.checkXMLNoText( subelement, sublocation, 'c3t5' )
                        Globals.checkXMLNoTail( subelement, sublocation, 'z2f8' )
                        Globals.checkXMLNoAttributes( subelement, sublocation, '2w3e' )
                        Globals.checkXMLNoSubelements( subelement, sublocation, 'm5o0' )
                        #self.something = subelement.text
                        for attrib,value in subelement.items():
                            logging.warning( "3h6r Unprocessed '{}' attribute ({}) in {} subelement of workPrefix element".format( attrib, value, subelement.tag ) )
                    else: logging.warning( "8h4g Unprocessed '{}' sub-element ({}) in workPrefix element".format( subelement.tag, subelement.text ) )
            else: logging.error( "Expected to load '{}' but got '{}'".format( OSISXMLBible.OSISNameSpace+"work", element.tag ) )
            if element.tail is not None and element.tail.strip(): logging.error( "Unexpected '{}' tail data after {} element in header element".format( element.tail, element.tag ) )
        if not numWorks: logging.warning( "OSIS header doesn't specify any work records." )
    # end of OSISXMLBible.validateHeader


    def validateFrontMatter( self, frontMatter ):
        """
        Check/validate the given OSIS front matter (div) record.
        """
        if Globals.verbosityLevel > 3: print( _("Validating OSIS front matter...") )
        frontMatterLocation = "frontMatter"
        Globals.checkXMLNoText( frontMatter, frontMatterLocation, 'c3a2' )
        Globals.checkXMLNoTail( frontMatter, frontMatterLocation, 'm7s9' )
        # Process the attributes first
        for attrib,value in frontMatter.items():
            if attrib=="type":
                pass # We've already processed this
            else: logging.warning( "98h4 Unprocessed {} attribute ({}) in {}".format( attrib, value, frontMatterLocation ) )

        for element in frontMatter:
            if element.tag == OSISXMLBible.OSISNameSpace+"titlePage":
                location = "titlePage of " + frontMatterLocation
                Globals.checkXMLNoText( element, location, 'k9l3' )
                Globals.checkXMLNoTail( element, location, 'a3s4' )
                Globals.checkXMLNoAttributes( element, location, '1w34' )
                # Process the attributes first
                for attrib,value in element.items():
                    if attrib=="type":
                        if Globals.debugFlag: assert( value == 'front' ) # We've already processed this in the calling routine
                    else: logging.warning( "3f5d Unprocessed {} attribute ({}) in {}".format( attrib, value, location ) )

                # Now process the subelements
                for subelement in element.getchildren():
                    Globals.checkXMLNoSubelements( subelement, location )
                    if subelement.tag == OSISXMLBible.OSISNameSpace+"p":
                        sublocation = "p of " + location
                        Globals.checkXMLNoTail( subelement, sublocation, 'h3x5' )
                        Globals.checkXMLNoAttributes( subelement, sublocation, '5ygg' )
                        Globals.checkXMLNoSubelements( subelement, sublocation, '8j54' )
                        p = element.text
                    else: logging.warning( "1dc5 Unprocessed '{}' sub-element ({}) in {}".format( subelement.tag, subelement.text, location ) )
            elif element.tag == OSISXMLBible.OSISNameSpace+"div":
                location = "div of " + frontMatterLocation
                Globals.checkXMLNoText( element, location, 'b3f4' )
                Globals.checkXMLNoTail( element, location, 'd3s2' )
                # Process the attributes first
                divType = None
                for attrib,value in element.items():
                    if attrib=="type":
                        divType = value
                    else: logging.warning( "7h4g Unprocessed {} attribute ({}) in {}".format( attrib, value, location ) )
                if Globals.debugFlag: assert( divType == 'x-license' )

                # Now process the subelements
                for subelement in element.getchildren():
                    if subelement.tag == OSISXMLBible.OSISNameSpace+"title":
                        sublocation = "title of " + location
                        Globals.checkXMLNoTail( subelement, sublocation, 'k8j8' )
                        Globals.checkXMLNoAttributes( subelement, sublocation, '48j6' )
                        Globals.checkXMLNoSubelements( subelement, sublocation, 'l0l0' )
                        date = subelement.text
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+"p":
                        sublocation = "p of " + location
                        Globals.checkXMLNoTail( subelement, sublocation, 'd4d4' )
                        Globals.checkXMLNoAttributes( subelement, sublocation, '2de5' )
                        p = element.text
                        # Now process the subelements
                        for sub2element in subelement.getchildren():
                            Globals.checkXMLNoSubelements( sub2element, sublocation, 's3s3' )
                            if sub2element.tag == OSISXMLBible.OSISNameSpace+"a":
                                sub2location = "a of " + sublocation
                                Globals.checkXMLNoSubelements( sub2element, sub2location, 'j4h3' )
                                aText, aTail = element.text, element.tail
                                # Process the attributes
                                href = None
                                for attrib,value in sub2element.items():
                                    if attrib=="href":
                                        href = value
                                    else: logging.warning( "7g4a Unprocessed {} attribute ({}) in {}".format( attrib, value, sub2location ) )
                            else: logging.warning( "3d45 Unprocessed '{}' sub2-element ({}) in {}".format( sub2element.tag, sub2element.text, sublocation ) )
                    else: logging.warning( "034f Unprocessed '{}' sub-element ({}) in {}".format( subelement.tag, subelement.text, location ) )
            else: logging.warning( "2sd4 Unprocessed '{}' sub-element ({}) in {}".format( element.tag, element.text, frontMatterLocation ) )
            if element.tail is not None and element.tail.strip(): logging.error( "Unexpected '{}' tail data after {} element in header element".format( element.tail, element.tag ) )
    # end of OSISXMLBible.validateFrontMatter


    def validateAndExtractMainDiv( self, div ):
        """
        Check/validate and extract data from the given OSIS div record.
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
            Globals.checkXMLNoText( element, location+" at "+verseMilestone, 's2a8' )
            Globals.checkXMLNoTail( element, location+" at "+verseMilestone, 'j9k7' )
            OSISChapterID = sID = eID = chapterN = canonical = None
            for attrib,value in element.items():
                if attrib=="osisID": OSISChapterID = value
                elif attrib=="sID": sID = value
                elif attrib=="eID": eID = value
                elif attrib=="n": chapterN = value
                elif attrib=="canonical": canonical = value
                else:
                    displayTag = element.tag[len(self.OSISNameSpace):] if element.tag.startswith(self.OSISNameSpace) else element.tag
                    logging.warning( _("5f3d Unprocessed '{}' attribute ({}) in {} subelement of {}").format( attrib, value, displayTag, location ) )
            if sID and not OSISChapterID: logging.error( _("Missing chapter ID attribute in {}: {}").format( location, element.items() ) )

            if len(element)==0 and ( sID or eID or OSISChapterID): # it's a chapter milestone (no sub-elements)
                # No verse milestone should be open because verses can't cross chapter boundaries
                if verseMilestone:
                    if haveEIDs: logging.error( _("Unexpected {} chapter milestone while {} verse milestone is still open at {}").format( element.items(), verseMilestone, location ) )

                if OSISChapterID and sID and not eID and OSISChapterID==sID:
                    chapterMilestone = sID
                    if not chapterMilestone.count('.')==1: logging.error( "{} chapter milestone seems wrong format for {} at {}".format( chapterMilestone, OSISChapterID, location ) )
                elif eID and not OSISChapterID and not sID:
                    if chapterMilestone and eID==chapterMilestone: chapterMilestone = ''
                    else:
                        logging.error( _("Chapter milestone {} end didn't match {} at {}").format( eID, chapterMilestone, location ) )
                elif OSISChapterID and not (sID or eID): # some OSIS formats use this
                    if Globals.debugFlag: assert( canonical == "true" )
                    chapterMilestone = OSISChapterID
                else:
                    logging.error( _("Unrecognized chapter milestone in {}: {} at {}").format( location, element.items(), location ) )

                if chapterMilestone: # Have a chapter milestone like Jas.1
                    bits = chapterMilestone.split( '.' )
                    if Globals.debugFlag: assert( len(bits) == 2 )
                    cmBBB = None
                    try:
                        cmBBB = Globals.BibleBooksCodes.getBBBFromOSIS( bits[0] )
                    except:
                        logging.critical( _("'{}' is not a valid OSIS book identifier").format( bits[0] ) )
                    if cmBBB and cmBBB != BBB: # We've started on a new book
                        #if BBB and ( len(bookResults)>20 or len(USFMResults)>20 ): # Save the previous book
                        if BBB and len(self.thisBook._rawLines) > 5: # Save the previous book
                            #print( verseMilestone )
                            if Globals.verbosityLevel > 2: print( "Saving previous {} book into results...".format( BBB ) )
                            #print( mainDivOsisID, "results", BBB, bookResults[:10], "..." )
                            # Remove the last titles
                            #lastBookResult = bookResults.pop()
                            #if lastBookResult[0]!='sectionTitle':
                                #bookResults.append( lastBookResult ) # No good -- put it back
                                #lastBookResult = None
                            #lastUSFMResult = USFMResults.pop()
                            #if lastUSFMResult[0]!='s':
                                #USFMResults.append( lastUSFMResult ) # No good -- put it back
                                #lastUSFMResult = None
                            lastLineTuple = self.thisBook._rawLines.pop()
                            if Globals.debugFlag: assert( len(lastLineTuple) == 2 )
                            if lastLineTuple[0] != 's':
                                self.thisBook._rawLines.append( lastLineTuple ) # No good -- put it back
                                lastLineTuple = None
                            #if bookResults: self.bkData[BBB] = bookResults
                            #if USFMResults: self.USFMBooks[BBB] = USFMResults
                            self.saveBook( self.thisBook )
                            #bookResults, USFMResults = [], []
                            #if lastBookResult:
                                #bookResults.append( ('header',cmBBB,) )
                                #lastBookResultList = list( lastBookResult )
                                #lastBookResultList[0] = 'mainTitle'
                                #adjBookResult = tuple( lastBookResultList )
                                ##print( lastBookResultList )
                                #bookResults.append( adjBookResult )
                            #if lastUSFMResult:
                                #USFMResults.append( ('id',(USFMAbbreviation if USFMAbbreviation else mainDivOsisID).upper() + " converted to USFM from OSIS by {} V{}".format( ProgName, ProgVersion ),) )
                                #USFMResults.append( ('h',USFMAbbreviation if USFMAbbreviation else mainDivOsisID,) )
                                #lastUSFMResultList = list( lastUSFMResult )
                                #lastUSFMResultList[0] = 'mt1'
                                ##print( lastUSFMResultList )
                                #adjSFMResult = tuple( lastUSFMResultList )
                                #USFMResults.append( adjSFMResult )
                            if lastLineTuple:
                                self.thisBook.appendLine( 'id', (USFMAbbreviation if USFMAbbreviation else mainDivOsisID).upper() + " converted to USFM from OSIS by {} V{}".format( ProgName, ProgVersion ) )
                                self.thisBook.appendLine( 'h', USFMAbbreviation if USFMAbbreviation else mainDivOsisID )
                                self.thisBook.appendLine( 'mt1', lastLineTuple[1] ) # Change from s to mt1
                            chapterMilestone = verseMilestone = ''
                            foundH = False
                        BBB = cmBBB[0] if isinstance( cmBBB, list) else cmBBB # It can be a list like: ['EZR', 'EZN']
                        #print( "23f4 BBB is", BBB )
                        USFMAbbreviation = Globals.BibleBooksCodes.getUSFMAbbreviation( BBB )
                        USFMNumber = Globals.BibleBooksCodes.getUSFMNumber( BBB )
                        if Globals.verbosityLevel > 2: print( _("  It seems we have {}...").format( BBB ) )
                        self.thisBook = BibleBook( BBB )
                        self.thisBook.objectNameString = "OSIS XML Bible Book object"
                        self.thisBook.objectTypeString = "OSIS"
                    #bookResults.append( ('chapter', chapterMilestone,) )
                    #USFMResults.append( ('c',bits[1],) )
                    self.thisBook.appendLine( 'c', bits[1] )

                #print( "validateChapterElement returning milestone:", chapterMilestone )
                return chapterMilestone

            else: # not a milestone -- it's a chapter container
                bits = OSISChapterID.split('.')
                if Globals.debugFlag: assert( len(bits)==2 and bits[1].isdigit() )
                #print( "validateChapterElement returning data:", 'chapterContainer.' + OSISChapterID )
                return 'chapterContainer.' + OSISChapterID
        # end of OSISXMLBible.validateChapterElement


        def validateVerseElement( element, verseMilestone, chapterMilestone, locationDescription ):
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
                'verseContents#' + verse number string + '#' + verse contents for a verse contained within the <verse>...</verse> markers
            """
            nonlocal haveEIDs
            #print( "OSISXMLBible.validateVerseElement at {} with '{}' and '{}'".format( locationDescription, chapterMilestone, verseMilestone ) )
            location = "validateVerseElement: " + locationDescription
            verseText = element.text
            #print( "vT", verseText )
            #Globals.checkXMLNoText( element, location+" at "+verseMilestone, 'x2f5' )
            OSISVerseID = sID = eID = n = None
            for attrib,value in element.items():
                if attrib=="osisID": OSISVerseID = value
                elif attrib=="sID": sID = value
                elif attrib=="eID": eID = value
                elif attrib=="n": n = value
                else:
                    displayTag = element.tag[len(self.OSISNameSpace):] if element.tag.startswith(self.OSISNameSpace) else element.tag
                    logging.warning( "8jh6 Unprocessed '{}' attribute ({}) in {} subelement of {}".format( attrib, value, displayTag, location ) )
            if Globals.debugFlag: print( " validateVerseElement attributes: OSISVerseID = '{}' sID = '{}' eID = '{}' n = '{}'".format( OSISVerseID, sID, eID, n ) )
            if sID and eID:
                logging.critical( _("Invalid combined sID and eID verse attributes in {}: {}").format( location, element.items() ) )
            if sID and not OSISVerseID:
                logging.error( _("Missing verse attributes in {}: {}").format( location, element.items() ) )

            # See if this is a milestone or a verse container
            if len(element)==0 and ( sID or eID ): # it's a milestone (no sub-elements)
                if Globals.debugFlag: assert( not verseText )
                if sID and OSISVerseID and not eID: # we have a start milestone
                    if verseMilestone: # but we already have an open milestone
                        if haveEIDs: logging.error( "Got a {} verse milestone while {} is still open at {}".format( sID, verseMilestone, location ) )
                    verseMilestone = sID
                    #for char in (' ','-',):
                    #    if char in verseMilestone: # it contains a range like 'Mark.6.17 Mark.6.18' or 'Mark.6.17-Mark.6.18'
                    #        chunks = verseMilestone.split( char )
                    #        if Globals.debugFlag: assert( len(chunks) == 2 )
                    #        verseMilestone = chunks[0] # Take the start of the range
                    #if not verseMilestone.count('.')==2: logging.error( "validateVerseElement: {} verse milestone seems wrong format for {}".format( verseMilestone, OSISVerseID ) )
                    if chapterMilestone.startswith( 'chapterContainer.' ): # The chapter is a container but the verse is a milestone!
                        if not verseMilestone.startswith( chapterMilestone[17:] ): logging.error( "'{}' verse milestone seems wrong in '{}' chapter milestone at {}".format( verseMilestone, chapterMilestone, location ) )
                    elif not verseMilestone.startswith( chapterMilestone ): logging.error( "'{}' verse milestone seems wrong in '{}' chapter milestone at {}".format( verseMilestone, chapterMilestone, location ) )
                elif eID and not OSISVerseID and not sID: # we have an end milestone
                    haveEIDs = True
                    if verseMilestone:
                        if eID==verseMilestone: pass # Good -- the end milestone matched the open start milestone
                        else:
                            logging.error( "'{}' verse milestone end didn't match last end milestone '{}' at {}".format( verseMilestone, eID, location ) )
                    logging.critical( "Have '{}' end milestone but no start milestone encountered at {}".format( eID, location ) )
                    return '' # end milestone closes any open milestone
                else:
                    logging.critical( "Unrecognized verse milestone in {}: {}".format( location, element.items() ) )
                    print( " ", verseMilestone ); halt
                    return '' # don't have any other way to handle this

                if verseMilestone: # have an open milestone
                    #print( "'"+verseMilestone+"'" )
                    if Globals.debugFlag: assert( ' ' not in verseMilestone )
                    if '-' in verseMilestone: # Something like Jas.1.7-Jas.1.8
                        chunks = verseMilestone.split( '-' )
                        if len(chunks) != 2: logging.error( "Shouldn't have multiple hyphens in verse milestone '{}'".format( verseMilestone ) )
                        bits1 = chunks[0].split( '.' )
                        if len(bits1) != 3: logging.error( "Expected three components before hyphen in verse milestone '{}'".format( verseMilestone ) )
                        bits2 = chunks[1].split( '.' )
                        if len(bits2) != 3:
                            logging.error( "Expected three components after hyphen in verse milestone '{}'".format( verseMilestone ) )
                            bits2 = [bits1[0],bits1[1],'999'] # Try to do something intelligent
                        #bookResults.append( ('verse', verseMilestone,) )
                        #USFMResults.append( ('v',bits1[2]+'-'+bits2[2],) )
                        self.thisBook.appendLine( 'v', bits1[2]+'-'+bits2[2] )
                    else: # no hyphen
                        bits = verseMilestone.split( '.' )
                        if Globals.debugFlag: assert( len(bits) == 3 )
                        #bookResults.append( ('verse', verseMilestone,) )
                        #USFMResults.append( ('v',bits[2],) )
                        self.thisBook.appendLine( 'v', bits[2] )
                    vTail = element.tail
                    if vTail: # This is the main text of the verse (follows the verse milestone)
                        #bookResults.append( ('verse=',vTail,) )
                        #USFMResults.append( ('v~',vTail.replace('\n','').strip(),) ) # Newlines and leading spaces are irrelevant to USFM formatting
                        self.thisBook.appendLine( 'v~', vTail.replace('\n','').strip() ) # Newlines and leading spaces are irrelevant to USFM formatting
                    return verseMilestone

            else: # not a milestone -- it's verse container
                Globals.checkXMLNoTail( element, location+" at "+verseMilestone, 's2d4' )
                bits = OSISVerseID.split('.')
                #print( "OSISXMLBible.validateVerseElement verse container bits", bits, 'vT', verseText )
                if Globals.debugFlag: assert( len(bits)==3 and bits[1].isdigit() and bits[2].isdigit() )
                #print( "validateVerseElement: Have a verse container at", verseMilestone )
                if verseText.strip():
                    if self.source == "ftp://unboundftp.biola.edu/pub/albanian_utf8.zip": # Do some special handling
                        #print( "here", "&amp;quot;" in verseText, "&quot;" in verseText )
                        verseText = verseText.lstrip().replace('&quot;','"').replace('&lt;','<').replace('&gt;','>') # Fix some encoding issues
                        if "&" in verseText: print( "Still have ampersand in '{}'".format( verseText ) )
                    return 'verseContents#' + bits[2] + '#' + verseText
                else: # it's a container for subelements
                    return 'verseContainer.' + bits[2]

            halt # Should never reach this point in the code
        # end of OSISXMLBible.validateVerseElement


        def validateCrossReferenceOrFootnote( element, locationDescription, verseMilestone ):
            """
            Check/validate and process a cross-reference or footnote.

            Note that this function DOES NOT PROCESS THE TAIL.
            """
            #print( "validateCrossReferenceOrFootnote at", locationDescription, verseMilestone )
            #print( "element tag='{}' text='{}' tail='{}' attr={} ch={}".format( element.tag, element.text, element.tail, element.items(), element.getchildren() ) )
            location = "validateCrossReferenceOrFootnote: " + locationDescription
            noteType = noteN = noteOsisRef = noteOsisID = placement = None
            for attrib,value in element.items():
                if attrib=="type":
                    noteType = value # cross-reference or empty for a footnote
                elif attrib=="n":
                    noteN = value
                elif attrib=="osisRef":
                    noteOsisRef = value
                elif attrib=="osisID":
                    noteOsisID = value
                elif attrib=="placement":
                    placement = value
                else: logging.warning( "2s4d Unprocessed '{}' attribute ({}) in {} sub-element of {} at {}".format( attrib, value, element.tag, location, verseMilestone ) )
            if Globals.debugFlag: print( "  note attributes: noteType = '{}' noteN = '{}' noteOsisRef = '{}' noteOsisID = '{}' at {}".format( noteType, noteN, noteOsisRef, noteOsisID, verseMilestone ) )
            guessed = False
            if not noteType: # easier to handle later if we decide what it is now
                if not element.items(): # it's just a note with NO ATTRIBUTES at all
                    noteType = 'footnote'
                else: # we have some attributes
                    noteType = 'footnote' if noteN else 'crossReference'
                guessed = True
            #assert( noteType and noteN )
            if noteType == 'crossReference':
                #print( "  noteType =", noteType, "noteN =", noteN )
                if Globals.debugFlag: assert( not placement )
                if not noteN: noteN = '-'
                #bookResults.append( ('crossReference',noteN,) )
                #USFMResults.append( ('x',noteN,) )
                self.thisBook.appendToLastLine( '\\x {}'.format( noteN ) )
            elif noteType == 'footnote':
                #print( "  noteType =", noteType, "noteN =", noteN )
                if Globals.debugFlag: assert( not placement )
                if not noteN: noteN = '~'
                #bookResults.append( ('footnote',noteN,) )
                #USFMResults.append( ('f',noteN,) )
                self.thisBook.appendToLastLine( '\\f {}'.format( noteN ) )
            elif noteType == 'study':
                #print( "  noteType =", noteType, "noteN =", noteN )
                if Globals.debugFlag: assert( not placement )
                if not noteN: noteN = '~'
                #bookResults.append( ('studyNote',noteN,) )
                #USFMResults.append( ('f',noteN,) )
                self.thisBook.appendToLastLine( '\\f {}'.format( noteN ) )
                #print( "study note1", location, "Type =", noteType, "N =", noteN, "Ref =", noteOsisRef, "ID =", noteOsisID, "p =", placement ); halt
            elif noteType == 'variant':
                #print( "  noteType =", noteType, "noteN =", noteN )
                if Globals.debugFlag: assert( not placement )
                # What do we do here ???? XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
                #if not noteN: noteN = '~'
                #bookResults.append( ('variant',noteN,) )
                #USFMResults.append( ('f',noteN,) )
                self.thisBook.appendLine( 'var', noteN )
            elif noteType == 'x-index':
                #print( "  noteType =", noteType, "noteN =", noteN )
                if Globals.debugFlag: assert( placement in ('inline',) )
                if not noteN: noteN = '~'
                #bookResults.append( ('index',noteN,) )
                #USFMResults.append( ('ix',noteN,) )
                self.thisBook.appendLine( 'ix', noteN )
            else: print( "note1", noteType ); halt
            noteText = element.text
            #if not noteText or noteText.isspace(): # Maybe we can infer the anchor reference
            #    if verseMilestone and verseMilestone.count('.')==2: # Something like Gen.1.3
            #        noteText = verseMilestone.split('.',1)[1] # Just get the verse reference like "1.3"
            #    else: noteText = ''
            if noteText and not noteText.isspace(): # In some OSIS files, this is the anchor reference (in others, that's put in the tail of an enclosed reference subelement)
                #print( "  noteType = {}, noteText = '{}'".format( noteType, noteText ) )
                if noteType == 'crossReference': # This could be something like '1:6:' or '1:8: a'
                    #bookResults.append( ('crossReferenceSource',noteText,) )
                    #USFMResults.append( ('xt',noteText) )
                    self.thisBook.appendToLastLine( '\\xt {}'.format( noteText ) )
                elif noteType == 'footnote': # This could be something like '4:3 In Greek: some note.' or it could just be random text
                    #print( "  noteType =", noteType, "noteText =", noteText )
                    if Globals.debugFlag: assert( noteText )
                    if ':' in noteText and noteText[0].isdigit(): # Let's roughly assume that it starts with a chapter:verse reference
                        bits = noteText.split( None, 1 )
                        if Globals.debugFlag: assert( len(bits) == 2 )
                        sourceText, footnoteText = bits
                        if Globals.debugFlag: assert( sourceText and footnoteText )
                        #print( "  footnoteSource = '{}', sourceText = '{}'".format( footnoteSource, sourceText ) )
                        #bookResults.append( ('footnoteSource',sourceText,) )
                        if not sourceText[-1] == ' ': sourceText += ' '
                        #USFMResults.append( ('fr',sourceText) )
                        #bookResults.append( ('footnoteText',footnoteText,) )
                        #USFMResults.append( ('ft',footnoteText,) )
                        self.thisBook.appendToLastLine( '\\fr {}'.format( sourceText ) )
                        self.thisBook.appendToLastLine( '\\ft {}'.format( footnoteText )  )
                    else: # Let's assume it's a simple note
                        #bookResults.append( ('footnoteText',noteText,) )
                        #USFMResults.append( ('ft',noteText,) )
                        self.thisBook.appendToLastLine( '\\ft {}'.format( noteText ) )
                elif noteType == 'study':
                    #print( "Need to handle study note properly here" ) # ................. xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
                    #bookResults.append( ('studyNote+',noteText,) )
                    #USFMResults.append( ('sn+',noteText,) )
                    self.thisBook.appendToLastLine( '\\sn~ {}'.format( noteText ) )
                    #print( "study note2", location, "Type =", noteType, "N =", noteN, "Ref =", noteOsisRef, "ID =", noteOsisID, "p =", placement ); halt
                elif noteType == 'x-index':
                    #print( "Need to handle index note properly here" ) # ................. xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
                    #bookResults.append( ('index+',noteText,) )
                    #USFMResults.append( ('ix+',noteText,) )
                    self.thisBook.appendLine( 'ix~', noteText )
                else: print( "note2", noteType ); halt
            for subelement in element.getchildren():
                if subelement.tag == OSISXMLBible.OSISNameSpace+"reference": # cross-references
                    sublocation = "validateCrossReferenceOrFootnote: reference of " + locationDescription
                    #print( "  Have", sublocation, "7h3f" )
                    referenceText = subelement.text
                    referenceTail = (subelement.tail if subelement.tail is not None else '').strip()
                    referenceOsisRef = referenceType = None
                    for attrib,value in subelement.items():
                        if attrib=="osisRef":
                            referenceOsisRef = value
                        elif attrib=="type":
                            referenceType = value
                        else:
                            logging.warning( "1sc5 Unprocessed '{}' attribute ({}) in {} sub-element of {} at {}".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                    #print( "  reference attributes: noteType = {}, referenceText = '{}', referenceOsisRef = '{}', referenceType = '{}', referenceTail = '{}'". \
                    #                        format( noteType, referenceText, referenceOsisRef, referenceType, referenceTail ) )
                    if not referenceType and referenceText: # Maybe we can infer the anchor reference
                        if verseMilestone and verseMilestone.count('.')==2: # Something like Gen.1.3
                            #print( 'vm', verseMilestone )
                            #print( 'ror', referenceOsisRef )
                            anchor = verseMilestone.split('.',1)[1] # Just get the verse reference like "1.3"
                            #referenceType = 'source' # so it works below for cross-references
                            #print( 'rt', referenceText )
                            if noteType=='crossReference':
                                #assert( not noteText and not referenceTail )
                                if noteText and not noteText.isspace():
                                    logging.error( "What do we do here with the note at {}".format( verseMilestone ) )
                                #bookResults.append( ('crossReferenceSource',anchor,) )
                                #USFMResults.append( ('xo',anchor) )
                                self.thisBook.appendToLastLine( '\\xo {}'.format( anchor ) )
                            elif noteType=='footnote':
                                #bookResults.append( ('footnoteSource',anchor,) )
                                #USFMResults.append( ('v~',anchor) ) # There's no USFM for this
                                self.thisBook.appendLine( 'v~', anchor ) # There's no USFM for this
                            else:
                                print( sublocation, verseMilestone, noteType, referenceType, referenceText )
                                halt
                    if noteType=='crossReference' and referenceType=='source':
                        #assert( not noteText and not referenceTail )
                        if Globals.debugFlag: assert( not noteText or noteText.isspace() )
                        #bookResults.append( ('crossReferenceSource',referenceText,) )
                        #USFMResults.append( ('xt',referenceText) )
                        self.thisBook.appendToLastLine( '\\xt {}'.format( referenceText ) )
                    elif noteType=='crossReference' and not referenceType and referenceOsisRef is not None:
                        #bookResults.append( ('crossReference',referenceText,referenceTail,) )
                        if 0 and USFMResults and USFMResults[-1][0]=='xt': # Combine multiple cross-references into one xt field
                            #USFMResults.append( ('xt',USFMResults.pop()[1]+referenceText+referenceTail,) )
                            self.thisBook.appendToLastLine( '\\xt {}'.format( USFMResults.pop()[1]+referenceText+referenceTail ) )
                        else:
                            #USFMResults.append( ('xt',referenceText+referenceTail,) )
                            self.thisBook.appendToLastLine( '\\xt {}'.format( referenceText+referenceTail ) )
                    elif noteType=='footnote' and referenceType=='source':
                        if Globals.debugFlag: assert( referenceText and not noteText )
                        #bookResults.append( ('footnoteSource',referenceText,) )
                        if not referenceText[-1] == ' ': referenceText += ' '
                        #USFMResults.append( ('fr',referenceText,) )
                        self.thisBook.appendToLastLine( '\\fr {}'.format( referenceText ) )
                        if Globals.debugFlag: assert( referenceTail )
                        #bookResults.append( ('footnoteText',referenceTail,) )
                        #USFMResults.append( ('ft',referenceTail,) )
                        self.thisBook.appendToLastLine( '\\ft {}'.format( referenceTail ) )
                    elif noteType=='study' and referenceType=='source': # This bit needs fixing up properly ................................xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
                        #print( "rT='{}' nT='{}' rTail='{}'".format( referenceText, noteText, referenceTail ) )
                        if Globals.debugFlag: assert( referenceText and not noteText.strip() )
                        bookResults.append( ('studySource',referenceText,) )
                        if not referenceText[-1] == ' ': referenceText += ' '
                        USFMResults.append( ('sr',referenceText,) )
                        if referenceTail:
                            #bookResults.append( ('studyText',referenceTail,) )
                            #USFMResults.append( ('st',referenceTail,) )
                            self.thisBook.appendLine( 'st', referenceTail )
                        #else: logging.warning( "How come there's no tail? rT='{}' nT='{}' rTail='{}'".format( referenceText, noteText, referenceTail ) )
                        #print( "study note3", location, "Type =", noteType, "N =", noteN, "Ref =", noteOsisRef, "ID =", noteOsisID, "p =", placement ); halt
                    else:
                        logging.critical( "Don't know how to handle notetype='{}' and referenceType='{}' yet".format( noteType, referenceType ) )
                    for sub2element in subelement.getchildren(): # Can have nested references in some (horrible) OSIS files)
                        if sub2element.tag == OSISXMLBible.OSISNameSpace+"reference": # cross-references
                            sub2location = "validateCrossReferenceOrFootnote: reference of reference of " + locationDescription
                            #print( "  Have", sub2location, "w3r5" )
                            Globals.checkXMLNoTail( sub2element, sub2location+" at "+verseMilestone, 'x3b7' )
                            Globals.checkXMLNoAttributes( sub2element, sub2location+" at "+verseMilestone, '67t4' )
                            Globals.checkXMLNoSubelements( sub2element, sub2location+" at "+verseMilestone, '6hnm' )
                            subreferenceText = sub2element.text
                            if Globals.debugFlag: assert( noteType == 'crossReference' )
                            #bookResults.append( ('crossReferenceSource+',subreferenceText,) )
                            #USFMResults.append( ('xo+',subreferenceText,) )
                            self.thisBook.appendToLastLine( '\\xo {}'.format( subreferenceText ) )
                        else: logging.warning( "7h45 Unprocessed '{}' sub2element ({}) in {} at {}".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                elif subelement.tag == OSISXMLBible.OSISNameSpace+"q":
                    sublocation = "validateCrossReferenceOrFootnote: q of " + locationDescription
                    Globals.checkXMLNoAttributes( subelement, sublocation+" at "+verseMilestone, '3d4r' )
                    Globals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, 'n56d' )
                    if Globals.debugFlag: assert( noteType == 'footnote' )
                    qText, qTail = subelement.text, subelement.tail
                    if Globals.debugFlag: assert( qText )
                    #bookResults.append( ('footnoteQ',qText,) )
                    #USFMResults.append( ('fq',qText,) )
                    self.thisBook.appendToLastLine( '\\fq {}'.format( qText ) )
                    if qTail:
                        #bookResults.append( ('note+',qTail,) )
                        #USFMResults.append( ('ft',qTail,) )
                        self.thisBook.appendToLastLine( '\\ft {}'.format( qTail ) )
                elif subelement.tag == OSISXMLBible.OSISNameSpace+"catchWord":
                    sublocation = "validateCrossReferenceOrFootnote: catchWord of " + locationDescription
                    Globals.checkXMLNoTail( subelement, sublocation+" at "+verseMilestone, 'c48n' )
                    Globals.checkXMLNoAttributes( subelement, sublocation+" at "+verseMilestone, '2w43' )
                    catchWordText = subelement.text
                    if noteType == 'footnote':
                        #bookResults.append( ('footnoteCatchWord',catchWordText,) )
                        #USFMResults.append( ('fq',catchWordText,) )
                        self.thisBook.appendToLastLine( '\\fq {}'.format( catchWordText ) )
                        for sub2element in subelement.getchildren(): # Can have nested catchWords in some (horrible) OSIS files)
                            if sub2element.tag == OSISXMLBible.OSISNameSpace+"catchWord": #
                                sub2location = "validateCrossReferenceOrFootnote: catchWord of catchWord of " + locationDescription
                                #print( "  Have", sub2location, "j2f6" )
                                Globals.checkXMLNoTail( sub2element, sub2location+" at "+verseMilestone, 'c456n' )
                                Globals.checkXMLNoAttributes( sub2element, sub2location+" at "+verseMilestone, '2d4r' )
                                Globals.checkXMLNoSubelements( sub2element, sub2location+" at "+verseMilestone, '23c6' )
                                subCatchWordText = sub2element.text
                                if Globals.debugFlag: assert( noteType == 'footnote' )
                                #bookResults.append( ('footnoteCatchWord2',subCatchWordText,) )
                                #USFMResults.append( ('fq',subCatchWordText,) )
                                self.thisBook.appendToLastLine( '\\fq {}'.format( subCatchWordText ) )
                            else:
                                logging.warning( "8j6g Unprocessed '{}' sub2element ({}) in {} at {}".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                    elif noteType == 'variant':
                        pass # What should we be doing here ??? XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
                    else: print( noteType ); halt
                elif subelement.tag == OSISXMLBible.OSISNameSpace+"hi":
                    sublocation = "validateCrossReferenceOrFootnote: hi of " + locationDescription
                    Globals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, '7j8k' )
                    highlightedText = subelement.text
                    if Globals.debugFlag: assert( highlightedText )
                    highlightType = None
                    for attrib,value in subelement.items():
                        if attrib=="type":
                            highlightType = value
                            if Globals.debugFlag: assert( highlightType == 'italic' )
                        else:
                            logging.warning( "3d5f Unprocessed '{}' attribute ({}) in {} sub2-element of {} at {}".format( attrib, value, subelement.tag, location, verseMilestone ) )
                    #bookResults.append( (highlightType,highlightedText,) )
                    #USFMResults.append( ('it',highlightedText,) )
                    self.thisBook.appendLine( 'it', highlightedText )
                    pTail = subelement.tail
                    if pTail:
                        #bookResults.append( ('note+',pTail,) )
                        #USFMResults.append( ('note+',pTail,) )
                        self.thisBook.appendLine( 'note~', pTail )
                    justFinishedLG = False
                elif subelement.tag == OSISXMLBible.OSISNameSpace+"rdg":
                    sublocation = "validateCrossReferenceOrFootnote: rdg of " + locationDescription
                    Globals.checkXMLNoText( subelement, sublocation+" at "+verseMilestone, '2s5h' )
                    Globals.checkXMLNoTail( subelement, sublocation+" at "+verseMilestone, 'c54b' )
                    # Process the attributes first
                    readingType = None
                    for attrib,value in subelement.items():
                        if attrib=="type":
                            readingType = value
                            #print( readingType )
                            if Globals.debugFlag: assert( readingType == 'x-qere' )
                        else: logging.warning( "2s3d Unprocessed '{}' attribute ({}) in {} sub2-element of {} at {}".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                    for sub2element in subelement.getchildren():
                        if sub2element.tag == OSISXMLBible.OSISNameSpace+"w": # cross-references
                            sub2location = "validateCrossReferenceOrFootnote: w of rdg of " + locationDescription
                            #print( "  Have", sub2location, "6n83" )
                            rdgW = sub2element.text
                            Globals.checkXMLNoTail( sub2element, sub2location+" at "+verseMilestone, '5b3f' )
                            Globals.checkXMLNoSubelements( sub2element, sub2location+" at "+verseMilestone, 's2vb' )
                            # Process the attributes
                            lemma = None
                            for attrib,value in sub2element.items():
                                if attrib=="lemma":
                                    lemma = value
                                    #print( lemma )
                                else: logging.warning( "6b8m Unprocessed '{}' attribute ({}) in {} sub2-element of {} at {}".format( attrib, value, sub2element.tag, sub2location, verseMilestone ) )
                            #bookResults.append( ('rdgW',rdgW,) )
                            #USFMResults.append( ('rdgW',rdgW,) )
                            self.thisBook.appendLine( 'rdgW', rdgW )
                        elif sub2element.tag == OSISXMLBible.OSISNameSpace+"seg": # cross-references
                            sub2location = "validateCrossReferenceOrFootnote: seg of rdg of " + locationDescription
                            #print( "  Have", sub2location, "6n83" )
                            rdgSeg = sub2element.text
                            Globals.checkXMLNoTail( sub2element, sub2location+" at "+verseMilestone, 'fyg5' )
                            Globals.checkXMLNoSubelements( sub2element, sub2location+" at "+verseMilestone, 's2db' )
                            # Process the attributes
                            theType = None
                            for attrib,value in sub2element.items():
                                if attrib=="type":
                                    theType = value
                                    #print( theType )
                                else: logging.warning( "k6g3 Unprocessed '{}' attribute ({}) in {} sub2-element of {} at {}".format( attrib, value, sub2element.tag, sub2location, verseMilestone ) )
                            #bookResults.append( ('rdgSeg',rdgSeg,) )
                            #USFMResults.append( ('rdgSeg',rdgSeg,) )
                            self.thisBook.appendLine( 'rdgSeg', rdgSeg )
                        else:
                            logging.warning( "3dxm Unprocessed '{}' sub2element ({}) in {} at {}".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                    justFinishedLG = False
                elif subelement.tag == OSISXMLBible.OSISNameSpace+"divineName":
                    sublocation = "validateCrossReferenceOrFootnote: divineName of " + locationDescription
                    Globals.checkXMLNoAttributes( subelement, sublocation+" at "+verseMilestone, '3r6y' )
                    Globals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, 's2r54' )
                    divineName, trailingText = subelement.text, subelement.tail
                    #bookResults.append( ('nd',divineName,) )
                    #USFMResults.append( ('nd',divineName,) )
                    self.thisBook.appendLine( 'nd',divineName )
                    if trailingText:
                        #bookResults.append( ('nd+',trailingText,) )
                        #USFMResults.append( ('nd+',trailingText,) )
                        self.thisBook.appendLine( 'nd+', trailingText )
                else:
                    logging.warning( "1d54 Unprocessed '{}' sub-element ({}) in {} at {}".format( subelement.tag, subelement.text, location, verseMilestone ) )
            #print( "  Note tail = '{}' (will be used later)".format( element.tail ) )
            #print( "USFMResults =", USFMResults )
        # end of OSISXMLBible.validateCrossReferenceOrFootnote


        def validateLG( element, locationDescription, verseMilestone ):
            """
            Check/validate and process a OSIS Bible lg field, including all subfields.

            Returns a possibly updated verseMilestone.
            """
            #print( "validateLG at {} at {}".format( location, verseMilestone ) )
            location = "validateLG: " + locationDescription
            Globals.checkXMLNoText( element, location+" at "+verseMilestone, '3f6v' )
            #lgText = element.text
            lgTail = element.tail.strip()
            for attrib,value in element.items():
                if attrib=="type":
                    halt
                elif attrib=="n":
                    halt
                elif attrib=="osisRef":
                    halt
                elif attrib=="osisID":
                    halt
                else: logging.warning( "9f3k Unprocessed '{}' attribute ({}) in {} element of {} at {}".format( attrib, value, element.tag, location, verseMilestone ) )
            for subelement in element.getchildren():
                if subelement.tag == OSISXMLBible.OSISNameSpace+"l":
                    sublocation = "validateLG l of " + locationDescription
                    Globals.checkXMLNoTail( subelement, sublocation+" at "+verseMilestone, '3d56g' )
                    lText = subelement.text.strip()
                    level3 = None
                    for attrib,value in subelement.items():
                        if attrib=="level":
                            level3 = value
                        else:
                            logging.warning( "2xc4 Unprocessed '{}' attribute ({}) in {} sub-element of {} at {}".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                    if not level3:
                        #print( "level3 problem", verseMilestone, lText, subelement.items() )
                        logging.warning( "No level attribute specified in {} at {}".format( sublocation, verseMilestone ) )
                        level3 = '1' # Dunno what we have here ???
                    if Globals.debugFlag: assert( level3 in ('1','2','3',) )
                    #bookResults.append( ('lg', level3, lText,) )
                    #USFMResults.append( ('q'+level3,lText,) )
                    self.thisBook.appendLine( 'q'+level3, '' if lText is None else lText )
                    for sub2element in subelement.getchildren():
                        if sub2element.tag == OSISXMLBible.OSISNameSpace+"verse":
                            sub2location = "validateLG: verse of l of  " + locationDescription
                            verseMilestone = validateVerseElement( sub2element, verseMilestone, chapterMilestone, sub2location )
                        elif sub2element.tag == OSISXMLBible.OSISNameSpace+"note":
                            sub2location = "validateLG: note of l of  " + locationDescription
                            validateCrossReferenceOrFootnote( sub2element, sub2location, verseMilestone )
                            noteTail = sub2element.tail
                            if noteTail: # This is the main text of the verse (follows the inserted note)
                                #bookResults.append( ('lverse+', noteTail,) )
                                adjNoteTail = noteTail.replace('\n','') # XML line formatting is irrelevant to USFM
                                if adjNoteTail:
                                    #USFMResults.append( ('lv~',adjNoteTail,) )
                                    self.thisBook.appendLine( 'v~', adjNoteTail )
                        elif sub2element.tag == OSISXMLBible.OSISNameSpace+"divineName":
                            sub2location = "validateLG: divineName of l of  " + locationDescription
                            Globals.checkXMLNoAttributes( sub2element, sub2location+" at "+verseMilestone, '3q6y' )
                            Globals.checkXMLNoSubelements( sub2element, sub2location+" at "+verseMilestone, '4v6g' )
                            divineName, trailingText = sub2element.text, sub2element.tail
                            #bookResults.append( ('nd',divineName,) )
                            #USFMResults.append( ('nd',divineName,) )
                            self.thisBook.appendLine( 'nd', divineName )
                            if trailingText:
                                #bookResults.append( ('nd+',trailingText,) )
                                #USFMResults.append( ('nd+',trailingText,) )
                                self.thisBook.appendLine( 'nd~', trailingText )
                        else:
                            logging.warning( "4j12 Unprocessed '{}' sub2element ({}) in {} at {}".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                elif subelement.tag == OSISXMLBible.OSISNameSpace+"divineName":
                    sublocation = "validateLG divineName of " + locationDescription
                    print( "6b3i", sublocation )
                    Globals.checkXMLNoText( subelement, sublocation+" at "+verseMilestone, '2d5g' )
                    Globals.checkXMLNoTail( subelement, sublocation+" at "+verseMilestone, 'v32v' )
                    Globals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, '2sd5' )
                    Globals.checkXMLNoAttributes( subelement, sublocation+" at "+verseMilestone, '6y4t' )
                else:
                    logging.warning( "q2b6 Unprocessed '{}' sub-element ({}) in {} at {}".format( subelement.tag, subelement.text, location, verseMilestone ) )
            if lgTail: # and lgTail!='\n': # This is the main text of the verse (outside of the quotation indents)
                #bookResults.append( ('margin',lgTail,) )
                #USFMResults.append( ('m',lgTail,) )
                self.thisBook.appendLine( 'm', lgTail )
            return verseMilestone
        # end of OSISXMLBible.validateLG


        def validateTitle( element, locationDescription, verseMilestone ):
            """
            Check/validate and process a OSIS Bible paragraph, including all subfields.
            """
            location = "validateTitle: " + locationDescription
            Globals.checkXMLNoTail( element, location+" at "+verseMilestone, 'c4vd' )
            titleText = element.text
            titleType = titleSubType = titleShort = titleLevel = None
            for attrib,value in element.items():
                if attrib=="type":
                    titleType = value
                elif attrib=="subType":
                    titleSubType = value
                elif attrib=="short":
                    titleShort = value
                elif attrib=="level":
                    titleLevel = value # Not used anywhere yet :(
                else: logging.warning( "4b8e Unprocessed '{}' attribute ({}) in {} at {}".format( attrib, value, location, verseMilestone ) )
            if titleSubType: assert( titleSubType == 'x-preverse' )
            if chapterMilestone:
                Globals.checkXMLNoSubelements( element, location+" at "+verseMilestone, '2d45' )
                if titleText:
                    if not titleType and not titleShort and self.language=='ksw': # it's a Karen alternate chapter number
                        #bookResults.append( ("alternateChapterNumber",titleText,) )
                        #USFMResults.append( ('ca',titleText,) )
                        self.thisBook.appendLine( 'cp', titleText )
                    else: # let's guess that it's a section heading
                        #bookResults.append( ('title', titleType, titleText,) )
                        #USFMResults.append( ('ms1', titleText,) )
                        self.thisBook.appendLine( 'ms1', titleText )
            else: # Must be in the introduction if it's before all chapter milestones
                #assert( titleText )
                #bookResults.append( ('title', titleType, titleText,) )
                #USFMResults.append( ('imt', titleText,) ) # Could it also be 'is'?
                if titleText:
                    self.thisBook.appendLine( 'imt', titleText ) # Could it also be 'is'?
            for subelement in element.getchildren():
                if subelement.tag == OSISXMLBible.OSISNameSpace+"title": # section reference(s)
                    sublocation = "validateTitle: title of " + locationDescription
                    Globals.checkXMLNoTail( subelement, sublocation+" at "+verseMilestone, '21d5' )
                    sectionReference = subelement.text
                    sectionReferenceType = None
                    for attrib,value in subelement.items():
                        if attrib=="type":
                            sectionReferenceType = value
                        else:
                            logging.warning( "56v3 Unprocessed '{}' attribute ({}) in {} sub2element of {} at {}".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                    if sectionReference:
                        #print( divType, self.subDivType, sectionReferenceType ); halt
                        #assert( divType=='section' and self.subDivType in ('outline',) and sectionReferenceType=='parallel' )
                        #assert( divType=='section' and sectionReferenceType=='parallel' )
                        #bookResults.append( ('title',sectionReference,) )
                        #USFMResults.append( ('r',sectionReference,) )
                        self.thisBook.appendLine( 'r', sectionReference )
                    for sub2element in subelement.getchildren():
                        if sub2element.tag == OSISXMLBible.OSISNameSpace+"reference":
                            sub2location = "reference of " + sublocation
                            Globals.checkXMLNoSubelements( sub2element, sub2location+" at "+verseMilestone, 'f5g2' )
                            referenceText = sub2element.text
                            referenceTail = sub2element.tail
                            referenceOsisRef = None
                            for attrib,value in sub2element.items():
                                if attrib=="osisRef":
                                    referenceOsisRef = value
                                else: logging.warning( "89n5 Unprocessed '{}' attribute ({}) in {} sub3element of {} at {}".format( attrib, value, sub2element.tag, sublocation, verseMilestone ) )
                            #print( referenceText, referenceOsisRef, referenceTail )
                            #bookResults.append( ('reference',referenceText,) )
                            #USFMResults.append( ('r+',referenceText+referenceTail,) )
                            self.thisBook.appendLine( 'r~', referenceText+referenceTail )
                        else:
                            logging.warning( "2d6h Unprocessed '{}' sub3element ({}) in {} at {}".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
        # end of OSISXMLBible.validateTitle

        def validateParagraph( element, locationDescription, verseMilestone ):
            """
            Check/validate and process a OSIS Bible paragraph, including all subfields.

            Returns a possibly updated verseMilestone.
            """
            nonlocal chapterMilestone
            #print( "validateParagraph at {} at {}".format( locationDescription, verseMilestone ) )
            location = "validateParagraph: " + locationDescription
            paragraphType = None
            for attrib,value in element.items():
                if attrib=="type":
                    paragraphType = value
                else: logging.warning( "6g3f Unprocessed '{}' attribute ({}) in {} element of {} at {}".format( attrib, value, element.tag, location, verseMilestone ) )
            if paragraphType: assert( paragraphType == "x-center" )
            justFinishedLG = False
            if not element.text: # A new paragraph starting
                p = None
            else: # A new paragraph in the middle of a verse, e.g., James 3:5b
                p = element.text.strip()
                #if p.isspace(): p = None # Ignore newlines and blank lines in the xml file
            if chapterMilestone:
                #bookResults.append( ('p',p,) )
                #USFMResults.append( ('p',p.replace('\n','') if p is not None else p,) )
                self.thisBook.appendLine( 'p', '' if p is None else p )
            else: # Must be in the introduction
                #bookResults.append( ('ip',p,) )
                #USFMResults.append( ('ip',p,) )
                self.thisBook.appendLine( 'ip', '' if p is None else p )
            for subelement in element.getchildren():
                if subelement.tag == OSISXMLBible.OSISNameSpace+"chapter": # A chapter break within a paragraph (relatively rare)
                    sublocation = "validateParagraph: chapter of " + locationDescription
                    chapterMilestone = validateChapterElement( subelement, chapterMilestone, verseMilestone, sublocation )
                elif subelement.tag == OSISXMLBible.OSISNameSpace+"verse":
                    sublocation = "validateParagraph: verse of " + locationDescription
                    if justFinishedLG: # Have a verse straight after a LG (without an intervening p)
                        #USFMResults.append( ('m',None,) )
                        self.thisBook.appendLine( 'm', '' )
                        #print( "Added m" )
                    verseMilestone = validateVerseElement( subelement, verseMilestone, chapterMilestone, sublocation )
                    justFinishedLG = False
                elif subelement.tag == OSISXMLBible.OSISNameSpace+"note":
                    sublocation = "validateParagraph: note of " + locationDescription
                    validateCrossReferenceOrFootnote( subelement, sublocation, verseMilestone )
                    noteTail = subelement.tail
                    if noteTail and not noteTail.isspace(): # This is the main text of the verse (follows the inserted note)
                        #print( "et '" + element.tail + "'" )
                        #bookResults.append( ('lverse+', noteTail,) )
                        #adjNoteTail = noteTail.replace('\n','') # XML line formatting is irrelevant to USFM
                        adjNoteTail = noteTail.strip() # XML line formatting is irrelevant to USFM
                        if adjNoteTail:
                            #USFMResults.append( ('lv~',adjNoteTail,) )
                            self.thisBook.appendLine( 'v~', adjNoteTail )
                    justFinishedLG = False
                elif subelement.tag == OSISXMLBible.OSISNameSpace+"lg":
                    sublocation = "validateParagraph: lg of " + locationDescription
                    verseMilestone = validateLG( subelement, sublocation, verseMilestone )
                    if 0:
                        Globals.checkXMLNoText( subelement, sublocation+" at "+verseMilestone, '3ch6' )
                        #lgText = subelement.text
                        lgTail = subelement.tail
                        for attrib,value in subelement.items():
                            if attrib=="type":
                                halt
                            elif attrib=="n":
                                halt
                            elif attrib=="osisRef":
                                halt
                            elif attrib=="osisID":
                                halt
                            else: logging.warning( "1s5g Unprocessed '{}' attribute ({}) in {} sub-element of {} at {}".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                        for sub2element in subelement.getchildren():
                            if sub2element.tag == OSISXMLBible.OSISNameSpace+"l":
                                sub2location = "l of " + sublocation
                                Globals.checkXMLNoTail( sub2element, sub2location+" at "+verseMilestone, '4vw3' )
                                lText = sub2element.text
                                level3 = None
                                for attrib,value in sub2element.items():
                                    if attrib=="level":
                                        level3 = value
                                    else: logging.warning( "9d3k Unprocessed '{}' attribute ({}) in {} sub-element of {} at {}".format( attrib, value, sub2element.tag, sub2location, verseMilestone ) )
                                if not level3:
                                    #print( "level3 problem", verseMilestone, lText, sub2element.items() )
                                    logging.warning( "validateParagraph: No level attribute specified in {} at {}".format( sub2location, verseMilestone ) )
                                    level3 = '1' # Dunno what we have here ???
                                if Globals.debugFlag: assert( level3 in ('1','2','3',) )
                                #bookResults.append( ('lg', level3, lText,) )
                                #USFMResults.append( ('q'+level3,lText,) )
                                self.thisBook.appendLine( 'q'+level3, lText )
                                for sub3element in sub2element.getchildren():
                                    if sub3element.tag == OSISXMLBible.OSISNameSpace+"verse":
                                        sub3location = "verse of " + sub2location
                                        verseMilestone = validateVerseElement( sub3element, verseMilestone, chapterMilestone, sub3location )
                                    elif sub3element.tag == OSISXMLBible.OSISNameSpace+"note":
                                        sub3location = "note of " + sub2location
                                        validateCrossReferenceOrFootnote( sub3element, sub3location, verseMilestone )
                                        noteTail = sub3element.tail
                                        if noteTail: # This is the main text of the verse (follows the inserted note)
                                            bookResults.append( ('lverse+', noteTail,) )
                                            adjNoteTail = noteTail.replace('\n','') # XML line formatting is irrelevant to USFM
                                            if adjNoteTail: USFMResults.append( ('v~',adjNoteTail,) )
                                    else: logging.warning( "32df Unprocessed '{}' sub3element ({}) in {} at {}".format( sub3element.tag, sub3element.text, sub2location, verseMilestone ) )
                            else: logging.warning( "5g1e Unprocessed '{}' sub2element ({}) in {} at {}".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                        if lgTail and lgTail!='\n': # This is the main text of the verse (outside of the quotation indents)
                            #bookResults.append( ('margin',lgTail,) )
                            #USFMResults.append( ('m',lgTail,) )
                            self.thisBook.appendLine( 'm', lgTail )
                    justFinishedLG = True
                elif subelement.tag == OSISXMLBible.OSISNameSpace+"reference":
                    sublocation = "validateParagraph: reference of " + locationDescription
                    Globals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, 'vbs4' )
                    reference = subelement.text
                    theType = None
                    for attrib,value in subelement.items():
                        if attrib=="type":
                            theType = value
                        else: logging.warning( "4f5f Unprocessed '{}' attribute ({}) in {} sub2-element of {} at {}".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                    if theType:
                        if theType == 'x-bookName':
                            #bookResults.append( (theType,reference,) )
                            #USFMResults.append( ('bk',reference,) )
                            self.thisBook.appendLine( 'bk', reference )
                        else: halt
                    pTail = subelement.tail
                    if pTail and not pTail.isspace(): # Just ignore XML spacing characters
                        #bookResults.append( ('paragraph+',pTail,) )
                        #USFMResults.append( ('p+',pTail,) )
                        self.thisBook.appendLine( 'p', pTail ) # 'p~'
                    justFinishedLG = False
                elif subelement.tag == OSISXMLBible.OSISNameSpace+"hi":
                    sublocation = "validateParagraph: hi of " + locationDescription
                    Globals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, 'gb5gb' )
                    highlightedText = subelement.text
                    if Globals.debugFlag: assert( highlightedText )
                    highlightType = None
                    for attrib,value in subelement.items():
                        if attrib=="type":
                            highlightType = value
                            if Globals.debugFlag: assert( highlightType == 'italic' )
                        else: logging.warning( "7kj3 Unprocessed '{}' attribute ({}) in {} sub2-element of {} at {}".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                    #bookResults.append( (highlightType,highlightedText,) )
                    #USFMResults.append( ('it',highlightedText,) )
                    self.thisBook.appendLine( 'it', highlightedText )
                    pTail = subelement.tail
                    if pTail and not pTail.isspace(): # Just ignore XML spacing characters
                        #bookResults.append( ('paragraph+',pTail,) )
                        #USFMResults.append( ('p+',pTail,) )
                        self.thisBook.appendLine( 'p', pTail ) # 'p~'
                    justFinishedLG = False
                elif subelement.tag == OSISXMLBible.OSISNameSpace+"lb":
                    sublocation = "validateParagraph: lb of " + locationDescription
                    Globals.checkXMLNoText( subelement, sublocation+" at "+verseMilestone, 'cf4g' )
                    Globals.checkXMLNoTail( subelement, sublocation+" at "+verseMilestone, '3c5f' )
                    Globals.checkXMLNoAttributes( subelement, sublocation+" at "+verseMilestone, '5t3x' )
                    Globals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone )
                    #bookResults.append( ('lb',None,) )
                    #USFMResults.append( ('m',None,) )
                    self.thisBook.appendLine( 'm', '' )
                    justFinishedLG = False
                elif subelement.tag == OSISXMLBible.OSISNameSpace+"w":
                    sublocation = "validateParagraph: w of " + locationDescription
                    Globals.checkXMLNoAttributes( subelement, sublocation+" at "+verseMilestone, '3s5f' )
                    Globals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, 'f3v5' )
                    word, trailingPunctuation = subelement.text, subelement.tail
                    if trailingPunctuation is None: trailingPunctuation = ''
                    combined = word + trailingPunctuation
                    #bookResults.append( ('w',combined,) )
                    #USFMResults.append( ('w+',combined,) )
                    self.thisBook.appendLine( 'w~', combined )
                elif subelement.tag == OSISXMLBible.OSISNameSpace+"signed":
                    sublocation = "validateParagraph: signed of " + locationDescription
                    Globals.checkXMLNoTail( subelement, sublocation+" at "+verseMilestone, 'fc3v3' )
                    Globals.checkXMLNoAttributes( subelement, sublocation+" at "+verseMilestone, '9i6h' )
                    Globals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone )
                    signedName = subelement.text
                    #bookResults.append( ('sig',signedName,) )
                    #USFMResults.append( ('sig',signedName,) )
                    self.thisBook.appendLine( 'sig', signedName )
                elif subelement.tag == OSISXMLBible.OSISNameSpace+"divineName":
                    sublocation = "validateParagraph: divineName of " + locationDescription
                    Globals.checkXMLNoAttributes( subelement, sublocation+" at "+verseMilestone, '3f7h' )
                    Globals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, 'v4g7' )
                    divineName, trailingText = subelement.text, subelement.tail
                    #bookResults.append( ('nd',divineName,) )
                    #USFMResults.append( ('nd',divineName,) )
                    self.thisBook.appendLine( 'nd', divineName )
                    #bookResults.append( ('nd+',trailingText,) )
                    #USFMResults.append( ('nd+',trailingText,) )
                    self.thisBook.appendLine( 'nd~', trailingText )
                else: logging.warning( "3kj6 Unprocessed '{}' sub-element ({}) in {} at {}".format( subelement.tag, subelement.text, location, verseMilestone ) )
            if element.tail and not element.tail.isspace(): # Just ignore XML spacing characters
                #bookResults.append( ('paragraph+',element.tail,) )
                #USFMResults.append( ('p+',element.tail,) )
                self.thisBook.appendLine( 'p', element.tail ) # 'p~'
            return verseMilestone
        # end of OSISXMLBible.validateParagraph


        if Globals.verbosityLevel > 3: print( _("Validating OSIS main div...") )
        #bookResults, USFMResults = [], []
        haveEIDs = False

        # Process the div attributes first
        mainDivType = mainDivOsisID = mainDivCanonical = None
        BBB = USFMAbbreviation = USFMNumber = ''
        for attrib,value in div.items():
            if attrib=="type":
                mainDivType = value
                if mainDivOsisID and Globals.verbosityLevel > 2: print( _("Validating {} {}...").format( mainDivOsisID, mainDivType ) )
            elif attrib=="osisID":
                mainDivOsisID = value
                if mainDivType and Globals.verbosityLevel > 2: print( _("Validating {} {}...").format( mainDivOsisID, mainDivType ) )
            elif attrib=="canonical":
                mainDivCanonical = value
            else: logging.warning( "93f5 Unprocessed '{}' attribute ({}) in main div element".format( attrib, value ) )
        if not mainDivType or not (mainDivOsisID or mainDivCanonical): logging.warning( "Incomplete mainDivType '{}' and mainDivOsisID '{}' attributes in main div element".format( mainDivType, mainDivOsisID ) )
        if mainDivType=='book':
            # This is a single book
            if len(mainDivOsisID)>3 and mainDivOsisID[-1] in ('1','2','3',) and mainDivOsisID[-2]=='.': # Fix a bug in the Snowfall USFM to OSIS software
                logging.critical( "Fixing bug in OSIS '{}' book ID".format( mainDivOsisID ) )
                mainDivOsisID = mainDivOsisID[:-2] # Change 1Kgs.1 to 1Kgs
            try:
                BBB = Globals.BibleBooksCodes.getBBBFromOSIS( mainDivOsisID )
            except:
                logging.critical( _("'{}' is not a valid OSIS book identifier").format( mainDivOsisID ) )
            if BBB:
                if isinstance( BBB, list ): # There must be multiple alternatives for BBB from the OSIS one
                    if Globals.verbosityLevel > 2: print( "Multiple alternatives for OSIS '{}': {} (Choosing the first one)".format( mainDivOsisID, BBB ) )
                    BBB = BBB[0]
                if Globals.verbosityLevel > 2: print( _("  Validating {}...").format( BBB ) )
                USFMAbbreviation = Globals.BibleBooksCodes.getUSFMAbbreviation( BBB )
                USFMNumber = Globals.BibleBooksCodes.getUSFMNumber( BBB )
                self.thisBook = BibleBook( BBB )
                self.thisBook.objectNameString = "OSIS XML Bible Book object"
                self.thisBook.objectTypeString = "OSIS"
            #bookResults.append( (mainDivType+'Div', mainDivOsisID,) )
            #USFMResults.append( ('id',(USFMAbbreviation if USFMAbbreviation else mainDivOsisID).upper() + " converted to USFM from OSIS by {} V{}".format( ProgName, ProgVersion ),) )
            self.thisBook.appendLine( 'id', (USFMAbbreviation if USFMAbbreviation else mainDivOsisID).upper() + " converted to USFM from OSIS by {} V{}".format( ProgName, ProgVersion ) )
            #USFMResults.append( ('h',USFMAbbreviation if USFMAbbreviation else mainDivOsisID,) )
            self.thisBook.appendLine( 'h', USFMAbbreviation if USFMAbbreviation else mainDivOsisID )
        elif mainDivType=='bookGroup':
            # This is all the books lumped in together into one big div
            if Globals.debugFlag: assert( mainDivCanonical == "true" )
            # We have to set BBB when we get a chapter reference
            if Globals.verbosityLevel > 2: print( _("  Validating a book group...") )

        chapterMilestone = verseMilestone = ''
        foundH = False
        for element in div:
########### Title -- could be a book title or (in some OSIS files) a section title (with no way to tell the difference)
#               or even worse still (in the Karen), an alternate chapter number
            if element.tag == OSISXMLBible.OSISNameSpace+"title":
                location = "title of {} div".format( mainDivType )
                validateTitle( element, location, verseMilestone )
                if 0:
                    titleText = element.text
                    # Process the attributes
                    titleType = titleShort = None
                    for attrib,value in element.items():
                        if attrib=="type":
                            titleType = value
                        elif attrib=="short":
                            titleShort = value
                        else: logging.warning( "8k4d Unprocessed '{}' attribute ({}) in {} at {}".format( attrib, value, location, verseMilestone ) )
                    if titleType=='' or titleType == "main": # Some OSIS files don't have a title type attribute :(
                        if titleShort:
                            if Globals.debugFlag: assert( not foundH )
                            bookResults.append( ("title",titleType,titleShort,) )
                            USFMResults.append( ('h',titleShort,) )
                            foundH = True
                        elif not foundH:
                            USFMResults.append( ('h','UNKNOWN',) )
                            foundH = True
                        if titleText:
                            if Globals.debugFlag: assert( len(element) == 0 ) # The title is encoded here not in subelements
                            if not titleType and not titleShort: # Assume it's a section header
                                bookResults.append( ("sectionTitle",titleText,) )
                                USFMResults.append( ('s',titleText,) )
                            else: # Assume it's a main title
                                bookResults.append( ("title+",titleText,) )
                                USFMResults.append( ('mt1',titleText,) )
                    else: print( "unknown title type =", titleType ); halt
                    # Now process the subelements
                    for subelement in element.getchildren():
                        if subelement.tag == OSISXMLBible.OSISNameSpace+"title": # subtitles
                            sublocation = "subtitle of " + location
                            if Globals.debugFlag: assert( not titleText ) # The text should be specified in the subtitles in this case
                            Globals.checkXMLNoTail( subelement, sublocation+" at "+verseMilestone, '4gg6' )
                            Globals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, '3c45' )
                            title = subelement.text
                            subtitleType = subtitleLevel = None
                            for attrib,value in subelement.items():
                                if attrib=="type":
                                    subtitleType = value
                                elif attrib=="level":
                                    subtitleLevel = value
                                else: logging.warning( "235h Unprocessed '{}' attribute ({}) in {} at {}".format( attrib, value, sublocation, verseMilestone ) )
                            if not title: logging.warning( "Blank title field in {} (type='{}', level='{}')".format( sublocation, subtitleType, subtitleLevel ) )
                            bookResults.append( ("subtitle",subtitleType,subtitleLevel,title,) )
                            if subtitleLevel and title: USFMResults.append( ('mt'+subtitleLevel,title,) )
                            #else: print( "{} '{}' '{}' '{}'".format( sublocation, title, subtitleType, subtitleLevel ) ); halt
                        else: logging.warning( "84g6 Unprocessed '{}' sub-element ({}) in {} at {}".format( subelement.tag, subelement.text, location, verseMilestone ) )
                    titleTail = element.tail
                    if titleTail:
                        bookResults.append( ('TTparagraph+', titleTail,) )
                        adjTitleTail = titleTail.replace('\n','') # XML line formatting is irrelevant to USFM
                        if adjTitleTail: USFMResults.append( ('TTp+',adjTitleTail,) )
########### Div (of the main div) -- most stuff would be expected to be inside a section div inside the book div
            elif element.tag == OSISXMLBible.OSISNameSpace+"div":
                location = "div of {} div".format( mainDivType )
                Globals.checkXMLNoText( element, location+" at "+verseMilestone, '3f6h' )
                Globals.checkXMLNoTail( element, location+" at "+verseMilestone, '0j6h' )
                # Process the attributes
                divType = divCanonical = divScope = None
                for attrib,value in element.items():
                    if attrib==OSISXMLBible.XMLNameSpace+"space":
                        divSpace = value
                    elif attrib=="type":
                        divType = value
                        location = value + ' ' + location
                    elif attrib=="canonical":
                        divCanonical = value
                    elif attrib=="scope":
                        divScope = value
                    else: logging.warning( "2h56 Unprocessed '{}' attribute ({}) in {} at {}".format( attrib, value, location, verseMilestone ) )
                # Now process the subelements
                for subelement in element.getchildren():
###                 ### chapter in div
                    if subelement.tag == OSISXMLBible.OSISNameSpace+"chapter":
                        sublocation = "chapter of " + location
                        chapterMilestone = validateChapterElement( subelement, chapterMilestone, verseMilestone, sublocation )
###                 ### verse in div
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+"verse":
                        sublocation = "verse of " + location
                        verseMilestone = validateVerseElement( subelement, verseMilestone, chapterMilestone, sublocation )
###                 ### title in div
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+"title":  # section heading
                        sublocation = "title of " + location
                        validateTitle( subelement, sublocation, verseMilestone )
                        if 0:
                            Globals.checkXMLNoTail( subelement, sublocation+" at "+verseMilestone, '3d4f' )
                            sectionHeading = subelement.text
                            titleType = None
                            for attrib,value in subelement.items():
                                if attrib=="type":
                                    titleType = value
                                else: logging.warning( "4h2x Unprocessed '{}' attribute ({}) in {} at {}".format( attrib, value, sublocation, verseMilestone ) )
                            if chapterMilestone:
                                bookResults.append( ('title', titleType, sectionHeading,) )
                                USFMResults.append( ('s', sectionHeading,) )
                            else: # Must be in the introduction
                                bookResults.append( ('title', titleType, sectionHeading,) )
                                USFMResults.append( ('is', sectionHeading,) )
                            for sub2element in subelement.getchildren():
                                if sub2element.tag == OSISXMLBible.OSISNameSpace+"title": # section reference(s)
                                    sub2location = "title of " + sublocation
                                    Globals.checkXMLNoTail( sub2element, sub2location+" at "+verseMilestone, '3d5g' )
                                    sectionReference = sub2element.text
                                    sectionReferenceType = None
                                    for attrib,value in sub2element.items():
                                        if attrib=="type":
                                            sectionReferenceType = value
                                        else: logging.warning( "8h4d Unprocessed '{}' attribute ({}) in {} sub2element of {} at {}".format( attrib, value, sub2element.tag, sub2location, verseMilestone ) )
                                    if sectionReference:
                                        #print( divType, self.subDivType, sectionReferenceType ); halt
                                        #assert( divType=='section' and self.subDivType in ('outline',) and sectionReferenceType=='parallel' )
                                        if Globals.debugFlag: assert( divType=='section' and sectionReferenceType=='parallel' )
                                        bookResults.append( ('title',sectionReference,) )
                                        USFMResults.append( ('r',sectionReference,) )
                                    for sub3element in sub2element.getchildren():
                                        if sub3element.tag == OSISXMLBible.OSISNameSpace+"reference":
                                            sub3location = "reference of " + sub2location
                                            Globals.checkXMLNoSubelements( sub3element, sub3location+" at "+verseMilestone, '3d3d' )
                                            referenceText = sub3element.text
                                            referenceTail = sub3element.tail
                                            referenceOsisRef = None
                                            for attrib,value in sub3element.items():
                                                if attrib=="osisRef":
                                                    referenceOsisRef = value
                                                else: logging.warning( "7k43 Unprocessed '{}' attribute ({}) in {} sub3element of {} at {}".format( attrib, value, sub3element.tag, sub2location, verseMilestone ) )
                                            #print( referenceText, referenceOsisRef, referenceTail )
                                            bookResults.append( ('reference',referenceText,) )
                                            USFMResults.append( ('r+',referenceText+referenceTail,) )
                                        else: logging.warning( "46g2 Unprocessed '{}' sub3element ({}) in {} at {}".format( sub3element.tag, sub3element.text, sub2location, verseMilestone ) )
###                 ### p in div
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+"p": # Most scripture data occurs in here
                        sublocation = "p of " + location
                        verseMilestone = validateParagraph( subelement, sublocation, verseMilestone )
###                 ### list in div
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+"list":
                        sublocation = "list of " + location
                        Globals.checkXMLNoText( subelement, sublocation+" at "+verseMilestone, '2dx34' )
                        Globals.checkXMLNoTail( subelement, sublocation+" at "+verseMilestone, '2c5b' )
                        Globals.checkXMLNoAttributes( subelement, sublocation+" at "+verseMilestone, '2sd4' )
                        Globals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, 'x3f5' )
                        self.list = subelement.text
                        for attrib,value in subelement.items():
                            logging.warning( "7k2a Unprocessed '{}' attribute ({}) in {} subelement of {} at {}".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
###                 ### lg in div
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+"lg":
                        sublocation = "lg of " + location
                        verseMilestone = validateLG( subelement, sublocation, verseMilestone )
###                 ### div in div
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+"div":
                        sublocation = "div of " + location
                        Globals.checkXMLNoText( subelement, sublocation+" at "+verseMilestone, 'dcv4' )
                        Globals.checkXMLNoTail( subelement, sublocation+" at "+verseMilestone, '2c5bv' )
                        subDivType = subDivScope = subDivSpace = None
                        for attrib,value in subelement.items():
                            if attrib=="type":
                                subDivType = value
                                sublocation = value + ' ' + sublocation
                            elif attrib=="scope":
                                subDivScope = value # Should be an OSIS verse range
                            elif attrib==self.XMLNameSpace+"space":
                                subDivSpace = value
                                if Globals.debugFlag: assert( subDivSpace == 'preserve' )
                            else: logging.warning( "84kf Unprocessed '{}' attribute ({}) in {} at {}".format( attrib, value, sublocation, verseMilestone ) )
                        #print( "self.subDivType", self.subDivType )
                        for sub2element in subelement.getchildren():
                            if sub2element.tag == OSISXMLBible.OSISNameSpace+"title":
                                sub2location = "title of " + sublocation
                                Globals.checkXMLNoTail( sub2element, sub2location+" at "+verseMilestone, '4v5g' )
                                title = sub2element.text
                                titleType = titleSubType = None
                                for attrib,value in sub2element.items():
                                    if attrib=="type":
                                        titleType = value
                                    elif attrib=="subType":
                                        titleSubType = value
                                    else: logging.warning( "1d4r Unprocessed '{}' attribute ({}) in {} sub2element of {} at {}".format( attrib, value, sub2element.tag, sub2location, verseMilestone ) )
                                #if titleType: print( "titleType", titleType )
                                if titleType: assert( titleType in ('psalm','parallel',) )
                                if titleSubType: assert( titleSubType == 'x-preverse' )
                                if title:
                                    #print( divType, subDivType )
                                    if divType=='introduction' and subDivType in ('section','outline',):
                                        #bookResults.append( ('title',title,) )
                                        #USFMResults.append( ('iot' if subDivType == 'outline' else 'is',title,) )
                                        self.thisBook.appendLine( 'iot' if subDivType == 'outline' else 'is',title )
                                    elif divType=='majorSection' and subDivType=='section':
                                        #bookResults.append( ('title',title,) )
                                        #USFMResults.append( ('xxxx1' if subDivType == 'outline' else 's1',title,) )
                                        self.thisBook.appendLine( 'xxxx1' if subDivType == 'outline' else 's1',title )
                                    elif divType=='section' and subDivType=='subSection':
                                        #bookResults.append( ('title',title,) )
                                        #USFMResults.append( ('xxxx3' if subDivType == 'outline' else 'xxxx4',title,) )
                                        self.thisBook.appendLine( 'xxxx3' if subDivType == 'outline' else 's',title )
                                    elif divType=='section' and subDivType=='outline':
                                        #bookResults.append( ('title',title,) )
                                        #USFMResults.append( ('iot',title,) )
                                        self.thisBook.appendLine( 'iot', title )
                                    else: halt
                                for sub3element in sub2element.getchildren():
                                    if sub3element.tag == OSISXMLBible.OSISNameSpace+"reference":
                                        sub3location = "reference of " + sub2location
                                        Globals.checkXMLNoSubelements( sub3element, sub3location+" at "+verseMilestone, 'k6l3' )
                                        referenceText = sub3element.text
                                        referenceTail = sub3element.tail
                                        referenceOsisRef = None
                                        for attrib,value in sub3element.items():
                                            if attrib=="osisRef":
                                                referenceOsisRef = value
                                            else: logging.warning( "nm46 Unprocessed '{}' attribute ({}) in {} sub3element of {} at {}".format( attrib, value, sub3element.tag, sub2location, verseMilestone ) )
                                        #print( referenceText, referenceOsisRef, referenceTail )
                                        #bookResults.append( ('reference',referenceText,) )
                                        #USFMResults.append( ('r+',referenceText+referenceTail,) )
                                        self.thisBook.appendLine( 'r~', referenceText+referenceTail )
                                    elif sub3element.tag == OSISXMLBible.OSISNameSpace+"note":
                                        sub3location = "note of " + sub2location
                                        validateCrossReferenceOrFootnote( sub3element, sub3location, verseMilestone )
                                        noteTail = sub3element.tail
                                        if noteTail: # This is the main text of the verse (follows the inserted note)
                                            #bookResults.append( ('lverse+', noteTail,) )
                                            self.thisBook.appendLine( 'lverse~', noteTail )
                                            adjNoteTail = noteTail.replace('\n','') # XML line formatting is irrelevant to USFM
                                            if adjNoteTail: USFMResults.append( ('v~',adjNoteTail,) )
                                    else: logging.warning( "m4g5 Unprocessed '{}' sub3element ({}) in {} at {}".format( sub3element.tag, sub3element.text, sub2location, verseMilestone ) )
                            elif sub2element.tag == OSISXMLBible.OSISNameSpace+"p":
                                sub2location = "p of " + sublocation
                                verseMilestone = validateParagraph( sub2element, sub2location, verseMilestone )
                            elif sub2element.tag == OSISXMLBible.OSISNameSpace+"lg":
                                sub2location = "lg of " + sublocation
                                verseMilestone = validateLG( sub2element, sub2location, verseMilestone )
                            elif sub2element.tag == OSISXMLBible.OSISNameSpace+"list":
                                sub2location = "list of " + sublocation
                                #print( "list", divType, subDivType )
                                Globals.checkXMLNoText( sub2element, sub2location+" at "+verseMilestone, '3x6g' )
                                Globals.checkXMLNoTail( sub2element, sub2location+" at "+verseMilestone, '8j4g' )
                                Globals.checkXMLNoAttributes( sub2element, sub2location+" at "+verseMilestone, '7tgf' )
                                for sub3element in sub2element.getchildren():
                                    if sub3element.tag == OSISXMLBible.OSISNameSpace+"item":
                                        sub3location = "item of " + sub2location
                                        Globals.checkXMLNoTail( sub3element, sub3location+" at "+verseMilestone, '3d8n' )
                                        Globals.checkXMLNoAttributes( sub3element, sub3location+" at "+verseMilestone, '4g7g' )
                                        item = sub3element.text
                                        if item:
                                            if subDivType == 'outline':
                                                #bookResults.append( ('item',item,) )
                                                #USFMResults.append( ('io1',item,) )
                                                self.thisBook.appendLine( 'io1', item )
                                            else: halt
                                        for sub4element in sub3element.getchildren():
                                            if sub4element.tag == OSISXMLBible.OSISNameSpace+"list":
                                                sub4location = "list of " + sub3location
                                                Globals.checkXMLNoText( sub4element, sub4location+" at "+verseMilestone, '5g3d' )
                                                Globals.checkXMLNoTail( sub4element, sub4location+" at "+verseMilestone, '4w5x' )
                                                Globals.checkXMLNoAttributes( sub4element, sub4location+" at "+verseMilestone, '3d45' )
                                                for sub5element in sub4element.getchildren():
                                                    if sub5element.tag == OSISXMLBible.OSISNameSpace+"item":
                                                        sub5location = "item of " + sub4location
                                                        Globals.checkXMLNoTail( sub5element, sub5location+" at "+verseMilestone, '4c5t' )
                                                        Globals.checkXMLNoAttributes( sub5element, sub5location+" at "+verseMilestone, '2sd1' )
                                                        Globals.checkXMLNoSubelements( sub5element, sub5location+" at "+verseMilestone, '8j7n' )
                                                        subItem = sub5element.text
                                                        if subItem:
                                                            if subDivType == 'outline':
                                                                #bookResults.append( ('subItem',subItem,) )
                                                                #USFMResults.append( ('io2',subItem,) )
                                                                self.thisBook.appendLine( 'io2', subItem )
                                                            else: halt
                                                    else: logging.warning( "3kt6 Unprocessed '{}' sub5element ({}) in {} at {}".format( sub5element.tag, sub5element.text, sub4location, verseMilestone ) )
                                            else: logging.warning( "2h4s Unprocessed '{}' sub4element ({}) in {} at {}".format( sub4element.tag, sub4element.text, sub3location, verseMilestone ) )
                                    else: logging.warning( "8k4j Unprocessed '{}' sub3element ({}) in {} at {}".format( sub3element.tag, sub3element.text, sub2location, verseMilestone ) )
                            elif sub2element.tag == OSISXMLBible.OSISNameSpace+"chapter":
                                sub2location = "chapter of " + sublocation
                                chapterMilestone = validateChapterElement( sub2element, chapterMilestone, verseMilestone, sub2location )
                            elif sub2element.tag == OSISXMLBible.OSISNameSpace+"verse":
                                sub2location = "verse of " + sublocation
                                verseMilestone = validateVerseElement( sub2element, verseMilestone, chapterMilestone, sub2location )
                            else: logging.warning( "14k5 Unprocessed '{}' sub2element ({}) in {} at {}".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                    else: logging.warning( "3f67 Unprocessed '{}' sub-element ({}) in {} at {}".format( subelement.tag, subelement.text, location, verseMilestone ) )
########### P
            elif element.tag == OSISXMLBible.OSISNameSpace+"p":
                location = "p of {} div".format( mainDivType )
                verseMilestone = validateParagraph( element, location, verseMilestone )
########### Q
            elif element.tag == OSISXMLBible.OSISNameSpace+"q":
                location = "q of {} div".format( mainDivType )
                qText = element.text
                pass
                qTail = element.tail
                pass
                # Process the attributes
                sID = eID = level = marker = None
                for attrib,value in element.items():
                    if attrib=="sID":
                        sID = value
                        pass
                    elif attrib=="eID":
                        eID = value
                        pass
                    elif attrib=="level":
                        level = value
                        pass
                    elif attrib=="marker":
                        marker = value
                        if Globals.debugFlag: assert( len(marker) == 1 )
                        pass
                    else: logging.warning( "6j33 Unprocessed '{}' attribute ({}) in {} at {}".format( attrib, value, location, verseMilestone ) )
                # Now process the subelements
                for subelement in element.getchildren():
                    if subelement.tag == OSISXMLBible.OSISNameSpace+"verse":
                        sublocation = "verse of " + location
                        verseMilestone = validateVerseElement( subelement, verseMilestone, chapterMilestone, sublocation )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+"transChange":
                        sublocation = "transChange of " + location
                        text = subelement.text
                        if Globals.debugFlag: assert( text )
                        tCTail = subelement.tail
                        # Process the attributes
                        transchangeType = None
                        for attrib,value in subelement.items():
                            if attrib=="type":
                                transchangeType = value
                            else: logging.warning( "821k Unprocessed '{}' attribute ({}) in {} at {}".format( attrib, value, sublocation, verseMilestone ) )
                        if Globals.debugFlag: assert( transchangeType in ('added',) )
                        # Now process the subelements
                        for sub2element in subelement.getchildren():
                            if sub2element.tag == OSISXMLBible.OSISNameSpace+"note":
                                sub2location = "note of " + sublocation
                                validateCrossReferenceOrFootnote( sub2element, sub2location, verseMilestone )
                                noteTail = sub2element.tail
                                if noteTail: # This is the main text of the verse (follows the inserted note)
                                    bookResults.append( ('q+', noteTail,) )
                                    adjNoteTail = noteTail.replace('\n','') # XML line formatting is irrelevant to USFM
                                    if adjNoteTail: USFMResults.append( ('q+',adjNoteTail,) )
                            else: logging.warning( "2j46 Unprocessed '{}' sub2-element ({}) in {} at {}".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                        if tCTail: # This is the main text of the verse quotation (follows the inserted transChange)
                            bookResults.append( ('tCq+', tCTail,) )
                            adjTCTail = tCTail.replace('\n','') # XML line formatting is irrelevant to USFM
                            if adjTCTail: USFMResults.append( ('tCq+',adjTCTail,) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+"note":
                        sublocation = "note of " + location
                        validateCrossReferenceOrFootnote( subelement, sublocation, verseMilestone )
                        noteTail = subelement.tail
                        if noteTail: # This is the main text of the verse (follows the inserted note)
                            bookResults.append( ('q+', noteTail,) )
                            adjNoteTail = noteTail.replace('\n','') # XML line formatting is irrelevant to USFM
                            if adjNoteTail: USFMResults.append( ('q+',adjNoteTail,) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+"p":
                        Globals.checkXMLNoTail( subelement, sublocation+" at "+verseMilestone, '2s7z' )
                        Globals.checkXMLNoAttributes( subelement, sublocation+" at "+verseMilestone, '8h4g' )
                        Globals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, '2k3m' )
                        p = element.text
                        if p == '¶':
                            bookResults.append( ('paragraph', None,) )
                            bookResults.append( ('p', None,) )
                        else:
                            # print( "p = '{}'".format( element.text ) ); halt
                            bookResults.append( ('paragraph', p,) )
                            bookResults.append( ('p', p,) )
                    else: logging.warning( "95k3 Unprocessed '{}' sub-element ({}) in {} at {}".format( subelement.tag, subelement.text, location, verseMilestone ) )
########### Chapter
            elif element.tag == OSISXMLBible.OSISNameSpace+"chapter":
                location = "chapter of {} div".format( mainDivType )
                chapterMilestone = validateChapterElement( element, chapterMilestone, verseMilestone, location )
                #print( "BBB is", BBB )
                if chapterMilestone and mainDivType=='bookGroup':
                    #print( "cm", chapterMilestone )
                    OSISBookID = chapterMilestone.split('.')[0]
                    try:
                        newBBB = Globals.BibleBooksCodes.getBBBFromOSIS( OSISBookID )
                    except:
                        logging.critical( _("'{}' is not a valid OSIS book identifier").format( OSISBookID ) )
                    if newBBB != BBB:
                        BBB = newBBB
                        USFMAbbreviation = Globals.BibleBooksCodes.getUSFMAbbreviation( BBB )
                        USFMNumber = Globals.BibleBooksCodes.getUSFMNumber( BBB )
                        if Globals.verbosityLevel > 1: print( _("  Validating {}...").format( BBB ) )
                if chapterMilestone.startswith('chapterContainer.'): # it must have been a container -- process the subelements
                    OSISChapterID = chapterMilestone[17:] # Remove the 'chapterContainer.' prefix
                    chapterBits = OSISChapterID.split( '.' )
                    if Globals.debugFlag: assert( len(chapterBits) == 2 )
                    if Globals.debugFlag: assert( chapterBits[1].isdigit() )
                    #bookResults.append( ('chapter', chapterBits[1],) )
                    #USFMResults.append( ('c', chapterBits[1],) )
                    self.thisBook.appendLine( 'c', chapterBits[1] )
                    for subelement in element.getchildren():
                        if subelement.tag == OSISXMLBible.OSISNameSpace+"p": # Most scripture data occurs in here
                            sublocation = "p of " + location
                            verseMilestone = validateParagraph( subelement, sublocation, verseMilestone )
                        elif subelement.tag == OSISXMLBible.OSISNameSpace+"title":  # section heading
                            sublocation = "title of " + location
                            validateTitle( subelement, sublocation, verseMilestone )
                        elif subelement.tag == OSISXMLBible.OSISNameSpace+"verse":
                            sublocation = "verse of " + location
                            verseMilestone = validateVerseElement( subelement, verseMilestone, chapterMilestone, sublocation )
                            #print( 'vM', verseMilestone ); halt
                            if verseMilestone and verseMilestone.startswith('verseContainer.'): # it must have been a container -- process the subelements
                                #print( "Yikes!" ) # Why??????????????
                                #bookResults.append( ('verse', verseMilestone[15:],) ) # Remove the 'verseContainer.' prefix
                                #USFMResults.append( ('v', verseMilestone[15:],) ) # Remove the 'verseContainer.' prefix
                                self.thisBook.appendLine( 'v', verseMilestone[15:] ) # Remove the 'verseContainer.' prefix
                                for sub2element in subelement.getchildren():
                                    if sub2element.tag == OSISXMLBible.OSISNameSpace+"w":
                                        sub2location = "w of " + sublocation
                                        Globals.checkXMLNoTail( sub2element, sub2location+" at "+verseMilestone, '2k3c' )
                                        word = sub2element.text
                                        if Globals.debugFlag: assert( word ) # That should be the actual word
                                        # Process the attributes
                                        lemma = morph = None
                                        for attrib,value in sub2element.items():
                                            if attrib=="lemma": lemma = value
                                            elif attrib=="morph": morph = value
                                            else: logging.warning( "2h54 Unprocessed '{}' attribute ({}) in {} at {}".format( attrib, value, sub2location, verseMilestone ) )
                                        # Now process the subelements
                                        segText = segTail = None
                                        for sub3element in sub2element.getchildren():
                                            if sub3element.tag == OSISXMLBible.OSISNameSpace+"seg":
                                                sub3location = "seg of " + sub2location
                                                Globals.checkXMLNoSubelements( sub3element, sub3location+" at "+verseMilestone, '43gx' )
                                                segText, segTail = sub3element.text, sub3element.tail # XXX unused .............................................
                                                # Process the attributes
                                                for attrib,value in sub3element.items():
                                                    if attrib=="type": segType = value
                                                    else: logging.warning( "963k Unprocessed '{}' attribute ({}) in {} at {}".format( attrib, value, sub3location, verseMilestone ) )
                                        #bookResults.append( ('word', (word,lemma,),) )
                                        #USFMResults.append( ('v~', "{} [{}]".format( word,lemma),) )
                                        self.thisBook.appendLine( 'vw', "{} [{}]".format( word,lemma) )
                                    elif sub2element.tag == OSISXMLBible.OSISNameSpace+"seg":
                                        sub2location = "seg of " + sublocation
                                        Globals.checkXMLNoTail( sub2element, sub2location+" at "+verseMilestone, '9s8v' )
                                        Globals.checkXMLNoSubelements( sub2element, sub2location+" at "+verseMilestone, '93dr' )
                                        seg = sub2element.text
                                        if Globals.debugFlag: assert( seg ) # That should be the actual segment character
                                        # Process the attributes first
                                        for attrib,value in sub2element.items():
                                            if attrib=="type":
                                                segType = value
                                            else: logging.warning( "5jj2 Unprocessed '{}' attribute ({}) in {} at {}".format( attrib, value, sub2location, verseMilestone ) )
                                        #bookResults.append( ('segment', (seg,segType,),) )
                                        self.thisBook.appendLine( 'segment', "{} [{}]".format( seg,segType) )
                                    elif sub2element.tag == OSISXMLBible.OSISNameSpace+"note":
                                        sub2location = "note of " + sublocation
                                        validateCrossReferenceOrFootnote( sub2element, sub2location, verseMilestone )
                                        noteTail = sub2element.tail
                                        if noteTail: # This is the main text of the verse (follows the inserted note)
                                            #bookResults.append( ('lverse+', noteTail,) )
                                            adjNoteTail = noteTail.replace('\n','') # XML line formatting is irrelevant to USFM
                                            if adjNoteTail:
                                                #USFMResults.append( ('lv~',adjNoteTail,) )
                                                self.thisBook.appendLine( 'v~', adjNoteTail )
                                        # Now process the subelements
                                        for sub3element in sub2element.getchildren():
                                            if sub3element.tag == OSISXMLBible.OSISNameSpace+"catchWord":
                                                sub3location = "catchword of " + sub2location
                                                Globals.checkXMLNoTail( sub3element, sub3location+" at "+verseMilestone, '9k8j' )
                                                Globals.checkXMLNoAttributes( sub3element, sub3location+" at "+verseMilestone, '3d2a' )
                                                Globals.checkXMLNoSubelements( sub3element, sub3location+" at "+verseMilestone, '0o9i' )
                                                catchWord = sub3element.text
                                            elif sub3element.tag == OSISXMLBible.OSISNameSpace+"rdg":
                                                sub3location = "rdg of " + sub2location
                                                Globals.checkXMLNoTail( sub3element, sub3location+" at "+verseMilestone, '8h7g' )
                                                rdg = sub3element.text
                                                # Process the attributes
                                                for attrib,value in sub3element.items():
                                                    if attrib=="type":
                                                        pass
                                                    else: logging.warning( "3hgh Unprocessed '{}' attribute ({}) in {} at {}".format( attrib, value, sub3location, verseMilestone ) )
                                                # Now process the subelements
                                                for sub4element in sub3element.getchildren():
                                                    if sub4element.tag == OSISXMLBible.OSISNameSpace+"w":
                                                        sub4location = "w of " + sub3location
                                                        Globals.checkXMLNoTail( sub4element, sub4location+" at "+verseMilestone, '6g5d' )
                                                        Globals.checkXMLNoSubelements( sub4element, sub4location+" at "+verseMilestone, '5r4d' )
                                                        word = sub4element.text
                                                        # Process the attributes
                                                        lemma = None
                                                        for attrib,value in sub4element.items():
                                                            if attrib=="lemma": lemma = value
                                                            else: logging.warning( "85kd Unprocessed '{}' attribute ({}) in {} at {}".format( attrib, value, sub4location, verseMilestone ) )
                                                    elif sub4element.tag == OSISXMLBible.OSISNameSpace+"seg":
                                                        sub4location = "seg of " + sub3location
                                                        Globals.checkXMLNoTail( sub4element, sub4location+" at "+verseMilestone, '5r4q' )
                                                        Globals.checkXMLNoSubelements( sub4element, sub4location+" at "+verseMilestone, '4s3a' )
                                                        word = sub4element.text
                                                        # Process the attributes
                                                        segType = None
                                                        for attrib,value in sub4element.items():
                                                            if attrib=="type": segType = value
                                                            else: logging.warning( "9r5j Unprocessed '{}' attribute ({}) in {} at {}".format( attrib, value, sub4location, verseMilestone ) )
                                                    else: logging.warning( "7k3s Unprocessed '{}' sub-element ({}) in {} at {}".format( sub4element.tag, sub4element.text, sub3location, verseMilestone ) )
                                            else: logging.warning( "9y5g Unprocessed '{}' sub-element ({}) in {} at {}".format( sub3element.tag, sub3element.text, sub2location, verseMilestone ) )
                                    else: logging.warning( "05kq Unprocessed '{}' sub-element ({}) in {} at {}".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                            elif verseMilestone and verseMilestone.startswith('verseContents#'): # it must have been a container -- process the string
                                print( "verseContents", verseMilestone )
                                bits = verseMilestone.split( '#', 2 )
                                if Globals.debugFlag: assert( len(bits) == 3 )
                                if Globals.debugFlag: assert( bits[0] == 'verseContents' )
                                if Globals.debugFlag: assert( bits[1].isdigit() )
                                if Globals.debugFlag: assert( bits[2] )
                                thisData = bits[1]
                                if bits[2].strip(): thisData += ' ' + bits[2].replace('\n','')
                                #assert( bits[2].strip() )
                                #bookResults.append( ('verse', bits[1],) ) # The verse number
                                #USFMResults.append( ('v', bits[1],) ) # The verse number
                                #bookResults.append( ('verse+',bits[2],) )
                                #USFMResults.append( ('v~',bits[2].replace('\n','').strip(),) ) # Newlines and leading spaces are irrelevant to USFM formatting
                                self.thisBook.appendLine( 'v', thisData )
                                #print( USFMResults[-4:] )
                                print( self.thisBook._rawLines[-4:] )
                        else: logging.warning( "4s9j Unprocessed '{}' sub-element ({}) in {} at {}".format( subelement.tag, subelement.text, location, verseMilestone ) )
########### Verse
            elif element.tag == OSISXMLBible.OSISNameSpace+"verse": # Some OSIS Bibles have verse milestones directly in a bookgroup div
                location = "verse of {} div".format( mainDivType )
                verseMilestone = validateVerseElement( element, verseMilestone, chapterMilestone, location )
########### Lg
            elif element.tag == OSISXMLBible.OSISNameSpace+"lg":
                location = "lg of {} div".format( mainDivType )
                verseMilestone = validateLG( element, location, verseMilestone )
########### TransChange
            elif element.tag == OSISXMLBible.OSISNameSpace+"transChange":
                location = "transChange of {} div".format( mainDivType )
                text = element.text
                if Globals.debugFlag: assert( text )
                tCTail = element.tail
                # Process the attributes
                transchangeType = None
                for attrib,value in element.items():
                    if attrib=="type":
                        transchangeType = value
                    else: logging.warning( "8k2j Unprocessed '{}' attribute ({}) in {} at {}".format( attrib, value, location, verseMilestone ) )
                if Globals.debugFlag: assert( transchangeType in ('added',) )
                # Now process the subelements
                for subelement in element.getchildren():
                    if subelement.tag == OSISXMLBible.OSISNameSpace+"note":
                        sublocation = "note of " + location
                        validateCrossReferenceOrFootnote( subelement, sublocation, verseMilestone )
                        noteTail = subelement.tail
                        if noteTail: # This is the main text of the verse (follows the inserted note)
                            bookResults.append( ('q+', noteTail,) )
                            adjNoteTail = noteTail.replace('\n','') # XML line formatting is irrelevant to USFM
                            if adjNoteTail: USFMResults.append( ('q+',adjNoteTail,) )
                    else: logging.warning( "2f5z Unprocessed '{}' sub-element ({}) in {} at {}".format( subelement.tag, subelement.text, location, verseMilestone ) )
                if tCTail: # This is the main text of the verse (follows the inserted transChange)
                    bookResults.append( ('tCverse+', tCTail,) )
                    adjTCTail = tCTail.replace('\n','') # XML line formatting is irrelevant to USFM
                    if adjTCTail: USFMResults.append( ('tCv~',adjTCTail,) )
########### Note
            elif element.tag == OSISXMLBible.OSISNameSpace+"note":
                location = "note of {} div".format( mainDivType )
                validateCrossReferenceOrFootnote( element, location, verseMilestone )
                noteTail = element.tail
                if noteTail: # This is the main text of the verse (follows the inserted note)
                    bookResults.append( ('lverse+', noteTail,) )
                    adjNoteTail = noteTail.replace('\n','') # XML line formatting is irrelevant to USFM
                    if adjNoteTail: self.thisBook.appendLine( 'v~', adjNoteTail ) # USFMResults.append( ('lv~',adjNoteTail,) )
########### Left-overs!
            else: logging.warning( "5ks1 Unprocessed '{}' sub-element ({}) in {} div at {}".format( element.tag, element.text, mainDivType, verseMilestone ) )
            #if element.tail is not None and element.tail.strip(): logging.error( "Unexpected left-over '{}' tail data after {} element in {} div at {}".format( element.tail, element.tag, mainDivType, verseMilestone ) )

        #print( "Done Validating", BBB, mainDivOsisID, mainDivType )
        #print( "bookResults", bookResults )
        if BBB:
            if Globals.verbosityLevel > 2: print( "  Saving {} into results...".format( BBB ) )
            #print( mainDivOsisID, "results", BBB, bookResults[:10], "..." )
            #if bookResults: self.bkData[BBB] = bookResults
            #if USFMResults: self.USFMBooks[BBB] = USFMResults
            self.saveBook( self.thisBook )
    # end of OSISXMLBible.validateAndExtractMainDiv


    #def getVerseDataList( self, reference ):
        #"""Returns a list of 2-tuples containing (word, lemma)."""
        #assert( len(reference) == 3 ) # BBB,C,V
        #BBB, chapterString, verseString = reference
        #assert( isinstance(BBB,str) and len(BBB)==3 )
        #assert( BBB in Globals.BibleBooksCodes )
        #assert( isinstance( chapterString, str ) )
        #assert( isinstance( verseString, str ) )
        #if BBB in self.books:
            #foundChapter, foundVerse, result = False, False, []
            #for info in self.books[BBB]:
                #if len(info)==2:
                    #name, value = info
                    #if name == 'chapter':
                        #foundChapter = value == chapterString
                        #foundVerse = False
                    #if foundChapter and name=='verse': foundVerse = value == verseString
                    #if foundVerse:
                        #if name=='word': result.append( value )
                        #elif name=='segment': result.append( value )
                        #elif name!='chapter' and name!='verse': print( "OSISXMLBible got", name, value )
            #return result
    ## end of getVerseData

    #def getVerseText( self, reference ):
        #"""Returns the text for the verse."""
        #assert( len(reference) == 3 ) # BBB,C,V
        #result = ''
        #data = self.getVerseDataList( reference )
        #if data:
            #for word, lemma in data: # throw away the lemma data and segment types
                #if result: result += ' '
                #result += word
            #return result
# end of OSISXMLBible class


def demo():
    """
    Main program to handle command line parameters and then run what they want.
    """
    if Globals.verbosityLevel > 0: print( ProgNameVersion )


    if 1: # Test OSISXMLBible object
        testFilepaths = (
            #"Tests/DataFilesForTests/OSISTest1/",
            #"Tests/DataFilesForTests/OSISTest2/",
            #"../morphhb/wlc/Ruth.xml", "../morphhb/wlc/Dan.xml", "../morphhb/wlc/", # Hebrew Ruth, Daniel, Bible
            #"../../../../../Data/Work/Bibles/Formats/OSIS/Crosswire USFM-to-OSIS (Perl)/Matigsalug.osis.xml", # Entire Bible in one file 4.4MB
            #"../../../../../Data/Work/Bibles/Formats/OSIS/kjvxml from DMSmith/kjv.xml", # Entire Bible in one file 23.7MB
            #"../../../../../Data/Work/Bibles/Formats/OSIS/kjvxml from DMSmith/kjvfull.xml", # Entire Bible in one file 24.2MB
            #"../../../../../Data/Work/Bibles/Formats/OSIS/kjvxml from DMSmith/kjvlite.xml", # Entire Bible in one file 7.7MB
            #"../../MatigsalugOSIS/OSIS-Output/MBTGEN.xml",
            "../../MatigsalugOSIS/OSIS-Output/MBTRUT.xml", # Single books
            #    "../../MatigsalugOSIS/OSIS-Output/MBTMRK.xml", "../../MatigsalugOSIS/OSIS-Output/MBTJAS.xml", # Single books
            #    "../../MatigsalugOSIS/OSIS-Output/MBT2PE.xml", # Single book
            #"../../MatigsalugOSIS/OSIS-Output", # Entire folder of single books
            )
        justOne = ( testFilepaths[0], )

        for j, testFilepath in enumerate( justOne ): # Choose testFilepaths or justOne
            # Demonstrate the OSIS Bible class
            if Globals.verbosityLevel > 1: print( "\n{}/ Demonstrating the OSIS Bible class...".format( j+1 ) )
            if Globals.verbosityLevel > 0: print( "  Test filepath is '{}'".format( testFilepath ) )
            oB = OSISXMLBible( testFilepath ) # Load and process the XML
            oB.load()
            if Globals.verbosityLevel > 0: print( oB ) # Just print a summary
            print( 'RUT' in oB )
            oBB = oB['RUT']
            try: print( "rawLines", oBB._rawLines[:50] )
            except: print( "processedLines", oBB._processedLines[:50] )
            print( "rejected", list(zip( oBB.badMarkers, oBB.badMarkerCounts)) )
            for j in range( 0, 30 ):
                print( "  processedLines", oBB._processedLines[j] )
            if 1: # Test verse lookup
                import VerseReferences
                for referenceTuple in ( ('OT','GEN','1','1'), ('OT','GEN','1','3'),
                                    ('OT','RUT','1','1'), ('OT','RUT','3','3'),
                                    ('OT','PSA','3','0'), ('OT','PSA','3','1'),
                                    ('OT','DAN','1','21'),
                                    ('NT','MAT','3','5'), ('NT','JDE','1','4'), ('NT','REV','22','21'),
                                    ('DC','BAR','1','1'), ('DC','MA1','1','1'), ('DC','MA2','1','1',), ):
                    (t, b, c, v) = referenceTuple
                    if t=='OT' and len(oB)==27: continue # Don't bother with OT references if it's only a NT
                    if t=='NT' and len(oB)==39: continue # Don't bother with NT references if it's only a OT
                    if t=='DC' and len(oB)<=66: continue # Don't bother with DC references if it's too small
                    svk = VerseReferences.SimpleVerseKey( b, c, v )
                    #print( svk, oB.getVerseDataList( svk ) )
                    print( svk, oB.getVerseText( svk ) )
# end of demo

if __name__ == '__main__':
    # Configure basic set-up
    parser = Globals.setup( ProgName, ProgVersion )
    Globals.addStandardOptionsAndProcess( parser )

    demo()

    Globals.closedown( ProgName, ProgVersion )
# end of OSISXMLBible.py