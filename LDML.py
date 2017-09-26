#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# LDML.py
#
# Module handling Unicode LOCALE DATA MARKUP LANGUAGE (XML) files
#
# Copyright (C) 2017 Robert Hunt
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
Module handling / reading Unicode LDML XML files.
    LDML = Locale Data Markup Language (see http://unicode.org/reports/tr35/tr35-4.html)

The XML data file is loaded into a Python dictionary and made available in
    that form.

This module (and most of the Bible Organisational System / BOS modules that
    load XML files) do it quite manually and quite pedantically. Although
    this makes what could be simple code quite long, it does allow us to
    be alerted if/when the file format (which we have no control over) is
    modified or extended.

The module is tested on LDML files from the SIL NRSI Github repository
    at https://github.com/silnrsi
"""

from gettext import gettext as _

LastModifiedDate = '2017-09-26' # by RJH
ShortProgName = "LDML_Handler"
ProgName = "Unicode LOCALE DATA MARKUP LANGUAGE handler"
ProgVersion = '0.02'
ProgNameVersion = '{} v{}'.format( ShortProgName, ProgVersion )
ProgNameVersionDate = '{} {} {}'.format( ProgNameVersion, _("last modified"), LastModifiedDate )

debuggingThisModule = False


import sys, os, logging
from collections import OrderedDict
import multiprocessing
from xml.etree.ElementTree import ElementTree

import BibleOrgSysGlobals



def exp( messageString ):
    """
    Expands the message string in debug mode.
    Prepends the module name to a error or warning message string
        if we are in debug mode.
    Returns the new string.
    """
    try: nameBit, errorBit = messageString.split( ': ', 1 )
    except ValueError: nameBit, errorBit = '', messageString
    if BibleOrgSysGlobals.debugFlag or debuggingThisModule:
        nameBit = '{}{}{}'.format( ShortProgName, '.' if nameBit else '', nameBit )
    return '{}{}'.format( nameBit+': ' if nameBit else '', errorBit )
# end of exp



def getFlagFromAttribute( attributeName, attributeValue ):
    """
    Get a 'true' or 'false' string and convert to True/False.
    """
    if attributeValue == 'true': return True
    if attributeValue == 'false': return False
    logging.error( _("Unexpected {} attribute value of {}").format( attributeName, attributeValue ) )
    return attributeValue
# end of getFlagFromAttribute

def getFlagFromText( subelement ):
    """
    Get a 'true' or 'false' string and convert to True/False.
    """
    if subelement.text == 'true': return True
    if subelement.text == 'false': return False
    logging.error( _("Unexpected {} text value of {}").format( subelement.tag, subelement.text ) )
    return subelement.text
# end of getFlagFromText



class LDMLFile:
    """
    A class to load and validate the XML Unicode LOCALE DATA MARKUP LANGUAGE files.
    """
    def __init__( self, givenFolderName, givenFilename ):
        """
        """
        assert givenFolderName
        assert givenFilename
        assert givenFilename.endswith( '.ldml' ) or givenFilename.endswith( '.xml' )

        self.givenFolderName, self.givenFilename = givenFolderName, givenFilename
        self.filepath = os.path.join( givenFolderName, givenFilename )
        self.languageCode = givenFilename[:-5] # Remove the .ldml
    # end of LDMLFile.__init__


    def load( self ):
        """
        Load the something.ldml file (which is an LDML file) and parse it into the dictionary PTXLanguages.

        LDML = Locale Data Markup Language (see http://unicode.org/reports/tr35/tr35-4.html)
        """
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
            print( exp("load()") )

        urnPrefix = '{urn://www.sil.org/ldml/0.1}'
        lenUrnPrefix = len( urnPrefix )
        def removeSILPrefix( someText ):
            """
            Remove the SIL URN which might be prefixed to the element tag.
            """
            if someText and someText.startswith( urnPrefix ): return someText[lenUrnPrefix:]
            return someText
        # end of removeSILPrefix


        # Main code for LDMLFile.load()
        if BibleOrgSysGlobals.verbosityLevel > 0:
            print( "    Loading LOCALE DATA MARKUP LANGUAGE (LDML) file from {}…".format( self.filepath ) )

        LDMLData = OrderedDict()

        languageTree = ElementTree().parse( self.filepath )
        assert len( languageTree ) # Fail here if we didn't load anything at all

        # Find the main container
        if languageTree.tag=='ldml':
            treeLocation = "PTX8 {} file for {}".format( languageTree.tag, self.languageCode )
            BibleOrgSysGlobals.checkXMLNoAttributes( languageTree, treeLocation )
            BibleOrgSysGlobals.checkXMLNoText( languageTree, treeLocation )
            BibleOrgSysGlobals.checkXMLNoTail( languageTree, treeLocation )

            identity = OrderedDict()
            characters = OrderedDict()
            delimiters = OrderedDict()
            layout = OrderedDict()
            numbers = OrderedDict()
            collations = OrderedDict()
            localeDisplayNames = OrderedDict()
            dates = OrderedDict()
            special = OrderedDict()

            # Now process the actual entries
            for element in languageTree:
                elementLocation = element.tag + ' in ' + treeLocation
                #if debuggingThisModule: print( "  Processing1 {} ({})…".format( elementLocation, element.text.strip() ) )
                BibleOrgSysGlobals.checkXMLNoAttributes( element, elementLocation )
                BibleOrgSysGlobals.checkXMLNoText( element, elementLocation )
                BibleOrgSysGlobals.checkXMLNoTail( element, elementLocation )
                assert element.tag not in LDMLData

                if element.tag == 'identity':
                    for subelement in element:
                        subelementLocation = subelement.tag + ' in ' + elementLocation
                        #if debuggingThisModule: print( "    Processing {}…".format( subelementLocation ) )
                        BibleOrgSysGlobals.checkXMLNoText( subelement, subelementLocation )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, subelementLocation )
                        if subelement.tag == 'version':
                            BibleOrgSysGlobals.checkXMLNoSubelements( subelement, subelementLocation )
                            number = None
                            for attrib,value in subelement.items():
                                if attrib=='number': number = value
                                else:
                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, subelementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                            assert subelement.tag not in identity
                            identity[subelement.tag] = number
                        elif subelement.tag == 'generation':
                            BibleOrgSysGlobals.checkXMLNoSubelements( subelement, subelementLocation )
                            date = None
                            for attrib,value in subelement.items():
                                if attrib=='date': date = value
                                else:
                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, subelementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                            assert subelement.tag not in identity
                            identity[subelement.tag] = date
                        elif subelement.tag in ('language','territory'):
                            BibleOrgSysGlobals.checkXMLNoSubelements( subelement, subelementLocation )
                            lgType = None
                            for attrib,value in subelement.items():
                                if attrib=='type': lgType = value
                                else:
                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, subelementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                            assert subelement.tag not in identity
                            identity[subelement.tag] = lgType
                        elif subelement.tag == 'special':
                            BibleOrgSysGlobals.checkXMLNoAttributes( subelement, subelementLocation )
                            for sub2element in subelement:
                                sub2elementLocation = sub2element.tag + ' in ' + subelementLocation
                                #if debuggingThisModule: print( "      Processing {}…".format( sub2elementLocation ) )
                                BibleOrgSysGlobals.checkXMLNoText( sub2element, sub2elementLocation )
                                BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2elementLocation )
                                BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2elementLocation )
                                windowsLCID = draft = source = None
                                for attrib,value in sub2element.items():
                                    if attrib=='windowsLCID': windowsLCID = value
                                    elif attrib=='draft': draft = value
                                    elif attrib=='source': source = value
                                    else:
                                        logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub2elementLocation ) )
                                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                assert subelement.tag not in identity
                                identity[subelement.tag] = {'tag':sub2element.tag,'windowsLCID':windowsLCID,'draft':draft,'source':source}
                        else:
                            logging.error( _("Unprocessed {} subelement in {}").format( subelement.tag, subelementLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    if identity:
                        #print( "identity", identity )
                        assert element.tag not in LDMLData
                        LDMLData[element.tag] = identity

                elif element.tag == 'characters':
                    for subelement in element:
                        subelementLocation = subelement.tag + ' in ' + elementLocation
                        #if debuggingThisModule: print( "    Processing {}…".format( subelementLocation ) )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, subelementLocation )
                        if subelement.tag == 'exemplarCharacters':
                            BibleOrgSysGlobals.checkXMLNoSubelements( subelement, subelementLocation )
                            ecType = None
                            for attrib,value in subelement.items():
                                if attrib=='type': ecType = value
                                else:
                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, subelementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                            if subelement.tag not in characters:
                                characters[subelement.tag] = []
                            characters[subelement.tag].append( (ecType,subelement.text) )
                        elif subelement.tag == 'special':
                            BibleOrgSysGlobals.checkXMLNoAttributes( subelement, subelementLocation )
                            BibleOrgSysGlobals.checkXMLNoText( subelement, subelementLocation )
                            assert subelement.tag not in characters
                            characters[subelement.tag] = {}
                            for sub2element in subelement:
                                sub2elementLocation = sub2element.tag + ' in ' + subelementLocation
                                #if debuggingThisModule: print( "      Processing {}…".format( sub2elementLocation ) )
                                BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2elementLocation )
                                BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2elementLocation )
                                secType = None
                                for attrib,value in sub2element.items():
                                    if attrib=='type': secType = value
                                    else:
                                        logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub2elementLocation ) )
                                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                if sub2element.tag not in characters[subelement.tag]:
                                    characters[subelement.tag][sub2element.tag] = []
                                characters[subelement.tag][sub2element.tag].append( (secType,sub2element.text) )
                        else:
                            logging.error( _("Unprocessed {} subelement in {}").format( subelement.tag, subelementLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    if characters:
                        #print( "characters", characters )
                        assert element.tag not in LDMLData
                        LDMLData[element.tag] = characters

                elif element.tag == 'delimiters':
                    for subelement in element:
                        subelementLocation = subelement.tag + ' in ' + elementLocation
                        #if debuggingThisModule: print( "    Processing {}…".format( subelementLocation ) )
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, subelementLocation )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, subelementLocation )
                        if subelement.tag in ('quotationStart','quotationEnd','alternateQuotationStart','alternateQuotationEnd',):
                            BibleOrgSysGlobals.checkXMLNoSubelements( subelement, subelementLocation )
                            assert subelement.tag not in delimiters
                            delimiters[subelement.tag] = subelement.text
                        elif subelement.tag == 'special':
                            BibleOrgSysGlobals.checkXMLNoText( subelement, subelementLocation )
                            assert subelement.tag not in delimiters
                            delimiters[subelement.tag] = OrderedDict()
                            for sub2element in subelement:
                                sub2elementLocation = sub2element.tag + ' in ' + subelementLocation
                                adjusted2Tag = removeSILPrefix( sub2element.tag )
                                #if debuggingThisModule: print( "      Processing {}…".format( sub2elementLocation ) )
                                BibleOrgSysGlobals.checkXMLNoText( sub2element, sub2elementLocation )
                                BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2elementLocation )
                                if adjusted2Tag not in delimiters:
                                    delimiters[subelement.tag][adjusted2Tag] = {}
                                paraContinueType = None
                                for attrib,value in sub2element.items():
                                    #print( "here9", attrib, value )
                                    if attrib=='paraContinueType': paraContinueType = value
                                    else:
                                        logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub2elementLocation ) )
                                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                for sub3element in sub2element:
                                    sub3elementLocation = sub3element.tag + ' in ' + sub2elementLocation
                                    adjusted3Tag = removeSILPrefix( sub3element.tag )
                                    #if debuggingThisModule: print( "        Processing {}…".format( sub3elementLocation ) )
                                    #BibleOrgSysGlobals.checkXMLNoText( sub3element, sub3elementLocation, "ABC" )
                                    BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3elementLocation )
                                    BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3elementLocation )
                                    openA = close = level = paraClose = pattern = context = qContinue = qType = None
                                    for attrib,value in sub3element.items():
                                        #print( attrib, value )
                                        if attrib=='open': openA = value
                                        elif attrib=='close': close = value
                                        elif attrib=='level':
                                            level = value
                                            if debuggingThisModule: assert level in '123'
                                        elif attrib=='paraClose':
                                            paraClose = value
                                            if debuggingThisModule: assert paraClose in ('false',)
                                        elif attrib=='pattern': pattern = value
                                        elif attrib=='context':
                                            context = value
                                            if debuggingThisModule: assert context in ('medial','final',)
                                        elif attrib=='continue':
                                            qContinue = value
                                        elif attrib=='type':
                                            qType = value
                                        else:
                                            logging.error( _("DS Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub3elementLocation ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                    if adjusted3Tag not in delimiters[subelement.tag][adjusted2Tag]:
                                        delimiters[subelement.tag][adjusted2Tag][adjusted3Tag] = []
                                    delimiters[subelement.tag][adjusted2Tag][adjusted3Tag] \
                                            .append( (openA,close,level,paraClose,pattern,context,paraContinueType,qContinue,qType,sub3element.text) )
                        else:
                            logging.error( _("Unprocessed {} subelement in {}").format( subelement.tag, subelementLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    #print( '\n', element.tag, LDMLData[element.tag] )
                    if delimiters:
                        #print( "delimiters", delimiters )
                        assert element.tag not in LDMLData
                        LDMLData[element.tag] = delimiters

                elif element.tag == 'layout':
                    for subelement in element:
                        subelementLocation = subelement.tag + ' in ' + elementLocation
                        #if debuggingThisModule: print( "    Processing {}…".format( subelementLocation ) )
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, subelementLocation )
                        BibleOrgSysGlobals.checkXMLNoText( subelement, subelementLocation )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, subelementLocation )
                        if subelement.tag == 'orientation':
                            assert subelement.tag not in layout
                            layout[subelement.tag] = {}
                            for sub2element in subelement:
                                sub2elementLocation = sub2element.tag + ' in ' + subelementLocation
                                #if debuggingThisModule: print( "      Processing {}…".format( sub2elementLocation ) )
                                BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, sub2elementLocation )
                                BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2elementLocation )
                                BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2elementLocation )
                                assert sub2element.tag not in layout[subelement.tag]
                                layout[subelement.tag][sub2element.tag] = sub2element.text
                        else:
                            logging.error( _("Unprocessed {} subelement in {}").format( subelement.tag, subelementLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    if layout:
                        #print( "layout", layout )
                        assert element.tag not in LDMLData
                        LDMLData[element.tag] = layout

                elif element.tag == 'numbers':
                    numbers = {}
                    for subelement in element:
                        subelementLocation = subelement.tag + ' in ' + elementLocation
                        #if debuggingThisModule: print( "    Processing {}…".format( subelementLocation ) )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, subelementLocation )
                        if subelement.tag == 'defaultNumberingSystem':
                            BibleOrgSysGlobals.checkXMLNoAttributes( subelement, subelementLocation )
                            assert subelement.tag not in numbers
                            numbers[subelement.tag]  = subelement.text
                        elif subelement.tag == 'numberingSystem':
                            BibleOrgSysGlobals.checkXMLNoText( subelement, subelementLocation )
                            nID = digits = nType = None
                            for attrib,value in subelement.items():
                                if attrib=='id': nID = value
                                elif attrib=='digits': digits = value
                                elif attrib=='type': nType = value
                                else:
                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, subelementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                            assert subelement.tag not in numbers
                            numbers[subelement.tag] = (nID,digits,nType)
                        elif subelement.tag == 'symbols':
                            symbols = {}
                            BibleOrgSysGlobals.checkXMLNoText( subelement, subelementLocation )
                            BibleOrgSysGlobals.checkXMLNoTail( subelement, subelementLocation )
                            numberSystem = None
                            for attrib,value in subelement.items():
                                if attrib=='numberSystem': numberSystem = value
                                else:
                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, subelementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                            if numberSystem not in symbols:
                                symbols[numberSystem] = {}
                            for sub2element in subelement:
                                sub2elementLocation = sub2element.tag + ' in ' + subelementLocation
                                #if debuggingThisModule: print( "      Processing {} ({})…".format( sub2elementLocation, sub2element.tag.strip() ) )
                                BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, sub2elementLocation, "DGD361" )
                                BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2elementLocation )
                                BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2elementLocation )
                                if sub2element.tag not in symbols[numberSystem]:
                                    symbols[numberSystem][sub2element.tag] = sub2element.text
                            if symbols:
                                #print( "symbols", symbols )
                                assert subelement.tag not in numbers
                                numbers[subelement.tag] = symbols
                        elif subelement.tag == 'currencyFormats':
                            currencyFormats = {}
                            BibleOrgSysGlobals.checkXMLNoText( subelement, subelementLocation )
                            BibleOrgSysGlobals.checkXMLNoTail( subelement, subelementLocation )
                            numberSystem = None
                            for attrib,value in subelement.items():
                                if attrib=='numberSystem': numberSystem = value
                                else:
                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, subelementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                            if numberSystem not in currencyFormats:
                                currencyFormats[numberSystem] = {}
                            for sub2element in subelement:
                                sub2elementLocation = sub2element.tag + ' in ' + subelementLocation
                                #if debuggingThisModule: print( "      Processing {} ({})…".format( sub2elementLocation, sub2element.tag.strip() ) )
                                BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, sub2elementLocation, "DGD461" )
                                BibleOrgSysGlobals.checkXMLNoText( sub2element, sub2elementLocation )
                                BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2elementLocation )
                                #if sub2element.tag not in currencyFormats[numberSystem]:
                                    #currencyFormats[numberSystem][sub2element.tag] = sub2element.text
                                if sub2element.tag == 'currencyFormatLength':
                                    for sub3element in sub2element:
                                        sub3elementLocation = sub3element.tag + ' in ' + sub2elementLocation
                                        #if debuggingThisModule: print( "        Processing {} ({})…".format( sub3elementLocation, sub3element.text.strip() ) )
                                        BibleOrgSysGlobals.checkXMLNoText( sub3element, sub3elementLocation )
                                        BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3elementLocation )
                                        if sub3element.tag == 'currencyFormat':
                                            draft = cfType = alt = None
                                            for attrib,value in sub3element.items():
                                                #if attrib=='draft': draft = value
                                                if attrib=='type': cfType = value
                                                #elif attrib=='alt': alt = value
                                                else:
                                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub3elementLocation ) )
                                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                            for sub4element in sub3element:
                                                sub4elementLocation = sub4element.tag + ' in ' + sub3elementLocation
                                                #if debuggingThisModule: print( "          Processing {} ({})…".format( sub4elementLocation, sub4element.text.strip() ) )
                                                BibleOrgSysGlobals.checkXMLNoAttributes( sub4element, sub4elementLocation )
                                                BibleOrgSysGlobals.checkXMLNoSubelements( sub4element, sub4elementLocation )
                                                BibleOrgSysGlobals.checkXMLNoTail( sub4element, sub4elementLocation )
                                        else:
                                            logging.error( _("Unprocessed {} sub3element in {}").format( sub3element.tag, sub3elementLocation ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                else:
                                    logging.error( _("Unprocessed {} sub2element in {}").format( sub2element.tag, sub2elementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                            if currencyFormats:
                                #print( "currencyFormats", currencyFormats )
                                assert subelement.tag not in numbers
                                numbers[subelement.tag] = currencyFormats
                        elif subelement.tag == 'currencies':
                            currencies = {}
                            BibleOrgSysGlobals.checkXMLNoAttributes( subelement, subelementLocation )
                            BibleOrgSysGlobals.checkXMLNoText( subelement, subelementLocation )
                            BibleOrgSysGlobals.checkXMLNoTail( subelement, subelementLocation )
                            for sub2element in subelement:
                                sub2elementLocation = sub2element.tag + ' in ' + subelementLocation
                                #if debuggingThisModule: print( "      Processing {} ({})…".format( sub2elementLocation, sub2element.text.strip() ) )
                                BibleOrgSysGlobals.checkXMLNoText( sub2element, sub2elementLocation )
                                BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2elementLocation )
                                if sub2element.tag == 'currency':
                                    cuType = None
                                    for attrib,value in sub2element.items():
                                        #print( "here9", attrib, value )
                                        if attrib=='type': cuType = value
                                        else:
                                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub2elementLocation ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                    assert cuType not in currencies
                                    currencies[cuType] = {}
                                    for sub3element in sub2element:
                                        sub3elementLocation = sub3element.tag + ' in ' + sub2elementLocation
                                        #if debuggingThisModule: print( "        Processing {} ({})…".format( sub3elementLocation, sub3element.text.strip() ) )
                                        BibleOrgSysGlobals.checkXMLNoAttributes( sub3element, sub3elementLocation )
                                        BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3elementLocation )
                                        BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3elementLocation )
                                        assert sub3element.tag not in currencies[cuType]
                                        currencies[cuType][sub3element.tag]= sub3element.text
                                else:
                                    logging.error( _("Unprocessed {} sub2element in {}").format( sub2element.tag, sub2elementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                            if currencies:
                                #print( "currencies", currencies )
                                assert subelement.tag not in numbers
                                numbers[subelement.tag] = currencies
                        else:
                            logging.error( _("Unprocessed {} subelement in {}").format( subelement.tag, subelementLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                    if numbers:
                        #print( "numbers", numbers )
                        assert element.tag not in LDMLData
                        LDMLData[element.tag] = numbers

                elif element.tag == 'collations':
                    for subelement in element:
                        subelementLocation = subelement.tag + ' in ' + elementLocation
                        #if debuggingThisModule: print( "    Processing {}…".format( subelementLocation ) )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, subelementLocation )
                        if subelement.tag == 'defaultCollation':
                            BibleOrgSysGlobals.checkXMLNoAttributes( subelement, subelementLocation )
                            BibleOrgSysGlobals.checkXMLNoSubelements( subelement, subelementLocation )
                            assert subelement.tag not in collations
                            collations[subelement.tag]  = subelement.text
                        elif subelement.tag == 'collation':
                            BibleOrgSysGlobals.checkXMLNoText( subelement, subelementLocation )
                            assert subelement.tag not in collations
                            collations[subelement.tag] = {}
                            cType = None
                            for attrib,value in subelement.items():
                                if attrib=='type': cType = value
                                else:
                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, subelementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                            assert cType not in collations[subelement.tag]
                            collations[subelement.tag][cType] = {}
                            for sub2element in subelement:
                                sub2elementLocation = sub2element.tag + ' in ' + subelementLocation
                                #if debuggingThisModule: print( "      Processing {}…".format( sub2elementLocation ) )
                                BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, sub2elementLocation, "DGD561" )
                                BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2elementLocation )
                                if sub2element.tag not in collations[subelement.tag][cType]:
                                    collations[subelement.tag][cType][sub2element.tag] = {}
                                for sub3element in sub2element:
                                    sub3elementLocation = sub3element.tag + ' in ' + sub2elementLocation
                                    #if debuggingThisModule: print( "        Processing {}…".format( sub3elementLocation ) )
                                    BibleOrgSysGlobals.checkXMLNoAttributes( sub3element, sub3elementLocation, "DSD354" )
                                    BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3elementLocation )
                                    BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3elementLocation )
                                    if sub3element.tag not in collations[subelement.tag][cType][sub2element.tag]:
                                        collations[subelement.tag][cType][sub2element.tag][sub3element.tag] = []
                                    collations[subelement.tag][cType][sub2element.tag][sub3element.tag].append( sub3element.text )
                        else:
                            logging.error( _("Unprocessed {} subelement in {}").format( subelement.tag, subelementLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                    if collations:
                        #print( "collations", collations )
                        assert element.tag not in LDMLData
                        LDMLData[element.tag] = collations

                elif element.tag == 'localeDisplayNames':
                    languages = OrderedDict()
                    territories = OrderedDict()
                    for subelement in element:
                        subelementLocation = subelement.tag + ' in ' + elementLocation
                        #if debuggingThisModule: print( "    Processing2 {} ({})…".format( subelementLocation, subelement.text.strip() ) )
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, subelementLocation )
                        BibleOrgSysGlobals.checkXMLNoText( subelement, subelementLocation )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, subelementLocation )
                        if subelement.tag == 'languages':
                            languages = OrderedDict()
                            for sub2element in subelement:
                                sub2elementLocation = sub2element.tag + ' in ' + subelementLocation
                                #if debuggingThisModule: print( "      Processing3a {} ({})…".format( sub2elementLocation, sub2element.text.strip() ) )
                                BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2elementLocation )
                                BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2elementLocation )
                                if sub2element.tag == 'language':
                                    draft = lType = None
                                    for attrib,value in sub2element.items():
                                        #print( "here7", attrib, value )
                                        if attrib=='draft': draft = value
                                        elif attrib=='type': lType = value
                                        else:
                                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub2elementLocation ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                    assert lType not in languages
                                    languages[lType] = (lType,sub2element.text,draft)
                                else:
                                    logging.error( _("Unprocessed {} sub2element in {}").format( sub2element.tag, sub2elementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                            if languages:
                                assert subelement.tag not in localeDisplayNames
                                localeDisplayNames[subelement.tag] = languages
                        elif subelement.tag == 'territories':
                            for sub2element in subelement:
                                sub2elementLocation = sub2element.tag + ' in ' + subelementLocation
                                #if debuggingThisModule: print( "      Processing3b {} ({})…".format( sub2elementLocation, sub2element.text.strip() ) )
                                BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2elementLocation )
                                BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2elementLocation )
                                if sub2element.tag == 'territory':
                                    draft = tType = alt = None
                                    for attrib,value in sub2element.items():
                                        #print( "here8", attrib, value )
                                        if attrib=='draft': draft = value
                                        elif attrib=='type': tType = value
                                        elif attrib=='alt': alt = value
                                        else:
                                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub2elementLocation ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                    assert tType not in territories
                                    territories[tType] = (tType,sub2element.text,draft,alt)
                                else:
                                    logging.error( _("Unprocessed {} sub2element in {}").format( sub2element.tag, sub2elementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                            if territories:
                                assert subelement.tag not in localeDisplayNames
                                localeDisplayNames[subelement.tag] = territories
                        else:
                            logging.error( _("Unprocessed {} subelement in {}").format( subelement.tag, subelementLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                    if localeDisplayNames:
                        #print( "localeDisplayNames", localeDisplayNames )
                        assert element.tag not in LDMLData
                        LDMLData[element.tag] = localeDisplayNames

                elif element.tag == 'dates':
                    dates = OrderedDict()
                    calendars = OrderedDict()
                    fields = OrderedDict()
                    timeZoneNames = OrderedDict()
                    for subelement in element:
                        subelementLocation = subelement.tag + ' in ' + elementLocation
                        #if debuggingThisModule: print( "    Processing2 {} ({})…".format( subelementLocation, subelement.text.strip() ) )
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, subelementLocation )
                        BibleOrgSysGlobals.checkXMLNoText( subelement, subelementLocation )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, subelementLocation )
                        if subelement.tag == 'calendars':
                            for sub2element in subelement:
                                sub2elementLocation = sub2element.tag + ' in ' + subelementLocation
                                #if debuggingThisModule: print( "      Processing3a {} ({})…".format( sub2elementLocation, sub2element.text.strip() ) )
                                BibleOrgSysGlobals.checkXMLNoText( sub2element, sub2elementLocation )
                                BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2elementLocation )
                                if sub2element.tag == 'calendar':
                                    cType = None
                                    for attrib,value in sub2element.items():
                                        #print( "here7", attrib, value )
                                        #if attrib=='draft': draft = value
                                        if attrib=='type': cType = value
                                        else:
                                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub2elementLocation ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                    calendar = {}
                                    for sub3element in sub2element:
                                        sub3elementLocation = sub3element.tag + ' in ' + sub2elementLocation
                                        #if debuggingThisModule: print( "        ProcessingD3 {} ({})…".format( sub3elementLocation, sub3element.text.strip() ) )
                                        BibleOrgSysGlobals.checkXMLNoAttributes( sub3element, sub3elementLocation )
                                        BibleOrgSysGlobals.checkXMLNoText( sub3element, sub3elementLocation )
                                        BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3elementLocation )
                                        if sub3element.tag == 'dateTimeFormats':
                                            dateTimeFormats = OrderedDict()
                                            for sub4element in sub3element:
                                                sub4elementLocation = sub4element.tag + ' in ' + sub3elementLocation
                                                #if debuggingThisModule: print( "          ProcessingD4 {} ({})…".format( sub4elementLocation, sub4element.text.strip() ) )
                                                BibleOrgSysGlobals.checkXMLNoAttributes( sub4element, sub4elementLocation )
                                                BibleOrgSysGlobals.checkXMLNoText( sub4element, sub4elementLocation )
                                                BibleOrgSysGlobals.checkXMLNoTail( sub4element, sub4elementLocation )
                                                if sub4element.tag == 'intervalFormats':
                                                    for sub5element in sub4element:
                                                        sub5elementLocation = sub5element.tag + ' in ' + sub4elementLocation
                                                        #if debuggingThisModule: print( "            ProcessingD5 {} ({})…".format( sub5elementLocation, sub5element.text.strip() ) )
                                                        BibleOrgSysGlobals.checkXMLNoTail( sub5element, sub5elementLocation )
                                                        if sub5element.tag == 'intervalFormatFallback':
                                                            BibleOrgSysGlobals.checkXMLNoSubelements( sub5element, sub5elementLocation )
                                                            draft = None
                                                            for attrib,value in sub5element.items():
                                                                #print( "here7", attrib, value )
                                                                if attrib=='draft': draft = value
                                                                #if attrib=='type': cType = value
                                                                else:
                                                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub5elementLocation ) )
                                                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                                            pass # Save text XXXXXXXXXXXXXXX
                                                            for sub6element in sub5element:
                                                                sub6elementLocation = sub6element.tag + ' in ' + sub5elementLocation
                                                                #if debuggingThisModule: print( "              ProcessingD6 {} ({})…".format( sub6elementLocation, sub6element.text.strip() ) )
                                                                BibleOrgSysGlobals.checkXMLNoAttributes( sub6element, sub6elementLocation )
                                                                BibleOrgSysGlobals.checkXMLNoText( sub6element, sub6elementLocation )
                                                                BibleOrgSysGlobals.checkXMLNoSubelements( sub6element, sub6elementLocation )
                                                                BibleOrgSysGlobals.checkXMLNoTail( sub6element, sub6elementLocation )
                                                                if 1: pass
                                                                else:
                                                                    logging.error( _("Unprocessed {} sub6element in {}").format( sub6element.tag, sub6elementLocation ) )
                                                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                                        elif sub5element.tag == 'intervalFormatItem':
                                                            BibleOrgSysGlobals.checkXMLNoText( sub5element, sub5elementLocation )
                                                            ifiID = None
                                                            for attrib,value in sub5element.items():
                                                                #print( "here7", attrib, value )
                                                                if attrib=='id': ifiID = value
                                                                #if attrib=='type': cType = value
                                                                else:
                                                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub5elementLocation ) )
                                                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                                            pass # Save text XXXXXXXXXXXXXXX
                                                            for sub6element in sub5element:
                                                                sub6elementLocation = sub6element.tag + ' in ' + sub5elementLocation
                                                                #if debuggingThisModule: print( "              ProcessingD6 {} ({})…".format( sub6elementLocation, sub6element.text.strip() ) )
                                                                BibleOrgSysGlobals.checkXMLNoSubelements( sub6element, sub6elementLocation )
                                                                BibleOrgSysGlobals.checkXMLNoTail( sub6element, sub6elementLocation )
                                                                if 1: pass
                                                                else:
                                                                    logging.error( _("Unprocessed {} sub6element in {}").format( sub6element.tag, sub6elementLocation ) )
                                                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                                        else:
                                                            logging.error( _("Unprocessed {} sub5element in {}").format( sub5element.tag, sub5elementLocation ) )
                                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                                    dateTimeFormats[sub4element.tag] = sub4element.text
                                                else:
                                                    logging.error( _("Unprocessed {} sub4element in {}").format( sub4element.tag, sub4elementLocation ) )
                                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                        elif sub3element.tag == 'dayPeriods':
                                            dayPeriods = OrderedDict()
                                            for sub4element in sub3element:
                                                sub4elementLocation = sub4element.tag + ' in ' + sub3elementLocation
                                                #if debuggingThisModule: print( "          ProcessingD4 {} ({})…".format( sub4elementLocation, sub4element.text.strip() ) )
                                                BibleOrgSysGlobals.checkXMLNoText( sub4element, sub4elementLocation )
                                                BibleOrgSysGlobals.checkXMLNoTail( sub4element, sub4elementLocation )
                                                if sub4element.tag == 'dayPeriodContext':
                                                    for sub5element in sub4element:
                                                        sub5elementLocation = sub5element.tag + ' in ' + sub4elementLocation
                                                        #if debuggingThisModule: print( "            ProcessingD5 {} ({})…".format( sub5elementLocation, sub5element.text.strip() ) )
                                                        BibleOrgSysGlobals.checkXMLNoTail( sub5element, sub5elementLocation )
                                                        if sub5element.tag == 'dayPeriodWidth':
                                                            dpwType = None
                                                            for attrib,value in sub5element.items():
                                                                #print( "here7", attrib, value )
                                                                #if attrib=='draft': draft = value
                                                                if attrib=='type': dpwType = value
                                                                else:
                                                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub5elementLocation ) )
                                                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                                            pass # Save text XXXXXXXXXXXXXXX
                                                            for sub6element in sub5element:
                                                                sub6elementLocation = sub6element.tag + ' in ' + sub5elementLocation
                                                                #if debuggingThisModule: print( "              ProcessingD6 {} ({})…".format( sub6elementLocation, sub6element.text.strip() ) )
                                                                BibleOrgSysGlobals.checkXMLNoSubelements( sub6element, sub6elementLocation )
                                                                BibleOrgSysGlobals.checkXMLNoTail( sub6element, sub6elementLocation )
                                                                dpType = dpDraft = None
                                                                for attrib,value in sub6element.items():
                                                                    #print( "here7", attrib, value )
                                                                    if attrib=='type': dpType = value
                                                                    elif attrib=='draft': dpDraft = value
                                                                    else:
                                                                        logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub6elementLocation ) )
                                                                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                                                pass # Save text field XXXXXXXXXXXXXX
                                                                if 1: pass
                                                                else:
                                                                    logging.error( _("Unprocessed {} sub6element in {}").format( sub6element.tag, sub6elementLocation ) )
                                                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                                        elif sub5element.tag == 'intervalFormatItem':
                                                            BibleOrgSysGlobals.checkXMLNoText( sub5element, sub5elementLocation )
                                                            ifiID = None
                                                            for attrib,value in sub5element.items():
                                                                #print( "here7", attrib, value )
                                                                if attrib=='id': ifiID = value
                                                                #if attrib=='type': cType = value
                                                                else:
                                                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub5elementLocation ) )
                                                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                                            pass # Save text XXXXXXXXXXXXXXX
                                                            for sub6element in sub5element:
                                                                sub6elementLocation = sub6element.tag + ' in ' + sub5elementLocation
                                                                #if debuggingThisModule: print( "              ProcessingD6 {} ({})…".format( sub6elementLocation, sub6element.text.strip() ) )
                                                                BibleOrgSysGlobals.checkXMLNoSubelements( sub6element, sub6elementLocation )
                                                                BibleOrgSysGlobals.checkXMLNoTail( sub6element, sub6elementLocation )
                                                                if 1: pass
                                                                else:
                                                                    logging.error( _("Unprocessed {} sub6element in {}").format( sub6element.tag, sub6elementLocation ) )
                                                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                                        else:
                                                            logging.error( _("Unprocessed {} sub5element in {}").format( sub5element.tag, sub5elementLocation ) )
                                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                                    dayPeriods[sub4element.tag] = sub4element.text
                                                else:
                                                    logging.error( _("Unprocessed {} sub4element in {}").format( sub4element.tag, sub4elementLocation ) )
                                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                        else:
                                            logging.error( _("Unprocessed {} sub3element in {}").format( sub3element.tag, sub3elementLocation ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                else:
                                    logging.error( _("Unprocessed {} sub2element in {}").format( sub2element.tag, sub2elementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                            if dateTimeFormats:
                                assert 'dateTimeFormats' not in calendar
                                calendar['dateTimeFormats'] = dateTimeFormats
                            if dayPeriods:
                                assert 'dayPeriods' not in calendar
                                calendar['dayPeriods'] = dayPeriods
                            assert cType not in calendars
                            calendars[cType] = calendar
                            if calendars:
                                assert subelement.tag not in dates
                                dates[subelement.tag] = calendars
                        elif subelement.tag == 'fields':
                            for sub2element in subelement:
                                sub2elementLocation = sub2element.tag + ' in ' + subelementLocation
                                #if debuggingThisModule: print( "      Processing3b {} ({})…".format( sub2elementLocation, sub2element.text.strip() ) )
                                BibleOrgSysGlobals.checkXMLNoText( sub2element, sub2elementLocation )
                                BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2elementLocation )
                                if sub2element.tag == 'field':
                                    draft = fType = alt = None
                                    for attrib,value in sub2element.items():
                                        #print( "here8", attrib, value )
                                        #if attrib=='draft': draft = value
                                        if attrib=='type': fType = value
                                        #elif attrib=='alt': alt = value
                                        else:
                                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub2elementLocation ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                    for sub3element in sub2element:
                                        sub3elementLocation = sub3element.tag + ' in ' + sub2elementLocation
                                        #if debuggingThisModule: print( "        Processing {}…".format( sub3elementLocation ) )
                                        BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3elementLocation )
                                        BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3elementLocation )
                                        if sub3element.tag == 'displayName':
                                            draft = dnType = alt = None
                                            for attrib,value in sub3element.items():
                                                if attrib=='draft': draft = value
                                                #elif attrib=='type': dnType = value
                                                #elif attrib=='alt': alt = value
                                                else:
                                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub3elementLocation ) )
                                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                        else:
                                            logging.error( _("Unprocessed {} sub3element in {}").format( sub3element.tag, sub3elementLocation ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                    assert fType not in fields
                                    fields[fType] = (fType,sub2element.text,draft,alt)
                                else:
                                    logging.error( _("Unprocessed {} sub2element in {}").format( sub2element.tag, sub2elementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                            if fields:
                                assert subelement.tag not in dates
                                dates[subelement.tag] = fields
                        elif subelement.tag == 'timeZoneNames':
                            for sub2element in subelement:
                                sub2elementLocation = sub2element.tag + ' in ' + subelementLocation
                                #if debuggingThisModule: print( "      Processing3g {} ({})…".format( sub2elementLocation, sub2element.text.strip() ) )
                                BibleOrgSysGlobals.checkXMLNoText( sub2element, sub2elementLocation )
                                BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2elementLocation )
                                if sub2element.tag == 'metazone':
                                    dnType = None
                                    for attrib,value in sub2element.items():
                                        #print( "here58", attrib, value )
                                        if attrib=='type': dnType = value
                                        else:
                                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub2elementLocation ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                    metazone = {}
                                    for sub3element in sub2element:
                                        sub3elementLocation = sub3element.tag + ' in ' + sub2elementLocation
                                        #if debuggingThisModule: print( "        Processing8 {} ({})…".format( sub3elementLocation, sub3element.text.strip() ) )
                                        BibleOrgSysGlobals.checkXMLNoAttributes( sub3element, sub3elementLocation )
                                        BibleOrgSysGlobals.checkXMLNoText( sub3element, sub3elementLocation )
                                        BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3elementLocation )
                                        if sub3element.tag == 'short':
                                            if sub3element.tag not in metazone:
                                                metazone[sub3element.tag] = {}
                                            for sub4element in sub3element:
                                                sub4elementLocation = sub4element.tag + ' in ' + sub3elementLocation
                                                #if debuggingThisModule: print( "          Processing9 {} ({})…".format( sub4elementLocation, sub4element.text.strip() ) )
                                                BibleOrgSysGlobals.checkXMLNoAttributes( sub4element, sub4elementLocation )
                                                BibleOrgSysGlobals.checkXMLNoSubelements( sub4element, sub4elementLocation )
                                                BibleOrgSysGlobals.checkXMLNoTail( sub4element, sub4elementLocation )
                                                if sub4element.tag == 'standard':
                                                    metazone[sub3element.tag][sub4element.tag] = sub4element.text
                                                else:
                                                    logging.error( _("Unprocessed {} sub4element in {}").format( sub4element.tag, sub4elementLocation ) )
                                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                        else:
                                            logging.error( _("Unprocessed {} sub3element in {}").format( sub3element.tag, sub3elementLocation ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                    if metazone:
                                        assert sub2element.tag not in timeZoneNames
                                        timeZoneNames[sub2element.tag] = metazone
                                else:
                                    logging.error( _("Unprocessed {} sub2element in {}").format( sub2element.tag, sub2elementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                            if timeZoneNames:
                                assert subelement.tag not in dates
                                dates[subelement.tag] = timeZoneNames
                        else:
                            logging.error( _("Unprocessed {} subelement in {}").format( subelement.tag, subelementLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                    if dates:
                        #print( "dates", dates )
                        assert element.tag not in LDMLData
                        LDMLData[element.tag] = dates

                elif element.tag == 'special':
                    special = OrderedDict()
                    for subelement in element:
                        subelementLocation = subelement.tag + ' in ' + elementLocation
                        #if debuggingThisModule: print( "    Processing {}…".format( subelementLocation ) )
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, subelementLocation )
                        BibleOrgSysGlobals.checkXMLNoText( subelement, subelementLocation )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, subelementLocation )
                        assert subelement.tag not in special
                        if subelement.tag.endswith( 'external-resources' ):
                            adjustedTag = removeSILPrefix( subelement.tag )
                            special[adjustedTag] = {}
                            for sub2element in subelement:
                                sub2elementLocation = sub2element.tag + ' in ' + subelementLocation
                                #if debuggingThisModule: print( "      Processing {}…".format( sub2elementLocation ) )
                                BibleOrgSysGlobals.checkXMLNoText( sub2element, sub2elementLocation )
                                BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2elementLocation )
                                BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2elementLocation )
                                erName = erSize = None
                                for attrib,value in sub2element.items():
                                    #print( "here7", attrib, value )
                                    if attrib=='name': erName = value
                                    elif attrib=='size': erSize = value
                                    else:
                                        logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub2elementLocation ) )
                                        if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                assert erName
                                if sub2element.tag not in special[adjustedTag]:
                                    special[adjustedTag][sub2element.tag] = []
                                special[adjustedTag][sub2element.tag].append( (erName,erSize) )
                        else:
                            logging.error( _("Unprocessed {} subelement in {}").format( subelement.tag, subelementLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                    if special:
                        #print( "special", special )
                        assert element.tag not in LDMLData
                        LDMLData[element.tag] = special
                else:
                    logging.error( _("Unprocessed {} element in {}").format( element.tag, elementLocation ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
        else:
            logging.critical( _("Unrecognised PTX8 {} language settings tag: {}").format( self.languageCode, languageTree.tag ) )
            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt

        if BibleOrgSysGlobals.verbosityLevel > 2:
            print( "\n\nLDML data for {} ({}):".format( self.languageCode, len(LDMLData) ) )
            for key in LDMLData:
                #print( "\n      {}: ({}) {}".format( key, len(LDMLData[key]), LDMLData[key] ) )
                print( "\n      {} ({}):".format( key, len(LDMLData[key]) ) )
                for key2 in LDMLData[key]:
                    print( "        {} ({}): {!r}".format( key2, len(LDMLData[key][key2]), LDMLData[key][key2] ) )
        elif debuggingThisModule: print( '\nLDMLData', len(LDMLData), LDMLData )
        return LDMLData
    # end of LDML.load
# end of class LDMLFile



def demo():
    """
    Demonstrate reading and checking some LDML files.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( ProgNameVersion )

    mainTestFolder = '../../../ExternalPrograms/SIL_NRSI/sldr/sldr/'
    if 1: # test load all SIL LDML files (cloned from GitHub)
        for something in os.listdir( mainTestFolder ):
            somepath = os.path.join( mainTestFolder, something )
            if os.path.isdir( somepath ):
                if BibleOrgSysGlobals.verbosityLevel > 0:
                    print( "\n\nA: Looking for files in folder: {}".format( somepath ) )

                for something2 in os.listdir( somepath ):
                    somepath2 = os.path.join( somepath, something2 )
                    if os.path.isfile( somepath2 ):
                        if BibleOrgSysGlobals.verbosityLevel > 0:
                            print( "  Found {}".format( somepath2 ) )

                            if os.access( somepath2, os.R_OK ):
                                thisLDMLfile = LDMLFile( somepath, something2 )
                                LDMLdict = thisLDMLfile.load()
                                if BibleOrgSysGlobals.verbosityLevel > 0: print( LDMLdict )
                                if BibleOrgSysGlobals.strictCheckingFlag: thisLDMLfile.check()
                                #DBErrors = thisLDMLfile.getErrors()
                                # print( DBErrors )
                                #print( thisLDMLfile.getVersification () )
                                #print( thisLDMLfile.getAddedUnits () )
                                #for ref in ('GEN','Genesis','GeNeSiS','Gen','MrK','mt','Prv','Xyz',):
                                    ##print( "Looking for", ref )
                                    #print( "Tried finding '{}' in '{}': got '{}'".format( ref, name, UB.getXRefBBB( ref ) ) )
                            else: print( "Sorry, test file '{}' is not readable on this computer.".format( somepath2 ) )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nPTX8 B/ Trying single module in {}".format( testFolder ) )
        thisLDMLfile = LDML( testFolder )
        thisLDMLfile.load()
        if BibleOrgSysGlobals.verbosityLevel > 0: print( thisLDMLfile )


if __name__ == '__main__':
    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( ProgName, ProgVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    demo()

    BibleOrgSysGlobals.closedown( ProgName, ProgVersion )
# end of LDML.py
