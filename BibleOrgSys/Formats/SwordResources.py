#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# SwordResources.py
#
# Interface module handling Sword resources
#   using either the Sword engine (if available) or else our own software
#
# Copyright (C) 2013-2020 Robert Hunt
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
This is the interface module used to give a unified interface to either:
    1/ The Crosswire Sword engine (libsword) via Python3 SWIG bindings,
        or, if that's not available, to
    2/ Our own SwordInstallManager.py which downloads modules from remote
        repositories, and our (still primitive) module that reads Sword
        files directly called SwordModules.py
"""
from gettext import gettext as _
from typing import List, Optional
import logging
import re

if __name__ == '__main__':
    import os.path
    import sys
    aboveAboveFolderPath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderPath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderPath )
from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import vPrint

#from BibleOrgSys.Misc.singleton import singleton
from BibleOrgSys.Reference.VerseReferences import SimpleVerseKey
from BibleOrgSys.Internals.InternalBibleInternals import InternalBibleEntryList, InternalBibleEntry


LAST_MODIFIED_DATE = '2020-04-16' # by RJH
SHORT_PROGRAM_NAME = "SwordResources"
PROGRAM_NAME = "Sword resource handler"
PROGRAM_VERSION = '0.30'
programNameVersion = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

debuggingThisModule = False



logger = logging.getLogger(SHORT_PROGRAM_NAME)



SwordType = None
try:
    import Sword # Python bindings for the Crosswire Sword C++ library
    SwordType = 'CrosswireLibrary'
    SWORD_TEXT_DIRECTIONS = { Sword.DIRECTION_LTR:'LTR', Sword.DIRECTION_RTL:'RTL', Sword.DIRECTION_BIDI:'BiDi' }
    SWORD_MARKUPS = { Sword.FMT_UNKNOWN:'Unknown', Sword.FMT_PLAIN:'Plain', Sword.FMT_THML:'THML',
                     Sword.FMT_GBF:'GBF', Sword.FMT_HTML:'HTML', Sword.FMT_HTMLHREF:'HTMLHREF',
                     Sword.FMT_RTF:'RTF', Sword.FMT_OSIS:'OSIS', Sword.FMT_WEBIF:'WEBIF',
                     Sword.FMT_TEI:'TEI', Sword.FMT_XHTML:'XHTML' }
    try: SWORD_MARKUPS[Sword.FMT_LATEX] = 'LaTeX'
    except AttributeError: pass # Sword 1.7.4 doesn't have this
    SWORD_ENCODINGS = { Sword.ENC_UNKNOWN:'Unknown', Sword.ENC_LATIN1:'Latin1',
                    Sword.ENC_UTF8:'UTF8', Sword.ENC_SCSU:'SCSU', Sword.ENC_UTF16:'UTF16',
                    Sword.ENC_RTF:'RTF', Sword.ENC_HTML:'HTML' }
    from BibleOrgSys.Bible import BibleBook
    try: from BibleOrgSys.Formats import SwordModules #anyway, even if only used for testing
    except ImportError: pass # doesn't really matter
except (ImportError, ModuleNotFoundError): # Sword library (dll and python bindings) seem to be not available
    try:
        from BibleOrgSys.Formats import SwordModules # Not as good/reliable/efficient/well-tested/up-to-date as the real Sword library, but better than nothing
        SwordType = 'OurCode'
    except ImportError:
        logger.critical( _("You don't appear to have any way installed to read Sword modules.") )


def setSwordType( newType:str ) -> None:
    """
    Used for testing.

    Sets the global SwordType to a different value
    """
    global SwordType
    assert newType in ('CrosswireLibrary', 'OurCode' )
    oldType = SwordType
    assert oldType in ('CrosswireLibrary', 'OurCode' )
    SwordType = newType
    if BibleOrgSysGlobals.verbosityLevel > 0 and newType != oldType:
        vPrint( 'Quiet', debuggingThisModule, f"SwordResources.SwordType changed to '{newType}'." )
# end of setSwordType


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
            #vPrint( 'Quiet', debuggingThisModule, '{} {!r}->{!r} {!r}->{!r} in {!r}'.format( ix, openCode,newOpenCode,closeCode,newCloseCode, verseLine ) )
            verseLine = verseLine.replace( openCode, newOpenCode, 1 )
            ixEnd = verseLine.find( closeCode, ix )
            if ixEnd == -1:
                logger.error( 'Missing {!r} close code to match {!r}'.format( closeCode, openCode ) )
                verseLine = verseLine + newCloseCode # Try to fix it by adding a closing code at the end
            else:
                verseLine = verseLine.replace( closeCode, newCloseCode, 1 )
            ix = verseLine.find( openCode, ix )
        if verseLine.find( closeCode ) != -1:
            logger.error( 'Unexpected {!r} close code without any previous {!r}'.format( closeCode, openCode )  )
            verseLine = verseLine.replace( closeCode, newCloseCode, 1 )
            # Try to fix it by adding an opening code at or near the beginning of the line
            #   but we have to skip past any paragraph markers
            insertIndex = 0
            while verseLine[insertIndex] == '\\':
                insertIndex += 1
                while insertIndex < len(verseLine)-1:
                    if verseLine[insertIndex] == ' ': break
                    insertIndex += 1
            if insertIndex != 0 and debuggingThisModule: vPrint( 'Quiet', debuggingThisModule, "insertIndex={} vL={!r}".format( insertIndex, verseLine ) )
            verseLine = verseLine[:insertIndex] + ' '+newOpenCode + verseLine[insertIndex:]
            if insertIndex != 0 and debuggingThisModule: vPrint( 'Quiet', debuggingThisModule, "new vL={!r}".format( verseLine ) )

    return verseLine
# end of replaceFixedPairs



def filterOSISVerseLine( osisVerseString, moduleName, BBB, C, V ):
    """
    Given a verse entry string made up of OSIS segments,
        convert it into our internal format

    moduleName, BBB, C, V are just used for more helpful error/information messages.

    OSIS is a pig to extract the information out of,
        but we use it nevertheless because it's the native format
        and hence most likely to represent the original well.

    We use \\NL** as an internal code for a newline
        to show where a verse line needs to be broken into internal chunks.

    Returns the filtered line(s).
    """
    if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
        vPrint( 'Quiet', debuggingThisModule, "\nfilterOSISVerseLine( {} {} {}:{} … {!r} )".format( moduleName, BBB, C, V, osisVerseString ) )

    verseLine = osisVerseString
    haveFootnoteFlag = False


    def handleOSISWordAttributes( attributeString ):
        """
        Handle OSIS XML attributes from the <w …> field.

        Returns the string to replace the attributes.
        """
        originalAttributeString = attributeString

        attributeReplacementResult = ''
        attributeCount = attributeString.count( '="' )
        #vPrint( 'Quiet', debuggingThisModule, 'Attributes={} {!r}'.format( attributeCount, attributeString ) )
        for j in range( attributeCount ):
            match2 = re.search( 'savlm="(.+?)"', attributeString )
            if match2:
                savlm = match2.group(1)
                #vPrint( 'Quiet', debuggingThisModule, 'savlm', repr(savlm) )
                while True:
                    match3 = re.search( 'strong:([GH]\d{1,5})', savlm )
                    if not match3: break
                    #vPrint( 'Quiet', debuggingThisModule, 'string', repr(match3.group(1) ) )
                    attributeReplacementResult += '\\str {}\\str*'.format( match3.group(1) )
                    savlm = savlm[:match3.start()] + savlm[match3.end():] # Remove this Strongs' number
                attributeString = attributeString[:match2.start()] + attributeString[match2.end():] # Remove this attribute entry

            match2 = re.search( 'lemma="(.+?)"', attributeString )
            if match2:
                lemma = match2.group(1)
                #vPrint( 'Quiet', debuggingThisModule, 'lemma', repr(lemma) )
                while True:
                    match3 = re.search( 'strong:([GH]\d{1,5})', lemma )
                    if not match3: break
                    #vPrint( 'Quiet', debuggingThisModule, 'string', repr(match3.group(1) ) )
                    attributeReplacementResult += '\\str {}\\str*'.format( match3.group(1) )
                    lemma = lemma[:match3.start()] + lemma[match3.end():] # Remove this Strongs' number
                attributeString = attributeString[:match2.start()] + attributeString[match2.end():] # Remove this attribute entry

            match2 = re.search( 'morph="(.+?)"', attributeString )
            if match2:
                morph = match2.group(1)
                #vPrint( 'Quiet', debuggingThisModule, 'morph', repr(morph) )
                while True:
                    match3 = re.search( 'strongMorph:(TH\d{1,4})', morph )
                    if not match3: break
                    #vPrint( 'Quiet', debuggingThisModule, 'string', repr(match3.group(1) ) )
                    attributeReplacementResult += '\\morph {}\\morph*'.format( match3.group(1) )
                    morph = morph[:match3.start()] + morph[match3.end():] # Remove this Strongs' number
                attributeString = attributeString[:match2.start()] + attributeString[match2.end():] # Remove this attribute entry

            match2 = re.search( 'type="(.+?)"', attributeString )
            if match2:
                typeValue = match2.group(1)
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                    vPrint( 'Quiet', debuggingThisModule, 'handleOSISWordAttributes CH424 {} {} {}:{} typeValue {!r} \n  from {!r}' \
                        .format( moduleName, BBB, C, V, typeValue, originalAttributeString ) ) # Seems to have an incrementing value on the end for some reason
                # In wlc module it's x-ketiv or x-qere
                assert typeValue in ('x-ketiv','x-qere','x-invertednun',) \
                or typeValue.startswith( 'x-split' ) # e.g., x-split or x-split-1 -- what do these mean?
                attributeString = attributeString[:match2.start()] + attributeString[match2.end():] # Remove this attribute entry
            match2 = re.search( 'subType="(.+?)"', attributeString )
            if match2:
                subType = match2.group(1)
                #vPrint( 'Quiet', debuggingThisModule, 'subType', repr(subType) ) # e.g., x-28 -- what does this mean?
                attributeString = attributeString[:match2.start()] + attributeString[match2.end():] # Remove this attribute entry

            match2 = re.search( 'src="(.+?)"', attributeString ) # Can be two numbers separated by a space!
            if match2:
                src = match2.group(1)
                #vPrint( 'Quiet', debuggingThisModule, 'src', repr(src) ) # What does this mean?
                attributeString = attributeString[:match2.start()] + attributeString[match2.end():] # Remove this attribute entry

            match2 = re.search( 'gloss="(.+?)"', attributeString )
            if match2:
                gloss = match2.group(1)
                #vPrint( 'Quiet', debuggingThisModule, 'gloss', repr(gloss) ) # What does this mean?
                attributeString = attributeString[:match2.start()] + attributeString[match2.end():] # Remove this attribute entry

            match2 = re.search( 'wn="(\d+?)"', attributeString )
            if match2:
                wn = match2.group(1)
                #vPrint( 'Quiet', debuggingThisModule, 'wn', repr(wn) ) # What does this mean?
                attributeString = attributeString[:match2.start()] + attributeString[match2.end():] # Remove this attribute entry

        if attributeString.strip():
            vPrint( 'Quiet', debuggingThisModule, 'Unhandled {} word attributes: {!r} from {!r}'.format( moduleName, attributeString, originalAttributeString ) )
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
        #vPrint( 'Quiet', debuggingThisModule, 'attributeReplacementResult', repr(attributeReplacementResult) )
        return attributeReplacementResult
    # end of handleOSISWordAttributes


    # Start of main code for filterOSISVerseLine
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
                      ( '<title subtype="x-preverse" type="section"></title>', '' ), # NetFree why???
                      ):
        verseLine = verseLine.replace( old, new )

    # Delete info line(s)
    match = re.search( '<milestone type="x-importer" subType="x-osis2mod" n="\\$Rev: .+? \\$"/>', verseLine )
    if match:
        verseLine = verseLine[:match.start()] + verseLine[match.end():] # Delete it

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
        #vPrint( 'Quiet', debuggingThisModule, "filterOSISVerseLine QP472 {} {} {}:{} Div section attributes={!r} from {!r}".format( moduleName, BBB, C, V, attributes, verseLine ) )
        if moduleName not in ('mxt_BL_1983','zpq_BL_1987',): # has both!
            if moduleName in ('farflb','ury_WBTI_2005','vietlccmn','vietnvb',):
                assert len(attributes) == 0 # seems to have no other attributes
            else: assert 'scope="' in attributes
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
    match = re.search( '<chapter ([^/>]*?)sID="([^/>]+?)"([^/>]*?)/>', verseLine ) # milestone (self-closing)
    if match:
        attributes, sID = match.group(1) + match.group(3), match.group(2)
        #vPrint( 'Quiet', debuggingThisModule, 'filterOSISVerseLine CD734 {} {} {}:{} Chapter sID {!r} attributes={!r}'.format( moduleName, BBB, C, V, sID, attributes ) )
        assert C and C != '0'
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            if moduleName not in ('adg','agl','bela','bur','chv','cslelizabeth','ctt','frekhan','kaz','khk',
                              'mapm','oshb','oss','porcap','ruscars','russynodal',) \
            and BBB not in ('EZR','NEH','EST','JOB','PSA','PRO','ECC',): # not sure what this is about---------needs attention
                assert V == '0'
        #if BibleOrgSysGlobals.debugFlag and debuggingThisModule: vPrint( 'Quiet', debuggingThisModule, "CCCC {!r}(:{!r})".format( C, V ) )
        verseLine = verseLine[:match.start()] + verseLine[match.end():]
    match = re.search( '<chapter ([^/>]*?)osisID="([^/>]+?)"([^/>]*?)>', verseLine ) # open chapter container
    if match:
        attributes, osisID = match.group(1) + match.group(3), match.group(2)
        #vPrint( 'Quiet', debuggingThisModule, 'Chapter osisID {!r} attributes={!r} @ {} {}:{}'.format( osisID, attributes, BBB, C, V ) )
        #assert C and C != '0'
        assert V == '0'
        #if BibleOrgSysGlobals.debugFlag and debuggingThisModule: vPrint( 'Quiet', debuggingThisModule, "CCCC {!r}(:{!r})".format( C, V ) )
        verseLine = verseLine[:match.start()] + verseLine[match.end():]
    verseLine = verseLine.replace( '</chapter>', '' )
    while True:
        match = re.search( '<div ([^/>]*?)type="([^/>]+?)"([^/>]*?)/?> ?<title>(.+?)</title>', verseLine )
        if not match: break
        attributes, sectionType, words = match.group(1) + match.group(3), match.group(2), match.group(4)
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            vPrint( 'Quiet', debuggingThisModule, 'Div title {!r} attributes={!r} Words={!r}'.format( sectionType, attributes, words ) )
        if sectionType == 'section': titleMarker = 's1'
        elif sectionType == 'subSection': titleMarker = 's2'
        elif sectionType == 'majorSection': titleMarker = 'ms'
        elif sectionType == 'book': titleMarker = 'mt1'
        elif sectionType == 'bookGroup': titleMarker = 'ms1'
        elif sectionType == 'introduction': titleMarker = 'iot'
        elif sectionType == 'x-majorSection1': titleMarker = 'ms1' # in vietlccmn
        elif sectionType == 'x-majorSection2': titleMarker = 'ms2' # in vietlccmn
        elif sectionType == 'x-subSubSection': titleMarker = 's3'
        elif sectionType == 'x-subSubSubSection': titleMarker = 's4'
        else:
            vPrint( 'Quiet', debuggingThisModule, 'filterOSISVerseLine HF253 matched:', repr(match.group(0)) ); halt
            if BibleOrgSysGlobals.debugFlag or debuggingThisModule: halt
        replacement = '\\NL**\\{} {}\\NL**'.format( titleMarker, words )
        #vPrint( 'Quiet', debuggingThisModule, 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
    match = re.search( '<div ([^/>]*?)type="([^/>]+?)"([^/>]*?)/><title>', verseLine )
    if match: # handle left over div/title start fields
        attributes, sectionType = match.group(1) + match.group(3), match.group(2)
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            vPrint( 'Quiet', debuggingThisModule, 'Section title start {!r} attributes={!r}'.format( sectionType, attributes ) )
        if sectionType == 'section': titleMarker = 's1'
        elif sectionType == 'subSection': titleMarker = 's2'
        elif sectionType == 'x-subSubSection': titleMarker = 's3'
        else: vPrint( 'Quiet', debuggingThisModule, 'filterOSISVerseLine CV745 matched:', repr(match.group(0)) ); halt
        replacement = '\\NL**\\{} '.format( titleMarker )
        #vPrint( 'Quiet', debuggingThisModule, 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
    while True:
        match = re.search( '<div ([^/>]*?)type="([^/>]+?)"([^/>]*?)/>.NL..<head>(.+?)</head>', verseLine )
        if not match: break
        attributes, sectionType, words = match.group(1) + match.group(3), match.group(2), match.group(4)
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: vPrint( 'Quiet', debuggingThisModule, 'Section title {!r} attributes={!r} Words={!r}'.format( sectionType, attributes, words ) )
        if sectionType == 'outline': titleMarker = 'iot'
        else: vPrint( 'Quiet', debuggingThisModule, 'filterOSISVerseLine KG535 matched:', repr(match.group(0)) ); halt
        replacement = '\\NL**\\{} {}\\NL**'.format( titleMarker, words )
        #vPrint( 'Quiet', debuggingThisModule, 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
    while True:
        match = re.search( '<div ([^/>]*?)type="([^/>]+?)"([^/>]*?)/?>', verseLine )
        if not match: break
        attributes, divType = match.group(1) + match.group(3), match.group(2)
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: vPrint( 'Quiet', debuggingThisModule, 'Div type={!r} attributes={!r}'.format( divType, attributes ) )
        if divType == 'x-p': replacement = '\\NL**\\p\\NL**'
        elif divType == 'glossary': replacement = '\\NL**\\id GLO\\NL**' #### WEIRD -- appended to 3 John
        elif divType == 'book': replacement = '' # We don't need this
        elif divType == 'outline': replacement = '\\NL**\\iot '
        elif divType == 'paragraph': replacement = '\\NL**\\ip ' if C=='-1' else '\\NL**\\p\\NL**'
        elif divType == 'majorSection': replacement = '\\NL**\\ms\\NL**'
        elif divType == 'section': replacement = '\\NL**\\s1 '
        elif divType == 'subSection': replacement = '\\NL**\\s2 '
        elif divType == 'afterword': replacement = '\\NL**\\cls ' # or pmc ???
        elif divType == 'x-subSubSection': replacement = '\\NL**\\s3 '
        elif divType == 'x-Synodal-empty': replacement = '\\NL**\\rem DIV Synodal-empty'
        elif divType in ( 'preface', 'titlePage', 'introduction', ): replacement = '\\NL**\\ip '
        elif divType in ( 'x-license', 'x-trademark', ): replacement = '\\NL**\\rem '
        elif divType.startswith( 'x-' ): replacement = '\\NL**\\rem DIV {} '.format( divType[2:] )
        else:
            vPrint( 'Quiet', debuggingThisModule, 'filterOSISVerseLine CS456 matched:', repr(match.group(0)) )
            if BibleOrgSysGlobals.debugFlag or debuggingThisModule: halt
            replacement = '\\NL**\\rem DIV {} '.format( divType[2:] )
        #vPrint( 'Quiet', debuggingThisModule, 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
    verseLine = verseLine.replace( '</div>', '' )
    while True:
        match = re.search( '<title type="parallel"><reference type="parallel">(.+?)</reference></title>', verseLine )
        if not match: break
        reference = match.group(1)
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: vPrint( 'Quiet', debuggingThisModule, 'Parallel reference={!r}'.format( reference ) )
        replacement = '\\NL**\\r {}\\NL**'.format( reference )
        #vPrint( 'Quiet', debuggingThisModule, 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
    while True:
        match = re.search( '<title type="scope"><reference>(.+?)</reference></title>', verseLine )
        if not match: break
        reference = match.group(1)
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: vPrint( 'Quiet', debuggingThisModule, 'Section Parallel reference={!r}'.format( reference ) )
        replacement = '\\NL**\\sr {}\\NL**'.format( reference )
        #vPrint( 'Quiet', debuggingThisModule, 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
    while True:
        match = re.search( '<title ([^/>]+?)>(.+?)</title>', verseLine )
        if not match: break
        attributes, words = match.group(1), match.group(2)
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: vPrint( 'Quiet', debuggingThisModule, 'Title attributes={!r} Words={!r}'.format( attributes, words ) )
        titleMarker = 's1'
        replacement = '\\NL**\\{} {}\\NL**'.format( titleMarker, words )
        #vPrint( 'Quiet', debuggingThisModule, 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
    verseLine = verseLine.replace( '</title>', '\\NL**' )
    verseLine = verseLine.replace( '<title>', '\\NL**\\s1 ' )
    while True:
        match = re.search( '<w ([^/>]+?)/>', verseLine )
        if not match: break
        replacement = handleOSISWordAttributes( match.group(1) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
        #vPrint( 'Quiet', debuggingThisModule, "verseLineB", repr(verseLine) )
    while True:
        match = re.search( '<w ([^/>]+?)>(.*?)</w>', verseLine ) # Can have no words inside
        if not match: break
        attributes, words = match.group(1), match.group(2)
        #vPrint( 'Quiet', debuggingThisModule, 'AttributesC={!r} Words={!r}'.format( attributes, words ) )
        replacement = words
        replacement += handleOSISWordAttributes( attributes )
        #vPrint( 'Quiet', debuggingThisModule, 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
        #vPrint( 'Quiet', debuggingThisModule, "\nverseLineW", repr(verseLine) )
    while True:
        match = re.search( '<q ([^/>]+?)>(.+?)</q>', verseLine )
        if not match: break
        attributes, words = match.group(1), match.group(2)
        if 'who="Jesus"' in attributes:
            if 'marker="' in attributes and 'marker=""' not in attributes:
                #vPrint( 'Quiet', debuggingThisModule, 'AttributesQM={!r} Words={!r}'.format( attributes, words ) )
                if BibleOrgSysGlobals.debugFlag: halt
            replacement = '\\wj {}\\wj*'.format( words )
        else:
            #vPrint( 'Quiet', debuggingThisModule, 'AttributesQ={!r} Words={!r}'.format( attributes, words ) )
            if BibleOrgSysGlobals.debugFlag: halt
        #vPrint( 'Quiet', debuggingThisModule, 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
    while True:
        match = re.search( '<q ([^/>]+?)>', verseLine ) # Leftovers (no </q>)
        if not match: break
        attributes = match.group(1)
        if 'who="Jesus"' in attributes:
            if 'marker="' in attributes and 'marker=""' not in attributes:
                #vPrint( 'Quiet', debuggingThisModule, 'AttributesQM={!r} Words={!r}'.format( attributes, words ) )
                if BibleOrgSysGlobals.debugFlag: halt
            replacement = '\\wj '
        else:
            #vPrint( 'Quiet', debuggingThisModule, 'AttributesQ={!r} Words={!r}'.format( attributes, words ) )
            if BibleOrgSysGlobals.debugFlag: halt
        #vPrint( 'Quiet', debuggingThisModule, 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
    while True:
        match = re.search( '<q ([^/>]*?)sID="(.+?)"(.*?)/>', verseLine )
        if not match: break
        attributes, sID = match.group(1) + match.group(3), match.group(2)
        #vPrint( 'Quiet', debuggingThisModule, 'Q attributesC={!r} sID={!r}'.format( attributes, sID ) )
        match2 = re.search( 'level="(.+?)"', attributes )
        level = match2.group(1) if match2 else '1'
        match2 = re.search( 'marker="(.+?)"', attributes )
        quoteSign = match2.group(1) if match2 else ''
        replacement = '\\NL**\\q{} {}'.format( level, quoteSign )
        #vPrint( 'Quiet', debuggingThisModule, 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
    while True:
        match = re.search( '<q ([^/>]*?)eID="(.+?)"(.*?)/>', verseLine )
        if not match: break
        attributes, eID = match.group(1) + match.group(3), match.group(2)
        #vPrint( 'Quiet', debuggingThisModule, 'Q attributesC={!r} eID={!r}'.format( attributes, eID ) )
        match2 = re.search( 'marker="(.+?)"', attributes )
        quoteSign = match2.group(1) if match2 else ''
        replacement = '{}\\NL**'.format( quoteSign )
        #vPrint( 'Quiet', debuggingThisModule, 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
    while True:
        match = re.search( '<q ([^/>]*?)type="block"(.*?)/>', verseLine )
        if not match: break
        attributes = match.group(1) + match.group(2)
        replacement = '\\NL**\\pc '
        #vPrint( 'Quiet', debuggingThisModule, 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
    while True:
        match = re.search( '<q(.*?)>(.+?)</q>', verseLine )
        if not match: break
        attributes, words = match.group(1), match.group(2)
        replacement = '\\NL**\\pc {}\\NL**'.format( words )
        #vPrint( 'Quiet', debuggingThisModule, 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
    while True:
        match = re.search( '<l ([^/>]*?)level="([^/>]+?)"([^/>]*?)/>', verseLine ) # self-closing l
        if not match: break
        attributes, level = match.group(1)+match.group(3), match.group(2)
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            vPrint( 'Quiet', debuggingThisModule, 'filterOSISVerseLine AD354 {} {} {}:{} AttributesL={!r} Level={!r} \n  from {!r}'.format( moduleName, BBB, C, V, attributes, level, verseLine ) )
        assert level in '1234'
        if 'sID="' in attributes:
            replacement = '\\NL**\\q{} '.format( level )
        elif 'eID="' in attributes:
            replacement = '' # Remove eIDs completely
        else:
            vPrint( 'Quiet', debuggingThisModule, 'filterOSISVerseLine MR562 Level attributesLl2={!r} Level={!r}'.format( attributes, level ) )
            halt
        #vPrint( 'Quiet', debuggingThisModule, 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
    while True:
        match = re.search( '<l ([^/>]+?)/>', verseLine )
        if not match: break
        attributes = match.group(1)
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            vPrint( 'Quiet', debuggingThisModule, 'filterOSISVerseLine SJ430 Level Attributes={!r}'.format( attributes ) )
        if 'sID="' in attributes:
            replacement = '\\NL**\\q1 '
        elif 'eID="' in attributes:
            replacement = '\\NL**' # Remove eIDs completely
        else:
            vPrint( 'Quiet', debuggingThisModule, 'filterOSISVerseLine BD534 AttributesL2={!r} Level={!r}'.format( attributes, level ) )
            halt
        #vPrint( 'Quiet', debuggingThisModule, 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
    while True: # handle list items
        match = re.search( '<item ([^/>]*?)type="(.+?)"([^/>]*?)>(.+?)</item>', verseLine )
        if not match: break
        attributes, itemType, item = match.group(1)+match.group(3), match.group(2), match.group(4)
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            vPrint( 'Quiet', debuggingThisModule, 'filterOSISVerseLine ND463 {} Item={!r} Type={!r} attributes={!r}'.format( moduleName, item, itemType, attributes ) )
        assert itemType in ( 'x-indent-1', 'x-indent-2', 'x-listitem', )
        marker = 'io' if 'x-introduction' in attributes else 'li'
        replacement = '\\NL**\\{} {}\\NL**'.format( marker+itemType[-1], item )
        #vPrint( 'Quiet', debuggingThisModule, 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
    match = re.search( '<item ([^/>]*?)type="(.+?)"([^/>]*?)>', verseLine )
    if match: # Handle left-over list items
        attributes, itemType = match.group(1)+match.group(3), match.group(2)
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: vPrint( 'Quiet', debuggingThisModule, 'Item Type={!r} attributes={!r}'.format( itemType, attributes ) )
        assert itemType in ( 'x-indent-1', 'x-indent-2', )
        marker = 'io' if 'x-introduction' in attributes else 'li'
        replacement = '\\NL**\\{}\\NL**'.format( marker+itemType[-1] )
        #vPrint( 'Quiet', debuggingThisModule, 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
    verseLine = verseLine.replace( '</item>', '\\NL**' )
    while True: # handle names
        match = re.search( '<name ([^/>]*?)type="(.+?)"([^/>]*?)>(.+?)</name>', verseLine )
        if not match: break
        attributes, nameType, name = match.group(1)+match.group(3), match.group(2), match.group(4)
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: vPrint( 'Quiet', debuggingThisModule, 'Name={!r} Type={!r} attributes={!r}'.format( name, nameType, attributes ) )
        if nameType == 'x-workTitle': marker = 'bk'
        else: halt
        replacement = '\\{} {}\\{}*'.format( marker, name, marker )
        #vPrint( 'Quiet', debuggingThisModule, 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
    while True:
        match = re.search( '<seg ([^/>]+?)>([^<]+?)</seg>', verseLine )
        if not match: break
        attributes, words = match.group(1), match.group(2)
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: vPrint( 'Quiet', debuggingThisModule, 'Seg attributes={!r} Words={!r}'.format( attributes, words ) )
        if 'type="keyword"' in attributes: replacement = '\\k {}\\k*'.format( words)
        elif 'type="verseNumber"' in attributes: replacement = '\\vp {}\\NL**'.format( words)
        elif 'type="x-us-time"' in attributes: replacement = '{}'.format( words)
        elif 'type="x-transChange"' in attributes and 'subType="x-added"' in attributes: replacement = '\\add {}\\add*'.format( words)
        elif 'type="x-big"' in attributes: replacement = '\\em {}\\em*'.format( words) # not sure what this should be
        else:
            #vPrint( 'Quiet', debuggingThisModule, 'filterOSISVerseLine FG353 {} {} {}:{} Matched: {!r}'.format( moduleName, BBB, C, V, match.group(0) ) )
            if BibleOrgSysGlobals.debugFlag or debuggingThisModule: halt
            replacement = '\\it {}\\it*'.format( words) # default to italic
        #vPrint( 'Quiet', debuggingThisModule, 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
        #vPrint( 'Quiet', debuggingThisModule, "verseLineC", repr(verseLine) )
    while True:
        match = re.search( '<foreign ([^/>]+?)>(.+?)</foreign>', verseLine )
        if not match: break
        attributes, words = match.group(1), match.group(2)
        #vPrint( 'Quiet', debuggingThisModule, 'Attributes={!r} Words={!r}'.format( attributes, words ) )
        replacement = '\\tl {}\\tl*'.format( words )
        #vPrint( 'Quiet', debuggingThisModule, 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
        #vPrint( 'Quiet', debuggingThisModule, "verseLineC", repr(verseLine) )
    while True:
        match = re.search( '<reference([^/>]*?)>(.+?)</reference>', verseLine )
        if not match: break
        attributes, referenceField = match.group(1), match.group(2)
        #if attributes: vPrint( 'Quiet', debuggingThisModule, 'Attributes={!r} referenceField={!r}'.format( attributes, referenceField ) )
        marker = 'ior' if V=='0' else 'x'
        replacement = '\\{} {}\\{}*'.format( marker, referenceField, marker )
        #vPrint( 'Quiet', debuggingThisModule, 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
        #vPrint( 'Quiet', debuggingThisModule, "verseLineC", repr(verseLine) )
    while True:
        match = re.search( '<reference([^/>]*?)/>', verseLine )
        if not match: break
        attributes = match.group(1)
        #vPrint( 'Quiet', debuggingThisModule, 'Attributes={!r}'.format( attributes ) )
        matcha = re.search( 'osisRef="(.+?)"', attributes )
        osisRef = matcha.group(1) if matcha else ''
        #vPrint( 'Quiet', debuggingThisModule, 'osisRef={!r}'.format( osisRef ) )
        replacement = '\\x {}\\x*'.format( osisRef )
        #vPrint( 'Quiet', debuggingThisModule, 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
        #vPrint( 'Quiet', debuggingThisModule, "verseLineC", repr(verseLine) )
    while True:
        match = re.search( '<hi ([^/>]+?)>(.+?)</hi>', verseLine )
        if not match: break
        attributes, words = match.group(1), match.group(2)
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            vPrint( 'Quiet', debuggingThisModule, 'Highlight attributes={!r} Words={!r}'.format( attributes, words ) )
        if '"italic"' in attributes: marker = 'it'
        elif '"small-caps"' in attributes: marker = 'sc'
        elif '"super"' in attributes: marker = 'ord' # We don't have anything exact for this XXXXXXXXXXXXXXXX
        elif '"acrostic"' in attributes: marker = 'tl'
        elif '"bold"' in attributes: marker = 'bd'
        elif '"underline"' in attributes: marker = 'em' # We don't have an underline marker
        elif '"x-superscript"' in attributes: marker = 'ord' # We don't have a superscript marker
        else:
            vPrint( 'Quiet', debuggingThisModule, 'FX353 Matched:', repr(match.group(0)) )
            if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.strictCheckingFlag or debuggingThisModule: halt
            marker = attributes
        replacement = '\\{} {}\\{}*'.format( marker, words, marker )
        #vPrint( 'Quiet', debuggingThisModule, 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
        #vPrint( 'Quiet', debuggingThisModule, "verseLineC", repr(verseLine) )
    while True: # Handle left-over highlights (that have no further information)
        match = re.search( '<hi>(.+?)</hi>', verseLine )
        if not match: break
        words = match.group(1)
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            vPrint( 'Quiet', debuggingThisModule, 'Highlight Words={!r}'.format( words ) )
        #if moduleName in ( 'LITV', 'MKJV', 'TS1998', ):
        marker = 'add'
        replacement = '\\{} {}\\{}*'.format( marker, words, marker )
        #vPrint( 'Quiet', debuggingThisModule, 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
        #vPrint( 'Quiet', debuggingThisModule, "verseLineC", repr(verseLine) )

    # Milestones
    while True:
        match = re.search( '<milestone ([^/>]*?)type="x-usfm-(.+?)"([^/>]*?)/>', verseLine )
        if not match: break
        attributes, marker = match.group(1)+match.group(3), match.group(2)
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            vPrint( 'Quiet', debuggingThisModule, f'Milestone attributes={attributes!r} marker={marker!r}' )
        match2 = re.search( 'n="(.*?)"', attributes ) # Can be empty string in JPS!!!
        if match2:
            if match.group(1):
                replacement = '\\NL**\\{} {}\\NL**'.format( marker, match2.group(1) )
            else:
                logging.warning( f"filterOSISVerseLine at {BBB} {C}:{V} empty n attribute in '{verseLine}'")
                replacement = ''
            #vPrint( 'Quiet', debuggingThisModule, 'replacement', repr(replacement) )
        else:
            logging.critical( f"filterOSISVerseLine at {BBB} {C}:{V} can't decode '{verseLine}'")
            replacement = ''
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
        #vPrint( 'Quiet', debuggingThisModule, "verseLineC", repr(verseLine) )
    while True: # Not sure what this is all about -- just delete it
        match = re.search( '<milestone ([^/>]*?)type="x-strongsMarkup"([^/>]*?)/>', verseLine )
        if not match: break
        attributes = match.group(1)+match.group(2)
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            vPrint( 'Quiet', debuggingThisModule, 'Strongs milestone attributes={!r}'.format( attributes ) )
        verseLine = verseLine[:match.start()] + verseLine[match.end():]
        #vPrint( 'Quiet', debuggingThisModule, "verseLineC", repr(verseLine) )
    while True:
        match = re.search( '<milestone ([^/>]*?)type="x-p"([^/>]*?)/>', verseLine )
        if not match: break
        attributes = match.group(1)+match.group(2)
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            vPrint( 'Quiet', debuggingThisModule, 'x-p milestone attributes={!r}'.format( attributes ) )
        match2 = re.search( 'marker="(.+?)"', attributes )
        if match2:
            replacement = '\\p {}\\NL**'.format( match2.group(1) )
            #vPrint( 'Quiet', debuggingThisModule, 'replacement', repr(replacement) )
        else: replacement = ''; halt
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
        #vPrint( 'Quiet', debuggingThisModule, "verseLineC", repr(verseLine) )
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
            vPrint( 'Quiet', debuggingThisModule, 'Closer attributes1={!r} words={!r}'.format( attributes1, words ) )
        replacement = '\\sig {}\\sig*'.format( words )
        #vPrint( 'Quiet', debuggingThisModule, 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
    while True:
        match = re.search( '<note ([^/>]*?)swordFootnote="([^/>]+?)"([^/>]*?)>(.*?)</note>', verseLine )
        if not match: break
        attributes, number, noteContents = match.group(1)+match.group(3), match.group(2), match.group(4)
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            vPrint( 'Quiet', debuggingThisModule, 'Note attributes={!r} Number={!r}'.format( attributes, number ) )
        if 'crossReference' in attributes:
            assert noteContents == ''
            replacement = '\\x {}\\x*'.format( number )
        else: halt
        #vPrint( 'Quiet', debuggingThisModule, 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
    while True:
        match = re.search( '<note([^/>]*?)>(.*?)</note>', verseLine )
        if not match: break
        attributes, noteContents = match.group(1), match.group(2).rstrip().replace( '\\NL**\\q1\\NL**', '//' ) # was <l />
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            vPrint( 'Quiet', debuggingThisModule, 'Note attributes={!r} contents={!r}'.format( attributes, noteContents ) )
        replacement = '\\f + \\ft {}\\f*'.format( noteContents )
        #vPrint( 'Quiet', debuggingThisModule, 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
        haveFootnoteFlag = True
    while True:
        match = re.search( '<abbr([^/>]*?)>(.*?)</abbr>', verseLine )
        if not match: break
        attributes, abbr = match.group(1), match.group(2)
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            vPrint( 'Quiet', debuggingThisModule, 'Abbr attributes={!r} abbr={!r}'.format( attributes, abbr ) )
        replacement = '{}'.format( abbr )
        #vPrint( 'Quiet', debuggingThisModule, 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
    while True:
        match = re.search( '<a ([^/>]*?)href="([^>]+?)"([^/>]*?)>(.+?)</a>', verseLine )
        if not match: break
        attributes, linkHREF, linkContents = match.group(1)+match.group(3), match.group(2), match.group(4)
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            vPrint( 'Quiet', debuggingThisModule, 'Link attributes={!r} HREF={!r} contents={!r}'.format( attributes, linkHREF, linkContents ) )
        replacement = linkContents
        #vPrint( 'Quiet', debuggingThisModule, 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]

    # Now scan for remaining fixed open and close fields
    replacementList = [
            ('<seg><divineName>','\\nd ','</divineName></seg>','\\nd*'),
            ('<seg><transChange type="added">','\\add ','</transChange></seg>','\\add*'),
            #('<transChange type="added">','\\add ','</transChange>','\\add*'),
            ('<catchWord>','\\add ','</catchWord>','\\add*'), # Not sure what this one is???
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
    if haveFootnoteFlag:
        replacementList.append( ('<rdg type="alternative">','\\fqa ','</rdg>','') ) # Presumably inside a footnote
        replacementList.append( ('<rdg type="x-equivalent">','\\fl Equiv. \\fq ','</rdg>','') ) # Presumably inside a footnote
        replacementList.append( ('<rdg type="x-identity">','\\fl Identity: \\fq ','</rdg>','') ) # Presumably inside a footnote
        replacementList.append( ('<rdg type="x-literal">','\\fl Lit. \\fq ','</rdg>','') ) # Presumably inside a footnote
        replacementList.append( ('<rdg type="x-meaning">','\\fl Meaning: \\fq ','</rdg>','') ) # Presumably inside a footnote
    verseLine = replaceFixedPairs( replacementList, verseLine )

    # Check for anything left that we should have caught above
    if '<' in verseLine or '>' in verseLine:
        vPrint( 'Quiet', debuggingThisModule, "filterOSISVerseLine XX123 left-over {} {} {}:{} verseLine={!r}".format( moduleName, BBB, C, V, verseLine ) )
        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            if BBB!='PSA' or V not in ('1','5',): vPrint( 'Quiet', debuggingThisModule, "Stopped at", moduleName, BBB, C, V ); halt
    #if V == '3': halt

    return verseLine
# end of filterOSISVerseLine


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
        vPrint( 'Quiet', debuggingThisModule, "\nimportOSISVerseLine( {} {} {}:{} … {!r} )".format( moduleName, BBB, C, V, osisVerseString ) )

    verseLine = filterOSISVerseLine( osisVerseString, moduleName, BBB, C, V )

    # Now divide up lines and enter them
    location = '{} {} {}:{} {!r}'.format( moduleName, BBB, C, V, osisVerseString ) if debuggingThisModule else '{} {} {}:{}'.format( moduleName, BBB, C, V )
    if verseLine or V != '0':
        thisBook.addVerseSegments( V, verseLine, location )
# end of importOSISVerseLine



def filterGBFVerseLine( gbfVerseString, moduleName, BBB, C, V ):
    """
    Given a verse entry string made up of GBF (General Bible Format) segments,
        convert it into our internal format.

    moduleName, BBB, C, V are just used for more helpful error/information messages.

    We use \\NL** as an internal code for a newline
        to show where a verse line needs to be broken into internal chunks.

    Return the verse line(s).
    """
    if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
        vPrint( 'Quiet', debuggingThisModule, "\nfilterGBFVerseLine( {} {} {}:{} … {!r} )".format( moduleName, BBB, C, V, gbfVerseString ) )

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
            #vPrint( 'Quiet', debuggingThisModule, 'replacement1 (repeat)', caller, repr(replacement1), contentsDict )
            verseLine = verseLine[:match1.start()] + replacement1 + verseLine[match1.end():]
        elif match2: # normal case -- let's separate out all of the numbered callees
            callee, contents = match2.group(1), match2.group(2).rstrip()
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                vPrint( 'Quiet', debuggingThisModule, 'FN caller={!r} callee={!r} contents={!r} {}'.format( caller, callee, contents, contentsDict ) )
            replacement2 = '{}) {}'.format( callee, contents )
            j = 0
            while replacement2:
                #vPrint( 'Quiet', debuggingThisModule, 'Loop {} start: now {} with replacement2={!r}'.format( j, contentsDict, replacement2 ) )
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
                    #vPrint( 'Quiet', debuggingThisModule, 'Loop {} with match8: now {} with replacement={!r}'.format( j, contentsDict, replacement2 ) )
                else: # We only have one part
                    #vPrint( 'Quiet', debuggingThisModule, repr(callee9), repr(callee) )
                    #assert callee9 == callee
                    contentsDict[callee9] = replacement2[len(callee9)+2:]
                    replacement2 = ''
                    #vPrint( 'Quiet', debuggingThisModule, 'Loop {} with no match8: now {} with replacement={!r}'.format( j, contentsDict, replacement2 ) )
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
                vPrint( 'Quiet', debuggingThisModule, 'FN caller={!r} unnumbered contents={!r}'.format( caller, contents ) )
            nextOne = ' {}) '.format( int(caller)+1 )
            if nextOne in contents: # It contains the next footnote(s) as well
                halt # Not expected
            else:
                replacement3 = ''
            replacement1 = '\\f + \\ft {}\\f*'.format( contentsDict[caller] )
            #vPrint( 'Quiet', debuggingThisModule, 'replacement1', repr(replacement1) )
            #vPrint( 'Quiet', debuggingThisModule, 'replacement3', repr(replacement3) )
            assert match3.start()>match1.start() and match3.end()>match1.end() and match3.start()>match1.end()
            verseLine = verseLine[:match1.start()] + replacement1 + \
                        verseLine[match1.end():match3.start()] + replacement3 + verseLine[match3.end():]
        else:
            vPrint( 'Quiet', debuggingThisModule, 'WHY FN caller={!r} callee={!r} contents={!r} {}'.format( caller, callee, contents, contentsDict ) )
            halt
        #vPrint( 'Quiet', debuggingThisModule, repr(verseLine ) )
        lastCalled = callee, contents
    while True:
        match4 = re.search( '<RF>(.+?)<Rf>', verseLine ) # Footnote that doesn't match the above system
        if not match4: break
        contents = match4.group(1)
        #vPrint( 'Quiet', debuggingThisModule, 'match4', repr(contents), repr(verseLine), contentsDict )
        #assert len(contents) > 2 and not contents[0].isdigit()
        replacement4 = '\\f + \\ft {}\\f*'.format( contents )
        #vPrint( 'Quiet', debuggingThisModule, 'replacement4', repr(replacement4) )
        verseLine = verseLine[:match4.start()] + replacement4 + verseLine[match4.end():]

    while True:
        match = re.search( '<WT(.+?)>', verseLine ) # What's this
        if not match: break
        replacement = '' # TEMP …… xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
        #vPrint( 'Quiet', debuggingThisModule, 'replacement1', repr(replacement1) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
    while True:
        match = re.search( '<WH0(\d{1,4})>', verseLine ) # Found in rwebster
        if not match: break
        replacement = '\\str H{} \\str*'.format( match.group( 1 ) )
        #vPrint( 'Quiet', debuggingThisModule, 'replacement1', repr(replacement1) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
    while True:
        match = re.search( '<WG(\d{1,4})>', verseLine ) # Found in rwebster
        if not match: break
        replacement = '\\str G{} \\str*'.format( match.group( 1 ) )
        #vPrint( 'Quiet', debuggingThisModule, 'replacement1', repr(replacement1) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]

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
        vPrint( 'Quiet', debuggingThisModule, "filterGBFVerseLine XX246 left-over {} {} {}:{} verseLine={!r}".format( moduleName, BBB, C, V, verseLine ) )
        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            vPrint( 'Quiet', debuggingThisModule, "Stopped at", moduleName, BBB, C, V ); halt

    return verseLine
# end of filterGBFVerseLine

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
        vPrint( 'Quiet', debuggingThisModule, "\nimportGBFVerseLine( {} {} {}:{} … {!r} )".format( moduleName, BBB, C, V, gbfVerseString ) )

    verseLine = filterGBFVerseLine( gbfVerseString, moduleName, BBB, C, V )

    # Now divide up lines and enter them
    location = '{} {} {}:{} {!r}'.format( moduleName, BBB, C, V, gbfVerseString ) if debuggingThisModule else '{} {} {}:{}'.format( moduleName, BBB, C, V )
    thisBook.addVerseSegments( V, verseLine, location )
# end of importGBFVerseLine



def filterTHMLVerseLine( thmlVerseString, moduleName, BBB, C, V ):
    """
    Given a verse entry string made up of THML segments,
        convert it into our internal format.

    moduleName, BBB, C, V are just used for more helpful error/information messages.

    We use \\NL** as an internal code for a newline
        to show where a verse line needs to be broken into internal chunks.

    Returns the verse line(s).
    """
    if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
        vPrint( 'Quiet', debuggingThisModule, "\nfilterTHMLVerseLine( {} {} {}:{} … {!r} )".format( moduleName, BBB, C, V, thmlVerseString ) )
    verseLine = thmlVerseString

    # Regular expression substitutions
    while True:
        match = re.search( '<div class="title">(.+?)</div>', verseLine )
        if not match: break
        replacement = '\\mt {}'.format( match.group(1) )
        #vPrint( 'Quiet', debuggingThisModule, 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
    while True:
        match = re.search( '<div class="sechead">(.+?)</div>', verseLine )
        if not match: break
        replacement = '\\s {}'.format( match.group(1) )
        #vPrint( 'Quiet', debuggingThisModule, 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
    while True:
        match = re.search( '<p>(.+?)</p>', verseLine )
        if not match: break
        replacement = '\\p {}'.format( match.group(1) )
        #vPrint( 'Quiet', debuggingThisModule, 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
    while True:
        match = re.search( '<scripRef([^/>]+?)>(.+?)</scripRef>', verseLine )
        if not match: break
        attributes, contents = match.group(1), match.group(2)
        #vPrint( 'Quiet', debuggingThisModule, 'match   attrs={!r}   contents={!r}'.format( attributes, contents ) )
        matcha = re.search( 'passage="(.+?)"', attributes )
        passage = matcha.group(1) if matcha else ''
        matchb = re.search( 'version="(.+?)"', attributes )
        version = matchb.group(1) if matchb else ''
        #vPrint( 'Quiet', debuggingThisModule, 'match1   passage={!r}   version={!r}'.format( passage, version ) )
        replacement = '\\x - \\xo {} \\xt {} {} \\x*'.format( contents, version, passage )
        #vPrint( 'Quiet', debuggingThisModule, 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
    while True:
        match = re.search( '<a ([^/>]*?)href="([^>]+?)"([^/>]*?)>(.+?)</a>', verseLine )
        if not match: break
        attributes, linkHREF, linkContents = match.group(1)+match.group(3), match.group(2), match.group(4)
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            vPrint( 'Quiet', debuggingThisModule, 'Link attributes={!r} HREF={!r} contents={!r}'.format( attributes, linkHREF, linkContents ) )
        replacement = linkContents
        #vPrint( 'Quiet', debuggingThisModule, 'replacement', repr(replacement) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]
    while True:
        match = re.search( '<WT(.+?)>', verseLine ) # What's this
        if not match: break
        replacement = '' # TEMP …… xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
        #vPrint( 'Quiet', debuggingThisModule, 'replacement1', repr(replacement1) )
        verseLine = verseLine[:match.start()] + replacement + verseLine[match.end():]

    # Straight substitutions
    for old, new in ( ( '<br />', '\\NL**' ), ( '<br/>', '\\NL**' ),
                      ):
        verseLine = verseLine.replace( old, new )

    # Now scan for fixed open and close fields
    replacementList = ( ('<font color="#ff0000">','\\wj ', '</font>','\\wj*'),
                        ( '<small>', '\\sc ', '</small>', '\\sc*' ),
                        ( '<sc>', '\\sc ', '</sc>', '\\sc*' ),
                        ( '<note>', '\\f ', '</note>', '\\f*' ),
                        ( '<scripRef>', '\\x ', '</scripRef>', '\\x*' ),
                        ( '<b>', '\\bd ', '</b>', '\\bd*' ),
                        ( '<i>', '\\it ', '</i>', '\\it*' ),
                        ( '<sup>', '\\ord ', '</sup>', '\\ord*' ), # Ord is the best we have for superscript
                        )
    verseLine = replaceFixedPairs( replacementList, verseLine )

    # Check for anything left that we should have caught above
    if '<' in verseLine or '>' in verseLine:
        vPrint( 'Quiet', debuggingThisModule, "filterTHMLVerseLine XX369 left-over {} {} {}:{} verseLine={!r}".format( moduleName, BBB, C, V, verseLine ) )
        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            vPrint( 'Quiet', debuggingThisModule, "Stopped at", moduleName, BBB, C, V ); halt

    return verseLine
# end of filterTHMLVerseLine

def importTHMLVerseLine( thmlVerseString, thisBookObject, moduleName, BBB, C, V ):
    """
    Given a verse entry string made up of THML segments,
        convert it into our internal format
        and add the line(s) to thisBookObject.

    moduleName, BBB, C, V are just used for more helpful error/information messages.

    We use \\NL** as an internal code for a newline
        to show where a verse line needs to be broken into internal chunks.

    Adds the line(s) to thisBookObject. No return value.
    """
    if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
        vPrint( 'Quiet', debuggingThisModule, "\nimportTHMLVerseLine( {} {} {}:{} … {!r} )".format( moduleName, BBB, C, V, thmlVerseString ) )

    verseLine = filterTHMLVerseLine( thmlVerseString, moduleName, BBB, C, V )

    # Now divide up lines and enter them
    location = '{} {} {}:{} {!r}'.format( moduleName, BBB, C, V, thmlVerseString ) if debuggingThisModule else '{} {} {}:{}'.format( moduleName, BBB, C, V )
    thisBookObject.addVerseSegments( V, verseLine, location )
# end of importTHMLVerseLine



class SwordKey( SimpleVerseKey ):
    """
    Just a SimpleVerseKey class (with BBB, C, V, optional S)
        with a couple of calls compatible with the SwordKey class.
    """
    def getChapter( self ):
        return self.getChapterNumberInt()

    def getVerse( self ):
        return self.getVerseNumberInt()
# end of class SwordKey



class SwordInterface():
    """
    This is the interface class that we use between our higher level code
        and the code reading the actual installed Sword modules.
    """
    def __init__( self ):
        """
        """
        vPrint( 'Normal', debuggingThisModule, f"SwordResources.SwordInterface is using '{SwordType}'." )
        if SwordType == 'CrosswireLibrary':
            self.library = Sword.SWMgr()
            #self.keyCache = {}
            #self.verseCache = OrderedDict()
        elif SwordType == 'OurCode':
            self.library = SwordModules.SwordModules() # Loads all of conf files that it can find
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                vPrint( 'Quiet', debuggingThisModule, 'Sword library', self.library )
        else: halt # programming error
    # end of SwordInterface.__init__


    def augmentModules( self, newPath:str ) -> None:
        """
        Adds another path to search for modules in.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            vPrint( 'Quiet', debuggingThisModule, f"SwordInterface.augmentModules( {newPath} )" )
            assert self.library is not None

        someFlag = 0 # Don't know what this means in undocumented Sword library
        if SwordType == 'CrosswireLibrary':
            self.library.augmentModules( newPath, someFlag )
        elif SwordType == 'OurCode':
            self.library.augmentModules( newPath, someFlag )
    # end of SwordInterface.augmentModules


    def getAvailableModuleCodes( self, onlyModuleTypes:Optional[List[str]]=None ):
        """
        Module type is a list of strings for the type(s) of modules to include.

        Returns a list of available Sword module codes.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            vPrint( 'Quiet', debuggingThisModule, _("SwordInterface.getAvailableModuleCodes( {} )").format( onlyModuleTypes ) )

        if SwordType == 'CrosswireLibrary':
            availableModuleCodes = []
            for j,moduleBuffer in enumerate(self.library.getModules()):
                moduleID = moduleBuffer.getRawData()
                #module = self.library.getModule( moduleID )
                #if 0:
                    #vPrint( 'Quiet', debuggingThisModule, "{} {} ({}) {} {!r}".format( j, module.getName(), module.getType(), module.getLanguage(), module.getEncoding() ) )
                    #try: vPrint( 'Quiet', debuggingThisModule, "    {} {!r} {} {}".format( module.getDescription(), module.getMarkup(), module.getDirection(), "" ) )
                    #except UnicodeDecodeError: vPrint( 'Quiet', debuggingThisModule, "   Description is not Unicode!" )
                #vPrint( 'Quiet', debuggingThisModule, "moduleID", repr(moduleID) )
                availableModuleCodes.append( moduleID )
            return availableModuleCodes
        elif SwordType == 'OurCode':
            return self.library.getAvailableModuleCodes( onlyModuleTypes )
    # end of SwordInterface.getAvailableModuleCodes


    def getAvailableModuleCodeDuples( self, onlyModuleTypes=None ):
        """
        Module type is a list of strings for the type(s) of modules to include.

        Returns a list of 2-tuples (duples) containing module abbreviation and type
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            vPrint( 'Quiet', debuggingThisModule, _("SwordInterface.getAvailableModuleCodeDuples( {} )").format( onlyModuleTypes ) )

        if SwordType == 'CrosswireLibrary':
            availableModuleCodes = []
            for j,moduleBuffer in enumerate(self.library.getModules()):
                moduleID = moduleBuffer.getRawData()
                module = self.library.getModule( moduleID )
                moduleType = module.getType()
                #if 1:
                    #vPrint( 'Quiet', debuggingThisModule, "{} {} ({}) {} {!r}".format( j, module.getName(), module.getType(), module.getLanguage(), module.getEncoding() ) )
                    #try: vPrint( 'Quiet', debuggingThisModule, "    {} {!r} {} {}".format( module.getDescription(), module.getMarkup(), module.getDirection(), "" ) )
                    #except UnicodeDecodeError: vPrint( 'Quiet', debuggingThisModule, "   Description is not Unicode!" )
                #vPrint( 'Quiet', debuggingThisModule, "moduleID", repr(moduleID), repr(moduleType) )
                assert moduleType in ( 'Biblical Texts', 'Commentaries', 'Lexicons / Dictionaries', 'Generic Books' )
                if onlyModuleTypes is None or moduleType in onlyModuleTypes:
                    availableModuleCodes.append( (moduleID,moduleType) )
            return availableModuleCodes
        elif SwordType == 'OurCode':
            result1 = self.library.getAvailableModuleCodeDuples( onlyModuleTypes )
            #vPrint( 'Quiet', debuggingThisModule, 'getAvailableModuleCodeDuples.result1', result1 )
            if result1:
                result2 = [(name,SwordModules.GENERIC_SWORD_MODULE_TYPE_NAMES[modType]) for name,modType in result1]
                #vPrint( 'Quiet', debuggingThisModule, 'getAvailableModuleCodeDuples.result2', result2 )
                return result2
    # end of SwordInterface.getAvailableModuleCodeDuples


    def getModule( self, moduleAbbreviation='KJV' ):
        """
        Get the requested module.

        (Doesn't load books)
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            vPrint( 'Quiet', debuggingThisModule, "SwordInterface.getModule( {} )".format( moduleAbbreviation ) )

        if SwordType == 'CrosswireLibrary':
            #vPrint( 'Quiet', debuggingThisModule, "gM", module.getName() )
            for tryAbbreviation in ( moduleAbbreviation, moduleAbbreviation.title(),
                                    moduleAbbreviation.upper(), moduleAbbreviation.lower() ):
                result = self.library.getModule( tryAbbreviation )
                #vPrint( 'Quiet', debuggingThisModule, 'getModule.result', tryAbbreviation, result )
                if result is not None: return result
        elif SwordType == 'OurCode':
            #lmResult = self.library.loadModule( moduleAbbreviation ) # e.g., KJV
            #except KeyError: lmResult = self.library.loadBooks( moduleAbbreviation.lower() ) # needs kjv??? why? what changed?
            #vPrint( 'Quiet', debuggingThisModule, moduleAbbreviation, lmResult ); halt
            #resultFlag, theModule = lmResult
            #if debuggingThisModule and not resultFlag: vPrint( 'Quiet', debuggingThisModule, "failed here!" ); halt
            #return theModule
            result1 = self.library.getModule( moduleAbbreviation )
            return result1
    # end of SwordInterface.getModule


    def loadBook( self, BBB, BibleObject, moduleAbbreviation='KJV' ):
        """
        Load the given book from a Sword Module into the given BibleObject.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            vPrint( 'Quiet', debuggingThisModule, "SwordInterface.loadBook( {}, …, {} )".format( BBB, moduleAbbreviation ) )
            assert BBB not in BibleObject

        module = self.getModule( moduleAbbreviation )
        if module is None:
            logger.critical( _("Unable to load {!r} module -- not known by Sword").format( moduleAbbreviation ) )
            return

        self.triedLoadingBook[BBB] = True
        self.bookNeedsReloading[BBB] = False

        # Create the new book
        if BibleOrgSysGlobals.verbosityLevel > 2:  vPrint( 'Quiet', debuggingThisModule, '  Loading {} {}…'.format( moduleAbbreviation, BBB ) )
        thisBook = BibleBook( BibleObject, BBB )
        thisBook.objectNameString = 'Sword Bible Book object'
        thisBook.objectTypeString = 'Sword Bible'
        currentC, haveText = '0', False

        if SwordType=='CrosswireLibrary': # need to load the module
            markupCode = ord( module.getMarkup() )
            encoding = ord( module.getEncoding() )
            if encoding == Sword.ENC_LATIN1: BibleObject.encoding = 'latin-1'
            elif encoding == Sword.ENC_UTF8: BibleObject.encoding = 'utf-8'
            elif encoding == Sword.ENC_UTF16: BibleObject.encoding = 'utf-16'
            elif BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt

            if BibleOrgSysGlobals.verbosityLevel > 2:
                vPrint( 'Quiet', debuggingThisModule, 'Description: {!r}'.format( module.getDescription() ) )
                vPrint( 'Quiet', debuggingThisModule, 'Direction: {!r}={}'.format( ord(module.getDirection()), SWORD_TEXT_DIRECTIONS[ord(module.getDirection())] ) )
                vPrint( 'Quiet', debuggingThisModule, 'Encoding: {!r}={}'.format( encoding, SWORD_ENCODINGS[encoding] ) )
                vPrint( 'Quiet', debuggingThisModule, 'Language: {!r}'.format( module.getLanguage() ) )
                vPrint( 'Quiet', debuggingThisModule, 'Markup: {!r}={}'.format( markupCode, SWORD_MARKUPS[markupCode] ) )
                vPrint( 'Quiet', debuggingThisModule, 'Name: {!r}'.format( module.getName() ) )
                vPrint( 'Quiet', debuggingThisModule, 'RenderHeader: {!r}'.format( module.getRenderHeader() ) )
                vPrint( 'Quiet', debuggingThisModule, 'Type: {!r}'.format( module.getType() ) )
                vPrint( 'Quiet', debuggingThisModule, 'IsSkipConsecutiveLinks: {!r}'.format( module.isSkipConsecutiveLinks() ) )
                vPrint( 'Quiet', debuggingThisModule, 'IsUnicode: {!r}'.format( module.isUnicode() ) )
                vPrint( 'Quiet', debuggingThisModule, 'IsWritable: {!r}'.format( module.isWritable() ) )
                #return

# UNFINISHED
            for index in range( 999999 ):
                module.setIndex( index )
                if module.getIndex() != index: break # Gone too far

                # Find where we're at
                verseKey = module.getKey()
                verseKeyText = verseKey.getShortText()
                #if '2' in verseKeyText: halt # for debugging first verses
                #if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                    #vPrint( 'Quiet', debuggingThisModule, '\nvkst={!r} vkix={}'.format( verseKeyText, verseKey.getIndex() ) )

                #nativeVerseText = module.renderText().decode( self.encoding, 'replace' )
                #nativeVerseText = str( module.renderText() ) if self.encoding=='utf-8' else str( module.renderText(), encoding=self.encoding )
                #vPrint( 'Quiet', debuggingThisModule, 'getRenderHeader: {} {!r}'.format( len(module.getRenderHeader()), module.getRenderHeader() ) )
                #vPrint( 'Quiet', debuggingThisModule, 'stripText: {} {!r}'.format( len(module.stripText()), module.stripText() ) )
                #vPrint( 'Quiet', debuggingThisModule, 'renderText: {} {!r}'.format( len(str(module.renderText())), str(module.renderText()) ) )
                #vPrint( 'Quiet', debuggingThisModule, 'getRawEntry: {} {!r}'.format( len(module.getRawEntry()), module.getRawEntry() ) )
                try: nativeVerseText = module.getRawEntry()
                #try: nativeVerseText = str( module.renderText() )
                except UnicodeDecodeError: nativeVerseText = ''

                if ':' not in verseKeyText:
                    if BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.verbosityLevel > 2:
                        vPrint( 'Quiet', debuggingThisModule, "Unusual Sword verse key: {} (gave {!r})".format( verseKeyText, nativeVerseText ) )
                    if BibleOrgSysGlobals.debugFlag:
                        assert verseKeyText in ( '[ Module Heading ]', '[ Testament 1 Heading ]', '[ Testament 2 Heading ]', )
                    if BibleOrgSysGlobals.verbosityLevel > 3:
                        if markupCode == Sword.FMT_OSIS:
                            match = re.search( '<milestone ([^/>]*?)type="x-importer"([^/>]*?)/>', nativeVerseText )
                            if match:
                                attributes = match.group(1) + match.group(2)
                                match2 = re.search( 'subType="(.+?)"', attributes )
                                subType = match2.group(1) if match2 else None
                                if subType and subType.startswith( 'x-' ): subType = subType[2:] # Remove the x- prefix
                                match2 = re.search( 'n="(.+?)"', attributes )
                                n = match2.group(1) if match2 else None
                                if n: n = n.replace( '$', '' ).strip()
                                vPrint( 'Quiet', debuggingThisModule, "Module created by {} {}".format( subType, n ) )
                    continue
                vkBits = verseKeyText.split()
                assert len(vkBits) == 2
                osisBBB = vkBits[0]
                BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromOSISAbbreviation( osisBBB )
                if isinstance( BBB, list ): BBB = BBB[0] # We sometimes get a list of options -- take the first = most likely one
                vkBits = vkBits[1].split( ':' )
                assert len(vkBits) == 2
                C, V = vkBits
                #vPrint( 'Quiet', debuggingThisModule, 'At {} {}:{}'.format( BBB, C, V ) )

                if C != currentC:
                    thisBook.addLine( 'c', C )
                    #if C == '2': halt
                    currentC = C

                if nativeVerseText:
                    haveText = True
                    if markupCode == Sword.FMT_OSIS: importOSISVerseLine( nativeVerseText, thisBook, moduleAbbreviation, BBB, C, V )
                    elif markupCode == Sword.FMT_GBF: importGBFVerseLine( nativeVerseText, thisBook, moduleAbbreviation, BBB, C, V )
                    elif markupCode == Sword.FMT_THML: importTHMLVerseLine( nativeVerseText, thisBook, moduleAbbreviation, BBB, C, V )
                    else:
                        vPrint( 'Quiet', debuggingThisModule, 'markupCode', repr(markupCode) )
                        if BibleOrgSysGlobals.debugFlag: halt
                        return

            if haveText: # Save the book
                vPrint( 'Verbose', debuggingThisModule, "Saving", moduleAbbreviation, currentBBB, bookCount )
                BibleObject.stashBook( thisBook )


        elif SwordType=='OurCode':
            # module is already loaded above in getModule call WRONG………..
            #vPrint( 'Quiet', debuggingThisModule, "moduleConfig =", module.SwordModuleConfiguration )
            BibleObject.books = module.books
    # end of SwordInterface.loadBook


    def loadBooks( self, BibleObject, moduleAbbreviation='KJV' ):
        """
        Load all the books from a Sword Module into the given BibleObject.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            vPrint( 'Quiet', debuggingThisModule, "SwordInterface.loadBooks( …, {} )".format( moduleAbbreviation ) )

        module = self.getModule( moduleAbbreviation )
        if module is None:
            logger.critical( _("Unable to load {!r} module -- not known by Sword").format( moduleAbbreviation ) )
            return

        if SwordType=='CrosswireLibrary': # need to load the module
            markupCode = ord( module.getMarkup() )
            encoding = ord( module.getEncoding() )
            if encoding == Sword.ENC_LATIN1: BibleObject.encoding = 'latin-1'
            elif encoding == Sword.ENC_UTF8: BibleObject.encoding = 'utf-8'
            elif encoding == Sword.ENC_UTF16: BibleObject.encoding = 'utf-16'
            elif BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt

            if BibleOrgSysGlobals.verbosityLevel > 2:
                vPrint( 'Quiet', debuggingThisModule, 'Description: {!r}'.format( module.getDescription() ) )
                vPrint( 'Quiet', debuggingThisModule, 'Direction: {!r}={}'.format( ord(module.getDirection()), SWORD_TEXT_DIRECTIONS[ord(module.getDirection())] ) )
                vPrint( 'Quiet', debuggingThisModule, 'Encoding: {!r}={}'.format( encoding, SWORD_ENCODINGS[encoding] ) )
                vPrint( 'Quiet', debuggingThisModule, 'Language: {!r}'.format( module.getLanguage() ) )
                vPrint( 'Quiet', debuggingThisModule, 'Markup: {!r}={}'.format( markupCode, SWORD_MARKUPS[markupCode] ) )
                vPrint( 'Quiet', debuggingThisModule, 'Name: {!r}'.format( module.getName() ) )
                vPrint( 'Quiet', debuggingThisModule, 'RenderHeader: {!r}'.format( module.getRenderHeader() ) )
                vPrint( 'Quiet', debuggingThisModule, 'Type: {!r}'.format( module.getType() ) )
                vPrint( 'Quiet', debuggingThisModule, 'IsSkipConsecutiveLinks: {!r}'.format( module.isSkipConsecutiveLinks() ) )
                vPrint( 'Quiet', debuggingThisModule, 'IsUnicode: {!r}'.format( module.isUnicode() ) )
                vPrint( 'Quiet', debuggingThisModule, 'IsWritable: {!r}'.format( module.isWritable() ) )
                #return

            bookCount = 0
            currentBBB = None
            for index in range( 999999 ):
                module.setIndex( index )
                if module.getIndex() != index: break # Gone too far

                # Find where we're at
                verseKey = module.getKey()
                verseKeyText = verseKey.getShortText()
                #if '2' in verseKeyText: halt # for debugging first verses
                #if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                    #vPrint( 'Quiet', debuggingThisModule, '\nvkst={!r} vkix={}'.format( verseKeyText, verseKey.getIndex() ) )

                #nativeVerseText = module.renderText().decode( self.encoding, 'replace' )
                #nativeVerseText = str( module.renderText() ) if self.encoding=='utf-8' else str( module.renderText(), encoding=self.encoding )
                #vPrint( 'Quiet', debuggingThisModule, 'getRenderHeader: {} {!r}'.format( len(module.getRenderHeader()), module.getRenderHeader() ) )
                #vPrint( 'Quiet', debuggingThisModule, 'stripText: {} {!r}'.format( len(module.stripText()), module.stripText() ) )
                #vPrint( 'Quiet', debuggingThisModule, 'renderText: {} {!r}'.format( len(str(module.renderText())), str(module.renderText()) ) )
                #vPrint( 'Quiet', debuggingThisModule, 'getRawEntry: {} {!r}'.format( len(module.getRawEntry()), module.getRawEntry() ) )
                try: nativeVerseText = module.getRawEntry().encode( BibleObject.encoding, 'namereplace' ).decode( 'utf-8', 'namereplace' )
                #try: nativeVerseText = str( module.renderText() )
                except UnicodeDecodeError: nativeVerseText = ''
                assert isinstance( nativeVerseText, str )

                if ':' not in verseKeyText:
                    if BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.verbosityLevel > 2:
                        vPrint( 'Quiet', debuggingThisModule, "Unusual Sword verse key: {} (gave {!r})".format( verseKeyText, nativeVerseText ) )
                    if BibleOrgSysGlobals.debugFlag:
                        assert verseKeyText in ( '[ Module Heading ]', '[ Testament 1 Heading ]', '[ Testament 2 Heading ]', )
                    if BibleOrgSysGlobals.verbosityLevel > 3:
                        if markupCode == Sword.FMT_OSIS:
                            match = re.search( '<milestone ([^/>]*?)type="x-importer"([^/>]*?)/>', nativeVerseText )
                            if match:
                                attributes = match.group(1) + match.group(2)
                                match2 = re.search( 'subType="(.+?)"', attributes )
                                subType = match2.group(1) if match2 else None
                                if subType and subType.startswith( 'x-' ): subType = subType[2:] # Remove the x- prefix
                                match2 = re.search( 'n="(.+?)"', attributes )
                                n = match2.group(1) if match2 else None
                                if n: n = n.replace( '$', '' ).strip()
                                vPrint( 'Quiet', debuggingThisModule, "Module created by {} {}".format( subType, n ) )
                    continue
                vkBits = verseKeyText.split()
                assert len(vkBits) == 2
                osisBBB = vkBits[0]
                BBB = BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromOSISAbbreviation( osisBBB )
                if isinstance( BBB, list ): BBB = BBB[0] # We sometimes get a list of options -- take the first = most likely one
                vkBits = vkBits[1].split( ':' )
                assert len(vkBits) == 2
                C, V = vkBits
                #vPrint( 'Quiet', debuggingThisModule, 'At {} {}:{}'.format( BBB, C, V ) )

                # Start a new book if necessary
                if BBB != currentBBB:
                    if currentBBB is not None and haveText: # Save the previous book
                        vPrint( 'Verbose', debuggingThisModule, "Saving", currentBBB, bookCount )
                        BibleObject.stashBook( thisBook )
                    # Create the new book
                    if BibleOrgSysGlobals.verbosityLevel > 2:  vPrint( 'Quiet', debuggingThisModule, '  Loading {} {}…'.format( moduleAbbreviation, BBB ) )
                    thisBook = BibleBook( BibleObject, BBB )
                    thisBook.objectNameString = 'Sword Bible Book object'
                    thisBook.objectTypeString = 'Sword Bible'
                    currentBBB, currentC, haveText = BBB, '0', False
                    bookCount += 1

                if C != currentC:
                    thisBook.addLine( 'c', C )
                    #if C == '2': halt
                    currentC = C

                if nativeVerseText:
                    haveText = True
                    if markupCode == Sword.FMT_OSIS: importOSISVerseLine( nativeVerseText, thisBook, moduleAbbreviation, BBB, C, V )
                    elif markupCode == Sword.FMT_GBF: importGBFVerseLine( nativeVerseText, thisBook, moduleAbbreviation, BBB, C, V )
                    elif markupCode == Sword.FMT_THML: importTHMLVerseLine( nativeVerseText, thisBook, moduleAbbreviation, BBB, C, V )
                    else:
                        vPrint( 'Quiet', debuggingThisModule, 'markupCode', repr(markupCode) )
                        if BibleOrgSysGlobals.debugFlag: halt
                        return

            if currentBBB is not None and haveText: # Save the very last book
                vPrint( 'Verbose', debuggingThisModule, "Saving", moduleAbbreviation, currentBBB, bookCount )
                BibleObject.stashBook( thisBook )


        elif SwordType=='OurCode':
            #vPrint( 'Quiet', debuggingThisModule, "moduleConfig =", module.SwordModuleConfiguration )
            result, module = self.library.loadModule( moduleAbbreviation )
            #vPrint( 'Quiet', debuggingThisModule, result, module ); halt
            if result: BibleObject.books = module.books
    # end of SwordInterface.loadBooks


    def makeKey( self, BBB, C, V ):
        #if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            #vPrint( 'Quiet', debuggingThisModule, "SwordInterface.makeKey( {} {}:{} )".format( BBB, C, V ) )

        #if BCV  in self.keyCache:
            #vPrint( 'Quiet', debuggingThisModule, "Cached", BCV )
            #return self.keyCache[BCV]
        if SwordType == 'CrosswireLibrary':
            B = BibleOrgSysGlobals.loadedBibleBooksCodes.getOSISAbbreviation( BBB )
            refString = "{} {}:{}".format( B, C, V )
            #vPrint( 'Quiet', debuggingThisModule, 'refString', refString )
            verseKey = Sword.VerseKey( refString )
            #self.keyCache[BCV] = verseKey
            return verseKey
        elif SwordType == 'OurCode':
            return SwordKey( BBB, C, V )
    # end of SwordInterface.makeKey


    def getContextVerseData( self, module, key ):
        """
        Returns a InternalBibleEntryList of 5-tuples, e.g.,
            [
            ('c', 'c', '1', '1', []),
            ('c#', 'c', '1', '1', []),
            ('v', 'v', '1', '1', []),
            ('v~', 'v~', 'In the beginning God created the heavens and the earth.',
                                    'In the beginning God created the heavens and the earth.', [])
            ]
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            vPrint( 'Quiet', debuggingThisModule, _("SwordInterface.getContextVerseData( {}, {} )").format( module.getName(), key.getShortText() ) )

        if SwordType == 'CrosswireLibrary':
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                mm = module.getMarkup()
                vPrint( 'Quiet', debuggingThisModule, "  module markup", repr(mm), SWORD_MARKUPS[ord(mm)] )
            try: verseText = module.stripText( key )
            except UnicodeDecodeError:
                vPrint( 'Quiet', debuggingThisModule, "Can't decode utf-8 text of {} {}".format( module.getName(), key.getShortText() ) )
                return
            if '\n' in verseText or '\r' in verseText: # Why!!!
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                    vPrint( 'Quiet', debuggingThisModule, _("getContextVerseData: Why does it have CR or LF in {} {} {}") \
                            .format( module.getName(), key.getShortText(), repr(verseText) ) )
                verseText = verseText.replace( '\n', '' ).replace( '\r', '' )
            verseText = verseText.rstrip()
            #vPrint( 'Quiet', debuggingThisModule, 'verseText', repr(verseText) )
            verseData = InternalBibleEntryList()
            #c, v = key.getChapterNumberStr(), key.getVerseNumberStr()
            cv = key.getShortText().split( ' ', 1 )[1]
            c, v = cv.split( ':', 1 )
            #vPrint( 'Quiet', debuggingThisModule, 'c,v', repr(c), repr(v) )
            # Prepend the verse number since Sword modules don't contain that info in the data
            if v=='1': verseData.append( InternalBibleEntry( 'c#','c', c, c, None, c ) )
            verseData.append( InternalBibleEntry( 'v','v', v, v, None, v ) )
            verseData.append( InternalBibleEntry( 'v~','v~', verseText, verseText, None, verseText ) )
            contextVerseData = verseData, [] # No context
        elif SwordType == 'OurCode':
            #vPrint( 'Quiet', debuggingThisModule, _("module"), module )
            try: contextVerseData = module.getContextVerseData( key ) # a call to InternalBible.py
            except KeyError: # Just create a blank verse entry
                verseData = InternalBibleEntryList()
                c, v = key.getChapterNumberStr(), key.getVerseNumberStr()
                if v=='1': verseData.append( InternalBibleEntry( 'c#','c', c, c, None, c ) )
                verseData.append( InternalBibleEntry( 'v','v', v, v, None, v ) )
                contextVerseData = verseData, [] # No context
            #vPrint( 'Quiet', debuggingThisModule, _("gVD={} key={}, st={}").format( module.getName(), key, contextVerseData ) )
            if contextVerseData is None:
                if key.getChapter()!=0 or key.getVerse()!=0: # We're not surprised if there's no chapter or verse zero
                    vPrint( 'Quiet', debuggingThisModule, _("SwordInterface.getContextVerseData no VerseData"), module.getName(), key, contextVerseData )
                contextVerseData = [], None
            else:
                verseData, context = contextVerseData
                #vPrint( 'Quiet', debuggingThisModule, "vD", verseData )
                #assert isinstance( verseData, InternalBibleEntryList ) or isinstance( verseData, list )
                assert isinstance( verseData, InternalBibleEntryList )
                #assert isinstance( verseData, list )
                assert 1 <= len(verseData) <= 6
        #vPrint( 'Quiet', debuggingThisModule, verseData ); halt
        return contextVerseData
    # end of SwordInterface.getContextVerseData


    def getVerseDataList( self, module, key ):
        """
        Overrides the one in InternalBible?
            No, it has different parameters (two instead of one).

        Returns a list of 5-tuples, e.g.,
            [
            ('c', 'c', '1', '1', []),
            ('c#', 'c', '1', '1', []),
            ('v', 'v', '1', '1', []),
            ('v~', 'v~', 'In the beginning God created the heavens and the earth.',
                                    'In the beginning God created the heavens and the earth.', [])
            ]
        """
        vPrint( 'Quiet', debuggingThisModule, "SwordResources: getVerseDataList( {}, {} )".format( module, key ) )

        if SwordType == 'CrosswireLibrary':
            try: verseText = module.stripText( key )
            except UnicodeDecodeError:
                logger.critical( "getVerseDataList: can't decode utf-8 text of {} {}".format( module.getName(), key.getShortText() ) )
                return
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                if '\n' in verseText or '\r' in verseText:
                    vPrint( 'Quiet', debuggingThisModule, _("getVerseDataList: Why does it have CR or LF in {} {}").format( module.getName(), repr(verseText) ) )
            verseData = []
            c, v = str(key.getChapter()), str(key.getVerse())
            # Prepend the verse number since Sword modules don't contain that info in the data
            if v=='1': verseData.append( ('c#','c', c, c, [],) )
            verseData.append( ('v','v', v, v, [],) )
            verseData.append( ('v~','v~', verseText, verseText, [],) )
        elif SwordType == 'OurCode':
            #vPrint( 'Quiet', debuggingThisModule, _("module"), module )
            stuff = module.getContextVerseData( key )
            #vPrint( 'Quiet', debuggingThisModule, _("gVD={} key={}, st={}").format( module.getName(), key, stuff ) )
            if stuff is None:
                vPrint( 'Quiet', debuggingThisModule, _("SwordInterface.getVerseDataList no VerseData"), module.getName(), key, stuff )
                assert key.getChapter()==0 or key.getVerse()==0
            else:
                verseData, context = stuff
                #vPrint( 'Quiet', debuggingThisModule, "vD", verseData )
                #assert isinstance( verseData, InternalBibleEntryList ) or isinstance( verseData, list )
                assert isinstance( verseData, InternalBibleEntryList )
                #assert isinstance( verseData, list )
                assert 1 <= len(verseData) <= 6
        #vPrint( 'Quiet', debuggingThisModule, verseData ); halt
        return verseData
    # end of SwordInterface.getVerseDataList


    def getVerseText( self, module, key ):
        """
        Gets all the lines representing a verse and converts to a single string.

        Returns a string that represents the verse
            with chapter and verse number metadata removed
            and with some temporary/proprietary/minimal encoding:
                ¶: start of paragraph
                §: back to margin
        """
        #cacheKey = (module.getName(), key.getShortText())
        #if cacheKey in self.verseCache:
            #vPrint( 'Quiet', debuggingThisModule, "Cached", cacheKey )
            #return self.verseCache[cacheKey]
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            vPrint( 'Quiet', debuggingThisModule, "SwordInterface.getVerseText({},{})".format( module.getName(), key.getText() ) )

        if SwordType == 'CrosswireLibrary':
            try: verseText = module.stripText( key ) #.encode( 'utf-8', 'namereplace' )
            except UnicodeDecodeError:
                logger.critical( "getVerseText: can't decode utf-8 text of {} {}".format( module.getName(), key.getShortText() ) )
                return ''
        elif SwordType == 'OurCode':
            context, verseData = module.getContextVerseData( key )
            #vPrint( 'Quiet', debuggingThisModule, 'gVT for', module.getName(), 'with KEY =', key, 'got VD =', verseData )
            assert isinstance( verseData, list )
            assert 2 <= len(verseData) <= 5
            verseText = ''
            for entry in verseData:
                vPrint( 'Quiet', debuggingThisModule, "  Entry = {!r}".format( entry ) )
                assert isinstance( entry, InternalBibleEntry ) # Seems to be FAILING !!!!!!!!!!!!!!!!!!!!!!!!!!
                marker, cleanText = entry.getMarker(), entry.getCleanText()
                if marker == 'c': pass # Ignore
                elif marker == 'p': verseText += '¶' + cleanText
                elif marker == 'm': verseText += '§' + cleanText
                elif marker == 'v': pass # Ignore
                elif marker == 'v~': verseText += cleanText
                else: vPrint( 'Quiet', debuggingThisModule, "Unknown marker", marker, cleanText ); halt
        #self.verseCache[cacheKey] = verseText
        #vPrint( 'Quiet', debuggingThisModule, module.getName(), key.getShortText(), "'"+verseText+"'" )
        return verseText
    # end of SwordInterface.getVerseText
# end of class SwordInterface


def getBCV( BCV, moduleAbbreviation='KJV' ): # Very slow -- for testing only
    """
    """
    if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
        vPrint( 'Quiet', debuggingThisModule, "SwordResources.getBCV( {}, {} )".format( BCV, moduleAbbreviation ) )

    library = Sword.SWMgr()
    module = library.getModule( moduleAbbreviation )
    refString = "{} {}:{}".format( BCV[0][:3], BCV[1], BCV[2] )
    #vPrint( 'Quiet', debuggingThisModule, 'refString', refString )
    return module.stripText( Sword.VerseKey( refString ) )
# end of getBCV



def briefDemo() -> None:
    """
    Sword Resources
    """
    BibleOrgSysGlobals.introduceProgram( __name__, programNameVersion, LAST_MODIFIED_DATE )
    vPrint( 'Normal', debuggingThisModule, " using", SwordType )

    if SwordType == 'CrosswireLibrary':
        vPrint( 'Quiet', debuggingThisModule, "Sword Version string", Sword.SWORD_VERSION_STR )
        library = Sword.SWMgr()

    def Find( attribute ):
        """
        Search for methods and attributes
        """
        if debuggingThisModule or  BibleOrgSysGlobals.verbosityLevel > 0:
            vPrint( 'Quiet', debuggingThisModule, "\nSearching for attribute {!r}…".format( attribute ) )
        found = False
        AA = attribute.upper()
        for thing in dir(Sword):
            BB = thing.upper()
            if BB.startswith(AA): vPrint( 'Quiet', debuggingThisModule, "  Have {} in Sword".format( thing ) ); found = True
        for thing in dir(Sword.SWVersion()):
            BB = thing.upper()
            if BB.startswith(AA): vPrint( 'Quiet', debuggingThisModule, "  Have {} in SWVersion".format( thing ) ); found = True
        for thing in dir(Sword.SWMgr()):
            BB = thing.upper()
            if BB.startswith(AA): vPrint( 'Quiet', debuggingThisModule, "  Have {} in SWMgr".format( thing ) ); found = True
        module = library.getModule( 'KJV' )
        for thing in dir(module):
            BB = thing.upper()
            if BB.startswith(AA): vPrint( 'Quiet', debuggingThisModule, "  Have {} in SWModule".format( thing ) ); found = True
        for thing in dir(Sword.SWKey()):
            BB = thing.upper()
            if BB.startswith(AA): vPrint( 'Quiet', debuggingThisModule, "  Have {} in SWKey".format( thing ) ); found = True
        for thing in dir(Sword.VerseKey()):
            BB = thing.upper()
            if BB.startswith(AA): vPrint( 'Quiet', debuggingThisModule, "  Have {} in VerseKey".format( thing ) ); found = True
        #for thing in dir(Sword.InstallMgr()):
            #BB = thing.upper()
            #if BB.startswith(AA): vPrint( 'Quiet', debuggingThisModule, "  Have {} in InstallMgr".format( thing ) ); found = True
        for thing in dir(Sword.LocaleMgr()):
            BB = thing.upper()
            if BB.startswith(AA): vPrint( 'Quiet', debuggingThisModule, "  Have {} in LocaleMgr".format( thing ) ); found = True
        for thing in dir(Sword.SWFilterMgr()):
            BB = thing.upper()
            if BB.startswith(AA): vPrint( 'Quiet', debuggingThisModule, "  Have {} in SWFilterMgr".format( thing ) ); found = True
        if not found: vPrint( 'Quiet', debuggingThisModule, " Sorry, {!r} not found.".format( attribute ) )
    # end of Find

    if 0: # Install manager
        vPrint( 'Quiet', debuggingThisModule, "\nINSTALL MANAGER" )
        im = Sword.InstallMgr() # FAILS
        vPrint( 'Quiet', debuggingThisModule, "\ndir im", im, dir(im) )

    if 0: # Locale manager
        vPrint( 'Quiet', debuggingThisModule, "\nLOCALE MANAGER" )
        lm = Sword.LocaleMgr()
        if BibleOrgSysGlobals.verbosityLevel > 0:
            vPrint( 'Quiet', debuggingThisModule, "dir lm", lm, dir(lm) )
            vPrint( 'Quiet', debuggingThisModule, "default {}".format( lm.getDefaultLocaleName() ) )
            vPrint( 'Quiet', debuggingThisModule, "available {}".format( lm.getAvailableLocales() ) ) # Gives weird result: "available ()"
            vPrint( 'Quiet', debuggingThisModule, "locale {}".format( lm.getLocale( "en" ) ) ) # Needs a string parameter but why does it return None?

    if 0: # try filters
        vPrint( 'Quiet', debuggingThisModule, "\nFILTER MANAGER" )
        fm = Sword.SWFilterMgr()
        vPrint( 'Quiet', debuggingThisModule, "\ndir filters", dir(fm) )

    if SwordType == 'CrosswireLibrary':
        # Get a list of available module names and types
        vPrint( 'Quiet', debuggingThisModule, "\n{} modules are installed.".format( len(library.getModules()) ) )
        for j,moduleBuffer in enumerate(library.getModules()):
            moduleID = moduleBuffer.getRawData()
            module = library.getModule( moduleID )
            if 0:
                vPrint( 'Quiet', debuggingThisModule, "{} {} ({}) {} {!r}".format( j, module.getName(), module.getType(), module.getLanguage(), module.getEncoding() ) )
                try: vPrint( 'Quiet', debuggingThisModule, "    {} {!r} {} {}".format( module.getDescription(), module.getMarkup(), module.getDirection(), "" ) )
                except UnicodeDecodeError: vPrint( 'Quiet', debuggingThisModule, "   Description is not Unicode!" )
            break
        #vPrint( 'Quiet', debuggingThisModule, "\n", j, "dir module", dir(module) )

        # Try some modules
        mod1 = library.getModule( 'KJV' )
        assert mod1 is not None
        vPrint( 'Quiet', debuggingThisModule, "\nmod1 {} ({}) {!r}".format( mod1.getName(), mod1.getType(), mod1.getDescription() ) )
        mod2 = library.getModule( 'ASV' )
        assert mod2 is not None
        vPrint( 'Quiet', debuggingThisModule, "\nmod2 {} ({}) {!r}".format( mod2.getName(), mod2.getType(), mod2.getDescription() ) )
        mod3 = library.getModule( 'WEB' )
        assert mod3 is not None
        vPrint( 'Quiet', debuggingThisModule, "\nmod3 {} ({}) {!r}".format( mod3.getName(), mod3.getType(), mod3.getDescription() ) )
        # abbott = library.getModule( 'Abbott' )
        # assert abbott is not None
        # if BibleOrgSysGlobals.verbosityLevel > 0:
        #     vPrint( 'Quiet', debuggingThisModule, "\nabbott {} ({}) {!r}".format( abbott.getName(), abbott.getType(), abbott.getDescription() ) )
        strongsGreek = library.getModule( 'StrongsGreek' )
        assert strongsGreek is not None
        vPrint( 'Quiet', debuggingThisModule, "\nSG {} ({}) {!r}\n".format( strongsGreek.getName(), strongsGreek.getType(), strongsGreek.getDescription() ) )
        strongsHebrew = library.getModule( 'StrongsHebrew' )
        assert strongsHebrew is not None
        vPrint( 'Quiet', debuggingThisModule, "\nSH {} ({}) {!r}\n\n".format( strongsHebrew.getName(), strongsHebrew.getType(), strongsHebrew.getDescription() ) )

        # Try a sword key
        sk = Sword.SWKey( "H0430" )
        #vPrint( 'Quiet', debuggingThisModule, "\ndir sk", dir(sk) )

        # Try a verse key
        vk = Sword.VerseKey( "Jn 3:16" )
        #vPrint( 'Quiet', debuggingThisModule, "\ndir vk", dir(vk) )
        #vPrint( 'Quiet', debuggingThisModule, "val", vk.validateCurrentLocale() ) # gives None
        if BibleOrgSysGlobals.verbosityLevel > 0:
            vPrint( 'Quiet', debuggingThisModule, "getInfo", vk.getLocale(), vk.getBookCount(), vk.getBookMax(), vk.getIndex(), vk.getVersificationSystem() )
            vPrint( 'Quiet', debuggingThisModule, "getBCV {}({}/{}) {}/{}:{} in {!r}({})/{}".format( vk.getBookName(), vk.getBookAbbrev(), vk.getOSISBookName(), vk.getChapter(), vk.getChapterMax(), vk.getVerse(), repr(vk.getTestament()), vk.getTestamentIndex(), vk.getTestamentMax() ) )
            vPrint( 'Quiet', debuggingThisModule, "getText {} {} {} {} {!r}".format( vk.getOSISRef(), vk.getText(), vk.getRangeText(), vk.getShortText(), vk.getSuffix() ) )
            #vPrint( 'Quiet', debuggingThisModule, "bounds {} {}".format( vk.getLowerBound(), vk.getUpperBound() ) )

        if 0: # Set a filter HOW DO WE DO THIS???
            rFs = mod1.getRenderFilters()
            vPrint( 'Quiet', debuggingThisModule, mod1.getRenderFilters() )
            mod1.setRenderFilter()

        try: vPrint( 'Quiet', debuggingThisModule, "\n{} {}: {}".format( mod1.getName(), "Jonny 1:1", mod1.renderText( Sword.VerseKey("Jn 1:1") ) ) )
        except UnicodeDecodeError: vPrint( 'Quiet', debuggingThisModule, "Unicode decode error in", mod1.getName() )
        except UnicodeEncodeError: vPrint( 'Quiet', debuggingThisModule, "Unicode encode error in", mod1.getName() )

        mod1.increment()
        vPrint( 'Quiet', debuggingThisModule, "\n{} {}: {}".format( mod1.getName(), mod1.getKey().getText(), mod1.stripText(  ) ) )
        mod1.increment()
        vPrint( 'Quiet', debuggingThisModule, "\n{} {}: {}".format( mod1.getName(), mod1.getKey().getText(), mod1.renderText(  ) ) )
        try: vPrint( 'Quiet', debuggingThisModule, "\n{} {}: {}".format( mod2.getName(), vk.getText(), mod2.renderText( vk ) ) )
        except UnicodeDecodeError: vPrint( 'Quiet', debuggingThisModule, "Unicode decode error in", mod2.getName() )
        except UnicodeEncodeError: vPrint( 'Quiet', debuggingThisModule, "Unicode encode error in", mod2.getName() )
        try: vPrint( 'Quiet', debuggingThisModule, "\n{} {}: {}".format( mod3.getName(), vk.getText(), mod3.renderText( vk ) ) )
        except UnicodeDecodeError: vPrint( 'Quiet', debuggingThisModule, "Unicode decode error in", mod3.getName() )
        except UnicodeEncodeError: vPrint( 'Quiet', debuggingThisModule, "Unicode encode error in", mod3.getName() )
        try: vPrint( 'Quiet', debuggingThisModule, "\n{} {}: {}".format( mod3.getName(), vk.getText(), mod3.renderText( vk ) ) )
        except UnicodeDecodeError: vPrint( 'Quiet', debuggingThisModule, "Unicode decode error in", mod3.getName() )
        except UnicodeEncodeError: vPrint( 'Quiet', debuggingThisModule, "Unicode encode error in", mod3.getName() )

        try: vPrint( 'Quiet', debuggingThisModule, "\n{} {}: {}".format( strongsGreek.getName(), sk.getText(), strongsGreek.renderText( Sword.SWKey("G746") ) ) )
        except UnicodeDecodeError: vPrint( 'Quiet', debuggingThisModule, "Unicode decode error in", strongsGreek.getName() )
        except UnicodeEncodeError: vPrint( 'Quiet', debuggingThisModule, "Unicode encode error in", strongsGreek.getName() )
        try: vPrint( 'Quiet', debuggingThisModule, "\n{} {}: {}".format( strongsHebrew.getName(), sk.getText(), strongsHebrew.renderText( sk ) ) )
        except UnicodeDecodeError: vPrint( 'Quiet', debuggingThisModule, "Unicode decode error in", strongsHebrew.getName() )
        except UnicodeEncodeError: vPrint( 'Quiet', debuggingThisModule, "Unicode encode error in", strongsHebrew.getName() )

        if 0: # Get all vernacular booknames
            # VerseKey vk; while (!vk.Error()) { cout << vk.getBookName(); vk.setBook(vk.getBook()+1); }
            vk = Sword.VerseKey()
            while vk.popError()=='\x00':
                if BibleOrgSysGlobals.verbosityLevel > 0:
                    vPrint( 'Quiet', debuggingThisModule, "bookname", vk.getBookName() )
                booknumber = int( bytes( vk.getBook(),'utf-8' )[0] )
                vk.setBook( booknumber + 1 )

        if 0: # Get booknames by testament (from http://www.crosswire.org/wiki/DevTools:Code_Examples)
            vk = Sword.VerseKey()
            for t in range( 1, 2+1 ):
                vk.setTestament( t )
                for i in range( 1, vk.getBookMax()+1 ):
                    vk.setBook( i )
                    if debuggingThisModule: vPrint( 'Quiet', debuggingThisModule, t, i, vk.getBookName() )

        # Try a tree key on a GenBook
        module = library.getModule( 'Westminster' )
        vPrint( 'Quiet', debuggingThisModule, "\nmodule {} ({}) {!r}".format( module.getName(), module.getType(), module.getDescription() ) )
        def getGenBookTOC( tk, parent ):
            if tk is None: # obtain one from the module
                tk = Sword.TreeKey_castTo( module.getKey() ) # Only works for gen books
            if tk and tk.firstChild():
                while True:
                    if debuggingThisModule: vPrint( 'Quiet', debuggingThisModule, " ", tk.getText() )
                    # Keep track of the information for custom implementation
                    #Class *item = storeItemInfoForLaterUse(parent, text);
                    item = (parent) # temp ……
                    if tk.hasChildren():
                        if debuggingThisModule: vPrint( 'Quiet', debuggingThisModule, "  Getting children…" )
                        getGenBookTOC( tk, item )
                    if not tk.nextSibling(): break
        # end of getGenBookTOC
        getGenBookTOC( None, None )

    #Find( "sw" ) # lots!
    #Find( "store" ) # storeItemInfoForLaterUse
    #Find( "getGlobal" ) # should be lots

    if 1: # Test the SwordInterface (using Sword code)
        vPrint( 'Quiet', debuggingThisModule, "\n\nTesting SwordInterface using", SwordType )
        si = SwordInterface()
        if BibleOrgSysGlobals.verbosityLevel > 0:
            vPrint( 'Quiet', debuggingThisModule, "SwordInterface getAvailableModuleCodes", si.getAvailableModuleCodes() )
            vPrint( 'Quiet', debuggingThisModule, "SwordInterface getAvailableModuleCodeDuples", si.getAvailableModuleCodeDuples() )
            vPrint( 'Quiet', debuggingThisModule, "KJV", si.getModule() )
            vPrint( 'Quiet', debuggingThisModule, "makeKey", si.makeKey( 'GEN', '1', '1' ) )

    if 1 and __name__=='__main__' and SwordType=='CrosswireLibrary': # Test the SwordInterface again (using our code)
        # Don't switch SwordType unless this is the main module, coz it messes up the demo tests
        setSwordType( 'OurCode' )
        vPrint( 'Quiet', debuggingThisModule, "\n\nTesting SwordInterface using", SwordType )
        si = SwordInterface()
        if BibleOrgSysGlobals.verbosityLevel > 0:
            vPrint( 'Quiet', debuggingThisModule, "SwordInterface getAvailableModuleCodes", si.getAvailableModuleCodes() )
            vPrint( 'Quiet', debuggingThisModule, "SwordInterface getAvailableModuleCodeDuples", si.getAvailableModuleCodeDuples() )
            vPrint( 'Quiet', debuggingThisModule, "KJV", si.getModule() )
            vPrint( 'Quiet', debuggingThisModule, "makeKey", si.makeKey( 'GEN', '1', '1' ) )
# end of SwordResources.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, programNameVersion, LAST_MODIFIED_DATE )
    vPrint( 'Normal', debuggingThisModule, " using", SwordType )

    #vPrint( 'Quiet', debuggingThisModule, "\ndir Sword", dir(Sword) )
    # Gives: dir Sword ['AttributeListMap', 'AttributeListMap_swigregister', 'AttributeTypeListMap',
    # 'AttributeTypeListMap_swigregister', 'AttributeValueMap', 'AttributeValueMap_swigregister', 'BIB_BIBTEX',
    # 'BOOKBLOCKS', 'BasicFilterUserData', 'BasicFilterUserData_swigregister', 'CHAPTERBLOCKS', 'DIRECTION_BIDI',
    # 'DIRECTION_LTR', 'DIRECTION_RTL', 'DirEntry', 'DirEntryVector', 'DirEntryVector_swigregister',
    # 'DirEntry_swigregister', 'ENC_HTML', 'ENC_LATIN1', 'ENC_RTF', 'ENC_SCSU', 'ENC_UNKNOWN', 'ENC_UTF16',
    # 'ENC_UTF8', 'ENDOFABBREVS', 'EncodingFilterMgr', 'EncodingFilterMgr_castTo',
    # 'EncodingFilterMgr_swigregister', 'FAILED',
    # 'FMT_GBF', 'FMT_HTML', 'FMT_HTMLHREF', 'FMT_LATEX', 'FMT_OSIS', 'FMT_PLAIN', 'FMT_RTF', 'FMT_TEI',
    # 'FMT_THML', 'FMT_UNKNOWN', 'FMT_WEBIF', 'FMT_XHTML',
    # 'FileDesc', 'FileDesc_swigregister', 'FileMgr', 'FileMgr_copyDir', 'FileMgr_copyFile',
    # 'FileMgr_createParent', 'FileMgr_createPathAndFile', 'FileMgr_existsDir', 'FileMgr_existsFile',
    # 'FileMgr_getLine', 'FileMgr_getSystemFileMgr', 'FileMgr_isDirectory', 'FileMgr_openFileReadOnly',
    # 'FileMgr_removeDir', 'FileMgr_removeFile', 'FileMgr_setSystemFileMgr', 'FileMgr_swigregister',
    # 'GBFHTMLHREF', 'GBFHTMLHREF_swigregister', 'INHERITED', 'InstallMgr', 'InstallMgr_getModuleStatus',
    # 'InstallMgr_swigregister', 'InstallSource', 'InstallSourceMap', 'InstallSourceMap_swigregister',
    # 'InstallSource_swigregister', 'JUNKBUFSIZE', 'KEYERR_OUTOFBOUNDS', 'LZSSCompress', 'LZSSCompress_castTo',
    # 'LZSSCompress_swigregister', 'ListKey', 'ListKey_castTo', 'ListKey_swigregister', 'LocaleMgr',
    # 'LocaleMgr_getSystemLocaleMgr', 'LocaleMgr_setSystemLocaleMgr', 'LocaleMgr_swigregister', 'MarkupCallback',
    # 'MarkupCallback_swigregister', 'MarkupFilterMgr', 'MarkupFilterMgr_castTo', 'MarkupFilterMgr_swigregister',
    # 'ModuleMap', 'ModuleMap_swigregister', 'MyMarkup', 'MyMarkup_swigregister', 'OSISData',
    # 'OSISData_swigregister', 'OSISHTMLHREF', 'OSISHTMLHREF_swigregister', 'PyConfigEntMap',
    # 'PyConfigEntMap_swigregister', 'PyOSISHTMLHREF', 'PyOSISHTMLHREF_getData', 'PyOSISHTMLHREF_swigregister',
    # 'PySectionMap', 'PySectionMap_swigregister', 'PyStringMgr', 'PyStringMgr_swigregister', 'PyThMLHTMLHREF',
    # 'PyThMLHTMLHREF_getData', 'PyThMLHTMLHREF_swigregister', 'RawCom', 'RawCom_castTo', 'RawCom_createModule',
    # 'RawCom_swigregister', 'RawGenBook', 'RawGenBook_castTo', 'RawGenBook_createModule',
    # 'RawGenBook_swigregister', 'RawLD', 'RawLD4', 'RawLD4_castTo', 'RawLD4_createModule', 'RawLD4_swigregister',
    # 'RawLD_castTo', 'RawLD_createModule', 'RawLD_swigregister', 'RawStr', 'RawStr4', 'RawStr4_createModule',
    # 'RawStr4_swigregister', 'RawStr_createModule', 'RawStr_swigregister', 'RawText', 'RawText_castTo',
    # 'RawText_createModule', 'RawText_swigregister', 'RawVerse', 'RawVerse_createModule',
    # 'RawVerse_swigregister', 'RemoteTransport', 'RemoteTransport_swigregister', 'RenderCallback',
    # 'RenderCallback_swigregister', 'ReturnSuccess', 'ReturnSuccess_swigregister', 'SEARCHFLAG_MATCHWHOLEENTRY',
    # 'SUCCEEDED', 'SWBasicFilter', 'SWBasicFilter_swigregister', 'SWBuf', 'SWBuf_swigregister', 'SWClass',
    # 'SWClass_swigregister', 'SWCom', 'SWCom_castTo', 'SWCom_swigregister', 'SWCompress',
    # 'SWCompress_swigregister', 'SWConfig', 'SWConfig_swigregister', 'SWDisplay', 'SWDisplay_swigregister',
    # 'SWFilter', 'SWFilterMgr', 'SWFilterMgr_swigregister', 'SWFilter_swigregister', 'SWGenBook',
    # 'SWGenBook_castTo', 'SWGenBook_swigregister', 'SWKey', 'SWKey_swigregister', 'SWLD', 'SWLD_castTo',
    # 'SWLD_swigregister', 'SWLocale', 'SWLocale_swigregister', 'SWLog', 'SWLog_getSystemLog',
    # 'SWLog_setSystemLog', 'SWLog_swigregister', 'SWMgr', 'SWMgr_swigregister', 'SWModule', 'SWModule_castTo',
    # 'SWModule_createModule', 'SWModule_swigregister', 'SWORD_VERSION_MAJOR', 'SWORD_VERSION_MICRO',
    # 'SWORD_VERSION_MINOR', 'SWORD_VERSION_NANO', 'SWORD_VERSION_NUM', 'SWORD_VERSION_STR', 'SWObject',
    # 'SWObject_swigregister', 'SWOptionFilter', 'SWOptionFilter_castTo', 'SWOptionFilter_swigregister',
    # 'SWSearchable', 'SWSearchable_swigregister', 'SWSearcher', 'SWSearcher_Callback', 'SWSearcher_swigregister',
    # 'SWText', 'SWText_castTo', 'SWText_swigregister', 'SWVersion', 'SWVersion_swigregister', 'SW_POSITION',
    # 'SW_POSITION_swigregister', 'StatusReporter', 'StatusReporter_swigregister', 'StringList',
    # 'StringList_swigregister', 'StringMgr', 'StringMgr_getSystemStringMgr', 'StringMgr_hasUTF8Support',
    # 'StringMgr_setSystemStringMgr', 'StringMgr_swigregister', 'StringVector', 'StringVector_swigregister',
    # 'SwigPyIterator', 'SwigPyIterator_swigregister',
    # 'ThMLData', 'ThMLData_swigregister', 'ThMLHTMLHREF', 'ThMLHTMLHREF_swigregister',
    # 'TreeKey', 'TreeKeyIdx', 'TreeKeyIdx_castTo', 'TreeKeyIdx_create', 'TreeKeyIdx_swigregister',
    # 'TreeKey_castTo', 'TreeKey_swigregister',
    # 'URL', 'URL_decode', 'URL_encode', 'URL_swigregister',
    # 'UTF8HTML', 'UTF8HTML_swigregister', 'VERSEBLOCKS',
    # 'VerseKey', 'VerseKey_castTo', 'VerseKey_convertToOSIS', 'VerseKey_swigregister', 'VerseTreeKey',
    # 'VerseTreeKey_castTo', 'VerseTreeKey_swigregister',
    # 'VersificationMgr', 'VersificationMgr_getSystemVersificationMgr',
    # 'VersificationMgr_setSystemVersificationMgr', 'VersificationMgr_swigregister',
    # 'XMLTag', 'XMLTag_swigregister',
    # 'ZipCompress', 'ZipCompress_castTo', 'ZipCompress_swigregister',
    # '_Sword', '__builtin__', '__builtins__', '__cached__', '__doc__', '__file__', '__loader__', '__name__',
    # '__package__', '__spec__', '_newclass', '_object', '_swig_getattr', '_swig_property', '_swig_repr',
    # '_swig_setattr', '_swig_setattr_nondynamic', 'abbrev', 'abbrev_swigregister', 'builtin_abbrevs', 'cvar',
    # 'sbook', 'sbook_swigregister', 'toupperstr', 'toupperstr_utf8', 'weakref', 'weakref_proxy',
    # 'zCom', 'zCom_castTo', 'zCom_createModule', 'zCom_swigregister',
    # 'zLD', 'zLD_castTo', 'zLD_createModule', 'zLD_swigregister',
    # 'zStr', 'zStr_createModule', 'zStr_swigregister',
    # 'zText', 'zText_castTo', 'zText_createModule', 'zText_swigregister',
    # 'zVerse', 'zVerse_createModule', 'zVerse_swigregister']

    if SwordType == 'CrosswireLibrary':
        vPrint( 'Quiet', debuggingThisModule, "Sword Version string", Sword.SWORD_VERSION_STR )
        # Gives: Sword Version string 1.8.900
        #if BibleOrgSysGlobals.verbosityLevel > 0:
            #vPrint( 'Quiet', debuggingThisModule, "\ndir Sword.SWVersion()", dir(Sword.SWVersion()) )
            # Gives: dir Sword.SWVersion() ['__class__', '__del__', '__delattr__', '__dict__', '__dir__', '__doc__',
            # '__eq__', '__format__', '__ge__', '__getattr__', '__getattribute__', '__gt__', '__hash__', '__init__',
            # '__init_subclass__', '__le__', '__lt__', '__module__', '__ne__', '__new__', '__reduce__',
            # '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__', '__subclasshook__',
            # '__swig_destroy__', '__swig_getmethods__', '__swig_setmethods__', '__weakref__', 'compare',
            # 'currentVersion', 'getText', 'major', 'minor', 'minor2', 'minor3', 'this']
            #vPrint( 'Quiet', debuggingThisModule, 'Version string', repr(Sword.SWVersion().getText()) )
            # Gives: Version string '0.0'
            #vPrint( 'Quiet', debuggingThisModule, "Version ints", repr(Sword.SWVersion().major), Sword.SWVersion().minor, Sword.SWVersion().minor2, Sword.SWVersion().minor3 ) # ints
            # Gives: Version ints 0 0 -1 -1

        library = Sword.SWMgr()
        #vPrint( 'Quiet', debuggingThisModule, "\ndir library", dir(library) )
        # Gives: dir library ['InstallScan', 'MODTYPE_BIBLES', 'MODTYPE_COMMENTARIES', 'MODTYPE_DAILYDEVOS',
        # 'MODTYPE_GENBOOKS', 'MODTYPE_LEXDICTS', '__class__', '__del__', '__delattr__', '__dict__', '__dir__',
        # '__doc__', '__eq__', '__format__', '__ge__', '__getattr__', '__getattribute__', '__gt__', '__hash__',
        # '__init__', '__init_subclass__', '__le__', '__lt__', '__module__', '__ne__', '__new__', '__reduce__',
        # '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__', '__subclasshook__',
        # '__swig_destroy__', '__swig_getmethods__', '__swig_setmethods__', '__weakref__', 'augmentModules',
        # 'config', 'configPath', 'deleteModule', 'filterText', 'getGlobalOption', 'getGlobalOptionTip',
        # 'getGlobalOptionValues', 'getGlobalOptionValuesVector', 'getGlobalOptions', 'getGlobalOptionsVector',
        # 'getModule', 'getModuleAt', 'getModules', 'globalConfPath', 'isICU', 'load', 'prefixPath',
        # 'setCipherKey', 'setGlobalOption', 'sysConfig', 'this']
        #vPrint( 'Quiet', debuggingThisModule, "\nlibrary getHomeDir", library.getHomeDir().getRawData() ) # Fails

    def Find( attribute ):
        """
        Search for methods and attributes
        """
        if debuggingThisModule or  BibleOrgSysGlobals.verbosityLevel > 0:
            vPrint( 'Quiet', debuggingThisModule, "\nSearching for attribute {!r}…".format( attribute ) )
        found = False
        AA = attribute.upper()
        for thing in dir(Sword):
            BB = thing.upper()
            if BB.startswith(AA): vPrint( 'Quiet', debuggingThisModule, "  Have {} in Sword".format( thing ) ); found = True
        for thing in dir(Sword.SWVersion()):
            BB = thing.upper()
            if BB.startswith(AA): vPrint( 'Quiet', debuggingThisModule, "  Have {} in SWVersion".format( thing ) ); found = True
        for thing in dir(Sword.SWMgr()):
            BB = thing.upper()
            if BB.startswith(AA): vPrint( 'Quiet', debuggingThisModule, "  Have {} in SWMgr".format( thing ) ); found = True
        module = library.getModule( 'KJV' )
        for thing in dir(module):
            BB = thing.upper()
            if BB.startswith(AA): vPrint( 'Quiet', debuggingThisModule, "  Have {} in SWModule".format( thing ) ); found = True
        for thing in dir(Sword.SWKey()):
            BB = thing.upper()
            if BB.startswith(AA): vPrint( 'Quiet', debuggingThisModule, "  Have {} in SWKey".format( thing ) ); found = True
        for thing in dir(Sword.VerseKey()):
            BB = thing.upper()
            if BB.startswith(AA): vPrint( 'Quiet', debuggingThisModule, "  Have {} in VerseKey".format( thing ) ); found = True
        #for thing in dir(Sword.InstallMgr()):
            #BB = thing.upper()
            #if BB.startswith(AA): vPrint( 'Quiet', debuggingThisModule, "  Have {} in InstallMgr".format( thing ) ); found = True
        for thing in dir(Sword.LocaleMgr()):
            BB = thing.upper()
            if BB.startswith(AA): vPrint( 'Quiet', debuggingThisModule, "  Have {} in LocaleMgr".format( thing ) ); found = True
        for thing in dir(Sword.SWFilterMgr()):
            BB = thing.upper()
            if BB.startswith(AA): vPrint( 'Quiet', debuggingThisModule, "  Have {} in SWFilterMgr".format( thing ) ); found = True
        if not found: vPrint( 'Quiet', debuggingThisModule, " Sorry, {!r} not found.".format( attribute ) )
    # end of Find

    if 0: # Install manager
        vPrint( 'Quiet', debuggingThisModule, "\nINSTALL MANAGER" )
        im = Sword.InstallMgr() # FAILS
        vPrint( 'Quiet', debuggingThisModule, "\ndir im", im, dir(im) )

    if 0: # Locale manager
        vPrint( 'Quiet', debuggingThisModule, "\nLOCALE MANAGER" )
        lm = Sword.LocaleMgr()
        if BibleOrgSysGlobals.verbosityLevel > 0:
            vPrint( 'Quiet', debuggingThisModule, "dir lm", lm, dir(lm) )
            vPrint( 'Quiet', debuggingThisModule, "default {}".format( lm.getDefaultLocaleName() ) )
            vPrint( 'Quiet', debuggingThisModule, "available {}".format( lm.getAvailableLocales() ) ) # Gives weird result: "available ()"
            vPrint( 'Quiet', debuggingThisModule, "locale {}".format( lm.getLocale( "en" ) ) ) # Needs a string parameter but why does it return None?

    if 0: # try filters
        vPrint( 'Quiet', debuggingThisModule, "\nFILTER MANAGER" )
        fm = Sword.SWFilterMgr()
        vPrint( 'Quiet', debuggingThisModule, "\ndir filters", dir(fm) )

    if SwordType == 'CrosswireLibrary':
        # Get a list of available module names and types
        vPrint( 'Quiet', debuggingThisModule, "\n{} modules are installed.".format( len(library.getModules()) ) )
        for j,moduleBuffer in enumerate(library.getModules()):
            moduleID = moduleBuffer.getRawData()
            module = library.getModule( moduleID )
            if 0:
                vPrint( 'Quiet', debuggingThisModule, "{} {} ({}) {} {!r}".format( j, module.getName(), module.getType(), module.getLanguage(), module.getEncoding() ) )
                try: vPrint( 'Quiet', debuggingThisModule, "    {} {!r} {} {}".format( module.getDescription(), module.getMarkup(), module.getDirection(), "" ) )
                except UnicodeDecodeError: vPrint( 'Quiet', debuggingThisModule, "   Description is not Unicode!" )
        #vPrint( 'Quiet', debuggingThisModule, "\n", j, "dir module", dir(module) )

        # Try some modules
        mod1 = library.getModule( 'KJV' )
        assert mod1 is not None
        vPrint( 'Quiet', debuggingThisModule, "\nmod1 {} ({}) {!r}".format( mod1.getName(), mod1.getType(), mod1.getDescription() ) )
        mod2 = library.getModule( 'ASV' )
        assert mod2 is not None
        vPrint( 'Quiet', debuggingThisModule, "\nmod2 {} ({}) {!r}".format( mod2.getName(), mod2.getType(), mod2.getDescription() ) )
        mod3 = library.getModule( 'WEB' )
        assert mod3 is not None
        vPrint( 'Quiet', debuggingThisModule, "\nmod3 {} ({}) {!r}".format( mod3.getName(), mod3.getType(), mod3.getDescription() ) )
        # abbott = library.getModule( 'Abbott' )
        # assert abbott is not None
        # if BibleOrgSysGlobals.verbosityLevel > 0:
        #     vPrint( 'Quiet', debuggingThisModule, "\nabbott {} ({}) {!r}".format( abbott.getName(), abbott.getType(), abbott.getDescription() ) )
        strongsGreek = library.getModule( 'StrongsGreek' )
        assert strongsGreek is not None
        vPrint( 'Quiet', debuggingThisModule, "\nSG {} ({}) {!r}\n".format( strongsGreek.getName(), strongsGreek.getType(), strongsGreek.getDescription() ) )
        strongsHebrew = library.getModule( 'StrongsHebrew' )
        assert strongsHebrew is not None
        vPrint( 'Quiet', debuggingThisModule, "\nSH {} ({}) {!r}\n\n".format( strongsHebrew.getName(), strongsHebrew.getType(), strongsHebrew.getDescription() ) )

        # Try a sword key
        sk = Sword.SWKey( "H0430" )
        #vPrint( 'Quiet', debuggingThisModule, "\ndir sk", dir(sk) )

        # Try a verse key
        vk = Sword.VerseKey( "Jn 3:16" )
        #vPrint( 'Quiet', debuggingThisModule, "\ndir vk", dir(vk) )
        #vPrint( 'Quiet', debuggingThisModule, "val", vk.validateCurrentLocale() ) # gives None
        if BibleOrgSysGlobals.verbosityLevel > 0:
            vPrint( 'Quiet', debuggingThisModule, "getInfo", vk.getLocale(), vk.getBookCount(), vk.getBookMax(), vk.getIndex(), vk.getVersificationSystem() )
            vPrint( 'Quiet', debuggingThisModule, "getBCV {}({}/{}) {}/{}:{} in {!r}({})/{}".format( vk.getBookName(), vk.getBookAbbrev(), vk.getOSISBookName(), vk.getChapter(), vk.getChapterMax(), vk.getVerse(), repr(vk.getTestament()), vk.getTestamentIndex(), vk.getTestamentMax() ) )
            vPrint( 'Quiet', debuggingThisModule, "getText {} {} {} {} {!r}".format( vk.getOSISRef(), vk.getText(), vk.getRangeText(), vk.getShortText(), vk.getSuffix() ) )
            #vPrint( 'Quiet', debuggingThisModule, "bounds {} {}".format( vk.getLowerBound(), vk.getUpperBound() ) )

        if 0: # Set a filter HOW DO WE DO THIS???
            rFs = mod1.getRenderFilters()
            vPrint( 'Quiet', debuggingThisModule, mod1.getRenderFilters() )
            mod1.setRenderFilter()

        try: vPrint( 'Quiet', debuggingThisModule, "\n{} {}: {}".format( mod1.getName(), "Jonny 1:1", mod1.renderText( Sword.VerseKey("Jn 1:1") ) ) )
        except UnicodeDecodeError: vPrint( 'Quiet', debuggingThisModule, "Unicode decode error in", mod1.getName() )
        except UnicodeEncodeError: vPrint( 'Quiet', debuggingThisModule, "Unicode encode error in", mod1.getName() )

        mod1.increment()
        vPrint( 'Quiet', debuggingThisModule, "\n{} {}: {}".format( mod1.getName(), mod1.getKey().getText(), mod1.stripText(  ) ) )
        mod1.increment()
        vPrint( 'Quiet', debuggingThisModule, "\n{} {}: {}".format( mod1.getName(), mod1.getKey().getText(), mod1.renderText(  ) ) )
        try: vPrint( 'Quiet', debuggingThisModule, "\n{} {}: {}".format( mod2.getName(), vk.getText(), mod2.renderText( vk ) ) )
        except UnicodeDecodeError: vPrint( 'Quiet', debuggingThisModule, "Unicode decode error in", mod2.getName() )
        except UnicodeEncodeError: vPrint( 'Quiet', debuggingThisModule, "Unicode encode error in", mod2.getName() )
        try: vPrint( 'Quiet', debuggingThisModule, "\n{} {}: {}".format( mod3.getName(), vk.getText(), mod3.renderText( vk ) ) )
        except UnicodeDecodeError: vPrint( 'Quiet', debuggingThisModule, "Unicode decode error in", mod3.getName() )
        except UnicodeEncodeError: vPrint( 'Quiet', debuggingThisModule, "Unicode encode error in", mod3.getName() )
        try: vPrint( 'Quiet', debuggingThisModule, "\n{} {}: {}".format( mod3.getName(), vk.getText(), mod3.renderText( vk ) ) )
        except UnicodeDecodeError: vPrint( 'Quiet', debuggingThisModule, "Unicode decode error in", mod3.getName() )
        except UnicodeEncodeError: vPrint( 'Quiet', debuggingThisModule, "Unicode encode error in", mod3.getName() )

        # try: vPrint( 'Quiet', debuggingThisModule, "\n{} {}: {}".format( abbott.getName(), vk.getText(), abbott.renderText( vk ) ) )
        # except UnicodeDecodeError: vPrint( 'Quiet', debuggingThisModule, "Unicode decode error in", abbott.getName() )
        # except UnicodeEncodeError: vPrint( 'Quiet', debuggingThisModule, "Unicode encode error in", abbott.getName() )

        try: vPrint( 'Quiet', debuggingThisModule, "\n{} {}: {}".format( strongsGreek.getName(), sk.getText(), strongsGreek.renderText( Sword.SWKey("G746") ) ) )
        except UnicodeDecodeError: vPrint( 'Quiet', debuggingThisModule, "Unicode decode error in", strongsGreek.getName() )
        except UnicodeEncodeError: vPrint( 'Quiet', debuggingThisModule, "Unicode encode error in", strongsGreek.getName() )
        try: vPrint( 'Quiet', debuggingThisModule, "\n{} {}: {}".format( strongsHebrew.getName(), sk.getText(), strongsHebrew.renderText( sk ) ) )
        except UnicodeDecodeError: vPrint( 'Quiet', debuggingThisModule, "Unicode decode error in", strongsHebrew.getName() )
        except UnicodeEncodeError: vPrint( 'Quiet', debuggingThisModule, "Unicode encode error in", strongsHebrew.getName() )

        if 0: # Get all vernacular booknames
            # VerseKey vk; while (!vk.Error()) { cout << vk.getBookName(); vk.setBook(vk.getBook()+1); }
            vk = Sword.VerseKey()
            while vk.popError()=='\x00':
                if BibleOrgSysGlobals.verbosityLevel > 0:
                    vPrint( 'Quiet', debuggingThisModule, "bookname", vk.getBookName() )
                booknumber = int( bytes( vk.getBook(),'utf-8' )[0] )
                vk.setBook( booknumber + 1 )

        if 0: # Get booknames by testament (from http://www.crosswire.org/wiki/DevTools:Code_Examples)
            vk = Sword.VerseKey()
            for t in range( 1, 2+1 ):
                vk.setTestament( t )
                for i in range( 1, vk.getBookMax()+1 ):
                    vk.setBook( i )
                    if debuggingThisModule: vPrint( 'Quiet', debuggingThisModule, t, i, vk.getBookName() )

        # Try a tree key on a GenBook
        module = library.getModule( 'Westminster' )
        vPrint( 'Quiet', debuggingThisModule, "\nmodule {} ({}) {!r}".format( module.getName(), module.getType(), module.getDescription() ) )
        def getGenBookTOC( tk, parent ):
            if tk is None: # obtain one from the module
                tk = Sword.TreeKey_castTo( module.getKey() ) # Only works for gen books
            if tk and tk.firstChild():
                while True:
                    if debuggingThisModule: vPrint( 'Quiet', debuggingThisModule, " ", tk.getText() )
                    # Keep track of the information for custom implementation
                    #Class *item = storeItemInfoForLaterUse(parent, text);
                    item = (parent) # temp ……
                    if tk.hasChildren():
                        if debuggingThisModule: vPrint( 'Quiet', debuggingThisModule, "  Getting children…" )
                        getGenBookTOC( tk, item )
                    if not tk.nextSibling(): break
        # end of getGenBookTOC
        getGenBookTOC( None, None )

    #Find( "sw" ) # lots!
    #Find( "store" ) # storeItemInfoForLaterUse
    #Find( "getGlobal" ) # should be lots

    if 1: # Test the SwordInterface (using Sword code)
        vPrint( 'Quiet', debuggingThisModule, "\n\nTesting SwordInterface using", SwordType )
        si = SwordInterface()
        if BibleOrgSysGlobals.verbosityLevel > 0:
            vPrint( 'Quiet', debuggingThisModule, "SwordInterface getAvailableModuleCodes", si.getAvailableModuleCodes() )
            vPrint( 'Quiet', debuggingThisModule, "SwordInterface getAvailableModuleCodeDuples", si.getAvailableModuleCodeDuples() )
            vPrint( 'Quiet', debuggingThisModule, "KJV", si.getModule() )
            vPrint( 'Quiet', debuggingThisModule, "makeKey", si.makeKey( 'GEN', '1', '1' ) )

    if 1 and __name__=='__main__' and SwordType=='CrosswireLibrary': # Test the SwordInterface again (using our code)
        # Don't switch SwordType unless this is the main module, coz it messes up the demo tests
        setSwordType( 'OurCode' )
        vPrint( 'Quiet', debuggingThisModule, "\n\nTesting SwordInterface using", SwordType )
        si = SwordInterface()
        if BibleOrgSysGlobals.verbosityLevel > 0:
            vPrint( 'Quiet', debuggingThisModule, "SwordInterface getAvailableModuleCodes", si.getAvailableModuleCodes() )
            vPrint( 'Quiet', debuggingThisModule, "SwordInterface getAvailableModuleCodeDuples", si.getAvailableModuleCodeDuples() )
            vPrint( 'Quiet', debuggingThisModule, "KJV", si.getModule() )
            vPrint( 'Quiet', debuggingThisModule, "makeKey", si.makeKey( 'GEN', '1', '1' ) )
# end of SwordResources.fullDemo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of SwordResources.py
