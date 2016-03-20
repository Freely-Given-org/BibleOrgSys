#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# SwordBible.py
#
# Module handling Sword Bible files
#
# Copyright (C) 2015-2016 Robert Hunt
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
Module detecting and loading Crosswire Sword Bible binary files.

Files are usually:
    ot
    ot.vss
    nt
    nt.vss
"""

from gettext import gettext as _

LastModifiedDate = '2016-03-01' # by RJH
ShortProgName = "SwordBible"
ProgName = "Sword Bible format handler"
ProgVersion = '0.28'
ProgNameVersion = '{} v{}'.format( ShortProgName, ProgVersion )
ProgNameVersionDate = '{} {} {}'.format( ProgNameVersion, _("last modified"), LastModifiedDate )

debuggingThisModule = False


import logging, os, re
import multiprocessing

try: import Sword # Assumes that the Sword Python bindings are installed on this computer
except ImportError: # Sword library (dll and python bindings) seem to be not available
    logging.critical( _("You need to install the Sword library with Python3 bindings on your computer in order to use this module.") )

import BibleOrgSysGlobals
from Bible import Bible, BibleBook
#from BibleOrganizationalSystems import BibleOrganizationalSystem


 # Must be lowercase
compulsoryTopFolders = ( 'mods.d', 'modules', ) # Both should be there -- the first one contains the .conf file(s)
compulsoryBottomFolders = ( 'rawtext', 'ztext', ) # Either one
compulsoryFiles = ( 'ot','ot.vss', 'ot.bzs','ot.bzv','ot.bzz', 'nt','nt.vss', 'nt.bzs','nt.bzv','nt.bzz', ) # At least two


# Sword enums
DIRECTION_LTR = 0; DIRECTION_RTL = 1; DIRECTION_BIDI = 2
FMT_UNKNOWN = 0; FMT_PLAIN = 1; FMT_THML = 2; FMT_GBF = 3; FMT_HTML = 4; FMT_HTMLHREF = 5; FMT_RTF = 6; FMT_OSIS = 7; FMT_WEBIF = 8; FMT_TEI = 9; FMT_XHTML = 10
FMT_DICT = { 1:'PLAIN', 2:'THML', 3:'GBF', 4:'HTML', 5:'HTMLHREF', 6:'RTF', 7:'OSIS', 8:'WEBIF', 9:'TEI', 10:'XHTML' }
ENC_UNKNOWN = 0; ENC_LATIN1 = 1; ENC_UTF8 = 2; ENC_UTF16 = 3; ENC_RTF = 4; ENC_HTML = 5



def SwordBibleFileCheck( givenFolderName, strictCheck=True, autoLoad=False, autoLoadBooks=False ):
    """
    Given a folder, search for Sword Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number of Bibles found.

    if autoLoad is true and exactly one Sword Bible is found,
        returns the loaded SwordBible object.
    """
    if BibleOrgSysGlobals.verbosityLevel > 2: print( "SwordBibleFileCheck( {}, {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad, autoLoadBooks ) )
    if BibleOrgSysGlobals.debugFlag: assert givenFolderName and isinstance( givenFolderName, str )
    if BibleOrgSysGlobals.debugFlag: assert autoLoad in (True,False,)

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( _("SwordBibleFileCheck: Given {!r} folder is unreadable").format( givenFolderName ) )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( _("SwordBibleFileCheck: Given {!r} path is not a folder").format( givenFolderName ) )
        return False

    def confirmThisFolder( checkFolderPath ):
        """
        We are given the path to a folder that contains the two main top level folders.

        Now we need to find one or more .conf files and the associated Bible folders.

        Returns a list of Bible module names (without the .conf) -- they are the case of the folder name.
        """
        if BibleOrgSysGlobals.verbosityLevel > 3:
            print( " SwordBibleFileCheck.confirmThisFolder: Looking for files in given {}".format( checkFolderPath ) )

        # See if there's any .conf files in the mods.d folder
        confFolder = os.path.join( checkFolderPath, 'mods.d/' )
        foundConfFiles = []
        for something in os.listdir( confFolder ):
            somepath = os.path.join( confFolder, something )
            if os.path.isdir( somepath ):
                if something == '__MACOSX': continue # don't visit these directories
                print( _("SwordBibleFileCheck: Didn't expect a subfolder in conf folder: {}").format( something ) )
            elif os.path.isfile( somepath ):
                if something.endswith( '.conf' ):
                    foundConfFiles.append( something[:-5].upper() ) # Remove the .conf bit and make it UPPERCASE
                else:
                    logging.warning( _("SwordBibleFileCheck: Didn't expect this file in conf folder: {}").format( something ) )
        if not foundConfFiles: return 0
        #print( foundConfFiles )

        # See if there's folders for the Sword module files matching the .conf files
        compressedFolder = os.path.join( checkFolderPath, 'modules/', 'texts/', 'ztext/' )
        foundTextFolders = []
        for folderType in ( 'rawtext', 'ztext' ):
            mainTextFolder = os.path.join( checkFolderPath, 'modules/', 'texts/', folderType+'/' )
            if os.access( mainTextFolder, os.R_OK ): # The subfolder is readable
                for something in os.listdir( mainTextFolder ):
                    somepath = os.path.join( mainTextFolder, something )
                    if os.path.isdir( somepath ):
                        if something == '__MACOSX': continue # don't visit these directories
                        potentialName = something.upper()
                        if potentialName in foundConfFiles:
                            foundTextFiles = []
                            textFolder = os.path.join( mainTextFolder, something+'/' )
                            for something2 in os.listdir( textFolder ):
                                somepath2 = os.path.join( textFolder, something2 )
                                if os.path.isdir( somepath2 ):
                                    if something2 == '__MACOSX': continue # don't visit these directories
                                    if something2 != 'lucene':
                                        logging.warning( _("SwordBibleFileCheck1: Didn't expect a subfolder in {} text folder: {}").format( something, something2 ) )
                                elif os.path.isfile( somepath2 ):
                                    if folderType == 'rawtext' and something2 in ( 'ot','ot.vss', 'nt','nt.vss' ):
                                        foundTextFiles.append( something2 )
                                    elif folderType == 'ztext' and something2 in ( 'ot.bzs','ot.bzv','ot.bzz', 'nt.bzs','nt.bzv','nt.bzz' ):
                                        foundTextFiles.append( something2 )
                                    else:
                                        if something2 not in ( 'errata', 'appendix', ):
                                            logging.warning( _("SwordBibleFileCheck1: Didn't expect this file in {} text folder: {}").format( something, something2 ) )
                            #print( foundTextFiles )
                            if len(foundTextFiles) >= 2:
                                foundTextFolders.append( something )
                        else:
                            logging.warning( _("SwordBibleFileCheck2: Didn't expect a subfolder in {} folder: {}").format( folderType, something ) )
                    elif os.path.isfile( somepath ):
                        logging.warning( _("SwordBibleFileCheck2: Didn't expect this file in {} folder: {}").format( folderType, something ) )
        if not foundTextFolders:
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "    Looked hopeful but no actual module folders or files found" )
            return None
        #print( foundTextFolders )
        return foundTextFolders
    # end of confirmThisFolder

    # Main part of SwordBibleFileCheck
    # Find all the files and folders in this folder
    if BibleOrgSysGlobals.verbosityLevel > 3:
        print( " SwordBibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
    foundFolders, foundFiles = [], []
    numFound = foundFolderCount = foundFileCount = 0
    for something in os.listdir( givenFolderName ):
        somepath = os.path.join( givenFolderName, something )
        if os.path.isdir( somepath ):
            if something == '__MACOSX': continue # don't visit these directories
            foundFolders.append( something ) # Save folder name in case we have to go a level down
            if something in compulsoryTopFolders:
                foundFolderCount += 1
        elif os.path.isfile( somepath ):
            somethingUpper = something.upper()
            if somethingUpper in compulsoryFiles: foundFileCount += 1
    if foundFolderCount == len(compulsoryTopFolders):
        assert foundFileCount == 0
        foundConfNames = confirmThisFolder( givenFolderName )
        numFound = 0 if foundConfNames is None else len(foundConfNames)
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "SwordBibleFileCheck got", numFound, givenFolderName, foundConfNames )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            oB = SwordBible( givenFolderName )
            if autoLoadBooks: oB.load() # Load and process the file
            return oB
        return numFound
    elif foundFileCount and BibleOrgSysGlobals.verbosityLevel > 2: print( "    Looked hopeful but no actual files found" )

    # Look one level down
    numFound = 0
    foundProjects = []
    numFound = foundFolderCount = foundFileCount = 0
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
        if not os.access( tryFolderName, os.R_OK ): # The subfolder is not readable
            logging.warning( _("SwordBibleFileCheck: {!r} subfolder is unreadable").format( tryFolderName ) )
            continue
        if BibleOrgSysGlobals.verbosityLevel > 3: print( "    SwordBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
        foundSubfolders, foundSubfiles = [], []
        for something in os.listdir( tryFolderName ):
            somepath = os.path.join( givenFolderName, thisFolderName, something )
            if os.path.isdir( somepath ):
                foundSubfolders.append( something )
                if something in compulsoryTopFolders: foundFolderCount += 1
            elif os.path.isfile( somepath ):
                somethingUpper = something.upper()
                if somethingUpper in compulsoryFiles: foundFileCount += 1
        if foundFolderCount == len(compulsoryTopFolders):
            assert foundFileCount == 0
            foundConfNames = confirmThisFolder( tryFolderName )
            if foundConfNames:
                for confName in foundConfNames:
                    foundProjects.append( (tryFolderName,confName) )
                    numFound += 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "SwordBibleFileCheck foundProjects", numFound, foundProjects )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            if BibleOrgSysGlobals.debugFlag: assert len(foundProjects) == 1
            oB = SwordBible( foundProjects[0][0], foundProjects[0][1] )
            if autoLoadBooks: oB.load() # Load and process the file
            return oB
        return numFound
# end of SwordBibleFileCheck



def replaceFixedPairs( replacementList, verseLine ):
    """
    Given a set of 4-tuples, e.g., ('<divineName>','\\nd ','</divineName>','\\nd*')
        search for matching opening and closing pairs and make the replacements,
        issuing errors for mismatches.

    Since we've handling verse segments, it's possible that
        the opening segment was in the previous verse
        or the closing segment is in the next verse.
    In that case, place missing opening segments right at the beginning of the verse
        and missing closing segments right at the end.

    Returns the new verseLine.
    """
    for openCode,newOpenCode,closeCode,newCloseCode in replacementList:
        ix = verseLine.find( openCode )
        while ix != -1:
            #print( '{} {!r}->{!r} {!r}->{!r} in {!r}'.format( ix, openCode,newOpenCode,closeCode,newCloseCode, verseLine ) )
            verseLine = verseLine.replace( openCode, newOpenCode, 1 )
            ixEnd = verseLine.find( closeCode, ix )
            if ixEnd == -1:
                logging.error( 'Missing {!r} close code to match {!r}'.format( closeCode, openCode ) )
                verseLine = verseLine + newCloseCode # Try to fix it by adding a closing code at the end
            else:
                verseLine = verseLine.replace( closeCode, newCloseCode, 1 )
            ix = verseLine.find( openCode, ix )
        if verseLine.find( closeCode ) != -1:
            logging.error( 'Unexpected {!r} close code without any previous {!r}'.format( closeCode, openCode )  )
            verseLine = verseLine.replace( closeCode, newCloseCode, 1 )
            # Try to fix it by adding an opening code at or near the beginning of the line
            #   but we have to skip past any paragraph markers
            insertIndex = 0
            while verseLine[insertIndex] == '\\':
                insertIndex += 1
                while insertIndex < len(verseLine)-1:
                    if verseLine[insertIndex] == ' ': break
                    insertIndex += 1
            if insertIndex != 0 and debuggingThisModule: print( "insertIndex={} vL={!r}".format( insertIndex, verseLine ) )
            verseLine = verseLine[:insertIndex] + ' '+newOpenCode + verseLine[insertIndex:]
            if insertIndex != 0 and debuggingThisModule: print( "new vL={!r}".format( verseLine ) )

    return verseLine
# end of replaceFixedPairs



def importOSISVerseLine( osisVerseString, thisBook, moduleName, BBB, C, V ):
    """
    Given a verse entry string made up of OSIS segments,
        convert it into our internal format
        and add the line(s) to thisBook.

    moduleName, BBB, C, V are just used for more helpful error/information messages.

    OSIS is a pig to extract the information out of,
        but we use it nevertheless because it's the native format
        and hence most likely to represent the original well.

    We use \\NL** as an internal code for a newline
        to show where a verse line needs to be broken into internal chunks.

    Adds the line(s) to thisBook. No return value.
    """
    if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
        print( "\nimportOSISVerseLine( {} {} {}:{} ... {!r} )".format( moduleName, BBB, C, V, osisVerseString ) )
    verseLine = osisVerseString


    def handleOSISWordAttributes( attributeString ):
        """
        Handle OSIS XML attributes from the <w ...> field.

        Returns the string to replace the attributes.
        """
        attributeReplacementResult = ''
        attributeCount = attributeString.count( '="' )
        #print( 'Attributes={} {!r}'.format( attributeCount, attributeString ) )
        for j in range( 0, attributeCount ):
            match2 = re.search( 'savlm="(.+?)"', attributeString )
            if match2:
                savlm = match2.group(1)
                #print( 'savlm', repr(savlm) )
                while True:
                    match3 = re.search( 'strong:([GH]\d{1,5})', savlm )
                    if not match3: break
                    #print( 'string', repr(match3.group(1) ) )
                    attributeReplacementResult += '\\str {}\\str*'.format( match3.group(1) )
                    savlm = savlm[:match3.start()] + savlm[match3.end():] # Remove this Strongs' number
                attributeString = attributeString[:match2.start()] + attributeString[match2.end():] # Remove this attribute entry

            match2 = re.search( 'lemma="(.+?)"', attributeString )
            if match2:
                lemma = match2.group(1)
                #print( 'lemma', repr(lemma) )
                while True:
                    match3 = re.search( 'strong:([GH]\d{1,5})', lemma )
                    if not match3: break
                    #print( 'string', repr(match3.group(1) ) )
                    attributeReplacementResult += '\\str {}\\str*'.format( match3.group(1) )
                    lemma = lemma[:match3.start()] + lemma[match3.end():] # Remove this Strongs' number
                attributeString = attributeString[:match2.start()] + attributeString[match2.end():] # Remove this attribute entry

            match2 = re.search( 'morph="(.+?)"', attributeString )
            if match2:
                morph = match2.group(1)
                #print( 'morph', repr(morph) )
                while True:
                    match3 = re.search( 'strongMorph:(TH\d{1,4})', morph )
                    if not match3: break
                    #print( 'string', repr(match3.group(1) ) )
                    attributeReplacementResult += '\\morph {}\\morph*'.format( match3.group(1) )
                    morph = morph[:match3.start()] + morph[match3.end():] # Remove this Strongs' number
                attributeString = attributeString[:match2.start()] + attributeString[match2.end():] # Remove this attribute entry

            match2 = re.search( 'type="(.+?)"', attributeString )
            if match2:
                typeValue = match2.group(1)
                #print( 'typeValue', repr(typeValue) ) # Seems to have an incrementing value on the end for some reason
                assert typeValue.startswith( 'x-split' ) # e.g., x-split or x-split-1 -- what do these mean?
                attributeString = attributeString[:match2.start()] + attributeString[match2.end():] # Remove this attribute entry
            match2 = re.search( 'subType="(.+?)"', attributeString )
            if match2:
                subType = match2.group(1)
                #print( 'subType', repr(subType) ) # e.g., x-28 -- what does this mean?
                attributeString = attributeString[:match2.start()] + attributeString[match2.end():] # Remove this attribute entry

            match2 = re.search( 'src="(.+?)"', attributeString ) # Can be two numbers separated by a space!
            if match2:
                src = match2.group(1)
                #print( 'src', repr(src) ) # What does this mean?
                attributeString = attributeString[:match2.start()] + attributeString[match2.end():] # Remove this attribute entry

            match2 = re.search( 'wn="(\d+?)"', attributeString )
            if match2:
                wn = match2.group(1)
                #print( 'wn', repr(wn) ) # What does this mean?
                attributeString = attributeString[:match2.start()] + attributeString[match2.end():] # Remove this attribute entry

        if attributeString.strip():
            print( 'Unhandled word attributes', repr(attributeString) )
            if BibleOrgSysGlobals.debugFlag: halt
        #print( 'attributeReplacementResult', repr(attributeReplacementResult) )
        return attributeReplacementResult
    # end of handleOSISWordAttributes


    # Start of main code for importOSISVerseLine
    # Straight substitutions
    for old, new in ( ( ' />', '/>' ),
                      ( '<milestone marker="¶" type="x-p"/>', '\\NL**\\p\\NL**' ),
                      ( '<milestone marker="¶" subType="x-added" type="x-p"/>', '\\NL**\\p\\NL**' ),
                      ( '<milestone type="x-extra-p"/>', '\\NL**\\p\\NL**' ),
                      ( '<milestone type="line"/><milestone type="line"/>', '\\NL**\\b\\NL**' ),
                      ( '<milestone type="line"/>', '\\NL**' ),
                      ( '<titlePage>', '\\NL**' ), ( '</titlePage>', '\\NL**' ),
                      ( '<lb type="x-begin-paragraph"/>', '\\NL**\\p\\NL**' ), # in ESV
                      ( '<lb type="x-end-paragraph"/>', '\\NL**' ), # in ESV
                      ( '<lb subType="x-same-paragraph" type="x-begin-paragraph"/>', '\\NL**' ), # in ESV
                      ( '<lb subType="x-extra-space" type="x-begin-paragraph"/>', '\\NL**\\b\\NL**' ), # in ESV
                      ( '<lb/>', '\\NL**' ),
                      ( '<lb type="x-unparagraphed"/>', '' ),
                      ( '<list>', '\\NL**' ), ( '</list>', '\\NL**' ),
                      ( '<l/>', '\\NL**\\q1\\NL**' ),
                      ):
        verseLine = verseLine.replace( old, new )

    # Delete end book and chapter (self-closing) markers (we'll add our own later)
    while True: # Delete end book markers (should only be maximum of one theoretically but not always so)
        match = re.search( '<div [^/>]*?eID=[^/>]+?/>', verseLine )
        if not match: break
        verseLine = verseLine[:match.start()] + verseLine[match.end():]
    while True: # Delete preverse milestones
        match = re.search( '<div [^/>]*?subType="x-preverse"[^/>]*?/>', verseLine )
        if not match: break
        verseLine = verseLine[:match.start()] + verseLine[match.end():]
    while True:
        match = re.search( '<div [^/>]*?type="front"[^/>]*?/>', verseLine )
        if not match: break
        assert V == '0'
        verseLine = verseLine[:match.start()] + verseLine[match.end():] # It's in v0 anyway so no problem
    while True:
        match = re.search( '<div ([^/>]*?)type="section"([^/>]*?)>', verseLine )
        if not match: break
        attributes = match.group(1) + match.group(2)
        print( "Div section attributes={!r}".format( attributes ) )
        assert 'scope="' in attributes
        verseLine = verseLine[:match.start()] + verseLine[match.end():]
    while True:
        match = re.search( '<div [^/>]*?type="colophon"[^/>]*?/>', verseLine )
        if not match: break
        verseLine = verseLine[:match.start()] + verseLine[match.end():] # Not sure what this is (Rom 16:27) but delete it for now
    while True: # Delete end chapter markers (should only be maximum of one theoretically)
        match = re.search( '<chapter [^/>]*?eID=[^/>]+?/>', verseLine )
        if not match: break
        verseLine = verseLine[:match.start()] + verseLine[match.end():]
    while True: # Delete start verse markers (should only be maximum of one theoretically but can be more -- bridged verses???)
        match = re.search( '<verse [^/>]*?osisID="[^/>]+?"[^/>]*?>', verseLine )
        if not match: break
        assert V != '0'
        verseLine = verseLine[:match.start()] + verseLine[match.end():]
    verseLine = verseLine.replace( '</verse>', '' ) # Delete left-overs (normally expected at the end of the verse line)
    while True: # Delete lg start and end milestones
        match = re.search( '<lg [^/>]+?/>', verseLine )
        if not match: break
        verseLine = verseLine[:match.start()] + verseLine[match.end():]

    # Other regular expression data extractions
    match = re.search( '<chapter ([^/>]*?)sID="([^/>]+?)"([^/>]*?)/>', verseLine )
    if match:
        attributes, sID = match.group(1) + match.group(3), match.group(2)
        #print( 'Chapter sID {!r} attributes={!r} @ {} {}:{}'.format( sID, attributes, BBB, C, V ) )
        assert C and C != '0'
        assert V == '0'
        #if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( "CCCC {!r}(:{!r})".format( C, V ) )
        #thisBook.addLine( 'c', C ) # Don't need this coz it's done by the calling routine
        verseLine = verseLine[:match.start()] + verseLine[match.end():]
    match = re.search( '<chapter ([^/>]*?)osisID="([^/>]+?)"([^/>]*?)>', verseLine )
    if match:
        attributes, osisID = match.group(1) + match.group(3), match.group(2)
        #print( 'Chapter osisID {!r} attributes={!r} @ {} {}:{}'.format( osisID, attributes, BBB, C, V ) )
        #assert C and C != '0'
        assert V == '0'
        #if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( "CCCC {!r}(:{!r})".format( C, V ) )
        #thisBook.addLine( 'c', C ) # Don't need this coz it's done by the calling routine
        verseLine = verseLine[:match.start()] + verseLine[match.end():]
    verseLine = verseLine.replace( '</chapter>', '' )
    while True:
        match = re.search( '<div ([^/>]*?)type="([^/>]+?)"([^/>]*?)/?> ?<title>(.+?)</title>', verseLine )
        if not match: break
        attributes, sectionType, words = match.group(1) + match.group(3), match.group(2), match.group(4)
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( 'Div title {!r} attributes={!r} Words={!r}'.format( sectionType, attributes, words ) )
        if sectionType == 'section': titleMarker = 's1'
        elif sectionType == 'subSection': titleMarker = 's2'
        elif sectionType == 'x-subSubSection': titleMarker = 's3'
        elif sectionType == 'majorSection': titleMarker = 'sr'
        elif sectionType == 'book': titleMarker = 'mt1'
        elif sectionType == 'introduction': titleMarker = 'iot'
        else: print( 'Matched:', repr(match.group(0)) ); halt
        replacement = '\\NL**\\{} {}\\NL**'.format( titleMarker, words )
        #print( 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
    match = re.search( '<div ([^/>]*?)type="([^/>]+?)"([^/>]*?)/><title>', verseLine )
    if match: # handle left over div/title start fields
        attributes, sectionType = match.group(1) + match.group(3), match.group(2)
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( 'Section title start {!r} attributes={!r}'.format( sectionType, attributes ) )
        if sectionType == 'section': titleMarker = 's1'
        elif sectionType == 'subSection': titleMarker = 's2'
        elif sectionType == 'x-subSubSection': titleMarker = 's3'
        else: print( 'Matched:', repr(match.group(0)) ); halt
        replacement = '\\NL**\\{} '.format( titleMarker )
        #print( 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
    while True:
        match = re.search( '<div ([^/>]*?)type="([^/>]+?)"([^/>]*?)/>.NL..<head>(.+?)</head>', verseLine )
        if not match: break
        attributes, sectionType, words = match.group(1) + match.group(3), match.group(2), match.group(4)
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( 'Section title {!r} attributes={!r} Words={!r}'.format( sectionType, attributes, words ) )
        if sectionType == 'outline': titleMarker = 'iot'
        else: print( 'Matched:', repr(match.group(0)) ); halt
        replacement = '\\NL**\\{} {}\\NL**'.format( titleMarker, words )
        #print( 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
    while True:
        match = re.search( '<div ([^/>]*?)type="([^/>]+?)"([^/>]*?)/?>', verseLine )
        if not match: break
        attributes, divType = match.group(1) + match.group(3), match.group(2)
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( 'Div type={!r} attributes={!r}'.format( divType, attributes ) )
        if divType == 'x-p': replacement = '\\NL**\\p\\NL**'
        elif divType == 'glossary': replacement = '\\NL**\\id GLO\\NL**' #### WEIRD -- appended to 3 John
        elif divType == 'book': replacement = '' # We don't need this
        elif divType == 'outline': replacement = '\\NL**\\iot '
        elif divType == 'paragraph': replacement = '\\NL**\\ip ' if C=='0' else '\\NL**\\p\\NL**'
        elif divType == 'majorSection': replacement = '\\NL**\\ms\\NL**'
        elif divType == 'section': replacement = '\\NL**\\s1 '
        elif divType in ( 'preface', 'titlePage', 'introduction', ): replacement = '\\NL**\\ip '
        elif divType in ( 'x-license', 'x-trademark', ): replacement = '\\NL**\\rem '
        else: print( 'Matched:', repr(match.group(0)) ); halt
        #print( 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
    verseLine = verseLine.replace( '</div>', '' )
    while True:
        match = re.search( '<title type="parallel"><reference type="parallel">(.+?)</reference></title>', verseLine )
        if not match: break
        reference = match.group(1)
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( 'Parallel reference={!r}'.format( reference ) )
        replacement = '\\NL**\\r {}\\NL**'.format( reference )
        #print( 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
    while True:
        match = re.search( '<title type="scope"><reference>(.+?)</reference></title>', verseLine )
        if not match: break
        reference = match.group(1)
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( 'Section Parallel reference={!r}'.format( reference ) )
        replacement = '\\NL**\\sr {}\\NL**'.format( reference )
        #print( 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
    while True:
        match = re.search( '<title ([^/>]+?)>(.+?)</title>', verseLine )
        if not match: break
        attributes, words = match.group(1), match.group(2)
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( 'Title attributes={!r} Words={!r}'.format( attributes, words ) )
        titleMarker = 's1'
        replacement = '\\NL**\\{} {}\\NL**'.format( titleMarker, words )
        #print( 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
    verseLine = verseLine.replace( '</title>', '\\NL**' )
    verseLine = verseLine.replace( '<title>', '\\NL**\\s1 ' )
    while True:
        match = re.search( '<w ([^/>]+?)/>', verseLine )
        if not match: break
        replacement = handleOSISWordAttributes( match.group(1) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
        #print( "verseLineB", repr(verseLine) )
    while True:
        match = re.search( '<w ([^/>]+?)>(.*?)</w>', verseLine ) # Can have no words inside
        if not match: break
        attributes, words = match.group(1), match.group(2)
        #print( 'AttributesC={!r} Words={!r}'.format( attributes, words ) )
        replacement = words
        replacement += handleOSISWordAttributes( attributes )
        #print( 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
        #print( "\nverseLineW", repr(verseLine) )
    while True:
        match = re.search( '<q ([^/>]+?)>(.+?)</q>', verseLine )
        if not match: break
        attributes, words = match.group(1), match.group(2)
        if 'who="Jesus"' in attributes:
            if 'marker="' in attributes and 'marker=""' not in attributes:
                print( 'AttributesQM={!r} Words={!r}'.format( attributes, words ) )
                if BibleOrgSysGlobals.debugFlag: halt
            replacement = '\\wj {}\\wj*'.format( words )
        else:
            print( 'AttributesQ={!r} Words={!r}'.format( attributes, words ) )
            if BibleOrgSysGlobals.debugFlag: halt
        #print( 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
    while True:
        match = re.search( '<q ([^/>]+?)>', verseLine ) # Leftovers (no </q>)
        if not match: break
        attributes = match.group(1)
        if 'who="Jesus"' in attributes:
            if 'marker="' in attributes and 'marker=""' not in attributes:
                print( 'AttributesQM={!r} Words={!r}'.format( attributes, words ) )
                if BibleOrgSysGlobals.debugFlag: halt
            replacement = '\\wj '
        else:
            print( 'AttributesQ={!r} Words={!r}'.format( attributes, words ) )
            if BibleOrgSysGlobals.debugFlag: halt
        #print( 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
    while True:
        match = re.search( '<q ([^/>]*?)sID="(.+?)"(.*?)/>', verseLine )
        if not match: break
        attributes, sID = match.group(1) + match.group(3), match.group(2)
        #print( 'Q attributesC={!r} sID={!r}'.format( attributes, sID ) )
        match2 = re.search( 'level="(.+?)"', attributes )
        level = match2.group(1) if match2 else '1'
        match2 = re.search( 'marker="(.+?)"', attributes )
        quoteSign = match2.group(1) if match2 else ''
        replacement = '\\NL**\\q{} {}'.format( level, quoteSign )
        #print( 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
    while True:
        match = re.search( '<q ([^/>]*?)eID="(.+?)"(.*?)/>', verseLine )
        if not match: break
        attributes, eID = match.group(1) + match.group(3), match.group(2)
        #print( 'Q attributesC={!r} eID={!r}'.format( attributes, eID ) )
        match2 = re.search( 'marker="(.+?)"', attributes )
        quoteSign = match2.group(1) if match2 else ''
        replacement = '{}\\NL**'.format( quoteSign )
        #print( 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
    while True:
        match = re.search( '<q ([^/>]*?)type="block"(.*?)/>', verseLine )
        if not match: break
        attributes = match.group(1) + match.group(2)
        replacement = '\\NL**\\pc '
        #print( 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
    while True:
        match = re.search( '<q(.*?)>(.+?)</q>', verseLine )
        if not match: break
        attributes, words = match.group(1), match.group(2)
        replacement = '\\NL**\\pc {}\\NL**'.format( words )
        print( 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
    while True:
        match = re.search( '<l ([^/>]*?)level="(.+?)"([^/>]*?)/>', verseLine )
        if not match: break
        attributes, level = match.group(1)+match.group(3), match.group(2)
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( 'AttributesL={!r} Level={!r}'.format( attributes, level ) )
        assert level in '1234'
        if 'sID="' in attributes:
            replacement = '\\NL**\\q{} '.format( level )
        elif 'eID="' in attributes:
            replacement = '' # Remove eIDs completely
        else:
            print( 'Level attributesLl2={!r} Level={!r}'.format( attributes, level ) )
            halt
        #print( 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
    while True:
        match = re.search( '<l ([^/>]+?)/>', verseLine )
        if not match: break
        attributes = match.group(1)
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( 'Level Attributes={!r}'.format( attributes ) )
        if 'sID="' in attributes:
            replacement = '\\NL**\\q1 '
        elif 'eID="' in attributes:
            replacement = '\\NL**' # Remove eIDs completely
        else:
            print( 'AttributesL2={!r} Level={!r}'.format( attributes, level ) )
            halt
        #print( 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
    while True: # handle list items
        match = re.search( '<item ([^/>]*?)type="(.+?)"([^/>]*?)>(.+?)</item>', verseLine )
        if not match: break
        attributes, itemType, item = match.group(1)+match.group(3), match.group(2), match.group(4)
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( 'Item={!r} Type={!r} attributes={!r}'.format( item, itemType, attributes ) )
        assert itemType in ( 'x-indent-1', 'x-indent-2', )
        marker = 'io' if 'x-introduction' in attributes else 'li'
        replacement = '\\NL**\\{} {}\\NL**'.format( marker+itemType[-1], item )
        #print( 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
    match = re.search( '<item ([^/>]*?)type="(.+?)"([^/>]*?)>', verseLine )
    if match: # Handle left-over list items
        attributes, itemType = match.group(1)+match.group(3), match.group(2)
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( 'Item Type={!r} attributes={!r}'.format( itemType, attributes ) )
        assert itemType in ( 'x-indent-1', 'x-indent-2', )
        marker = 'io' if 'x-introduction' in attributes else 'li'
        replacement = '\\NL**\\{}\\NL**'.format( marker+itemType[-1] )
        #print( 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
    verseLine = verseLine.replace( '</item>', '\\NL**' )
    while True: # handle names
        match = re.search( '<name ([^/>]*?)type="(.+?)"([^/>]*?)>(.+?)</name>', verseLine )
        if not match: break
        attributes, nameType, name = match.group(1)+match.group(3), match.group(2), match.group(4)
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( 'Name={!r} Type={!r} attributes={!r}'.format( name, nameType, attributes ) )
        if nameType == 'x-workTitle': marker = 'bk'
        else: halt
        replacement = '\\{} {}\\{}*'.format( marker, name, marker )
        print( 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
    while True:
        match = re.search( '<seg ([^/>]+?)>([^<]+?)</seg>', verseLine )
        if not match: break
        attributes, words = match.group(1), match.group(2)
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( 'Seg attributes={!r} Words={!r}'.format( attributes, words ) )
        if 'type="keyword"' in attributes: marker = 'k'
        elif 'type="x-transChange"' in attributes and 'subType="x-added"' in attributes: marker = 'add'
        else: halt
        replacement = '\\{} {}\\{}*'.format( marker, words, marker )
        #print( 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
        #print( "verseLineC", repr(verseLine) )
    while True:
        match = re.search( '<foreign ([^/>]+?)>(.+?)</foreign>', verseLine )
        if not match: break
        attributes, words = match.group(1), match.group(2)
        #print( 'Attributes={!r} Words={!r}'.format( attributes, words ) )
        replacement = '\\tl {}\\tl*'.format( words )
        #print( 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
        #print( "verseLineC", repr(verseLine) )
    while True:
        match = re.search( '<reference([^/>]*?)>(.+?)</reference>', verseLine )
        if not match: break
        attributes, referenceField = match.group(1), match.group(2)
        #print( 'Attributes={!r} referenceField={!r}'.format( attributes, referenceField ) )
        marker = 'ior' if V=='0' else 'XXX'
        replacement = '\\{} {}\\{}*'.format( marker, referenceField, marker )
        #print( 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
        #print( "verseLineC", repr(verseLine) )
    while True:
        match = re.search( '<hi ([^/>]+?)>(.+?)</hi>', verseLine )
        if not match: break
        attributes, words = match.group(1), match.group(2)
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( 'Highlight attributes={!r} Words={!r}'.format( attributes, words ) )
        if '"italic"' in attributes: marker = 'it'
        elif '"small-caps"' in attributes: marker = 'sc'
        elif '"super"' in attributes: marker = 'ord' # We don't have anything exact for this XXXXXXXXXXXXXXXX
        elif '"acrostic"' in attributes: marker = 'tl'
        elif '"bold"' in attributes: marker = 'bd'
        elif '"underline"' in attributes: marker = 'em' # We don't have an underline marker
        elif '"x-superscript"' in attributes: marker = 'ord' # We don't have a superscript marker
        elif BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
        replacement = '\\{} {}\\{}*'.format( marker, words, marker )
        #print( 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
        #print( "verseLineC", repr(verseLine) )
    while True: # Handle left-over highlights (that have no further information)
        match = re.search( '<hi>(.+?)</hi>', verseLine )
        if not match: break
        words = match.group(1)
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( 'Highlight Words={!r}'.format( words ) )
        #if moduleName in ( 'LITV', 'MKJV', 'TS1998', ):
        marker = 'add'
        replacement = '\\{} {}\\{}*'.format( marker, words, marker )
        #print( 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
        #print( "verseLineC", repr(verseLine) )
    while True:
        match = re.search( '<milestone ([^/>]*?)type="x-usfm-(.+?)"([^/>]*?)/>', verseLine )
        if not match: break
        attributes, marker = match.group(1)+match.group(3), match.group(2)
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( 'Milestone attributes={!r} marker={!r}'.format( attributes, marker ) )
        match2 = re.search( 'n="(.+?)"', attributes )
        if match2:
            replacement = '\\NL**\\{} {}\\NL**'.format( marker, match2.group(1) )
            #print( 'replacement', repr(replacement) )
        else: replacement = ''; halt
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
        #print( "verseLineC", repr(verseLine) )
    while True: # Not sure what this is all about -- just delete it
        match = re.search( '<milestone ([^/>]*?)type="x-strongsMarkup"([^/>]*?)/>', verseLine )
        if not match: break
        attributes = match.group(1)+match.group(2)
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( 'Strongs milestone attributes={!r}'.format( attributes ) )
        verseLine = verseLine[:match.start()] + verseLine[match.end():]
        #print( "verseLineC", repr(verseLine) )
    while True:
        match = re.search( '<milestone ([^/>]*?)type="cQuote"([^/>]*?)/>', verseLine )
        if not match: break
        attributes = match.group(1)+match.group(2)
        match2 = re.search( 'marker="(.+?)"', attributes )
        quoteSign = match2.group(1) if match2 else ''
        replacement = quoteSign
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
    while True:
        match = re.search( '<closer ([^/>]*?)sID="([^/>]+?)"([^/>]*?)/>(.*?)<closer ([^/>]*?)eID="([^/>]+?)"([^/>]*?)/>', verseLine )
        if not match: break
        attributes1, sID, words, attributes2, eID = match.group(1) + match.group(3), match.group(2), match.group(4), match.group(5) + match.group(7), match.group(6)
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( 'Closer attributes1={!r} words={!r}'.format( attributes1, words ) )
        replacement = '\\sig {}\\sig*'.format( words )
        #print( 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
    while True:
        match = re.search( '<note ([^/>]*?)swordFootnote="([^/>]+?)"([^/>]*?)>(.*?)</note>', verseLine )
        if not match: break
        attributes, number, noteContents = match.group(1)+match.group(3), match.group(2), match.group(4)
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( 'Note attributes={!r} Number={!r}'.format( attributes, number ) )
        if 'crossReference' in attributes:
            assert noteContents == ''
            replacement = '\\x {}\\x*'.format( number )
        else: halt
        #print( 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
    while True:
        match = re.search( '<note([^/>]*?)>(.*?)</note>', verseLine )
        if not match: break
        attributes, noteContents = match.group(1), match.group(2).rstrip().replace( '\\NL**\\q1\\NL**', '//' ) # was <l />
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( 'Note attributes={!r} contents={!r}'.format( attributes, noteContents ) )
        replacement = '\\f + \\ft {}\\f*'.format( noteContents )
        #print( 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
    while True:
        match = re.search( '<abbr([^/>]*?)>(.*?)</abbr>', verseLine )
        if not match: break
        attributes, abbr = match.group(1), match.group(2)
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( 'Abbr attributes={!r} abbr={!r}'.format( attributes, abbr ) )
        replacement = '{}'.format( abbr )
        #print( 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
    while True:
        match = re.search( '<a ([^/>]*?)href="([^>]+?)"([^/>]*?)>(.+?)</a>', verseLine )
        if not match: break
        attributes, linkHREF, linkContents = match.group(1)+match.group(3), match.group(2), match.group(4)
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( 'Link attributes={!r} HREF={!r} contents={!r}'.format( attributes, linkHREF, linkContents ) )
        replacement = linkContents
        #print( 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]

    # Now scan for remaining fixed open and close fields
    replacementList = [
            ('<seg><divineName>','\\nd ','</divineName></seg>','\\nd*'),
            ('<seg><transChange type="added">','\\add ','</transChange></seg>','\\add*'),
            ('<transChange type="added">','\\add ','</transChange>','\\add*'),
            #('<hi type="bold">','\\bd ','</hi>','\\bd*'),
            ('<speaker>','\\sp ','</speaker>','\\sp*'),
            ('<inscription>','\\bdit ','</inscription>','\\bdit*'), # What should this really be?
            ('<milestone type="x-idiom-start"/>','\\bdit ','<milestone type="x-idiom-end"/>','\\bdit*'), # What should this really be?
            ('<seg>','','</seg>',''), # Just remove these left-overs
            ('<foreign>','\\tl ','</foreign>','\\tl*'),
            ('<i>','\\it ','</i>','\\it*'),
            ]
    if '<divineName>' in verseLine:
        replacementList.append( ('<divineName>','\\nd ','</divineName>','\\nd*') )
    else: replacementList.append( ('<divineName type="x-yhwh">','\\nd ','</divineName>','\\nd*') )
    if '<transChange>' in verseLine:
        replacementList.append( ('<transChange>','\\add ','</transChange>','\\add*') )
    else: replacementList.append( ('<transChange type="added">','\\add ','</transChange>','\\add*') )
    verseLine = replaceFixedPairs( replacementList, verseLine )

    # Check for anything left that we should have caught above
    if '<' in verseLine or '>' in verseLine:
        print( "{} {} {}:{} verseLine={!r}".format( moduleName, BBB, C, V, verseLine ) )
        if BibleOrgSysGlobals.debugFlag:
            if BBB!='PSA' or V not in ('1','5',): print( "Stopped at", moduleName, BBB, C, V ); halt
    #if V == '3': halt

    # Now divide up lines and enter them
    location = '{} {} {}:{} {!r}'.format( moduleName, BBB, C, V, osisVerseString ) if debuggingThisModule else '{} {} {}:{}'.format( moduleName, BBB, C, V )
    if verseLine or V != '0':
        thisBook.addVerseSegments( V, verseLine, location )
# end of importOSISVerseLine



def importGBFVerseLine( gbfVerseString, thisBook, moduleName, BBB, C, V ):
    """
    Given a verse entry string made up of GBF (General Bible Format) segments,
        convert it into our internal format
        and add the line(s) to thisBook.

    moduleName, BBB, C, V are just used for more helpful error/information messages.

    We use \\NL** as an internal code for a newline
        to show where a verse line needs to be broken into internal chunks.

    Adds the line(s) to thisBook. No return value.
    """
    if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
        print( "\nimportGBFVerseLine( {} {} {}:{} ... {!r} )".format( moduleName, BBB, C, V, gbfVerseString ) )
    verseLine = gbfVerseString

    if moduleName == 'ASV': # Fix a module bug
        verseLine = verseLine.replace( 'pit of the<RF>1<Rf> shearing', 'pit of the<RF>2<Rf> shearing' )

    # Scan for footnote callers and callees
    lastCalled = None
    contentsDict = {}
    while True:
        match1 = re.search( '<RF>(\d{1,2}?)<Rf>', verseLine ) # Footnote caller
        if not match1: break
        caller = match1.group(1)
        match2 = re.search( '<RF>(\d{1,2}?)\\)? (.+?)<Rf>', verseLine ) # Footnote text starts with 1) or just 1
        if not match2:
            match3 = re.search( '<RF>([^\d].+?)<Rf>', verseLine )
        if match1 or match2: assert match1 and (match2 or lastCalled or match3)
        #if not match1: break
        #caller = int(match1.group(1))
        if caller in contentsDict: # We have a repeat of a previous caller
            replacement1 = '\\f + \\ft {}\\f*'.format( contentsDict[caller] )
            #print( 'replacement1 (repeat)', caller, repr(replacement1), contentsDict )
            verseLine = verseLine[:match1.start()] + replacement1 + verseLine[match1.end():]
        elif match2: # normal case -- let's separate out all of the numbered callees
            callee, contents = match2.group(1), match2.group(2).rstrip()
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                print( 'FN caller={!r} callee={!r} contents={!r} {}'.format( caller, callee, contents, contentsDict ) )
            replacement2 = '{}) {}'.format( callee, contents )
            j = 0
            while replacement2:
                #print( 'Loop {} start: now {} with replacement2={!r}'.format( j, contentsDict, replacement2 ) )
                match8 = re.search( '(\d{1,2})\\) (.*?)(\d{1,2})\\) ', replacement2 )
                match9 = re.search( '(\d{1,2})\\) ', replacement2 )
                if match8: assert match9 and match9.group(1)==match8.group(1)
                if not match9: break
                if match8: callee8a, contents8, callee8b = match8.group(1), match8.group(2), match8.group(3)
                callee9 = match9.group(1)
                if match8: # We have two parts
                    assert callee8a == callee9
                    contentsDict[callee9] = contents8
                    replacement2 = replacement2[match8.end()-2-len(callee8b):]
                    #print( 'Loop {} with match8: now {} with replacement={!r}'.format( j, contentsDict, replacement2 ) )
                else: # We only have one part
                    #print( repr(callee9), repr(callee) )
                    #assert callee9 == callee
                    contentsDict[callee9] = replacement2[len(callee9)+2:]
                    replacement2 = ''
                    #print( 'Loop {} with no match8: now {} with replacement={!r}'.format( j, contentsDict, replacement2 ) )
                j += 1
            if j==0: # We found nothing above
                contentsDict[callee] = contents
                replacement2 = ''
            replacement1 = '\\f + \\ft {}\\f*'.format( contentsDict[caller] )
            assert match2.start()>match1.start() and match2.end()>match1.end() and match2.start()>match1.end()
            verseLine = verseLine[:match1.start()] + replacement1 + \
                        verseLine[match1.end():match2.start()] + replacement2 + verseLine[match2.end():]
        elif match3: # We have a callee without a number
            assert caller == '1' # Would only work for a single footnote I think
            callee, contents = caller, match3.group(1).rstrip()
            contentsDict[caller] = contents
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                print( 'FN caller={!r} unnumbered contents={!r}'.format( caller, contents ) )
            nextOne = ' {}) '.format( int(caller)+1 )
            if nextOne in contents: # It contains the next footnote(s) as well
                halt # Not expected
            else:
                replacement3 = ''
            replacement1 = '\\f + \\ft {}\\f*'.format( contentsDict[caller] )
            #print( 'replacement1', repr(replacement1) )
            #print( 'replacement3', repr(replacement3) )
            assert match3.start()>match1.start() and match3.end()>match1.end() and match3.start()>match1.end()
            verseLine = verseLine[:match1.start()] + replacement1 + \
                        verseLine[match1.end():match3.start()] + replacement3 + verseLine[match3.end():]
        else:
            print( 'WHY FN caller={!r} callee={!r} contents={!r} {}'.format( caller, callee, contents, contentsDict ) )
            halt
        #print( repr(verseLine ) )
        lastCalled = callee, contents
    match4 = re.search( '<RF>(.+?)<Rf>', verseLine ) # Footnote that doesn't match the above system
    if match4:
        contents = match4.group(1)
        #print( 'match4', repr(contents), repr(verseLine), contentsDict )
        assert len(contents) > 2 and not contents[0].isdigit()
        replacement4 = '\\f + \\ft {}\\f*'.format( contents )
        #print( 'replacement4', repr(replacement4) )
        verseLine = verseLine[:match4.start()] + replacement4 + verseLine[match4.end():]

    # Now scan for fixed open and close fields
    replacementList = ( ('<FI>','\\it ','<Fi>','\\it*'),
                        ('<FO><FO>','\\NL**\\d ','<Fo><Fo>','\\NL**'),
                        ('<FO>','\\em ','<Fo>','\\em*'),
                        )
    verseLine = replaceFixedPairs( replacementList, verseLine )

    # Straight substitutions
    for old, new in (( '<CM>', '\\NL**\\p\\NL**' ),
                     ( '<Fo>', '\\NL**' ), # Handle left-overs
                     ( '\n', '\\NL**' ),
                      ):
        verseLine = verseLine.replace( old, new )

    # Check for anything left that we should have caught above
    if '<' in verseLine or '>' in verseLine:
        print( "{} {} {}:{} verseLine={!r}".format( moduleName, BBB, C, V, verseLine ) )
        if BibleOrgSysGlobals.debugFlag: print( moduleName, BBB, C, V ); halt

    # Now divide up lines and enter them
    location = '{} {} {}:{} {!r}'.format( moduleName, BBB, C, V, gbfVerseString ) if debuggingThisModule else '{} {} {}:{}'.format( moduleName, BBB, C, V )
    thisBook.addVerseSegments( V, verseLine, location )
# end of importGBFVerseLine



def importTHMLVerseLine( thmlVerseString, thisBook, moduleName, BBB, C, V ):
    """
    Given a verse entry string made up of THML segments,
        convert it into our internal format
        and add the line(s) to thisBook.

    moduleName, BBB, C, V are just used for more helpful error/information messages.

    We use \\NL** as an internal code for a newline
        to show where a verse line needs to be broken into internal chunks.

    Adds the line(s) to thisBook. No return value.
    """
    if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
        print( "\nimportTHMLVerseLine( {} {} {}:{} ... {!r} )".format( moduleName, BBB, C, V, thmlVerseString ) )
    verseLine = thmlVerseString

    # Straight substitutions
    for old, new in ( ( '<br />', '\\NL**' ),
                      ):
        verseLine = verseLine.replace( old, new )
    # Now scan for fixed open and close fields
    replacementList = ( ('<font color="#ff0000">','\\wj ', '</font>','\\wj*'),
                        ( '<small>', '\\sc ', '</small>', '\\sc*' ),
                        )
    verseLine = replaceFixedPairs( replacementList, verseLine )

    # Check for anything left that we should have caught above
    if '<' in verseLine or '>' in verseLine or '=' in verseLine:
        print( "{} {} {}:{} verseLine={!r}".format( moduleName, BBB, C, V, verseLine ) )
        if BibleOrgSysGlobals.debugFlag: print( moduleName, BBB, C, V ); halt

    # Now divide up lines and enter them
    location = '{} {} {}:{} {!r}'.format( moduleName, BBB, C, V, thmlVerseString ) if debuggingThisModule else '{} {} {}:{}'.format( moduleName, BBB, C, V )
    thisBook.addVerseSegments( V, verseLine, location )
# end of importTHMLVerseLine



class SwordBible( Bible ):
    """
    Class for reading, validating, and converting SwordBible files.
    """
    def __init__( self, sourceFolder=None, moduleName=None, encoding='utf-8' ):
        """
        Constructor: just sets up the Bible object.

        The sourceFolder should be the one containing mods.d and modules folders.
        The module name (if needed) should be the name of one of the .conf files in the mods.d folder
            (with or without the .conf on it).
        """
        #print( "SwordBible.__init__( {} {} {} )".format( sourceFolder, moduleName, encoding ) )
        if not sourceFolder and not moduleName:
            logging.critical( _("SwordBible must be passed either a folder path or a module name!" ) )
            return

         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = "Sword Bible object"
        self.objectTypeString = "Sword"

        # Now we can set our object variables
        self.sourceFolder, self.moduleName, self.encoding = sourceFolder, moduleName, encoding

        if self.sourceFolder:
            # Do a preliminary check on the readability of our folder
            if not os.access( self.sourceFolder, os.R_OK ):
                logging.critical( _("SwordBible: Folder {!r} is unreadable").format( self.sourceFolder ) )

            if not self.moduleName: # If we weren't passed the module name, we need to assume that there's only one
                confFolder = os.path.join( self.sourceFolder, 'mods.d/' )
                foundConfs = []
                for something in os.listdir( confFolder ):
                    somepath = os.path.join( confFolder, something )
                    if os.path.isfile( somepath ) and something.endswith( '.conf' ):
                        foundConfs.append( something[:-5] ) # Drop the .conf bit
                if foundConfs == 0:
                    logging.critical( "No .conf files found in {}".format( confFolder ) )
                elif len(foundConfs) > 1:
                    logging.critical( "Too many .conf files found in {}".format( confFolder ) )
                else:
                    print( "Got", foundConfs[0] )
                    self.moduleName = foundConfs[0]

        # Load the Sword manager and find our module
        self.SWMgr = Sword.SWMgr()
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            availableGlobalOptions = [str(option) for option in self.SWMgr.getGlobalOptions()]
            print( "availableGlobalOptions", availableGlobalOptions )
        # Don't need to set options if we use getRawEntry() rather than stripText() or renderText()
        #for optionName in ( 'Headings', 'Footnotes', 'Cross-references', "Strong's Numbers", 'Morphological Tags', ):
            #self.SWMgr.setGlobalOption( optionName, 'On' )

        if self.sourceFolder:
            self.SWMgr.augmentModules( self.sourceFolder, False ) # Add our folder to the SW Mgr
        availableModuleCodes = []
        for j,moduleBuffer in enumerate(self.SWMgr.getModules()):
            moduleID = moduleBuffer.getRawData()
            if moduleID.upper() == self.moduleName.upper(): self.moduleName = moduleID # Get the case correct
            #module = SWMgr.getModule( moduleID )
            #if 0:
                #print( "{} {} ({}) {} {!r}".format( j, module.getName(), module.getType(), module.getLanguage(), module.getEncoding() ) )
                #try: print( "    {} {!r} {} {}".format( module.getDescription(), module.getMarkup(), module.getDirection(), "" ) )
                #except UnicodeDecodeError: print( "   Description is not Unicode!" )
            #print( "moduleID", repr(moduleID) )
            availableModuleCodes.append( moduleID )
        #print( "Available module codes:", availableModuleCodes )
        if self.moduleName not in availableModuleCodes:
            logging.critical( "Unable to find {!r} Sword module".format( self.moduleName ) )
            if BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.verbosityLevel > 2:
                print( "Available module codes:", availableModuleCodes )

        self.abbreviation = self.moduleName
    # end of SwordBible.__init__


    def load( self ):
        """
        Load the compressed data file and import book elements.
        """
        if BibleOrgSysGlobals.verbosityLevel > 1: print( _("\nLoading {} module...").format( self.moduleName ) )
        module = self.SWMgr.getModule( self.moduleName )
        if module is None:
            logging.critical( "Unable to load {!r} module -- not known by Sword".format( self.moduleName ) )
            return

        markupCode = ord( module.getMarkup() )
        encoding = ord( module.getEncoding() )
        if encoding == ENC_LATIN1: self.encoding = 'latin-1'
        elif encoding == ENC_UTF8: self.encoding = 'utf-8'
        elif encoding == ENC_UTF16: self.encoding = 'utf-16'
        elif BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt

        if BibleOrgSysGlobals.verbosityLevel > 3:
            print( 'Description: {!r}'.format( module.getDescription() ) )
            print( 'Direction: {!r}'.format( ord(module.getDirection()) ) )
            print( 'Encoding: {!r}'.format( encoding ) )
            print( 'Language: {!r}'.format( module.getLanguage() ) )
            print( 'Markup: {!r}={}'.format( markupCode, FMT_DICT[markupCode] ) )
            print( 'Name: {!r}'.format( module.getName() ) )
            print( 'RenderHeader: {!r}'.format( module.getRenderHeader() ) )
            print( 'Type: {!r}'.format( module.getType() ) )
            print( 'IsSkipConsecutiveLinks: {!r}'.format( module.isSkipConsecutiveLinks() ) )
            print( 'IsUnicode: {!r}'.format( module.isUnicode() ) )
            print( 'IsWritable: {!r}'.format( module.isWritable() ) )
            #return

        bookCount = 0
        currentBBB = None
        for index in range( 0, 999999 ):
            module.setIndex( index )
            if module.getIndex() != index: break # Gone too far

            # Find where we're at
            verseKey = module.getKey()
            verseKeyText = verseKey.getShortText()
            #if '2' in verseKeyText: halt # for debugging first verses
            #if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                #print( '\nvkst={!r} vkix={}'.format( verseKeyText, verseKey.getIndex() ) )

            #nativeVerseText = module.renderText().decode( self.encoding, 'replace' )
            #nativeVerseText = str( module.renderText() ) if self.encoding=='utf-8' else str( module.renderText(), encoding=self.encoding )
            #print( 'getRenderHeader: {} {!r}'.format( len(module.getRenderHeader()), module.getRenderHeader() ) )
            #print( 'stripText: {} {!r}'.format( len(module.stripText()), module.stripText() ) )
            #print( 'renderText: {} {!r}'.format( len(str(module.renderText())), str(module.renderText()) ) )
            #print( 'getRawEntry: {} {!r}'.format( len(module.getRawEntry()), module.getRawEntry() ) )
            try: nativeVerseText = module.getRawEntry()
            #try: nativeVerseText = str( module.renderText() )
            except UnicodeDecodeError: nativeVerseText = ''

            if ':' not in verseKeyText:
                if BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.verbosityLevel > 2:
                    print( "Unusual Sword verse key: {} (gave {!r})".format( verseKeyText, nativeVerseText ) )
                if BibleOrgSysGlobals.debugFlag:
                    assert verseKeyText in ( '[ Module Heading ]', '[ Testament 1 Heading ]', '[ Testament 2 Heading ]', )
                if BibleOrgSysGlobals.verbosityLevel > 3:
                    if markupCode == FMT_OSIS:
                        match = re.search( '<milestone ([^/>]*?)type="x-importer"([^/>]*?)/>', nativeVerseText )
                        if match:
                            attributes = match.group(1) + match.group(2)
                            match2 = re.search( 'subType="(.+?)"', attributes )
                            subType = match2.group(1) if match2 else None
                            if subType and subType.startswith( 'x-' ): subType = subType[2:] # Remove the x- prefix
                            match2 = re.search( 'n="(.+?)"', attributes )
                            n = match2.group(1) if match2 else None
                            if n: n = n.replace( '$', '' ).strip()
                            print( "Module created by {} {}".format( subType, n ) )
                continue
            vkBits = verseKeyText.split()
            assert len(vkBits) == 2
            osisBBB = vkBits[0]
            BBB = BibleOrgSysGlobals.BibleBooksCodes.getBBBFromOSIS( osisBBB )
            if isinstance( BBB, list ): BBB = BBB[0] # We sometimes get a list of options -- take the first = most likely one
            vkBits = vkBits[1].split( ':' )
            assert len(vkBits) == 2
            C, V = vkBits
            #print( 'At {} {}:{}'.format( BBB, C, V ) )

            # Start a new book if necessary
            if BBB != currentBBB:
                if currentBBB is not None and haveText: # Save the previous book
                    if BibleOrgSysGlobals.verbosityLevel > 3: print( "Saving", currentBBB, bookCount )
                    self.saveBook( thisBook )
                # Create the new book
                if BibleOrgSysGlobals.verbosityLevel > 2:  print( '  Loading {} {}...'.format( self.moduleName, BBB ) )
                thisBook = BibleBook( self, BBB )
                thisBook.objectNameString = "Sword Bible Book object"
                thisBook.objectTypeString = "Sword Bible"
                currentBBB, currentC, haveText = BBB, '0', False
                bookCount += 1

            if C != currentC:
                thisBook.addLine( 'c', C )
                #if C == '2': halt
                currentC = C

            if nativeVerseText:
                haveText = True
                if markupCode == FMT_OSIS: importOSISVerseLine( nativeVerseText, thisBook, self.moduleName, BBB, C, V )
                elif markupCode == FMT_GBF: importGBFVerseLine( nativeVerseText, thisBook, self.moduleName, BBB, C, V )
                elif markupCode == FMT_THML: importTHMLVerseLine( nativeVerseText, thisBook, self.moduleName, BBB, C, V )
                else:
                    print( 'markupCode', repr(markupCode) )
                    if BibleOrgSysGlobals.debugFlag: halt
                    return

        if currentBBB is not None and haveText: # Save the very last book
            if BibleOrgSysGlobals.verbosityLevel > 3: print( "Saving", self.moduleName, currentBBB, bookCount )
            self.saveBook( thisBook )

        self.doPostLoadProcessing()
    # end of SwordBible.load
# end of SwordBible class



def testSwB( SwFolderPath, SwModuleName=None ):
    """
    Crudely demonstrate and test the Sword Bible class
    """
    import VerseReferences

    if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Demonstrating the Sword Bible class...") )
    if BibleOrgSysGlobals.verbosityLevel > 0: print( "  Test folder is {!r} {!r}".format( SwFolderPath, SwModuleName ) )
    SwBible = SwordBible( SwFolderPath, SwModuleName )
    SwBible.load() # Load and process the file
    if BibleOrgSysGlobals.verbosityLevel > 1: print( SwBible ) # Just print a summary
    if BibleOrgSysGlobals.strictCheckingFlag:
        SwBible.check()
        #print( UsfmB.books['GEN']._processedLines[0:40] )
        SwBErrors = SwBible.getErrors()
        # print( SwBErrors )
    if BibleOrgSysGlobals.commandLineArguments.export:
        ##SwBible.toDrupalBible()
        SwBible.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
    for reference in ( ('OT','GEN','1','1'), ('OT','GEN','1','3'), ('OT','PSA','3','0'), ('OT','PSA','3','1'),
                        ('OT','DAN','1','21'),
                        ('NT','MAT','1','1'), ('NT','MAT','3','5'), ('NT','MAT','3','8'),
                        ('NT','JDE','1','4'), ('NT','REV','22','21'),
                        ('DC','BAR','1','1'), ('DC','MA1','1','1'), ('DC','MA2','1','1',), ):
        (t, b, c, v) = reference
        if t=='OT' and len(SwBible)==27: continue # Don't bother with OT references if it's only a NT
        if t=='NT' and len(SwBible)==39: continue # Don't bother with NT references if it's only a OT
        if t=='DC' and len(SwBible)<=66: continue # Don't bother with DC references if it's too small
        svk = VerseReferences.SimpleVerseKey( b, c, v )
        #print( svk, SwBible.getVerseDataList( reference ) )
        shortText = svk.getShortText()
        try:
            verseText = SwBible.getVerseText( svk )
            fullVerseText = SwBible.getVerseText( svk, fullTextFlag=True )
        except KeyError:
            verseText = fullVerseText = "Verse not available!"
        if BibleOrgSysGlobals.verbosityLevel > 1:
            if BibleOrgSysGlobals.debugFlag: print()
            print( reference, shortText, verseText )
            if BibleOrgSysGlobals.debugFlag: print( '  {}'.format( fullVerseText ) )
    return SwBible
# end of testSwB


def demo():
    """
    Main program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( ProgNameVersion )


    testFolder = '/home/robert/.sword/'
    # Matigsalug_Test module
    testFolder = '../../../../../Data/Websites/Freely-Given.org/Software/BibleDropBox/Matigsalug.USFM.Demo/Sword_(from OSIS_Crosswire_Python)/CompressedSwordModule'


    if 0: # demo the file checking code -- first with the whole folder and then with only one folder
        result1 = SwordBibleFileCheck( testFolder )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Sword TestA1", result1 )
        result2 = SwordBibleFileCheck( testFolder, autoLoad=True )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Sword TestA2", result2 )
        result3 = SwordBibleFileCheck( testFolder, autoLoadBooks=True )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Sword TestA3", result3 )

    if 0: # specify testFolder containing a single module
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nSword B/ Trying single module in {}".format( testFolder ) )
        testSwB( testFolder )

    if 0: # specified single installed module
        singleModule = 'ASV'
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nSword C/ Trying installed {} module".format( singleModule ) )
        SwBible = testSwB( None, singleModule )
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: # Print the index of a small book
            BBB = 'JN1'
            if BBB in SwBible:
                SwBible.books[BBB].debugPrint()
                for entryKey in SwBible.books[BBB]._CVIndex:
                    print( BBB, entryKey, SwBible.books[BBB]._CVIndex.getEntries( entryKey ) )

    if 1: # specified installed modules
        good = ('KJV','WEB','KJVA','YLT','ASV','LEB','ESV','ISV','NET','OEB',
                'AB','ABP','ACV','AKJV','BBE','BSV','BWE','CPDV','Common','DRC','Darby',
                'EMTV','Etheridge','Geneva1599','Godbey','GodsWord','JPS','KJVPCE','LITV','LO','Leeser',
                'MKJV','Montgomery','Murdock','NETfree','NETtext','NHEB','NHEBJE','NHEBME','Noyes',
                'OEBcth','OrthJBC','RKJNT','RNKJV','RWebster','RecVer','Rotherham',
                'SPE','TS1998','Twenty','Tyndale','UKJV','WEBBE','WEBME','Webster','Weymouth','Worsley',)
        nonEnglish = (  )
        bad = ( )
        for j, testFilename in enumerate( good ): # Choose one of the above: good, nonEnglish, bad
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nSword D{}/ Trying {}".format( j+1, testFilename ) )
            #myTestFolder = os.path.join( testFolder, testFilename+'/' )
            #testFilepath = os.path.join( testFolder, testFilename+'/', testFilename+'_utf8.txt' )
            testSwB( testFolder, testFilename )


    if 0: # all discovered modules in the test folder
        foundFolders, foundFiles = [], []
        for something in os.listdir( testFolder ):
            somepath = os.path.join( testFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )

        if BibleOrgSysGlobals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nTrying all {} discovered modules...".format( len(foundFolders) ) )
            parameters = [(testFolder,folderName) for folderName in sorted(foundFolders)]
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.map( testSwB, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
        else: # Just single threaded
            for j, someFolder in enumerate( sorted( foundFolders ) ):
                if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nSword E{}/ Trying {}".format( j+1, someFolder ) )
                #myTestFolder = os.path.join( testFolder, someFolder+'/' )
                testSwB( testFolder, someFolder )
# end of demo


if __name__ == '__main__':
    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( ProgName, ProgVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    demo()

    BibleOrgSysGlobals.closedown( ProgName, ProgVersion )
# end of SwordBible.py