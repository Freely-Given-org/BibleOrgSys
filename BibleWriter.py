#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# BibleWriter.py
#   Last modified: 2013-07-03 by RJH (also update ProgVersion below)
#
# Module writing out InternalBibles in various formats.
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
PROTOTYPE ONLY AT THIS STAGE! (Code not well structured.)

Module for exporting Bibles in various formats including USFM, USX, and OSIS.

A class which extends InternalBible.

This is intended to be a virtual class, i.e., to be extended further
    by classes which load particular kinds of Bibles (e.g., OSIS, USFM, USX, etc.)

Contains functions:
    toPseudoUSFM( self, outputFolder=None )
    toUSFM( self, outputFolder=None )
    toTheWord( self, outputFolder=None )
    toMediaWiki( self, outputFolder=None, controlDict=None, validationSchema=None )
    toZefaniaXML( self, outputFolder=None, controlDict=None, validationSchema=None )
    toUSXXML( self, outputFolder=None, controlDict=None, validationSchema=None )
    toOSISXML( self, outputFolder=None, controlDict=None, validationSchema=None )
    toSwordModule( self, outputFolder=None, controlDict=None, validationSchema=None )
    toHTML5( self, outputFolder=None, controlDict=None, validationSchema=None )
    doAllExports( self, givenOutputFolderName=None )
"""

ProgName = "Bible writer"
ProgVersion = "0.15"
ProgNameVersion = "{} v{}".format( ProgName, ProgVersion )

debuggingThisModule = False


import sys, os, logging, datetime
from gettext import gettext as _
import multiprocessing

import Globals, ControlFiles
from InternalBible import InternalBible
from BibleOrganizationalSystems import BibleOrganizationalSystem
from BibleReferences import BibleReferenceList
from MLWriter import MLWriter


defaultControlFolder = "ControlFiles/" # Relative to the current working directory



class BibleWriter( InternalBible ):
    """
    Class to export Bibles.

    """
    def __init__( self ):
        """
        #    Create the object.
        #    """
        InternalBible.__init__( self  ) # Initialise the base class
        self.doneSetupGeneric = False
        #self.genericBOS = BibleOrganizationalSystem( "GENERIC-KJV-81" )
        #self.genericBRL = BibleReferenceList( self.genericBOS, BibleObject=self ) # self isn't actualised yet!!!
    # end of BibleWriter.__init_


    #def x__str__( self ):
        #"""
        #This method returns the string representation of a Bible.

        #@return: the name of a Bible object formatted as a string
        #@rtype: string
        #"""
        #result = "Bible Writer object"
        #if self.name: result += ('\n' if result else '') + self.name
        #if self.sourceFolder: result += ('\n' if result else '') + "  From: " + self.sourceFolder
        #result += ('\n' if result else '') + "  Number of books = " + str(len(self.books))
        #return result
    ## end of BibleWriter.__str__



    def setDefaultControlFolder( self, newFolderName ):
        global defaultControlFolder
        defaultControlFolder = newFolderName
    # end of BibleWriter.setDefaultControlFolder



    def __setupWriter( self ):
        """
        Do some generic system setting up.

        Unfortunately, I don't know how to do this in the _init__ function
            coz it uses self (which isn't actualised yet in init).
        """
        assert( not self.doneSetupGeneric )
        self.genericBOS = BibleOrganizationalSystem( "GENERIC-KJV-81" )
        self.genericBRL = BibleReferenceList( self.genericBOS, BibleObject=self )
        self.doneSetupGeneric = True
    # end of BibleWriter.__setupWriter



    def toPseudoUSFM( self, outputFolder=None ):
        """
        Write the pseudo USFM out directly (for debugging, etc.).
        """
        if Globals.verbosityLevel > 1: print( "Running BibleWriter:toPseudoUSFM..." )
        if Globals.debugFlag: assert( self.books )

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolder: outputFolder = "OutputFiles/BOS_PseudoUSFMExport/"
        if not os.access( outputFolder, os.F_OK ): os.makedirs( outputFolder ) # Make the empty folder if there wasn't already one there

        allCharMarkers = Globals.USFMMarkers.getCharacterMarkersList( expandNumberableMarkers=True )


        # Write the raw and pseudo-USFM files
        for BBB,bookObject in self.books.items():
            try: rawUSFMData = bookObject._rawLines
            except: rawUSFMData = None # it's been deleted  :-(
            if rawUSFMData:
                #print( "\pseudoUSFMData", pseudoUSFMData[:50] ); halt
                USFMAbbreviation = Globals.BibleBooksCodes.getUSFMAbbreviation( BBB )
                USFMNumber = Globals.BibleBooksCodes.getUSFMNumber( BBB )

                filename = "{}{}BWr.rSFM".format( USFMNumber, USFMAbbreviation.upper() ) # BWr = BibleWriter
                filepath = os.path.join( outputFolder, filename )
                if Globals.verbosityLevel > 3: print( "  " + _("Writing '{}'...").format( filepath ) )
                with open( filepath, 'wt' ) as myFile:
                    for marker,text in rawUSFMData:
                        myFile.write( "{}: '{}'\n".format( marker, text ) )

            pseudoUSFMData = bookObject._processedLines
            #print( "\pseudoUSFMData", pseudoUSFMData[:50] ); halt
            USFMAbbreviation = Globals.BibleBooksCodes.getUSFMAbbreviation( BBB )
            USFMNumber = Globals.BibleBooksCodes.getUSFMNumber( BBB )

            filename = "{}{}BWr.pSFM".format( USFMNumber, USFMAbbreviation.upper() ) # BWr = BibleWriter
            filepath = os.path.join( outputFolder, filename )
            if Globals.verbosityLevel > 3: print( "  " + _("Writing '{}'...").format( filepath ) )
            with open( filepath, 'wt' ) as myFile:
                for marker,originalMarker,text,cleanText,extras in pseudoUSFMData:
                    myFile.write( "{} ({}): '{}' '{}' {}\n".format( marker, originalMarker, text, cleanText, extras ) )

        return True
    # end of BibleWriter.toPseudoUSFM



    def toUSFM( self, outputFolder=None ):
        """
        Adjust the pseudo USFM and write the USFM files.
        """
        if Globals.verbosityLevel > 1: print( "Running BibleWriter:toUSFM..." )
        if Globals.debugFlag: assert( self.books )

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolder: outputFolder = "OutputFiles/BOS_USFMExport/"
        if not os.access( outputFolder, os.F_OK ): os.makedirs( outputFolder ) # Make the empty folder if there wasn't already one there
        #if not controlDict: controlDict = {}; ControlFiles.readControlFile( 'ControlFiles', "To_MediaWiki_controls.txt", controlDict )
        #assert( controlDict and isinstance( controlDict, dict ) )

        allCharMarkers = Globals.USFMMarkers.getCharacterMarkersList( expandNumberableMarkers=True )


        # Adjust the extracted outputs
        for BBB,bookObject in self.books.items():
            pseudoUSFMData = bookObject._processedLines
            #print( "\pseudoUSFMData", pseudoUSFMData[:50] ); halt
            USFMAbbreviation = Globals.BibleBooksCodes.getUSFMAbbreviation( BBB )
            USFMNumber = Globals.BibleBooksCodes.getUSFMNumber( BBB )

            USFM = ""
            inField = None
            if Globals.verbosityLevel > 2: print( "  " + _("Adjusting USFM output..." ) )
            for pseudoMarker,originalMarker,text,cleanText,extras in pseudoUSFMData:
                if (not USFM) and pseudoMarker!='id': # We need to create an initial id line
                    USFM += '\\id {} -- BibleOrgSys USFM export v{}'.format( USFMAbbreviation.upper(), ProgVersion )
                if pseudoMarker in ('c#',): continue # Ignore our additions
                value = cleanText # (temp)
                if Globals.debugFlag and debuggingThisModule: print( "pseudoMarker = '{}' value = '{}'".format( pseudoMarker, value ) )
                if pseudoMarker in ('v','f','fr','x','xo',): # These fields should always end with a space but the processing will have removed them
                    if Globals.debugFlag: assert( value )
                    if value[-1] != ' ': value += ' ' # Append a space since it didn't have one
                if pseudoMarker[-1]=='~' or Globals.USFMMarkers.isNewlineMarker(pseudoMarker): # Have a continuation field
                    if inField is not None:
                        USFM += '\\{}*'.format( inField ) # Do a close marker for footnotes and cross-references
                        inField = None
                if pseudoMarker[-1]=='~': USFM += value
                else: # not a continuation marker
                    adjValue = value
                    #if pseudoMarker in ('it','bk','ca','nd',): # Character markers to be closed -- had to remove ft and xt from this list for complex footnotes with f fr fq ft fq ft f*
                    if pseudoMarker in allCharMarkers: # Character markers to be closed
                        #if (USFM[-2]=='\\' or USFM[-3]=='\\') and USFM[-1]!=' ':
                        if USFM[-1] != ' ':
                            USFM += ' ' # Separate markers by a space e.g., \p\bk Revelation
                            if Globals.debugFlag: print( "USFM: Added space to '{}' before '{}'".format( USFM[-2], pseudoMarker ) )
                        adjValue += '\\{}*'.format( pseudoMarker ) # Do a close marker
                    elif pseudoMarker in ('f','x',): inField = pseudoMarker # Remember these so we can close them later
                    elif pseudoMarker in ('fr','fq','ft','xo',): USFM += '' # These go on the same line just separated by spaces and don't get closed
                    elif USFM: USFM += '\n' # paragraph markers go on a new line
                    if not value: USFM += '\\{}'.format( pseudoMarker )
                    else: USFM += '\\{} {}'.format( pseudoMarker,adjValue )
                #print( pseudoMarker, USFM[-200:] )

            # Write the USFM output
            #print( "\nUSFM", USFM[:3000] )
            filename = "{}{}BWr.SFM".format( USFMNumber, USFMAbbreviation.upper() ) # This seems to be the undocumented standard filename format (and BWr = BibleWriter)
            #if not os.path.exists( USFMOutputFolder ): os.makedirs( USFMOutputFolder )
            filepath = os.path.join( outputFolder, filename )
            if Globals.verbosityLevel > 2: print( "  " + _("Writing '{}'...").format( filepath ) )
            with open( filepath, 'wt' ) as myFile: myFile.write( USFM )
        return True
    # end of BibleWriter.toUSFM


    def toUSFM( self, outputFolder=None ):
        """
        Adjust the pseudo USFM and write the USFM files.
        """
        if Globals.verbosityLevel > 1: print( "Running BibleWriter:toUSFM..." )
        if Globals.debugFlag: assert( self.books )

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolder: outputFolder = "OutputFiles/BOS_USFMExport/"
        if not os.access( outputFolder, os.F_OK ): os.makedirs( outputFolder ) # Make the empty folder if there wasn't already one there
        #if not controlDict: controlDict = {}; ControlFiles.readControlFile( 'ControlFiles', "To_MediaWiki_controls.txt", controlDict )
        #assert( controlDict and isinstance( controlDict, dict ) )

        allCharMarkers = Globals.USFMMarkers.getCharacterMarkersList( expandNumberableMarkers=True )


        # Adjust the extracted outputs
        for BBB,bookObject in self.books.items():
            pseudoUSFMData = bookObject._processedLines
            #print( "\pseudoUSFMData", pseudoUSFMData[:50] ); halt
            USFMAbbreviation = Globals.BibleBooksCodes.getUSFMAbbreviation( BBB )
            USFMNumber = Globals.BibleBooksCodes.getUSFMNumber( BBB )

            USFM = ""
            inField = None
            if Globals.verbosityLevel > 2: print( "  " + _("Adjusting USFM output..." ) )
            for pseudoMarker,originalMarker,text,cleanText,extras in pseudoUSFMData:
                if (not USFM) and pseudoMarker!='id': # We need to create an initial id line
                    USFM += '\\id {} -- BibleOrgSys USFM export v{}'.format( USFMAbbreviation.upper(), ProgVersion )
                if pseudoMarker in ('c#',): continue # Ignore our additions
                value = cleanText # (temp)
                if Globals.debugFlag and debuggingThisModule: print( "pseudoMarker = '{}' value = '{}'".format( pseudoMarker, value ) )
                if pseudoMarker in ('v','f','fr','x','xo',): # These fields should always end with a space but the processing will have removed them
                    if Globals.debugFlag: assert( value )
                    if value[-1] != ' ': value += ' ' # Append a space since it didn't have one
                if pseudoMarker[-1]=='~' or Globals.USFMMarkers.isNewlineMarker(pseudoMarker): # Have a continuation field
                    if inField is not None:
                        USFM += '\\{}*'.format( inField ) # Do a close marker for footnotes and cross-references
                        inField = None
                if pseudoMarker[-1]=='~': USFM += value
                else: # not a continuation marker
                    adjValue = value
                    #if pseudoMarker in ('it','bk','ca','nd',): # Character markers to be closed -- had to remove ft and xt from this list for complex footnotes with f fr fq ft fq ft f*
                    if pseudoMarker in allCharMarkers: # Character markers to be closed
                        #if (USFM[-2]=='\\' or USFM[-3]=='\\') and USFM[-1]!=' ':
                        if USFM[-1] != ' ':
                            USFM += ' ' # Separate markers by a space e.g., \p\bk Revelation
                            if Globals.debugFlag: print( "USFM: Added space to '{}' before '{}'".format( USFM[-2], pseudoMarker ) )
                        adjValue += '\\{}*'.format( pseudoMarker ) # Do a close marker
                    elif pseudoMarker in ('f','x',): inField = pseudoMarker # Remember these so we can close them later
                    elif pseudoMarker in ('fr','fq','ft','xo',): USFM += '' # These go on the same line just separated by spaces and don't get closed
                    elif USFM: USFM += '\n' # paragraph markers go on a new line
                    if not value: USFM += '\\{}'.format( pseudoMarker )
                    else: USFM += '\\{} {}'.format( pseudoMarker,adjValue )
                #print( pseudoMarker, USFM[-200:] )

            # Write the USFM output
            #print( "\nUSFM", USFM[:3000] )
            filename = "{}{}BWr.SFM".format( USFMNumber, USFMAbbreviation.upper() ) # This seems to be the undocumented standard filename format (and BWr = BibleWriter)
            #if not os.path.exists( USFMOutputFolder ): os.makedirs( USFMOutputFolder )
            filepath = os.path.join( outputFolder, filename )
            if Globals.verbosityLevel > 2: print( "  " + _("Writing '{}'...").format( filepath ) )
            with open( filepath, 'wt' ) as myFile: myFile.write( USFM )
        return True
    # end of BibleWriter.toUSFM


    def toTheWord( self, outputFolder=None ):
        """
        Adjust the pseudo USFM and write the USFM files.
        """
        if Globals.verbosityLevel > 1: print( "Running BibleWriter:toTheWord..." )
        if Globals.debugFlag: assert( self.books )

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolder: outputFolder = "OutputFiles/BOS_TheWordExport/"
        if not os.access( outputFolder, os.F_OK ): os.makedirs( outputFolder ) # Make the empty folder if there wasn't already one there
        #if not controlDict: controlDict = {}; ControlFiles.readControlFile( 'ControlFiles', "To_MediaWiki_controls.txt", controlDict )
        #assert( controlDict and isinstance( controlDict, dict ) )

        allCharMarkers = Globals.USFMMarkers.getCharacterMarkersList( expandNumberableMarkers=True )


        # Adjust the extracted outputs
        for BBB,bookObject in self.books.items():
            pseudoUSFMData = bookObject._processedLines
            #print( "\pseudoUSFMData", pseudoUSFMData[:50] ); halt
            USFMAbbreviation = Globals.BibleBooksCodes.getUSFMAbbreviation( BBB )
            USFMNumber = Globals.BibleBooksCodes.getUSFMNumber( BBB )

            USFM = ""
            inField = None
            if Globals.verbosityLevel > 2: print( "  " + _("Adjusting USFM output..." ) )
            for pseudoMarker,originalMarker,text,cleanText,extras in pseudoUSFMData:
                if (not USFM) and pseudoMarker!='id': # We need to create an initial id line
                    USFM += '\\id {} -- BibleOrgSys TheWord export v{}'.format( USFMAbbreviation.upper(), ProgVersion )
                if pseudoMarker in ('c#',): continue # Ignore our additions
                value = cleanText # (temp)
                if Globals.debugFlag and debuggingThisModule: print( "pseudoMarker = '{}' value = '{}'".format( pseudoMarker, value ) )
                if pseudoMarker in ('v','f','fr','x','xo',): # These fields should always end with a space but the processing will have removed them
                    if Globals.debugFlag: assert( value )
                    if value[-1] != ' ': value += ' ' # Append a space since it didn't have one
                if pseudoMarker[-1]=='~' or Globals.USFMMarkers.isNewlineMarker(pseudoMarker): # Have a continuation field
                    if inField is not None:
                        USFM += '\\{}*'.format( inField ) # Do a close marker for footnotes and cross-references
                        inField = None
                if pseudoMarker[-1]=='~': USFM += value
                else: # not a continuation marker
                    adjValue = value
                    #if pseudoMarker in ('it','bk','ca','nd',): # Character markers to be closed -- had to remove ft and xt from this list for complex footnotes with f fr fq ft fq ft f*
                    if pseudoMarker in allCharMarkers: # Character markers to be closed
                        #if (USFM[-2]=='\\' or USFM[-3]=='\\') and USFM[-1]!=' ':
                        if USFM[-1] != ' ':
                            USFM += ' ' # Separate markers by a space e.g., \p\bk Revelation
                            if Globals.debugFlag: print( "toTheWord: Added space to '{}' before '{}'".format( USFM[-2], pseudoMarker ) )
                        adjValue += '\\{}*'.format( pseudoMarker ) # Do a close marker
                    elif pseudoMarker in ('f','x',): inField = pseudoMarker # Remember these so we can close them later
                    elif pseudoMarker in ('fr','fq','ft','xo',): USFM += '' # These go on the same line just separated by spaces and don't get closed
                    elif USFM: USFM += '\n' # paragraph markers go on a new line
                    if not value: USFM += '\\{}'.format( pseudoMarker )
                    else: USFM += '\\{} {}'.format( pseudoMarker,adjValue )
                #print( pseudoMarker, USFM[-200:] )

            # Write the USFM output
            #print( "\nUSFM", USFM[:3000] )
            filename = "{}{}BWr.SFM".format( USFMNumber, USFMAbbreviation.upper() ) # This seems to be the undocumented standard filename format (and BWr = BibleWriter)
            #if not os.path.exists( USFMOutputFolder ): os.makedirs( USFMOutputFolder )
            filepath = os.path.join( outputFolder, filename )
            if Globals.verbosityLevel > 2: print( "  " + _("Writing '{}'...").format( filepath ) )
            with open( filepath, 'wt' ) as myFile: myFile.write( USFM )
        return True
    # end of BibleWriter.toTheWord


    def toMediaWiki( self, outputFolder=None, controlDict=None, validationSchema=None ):
        """
        Using settings from the given control file,
            converts the USFM information to a Media Wiki file.
        """
        if Globals.verbosityLevel > 1: print( "Running BibleWriter:toMediaWiki..." )
        if Globals.debugFlag: assert( self.books )

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolder: outputFolder = "OutputFiles/BOS_MediaWikiExport/"
        if not os.access( outputFolder, os.F_OK ): os.makedirs( outputFolder ) # Make the empty folder if there wasn't already one there
        if not controlDict:
            controlDict, defaultControlFilename = {}, "To_MediaWiki_controls.txt"
            try:
                ControlFiles.readControlFile( defaultControlFolder, defaultControlFilename, controlDict )
            except:
                logging.critical( "Unable to read control dict {} from {}".format( defaultControlFilename, defaultControlFolder ) )
        if Globals.debugFlag: assert( controlDict and isinstance( controlDict, dict ) )

        unhandledMarkers = set()

        bookAbbrevDict, bookNameDict, bookAbbrevNameDict = {}, {}, {}
        for BBB in Globals.BibleBooksCodes.getAllReferenceAbbreviations(): # Pre-process the language booknames
            if BBB in controlDict and controlDict[BBB]:
                bits = controlDict[BBB].split(',')
                if len(bits)!=2: logging.error( _("toMediaWiki: Unrecognized language book abbreviation and name for {}: '{}'").format( BBB, controlDict[BBB] ) )
                bookAbbrev = bits[0].strip().replace('"','') # Remove outside whitespace then the double quote marks
                bookName = bits[1].strip().replace('"','') # Remove outside whitespace then the double quote marks
                bookAbbrevDict[bookAbbrev], bookNameDict[bookName], bookAbbrevNameDict[BBB] = BBB, BBB, (bookAbbrev,bookName,)
                if ' ' in bookAbbrev: bookAbbrevDict[bookAbbrev.replace(' ','',1)] = BBB # Duplicate entries without the first space (presumably between a number and a name like 1 Kings)
                if ' ' in bookName: bookNameDict[bookName.replace(' ','',1)] = BBB # Duplicate entries without the first space

        toWikiMediaGlobals = { "verseRef":'', "XRefNum":0, "FootnoteNum":0, "lastRef":'', "OneChapterOSISBookCodes":Globals.BibleBooksCodes.getOSISSingleChapterBooksList() } # These are our global variables

# TODO: Need to handle footnotes \f + \fr ref \fk key \ft text \f* 	becomes <ref><!--\fr ref \fk key \ft-->text</ref>
        def writeBook( writerObject, BBB, bkData ):
            """Writes a book to the MediaWiki writerObject."""

            def processXRefsAndFootnotes( verse, extras ):
                """Convert cross-references and footnotes and return the adjusted verse text."""

                def processXRef( USFMxref ):
                    """
                    Return the OSIS code for the processed cross-reference (xref).

                    NOTE: The parameter here already has the /x and /x* removed.

                    \\x - \\xo 2:2: \\xt Lib 19:9-10; Diy 24:19.\\xt*\\x* (Backslashes are shown doubled here)
                        gives
                    <note type="crossReference" n="1">2:2: <reference>Lib 19:9-10; Diy 24:19.</reference></note> (Crosswire -- invalid OSIS -- which then needs to be converted)
                    <note type="crossReference" osisRef="Ruth.2.2" osisID="Ruth.2.2!crossreference.1" n="-"><reference type="source" osisRef="Ruth.2.2">2:2: </reference><reference osisRef="-">Lib 19:9-10</reference>; <reference osisRef="Ruth.Diy.24!:19">Diy 24:19</reference>.</note> (Snowfall)
                    \\x - \\xo 3:5: a \\xt Rum 11:1; \\xo b \\xt Him 23:6; 26:5.\\xt*\\x* is more complex still.
                    """
                    nonlocal BBB
                    toWikiMediaGlobals["XRefNum"] += 1
                    OSISxref = '<note type="crossReference" osisRef="{}" osisID="{}!crossreference.{}">'.format( toWikiMediaGlobals["verseRef"], toWikiMediaGlobals["verseRef"], toWikiMediaGlobals["XRefNum"] )
                    for j,token in enumerate(USFMxref.split('\\')):
                        #print( "processXRef", j, "'"+token+"'", "from", '"'+USFMxref+'"' )
                        if j==0: # The first token (but the x has already been removed)
                            rest = token.strip()
                            if rest != '-': logging.warning( _("toMediaWiki: We got something else here other than hyphen (probably need to do something with it): {} '{}' from '{}'").format( chapterRef, token, text ) )
                        elif token.startswith('xo '): # xref reference follows
                            adjToken = token[3:].strip()
                            if adjToken.endswith(' a'): adjToken = adjToken[:-2] # Remove any 'a' suffix (occurs when a cross-reference has multiple (a and b) parts
                            if adjToken.endswith(':'): adjToken = adjToken[:-1] # Remove any final colon (this is a language dependent hack)
                            adjToken = getBookAbbreviationFunction(BBB) + ' ' + adjToken # Prepend the vernacular book abbreviation
                            osisRef = BRL.parseToOSIS( adjToken, toWikiMediaGlobals["verseRef"] )
                            if osisRef is not None:
                                OSISxref += '<reference type="source" osisRef="{}">{}</reference>'.format( osisRef,token[3:] )
                                if not BRL.containsReference( BBB, currentChapterNumberString, verseNumberString ):
                                    logging.error( _("toMediaWiki: Cross-reference at {} {}:{} seems to contain the wrong self-reference '{}'").format( BBB, currentChapterNumberString, verseNumberString, token ) )
                        elif token.startswith('xt '): # xref text follows
                            xrefText = token[3:]
                            finalPunct = ''
                            while xrefText[-1] in (' ,;.'): finalPunct = xrefText[-1] + finalPunct; xrefText = xrefText[:-1]
                            #adjString = xrefText[:-6] if xrefText.endswith( ' (LXX)' ) else xrefText # Sorry, this is a crude hack to avoid unnecessary error messages
                            osisRef = BRL.parseToOSIS( xrefText, toWikiMediaGlobals["verseRef"] )
                            if osisRef is not None:
                                OSISxref += '<reference type="source" osisRef="{}">{}</reference>'.format( osisRef, xrefText+finalPunct )
                        elif token.startswith('x '): # another whole xref entry follows
                            rest = token[2:].strip()
                            if rest != '-': logging.warning( _("toMediaWiki: We got something else here other than hyphen (probably need to do something with it): {} '{}' from '{}'").format( chapterRef, token, text ) )
                        elif token in ('xt*', 'x*'):
                            pass # We're being lazy here and not checking closing markers properly
                        else:
                            logging.warning( _("toMediaWiki: Unprocessed '{}' token in {} xref '{}'").format( token, toWikiMediaGlobals["verseRef"], USFMxref ) )
                    OSISxref += '</note>'
                    return OSISxref
                # end of processXRef

                def processFootnote( USFMfootnote ):
                    """
                    Return the OSIS code for the processed footnote.

                    NOTE: The parameter here already has the /f and /f* removed.

                    \\f + \\fr 1:20 \\ft Su ka kaluwasan te Nawumi ‘keupianan,’ piru ka kaluwasan te Mara ‘masakit se geyinawa.’\\f* (Backslashes are shown doubled here)
                        gives
                    <note n="1">1:20 Su ka kaluwasan te Nawumi ‘keupianan,’ piru ka kaluwasan te Mara ‘masakit se geyinawa.’</note> (Crosswire)
                    <note osisRef="Ruth.1.20" osisID="Ruth.1.20!footnote.1" n="+"><reference type="source" osisRef="Ruth.1.20">1:20 </reference>Su ka kaluwasan te Nawumi ‘keupianan,’ piru ka kaluwasan te Mara ‘masakit se geyinawa.’</note> (Snowfall)
                    """
                    toWikiMediaGlobals["FootnoteNum"] += 1
                    OSISfootnote = '<note osisRef="{}" osisID="{}!footnote.{}">'.format( toWikiMediaGlobals["verseRef"], toWikiMediaGlobals["verseRef"], toWikiMediaGlobals["FootnoteNum"] )
                    for j,token in enumerate(USFMfootnote.split('\\')):
                        #print( "processFootnote", j, token, USFMfootnote )
                        if j==0: continue # ignore the + for now
                        elif token.startswith('fr '): # footnote reference follows
                            adjToken = token[3:].strip()
                            if adjToken.endswith(':'): adjToken = adjToken[:-1] # Remove any final colon (this is a language dependent hack)
                            adjToken = getBookAbbreviationFunction(BBB) + ' ' + adjToken # Prepend the vernacular book abbreviation
                            osisRef = BRL.parseToOSIS( adjToken, toWikiMediaGlobals["verseRef"] )
                            if osisRef is not None:
                                OSISfootnote += '<reference osisRef="{}" type="source">{}</reference>'.format( osisRef, token[3:] )
                                if not BRL.containsReference( BBB, currentChapterNumberString, verseNumberString ):
                                    logging.error( _("toMediaWiki: Footnote at {} {}:{} seems to contain the wrong self-reference '{}'").format( BBB, currentChapterNumberString, verseNumberString, token ) )
                        elif token.startswith('ft '): # footnote text follows
                            OSISfootnote += token[3:]
                        elif token.startswith('fq ') or token.startswith('fqa '): # footnote quote follows -- NOTE: We also assume here that the next marker closes the fq field
                            OSISfootnote += '<catchWord>{}</catchWord>'.format( token[3:] ) # Note that the trailing space goes in the catchword here -- seems messy
                        elif token in ('ft*','ft* ','fq*','fq* ','fqa*','fqa* '):
                            pass # We're being lazy here and not checking closing markers properly
                        else:
                            logging.warning( _("toMediaWiki: Unprocessed '{}' token in {} footnote '{}'").format( token, toWikiMediaGlobals["verseRef"], USFMfootnote ) )
                    OSISfootnote += '</note>'
                    #print( '', OSISfootnote )
                    return OSISfootnote
                # end of processFootnote

                while '\\x ' in verse and '\\x*' in verse: # process cross-references (xrefs)
                    ix1 = verse.index('\\x ')
                    ix2 = verse.find('\\x* ') # Note the extra space here at the end
                    if ix2 == -1: # Didn't find it so must be no space after the asterisk
                        ix2 = verse.index('\\x*')
                        ix2b = ix2 + 3 # Where the xref ends
                        logging.warning( _("toMediaWiki: No space after xref entry in {}").format( toWikiMediaGlobals["verseRef"] ) )
                    else: ix2b = ix2 + 4
                    xref = verse[ix1+3:ix2]
                    osisXRef = processXRef( xref )
                    #print( osisXRef )
                    verse = verse[:ix1] + osisXRef + verse[ix2b:]
                while '\\f ' in verse and '\\f*' in verse: # process footnotes
                    ix1 = verse.index('\\f ')
                    ix2 = verse.find('\\f*')
#                    ix2 = verse.find('\\f* ') # Note the extra space here at the end -- doesn't always work if there's two footnotes within one verse!!!
#                    if ix2 == -1: # Didn't find it so must be no space after the asterisk
#                        ix2 = verse.index('\\f*')
#                        ix2b = ix2 + 3 # Where the footnote ends
#                        #logging.warning( 'toMediaWiki: No space after footnote entry in {}'.format(toWikiMediaGlobals["verseRef"] )
#                    else: ix2b = ix2 + 4
                    footnote = verse[ix1+3:ix2]
                    osisFootnote = processFootnote( footnote )
                    #print( osisFootnote )
                    verse = verse[:ix1] + osisFootnote + verse[ix2+3:]
#                    verse = verse[:ix1] + osisFootnote + verse[ix2b:]
                return verse
            # end of processXRefsAndFootnotes

            bookRef = Globals.BibleBooksCodes.getOSISAbbreviation( BBB ) # OSIS book name
            if bookRef is None:
                print( "Doesn't encode OSIS '{}' book yet".format( BBB ) )
                return
            bookName = None
            verseText = '' # Do we really need this?
            #chapterNumberString = None
            for marker,originalMarker,text,cleanText,extras in bkData._processedLines: # Process USFM lines
                #print( "toMediaWiki:writeBook", BBB, bookRef, bookName, marker, text, extras )
                if marker in ("id","h","mt1"):
                    writerObject.writeLineComment( '\\{} {}'.format( marker, text ) )
                    bookName = text # in case there's no toc2 entry later
                elif marker=="toc2":
                    bookName = text
                elif marker=="li":
                    # :<!-- \li -->text
                    writerObject.writeLineText( ":" )
                    writerObject.writeLineComment( '\\li' )
                    writerObject.writeLineText( text )
                elif marker=="c":
                    chapterNumberString = text
                    chapterRef = bookRef + '.' + chapterNumberString
                    # Bible:BookName_#
                    if bookName: writerObject.writeLineText( 'Bible:{}_{}'.format(bookName, chapterNumberString) )
                elif marker=="s1":
                    # === text ===
                    writerObject.writeLineText( '=== {} ==='.format(text) )
                elif marker=="r":
                    # <span class="srefs">text</span>
                    if text: writerObject.writeLineOpenClose( 'span', text, ('class','srefs') )
                elif marker=='p':
                    writerObject.writeNewLine( 2 );
                elif marker=='v':
                    #if not chapterNumberString: # some single chapter books don't have a chapter number marker in them
                    #    if Globals.debugFlag: assert( BBB in Globals.BibleBooksCodes.getSingleChapterBooksList() )
                    #    chapterNumberString = '1'
                    #    chapterRef = bookRef + '.' + chapterNumberString
                    verseNumberString = text # Gets written with in the v~ line
                    # <span id="chapter#_#"><sup>#</sup> text</span>
                    #writerObject.writeLineOpenClose( 'span', '<sup>{}</sup> {}'.format(verseNumberString,adjText), ('id',"chapter{}_{}".format(chapterNumberString, verseNumberString) ), noTextCheck=True )
                elif marker=='v~':
                    # TODO: We haven't stripped out character fields from within the verse -- not sure how MediaWiki handles them yet
                    if not text: # this is an empty (untranslated) verse
                        adjText = '- - -' # but we'll put in a filler
                    else: adjText = processXRefsAndFootnotes( text, extras )
                    # <span id="chapter#_#"><sup>#</sup> text</span>
                    writerObject.writeLineOpenClose( 'span', '<sup>{}</sup> {}'.format(verseNumberString,adjText), ('id',"chapter{}_{}".format(chapterNumberString, verseNumberString) ), noTextCheck=True )
                elif marker=="q1":
                    adjText = processXRefsAndFootnotes( verseText, extras )
                    writerObject.writeLineText( ':{}'.format(adjText, noTextCheck=True) ) # No check so it doesn't choke on embedded xref and footnote fields
                elif marker=="q2":
                    adjText = processXRefsAndFootnotes( verseText, extras )
                    writerObject.writeLineText( '::{}'.format(adjText, noTextCheck=True) )
                elif marker=='m': # Margin/Flush-left paragraph
                    adjText = processXRefsAndFootnotes( verseText, extras )
                    writerObject.writeLineText( '::{}'.format(adjText, noTextCheck=True) )
                else:
                    unhandledMarkers.add( marker )
        # end of toMediaWiki:writeBook

        # Set-up our Bible reference system
        if controlDict['PublicationCode'] == "GENERIC":
            BOS = self.genericBOS
            BRL = self.genericBRL
        else:
            BOS = BibleOrganizationalSystem( controlDict["PublicationCode"] )
            BRL = BibleReferenceList( BOS, BibleObject=None )

        if Globals.verbosityLevel > 1: print( _("Exporting to MediaWiki format...") )
        xw = MLWriter( controlDict["MediaWikiOutputFilename"], outputFolder )
        xw.setHumanReadable()
        xw.start()
        for BBB,bookData in self.books.items():
            writeBook( xw, BBB, bookData )
        xw.close()
        if unhandledMarkers:
            logging.warning( "toMediaWiki: Unhandled USFM markers were {}".format( unhandledMarkers ) )
            if Globals.verbosityLevel > 1:
                print( "  " + _("WARNING: Unhandled toMediaWiki USFM markers were {}").format( unhandledMarkers ) )
        if validationSchema: return xw.validate( validationSchema )
        return True
    # end of BibleWriter.toMediaWiki



    def toZefaniaXML( self, outputFolder=None, controlDict=None, validationSchema=None ):
        """
        Using settings from the given control file,
            converts the USFM information to a UTF-8 Zefania XML file.

        This format is roughly documented at http://de.wikipedia.org/wiki/Zefania_XML
            but more fields can be discovered by looking at downloaded files.
        """
        if Globals.verbosityLevel > 1: print( "Running BibleWriter:toZefaniaXML..." )
        if Globals.debugFlag: assert( self.books )

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolder: outputFolder = "OutputFiles/BOS_ZefaniaExport/"
        if not os.access( outputFolder, os.F_OK ): os.makedirs( outputFolder ) # Make the empty folder if there wasn't already one there
        if not controlDict:
            controlDict, defaultControlFilename = {}, "To_Zefania_controls.txt"
            try:
                ControlFiles.readControlFile( defaultControlFolder, defaultControlFilename, controlDict )
            except:
                logging.critical( "Unable to read control dict {} from {}".format( defaultControlFilename, defaultControlFolder ) )
        if Globals.debugFlag: assert( controlDict and isinstance( controlDict, dict ) )

        unhandledMarkers = set()

        def writeHeader( writerObject ):
            """Writes the Zefania header to the Zefania XML writerObject."""
            writerObject.writeLineOpen( 'INFORMATION' )
            if "ZefaniaTitle" in controlDict and controlDict["ZefaniaTitle"]: writerObject.writeLineOpenClose( 'title' , controlDict["ZefaniaTitle"] )
            if "ZefaniaSubject" in controlDict and controlDict["ZefaniaSubject"]: writerObject.writeLineOpenClose( 'subject', controlDict["ZefaniaSubject"] )
            if "ZefaniaDescription" in controlDict and controlDict["ZefaniaDescription"]: writerObject.writeLineOpenClose( 'description', controlDict["ZefaniaDescription"] )
            if "ZefaniaPublisher" in controlDict and controlDict["ZefaniaPublisher"]: writerObject.writeLineOpenClose( 'publisher', controlDict["ZefaniaPublisher"] )
            if "ZefaniaContributors" in controlDict and controlDict["ZefaniaContributors"]: writerObject.writeLineOpenClose( 'contributors', controlDict["ZefaniaContributors"] )
            if "ZefaniaIdentifier" in controlDict and controlDict["ZefaniaIdentifier"]: writerObject.writeLineOpenClose( 'identifier', controlDict["ZefaniaIdentifier"] )
            if "ZefaniaSource" in controlDict and controlDict["ZefaniaSource"]: writerObject.writeLineOpenClose( 'identifier', controlDict["ZefaniaSource"] )
            if "ZefaniaCoverage" in controlDict and controlDict["ZefaniaCoverage"]: writerObject.writeLineOpenClose( 'coverage', controlDict["ZefaniaCoverage"] )
            writerObject.writeLineOpenClose( 'format', 'Zefania XML Bible Markup Language' )
            writerObject.writeLineOpenClose( 'date', datetime.datetime.now().date().isoformat() )
            writerObject.writeLineOpenClose( 'creator', 'BibleWriter.py' )
            writerObject.writeLineOpenClose( 'type', 'bible text' )
            if "ZefaniaLanguage" in controlDict and controlDict["ZefaniaLanguage"]: writerObject.writeLineOpenClose( 'language', controlDict["ZefaniaLanguage"] )
            if "ZefaniaRights" in controlDict and controlDict["ZefaniaRights"]: writerObject.writeLineOpenClose( 'rights', controlDict["ZefaniaRights"] )
            writerObject.writeLineClose( 'INFORMATION' )
        # end of toZefaniaXML:writeHeader

        def writeBook( writerObject, BBB, bkData ):
            """Writes a book to the Zefania XML writerObject."""
            #print( 'BIBLEBOOK', [('bnumber',Globals.BibleBooksCodes.getReferenceNumber(BBB)), ('bname',Globals.BibleBooksCodes.getEnglishName_NR(BBB)), ('bsname',Globals.BibleBooksCodes.getOSISAbbreviation(BBB))] )
            OSISAbbrev = Globals.BibleBooksCodes.getOSISAbbreviation( BBB )
            if not OSISAbbrev:
                logging.error( "toZefania: Can't write {} Zefania book because no OSIS code available".format( BBB ) ); return
            writerObject.writeLineOpen( 'BIBLEBOOK', [('bnumber',Globals.BibleBooksCodes.getReferenceNumber(BBB)), ('bname',Globals.BibleBooksCodes.getEnglishName_NR(BBB)), ('bsname',OSISAbbrev)] )
            haveOpenChapter = False
            for marker,originalMarker,text,cleanText,extras in bkData._processedLines: # Process USFM lines
                if marker=="c":
                    if haveOpenChapter:
                        writerObject.writeLineClose ( 'CHAPTER' )
                    writerObject.writeLineOpen ( 'CHAPTER', ('cnumber',text) )
                    haveOpenChapter = True
                elif marker=='v':
                    #print( "Text '{}'".format( text ) )
                    if not text: logging.warning( "toZefaniaXML: Missing text for v" ); continue
                    verseNumberString = text.replace('<','').replace('>','').replace('"','') # Used below but remove anything that'll cause a big XML problem later
                    #writerObject.writeLineOpenClose ( 'VERS', verseText, ('vnumber',verseNumberString) )
                elif marker=='v~':
                    #print( "Text '{}'".format( text ) )
                    if not text: logging.warning( "toZefaniaXML: Missing text for v~" ); continue
                    # TODO: We haven't stripped out character fields from within the verse -- not sure how Zefania handles them yet
                    if not text: # this is an empty (untranslated) verse
                        text = '- - -' # but we'll put in a filler
                    writerObject.writeLineOpenClose ( 'VERS', text, ('vnumber',verseNumberString) )
                else: unhandledMarkers.add( marker )
            if haveOpenChapter:
                writerObject.writeLineClose( 'CHAPTER' )
            writerObject.writeLineClose( 'BIBLEBOOK' )
        # end of toZefaniaXML:writeBook

        # Set-up our Bible reference system
        if controlDict['PublicationCode'] == "GENERIC":
            BOS = self.genericBOS
            BRL = self.genericBRL
        else:
            BOS = BibleOrganizationalSystem( controlDict["PublicationCode"] )
            BRL = BibleReferenceList( BOS, BibleObject=None )

        if Globals.verbosityLevel > 1: print( _("Exporting to Zefania format...") )
        xw = MLWriter( controlDict["ZefaniaOutputFilename"], outputFolder )
        xw.setHumanReadable()
        xw.start()
# TODO: Some modules have <XMLBIBLE xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="zef2005.xsd" version="2.0.1.18" status='v' revision="1" type="x-bible" biblename="KJV+">
        xw.writeLineOpen( 'XMLBible', [('xmlns:xsi',"http://www.w3.org/2001/XMLSchema-instance"), ('type',"x-bible"), ('biblename',controlDict["ZefaniaBibleName"]) ] )
        if True: #if controlDict["ZefaniaFiles"]=="byBible":
            writeHeader( xw )
            for BBB,bookData in self.books.items():
                writeBook( xw, BBB, bookData )
        xw.writeLineClose( 'XMLBible' )
        xw.close()
        if unhandledMarkers:
            logging.warning( "toZefania: Unhandled USFM markers were {}".format( unhandledMarkers ) )
            if Globals.verbosityLevel > 1:
                print( "  " + _("WARNING: Unhandled toZefania USFM markers were {}").format( unhandledMarkers ) )
        if validationSchema: return xw.validate( validationSchema )
        return True
    # end of BibleWriter.toZefaniaXML



    def toUSXXML( self, outputFolder=None, controlDict=None, validationSchema=None ):
        """
        Using settings from the given control file,
            converts the USFM information to UTF-8 USX XML files.

        If a schema is given (either a path or URL), the XML output files are validated.
        """
        if Globals.verbosityLevel > 1: print( "Running BibleWriter:toUSXXML..." )
        if Globals.debugFlag: assert( self.books )

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolder: outputFolder = "OutputFiles/BOS_USXExport/"
        if not os.access( outputFolder, os.F_OK ): os.makedirs( outputFolder ) # Make the empty folder if there wasn't already one there
        if not controlDict:
            controlDict, defaultControlFilename = {}, "To_USX_controls.txt"
            try:
                ControlFiles.readControlFile( defaultControlFolder, defaultControlFilename, controlDict )
            except:
                logging.critical( "Unable to read control dict {} from {}".format( defaultControlFilename, defaultControlFolder ) )
        if Globals.debugFlag: assert( controlDict and isinstance( controlDict, dict ) )

        unhandledMarkers = set()
        allCharMarkers = Globals.USFMMarkers.getCharacterMarkersList( expandNumberableMarkers=True )
        #print( allCharMarkers ); halt

        def writeBook( BBB, bkData ):
            """ Writes a book to the USX XML writerObject. """

            def handleInternalTextMarkersForUSX( originalText ):
                """
                Handles character formatting markers within the originalText.
                Tries to find pairs of markers and replaces them with html char segments.
                """
                if '\\' not in originalText: return originalText
                print( "toUSXXML:hITM4USX:", BBB, c, v, marker, "'"+originalText+"'" )
                markerList = sorted( Globals.USFMMarkers.getMarkerListFromText( originalText ),
                                            key=lambda s: -len(s[4])) # Sort by longest characterContext first (maximum nesting)
                for insideMarker, iMIndex, nextSignificantChar, fullMarker, characterContext, endIndex, markerField in markerList: # check for internal markers
                    pass
                # Old code
                adjText = originalText
                haveOpenChar = False
                for charMarker in allCharMarkers:
                    # Handle USFM character markers
                    fullCharMarker = '\\' + charMarker + ' '
                    if fullCharMarker in adjText:
                        if haveOpenChar:
                            adjText = adjText.replace( 'CLOSED_BIT', ' closed="false"' ) # Fix up closed bit since it wasn't closed
                            logging.info( "toUSXXML: USX export had to close automatically in {} {}:{} {}:'{}' now '{}'".format( BBB, c, v, marker, originalText, adjText ) ) # The last marker presumably only had optional closing (or else we just messed up nesting markers)
                        adjText = adjText.replace( fullCharMarker, '{}<char style="{}"CLOSED_BIT>'.format( '</char>' if haveOpenChar else '', charMarker ) )
                        haveOpenChar = True
                    endCharMarker = '\\' + charMarker + '*'
                    if endCharMarker in adjText:
                        if not haveOpenChar: # Then we must have a missing open marker (or extra closing marker)
                            logging.error( "toUSXXML: Ignored extra '{}' closing marker in {} {}:{} {}:'{}' now '{}'".format( charMarker, BBB, c, v, marker, originalText, adjText ) )
                            adjText = adjText.replace( endCharMarker, '' ) # Remove the unused marker
                        else: # looks good
                            adjText = adjText.replace( 'CLOSED_BIT', '' ) # Fix up closed bit since it was specifically closed
                            adjText = adjText.replace( endCharMarker, '</char>' )
                            haveOpenChar = False
                if haveOpenChar:
                    adjText = adjText.replace( 'CLOSED_BIT', ' closed="false"' ) # Fix up closed bit since it wasn't closed
                    adjText += '{}</char>'.format( '' if adjText[-1]==' ' else ' ')
                    logging.info( "toUSXXML: Had to close automatically in {} {}:{} {}:'{}' now '{}'".format( BBB, c, v, marker, originalText, adjText ) )
                if '\\' in adjText: logging.critical( "toUSXXML: Didn't handle a backslash in {} {}:{} {}:'{}' now '{}'".format( BBB, c, v, marker, originalText, adjText ) )
                return adjText
            # end of toUSXXML.handleInternalTextMarkersForUSX

            def handleNotes( text, extras ):
                """ Integrate notes into the text again. """

                def processXRef( USXxref ):
                    """
                    Return the USX XML for the processed cross-reference (xref).

                    NOTE: The parameter here already has the /x and /x* removed.

                    \\x - \\xo 2:2: \\xt Lib 19:9-10; Diy 24:19.\\xt*\\x* (Backslashes are shown doubled here)
                        gives
                    <note style="x" caller="-"><char style="xo" closed="false">1:3: </char><char style="xt">2Kur 4:6.</char></note>
                    """
                    USXxrefXML = '<note ' if version>=2 else '<note style="x" '
                    xoOpen = xtOpen = False
                    for j,token in enumerate(USXxref.split('\\')):
                        #print( "toUSXXML:processXRef", j, "'"+token+"'", "from", '"'+USXxref+'"', xoOpen, xtOpen )
                        lcToken = token.lower()
                        if j==0: # The first token (but the x has already been removed)
                            USXxrefXML += ('caller="{}" style="x">' if version>=2 else 'caller="{}">') \
                                .format( token.rstrip() )
                        elif lcToken.startswith('xo '): # xref reference follows
                            if xoOpen: # We have multiple xo fields one after the other (probably an encoding error)
                                if Globals.debugFlag: assert( not xtOpen )
                                USXxrefXML += ' closed="false">' + adjToken + '</char>'
                                xoOpen = False
                            if xtOpen: # if we have multiple cross-references one after the other
                                USXxrefXML += ' closed="false">' + adjToken + '</char>'
                                xtOpen = False
                            adjToken = token[3:]
                            USXxrefXML += '<char style="xo"'
                            xoOpen = True
                        elif lcToken.startswith('xo*'):
                            if Globals.debugFlag: assert( xoOpen and not xtOpen )
                            USXxrefXML += '>' + adjToken + '</char>'
                            xoOpen = False
                        elif lcToken.startswith('xt '): # xref text follows
                            if xtOpen: # Multiple xt's in a row
                                if Globals.debugFlag: assert( not xoOpen )
                                USXxrefXML += ' closed="false">' + adjToken + '</char>'
                            if xoOpen:
                                USXxrefXML += ' closed="false">' + adjToken + '</char>'
                                xoOpen = False
                            adjToken = token[3:]
                            USXxrefXML += '<char style="xt"'
                            xtOpen = True
                        elif lcToken.startswith('xt*'):
                            if Globals.debugFlag: assert( xtOpen and not xoOpen )
                            USXxrefXML += '>' + adjToken + '</char>'
                            xtOpen = False
                        #elif lcToken in ('xo*','xt*','x*',):
                        #    pass # We're being lazy here and not checking closing markers properly
                        else:
                            logging.warning( _("toUSXXML: Unprocessed '{}' token in {} {}:{} xref '{}'").format( token, BBB, c, v, USXxref ) )
                    if xoOpen:
                        if Globals.debugFlag: assert( not xtOpen )
                        USXxrefXML += ' closed="false">' + adjToken + '</char>'
                        xoOpen = False
                    if xtOpen:
                        USXxrefXML += ' closed="false">' + adjToken + '</char>'
                    USXxrefXML += '</note>'
                    return USXxrefXML
                # end of toUSXXML.processXRef

                def processFootnote( USXfootnote ):
                    """
                    Return the USX XML for the processed footnote.

                    NOTE: The parameter here already has the /f and /f* removed.

                    \\f + \\fr 1:20 \\ft Su ka kaluwasan te Nawumi ‘keupianan,’ piru ka kaluwasan te Mara ‘masakit se geyinawa.’\\f* (Backslashes are shown doubled here)
                        gives
                    <note style="f" caller="+"><char style="fr" closed="false">2:23 </char><char style="ft">Te Hibruwanen: bayew egpekegsahid ka ngaran te “malitan” wey “lukes.”</char></note>
                    """
                    USXfootnoteXML = '<note style="f" '
                    frOpen = fTextOpen = fCharOpen = False
                    for j,token in enumerate(USXfootnote.split('\\')):
                        #print( "USX processFootnote", j, "'"+token+"'", frOpen, fTextOpen, fCharOpen, USXfootnote )
                        lcToken = token.lower()
                        if j==0:
                            USXfootnoteXML += 'caller="{}">'.format( token.rstrip() )
                        elif lcToken.startswith('fr '): # footnote reference follows
                            if frOpen:
                                if Globals.debugFlag: assert( not fTextOpen )
                                logging.error( _("toUSXXML: Two consecutive fr fields in {} {}:{} footnote '{}'").format( token, BBB, c, v, USXfootnote ) )
                            if fTextOpen:
                                if Globals.debugFlag: assert( not frOpen )
                                USXfootnoteXML += ' closed="false">' + adjToken + '</char>'
                                fTextOpen = False
                            if Globals.debugFlag: assert( not fCharOpen )
                            adjToken = token[3:]
                            USXfootnoteXML += '<char style="fr"'
                            frOpen = True
                        elif lcToken.startswith('fr* '):
                            if Globals.debugFlag: assert( frOpen and not fTextOpen and not fCharOpen )
                            USXfootnoteXML += '>' + adjToken + '</char>'
                            frOpen = False
                        elif lcToken.startswith('ft ') or lcToken.startswith('fq ') or lcToken.startswith('fqa ') or lcToken.startswith('fv ') or lcToken.startswith('fk '):
                            if fCharOpen:
                                if Globals.debugFlag: assert( not frOpen )
                                USXfootnoteXML += '>' + adjToken + '</char>'
                                fCharOpen = False
                            if frOpen:
                                if Globals.debugFlag: assert( not fTextOpen )
                                USXfootnoteXML += ' closed="false">' + adjToken + '</char>'
                                frOpen = False
                            if fTextOpen:
                                USXfootnoteXML += ' closed="false">' + adjToken + '</char>'
                                fTextOpen = False
                            fMarker = lcToken.split()[0] # Get the bit before the space
                            USXfootnoteXML += '<char style="{}"'.format( fMarker )
                            adjToken = token[len(fMarker)+1:] # Get the bit after the space
                            #print( "'{}' '{}'".format( fMarker, adjToken ) )
                            fTextOpen = True
                        elif lcToken.startswith('ft*') or lcToken.startswith('fq*') or lcToken.startswith('fqa*') or lcToken.startswith('fv*') or lcToken.startswith('fk*'):
                            if Globals.debugFlag: assert( fTextOpen and not frOpen and not fCharOpen )
                            USXfootnoteXML += '>' + adjToken + '</char>'
                            fTextOpen = False
                        else: # Could be character formatting (or closing of character formatting)
                            subTokens = lcToken.split()
                            firstToken = subTokens[0]
                            #print( "ft", firstToken )
                            if firstToken in allCharMarkers: # Yes, confirmed
                                if fCharOpen: # assume that the last one is closed by this one
                                    if Globals.debugFlag: assert( not frOpen )
                                    USXfootnoteXML += '>' + adjToken + '</char>'
                                    fCharOpen = False
                                if frOpen:
                                    if Globals.debugFlag: assert( not fCharOpen )
                                    USXfootnoteXML += ' closed="false">' + adjToken + '</char>'
                                    frOpen = False
                                USXfootnoteXML += '<char style="{}"'.format( firstToken )
                                adjToken = token[len(firstToken)+1:] # Get the bit after the space
                                fCharOpen = firstToken
                            else: # The problem is that a closing marker doesn't have to be followed by a space
                                if firstToken[-1]=='*' and firstToken[:-1] in allCharMarkers: # it's a closing tag (that was followed by a space)
                                    if fCharOpen:
                                        if Globals.debugFlag: assert( not frOpen )
                                        if not firstToken.startswith( fCharOpen+'*' ): # It's not a matching tag
                                            logging.warning( _("toUSXXML: '{}' closing tag doesn't match '{}' in {} {}:{} footnote '{}'").format( firstToken, fCharOpen, BBB, c, v, USXfootnote ) )
                                        USXfootnoteXML += '>' + adjToken + '</char>'
                                        fCharOpen = False
                                    logging.warning( _("toUSXXML: '{}' closing tag doesn't match in {} {}:{} footnote '{}'").format( firstToken, BBB, c, v, USXfootnote ) )
                                else:
                                    ixAS = firstToken.find( '*' )
                                    #print( firstToken, ixAS, firstToken[:ixAS] if ixAS!=-1 else '' )
                                    if ixAS!=-1 and ixAS<4 and firstToken[:ixAS] in allCharMarkers: # it's a closing tag
                                        if fCharOpen:
                                            if Globals.debugFlag: assert( not frOpen )
                                            if not firstToken.startswith( fCharOpen+'*' ): # It's not a matching tag
                                                logging.warning( _("toUSXXML: '{}' closing tag doesn't match '{}' in {} {}:{} footnote '{}'").format( firstToken, fCharOpen, BBB, c, v, USXfootnote ) )
                                            USXfootnoteXML += '>' + adjToken + '</char>'
                                            fCharOpen = False
                                        logging.warning( _("toUSXXML: '{}' closing tag doesn't match in {} {}:{} footnote '{}'").format( firstToken, BBB, c, v, USXfootnote ) )
                                    else:
                                        logging.warning( _("toUSXXML: Unprocessed '{}' token in {} {}:{} footnote '{}'").format( firstToken, BBB, c, v, USXfootnote ) )
                                        #print( allCharMarkers )
                                        #halt
                    #print( "  ", frOpen, fCharOpen, fTextOpen )
                    if frOpen:
                        logging.warning( _("toUSXXML: Unclosed 'fr' token in {} {}:{} footnote '{}'").format( BBB, c, v, USXfootnote) )
                        if Globals.debugFlag: assert( not fCharOpen and not fTextOpen )
                        USXfootnoteXML += ' closed="false">' + adjToken + '</char>'
                    if fCharOpen: logging.warning( _("toUSXXML: Unclosed '{}' token in {} {}:{} footnote '{}'").format( fCharOpen, BBB, c, v, USXfootnote) )
                    if fTextOpen: USXfootnoteXML += ' closed="false">' + adjToken + '</char>'
                    USXfootnoteXML += '</note>'
                    #print( '', USXfootnote, USXfootnoteXML )
                    #if BBB=='EXO' and c=='17' and v=='7': halt
                    return USXfootnoteXML
                # end of toUSXXML.processFootnote


                adjText = text
                offset = 0
                for extraType, extraIndex, extraText, cleanExtraText in extras: # do any footnotes and cross-references
                    #print( "{} {}:{} Text='{}' eT={}, eI={}, eText='{}'".format( BBB, c, v, text, extraType, extraIndex, extraText ) )
                    adjIndex = extraIndex - offset
                    lenT = len( adjText )
                    if adjIndex > lenT: # This can happen if we have verse/space/notes at end (and the space was deleted after the note was separated off)
                        logging.warning( _("toUSXXML: Space before note at end of verse in {} {}:{} has been lost").format( BBB, c, v ) )
                        # No need to adjust adjIndex because the code below still works
                    elif adjIndex<0 or adjIndex>lenT: # The extras don't appear to fit correctly inside the text
                        print( "toUSXXML: Extras don't fit inside verse at {} {}:{}: eI={} o={} len={} aI={}".format( BBB, c, v, extraIndex, offset, len(text), adjIndex ) )
                        print( "  Verse='{}'".format( text ) )
                        print( "  Extras='{}'".format( extras ) )
                    #assert( 0 <= adjIndex <= len(verse) )
                    #adjText = checkText( extraText, checkLeftovers=False ) # do any general character formatting
                    #if adjText!=extraText: print( "processXRefsAndFootnotes: {}@{}-{}={} '{}' now '{}'".format( extraType, extraIndex, offset, adjIndex, extraText, adjText ) )
                    if extraType == 'fn':
                        extra = processFootnote( extraText )
                        #print( "fn got", extra )
                    elif extraType == 'xr':
                        extra = processXRef( extraText )
                        #print( "xr got", extra )
                    else: print( extraType ); halt
                    #print( "was", verse )
                    adjText = adjText[:adjIndex] + extra + adjText[adjIndex:]
                    offset -= len( extra )
                    #print( "now", verse )
                return adjText
            # end of handleNotes

            USXAbbrev = Globals.BibleBooksCodes.getUSFMAbbreviation( BBB ).upper()
            USXNumber = Globals.BibleBooksCodes.getUSXNumber( BBB )
            if not USXAbbrev: logging.error( "toUSXXML: Can't write {} USX book because no USFM code available".format( BBB ) ); return
            if not USXNumber: logging.error( "toUSXXML: Can't write {} USX book because no USX number available".format( BBB ) ); return

            version = 2
            xtra = ' ' if version<2 else ''
            c = v = '0'
            xw = MLWriter( USXNumber+USXAbbrev+".usx", outputFolder )
            xw.setHumanReadable()
            xw.spaceBeforeSelfcloseTag = True
            xw.start( lineEndings='w', writeBOM=True ) # Try to imitate Paratext output as closely as possible
            xw.writeLineOpen( 'usx', ('version','2.0') ) if version>=2 else xw.writeLineOpen( 'usx' )
            haveOpenPara = paraJustOpened = False
            for marker,originalMarker,text,cleanText,extras in bkData._processedLines: # Process USFM lines
                markerShouldHaveContent = Globals.USFMMarkers.markerShouldHaveContent( marker )
                #print( BBB, c, v, marker, markerShouldHaveContent, haveOpenPara, paraJustOpened )
                adjText = handleNotes( text, extras )
                if marker == 'id':
                    if haveOpenPara: # This should never happen coz the ID line should have been the first line in the file
                        logging.error( "toUSXXML: Book {}{} has a id line inside an open paragraph: '{}'".format( BBB, " ({})".format(USXAbbrev) if USXAbbrev!=BBB else '', adjText ) )
                        xw.removeFinalNewline( True )
                        xw.writeLineClose( 'para' )
                        haveOpenPara = False
                    adjTxLen = len( adjText )
                    if adjTxLen<3 or (adjTxLen>3 and adjText[3]!=' '): # Doesn't seem to have a standard BBB at the beginning of the ID line
                        logging.warning( "toUSXXML: Book {}{} has a non-standard id line: '{}'".format( BBB, " ({})".format(USXAbbrev) if USXAbbrev!=BBB else '', adjText ) )
                    if adjText[0:3] != USXAbbrev:
                        logging.error( "toUSXXML: Book {}{} might be incorrect -- we got: '{}'".format( BBB, " ({})".format(USXAbbrev) if USXAbbrev!=BBB else '', adjText[0:3] ) )
                    adjText = adjText[4:] # Remove the book code from the ID line because it's put in as an attribute
                    if adjText: xw.writeLineOpenClose( 'book', handleInternalTextMarkersForUSX(adjText)+xtra, [('code',USXAbbrev),('style',marker)] )
                    elif not text: logging.error( "toUSXXML: {} {}:{} has a blank id line that was ignored".format( BBB, c, v ) )
                elif marker == 'c':
                    if haveOpenPara:
                        xw.removeFinalNewline( True )
                        xw.writeLineClose( 'para' )
                        haveOpenPara = False
                    c = adjText
                    #print( 'c', c )
                    xw.writeLineOpenSelfclose ( 'chapter', [('number',c),('style','c')] )
                elif marker == 'c~': # Don't really know what this stuff is!!!
                    if not adjText: logging.warning( "toUSXXML: Missing text for c~" ); continue
                    # TODO: We haven't stripped out character fields from within the text -- not sure how USX handles them yet
                    xw.removeFinalNewline( True )
                    xw.writeLineText( handleInternalTextMarkersForUSX(adjText)+xtra, noTextCheck=True ) # no checks coz might already have embedded XML
                elif marker == 'c#': # Chapter number added for printing
                    pass # Just ignore it completely
                elif marker == 'v':
                    v = adjText.replace('<','').replace('>','').replace('"','') # Used below but remove anything that'll cause a big XML problem later
                    if paraJustOpened: paraJustOpened = False
                    else:
                        xw.removeFinalNewline( True )
                        if version>=2: xw._writeToBuffer( ' ' ) # Space between verses
                    xw.writeLineOpenSelfclose ( 'verse', [('number',v),('style','v')] )
                elif marker == 'v~':
                    if not adjText: logging.warning( "toUSXXML: Missing text for v~" ); continue
                    # TODO: We haven't stripped out character fields from within the verse -- not sure how USX handles them yet
                    xw.removeFinalNewline( True )
                    xw.writeLineText( handleInternalTextMarkersForUSX(adjText)+xtra, noTextCheck=True ) # no checks coz might already have embedded XML
                elif markerShouldHaveContent == 'N': # N = never, e.g., b, nb
                    if haveOpenPara:
                        xw.removeFinalNewline( True )
                        xw.writeLineClose( 'para' )
                        haveOpenPara = False
                    if adjText: logging.error( "toUSXXML: {} {}:{} has a {} line containing text ('{}') that was ignored".format( BBB, c, v, originalMarker, adjText ) )
                    xw.writeLineOpenSelfclose ( 'para', ('style',marker) )
                elif markerShouldHaveContent == 'S': # S = sometimes, e.g., p,pi,q,q1,q2,q3,q4,m
                    if haveOpenPara:
                        xw.removeFinalNewline( True )
                        xw.writeLineClose( 'para' )
                        haveOpenPara = False
                    if not adjText: xw.writeLineOpen( 'para', ('style',originalMarker) )
                    else: xw.writeLineOpenText( 'para', handleInternalTextMarkersForUSX(adjText)+xtra, ('style',originalMarker), noTextCheck=True ) # no checks coz might already have embedded XML
                    haveOpenPara = paraJustOpened = True
                else:
                    #assert( markerShouldHaveContent == 'A' ) # A = always, e.g.,  ide, mt, h, s, ip, etc.
                    if markerShouldHaveContent != 'A':
                        logging.debug( "BibleWriter.toUSXXML: ToProgrammer -- should be 'A': '{}' is '{}' Why?".format( marker, markerShouldHaveContent ) )
                    if haveOpenPara:
                        xw.removeFinalNewline( True )
                        xw.writeLineClose( 'para' )
                        haveOpenPara = False
                    if 1 or adjText: xw.writeLineOpenClose( 'para', handleInternalTextMarkersForUSX(adjText)+xtra, ('style',originalMarker), noTextCheck=True ) # no checks coz might already have embedded XML
                    else: logging.info( "toUSXXML: {} {}:{} has a blank {} line that was ignored".format( BBB, c, v, originalMarker ) )
            if haveOpenPara:
                xw.removeFinalNewline( True )
                xw.writeLineClose( 'para' )
            xw.writeLineClose( 'usx' )
            xw.close( writeFinalNL=True ) # Try to imitate Paratext output as closely as possible
            if validationSchema: return xw.validate( validationSchema )
        # end of toUSXXML.writeBook

        # Set-up our Bible reference system
        if controlDict['PublicationCode'] == "GENERIC":
            BOS = self.genericBOS
            BRL = self.genericBRL
        else:
            BOS = BibleOrganizationalSystem( controlDict["PublicationCode"] )
            BRL = BibleReferenceList( BOS, BibleObject=None )

        if Globals.verbosityLevel > 1: print( _("Exporting to USX format...") )
        #USXOutputFolder = os.path.join( "OutputFiles/", "USX output/" )
        #if not os.access( USXOutputFolder, os.F_OK ): os.mkdir( USXOutputFolder ) # Make the empty folder if there wasn't already one there

        validationResults = ( 0, '', '', ) # xmllint result code, program output, error output
        for BBB,bookData in self.books.items():
            bookResults = writeBook( BBB, bookData )
            if validationSchema:
                if bookResults[0] > validationResults[0]: validationResults = ( bookResults[0], validationResults[1], validationResults[2], )
                if bookResults[1]: validationResults = ( validationResults[0], validationResults[1] + bookResults[1], validationResults[2], )
                if bookResults[2]: validationResults = ( validationResults[0], validationResults[1], validationResults[2] + bookResults[2], )
        if unhandledMarkers:
            logging.warning( "toUSXXML: Unhandled USFM markers were {}".format( unhandledMarkers ) )
            if Globals.verbosityLevel > 1:
                print( "  " + _("WARNING: Unhandled toUSX USFM markers were {}").format( unhandledMarkers ) )
        if validationSchema: return validationResults
        return True
    # end of BibleWriter.toUSXXML



    def _writeSwordLocale( self, name, description, BibleOrganizationalSystem, getBookNameFunction, localeFilepath ):
        """
        Writes a UTF-8 Sword locale file containing the book names and abbreviations.
        """
        if Globals.verbosityLevel > 1: print( _("Writing Sword locale file {}...").format(localeFilepath) )

        with open( localeFilepath, 'wt' ) as SwLocFile:
            SwLocFile.write( '[Meta]\nName={}\n'.format( name ) )
            SwLocFile.write( 'Description={}\n'.format( description ) )
            SwLocFile.write( 'Encoding=UTF-8\n\n[Text]\n' )

            # This first section contains EnglishBookName=VernacularBookName
            bookList = []
            for BBB in BibleOrganizationalSystem.getBookList():
                if BBB in self.books:
                    vernacularName = getBookNameFunction(BBB)
                    SwLocFile.write( '{}={}\n'.format( Globals.BibleBooksCodes.getEnglishName_NR(BBB), vernacularName ) ) # Write the first English book name and the language book name
                    bookList.append( vernacularName )

            # This second section contains many VERNACULARABBREV=SwordBookAbbrev
            SwLocFile.write( '\n[Book Abbrevs]\n' )
            abbrevList = []
            for BBB in BibleOrganizationalSystem.getBookList(): # First pass writes the full vernacular book names (with and without spaces removed)
                if BBB in self.books:
                    swordAbbrev = Globals.BibleBooksCodes.getSwordAbbreviation( BBB )
                    vernacularName = getBookNameFunction(BBB).upper()
                    #assert( vernacularName not in abbrevList )
                    if vernacularName in abbrevList:
                        logging.debug( "BibleWriter._writeSwordLocale: ToProgrammer -- vernacular name IS in abbrevList -- what does this mean? Why? '{}' {}".format( vernacularName, abbrevList ) )
                    SwLocFile.write( '{}={}\n'.format( vernacularName, swordAbbrev ) ) # Write the UPPER CASE language book name and the Sword abbreviation
                    abbrevList.append( vernacularName )
                    if ' ' in vernacularName:
                        vernacularAbbrev = vernacularName.replace( ' ', '' )
                        if Globals.debugFlag: assert( vernacularAbbrev not in abbrevList )
                        SwLocFile.write( '{}={}\n'.format( vernacularAbbrev, swordAbbrev ) ) # Write the UPPER CASE language book name and the Sword abbreviation
                        abbrevList.append( vernacularAbbrev )
            for BBB in BibleOrganizationalSystem.getBookList(): # Second pass writes the shorter vernacular book abbreviations
                if BBB in self.books:
                    swordAbbrev = Globals.BibleBooksCodes.getSwordAbbreviation( BBB )
                    vernacularName = getBookNameFunction(BBB).replace( ' ', '' ).upper()
                    vernacularAbbrev = vernacularName
                    if len(vernacularName)>4  or (len(vernacularName)>3 and not vernacularName[0].isdigit):
                        vernacularAbbrev = vernacularName[:4 if vernacularName[0].isdigit() else 3]
                        if vernacularAbbrev in abbrevList:
                            if swordAbbrev == 'Philem':
                                vernacularAbbrev = vernacularName[:5]
                                if vernacularAbbrev not in abbrevList:
                                    SwLocFile.write( '{}={}\n'.format( vernacularAbbrev, swordAbbrev ) ) # Write the UPPER CASE language book name and the Sword abbreviation
                                    abbrevList.append( vernacularAbbrev )
                            else: logging.warning( "   Oops, shouldn't have written {} (also could be {}) to Sword locale file".format( vernacularAbbrev, swordAbbrev ) ) # Need to fix this
                        else:
                            SwLocFile.write( '{}={}\n'.format( vernacularAbbrev, swordAbbrev ) ) # Write the UPPER CASE language book name and the Sword abbreviation
                            abbrevList.append( vernacularAbbrev )
                    changed = False
                    for somePunct in ( ".''̉΄" ): # Remove punctuation and glottals (all UPPER CASE here)
                        if somePunct in vernacularAbbrev:
                            vernacularAbbrev = vernacularAbbrev.replace( somePunct, '' )
                            changed = True
                    if changed:
                        if vernacularAbbrev in abbrevList:
                            logging.warning( "   Oops, maybe shouldn't have written {} (also could be {}) to Sword locale file".format( vernacularAbbrev, swordAbbrev ) )
                        else:
                            SwLocFile.write( '{}={}\n'.format( vernacularAbbrev, swordAbbrev ) )
                            abbrevList.append( vernacularAbbrev )
                        changed = False
                    for vowel in ( 'AΆÁÂÃÄÅEÈÉÊËIÌÍÎÏOÒÓÔÕÖUÙÚÛÜ' ): # Remove vowels (all UPPER CASE here)
                        if vowel in vernacularAbbrev:
                            vernacularAbbrev = vernacularAbbrev.replace( vowel, '' )
                            changed = True
                    if changed:
                        if vernacularAbbrev in abbrevList:
                            logging.warning( "   Oops, maybe shouldn't have written {} (also could be {}) to Sword locale file".format( vernacularAbbrev, swordAbbrev ) )
                        else:
                            SwLocFile.write( '{}={}\n'.format( vernacularAbbrev, swordAbbrev ) )
                            abbrevList.append( vernacularAbbrev )

        if Globals.verbosityLevel > 1: print( _("  Wrote {} book names and {} abbreviations.").format( len(bookList), len(abbrevList) ) )
    # end of BibleWriter._writeSwordLocale



    def toOSISXML( self, outputFolder=None, controlDict=None, validationSchema=None ):
        """
        Using settings from the given control file,
            converts the USFM information to one or more UTF-8 OSIS XML files.

        If a schema is given (either a path or URL), the XML output file(s) is validated.

        TODO: We're not consistent about handling errors: sometimes we use assert, sometime raise (both of which abort the program), and sometimes log errors or warnings.
        """
        if Globals.verbosityLevel > 1: print( "Running BibleWriter:toOSISXML..." )
        if Globals.debugFlag: assert( self.books )

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolder: outputFolder = "OutputFiles/BOS_OSISExport/"
        if not os.access( outputFolder, os.F_OK ): os.makedirs( outputFolder ) # Make the empty folder if there wasn't already one there
        if not controlDict:
            controlDict, defaultControlFilename = {}, "To_OSIS_controls.txt"
            try:
                ControlFiles.readControlFile( defaultControlFolder, defaultControlFilename, controlDict )
            except:
                logging.critical( "Unable to read control dict {} from {}".format( defaultControlFilename, defaultControlFolder ) )
        if Globals.debugFlag: assert( controlDict and isinstance( controlDict, dict ) )

        # Set-up our Bible reference system
        #if Globals.debugFlag: print( "BibleWriter:toOSISXML publicationCode =", controlDict["PublicationCode"] )
        if controlDict['PublicationCode'] == "GENERIC":
            BOS = self.genericBOS
            BRL = self.genericBRL
        else:
            BOS = BibleOrganizationalSystem( controlDict["PublicationCode"] )
            BRL = BibleReferenceList( BOS, BibleObject=None )

        booksNamesSystemName = BOS.getOrganizationalSystemValue( 'booksNamesSystem' )
        if booksNamesSystemName and booksNamesSystemName!='None' and booksNamesSystemName!='Unknown': # default (if we know the book names system)
            getBookNameFunction = BOS.getBookName
            getBookAbbreviationFunction = BOS.getBookAbbreviation
        else: # else use our local functions from our deduced book names
            getBookNameFunction = self.getAssumedBookName # from USFMBible (which gets it from USFMBibleBook)
            getBookAbbreviationFunction = Globals.BibleBooksCodes.getOSISAbbreviation

        unhandledMarkers = set()

        # Let's write a Sword locale while we're at it -- might be useful if we make a Sword module from this OSIS file
        self._writeSwordLocale( controlDict["xmlLanguage"], controlDict["LanguageName"], BOS, getBookNameFunction, os.path.join( outputFolder, "SwLocale-utf8.conf" ) )
        #if Globals.verbosityLevel > 1: print( _("Writing Sword locale file {}...").format(SwLocFilepath) )
        #with open( SwLocFilepath, 'wt' ) as SwLocFile:
            #SwLocFile.write( '[Meta]\nName={}\n'.format(controlDict["xmlLanguage"]) )
            #SwLocFile.write( 'Description={}\n'.format(controlDict["LanguageName"]) )
            #SwLocFile.write( 'Encoding=UTF-8\n\n[Text]\n' )
            #for BBB in BOS.getBookList():
                #if BBB in self.books:
                    #SwLocFile.write( '{}={}\n'.format(Globals.BibleBooksCodes.getEnglishName_NR(BBB), getBookNameFunction(BBB) ) ) # Write the first English book name and the language book name
            #SwLocFile.write( '\n[Book Abbrevs]\n' )
            #for BBB in BOS.getBookList():
                #if BBB in self.books:
                    #SwLocFile.write( '{}={}\n'.format(Globals.BibleBooksCodes.getEnglishName_NR(BBB).upper(), Globals.BibleBooksCodes.getSwordAbbreviation(BBB) ) ) # Write the UPPER CASE language book name and the Sword abbreviation

        def writeHeader( writerObject ):
            """Writes the OSIS header to the OSIS XML writerObject."""
            writerObject.writeLineOpen( 'header' )
            writerObject.writeLineOpen( 'work', ('osisWork', controlDict["osisWork"]) )
            writerObject.writeLineOpenClose( 'title', controlDict["Title"] )
            writerObject.writeLineOpenClose( 'creator', "BibleWriter.py", ('role',"encoder") )
            writerObject.writeLineOpenClose( 'type',  "Bible", ('type',"OSIS") )
            writerObject.writeLineOpenClose( 'identifier', controlDict["Identifier"], ('type',"OSIS") )
            writerObject.writeLineOpenClose( 'scope', "dunno" )
            writerObject.writeLineOpenClose( 'refSystem', "Bible" )
            writerObject.writeLineClose( 'work' )
            # Snowfall software write two work entries ???
            writerObject.writeLineOpen( 'work', ('osisWork',"bible") )
            writerObject.writeLineOpenClose( 'creator', "BibleWriter.py", ('role',"encoder") )
            writerObject.writeLineOpenClose( 'type',  "Bible", ('type',"OSIS") )
            writerObject.writeLineOpenClose( 'refSystem', "Bible" )
            writerObject.writeLineClose( 'work' )
            writerObject.writeLineClose( 'header' )
        # end of toOSISXML:writeHeader

        toOSISGlobals = { "verseRef":'', "XRefNum":0, "FootnoteNum":0, "lastRef":'', "OneChapterOSISBookCodes":Globals.BibleBooksCodes.getOSISSingleChapterBooksList() } # These are our global variables


        def writeBook( writerObject, BBB, bkData ):
            """Writes a book to the OSIS XML writerObject.
            """

            def checkText( textToCheck, checkLeftovers=True ):
                """Handle some general backslash codes and warn about any others still unprocessed."""

                def checkTextHelper( marker, helpText ):
                    """ Adjust the text to make the number of start and close markers equal. """
                    count1, count2 = helpText.count('\\'+marker+' '), helpText.count('\\'+marker+'*') # count open and close markers
                    while count1 < count2:
                        helpText = '\\'+marker+' ' + helpText
                        count1, count2 = helpText.count('\\'+marker+' '), helpText.count('\\'+marker+'*') # count open and close markers again
                    while count1 > count2:
                        helpText += '\\'+marker+'*'
                        count1, count2 = helpText.count('\\'+marker+' '), helpText.count('\\'+marker+'*') # count open and close markers again
                    if Globals.debugFlag: assert( count1 == count2 )
                    return helpText
                # end of checkTextHelper

                adjText = textToCheck
                if '<<' in adjText or '>>' in adjText:
                    logging.warning( _("toOSIS: Unexpected double angle brackets in {}: '{}' field is '{}'").format( toOSISGlobals["verseRef"], marker, textToCheck ) )
                    adjText = adjText.replace('<<','“' ).replace('>>','”' )
                if '\\add ' in adjText: adjText = checkTextHelper('add',adjText).replace('\\add ','<i>').replace('\\add*','</i>') # temp XXXXXX ...
                if '\\sig ' in adjText: adjText = checkTextHelper('sig',adjText).replace('\\sig ','<signed>').replace('\\sig*','</signed>')
                if '\\bk ' in adjText: adjText = checkTextHelper('bk',adjText).replace('\\bk ','<reference type="x-bookName">').replace('\\bk*','</reference>')
                if '\\nd ' in adjText: adjText = checkTextHelper('nd',adjText).replace('\\nd ','<divineName>').replace('\\nd*','</divineName>')
                if '\\it ' in adjText: adjText = checkTextHelper('it',adjText).replace('\\it ','<hi type="italic">').replace('\\it*','</hi>')
                if '\\bd ' in adjText: adjText = checkTextHelper('bd',adjText).replace('\\bd ','<hi type="bold">').replace('\\bd*','</hi>')
                if '\\em ' in adjText: adjText = checkTextHelper('em',adjText).replace('\\em ','<hi type="bold">').replace('\\em*','</hi>')
                if '\\sc ' in adjText: adjText = checkTextHelper('sc',adjText).replace('\\sc ','<hi type="SMALLCAPS">').replace('\\sc*','</hi>') # XXXXXX temp ....
                if '\\wj ' in adjText: adjText = checkTextHelper('wj',adjText).replace('\\wj ','<hi type="bold">').replace('\\wj*','</hi>') # XXXXXX temp ....
                if '\\fig ' in adjText: # Figure is not used in Sword modules so we'll remove it from the OSIS (for now at least)
                    ix1 = adjText.find( '\\fig ' )
                    ix2 = adjText.find( '\\fig*' )
                    if ix2 == -1: print( _("toOSIS: Missing fig end marker for OSIS in {}: '{}' field is '{}'").format( toOSISGlobals["verseRef"], marker, textToCheck ), file=sys.stderr )
                    else:
                        if Globals.debugFlag: assert( ix2 > ix1 )
                        #print( "was '{}'".format( adjText ) )
                        adjText = adjText[:ix1] + adjText[ix2+5:] # Remove the \\fig..\\fig* field
                        #print( "now '{}'".format( adjText ) )
                        print( _("toOSIS: Figure reference removed for OSIS generation in {}: '{}' field").format( toOSISGlobals["verseRef"], marker ), file=sys.stderr )
                if checkLeftovers and '\\' in adjText:
                    logging.error( _("toOSIS: We still have some unprocessed backslashes for OSIS in {}: '{}' field is '{}'").format( toOSISGlobals["verseRef"], marker, textToCheck ) )
                    print( _("toOSIS: We still have some unprocessed backslashes for OSIS in {}: '{}' field is '{}'").format( toOSISGlobals["verseRef"], marker, textToCheck ), file=sys.stderr )
                    adjText = adjText.replace('\\','ENCODING ERROR HERE ' )
                return adjText
            # end of checkText

            def processXRefsAndFootnotes( verse, extras, offset=0 ):
                """Convert cross-references and footnotes and return the adjusted verse text."""

                def processXRef( USFMxref ):
                    """
                    Return the OSIS code for the processed cross-reference (xref).

                    NOTE: The parameter here already has the /x and /x* removed.

                    \\x - \\xo 2:2: \\xt Lib 19:9-10; Diy 24:19.\\xt*\\x* (Backslashes are shown doubled here)
                        gives
                    <note type="crossReference" n="1">2:2: <reference>Lib 19:9-10; Diy 24:19.</reference></note> (Crosswire -- invalid OSIS -- which then needs to be converted)
                    <note type="crossReference" osisRef="Ruth.2.2" osisID="Ruth.2.2!crossreference.1" n="-"><reference type="source" osisRef="Ruth.2.2">2:2: </reference><reference osisRef="-">Lib 19:9-10</reference>; <reference osisRef="Ruth.Diy.24!:19">Diy 24:19</reference>.</note> (Snowfall)
                    \\x - \\xo 3:5: a \\xt Rum 11:1; \\xo b \\xt Him 23:6; 26:5.\\xt*\\x* is more complex still.
                    """
                    #nonlocal BBB
                    toOSISGlobals["XRefNum"] += 1
                    OSISxref = '<note type="crossReference" osisRef="{}" osisID="{}!crossreference.{}">'.format( toOSISGlobals["verseRef"], toOSISGlobals["verseRef"], toOSISGlobals["XRefNum"] )
                    for j,token in enumerate(USFMxref.split('\\')):
                        #print( "toOSIS:processXRef", j, "'"+token+"'", "from", '"'+USFMxref+'"' )
                        lcToken = token.lower()
                        if j==0: # The first token (but the x has already been removed)
                            rest = token.strip()
                            if rest != '-': logging.warning( _("toOSIS: We got something else here other than hyphen (probably need to do something with it): {} '{}' from '{}'").format(chapterRef, token, text) )
                        elif lcToken.startswith('xo '): # xref reference follows
                            adjToken = token[3:].strip()
                            #print( "toOSIS:processXRef(xo)", j, "'"+token+"'", "'"+adjToken+"'", "from", '"'+USFMxref+'"' )
                            if j==1:
                                if len(adjToken)>2 and adjToken[-2]==' ' and adjToken[-1]=='a':
                                    suffixLetter = adjToken[-1]
                                    adjToken = adjToken[:-2] # Remove any suffix (occurs when a cross-reference has multiple (a and b) parts
                                if adjToken.endswith(':'): adjToken = adjToken[:-1] # Remove any final colon (this is a language dependent hack)
                                adjToken = getBookAbbreviationFunction(BBB) + ' ' + adjToken # Prepend a book abbreviation for the anchor (will be processed to an OSIS reference later)
                                selfReference = adjToken
                            else: # j > 1 -- this xo field may possibly only contain a letter suffix
                                if len(adjToken)==1 and adjToken in ('b','c','d','e','f','g','h',):
                                    adjToken = selfReference
                                else: # Could be another complete reference
                                    #print( "<<< Programming error here in toOSIS:processXRef for '{}' at {} {}:{}".format( USFMxref, BBB, currentChapterNumberString, verseNumberString )  )
                                    #print( "  '"+lcToken+"'", len(adjToken), "'"+adjToken+"'" )
                                    if len(adjToken)>2 and adjToken[-2]==' ' and adjToken[-1]=='a':
                                        suffixLetter = adjToken[-1]
                                        adjToken = adjToken[:-2] # Remove any suffix (occurs when a cross-reference has multiple (a and b) parts
                                    if adjToken.endswith(':'): adjToken = adjToken[:-1] # Remove any final colon (this is a language dependent hack)
                                    adjToken = getBookAbbreviationFunction(BBB) + ' ' + adjToken # Prepend a book abbreviation for the anchor (will be processed to an OSIS reference later)
                                    selfReference = adjToken
                            osisRef = BRL.parseToOSIS( adjToken, toOSISGlobals["verseRef"] )
                            if osisRef is not None:
                                #print( "  osisRef = {}".format( osisRef ) )
                                OSISxref += '<reference type="source" osisRef="{}">{}</reference>'.format(osisRef,token[3:])
                                if not BRL.containsReference( BBB, currentChapterNumberString, verseNumberString ):
                                    logging.error( _("toOSIS: Cross-reference at {} {}:{} seems to contain the wrong self-reference anchor '{}'").format(BBB,currentChapterNumberString,verseNumberString, token[3:].rstrip()) )
                        elif lcToken.startswith('xt '): # xref text follows
                            xrefText = token[3:]
                            finalPunct = ''
                            while xrefText[-1] in (' ,;.'): finalPunct = xrefText[-1] + finalPunct; xrefText = xrefText[:-1]
                            #adjString = xrefText[:-6] if xrefText.endswith( ' (LXX)' ) else xrefText # Sorry, this is a crude hack to avoid unnecessary error messages
                            osisRef = BRL.parseToOSIS( xrefText, toOSISGlobals["verseRef"] )
                            if osisRef is not None:
                                OSISxref += '<reference type="source" osisRef="{}">{}</reference>'.format(osisRef,xrefText+finalPunct)
                        elif lcToken.startswith('x '): # another whole xref entry follows
                            rest = token[2:].strip()
                            if rest != '-': logging.warning( _("toOSIS: We got something else here other than hyphen (probably need to do something with it): {} '{}' from '{}'").format(chapterRef, token, text) )
                        elif lcToken in ('xo*','xt*','x*',):
                            pass # We're being lazy here and not checking closing markers properly
                        else:
                            logging.warning( _("toOSIS: Unprocessed '{}' token in {} xref '{}'").format( token, toOSISGlobals["verseRef"], USFMxref ) )
                    OSISxref += '</note>'
                    return OSISxref
                # end of processXRef

                def processFootnote( USFMfootnote ):
                    """
                    Return the OSIS code for the processed footnote.

                    NOTE: The parameter here already has the /f and /f* removed.

                    \\f + \\fr 1:20 \\ft Su ka kaluwasan te Nawumi ‘keupianan,’ piru ka kaluwasan te Mara ‘masakit se geyinawa.’\\f* (Backslashes are shown doubled here)
                        gives
                    <note n="1">1:20 Su ka kaluwasan te Nawumi ‘keupianan,’ piru ka kaluwasan te Mara ‘masakit se geyinawa.’</note> (Crosswire)
                    <note osisRef="Ruth.1.20" osisID="Ruth.1.20!footnote.1" n="+"><reference type="source" osisRef="Ruth.1.20">1:20 </reference>Su ka kaluwasan te Nawumi ‘keupianan,’ piru ka kaluwasan te Mara ‘masakit se geyinawa.’</note> (Snowfall)
                    """
                    toOSISGlobals["FootnoteNum"] += 1
                    OSISfootnote = '<note osisRef="{}" osisID="{}!footnote.{}">'.format( toOSISGlobals["verseRef"], toOSISGlobals["verseRef"], toOSISGlobals["FootnoteNum"] )
                    for j,token in enumerate(USFMfootnote.split('\\')):
                        #print( "processFootnote", j, token, USFMfootnote )
                        lcToken = token.lower()
                        if j==0: continue # ignore the + for now
                        elif lcToken.startswith('fr '): # footnote reference follows
                            adjToken = token[3:].strip()
                            if adjToken.endswith(':'): adjToken = adjToken[:-1] # Remove any final colon (this is a language dependent hack)
                            adjToken = getBookAbbreviationFunction(BBB) + ' ' + adjToken # Prepend a book abbreviation for the anchor (will be processed to an OSIS reference later)
                            osisRef = BRL.parseToOSIS( adjToken, toOSISGlobals["verseRef"] ) # Note that this may return None
                            if osisRef is not None:
                                OSISfootnote += '<reference type="source" osisRef="{}">{}</reference>'.format(osisRef,token[3:])
                                if not BRL.containsReference( BBB, currentChapterNumberString, verseNumberString ):
                                    logging.error( _("toOSIS: Footnote at {} {}:{} seems to contain the wrong self-reference anchor '{}'").format(BBB,currentChapterNumberString,verseNumberString, token[3:].rstrip()) )
                        elif lcToken.startswith('ft ') or lcToken.startswith('fr* '): # footnote text follows
                            OSISfootnote += token[3:]
                        elif lcToken.startswith('fq ') or token.startswith('fqa '): # footnote quote follows -- NOTE: We also assume here that the next marker closes the fq field
                            OSISfootnote += '<catchWord>{}</catchWord>'.format(token[3:]) # Note that the trailing space goes in the catchword here -- seems messy
                        elif lcToken in ('fr*','fr* ','ft*','ft* ','fq*','fq* ','fqa*','fqa* ',):
                            pass # We're being lazy here and not checking closing markers properly
                        else:
                            logging.warning( _("toOSIS: Unprocessed '{}' token in {} footnote '{}'").format(token, toOSISGlobals["verseRef"], USFMfootnote) )
                    OSISfootnote += '</note>'
                    #print( '', OSISfootnote )
                    #if currentChapterNumberString=='5' and verseNumberString=='29': halt
                    return OSISfootnote
                # end of processFootnote

                #if extras: print( '\n', chapterRef )
                if Globals.debugFlag: assert( offset >= 0 )
                for extraType, extraIndex, extraText, cleanExtraText in extras: # do any footnotes and cross-references
                    adjIndex = extraIndex - offset
                    lenV = len( verse )
                    if adjIndex > lenV: # This can happen if we have verse/space/notes at end (and the space was deleted after the note was separated off)
                        logging.warning( _("toOSIS: Space before note at end of verse in {} has been lost").format( toOSISGlobals["verseRef"] ) )
                        # No need to adjust adjIndex because the code below still works
                    elif adjIndex<0 or adjIndex>lenV: # The extras don't appear to fit correctly inside the verse
                        print( "toOSIS: Extras don't fit inside verse at {}: eI={} o={} len={} aI={}".format( toOSISGlobals["verseRef"], extraIndex, offset, len(verse), adjIndex ) )
                        print( "  Verse='{}'".format( verse ) )
                        print( "  Extras='{}'".format( extras ) )
                    #assert( 0 <= adjIndex <= len(verse) )
                    adjText = checkText( extraText, checkLeftovers=False ) # do any general character formatting on the notes
                    #if adjText!=extraText: print( "processXRefsAndFootnotes: {}@{}-{}={} '{}' now '{}'".format( extraType, extraIndex, offset, adjIndex, extraText, adjText ) )
                    if extraType == 'fn':
                        extra = processFootnote( adjText )
                        #print( "fn got", extra )
                    elif extraType == 'xr':
                        extra = processXRef( adjText )
                        #print( "xr got", extra )
                    else: print( extraType ); halt
                    #print( "was", verse )
                    verse = verse[:adjIndex] + extra + verse[adjIndex:]
                    offset -= len( extra )
                    #print( "now", verse )
                return verse
            # end of processXRefsAndFootnotes

            def writeVerseStart( writerObject, BBB, chapterRef, verseNumberText ):
                """
                Processes and writes a verse milestone to the OSIS XML writerObject.
                    <verse sID="Gen.1.31" osisID="Gen.1.31"/>
                    Ne nakita te Manama ka langun ne innimu rin wey natelesan amana sikandin. Ne nasagkup e wey napawe, ne seeye ka igkeen-em ne aldew.
                    <verse eID="Gen.1.31"/>

                Has to handle joined verses, e.g.,
                    <verse sID="Esth.9.16" osisID="Esth.9.16 Esth.9.17"/>text<verse eID="Esth.9.16"/> (Crosswire)
                    <verse sID="Esth.9.16-Esth.9.17" osisID="Esth.9.16 Esth.9.17" n="16-17"/>text<verse eID="Esth.9.16-Esth.9.17"/> (Snowfall)
                """
                nonlocal haveOpenVsID
                if haveOpenVsID != False: # Close the previous verse
                    writerObject.writeLineOpenSelfclose( 'verse', ('eID',haveOpenVsID) )
                #verseNumberString = text.split()[0] # Get the first token which is the first number
                #offset = len(verseNumberString) + 1 # Add one for the following space
                ##while offset<len(text): # Remove any additional leading spaces (this can easily happen if verse initial xrefs are followed by an extra space)
                ##    if text[offset]==' ': offset += 1
                ##    else: break
                #verseText = text[offset:] # Get the rest of the string which is the verse text
                if '-' in verseNumberString:
                    bits = verseNumberString.split('-')
                    if len(bits)!=2 or not bits[0].isdigit() or not bits[1].isdigit(): logging.critical( _("toOSIS: Doesn't handle verse number of form '{}' yet for {}").format(verseNumberString,chapterRef) )
                    toOSISGlobals["verseRef"]  = chapterRef + '.' + bits[0]
                    verseRef2 = chapterRef + '.' + bits[1]
                    sID    = toOSISGlobals["verseRef"] + '-' + verseRef2
                    osisID = toOSISGlobals["verseRef"] + ' ' + verseRef2
                elif ',' in verseNumberString:
                    bits = verseNumberString.split(',')
                    if len(bits)<2 or not bits[0].isdigit() or not bits[1].isdigit(): logging.critical( _("toOSIS: Doesn't handle verse number of form '{}' yet for {}").format(verseNumberString,chapterRef) )
                    sID = toOSISGlobals["verseRef"] = chapterRef + '.' + bits[0]
                    osisID = ''
                    for bit in bits: # Separate the OSIS ids by spaces
                        osisID += ' ' if osisID else ''
                        osisID += chapterRef + '.' + bit
                    #print( "Hey comma verses '{}' '{}'".format( sID, osisID ) )
                elif verseNumberString.isdigit():
                    sID = osisID = toOSISGlobals["verseRef"] = chapterRef + '.' + verseNumberString
                else:
                    logging.critical( _("toOSIS: Doesn't handle verse number of form '{}' yet for {}").format(verseNumberString,chapterRef) )
                    tempID = toOSISGlobals["verseRef"] = chapterRef + '.' + verseNumberString # Try it anyway
                    sID = osisID = tempID.replace('<','').replace('>','').replace('"','') # But remove anything that'll cause a big XML problem later
                #print( "here SID='{}' osisID='{}'".format( sID, osisID ) )
                writerObject.writeLineOpenSelfclose( 'verse', [('sID',sID), ('osisID',osisID)] ); haveOpenVsID = sID
                #adjText = processXRefsAndFootnotes( verseText, extras, offset )
                #writerObject.writeLineText( checkText(adjText), noTextCheck=True )
                ##writerObject.writeLineOpenSelfclose( 'verse', ('eID',sID) )
            # end of writeVerseStart

            def closeAnyOpenMajorSection():
                """ Close a <div> if it's open. """
                nonlocal haveOpenMajorSection
                if haveOpenMajorSection:
                    writerObject.writeLineClose( 'div' )
                    haveOpenMajorSection = False
            # end of closeAnyOpenMajorSection

            def closeAnyOpenSection():
                """ Close a <div> if it's open. """
                nonlocal haveOpenL, haveOpenLG, haveOpenParagraph, haveOpenSubsection
                nonlocal haveOpenSection
                if haveOpenL:
                    logging.error( "toOSIS: closeAnyOpenSection: Why was L open at {}?".format( toOSISGlobals["verseRef"] ) )
                    writerObject.writeLineClose( 'l' )
                    haveOpenL = False
                if haveOpenLG:
                    logging.error( "toOSIS: closeAnyOpenSection: Why was LG open at {}?".format( toOSISGlobals["verseRef"] ) )
                    writerObject.writeLineClose( 'lg' )
                    haveOpenLG = False
                if haveOpenParagraph:
                    logging.error( "toOSIS: closeAnyOpenSection: Why was paragraph open at {}?".format( toOSISGlobals["verseRef"] ) )
                    writerObject.writeLineClose( 'p' )
                    haveOpenParagraph = False
                if haveOpenSubsection:
                    logging.error( "toOSIS: closeAnyOpenSection: Why was subsection open at {}?".format( toOSISGlobals["verseRef"] ) )
                    writerObject.writeLineClose( 'div' )
                    haveOpenSubsection = False
                if haveOpenSection:
                    writerObject.writeLineClose( 'div' )
                    haveOpenSection = False
            # end of closeAnyOpenSection

            def closeAnyOpenSubsection():
                """ Close a <div> if it's open. """
                nonlocal haveOpenSubsection
                if haveOpenSubsection:
                    writerObject.writeLineClose( 'div' )
                    haveOpenSubsection = False
            # end of closeAnyOpenSubsection

            def closeAnyOpenParagraph():
                """ Close a <p> if it's open. """
                nonlocal haveOpenParagraph
                if haveOpenParagraph:
                    writerObject.writeLineClose( 'p' )
                    haveOpenParagraph = False
            # end of closeAnyOpenParagraph

            def closeAnyOpenLG():
                """ Close a <lg> if it's open. """
                nonlocal haveOpenLG
                if haveOpenLG:
                    #print( "closeAnyOpenLG", toOSISGlobals["verseRef"] )
                    writerObject.writeLineClose( 'lg' )
                    haveOpenLG = False
            # end of closeAnyOpenLG

            def closeAnyOpenL():
                """ Close a <l> if it's open. """
                nonlocal haveOpenL
                if haveOpenL:
                    writerObject.writeLineClose( 'l' )
                    haveOpenL = False
            # end of closeAnyOpenL

            bookRef = Globals.BibleBooksCodes.getOSISAbbreviation( BBB ) # OSIS book name
            if not bookRef:
                logging.error( "toOSIS: Can't write {} OSIS book because no OSIS code available".format( BBB ) )
                return
            chapterRef = bookRef + '.0' # Not used by OSIS
            toOSISGlobals["verseRef"] = chapterRef + '.0' # Not used by OSIS
            writerObject.writeLineOpen( 'div', [('type',"book"), ('osisID',bookRef)] )
            haveOpenIntro = haveOpenOutline = haveOpenMajorSection = haveOpenSection = haveOpenSubsection = needChapterEID = haveOpenParagraph = haveOpenVsID = haveOpenLG = haveOpenL = False
            lastMarker = unprocessedMarker = ''
            for marker,originalMarker,text,cleanText,extras in bkData._processedLines: # Process USFM lines
                #print( "toOSIS:", marker, originalMarker, text )
                if marker in ( 'id', 'h1', 'mt2' ): continue # We just ignore these markers
                if marker=='mt1':
                    if text: writerObject.writeLineOpenClose( 'title', checkText(text) )
                elif marker=='is1' or marker=='imt1':
                    #print( marker, "'"+text+"'" )
                    if not haveOpenIntro:
                        writerObject.writeLineOpen( 'div', [('type',"introduction"),('canonical',"false")] )
                        haveOpenIntro = True
                    if text: writerObject.writeLineOpenClose( 'title', checkText(text) ) # Introduction heading
                    logging.error( _("toOSIS: {} Have a blank {} field—ignoring it").format( toOSISGlobals["verseRef"], marker ) )
                elif marker=='ip':
                    if not haveOpenIntro: # Shouldn't happen but we'll try our best
                        logging.error( _("toOSIS: {} Have an ip not in an introduction section—ignoring it").format( toOSISGlobals["verseRef"] ) )
                        writerObject.writeLineOpen( 'div', [('type',"introduction"),('canonical',"false")] )
                        haveOpenIntro = True
                    closeAnyOpenParagraph()
                    writerObject.writeLineOpenText( 'p', checkText(text), noTextCheck=True ) # Sometimes there's text
                    haveOpenParagraph = True
                elif marker=='iot':
                    if not haveOpenIntro: # Shouldn't happen but we'll try our best
                        logging.error( _("toOSIS: {} Have an iot not in an introduction section").format( toOSISGlobals["verseRef"] ) )
                        writerObject.writeLineOpen( 'div', [('type',"introduction"),('canonical',"false")] )
                        haveOpenIntro = True
                    if haveOpenSection or haveOpenOutline: logging.error( "toOSIS: Not handled yet iot in {} hOS={} hOO={}".format(BBB,haveOpenSection,haveOpenOutline) )
                    closeAnyOpenParagraph()
                    writerObject.writeLineOpen( 'div', ('type',"outline") )
                    if text: writerObject.writeLineOpenClose( 'title', checkText(text) )
                    writerObject.writeLineOpen( 'list' )
                    haveOpenOutline = True
                elif marker=='io1':
                    if not haveOpenIntro: # Shouldn't happen but we'll try our best
                        logging.error( _("toOSIS: {} Have an io1 not in an introduction section").format( toOSISGlobals["verseRef"] ) )
                        writerObject.writeLineOpen( 'div', [('type',"introduction"),('canonical',"false")] )
                        haveOpenIntro = True
                    if not haveOpenOutline: # Shouldn't happen but we'll try our best
                        logging.warning( _("toOSIS: {} Have an io1 not in an outline section").format( toOSISGlobals["verseRef"] ) )
                        closeAnyOpenParagraph()
                        writerObject.writeLineOpen( 'div', ('type',"outline") )
                        writerObject.writeLineOpen( 'list' )
                        haveOpenOutline = True
                    if text: writerObject.writeLineOpenClose( 'item', checkText(text) )
                elif marker=='io2':
                    if not haveOpenIntro:
                        logging.error( _("toOSIS: {} Have an io2 not in an introduction section").format( toOSISGlobals["verseRef"] ) )
                    if not haveOpenOutline:
                        logging.error( _("toOSIS: {} Have an io2 not in an outline section").format( toOSISGlobals["verseRef"] ) )
                    writerObject.writeLineOpenClose( 'item', checkText(text) ) # TODO: Shouldn't this be different from an io1???
                elif marker=='c':
                    if haveOpenVsID != False: # Close the previous verse
                        writerObject.writeLineOpenSelfclose( 'verse', ('eID',haveOpenVsID) )
                        haveOpenVsID = False
                    if haveOpenOutline:
                        if text!='1' and not text.startswith('1 '): logging.error( _("toOSIS: {} This should normally be chapter 1 to close the introduction (got '{}')").format( toOSISGlobals["verseRef"], text ) )
                        writerObject.writeLineClose( 'list' )
                        writerObject.writeLineClose( 'div' )
                        haveOpenOutline = False
                    if haveOpenIntro:
                        if text!='1' and not text.startswith('1 '): logging.error( _("toOSIS: {} This should normally be chapter 1 to close the introduction (got '{}')").format( toOSISGlobals["verseRef"], text ) )
                        closeAnyOpenParagraph()
                        writerObject.writeLineClose( 'div' )
                        haveOpenIntro = False
                    closeAnyOpenLG()
                    if needChapterEID:
                        writerObject.writeLineOpenSelfclose( 'chapter', ('eID',chapterRef) ) # This is an end milestone marker
                    currentChapterNumberString, verseNumberString = text, '0'
                    if not currentChapterNumberString.isdigit(): logging.critical( _("toOSIS: Can't handle non-digit '{}' chapter number yet").format(text) )
                    chapterRef = bookRef + '.' + checkText(currentChapterNumberString)
                    writerObject.writeLineOpenSelfclose( 'chapter', [('sID',chapterRef), ('osisID',chapterRef)] ) # This is a milestone marker
                    needChapterEID = True
                elif marker=='c~':
                    adjText = processXRefsAndFootnotes( text, extras, 0 )
                    writerObject.writeLineText( checkText(adjText), noTextCheck=True )
                elif marker == 'c#': # Chapter number added for printing
                    pass # Just ignore it completely
                elif marker=='ms1':
                    if haveOpenParagraph:
                        closeAnyOpenLG()
                        closeAnyOpenParagraph()
                    closeAnyOpenSubsection()
                    closeAnyOpenSection()
                    closeAnyOpenMajorSection()
                    writerObject.writeLineOpen( 'div', ('type',"majorSection") )
                    haveOpenMajorSection = True
                    if text: writerObject.writeLineOpenClose( 'title', checkText(text) ) # Section heading
                    logging.info( _("toOSIS: {} Blank ms1 section heading encountered").format( toOSISGlobals["verseRef"] ) )
                elif marker=='s1':
                    if haveOpenParagraph:
                        closeAnyOpenLG()
                        closeAnyOpenParagraph()
                    closeAnyOpenSubsection()
                    closeAnyOpenSection()
                    writerObject.writeLineOpen( 'div', ('type', "section") )
                    haveOpenSection = True
                    #print( "{} {}:{}".format( BBB, currentChapterNumberString, verseNumberString ) )
                    #print( "{} = '{}'".format( marker, text ) )
                    flag = False # Set this flag if the text already contains XML formatting
                    for format in ('\\nd ','\\bd ', '\\sc ', ):
                        if format in text: flag = True; break
                    if extras: flag = True
                    adjustedText = processXRefsAndFootnotes( text, extras )
                    if text: writerObject.writeLineOpenClose( 'title', checkText(adjustedText), noTextCheck=flag ) # Section heading
                    logging.info( _("toOSIS: {} Blank s1 section heading encountered").format( toOSISGlobals["verseRef"] ) )
                elif marker=='s2':
                    if haveOpenParagraph:
                        closeAnyOpenLG()
                        closeAnyOpenParagraph()
                    closeAnyOpenSubsection()
                    writerObject.writeLineOpen( 'div', ('type', "subSection") )
                    haveOpenSubsection = True
                    if text: writerObject.writeLineOpenClose( 'title',checkText(text) ) # Section heading
                    logging.info( _("toOSIS: {} Blank s2 section heading encountered").format( toOSISGlobals["verseRef"] ) )
                elif marker=='mr':
                    # Should only follow a ms1 I think
                    if haveOpenParagraph or haveOpenSection or not haveOpenMajorSection: logging.error( _("toOSIS: Didn't expect major reference 'mr' marker after {}").format(toOSISGlobals["verseRef"]) )
                    if text: writerObject.writeLineOpenClose( 'title', checkText(text), ('type',"parallel") ) # Section reference
                elif marker=='r':
                    # Should only follow a s1 I think
                    if haveOpenParagraph or not haveOpenSection: logging.error( _("toOSIS: Didn't expect reference 'r' marker after {}").format(toOSISGlobals["verseRef"]) )
                    if text: writerObject.writeLineOpenClose( 'title', checkText(text), ('type',"parallel") ) # Section reference
                elif marker=='p':
                    closeAnyOpenLG()
                    closeAnyOpenParagraph()
                    if not haveOpenSection:
                        writerObject.writeLineOpen( 'div', ('type', "section") )
                        haveOpenSection = True
                    adjustedText = processXRefsAndFootnotes( text, extras )
                    writerObject.writeLineOpenText( 'p', checkText(adjustedText), noTextCheck=True ) # Sometimes there's text
                    haveOpenParagraph = True
                elif marker=='v':
                    verseNumberString = text
                    if not haveOpenL: closeAnyOpenLG()
                    writeVerseStart( writerObject, BBB, chapterRef, verseNumberString )
                    closeAnyOpenL()
                elif marker=='v~':
                    adjText = processXRefsAndFootnotes( text, extras, 0 )
                    writerObject.writeLineText( checkText(adjText), noTextCheck=True )
                elif marker in ('q1','q2','q3',):
                    qLevel = marker[1] # The digit
                    closeAnyOpenL()
                    if not haveOpenLG:
                        writerObject.writeLineOpen( 'lg' )
                        haveOpenLG = True
                    if text:
                        adjustedText = processXRefsAndFootnotes( text, extras )
                        writerObject.writeLineOpenClose( 'l', checkText(adjustedText), ('level',qLevel), noTextCheck=True )
                    else: # No text -- this q1 applies to the next marker
                        writerObject.writeLineOpen( 'l', ('level',qLevel) )
                        haveOpenL = True
                elif marker=='m': # Margin/Flush-left paragraph
                    closeAnyOpenL()
                    closeAnyOpenLG()
                    if text: writerObject.writeLineText( checkText(text), noTextCheck=True )
                elif marker=='b': # Blank line
                        # Doesn't seem that OSIS has a way to encode this presentation element
                        writerObject.writeNewLine() # We'll do this for now
                else: unhandledMarkers.add( marker )
                if marker not in ('v','v~','p','q1','q2','q3','s1',) and extras: print( "toOSIS: Programming note: Didn't handle extras", marker, extras )
                lastMarker = marker

            # At the end of everything
            closeAnyOpenLG() # A file can easily end with a q1 field
            if haveOpenIntro or haveOpenOutline or haveOpenLG or haveOpenL or unprocessedMarker:
                logging.error( "toOSIS: a {} {} {} {} {}".format( haveOpenIntro, haveOpenOutline, haveOpenLG, haveOpenL, unprocessedMarker ) )
                logging.error( "toOSIS: b {} {}:{}".format( BBB, currentChapterNumberString, verseNumberString ) )
                logging.error( "toOSIS: c {} = '{}'".format( marker, text ) )
                logging.error( "toOSIS: d These shouldn't be open here" )
            if needChapterEID:
                writerObject.writeLineOpenSelfclose( 'chapter', ('eID',chapterRef) ) # This is an end milestone marker
            if haveOpenParagraph:
                closeAnyOpenLG()
                closeAnyOpenParagraph()
            closeAnyOpenSection()
            closeAnyOpenMajorSection()
            writerObject.writeLineClose( 'div' ) # Close book division
            writerObject.writeNewLine()
        # end of toOSISXML:writeBook

        if controlDict["osisFiles"]=="byBook": # Write an individual XML file for each book
            if Globals.verbosityLevel > 1: print( _("Exporting individually to OSIS XML format...") )
            validationResults = ( 0, '', '', ) # xmllint result code, program output, error output
            for BBB,bookData in self.books.items(): # Process each Bible book
                xw = MLWriter( controlDict["osisOutputFilename"].replace('_Bible',"_Book-{}".format(BBB)), outputFolder )
                xw.setHumanReadable( 'All' ) # Can be set to 'All', 'Header', or 'None' -- one output file went from None/Header=4.7MB to All=5.7MB
                xw.start()
                xw.writeLineOpen( 'osis', [('xmlns',"http://www.bibletechnologies.net/2003/OSIS/namespace"), ('xmlns:xsi',"http://www.w3.org/2001/XMLSchema-instance"), ('xsi:schemaLocation',"http://www.bibletechnologies.net/2003/OSIS/namespace http://www.bibletechnologies.net/osisCore.2.1.1.xsd")] )
                xw.writeLineOpen( 'osisText', [('osisRefWork',"Bible"), ('xml:lang',controlDict["xmlLanguage"]), ('osisIDWork',controlDict["osisIDWork"])] )
                xw.setSectionName( 'Header' )
                writeHeader( xw )
                xw.setSectionName( 'Main' )
                writeBook( xw, BBB, bookData )
                xw.writeLineClose( 'osisText' )
                xw.writeLineClose( 'osis' )
                xw.close()
                if validationSchema:
                    bookResults = xw.validate( validationSchema )
                    if bookResults[0] > validationResults[0]: validationResults = ( bookResults[0], validationResults[1], validationResults[2], )
                    if bookResults[1]: validationResults = ( validationResults[0], validationResults[1] + bookResults[1], validationResults[2], )
                    if bookResults[2]: validationResults = ( validationResults[0], validationResults[1], validationResults[2] + bookResults[2], )
        elif controlDict["osisFiles"]=="byBible": # write all the books into a single file
            if Globals.verbosityLevel > 1: print( _("Exporting to OSIS XML format...") )
            xw = MLWriter( controlDict["osisOutputFilename"], outputFolder )
            xw.setHumanReadable( 'All' ) # Can be set to 'All', 'Header', or 'None' -- one output file went from None/Header=4.7MB to All=5.7MB
            xw.start()
            xw.writeLineOpen( 'osis', [('xmlns',"http://www.bibletechnologies.net/2003/OSIS/namespace"), ('xmlns:xsi',"http://www.w3.org/2001/XMLSchema-instance"), ('xsi:schemaLocation',"http://www.bibletechnologies.net/2003/OSIS/namespace http://www.bibletechnologies.net/osisCore.2.1.1.xsd")] )
            xw.writeLineOpen( 'osisText', [('osisRefWork',"Bible"), ('xml:lang',controlDict["xmlLanguage"]), ('osisIDWork',controlDict["osisIDWork"])] )
            xw.setSectionName( 'Header' )
            writeHeader( xw )
            xw.setSectionName( 'Main' )
            for BBB,bookData in self.books.items(): # Process each Bible book
                writeBook( xw, BBB, bookData )
            xw.writeLineClose( 'osisText' )
            xw.writeLineClose( 'osis' )
            xw.close()
            if validationSchema: validationResults = xw.validate( validationSchema )
        else:
            logging.critical( "Unrecognized toOSIS control \"osisFiles\" = '{}'".format( controlDict["osisFiles"] ) )
        if unhandledMarkers:
            logging.warning( "toOSISXML: Unhandled USFM markers were {}".format( unhandledMarkers ) )
            if Globals.verbosityLevel > 1:
                print( "  " + _("WARNING: Unhandled toOSIS USFM markers were {}").format( unhandledMarkers ) )
        if Globals.verbosityLevel > 2:
            print( "Need to find and look at an example where a new chapter isn't a new <p> to see how chapter eIDs should be handled there" )
        if validationSchema: return validationResults
        return True
    # end of BibleWriter.toOSISXML



    def toSwordModule( self, outputFolder=None, controlDict=None, validationSchema=None ):
        """
        Using settings from the given control file,
            converts the USFM information to a UTF-8 OSIS-XML-based Sword module.
        """
        if Globals.verbosityLevel > 1: print( "Running BibleWriter:toSwordModule..." )
        if Globals.debugFlag: assert( self.books )

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolder: outputFolder = "OutputFiles/BOS_SwordExport/"
        if not os.access( outputFolder, os.F_OK ): os.makedirs( outputFolder ) # Make the empty folder if there wasn't already one there
        if not controlDict:
            controlDict, defaultControlFilename = {}, "To_OSIS_controls.txt"
            try:
                ControlFiles.readControlFile( defaultControlFolder, defaultControlFilename, controlDict )
            except:
                logging.critical( "Unable to read control dict {} from {}".format( defaultControlFilename, defaultControlFolder ) )

        import struct
        if Globals.debugFlag: assert( struct.calcsize("IH") == 6 ) # Six-byte format

        # Set-up our Bible reference system
        if controlDict['PublicationCode'] == "GENERIC":
            BOS = self.genericBOS
            BRL = self.genericBRL
        else:
            BOS = BibleOrganizationalSystem( controlDict["PublicationCode"] )
            BRL = BibleReferenceList( BOS, BibleObject=None )

        booksNamesSystemName = BOS.getOrganizationalSystemValue( 'booksNamesSystem' )
        if booksNamesSystemName and booksNamesSystemName!='None' and booksNamesSystemName!='Unknown': # default (if we know the book names system)
            getBookNameFunction = BOS.getBookName
            getBookAbbreviationFunction = BOS.getBookAbbreviation
        else: # else use our local functions from our deduced book names
            getBookNameFunction = self.getAssumedBookName # from USFMBible (which gets it from USFMBibleBook)
            getBookAbbreviationFunction = Globals.BibleBooksCodes.getOSISAbbreviation

        if 0:
            bookAbbrevDict, bookNameDict, bookAbbrevNameDict = {}, {}, {}
            for BBB in Globals.BibleBooksCodes.getAllReferenceAbbreviations(): # Pre-process the language booknames
                if BBB in controlDict and controlDict[BBB]:
                    bits = controlDict[BBB].split(',')
                    if len(bits)!=2: logging.error( _("toSword: Unrecognized language book abbreviation and name for {}: '{}'").format( BBB, controlDict[BBB] ) )
                    bookAbbrev = bits[0].strip().replace('"','') # Remove outside whitespace then the double quote marks
                    bookName = bits[1].strip().replace('"','') # Remove outside whitespace then the double quote marks
                    bookAbbrevDict[bookAbbrev], bookNameDict[bookName], bookAbbrevNameDict[BBB] = BBB, BBB, (bookAbbrev,bookName,)
                    if ' ' in bookAbbrev: bookAbbrevDict[bookAbbrev.replace(' ','',1)] = BBB # Duplicate entries without the first space (presumably between a number and a name like 1 Kings)
                    if ' ' in bookName: bookNameDict[bookName.replace(' ','',1)] = BBB # Duplicate entries without the first space

        unhandledMarkers = set()


        # Let's write a Sword locale while we're at it
        self._writeSwordLocale( controlDict["xmlLanguage"], controlDict["LanguageName"], BOS, getBookNameFunction, os.path.join( outputFolder, "SwLocale-utf8.conf" ) )
        #SwLocFilepath = os.path.join( outputFolder, "SwLocale-utf8.conf" )
        #if Globals.verbosityLevel > 1: print( _("Writing Sword locale file {}...").format(SwLocFilepath) )
        #with open( SwLocFilepath, 'wt' ) as SwLocFile:
            #SwLocFile.write( '[Meta]\nName={}\n'.format(controlDict["xmlLanguage"]) )
            #SwLocFile.write( 'Description={}\n'.format(controlDict["LanguageName"]) )
            #SwLocFile.write( 'Encoding=UTF-8\n\n[Text]\n' )
            #for BBB in BOS.getBookList():
                #if BBB in self.books:
                    #SwLocFile.write( '{}={}\n'.format(Globals.BibleBooksCodes.getEnglishName_NR(BBB), getBookNameFunction(BBB) ) ) # Write the first English book name and the vernacular book name
            #SwLocFile.write( '\n[Book Abbrevs]\n' )
            #for BBB in BOS.getBookList():
                #if BBB in self.books:
                    #SwLocFile.write( '{}={}\n'.format(Globals.BibleBooksCodes.getEnglishName_NR(BBB).upper(), Globals.BibleBooksCodes.getSwordAbbreviation(BBB) ) ) # Write the UPPER CASE language book name and the Sword abbreviation

        # Make our other folders if necessary
        modsdFolder = os.path.join( outputFolder, "mods.d" )
        if not os.access( modsdFolder, os.F_OK ): os.mkdir( modsdFolder ) # Make the empty folder if there wasn't already one there
        modulesFolder = os.path.join( outputFolder, "modules" )
        if not os.access( modulesFolder, os.F_OK ): os.mkdir( modulesFolder ) # Make the empty folder if there wasn't already one there
        textsFolder = os.path.join( modulesFolder, "texts" )
        if not os.access( textsFolder, os.F_OK ): os.mkdir( textsFolder ) # Make the empty folder if there wasn't already one there
        rawTextFolder = os.path.join( textsFolder, "rawtext" )
        if not os.access( rawTextFolder, os.F_OK ): os.mkdir( rawTextFolder ) # Make the empty folder if there wasn't already one there
        lgFolder = os.path.join( rawTextFolder, controlDict["osisWork"].lower() )
        if not os.access( lgFolder, os.F_OK ): os.mkdir( lgFolder ) # Make the empty folder if there wasn't already one there

        toSwordGlobals = { 'currentID':0, "idStack":[], "verseRef":'', "XRefNum":0, "FootnoteNum":0, "lastRef":'', 'offset':0, 'length':0, "OneChapterOSISBookCodes":Globals.BibleBooksCodes.getOSISSingleChapterBooksList() } # These are our global variables

        def writeIndexEntry( writerObject, indexFile ):
            """ Writes a newline to the main file and an entry to the index file. """
            writerObject.writeNewLine()
            writerObject._writeToBuffer( "IDX " ) # temp ..... XXXXXXX
            indexFile.write( struct.pack( "IH", toSwordGlobals['offset'], toSwordGlobals['length'] ) )
            toSwordGlobals['offset'] = writerObject.getFilePosition() # Get the new offset
            toSwordGlobals['length'] = 0 # Reset
        # end of toSwordModule:writeIndexEntry

        def writeBook( writerObject, ix, BBB, bkData ):
            """ Writes a Bible book to the output files. """

            def checkText( textToCheck ):
                """Handle some general backslash codes and warn about any others still unprocessed."""

                def checkTextHelper( marker, helpText ):
                    """ Adjust the text to make the number of start and close markers equal. """
                    count1, count2 = helpText.count('\\'+marker+' '), helpText.count('\\'+marker+'*') # count open and close markers
                    while count1 < count2:
                        helpText = '\\'+marker+' ' + helpText
                        count1, count2 = helpText.count('\\'+marker+' '), helpText.count('\\'+marker+'*') # count open and close markers again
                    while count1 > count2:
                        helpText += '\\'+marker+'*'
                        count1, count2 = helpText.count('\\'+marker+' '), helpText.count('\\'+marker+'*') # count open and close markers again
                    if Globals.debugFlag: assert( count1 == count2 )
                    return helpText
                # end of checkTextHelper

                adjText = textToCheck
                if '<<' in adjText or '>>' in adjText:
                    logging.warning( _("toSword: Unexpected double angle brackets in {}: '{}' field is '{}'").format(toOSISGlobals["verseRef"],marker,textToCheck) )
                    adjText = adjText.replace('<<','“' ).replace('>>','”' )
                if '\\add ' in adjText: adjText = checkTextHelper('add',adjText).replace('\\add ','<i>').replace('\\add*','</i>') # temp XXXXXX ...
                if '\\sig ' in adjText: adjText = checkTextHelper('sig',adjText).replace('\\sig ','<b>').replace('\\sig*','</b>') # temp... XXXXXXX
                if '\\bk ' in adjText: adjText = checkTextHelper('bk',adjText).replace('\\bk ','<reference type="x-bookName">').replace('\\bk*','</reference>')
                if '\\nd ' in adjText: adjText = checkTextHelper('nd',adjText).replace('\\nd ','<divineName>').replace('\\nd*','</divineName>')
                if '\\it ' in adjText: adjText = checkTextHelper('it',adjText).replace('\\it ','<hi type="italic">').replace('\\it*','</hi>')
                if '\\bd ' in adjText: adjText = checkTextHelper('bd',adjText).replace('\\bd ','<hi type="bold">').replace('\\bd*','</hi>')
                if '\\em ' in adjText: adjText = checkTextHelper('em',adjText).replace('\\em ','<hi type="bold">').replace('\\em*','</hi>')
                if '\\sc ' in adjText: adjText = checkTextHelper('sc',adjText).replace('\\sc ','<hi type="SMALLCAPS">').replace('\\sc*','</hi>') # XXXXXX temp ....
                if '\\wj ' in adjText: adjText = checkTextHelper('wj',adjText).replace('\\wj ','<hi type="bold">').replace('\\wj*','</hi>') # XXXXXX temp ....
                if '\\' in adjText:
                    logging.error( _("toSword: We still have some unprocessed backslashes for Sword in {}: '{}' field is '{}'").format(toSwordGlobals["verseRef"],marker,textToCheck) )
                    adjText = adjText.replace('\\','ENCODING ERROR HERE ' )
                return adjText
            # end of checkText

            def processXRefsAndFootnotes( verse, extras ):
                """Convert cross-references and footnotes and return the adjusted verse text."""

                def processXRef( USFMxref ):
                    """
                    Return the OSIS code for the processed cross-reference (xref).

                    NOTE: The parameter here already has the /x and /x* removed.

                    \\x - \\xo 2:2: \\xt Lib 19:9-10; Diy 24:19.\\xt*\\x* (Backslashes are shown doubled here)
                        gives
                    <note type="crossReference" n="1">2:2: <reference>Lib 19:9-10; Diy 24:19.</reference></note> (Crosswire -- invalid OSIS -- which then needs to be converted)
                    <note type="crossReference" osisRef="Ruth.2.2" osisID="Ruth.2.2!crossreference.1" n="-"><reference type="source" osisRef="Ruth.2.2">2:2: </reference><reference osisRef="-">Lib 19:9-10</reference>; <reference osisRef="Ruth.Diy.24!:19">Diy 24:19</reference>.</note> (Snowfall)
                    \\x - \\xo 3:5: a \\xt Rum 11:1; \\xo b \\xt Him 23:6; 26:5.\\xt*\\x* is more complex still.
                    """
                    nonlocal BBB
                    toSwordGlobals["XRefNum"] += 1
                    OSISxref = '<note type="crossReference" osisRef="{}" osisID="{}!crossreference.{}">'.format(toSwordGlobals["verseRef"],toSwordGlobals["verseRef"],toSwordGlobals["XRefNum"])
                    for j,token in enumerate(USFMxref.split('\\')):
                        #print( "processXRef", j, "'"+token+"'", "from", '"'+USFMxref+'"' )
                        if j==0: # The first token (but the x has already been removed)
                            rest = token.strip()
                            if rest != '-':
                                logging.warning( _("toSword: We got something else here other than hyphen (probably need to do something with it): {} '{}' from '{}'").format(chapterRef, token, text) )
                        elif token.startswith('xo '): # xref reference follows
                            adjToken = token[3:].strip()
                            if adjToken.endswith(' a'): adjToken = adjToken[:-2] # Remove any 'a' suffix (occurs when a cross-reference has multiple (a and b) parts
                            if adjToken.endswith(':'): adjToken = adjToken[:-1] # Remove any final colon (this is a language dependent hack)
                            adjToken = getBookAbbreviationFunction(BBB) + ' ' + adjToken # Prepend the vernacular book abbreviation
                            osisRef = BRL.parseToOSIS( adjToken )
                            if osisRef is not None:
                                OSISxref += '<reference type="source" osisRef="{}">{}</reference>'.format(osisRef,token[3:])
                                if not BRL.containsReference( BBB, currentChapterNumberString, verseNumberString ):
                                    logging.error( _("toSword: Cross-reference at {} {}:{} seems to contain the wrong self-reference '{}'").format(BBB,currentChapterNumberString,verseNumberString, token) )
                        elif token.startswith('xt '): # xref text follows
                            xrefText = token[3:]
                            finalPunct = ''
                            while xrefText[-1] in (' ,;.'): finalPunct = xrefText[-1] + finalPunct; xrefText = xrefText[:-1]
                            #adjString = xrefText[:-6] if xrefText.endswith( ' (LXX)' ) else xrefText # Sorry, this is a crude hack to avoid unnecessary error messages
                            osisRef = BRL.parseToOSIS( xrefText )
                            if osisRef is not None:
                                OSISxref += '<reference type="source" osisRef="{}">{}</reference>'.format(osisRef,xrefText+finalPunct)
                        elif token.startswith('x '): # another whole xref entry follows
                            rest = token[2:].strip()
                            if rest != '-':
                                logging.warning( _("toSword: We got something else here other than hyphen (probably need to do something with it): {} '{}' from '{}'").format(chapterRef, token, text) )
                        elif token in ('xt*', 'x*'):
                            pass # We're being lazy here and not checking closing markers properly
                        else:
                            logging.warning( _("toSword: Unprocessed '{}' token in {} xref '{}'").format(token, toSwordGlobals["verseRef"], USFMxref) )
                    OSISxref += '</note>'
                    return OSISxref
                # end of processXRef

                def processFootnote( USFMfootnote ):
                    """
                    Return the OSIS code for the processed footnote.

                    NOTE: The parameter here already has the /f and /f* removed.

                    \\f + \\fr 1:20 \\ft Su ka kaluwasan te Nawumi ‘keupianan,’ piru ka kaluwasan te Mara ‘masakit se geyinawa.’\\f* (Backslashes are shown doubled here)
                        gives
                    <note n="1">1:20 Su ka kaluwasan te Nawumi ‘keupianan,’ piru ka kaluwasan te Mara ‘masakit se geyinawa.’</note> (Crosswire)
                    <note osisRef="Ruth.1.20" osisID="Ruth.1.20!footnote.1" n="+"><reference type="source" osisRef="Ruth.1.20">1:20 </reference>Su ka kaluwasan te Nawumi ‘keupianan,’ piru ka kaluwasan te Mara ‘masakit se geyinawa.’</note> (Snowfall)
                    """
                    toSwordGlobals["FootnoteNum"] += 1
                    OSISfootnote = '<note osisRef="{}" osisID="{}!footnote.{}">'.format(toSwordGlobals["verseRef"],toSwordGlobals["verseRef"],toSwordGlobals["FootnoteNum"])
                    for j,token in enumerate(USFMfootnote.split('\\')):
                        #print( "processFootnote", j, token, USFMfootnote )
                        if j==0: continue # ignore the + for now
                        elif token.startswith('fr '): # footnote reference follows
                            adjToken = token[3:].strip()
                            if adjToken.endswith(':'): adjToken = adjToken[:-1] # Remove any final colon (this is a language dependent hack)
                            adjToken = getBookAbbreviationFunction(BBB) + ' ' + adjToken # Prepend the vernacular book abbreviation
                            osisRef = BRL.parseToOSIS( adjToken )
                            if osisRef is not None:
                                OSISfootnote += '<reference osisRef="{}" type="source">{}</reference>'.format(osisRef,token[3:])
                                if not BRL.containsReference( BBB, currentChapterNumberString, verseNumberString ):
                                    logging.error( _("toSword: Footnote at {} {}:{} seems to contain the wrong self-reference '{}'").format(BBB,currentChapterNumberString,verseNumberString, token) )
                        elif token.startswith('ft '): # footnote text follows
                            OSISfootnote += token[3:]
                        elif token.startswith('fq ') or token.startswith('fqa '): # footnote quote follows -- NOTE: We also assume here that the next marker closes the fq field
                            OSISfootnote += '<catchWord>{}</catchWord>'.format(token[3:]) # Note that the trailing space goes in the catchword here -- seems messy
                        elif token in ('ft*','ft* ','fq*','fq* ','fqa*','fqa* '):
                            pass # We're being lazy here and not checking closing markers properly
                        else:
                            logging.warning( _("toSword: Unprocessed '{}' token in {} footnote '{}'").format(token, toSwordGlobals["verseRef"], USFMfootnote) )
                    OSISfootnote += '</note>'
                    #print( '', OSISfootnote )
                    return OSISfootnote
                # end of processFootnote

                while '\\x ' in verse and '\\x*' in verse: # process cross-references (xrefs)
                    ix1 = verse.index('\\x ')
                    ix2 = verse.find('\\x* ') # Note the extra space here at the end
                    if ix2 == -1: # Didn't find it so must be no space after the asterisk
                        ix2 = verse.index('\\x*')
                        ix2b = ix2 + 3 # Where the xref ends
                        logging.warning( _("toSword: No space after xref entry in {}").format(toSwordGlobals["verseRef"]) )
                    else: ix2b = ix2 + 4
                    xref = verse[ix1+3:ix2]
                    osisXRef = processXRef( xref )
                    #print( osisXRef )
                    verse = verse[:ix1] + osisXRef + verse[ix2b:]
                while '\\f ' in verse and '\\f*' in verse: # process footnotes
                    ix1 = verse.index('\\f ')
                    ix2 = verse.find('\\f*')
#                    ix2 = verse.find('\\f* ') # Note the extra space here at the end -- doesn't always work if there's two footnotes within one verse!!!
#                    if ix2 == -1: # Didn't find it so must be no space after the asterisk
#                        ix2 = verse.index('\\f*')
#                        ix2b = ix2 + 3 # Where the footnote ends
#                        #logging.warning( 'toSword: No space after footnote entry in {}'.format(toSwordGlobals["verseRef"] )
#                    else: ix2b = ix2 + 4
                    footnote = verse[ix1+3:ix2]
                    osisFootnote = processFootnote( footnote )
                    #print( osisFootnote )
                    verse = verse[:ix1] + osisFootnote + verse[ix2+3:]
#                    verse = verse[:ix1] + osisFootnote + verse[ix2b:]
                return verse
            # end of processXRefsAndFootnotes

            def writeVerseStart( writerObject, BBB, chapterRef, verseNumberString ):
                """
                Processes and writes a verse to the OSIS XML writerObject.
                    <verse sID="Gen.1.31" osisID="Gen.1.31"/>
                    Ne nakita te Manama ka langun ne innimu rin wey natelesan amana sikandin. Ne nasagkup e wey napawe, ne seeye ka igkeen-em ne aldew.
                    <verse eID="Gen.1.31"/>

                Has to handle joined verses, e.g.,
                    <verse sID="Esth.9.16" osisID="Esth.9.16 Esth.9.17"/>text<verse eID="Esth.9.16"/> (Crosswire)
                    <verse sID="Esth.9.16-Esth.9.17" osisID="Esth.9.16 Esth.9.17" n="16-17"/>text<verse eID="Esth.9.16-Esth.9.17"/> (Snowfall)
                """
                nonlocal haveOpenVsID
                osisID = sID = toSwordGlobals["verseRef"] # default
                if haveOpenVsID != False: # Close the previous verse
                    writerObject.writeLineOpenSelfclose( 'verse', ('eID',haveOpenVsID) )
                #verseNumberString = text.split()[0] # Get the first token which is the first number
                #verseText = text[len(verseNumberString)+1:].lstrip() # Get the rest of the string which is the verse text
                if '-' in verseNumberString:
                    bits = verseNumberString.split('-')
                    if (len(bits)!=2 or not bits[0].isdigit() or not bits[1].isdigit()):
                        logging.critical( _("toSword: Doesn't handle verse number of form '{}' yet for {}").format(verseNumberString,chapterRef) )
                    toSwordGlobals["verseRef"]  = chapterRef + '.' + bits[0]
                    verseRef2 = chapterRef + '.' + bits[1]
                    sID    = toSwordGlobals["verseRef"] + '-' + verseRef2
                    osisID = toSwordGlobals["verseRef"] + ' ' + verseRef2
                elif ',' in verseNumberString:
                    bits = verseNumberString.split(',')
                    if (len(bits)<2 or not bits[0].isdigit() or not bits[1].isdigit()):
                        logging.critical( _("toSword: Doesn't handle verse number of form '{}' yet for {}").format(verseNumberString,chapterRef) )
                    sID = toSwordGlobals["verseRef"] = chapterRef + '.' + bits[0]
                    osisID = ''
                    for bit in bits: # Separate the OSIS ids by spaces
                        osisID += ' ' if osisID else ''
                        osisID += chapterRef + '.' + bit
                    #print( "Hey comma verses '{}' '{}'".format( sID, osisID ) )
                elif verseNumberString.isdigit():
                    sID = osisID = toSwordGlobals["verseRef"] = chapterRef + '.' + verseNumberString
                else:
                    logging.critical( _("toSword: Doesn't handle verse number of form '{}' yet for {}").format(verseNumberString,chapterRef) )
                writerObject.writeLineOpenSelfclose( 'verse', [('sID',sID), ('osisID',osisID)] ); haveOpenVsID = sID
                #adjText = processXRefsAndFootnotes( verseText, extras )
                #writerObject.writeLineText( checkText(adjText), noTextCheck=True )
                ##writerObject.writeLineOpenSelfclose( 'verse', ('eID',sID) )
                #writeIndexEntry( writerObject, indexFile )
            # end of writeVerseStart

            def closeAnyOpenMajorSection():
                """ Close a <div> if it's open. """
                nonlocal haveOpenMajorSection
                if haveOpenMajorSection:
                    writerObject.writeLineClose( 'div' )
                    haveOpenMajorSection = False
            # end of closeAnyOpenMajorSection

            def closeAnyOpenSection():
                """ Close a <div> if it's open. """
                nonlocal haveOpenSection
                if haveOpenSection:
                    writerObject.writeLineClose( 'div' )
                    haveOpenSection = False
            # end of closeAnyOpenSection

            def closeAnyOpenSubsection():
                """ Close a <div> if it's open. """
                nonlocal haveOpenSubsection
                if haveOpenSubsection:
                    writerObject.writeLineClose( 'div' )
                    haveOpenSubsection = False
            # end of closeAnyOpenSubsection

            def closeAnyOpenParagraph():
                """ Close a <p> if it's open. """
                nonlocal haveOpenParagraph
                if haveOpenParagraph:
                    writerObject.writeLineOpenSelfclose( 'div', [('eID',toSwordGlobals['idStack'].pop()), ('type',"paragraph")] )
                    haveOpenParagraph = False
            # end of closeAnyOpenParagraph

            def closeAnyOpenLG():
                """ Close a <lg> if it's open. """
                nonlocal haveOpenLG
                if haveOpenLG:
                    writerObject.writeLineClose( 'lg' )
                    haveOpenLG = False
            # end of closeAnyOpenLG

            def closeAnyOpenL():
                """ Close a <l> if it's open. """
                nonlocal haveOpenL
                if haveOpenL:
                    writerObject.writeLineClose( 'l' )
                    haveOpenL = False
            # end of closeAnyOpenL

            def getNextID():
                """ Returns the next sID sequence code. """
                toSwordGlobals['currentID'] += 1
                return "gen{}".format(toSwordGlobals['currentID'])
            # end of getNextID

            def getSID():
                """ Returns a tuple containing ('sID', getNextID() ). """
                ID = getNextID()
                toSwordGlobals['idStack'].append( ID )
                return ('sID', ID )
            # end of getSID

            bookRef = Globals.BibleBooksCodes.getOSISAbbreviation( BBB ) # OSIS book name
            writerObject.writeLineOpen( 'div', [('osisID',bookRef), getSID(), ('type',"book")] )
            haveOpenIntro = haveOpenOutline = haveOpenMajorSection = haveOpenSection = haveOpenSubsection = needChapterEID = haveOpenParagraph = haveOpenVsID = haveOpenLG = haveOpenL = False
            lastMarker = unprocessedMarker = ''
            #chapterNumberString = None
            for marker,originalMarker,text,cleanText,extras in bkData._processedLines: # Process USFM lines
                #print( BBB, marker, text )
                #print( " ", haveOpenIntro, haveOpenOutline, haveOpenMajorSection, haveOpenSection, haveOpenSubsection, needChapterEID, haveOpenParagraph, haveOpenVsID, haveOpenLG, haveOpenL )
                #print( toSwordGlobals['idStack'] )
                if marker in ( 'id', 'h1', 'mt2' ): continue # We just ignore these markers
                if marker=='mt1': writerObject.writeLineOpenClose( 'title', checkText(text) )
                elif marker=='is1' or marker=='imt1':
                    if haveOpenIntro: # already -- assume it's a second one
                        closeAnyOpenParagraph()
                        writerObject.writeLineOpenSelfclose( 'div', [('eID',toSwordGlobals['idStack'].pop()), ('type',"introduction")] )
                        haveOpenIntro = False
                    writerObject.writeLineOpen( 'div', [getSID(), ('type',"introduction")] )
                    if text: writerObject.writeLineOpenClose( 'title', checkText(text) ) # Introduction heading
                    else:
                        logging.error( _("toSword: {} Have a blank {} field—ignoring it").format( toSwordGlobals["verseRef"], marker ) )
                    haveOpenIntro = True
                    chapterRef = bookRef + '.0' # Not used by OSIS
                    toSwordGlobals["verseRef"] = chapterRef + '.0' # Not used by OSIS
                elif marker=='ip':
                    if not haveOpenIntro: # Shouldn't happen but we'll try our best
                        logging.error( "toSword: {} Have an ip not in an introduction section—opening an intro section".format( toSwordGlobals["verseRef"] ) )
                        writerObject.writeLineOpen( 'div', ('type',"introduction") )
                        haveOpenIntro = True
                    closeAnyOpenParagraph()
                    writerObject.writeLineOpenSelfclose( 'div', [getSID(), ('type',"paragraph")] )
                    writerObject.writeLineText( checkText(text), noTextCheck=True ) # Sometimes there's text
                    haveOpenParagraph = True
                elif marker=='iot':
                    if not haveOpenIntro: # Shouldn't happen but we'll try our best
                        logging.error( "toSword: {} Have a iot not in an introduction section—opening an intro section".format( toSwordGlobals["verseRef"] ) )
                        writerObject.writeLineOpen( 'div', ('type',"introduction") )
                        haveOpenIntro = True
                    if haveOpenOutline:
                        writerObject.writeLineClose( 'list' )
                        writerObject.writeLineOpenSelfclose( 'div', [('eID',toSwordGlobals['idStack'].pop()), ('type',"outline")] )
                        haveOpenOutline = False
                    if haveOpenSection:
                        logging.error( "toSword: {} Not handled yet iot".format( toSwordGlobals["verseRef"] ) )
                    closeAnyOpenParagraph()
                    writerObject.writeLineOpenSelfclose( 'div', [getSID(), ('type',"outline")] )
                    if text: writerObject.writeLineOpenClose( 'title', checkText(text) )
                    writerObject.writeLineOpen( 'list' )
                    haveOpenOutline = True
                elif marker=='io1':
                    #if haveOpenIntro:
                    #    closeAnyOpenParagraph()
                    #    writerObject.writeLineOpenSelfclose( 'div', [('eID',toSwordGlobals['idStack'].pop()), ('type',"introduction")] )
                    #    haveOpenIntro = False
                    if not haveOpenIntro: # Shouldn't happen but we'll try our best
                        logging.error( "toSword: {} Have an io1 not in an introduction section—opening an intro section".format( toSwordGlobals["verseRef"] ) )
                        writerObject.writeLineOpen( 'div', ('type',"introduction") )
                        haveOpenIntro = True
                    if not haveOpenOutline: # Shouldn't happen but we'll try our best
                        logging.warning( _("toSword: {} Have an io1 not in an outline section—opening an outline section".format(toSwordGlobals["verseRef"]) ) )
                        closeAnyOpenParagraph()
                        writerObject.writeLineOpenSelfclose( 'div', [getSID(), ('type',"outline")] )
                        writerObject.writeLineOpen( 'list' )
                        haveOpenOutline = True
                    if text: writerObject.writeLineOpenClose( 'item', checkText(text) )
                elif marker=='io2':
                    if not haveOpenIntro:
                        logging.error( _("toSword: {} Have an io2 not in an introduction section").format( toSwordGlobals["verseRef"] ) )
                    if not haveOpenOutline:
                        logging.error( _("toSword: {} Have an io2 not in an outline section").format( toSwordGlobals["verseRef"] ) )
                    writerObject.writeLineOpenClose( 'item', checkText(text) ) # TODO: Shouldn't this be different from an io1???
                elif marker=='c':
                    if haveOpenOutline:
                        if text!='1' and not text.startswith('1 '):
                            logging.error( _("toSword: {} This should normally be chapter 1 to close the introduction (got '{}')").format( toSwordGlobals["verseRef"], text ) )
                        writerObject.writeLineClose( 'list' )
                        writerObject.writeLineOpenSelfclose( 'div', [('eID',toSwordGlobals['idStack'].pop()), ('type',"outline")] )
                        haveOpenOutline = False
                    if haveOpenIntro:
                        if text!='1' and not text.startswith('1 '):
                            logging.error( _("toSword: {} This should normally be chapter 1 to close the introduction (got '{}')").format( toSwordGlobals["verseRef"], text ) )
                        closeAnyOpenParagraph()
                        writerObject.writeLineOpenSelfclose( 'div', [('eID',toSwordGlobals['idStack'].pop()), ('type',"introduction")] )
                        haveOpenIntro = False
                    closeAnyOpenLG()
                    if needChapterEID:
                        writerObject.writeLineOpenSelfclose( 'chapter', ('eID',chapterRef) ) # This is an end milestone marker
                    writeIndexEntry( writerObject, ix )
                    currentChapterNumberString, verseNumberString = text, '0'
                    if not currentChapterNumberString.isdigit():
                        logging.critical( _("toSword: Can't handle non-digit '{}' chapter number yet").format(text) )
                    chapterRef = bookRef + '.' + checkText(currentChapterNumberString)
                    writerObject.writeLineOpenSelfclose( 'chapter', [('osisID',chapterRef), ('sID',chapterRef)] ) # This is a milestone marker
                    needChapterEID = True
                    writeIndexEntry( writerObject, ix )
                elif marker=='ms1':
                    if haveOpenParagraph:
                        closeAnyOpenLG()
                        closeAnyOpenParagraph()
                    closeAnyOpenSubsection()
                    closeAnyOpenSection()
                    closeAnyOpenMajorSection()
                    writerObject.writeLineOpen( 'div', ('type',"majorSection") )
                    haveOpenMajorSection = True
                    if text: writerObject.writeLineOpenClose( 'title', checkText(text) ) # Section heading
                    else:
                        logging.info( _("toSword: Blank ms1 section heading encountered after {}").format( toSwordGlobals["verseRef"] ) )
                elif marker=='s1':
                    if haveOpenParagraph:
                        closeAnyOpenLG()
                        closeAnyOpenParagraph()
                    closeAnyOpenSubsection()
                    closeAnyOpenSection()
                    writerObject.writeLineOpen( 'div', [getSID(), ('type',"section")] )
                    haveOpenSection = True
                    if text: writerObject.writeLineOpenClose( 'title', checkText(text) ) # Section heading
                    else:
                        logging.info( _("toSword: Blank s1 section heading encountered after {}:{}").format( currentChapterNumberString, verseNumberString ) )
                elif marker=='s2':
                    if haveOpenParagraph:
                        closeAnyOpenLG()
                        closeAnyOpenParagraph()
                    closeAnyOpenSubsection()
                    writerObject.writeLineOpen( 'div', ('type', "subSection") )
                    haveOpenSubsection = True
                    if text: writerObject.writeLineOpenClose( 'title', checkText(text) ) # Section heading
                    else:
                        logging.info( _("toSword: Blank s2 section heading encountered after {}:{}").format( currentChapterNumberString, verseNumberString ) )
                elif marker=='mr':
                    # Should only follow a ms1 I think
                    if haveOpenParagraph or haveOpenSection or not haveOpenMajorSection: logging.error( _("toSword: Didn't expect major reference 'mr' marker after {}").format(toSwordGlobals["verseRef"]) )
                    if text: writerObject.writeLineOpenClose( 'title', checkText(text), ('type',"parallel") ) # Section reference
                elif marker=='r':
                    # Should only follow a s1 I think
                    if haveOpenParagraph or not haveOpenSection: logging.error( _("toSword: Didn't expect reference 'r' marker after {}").format(toSwordGlobals["verseRef"]) )
                    if text: writerObject.writeLineOpenClose( 'title', checkText(text), ('type',"parallel") ) # Section reference
                elif marker=='p':
                    closeAnyOpenLG()
                    closeAnyOpenParagraph()
                    if not haveOpenSection:
                        writerObject.writeLineOpenSelfclose( 'div', [getSID(), ('type',"section")] )
                        haveOpenSection = True
                    adjustedText = processXRefsAndFootnotes( text, extras )
                    writerObject.writeLineOpenSelfclose( 'div', [getSID(), ('type',"paragraph")] )
                    writerObject.writeLineText( checkText(adjustedText), noTextCheck=True ) # Sometimes there's text
                    haveOpenParagraph = True
                elif marker=='v':
                    #if not chapterNumberString: # Some single chapter books don't have an explicit c marker
                    #    if Globals.debugFlag: assert( BBB in Globals.BibleBooksCodes.getSingleChapterBooksList() )
                    verseNumberString = text
                    if not haveOpenL: closeAnyOpenLG()
                    writeVerseStart( writerObject, BBB, chapterRef, verseNumberString )
                    #closeAnyOpenL()
                elif marker=='v~':
                    #if not haveOpenL: closeAnyOpenLG()
                    #writeVerseStart( writerObject, ix, BBB, chapterRef, text )
                    adjText = processXRefsAndFootnotes( text, extras )
                    writerObject.writeLineText( checkText(adjText), noTextCheck=True )
                    #writerObject.writeLineOpenSelfclose( 'verse', ('eID',sID) )
                    writeIndexEntry( writerObject, ix )
                    closeAnyOpenL()
                elif marker=='q1' or marker=='q2' or marker=='q3':
                    qLevel = '1' if marker=='q1' else '2' if marker=='q2' else '3'
                    if not haveOpenLG:
                        writerObject.writeLineOpen( 'lg' )
                        haveOpenLG = True
                    if text:
                        adjustedText = processXRefsAndFootnotes( text, extras )
                        writerObject.writeLineOpenClose( 'l', checkText(adjustedText), ('level',qLevel), noTextCheck=True )
                    else: # No text -- this q1 applies to the next marker
                        writerObject.writeLineOpen( 'l', ('level',qLevel) )
                        haveOpenL = True
                elif marker=='m': # Margin/Flush-left paragraph
                    closeAnyOpenL()
                    closeAnyOpenLG()
                    if text: writerObject.writeLineText( checkText(text) )
                elif marker=='b': # Blank line
                        # Doesn't seem that OSIS has a way to encode this presentation element
                        writerObject.writeNewLine() # We'll do this for now
                else: unhandledMarkers.add( marker )
                lastMarker = marker
            if (haveOpenIntro or haveOpenOutline or haveOpenLG or haveOpenL or unprocessedMarker):
                logging.error( "toSword: a {} {} {} {} {}".format( haveOpenIntro, haveOpenOutline, haveOpenLG, haveOpenL, unprocessedMarker ) )
                logging.error( "toSword: b {} {}:{}".format( BBB, currentChapterNumberString, verseNumberString ) )
                logging.error( "toSword: c {} = '{}'".format( marker, text ) )
                logging.error( "toSword: d These shouldn't be open here" )
            if needChapterEID:
                writerObject.writeLineOpenSelfclose( 'chapter', ('eID',chapterRef) ) # This is an end milestone marker
            if haveOpenParagraph:
                closeAnyOpenLG()
                closeAnyOpenParagraph()
            closeAnyOpenSection()
            closeAnyOpenMajorSection()
            writerObject.writeLineClose( 'div' ) # Close book division
            writerObject.writeNewLine()
        # end of toSwordModule:writeBook

        # An uncompressed Sword module consists of a .conf file
        #   plus ot and nt XML files with binary indexes ot.vss and nt.vss (containing 6-byte chunks = 4-byte offset, 2-byte length)
        if Globals.verbosityLevel > 1: print( _("Exporting to Sword modified-OSIS XML format...") )
        xwOT = MLWriter( 'ot', lgFolder )
        xwNT = MLWriter( 'nt', lgFolder )
        xwOT.setHumanReadable( 'NLSpace', indentSize=5 ) # Can be set to 'All', 'Header', or 'None'
        xwNT.setHumanReadable( 'NLSpace', indentSize=5 ) # Can be set to 'All', 'Header', or 'None'
        xwOT.start( noAutoXML=True ); xwNT.start( noAutoXML=True )
        toSwordGlobals['length'] = xwOT.writeLineOpenSelfclose( 'milestone', [('type',"x-importer"), ('subtype',"x-BibleWriter.py"), ('n',"${} $".format(ProgVersion))] )
        toSwordGlobals['length'] = xwNT.writeLineOpenSelfclose( 'milestone', [('type',"x-importer"), ('subtype',"x-BibleWriter.py"), ('n',"${} $".format(ProgVersion))] )
        xwOT.setSectionName( 'Main' ); xwNT.setSectionName( 'Main' )
        with open( os.path.join( lgFolder, 'ot.vss' ), 'wb' ) as ixOT, open( os.path.join( lgFolder, 'nt.vss' ), 'wb' ) as ixNT:
            ixOT.write( struct.pack( "IH", 0, 0 ) ) # Write the first dummy entry
            ixNT.write( struct.pack( "IH", 0, 0 ) ) # Write the first dummy entry
            writeIndexEntry( xwOT, ixOT ) # Write the second entry pointing to the opening milestone
            writeIndexEntry( xwNT, ixNT ) # Write the second entry pointing to the opening milestone
            for BBB,bookData in self.books.items(): # Process each Bible book
                if Globals.BibleBooksCodes.isOldTestament_NR( BBB ):
                    xw = xwOT; ix = ixOT
                elif Globals.BibleBooksCodes.isNewTestament_NR( BBB ):
                    xw = xwNT; ix = ixNT
                else:
                    logging.critical( _("toSword: Sword module writer doesn't know how to encode {} book or appendix").format(BBB) )
                    continue
                writeBook( xw, ix, BBB, bookData )
        xwOT.close(); xwNT.close()
        if unhandledMarkers:
            logging.warning( "toSwordModule: Unhandled USFM markers were {}".format( unhandledMarkers ) )
            if Globals.verbosityLevel > 1:
                print( "  " + _("WARNING: Unhandled toSwordModule USFM markers were {}").format( unhandledMarkers ) )
        if validationSchema:
            OTresults= xwOT.validate( validationSchema )
            NTresults= xwNT.validate( validationSchema )
            return OTresults and NTresults
        return True
    #end of BibleWriter.toSwordModule



    def toHTML5( self, outputFolder=None, controlDict=None, validationSchema=None ):
        """
        Using settings from the given control file,
            converts the USFM information to UTF-8 HTML files.
        """
        if Globals.verbosityLevel > 1: print( "Running BibleWriter:toHTML5..." )
        if Globals.debugFlag: assert( self.books )

        if not self.doneSetupGeneric: self.__setupWriter()
        if not outputFolder: outputFolder = "OutputFiles/BOS_HTML5Export/"
        if not os.access( outputFolder, os.F_OK ): os.makedirs( outputFolder ) # Make the empty folder if there wasn't already one there
        if not controlDict:
            controlDict, defaultControlFilename = {}, "To_HTML5_controls.txt"
            try:
                ControlFiles.readControlFile( defaultControlFolder, defaultControlFilename, controlDict )
            except:
                logging.critical( "Unable to read control dict {} from {}".format( defaultControlFilename, defaultControlFolder ) )
        if Globals.debugFlag: assert( controlDict and isinstance( controlDict, dict ) )

        unhandledMarkers = set()

        def writeHeader( writerObject ):
            """Writes the HTML5 header to the HTML writerObject."""
            writerObject.writeLineOpen( 'head' )
            writerObject.writeLineText( '<meta http-equiv="Content-Type" content="text/html;charset=utf-8">', noTextCheck=True )
            writerObject.writeLineText( '<link rel="stylesheet" type="text/css" href="../CSS/BibleBook.css">', noTextCheck=True )
            if "HTML5Title" in controlDict and controlDict["HTML5Title"]:
                writerObject.writeLineOpenClose( 'title' , controlDict["HTML5Title"].replace('__PROJECT_NAME__',self.name) )
            #if "HTML5Subject" in controlDict and controlDict["HTML5Subject"]: writerObject.writeLineOpenClose( 'subject', controlDict["HTML5Subject"] )
            #if "HTML5Description" in controlDict and controlDict["HTML5Description"]: writerObject.writeLineOpenClose( 'description', controlDict["HTML5Description"] )
            #if "HTML5Publisher" in controlDict and controlDict["HTML5Publisher"]: writerObject.writeLineOpenClose( 'publisher', controlDict["HTML5Publisher"] )
            #if "HTML5Contributors" in controlDict and controlDict["HTML5Contributors"]: writerObject.writeLineOpenClose( 'contributors', controlDict["HTML5Contributors"] )
            #if "HTML5Identifier" in controlDict and controlDict["HTML5Identifier"]: writerObject.writeLineOpenClose( 'identifier', controlDict["HTML5Identifier"] )
            #if "HTML5Source" in controlDict and controlDict["HTML5Source"]: writerObject.writeLineOpenClose( 'identifier', controlDict["HTML5Source"] )
            #if "HTML5Coverage" in controlDict and controlDict["HTML5Coverage"]: writerObject.writeLineOpenClose( 'coverage', controlDict["HTML5Coverage"] )
            #writerObject.writeLineOpenClose( 'format', 'HTML5 markup language' )
            #writerObject.writeLineOpenClose( 'date', datetime.datetime.now().date().isoformat() )
            #writerObject.writeLineOpenClose( 'creator', 'BibleWriter.py' )
            #writerObject.writeLineOpenClose( 'type', 'bible text' )
            #if "HTML5Language" in controlDict and controlDict["HTML5Language"]: writerObject.writeLineOpenClose( 'language', controlDict["HTML5Language"] )
            #if "HTML5Rights" in controlDict and controlDict["HTML5Rights"]: writerObject.writeLineOpenClose( 'rights', controlDict["HTML5Rights"] )
            writerObject.writeLineClose( 'head' )

            writerObject.writeLineOpen( 'body' )
            writerObject.writeLineOpen( 'header' )
            writerObject.writeLineText( 'HEADER STUFF GOES HERE' )
            writerObject.writeLineClose( 'header' )
            writerObject.writeLineOpen( 'nav' )
            writerObject.writeLineText( 'NAVIGATION STUFF GOES HERE' )
            writerObject.writeLineClose( 'nav' )
        # end of toHTML5.writeHeader

        def writeFooter( writerObject ):
            """Writes the HTML5 footer to the HTML writerObject."""
            writerObject.writeLineOpen( 'footer' )
            writerObject.writeLineOpen( 'p', ('class','footerLine') )
            writerObject.writeLineOpen( 'a', ('href','http://www.w3.org/html/logo/') )
            writerObject.writeLineText( '<img src="http://www.w3.org/html/logo/badge/html5-badge-h-css3-semantics.png" width="165" height="64" alt="HTML5 Powered with CSS3 / Styling, and Semantics" title="HTML5 Powered with CSS3 / Styling, and Semantics">', noTextCheck=True )
            writerObject.writeLineClose( 'a' )
            writerObject.writeLineText( "This page automatically created by: {} v{} {}".format( ProgName, ProgVersion, datetime.date.today().strftime("%d-%b-%Y") ) )
            writerObject.writeLineClose( 'p' )
            writerObject.writeLineClose( 'footer' )
            writerObject.writeLineClose( 'body' )
        # end of toHTML5.writeFooter

        def convertToPageReference( refTuple ):
            assert( refTuple and len(refTuple)==4 )
            assert( refTuple[0] and len(refTuple[0])==3 ) #BBB
            return '{}#C{}V{}'.format( filenameDict[refTuple[0]], refTuple[1], refTuple[2] )
        # end of toHTML5.convertToPageReference

        def createSectionReference( givenRef ):
            """ Returns an HTML string for a section reference. """
            #print( "createSectionReference: '{}'".format( givenRef ) )
            theRef = givenRef
            result = bracket = ''
            for bracketLeft,bracketRight in (('(',')'),('[',']'),):
                if theRef and theRef[0]==bracketLeft and theRef[-1]==bracketRight:
                    result += bracketLeft
                    bracket = bracketRight
                    theRef = theRef[1:-1] # Remove the brackets
            refs = theRef.split( ';' )
            for j,ref in enumerate(refs):
                if j: result += '; '
                ref = ref.strip()
                if ref:
                    analysis = BRL.getFirstReference( ref, "section reference '{}' from '{}'".format( ref, givenRef ) )
                    #print( "a", analysis )
                    if analysis: result += '<a href="{}">{}</a>'.format( convertToPageReference(analysis), ref )
                    else: result += ref
            #print( "now = '{}'".format( result ) )
            return result + bracket
        # end of toHTML5.createSectionReference

        def writeBook( writerObject, BBB, bkData ):
            """Writes a book to the HTML5 writerObject."""
            writeHeader( writerObject )
            haveOpenSection = haveOpenParagraph = haveOpenList = False
            C = V = ''
            for marker,originalMarker,text,cleanText,extras in bkData._processedLines: # Process internal Bible lines
                #if BBB=='MRK': print( "writeBook", marker, cleanText )
                #print( "toHTML5.writeBook", BBB, C, V, marker, cleanText )
                if marker in ('id','ide','toc1','toc2','toc3','rem',):
                    pass # Just ignore these lines

                # Markers usually only found in the introduction
                elif marker in ('mt1','mt2',):
                    assert( not haveOpenParagraph )
                    writerObject.writeLineOpenClose( 'h1', cleanText, ('class','mainTitle'+marker[2]) )
                elif marker in ('ms1','ms2',):
                    if not haveOpenParagraph:
                        logging.warning( "toHTML5: Have main section heading {} outside a paragraph in {}".format( cleanText, BBB ) )
                        writerObject.writeLineOpen( 'p', ('class','unknownParagraph') ); haveOpenParagraph = True
                    if cleanText: writerObject.writeLineOpenClose( 'h2', cleanText, ('class','mainSectionHeading'+marker[1]) )
                elif marker == 'ip':
                    if haveOpenParagraph: writerObject.writeLineClose( 'p' ); haveOpenParagraph = False
                    writerObject.writeLineOpen( 'p', ('class','introductoryParagraph') ); haveOpenParagraph = True
                    if cleanText: writerObject.writeLineText( cleanText )
                elif marker == 'iot':
                    if haveOpenParagraph: writerObject.writeLineClose( 'p' ); haveOpenParagraph = False
                    if cleanText: writerObject.writeLineOpenClose( 'h3', cleanText, ('class','outlineTitle') )
                elif marker in ('io1','io2','io3',):
                    if haveOpenParagraph: writerObject.writeLineClose( 'p' ); haveOpenParagraph = False
                    if cleanText: writerObject.writeLineOpenClose( 'p', cleanText, ('class','outlineEntry'+marker[2]) )

                # Now markers in the main text
                elif marker in 'c':
                    # What should we put in here -- we don't need/want to display it, but it's a place to jump to
                    writerObject.writeLineOpenClose( 'span', ' ', [('class','chapterStart'),('id','C'+cleanText)] )
                elif marker in 'c#':
                    C = cleanText
                    if not haveOpenParagraph:
                        logging.warning( "toHTML5: Have chapter number {} outside a paragraph in {}".format( cleanText, BBB ) )
                        writerObject.writeLineOpen( 'p', ('class','unknownParagraph') ); haveOpenParagraph = True
                    writerObject.writeLineOpenClose( 'span', cleanText, ('class','chapterNumber') )
                elif marker in ('s1','s2','s3',):
                    if haveOpenParagraph: writerObject.writeLineClose( 'p' ); haveOpenParagraph = False
                    if marker == 's1':
                        if haveOpenSection: writerObject.writeLineClose( 'section' ); haveOpenSection = False
                        writerObject.writeLineOpen( 'section', ('class','regularSection') ); haveOpenSection = True
                    if cleanText: writerObject.writeLineOpenClose( 'h2', cleanText, ('class','sectionHeading'+marker[1]) )
                elif marker == 'r':
                    assert( haveOpenSection )
                    assert( not haveOpenParagraph )
                    if cleanText: writerObject.writeLineOpenClose( 'span', createSectionReference(cleanText), ('class','sectionReference'), noTextCheck=True )
                elif marker == 'v':
                    V = cleanText
                    if not haveOpenParagraph:
                        logging.warning( "toHTML5: Have verse number {} outside a paragraph in {}".format( cleanText, BBB ) )
                    if 1: # no span -- it's simpler so why not!
                        writerObject.writeLineOpenClose( 'sup', cleanText, [('class','verseNumber'),('id','C'+C+'V'+cleanText)] )
                    else: # use sup and then span
                        writerObject.writeLineOpen( 'sup' )
                        writerObject.writeLineOpenClose( 'span', cleanText, [('class','verseNumber'),('id','C'+C+'V'+cleanText)] )
                        writerObject.writeLineClose( 'sup' )
                elif marker == 'p':
                    if haveOpenList: writerObject.writeLineClose( 'p' ); haveOpenList = False
                    if haveOpenParagraph: writerObject.writeLineClose( 'p' ); haveOpenParagraph = False
                    writerObject.writeLineOpen( 'p', ('class','proseParagraph') ); haveOpenParagraph = True
                elif marker == 'pi':
                    if haveOpenParagraph: writerObject.writeLineClose( 'p' )
                    writerObject.writeLineOpen( 'p', ('class','indentedProseParagraph') ); haveOpenParagraph = True
                elif marker == 'q1':
                    if haveOpenParagraph: writerObject.writeLineClose( 'p' )
                    writerObject.writeLineOpen( 'p', ('class','poetryParagraph1') ); haveOpenParagraph = True
                    if cleanText: writerObject.writeLineText( cleanText )
                elif marker == 'q2':
                    if haveOpenParagraph: writerObject.writeLineClose( 'p' )
                    writerObject.writeLineOpen( 'p', ('class','poetryParagraph2') ); haveOpenParagraph = True
                    if cleanText: writerObject.writeLineText( cleanText )
                elif marker == 'q3':
                    if haveOpenParagraph: writerObject.writeLineClose( 'p' )
                    writerObject.writeLineOpen( 'p', ('class','poetryParagraph3') ); haveOpenParagraph = True
                    if cleanText: writerObject.writeLineText( cleanText )
                elif marker == 'li1':
                    if not haveOpenList:
                        writerObject.writeLineOpen( 'p', ('class','list') ); haveOpenList = True
                    writerObject.writeLineOpen( 'span', ('class','listItem1') )
                    if cleanText: writerObject.writeLineText( cleanText )

                # Character markers
                elif marker=='v~':
                    if not haveOpenParagraph:
                        logging.warning( "toHTML5: Have verse text {} outside a paragraph in {}".format( cleanText, BBB ) )
                        writerObject.writeLineOpen( 'p', ('class','unknownParagraph') ); haveOpenParagraph = True
                    if cleanText: writerObject.writeLineText( cleanText )
                else: unhandledMarkers.add( marker )
            if haveOpenList: writerObject.writeLineClose( 'p' ); haveOpenList = False
            if haveOpenParagraph: writerObject.writeLineClose( 'p' ); haveOpenParagraph = False
            if haveOpenSection: writerObject.writeLineClose( 'section' ); haveOpenSection = False
            writeFooter( writerObject )
        # end of toHTML5.writeBook

        # Set-up our Bible reference system
        if controlDict['PublicationCode'] == "GENERIC":
            BOS = self.genericBOS
            BRL = self.genericBRL
        else:
            BOS = BibleOrganizationalSystem( controlDict["PublicationCode"] )
            BRL = BibleReferenceList( BOS, BibleObject=None )

        if Globals.verbosityLevel > 1: print( _("Exporting to HTML5 format...") )
        suffix = controlDict['HTML5Suffix'] if 'HTML5Suffix' in controlDict else 'html'
        filenameDict = {}
        for BBB in self.books: # Make a list of filenames
            filename = controlDict['HTML5OutputFilenameTemplate'].replace('__PROJECT_NAME__','BIBLE') \
                            .replace('__BOOKCODE__',BBB ).replace('__SUFFIX__',suffix)
            filenameDict[BBB] = filename

        if controlDict["HTML5Files"]=="byBook":
            for BBB,bookData in self.books.items(): # Now export the books
                if Globals.verbosityLevel > 2: print( _("  Exporting {} to HTML5 format...").format( BBB ) )
                xw = MLWriter( filenameDict[BBB], outputFolder, 'HTML' )
                xw.setHumanReadable()
                xw.start( noAutoXML=True )
                xw.writeLineText( '<!DOCTYPE html>', noTextCheck=True )
                xw.writeLineOpen( 'html' )
                if Globals.debugFlag: writeBook( xw, BBB, bookData )
                else:
                    try: writeBook( xw, BBB, bookData )
                    except Exception as err:
                        print( BBB, "Unexpected error:", sys.exc_info()[0], err)
                        logging.error( "toHTML5: Oops, creating {} failed!".format( BBB ) )
                xw.writeLineClose( 'html' )
                xw.close()
        else: halt # not done yet
        if unhandledMarkers:
            logging.warning( "toHTML5: Unhandled USFM markers were {}".format( unhandledMarkers ) )
            if Globals.verbosityLevel > 1:
                print( "  " + _("WARNING: Unhandled toHTML5 USFM markers were {}").format( unhandledMarkers ) )
        if validationSchema: return xw.validate( validationSchema )
        return True
    # end of BibleWriter.toHTML5


    #def doExport( self, n ):
        #"""
        #Only used for multiprocessing.
        #"""
        #print( "BibleWriter.doExport( {} )".format( n ) )
        #if n==0: f = self.toUSFM
        #elif n==1: f = self.toMediaWiki
        #elif n==2: f = self.toZefaniaXML
        #elif n==3: f = self.toUSXXML
        #elif n==4: f = self.toOSISXML
        #elif n==5: f = self.toSwordModule
        #elif n==6: f = self.toHTML5
        #return f( self.__outputFolders[n] )
    ## end of BibleWriter.doExport


    def doAllExports( self, givenOutputFolderName=None ):
        """
        """
        if Globals.verbosityLevel > 1: print( _("BibleWriter.doAllExports: Exporting {} ({}) to all formats...").format( self.name, self.objectTypeString ) )
        if givenOutputFolderName == None: givenOutputFolderName = "OutputFiles"

        if Globals.debugFlag: assert( givenOutputFolderName and isinstance( givenOutputFolderName, str ) )
        # Check that the given folder is readable
        if not os.access( givenOutputFolderName, os.W_OK ):
            logging.critical( _("BibleWriter.doAllExports: Given '{}' folder is unwritable").format( givenOutputFolderName ) )
            return False

        # Define our various output folders
        PseudoUSFMOutputFolder = os.path.join( givenOutputFolderName, "BOS_PseudoUSFM" + "Export" )
        USFMOutputFolder = os.path.join( givenOutputFolderName, "BOS_USFM" + ("Reexport" if self.objectTypeString=='USFM' else "Export" ) )
        TWOutputFolder = os.path.join( givenOutputFolderName, "BOS_TheWord" + ("Reexport" if self.objectTypeString=='TheWord' else "Export" ) )
        MWOutputFolder = os.path.join( givenOutputFolderName, "BOS_MediaWiki" + ("Reexport" if self.objectTypeString=='MediaWiki' else "Export" ) )
        zOutputFolder = os.path.join( givenOutputFolderName, "BOS_Zefania" + ("Reexport" if self.objectTypeString=='Zefania' else "Export" ) )
        USXOutputFolder = os.path.join( givenOutputFolderName, "BOS_USX" + ("Reexport" if self.objectTypeString=='USX' else "Export" ) )
        OSISOutputFolder = os.path.join( givenOutputFolderName, "BOS_OSIS" + ("Reexport" if self.objectTypeString=='OSIS' else "Export" ) )
        swOutputFolder = os.path.join( givenOutputFolderName, "BOS_Sword" + ("Reexport" if self.objectTypeString=='Sword' else "Export" ) )
        htmlOutputFolder = os.path.join( givenOutputFolderName, "BOS_HTML5" + "Export" )
        pickleOutputFolder = os.path.join( givenOutputFolderName, "BOS_Bible_Object_Pickle" )

        # Don't know why this causes a seg fault
        #if Globals.debugFlag: self.pickle( folder=pickleOutputFolder ) # halts if fails
        #else:
            #try: self.pickle( folder=pickleOutputFolder )
            #except: print( "BibleWriter.doAllExports: pickle( {} ) failed.".format( folder ) )

        if Globals.debugFlag:
            PseudoUSFMExportResult = self.toPseudoUSFM( PseudoUSFMOutputFolder )
            USFMExportResult = self.toUSFM( USFMOutputFolder )
            TWExportResult = self.toTheWord( TWOutputFolder )
            MWExportResult = self.toMediaWiki( MWOutputFolder )
            zExportResult = self.toZefaniaXML( zOutputFolder )
            USXExportResult = self.toUSXXML( USXOutputFolder )
            OSISExportResult = self.toOSISXML( OSISOutputFolder )
            swExportResult = self.toSwordModule( swOutputFolder )
            htmlExportResult = self.toHTML5( htmlOutputFolder )
        elif 0 and Globals.maxProcesses > 1: # Process all the exports with different threads
            # DON'T KNOW WHY THIS CAUSES A SEGFAULT
            self.__outputFolders = [USFMOutputFolder, MWOutputFolder, zOutputFolder, USXOutputFolder, OSISOutputFolder, swOutputFolder, htmlOutputFolder]
            #self.__outputProcesses = [self.toUSFM, self.toMediaWiki, self.toZefaniaXML, self.toUSXXML, self.toOSISXML, self.toSwordModule, self.toHTML5]
            #assert( len(self.__outputFolders) == len(self.__outputProcesses) )
            print( "here1" )
            with multiprocessing.Pool( processes=Globals.maxProcesses ) as pool: # start worker processes
                print( "here2" )
                print( range( len(self.__outputFolders) ) )
                results = pool.map( self.doExport, range( len(self.__outputFolders) ) ) # have the pool do our loads
                print( "got results", len(results) )
                assert( len(results) == len(self.__outputFolders) )
                USFMExportResult = results[0]
                MWExportResult = results[1]
                zExportResult = results[2]
                USXExportResult = results[3]
                OSISExportResult = results[4]
                swExportResult = results[5]
                htmlExportResult = results[6]
        else: # Just single threaded and not debugging
            try: PseudoUSFMExportResult = self.toPseudoUSFM( PseudoUSFMOutputFolder )
            except Exception as err:
                PseudoUSFMExportResult = False
                print("BibleWriter.doAllExports.toPseudoUSFM Unexpected error:", sys.exc_info()[0], err)
                logging.error( "BibleWriter.doAllExports.toPseudoUSFM: Oops, failed!" )
            try: USFMExportResult = self.toUSFM( USFMOutputFolder )
            except Exception as err:
                USFMExportResult = False
                print("BibleWriter.doAllExports.toUSFM Unexpected error:", sys.exc_info()[0], err)
                logging.error( "BibleWriter.doAllExports.toUSFM: Oops, failed!" )
            try: TWExportResult = self.toTheWord( TWOutputFolder )
            except Exception as err:
                TWExportResult = False
                print("BibleWriter.doAllExports.toTheWord Unexpected error:", sys.exc_info()[0], err)
                logging.error( "BibleWriter.doAllExports.toTheWord: Oops, failed!" )
            try: MWExportResult = self.toMediaWiki( MWOutputFolder )
            except Exception as err:
                MWExportResult = False
                print("BibleWriter.doAllExports.toMediaWiki Unexpected error:", sys.exc_info()[0], err)
                logging.error( "BibleWriter.doAllExports.toMediaWiki: Oops, failed!" )
            try: zExportResult = self.toZefaniaXML( zOutputFolder )
            except Exception as err:
                zExportResult = False
                print("BibleWriter.doAllExports.toZefaniaXML Unexpected error:", sys.exc_info()[0], err)
                logging.error( "BibleWriter.doAllExports.toZefaniaXML: Oops, failed!" )
            try: USXExportResult = self.toUSXXML( USXOutputFolder )
            except Exception as err:
                USXExportResult = False
                print("BibleWriter.doAllExports.toUSXXML Unexpected error:", sys.exc_info()[0], err)
                logging.error( "BibleWriter.doAllExports.toUSXXML: Oops, failed!" )
            try: OSISExportResult = self.toOSISXML( OSISOutputFolder )
            except Exception as err:
                OSISExportResult = False
                print("BibleWriter.doAllExports.toOSISXML Unexpected error:", sys.exc_info()[0], err)
                logging.error( "BibleWriter.doAllExports.toOSISXML: Oops, failed!" )
            try: swExportResult = self.toSwordModule( swOutputFolder )
            except Exception as err:
                swExportResult = False
                print("BibleWriter.doAllExports.toSwordModule Unexpected error:", sys.exc_info()[0], err)
                logging.error( "BibleWriter.doAllExports.toSwordModule: Oops, failed!" )
            try: htmlExportResult = self.toHTML5( htmlOutputFolder )
            except Exception as err:
                htmlExportResult = False
                print("BibleWriter.doAllExports.toHTML5 Unexpected error:", sys.exc_info()[0], err)
                logging.error( "BibleWriter.doAllExports.toHTML5: Oops, failed!" )

        if Globals.verbosityLevel > 1:
            if PseudoUSFMExportResult and USFMExportResult and TWExportResult and MWExportResult and zExportResult \
            and USXExportResult and OSISExportResult and swExportResult and htmlExportResult:
                print( "BibleWriter.doAllExports finished them all successfully!" )
            else: print( "BibleWriter.doAllExports finished:  PsUSFM={} USFM={}  TW={} MW={}  Zef={}  USX={}  OSIS={}  Sw={}  HTML={}" \
                    .format( PseudoUSFMExportResult, USFMExportResult, TWExportResult, MWExportResult, zExportResult, USXExportResult, OSISExportResult, swExportResult, htmlExportResult ) )
        return {'PseudoUSFMExport':PseudoUSFMExportResult, 'USFMExport':USFMExportResult,
                    'TWExport':TWExportResult, 'MWExport':MWExportResult, 'zExport':zExportResult,
                    'USXExport':USXExportResult, 'OSISExport':OSISExportResult, 'swExport':swExportResult,
                    'htmlExport':htmlExportResult}
    # end of BibleWriter.doAllExports
# end of class BibleWriter



def demo():
    """
    Demonstrate reading and processing some Bible databases.
    """
    if Globals.verbosityLevel > 0: print( ProgNameVersion )

    # Since this is only designed to be a virtual base class, it can't actually do much at all
    BW = BibleWriter()
    BW.objectNameString = "Dummy test Bible Writer object"
    if Globals.verbosityLevel > 0: print( BW ); print()

    # But we'll test reading and writing a USX Bible
    from USXXMLBible import USXXMLBible
    from USXFilenames import USXFilenames
    testData = (
            #("Matigsalug", "../../../../../Data/Work/VirtualBox_Shared_Folder/PT7.3 Exports/USXExports/Projects/MBTV/",),
            ("Matigsalug", "../../../../../Data/Work/VirtualBox_Shared_Folder/PT7.4 Exports/USX Exports/MBTV/",),
            ) # You can put your USX test folder here

    for name, testFolder in testData:
        if os.access( testFolder, os.R_OK ):
            UB = USXXMLBible( testFolder, name )
            UB.load()
            if Globals.verbosityLevel > 0: print( UB )
            if Globals.strictCheckingFlag: UB.check()
            doaResults = UB.doAllExports()
            if Globals.strictCheckingFlag: # Now compare the original and the derived USX XML files
                outputFolder = "OutputFiles/BOS_USXReexport/"
                fN = USXFilenames( testFolder )
                f1 = os.listdir( testFolder ) # Originals
                f2 = os.listdir( outputFolder ) # Derived
                if Globals.verbosityLevel > 1: print( "\nComparing original and re-exported USX files..." )
                for j, (BBB,filename) in enumerate( fN.getPossibleFilenames() ):
                    if filename in f1 and filename in f2:
                        #print( "\n{}: {} {}".format( j+1, BBB, filename ) )
                        result = Globals.fileCompareXML( filename, filename, testFolder, outputFolder )
                        if Globals.debugFlag:
                            if not result: halt
        else: print( "Sorry, test folder '{}' is not readable on this computer.".format( testFolder ) )
# end of demo

if __name__ == '__main__':
    # Configure basic set-up
    parser = Globals.setup( ProgName, ProgVersion )
    parser.add_option("-e", "--export", action="store_true", dest="export", default=False, help="export the XML file to .py and .h tables suitable for directly including into other programs")
    Globals.addStandardOptionsAndProcess( parser )

    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    demo()

    Globals.closedown( ProgName, ProgVersion )
# end of BibleWriter.py