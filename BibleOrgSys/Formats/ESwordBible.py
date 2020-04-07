#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# ESwordBible.py
#
# Module handling "e-Sword" Bible module files
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
Module reading and loading e-Sword Bible files.
These can be downloaded from: http://www.BibleSupport.com and http://www.biblemodulesresource.com.

e-Sword Bible modules use RTF internally for formatting.
    See http://en.wikipedia.org/wiki/Rich_Text_Format
    and http://e-sword-users.org/users/node/3969

    Database has one verse per entry (KJV versification)
    OT has 23145 lines
    NT has 7957 lines
    Bible has 31102 lines.

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

from gettext import gettext as _

LAST_MODIFIED_DATE = '2019-02-04' # by RJH
SHORT_PROGRAM_NAME = "e-SwordBible"
PROGRAM_NAME = "e-Sword Bible format handler"
PROGRAM_VERSION = '0.40'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'
programNameVersionDate = f'{programNameVersion} {_("last modified")} {LAST_MODIFIED_DATE}'

debuggingThisModule = False


import logging, os, re
import sqlite3
import multiprocessing

if __name__ == '__main__':
    import sys
    aboveAboveFolderPath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderPath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderPath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.Bible import Bible, BibleBook
from BibleOrgSys.Reference.BibleOrganisationalSystems import BibleOrganisationalSystem



FILENAME_ENDINGS_TO_ACCEPT = ('.BBLX',) # Must be UPPERCASE here
BIBLE_FILENAME_ENDINGS_TO_ACCEPT = ('.BBLX',) # Must be UPPERCASE here



def ESwordBibleFileCheck( givenFolderName, strictCheck=True, autoLoad=False, autoLoadBooks=False ):
    """
    Given a folder, search for e-Sword Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number of Bibles found.

    if autoLoad is true and exactly one e-Sword Bible is found,
        returns the loaded ESwordBible object.
    """
    if BibleOrgSysGlobals.verbosityLevel > 2: print( "ESwordBibleFileCheck( {}, {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad, autoLoadBooks ) )
    if BibleOrgSysGlobals.debugFlag: assert givenFolderName and isinstance( givenFolderName, str )
    if BibleOrgSysGlobals.debugFlag: assert autoLoad in (True,False,)

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( _("ESwordBibleFileCheck: Given {!r} folder is unreadable").format( givenFolderName ) )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( _("ESwordBibleFileCheck: Given {!r} path is not a folder").format( givenFolderName ) )
        return False

    # Find all the files and folders in this folder
    if BibleOrgSysGlobals.verbosityLevel > 3: print( " ESwordBibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
    foundFolders, foundFiles = [], []
    for something in os.listdir( givenFolderName ):
        somepath = os.path.join( givenFolderName, something )
        if os.path.isdir( somepath ):
            if something in BibleOrgSysGlobals.COMMONLY_IGNORED_FOLDERS:
                continue # don't visit these directories
            foundFolders.append( something )
        elif os.path.isfile( somepath ):
            somethingUpper = something.upper()
            somethingUpperProper, somethingUpperExt = os.path.splitext( somethingUpper )
            #ignore = False
            #for ending in filenameEndingsToIgnore:
                #if somethingUpper.endswith( ending): ignore=True; break
            #if ignore: continue
            #if not somethingUpperExt[1:] in extensionsToIgnore: # Compare without the first dot
            if somethingUpperExt in FILENAME_ENDINGS_TO_ACCEPT:
                foundFiles.append( something )

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
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "{} doing autoload of {}…".format( programNameVersion, lastFilenameFound ) )
            eSB = ESwordBible( givenFolderName, lastFilenameFound )
            if autoLoad or autoLoadBooks: eSB.preload()
            if autoLoadBooks: eSB.load() # Load and process the database
            return eSB
        return numFound
    elif looksHopeful and BibleOrgSysGlobals.verbosityLevel > 2: print( "    Looked hopeful but no actual files found" )

    # Look one level down
    numFound = 0
    foundProjects = []
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
        if not os.access( tryFolderName, os.R_OK ): # The subfolder is not readable
            logging.warning( _("ESwordBibleFileCheck: {!r} subfolder is unreadable").format( tryFolderName ) )
            continue
        if BibleOrgSysGlobals.verbosityLevel > 3: print( "    ESwordBibleFileCheck: Looking for files in {!r}".format( tryFolderName ) )
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
                if somethingUpperExt in FILENAME_ENDINGS_TO_ACCEPT:
                    foundSubfiles.append( something )

        # See if there's an e-Sword project here in this folder
        for thisFilename in sorted( foundSubfiles ):
            foundProjects.append( (tryFolderName, thisFilename,) )
            lastFilenameFound = thisFilename
            numFound += 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "ESwordBibleFileCheck foundProjects", numFound, foundProjects )
        if numFound == 1 and (autoLoad and autoLoadBooks):
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "{} doing autoload of {}…".format( programNameVersion, foundProjects[0][1] ) )
            if BibleOrgSysGlobals.debugFlag: assert len(foundProjects) == 1
            eSB = ESwordBible( foundProjects[0][0], foundProjects[0][1] )
            if autoLoad or autoLoadBooks: eSB.preload()
            if autoLoadBooks: eSB.load() # Load and process the database
            return eSB
        return numFound
# end of ESwordBibleFileCheck



def handleRTFLine( self, myName, BBB, C, V, originalLine, bookObject, myGlobals ):
    """
    self here is a BibleObject

    Adjusts the formatting of the RTF line for Bible reference BBB C:V
        and then writes it to the bookObject.

    C and V might be strings or integers

    Try to convert display formatting to semantic formatting as much as possible

    myGlobals dict contains flags.

    Appends pseudo-USFM results to the supplied bookObject.

    NOTE: originalLine can be None here.

    NOTE: There are no checks in here yet to discover nested character-formatting markers.  :-(
    """
    if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
        #if debuggingThisModule:
        print( "ESwordModule.handleRTFLine( {} {} {}:{} {!r} … {}".format( myName, BBB, C, V, originalLine, myGlobals ) )
        assert originalLine is None or '\r' not in originalLine
    #print( "ESwordModule.handleRTFLine: {} {}:{} {!r}".format( BBB, C, V, originalLine ) )
    line = originalLine

    writtenV = False
    if V==1: appendedCFlag = False
    if C!=1 and V==1: bookObject.addLine( 'c', str(C) ); appendedCFlag = True

    # It seems that some commentaries can have newlines in the entries
    line = line.replace( '\n', '#$#' ) # Replace \n with our temporary newline sequence

    # Now we have to convert RTF codes to our internal codes
    # First do special characters
    line = line.replace( '\\ldblquote', '“' ).replace( '\\rdblquote', '”' ) \
                .replace( '\\lquote', '‘' ).replace( '\\rquote', '’' ) \
                .replace( '\\emdash', '—' ).replace( '\\endash', '–' )
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
        match = re.search( r'\\u[1-2][0-9][0-9]\?', line )
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
    line = re.sub( r'\\cf6\\super (.{1,5})\\cf1\\nosupersub[ —”]', r'~^~ord \1~^~ord*', line ) # For Free Bible -- ordinal gives superscript
    line = re.sub( r'\\cf6\\super (.{1,5})\\cf0\\i0\\b0\\ulnone\\nosupersub', r'~^~ord \1~^~ord*', line ) # For Free Bible at end of line -- ordinal gives superscript

    # Stuff to just remove -- not sure what most of this RTF stuff is about yet
    while True:
        line = line.lstrip()
        changed = False
        for stuff in ( '\\viewkind4', '\\uc1', '\\nowidctlpar',
                '\\paperw12240', '\\paperh15840',
                '\\fi-360','\\li360',
                '\\tx360','\\tx720', '\\tx1440', '\\tx2160' '\\tx2880', '\\tx3600', '\\tx4320','\\tx5040','\\tx5760','\\tx6480','\\tx7200', '\\tx7920', '\\tx8640', '\\tx9360', '\\tx10080',
                '\\margl1440', '\\margt1440', '\\margr1440', '\\margb1440', '\\deftab1134', '\\widowctrl',
                '\\formshade', '\\sectd', '\\pard', '\\keepn',
                '\\headery720', '\\footery720', '\\pgwsxn12240', '\\pghsxn15840', '\\marglsxn1800',
                '\\margtsxn1440', '\\margrsxn1800', '\\margbsxn1440', '\\pgbrdropt32',
                '\\s17', '\\s1', '\\sa120','\\sb120'
                '\\itap0', '\\nosupersub', '\\ulnone',
                '\\cf15','\\cf14','\\cf10', '\\cf1','\\cf0',
                '\\lang1030', '\\lang1033', '\\f0', '\\i0', '\\b0', ):
            if line.startswith( stuff ): line = line[len(stuff):]; changed = True
            #print( "stuff", repr(stuff) )
            #print( "line", repr(line[:20]) )
            #if line.startswith( '\\pd' ): halt
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
    line = re.sub( r'{\\cf15\\I (.+?)}', r'~^~add \1~^~add*', line )
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
    line = line.replace( '\\i ', '~^~it ' ).replace( '\\i1', '~^~it ' ).replace( '\\i0', '~^~it*' )

    # Not sure what this is
    line = re.sub( r'{\\cf2\\super (.+?)}', r'', line ) # Notes like '[2]' -- deleted for now
    line = line.replace( '\\cf2  \\cf0', '' ) # LEB
    line = line.replace( '\\cf0 ', '' ) # Calvin
    line = line.replace( '\\loch\\f0', '' ).replace( '\\hich\\f0', '' ) # Calvin

    line = line.replace( '\\par\\par', '\\par' )
    #line = line.replace( '\\par', '#$#~^~p' ) # Hits \\pard wrongly
    line = re.sub( r'\\par([^d])', r'#$#~^~p\1', line )
    line = line.replace( '\\m ', '#$#~^~m ' )

    # Handle module formatting errors -- formatting that goes across verses!
    line = line.replace( '{\\cf2\\super [ ','[ ' ) # In one module Luke 22:42 -- weird
    line = line.replace( '{\\cf 2 [','[' ) # In one module John 1:4 -- weird
    line = line.replace( ']}',']' ) # In one module Luke 22:44; 23:34 -- weird
    if myName=="Lexham English Bible": line = line.replace( '\\cf14 ','') # Not sure what this is in LEB

    # Handle other left-overs
    line = line \
                .replace( '\\pard', '' ) \
                .replace( '\\keepn', '' ) \
                .replace( '\\sa120', '' ) \
                .replace( '\\sb120', '' )

    # Check what's left at the end
    line = line.replace( '\\line', '#$#' ) # Use this for our newline marker
    line = line.strip() # There seem to be extra spaces in many modules
    if '\\' in line or '{' in line or '}' in line:
        if BibleOrgSysGlobals.debugFlag:
            logging.error( "{} original line: {!r}".format( myName, originalLine ) )
            logging.error( "Saved line: {!r}".format( savedLine ) )
        logging.error( "ESwordModule.load: Doesn't handle {} {}:{} formatted line yet: {!r}".format( BBB, C, V, line ) )
        if 1: # Unhandled stuff -- not done properly yet… xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
            line = re.sub( '<(.+?)>', '', line ) # Remove all remaining sets of angle brackets
        if 0 and BibleOrgSysGlobals.debugFlag: halt
    line = line.replace( '~^~', '\\' ) # Restore our internal formatting codes


    if '#$#' in line: # We need to break the original line into different USFM markers
        #print( "\nMessing with segments: {} {}:{} {!r}".format( BBB, C, V, line ) )
        segments = line.split( '#$#' )
        assert len(segments) >= 2
        #print( " segments (split by backslash):", segments )
        leftovers = ''
        for segment in segments:
            if segment and segment[0] == '\\':
                bits = segment.split( None, 1 )
                #print( " bits", bits )
                marker = bits[0][1:]
                if len(bits) == 1:
                    #if bits[0] in ('\\p','\\b'):
                    if BibleOrgSysGlobals.loadedUSFMMarkers.isNewlineMarker( marker ):
                        if C==1 and V==1 and not appendedCFlag: bookObject.addLine( 'c', str(C) ); appendedCFlag = True
                        bookObject.addLine( marker, '' )
                    else:
                        logging.error( "It seems that we had a blank {!r} field in {!r}".format( bits[0], originalLine ) )
                        #halt
                else:
                    assert len(bits) == 2
                    if 0 and BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                        print( "\n{} {}:{} {!r}".format( BBB, C, V, originalLine ) )
                        print( "line", repr(line) )
                        print( "seg", repr(segment) )
                        print( "segments:", segments )
                        print( "bits", bits )
                        print( "marker", marker )
                        print( "leftovers", repr(leftovers) )
                    if BibleOrgSysGlobals.loadedUSFMMarkers.isNewlineMarker( marker ):
                        if BibleOrgSysGlobals.debugFlag:
                            assert marker in ('mt1','mt2','mt3', 's1','s2','s3', 'p', 'q1','q2','q3', 'm', 'r', 'b',)
                        bookObject.addLine( marker, bits[1] )
                    elif not writtenV:
                        bookObject.addLine( 'v', '{} \\{} {}'.format( V, marker, segment ) )
                        writtenV = True
                    else: leftovers += '\\{} {}'.format( marker, segment )
            else: # What is segment is blank (\\NL* at end of line)???
                if C==1 and V==1 and not appendedCFlag: bookObject.addLine( 'c', str(C) ); appendedCFlag = True
                if not writtenV:
                    bookObject.addLine( 'v', '{} {}'.format( V, leftovers+segment ) )
                    writtenV = True
                else:
                    bookObject.addLine( 'v~', leftovers+segment )
                leftovers = ''
                #if myGlobals['haveParagraph']:
                    #bookObject.addLine( 'p', '' )
                    #myGlobals['haveParagraph'] = False
        if leftovers:
            if 1 or BibleOrgSysGlobals.debugFlag or debuggingThisModule:
                logging.critical( "ESwordModule.handleRTFLine: Had leftovers {!r} from {!r}".format( leftovers, originalLine ) )
            else:
                logging.critical( "ESwordModule.handleRTFLine: Had leftovers {!r}".format( leftovers ) )
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag: assert not leftovers
    else: # no newlines in the middle
        if C in (0,'0') and V in (0,'0'):
            bookObject.addLine( 'ip', line )
        else:
            if C==1 and V==1 and not appendedCFlag: bookObject.addLine( 'c', str(C) ); appendedCFlag = True
            #print( BBB, C, V, repr(line) )
            bookObject.addLine( 'v', '{} {}'.format( V, line ) )
# end of ESwordModule.handleRTFLine


def handleHTMLLine( self, myName, BBB, C, V, originalLine, bookObject, myGlobals ):
    """
    self here is a BibleObject

    Adjusts the formatting of the RTF line for Bible reference BBB C:V
        and then writes it to the bookObject.

    C and V might be strings or integers

    Try to convert display formatting to semantic formatting as much as possible

    myGlobals dict contains flags.

    Appends pseudo-USFM results to the supplied bookObject.

    NOTE: originalLine can be None here.

    NOTE: There are no checks in here yet to discover nested character-formatting markers.  :-(
    """
    if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
        #if debuggingThisModule:
            #print( "ESwordModule.handleHTMLLine( {} {} {}:{} {!r} … {}".format( myName, BBB, C, V, originalLine, myGlobals ) )
        assert originalLine is None or '\r' not in originalLine
    #print( "ESwordModule.handleHTMLLine: {} {}:{} {!r}".format( BBB, C, V, originalLine ) )
    line = originalLine

    if line and line[0]=='\n': line = line[1:] # Remove leading newline
    if line and line[-1]=='\n': line = line[:-1] # Remove trailing newline
    line = line.replace( '\n', '<br />' )

    writtenV = False
    if V==1: appendedCFlag = False
    if C!=1 and V==1: bookObject.addLine( 'c', str(C) ); appendedCFlag = True

    if '#$#' in line: # We need to break the original line into different USFM markers
        #print( "\nMessing with segments: {} {}:{} {!r}".format( BBB, C, V, line ) )
        segments = line.split( '#$#' )
        assert len(segments) >= 2
        #print( " segments (split by backslash):", segments )
        leftovers = ''
        for segment in segments:
            if segment and segment[0] == '\\':
                bits = segment.split( None, 1 )
                #print( " bits", bits )
                marker = bits[0][1:]
                if len(bits) == 1:
                    #if bits[0] in ('\\p','\\b'):
                    if BibleOrgSysGlobals.loadedUSFMMarkers.isNewlineMarker( marker ):
                        if C==1 and V==1 and not appendedCFlag: bookObject.addLine( 'c', str(C) ); appendedCFlag = True
                        bookObject.addLine( marker, '' )
                    else:
                        logging.error( "It seems that we had a blank {!r} field in {!r}".format( bits[0], originalLine ) )
                        #halt
                else:
                    assert len(bits) == 2
                    if 0 and BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                        print( "\n{} {}:{} {!r}".format( BBB, C, V, originalLine ) )
                        print( "line", repr(line) )
                        print( "seg", repr(segment) )
                        print( "segments:", segments )
                        print( "bits", bits )
                        print( "marker", marker )
                        print( "leftovers", repr(leftovers) )
                    if BibleOrgSysGlobals.loadedUSFMMarkers.isNewlineMarker( marker ):
                        if BibleOrgSysGlobals.debugFlag:
                            assert marker in ('mt1','mt2','mt3', 's1','s2','s3', 'p', 'q1','q2','q3', 'm', 'r', 'b',)
                        bookObject.addLine( marker, bits[1] )
                    elif not writtenV:
                        bookObject.addLine( 'v', '{} \\{} {}'.format( V, marker, segment ) )
                        writtenV = True
                    else: leftovers += '\\{} {}'.format( marker, segment )
            else: # What is segment is blank (\\NL* at end of line)???
                if C==1 and V==1 and not appendedCFlag: bookObject.addLine( 'c', str(C) ); appendedCFlag = True
                if not writtenV:
                    bookObject.addLine( 'v', '{} {}'.format( V, leftovers+segment ) )
                    writtenV = True
                else:
                    bookObject.addLine( 'v~', leftovers+segment )
                leftovers = ''
                #if myGlobals['haveParagraph']:
                    #bookObject.addLine( 'p', '' )
                    #myGlobals['haveParagraph'] = False
        if leftovers: logging.critical( "ESwordModule.handleRTFLine: Had leftovers {!r}".format( leftovers ) )
        if BibleOrgSysGlobals.debugFlag: assert not leftovers
        #halt
    else: # no newlines in the middle
        if C in (0,'0') and V in (0,'0'):
            bookObject.addLine( 'ip', line )
        else:
            if C==1 and V==1 and not appendedCFlag: bookObject.addLine( 'c', str(C) ); appendedCFlag = True
            #print( BBB, C, V, repr(line) )
            bookObject.addLine( 'v', '{} {}'.format( V, line ) )
# end of ESwordModule.handleHTMLLine


def handleESwordLine( self, myName, BBB, C, V, originalLine, bookObject, myGlobals ):
    """
    self here is a BibleObject

    Adjusts the formatting of the RTF line for Bible reference BBB C:V
        and then writes it to the bookObject.

    C and V might be strings or integers

    Try to convert display formatting to semantic formatting as much as possible

    myGlobals dict contains flags.

    Appends pseudo-USFM results to the supplied bookObject.

    NOTE: originalLine can be None here.

    NOTE: There are no checks in here yet to discover nested character-formatting markers.  :-(
    """
    if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag:
        if debuggingThisModule:
            print( "ESwordModule.handleESwordLine( {} {} {}:{} {!r} … {}".format( myName, BBB, C, V, originalLine, myGlobals ) )
        assert originalLine is None or '\r' not in originalLine

    #print( "ESwordModule.handleESwordLine: {} {}:{} {!r}".format( BBB, C, V, originalLine ) )
    if originalLine is None: # We don't have an entry for this C:V
        return

    if '<span ' in originalLine or '<p ' in originalLine: # Seems to be HTML
        handleHTMLLine( self, myName, BBB, C, V, originalLine, bookObject, myGlobals )
        return
    elif '\\viewkind' in originalLine or '\\uc1' in originalLine \
    or '\\paper' in originalLine or '\\par' in originalLine: # Seems to be RTF
        handleRTFLine( self, myName, BBB, C, V, originalLine, bookObject, myGlobals )
        return
    else:
        if debuggingThisModule:
            print( "ESwordModule.handleESwordLine: What's this: {} {} {}:{} {!r}".format( myName, BBB, C, V, originalLine ) )
            if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag: halt # What's this???
        bookObject.addLine( 'v', '{} {}'.format( V, originalLine ) )
# end of ESwordModule.handleESwordLine



class ESwordBible( Bible ):
    """
    Class for reading, validating, and converting ESwordBible files.
    """
    def __init__( self, sourceFolder, givenFilename, encoding='utf-8' ):
        """
        Constructor: just sets up the Bible object.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "ESwordBible.init( {!r}, {!r}, {!r} )".format( sourceFolder, givenFilename, encoding ) )

         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = 'e-Sword Bible object'
        self.objectTypeString = 'e-Sword-Bible'

        # Now we can set our object variables
        self.sourceFolder, self.sourceFilename, self.encoding = sourceFolder, givenFilename, encoding
        self.sourceFilepath =  os.path.join( self.sourceFolder, self.sourceFilename )

        # Do a preliminary check on the readability of our file
        if not os.access( self.sourceFilepath, os.R_OK ):
            logging.critical( _("ESwordBible: File {!r} is unreadable").format( self.sourceFilepath ) )

        filenameBits = os.path.splitext( self.sourceFilename )
        self.name = filenameBits[0]
        self.fileExtension = filenameBits[1]

        #if self.fileExtension.upper().endswith('X'):
            #logging.warning( _("ESwordBible: File {!r} is encrypted").format( self.sourceFilepath ) )
        self.preloaded = False
    # end of ESwordBible.__init__


    #def handleRTFLine( self, myName, BBB, C, V, originalLine, bookObject, myGlobals ):
        #"""
        #Adjusts the formatting of the RTF line for Bible reference BBB C:V
            #and then writes it to the bookObject.

        #Try to convert display formatting to semantic formatting as much as possible

        #myGlobals dict contains flags.

        #Appends pseudo-USFM results to the supplied bookObject.

        #NOTE: originalLine can be None here.

        #NOTE: There are no checks in here yet to discover nested character-formatting markers.  :-(
        #"""
        #if BibleOrgSysGlobals.debugFlag:
            #if 0 and debuggingThisModule:
                #print( "ESwordBible.handleRTFLine( {} {} {}:{} {!r} … {}".format( myName, BBB, C, V, originalLine, myGlobals ) )
            #assert originalLine is None or ('\n' not in originalLine and '\r' not in originalLine )

        ##print( BBB, C, V, repr(originalLine) )
        #line = originalLine

        #writtenV = False
        #if V==1: appendedCFlag = False
        #if C!=1 and V==1: bookObject.addLine( 'c', str(C) ); appendedCFlag = True

        #if line is None: # We don't have an entry for this C:V
            #return

        ## Now we have to convert RTF codes to our internal codes
        ## First do special characters
        #line = line.replace( '\\ldblquote', '“' ).replace( '\\rdblquote', '”' ).replace( '\\lquote', '‘' ).replace( '\\rquote', '’' )
        #line = line.replace( '\\emdash', '—' ).replace( '\\endash', '–' )
        ## Now do Unicode characters
        #while True: # Find patterns like \\'d3
            #match = re.search( r"\\'[0-9a-f][0-9a-f]", line )
            #if not match: break
            ##print( originalLine )
            ##print( line )
            ##h1, h2 = line[match.start()+2], line[match.start()+3]
            #i = int( line[match.start()+2:match.end()], 16 ) # Convert two hex characters to decimal
            ##print( h1, h2, i, chr(i) )
            #line = line[:match.start()] + chr( i ) + line[match.end():]
            ##print( line )
            ##print( repr(line) )
        #while True: # Find patterns like \\u253?
            #match = re.search( r"\\u[1-2][0-9][0-9]\?", line )
            #if not match: break
            ##print( originalLine )
            ##print( line )
            ##h1, h2 = line[match.start()+2], line[match.start()+3]
            #i = int( line[match.start()+2:match.end()-1] ) # Convert three digits to decimal
            ##print( h1, h2, i, chr(i) )
            #line = line[:match.start()] + chr( i ) + line[match.end():]
            ##print( line )
            ##print( repr(line) )

        ## We will temporarily use ~^~ instead of backslash so we can distinguish our own codes from the RTF codes
        ## Try to guess some semantic formatting
        ##line = re.sub( r'\\cf14 (.+?)\\cf0', r'~^~add \1~^~add*', line )
        ##line = re.sub( r'\\cf15\\i (.+?)\\cf0\\i0', r'~^~add \1~^~add*', line )

        ## Stuff to just remove -- not sure what most of this is about yet
        #while True:
            #line = line.lstrip()
            #changed = False
            #for stuff in ( '\\viewkind4', '\\uc1', '\\nowidctlpar',
                    #'\\paperw12240', '\\paperh15840',
                    #'\\tx720', '\\tx1440', '\\tx2160' '\\tx2880', '\\tx3600', '\\tx4320', '\\tx5040', '\\tx5760', '\\tx6480', '\\tx7200', '\\tx7920', '\\tx8640', '\\tx9360', '\\tx10080',
                    #'\\margl1440', '\\margt1440', '\\margr1440', '\\margb1440', '\\deftab1134', '\\widowctrl',
                    #'\\formshade', '\\sectd',
                    #'\\headery720', '\\footery720', '\\pgwsxn12240', '\\pghsxn15840', '\\marglsxn1800',
                    #'\\margtsxn1440', '\\margrsxn1800', '\\margbsxn1440', '\\pgbrdropt32', '\\s17',
                    #'\\itap0', '\\nosupersub', '\\ulnone',
                    #'\\cf15', '\\cf14', '\\cf10', '\\cf0', '\\lang1030', '\\lang1033', '\\f0', '\\i0', '\\b0', ):
                #if line.startswith( stuff ): line = line[len(stuff):]; changed = True
            #if not changed: break
        #for stuff in ( '\\nosupersub', '\\ulnone', '\\b0', '\\i0', '\\cf0', ):
            #if line.endswith( stuff ): line = line[:-len(stuff)]
        #if BibleOrgSysGlobals.debugFlag: savedLine = line

        ## Try to guess some semantic formatting
        #line = re.sub( r'\\b\\i\\f0 (.+?)\\cf0\\b0\\i0\\line', r'~^~s1 \1*#$#', line ) # section heading
        #line = re.sub( r'\\cf10\\b\\i (.+?)\\cf0\\b0\\i0\\line', r'~^~s1 \1*#$#', line ) # section heading in LEB
        #line = re.sub( r'\\cf14 (.+?)\\cf0', r'~^~add \1~^~add*', line )
        #line = re.sub( r'\\cf15\\i (.+?)\\cf0\\i0', r'~^~add \1~^~add*', line )
        #line = re.sub( r'\\cf15\\i(.+?)\\cf0\\i0 ', r'~^~add \1~^~add*', line ) # LEB (error???)
        #line = re.sub( r'^\\i (.+?)\\cf0\\i0 ', r'~^~add \1~^~add*', line ) # LEB (error???)
        #line = re.sub( r'{\\cf15\\I (.+?)}', r'~^~add \1~^~add*', line )
        #line = re.sub( r'{\\cf15 (.+?)}', r'~^~add \1~^~add*', line )
        #line = re.sub( r'\\i\\f0 (.+?)\\cf0\\i0', r'~^~add \1~^~add*', line )

        ## Unfortunately, it's all display formatting, no semantic formatting  :-(
        ## NOTE: This doesn't handle nesting yet
        #line = re.sub( r'{\\cf10\\b\\i (.+?)\\cf0\\b0\\i0', r'~^~bdit \1~^~bdit*', line )
        #line = re.sub( r'{\\b (.+?)}', r'~^~bd \1~^~bd*', line )
        #line = re.sub( r'{\\cf15\\i (.+?)}', r'~^~it \1~^~it*', line )
        #line = re.sub( r'{\\cf10\\i (.+?)}', r'~^~it \1~^~it*', line ) # What is different about these?
        #line = re.sub( r'{\\cf2\\i (.+?)}', r'~^~it \1~^~it*', line )
        #line = re.sub( r'{\\i (.+?)}', r'~^~it \1~^~it*', line )
        #line = re.sub( r'{\\i(.+?)}', r'~^~it \1~^~it*', line ) # Also occurs without the space in some modules
        #line = re.sub( r'{\\qc (.+?)}', r'~^~qc \1~^~qc*', line )

        #line = line.replace( '\\b1', '~^~bd ' ).replace( '\\b0', '~^~bd*' )
        #line = line.replace( '\\cf15\\i ', '~^~+it ' ).replace( '\\cf14\\i0', '~^~it*' ) # Attempt to handle some nesting in LEB
        #line = line.replace( '\\i ', '~^~it ' ).replace( '\\i1', '~^~it ' ).replace( '\\i0', '~^~it*' )

        ## Not sure what this is
        #line = re.sub( r'{\\cf2\\super (.+?)}', r'', line ) # Notes like '[2]' -- deleted for now
        #line = line.replace( '\\cf2  \\cf0', '' ) # LEB
        #line = line.replace( '\\cf0 ', '' ) # Calvin
        #line = line.replace( '\\loch\\f0', '' ).replace( '\\hich\\f0', '' ) # Calvin

        #line = line.replace( '\\par\\par', '#$#~^~p' )
        #line = line.replace( '\\par', '#$#~^~p' )
        #line = line.replace( '\\m ', '#$#~^~m ' )

        ## Handle module formatting errors -- formatting that goes across verses!
        #line = line.replace( '{\\cf2\\super [ ','[ ' ) # In one module Luke 22:42 -- weird
        #line = line.replace( '{\\cf 2 [','[' ) # In one module John 1:4 -- weird
        #line = line.replace( ']}',']' ) # In one module Luke 22:44; 23:34 -- weird
        #if myName=="Lexham English Bible": line = line.replace( '\\cf14 ','') # Not sure what this is in LEB

        ## Check what's left at the end
        #line = line.replace( '\\line', '#$#' ) # Use this for our newline marker
        #line = line.strip() # There seem to be extra spaces in many modules
        #if '\\' in line or '{' in line or '}' in line:
            #if BibleOrgSysGlobals.debugFlag:
                #logging.error( "{} original line: {!r}".format( myName, originalLine ) )
                #logging.error( "Saved line: {!r}".format( savedLine ) )
            #logging.error( "ESwordBible.load: Doesn't handle {} {}:{} formatted line yet: {!r}".format( BBB, C, V, line ) )
            #if 1: # Unhandled stuff -- not done properly yet… xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
                #line = re.sub( '<(.+?)>', '', line ) # Remove all remaining sets of angle brackets
            #if 0 and BibleOrgSysGlobals.debugFlag: halt
        #line = line.replace( '~^~', '\\' ) # Restore our internal formatting codes


        #if '#$#' in line: # We need to break the original line into different USFM markers
            ##print( "\nMessing with segments: {} {}:{} {!r}".format( BBB, C, V, line ) )
            #segments = line.split( '#$#' )
            #assert len(segments) >= 2
            ##print( " segments (split by backslash):", segments )
            #leftovers = ''
            #for segment in segments:
                #if segment and segment[0] == '\\':
                    #bits = segment.split( None, 1 )
                    ##print( " bits", bits )
                    #marker = bits[0][1:]
                    #if len(bits) == 1:
                        ##if bits[0] in ('\\p','\\b'):
                        #if BibleOrgSysGlobals.loadedUSFMMarkers.isNewlineMarker( marker ):
                            #if C==1 and V==1 and not appendedCFlag: bookObject.addLine( 'c', str(C) ); appendedCFlag = True
                            #bookObject.addLine( marker, '' )
                        #else:
                            #logging.error( "It seems that we had a blank {!r} field in {!r}".format( bits[0], originalLine ) )
                            ##halt
                    #else:
                        #assert len(bits) == 2
                        #if 0 and BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                            #print( "\n{} {}:{} {!r}".format( BBB, C, V, originalLine ) )
                            #print( "line", repr(line) )
                            #print( "seg", repr(segment) )
                            #print( "segments:", segments )
                            #print( "bits", bits )
                            #print( "marker", marker )
                            #print( "leftovers", repr(leftovers) )
                        #if BibleOrgSysGlobals.loadedUSFMMarkers.isNewlineMarker( marker ):
                            #if BibleOrgSysGlobals.debugFlag:
                                #assert marker in ('mt1','mt2','mt3', 's1','s2','s3', 'p', 'q1','q2','q3', 'm', 'r', 'b',)
                            #bookObject.addLine( marker, bits[1] )
                        #elif not writtenV:
                            #bookObject.addLine( 'v', '{} \\{} {}'.format( V, marker, segment ) )
                            #writtenV = True
                        #else: leftovers += '\\{} {}'.format( marker, segment )
                #else: # What is segment is blank (\\NL* at end of line)???
                    #if C==1 and V==1 and not appendedCFlag: bookObject.addLine( 'c', str(C) ); appendedCFlag = True
                    #if not writtenV:
                        #bookObject.addLine( 'v', '{} {}'.format( V, leftovers+segment ) )
                        #writtenV = True
                    #else:
                        #bookObject.addLine( 'v~', leftovers+segment )
                    #leftovers = ''
                    ##if myGlobals['haveParagraph']:
                        ##bookObject.addLine( 'p', '' )
                        ##myGlobals['haveParagraph'] = False
            #if leftovers: logging.critical( "Had leftovers {!r}".format( leftovers ) )
            #if BibleOrgSysGlobals.debugFlag: assert not leftovers
            ##halt
        #else: # no newlines in the middle
            #if C==1 and V==1 and not appendedCFlag: bookObject.addLine( 'c', str(C) ); appendedCFlag = True
            ##print( BBB, C, V, repr(line) )
            #bookObject.addLine( 'v', '{} {}'.format( V, line ) )
    ## end of ESwordBible.handleRTFLine


    def checkForExtraMaterial( self, cursor, BOS ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( _("checkForExtraMaterial( …, … )") )

        if BibleOrgSysGlobals.verbosityLevel > 0: print( _("Checking {} for extra material…").format( self.sourceFilepath ) )

        cursor.execute('select * from Bible' )
        for row in cursor:
            assert len(row) == 4
            BBBn, C, V, text = row # First three are integers, the last is a string
            #print( repr(BBBn), repr(C), repr(V), repr(text) )
            if BBBn<1 or BBBn>66: print( "Found book number {}".format( BBBn ) )
            BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromReferenceNumber( BBBn )
            if not BOS.isValidBCVRef( (BBB,str(C),str(V),''), 'checkForExtraMaterial' ):
                logging.error( "checkForExtraMaterial: {} contains {} {}:{} {!r}".format( self.name, BBB, C, V, text ) )
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                    print( "checkForExtraMaterial: {} contains {} {}:{} {!r}".format( self.name, BBB, C, V, text ) )
                    #halt
    # end of ESwordBible.checkForExtraMaterial


    def preload( self ):
        """
        Load Bible details out of the SQLite3 database.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( "preload()" )

        if BibleOrgSysGlobals.verbosityLevel > 2: print( _("Preloading {}…").format( self.sourceFilepath ) )
        loadErrors = []

        fileExtensionUpper = self.fileExtension.upper()
        if fileExtensionUpper not in FILENAME_ENDINGS_TO_ACCEPT:
            logging.critical( "{} doesn't appear to be a e-Sword file".format( self.sourceFilename ) )
        elif not self.sourceFilename.upper().endswith( BIBLE_FILENAME_ENDINGS_TO_ACCEPT[0] ):
            logging.critical( "{} doesn't appear to be a e-Sword Bible file".format( self.sourceFilename ) )

        connection = sqlite3.connect( self.sourceFilepath )
        connection.row_factory = sqlite3.Row # Enable row names
        self.cursor = connection.cursor()

        # First get the settings
        if self.suppliedMetadata is None: self.suppliedMetadata = {}
        self.suppliedMetadata['e-Sword-Bible'] = {}
        self.cursor.execute( 'select * from Details' )
        row = self.cursor.fetchone()
        for key in row.keys():
            self.suppliedMetadata['e-Sword-Bible'][key] = row[key]
        #print( self.suppliedMetadata['e-Sword-Bible'] ); halt
        #if 'Description' in self.settingsDict and len(self.settingsDict['Description'])<40: self.name = self.settingsDict['Description']
        #if 'Abbreviation' in self.settingsDict: self.abbreviation = self.settingsDict['Abbreviation']
        if 'encryption' in self.suppliedMetadata['e-Sword-Bible']:
            logging.critical( "{} is encrypted: level {}".format( self.sourceFilename, self.suppliedMetadata['e-Sword-Bible']['encryption'] ) )


        ## Just get some information from the file
        #self.cursor.execute( 'select * from Bible' )
        #rows = self.cursor.fetchall()
        #numRows = len(rows)
        #if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>2: print( '{} rows found'.format( numRows ) )
        #BBBn1 = rows[0][0]
        #if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>2: print( 'First book number is {}'.format( BBBn1 ) )
        #del rows
        #BBB1 = None
        #if BBBn1 <= 66: BBB1 = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromReferenceNumber( BBBn1 )


        #testament = BBB = None
        #booksExpected = textLineCountExpected = 0
        #if self.suppliedMetadata['e-Sword-Bible']['OT'] and self.suppliedMetadata['e-Sword-Bible']['NT']:
            #testament, BBB = 'BOTH', 'GEN'
            #booksExpected, textLineCountExpected = 66, 31102
        #elif self.suppliedMetadata['e-Sword-Bible']['OT']:
            #testament, BBB = 'OT', 'GEN'
            #booksExpected, textLineCountExpected = 39, 23145
        #elif self.suppliedMetadata['e-Sword-Bible']['NT']:
            #testament, BBB = 'NT', 'MAT'
            #booksExpected, textLineCountExpected = 27, 7957
        #elif self.suppliedMetadata['e-Sword-Bible']['Abbreviation'] == 'VIN2011': # Handle encoding error
            #logging.critical( "e-Sword settings encoding error -- no testament set: {}".format( self.suppliedMetadata['e-Sword-Bible'] ) )
            #loadErrors.append( "e-Sword settings encoding error -- no testament set: {}".format( self.suppliedMetadata['e-Sword-Bible'] ) )
            #testament, BBB = 'BOTH', 'GEN'
            #booksExpected, textLineCountExpected = 66, 31102
        #elif self.suppliedMetadata['e-Sword-Bible']['Apocrypha']: # incomplete
            #testament, BBB = 'AP', 'XXX'
            #booksExpected, textLineCountExpected = 99, 999999
            #halt
        #if not BBB:
            #logging.critical( "e-Sword settings encoding error -- no testament set: {}".format( self.suppliedMetadata['e-Sword-Bible'] ) )
            #loadErrors.append( "e-Sword settings encoding error -- no testament set: {}".format( self.suppliedMetadata['e-Sword-Bible'] ) )
            #if 0:
                #cursor.execute( 'select * from Bible' )
                #rows = cursor.fetchall()
                #print( "rows", len(rows) )
                #for row in rows:
                    #assert len(row) == 4
                    #BBBn, C, V, text = row # First three are integers, the last is a string
                    #print( BBBn, C, V, repr(text) )
                    #if C==2: break
                #del rows # Takes a lot of memory
        #if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>2:
            #print( "Testament={} BBB={} BBB1={}, bE={}, tLCE={} nR={}".format( testament, BBB, BBB1, booksExpected, textLineCountExpected, numRows ) )
        #if BBB1 != BBB:
            #logging.critical( "First book seems wrong: {} instead of {}".format( BBB1, BBB ) )
            #loadErrors.append( "First book seems wrong: {} instead of {}".format( BBB1, BBB ) )
            #if not BBB: BBB = BBB1
        #if numRows != textLineCountExpected:
            #logging.critical( "Row count for {} seems wrong: {} instead of {}".format( self.sourceFilename, numRows, textLineCountExpected ) )
            #loadErrors.append( "Row count for {} seems wrong: {} instead of {}".format( self.sourceFilename, numRows, textLineCountExpected ) )
        ##halt

        self.BibleOrganisationalSystem = BibleOrganisationalSystem( 'GENERIC-KJV-66-ENG' )
        self.preloaded = True
    # end of ESwordBible.preload


    def load( self ):
        """
        Load all the books out of the SQLite3 database.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( _("load()") )
        if not self.preloaded: self.preload()

        if BibleOrgSysGlobals.verbosityLevel > 2: print( _("Loading {}…").format( self.sourceFilepath ) )
        loadErrors = []

        #fileExtensionUpper = self.fileExtension.upper()
        #if fileExtensionUpper not in FILENAME_ENDINGS_TO_ACCEPT:
            #logging.critical( "{} doesn't appear to be a e-Sword file".format( self.sourceFilename ) )
        #elif not self.sourceFilename.upper().endswith( BIBLE_FILENAME_ENDINGS_TO_ACCEPT[0] ):
            #logging.critical( "{} doesn't appear to be a e-Sword Bible file".format( self.sourceFilename ) )

        #connection = sqlite3.connect( self.sourceFilepath )
        #connection.row_factory = sqlite3.Row # Enable row names
        #cursor = connection.cursor()

        ## First get the settings
        #if self.suppliedMetadata is None: self.suppliedMetadata = {}
        #self.suppliedMetadata['e-Sword-Bible'] = {}
        #cursor.execute( 'select * from Details' )
        #row = cursor.fetchone()
        #for key in row.keys():
            #self.suppliedMetadata['e-Sword-Bible'][key] = row[key]
        ##print( self.suppliedMetadata['e-Sword-Bible'] ); halt
        ##if 'Description' in self.settingsDict and len(self.settingsDict['Description'])<40: self.name = self.settingsDict['Description']
        ##if 'Abbreviation' in self.settingsDict: self.abbreviation = self.settingsDict['Abbreviation']
        #if 'encryption' in self.suppliedMetadata['e-Sword-Bible']:
            #logging.critical( "{} is encrypted: level {}".format( self.sourceFilename, self.suppliedMetadata['e-Sword-Bible']['encryption'] ) )


        # Just get some information from the file
# NOTE: Isn't this a highly inefficient way to find the number of rows in the database???
        self.cursor.execute( 'select * from Bible' )
        rows = self.cursor.fetchall()
        numRows = len(rows)
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>2: print( '{} rows found'.format( numRows ) )
        BBBn1 = rows[0][0]
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>2: print( 'First book number is {}'.format( BBBn1 ) )
        del rows
        BBB1 = None
        if BBBn1 <= 66: BBB1 = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromReferenceNumber( BBBn1 )


        testament = BBB = None
        booksExpected = textLineCountExpected = 0
        if self.suppliedMetadata['e-Sword-Bible']['OT'] and self.suppliedMetadata['e-Sword-Bible']['NT']:
            testament, BBB = 'BOTH', 'GEN'
            booksExpected, textLineCountExpected = 66, 31102
        elif self.suppliedMetadata['e-Sword-Bible']['OT']:
            testament, BBB = 'OT', 'GEN'
            booksExpected, textLineCountExpected = 39, 23145
        elif self.suppliedMetadata['e-Sword-Bible']['NT']:
            testament, BBB = 'NT', 'MAT'
            booksExpected, textLineCountExpected = 27, 7957
        elif self.suppliedMetadata['e-Sword-Bible']['Abbreviation'] == 'VIN2011': # Handle encoding error
            logging.critical( "e-Sword settings encoding error -- no testament set: {}".format( self.suppliedMetadata['e-Sword-Bible'] ) )
            loadErrors.append( "e-Sword settings encoding error -- no testament set: {}".format( self.suppliedMetadata['e-Sword-Bible'] ) )
            testament, BBB = 'BOTH', 'GEN'
            booksExpected, textLineCountExpected = 66, 31102
        elif self.suppliedMetadata['e-Sword-Bible']['Apocrypha']: # incomplete
            testament, BBB = 'AP', 'XXX'
            booksExpected, textLineCountExpected = 99, 999999
            halt
        if not BBB:
            logging.critical( "e-Sword settings encoding error -- no testament set: {}".format( self.suppliedMetadata['e-Sword-Bible'] ) )
            loadErrors.append( "e-Sword settings encoding error -- no testament set: {}".format( self.suppliedMetadata['e-Sword-Bible'] ) )
            #if 0:
                #self.cursor.execute( 'select * from Bible' )
                #rows = self.cursor.fetchall()
                #print( "rows", len(rows) )
                #for row in rows:
                    #assert len(row) == 4
                    #BBBn, C, V, text = row # First three are integers, the last is a string
                    #print( BBBn, C, V, repr(text) )
                    #if C==2: break
                #del rows # Takes a lot of memory
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>2:
            print( "Testament={} BBB={} BBB1={}, bE={}, tLCE={} nR={}".format( testament, BBB, BBB1, booksExpected, textLineCountExpected, numRows ) )
        if BBB1 != BBB:
            logging.critical( "First book seems wrong: {} instead of {}".format( BBB1, BBB ) )
            loadErrors.append( "First book seems wrong: {} instead of {}".format( BBB1, BBB ) )
            if not BBB: BBB = BBB1
        if numRows != textLineCountExpected:
            logging.critical( "Row count for {} seems wrong: {} instead of {}".format( self.sourceFilename, numRows, textLineCountExpected ) )
            loadErrors.append( "Row count for {} seems wrong: {} instead of {}".format( self.sourceFilename, numRows, textLineCountExpected ) )
        #halt

        #BOS = BibleOrganisationalSystem( 'GENERIC-KJV-66-ENG' )

        # Create the first book
        thisBook = BibleBook( self, BBB )
        thisBook.objectNameString = 'e-Sword Bible Book object'
        thisBook.objectTypeString = 'e-Sword-Bible'

        verseList = self.BibleOrganisationalSystem.getNumVersesList( BBB )
        numC, numV = len(verseList), verseList[0]
        nBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getReferenceNumber( BBB )
        C = V = 1

        bookCount = 0
        ourGlobals = {}
        continued = ourGlobals['haveParagraph'] = False
        haveLines = False
        while True:
            self.cursor.execute('select Scripture from BibleOrgSys.Bible where Book=? and Chapter=? and Verse=?', (nBBB,C,V) )
            try:
                row = self.cursor.fetchone()
                line = row[0]
            except TypeError: # This reference is missing (row is None)
                #print( "something wrong at", BBB, C, V )
                #if BibleOrgSysGlobals.debugFlag: halt
                #print( row )
                line = None
            #print ( nBBB, BBB, C, V, 'e-Sw file line is "' + line + '"' )
            if line is None: logging.warning( "ESwordBible.load: Have missing verse line at {} {}:{}".format( BBB, C, V ) )
            else: # line is not None
                if not isinstance( line, str ):
                    if 'encryption' in self.suppliedMetadata['e-Sword-Bible']:
                        logging.critical( "ESwordBible.load: Unable to decrypt verse line at {} {}:{} {!r}".format( BBB, C, V, line ) )
                        break
                    else:
                        logging.critical( "ESwordBible.load: Probably encrypted module: Unable to decode verse line at {} {}:{} {!r} {}".format( BBB, C, V, line, self.suppliedMetadata['e-Sword-Bible'] ) )
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
            handleESwordLine( self, self.name, BBB, C, V, line, thisBook, ourGlobals )
            V += 1
            if V > numV:
                C += 1
                if C > numC: # Save this book now
                    if haveLines:
                        if BibleOrgSysGlobals.verbosityLevel > 3: print( "  e-Sword saving", BBB, bookCount+1 )
                        self.stashBook( thisBook )
                    #else: print( "Not saving", BBB )
                    bookCount += 1 # Not the number saved but the number we attempted to process
                    if bookCount >= booksExpected: break
                    BBB = self.BibleOrganisationalSystem.getNextBookCode( BBB )
                    # Create the next book
                    thisBook = BibleBook( self, BBB )
                    thisBook.objectNameString = 'e-Sword Bible Book object'
                    thisBook.objectTypeString = 'e-Sword-Bible'
                    haveLines = False

                    verseList = self.BibleOrganisationalSystem.getNumVersesList( BBB )
                    numC, numV = len(verseList), verseList[0]
                    nBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getReferenceNumber( BBB )
                    C = V = 1
                    #thisBook.addLine( 'c', str(C) )
                else: # next chapter only
                    #thisBook.addLine( 'c', str(C) )
                    numV = verseList[C-1]
                    V = 1

            if ourGlobals['haveParagraph']:
                thisBook.addLine( 'p', '' )
                ourGlobals['haveParagraph'] = False

        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag:
            self.checkForExtraMaterial( self.cursor, self.BibleOrganisationalSystem )
        self.cursor.close()
        del self.cursor
        if loadErrors: self.errorDictionary['Load Errors'] = loadErrors
        self.applySuppliedMetadata( 'e-Sword-Bible' ) # Copy some to self.settingsDict
        self.doPostLoadProcessing()
    # end of ESwordBible.load


    def loadBook( self, BBB ):
        """
        Load the requested book out of the SQLite3 database.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( _("loadBook( {} )").format( BBB ) )

        if BBB in self.books:
            if BibleOrgSysGlobals.debugFlag: print( "  {} is already loaded -- returning".format( BBB ) )
            return # Already loaded
        if BBB in self.triedLoadingBook:
            logging.warning( "We had already tried loading e-SwordBible {} for {}".format( BBB, self.name ) )
            return # We've already attempted to load this book
        self.triedLoadingBook[BBB] = True
        self.bookNeedsReloading[BBB] = False
        if BibleOrgSysGlobals.verbosityLevel > 2: print( _("Loading {} from {}…").format( BBB, self.sourceFilepath ) )
        loadErrors = []

        # Create the book
        thisBook = BibleBook( self, BBB )
        thisBook.objectNameString = 'e-Sword Bible Book object'
        thisBook.objectTypeString = 'e-Sword-Bible'

        verseList = self.BibleOrganisationalSystem.getNumVersesList( BBB )
        numC, numV = len(verseList), verseList[0]
        nBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getReferenceNumber( BBB )
        C = V = 1

        ourGlobals = {}
        continued = ourGlobals['haveParagraph'] = False
        haveLines = False
        while True:
            self.cursor.execute('select Scripture from Bible where Book=? and Chapter=? and Verse=?', (nBBB,C,V) )
            try:
                row = self.cursor.fetchone()
                line = row[0]
            except TypeError: # This reference is missing (row is None)
                #print( "something wrong at", BBB, C, V )
                #if BibleOrgSysGlobals.debugFlag: halt
                #print( row )
                line = None
            #print ( nBBB, BBB, C, V, 'e-Sw file line is "' + line + '"' )
            if line is None: logging.warning( "ESwordBible.load: Have missing verse line at {} {}:{}".format( BBB, C, V ) )
            else: # line is not None
                if not isinstance( line, str ):
                    if 'encryption' in self.suppliedMetadata['e-Sword-Bible']:
                        logging.critical( "ESwordBible.load: Unable to decrypt verse line at {} {}:{} {!r}".format( BBB, C, V, line ) )
                        break
                    else:
                        logging.critical( "ESwordBible.load: Probably encrypted module: Unable to decode verse line at {} {}:{} {!r} {}".format( BBB, C, V, line, self.suppliedMetadata['e-Sword-Bible'] ) )
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
            handleESwordLine( self, self.name, BBB, C, V, line, thisBook, ourGlobals )
            V += 1
            if V > numV:
                C += 1
                if C <= numC: # next chapter only
                    #thisBook.addLine( 'c', str(C) )
                    numV = verseList[C-1]
                    V = 1
                else: # Save this book now
                    if haveLines:
                        if BibleOrgSysGlobals.verbosityLevel > 3: print( "  ESwordBible saving", BBB )
                        self.stashBook( thisBook )
                    #else: print( "Not saving", BBB )
                    break

            if ourGlobals['haveParagraph']:
                thisBook.addLine( 'p', '' )
                ourGlobals['haveParagraph'] = False
    # end of ESwordBible.loadBook
# end of ESwordBible class



def createESwordBibleModule( self, outputFolder, controlDict ):
    """
    Create a SQLite3 database module for the Windows program e-Sword.

    self here is a Bible object with _processedLines
    """
    import zipfile
    from BibleOrgSys.Reference.USFM3Markers import OFTEN_IGNORED_USFM_HEADER_MARKERS, USFM_ALL_INTRODUCTION_MARKERS, USFM_BIBLE_PARAGRAPH_MARKERS, removeUSFMCharacterField, replaceUSFMCharacterFields
    from BibleOrgSys.Internals.InternalBibleInternals import BOS_ADDED_NESTING_MARKERS, BOS_NESTING_MARKERS
    from BibleOrgSys.Formats.theWordBible import theWordOTBookLines, theWordNTBookLines, theWordBookLines, theWordIgnoredIntroMarkers
    def adjustLine( BBB, C, V, originalLine ):
        """
        Handle pseudo-USFM markers within the line (cross-references, footnotes, and character formatting).

        Parameters are the Scripture reference (for error messsages)
            and the line (string) containing the backslash codes.

        Returns a string with the backslash codes replaced by e-Sword RTF formatting codes.
        """
        line = originalLine # Keep a copy of the original line for error messages

        if '\\x' in line: # Remove cross-references completely (why???)
            #line = line.replace('\\x ','<RX>').replace('\\x*','<Rx>')
            line = removeUSFMCharacterField( 'x', line, closedFlag=True ).lstrip() # Remove superfluous spaces

        if '\\f' in line: # Handle footnotes
            line = removeUSFMCharacterField( 'f', line, closedFlag=True ).lstrip() # Remove superfluous spaces
            #for marker in ( 'fr', 'fm', ): # simply remove these whole field
                #line = removeUSFMCharacterField( marker, line, closedFlag=None )
            #for marker in ( 'fq', 'fqa', 'fl', 'fk', ): # italicise these ones
                #while '\\'+marker+' ' in line:
                    ##print( BBB, C, V, marker, line.count('\\'+marker+' '), line )
                    ##print( "was", "'"+line+"'" )
                    #ix = line.find( '\\'+marker+' ' )
                    #assert ix != -1
                    #ixEnd = line.find( '\\', ix+len(marker)+2 )
                    #if ixEnd == -1: # no following marker so assume field stops at the end of the line
                        #line = line.replace( '\\'+marker+' ', '<i>' ) + '</i>'
                    #elif line[ixEnd:].startswith( '\\'+marker+'*' ): # replace the end marker also
                        #line = line.replace( '\\'+marker+' ', '<i>' ).replace( '\\'+marker+'*', '</i>' )
                    #else: # leave the next marker in place
                        #line = line[:ixEnd].replace( '\\'+marker+' ', '<i>' ) + '</i>' + line[ixEnd:]
            #for marker in ( 'ft', ): # simply remove these markers (but leave behind the text field)
                #line = line.replace( '\\'+marker+' ', '' ).replace( '\\'+marker+'*', '' )
            ##for caller in '+*abcdefghijklmnopqrstuvwxyz': line.replace('\\f '+caller+' ','<RF>') # Handle single-character callers
            #line = re.sub( r'(\\f [a-z+*]{1,4} )', '<RF>', line ) # Handle one to three character callers
            #line = line.replace('\\f ','<RF>').replace('\\f*','<Rf>') # Must be after the italicisation
            ##if '\\f' in originalLine:
                ##print( "o", originalLine )
                ##print( "n", line )
                ##halt

        if '\\' in line: # Handle character formatting fields
            line = removeUSFMCharacterField( 'fig', line, closedFlag=True ) # Remove figures
            line = removeUSFMCharacterField( 'str', line, closedFlag=True ) # Remove Strong's numbers
            line = removeUSFMCharacterField( 'sem', line, closedFlag=True ) # Remove semantic tagging
            replacements = (
                ( ('add',), '~^~cf15~^~i ',' ~^~cf0~^~i0' ), # Note the spaces!
                ( ('qt',), '<FO>','<Fo>' ),
                ( ('wj',), '<FR>','<Fr>' ),
                ( ('ca','va',), '(',')' ),
                ( ('bdit',), '<b><i>','</i></b>' ),
                ( ('bd','em','k',), '<b>','</b>' ),
                ( ('it','rq','bk','dc','qs','sig','sls','tl',), '<i>','</i>' ),
                ( ('nd','sc',), '<font size=-1>','</font>' ),
                )
            line = replaceUSFMCharacterFields( replacements, line ) # This function also handles USFM 2.4 nested character markers
            if '\\nd' not in originalLine and '\\+nd' not in originalLine:
                line = line.replace('LORD', '<font size=-1>LORD</font>')
                #line = line.replace('\\nd ','<font size=-1>',).replace('\\nd*','</font>').replace('\\+nd ','<font size=-1>',).replace('\\+nd*','</font>')
            #else:
                #line = line.replace('LORD', '<font size=-1>LORD</font>')
            #line = line.replace('\\add ','<FI>').replace('\\add*','<Fi>').replace('\\+add ','<FI>').replace('\\+add*','<Fi>')
            #line = line.replace('\\qt ','<FO>').replace('\\qt*','<Fo>').replace('\\+qt ','<FO>').replace('\\+qt*','<Fo>')
            #line = line.replace('\\wj ','<FR>').replace('\\wj*','<Fr>').replace('\\+wj ','<FR>').replace('\\+wj*','<Fr>')

        #if '\\' in line: # Output simple HTML tags (with no semantic info)
            #line = line.replace('\\bdit ','<b><i>').replace('\\bdit*','</i></b>').replace('\\+bdit ','<b><i>').replace('\\+bdit*','</i></b>')
            #for marker in ( 'it', 'rq', 'bk', 'dc', 'qs', 'sig', 'sls', 'tl', ): # All these markers are just italicised
                #line = line.replace('\\'+marker+' ','<i>').replace('\\'+marker+'*','</i>').replace('\\+'+marker+' ','<i>').replace('\\+'+marker+'*','</i>')
            #for marker in ( 'bd', 'em', 'k', ): # All these markers are just bolded
                #line = line.replace('\\'+marker+' ','<b>').replace('\\'+marker+'*','</b>').replace('\\+'+marker+' ','<b>').replace('\\+'+marker+'*','</b>')
            #line = line.replace('\\sc ','<font size=-1>',).replace('\\sc*','</font>').replace('\\+sc ','<font size=-1>',).replace('\\+sc*','</font>')

        # Check what's left at the end
        if '\\' in line:
            logging.warning( "toESword.adjustLine: Doesn't handle formatted line yet: {} {}:{} {!r}".format( BBB, C, V, line ) )
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                print( "toESword.adjustLine: Doesn't handle formatted line yet: {} {}:{} {!r}".format( BBB, C, V, line ) )
                halt
        return line
    # end of toESword.adjustLine


    def handleIntroduction( BBB, bookData, ourGlobals ):
        """
        Go through the book introduction (if any) and extract main titles for e-Sword export.

        Parameters are BBB (for error messages),
            the actual book data, and
            ourGlobals dictionary for persistent variables.

        Returns the information in a composed line string.
        """
        intC, intV = -1, 0
        composedLine = ''
        while True:
            #print( "toESword.handleIntroduction", BBB, intC, V )
            try: result = bookData.getContextVerseData( (BBB,str(intC),str(intV),) ) # Currently this only gets one line
            except KeyError: break # Reached the end of the introduction
            verseData, context = result
            if debuggingThisModule or BibleOrgSysGlobals.strictCheckingFlag:
                assert len(verseData) == 1 # in the introductory section (each individual line is a "verse")
            marker, text = verseData[0].getMarker(), verseData[0].getFullText()
            if marker not in theWordIgnoredIntroMarkers and '¬' not in marker and marker not in BOS_ADDED_NESTING_MARKERS: # don't need added markers here either
                if   marker in ('mt1','mte1',): composedLine += '<TS1>'+adjustLine(BBB,intC,intV,text)+'<Ts>~^~line '
                elif marker in ('mt2','mte2',): composedLine += '<TS2>'+adjustLine(BBB,intC,intV,text)+'<Ts>~^~line '
                elif marker in ('mt3','mte3',): composedLine += '<TS3>'+adjustLine(BBB,intC,intV,text)+'<Ts>~^~line '
                elif marker in ('mt4','mte4',): composedLine += '<TS3>'+adjustLine(BBB,intC,intV,text)+'<Ts>~^~line '
                elif marker=='ms1': composedLine += '<TS2>'+adjustLine(BBB,intC,intV,text)+'<Ts>~^~line '
                elif marker in ('ms2','ms3','ms4'): composedLine += '<TS3>'+adjustLine(BBB,intC,intV,text)+'<Ts>~^~line '
                elif marker=='mr': composedLine += '<TS3>'+adjustLine(BBB,intC,intV,text)+'<Ts>~^~line '
                else:
                    logging.warning( "toESword.handleIntroduction: doesn't handle {} {!r} yet".format( BBB, marker ) )
                    if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                        print( "toESword.handleIntroduction: doesn't handle {} {!r} yet".format( BBB, marker ) )
                        halt
                    ourGlobals['unhandledMarkers'].add( marker + ' (in intro)' )
            intV += 1 # Step to the next introductory section "verse"

        # Check what's left at the end
        if '\\' in composedLine:
            logging.warning( "toESword.handleIntroduction: Doesn't handle formatted line yet: {} {!r}".format( BBB, composedLine ) )
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                print( "toESword.handleIntroduction: Doesn't handle formatted line yet: {} {!r}".format( BBB, composedLine ) )
                halt
        return composedLine.replace( '~^~', '\\' )
    # end of toESword.handleIntroduction


    def composeVerseLine( BBB, C, V, verseData, ourGlobals ):
        """
        Composes a single line representing a verse.

        Parameters are the Scripture reference (for error messages),
            the verseData (a list of InternalBibleEntries: pseudo-USFM markers and their contents),
            and a ourGlobals dictionary for holding persistent variables (between calls).

        This function handles the paragraph/new-line markers;
            adjustLine (above) is called to handle internal/character markers.

        Returns the composed line.
        """
        #print( "toESword.composeVerseLine( {} {}:{} {} {}".format( BBB, C, V, verseData, ourGlobals ) )
        composedLine = ourGlobals['line'] # We might already have some book headings to precede the text for this verse
        ourGlobals['line'] = '' # We've used them so we don't need them any more
        #marker = text = None

        vCount = 0
        lastMarker = gotVP = None
        #if BBB=='MAT' and C==4 and 14<V<18: print( BBB, C, V, ourGlobals, verseData )
        for verseDataEntry in verseData:
            marker, text = verseDataEntry.getMarker(), verseDataEntry.getFullText()
            if '¬' in marker or marker in BOS_ADDED_NESTING_MARKERS: continue # Just ignore added markers -- not needed here
            if marker in ('c','c#','cl','cp','rem',): lastMarker = marker; continue  # ignore all of these for this

            if marker == 'vp#': # This precedes a v field and has the verse number to be printed
                gotVP = text # Just remember it for now
            elif marker == 'v': # handle versification differences here
                vCount += 1
                if vCount == 1: # Handle verse bridges
                    if text != str(V):
                        composedLine += '<sup>('+text+')</sup> ' # Put the additional verse number into the text in parenthesis
                elif vCount > 1: # We have an additional verse number
                    if BibleOrgSysGlobals.debugFlag and debuggingThisModule: assert text != str(V)
                    composedLine += ' <sup>('+text+')</sup>' # Put the additional verse number into the text in parenthesis
                lastMarker = marker
                continue

            #print( "toESword.composeVerseLine:", BBB, C, V, marker, text )
            if marker in theWordIgnoredIntroMarkers:
                logging.error( "toESword.composeVerseLine: Found unexpected {} introduction marker at {} {}:{} {}".format( marker, BBB, C, V, repr(text) ) )
                print( "toESword.composeVerseLine:", BBB, C, V, marker, text, verseData )
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                    assert marker not in theWordIgnoredIntroMarkers # these markers shouldn't occur in verses

            if marker == 'ms1': composedLine += '<TS2>'+adjustLine(BBB,C,V,text)+'<Ts>~^~line '
            elif marker in ('ms2','ms3','ms4'): composedLine += '<TS3>'+adjustLine(BBB,C,V,text)+'<Ts>~^~line '
            elif marker == 's1':
                if ourGlobals['lastLine'] is not None and not composedLine: # i.e., don't do it for the very first line
                    ourGlobals['lastLine'] = ourGlobals['lastLine'].rstrip() + '\\line ' # append the new paragraph marker to the previous line
                composedLine += '~^~b~^~i~^~f0 '+adjustLine(BBB,C,V,text)+'~^~cf0~^~b0~^~i0~^~line '
            elif marker == 's2': composedLine += '~^~b~^~i~^~f0 '+adjustLine(BBB,C,V,text)+'~^~cf0~^~b0~^~i0~^~line '
            elif marker in ( 's3','s4', 'sr','mr', 'd', ): composedLine += '~^~b~^~i~^~f0 '+adjustLine(BBB,C,V,text)+'~^~b~^~i~^~f0 '
            elif marker in ( 'qa', 'r', ):
                if marker=='r' and text and text[0]!='(' and text[-1]!=')': # Put parenthesis around this if not already there
                    text = '(' + text + ')'
                composedLine += '<TS3><i>'+adjustLine(BBB,C,V,text)+'</i><Ts>'
            elif marker in ( 'm', ):
                assert not text
                if ourGlobals['lastLine'] is not None and not composedLine: # i.e., don't do it for the very first line
                    ourGlobals['lastLine'] = ourGlobals['lastLine'].rstrip() + '\\line ' # append the new paragraph marker to the previous line
                #if text:
                    #print( 'm', repr(text), verseData )
                    #composedLine += '~^~line '+adjustLine(BBB,C,V,text)
                    #if ourGlobals['pi1'] or ourGlobals['pi2'] or ourGlobals['pi3'] or ourGlobals['pi4'] or ourGlobals['pi5'] or ourGlobals['pi6'] or ourGlobals['pi7']:
                        #composedLine += '~^~line '
                    #else: composedLine += '~^~line '
                #else: # there is text
                    #composedLine += '~^~line'+adjustLine(BBB,C,V,text)
            elif marker in ( 'p', 'b', ):
                #print( marker, text )
                assert not text
                if ourGlobals['lastLine'] is not None and not composedLine: # i.e., don't do it for the very first line
                    ourGlobals['lastLine'] = ourGlobals['lastLine'].rstrip() + '\\line ' # append the new paragraph marker to the previous line
                #else: composedLine += '~^~line '
                #composedLine += adjustLine(BBB,C,V,text)
            elif marker in ( 'pi1', ):
                assert not text
            elif marker in ( 'pi2', ):
                assert not text
            elif marker in ( 'pi3', 'pmc', ):
                assert not text
            elif marker in ( 'pi4', ):
                assert not text
            elif marker in ( 'pc', ):
                assert not text
            elif marker in ( 'pr', 'pmr', 'cls', ):
                assert not text
            elif marker in ( 'b','nb','ib', 'mi', 'pm', 'pmo', ):
                assert not text
            elif marker in ( 'q1', 'qm1', ):
                assert not text
                if ourGlobals['lastLine'] is not None and not composedLine: # i.e., don't do it for the very first line
                    ourGlobals['lastLine'] += '\\line ' # append the new quotation paragraph marker to the previous line
                else: composedLine += '~^~line '
                #composedLine += adjustLine(BBB,C,V,text)
            elif marker in ( 'q2', 'qm2', ):
                assert not text
                if ourGlobals['lastLine'] is not None and not composedLine: # i.e., don't do it for the very first line
                    ourGlobals['lastLine'] += '\\line ' # append the new quotation paragraph marker to the previous line
                else: composedLine += '~^~line '
                #composedLine += '~^~line<PI2>'+adjustLine(BBB,C,V,text)
            elif marker in ( 'q3', 'qm3', ):
                assert not text
                if ourGlobals['lastLine'] is not None and not composedLine: # i.e., don't do it for the very first line
                    ourGlobals['lastLine'] += '\\line ' # append the new quotation paragraph marker to the previous line
                else: composedLine += '~^~line '
                #composedLine += '~^~line<PI3>'+adjustLine(BBB,C,V,text)
            elif marker in ( 'q4', 'qm4', ):
                assert not text
                if ourGlobals['lastLine'] is not None and not composedLine: # i.e., don't do it for the very first line
                    ourGlobals['lastLine'] += '\\line ' # append the new quotation paragraph marker to the previous line
                else: composedLine += '~^~line '
                #composedLine += '~^~line<PI4>'+adjustLine(BBB,C,V,text)
            elif marker == 'li1': composedLine += '<PI>• '+adjustLine(BBB,C,V,text)
            elif marker == 'li2': composedLine += '<PI2>• '+adjustLine(BBB,C,V,text)
            elif marker == 'li3': composedLine += '<PI3>• '+adjustLine(BBB,C,V,text)
            elif marker == 'li4': composedLine += '<PI4>• '+adjustLine(BBB,C,V,text)
            elif marker in ( 'cd', 'sp', ): composedLine += '<i>'+adjustLine(BBB,C,V,text)+'</i>'
            elif marker in ( 'v~', 'p~', ):
                #print( lastMarker )
                if lastMarker == 'p': composedLine += '~^~line ' # We had a continuation paragraph
                elif lastMarker == 'm': composedLine += '~^~line ' # We had a continuation paragraph
                elif lastMarker in BibleOrgSysGlobals.USFMParagraphMarkers: pass # Did we need to do anything here???
                elif lastMarker != 'v':
                    print( BBB, C, V, marker, lastMarker, verseData )
                    composedLine += adjustLine(BBB,C,V, text )
                    if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt # This should never happen -- probably a b marker with text
                #if ourGlobals['pi1']: composedLine += '<PI>'
                #elif ourGlobals['pi2']: composedLine += '<PI2>'
                #elif ourGlobals['pi3']: composedLine += '<PI3>'
                #elif ourGlobals['pi4']: composedLine += '<PI4>'
                #elif ourGlobals['pi5']: composedLine += '<PI5>'
                #elif ourGlobals['pi6']: composedLine += '<PI6>'
                #elif ourGlobals['pi7']: composedLine += '<PI7>'
                composedLine += adjustLine(BBB,C,V, text )
            else:
                logging.warning( "toESword.composeVerseLine: doesn't handle {!r} yet".format( marker ) )
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                    print( "toESword.composeVerseLine: doesn't handle {!r} yet".format( marker ) )
                    halt
                ourGlobals['unhandledMarkers'].add( marker )
            lastMarker = marker

        # Final clean-up
        #while '  ' in composedLine: # remove double spaces
            #composedLine = composedLine.replace( '  ', ' ' )

        # Check what's left at the end (but hide e-Sword \line markers first)
        if '\\' in composedLine.replace( '\\line ', '' ):
            logging.warning( "toESword.composeVerseLine: Doesn't handle formatted line yet: {} {}:{} {!r}".format( BBB, C, V, composedLine ) )
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                print( "toESword.composeVerseLine: Doesn't handle formatted line yet: {} {}:{} {!r}".format( BBB, C, V, composedLine ) )
                halt
        #haveAdd = False
        #for verseDataEntry in verseData:
            #marker, text = verseDataEntry.getMarker(), verseDataEntry.getFullText()
            #if text and '\\add' in text: haveAdd = True; break
        #if haveAdd: print( "Returning {} {}:{}: {}".format( BBB, C, V, composedLine.replace( '~^~', '\\' ).rstrip() ) )
        return composedLine.replace( '~^~', '\\' ).rstrip()
    # end of toESword.composeVerseLine


    def writeESwordBibleBook( sqlObject, BBB, ourGlobals ):
        """
        Writes a book to the e-Sword sqlObject file.
        """
        #print( "toESword.writeESwordBibleBook( {}, {}, {}".format( sqlObject, BBB, ourGlobals ) )
        nonlocal lineCount
        bkData = self.books[BBB] if BBB in self.books else None
        #print( bkData._processedLines )
        verseList = BOS.getNumVersesList( BBB )
        nBBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getReferenceNumber( BBB )
        numC, numV = len(verseList), verseList[0]

        ourGlobals['line'], ourGlobals['lastLine'] = '', None
        if bkData:
            # Write book headings (stuff before chapter 1)
            ourGlobals['line'] = handleIntroduction( BBB, bkData, ourGlobals )

            # Write the verses
            C = V = 1
            ourGlobals['lastLine'] = ourGlobals['lastBCV'] = None
            while True:
                verseData = None
                if bkData:
                    try:
                        result = bkData.getContextVerseData( (BBB,str(C),str(V),) )
                        verseData, context = result
                    except KeyError: # Just ignore missing verses
                        logging.warning( "BibleWriter.toESword: missing source verse at {} {}:{}".format( BBB, C, V ) )
                    # Handle some common versification anomalies
                    if (BBB,C,V) == ('JN3',1,14): # Add text for v15 if it exists
                        try:
                            result15 = bkData.getContextVerseData( ('JN3','1','15',) )
                            verseData15, context15 = result15
                            verseData.extend( verseData15 )
                        except KeyError: pass #  just ignore it
                    elif (BBB,C,V) == ('REV',12,17): # Add text for v15 if it exists
                        try:
                            result18 = bkData.getContextVerseData( ('REV','12','18',) )
                            verseData18, context18 = result18
                            verseData.extend( verseData18 )
                        except KeyError: pass #  just ignore it
                    composedLine = ''
                    if verseData:
                        composedLine = composeVerseLine( BBB, C, V, verseData, ourGlobals )
                        #if composedLine: # don't bother writing blank (unfinished?) verses
                            #print( "toESword: Writing", BBB, nBBB, C, V, marker, repr(line) )
                            #sqlObject.execute( 'INSERT INTO "Bible" VALUES(?,?,?,?)', (nBBB,C,V,composedLine) )
                        # Stay one line behind (because paragraph indicators get appended to the previous line)
                        if ourGlobals['lastBCV'] is not None \
                        and ourGlobals['lastLine']: # don't bother writing blank (unfinished?) verses
                            sqlObject.execute( 'INSERT INTO "Bible" VALUES(?,?,?,?)', \
                                (ourGlobals['lastBCV'][0],ourGlobals['lastBCV'][1],ourGlobals['lastBCV'][2],ourGlobals['lastLine']) )
                            lineCount += 1
                    ourGlobals['lastLine'] = composedLine
                ourGlobals['lastBCV'] = (nBBB,C,V)
                V += 1
                if V > numV:
                    C += 1
                    if C > numC:
                        break
                    else: # next chapter only
                        numV = verseList[C-1]
                        V = 1
            #assert not ourGlobals['line'] and not ourGlobals['lastLine'] #  We should have written everything

        # Write the last line of the file
        if ourGlobals['lastLine']: # don't bother writing blank (unfinished?) verses
            sqlObject.execute( 'INSERT INTO "Bible" VALUES(?,?,?,?)', \
                (ourGlobals['lastBCV'][0],ourGlobals['lastBCV'][1],ourGlobals['lastBCV'][2],ourGlobals['lastLine']) )
            lineCount += 1
    # end of toESword.writeESwordBibleBook


    # Set-up their Bible reference system
    BOS = BibleOrganisationalSystem( 'GENERIC-KJV-66-ENG' )
    #BRL = BibleReferenceList( BOS, BibleObject=None )

    # Try to figure out if it's an OT/NT or what (allow for up to 4 extra books like FRT,GLS, etc.)
    if len(self) <= (39+4) and self.containsAnyOT39Books() and not self.containsAnyNT27Books():
        testament, startBBB, endBBB = 'OT', 'GEN', 'MAL'
        booksExpected, textLineCountExpected, checkTotals = 39, 23145, theWordOTBookLines
    elif len(self) <= (27+4) and self.containsAnyNT27Books() and not self.containsAnyOT39Books():
        testament, startBBB, endBBB = 'NT', 'MAT', 'REV'
        booksExpected, textLineCountExpected, checkTotals = 27, 7957, theWordNTBookLines
    else: # assume it's an entire Bible
        testament, startBBB, endBBB = 'BOTH', 'GEN', 'REV'
        booksExpected, textLineCountExpected, checkTotals = 66, 31102, theWordBookLines
    extension = '.bblx'

    if BibleOrgSysGlobals.verbosityLevel > 2: print( _("  Exporting to e-Sword format…") )
    mySettings = {}
    mySettings['unhandledMarkers'] = set()
    handledBooks = []

    if 'e-SwordOutputFilename' in controlDict: filename = controlDict['e-SwordOutputFilename']
    elif self.sourceFilename: filename = self.sourceFilename
    elif self.shortName: filename = self.shortName
    elif self.abbreviation: filename = self.abbreviation
    elif self.name: filename = self.name
    else: filename = 'export'
    if not filename.endswith( extension ): filename += extension # Make sure that we have the right file extension
    filepath = os.path.join( outputFolder, BibleOrgSysGlobals.makeSafeFilename( filename ) )
    if os.path.exists( filepath ): os.remove( filepath )
    if BibleOrgSysGlobals.verbosityLevel > 2: print( '  writeESwordBibleBook: ' + _("Writing {!r}…").format( filepath ) )
    conn = sqlite3.connect( filepath )
    cursor = conn.cursor()

    # First write the settings Details table
    exeStr = 'CREATE TABLE Details (Description NVARCHAR(255), Abbreviation NVARCHAR(50), Comments TEXT, Version TEXT, VersionDate DATETIME, PublishDate DATETIME, RightToLeft BOOL, OT BOOL, NT BOOL, Strong BOOL' # incomplete
    customCSS = self.getSetting( 'CustomCSS' )
    if customCSS: exeStr += ', CustomCSS TEXT'
    exeStr += ')'
    cursor.execute( exeStr )

    values = []

    description = self.getSetting( 'Description' )
    if not description: description = self.getSetting( 'description' )
    if not description: description = self.name
    values.append( description )

    if self.abbreviation: abbreviation = self.abbreviation
    else: abbreviation = self.getSetting( 'WorkAbbreviation' )
    if not abbreviation: abbreviation = self.name[:3].upper()
    values.append( abbreviation )

    comments = self.getSetting( 'Comments' )
    values.append( comments )

    version = self.getSetting( 'Version' )
    values.append( version )

    versionDate = self.getSetting( 'VersionDate' )
    values.append( versionDate )

    publishDate = self.getSetting( 'PublishDate' )
    values.append( publishDate )

    rightToLeft = self.getSetting( 'RightToLeft' )
    values.append( rightToLeft )

    values.append( True if testament=='OT' or testament=='BOTH' else False )
    values.append( True if testament=='NT' or testament=='BOTH' else False )

    Strong = self.getSetting( 'Strong' )
    values.append( Strong if Strong else False )

    if customCSS: values.append( customCSS )

    exeStr = 'INSERT INTO "Details" VALUES(' + '?,'*(len(values)-1) + '?)'
    #print( exeStr, values )
    cursor.execute( exeStr, values )

    # Now create and fill the Bible table
    cursor.execute( 'CREATE TABLE Bible(Book INT, Chapter INT, Verse INT, Scripture TEXT)' )
    conn.commit() # save (commit) the changes
    BBB, lineCount = startBBB, 0
    while True: # Write each Bible book in the KJV order
        writeESwordBibleBook( cursor, BBB, mySettings )
        conn.commit() # save (commit) the changes
        handledBooks.append( BBB )
        if BBB == endBBB: break
        BBB = BOS.getNextBookCode( BBB )

    # Now create the index
    cursor.execute( 'CREATE INDEX BookChapterVerseIndex ON Bible (Book, Chapter, Verse)' )
    conn.commit() # save (commit) the changes
    cursor.close()

    if mySettings['unhandledMarkers']:
        logging.warning( "BibleWriter.toESword: Unhandled markers were {}".format( mySettings['unhandledMarkers'] ) )
        if BibleOrgSysGlobals.verbosityLevel > 1:
            print( "  " + _("WARNING: Unhandled toESword markers were {}").format( mySettings['unhandledMarkers'] ) )
    unhandledBooks = []
    for BBB in self.getBookList():
        if BBB not in handledBooks: unhandledBooks.append( BBB )
    if unhandledBooks:
        logging.warning( "toESword: Unhandled books were {}".format( unhandledBooks ) )
        if BibleOrgSysGlobals.verbosityLevel > 1:
            print( "  " + _("WARNING: Unhandled toESword books were {}").format( unhandledBooks ) )

    # Now create a zipped version
    if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Zipping {} e-Sword file…".format( filename ) )
    zf = zipfile.ZipFile( filepath+'.zip', 'w', compression=zipfile.ZIP_DEFLATED )
    zf.write( filepath, filename )
    zf.close()

    if BibleOrgSysGlobals.verbosityLevel > 0 and BibleOrgSysGlobals.maxProcesses > 1:
        print( "  BibleWriter.toESword finished successfully." )
    return True
# end of createESwordBibleModule



def testeSwB( indexString, eSwBfolder, eSwBfilename ):
    """
    Crudely demonstrate the e-Sword Bible class
    """
    from BibleOrgSys.Reference import VerseReferences
    #BiblesFolderpath = BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Bibles/' )
    #testFolder = BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Bibles/e-Sword modules/' ) # Must be the same as below

    #TUBfolder = os.path.join( eSwBfolder, eSwBfilename )
    if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Demonstrating the e-Sword Bible class {}…").format( indexString) )
    if BibleOrgSysGlobals.verbosityLevel > 0: print( "  Test folder is {!r} {!r}".format( eSwBfolder, eSwBfilename ) )
    eSwB = ESwordBible( eSwBfolder, eSwBfilename )
    eSwB.preload()
    #eSwB.load() # Load and process the file
    if BibleOrgSysGlobals.verbosityLevel > 1: print( "testeSwB1:", eSwB ) # Just print a summary
    #print( eSwB.suppliedMetadata['e-Sword-Bible'] )
    if eSwB is not None:
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
            try:
                shortText, verseText = svk.getShortText(), eSwB.getVerseText( svk )
                if BibleOrgSysGlobals.verbosityLevel > 1: print( reference, shortText, verseText )
            except KeyError:
                if BibleOrgSysGlobals.verbosityLevel > 1: print( reference, "not found!!!" )

        eSwB.discover() # Just to test this

        #if 0:# Now export the Bible and compare the round trip
            #eSwB.toESword()
            ##doaResults = eSwB.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
            #if BibleOrgSysGlobals.strictCheckingFlag: # Now compare the original and the derived USX XML files
                #outputFolder = "OutputFiles/BOS_e-Sword_Reexport/"
                #if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nComparing original and re-exported e-Sword files…" )
                #result = BibleOrgSysGlobals.fileCompare( eSwBfilename, eSwBfilename, eSwBfolder, outputFolder )
                #if BibleOrgSysGlobals.debugFlag:
                    #if not result: halt
    if BibleOrgSysGlobals.verbosityLevel > 2: print( "testeSwB2:", eSwB ) # Just print a summary
# end of testeSwB


def demo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( programNameVersion )


    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        testFolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'e-SwordTest/' )
        result1 = ESwordBibleFileCheck( testFolder )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "TestA1", result1 )
        result2 = ESwordBibleFileCheck( testFolder, autoLoad=True )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "TestA2", result2 )
        result3 = ESwordBibleFileCheck( testFolder, autoLoadBooks=True )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "TestA3", result3 )


    if 1: # individual modules in the same test folder
        testFolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'e-SwordTest/' )
        names = ('King James Bible Pure Cambridge Edition','KJ3.JayPGreen','Wycliffe_New_Testament(1385)',)
        for j, name in enumerate( names):
            indexString = 'B' + str( j+1 )
            fullname = name + '.bblx'
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "\neSw {}/ Trying {}".format( indexString, fullname ) )
            testeSwB( indexString, testFolder, fullname )
            #halt


    BiblesFolderpath = BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Bibles/' )
    if 1: # individual modules in the test folder
        testFolder = BiblesFolderpath.joinpath( 'e-Sword modules/' )
        names = ('LEB','Dansk_1819','Miles Coverdale (1535)',)
        for j, name in enumerate( names):
            indexString = 'C' + str( j+1 )
            fullname = name + '.bblx'
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "\neSw {}/ Trying {}".format( indexString, fullname ) )
            testeSwB( indexString, testFolder, fullname )
            #halt


    if 1: # individual modules in the output folder
        testFolder = BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH.joinpath( 'BOS_e-SwordExport/' )
        names = ('Matigsalug',)
        for j, name in enumerate( names, start=1 ):
            indexString = 'D' + str( j )
            fullname = name + '.bblx'
            pathname = os.path.join( testFolder, fullname )
            if os.path.exists( pathname ):
                if BibleOrgSysGlobals.verbosityLevel > 1: print( "\neSw {}/ Trying {}".format( indexString, fullname ) )
                testeSwB( indexString, testFolder, fullname )


    #if 1: # all discovered modules in the test folder
        #testFolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'e-SwordRoundtripTestFiles/' )
        #foundFolders, foundFiles = [], []
        #for something in os.listdir( testFolder ):
            #somepath = os.path.join( testFolder, something )
            #if os.path.isdir( somepath ): foundFolders.append( something )
            #elif os.path.isfile( somepath ) and somepath.endswith('.bblx'):
                #if something != 'acc.bblx': # has a corrupted file it seems
                    #foundFiles.append( something )

        #if BibleOrgSysGlobals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
            #if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nTrying all {} discovered modules…".format( len(foundFolders) ) )
            #parameters = [('E'+str(j+1),testFolder,filename) for j,filename in enumerate(sorted(foundFiles))]
            #BibleOrgSysGlobals.alreadyMultiprocessing = True
            #with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                #results = pool.map( testeSwB, parameters ) # have the pool do our loads
                #assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            #BibleOrgSysGlobals.alreadyMultiprocessing = False
        #else: # Just single threaded
            #for j, someFile in enumerate( sorted( foundFiles ) ):
                #indexString = 'E' + str( j+1 )
                #if BibleOrgSysGlobals.verbosityLevel > 1: print( "\neSw {}/ Trying {}".format( indexString, someFile ) )
                ##myTestFolder = os.path.join( testFolder, someFolder+'/' )
                #testeSwB( indexString, testFolder, someFile )
                ##break # only do the first one…temp

    BiblesFolderpath = BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../../../../mnt/SSDs/Bibles/' )
    if 1: # all discovered modules in the test folder
        testFolder = BiblesFolderpath.joinpath( 'e-Sword modules/' ) # Put your test folder here

        foundFolders, foundFiles = [], []
        for something in os.listdir( testFolder ):
            somepath = os.path.join( testFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ) and somepath.upper().endswith('.BBLX'): foundFiles.append( something )

        if BibleOrgSysGlobals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nTrying all {} discovered modules…".format( len(foundFolders) ) )
            parameters = [('F'+str(j+1),testFolder,filename) for j,filename in enumerate(sorted(foundFiles))]
            BibleOrgSysGlobals.alreadyMultiprocessing = True
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.starmap( testeSwB, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            for j, someFile in enumerate( sorted( foundFiles ) ):
                indexString = 'F' + str( j+1 )
                if BibleOrgSysGlobals.verbosityLevel > 1: print( "\neSw {}/ Trying {}".format( indexString, someFile ) )
                #myTestFolder = os.path.join( testFolder, someFolder+'/' )
                testeSwB( indexString, testFolder, someFile )
                #break # only do the first one…temp
# end of demo

if __name__ == '__main__':
    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    demo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of ESwordBible.py
