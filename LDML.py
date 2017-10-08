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

LastModifiedDate = '2017-10-09' # by RJH
ShortProgName = "LDML_Handler"
ProgName = "Unicode LOCALE DATA MARKUP LANGUAGE handler"
ProgVersion = '0.09'
ProgNameVersion = '{} v{}'.format( ShortProgName, ProgVersion )
ProgNameVersionDate = '{} {} {}'.format( ProgNameVersion, _("last modified"), LastModifiedDate )

debuggingThisModule = False


import sys, os, logging
from collections import OrderedDict
import multiprocessing
from xml.etree.ElementTree import ElementTree

import BibleOrgSysGlobals



draftValues = ('provisional', 'contributed', 'unconfirmed', 'proposed', )



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


        def loadIdentity( element, elementLocation, identity ):
            """
            Returns the updated dictionary.
            """
            for subelement in element:
                subelementLocation = subelement.tag + ' in ' + elementLocation
                #if debuggingThisModule: print( "    Processing {}…".format( subelementLocation ) )
                BibleOrgSysGlobals.checkXMLNoText( subelement, subelementLocation )
                BibleOrgSysGlobals.checkXMLNoTail( subelement, subelementLocation )
                if subelement.tag == 'version':
                    BibleOrgSysGlobals.checkXMLNoSubelements( subelement, subelementLocation )
                    number = None
                    for attrib,value in subelement.items():
                        #print( "hereV6", attrib, value )
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
                    lgType = lgCode = lgName = None
                    for attrib,value in subelement.items():
                        #print( "hereLorT6", attrib, value )
                        if attrib=='type': lgType = value
                        elif attrib=='code': lgCode = value
                        elif attrib=='name': lgName = value
                        else:
                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, subelementLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    assert subelement.tag not in identity
                    identity[subelement.tag] = lgType, lgCode, lgName
                elif subelement.tag == 'script':
                    BibleOrgSysGlobals.checkXMLNoText( subelement, subelementLocation )
                    BibleOrgSysGlobals.checkXMLNoSubelements( subelement, subelementLocation )
                    BibleOrgSysGlobals.checkXMLNoTail( subelement, subelementLocation )
                    sName = sCode = None
                    for attrib,value in subelement.items():
                        if attrib=='name': sName = value; assert sName in ('Latin',)
                        elif attrib=='code': sCode = value; assert sCode in ('Latn',)
                        else:
                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, subelementLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    assert subelement.tag not in identity
                    identity[subelement.tag] = (sName,sCode)
                elif subelement.tag == 'special':
                    BibleOrgSysGlobals.checkXMLNoAttributes( subelement, subelementLocation )
                    for sub2element in subelement:
                        sub2elementLocation = sub2element.tag + ' in ' + subelementLocation
                        #if debuggingThisModule: print( "      Processing {}…".format( sub2elementLocation ) )
                        BibleOrgSysGlobals.checkXMLNoText( sub2element, sub2elementLocation )
                        BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2elementLocation )
                        BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2elementLocation )
                        windowsLCID = draft = source = sDefaultRegion = None
                        for attrib,value in sub2element.items():
                            if attrib=='windowsLCID': windowsLCID = value
                            elif attrib=='draft': draft = value
                            elif attrib=='source': source = value
                            elif attrib=='defaultRegion': sDefaultRegion = value
                            else:
                                logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub2elementLocation ) )
                                if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                        assert subelement.tag not in identity
                        identity[subelement.tag] = {'tag':sub2element.tag,'windowsLCID':windowsLCID,'draft':draft,'source':source}
                else:
                    logging.error( _("Unprocessed {!r} subelement ({}) in {}").format( subelement.tag, subelement.text.strip() if subelement.text else subelement.text, elementLocation ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
            return identity
        # end of loadIdentity


        def loadContacts( element, elementLocation, contacts ):
            """
            Returns the updated dictionary.
            """
            for subelement in element:
                subelementLocation = subelement.tag + ' in ' + elementLocation
                #if debuggingThisModule: print( "    Processing {}…".format( subelementLocation ) )
                BibleOrgSysGlobals.checkXMLNoText( subelement, subelementLocation )
                BibleOrgSysGlobals.checkXMLNoSubelements( subelement, subelementLocation )
                BibleOrgSysGlobals.checkXMLNoTail( subelement, subelementLocation )
                if subelement.tag == 'contact':
                    cName = cEmail = None
                    for attrib,value in subelement.items():
                        #print( "hereC1", attrib, value )
                        if attrib=='name': cName = value
                        elif attrib=='email': cEmail = value
                        else:
                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, subelementLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    assert cName not in contacts
                    contacts[cName] = cEmail
                else:
                    logging.error( _("Unprocessed {!r} subelement ({}) in {}").format( subelement.tag, subelement.text.strip() if subelement.text else subelement.text, elementLocation ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
            return contacts
        # end of loadContacts


        def loadComments( element, elementLocation, comments ):
            """
            Returns the updated dictionary.
            """
            for subelement in element:
                subelementLocation = subelement.tag + ' in ' + elementLocation
                #if debuggingThisModule: print( "    Processing {}…".format( subelementLocation ) )
                BibleOrgSysGlobals.checkXMLNoText( subelement, subelementLocation )
                BibleOrgSysGlobals.checkXMLNoSubelements( subelement, subelementLocation )
                BibleOrgSysGlobals.checkXMLNoTail( subelement, subelementLocation )
                if subelement.tag == 'entry':
                    cDate = cName = cComment = None
                    for attrib,value in subelement.items():
                        #print( "hereC2", attrib, value )
                        if attrib=='date': cDate = value
                        elif attrib=='name': cName = value
                        elif attrib=='comment': cComment = value
                        else:
                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, subelementLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    assert cDate not in comments # Note: comment date might not be unique ???
                    comments[cDate] = (cName,cComment)
                else:
                    logging.error( _("Unprocessed {!r} subelement ({}) in {}").format( subelement.tag, subelement.text.strip() if subelement.text else subelement.text, elementLocation ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
            return comments
        # end of loadComments


        def loadStatus( element, elementLocation, status ):
            """
            Returns the updated dictionary.
            """
            sValue = None
            for attrib,value in element.items():
                #print( "hereSt2", attrib, value )
                if attrib=='value': sValue = value
                else:
                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, elementLocation ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
            assert element.tag not in status
            status[element.tag] = sValue
            return status
        # end of loadStatus


        def loadCharacters( element, elementLocation, characters ):
            """
            Returns the updated dictionary.
            """
            for subelement in element:
                subelementLocation = subelement.tag + ' in ' + elementLocation
                if debuggingThisModule: print( "    Processing {}…".format( subelementLocation ) )
                BibleOrgSysGlobals.checkXMLNoTail( subelement, subelementLocation )
                if subelement.tag == 'exemplarCharacters':
                    BibleOrgSysGlobals.checkXMLNoSubelements( subelement, subelementLocation )
                    ecType = ecDraft = None
                    for attrib,value in subelement.items():
                        #print( 'ECattrib', attrib, repr(value) )
                        if attrib=='type': ecType = value; assert ecType in ('auxiliary','index','digits','punctuation',)
                        elif attrib=='draft': ecDraft = value; assert ecDraft in draftValues
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
                elif subelement.tag == 'moreInformation':
                    BibleOrgSysGlobals.checkXMLNoAttributes( subelement, subelementLocation )
                    BibleOrgSysGlobals.checkXMLNoSubelements( subelement, subelementLocation )
                    BibleOrgSysGlobals.checkXMLNoTail( subelement, subelementLocation )
                    assert subelement.tag not in characters
                    characters[subelement.tag] = subelement.text
                else:
                    logging.error( _("Unprocessed {!r} subelement ({}) in {}").format( subelement.tag, subelement.text.strip() if subelement.text else subelement.text, elementLocation ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
            return characters
        # end of loadCharacters


        def loadDelimiters( element, elementLocation, delimiters ):
            """
            Returns the updated dictionary.
            """
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
                    logging.error( _("Unprocessed {!r} subelement ({}) in {}").format( subelement.tag, subelement.text.strip() if subelement.text else subelement.text, elementLocation ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
            #print( '\n', element.tag, LDMLData[element.tag] )
            return delimiters
        # end of loadDelimiters


        def loadLayout( element, elementLocation, layout ):
            """
            Returns the updated dictionary.
            """
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
                    logging.error( _("Unprocessed {!r} subelement ({}) in {}").format( subelement.tag, subelement.text.strip() if subelement.text else subelement.text, elementLocation ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
            return layout
        # end of loadLayout


        def loadNumbers( element, elementLocation, numbers ):
            """
            Returns the updated dictionary.
            """
            currencies = {}
            percentFormats = {}
            decimalFormats = {}
            miscPatterns = {}
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
                        #print( "symbols", symbols, subelement.tag )
                        #assert subelement.tag not in numbers # losing data here XXXXXXXXXXXXXXXXXXXXXXX
                        if subelement.tag in numbers: logging.critical( "Losing data here for {} numbers field".format( subelement.tag ) )
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
                        BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2elementLocation )
                        #if sub2element.tag not in currencyFormats[numberSystem]:
                            #currencyFormats[numberSystem][sub2element.tag] = sub2element.text
                        if sub2element.tag == 'currencyFormatLength':
                            BibleOrgSysGlobals.checkXMLNoText( sub2element, sub2elementLocation )
                            cflType = alt = None
                            for attrib,value in sub2element.items():
                                #if attrib=='draft': draft = value
                                if attrib=='type': cflType = value; assert cflType in ('short',)
                                #elif attrib=='alt': alt = value
                                else:
                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub2elementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
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
                                        #if debuggingThisModule: print( "          ProcessingCF {} ({})…".format( sub4elementLocation, sub4element.text.strip() ) )
                                        BibleOrgSysGlobals.checkXMLNoSubelements( sub4element, sub4elementLocation )
                                        BibleOrgSysGlobals.checkXMLNoTail( sub4element, sub4elementLocation )
                                        if sub4element.tag == 'pattern':
                                            pType = pCount = pDraft = None
                                            for attrib,value in sub4element.items():
                                                #print( "here CF-T7", attrib, value )
                                                if attrib=='type': pType = value # assert pType in ('1000','10000',)
                                                elif attrib=='count': pCount = value; assert pCount in ('zero','one','two','other','few','many',)
                                                elif attrib=='draft': pDraft = value
                                                else:
                                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub4elementLocation ) )
                                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                            pass # Save text XXXXX
                                        else:
                                            logging.error( _("Unprocessed {!r} sub4element ({}) in {}").format( sub4element.tag, sub4element.text.strip() if sub4element.text else sub4element.text, sub3elementLocation ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                else:
                                    logging.error( _("Unprocessed {!r} sub3element ({}) in {}").format( sub3element.tag, sub3element.text.strip() if sub3element.text else sub3element.text, sub2elementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                        elif sub2element.tag == 'unitPattern':
                            BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2elementLocation )
                            BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2elementLocation )
                            upCount = alt = None
                            for attrib,value in sub2element.items():
                                #print( "here UP7", attrib, value )
                                #if attrib=='draft': draft = value
                                if attrib=='count': upCount = value; assert upCount in ('zero','one','two','other','few','many',)
                                #elif attrib=='alt': alt = value
                                else:
                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub2elementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                            pass # Save text XXXXXXXXXXXXXXXXXXXXXX
                        else:
                            logging.error( _("Unprocessed {!r} sub2element ({}) in {}").format( sub2element.tag, sub2element.text.strip() if sub2element.text else sub2element.text, subelementLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                    if currencyFormats:
                        #print( "currencyFormats", currencyFormats )
                        #assert subelement.tag not in numbers # losing data here XXXXXXXXXXXXXXXXXXXXXXX
                        if subelement.tag in numbers: logging.critical( "Losing data here for {} currencyFormats field".format( subelement.tag ) )
                        numbers[subelement.tag] = currencyFormats
                elif subelement.tag == 'currencies':
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
                                #if attrib=='draft': draft = value
                                if attrib=='type': cuType = value
                                #elif attrib=='alt': alt = value
                                else:
                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub2elementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                            #assert cuType not in currencies # XXXXXXXXXXXXXX losing some info here
                            if cuType in currencies: logging.critical( "Losing data here for {} currencies field".format( cuType ) )
                            currencies[cuType] = {}
                            for sub3element in sub2element:
                                sub3elementLocation = sub3element.tag + ' in ' + sub2elementLocation
                                #if debuggingThisModule: print( "        Processing {} ({})…".format( sub3elementLocation, sub3element.text.strip() ) )
                                BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3elementLocation )
                                BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3elementLocation )
                                displayNames = []
                                symbols = []
                                if sub3element.tag == 'displayName':
                                    dnCount = dnDraft = None
                                    for attrib,value in sub3element.items():
                                        #print( "here dn2", attrib, value )
                                        if attrib=='count': dnCount = value
                                        elif attrib=='draft': dnDraft = value; assert dnDraft in draftValues
                                        #elif attrib=='alt': alt = value
                                        else:
                                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub3elementLocation ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                    displayNames.append( (dnCount,sub3element.text) )
                                elif sub3element.tag == 'symbol':
                                    sDraft = sAlt = None
                                    for attrib,value in sub3element.items():
                                        #print( "here S2", attrib, value )
                                        if attrib=='draft': sDraft = value; assert sDraft in draftValues
                                        elif attrib=='alt': sAlt = value; assert sAlt in ('variant','narrow',)
                                        else:
                                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub3elementLocation ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                    symbols.append( sub3element.text )
                                elif sub3element.tag == 'pattern':
                                    BibleOrgSysGlobals.checkXMLNoAttributes( sub3element, sub3elementLocation )
                                    symbols.append( sub3element.text )
                                else:
                                    logging.error( _("Unprocessed {!r} sub3element ({}) in {}").format( sub3element.tag, sub3element.text.strip() if sub3element.text else sub3element.text, sub2elementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                            if displayNames:
                                assert 'displayNames' not in currencies[cuType]
                                currencies[cuType]['displayNames']= displayNames
                            if symbols:
                                assert 'symbols' not in currencies[cuType]
                                currencies[cuType]['symbols']= symbols
                        else:
                            logging.error( _("Unprocessed {!r} sub2element ({}) in {}").format( sub2element.tag, sub2element.text.strip() if sub2element.text else sub2element.text, subelementLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                    if currencies:
                        #print( "currencies", currencies )
                        assert subelement.tag not in numbers
                        numbers[subelement.tag] = currencies

                elif subelement.tag == 'percentFormats':
                    BibleOrgSysGlobals.checkXMLNoText( subelement, subelementLocation )
                    BibleOrgSysGlobals.checkXMLNoTail( subelement, subelementLocation )
                    numberSystem = None
                    for attrib,value in subelement.items():
                        #if attrib=='draft': draft = value
                        if attrib=='numberSystem': numberSystem = value
                        #elif attrib=='alt': alt = value
                        else:
                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, subelementLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    for sub2element in subelement:
                        sub2elementLocation = sub2element.tag + ' in ' + subelementLocation
                        #if debuggingThisModule: print( "      Processing {} ({})…".format( sub2elementLocation, sub2element.text.strip() ) )
                        BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, sub2elementLocation )
                        BibleOrgSysGlobals.checkXMLNoText( sub2element, sub2elementLocation )
                        BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2elementLocation )
                        if sub2element.tag == 'percentFormat':
                            for sub3element in sub2element:
                                sub3elementLocation = sub3element.tag + ' in ' + sub2elementLocation
                                #if debuggingThisModule: print( "        Processing {} ({})…".format( sub3elementLocation, sub3element.text.strip() ) )
                                BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3elementLocation )
                                BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3elementLocation )
                                displayNames = []
                                symbols = []
                                if sub3element.tag == 'displayName':
                                    dnCount = None
                                    for attrib,value in sub3element.items():
                                        #if attrib=='draft': draft = value
                                        if attrib=='count': dnCount = value
                                        #elif attrib=='alt': alt = value
                                        else:
                                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub3elementLocation ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                    displayNames.append( (dnCount,sub3element.text) )
                                elif sub3element.tag == 'symbol':
                                    BibleOrgSysGlobals.checkXMLNoAttributes( sub3element, sub3elementLocation )
                                    symbols.append( sub3element.text )
                                else:
                                    logging.error( _("Unprocessed {!r} sub3element ({}) in {}").format( sub3element.tag, sub3element.text.strip() if sub3element.text else sub3element.text, sub2elementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                            if displayNames:
                                assert 'displayNames' not in percentFormats[cuType]
                                percentFormats[cuType]['displayNames']= displayNames
                            if symbols:
                                assert 'symbols' not in percentFormats[cuType]
                                percentFormats[cuType]['symbols']= symbols
                        elif sub2element.tag == 'percentFormatLength':
                            for sub3element in sub2element:
                                sub3elementLocation = sub3element.tag + ' in ' + sub2elementLocation
                                #if debuggingThisModule: print( "        Processing {} ({})…".format( sub3elementLocation, sub3element.text.strip() ) )
                                BibleOrgSysGlobals.checkXMLNoAttributes( sub3element, sub3elementLocation )
                                BibleOrgSysGlobals.checkXMLNoText( sub3element, sub3elementLocation )
                                BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3elementLocation )
                                if sub3element.tag == 'percentFormat':
                                    for sub4element in sub3element:
                                        sub4elementLocation = sub4element.tag + ' in ' + sub3elementLocation
                                        #if debuggingThisModule: print( "          Processing {} ({})…".format( sub4elementLocation, sub4element.text.strip() ) )
                                        BibleOrgSysGlobals.checkXMLNoSubelements( sub4element, sub4elementLocation )
                                        BibleOrgSysGlobals.checkXMLNoTail( sub4element, sub4elementLocation )
                                        if sub4element.tag == 'pattern':
                                            pDraft = None
                                            for attrib,value in sub4element.items():
                                                if attrib=='draft': pDraft = value
                                                else:
                                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub4elementLocation ) )
                                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                            pass # Save text XXXXX
                                        else:
                                            logging.error( _("Unprocessed {!r} sub4element ({}) in {}").format( sub4element.tag, sub4element.text.strip() if sub4element.text else sub4element.text, sub3elementLocation ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                else:
                                    logging.error( _("Unprocessed {!r} sub3element ({}) in {}").format( sub3element.tag, sub3element.text.strip() if sub3element.text else sub3element.text, sub2elementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                        else:
                            logging.error( _("Unprocessed {!r} sub2element ({}) in {}").format( sub2element.tag, sub2element.text.strip() if sub2element.text else sub2element.text, subelementLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                    if percentFormats:
                        #print( "percentFormats", percentFormats )
                        assert subelement.tag not in numbers
                        numbers[subelement.tag] = percentFormats

                elif subelement.tag == 'minimumGroupingDigits':
                    BibleOrgSysGlobals.checkXMLNoSubelements( subelement, subelementLocation )
                    BibleOrgSysGlobals.checkXMLNoTail( subelement, subelementLocation )
                    mgdDraft = None
                    for attrib,value in subelement.items():
                        if attrib=='draft': mgdDraft = value
                        else:
                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, subelementLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    pass # save text XXXXXXXXXXXXXXXXXXX

                elif subelement.tag == 'decimalFormats':
                    BibleOrgSysGlobals.checkXMLNoText( subelement, subelementLocation )
                    BibleOrgSysGlobals.checkXMLNoTail( subelement, subelementLocation )
                    numberSystem = None
                    for attrib,value in subelement.items():
                        #print( "hereDF8", attrib, value )
                        if attrib=='numberSystem': numberSystem = value # assert numberSystem in ('latn','arab','arabext','fullwide',)
                        else:
                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, subelementLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    for sub2element in subelement:
                        sub2elementLocation = sub2element.tag + ' in ' + subelementLocation
                        #if debuggingThisModule: print( "      Processing {} ({})…".format( sub2elementLocation, sub2element.text.strip() ) )
                        BibleOrgSysGlobals.checkXMLNoText( sub2element, sub2elementLocation )
                        BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2elementLocation )
                        if sub2element.tag == 'decimalFormatLength':
                            dflType = None
                            for attrib,value in sub2element.items():
                                #if attrib=='draft': draft = value
                                if attrib=='type': dflType = value
                                #elif attrib=='alt': alt = value
                                else:
                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub2elementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                            for sub3element in sub2element:
                                sub3elementLocation = sub3element.tag + ' in ' + sub2elementLocation
                                #if debuggingThisModule: print( "        Processing {} ({})…".format( sub3elementLocation, sub3element.text.strip() ) )
                                BibleOrgSysGlobals.checkXMLNoAttributes( sub3element, sub3elementLocation )
                                BibleOrgSysGlobals.checkXMLNoText( sub3element, sub3elementLocation )
                                BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3elementLocation )
                                if sub3element.tag == 'decimalFormat':
                                    for sub4element in sub3element:
                                        sub4elementLocation = sub4element.tag + ' in ' + sub3elementLocation
                                        #if debuggingThisModule: print( "          Processing {} ({})…".format( sub4elementLocation, sub4element.text.strip() ) )
                                        BibleOrgSysGlobals.checkXMLNoSubelements( sub4element, sub4elementLocation )
                                        BibleOrgSysGlobals.checkXMLNoTail( sub4element, sub4elementLocation )
                                        if sub4element.tag == 'pattern':
                                            pType = pCount = None
                                            for attrib,value in sub4element.items():
                                                #print( "here DF-T7", attrib, value )
                                                if attrib=='type': pType = value # assert pType in ('1000','10000',)
                                                elif attrib=='count': pCount = value; assert pCount in ('zero','one','two','other','few','many',)
                                                else:
                                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub4elementLocation ) )
                                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                            pass # Save text XXXXX
                                        else:
                                            logging.error( _("Unprocessed {!r} sub4element ({}) in {}").format( sub4element.tag, sub4element.text.strip() if sub4element.text else sub4element.text, sub3elementLocation ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                else:
                                    logging.error( _("Unprocessed {!r} sub3element ({}) in {}").format( sub3element.tag, sub3element.text.strip() if sub3element.text else sub3element.text, sub2elementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                        else:
                            logging.error( _("Unprocessed {!r} sub2element ({}) in {}").format( sub2element.tag, sub2element.text.strip() if sub2element.text else sub2element.text, subelementLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                    if decimalFormats:
                        #print( "decimalFormats", decimalFormats )
                        assert subelement.tag not in numbers
                        numbers[subelement.tag] = decimalFormats

                elif subelement.tag == 'miscPatterns':
                    BibleOrgSysGlobals.checkXMLNoText( subelement, subelementLocation )
                    BibleOrgSysGlobals.checkXMLNoTail( subelement, subelementLocation )
                    numberSystem = None
                    for attrib,value in subelement.items():
                        #print( "hereDF8", attrib, value )
                        if attrib=='numberSystem': numberSystem = value # assert numberSystem in ('latn','arab','arabext','fullwide',)
                        else:
                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, subelementLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    assert numberSystem not in miscPatterns
                    miscPatterns[numberSystem] = {}
                    for sub2element in subelement:
                        sub2elementLocation = sub2element.tag + ' in ' + subelementLocation
                        #if debuggingThisModule: print( "      Processing {} ({})…".format( sub2elementLocation, sub2element.text.strip() ) )
                        BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2elementLocation )
                        BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2elementLocation )
                        if sub2element.tag == 'pattern':
                            pType = None
                            for attrib,value in sub2element.items():
                                #if attrib=='draft': draft = value
                                if attrib=='type': pType = value; assert pType in ('atLeast',)
                                #elif attrib=='alt': alt = value
                                else:
                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub2elementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                            assert pType not in miscPatterns[numberSystem]
                            miscPatterns[numberSystem][pType] = sub2element.text
                        else:
                            logging.error( _("Unprocessed {!r} sub2element ({}) in {}").format( sub2element.tag, sub2element.text.strip() if sub2element.text else sub2element.text, subelementLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                    if miscPatterns:
                        #print( "miscPatterns", miscPatterns )
                        assert subelement.tag not in numbers
                        numbers[subelement.tag] = miscPatterns

                else:
                    logging.error( _("Unprocessed {!r} subelement ({}) in {}").format( subelement.tag, subelement.text.strip() if subelement.text else subelement.text, elementLocation ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
            return numbers
        # end of loadNumbers


        def loadCollations( element, elementLocation, collations ):
            """
            Returns the updated dictionary.
            """
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
                    #assert subelement.tag not in collations # XXXXXXXXXXXXXX losing some info here
                    if subelement.tag in collations: logging.critical( "Losing data here for {} collations field".format( subelement.tag ) )
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
                    logging.error( _("Unprocessed {!r} subelement ({}) in {}").format( subelement.tag, subelement.text.strip() if subelement.text else subelement.text, elementLocation ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
            return collations
        # end of loadCollations


        def loadLocateDisplayNames( element, elementLocation, localeDisplayNames ):
            """
            Returns the updated dictionary.
            """
            languages = OrderedDict()
            territories = OrderedDict()
            keys = OrderedDict()
            types = OrderedDict()
            scripts = OrderedDict()
            variants = OrderedDict()
            codePatterns = OrderedDict()
            measurementSystems = OrderedDict()
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
                        #if debuggingThisModule: print( "      ProcessingLgs3a {} ({})…".format( sub2elementLocation, sub2element.text.strip() ) )
                        BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2elementLocation )
                        BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2elementLocation )
                        if sub2element.tag == 'language':
                            lDraft = lType = lAlt = None
                            for attrib,value in sub2element.items():
                                #print( "here Lg7", attrib, value )
                                if attrib=='draft': lDraft = value
                                elif attrib=='type': lType = value
                                elif attrib=='alt': lAlt = value; assert lAlt in ('short','long','variant','secondary',)
                                else:
                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub2elementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                            #assert lType not in languages # XXXXXXXXXXXXXX losing some info here
                            if lType in languages: logging.critical( "Losing data here for {} languages field".format( lType ) )
                            languages[lType] = (lType,sub2element.text,lDraft)
                        else:
                            logging.error( _("Unprocessed {!r} sub2element ({}) in {}").format( sub2element.tag, sub2element.text.strip() if sub2element.text else sub2element.text, subelementLocation ) )
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
                            tDraft = tType = tAlt = None
                            for attrib,value in sub2element.items():
                                #print( "hereT8", attrib, value )
                                if attrib=='draft': tDraft = value
                                elif attrib=='type': tType = value
                                elif attrib=='alt': tAlt = value; assert tAlt in ('short','variant')
                                else:
                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub2elementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                            #assert tType not in territories # Losing info here XXXXXXXXXXXXXXXXXXXXXXX
                            if tType in territories: logging.critical( "Losing data here for {} territories field".format( tType ) )
                            territories[tType] = (tType,sub2element.text,tDraft,tAlt)
                        else:
                            logging.error( _("Unprocessed {!r} sub2element ({}) in {}").format( sub2element.tag, sub2element.text.strip() if sub2element.text else sub2element.text, subelementLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                elif subelement.tag == 'keys':
                    BibleOrgSysGlobals.checkXMLNoAttributes( subelement, subelementLocation )
                    BibleOrgSysGlobals.checkXMLNoText( subelement, subelementLocation )
                    BibleOrgSysGlobals.checkXMLNoTail( subelement, subelementLocation )
                    for sub2element in subelement:
                        sub2elementLocation = sub2element.tag + ' in ' + subelementLocation
                        #if debuggingThisModule: print( "      Processing3k {} ({})…".format( sub2elementLocation, sub2element.text.strip() ) )
                        BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2elementLocation )
                        BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2elementLocation )
                        if sub2element.tag == 'key':
                            draft = tType = alt = None
                            for attrib,value in sub2element.items():
                                #print( "hereK8", attrib, value )
                                #if attrib=='draft': draft = value
                                if attrib=='type': tType = value
                                #elif attrib=='alt': alt = value
                                else:
                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub2elementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                            assert tType not in territories
                            territories[tType] = (tType,sub2element.text,draft,alt)
                        else:
                            logging.error( _("Unprocessed {!r} sub2element ({}) in {}").format( sub2element.tag, sub2element.text.strip() if sub2element.text else sub2element.text, subelementLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                elif subelement.tag == 'types':
                    BibleOrgSysGlobals.checkXMLNoAttributes( subelement, subelementLocation )
                    BibleOrgSysGlobals.checkXMLNoText( subelement, subelementLocation )
                    BibleOrgSysGlobals.checkXMLNoTail( subelement, subelementLocation )
                    for sub2element in subelement:
                        sub2elementLocation = sub2element.tag + ' in ' + subelementLocation
                        #if debuggingThisModule: print( "      Processing3t {} ({})…".format( sub2elementLocation, sub2element.text.strip() ) )
                        BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2elementLocation )
                        BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2elementLocation )
                        if sub2element.tag == 'type':
                            tKey = kType = kAlt = None
                            for attrib,value in sub2element.items():
                                #print( "hereT8", attrib, value )
                                #if attrib=='draft': draft = value
                                if attrib=='key': tKey = value # assert tKey in ('colNormalization','cf','numbers','d0','m0','collation','lw','calendar','kr','kv')
                                elif attrib=='type': kType = value
                                elif attrib=='alt': kAlt = value; assert kAlt in ('short',)#'variant','stand-alone')
                                else:
                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub2elementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                            #assert kType not in types # losing data here XXXXXXXXXXXXXXXXXXXXXXX
                            if kType in types: logging.critical( "Losing data here for {} types field".format( kType ) )
                            types[kType] = {'type':kType,'key':tKey,'value':sub2element.text}
                        else:
                            logging.error( _("Unprocessed {!r} sub2element ({}) in {}").format( sub2element.tag, sub2element.text.strip() if sub2element.text else sub2element.text, subelementLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                elif subelement.tag == 'scripts':
                    BibleOrgSysGlobals.checkXMLNoAttributes( subelement, subelementLocation )
                    BibleOrgSysGlobals.checkXMLNoText( subelement, subelementLocation )
                    BibleOrgSysGlobals.checkXMLNoTail( subelement, subelementLocation )
                    for sub2element in subelement:
                        sub2elementLocation = sub2element.tag + ' in ' + subelementLocation
                        #if debuggingThisModule: print( "      Processing3scr {} ({})…".format( sub2elementLocation, sub2element.text.strip() ) )
                        BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2elementLocation )
                        BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2elementLocation )
                        if sub2element.tag == 'script':
                            sType = sAlt = sDraft = None
                            for attrib,value in sub2element.items():
                                #print( "hereS8", attrib, value )
                                if attrib=='type': sType = value
                                elif attrib=='alt': sAlt = value; assert sAlt in ('short','variant','stand-alone','secondary',)
                                elif attrib=='draft': sDraft = value; assert sDraft in draftValues
                                else:
                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub2elementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                            #assert sType not in scripts # XXXXXXXXXXXxx losing some info here
                            if sType in scripts: logging.critical( "Losing data here for {} scripts field".format( sType ) )
                            scripts[sType] = {'type':sType,'value':sub2element.text}
                        else:
                            logging.error( _("Unprocessed {!r} sub2element ({}) in {}").format( sub2element.tag, sub2element.text.strip() if sub2element.text else sub2element.text, subelementLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                elif subelement.tag == 'variants':
                    BibleOrgSysGlobals.checkXMLNoAttributes( subelement, subelementLocation )
                    BibleOrgSysGlobals.checkXMLNoText( subelement, subelementLocation )
                    BibleOrgSysGlobals.checkXMLNoTail( subelement, subelementLocation )
                    for sub2element in subelement:
                        sub2elementLocation = sub2element.tag + ' in ' + subelementLocation
                        #if debuggingThisModule: print( "      ProcessingV3 {} ({})…".format( sub2elementLocation, sub2element.text.strip() ) )
                        BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2elementLocation )
                        BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2elementLocation )
                        if sub2element.tag == 'variant':
                            vType = vAlt = vDraft = None
                            for attrib,value in sub2element.items():
                                #print( "hereV8", attrib, value )
                                if attrib=='type': vType = value
                                elif attrib=='alt': vAlt = value; assert vAlt in ('short','secondary',)
                                elif attrib=='draft': vDraft = value; assert vDraft in draftValues
                                else:
                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub2elementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                            #assert vType not in variants # XXXXXXXXXXXxx losing some info here
                            if vType in variants: logging.critical( "Losing data here for {} variants field".format( vType ) )
                            variants[vType] = {'type':vType,'value':sub2element.text}
                        else:
                            logging.error( _("Unprocessed {!r} sub2element ({}) in {}").format( sub2element.tag, sub2element.text.strip() if sub2element.text else sub2element.text, subelementLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                elif subelement.tag == 'codePatterns':
                    BibleOrgSysGlobals.checkXMLNoAttributes( subelement, subelementLocation )
                    BibleOrgSysGlobals.checkXMLNoText( subelement, subelementLocation )
                    BibleOrgSysGlobals.checkXMLNoTail( subelement, subelementLocation )
                    for sub2element in subelement:
                        sub2elementLocation = sub2element.tag + ' in ' + subelementLocation
                        #if debuggingThisModule: print( "      ProcessingCP6 {} ({})…".format( sub2elementLocation, sub2element.text.strip() ) )
                        BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2elementLocation )
                        BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2elementLocation )
                        if sub2element.tag == 'codePattern':
                            key = cpType = vAlt = None
                            for attrib,value in sub2element.items():
                                #print( "hereCP8", attrib, value )
                                if attrib=='type': cpType = value; assert cpType in ('language','script','territory')
                                #elif attrib=='xalt': vAlt = value; assert vAlt in ('short',)#'variant','stand-alone')
                                else:
                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub2elementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                            assert cpType not in codePatterns
                            codePatterns[cpType] = {'type':cpType,'value':sub2element.text}
                        else:
                            logging.error( _("Unprocessed {!r} sub2element ({}) in {}").format( sub2element.tag, sub2element.text.strip() if sub2element.text else sub2element.text, subelementLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                elif subelement.tag == 'measurementSystemNames':
                    BibleOrgSysGlobals.checkXMLNoAttributes( subelement, subelementLocation )
                    BibleOrgSysGlobals.checkXMLNoText( subelement, subelementLocation )
                    BibleOrgSysGlobals.checkXMLNoTail( subelement, subelementLocation )
                    for sub2element in subelement:
                        sub2elementLocation = sub2element.tag + ' in ' + subelementLocation
                        #if debuggingThisModule: print( "      ProcessingCP6 {} ({})…".format( sub2elementLocation, sub2element.text.strip() ) )
                        BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2elementLocation )
                        BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2elementLocation )
                        if sub2element.tag == 'measurementSystemName':
                            key = msnType = vAlt = None
                            for attrib,value in sub2element.items():
                                #print( "hereMSN8", attrib, value )
                                if attrib=='type': msnType = value # assert msnType in ('UK','US','metric',)
                                #elif attrib=='xalt': vAlt = value; assert vAlt in ('short',)#'variant','stand-alone')
                                else:
                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub2elementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                            assert msnType not in measurementSystems
                            measurementSystems[msnType] = {'type':msnType,'value':sub2element.text}
                        else:
                            logging.error( _("Unprocessed {!r} sub2element ({}) in {}").format( sub2element.tag, sub2element.text.strip() if sub2element.text else sub2element.text, subelementLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                else:
                    logging.error( _("Unprocessed {!r} subelement ({}) in {}").format( subelement.tag, subelement.text.strip() if subelement.text else subelement.text, elementLocation ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
            if territories:
                assert 'territories' not in localeDisplayNames
                localeDisplayNames['territories'] = territories
            if keys:
                assert 'keys' not in localeDisplayNames
                localeDisplayNames['keys'] = keys
            if types:
                assert 'types' not in localeDisplayNames
                localeDisplayNames['types'] = types
            if scripts:
                assert 'scripts' not in localeDisplayNames
                localeDisplayNames['scripts'] = scripts
            if variants:
                assert 'variants' not in localeDisplayNames
                localeDisplayNames['variants'] = variants
            if codePatterns:
                assert 'codePatterns' not in localeDisplayNames
                localeDisplayNames['codePatterns'] = codePatterns
            return localeDisplayNames
        # end of loadLocateDisplayNames


        def loadDates( element, elementLocation, dates ):
            """
            Returns the updated dictionary.
            """
            dCalendars = OrderedDict()
            fields = OrderedDict()
            timeZoneNames = OrderedDict()
            for subelement in element:
                subelementLocation = subelement.tag + ' in ' + elementLocation
                #if debuggingThisModule: print( "    Processing2 {} ({})…".format( subelementLocation, subelement.text.strip() ) )
                BibleOrgSysGlobals.checkXMLNoAttributes( subelement, subelementLocation )
                BibleOrgSysGlobals.checkXMLNoText( subelement, subelementLocation )
                BibleOrgSysGlobals.checkXMLNoTail( subelement, subelementLocation )
                if subelement.tag == 'calendars':
                    dCalendar = OrderedDict()
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
                            dateTimeFormats = OrderedDict()
                            dayPeriods = OrderedDict()
                            for sub3element in sub2element:
                                sub3elementLocation = sub3element.tag + ' in ' + sub2elementLocation
                                #if debuggingThisModule: print( "        ProcessingD-C {} ({})…".format( sub3elementLocation, sub3element.text.strip() ) )
                                BibleOrgSysGlobals.checkXMLNoAttributes( sub3element, sub3elementLocation )
                                BibleOrgSysGlobals.checkXMLNoText( sub3element, sub3elementLocation )
                                BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3elementLocation )
                                if sub3element.tag == 'dateTimeFormats':
                                    for sub4element in sub3element:
                                        sub4elementLocation = sub4element.tag + ' in ' + sub3elementLocation
                                        #if debuggingThisModule: print( "          ProcessingDTF4 {} ({})…".format( sub4elementLocation, sub4element.text.strip() ) )
                                        BibleOrgSysGlobals.checkXMLNoText( sub4element, sub4elementLocation )
                                        BibleOrgSysGlobals.checkXMLNoTail( sub4element, sub4elementLocation )
                                        if sub4element.tag == 'intervalFormats':
                                            BibleOrgSysGlobals.checkXMLNoAttributes( sub4element, sub4elementLocation )
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
                                                            logging.error( _("Unprocessed {!r} sub6element in {}").format( sub6element.tag, sub5elementLocation ) )
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
                                                            logging.error( _("Unprocessed {!r} sub6element in {}").format( sub6element.tag, sub5elementLocation ) )
                                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                                else:
                                                    logging.error( _("Unprocessed {!r} sub5element in {}").format( sub5element.tag, sub4elementLocation ) )
                                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                            dateTimeFormats[sub4element.tag] = sub4element.text
                                        elif sub4element.tag == 'availableFormats':
                                            BibleOrgSysGlobals.checkXMLNoAttributes( sub4element, sub4elementLocation )
                                            for sub5element in sub4element:
                                                sub5elementLocation = sub5element.tag + ' in ' + sub4elementLocation
                                                #if debuggingThisModule: print( "            ProcessingAF5 {} ({})…".format( sub5elementLocation, sub5element.text.strip() ) )
                                                BibleOrgSysGlobals.checkXMLNoTail( sub5element, sub5elementLocation )
                                                if sub5element.tag == 'dateFormatItem':
                                                    BibleOrgSysGlobals.checkXMLNoSubelements( sub5element, sub5elementLocation )
                                                    dfiID = dfiDraft = dfiCount = None
                                                    for attrib,value in sub5element.items():
                                                        #print( "hereDFI7", attrib, value )
                                                        if attrib=='id': dfiID = value # Things like MMMMd yyyyM
                                                        elif attrib=='draft': dfiDraft = value
                                                        elif attrib=='count': dfiCount = value # Things like one, other+
                                                        else:
                                                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub5elementLocation ) )
                                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                                    pass # Save text XXXXXXXXXXXXXXX
                                                else:
                                                    logging.error( _("Unprocessed {!r} sub5element in {}").format( sub5element.tag, sub4elementLocation ) )
                                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                        elif sub4element.tag == 'dateTimeFormatLength':
                                            dtflType = dtflDraft = None
                                            for attrib,value in sub4element.items():
                                                #print( "here7", attrib, value )
                                                if attrib=='type': dtflType = value
                                                elif attrib=='draft': dtflDraft = value
                                                else:
                                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub4elementLocation ) )
                                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                        else:
                                            logging.error( _("Unprocessed {!r} sub4element ({}) in {}").format( sub4element.tag, sub4element.text.strip() if sub4element.text else sub4element.text, sub3elementLocation ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                elif sub3element.tag == 'dateFormats':
                                    for sub4element in sub3element:
                                        sub4elementLocation = sub4element.tag + ' in ' + sub3elementLocation
                                        #if debuggingThisModule: print( "          ProcessingDF4 {} ({})…".format( sub4elementLocation, sub4element.text.strip() ) )
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
                                                            logging.error( _("Unprocessed {!r} sub6element in {}").format( sub6element.tag, sub5elementLocation ) )
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
                                                            logging.error( _("Unprocessed {!r} sub6element in {}").format( sub6element.tag, sub5elementLocation ) )
                                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                                else:
                                                    logging.error( _("Unprocessed {!r} sub5element in {}").format( sub5element.tag, sub4elementLocation ) )
                                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                            dateTimeFormats[sub4element.tag] = sub4element.text
                                        elif sub4element.tag == 'dateFormatLength':
                                            BibleOrgSysGlobals.checkXMLNoText( sub4element, sub4elementLocation )
                                            BibleOrgSysGlobals.checkXMLNoTail( sub4element, sub4elementLocation )
                                            dflType = None
                                            for attrib,value in sub4element.items():
                                                #print( "here7", attrib, value )
                                                #if attrib=='id': ifiID = value
                                                if attrib=='type': dflType = value
                                                else:
                                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub4elementLocation ) )
                                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                            for sub5element in sub4element:
                                                sub5elementLocation = sub5element.tag + ' in ' + sub4elementLocation
                                                #if debuggingThisModule: print( "            ProcessingD5 {} ({})…".format( sub5elementLocation, sub5element.text.strip() ) )
                                                BibleOrgSysGlobals.checkXMLNoAttributes( sub5element, sub5elementLocation )
                                                BibleOrgSysGlobals.checkXMLNoText( sub5element, sub5elementLocation )
                                                BibleOrgSysGlobals.checkXMLNoTail( sub5element, sub5elementLocation )
                                                if sub5element.tag == 'dateFormat':
                                                    for sub6element in sub5element:
                                                        sub6elementLocation = sub6element.tag + ' in ' + sub5elementLocation
                                                        #if debuggingThisModule: print( "              ProcessingD6 {} ({})…".format( sub6elementLocation, sub6element.text.strip() ) )
                                                        BibleOrgSysGlobals.checkXMLNoSubelements( sub6element, sub6elementLocation )
                                                        BibleOrgSysGlobals.checkXMLNoTail( sub6element, sub6elementLocation )
                                                        if sub6element.tag == 'pattern':
                                                            pDraft = None
                                                            for attrib,value in sub6element.items():
                                                                #print( "here7", attrib, value )
                                                                if attrib=='draft': pDraft = value; assert pDraft in draftValues
                                                                else:
                                                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub6elementLocation ) )
                                                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                                            pass # Save text xxxxxxxxxxxxxxx
                                                        else:
                                                            logging.error( _("Unprocessed {!r} sub6element in {}").format( sub6element.tag, sub5elementLocation ) )
                                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                                else:
                                                    logging.error( _("Unprocessed {!r} sub5element in {}").format( sub5element.tag, sub4elementLocation ) )
                                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                        else:
                                            logging.error( _("Unprocessed {!r} sub4element in {}").format( sub4element.tag, sub3elementLocation ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                elif sub3element.tag == 'dayPeriods':
                                    for sub4element in sub3element:
                                        sub4elementLocation = sub4element.tag + ' in ' + sub3elementLocation
                                        #if debuggingThisModule: print( "          ProcessingDP1 {} ({})…".format( sub4elementLocation, sub4element.text.strip() ) )
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
                                                            logging.error( _("Unprocessed {!r} sub6element ({}) in {}").format( sub6element.tag, sub6element.text.strip() if sub6element.text else sub6element.text, sub5elementLocation ) )
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
                                                            logging.error( _("Unprocessed {!r} sub6element in {}").format( sub6element.tag, sub5elementLocation ) )
                                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                                else:
                                                    logging.error( _("Unprocessed {!r} sub5element ({}) in {}").format( sub5element.tag, sub5element.text.strip() if sub5element.text else sub5element.text, sub4elementLocation ) )
                                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                            dayPeriods[sub4element.tag] = sub4element.text
                                        else:
                                            logging.error( _("Unprocessed {!r} sub4element ({}) in {}").format( sub4element.tag, sub4element.text.strip() if sub4element.text else sub4element.text, sub3elementLocation ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                elif sub3element.tag == 'months':
                                    for sub4element in sub3element:
                                        sub4elementLocation = sub4element.tag + ' in ' + sub3elementLocation
                                        #if debuggingThisModule: print( "          ProcessingDP1 {} ({})…".format( sub4elementLocation, sub4element.text.strip() ) )
                                        BibleOrgSysGlobals.checkXMLNoText( sub4element, sub4elementLocation )
                                        BibleOrgSysGlobals.checkXMLNoTail( sub4element, sub4elementLocation )
                                        if sub4element.tag == 'monthContext':
                                            mcType = None
                                            for attrib,value in sub4element.items():
                                                #print( "here7", attrib, value )
                                                #if attrib=='draft': draft = value
                                                if attrib=='type': mcType = value
                                                else:
                                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub4elementLocation ) )
                                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                            for sub5element in sub4element:
                                                sub5elementLocation = sub5element.tag + ' in ' + sub4elementLocation
                                                #if debuggingThisModule: print( "            ProcessingD5 {} ({})…".format( sub5elementLocation, sub5element.text.strip() ) )
                                                BibleOrgSysGlobals.checkXMLNoText( sub5element, sub5elementLocation )
                                                BibleOrgSysGlobals.checkXMLNoTail( sub5element, sub5elementLocation )
                                                if sub5element.tag == 'monthWidth':
                                                    mwType = None
                                                    for attrib,value in sub5element.items():
                                                        #print( "here7", attrib, value )
                                                        #if attrib=='draft': draft = value
                                                        if attrib=='type': mwType = value
                                                        else:
                                                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub5elementLocation ) )
                                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                                    for sub6element in sub5element:
                                                        sub6elementLocation = sub6element.tag + ' in ' + sub5elementLocation
                                                        #if debuggingThisModule: print( "              ProcessingD6 {} ({})…".format( sub6elementLocation, sub6element.text.strip() ) )
                                                        BibleOrgSysGlobals.checkXMLNoSubelements( sub6element, sub6elementLocation )
                                                        BibleOrgSysGlobals.checkXMLNoTail( sub6element, sub6elementLocation )
                                                        if sub6element.tag == 'month':
                                                            mType = mDraft = None
                                                            for attrib,value in sub6element.items():
                                                                #print( "here7", attrib, value )
                                                                if attrib=='type': mType = value
                                                                elif attrib=='draft': mDraft = value
                                                                else:
                                                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub6elementLocation ) )
                                                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                                            pass # Save text field XXXXXXXXXXXXXX
                                                        else:
                                                            logging.error( _("Unprocessed {!r} sub6element ({}) in {}").format( sub6element.tag, sub6element.text.strip() if sub6element.text else sub6element.text, sub5elementLocation ) )
                                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                                else:
                                                    logging.error( _("Unprocessed {!r} sub5element ({}) in {}").format( sub5element.tag, sub5element.text.strip() if sub5element.text else sub5element.text, sub4elementLocation ) )
                                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                        else:
                                            logging.error( _("Unprocessed {!r} sub4element ({}) in {}").format( sub4element.tag, sub4element.text.strip() if sub4element.text else sub4element.text, sub3elementLocation ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                elif sub3element.tag == 'days':
                                    for sub4element in sub3element:
                                        sub4elementLocation = sub4element.tag + ' in ' + sub3elementLocation
                                        #if debuggingThisModule: print( "          ProcessingDP1 {} ({})…".format( sub4elementLocation, sub4element.text.strip() ) )
                                        BibleOrgSysGlobals.checkXMLNoText( sub4element, sub4elementLocation )
                                        BibleOrgSysGlobals.checkXMLNoTail( sub4element, sub4elementLocation )
                                        if sub4element.tag == 'dayContext':
                                            dcType = None
                                            for attrib,value in sub4element.items():
                                                #print( "here7", attrib, value )
                                                #if attrib=='draft': draft = value
                                                if attrib=='type': dcType = value
                                                else:
                                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub4elementLocation ) )
                                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                            for sub5element in sub4element:
                                                sub5elementLocation = sub5element.tag + ' in ' + sub4elementLocation
                                                #if debuggingThisModule: print( "            ProcessingD5 {} ({})…".format( sub5elementLocation, sub5element.text.strip() ) )
                                                BibleOrgSysGlobals.checkXMLNoText( sub5element, sub5elementLocation )
                                                BibleOrgSysGlobals.checkXMLNoTail( sub5element, sub5elementLocation )
                                                if sub5element.tag == 'dayWidth':
                                                    dwType = None
                                                    for attrib,value in sub5element.items():
                                                        #print( "here7", attrib, value )
                                                        #if attrib=='draft': draft = value
                                                        if attrib=='type': dwType = value
                                                        else:
                                                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub5elementLocation ) )
                                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                                    for sub6element in sub5element:
                                                        sub6elementLocation = sub6element.tag + ' in ' + sub5elementLocation
                                                        #if debuggingThisModule: print( "              ProcessingD6 {} ({})…".format( sub6elementLocation, sub6element.text.strip() ) )
                                                        BibleOrgSysGlobals.checkXMLNoSubelements( sub6element, sub6elementLocation )
                                                        BibleOrgSysGlobals.checkXMLNoTail( sub6element, sub6elementLocation )
                                                        if sub6element.tag == 'day':
                                                            mType = mDraft = None
                                                            for attrib,value in sub6element.items():
                                                                #print( "here7", attrib, value )
                                                                if attrib=='type': mType = value
                                                                elif attrib=='draft': mDraft = value
                                                                else:
                                                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub6elementLocation ) )
                                                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                                            pass # Save text field XXXXXXXXXXXXXX
                                                        else:
                                                            logging.error( _("Unprocessed {!r} sub6element ({}) in {}").format( sub6element.tag, sub6element.text.strip() if sub6element.text else sub6element.text, sub5elementLocation ) )
                                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                                else:
                                                    logging.error( _("Unprocessed {!r} sub5element ({}) in {}").format( sub5element.tag, sub5element.text.strip() if sub5element.text else sub5element.text, sub4elementLocation ) )
                                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                        else:
                                            logging.error( _("Unprocessed {!r} sub4element ({}) in {}").format( sub4element.tag, sub4element.text.strip() if sub4element.text else sub4element.text, sub3elementLocation ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                elif sub3element.tag == 'timeFormats':
                                    for sub4element in sub3element:
                                        sub4elementLocation = sub4element.tag + ' in ' + sub3elementLocation
                                        #if debuggingThisModule: print( "          ProcessingDP1 {} ({})…".format( sub4elementLocation, sub4element.text.strip() ) )
                                        BibleOrgSysGlobals.checkXMLNoText( sub4element, sub4elementLocation )
                                        BibleOrgSysGlobals.checkXMLNoTail( sub4element, sub4elementLocation )
                                        if sub4element.tag == 'timeFormatLength':
                                            tflType = None
                                            for attrib,value in sub4element.items():
                                                #print( "here7", attrib, value )
                                                #if attrib=='draft': draft = value
                                                if attrib=='type': tflType = value
                                                else:
                                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub4elementLocation ) )
                                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                            for sub5element in sub4element:
                                                sub5elementLocation = sub5element.tag + ' in ' + sub4elementLocation
                                                #if debuggingThisModule: print( "            ProcessingD5 {} ({})…".format( sub5elementLocation, sub5element.text.strip() ) )
                                                BibleOrgSysGlobals.checkXMLNoAttributes( sub5element, sub5elementLocation )
                                                BibleOrgSysGlobals.checkXMLNoText( sub5element, sub5elementLocation )
                                                BibleOrgSysGlobals.checkXMLNoTail( sub5element, sub5elementLocation )
                                                if sub5element.tag == 'timeFormat':
                                                    for sub6element in sub5element:
                                                        sub6elementLocation = sub6element.tag + ' in ' + sub5elementLocation
                                                        #if debuggingThisModule: print( "              ProcessingD6 {} ({})…".format( sub6elementLocation, sub6element.text.strip() ) )
                                                        BibleOrgSysGlobals.checkXMLNoAttributes( sub6element, sub6elementLocation )
                                                        BibleOrgSysGlobals.checkXMLNoSubelements( sub6element, sub6elementLocation )
                                                        BibleOrgSysGlobals.checkXMLNoTail( sub6element, sub6elementLocation )
                                                        if sub6element.tag == 'pattern':
                                                            pass # Save text field XXXXXXXXXXXXXX
                                                        else:
                                                            logging.error( _("Unprocessed {!r} sub6element ({}) in {}").format( sub6element.tag, sub6element.text.strip() if sub6element.text else sub6element.text, sub5elementLocation ) )
                                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                                else:
                                                    logging.error( _("Unprocessed {!r} sub5element ({}) in {}").format( sub5element.tag, sub5element.text.strip() if sub5element.text else sub5element.text, sub4elementLocation ) )
                                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                        else:
                                            logging.error( _("Unprocessed {!r} sub4element ({}) in {}").format( sub4element.tag, sub4element.text.strip() if sub4element.text else sub4element.text, sub3elementLocation ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                elif sub3element.tag == 'cyclicNameSets':
                                    for sub4element in sub3element:
                                        sub4elementLocation = sub4element.tag + ' in ' + sub3elementLocation
                                        if debuggingThisModule: print( "          ProcessingDP1 {} ({})…".format( sub4elementLocation, sub4element.text.strip() ) )
                                        BibleOrgSysGlobals.checkXMLNoText( sub4element, sub4elementLocation )
                                        BibleOrgSysGlobals.checkXMLNoTail( sub4element, sub4elementLocation )
                                        if sub4element.tag == 'cyclicNameSet':
                                            cnsType = None
                                            for attrib,value in sub4element.items():
                                                #print( "herecns7", attrib, value )
                                                #if attrib=='draft': draft = value
                                                if attrib=='type': cnsType = value; assert cnsType in ('zodiacs','dayParts','days','solarTerms','years','months',)
                                                else:
                                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub4elementLocation ) )
                                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                            for sub5element in sub4element:
                                                sub5elementLocation = sub5element.tag + ' in ' + sub4elementLocation
                                                #if debuggingThisModule: print( "            ProcessingD5 {} ({})…".format( sub5elementLocation, sub5element.text.strip() ) )
                                                BibleOrgSysGlobals.checkXMLNoText( sub5element, sub5elementLocation )
                                                BibleOrgSysGlobals.checkXMLNoTail( sub5element, sub5elementLocation )
                                                if sub5element.tag == 'cyclicNameContext':
                                                    cncType = None
                                                    for attrib,value in sub5element.items():
                                                        #print( "herecnc7", attrib, value )
                                                        #if attrib=='draft': draft = value
                                                        if attrib=='type': cncType = value; assert cncType in ('format',)
                                                        else:
                                                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub5elementLocation ) )
                                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                                    for sub6element in sub5element:
                                                        sub6elementLocation = sub6element.tag + ' in ' + sub5elementLocation
                                                        #if debuggingThisModule: print( "              ProcessingD6 {} ({})…".format( sub6elementLocation, sub6element.text.strip() ) )
                                                        BibleOrgSysGlobals.checkXMLNoText( sub6element, sub6elementLocation )
                                                        BibleOrgSysGlobals.checkXMLNoTail( sub6element, sub6elementLocation )
                                                        if sub6element.tag == 'cyclicNameWidth':
                                                            cnwType = None
                                                            for attrib,value in sub6element.items():
                                                                #print( "herecnw7", attrib, value )
                                                                #if attrib=='draft': draft = value
                                                                if attrib=='type': cnwType = value; assert cnwType in ('abbreviated','narrow','wide',)
                                                                else:
                                                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub6elementLocation ) )
                                                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                                            for sub7element in sub6element:
                                                                sub7elementLocation = sub7element.tag + ' in ' + sub6elementLocation
                                                                #if debuggingThisModule: print( "              ProcessingD6 {} ({})…".format( sub6elementLocation, sub6element.text.strip() ) )
                                                                BibleOrgSysGlobals.checkXMLNoSubelements( sub7element, sub7elementLocation )
                                                                BibleOrgSysGlobals.checkXMLNoTail( sub7element, sub7elementLocation )
                                                                if sub7element.tag == 'cyclicName':
                                                                    cnType = None
                                                                    for attrib,value in sub6element.items():
                                                                        #print( "hereCN7", attrib, value )
                                                                        #if attrib=='draft': draft = value
                                                                        if attrib=='type': cnType = value; assert cnType in ('1','abbreviated','narrow','wide',)
                                                                        else:
                                                                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub6elementLocation ) )
                                                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                                                    pass # Save text field XXXXXXXXXXXXXX
                                                                else:
                                                                    logging.error( _("Unprocessed {!r} sub7element ({}) in {}").format( sub7element.tag, sub7element.text.strip() if sub7element.text else sub7element.text, sub6elementLocation ) )
                                                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                                        else:
                                                            logging.error( _("Unprocessed {!r} sub6element ({}) in {}").format( sub6element.tag, sub6element.text.strip() if sub6element.text else sub6element.text, sub5elementLocation ) )
                                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                                else:
                                                    logging.error( _("Unprocessed {!r} sub5element ({}) in {}").format( sub5element.tag, sub5element.text.strip() if sub5element.text else sub5element.text, sub4elementLocation ) )
                                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                        else:
                                            logging.error( _("Unprocessed {!r} sub4element ({}) in {}").format( sub4element.tag, sub4element.text.strip() if sub4element.text else sub4element.text, sub3elementLocation ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                elif sub3element.tag == 'eras':
                                    for sub4element in sub3element:
                                        sub4elementLocation = sub4element.tag + ' in ' + sub3elementLocation
                                        #if debuggingThisModule: print( "          ProcessingE1 {} ({})…".format( sub4elementLocation, sub4element.text.strip() ) )
                                        BibleOrgSysGlobals.checkXMLNoAttributes( sub4element, sub4elementLocation )
                                        BibleOrgSysGlobals.checkXMLNoText( sub4element, sub4elementLocation )
                                        BibleOrgSysGlobals.checkXMLNoTail( sub4element, sub4elementLocation )
                                        if sub4element.tag == 'eraAbbr':
                                            #cnsType = None
                                            #for attrib,value in sub4element.items():
                                                ##print( "hereEA7", attrib, value )
                                                ##if attrib=='draft': draft = value
                                                #if attrib=='xtype': cnsType = value; assert cnsType in ('zodiacs',)
                                                #else:
                                                    #logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub4elementLocation ) )
                                                    #if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                            for sub5element in sub4element:
                                                sub5elementLocation = sub5element.tag + ' in ' + sub4elementLocation
                                                #if debuggingThisModule: print( "            ProcessingEA5 {} ({})…".format( sub5elementLocation, sub5element.text.strip() ) )
                                                BibleOrgSysGlobals.checkXMLNoSubelements( sub5element, sub5elementLocation )
                                                BibleOrgSysGlobals.checkXMLNoTail( sub5element, sub5elementLocation )
                                                if sub5element.tag == 'era':
                                                    eDraft = eType = eAlt = None
                                                    for attrib,value in sub5element.items():
                                                        #print( "hereE7", attrib, value )
                                                        if attrib=='type': eType = value # assert eType in ('0','1','10','100','101',)
                                                        elif attrib=='draft': eDraft = value; assert eDraft in draftValues
                                                        elif attrib=='alt': eAlt = value; assert eAlt in ('variant',)
                                                        else:
                                                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub5elementLocation ) )
                                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                                    pass # save Text XXXXXXXXXXXXXXXXXXXXXXXXXXX
                                                else:
                                                    logging.error( _("Unprocessed {!r} sub5element ({}) in {}").format( sub5element.tag, sub5element.text.strip() if sub5element.text else sub5element.text, sub4elementLocation ) )
                                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                        elif sub4element.tag == 'eraNames':
                                            #cnsType = None
                                            #for attrib,value in sub4element.items():
                                                ##print( "hereEA7", attrib, value )
                                                ##if attrib=='draft': draft = value
                                                #if attrib=='xtype': cnsType = value; assert cnsType in ('zodiacs',)
                                                #else:
                                                    #logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub4elementLocation ) )
                                                    #if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                            for sub5element in sub4element:
                                                sub5elementLocation = sub5element.tag + ' in ' + sub4elementLocation
                                                if debuggingThisModule: print( "            ProcessingEN5 {} ({})…".format( sub5elementLocation, sub5element.text.strip() ) )
                                                BibleOrgSysGlobals.checkXMLNoSubelements( sub5element, sub5elementLocation )
                                                BibleOrgSysGlobals.checkXMLNoTail( sub5element, sub5elementLocation )
                                                if sub5element.tag == 'era':
                                                    eDraft = eType = eAlt = None
                                                    for attrib,value in sub5element.items():
                                                        #print( "hereE8", attrib, value )
                                                        if attrib=='type': eType = value # assert eType in ('0','1','10','100','101',)
                                                        #elif attrib=='xdraft': eDraft = value; assert eDraft in draftValues
                                                        elif attrib=='alt': eAlt = value; assert eAlt in ('variant',)
                                                        else:
                                                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub5elementLocation ) )
                                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                                    pass # save Text XXXXXXXXXXXXXXXXXXXXXXXXXXX
                                                else:
                                                    logging.error( _("Unprocessed {!r} sub5element ({}) in {}").format( sub5element.tag, sub5element.text.strip() if sub5element.text else sub5element.text, sub4elementLocation ) )
                                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                        elif sub4element.tag == 'eraNarrow':
                                            #cnsType = None
                                            #for attrib,value in sub4element.items():
                                                ##print( "hereEA7", attrib, value )
                                                ##if attrib=='draft': draft = value
                                                #if attrib=='xtype': cnsType = value; assert cnsType in ('zodiacs',)
                                                #else:
                                                    #logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub4elementLocation ) )
                                                    #if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                            for sub5element in sub4element:
                                                sub5elementLocation = sub5element.tag + ' in ' + sub4elementLocation
                                                #if debuggingThisModule: print( "            ProcessingEN6 {} ({})…".format( sub5elementLocation, sub5element.text.strip() ) )
                                                BibleOrgSysGlobals.checkXMLNoSubelements( sub5element, sub5elementLocation )
                                                BibleOrgSysGlobals.checkXMLNoTail( sub5element, sub5elementLocation )
                                                if sub5element.tag == 'era':
                                                    eDraft = eType = eAlt = None
                                                    for attrib,value in sub5element.items():
                                                        #print( "hereE8", attrib, value )
                                                        if attrib=='type': eType = value # assert eType in ('0','1','10','100','101',)
                                                        elif attrib=='draft': eDraft = value; assert eDraft in draftValues
                                                        elif attrib=='alt': eAlt = value; assert eAlt in ('variant',)
                                                        else:
                                                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub5elementLocation ) )
                                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                                    pass # save Text XXXXXXXXXXXXXXXXXXXXXXXXXXX
                                                else:
                                                    logging.error( _("Unprocessed {!r} sub5element ({}) in {}").format( sub5element.tag, sub5element.text.strip() if sub5element.text else sub5element.text, sub4elementLocation ) )
                                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                        else:
                                            logging.error( _("Unprocessed {!r} sub4element ({}) in {}").format( sub4element.tag, sub4element.text.strip() if sub4element.text else sub4element.text, sub3elementLocation ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                elif sub3element.tag == 'quarters':
                                    for sub4element in sub3element:
                                        sub4elementLocation = sub4element.tag + ' in ' + sub3elementLocation
                                        #if debuggingThisModule: print( "          ProcessingE1 {} ({})…".format( sub4elementLocation, sub4element.text.strip() ) )
                                        BibleOrgSysGlobals.checkXMLNoText( sub4element, sub4elementLocation )
                                        BibleOrgSysGlobals.checkXMLNoTail( sub4element, sub4elementLocation )
                                        if sub4element.tag == 'quarterContext':
                                            qcType = None
                                            for attrib,value in sub4element.items():
                                                #print( "hereQC7", attrib, value )
                                                #if attrib=='draft': draft = value
                                                if attrib=='type': qcType = value; assert qcType in ('format','stand-alone',)
                                                else:
                                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub4elementLocation ) )
                                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                            for sub5element in sub4element:
                                                sub5elementLocation = sub5element.tag + ' in ' + sub4elementLocation
                                                #if debuggingThisModule: print( "            ProcessingEA5 {} ({})…".format( sub5elementLocation, sub5element.text.strip() ) )
                                                BibleOrgSysGlobals.checkXMLNoTail( sub5element, sub5elementLocation )
                                                if sub5element.tag == 'quarterWidth':
                                                    eDraft = qwType = None
                                                    for attrib,value in sub5element.items():
                                                        #print( "hereQW7", attrib, value )
                                                        if attrib=='type': qwType = value; assert qwType in ('abbreviated','narrow','wide',)
                                                        #elif attrib=='xdraft': eDraft = value; assert eDraft in draftValues
                                                        else:
                                                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub5elementLocation ) )
                                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                                    for sub6element in sub5element:
                                                        sub6elementLocation = sub6element.tag + ' in ' + sub5elementLocation
                                                        #if debuggingThisModule: print( "              ProcessingD6 {} ({})…".format( sub6elementLocation, sub6element.text.strip() ) )
                                                        BibleOrgSysGlobals.checkXMLNoSubelements( sub6element, sub6elementLocation )
                                                        BibleOrgSysGlobals.checkXMLNoTail( sub6element, sub6elementLocation )
                                                        if sub6element.tag == 'quarter':
                                                            qType = None
                                                            for attrib,value in sub6element.items():
                                                                #print( "hereQ7", attrib, value )
                                                                #if attrib=='draft': draft = value
                                                                if attrib=='type': qType = value; assert qType in ('1','2','3','4',)
                                                                else:
                                                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub6elementLocation ) )
                                                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                                            pass # Save text field XXXXXXXXXXXXXX
                                                        else:
                                                            logging.error( _("Unprocessed {!r} sub6element ({}) in {}").format( sub6element.tag, sub6element.text.strip() if sub6element.text else sub6element.text, sub5elementLocation ) )
                                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                                else:
                                                    logging.error( _("Unprocessed {!r} sub5element ({}) in {}").format( sub5element.tag, sub5element.text.strip() if sub5element.text else sub5element.text, sub4elementLocation ) )
                                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                        else:
                                            logging.error( _("Unprocessed {!r} sub4element ({}) in {}").format( sub4element.tag, sub4element.text.strip() if sub4element.text else sub4element.text, sub3elementLocation ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                else:
                                    logging.error( _("Unprocessed {!r} sub3element ({}) in {}").format( sub3element.tag, sub3element.text.strip() if sub3element.text else sub3element.text, sub2elementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                        else:
                            logging.error( _("Unprocessed {!r} sub2element ({}) in {}").format( sub2element.tag, sub2element.text.strip() if sub2element.text else sub2element.text, subelementLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                    if dateTimeFormats:
                        assert 'dateTimeFormats' not in dCalendar
                        dCalendar['dateTimeFormats'] = dateTimeFormats
                    if dayPeriods:
                        assert 'dayPeriods' not in dCalendar
                        dCalendar['dayPeriods'] = dayPeriods
                    assert cType not in dCalendars
                    dCalendars[cType] = dCalendar
                    if dCalendars:
                        assert subelement.tag not in dates
                        dates[subelement.tag] = dCalendars
                elif subelement.tag == 'fields':
                    for sub2element in subelement:
                        sub2elementLocation = sub2element.tag + ' in ' + subelementLocation
                        #if debuggingThisModule: print( "      Processing3b {} ({})…".format( sub2elementLocation, sub2element.text.strip() ) )
                        BibleOrgSysGlobals.checkXMLNoText( sub2element, sub2elementLocation )
                        BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2elementLocation )
                        if sub2element.tag == 'field':
                            draft = fType = alt = None
                            for attrib,value in sub2element.items():
                                #print( "hereF8", attrib, value )
                                #if attrib=='draft': draft = value
                                if attrib=='type': fType = value # assert fType in ('day','day-narrow','day-short','dayperiod','era','fri','fri-narrow','fri-short','hour',...)
                                #elif attrib=='alt': alt = value
                                else:
                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub2elementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                            for sub3element in sub2element:
                                sub3elementLocation = sub3element.tag + ' in ' + sub2elementLocation
                                #if debuggingThisModule: print( "        Processing {}…".format( sub3elementLocation ) )
                                BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3elementLocation )
                                if sub3element.tag == 'displayName':
                                    BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3elementLocation )
                                    draft = dnType = alt = None
                                    for attrib,value in sub3element.items():
                                        if attrib=='draft': draft = value
                                        #elif attrib=='type': dnType = value
                                        #elif attrib=='alt': alt = value
                                        else:
                                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub3elementLocation ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                elif sub3element.tag == 'relativeTime':
                                    BibleOrgSysGlobals.checkXMLNoText( sub3element, sub3elementLocation )
                                    BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3elementLocation )
                                    rtType = alt = None
                                    for attrib,value in sub3element.items():
                                        #if attrib=='draft': draft = value
                                        if attrib=='type': rtType = value
                                        #elif attrib=='alt': alt = value
                                        else:
                                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub3elementLocation ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                    for sub4element in sub3element:
                                        sub4elementLocation = sub4element.tag + ' in ' + sub3elementLocation
                                        #if debuggingThisModule: print( "          ProcessingRT4 {} ({})…".format( sub4elementLocation, sub4element.text.strip() ) )
                                        BibleOrgSysGlobals.checkXMLNoSubelements( sub4element, sub4elementLocation )
                                        BibleOrgSysGlobals.checkXMLNoTail( sub4element, sub4elementLocation )
                                        if sub4element.tag == 'relativeTimePattern':
                                            rtpCount = rtpDraft = None
                                            for attrib,value in sub4element.items():
                                                if attrib=='count': rtpCount = value
                                                elif attrib=='draft': rtpDraft = value
                                                else:
                                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub4elementLocation ) )
                                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                            pass # save Text XXXXXXXXXXXXXXXXXXX
                                elif sub3element.tag == 'alias':
                                    BibleOrgSysGlobals.checkXMLNoText( sub3element, sub3elementLocation )
                                    BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3elementLocation )
                                    BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3elementLocation )
                                    aPath = aSource = None
                                    for attrib,value in sub3element.items():
                                        #if attrib=='draft': draft = value
                                        if attrib=='path': aPath = value
                                        elif attrib=='source': aSource = value
                                        else:
                                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub3elementLocation ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                elif sub3element.tag == 'relative':
                                    BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3elementLocation )
                                    BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3elementLocation )
                                    rType = rDraft = None
                                    for attrib,value in sub3element.items():
                                        if attrib=='type': rType = value
                                        elif attrib=='draft': rDraft = value
                                        else:
                                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub3elementLocation ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                    pass # save Text XXXXXXXXXXXXXXXXXXX
                                elif sub3element.tag == 'relativePeriod':
                                    BibleOrgSysGlobals.checkXMLNoAttributes( sub3element, sub3elementLocation )
                                    BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3elementLocation )
                                    BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3elementLocation )
                                    #rType = rDraft = None
                                    #for attrib,value in sub3element.items():
                                        #if attrib=='xtype': rType = value
                                        #elif attrib=='xdraft': rDraft = value
                                        #else:
                                            #logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub3elementLocation ) )
                                            #if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                    pass # save Text XXXXXXXXXXXXXXXXXXX
                                else:
                                    logging.error( _("Unprocessed {!r} sub3element ({}) in {}").format( sub3element.tag, sub3element.text.strip() if sub3element.text else sub3element.text, sub2elementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                            #assert fType not in fields # losing data here XXXXXXXXXXXXXXXXXXXXXXX
                            if fType in fields: logging.critical( "Losing data here for {} fields field".format( fType ) )
                            fields[fType] = (fType,sub2element.text,draft,alt)
                        else:
                            logging.error( _("Unprocessed {!r} sub2element ({}) in {}").format( sub2element.tag, sub2element.text.strip() if sub2element.text else sub2element.text, subelementLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                    if fields:
                        assert subelement.tag not in dates
                        dates[subelement.tag] = fields
                elif subelement.tag == 'timeZoneNames':
                    metazones = {}
                    regionFormats = {}
                    for sub2element in subelement:
                        sub2elementLocation = sub2element.tag + ' in ' + subelementLocation
                        #if debuggingThisModule: print( "      Processing3g {} ({})…".format( sub2elementLocation, sub2element.text.strip() ) )
                        BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2elementLocation )
                        metazones = {}
                        if sub2element.tag == 'metazone':
                            BibleOrgSysGlobals.checkXMLNoText( sub2element, sub2elementLocation )
                            mzType = None
                            for attrib,value in sub2element.items():
                                #print( "here58", attrib, value )
                                if attrib=='type': mzType = value
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
                                        if sub4element.tag in ('generic','standard','daylight'):
                                            metazone[sub3element.tag][sub4element.tag] = sub4element.text
                                        else:
                                            logging.error( _("Unprocessed {!r} sub4element in {}").format( sub4element.tag, sub3elementLocation ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                elif sub3element.tag == 'long':
                                    if sub3element.tag not in metazone:
                                        metazone[sub3element.tag] = {}
                                    for sub4element in sub3element:
                                        sub4elementLocation = sub4element.tag + ' in ' + sub3elementLocation
                                        #if debuggingThisModule: print( "          Processing9 {} ({})…".format( sub4elementLocation, sub4element.text.strip() ) )
                                        BibleOrgSysGlobals.checkXMLNoAttributes( sub4element, sub4elementLocation )
                                        BibleOrgSysGlobals.checkXMLNoSubelements( sub4element, sub4elementLocation )
                                        BibleOrgSysGlobals.checkXMLNoTail( sub4element, sub4elementLocation )
                                        if sub4element.tag in ('generic','standard','daylight'):
                                            metazone[sub3element.tag][sub4element.tag] = sub4element.text
                                        else:
                                            logging.error( _("Unprocessed {!r} sub4element in {}").format( sub4element.tag, sub3elementLocation ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                else:
                                    logging.error( _("Unprocessed {!r} sub3element ({}) in {}").format( sub3element.tag, sub3element.text.strip() if sub3element.text else sub3element.text, sub2elementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                            if metazone:
                                assert mzType not in metazones
                                metazones[mzType] = metazone
                        elif sub2element.tag == 'zone':
                            BibleOrgSysGlobals.checkXMLNoText( sub2element, sub2elementLocation )
                            zType = None
                            for attrib,value in sub2element.items():
                                #print( "here58", attrib, value )
                                if attrib=='type': zType = value
                                else:
                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub2elementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                            zone = {}
                            for sub3element in sub2element:
                                sub3elementLocation = sub3element.tag + ' in ' + sub2elementLocation
                                #if debuggingThisModule: print( "        Processing8 {} ({})…".format( sub3elementLocation, sub3element.text.strip() ) )
                                BibleOrgSysGlobals.checkXMLNoAttributes( sub3element, sub3elementLocation )
                                BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3elementLocation )
                                if sub3element.tag == 'short':
                                    BibleOrgSysGlobals.checkXMLNoText( sub3element, sub3elementLocation )
                                    if sub3element.tag not in zone:
                                        zone[sub3element.tag] = {}
                                    for sub4element in sub3element:
                                        sub4elementLocation = sub4element.tag + ' in ' + sub3elementLocation
                                        #if debuggingThisModule: print( "          Processing9 {} ({})…".format( sub4elementLocation, sub4element.text.strip() ) )
                                        BibleOrgSysGlobals.checkXMLNoAttributes( sub4element, sub4elementLocation )
                                        BibleOrgSysGlobals.checkXMLNoSubelements( sub4element, sub4elementLocation )
                                        BibleOrgSysGlobals.checkXMLNoTail( sub4element, sub4elementLocation )
                                        if sub4element.tag in ('generic','standard','daylight'):
                                            zone[sub3element.tag][sub4element.tag] = sub4element.text
                                        #elif sub4element.tag == 'standard':
                                            #zone[sub3element.tag][sub4element.tag] = sub4element.text
                                        #elif sub4element.tag == 'daylight':
                                            #zone[sub3element.tag][sub4element.tag] = sub4element.text
                                        else:
                                            logging.error( _("Unprocessed {!r} sub4element in {}").format( sub4element.tag, sub3elementLocation ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                elif sub3element.tag == 'long':
                                    BibleOrgSysGlobals.checkXMLNoText( sub3element, sub3elementLocation )
                                    if sub3element.tag not in zone:
                                        zone[sub3element.tag] = {}
                                    for sub4element in sub3element:
                                        sub4elementLocation = sub4element.tag + ' in ' + sub3elementLocation
                                        #if debuggingThisModule: print( "          Processing9 {} ({})…".format( sub4elementLocation, sub4element.text.strip() ) )
                                        BibleOrgSysGlobals.checkXMLNoAttributes( sub4element, sub4elementLocation )
                                        BibleOrgSysGlobals.checkXMLNoSubelements( sub4element, sub4elementLocation )
                                        BibleOrgSysGlobals.checkXMLNoTail( sub4element, sub4elementLocation )
                                        if sub4element.tag in ('generic','standard','daylight'):
                                            zone[sub3element.tag][sub4element.tag] = sub4element.text
                                        #elif sub4element.tag == 'standard':
                                            #zone[sub3element.tag][sub4element.tag] = sub4element.text
                                        #elif sub4element.tag == 'daylight':
                                            #zone[sub3element.tag][sub4element.tag] = sub4element.text
                                        else:
                                            logging.error( _("Unprocessed {!r} sub4element in {}").format( sub4element.tag, sub3elementLocation ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                elif sub3element.tag == 'exemplarCity':
                                    BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3elementLocation )
                                    #assert sub3element.tag not in zone # losing data here XXXXXXXXXXXXXXXXXXXXXXX
                                    if sub3element.tag in zone: logging.critical( "Losing data here for {} zone field".format( sub3element.tag ) )
                                    zone[sub3element.tag] = sub3element.text
                                else:
                                    logging.error( _("Unprocessed {!r} sub3element ({}) in {}").format( sub3element.tag, sub3element.text.strip() if sub3element.text else sub3element.text, sub2elementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                        elif sub2element.tag == 'regionFormat':
                            BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2elementLocation )
                            BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2elementLocation )
                            rfType = None
                            for attrib,value in sub2element.items():
                                #print( "hereRF58", attrib, value )
                                if attrib=='type': rfType = value; assert rfType in ('daylight','standard',)
                                else:
                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub2elementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                            regionFormats[rfType] = sub2element.text
                        else:
                            logging.error( _("Unprocessed {!r} sub2element ({}) in {}").format( sub2element.tag, sub2element.text.strip() if sub2element.text else sub2element.text, subelementLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                    if timeZoneNames:
                        assert subelement.tag not in dates
                        dates[subelement.tag] = timeZoneNames
                else:
                    logging.error( _("Unprocessed {!r} subelement ({}) in {}").format( subelement.tag, subelement.text.strip() if subelement.text else subelement.text, elementLocation ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
            return dates
        # end of loadDates


        def loadUnits( element, elementLocation, units ):
            """
            Returns the updated dictionary.
            """
            for subelement in element:
                subelementLocation = subelement.tag + ' in ' + elementLocation
                #if debuggingThisModule: print( "    Processing {}…".format( subelementLocation ) )
                BibleOrgSysGlobals.checkXMLNoText( subelement, subelementLocation )
                BibleOrgSysGlobals.checkXMLNoTail( subelement, subelementLocation )
                if subelement.tag == 'unitLength':
                    ulLong = ulType = None
                    for attrib,value in subelement.items():
                        if attrib=='long': ulLong = value
                        #elif attrib=='digits': digits = value
                        elif attrib=='type': ulType = value
                        else:
                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, subelementLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    for sub2element in subelement:
                        sub2elementLocation = sub2element.tag + ' in ' + subelementLocation
                        #if debuggingThisModule: print( "      Processing {} ({})…".format( sub2elementLocation, sub2element.text.strip() ) )
                        BibleOrgSysGlobals.checkXMLNoText( sub2element, sub2elementLocation )
                        BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2elementLocation )
                        if sub2element.tag == 'unit':
                            uType = None
                            for attrib,value in subelement.items():
                                #if attrib=='long': ulLong = value
                                #elif attrib=='digits': digits = value
                                if attrib=='type': uType = value
                                else:
                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub2elementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                            for sub3element in sub2element:
                                sub3elementLocation = sub3element.tag + ' in ' + sub2elementLocation
                                #if debuggingThisModule: print( "        Processing {} ({})…".format( sub3elementLocation, sub3element.text.strip() ) )
                                BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3elementLocation )
                                BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3elementLocation )
                                if sub3element.tag == 'displayName':
                                    dnDraft = None
                                    for attrib,value in sub3element.items():
                                        #if attrib=='draft': draft = value
                                        if attrib=='draft': dnDraft = value
                                        #elif attrib=='alt': alt = value
                                        else:
                                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub3elementLocation ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                    pass # Save text XXXXXXXXXXXXX
                                elif sub3element.tag == 'unitPattern':
                                    upCount = upDraft = None
                                    for attrib,value in sub3element.items():
                                        if attrib=='count': upCount = value
                                        elif attrib=='draft': upDraft = value
                                        else:
                                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub3elementLocation ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                    pass # Save text XXXXXXXXXXXXX
                                elif sub3element.tag == 'perUnitPattern':
                                    pupDraft = None
                                    for attrib,value in sub3element.items():
                                        #if attrib=='draft': draft = value
                                        if attrib=='draft': pupDraft = value
                                        #elif attrib=='alt': alt = value
                                        else:
                                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub3elementLocation ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                    pass # Save text XXXXXXXXXXXXX
                                else:
                                    logging.error( _("Unprocessed {!r} sub3element ({}) in {}").format( sub3element.tag, sub3element.text.strip() if sub3element.text else sub3element.text, sub2elementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                        elif sub2element.tag == 'compoundUnit':
                            cuType = None
                            for attrib,value in subelement.items():
                                #print( "hereCU6", attrib, value )
                                #if attrib=='long': ulLong = value
                                #elif attrib=='digits': digits = value
                                if attrib=='type': cuType = value; assert cuType in ('long','narrow',)
                                else:
                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub2elementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                            for sub3element in sub2element:
                                sub3elementLocation = sub3element.tag + ' in ' + sub2elementLocation
                                #if debuggingThisModule: print( "        Processing {} ({})…".format( sub3elementLocation, sub3element.text.strip() ) )
                                BibleOrgSysGlobals.checkXMLNoAttributes( sub3element, sub3elementLocation )
                                BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3elementLocation )
                                BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3elementLocation )
                                if sub3element.tag == 'compoundUnitPattern':
                                    cupCount = upDraft = None
                                    for attrib,value in sub3element.items():
                                        if attrib=='xcount': cupCount = value
                                        elif attrib=='xdraft': upDraft = value
                                        else:
                                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub3elementLocation ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                    pass # Save text XXXXXXXXXXXXX
                                else:
                                    logging.error( _("Unprocessed {!r} sub3element ({}) in {}").format( sub3element.tag, sub3element.text.strip() if sub3element.text else sub3element.text, sub2elementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                        elif sub2element.tag == 'coordinateUnit':
                            cuType = None
                            for attrib,value in subelement.items():
                                #print( "hereCooU6", attrib, value )
                                #if attrib=='long': ulLong = value
                                #elif attrib=='digits': digits = value
                                if attrib=='type': cuType = value; assert cuType in ('long','short','narrow',)
                                else:
                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub2elementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                            for sub3element in sub2element:
                                sub3elementLocation = sub3element.tag + ' in ' + sub2elementLocation
                                #if debuggingThisModule: print( "        Processing {} ({})…".format( sub3elementLocation, sub3element.text.strip() ) )
                                BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3elementLocation )
                                BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3elementLocation )
                                if sub3element.tag == 'coordinateUnitPattern':
                                    cupType = upDraft = None
                                    for attrib,value in sub3element.items():
                                        #print( "hereCUP7", attrib, value )
                                        if attrib=='type': cupType = value; assert cupType in ('east','north','west','south',)
                                        #if attrib=='xcount': cupCount = value
                                        #elif attrib=='xdraft': upDraft = value
                                        else:
                                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub3elementLocation ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                    pass # Save text XXXXXXXXXXXXX
                                else:
                                    logging.error( _("Unprocessed {!r} sub3element ({}) in {}").format( sub3element.tag, sub3element.text.strip() if sub3element.text else sub3element.text, sub2elementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                        else:
                            logging.error( _("Unprocessed {!r} sub2element ({}) in {}").format( sub2element.tag, sub2element.text.strip() if sub2element.text else sub2element.text, subelementLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                    #assert subelement.tag not in units
                    #units[subelement.tag] = (nID,digits,nType)
                elif subelement.tag == 'durationUnit':
                    duType = None
                    for attrib,value in subelement.items():
                        #print( "hereDU7", attrib, value )
                        if attrib=='type': duType = value; assert duType in ('hm','hms','ms',)
                        else:
                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, subelementLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    for sub2element in subelement:
                        sub2elementLocation = sub2element.tag + ' in ' + subelementLocation
                        #if debuggingThisModule: print( "      Processing {} ({})…".format( sub2elementLocation, sub2element.text.strip() ) )
                        BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2elementLocation )
                        BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2elementLocation )
                        if sub2element.tag == 'durationUnitPattern':
                            dupType = None
                            for attrib,value in subelement.items():
                                #if attrib=='long': ulLong = value
                                #elif attrib=='digits': digits = value
                                if attrib=='type': dupType = value
                                else:
                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub2elementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                            pass # save TEXT xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
                        else:
                            logging.error( _("Unprocessed {!r} sub2element ({}) in {}").format( sub2element.tag, sub2element.text.strip() if sub2element.text else sub2element.text, subelementLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                    #assert subelement.tag not in units
                    #units[subelement.tag] = (nID,digits,nType)
                else:
                    logging.error( _("Unprocessed {!r} subelement ({}) in {}").format( subelement.tag, subelement.text.strip() if subelement.text else subelement.text, elementLocation ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
            return units
        # end of loadUnits


        def loadCharacterLabels( element, elementLocation, characterLabels ):
            """
            Returns the updated dictionary.
            """
            for subelement in element:
                subelementLocation = subelement.tag + ' in ' + elementLocation
                #if debuggingThisModule: print( "    Processing {}…".format( subelementLocation ) )
                BibleOrgSysGlobals.checkXMLNoSubelements( subelement, subelementLocation )
                BibleOrgSysGlobals.checkXMLNoTail( subelement, subelementLocation )
                if subelement.tag == 'characterLabel':
                    clType = None
                    for attrib,value in subelement.items():
                        #print( "hereCI7", attrib, value )
                        #if attrib=='long': ulLong = value
                        #elif attrib=='digits': digits = value
                        if attrib=='type': clType = value
                        else:
                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, subelementLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    assert clType not in characterLabels
                    characterLabels[clType] = subelement.text
                else:
                    logging.error( _("Unprocessed {!r} subelement ({}) in {}").format( subelement.tag, subelement.text.strip() if subelement.text else subelement.text, elementLocation ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
            return characterLabels
        # end of loadCharacterLabels


        def loadListPatterns( element, elementLocation, listPatterns ):
            """
            Returns the updated dictionary.
            """
            for subelement in element:
                subelementLocation = subelement.tag + ' in ' + elementLocation
                #if debuggingThisModule: print( "    Processing {}…".format( subelementLocation ) )
                BibleOrgSysGlobals.checkXMLNoText( subelement, subelementLocation )
                BibleOrgSysGlobals.checkXMLNoTail( subelement, subelementLocation )
                if subelement.tag == 'listPattern':
                    lpType = None
                    for attrib,value in subelement.items():
                        #if attrib=='long': ulLong = value
                        #elif attrib=='digits': digits = value
                        if attrib=='type': lpType = value
                        else:
                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, subelementLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    for sub2element in subelement:
                        sub2elementLocation = sub2element.tag + ' in ' + subelementLocation
                        #if debuggingThisModule: print( "      Processing {} ({})…".format( sub2elementLocation, sub2element.text.strip() ) )
                        BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2elementLocation )
                        BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2elementLocation )
                        if sub2element.tag == 'listPatternPart':
                            lppDraft = lppType = None
                            for attrib,value in sub2element.items():
                                if attrib=='draft': lppDraft = value
                                elif attrib=='type': lppType = value
                                else:
                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub2elementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                            pass # Save Text XXXXX
                            #for sub3element in sub2element:
                                #sub3elementLocation = sub3element.tag + ' in ' + sub2elementLocation
                                ##if debuggingThisModule: print( "        Processing {} ({})…".format( sub3elementLocation, sub3element.text.strip() ) )
                                #BibleOrgSysGlobals.checkXMLNoAttributes( sub3element, sub3elementLocation )
                                #BibleOrgSysGlobals.checkXMLNoText( sub3element, sub3elementLocation )
                                #BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3elementLocation )
                                #BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3elementLocation )
                        else:
                            logging.error( _("Unprocessed {!r} sub2element ({}) in {}").format( sub2element.tag, sub2element.text.strip() if sub2element.text else sub2element.text, subelementLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                    assert lpType not in listPatterns
                    listPatterns[lpType] = subelement.text
                else:
                    logging.error( _("Unprocessed {!r} subelement ({}) in {}").format( subelement.tag, subelement.text.strip() if subelement.text else subelement.text, elementLocation ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
            return listPatterns
        # end of loadListPatterns


        def loadContextTransforms( element, elementLocation, contextTransforms ):
            """
            Returns the updated dictionary.
            """
            for subelement in element:
                subelementLocation = subelement.tag + ' in ' + elementLocation
                #if debuggingThisModule: print( "    Processing {}…".format( subelementLocation ) )
                BibleOrgSysGlobals.checkXMLNoText( subelement, subelementLocation )
                BibleOrgSysGlobals.checkXMLNoTail( subelement, subelementLocation )
                if subelement.tag == 'contextTransformUsage':
                    ctuType = None
                    for attrib,value in subelement.items():
                        #print( "hereCI7", attrib, value )
                        #if attrib=='long': ulLong = value
                        #elif attrib=='digits': digits = value
                        if attrib=='type': ctuType = value
                        else:
                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, subelementLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                    for sub2element in subelement:
                        sub2elementLocation = sub2element.tag + ' in ' + subelementLocation
                        #if debuggingThisModule: print( "      Processing {} ({})…".format( sub2elementLocation, sub2element.text.strip() ) )
                        BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2elementLocation )
                        BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2elementLocation )
                        if sub2element.tag == 'contextTransform':
                            lppDraft = ctType = None
                            for attrib,value in sub2element.items():
                                if attrib=='xdraft': lppDraft = value
                                elif attrib=='type': ctType = value
                                else:
                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub2elementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                            pass # Save Text XXXXX
                            #for sub3element in sub2element:
                                #sub3elementLocation = sub3element.tag + ' in ' + sub2elementLocation
                                ##if debuggingThisModule: print( "        Processing {} ({})…".format( sub3elementLocation, sub3element.text.strip() ) )
                                #BibleOrgSysGlobals.checkXMLNoAttributes( sub3element, sub3elementLocation )
                                #BibleOrgSysGlobals.checkXMLNoText( sub3element, sub3elementLocation )
                                #BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3elementLocation )
                                #BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3elementLocation )
                        else:
                            logging.error( _("Unprocessed {!r} sub2element ({}) in {}").format( sub2element.tag, sub2element.text.strip() if sub2element.text else sub2element.text, subelementLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                    assert ctuType not in contextTransforms
                    contextTransforms[ctuType] = subelement.text
                else:
                    logging.error( _("Unprocessed {!r} subelement ({}) in {}").format( subelement.tag, subelement.text.strip() if subelement.text else subelement.text, elementLocation ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
            return contextTransforms
        # end of loadContextTransforms


        def loadMetadata( element, elementLocation, metadata ):
            """
            Returns the updated dictionary.
            """
            for subelement in element:
                subelementLocation = subelement.tag + ' in ' + elementLocation
                #if debuggingThisModule: print( "    Processing {}…".format( subelementLocation ) )
                BibleOrgSysGlobals.checkXMLNoAttributes( subelement, subelementLocation )
                BibleOrgSysGlobals.checkXMLNoText( subelement, subelementLocation )
                BibleOrgSysGlobals.checkXMLNoTail( subelement, subelementLocation )
                assert subelement.tag not in metadata
                if subelement.tag == 'casingData':
                    adjustedTag = removeSILPrefix( subelement.tag )
                    metadata[adjustedTag] = {}
                    for sub2element in subelement:
                        sub2elementLocation = sub2element.tag + ' in ' + subelementLocation
                        #if debuggingThisModule: print( "      Processing {}…".format( sub2elementLocation ) )
                        BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2elementLocation )
                        BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2elementLocation )
                        if sub2element.tag == 'casingItem':
                            erName = erSize = ciType = None
                            for attrib,value in sub2element.items():
                                #print( "hereCI7", attrib, value )
                                #if attrib=='name': erName = value
                                #elif attrib=='size': erSize = value
                                if attrib=='type': ciType = value # assert ciType in ('language','month_narrow','calendar_field','currencyName_count','era_abbr','era_name','era_narrow','key','keyValue',)
                                else:
                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub2elementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                            #assert erName
                            if sub2element.tag not in metadata[adjustedTag]:
                                metadata[adjustedTag][sub2element.tag] = []
                            metadata[adjustedTag][sub2element.tag].append( (ciType,erName,erSize) )
                        else:
                            logging.error( _("Unprocessed {!r} sub2element ({}) in {}").format( sub2element.tag, sub2element.text.strip() if sub2element.text else sub2element.text, subLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                else:
                    logging.error( _("Unprocessed {!r} subelement ({}) in {}").format( subelement.tag, subelement.text.strip() if subelement.text else subelement.text, elementLocation ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
            return metadata
        # end of loadMetadata


        def loadSpecial( element, elementLocation, special ):
            """
            Returns the updated dictionary.
            """
            for subelement in element:
                subelementLocation = subelement.tag + ' in ' + elementLocation
                if debuggingThisModule: print( "    Processing {}…".format( subelementLocation ) )
                BibleOrgSysGlobals.checkXMLNoAttributes( subelement, subelementLocation )
                BibleOrgSysGlobals.checkXMLNoText( subelement, subelementLocation )
                BibleOrgSysGlobals.checkXMLNoTail( subelement, subelementLocation )
                assert subelement.tag not in special
                if subelement.tag.endswith( 'external-resources' ):
                    adjustedTag = removeSILPrefix( subelement.tag )
                    special[adjustedTag] = {}
                    fonts = {}
                    for sub2element in subelement:
                        sub2elementLocation = sub2element.tag + ' in ' + subelementLocation
                        if debuggingThisModule: print( "      Processing {}…".format( sub2elementLocation ) )
                        BibleOrgSysGlobals.checkXMLNoText( sub2element, sub2elementLocation )
                        BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2elementLocation )
                        if sub2element.tag.endswith( 'font' ):
                            BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2elementLocation )
                            fName = fSize = None
                            for attrib,value in sub2element.items():
                                #print( "        hereF1", attrib, value )
                                if attrib=='name': fName = value # assert fName in ('Times New Roman','Cambria',)
                                elif attrib=='size': fSize = value # assert fSize in ('1.4',)
                                #elif attrib=='type': erType = value; assert erType in ('default','hunspell',)
                                else:
                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub2elementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                            assert fName
                            assert fName not in fonts
                            fonts[fName] = sub2element.text
                        elif sub2element.tag.endswith( 'fontrole' ):
                            frName = frSize = frType = None
                            for attrib,value in sub2element.items():
                                #print( "        hereLS5", attrib, value )
                                if attrib=='name': frName = value
                                elif attrib=='size': frSize = value
                                elif attrib=='type': frType = value; assert frType in ('default','hunspell')
                                else:
                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub2elementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                            #assert erName
                            for sub3element in sub2element:
                                sub3elementLocation = sub3element.tag + ' in ' + sub2elementLocation
                                #if debuggingThisModule: print( "        Processing {} ({})…".format( sub3elementLocation, sub3element.text.strip() ) )
                                BibleOrgSysGlobals.checkXMLNoText( sub3element, sub3elementLocation )
                                BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3elementLocation )
                                if sub3element.tag.endswith( 'font' ):
                                    fName = isGraphite = None
                                    for attrib,value in sub3element.items():
                                        #print( "        hereF5", attrib, value )
                                        if attrib=='name': fName = value
                                        elif attrib=='isGraphite': isGraphite = value
                                        else:
                                            logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub3elementLocation ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                                    assert fName
                                    assert fName not in fonts
                                    fonts[fName] = {}
                                    for sub4element in sub3element:
                                        sub4elementLocation = sub4element.tag + ' in ' + sub3elementLocation
                                        #if debuggingThisModule: print( "          Processing9 {} ({})…".format( sub4elementLocation, sub4element.text.strip() ) )
                                        BibleOrgSysGlobals.checkXMLNoAttributes( sub4element, sub4elementLocation )
                                        BibleOrgSysGlobals.checkXMLNoSubelements( sub4element, sub4elementLocation )
                                        BibleOrgSysGlobals.checkXMLNoTail( sub4element, sub4elementLocation )
                                        if sub4element.tag.endswith( 'url' ):
                                            fonts[fName][sub4element.tag] = sub4element.text
                                        else:
                                            logging.error( _("Unprocessed {!r} sub4element in {}").format( sub4element.tag, sub3elementLocation ) )
                                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                                else:
                                    logging.error( _("Unprocessed {!r} sub3element ({}) in {}").format( sub3element.tag, sub3element.text.strip() if sub3element.text else sub3element.text, sub2elementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                        elif sub2element.tag.endswith( 'kbd' ):
                            keyboard = {}
                            kbdName = kbdSize = kbdType = kbdID = None
                            for attrib,value in sub2element.items():
                                #print( "        hereKBD7", attrib, value )
                                if attrib=='name': kbdName = value
                                elif attrib=='size': kbdSize = value
                                elif attrib=='type': kbdType = value; assert kbdType in ('kmp','hunspell')
                                elif attrib=='id': kbdID = value
                                else:
                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub2elementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                            #assert erName
                            for sub3element in sub2element:
                                sub3elementLocation = sub3element.tag + ' in ' + sub2elementLocation
                                #if debuggingThisModule: print( "        Processing {} ({})…".format( sub3elementLocation, sub3element.text.strip() ) )
                                BibleOrgSysGlobals.checkXMLNoAttributes( sub3element, sub3elementLocation )
                                BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3elementLocation )
                                BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3elementLocation )
                                if sub3element.tag.endswith( 'url' ):
                                    keyboard['url'] = sub3element.text
                                else:
                                    logging.error( _("Unprocessed {!r} sub3element ({}) in {}").format( sub3element.tag, sub3element.text.strip() if sub3element.text else sub3element.text, sub2elementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                        elif sub2element.tag.endswith( 'spell-checking' ):
                            spellChecker = {}
                            scName = scSize = scType = scID = None
                            for attrib,value in sub2element.items():
                                print( "        hereSC8", attrib, value )
                                if attrib=='xname': scName = value
                                elif attrib=='xsize': scSize = value
                                elif attrib=='type': scType = value; assert scType in ('xkmp','hunspell')
                                elif attrib=='xid': scID = value
                                else:
                                    logging.error( _("Unprocessed {!r} attribute ({}) in {}").format( attrib, value, sub2elementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag and BibleOrgSysGlobals.haltOnXMLWarning: halt
                            #assert erName
                            for sub3element in sub2element:
                                sub3elementLocation = sub3element.tag + ' in ' + sub2elementLocation
                                #if debuggingThisModule: print( "        Processing {} ({})…".format( sub3elementLocation, sub3element.text.strip() ) )
                                BibleOrgSysGlobals.checkXMLNoAttributes( sub3element, sub3elementLocation )
                                BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3elementLocation )
                                BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3elementLocation )
                                if sub3element.tag.endswith( 'url' ):
                                    spellChecker['url'] = sub3element.text
                                else:
                                    logging.error( _("Unprocessed {!r} sub3element ({}) in {}").format( sub3element.tag, sub3element.text.strip() if sub3element.text else sub3element.text, sub2elementLocation ) )
                                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                        else:
                            logging.error( _("Unprocessed {!r} sub2element ({}) in {}").format( sub2element.tag, sub2element.text.strip() if sub2element.text else sub2element.text, subelementLocation ) )
                            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
                        # Save our data
                        pass # It's being lost!
                        #if sub2element.tag not in special[adjustedTag]:
                            #special[adjustedTag][sub2element.tag] = []
                        #special[adjustedTag][sub2element.tag].append( (erType,erName,erSize) )
                else:
                    logging.error( _("Unprocessed {!r} subelement ({}) in {}").format( subelement.tag, subelement.text.strip() if subelement.text else subelement.text, elementLocation ) )
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag: halt
            return special
        # end of loadSpecial


        # Main code for LDMLFile.load()
        if BibleOrgSysGlobals.verbosityLevel > 3:
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
            contacts = OrderedDict()
            comments = OrderedDict()
            status = OrderedDict()
            characters = OrderedDict()
            delimiters = OrderedDict()
            layout = OrderedDict()
            numbers = OrderedDict()
            collations = OrderedDict()
            localeDisplayNames = OrderedDict()
            dates = OrderedDict()
            units = OrderedDict()
            characterLabels = OrderedDict()
            listPatterns = OrderedDict()
            contextTransforms = OrderedDict()
            metadata = OrderedDict()
            special = OrderedDict()

            # Now process the actual entries
            for element in languageTree:
                elementLocation = element.tag + ' in ' + treeLocation
                #if debuggingThisModule: print( "  Processing1 {} ({})…".format( elementLocation, element.text.strip() ) )
                if element.tag == 'status':
                    BibleOrgSysGlobals.checkXMLNoSubelements( element, elementLocation )
                else:
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, elementLocation )
                BibleOrgSysGlobals.checkXMLNoText( element, elementLocation )
                BibleOrgSysGlobals.checkXMLNoTail( element, elementLocation )
                assert element.tag not in LDMLData # Each one can only occur onces

                if element.tag == 'identity':
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag or debuggingThisModule:
                        identity = loadIdentity( element, elementLocation, identity )
                    else:
                        identity = None
                        try: identity = loadIdentity( element, elementLocation, identity )
                        except Exception as err: logging.error( 'LDML.load.loadIdentity failed with {} {}'.format( sys.exc_info()[0], err ) )
                    if identity:
                        #print( "identity", identity )
                        LDMLData[element.tag] = identity
                elif element.tag == 'contacts':
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag or debuggingThisModule:
                        contacts = loadContacts( element, elementLocation, contacts )
                    else:
                        contacts = None
                        try: contacts = loadContacts( element, elementLocation, contacts )
                        except Exception as err: logging.error( 'LDML.load.loadContacts failed with {} {}'.format( sys.exc_info()[0], err ) )
                    if contacts:
                        #print( "contacts", contacts )
                        LDMLData[element.tag] = contacts
                elif element.tag == 'comments':
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag or debuggingThisModule:
                        comments = loadComments( element, elementLocation, comments )
                    else:
                        comments = None
                        try: comments = loadComments( element, elementLocation, comments )
                        except Exception as err: logging.error( 'LDML.load.loadComments failed with {} {}'.format( sys.exc_info()[0], err ) )
                    if comments:
                        #print( "comments", comments )
                        LDMLData[element.tag] = comments
                elif element.tag == 'status':
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag or debuggingThisModule:
                        status = loadStatus( element, elementLocation, status )
                    else:
                        status = None
                        try: status = loadStatus( element, elementLocation, status )
                        except Exception as err: logging.error( 'LDML.load.loadStatus failed with {} {}'.format( sys.exc_info()[0], err ) )
                    if status:
                        #print( "status", status )
                        LDMLData[element.tag] = status
                elif element.tag == 'characters':
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag or debuggingThisModule:
                        characters = loadCharacters( element, elementLocation, characters )
                    else:
                        characters = None
                        try: characters = loadCharacters( element, elementLocation, characters )
                        except Exception as err: logging.error( 'LDML.load.loadCharacters failed with {} {}'.format( sys.exc_info()[0], err ) )
                    if characters:
                        #print( "characters", characters )
                        LDMLData[element.tag] = characters
                elif element.tag == 'delimiters':
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag or debuggingThisModule:
                        delimiters = loadDelimiters( element, elementLocation, delimiters )
                    else:
                        delimiters = None
                        try: delimiters = loadDelimiters( element, elementLocation, delimiters )
                        except Exception as err: logging.error( 'LDML.load.loadDelimiters failed with {} {}'.format( sys.exc_info()[0], err ) )
                    if delimiters:
                        #print( "delimiters", delimiters )
                        LDMLData[element.tag] = delimiters
                elif element.tag == 'layout':
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag or debuggingThisModule:
                        layout = loadLayout( element, elementLocation, layout )
                    else:
                        layout = None
                        try: layout = loadLayout( element, elementLocation, layout )
                        except Exception as err: logging.error( 'LDML.load.loadLayout failed with {} {}'.format( sys.exc_info()[0], err ) )
                    if layout:
                        #print( "layout", layout )
                        LDMLData[element.tag] = layout
                elif element.tag == 'numbers':
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag or debuggingThisModule:
                        numbers = loadNumbers( element, elementLocation, numbers )
                    else:
                        numbers = None
                        try: numbers = loadNumbers( element, elementLocation, numbers )
                        except Exception as err: logging.error( 'LDML.load.loadNumbers failed with {} {}'.format( sys.exc_info()[0], err ) )
                    if numbers:
                        #print( "numbers", numbers )
                        LDMLData[element.tag] = numbers
                elif element.tag == 'collations':
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag or debuggingThisModule:
                        collations = loadCollations( element, elementLocation, collations )
                    else:
                        collations = None
                        try: collations = loadCollations( element, elementLocation, collations )
                        except Exception as err: logging.error( 'LDML.load.loadCollations failed with {} {}'.format( sys.exc_info()[0], err ) )
                    if collations:
                        #print( "collations", collations )
                        LDMLData[element.tag] = collations
                elif element.tag == 'localeDisplayNames':
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag or debuggingThisModule:
                        localeDisplayNames = loadLocateDisplayNames( element, elementLocation, localeDisplayNames )
                    else:
                        localeDisplayNames = None
                        try: localeDisplayNames = loadLocateDisplayNames( element, elementLocation, localeDisplayNames )
                        except Exception as err: logging.error( 'LDML.load.loadLocateDisplayNames failed with {} {}'.format( sys.exc_info()[0], err ) )
                    if localeDisplayNames:
                        #print( "localeDisplayNames", localeDisplayNames )
                        LDMLData[element.tag] = localeDisplayNames
                elif element.tag == 'dates':
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag or debuggingThisModule:
                        dates = loadDates( element, elementLocation, dates )
                    else:
                        dates = None
                        try: dates = loadDates( element, elementLocation, dates )
                        except Exception as err: logging.error( 'LDML.load.loadDates failed with {} {}'.format( sys.exc_info()[0], err ) )
                    if dates:
                        #print( "dates", dates )
                        LDMLData[element.tag] = dates
                elif element.tag == 'units':
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag or debuggingThisModule:
                        units = loadUnits( element, elementLocation, units )
                    else:
                        units = None
                        try: units = loadUnits( element, elementLocation, units )
                        except Exception as err: logging.error( 'LDML.load.loadUnits failed with {} {}'.format( sys.exc_info()[0], err ) )
                    if units:
                        #print( "units", units )
                        LDMLData[element.tag] = units
                elif element.tag == 'characterLabels':
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag or debuggingThisModule:
                        characterLabels = loadCharacterLabels( element, elementLocation, characterLabels )
                    else:
                        characterLabels = None
                        try: characterLabels = loadCharacterLabels( element, elementLocation, characterLabels )
                        except Exception as err: logging.error( 'LDML.load.loadCharacterLabels failed with {} {}'.format( sys.exc_info()[0], err ) )
                    if characterLabels:
                        #print( "characterLabels", characterLabels )
                        LDMLData[element.tag] = characterLabels
                elif element.tag == 'listPatterns':
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag or debuggingThisModule:
                        listPatterns = loadListPatterns( element, elementLocation, listPatterns )
                    else:
                        listPatterns = None
                        try: listPatterns = loadListPatterns( element, elementLocation, listPatterns )
                        except Exception as err: logging.error( 'LDML.load.loadListPatterns failed with {} {}'.format( sys.exc_info()[0], err ) )
                    if listPatterns:
                        #print( "listPatterns", listPatterns )
                        LDMLData[element.tag] = listPatterns
                elif element.tag == 'contextTransforms':
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag or debuggingThisModule:
                        contextTransforms = loadContextTransforms( element, elementLocation, contextTransforms )
                    else:
                        contextTransforms = None
                        try: contextTransforms = loadContextTransforms( element, elementLocation, contextTransforms )
                        except Exception as err: logging.error( 'LDML.load.loadContextTransforms failed with {} {}'.format( sys.exc_info()[0], err ) )
                    if contextTransforms:
                        #print( "contextTransforms", contextTransforms )
                        LDMLData[element.tag] = contextTransforms
                elif element.tag == 'metadata':
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag or debuggingThisModule:
                        metadata = loadMetadata( element, elementLocation, metadata )
                    else:
                        metadata = None
                        try: metadata = loadMetadata( element, elementLocation, metadata )
                        except Exception as err: logging.error( 'LDML.load.loadMetadata failed with {} {}'.format( sys.exc_info()[0], err ) )
                    if metadata:
                        #print( "metadata", metadata )
                        LDMLData[element.tag] = metadata
                elif element.tag == 'special':
                    if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag or debuggingThisModule:
                        special = loadSpecial( element, elementLocation, special )
                    else:
                        special = None
                        try: special = loadSpecial( element, elementLocation, special )
                        except Exception as err: logging.error( 'LDML.load.loadSpecial failed with {} {}'.format( sys.exc_info()[0], err ) )
                    if special:
                        #print( "special", special )
                        LDMLData[element.tag] = special
                else:
                    logging.error( _("Unprocessed {} element ({}) in {}").format( element.tag, element.text.strip() if element.text else element.text, treeLocation ) )
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
        elif debuggingThisModule: print( '\nLDMLData for {} ({}): {}'.format( self.languageCode, len(LDMLData), LDMLData ) )
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
        for something in sorted( os.listdir( mainTestFolder ) ):
            somepath = os.path.join( mainTestFolder, something )
            if os.path.isdir( somepath ):
                if BibleOrgSysGlobals.verbosityLevel > 0:
                    print( "\n\nA: Looking for files in folder: {}".format( somepath ) )

                for something2 in sorted( os.listdir( somepath ) ):
                    if something2 in ( 'blo_Latn.xml', 'blt_Latn.xml', 'blt_Tavt.xml', ):
                        print( "Skipping {}".format( something2 ) )
                        continue # bad XML
                    somepath2 = os.path.join( somepath, something2 )
                    if os.path.isfile( somepath2 ):
                        if BibleOrgSysGlobals.verbosityLevel > 0:
                            print( "\nFound {}".format( somepath2 ) )

                        if os.access( somepath2, os.R_OK ):
                            thisLDMLfile = LDMLFile( somepath, something2 )
                            LDMLdict = thisLDMLfile.load()
                            if BibleOrgSysGlobals.verbosityLevel > 1: print( "  Loaded {} and got:\n  {}".format( something2, LDMLdict ) )
                            #if BibleOrgSysGlobals.strictCheckingFlag: thisLDMLfile.check()
                        else: print( "Sorry, test file '{}' is not readable on this computer.".format( somepath2 ) )
        #if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nPTX8 B/ Trying single module in {}".format( testFolder ) )
        #thisLDMLfile = LDMLFile( testFolder )
        #thisLDMLfile.load()
        #if BibleOrgSysGlobals.verbosityLevel > 0: print( "thisLDMLfile )


if __name__ == '__main__':
    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( ProgName, ProgVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    demo()

    BibleOrgSysGlobals.closedown( ProgName, ProgVersion )
# end of LDML.py
