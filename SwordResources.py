#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# SwordResources.py
#
# Module handling Sword resources using the Sword engine
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
Module handling content modules produced for Crosswire Sword.
This module uses the Sword engine (libsword) via the Python SWIG bindings.
(If you don't want to install that, consider our SwordModules module.)
"""

from gettext import gettext as _

LastModifiedDate = '2014-12-18' # by RJH
ShortProgName = "SwordResources"
ProgName = "Sword resource handler"
ProgVersion = "0.12"
ProgNameVersion = '{} v{}'.format( ProgName, ProgVersion )
ProgNameVersionDate = '{} {} {}'.format( ProgNameVersion, _("last modified"), LastModifiedDate )

debuggingThisModule = True


#from singleton import singleton
import os, logging
#from collections import OrderedDict

import BibleOrgSysGlobals
from VerseReferences import SimpleVerseKey
from InternalBibleInternals import InternalBibleEntryList, InternalBibleEntry


SwordType = None
try:
    import Swordx
    SwordType = "CrosswireLibrary"
except ImportError: # Sword library (dll and python bindings) seem to be not available
    if 0: # Warn the user that this won't work
        logging.critical( _("You need to install the Sword library on your computer in order to use this module.") )
        logging.info( _("Alternatively, you can try the all-Python SwordModules module.") )
        #sys.exit( 1 )
    else: # Use our own Python3 code instead
        try:
            import SwordModules
            SwordType = "OurCode"
        except ImportError:
            logging.critical( _("You don't appear to have any way installed to read Sword modules.") )



def t( messageString ):
    """
    Prepends the module name to a error or warning message string
        if we are in debug mode.
    Returns the new string.
    """
    try: nameBit, errorBit = messageString.split( ': ', 1 )
    except ValueError: nameBit, errorBit = '', messageString
    if BibleOrgSysGlobals.debugFlag or debuggingThisModule:
        nameBit = '{}{}{}: '.format( ShortProgName, '.' if nameBit else '', nameBit )
    return '{}{}'.format( nameBit, _(errorBit) )



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
        if SwordType == "CrosswireLibrary":
            self.library = Sword.SWMgr()
            #self.keyCache = {}
            #self.verseCache = {}
        elif SwordType == "OurCode":
            self.library = SwordModules.SwordModules() # Loads all of conf files that it can find
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                print( "Sword library", self.library )
    # end of SwordInterface.__init__


    def getAvailableModuleCodes( self ):
        """
        Returns a list of available Sword module codes.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( t("SwordResources.getAvailableModuleCodes()") )
        if SwordType == "CrosswireLibrary":
            availableModuleCodes = []
            for j,moduleBuffer in enumerate(self.library.getModules()):
                moduleID = moduleBuffer.getRawData()
                #module = library.getModule( moduleID )
                #if 0:
                    #print( "{} {} ({}) {} '{}'".format( j, module.getName(), module.getType(), module.getLanguage(), module.getEncoding() ) )
                    #try: print( "    {} '{}' {} {}".format( module.getDescription(), module.getMarkup(), module.getDirection(), "" ) )
                    #except UnicodeDecodeError: print( "   Description is not Unicode!" )
                print( "moduleID", repr(moduleID) )
                availableModuleCodes.append( moduleID )
            return availableModuleCodes
        elif SwordType == "OurCode":
            return self.library.getAvailableModuleCodes()
    # end of SwordInterface.getAvailableModuleCodes


    def getModule( self, moduleAbbreviation='KJV' ):
        """
        """
        if BibleOrgSysGlobals.debugFlag: print( "SwordResources.getModule({})".format( moduleAbbreviation ) )
        if SwordType == "CrosswireLibrary":
            #print( "gM", module.getName() )
            return self.library.getModule( moduleAbbreviation )
        elif SwordType == "OurCode":
            lmResult = self.library.loadModule( moduleAbbreviation ) # e.g., KJV
            #except KeyError: lmResult = self.library.loadModule( moduleAbbreviation.lower() ) # needs kjv??? why? what changed?
            #print( moduleAbbreviation, lmResult ); halt
            resultFlag, theModule = lmResult
            if not resultFlag: print( "failed here!" ); halt
            return theModule
    # end of SwordInterface.getModule


    def makeKey( self, BBB, C, V ):
        #if BibleOrgSysGlobals.debugFlag: print( "SwordResources.makeKey({})".format( BCV ) )
        #if BCV  in self.keyCache:
            #print( "Cached", BCV )
            #return self.keyCache[BCV]
        if SwordType == "CrosswireLibrary":
            B = BibleOrgSysGlobals.BibleBooksCodes.getOSISAbbreviation( BBB )
            refString = "{} {}:{}".format( B, C, V )
            #print( 'refString', refString )
            verseKey = Sword.VerseKey( refString )
            #self.keyCache[BCV] = verseKey
            return verseKey
        elif SwordType == "OurCode":
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
        if SwordType == "CrosswireLibrary":
            try: verseText = module.stripText( key )
            except UnicodeDecodeError:
                print( "Can't decode utf-8 text of {} {}".format( module.getName(), key.getShortText() ) )
                return
            if BibleOrgSysGlobals.debugFlag:
                if '\n' in verseText or '\r' in verseText:
                    print( t("getVerseData: Why does it have CR or LF in {} {} {}") \
                            .format( module.getName(), key.getShortText(), repr(verseText) ) )
            verseText = verseText.rstrip()
            verseData = InternalBibleEntryList()
            c, v = key.getChapterNumberStr(), key.getVerseNumberStr()
            # Prepend the verse number since Sword modules don't contain that info in the data
            if v=='1': verseData.append( InternalBibleEntry( 'c#','c', c, c, None, c ) )
            verseData.append( InternalBibleEntry( 'v','v', v, v, None, v ) )
            verseData.append( InternalBibleEntry( 'v~','v~', verseText, verseText, None, verseText ) )
            contextVerseData = verseData, [] # No context
        elif SwordType == "OurCode":
            #print( t("module"), module )
            try: contextVerseData = module.getContextVerseData( key )
            except KeyError: # Just create a blank verse entry
                verseData = InternalBibleEntryList()
                c, v = key.getChapterNumberStr(), key.getVerseNumberStr()
                if v=='1': verseData.append( InternalBibleEntry( 'c#','c', c, c, None, c ) )
                verseData.append( InternalBibleEntry( 'v','v', v, v, None, v ) )
                contextVerseData = verseData, [] # No context
            #print( t("gVD={} key={}, st={}").format( module.getName(), key, contextVerseData ) )
            if contextVerseData is None:
                if key.getChapter()!=0 or key.getVerse()!=0: # We're not surprised if there's no chapter or verse zero
                    print( t("SwordInterface.getVerseData no VD"), module.getName(), key, contextVerseData )
                contextVerseData = [], None
            else:
                verseData, context = contextVerseData
                #print( "vD", verseData )
                #assert( isinstance( verseData, InternalBibleEntryList ) or isinstance( verseData, list ) )
                assert( isinstance( verseData, InternalBibleEntryList ) )
                #assert( isinstance( verseData, list ) )
                assert( 1 <= len(verseData) <= 6 )
        #print( verseData ); halt
        return contextVerseData
    # end of SwordInterface.getContextVerseData


    def getVerseData( self, module, key ):
        """
        Returns a list of 5-tuples, e.g.,
            [
            ('c', 'c', '1', '1', []),
            ('c#', 'c', '1', '1', []),
            ('v', 'v', '1', '1', []),
            ('v~', 'v~', 'In the beginning God created the heavens and the earth.',
                                    'In the beginning God created the heavens and the earth.', [])
            ]
        """
        if SwordType == "CrosswireLibrary":
            try: verseText = module.stripText( key )
            except UnicodeDecodeError:
                print( "Can't decode utf-8 text of {} {}".format( module.getName(), key.getShortText() ) )
                return
            if BibleOrgSysGlobals.debugFlag:
                if '\n' in verseText or '\r' in verseText:
                    print( t("getVerseData: Why does it have CR or LF in {} {}").format( module.getName(), repr(verseText) ) )
            verseData = []
            c, v = str(key.getChapter()), str(key.getVerse())
            # Prepend the verse number since Sword modules don't contain that info in the data
            if v=='1': verseData.append( ('c#','c', c, c, [],) )
            verseData.append( ('v','v', v, v, [],) )
            verseData.append( ('v~','v~', verseText, verseText, [],) )
        elif SwordType == "OurCode":
            #print( t("module"), module )
            stuff = module.getContextVerseData( key )
            #print( t("gVD={} key={}, st={}").format( module.getName(), key, stuff ) )
            if stuff is None:
                print( t("SwordInterface.getVerseData no VD"), module.getName(), key, stuff )
                assert( key.getChapter()==0 or key.getVerse()==0 )
            else:
                verseData, context = stuff
                #print( "vD", verseData )
                #assert( isinstance( verseData, InternalBibleEntryList ) or isinstance( verseData, list ) )
                assert( isinstance( verseData, InternalBibleEntryList ) )
                #assert( isinstance( verseData, list ) )
                assert( 1 <= len(verseData) <= 6 )
        #print( verseData ); halt
        return verseData
    # end of SwordInterface.getVerseData


    def getVerseText( self, module, key ):
        #cacheKey = (module.getName(), key.getShortText())
        #if cacheKey in self.verseCache:
            #print( "Cached", cacheKey )
            #return self.verseCache[cacheKey]
        #if BibleOrgSysGlobals.debugFlag: print( "SwordResources.getVerseText({},{})".format( module.getName(), key.getText() ) )
        if SwordType == "CrosswireLibrary":
            try: verseText = module.stripText( key )
            except UnicodeDecodeError:
                print( "Can't decode utf-8 text of {} {}".format( module.getName(), key.getShortText() ) )
                return ''
        elif SwordType == "OurCode":
            verseData = module.getContextVerseData( key )
            #print( "gVT", module.getName(), key, verseData )
            assert( isinstance( verseData, list ) )
            assert( 2 <= len(verseData) <= 5 )
            verseText = ''
            for entry in verseData:
                marker, cleanText = entry.getMarker(), entry.getCleanText()
                if marker == 'c': pass # Ignore
                elif marker == 'p': verseText += '¶' + cleanText
                elif marker == 'm': verseText += '§' + cleanText
                elif marker == 'v': pass # Ignore
                elif marker == 'v~': verseText += cleanText
                else: print( "Unknown marker", marker, cleanText ); halt
        #self.verseCache[cacheKey] = verseText
        #print( module.getName(), key.getShortText(), "'"+verseText+"'" )
        return verseText
    # end of SwordInterface.getVerseText
# end of class SwordInterface


def getBCV( BCV, moduleAbbreviation='KJV' ): # Very slow -- for testing only
    if BibleOrgSysGlobals.debugFlag: print( "SwordResources.getBCV({},{})".format( BCV, moduleAbbreviation ) )
    library = Sword.SWMgr()
    module = library.getModule( moduleAbbreviation )
    refString = "{} {}:{}".format( BCV[0][:3], BCV[1], BCV[2] )
    #print( 'refString', refString )
    return module.stripText( Sword.VerseKey( refString ) )
# end of getBCV



def demo():
    """
    Sword
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( ProgNameVersion )

    #print( "\ndir Sword", dir(Sword) )

    if SwordType == "CrosswireLibrary":
        print( "\ndir Sword.SWVersion()", dir(Sword.SWVersion()) )
        print( "Version", Sword.SWVersion().getText() )
        print( "Versions", Sword.SWVersion().major, Sword.SWVersion().minor, Sword.SWVersion().minor2, Sword.SWVersion().minor3 ) # ints

        library = Sword.SWMgr()
        #print( "\ndir library", dir(library) )
        #print( "\nlibrary getHomeDir", library.getHomeDir().getRawData() )

    def Find( attribute ):
        """ Search for methods and attributes """
        print( "\nSearching for attribute '{}'...".format( attribute ) )
        found = False
        AA = attribute.upper()
        for thing in dir(Sword):
            BB = thing.upper()
            if BB.startswith(AA): print( "  Have {} in Sword".format( thing ) ); found = True
        for thing in dir(Sword.SWVersion()):
            BB = thing.upper()
            if BB.startswith(AA): print( "  Have {} in SWVersion".format( thing ) ); found = True
        for thing in dir(Sword.SWMgr()):
            BB = thing.upper()
            if BB.startswith(AA): print( "  Have {} in SWMgr".format( thing ) ); found = True
        module = library.getModule( "KJV" )
        for thing in dir(module):
            BB = thing.upper()
            if BB.startswith(AA): print( "  Have {} in SWModule".format( thing ) ); found = True
        for thing in dir(Sword.SWKey()):
            BB = thing.upper()
            if BB.startswith(AA): print( "  Have {} in SWKey".format( thing ) ); found = True
        for thing in dir(Sword.VerseKey()):
            BB = thing.upper()
            if BB.startswith(AA): print( "  Have {} in VerseKey".format( thing ) ); found = True
        #for thing in dir(Sword.InstallMgr()):
            #BB = thing.upper()
            #if BB.startswith(AA): print( "  Have {} in InstallMgr".format( thing ) ); found = True
        for thing in dir(Sword.LocaleMgr()):
            BB = thing.upper()
            if BB.startswith(AA): print( "  Have {} in LocaleMgr".format( thing ) ); found = True
        for thing in dir(Sword.SWFilterMgr()):
            BB = thing.upper()
            if BB.startswith(AA): print( "  Have {} in SWFilterMgr".format( thing ) ); found = True
        if not found: print( " Sorry, '{}' not found.".format( attribute ) )
    # end of Find

    if 0: # Install manager
        print( "\nINSTALL MANAGER" )
        im = Sword.InstallMgr() # FAILS
        print( "\ndir im", im, dir(im) )

    if 0: # Locale manager
        print( "\nLOCALE MANAGER" )
        lm = Sword.LocaleMgr()
        print( "dir lm", lm, dir(lm) )
        print( "default {}".format( lm.getDefaultLocaleName() ) )
        print( "available {}".format( lm.getAvailableLocales() ) ) # Gives weird result: "available ()"
        print( "locale {}".format( lm.getLocale( "en" ) ) ) # Needs a string parameter but why does it return None?

    if 0: # try filters
        print( "\nFILTER MANAGER" )
        fm = Sword.SWFilterMgr()
        print( "\ndir filters", dir(fm) )

    if SwordType == "CrosswireLibrary":
        # Get a list of available module names and types
        print( "\n{} modules are installed.".format( len(library.getModules()) ) )
        for j,moduleBuffer in enumerate(library.getModules()):
            moduleID = moduleBuffer.getRawData()
            module = library.getModule( moduleID )
            if 0:
                print( "{} {} ({}) {} '{}'".format( j, module.getName(), module.getType(), module.getLanguage(), module.getEncoding() ) )
                try: print( "    {} '{}' {} {}".format( module.getDescription(), module.getMarkup(), module.getDirection(), "" ) )
                except UnicodeDecodeError: print( "   Description is not Unicode!" )
        #print( "\n", j, "dir module", dir(module) )

        # Try some modules
        mod1 = library.getModule( "KJV" )
        print( "\nmod1 {} ({}) '{}'".format( mod1.getName(), mod1.getType(), mod1.getDescription() ) )
        mod2 = library.getModule( "ASV" )
        print( "\nmod2 {} ({}) '{}'".format( mod2.getName(), mod2.getType(), mod2.getDescription() ) )
        mod3 = library.getModule( "WEB" )
        print( "\nmod3 {} ({}) '{}'".format( mod3.getName(), mod3.getType(), mod3.getDescription() ) )
        strongsGreek = library.getModule( "StrongsGreek" )
        print( "\nSG {} ({}) '{}'\n".format( strongsGreek.getName(), strongsGreek.getType(), strongsGreek.getDescription() ) )
        strongsHebrew = library.getModule( "StrongsHebrew" )
        print( "\nSH {} ({}) '{}'\n".format( strongsHebrew.getName(), strongsHebrew.getType(), strongsHebrew.getDescription() ) )
        print()

        # Try a sword key
        sk = Sword.SWKey( "H0430" )
        #print( "\ndir sk", dir(sk) )

        # Try a verse key
        vk = Sword.VerseKey( "Jn 3:16" )
        #print( "\ndir vk", dir(vk) )
        #print( "val", vk.validateCurrentLocale() ) # gives None
        print( "getInfo", vk.getLocale(), vk.getBookCount(), vk.getBookMax(), vk.getIndex(), vk.getVersificationSystem() )
        print( "getBCV {}({}/{}) {}/{}:{} in '{}'({})/{}".format( vk.getBookName(), vk.getBookAbbrev(), vk.getOSISBookName(), vk.getChapter(), vk.getChapterMax(), vk.getVerse(), repr(vk.getTestament()), vk.getTestamentIndex(), vk.getTestamentMax() ) )
        print( "getText {} {} {} {} '{}'".format( vk.getOSISRef(), vk.getText(), vk.getRangeText(), vk.getShortText(), vk.getSuffix() ) )
        #print( "bounds {} {}".format( vk.getLowerBound(), vk.getUpperBound() ) )

        if 0: # Set a filter HOW DO WE DO THIS???
            rFs = mod1.getRenderFilters()
            print( mod1.getRenderFilters() )
            mod1.setRenderFilter()

        print( "\n{} {}: {}".format( mod1.getName(), "Jonny 1:1", mod1.renderText( Sword.VerseKey("Jn 1:1") ) ) )
        mod1.increment()
        print( "\n{} {}: {}".format( mod1.getName(), mod1.getKey().getText(), mod1.stripText(  ) ) )
        mod1.increment()
        print( "\n{} {}: {}".format( mod1.getName(), mod1.getKey().getText(), mod1.renderText(  ) ) )
        print( "\n{} {}: {}".format( mod2.getName(), vk.getText(), mod2.renderText( vk ) ) )
        print( "\n{} {}: {}".format( mod3.getName(), vk.getText(), mod3.renderText( vk ) ) )
        print( "\n{} {}: {}".format( mod3.getName(), vk.getText(), mod3.renderText( vk ) ) )

        print( "\n{} {}: {}".format( strongsGreek.getName(), sk.getText(), strongsGreek.renderText( Sword.SWKey("G746") ) ) )
        print( "\n{} {}: {}".format( strongsHebrew.getName(), sk.getText(), strongsHebrew.renderText( sk ) ) )

        if 0: # Get all vernacular booknames
            # VerseKey vk; while (!vk.Error()) { cout << vk.getBookName(); vk.setBook(vk.getBook()+1); }
            vk = Sword.VerseKey()
            while vk.popError()=='\x00':
                print( "bookname", vk.getBookName() )
                booknumber = int( bytes( vk.getBook(),'utf-8' )[0] )
                vk.setBook( booknumber + 1 )

        if 0: # Get booknames by testament (from http://www.crosswire.org/wiki/DevTools:Code_Examples)
            vk = Sword.VerseKey()
            for t in range( 1, 2+1 ):
                vk.setTestament( t )
                for i in range( 1, vk.getBookMax()+1 ):
                    vk.setBook( i )
                    print( t, i, vk.getBookName() )

        # Try a tree key on a GenBook
        module = library.getModule( "Westminster" )
        print( "\nmodule {} ({}) '{}'".format( module.getName(), module.getType(), module.getDescription() ) )
        def getGenBookTOC( tk, parent ):
            if tk is None: # obtain one from the module
                tk = Sword.TreeKey_castTo( module.getKey() ) # Only works for gen books
            if tk and tk.firstChild():
                while True:
                    print( " ", tk.getText() )
                    # Keep track of the information for custom implementation
                    #Class *item = storeItemInfoForLaterUse(parent, text);
                    item = (parent) # temp ....................
                    if tk.hasChildren():
                        print( "  Getting children..." )
                        getGenBookTOC( tk, item )
                    if not tk.nextSibling(): break
        # end of getGenBookTOC
        getGenBookTOC( None, None )

    #Find( "sw" ) # lots!
    #Find( "store" ) # storeItemInfoForLaterUse
    #Find( "getGlobal" ) # should be lots
# end of demo

if __name__ == '__main__':
    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( ProgName, ProgVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    demo()

    BibleOrgSysGlobals.closedown( ProgName, ProgVersion )
# end of SwordResources.py