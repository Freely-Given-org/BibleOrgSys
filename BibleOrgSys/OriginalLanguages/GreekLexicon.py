#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# GreekLexicon.py
#
# Module handling the Greek lexicon
#
# Copyright (C) 2014-2017 Robert Hunt
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
Module handling the morphgnt Greek lexicon.

    The first class is the one that reads and parses the XML source file.

    The later class is the one for users to
        access the Strongs lexical entries
        via various keys and in various formats.
"""

from gettext import gettext as _

LAST_MODIFIED_DATE = '2017-12-07' # by RJH
SHORT_PROGRAM_NAME = "GreekLexicon"
PROGRAM_NAME = "Greek Lexicon format handler"
PROGRAM_VERSION = '0.17'
programNameVersion = f'{PROGRAM_NAME} v{PROGRAM_VERSION}'
programNameVersionDate = f'{programNameVersion} {_("last modified")} {LAST_MODIFIED_DATE}'

debuggingThisModule = False


import logging, os.path, sys
import re
from xml.etree.ElementTree import ElementTree, ParseError

if __name__ == '__main__':
    aboveAboveFolderPath = os.path.dirname( os.path.dirname( os.path.dirname( os.path.abspath( __file__ ) ) ) )
    if aboveAboveFolderPath not in sys.path:
        sys.path.insert( 0, aboveAboveFolderPath )
from BibleOrgSys import BibleOrgSysGlobals



def t( messageString ):
    """
    Prepends the module name to a error or warning message string
        if we are in debug mode.
    Returns the new string.
    """
    try: nameBit, errorBit = messageString.split( ': ', 1 )
    except ValueError: nameBit, errorBit = '', messageString
    if BibleOrgSysGlobals.debugFlag or debuggingThisModule:
        nameBit = '{}{}{}'.format( SHORT_PROGRAM_NAME, '.' if nameBit else '', nameBit )
    return '{}{}'.format( nameBit, errorBit )



class GreekStrongsFileConverter:
    """
    Class for reading, validating, and converting Greek Strongs database.
    This is only intended as a transitory class (used to read the XML at start-up).
    The GreekLexicon class has functions more generally useful.

    Typical entries are:
        <entry strongs="00002">
            <strongs>2</strongs>   <greek BETA="*)AARW/N" unicode="Ἀαρών" translit="Aarṓn"/>   <pronunciation strongs="ah-ar-ohn'"/>
            <strongs_derivation>of Hebrew origin (<strongsref language="HEBREW" strongs="0175"/>);</strongs_derivation><strongs_def> Aaron, the brother of Moses</strongs_def><kjv_def>:--Aaron.</kjv_def>
            <see language="HEBREW" strongs="0175"/>
        </entry>
        <entry strongs="00003">
            <strongs>3</strongs>   <greek BETA="*)ABADDW/N" unicode="Ἀβαδδών" translit="Abaddṓn"/>   <pronunciation strongs="ab-ad-dohn'"/>
            <strongs_derivation>of Hebrew origin (<strongsref language="HEBREW" strongs="011"/>);</strongs_derivation><strongs_def> a destroying angel</strongs_def><kjv_def>:--Abaddon.</kjv_def>
            <see language="HEBREW" strongs="011"/>
        </entry>
        …
        <entry strongs="05624">
            <strongs>5624</strongs>   <greek BETA="W)FE/LIMOS" unicode="ὠφέλιμος" translit="ōphélimos"/>   <pronunciation strongs="o-fel'-ee-mos"/>
            <strongs_derivation>from a form of <strongsref language="GREEK" strongs="3786"/>;</strongs_derivation><strongs_def> helpful or serviceable, i.e.
                advantageous</strongs_def><kjv_def>:--profit(-able).</kjv_def>
            <see language="GREEK" strongs="3786"/>
        </entry>
        </entries></strongsdictionary>
    """
    databaseFilename = "strongsgreek.xml"
    treeTag = "strongsdictionary"


    def __init__( self ):
        """
        Constructor: just sets up the file converter object.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( t("GreekStrongsFileConverter.__init__()") )
        self.title = self.version = self.date = None
        self.XMLTree = self.header = self.StrongsEntries = None
    # end of GreekStrongsFileConverter.__init__


    def __str__( self ):
        """
        This method returns the string representation of a Greek Lexicon converter object.

        @return: the name of a Greek Lexicon converter object formatted as a string
        @rtype: string
        """
        result = "Greek Strongs Lexicon File Converter object"
        if self.title: result += ('\n' if result else '') + "  " + self.title
        if self.version: result += ('\n' if result else '') + "  " + _("Version: {} ").format( self.version )
        if self.date: result += ('\n' if result else '') + "  " + _("Date: {}").format( self.date )
        result += ('\n' if result else '') + "  " + _("Number of entries = {}").format( len(self.StrongsEntries) )
        return result
    # end of GreekStrongsFileConverter.__str__


    def loadAndValidate( self, XMLFolder ):
        """
        Load the source XML file and remove the header from the tree.
        Also, extracts some useful elements from the header element.
        """
        if BibleOrgSysGlobals.verbosityLevel > 2: print( _("Loading from {}…").format( XMLFolder ) )
        self.XMLFolder = XMLFolder
        XMLFileOrFilepath = os.path.join( XMLFolder, GreekStrongsFileConverter.databaseFilename )
        try: self.XMLTree = ElementTree().parse( XMLFileOrFilepath )
        except FileNotFoundError:
            logging.critical( t("GreekStrongsFileConverter could not find database at {}").format( XMLFileOrFilepath ) )
            raise FileNotFoundError
        except ParseError as err:
            logging.critical( _("Loader parse error in xml file {}: {} {}").format( GreekStrongsFileConverter.databaseFilename, sys.exc_info()[0], err ) )
            raise ParseError
        if BibleOrgSysGlobals.debugFlag: assert len( self.XMLTree ) # Fail here if we didn't load anything at all

        if self.XMLTree.tag == GreekStrongsFileConverter.treeTag:
            for segment in self.XMLTree:
                #print( segment.tag )
                if segment.tag == "prologue":
                    pass
                elif segment.tag == "entries":
                    self.validateEntries( segment )
                else: logging.error( "ks24 Unprocessed {!r} element ({}) in entry".format( segment.tag, segment.text ) )
        else: logging.error( "Expected to load {!r} but got {!r}".format( GreekStrongsFileConverter.treeTag, self.XMLTree.tag ) )
        if self.XMLTree.tail is not None and self.XMLTree.tail.strip(): logging.error( "vs42 Unexpected {!r} tail data after {} element".format( self.XMLTree.tail, self.XMLTree.tag ) )
    # end of GreekStrongsFileConverter.loadAndValidate


    def validateEntries( self, segment ):
        """
        Check/validate the given Strongs lexicon entries.
        """
        if BibleOrgSysGlobals.debugFlag: assert segment.tag == "entries"
        BibleOrgSysGlobals.checkXMLNoText( segment, segment.tag, "kw99" )
        BibleOrgSysGlobals.checkXMLNoTail( segment, segment.tag, "ls90" )
        BibleOrgSysGlobals.checkXMLNoAttributes( segment, segment.tag, "hsj2" )

        self.StrongsEntries = {}
        for element in segment:
            if element.tag == "entry":
                self.validateEntry( element )
    # end of GreekStrongsFileConverter.validateEntries


    def validateEntry( self, entry ):
        """
        Check/validate the given Strongs Greek lexicon entry.
        """
        if BibleOrgSysGlobals.debugFlag: assert entry.tag == "entry"
        BibleOrgSysGlobals.checkXMLNoText( entry, entry.tag, "na19" )
        BibleOrgSysGlobals.checkXMLNoTail( entry, entry.tag, "kaq9" )

        # Process the entry attributes first
        strongs5 = None
        for attrib,value in entry.items():
            if attrib ==  "strongs":
                strongs5 = value
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "Validating {} entry…".format( strongs5 ) )
            else: logging.warning( "Unprocessed {!r} attribute ({}) in main entry element".format( attrib, value ) )
        if BibleOrgSysGlobals.debugFlag: assert len(strongs5)==5 and strongs5.isdigit()

        entryResults = {}
        entryString = ""
        gettingEssentials = True
        for j, element in enumerate( entry ):
            #print( strongs5, j, element.tag, repr(entryString) )
            if element.tag == "strongs":
                if BibleOrgSysGlobals.debugFlag: assert gettingEssentials and j==0 and element.text
                BibleOrgSysGlobals.checkXMLNoAttributes( element, element.tag, "md3d" )
                if strongs5!='02717' and (3203 > int(strongs5) > 3302):
                    BibleOrgSysGlobals.checkXMLNoTail( element, element.tag, "f3g7" )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, element.tag, "m56g" )
                strongs = element.text
                if BibleOrgSysGlobals.debugFlag: assert strongs5.endswith( strongs )
                if element.tail and element.tail.strip(): entryString += element.tail.strip()
            elif element.tag == "greek":
                location = "greek in Strongs " + strongs5
                BibleOrgSysGlobals.checkXMLNoText( element, location, "jke0" )
                #BibleOrgSysGlobals.checkXMLNoTail( element, location, "ks24" )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, location, "df35" )
                # Process the attributes
                translit = greek = beta = None
                for attrib,value in element.items():
                    if attrib=="translit": translit = value
                    elif attrib=="unicode": greek = value
                    elif attrib=="BETA": beta = value
                    else: logging.warning( "scs4 Unprocessed {!r} attribute ({}) in {}".format( attrib, value, location ) )
                if BibleOrgSysGlobals.debugFlag: assert greek and translit and beta
                if 'word' not in entryResults: # This is the first/main entry
                    if BibleOrgSysGlobals.debugFlag: assert gettingEssentials and j==1
                    BibleOrgSysGlobals.checkXMLNoTail( element, location, "ks24" )
                    entryResults['word'] = (greek, translit, beta)
                else:
                    #print( "Have multiple greek entries in " + strongs5 )
                    if BibleOrgSysGlobals.debugFlag: assert j > 2
                    gettingEssentials = False
                    entryString += ' ' + BibleOrgSysGlobals.getFlattenedXML( element, strongs5 ) #.replace( '\n', '' )
            elif element.tag == "pronunciation":
                location = "pronunciation in Strongs " + strongs5
                BibleOrgSysGlobals.checkXMLNoText( element, location, "iw9k" )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, location, "0s20" )
                # Process the attributes
                pronunciation = None
                for attrib,value in element.items():
                    if attrib=="strongs": pronunciation = value
                    else: logging.warning( "scs4 Unprocessed {!r} attribute ({}) in {}".format( attrib, value, location ) )
                if gettingEssentials:
                    #BibleOrgSysGlobals.checkXMLNoTail( element, location, "kd02" )
                    if BibleOrgSysGlobals.debugFlag:
                        assert j == 2
                        assert pronunciation
                        assert 'pronunciation' not in entryResults
                    entryResults['pronunciation'] = pronunciation
                else:
                    if BibleOrgSysGlobals.debugFlag: assert j>2 and not gettingEssentials
                    if element.tail and element.tail.strip(): entryString += element.tail.strip().replace( '\n', '' )
            elif element.tag == "strongs_derivation":
                location = "strongs_derivation in Strongs " + strongs5
                BibleOrgSysGlobals.checkXMLNoAttributes( element, location, "jke0" )
                BibleOrgSysGlobals.checkXMLNoTail( element, location, "ks24" )
                derivation = BibleOrgSysGlobals.getFlattenedXML( element, strongs5 ).replace( '\n', '' )
                #print( strongs5, "derivation", repr(derivation) )
                if BibleOrgSysGlobals.debugFlag:
                    assert derivation and '\t' not in derivation and '\n' not in derivation
                entryString +=  derivation
            elif element.tag == "strongs_def":
                location = "strongs_def in Strongs " + strongs5
                BibleOrgSysGlobals.checkXMLNoAttributes( element, location, "jke0" )
                BibleOrgSysGlobals.checkXMLNoTail( element, location, "jd28" )
                definition = BibleOrgSysGlobals.getFlattenedXML( element, strongs5 ).replace( '\n', '' )
                #print( strongs5, "definition", repr(definition) )
                if BibleOrgSysGlobals.debugFlag:
                    assert definition and '\t' not in definition and '\n' not in definition
                entryString += definition
            elif element.tag == "kjv_def":
                location = "kjv_def in Strongs " + strongs5
                BibleOrgSysGlobals.checkXMLNoAttributes( element, location, "jke0" )
                #BibleOrgSysGlobals.checkXMLNoTail( element, location, "8s2s" )
                #BibleOrgSysGlobals.checkXMLNoSubelements( element, location, "dvb2" )
                KJVdefinition = BibleOrgSysGlobals.getFlattenedXML( element, strongs5 ).replace( '\n', '' )
                #print( strongs5, "KJVdefinition", repr(KJVdefinition), repr(entryString) )
                if BibleOrgSysGlobals.debugFlag: assert KJVdefinition and '\t' not in KJVdefinition and '\n' not in KJVdefinition
                entryString += KJVdefinition
            elif element.tag == "strongsref":
                location = "strongsref in Strongs " + strongs5
                BibleOrgSysGlobals.checkXMLNoText( element, location, "kls2" )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, location, "ks24" )
                strongsRef = BibleOrgSysGlobals.getFlattenedXML( element, strongs5 ).replace( '\n', '' )
                if BibleOrgSysGlobals.debugFlag:
                    assert strongsRef and '\t' not in strongsRef and '\n' not in strongsRef
                strongsRef = re.sub( '<language="GREEK" strongs="(\d{1,5})">', r'<StrongsRef>G\1</StrongsRef>', strongsRef )
                strongsRef = re.sub( '<strongs="(\d{1,5})" language="GREEK">', r'<StrongsRef>G\1</StrongsRef>', strongsRef )
                #strongsRef = re.sub( '<language="HEBREW" strongs="(\d{1,5})">', r'<StrongsRef>H\1</StrongsRef>', strongsRef )
                #strongsRef = re.sub( '<strongs="(\d{1,5})" language="HEBREW">', r'<StrongsRef>H\1</StrongsRef>', strongsRef )
                #print( strongs5, "strongsRef", repr(strongsRef) )
                entryString += ' ' + strongsRef
            elif element.tag == "see":
                location = "see in Strongs " + strongs5
                BibleOrgSysGlobals.checkXMLNoText( element, location, "iw9k" )
                BibleOrgSysGlobals.checkXMLNoTail( element, location, "kd02" )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, location, "0s20" )
                # Process the attributes
                seeLanguage = seeStrongsNumber = None
                for attrib,value in element.items():
                    if attrib == "language": seeLanguage = value
                    elif attrib == "strongs": seeStrongsNumber = value # Note: No leading zeroes here
                    else: logging.warning( "scs4 Unprocessed {!r} attribute ({}) in {}".format( attrib, value, location ) )
                if BibleOrgSysGlobals.debugFlag:
                    assert seeLanguage and seeStrongsNumber and seeStrongsNumber.isdigit()
                    assert seeLanguage in ('GREEK','HEBREW',)
                if 'see' not in entryResults: entryResults['see'] = []
                entryResults['see'].append( ('G' if seeLanguage=='GREEK' else 'H') + seeStrongsNumber )
            else: logging.error( "2d4f Unprocessed {!r} element ({}) in entry".format( element.tag, element.text ) )

        if entryString:
            #print( strongs5, "entryString", repr(entryString) )
            if BibleOrgSysGlobals.debugFlag:
                assert '\t' not in entryString and '\n' not in entryString
            entryString = re.sub( '<strongsref language="GREEK" strongs="(\d{1,5})"></strongsref>',
                                r'<StrongsRef>G\1</StrongsRef>', entryString )
            entryString = re.sub( '<strongsref strongs="(\d{1,5})" language="GREEK"></strongsref>',
                                r'<StrongsRef>G\1</StrongsRef>', entryString )
            entryString = re.sub( '<strongsref language="HEBREW" strongs="(\d{1,5})"></strongsref>',
                                r'<StrongsRef>H\1</StrongsRef>', entryString )
            entryString = re.sub( '<strongsref strongs="(\d{1,5})" language="HEBREW"></strongsref>',
                                r'<StrongsRef>H\1</StrongsRef>', entryString )
            if BibleOrgSysGlobals.debugFlag:
                assert 'strongsref' not in entryString
            entryResults['Entry'] = entryString
        #print( "entryResults", entryResults )
        self.StrongsEntries[strongs] = entryResults
    # end of GreekStrongsFileConverter.validateEntry


    def importDataToPython( self ):
        """
        Loads (and pivots) the data (not including the header) into suitable Python containers to use in a Python program.
        (Of course, you can just use the elementTree in self.XMLTree if you prefer.)
        """
        if BibleOrgSysGlobals.debugFlag:
            assert len( self.XMLTree )
            assert self.StrongsEntries
        return self.StrongsEntries # temp…… XXXXXXXXXXXXXXXXXXXXXXXXXXXXX…
    # end of GreekStrongsFileConverter.importDataToPython
# end of GreekStrongsFileConverter class




class GreekLexicon:
    """
    Class for handling an Greek Lexicon

    This class doesn't deal at all with XML, only with Python dictionaries, etc.
    """
    def __init__( self, XMLFolder, preload=False ):
        """
        Constructor: expects the filepath of the source XML file.
        Loads (and crudely validates the XML file) into an element tree.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( t("GreekLexicon.__init__( {} )").format( XMLFolder ) )
        self.XMLFolder = XMLFolder
        self.StrongsEntries = None
        if preload: self.load()
    # end of GreekLexicon.__init__


    def load( self ):
        """
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( t("GreekLexicon.load()") )
        assert self.StrongsEntries is None
        gStr = GreekStrongsFileConverter() # Create the empty object
        gStr.loadAndValidate( self.XMLFolder ) # Load the XML
        self.StrongsEntries = gStr.importDataToPython()
    # end of GreekLexicon.load


    def __str__( self ):
        """
        This method returns the string representation of the GreekLexicon object.

        @return: the name of the object formatted as a string
        @rtype: string
        """
        result = "Greek Strongs Lexicon object"
        #if self.title: result += ('\n' if result else '') + self.title
        #if self.version: result += ('\n' if result else '') + "Version: {} ".format( self.version )
        #if self.date: result += ('\n' if result else '') + "Date: {}".format( self.date )
        if self.StrongsEntries is not None:
            result += ('\n' if result else '') + "  " + _("Number of Strong's Greek entries = {}").format( len(self.StrongsEntries) )
        return result
    # end of GreekLexicon.__str__


    def getStrongsEntryData( self, key ):
        """
        The key is a Greek Strong's number (string) like 'G1979'.

        Returns an entry for the given key.
            This is a dictionary containing fields, e.g., ['usage'] = 'company, going, walk, way.'

        Returns None if the key is not found.
        """
        if BibleOrgSysGlobals.debugFlag: assert key and key[0]=='G' and key[1:].isdigit()
        keyDigits = key[1:]
        if self.StrongsEntries is None: self.load()
        if keyDigits in self.StrongsEntries: return self.StrongsEntries[keyDigits]
    # end of GreekLexicon.getStrongsEntryData


    def getStrongsEntryField( self, key, fieldName ):
        """
        The key is a Greek Strong's number (string) like 'G1979'.
        The fieldName is a name (string) like 'usage'.

        Returns a string for the given key and fieldName names.
        Returns None if the key or fieldName is not found.
        """
        if BibleOrgSysGlobals.debugFlag: assert key and key[0]=='G' and key[1:].isdigit()
        keyDigits = key[1:]
        if self.StrongsEntries is None: self.load()
        if keyDigits in self.StrongsEntries:
            #for f,d in self.StrongsEntries[keyDigits]:
                #if f==fieldName: return d
            if fieldName in self.StrongsEntries[keyDigits]: return self.StrongsEntries[keyDigits][fieldName]
    # end of GreekLexicon.getStrongsEntryField


    def getStrongsEntryHTML( self, key ):
        """
        The key is a Greek Strong's number (string) like 'G1979'.

        Returns an HTML li entry for the given key.
        Returns None if the key is not found.

        e.g., for G1, returns:
            <li value="1" id="nt:1">
            <span class="originalWord" title="{A}" xml:lang="grk">Α</span>
                of Hebrew origin; the first letter of the alphabet; figuratively, only (from its use as a numeral) the first:
                --Alpha. Often used (usually <translit="án" unicode="ἄν" BETA="A)/N">,
                before a vowel) also in composition (as a contraction from <span class="StrongsRef">G427</span> )
                in the sense of privation; so, in many words, beginning with this letter;
                occasionally in the sense of union (as a contraction of <span class="StrongsRef">G260</span> ).
            </li>
        """
        if BibleOrgSysGlobals.debugFlag: assert key and key[0]=='G' and key[1:].isdigit()
        keyDigits = key[1:]
        while len(keyDigits)>1 and keyDigits[0]=='0': keyDigits = keyDigits[1:] # Remove leading zeroes
        if self.StrongsEntries is None: self.load()
        if keyDigits in self.StrongsEntries:
            entry = self.StrongsEntries[keyDigits]
            wordEntry = '{}'.format( entry['Entry'].replace('<StrongsRef>','<span class="StrongsRef">').replace('</StrongsRef>','</span>').replace('<def>','<span class="def">').replace('</def>','</span>') ) \
                        if 'Entry' in entry else ''
            html = '<span class="GreekWord" title="{{{}}}" xml:lang="grk">{}</span> {}' \
                .format( keyDigits, keyDigits, entry['word'][1], entry['word'][0], wordEntry )
            return html
    # end of GreekLexicon.getStrongsEntryHTML
# end of GreekLexicon class




def demo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( programNameVersion )

    testFolder = BibleOrgSysGlobals.PARALLEL_RESOURCES_BASE_FOLDERPATH.joinpath( '../../ExternalPrograms/morphgnt/strongs-dictionary-xml/' ) # Greek lexicon folder


    if 1: # demonstrate the Greek Lexicon converter classes
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nDemonstrating the converter classes…" )

        print()
        gsc = GreekStrongsFileConverter()
        gsc.loadAndValidate( testFolder ) # Load the XML
        print( gsc ) # Just print a summary

        if BibleOrgSysGlobals.commandLineArguments.export:
            print( "Exports aren't written yet!" )
            #hlc.exportDataToPython() # Produce the .py tables
            #hlc.exportDataToC() # Produce the .h tables
            halt


    if 1: # demonstrate the Greek Lexicon class
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nDemonstrating the Greek Lexicon class…" )
        hl = GreekLexicon( testFolder ) # Load and process the XML
        print( hl ) # Just print a summary
        print()
        for strongsKey in ('G1','G123','G165','G1732','G1979','G2011','G5624','G5625',): # Last one is invalid
            print( '\n' + strongsKey )
            print( " Data:", hl.getStrongsEntryData( strongsKey ) )
            print( " Pronunciation:", hl.getStrongsEntryField( strongsKey, 'pronunciation' ) )
            print( " HTML:", hl.getStrongsEntryHTML( strongsKey ) )
# end of demo

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    demo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of GreekLexicon.py
