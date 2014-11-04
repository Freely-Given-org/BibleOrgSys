#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# ESwordBible.py
#   Last modified: 2014-11-04 by RJH (also update ProgVersion below)
#
# Module handling "e-Sword" Bible module files
#
# Copyright (C) 2013-2014 Robert Hunt
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
Module reading and loading e-Sword Bible files.
These can be downloaded from: http://www.BibleSupport.com and http://www.biblemodulesresource.com.

e-Sword Bible modules use RTF internally for formatting.
    See http://en.wikipedia.org/wiki/Rich_Text_Format
    and http://e-sword-users.org/users/node/3969

    file has one verse per line (KJV versification)
    OT (.ot file) has 23145 lines
    NT (.nt file) has 7957 lines
    Bible (.ont file) has 31102 lines.

e.g.,
    In the beginning of God's preparing the heavens and the earth--
    the earth hath existed waste and void, and darkness <FI>is<Fi> on the face of the deep, and the Spirit of God fluttering on the face of the waters,<CM>
    and God saith, `Let light be;' and light is.
    And God seeth the light that <FI>it is<Fi> good, and God separateth between the light and the darkness,
    and God calleth to the light `Day,' and to the darkness He hath called `Night;' and there is an evening, and there is a morning--day one.<CM>
    And God saith, `Let an expanse be in the midst of the waters, and let it be separating between waters and waters.'
    And God maketh the expanse, and it separateth between the waters which <FI>are<Fi> under the expanse, and the waters which <FI>are<Fi> above the expanse: and it is so.
    And God calleth to the expanse `Heavens;' and there is an evening, and there is a morning--day second.<CM>
"""

ProgName = "e-Sword Bible format handler"
ProgVersion = "0.11"
ProgNameVersion = "{} v{}".format( ProgName, ProgVersion )

debuggingThisModule = False


import logging, os, re
from gettext import gettext as _
import sqlite3
import multiprocessing

import BibleOrgSysGlobals
from Bible import Bible, BibleBook
from BibleOrganizationalSystems import BibleOrganizationalSystem
#from TheWordBible import handleLine



filenameEndingsToAccept = ('.BBLX',) # Must be UPPERCASE here
BibleFilenameEndingsToAccept = ('.BBLX',) # Must be UPPERCASE here



def ESwordBibleFileCheck( givenFolderName, strictCheck=True, autoLoad=False, autoLoadBooks=False ):
    """
    Given a folder, search for e-Sword Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number of Bibles found.

    if autoLoad is true and exactly one e-Sword Bible is found,
        returns the loaded ESwordBible object.
    """
    if BibleOrgSysGlobals.verbosityLevel > 2: print( "ESwordBibleFileCheck( {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad ) )
    if BibleOrgSysGlobals.debugFlag: assert( givenFolderName and isinstance( givenFolderName, str ) )
    if BibleOrgSysGlobals.debugFlag: assert( autoLoad in (True,False,) )

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( _("ESwordBibleFileCheck: Given {} folder is unreadable").format( repr(givenFolderName) ) )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( _("ESwordBibleFileCheck: Given {} path is not a folder").format( repr(givenFolderName) ) )
        return False

    # Find all the files and folders in this folder
    if BibleOrgSysGlobals.verbosityLevel > 3: print( " ESwordBibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
    foundFolders, foundFiles = [], []
    for something in os.listdir( givenFolderName ):
        somepath = os.path.join( givenFolderName, something )
        if os.path.isdir( somepath ): foundFolders.append( something )
        elif os.path.isfile( somepath ):
            somethingUpper = something.upper()
            somethingUpperProper, somethingUpperExt = os.path.splitext( somethingUpper )
            #ignore = False
            #for ending in filenameEndingsToIgnore:
                #if somethingUpper.endswith( ending): ignore=True; break
            #if ignore: continue
            #if not somethingUpperExt[1:] in extensionsToIgnore: # Compare without the first dot
            if somethingUpperExt in filenameEndingsToAccept:
                foundFiles.append( something )
    if '__MACOSX' in foundFolders:
        foundFolders.remove( '__MACOSX' )  # don't visit these directories

    # See if there's an ESwordBible project here in this given folder
    numFound = 0
    looksHopeful = False
    lastFilenameFound = None
    for thisFilename in sorted( foundFiles ):
        lastFilenameFound = thisFilename
        numFound += 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "ESwordBibleFileCheck got", numFound, givenFolderName, lastFilenameFound )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "{} doing autoload of {}...".format( ProgNameVersion, lastFilenameFound ) )
            twB = ESwordBible( givenFolderName, lastFilenameFound )
            if autoLoadBooks: twB.load() # Load and process the file
            return twB
        return numFound
    elif looksHopeful and BibleOrgSysGlobals.verbosityLevel > 2: print( "    Looked hopeful but no actual files found" )

    # Look one level down
    numFound = 0
    foundProjects = []
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
        if not os.access( tryFolderName, os.R_OK ): # The subfolder is not readable
            logging.warning( _("ESwordBibleFileCheck: {} subfolder is unreadable").format( repr(tryFolderName) ) )
            continue
        if BibleOrgSysGlobals.verbosityLevel > 3: print( "    ESwordBibleFileCheck: Looking for files in {}".format( repr(tryFolderName) ) )
        foundSubfolders, foundSubfiles = [], []
        for something in os.listdir( tryFolderName ):
            somepath = os.path.join( givenFolderName, thisFolderName, something )
            if os.path.isdir( somepath ): foundSubfolders.append( something )
            elif os.path.isfile( somepath ):
                somethingUpper = something.upper()
                somethingUpperProper, somethingUpperExt = os.path.splitext( somethingUpper )
                #ignore = False
                #for ending in filenameEndingsToIgnore:
                    #if somethingUpper.endswith( ending): ignore=True; break
                #if ignore: continue
                #if not somethingUpperExt[1:] in extensionsToIgnore: # Compare without the first dot
                if somethingUpperExt in filenameEndingsToAccept:
                    foundSubfiles.append( something )

        # See if there's an TW project here in this folder
        for thisFilename in sorted( foundSubfiles ):
            foundProjects.append( (tryFolderName, thisFilename,) )
            lastFilenameFound = thisFilename
            numFound += 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "ESwordBibleFileCheck foundProjects", numFound, foundProjects )
        if numFound == 1 and (autoLoad and autoLoadBooks):
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "{} doing autoload of {}...".format( ProgNameVersion, foundProjects[0][1] ) )
            if BibleOrgSysGlobals.debugFlag: assert( len(foundProjects) == 1 )
            twB = ESwordBible( foundProjects[0][0], foundProjects[0][1] )
            if autoLoadBooks: twB.load() # Load and process the file
            return twB
        return numFound
# end of ESwordBibleFileCheck



class ESwordBible( Bible ):
    """
    Class for reading, validating, and converting ESwordBible files.
    """
    def __init__( self, sourceFolder, givenFilename, encoding='utf-8' ):
        """
        Constructor: just sets up the Bible object.
        """
         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = 'e-Sword Bible object'
        self.objectTypeString = 'e-Sword'

        # Now we can set our object variables
        self.sourceFolder, self.sourceFilename, self.encoding = sourceFolder, givenFilename, encoding
        self.sourceFilepath =  os.path.join( self.sourceFolder, self.sourceFilename )

        # Do a preliminary check on the readability of our file
        if not os.access( self.sourceFilepath, os.R_OK ):
            logging.critical( _("ESwordBible: File {} is unreadable").format( repr(self.sourceFilepath) ) )

        filenameBits = os.path.splitext( self.sourceFilename )
        self.name = filenameBits[0]
        self.fileExtension = filenameBits[1]

        #if self.fileExtension.upper().endswith('X'):
            #logging.warning( _("ESwordBible: File {} is encrypted").format( repr(self.sourceFilepath) ) )
    # end of ESwordBible.__init__


    def handleLine( self, myName, BBB, C, V, originalLine, bookObject, myGlobals ):
        """
        Adjusts the formatting of the line for Bible reference BBB C:V
            and then writes it to the bookObject.

        Try to convert display formatting to semantic formatting as much as possible

        myGlobals dict contains flags.

        Appends pseudo-USFM results to the supplied bookObject.

        NOTE: originalLine can be None here.

        NOTE: There are no checks in here yet to discover nested character-formatting markers.  :-(
        """
        if BibleOrgSysGlobals.debugFlag:
            if debuggingThisModule:
                print( "ESwordBible.handleLine( {} {} {}:{} {} ... {}".format( myName, BBB, C, V, repr(originalLine), myGlobals ) )
            assert( originalLine is None or ('\n' not in originalLine and '\r' not in originalLine ) )
        #print( BBB, C, V, repr(originalLine) )
        line = originalLine

        writtenV = False
        if V==1: appendedCFlag = False
        if C!=1 and V==1: bookObject.appendLine( 'c', str(C) ); appendedCFlag = True

        if line is None: # We don't have an entry for this C:V
            return

        # Now we have to convert RTF codes to our internal codes
        # First do special characters
        line = line.replace( '\\ldblquote', '“' ).replace( '\\rdblquote', '”' ).replace( '\\lquote', '‘' ).replace( '\\rquote', '’' )
        line = line.replace( '\\emdash', '—' ).replace( '\\endash', '–' )
        # Now do Unicode characters
        while True: # Find patterns like \\'d3
            match = re.search( r"\\'[0-9a-f][0-9a-f]", line )
            if not match: break
            #print( originalLine )
            #print( line )
            #h1, h2 = line[match.start()+2], line[match.start()+3]
            i = int( line[match.start()+2:match.end()], 16 ) # Convert two hex characters to decimal
            #print( h1, h2, i, chr(i) )
            line = line[:match.start()] + chr( i ) + line[match.end():]
            #print( line )
            #print( repr(line) )
        while True: # Find patterns like \\u253?
            match = re.search( r"\\u[1-2][0-9][0-9]\?", line )
            if not match: break
            #print( originalLine )
            #print( line )
            #h1, h2 = line[match.start()+2], line[match.start()+3]
            i = int( line[match.start()+2:match.end()-1] ) # Convert three digits to decimal
            #print( h1, h2, i, chr(i) )
            line = line[:match.start()] + chr( i ) + line[match.end():]
            #print( line )
            #print( repr(line) )

        # We will temporarily use ~^~ instead of backslash so we can distinguish our own codes from the RTF codes
        # Try to guess some semantic formatting
        #line = re.sub( r'\\cf14 (.+?)\\cf0', r'~^~add \1~^~add*', line )
        #line = re.sub( r'\\cf15\\i (.+?)\\cf0\\i0', r'~^~add \1~^~add*', line )

        # Stuff to just remove -- not sure what most of this is about yet
        while True:
            line = line.lstrip()
            changed = False
            for stuff in ( '\\viewkind4', '\\uc1', '\\nowidctlpar',
                    '\\paperw12240', '\\paperh15840',
                    '\\tx720', '\\tx1440', '\\tx2160' '\\tx2880', '\\tx3600', '\\tx4320', '\\tx5040', '\\tx5760', '\\tx6480', '\\tx7200', '\\tx7920', '\\tx8640', '\\tx9360', '\\tx10080',
                    '\\margl1440', '\\margt1440', '\\margr1440', '\\margb1440', '\\deftab1134', '\\widowctrl',
                    '\\formshade', '\\sectd',
                    '\\headery720', '\\footery720', '\\pgwsxn12240', '\\pghsxn15840', '\\marglsxn1800',
                    '\\margtsxn1440', '\\margrsxn1800', '\\margbsxn1440', '\\pgbrdropt32', '\\s17',
                    '\\itap0', '\\nosupersub', '\\ulnone',
                    '\\cf15', '\\cf14', '\\cf10', '\\cf0', '\\lang1030', '\\lang1033', '\\f0', '\\i0', '\\b0', ):
                if line.startswith( stuff ): line = line[len(stuff):]; changed = True
            if not changed: break
        for stuff in ( '\\nosupersub', '\\ulnone', '\\b0', '\\i0', '\\cf0', ):
            if line.endswith( stuff ): line = line[:-len(stuff)]
        if BibleOrgSysGlobals.debugFlag: savedLine = line

        # Try to guess some semantic formatting
        line = re.sub( r'\\b\\i\\f0 (.+?)\\cf0\\b0\\i0\\line', r'~^~s1 \1*#$#', line ) # section heading
        line = re.sub( r'\\cf10\\b\\i (.+?)\\cf0\\b0\\i0\\line', r'~^~s1 \1*#$#', line ) # section heading in LEB
        line = re.sub( r'\\cf14 (.+?)\\cf0', r'~^~add \1~^~add*', line )
        line = re.sub( r'\\cf15\\i (.+?)\\cf0\\i0', r'~^~add \1~^~add*', line )
        line = re.sub( r'\\cf15\\i(.+?)\\cf0\\i0 ', r'~^~add \1~^~add*', line ) # LEB (error???)
        line = re.sub( r'^\\i (.+?)\\cf0\\i0 ', r'~^~add \1~^~add*', line ) # LEB (error???)
        line = re.sub( r'{\\cf15 (.+?)}', r'~^~add \1~^~add*', line )
        line = re.sub( r'\\i\\f0 (.+?)\\cf0\\i0', r'~^~add \1~^~add*', line )

        # Unfortunately, it's all display formatting, no semantic formatting  :-(
        # NOTE: This doesn't handle nesting yet
        line = re.sub( r'{\\cf10\\b\\i (.+?)\\cf0\\b0\\i0', r'~^~bdit \1~^~bdit*', line )
        line = re.sub( r'{\\b (.+?)}', r'~^~bd \1~^~bd*', line )
        line = re.sub( r'{\\cf15\\i (.+?)}', r'~^~it \1~^~it*', line )
        line = re.sub( r'{\\cf10\\i (.+?)}', r'~^~it \1~^~it*', line ) # What is different about these?
        line = re.sub( r'{\\cf2\\i (.+?)}', r'~^~it \1~^~it*', line )
        line = re.sub( r'{\\i (.+?)}', r'~^~it \1~^~it*', line )
        line = re.sub( r'{\\i(.+?)}', r'~^~it \1~^~it*', line ) # Also occurs without the space in some modules
        line = re.sub( r'{\\qc (.+?)}', r'~^~qc \1~^~qc*', line )

        line = line.replace( '\\b1', '~^~bd ' ).replace( '\\b0', '~^~bd*' )
        line = line.replace( '\\cf15\\i ', '~^~+it ' ).replace( '\\cf14\\i0', '~^~it*' ) # Attempt to handle some nesting in LEB
        line = line.replace( '\\i1', '~^~it ' ).replace( '\\i0', '~^~it*' )

        # Not sure what this is
        line = re.sub( r'{\\cf2\\super (.+?)}', r'', line ) # Notes like '[2]' -- deleted for now
        line = line.replace( '\\cf2  \\cf0', '' ) # LEB
        line = line.replace( '\\cf0 ', '' ) # Calvin
        line = line.replace( '\\loch\\f0', '' ).replace( '\\hich\\f0', '' ) # Calvin

        line = line.replace( '\\par\\par', '#$#~^~p' )
        line = line.replace( '\\par', '#$#~^~p' )
        line = line.replace( '\\m ', '#$#~^~m ' )

        # Handle module formatting errors -- formatting that goes across verses!
        line = line.replace( '{\\cf2\\super [ ','[ ' ) # In one module Luke 22:42 -- weird
        line = line.replace( '{\\cf 2 [','[' ) # In one module John 1:4 -- weird
        line = line.replace( ']}',']' ) # In one module Luke 22:44; 23:34 -- weird
        if myName=="Lexham English Bible": line = line.replace( '\\cf14 ','') # Not sure what this is in LEB

        # Check what's left at the end
        line = line.replace( '\\line', '#$#' ) # Use this for our newline marker
        line = line.strip() # There seem to be extra spaces in many modules
        if '\\' in line or '{' in line or '}' in line:
            if BibleOrgSysGlobals.debugFlag:
                logging.error( "{} original line: {}".format( myName, repr(originalLine) ) )
                logging.error( "Saved line: {}".format( repr(savedLine) ) )
            logging.error( "ESwordBible.load: Doesn't handle {} {}:{} formatted line yet: {}".format( BBB, C, V, repr(line) ) )
            if 1: # Unhandled stuff -- not done properly yet...............................................
                line = re.sub( '<(.+?)>', '', line ) # Remove all remaining sets of angle brackets
            if 0 and BibleOrgSysGlobals.debugFlag: halt
        line = line.replace( '~^~', '\\' ) # Restore our internal formatting codes


        if '#$#' in line: # We need to break the original line into different USFM markers
            #print( "\nMessing with segments: {} {}:{} '{}'".format( BBB, C, V, line ) )
            segments = line.split( '#$#' )
            assert( len(segments) >= 2 )
            #print( " segments (split by backslash):", segments )
            leftovers = ''
            for segment in segments:
                if segment and segment[0] == '\\':
                    bits = segment.split( None, 1 )
                    #print( " bits", bits )
                    marker = bits[0][1:]
                    if len(bits) == 1:
                        #if bits[0] in ('\\p','\\b'):
                        if BibleOrgSysGlobals.USFMMarkers.isNewlineMarker( marker ):
                            if C==1 and V==1 and not appendedCFlag: bookObject.appendLine( 'c', str(C) ); appendedCFlag = True
                            bookObject.appendLine( marker, '' )
                        else:
                            logging.error( "It seems that we had a blank '{}' field in '{}'".format( bits[0], originalLine ) )
                            #halt
                    else:
                        assert( len(bits) == 2 )
                        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                            print( "\n{} {}:{} '{}'".format( BBB, C, V, originalLine ) )
                            print( "line", repr(line) )
                            print( "seg", repr(segment) )
                            print( "segments:", segments )
                            print( "bits", bits )
                            print( "marker", marker )
                            print( "leftovers", repr(leftovers) )
                            assert( marker in ('mt1','mt2','mt3', 's1','s2','s3', 'q1','q2','q3', 'r') )
                        if BibleOrgSysGlobals.USFMMarkers.isNewlineMarker( marker ):
                            bookObject.appendLine( marker, bits[1] )
                        elif not writtenV:
                            bookObject.appendLine( 'v', '{} {}'.format( V, segment ) )
                            writtenV = True
                        else: leftovers += segment
                else: # What is segment is blank (\\NL* at end of line)???
                    if C==1 and V==1 and not appendedCFlag: bookObject.appendLine( 'c', str(C) ); appendedCFlag = True
                    if not writtenV:
                        bookObject.appendLine( 'v', '{} {}'.format( V, leftovers+segment ) )
                        writtenV = True
                    else:
                        bookObject.appendLine( 'v~', leftovers+segment )
                    leftovers = ''
                    #if myGlobals['haveParagraph']:
                        #bookObject.appendLine( 'p', '' )
                        #myGlobals['haveParagraph'] = False
            if leftovers: logging.critical( "Had leftovers {}".format( repr(leftovers) ) )
            if BibleOrgSysGlobals.debugFlag: assert( not leftovers )
            #halt
        else: # no newlines in the middle
            if C==1 and V==1 and not appendedCFlag: bookObject.appendLine( 'c', str(C) ); appendedCFlag = True
            #print( BBB, C, V, repr(line) )
            bookObject.appendLine( 'v', '{} {}'.format( V, line ) )
    # end of ESwordBible.handleLine


    def checkForExtraMaterial( self, cursor, BOS ):
        if BibleOrgSysGlobals.verbosityLevel > 0: print( _("Checking {} for extra material...").format( self.sourceFilepath ) )

        cursor.execute('select * from Bible' )
        for row in cursor:
            assert( len(row) == 4 )
            BBBn, C, V, text = row # First three are integers, the last is a string
            #print( repr(BBBn), repr(C), repr(V), repr(text) )
            if BBBn<1 or BBBn>66: print( "Found book number {}".format( BBBn ) )
            BBB = BibleOrgSysGlobals.BibleBooksCodes.getBBBFromReferenceNumber( BBBn )
            if not BOS.isValidBCVRef( (BBB,str(C),str(V),''), 'checkForExtraMaterial' ):
                logging.error( "checkForExtraMaterial: {} contains {} {}:{} {}".format( self.name, BBB, C, V, repr(text) ) )
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
    # end of ESwordBible.checkForExtraMaterial


    def load( self ):
        """
        Load a single source file and load book elements.
        """
        if BibleOrgSysGlobals.verbosityLevel > 2: print( _("Loading {}...").format( self.sourceFilepath ) )
        loadErrors = []

        fileExtensionUpper = self.fileExtension.upper()
        if fileExtensionUpper not in filenameEndingsToAccept:
            logging.critical( "{} doesn't appear to be a e-Sword file".format( self.sourceFilename ) )
        elif not self.sourceFilename.upper().endswith( BibleFilenameEndingsToAccept[0] ):
            logging.critical( "{} doesn't appear to be a e-Sword Bible file".format( self.sourceFilename ) )

        connection = sqlite3.connect( self.sourceFilepath )
        connection.row_factory = sqlite3.Row # Enable row names
        cursor = connection.cursor()

        # First get the settings
        cursor.execute( 'select * from Details' )
        row = cursor.fetchone()
        for key in row.keys():
            self.settingsDict[key] = row[key]
        #print( self.settingsDict ); halt
        if 'Description' in self.settingsDict and len(self.settingsDict['Description'])<40: self.name = self.settingsDict['Description']
        if 'Abbreviation' in self.settingsDict: self.abbreviation = self.settingsDict['Abbreviation']
        if 'encryption' in self.settingsDict: logging.critical( "{} is encrypted: level {}".format( self.sourceFilename, self.settingsDict['encryption'] ) )


        # Just get some information from the file
        cursor.execute( 'select * from Bible' )
        rows = cursor.fetchall()
        numRows = len(rows)
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>2: print( '{} rows found'.format( numRows ) )
        BBBn1 = rows[0][0]
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>2: print( 'First book number is {}'.format( BBBn1 ) )
        del rows
        BBB1 = None
        if BBBn1 <= 66: BBB1 = BibleOrgSysGlobals.BibleBooksCodes.getBBBFromReferenceNumber( BBBn1 )


        testament = BBB = None
        booksExpected = textLineCountExpected = 0
        if self.settingsDict['OT'] and self.settingsDict['NT']:
            testament, BBB = 'BOTH', 'GEN'
            booksExpected, textLineCountExpected = 66, 31102
        elif self.settingsDict['OT']:
            testament, BBB = 'OT', 'GEN'
            booksExpected, textLineCountExpected = 39, 23145
        elif self.settingsDict['NT']:
            testament, BBB = 'NT', 'MAT'
            booksExpected, textLineCountExpected = 27, 7957
        elif self.settingsDict['Abbreviation'] == 'VIN2011': # Handle encoding error
            logging.critical( "e-Sword settings encoding error -- no testament set: {}".format( self.settingsDict ) )
            loadErrors.append( "e-Sword settings encoding error -- no testament set: {}".format( self.settingsDict ) )
            testament, BBB = 'BOTH', 'GEN'
            booksExpected, textLineCountExpected = 66, 31102
        elif self.settingsDict['Apocrypha']: # incomplete
            testament, BBB = 'AP', 'XXX'
            booksExpected, textLineCountExpected = 99, 999999
            halt
        if not BBB:
            logging.critical( "e-Sword settings encoding error -- no testament set: {}".format( self.settingsDict ) )
            loadErrors.append( "e-Sword settings encoding error -- no testament set: {}".format( self.settingsDict ) )
            if 0:
                cursor.execute( 'select * from Bible' )
                rows = cursor.fetchall()
                print( "rows", len(rows) )
                for row in rows:
                    assert( len(row) == 4 )
                    BBBn, C, V, text = row # First three are integers, the last is a string
                    print( BBBn, C, V, repr(text) )
                    if C==2: break
                del rows # Takes a lot of memory
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>2:
            print( "Testament={} BBB={} BBB1={}, bE={}, tLCE={} nR={}".format( testament, BBB, BBB1, booksExpected, textLineCountExpected, numRows ) )
        if BBB1 != BBB:
            logging.critical( "First book seems wrong: {} instead of {}".format( BBB1, BBB ) )
            loadErrors.append( "First book seems wrong: {} instead of {}".format( BBB1, BBB ) )
            if not BBB: BBB = BBB1
        if numRows != textLineCountExpected:
            logging.critical( "Row count seems wrong: {} instead of {}".format( numRows, textLineCountExpected ) )
            loadErrors.append( "Row count seems wrong: {} instead of {}".format( numRows, textLineCountExpected ) )
        #halt

        BOS = BibleOrganizationalSystem( "GENERIC-KJV-66-ENG" )

        # Create the first book
        thisBook = BibleBook( self, BBB )
        thisBook.objectNameString = "e-Sword Bible Book object"
        thisBook.objectTypeString = "e-Sword"

        verseList = BOS.getNumVersesList( BBB )
        numC, numV = len(verseList), verseList[0]
        nBBB = BibleOrgSysGlobals.BibleBooksCodes.getReferenceNumber( BBB )
        C = V = 1

        bookCount = 0
        ourGlobals = {}
        continued = ourGlobals['haveParagraph'] = False
        haveLines = False
        while True:
            cursor.execute('select Scripture from Bible where Book=? and Chapter=? and Verse=?', (nBBB,C,V) )
            try:
                row = cursor.fetchone()
                line = row[0]
            except: # This reference is missing
                #print( "something wrong at", BBB, C, V )
                #if BibleOrgSysGlobals.debugFlag: halt
                #print( row )
                line = None
            #print ( nBBB, BBB, C, V, 'e-Sw file line is "' + line + '"' )
            if line is None: logging.warning( "ESwordBible.load: Found missing verse line at {} {}:{}".format( BBB, C, V ) )
            else: # line is not None
                if not isinstance( line, str ):
                    if 'encryption' in self.settingsDict:
                        logging.critical( "ESwordBible.load: Unable to decrypt verse line at {} {}:{} {}".format( BBB, C, V, repr(line) ) )
                        break
                    else:
                        logging.critical( "ESwordBible.load: Probably encrypted module: Unable to decode verse line at {} {}:{} {} {}".format( BBB, C, V, repr(line), self.settingsDict ) )
                        break
                elif not line: logging.warning( "ESwordBible.load: Found blank verse line at {} {}:{}".format( BBB, C, V ) )
                else:
                    haveLines = True

                    # Some modules end lines with \r\n or have it in the middle!
                    #   (We just ignore these for now)
                    if '\r' in line or '\n' in line:
                        if BibleOrgSysGlobals.debugFlag:
                            logging.warning( "ESwordBible.load: Found CR or LF characters in verse line at {} {}:{}".format( BBB, C, V ) )
                        #print( repr(line) )
                    while line and line[-1] in '\r\n': line = line[:-1] # Remove CR/LFs from the end
                    line = line.replace( '\r\n', ' ' ).replace( '\r', ' ' ).replace( '\n', ' ' ) # Replace CR/LFs in the middle

            #print( "e-Sword.load", BBB, C, V, repr(line) )
            self.handleLine( self.name, BBB, C, V, line, thisBook, ourGlobals )
            V += 1
            if V > numV:
                C += 1
                if C > numC: # Save this book now
                    if haveLines:
                        if BibleOrgSysGlobals.verbosityLevel > 3: print( "Saving", BBB, bookCount+1 )
                        self.saveBook( thisBook )
                    #else: print( "Not saving", BBB )
                    bookCount += 1 # Not the number saved but the number we attempted to process
                    if bookCount >= booksExpected: break
                    BBB = BOS.getNextBookCode( BBB )
                    # Create the next book
                    thisBook = BibleBook( self, BBB )
                    thisBook.objectNameString = "e-Sword Bible Book object"
                    thisBook.objectTypeString = "e-Sword"
                    haveLines = False

                    verseList = BOS.getNumVersesList( BBB )
                    numC, numV = len(verseList), verseList[0]
                    nBBB = BibleOrgSysGlobals.BibleBooksCodes.getReferenceNumber( BBB )
                    C = V = 1
                    #thisBook.appendLine( 'c', str(C) )
                else: # next chapter only
                    #thisBook.appendLine( 'c', str(C) )
                    numV = verseList[C-1]
                    V = 1

            if ourGlobals['haveParagraph']:
                thisBook.appendLine( 'p', '' )
                ourGlobals['haveParagraph'] = False

        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: self.checkForExtraMaterial( cursor, BOS )
        cursor.close()
        if loadErrors: self.errorDictionary['Load Errors'] = loadErrors
        self.doPostLoadProcessing()
    # end of ESwordBible.load
# end of ESwordBible class



def testeSwB( eSwBfolder, eSwBfilename ):
    # Crudely demonstrate the e-Sword Bible class
    import VerseReferences
    #testFolder = "../../../../../Data/Work/Bibles/e-Sword modules/" # Must be the same as below

    #TUBfolder = os.path.join( eSwBfolder, eSwBfilename )
    if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Demonstrating the e-Sword Bible class...") )
    if BibleOrgSysGlobals.verbosityLevel > 0: print( "  Test folder is {} {}".format( repr(eSwBfolder), repr(eSwBfilename) ) )
    eSwB = ESwordBible( eSwBfolder, eSwBfilename )
    eSwB.load() # Load and process the file
    if BibleOrgSysGlobals.verbosityLevel > 1: print( eSwB ) # Just print a summary
    #print( eSwB.settingsDict )
    if 0 and eSwB:
        if BibleOrgSysGlobals.strictCheckingFlag: eSwB.check()
        for reference in ( ('OT','GEN','1','1'), ('OT','GEN','1','3'), ('OT','PSA','3','0'), ('OT','PSA','3','1'), \
                            ('OT','DAN','1','21'),
                            ('NT','MAT','3','5'), ('NT','JDE','1','4'), ('NT','REV','22','21'), \
                            ('DC','BAR','1','1'), ('DC','MA1','1','1'), ('DC','MA2','1','1',), ):
            (t, b, c, v) = reference
            if t=='OT' and len(eSwB)==27: continue # Don't bother with OT references if it's only a NT
            if t=='NT' and len(eSwB)==39: continue # Don't bother with NT references if it's only a OT
            if t=='DC' and len(eSwB)<=66: continue # Don't bother with DC references if it's too small
            svk = VerseReferences.SimpleVerseKey( b, c, v )
            #print( svk, ob.getVerseDataList( reference ) )
            shortText, verseText = svk.getShortText(), eSwB.getVerseText( svk )
            if BibleOrgSysGlobals.verbosityLevel > 1: print( reference, shortText, verseText )

        # Now export the Bible and compare the round trip
        eSwB.toESword()
        doaResults = eSwB.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
        if BibleOrgSysGlobals.strictCheckingFlag: # Now compare the original and the derived USX XML files
            outputFolder = "OutputFiles/BOS_e-Sword_Reexport/"
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nComparing original and re-exported e-Sword files..." )
            result = BibleOrgSysGlobals.fileCompare( eSwBfilename, eSwBfilename, eSwBfolder, outputFolder )
            if BibleOrgSysGlobals.debugFlag:
                if not result: halt
# end of testeSwB


def demo():
    """
    Main program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( ProgNameVersion )


    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        testFolder = "Tests/DataFilesForTests/e-SwordTest/"
        result1 = ESwordBibleFileCheck( testFolder )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "TestA1", result1 )
        result2 = ESwordBibleFileCheck( testFolder, autoLoad=True )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "TestA2", result2 )


    if 0: # individual modules in the test folder
        testFolder = "../../../../../Data/Work/Bibles/e-Sword modules/"
        names = ('LEB','Dansk_1819','Miles Coverdale (1535)',)
        for j, name in enumerate( names):
            fullname = name + '.bblx'
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "\neSw B{}/ Trying {}".format( j+1, fullname ) )
            testeSwB( testFolder, fullname )
            #halt


    if 1: # individual modules in the output folder
        testFolder = "OutputFiles/BOS_e-SwordExport"
        names = ("Matigsalug",)
        for j, name in enumerate( names):
            fullname = name + '.bblx'
            pathname = os.path.join( testFolder, fullname )
            if os.path.exists( pathname ):
                if BibleOrgSysGlobals.verbosityLevel > 1: print( "\neSw C{}/ Trying {}".format( j+1, fullname ) )
                testeSwB( testFolder, fullname )


    if 0: # all discovered modules in the test folder
        testFolder = "Tests/DataFilesForTests/e-SwordRoundtripTestFiles/"
        foundFolders, foundFiles = [], []
        for something in os.listdir( testFolder ):
            somepath = os.path.join( testFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ) and somepath.endswith('.bblx'):
                if something != 'acc.bblx': # has a corrupted file it seems
                    foundFiles.append( something )

        if BibleOrgSysGlobals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nTrying all {} discovered modules...".format( len(foundFolders) ) )
            parameters = [filename for filename in sorted(foundFiles)]
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.map( testeSwB, parameters ) # have the pool do our loads
                assert( len(results) == len(parameters) ) # Results (all None) are actually irrelevant to us here
        else: # Just single threaded
            for j, someFile in enumerate( sorted( foundFiles ) ):
                if BibleOrgSysGlobals.verbosityLevel > 1: print( "\neSw D{}/ Trying {}".format( j+1, someFile ) )
                #myTestFolder = os.path.join( testFolder, someFolder+'/' )
                testeSwB( testFolder, someFile )
                #break # only do the first one.........temp

    if 0: # all discovered modules in the test folder
        testFolder = "../../../../../Data/Work/Bibles/e-Sword modules/" # Put your test folder here
        foundFolders, foundFiles = [], []
        for something in os.listdir( testFolder ):
            somepath = os.path.join( testFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ) and somepath.endswith('.bblx'): foundFiles.append( something )

        if BibleOrgSysGlobals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nTrying all {} discovered modules...".format( len(foundFolders) ) )
            parameters = [filename for filename in sorted(foundFiles)]
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.map( testeSwB, parameters ) # have the pool do our loads
                assert( len(results) == len(parameters) ) # Results (all None) are actually irrelevant to us here
        else: # Just single threaded
            for j, someFile in enumerate( sorted( foundFiles ) ):
                if BibleOrgSysGlobals.verbosityLevel > 1: print( "\neSw E{}/ Trying {}".format( j+1, someFile ) )
                #myTestFolder = os.path.join( testFolder, someFolder+'/' )
                testeSwB( testFolder, someFile )
                #break # only do the first one.........temp
# end of demo

if __name__ == '__main__':
    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( ProgName, ProgVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    demo()

    BibleOrgSysGlobals.closedown( ProgName, ProgVersion )
# end of ESwordBible.py