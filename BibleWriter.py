#!/usr/bin/python3
#
# BibleWriter.py
#   Last modified: 2013-04-13 by RJH (also update versionString below)
#
# Module handling the USFM markers for Bible books
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
Module for exporting Bibles in various formats including USFM, USX, and OSIS.
"""

progName = "Bible writer"
versionString = "0.05"


import sys, os, logging, datetime
from gettext import gettext as _
from collections import OrderedDict

import Globals
from InternalBible import InternalBible
from BibleOrganizationalSystems import BibleOrganizationalSystem
from BibleReferences import BibleReferenceList
from XMLWriter import XMLWriter
#from USFMBible import USFMBible


class BibleWriter( InternalBible ):
    """
    Class to export Bibles.

    """
    def x__init__( self, internalBibleObject ):
        """
        #    Create the object.
        #    """
        #USFMBible.__init__( self, sourceFolder, givenName, encoding )
        assert( isinstance( internalBibleObject, InternalBible ) )
        self.internalBibleObject = internalBibleObject
        self.genericBOS = BibleOrganizationalSystem( "GENERIC-KJV-81" )
        #self.genericBRL = BibleReferenceList( self.genericBOS, BibleObject=self ) # IT'S NOT DEFINED YET
    # end of BibleWriter.__init_


    def x__str__( self ):
        """
        This method returns the string representation of a Bible.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = "Bible Writer object"
        if self.name: result += ('\n' if result else '') + self.name
        if self.sourceFolder: result += ('\n' if result else '') + "  From: " + self.sourceFolder
        result += ('\n' if result else '') + "  Number of books = " + str(len(self.books))
        return result
    # end of BibleWriter.__str__


    def xloadAll( self ):
        """ Load the object from the USFM files """
        USFMBible.loadAll( self )
        #if Globals.commandLineOptions.export:
        #self.genericBOS = BibleOrganizationalSystem( "GENERIC-KJV-81" )
        self.genericBRL = BibleReferenceList( self.genericBOS, BibleObject=self )
    # end of BibleWriter.loadAll


    def setupWriter( self ):
        self.genericBOS = BibleOrganizationalSystem( "GENERIC-KJV-81" )
        self.genericBRL = BibleReferenceList( self.genericBOS, BibleObject=self )
    # end of BibleWriter.setupWriter


    def writeSwordLocale( self, name, description, BibleOrganizationalSystem, getBookNameFunction, localeFilepath ):
        """
        Writes a UTF-8 Sword locale file containing the book names and abbreviations.
        """
        if Globals.verbosityLevel>1: print( _("Writing Sword locale file {}...").format(localeFilepath) )

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
                        print( "ToProgrammer: vernac name IS in abbrevList -- what does this mean? Why? '{}' {}".format( vernacularName, abbrevList ) )
                    SwLocFile.write( '{}={}\n'.format( vernacularName, swordAbbrev ) ) # Write the UPPER CASE language book name and the Sword abbreviation
                    abbrevList.append( vernacularName )
                    if ' ' in vernacularName:
                        vernacularAbbrev = vernacularName.replace( ' ', '' )
                        assert( vernacularAbbrev not in abbrevList )
                        SwLocFile.write( '{}={}\n'.format( vernacularAbbrev, swordAbbrev ) ) # Write the UPPER CASE language book name and the Sword abbreviation
                        abbrevList.append( vernacularAbbrev )
            for BBB in BibleOrganizationalSystem.getBookList(): # Second pass writes the shorter vernacular book abbreviations
                if BBB in self.books:
                    swordAbbrev = Globals.BibleBooksCodes.getSwordAbbreviation( BBB )
                    vernacularName = getBookNameFunction(BBB).replace( ' ', '' ).upper()
                    if len(vernacularName)>4  or (len(vernacularName)>3 and not vernacularName[0].isdigit):
                        vernacularAbbrev = vernacularName[:4 if vernacularName[0].isdigit() else 3]
                        if vernacularAbbrev in abbrevList:
                            if swordAbbrev == 'Philem':
                                vernacularAbbrev = vernacularName[:5]
                                if vernacularAbbrev not in abbrevList:
                                    SwLocFile.write( '{}={}\n'.format( vernacularAbbrev, swordAbbrev ) ) # Write the UPPER CASE language book name and the Sword abbreviation
                                    abbrevList.append( vernacularAbbrev )
                            else: print( "   Oops, shouldn't have written {} (also could be {}) to Sword locale file".format( vernacularAbbrev, swordAbbrev ) ) # Need to fix this
                        else:
                            SwLocFile.write( '{}={}\n'.format( vernacularAbbrev, swordAbbrev ) ) # Write the UPPER CASE language book name and the Sword abbreviation
                            abbrevList.append( vernacularAbbrev )
                    changed = False
                    for something in ( ".''̉΄" ): # Remove punctuation and glottals (all UPPER CASE here)
                        if something in vernacularAbbrev:
                            vernacularAbbrev = vernacularAbbrev.replace( something, '' )
                            changed = True
                    if changed:
                        if vernacularAbbrev in abbrevList:
                            print( "   Oops, maybe shouldn't have written {} (also could be {}) to Sword locale file".format( vernacularAbbrev, swordAbbrev ) )
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
                            print( "   Oops, maybe shouldn't have written {} (also could be {}) to Sword locale file".format( vernacularAbbrev, swordAbbrev ) )
                        else:
                            SwLocFile.write( '{}={}\n'.format( vernacularAbbrev, swordAbbrev ) )
                            abbrevList.append( vernacularAbbrev )

        if Globals.verbosityLevel>1: print( _("  Wrote {} book names and {} abbreviations.").format( len(bookList), len(abbrevList) ) )
    # end of BibleWriter.writeSwordLocale


    def toMediaWiki( self, controlDict, validationSchema=None ):
        """
        Using settings from the given control file,
            converts the USFM information to a Media Wiki file.
        """
        assert( controlDict and isinstance( controlDict, dict ) )
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
                                if Globals.LogErrorsFlag and not BRL.containsReference( BBB, currentChapterNumberString, verseNumberString ):
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
                                if Globals.LogErrorsFlag and not BRL.containsReference( BBB, currentChapterNumberString, verseNumberString ):
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
                    #    assert( BBB in Globals.BibleBooksCodes.getSingleChapterBooksList() )
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

        if Globals.verbosityLevel>1: print( _("Exporting to MediaWiki format...") )
        outputFolder = "OutputFiles"
        if not os.access( outputFolder, os.F_OK ): os.mkdir( outputFolder ) # Make the empty folder if there wasn't already one there
        xw = XMLWriter().setOutputFilePath( controlDict["MediaWikiOutputFilename"], outputFolder )
        xw.setHumanReadable()
        xw.start()
        for BBB,bookData in self.books.items():
            writeBook( xw, BBB, bookData )
        xw.close()
        if unhandledMarkers and Globals.verbosityLevel>0: print( "  " + _("WARNING: Unhandled toMediaWiki USFM markers were {}").format(unhandledMarkers) )
        if validationSchema: return xw.validateXML( validationSchema )
    # end of BibleWriter.toMediaWiki



    def toZefania_XML( self, controlDict, validationSchema=None ):
        """
        Using settings from the given control file,
            converts the USFM information to a UTF-8 Zefania XML file.

        This format is roughly documented at http://de.wikipedia.org/wiki/Zefania_XML
            but more fields can be discovered by looking at downloaded files.
        """
        assert( controlDict and isinstance( controlDict, dict ) )
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
            writerObject.writeLineOpenClose( 'creator', 'USFMBible.py' )
            writerObject.writeLineOpenClose( 'type', 'bible text' )
            if "ZefaniaLanguage" in controlDict and controlDict["ZefaniaLanguage"]: writerObject.writeLineOpenClose( 'language', controlDict["ZefaniaLanguage"] )
            if "ZefaniaRights" in controlDict and controlDict["ZefaniaRights"]: writerObject.writeLineOpenClose( 'rights', controlDict["ZefaniaRights"] )
            writerObject.writeLineClose( 'INFORMATION' )
        # end of toZefania_XML:writeHeader

        def writeBook( writerObject, BBB, bkData ):
            """Writes a book to the Zefania XML writerObject."""
            #print( 'BIBLEBOOK', [('bnumber',Globals.BibleBooksCodes.getReferenceNumber(BBB)), ('bname',Globals.BibleBooksCodes.getEnglishName_NR(BBB)), ('bsname',Globals.BibleBooksCodes.getOSISAbbreviation(BBB))] )
            OSISAbbrev = Globals.BibleBooksCodes.getOSISAbbreviation( BBB )
            if not OSISAbbrev: logging.error( "toZefania: Can't write {} Zefania book because no OSIS code available".format( BBB ) ); return
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
                    if not text: print( "Missing text for v" ); continue
                    verseNumberString = text # Used below
                    #writerObject.writeLineOpenClose ( 'VERS', verseText, ('vnumber',verseNumberString) )
                elif marker=='v~':
                    #print( "Text '{}'".format( text ) )
                    if not text: print( "Missing text for v~" ); continue
                    # TODO: We haven't stripped out character fields from within the verse -- not sure how Zefania handles them yet
                    if not text: # this is an empty (untranslated) verse
                        text = '- - -' # but we'll put in a filler
                    writerObject.writeLineOpenClose ( 'VERS', text, ('vnumber',verseNumberString) )
                else: unhandledMarkers.add( marker )
            if haveOpenChapter:
                writerObject.writeLineClose( 'CHAPTER' )
            writerObject.writeLineClose( 'BIBLEBOOK' )
        # end of toZefania_XML:writeBook

        # Set-up our Bible reference system
        if controlDict['PublicationCode'] == "GENERIC":
            BOS = self.genericBOS
            BRL = self.genericBRL
        else:
            BOS = BibleOrganizationalSystem( controlDict["PublicationCode"] )
            BRL = BibleReferenceList( BOS, BibleObject=None )

        if Globals.verbosityLevel>1: print( _("Exporting to Zefania format...") )
        outputFolder = "OutputFiles"
        if not os.access( outputFolder, os.F_OK ): os.mkdir( outputFolder ) # Make the empty folder if there wasn't already one there
        xw = XMLWriter().setOutputFilePath( controlDict["ZefaniaOutputFilename"], outputFolder )
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
        if unhandledMarkers and Globals.verbosityLevel>0: print( "  " + _("WARNING: Unhandled toZefania USFM markers were {}").format(unhandledMarkers) )
        if validationSchema: return xw.validateXML( validationSchema )
    # end of BibleWriter.toZefania_XML


    def toUSX_XML( self, controlDict, validationSchema=None ):
        """
        Using settings from the given control file,
            converts the USFM information to UTF-8 USX XML files.

        If a schema is given (either a path or URL), the XML output files are validated.
        """
        assert( controlDict and isinstance( controlDict, dict ) )
        unhandledMarkers = set()
        allCharMarkers = self.USFMMarkers.getCharacterMarkersList( expandNumberableMarkers=True )
        #print( allCharMarkers ); halt

        def writeBook( BBB, bkData ):
            """ Writes a book to the USX XML writerObject. """

            def handleInternalTextMarkersForUSX( text ):
                """ Handles character formatting markers within the text. """
                #if '\\' in text: print( "toUSX:hITM:", BBB, c, v, marker, "'"+text+"'" )
                adjText = text
                haveOpenChar = False
                for charMarker in allCharMarkers:
                    fullCharMarker = '\\' + charMarker + ' '
                    if fullCharMarker in adjText:
                        if haveOpenChar:
                            adjText = adjText.replace( 'CLOSED_BIT', ' closed="false"' ) # Fix up closed bit since it wasn't closed
                            if Globals.LogErrorsFlag: logging.info( "toUSX: USX export had to close automatically in {} {}:{} {}:'{}' now '{}'".format( BBB, c, v, marker, text, adjText ) ) # The last marker presumably only had optional closing (or else we just messed up nesting markers)
                        adjText = adjText.replace( fullCharMarker, '{}<char style="{}"CLOSED_BIT>'.format( '</char>' if haveOpenChar else '', charMarker ) )
                        haveOpenChar = True
                    endCharMarker = '\\' + charMarker + '*'
                    if endCharMarker in adjText:
                        if not haveOpenChar: # Then we must have a missing open marker (or extra closing marker)
                            if Globals.LogErrorsFlag: logging.error( "toUSX: Ignored extra '{}' closing marker in {} {}:{} {}:'{}' now '{}'".format( charMarker, BBB, c, v, marker, text, adjText ) )
                            adjText = adjText.replace( endCharMarker, '' ) # Remove the unused marker
                        else: # looks good
                            adjText = adjText.replace( 'CLOSED_BIT', '' ) # Fix up closed bit since it was specifically closed
                            adjText = adjText.replace( endCharMarker, '</char>' )
                            haveOpenChar = False
                if haveOpenChar:
                    adjText = adjText.replace( 'CLOSED_BIT', ' closed="false"' ) # Fix up closed bit since it wasn't closed
                    adjText += '{}</char>'.format( '' if adjText[-1]==' ' else ' ')
                    if Globals.LogErrorsFlag: logging.info( "toUSX: Had to close automatically in {} {}:{} {}:'{}' now '{}'".format( BBB, c, v, marker, text, adjText ) )
                if '\\' in adjText: logging.critical( "toUSX: Didn't handle a backslash in {} {}:{} {}:'{}' now '{}'".format( BBB, c, v, marker, text, adjText ) )
                return adjText
            # end of handleInternalTextMarkersForUSX

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
                    USXxrefXML = '<note style="x" '
                    xoOpen = xtOpen = False
                    for j,token in enumerate(USXxref.split('\\')):
                        #print( "toUSX:processXRef", j, "'"+token+"'", "from", '"'+USXxref+'"', xoOpen, xtOpen )
                        lcToken = token.lower()
                        if j==0: # The first token (but the x has already been removed)
                            USXxrefXML += 'caller="{}">'.format( token.rstrip() )
                        elif lcToken.startswith('xo '): # xref reference follows
                            if xoOpen: # We have multiple xo fields one after the other (probably an encoding error)
                                assert( not xtOpen )
                                USXxrefXML += ' closed="false">' + adjToken + '</char>'
                                xoOpen = False
                            if xtOpen: # if we have multiple cross-references one after the other
                                USXxrefXML += ' closed="false">' + adjToken + '</char>'
                                xtOpen = False
                            adjToken = token[3:]
                            USXxrefXML += '<char style="xo"'
                            xoOpen = True
                        elif lcToken.startswith('xo*'):
                            assert( xoOpen and not xtOpen )
                            USXxrefXML += '>' + adjToken + '</char>'
                            xoOpen = False
                        elif lcToken.startswith('xt '): # xref text follows
                            if xtOpen: # Multiple xt's in a row
                                assert( not xoOpen )
                                USXxrefXML += ' closed="false">' + adjToken + '</char>'
                            if xoOpen:
                                USXxrefXML += ' closed="false">' + adjToken + '</char>'
                                xoOpen = False
                            adjToken = token[3:]
                            USXxrefXML += '<char style="xt"'
                            xtOpen = True
                        elif lcToken.startswith('xt*'):
                            assert( xtOpen and not xoOpen )
                            USXxrefXML += '>' + adjToken + '</char>'
                            xtOpen = False
                        #elif lcToken in ('xo*','xt*','x*',):
                        #    pass # We're being lazy here and not checking closing markers properly
                        else:
                            if Globals.LogErrorsFlag: logging.warning( _("toUSX: Unprocessed '{}' token in {} {}:{} xref '{}'").format( token, BBB, c, v, USXxref ) )
                    if xoOpen:
                        assert( not xtOpen )
                        USXxrefXML += ' closed="false">' + adjToken + '</char>'
                        xoOpen = False
                    if xtOpen:
                        USXxrefXML += ' closed="false">' + adjToken + '</char>'
                    USXxrefXML += '</note>'
                    return USXxrefXML
                # end of processXRef

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
                                assert( not fTextOpen )
                                if Globals.LogErrorsFlag: logging.error( _("toUSX: Two consecutive fr fields in {} {}:{} footnote '{}'").format( token, BBB, c, v, USXfootnote ) )
                            if fTextOpen:
                                assert( not frOpen )
                                USXfootnoteXML += ' closed="false">' + adjToken + '</char>'
                                fTextOpen = False
                            assert( not fCharOpen )
                            adjToken = token[3:]
                            USXfootnoteXML += '<char style="fr"'
                            frOpen = True
                        elif lcToken.startswith('fr* '):
                            assert( frOpen and not fTextOpen and not fCharOpen )
                            USXfootnoteXML += '>' + adjToken + '</char>'
                            frOpen = False
                        elif lcToken.startswith('ft ') or lcToken.startswith('fq ') or lcToken.startswith('fqa ') or lcToken.startswith('fv ') or lcToken.startswith('fk '):
                            if fCharOpen:
                                assert( not frOpen )
                                USXfootnoteXML += '>' + adjToken + '</char>'
                                fCharOpen = False
                            if frOpen:
                                assert( not fTextOpen )
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
                            assert( fTextOpen and not frOpen and not fCharOpen )
                            USXfootnoteXML += '>' + adjToken + '</char>'
                            fTextOpen = False
                        else: # Could be character formatting (or closing of character formatting)
                            subTokens = lcToken.split()
                            firstToken = subTokens[0]
                            #print( "ft", firstToken )
                            if firstToken in allCharMarkers: # Yes, confirmed
                                if fCharOpen: # assume that the last one is closed by this one
                                    assert( not frOpen )
                                    USXfootnoteXML += '>' + adjToken + '</char>'
                                    fCharOpen = False
                                if frOpen:
                                    assert( not fCharOpen )
                                    USXfootnoteXML += ' closed="false">' + adjToken + '</char>'
                                    frOpen = False
                                USXfootnoteXML += '<char style="{}"'.format( firstToken )
                                adjToken = token[len(firstToken)+1:] # Get the bit after the space
                                fCharOpen = firstToken
                            else: # The problem is that a closing marker doesn't have to be followed by a space
                                if firstToken[-1]=='*' and firstToken[:-1] in allCharMarkers: # it's a closing tag (that was followed by a space)
                                    if fCharOpen:
                                        assert( not frOpen )
                                        if not firstToken.startswith( fCharOpen+'*' ): # It's not a matching tag
                                            if Globals.LogErrorsFlag: logging.warning( _("toUSX: '{}' closing tag doesn't match '{}' in {} {}:{} footnote '{}'").format( firstToken, fCharOpen, BBB, c, v, USXfootnote ) )
                                        USXfootnoteXML += '>' + adjToken + '</char>'
                                        fCharOpen = False
                                    elif Globals.LogErrorsFlag: logging.warning( _("toUSX: '{}' closing tag doesn't match in {} {}:{} footnote '{}'").format( firstToken, BBB, c, v, USXfootnote ) )
                                else:
                                    ixAS = firstToken.find( '*' )
                                    #print( firstToken, ixAS, firstToken[:ixAS] if ixAS!=-1 else '' )
                                    if ixAS!=-1 and ixAS<4 and firstToken[:ixAS] in allCharMarkers: # it's a closing tag
                                        if fCharOpen:
                                            assert( not frOpen )
                                            if not firstToken.startswith( fCharOpen+'*' ): # It's not a matching tag
                                                if Globals.LogErrorsFlag: logging.warning( _("toUSX: '{}' closing tag doesn't match '{}' in {} {}:{} footnote '{}'").format( firstToken, fCharOpen, BBB, c, v, USXfootnote ) )
                                            USXfootnoteXML += '>' + adjToken + '</char>'
                                            fCharOpen = False
                                        elif Globals.LogErrorsFlag: logging.warning( _("toUSX: '{}' closing tag doesn't match in {} {}:{} footnote '{}'").format( firstToken, BBB, c, v, USXfootnote ) )
                                    else:
                                        if Globals.LogErrorsFlag: logging.warning( _("toUSX: Unprocessed '{}' token in {} {}:{} footnote '{}'").format( firstToken, BBB, c, v, USXfootnote ) )
                                        #print( allCharMarkers )
                                        #halt
                    #print( "  ", frOpen, fCharOpen, fTextOpen )
                    if frOpen:
                        if Globals.LogErrorsFlag: logging.warning( _("toUSX: Unclosed 'fr' token in {} {}:{} footnote '{}'").format( BBB, c, v, USXfootnote) )
                        assert( not fCharOpen and not fTextOpen )
                        USXfootnoteXML += ' closed="false">' + adjToken + '</char>'
                    if fCharOpen and Globals.LogErrorsFlag: logging.warning( _("toUSX: Unclosed '{}' token in {} {}:{} footnote '{}'").format( fCharOpen, BBB, c, v, USXfootnote) )
                    if fTextOpen: USXfootnoteXML += ' closed="false">' + adjToken + '</char>'
                    USXfootnoteXML += '</note>'
                    #print( '', USXfootnote, USXfootnoteXML )
                    #if BBB=='EXO' and c=='17' and v=='7': halt
                    return USXfootnoteXML
                # end of processFootnote


                adjText = text
                offset = 0
                for extraType, extraIndex, extraText, cleanExtraText in extras: # do any footnotes and cross-references
                    #print( "{} {}:{} Text='{}' eT={}, eI={}, eText='{}'".format( BBB, c, v, text, extraType, extraIndex, extraText ) )
                    adjIndex = extraIndex - offset
                    lenT = len( adjText )
                    if adjIndex > lenT: # This can happen if we have verse/space/notes at end (and the space was deleted after the note was separated off)
                        if Globals.LogErrorsFlag: logging.warning( _("toUSX: Space before note at end of verse in {} {}:{} has been lost").format( BBB, c, v ) )
                        # No need to adjust adjIndex because the code below still works
                    elif adjIndex<0 or adjIndex>lenT: # The extras don't appear to fit correctly inside the text
                        print( "toUSX: Extras don't fit inside verse at {} {}:{}: eI={} o={} len={} aI={}".format( BBB, c, v, extraIndex, offset, len(text), adjIndex ) )
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
            if not USXAbbrev and Globals.LogErrorsFlag: logging.error( "toUSX: Can't write {} USX book because no USFM code available".format( BBB ) ); return
            if not USXNumber and Globals.LogErrorsFlag: logging.error( "toUSX: Can't write {} USX book because no USX number available".format( BBB ) ); return

            c = v = '0'
            xw = XMLWriter().setOutputFilePath( USXNumber+USXAbbrev+".usx", USXOutputFolder )
            xw.setHumanReadable()
            xw.spaceBeforeSelfcloseTag = True
            xw.start( lineEndings='w', writeBOM=True ) # Try to imitate Paratext output as closely as possible
            xw.writeLineOpen( 'usx' )
            haveOpenPara = paraJustOpened = False
            for marker,originalMarker,text,cleanText,extras in bkData._processedLines: # Process USFM lines
                markerShouldHaveContent = self.USFMMarkers.markerShouldHaveContent( marker )
                #print( BBB, c, v, marker, markerShouldHaveContent, haveOpenPara, paraJustOpened )
                adjText = handleNotes( text, extras )
                if marker == 'id':
                    if haveOpenPara: # This should never happen coz the ID line should have been the first line in the file
                        if Globals.LogErrorsFlag: logging.error( "toUSX: Book {}{} has a id line inside an open paragraph: '{}'".format( BBB, " ({})".format(USXAbbrev) if USXAbbrev!=BBB else '', adjText ) )
                        xw.removeFinalNewline( True )
                        xw.writeLineClose( 'para' )
                        haveOpenPara = False
                    if len(adjText)!=3 and adjText[3]!=' ': # Doesn't seem to have a standard BBB at the beginning of the ID line
                        if Globals.LogErrorsFlag: logging.warning( "toUSX: Book {}{} has a non-standard id line: '{}'".format( BBB, " ({})".format(USXAbbrev) if USXAbbrev!=BBB else '', adjText ) )
                    if adjText[0:3] != USXAbbrev:
                        if Globals.LogErrorsFlag: logging.error( "toUSX: Book {}{} might be incorrect -- we got: '{}'".format( BBB, " ({})".format(USXAbbrev) if USXAbbrev!=BBB else '', adjText[0:3] ) )
                    adjText = adjText[4:] # Remove the book code from the ID line because it's put in as an attribute
                    if adjText: xw.writeLineOpenClose( 'book', handleInternalTextMarkersForUSX(adjText)+' ', [('code',USXAbbrev),('style',marker)] )
                    elif not text and Globals.LogErrorsFlag: logging.error( "toUSX: {} {}:{} has a blank id line that was ignored".format( BBB, c, v ) )
                elif marker == 'c':
                    if haveOpenPara:
                        xw.removeFinalNewline( True )
                        xw.writeLineClose( 'para' )
                        haveOpenPara = False
                    c = adjText
                    #print( 'c', c )
                    xw.writeLineOpenSelfclose ( 'chapter', [('number',c),('style','c')] )
                elif marker == 'c~': # Don't really know what this stuff is!!!
                    if not adjText: print( "toUSX: Missing text for c~" ); continue
                    # TODO: We haven't stripped out character fields from within the text -- not sure how USX handles them yet
                    xw.removeFinalNewline( True )
                    xw.writeLineText( handleInternalTextMarkersForUSX(adjText)+' ', noTextCheck=True ) # no checks coz might already have embedded XML
                elif marker == 'c#': # Chapter number added for printing
                    pass # Just ignore it completely
                elif marker == 'v':
                    v = adjText
                    if paraJustOpened: paraJustOpened = False
                    else: xw.removeFinalNewline( True )
                    xw.writeLineOpenSelfclose ( 'verse', [('number',v),('style','v')] )
                elif marker == 'v~':
                    if not adjText: print( "toUSX: Missing text for v~" ); continue
                    # TODO: We haven't stripped out character fields from within the verse -- not sure how USX handles them yet
                    xw.removeFinalNewline( True )
                    xw.writeLineText( handleInternalTextMarkersForUSX(adjText)+' ', noTextCheck=True ) # no checks coz might already have embedded XML
                elif markerShouldHaveContent == 'N': # N = never, e.g., b, nb
                    if haveOpenPara:
                        xw.removeFinalNewline( True )
                        xw.writeLineClose( 'para' )
                        haveOpenPara = False
                    if adjText: print( "toUSX: {} {}:{} has a {} line containing text ('{}') that was ignored".format( BBB, c, v, originalMarker, adjText ) )
                    xw.writeLineOpenSelfclose ( 'para', ('style',marker) )
                elif markerShouldHaveContent == 'S': # S = sometimes, e.g., p,pi,q,q1,q2,q3,q4,m
                    if haveOpenPara:
                        xw.removeFinalNewline( True )
                        xw.writeLineClose( 'para' )
                        haveOpenPara = False
                    if not adjText: xw.writeLineOpen( 'para', ('style',originalMarker) )
                    else: xw.writeLineOpenText( 'para', handleInternalTextMarkersForUSX(adjText)+' ', ('style',originalMarker), noTextCheck=True ) # no checks coz might already have embedded XML
                    haveOpenPara = paraJustOpened = True
                else:
                    #assert( markerShouldHaveContent == 'A' ) # A = always, e.g.,  ide, mt, h, s, ip, etc.
                    if markerShouldHaveContent != 'A':
                        print( "ToProgrammer: should be 'A': '{}' is '{}' Why?".format( marker, markerShouldHaveContent ) )
                    if haveOpenPara:
                        xw.removeFinalNewline( True )
                        xw.writeLineClose( 'para' )
                        haveOpenPara = False
                    if adjText: xw.writeLineOpenClose( 'para', handleInternalTextMarkersForUSX(adjText)+' ', ('style',originalMarker), noTextCheck=True ) # no checks coz might already have embedded XML
                    else: logging.info( "toUSX: {} {}:{} has a blank {} line that was ignored".format( BBB, c, v, originalMarker ) )
            if haveOpenPara:
                xw.removeFinalNewline( True )
                xw.writeLineClose( 'para' )
            xw.writeLineClose( 'usx' )
            xw.close( writeFinalNL=True ) # Try to imitate Paratext output as closely as possible
            if validationSchema: return xw.validateXML( validationSchema )
        # end of toUSX_XML:writeBook

        # Set-up our Bible reference system
        if controlDict['PublicationCode'] == "GENERIC":
            BOS = self.genericBOS
            BRL = self.genericBRL
        else:
            BOS = BibleOrganizationalSystem( controlDict["PublicationCode"] )
            BRL = BibleReferenceList( BOS, BibleObject=None )

        if Globals.verbosityLevel>1: print( _("Exporting to USX format...") )
        outputFolder = "OutputFiles"
        if not os.access( outputFolder, os.F_OK ): os.mkdir( outputFolder ) # Make the empty folder if there wasn't already one there
        USXOutputFolder = os.path.join( "OutputFiles/", "USX output/" )
        if not os.access( USXOutputFolder, os.F_OK ): os.mkdir( USXOutputFolder ) # Make the empty folder if there wasn't already one there

        validationResults = ( 0, '', '', ) # xmllint result code, program output, error output
        for BBB,bookData in self.books.items():
            bookResults = writeBook( BBB, bookData )
            if validationSchema:
                if bookResults[0] > validationResults[0]: validationResults = ( bookResults[0], validationResults[1], validationResults[2], )
                if bookResults[1]: validationResults = ( validationResults[0], validationResults[1] + bookResults[1], validationResults[2], )
                if bookResults[2]: validationResults = ( validationResults[0], validationResults[1], validationResults[2] + bookResults[2], )
        if unhandledMarkers and Globals.verbosityLevel>0: print( "  " + _("WARNING: Unhandled toUSX USFM markers were {}").format(unhandledMarkers) )
        if validationSchema: return validationResults
    # end of BibleWriter.toUSX_XML


    def toOSIS_XML( self, controlDict, validationSchema=None ):
        """
        Using settings from the given control file,
            converts the USFM information to one or more UTF-8 OSIS XML files.

        If a schema is given (either a path or URL), the XML output file(s) is validated.

        TODO: We're not consistent about handling errors: sometimes we use assert, sometime raise (both of which abort the program), and sometimes log errors or warnings.
        """
        assert( controlDict and isinstance( controlDict, dict ) )

        # Set-up our Bible reference system
        #if Globals.debugFlag: print( "BibleWriter:toOSIS_XML publicationCode =", controlDict["PublicationCode"] )
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
        outputFolder = "OutputFiles"
        if not os.access( outputFolder, os.F_OK ): os.mkdir( outputFolder ) # Make the empty folder if there wasn't already one there

        # Let's write a Sword locale while we're at it
        self.writeSwordLocale( controlDict["xmlLanguage"], controlDict["LanguageName"], BOS, getBookNameFunction, os.path.join( outputFolder, "SwLocale-utf8.conf" ) )
        #if Globals.verbosityLevel>1: print( _("Writing Sword locale file {}...").format(SwLocFilepath) )
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
        # end of toOSIS_XML:writeHeader

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
                    assert( count1 == count2 )
                    return helpText
                # end of checkTextHelper

                adjText = textToCheck
                if '<<' in adjText or '>>' in adjText:
                    if Globals.LogErrorsFlag: logging.warning( _("toOSIS: Unexpected double angle brackets in {}: '{}' field is '{}'").format( toOSISGlobals["verseRef"], marker, textToCheck ) )
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
                        assert( ix2 > ix1 )
                        #print( "was '{}'".format( adjText ) )
                        adjText = adjText[:ix1] + adjText[ix2+5:] # Remove the \\fig..\\fig* field
                        #print( "now '{}'".format( adjText ) )
                        print( _("toOSIS: Figure reference removed for OSIS generation in {}: '{}' field").format( toOSISGlobals["verseRef"], marker ), file=sys.stderr )
                if checkLeftovers and '\\' in adjText:
                    if Globals.LogErrorsFlag: logging.error( _("toOSIS: We still have some unprocessed backslashes for OSIS in {}: '{}' field is '{}'").format( toOSISGlobals["verseRef"], marker, textToCheck ) )
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
                            if rest != '-' and Globals.LogErrorsFlag: logging.warning( _("toOSIS: We got something else here other than hyphen (probably need to do something with it): {} '{}' from '{}'").format(chapterRef, token, text) )
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
                                if Globals.LogErrorsFlag and not BRL.containsReference( BBB, currentChapterNumberString, verseNumberString ):
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
                            if rest != '-' and Globals.LogErrorsFlag: logging.warning( _("toOSIS: We got something else here other than hyphen (probably need to do something with it): {} '{}' from '{}'").format(chapterRef, token, text) )
                        elif lcToken in ('xo*','xt*','x*',):
                            pass # We're being lazy here and not checking closing markers properly
                        else:
                            if Globals.LogErrorsFlag: logging.warning( _("toOSIS: Unprocessed '{}' token in {} xref '{}'").format( token, toOSISGlobals["verseRef"], USFMxref ) )
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
                                if Globals.LogErrorsFlag and not BRL.containsReference( BBB, currentChapterNumberString, verseNumberString ):
                                    logging.error( _("toOSIS: Footnote at {} {}:{} seems to contain the wrong self-reference anchor '{}'").format(BBB,currentChapterNumberString,verseNumberString, token[3:].rstrip()) )
                        elif lcToken.startswith('ft ') or lcToken.startswith('fr* '): # footnote text follows
                            OSISfootnote += token[3:]
                        elif lcToken.startswith('fq ') or token.startswith('fqa '): # footnote quote follows -- NOTE: We also assume here that the next marker closes the fq field
                            OSISfootnote += '<catchWord>{}</catchWord>'.format(token[3:]) # Note that the trailing space goes in the catchword here -- seems messy
                        elif lcToken in ('fr*','fr* ','ft*','ft* ','fq*','fq* ','fqa*','fqa* ',):
                            pass # We're being lazy here and not checking closing markers properly
                        else:
                            if Globals.LogErrorsFlag: logging.warning( _("toOSIS: Unprocessed '{}' token in {} footnote '{}'").format(token, toOSISGlobals["verseRef"], USFMfootnote) )
                    OSISfootnote += '</note>'
                    #print( '', OSISfootnote )
                    #if currentChapterNumberString=='5' and verseNumberString=='29': halt
                    return OSISfootnote
                # end of processFootnote

                #if extras: print( '\n', chapterRef )
                assert( offset >= 0 )
                for extraType, extraIndex, extraText, cleanExtraText in extras: # do any footnotes and cross-references
                    adjIndex = extraIndex - offset
                    lenV = len( verse )
                    if adjIndex > lenV: # This can happen if we have verse/space/notes at end (and the space was deleted after the note was separated off)
                        if Globals.LogErrorsFlag: logging.warning( _("toOSIS: Space before note at end of verse in {} has been lost").format( toOSISGlobals["verseRef"] ) )
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
                    if Globals.LogErrorsFlag: logging.critical( _("toOSIS: Doesn't handle verse number of form '{}' yet for {}").format(verseNumberString,chapterRef) )
                    sID = osisID = toOSISGlobals["verseRef"] = chapterRef + '.' + verseNumberString # Try it anyway
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
                    if Globals.LogErrorsFlag: logging.error( "toOSIS: closeAnyOpenSection: Why was L open at {}?".format( toOSISGlobals["verseRef"] ) )
                    writerObject.writeLineClose( 'l' )
                    haveOpenL = False
                if haveOpenLG:
                    if Globals.LogErrorsFlag: logging.error( "toOSIS: closeAnyOpenSection: Why was LG open at {}?".format( toOSISGlobals["verseRef"] ) )
                    writerObject.writeLineClose( 'lg' )
                    haveOpenLG = False
                if haveOpenParagraph:
                    if Globals.LogErrorsFlag: logging.error( "toOSIS: closeAnyOpenSection: Why was paragraph open at {}?".format( toOSISGlobals["verseRef"] ) )
                    writerObject.writeLineClose( 'p' )
                    haveOpenParagraph = False
                if haveOpenSubsection:
                    if Globals.LogErrorsFlag: logging.error( "toOSIS: closeAnyOpenSection: Why was subsection open at {}?".format( toOSISGlobals["verseRef"] ) )
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
                if Globals.LogErrorsFlag: logging.error( "toOSIS: Can't write {} OSIS book because no OSIS code available".format( BBB ) )
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
                    elif Globals.LogErrorsFlag: logging.error( _("toOSIS: {} Have a blank {} field—ignoring it").format( toOSISGlobals["verseRef"], marker ) )
                elif marker=='ip':
                    if not haveOpenIntro: # Shouldn't happen but we'll try our best
                        if Globals.LogErrorsFlag: logging.error( _("toOSIS: {} Have an ip not in an introduction section—ignoring it").format( toOSISGlobals["verseRef"] ) )
                        writerObject.writeLineOpen( 'div', [('type',"introduction"),('canonical',"false")] )
                        haveOpenIntro = True
                    closeAnyOpenParagraph()
                    writerObject.writeLineOpenText( 'p', checkText(text), noTextCheck=True ) # Sometimes there's text
                    haveOpenParagraph = True
                elif marker=='iot':
                    if not haveOpenIntro: # Shouldn't happen but we'll try our best
                        if Globals.LogErrorsFlag: logging.error( _("toOSIS: {} Have an iot not in an introduction section").format( toOSISGlobals["verseRef"] ) )
                        writerObject.writeLineOpen( 'div', [('type',"introduction"),('canonical',"false")] )
                        haveOpenIntro = True
                    if haveOpenSection or haveOpenOutline: print( "Not handled yet iot in {} hOS={} hOO={}".format(BBB,haveOpenSection,haveOpenOutline) )
                    closeAnyOpenParagraph()
                    writerObject.writeLineOpen( 'div', ('type',"outline") )
                    if text: writerObject.writeLineOpenClose( 'title', checkText(text) )
                    writerObject.writeLineOpen( 'list' )
                    haveOpenOutline = True
                elif marker=='io1':
                    if not haveOpenIntro: # Shouldn't happen but we'll try our best
                        if Globals.LogErrorsFlag: logging.error( _("toOSIS: {} Have an io1 not in an introduction section").format( toOSISGlobals["verseRef"] ) )
                        writerObject.writeLineOpen( 'div', [('type',"introduction"),('canonical',"false")] )
                        haveOpenIntro = True
                    if not haveOpenOutline: # Shouldn't happen but we'll try our best
                        if Globals.LogErrorsFlag: logging.warning( _("toOSIS: {} Have an io1 not in an outline section").format( toOSISGlobals["verseRef"] ) )
                        closeAnyOpenParagraph()
                        writerObject.writeLineOpen( 'div', ('type',"outline") )
                        writerObject.writeLineOpen( 'list' )
                        haveOpenOutline = True
                    if text: writerObject.writeLineOpenClose( 'item', checkText(text) )
                elif marker=='io2':
                    if not haveOpenIntro: raise Exception( "toOSIS: Have an io2 not in an introduction section" )
                    if not haveOpenOutline: raise Exception( "toOSIS: Have an io2 not in an outline section" )
                    writerObject.writeLineOpenClose( 'item', checkText(text) ) # TODO: Shouldn't this be different from an io1???
                elif marker=='c':
                    if haveOpenVsID != False: # Close the previous verse
                        writerObject.writeLineOpenSelfclose( 'verse', ('eID',haveOpenVsID) )
                        haveOpenVsID = False
                    if haveOpenOutline:
                        if text!='1' and not text.startswith('1 ') and Globals.LogErrorsFlag: logging.error( _("toOSIS: {} This should normally be chapter 1 to close the introduction (got '{}')").format( toOSISGlobals["verseRef"], text ) )
                        writerObject.writeLineClose( 'list' )
                        writerObject.writeLineClose( 'div' )
                        haveOpenOutline = False
                    if haveOpenIntro:
                        if text!='1' and not text.startswith('1 ') and Globals.LogErrorsFlag: logging.error( _("toOSIS: {} This should normally be chapter 1 to close the introduction (got '{}')").format( toOSISGlobals["verseRef"], text ) )
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
                    elif Globals.LogErrorsFlag: logging.info( _("toOSIS: Blank ms1 section heading encountered after {}:{}").format( currentChapterNumberString, verseNumberString ) )
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
                    elif Globals.LogErrorsFlag: logging.info( _("toOSIS: Blank s1 section heading encountered after {}:{}").format( currentChapterNumberString, verseNumberString ) )
                elif marker=='s2':
                    if haveOpenParagraph:
                        closeAnyOpenLG()
                        closeAnyOpenParagraph()
                    closeAnyOpenSubsection()
                    writerObject.writeLineOpen( 'div', ('type', "subSection") )
                    haveOpenSubsection = True
                    if text: writerObject.writeLineOpenClose( 'title',checkText(text) ) # Section heading
                    elif Globals.LogErrorsFlag: logging.info( _("toOSIS: Blank s2 section heading encountered after {}:{}").format( currentChapterNumberString, verseNumberString ) )
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
                if Globals.LogErrorsFlag:
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
        # end of toOSIS_XML:writeBook

        if controlDict["osisFiles"]=="byBook": # Write an individual XML file for each book
            if Globals.verbosityLevel>1: print( _("Exporting individually to OSIS XML format...") )
            validationResults = ( 0, '', '', ) # xmllint result code, program output, error output
            for BBB,bookData in self.books.items(): # Process each Bible book
                xw = XMLWriter().setOutputFilePath( controlDict["osisOutputFilename"].replace('_Bible',"_Book-{}".format(BBB)), outputFolder )
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
                    bookResults = xw.validateXML( validationSchema )
                    if bookResults[0] > validationResults[0]: validationResults = ( bookResults[0], validationResults[1], validationResults[2], )
                    if bookResults[1]: validationResults = ( validationResults[0], validationResults[1] + bookResults[1], validationResults[2], )
                    if bookResults[2]: validationResults = ( validationResults[0], validationResults[1], validationResults[2] + bookResults[2], )
        elif controlDict["osisFiles"]=="byBible": # write all the books into a single file
            if Globals.verbosityLevel>1: print( _("Exporting to OSIS XML format...") )
            xw = XMLWriter().setOutputFilePath( controlDict["osisOutputFilename"], outputFolder )
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
            if validationSchema: validationResults = xw.validateXML( validationSchema )
        elif Globals.LogErrorsFlag: logging.critical( "Unrecognized toOSIS control \"osisFiles\" = '{}'".format( controlDict["osisFiles"] ) )
        if unhandledMarkers and Globals.verbosityLevel>0: print( "  " + _("WARNING: Unhandled toOSIS USFM markers were {}").format(unhandledMarkers) )
        if Globals.verbosityLevel > 2: print( "Need to find and look at an example where a new chapter isn't a new <p> to see how chapter eIDs should be handled there" )
        if validationSchema: return validationResults
    # end of BibleWriter.toOSIS_XML


    def toSwordModule( self, controlDict, validationSchema=None ):
        """
        Using settings from the given control file,
            converts the USFM information to a UTF-8 OSIS-XML-based Sword module.
        """
        assert( controlDict and isinstance( controlDict, dict ) )

        import struct
        assert( struct.calcsize("IH") == 6 ) # Six-byte format

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

        outputFolder = "OutputFiles"
        if not os.access( outputFolder, os.F_OK ): os.mkdir( outputFolder ) # Make the empty folder if there wasn't already one there

        # Let's write a Sword locale while we're at it
        self.writeSwordLocale( controlDict["xmlLanguage"], controlDict["LanguageName"], BOS, getBookNameFunction, os.path.join( outputFolder, "SwLocale-utf8.conf" ) )
        #SwLocFilepath = os.path.join( outputFolder, "SwLocale-utf8.conf" )
        #if Globals.verbosityLevel>1: print( _("Writing Sword locale file {}...").format(SwLocFilepath) )
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
                    assert( count1 == count2 )
                    return helpText
                # end of checkTextHelper

                adjText = textToCheck
                if '<<' in adjText or '>>' in adjText:
                    if Globals.LogErrorsFlag: logging.warning( _("toSword: Unexpected double angle brackets in {}: '{}' field is '{}'").format(toOSISGlobals["verseRef"],marker,textToCheck) )
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
                    if Globals.LogErrorsFlag: logging.error( _("toSword: We still have some unprocessed backslashes for Sword in {}: '{}' field is '{}'").format(toSwordGlobals["verseRef"],marker,textToCheck) )
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
                            if rest != '-': logging.warning( _("toSword: We got something else here other than hyphen (probably need to do something with it): {} '{}' from '{}'").format(chapterRef, token, text) )
                        elif token.startswith('xo '): # xref reference follows
                            adjToken = token[3:].strip()
                            if adjToken.endswith(' a'): adjToken = adjToken[:-2] # Remove any 'a' suffix (occurs when a cross-reference has multiple (a and b) parts
                            if adjToken.endswith(':'): adjToken = adjToken[:-1] # Remove any final colon (this is a language dependent hack)
                            adjToken = getBookAbbreviationFunction(BBB) + ' ' + adjToken # Prepend the vernacular book abbreviation
                            osisRef = BRL.parseToOSIS( adjToken )
                            if osisRef is not None:
                                OSISxref += '<reference type="source" osisRef="{}">{}</reference>'.format(osisRef,token[3:])
                                if Globals.LogErrorsFlag and not BRL.containsReference( BBB, currentChapterNumberString, verseNumberString ):
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
                            if rest != '-' and Globals.LogErrorsFlag: logging.warning( _("toSword: We got something else here other than hyphen (probably need to do something with it): {} '{}' from '{}'").format(chapterRef, token, text) )
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
                                if Globals.LogErrorsFlag and not BRL.containsReference( BBB, currentChapterNumberString, verseNumberString ):
                                    logging.error( _("toSword: Footnote at {} {}:{} seems to contain the wrong self-reference '{}'").format(BBB,currentChapterNumberString,verseNumberString, token) )
                        elif token.startswith('ft '): # footnote text follows
                            OSISfootnote += token[3:]
                        elif token.startswith('fq ') or token.startswith('fqa '): # footnote quote follows -- NOTE: We also assume here that the next marker closes the fq field
                            OSISfootnote += '<catchWord>{}</catchWord>'.format(token[3:]) # Note that the trailing space goes in the catchword here -- seems messy
                        elif token in ('ft*','ft* ','fq*','fq* ','fqa*','fqa* '):
                            pass # We're being lazy here and not checking closing markers properly
                        elif Globals.LogErrorsFlag:
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
                if haveOpenVsID != False: # Close the previous verse
                    writerObject.writeLineOpenSelfclose( 'verse', ('eID',haveOpenVsID) )
                #verseNumberString = text.split()[0] # Get the first token which is the first number
                #verseText = text[len(verseNumberString)+1:].lstrip() # Get the rest of the string which is the verse text
                if '-' in verseNumberString:
                    bits = verseNumberString.split('-')
                    if len(bits)!=2 or not bits[0].isdigit() or not bits[1].isdigit(): logging.critical( _("toSword: Doesn't handle verse number of form '{}' yet for {}").format(verseNumberString,chapterRef) )
                    toSwordGlobals["verseRef"]  = chapterRef + '.' + bits[0]
                    verseRef2 = chapterRef + '.' + bits[1]
                    sID    = toSwordGlobals["verseRef"] + '-' + verseRef2
                    osisID = toSwordGlobals["verseRef"] + ' ' + verseRef2
                elif ',' in verseNumberString:
                    bits = verseNumberString.split(',')
                    if len(bits)<2 or not bits[0].isdigit() or not bits[1].isdigit(): logging.critical( _("toSword: Doesn't handle verse number of form '{}' yet for {}").format(verseNumberString,chapterRef) )
                    sID = toSwordGlobals["verseRef"] = chapterRef + '.' + bits[0]
                    osisID = ''
                    for bit in bits: # Separate the OSIS ids by spaces
                        osisID += ' ' if osisID else ''
                        osisID += chapterRef + '.' + bit
                    #print( "Hey comma verses '{}' '{}'".format( sID, osisID ) )
                elif verseNumberString.isdigit():
                    sID = osisID = toSwordGlobals["verseRef"] = chapterRef + '.' + verseNumberString
                elif Globals.LogErrorsFlag: logging.critical( _("toSword: Doesn't handle verse number of form '{}' yet for {}").format(verseNumberString,chapterRef) )
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
                    elif Globals.LogErrorsFlag: logging.error( _("toSword: {} Have a blank {} field—ignoring it").format( toSwordGlobals["verseRef"], marker ) )
                    haveOpenIntro = True
                    chapterRef = bookRef + '.0' # Not used by OSIS
                    toSwordGlobals["verseRef"] = chapterRef + '.0' # Not used by OSIS
                elif marker=='ip':
                    if not haveOpenIntro: # Shouldn't happen but we'll try our best
                        if Globals.LogErrorsFlag: logging.error( "toSword: {} Have an ip not in an introduction section—opening an intro section".format( toSwordGlobals["verseRef"] ) )
                        writerObject.writeLineOpen( 'div', ('type',"introduction") )
                        haveOpenIntro = True
                    closeAnyOpenParagraph()
                    writerObject.writeLineOpenSelfclose( 'div', [getSID(), ('type',"paragraph")] )
                    writerObject.writeLineText( checkText(text), noTextCheck=True ) # Sometimes there's text
                    haveOpenParagraph = True
                elif marker=='iot':
                    if not haveOpenIntro: # Shouldn't happen but we'll try our best
                        if Globals.LogErrorsFlag: logging.error( "toSword: {} Have a iot not in an introduction section—opening an intro section".format( toSwordGlobals["verseRef"] ) )
                        writerObject.writeLineOpen( 'div', ('type',"introduction") )
                        haveOpenIntro = True
                    if haveOpenOutline:
                        writerObject.writeLineClose( 'list' )
                        writerObject.writeLineOpenSelfclose( 'div', [('eID',toSwordGlobals['idStack'].pop()), ('type',"outline")] )
                        haveOpenOutline = False
                    if haveOpenSection: raise Exception( "Not handled yet iot" )
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
                        if Globals.LogErrorsFlag: logging.error( "toSword: {} Have an io1 not in an introduction section—opening an intro section".format( toSwordGlobals["verseRef"] ) )
                        writerObject.writeLineOpen( 'div', ('type',"introduction") )
                        haveOpenIntro = True
                    if not haveOpenOutline: # Shouldn't happen but we'll try our best
                        if Globals.LogErrorsFlag: logging.warning( _("toSword: {} Have an io1 not in an outline section—opening an outline section".format(toSwordGlobals["verseRef"]) ) )
                        closeAnyOpenParagraph()
                        writerObject.writeLineOpenSelfclose( 'div', [getSID(), ('type',"outline")] )
                        writerObject.writeLineOpen( 'list' )
                        haveOpenOutline = True
                    if text: writerObject.writeLineOpenClose( 'item', checkText(text) )
                elif marker=='io2':
                    if not haveOpenIntro: raise Exception( "toSword: Have an io2 not in an introduction section" )
                    if not haveOpenOutline: raise Exception( "toSword: Have an io2 not in an outline section" )
                    writerObject.writeLineOpenClose( 'item', checkText(text) ) # TODO: Shouldn't this be different from an io1???
                elif marker=='c':
                    if haveOpenOutline:
                        if text!='1' and not text.startswith('1 ') and Globals.LogErrorsFlag: logging.error( _("toSword: {} This should normally be chapter 1 to close the introduction (got '{}')").format( toSwordGlobals["verseRef"], text ) )
                        writerObject.writeLineClose( 'list' )
                        writerObject.writeLineOpenSelfclose( 'div', [('eID',toSwordGlobals['idStack'].pop()), ('type',"outline")] )
                        haveOpenOutline = False
                    if haveOpenIntro:
                        if text!='1' and not text.startswith('1 ') and Globals.LogErrorsFlag: logging.error( _("toSword: {} This should normally be chapter 1 to close the introduction (got '{}')").format( toSwordGlobals["verseRef"], text ) )
                        closeAnyOpenParagraph()
                        writerObject.writeLineOpenSelfclose( 'div', [('eID',toSwordGlobals['idStack'].pop()), ('type',"introduction")] )
                        haveOpenIntro = False
                    closeAnyOpenLG()
                    if needChapterEID:
                        writerObject.writeLineOpenSelfclose( 'chapter', ('eID',chapterRef) ) # This is an end milestone marker
                    writeIndexEntry( writerObject, ix )
                    currentChapterNumberString, verseNumberString = text, '0'
                    if not currentChapterNumberString.isdigit(): logging.critical( _("toSword: Can't handle non-digit '{}' chapter number yet").format(text) )
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
                    elif Globals.LogErrorsFlag: logging.info( _("toSword: Blank ms1 section heading encountered after {}").format( toSwordGlobals["verseRef"] ) )
                elif marker=='s1':
                    if haveOpenParagraph:
                        closeAnyOpenLG()
                        closeAnyOpenParagraph()
                    closeAnyOpenSubsection()
                    closeAnyOpenSection()
                    writerObject.writeLineOpen( 'div', [getSID(), ('type',"section")] )
                    haveOpenSection = True
                    if text: writerObject.writeLineOpenClose( 'title', checkText(text) ) # Section heading
                    elif Globals.LogErrorsFlag: logging.info( _("toSword: Blank s1 section heading encountered after {}:{}").format( currentChapterNumberString, verseNumberString ) )
                elif marker=='s2':
                    if haveOpenParagraph:
                        closeAnyOpenLG()
                        closeAnyOpenParagraph()
                    closeAnyOpenSubsection()
                    writerObject.writeLineOpen( 'div', ('type', "subSection") )
                    haveOpenSubsection = True
                    if text: writerObject.writeLineOpenClose( 'title', checkText(text) ) # Section heading
                    elif Globals.LogErrorsFlag: logging.info( _("toSword: Blank s2 section heading encountered after {}:{}").format( currentChapterNumberString, verseNumberString ) )
                elif marker=='mr':
                    # Should only follow a ms1 I think
                    if haveOpenParagraph or haveOpenSection or not haveOpenMajorSection: logging.error( _("toSword: Didn't expect major reference 'mr' marker after {}").format(toSwordGlobals["verseRef"]) )
                    writerObject.writeLineOpenClose( 'title', checkText(text), ('type',"parallel") ) # Section reference
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
                    #    assert( BBB in Globals.BibleBooksCodes.getSingleChapterBooksList() )
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
            if haveOpenIntro or haveOpenOutline or haveOpenLG or haveOpenL or unprocessedMarker:
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
        if Globals.verbosityLevel>1: print( _("Exporting to Sword modified-OSIS XML format...") )
        xwOT = XMLWriter().setOutputFilePath( 'ot', lgFolder )
        xwNT = XMLWriter().setOutputFilePath( 'nt', lgFolder )
        xwOT.setHumanReadable( 'NLSpace', indentSize=5 ) # Can be set to 'All', 'Header', or 'None'
        xwNT.setHumanReadable( 'NLSpace', indentSize=5 ) # Can be set to 'All', 'Header', or 'None'
        xwOT.start( noAutoXML=True ); xwNT.start( noAutoXML=True )
        toSwordGlobals['length'] = xwOT.writeLineOpenSelfclose( 'milestone', [('type',"x-importer"), ('subtype',"x-USFMBible.py"), ('n',"${} $".format(versionString))] )
        toSwordGlobals['length'] = xwNT.writeLineOpenSelfclose( 'milestone', [('type',"x-importer"), ('subtype',"x-USFMBible.py"), ('n',"${} $".format(versionString))] )
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
                    if Globals.LogErrorsFlag: logging.critical( _("toSword: Sword module writer doesn't know how to encode {} book or appendix").format(BBB) )
                    continue
                writeBook( xw, ix, BBB, bookData )
        xwOT.close(); xwNT.close()
        if unhandledMarkers and Globals.verbosityLevel>0: print( "  " + _("WARNING: Unhandled toSwordModule USFM markers were {}").format(unhandledMarkers) )
        if validationSchema:
            OTresults= xwOT.validateXML( validationSchema )
            NTresults= xwNT.validateXML( validationSchema )
            return OTresults, NTresults
    #end of BibleWriter.toSwordModule
# end of class BibleWriter


def demo():
    """
    Demonstrate reading and processing some Bible databases.
    """
    # Configure basic logging
    logging.basicConfig( format='%(levelname)s: %(message)s', level=logging.INFO ) # Removes the unnecessary and unhelpful 'root:' part of the logged messages

    # Handle command line parameters
    from optparse import OptionParser
    parser = OptionParser( version="v{}".format( versionString ) )
    parser.add_option("-e", "--export", action="store_true", dest="export", default=False, help="export the XML file to .py and .h tables suitable for directly including into other programs")
    Globals.addStandardOptionsAndProcess( parser )

    if Globals.verbosityLevel > 0: print( "{} V{}".format( progName, versionString ) )

    # Since this is only designed to be a base class, it can't actually do much at all
    BW = BibleWriter()
    BW.objectNameString = "Dummy test Bible Writer object"
    #BW.sourceFolder = "Nowhere"
    if Globals.verbosityLevel > 0: print( BW )

    if 0:
        from USFMBible import USFMBible

        usxSchemaFile = "/mnt/Data/Work/Bibles/Formats/USX/usx 1.rng"
        OSISSchemaFile = "/mnt/Data/Work/Bibles/Formats/OSIS/osisCore.2.1.1.xsd"
        validateXML = False

        if 1: # Do one test folder
            name, encoding, testFolder = "Matigsalug", "utf-8", "/mnt/Data/Work/Matigsalug/Bible/MBTV/" # You can put your test folder here
            #name, encoding, testFolder = "MS-BT", "utf-8", "/mnt/Data/Work/Matigsalug/Bible/MBTBT/" # You can put your test folder here
            #name, encoding, testFolder = "MS-Notes", "utf-8", "/mnt/Data/Work/Matigsalug/Bible/MBTBC/" # You can put your test folder here
            #name, encoding, testFolder = "WEB", "utf-8", "/mnt/Data/Work/Bibles/English translations/WEB (World English Bible)/2012-06-23 eng-web_usfm/" # You can put your test folder here

            if os.access( testFolder, os.R_OK ): # check that we can read the test data
                UB = USFMBible( testFolder, name, encoding, wantLoadErrorMessages ) # create the BibleWriter object
                UB.loadAll()
                print( UB )
                if not Globals.commandLineOptions.export: UB.check()
                UBErrors = UB.getErrors()
                #print( UBWErrors )

                if Globals.commandLineOptions.export:
                    UB.setupWriter()
                    #BW.genericBOS = BibleOrganizationalSystem( "GENERIC-KJV-81" )
                    #BW.genericBRL = BibleReferenceList( BW.genericBOS, BibleObject=BW )
                    import subprocess # for running xmllint
                    import ControlFiles
                    if Globals.verbosityLevel > 0: print( "NOTE: This is {} V{} -- i.e., not even alpha quality software!".format( progName, versionString ) )
                    #xmllintError = ("No error", "Unclassified", "Error in DTD", "Validation error", "Validation error", "Error in schema compilation", "Error writing output", "Error in pattern", "Error in reader registration", "Out of memory")

                    if 1: # Do USX XML export
                        USXControls = {}; ControlFiles.readControlFile( 'ControlFiles', "To_USX_controls.txt", USXControls )
                        validationResults = UB.toUSX_XML( USXControls, validationSchema=usxSchemaFile if validateXML else None )
                        if Globals.verbosityLevel>0 and validationResults and validationResults[0]: # print validation results
                            if validationResults[1]: print( "\nUSFX checkProgramOutputString\n{}".format( validationResults[1] ) )
                            if validationResults[2]: print( "\n USFX checkProgramErrorOutputString\n{}".format( validationResults[2] ) )
                        # Remove any empty files
                        USXOutputFolder = os.path.join( "OutputFiles/", "USX output/" )
                        for filename in os.listdir( USXOutputFolder ):
                            filepath = os.path.join( USXOutputFolder, filename )
                            if os.stat(filepath).st_size == 0:
                                print( "Removing empty file: {}".format( filepath ) )
                                os.remove( filepath ) # delete the zero-length file

                    if 1: # Do OSIS XML export
                        OSISControls = {}; ControlFiles.readControlFile( 'ControlFiles', "To_OSIS_controls.txt", OSISControls )
                        for control in OSISControls:
                            OSISControls[control] = OSISControls[control].replace('__PROJECT_NAME__','UBW-Test') #.replace('byBible','byBook')
                        #print( OSISControls ); halt
                        validationResults = UB.toOSIS_XML( OSISControls, validationSchema=OSISSchemaFile if validateXML else None )
                        if Globals.verbosityLevel>0 and validationResults and validationResults[0]: # print validation results
                            if validationResults[1]: print( "\nUSFX checkProgramOutputString\n{}".format( validationResults[1] ) )
                            if validationResults[2]: print( "\n USFX checkProgramErrorOutputString\n{}".format( validationResults[2] ) )
                        # Remove any empty files
                        OSISOutputFolder = os.path.join( "OutputFiles/" )
                        for filename in os.listdir( OSISOutputFolder ):
                            filepath = os.path.join( OSISOutputFolder, filename )
                            if os.stat(filepath).st_size == 0:
                                print( "Removing empty file: {}".format( filepath ) )
                                os.remove( filepath ) # delete the zero-length file

                    if 1: # Do Zefania XML export
                        ZefaniaControls = {}; ControlFiles.readControlFile( 'ControlFiles', "To_Zefania_controls.txt", ZefaniaControls )
                        BW.toZefania_XML( ZefaniaControls )

                    if 1: # Do MediaWiki export
                        MediaWikiControls = {}; ControlFiles.readControlFile( 'ControlFiles', "To_MediaWiki_controls.txt", MediaWikiControls )
                        BW.toMediaWiki( MediaWikiControls )

                    if 1: # Do Sword export
                        SwordControls = {}; ControlFiles.readControlFile( 'ControlFiles', "To_OSIS_controls.txt", SwordControls )
                        BW.toSwordModule( SwordControls ) # We use the same OSIS controls (except for the output filename)
            else: print( "Sorry, test folder '{}' doesn't exist on this computer.".format( testFolder ) )

        if 0: # Test a whole folder full of folders of USFM Bibles
            def findInfo():
                """ Find out info about the project from the included copyright.htm file """
                with open( os.path.join( somepath, "copyright.htm" ) ) as myFile: # Automatically closes the file when done
                    lastLine, lineCount = None, 0
                    title, nameDict = None, {}
                    for line in myFile:
                        lineCount += 1
                        if lineCount==1 and line and line[0]==chr(65279): #U+FEFF
                            #print( "      Detected UTF-16 Byte Order Marker in copyright.htm file" )
                            line = line[1:] # Remove the UTF-8 Byte Order Marker
                        if line[-1]=='\n': line = line[:-1] # Removing trailing newline character
                        if not line: continue # Just discard blank lines
                        lastLine = line
                        if line.startswith("<title>"): title = line.replace("<title>","").replace("</title>","").strip()
                        if line.startswith('<option value="'):
                            adjLine = line.replace('<option value="','').replace('</option>','')
                            USFM_BBB, name = adjLine[:3], adjLine[11:]
                            BBB = Globals.BibleBooksCodes.getBBBFromUSFM( USFM_BBB )
                            #print( USFM_BBB, BBB, name )
                            nameDict[BBB] = name
                return title, nameDict
            # end of findInfo

            testBaseFolder = "../../Haiola USFM test versions/"
            count = totalBooks = 0
            for something in sorted( os.listdir( testBaseFolder ) ):
                somepath = os.path.join( testBaseFolder, something )
                if os.path.isfile( somepath ): print( "Ignoring file '{}' in '{}'".format( something, testBaseFolder ) )
                elif os.path.isdir( somepath ): # Let's assume that it's a folder containing a USFM (partial) Bible
                    #if not something.startswith( 'hui' ): continue # This line is used for debugging only specific modules
                    count += 1
                    title, bookNameDict = findInfo()
                    if title is None: title = something[:-5] if something.endswith("_usfm") else something
                    name, encoding, testFolder = title, "utf-8", somepath
                    if os.access( testFolder, os.R_OK ):
                        if Globals.verbosityLevel > 0: print( "\n{}".format( count ) )
                        BW = BibleWriter( testFolder, name, encoding, wantLoadErrorMessages ) # create the BibleWriter object
                        BW.loadAll()
                        print( BW )
                        if not Globals.commandLineOptions.export: BW.check()
                        BWErrors = BW.getErrors()
                        #print( UBWErrors )

                        if Globals.commandLineOptions.export:
                            import subprocess # for running xmllint
                            import ControlFiles
                            if Globals.verbosityLevel > 0: print( "NOTE: This is {} V{} -- i.e., not even alpha quality software!".format( progName, versionString ) )
                            #xmllintError = ("No error", "Unclassified", "Error in DTD", "Validation error", "Validation error", "Error in schema compilation", "Error writing output", "Error in pattern", "Error in reader registration", "Out of memory")

                            if 1: # Do USX XML export
                                USXControls = {}; ControlFiles.readControlFile( 'ControlFiles', "To_USX_controls.txt", USXControls )
                                validationResults = BW.toUSX_XML( USXControls, validationSchema=usxSchemaFile if validateXML else None )
                                if Globals.verbosityLevel>0 and validationResults and validationResults[0]: # print validation results
                                    if validationResults[1]: print( "\nUSFX checkProgramOutputString\n{}".format( validationResults[1] ) )
                                    if validationResults[2]: print( "\n USFX checkProgramErrorOutputString\n{}".format( validationResults[2] ) )
                                # Remove any empty files
                                USXOutputFolder = os.path.join( "OutputFiles/", "USX output/" )
                                for filename in os.listdir( USXOutputFolder ):
                                    filepath = os.path.join( USXOutputFolder, filename )
                                    if os.stat(filepath).st_size == 0:
                                        print( "Removing empty file: {}".format( filepath ) )
                                        os.remove( filepath ) # delete the zero-length file

                            if 1: # Do OSIS XML export
                                OSISControls = {}; ControlFiles.readControlFile( 'ControlFiles', "To_OSIS_controls.txt", OSISControls )
                                for control in OSISControls:
                                    OSISControls[control] = OSISControls[control].replace('__PROJECT_NAME__','UBW-Test') #.replace('byBible','byBook')
                                #print( OSISControls ); halt
                                validationResults = BW.toOSIS_XML( OSISControls, validationSchema=OSISSchemaFile if validateXML else None )
                                if Globals.verbosityLevel>0 and validationResults and validationResults[0]: # print validation results
                                    if validationResults[1]: print( "\nUSFX checkProgramOutputString\n{}".format( validationResults[1] ) )
                                    if validationResults[2]: print( "\n USFX checkProgramErrorOutputString\n{}".format( validationResults[2] ) )
                                # Remove any empty files
                                OSISOutputFolder = os.path.join( "OutputFiles/" )
                                for filename in os.listdir( OSISOutputFolder ):
                                    filepath = os.path.join( OSISOutputFolder, filename )
                                    if os.stat(filepath).st_size == 0:
                                        print( "Removing empty file: {}".format( filepath ) )
                                        os.remove( filepath ) # delete the zero-length file

                            if 1: # Do Zefania XML export
                                ZefaniaControls = {}; ControlFiles.readControlFile( 'ControlFiles', "To_Zefania_controls.txt", ZefaniaControls )
                                BW.toZefania_XML( ZefaniaControls )

                            if 1: # Do MediaWiki export
                                MediaWikiControls = {}; ControlFiles.readControlFile( 'ControlFiles', "To_MediaWiki_controls.txt", MediaWikiControls )
                                BW.toMediaWiki( MediaWikiControls )

                            if 1: # Do Sword export
                                SwordControls = {}; ControlFiles.readControlFile( 'ControlFiles', "To_OSIS_controls.txt", SwordControls )
                                BW.toSwordModule( SwordControls ) # We use the same OSIS controls (except for the output filename)
                    else: print( "Sorry, test folder '{}' is not readable on this computer.".format( testFolder ) )
            if count: print( "\n{} total USFM (partial) Bibles processed.".format( count ) )
            if totalBooks: print( "{} total books ({} average per folder)".format( totalBooks, round(totalBooks/count) ) )
# end of demo

if __name__ == '__main__':
    demo()
# end of BibleWriter.py