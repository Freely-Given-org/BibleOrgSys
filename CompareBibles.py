#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# CompareBibles.py
#
# Module handling a internal Bible object
#
# Copyright (C) 2016 Robert Hunt
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
Module handling an internal Bible object.

A class which extends BibleWriter (which itself extends InternalBible).
"""

from gettext import gettext as _

LastModifiedDate = '2016-05-25' # by RJH
ShortProgName = "CompareBibles"
ProgName = "Bible compare analyzer"
ProgVersion = '0.02'
ProgNameVersion = '{} v{}'.format( ShortProgName, ProgVersion )
ProgNameVersionDate = '{} {} {}'.format( ProgNameVersion, _("last modified"), LastModifiedDate )

debuggingThisModule = True


import os.path, logging
import unicodedata
import multiprocessing
from collections import OrderedDict

import BibleOrgSysGlobals
from Bible import Bible



MAX_MISMATCHED_MARKERS = 3
DEFAULT_COMPARE_QUOTES =  '“”‘’«»‹›"¿¡' # Doesn't include apostrophe
DEFAULT_COMPARE_PUNCTUATION = '.,:;—?!–{}<>&%$#@=' # Doesn't include () and [], so these can vary
DEFAULT_COMPARE_DIGITS = '0123456789'
DEFAULT_ILLEGAL_STRINGS_COMMON = ( '  ','"',"''", "‘‘","’’", '<','=','>', ' -','- ','--',
                                  ' –','– ',' —','— ', # en-dash and em-dash
                                  '*,','*.','*?','*!', 'XXX','ALT','NEW', )
DEFAULT_ILLEGAL_STRINGS_1 = ( "'", '/', ) + DEFAULT_ILLEGAL_STRINGS_COMMON
DEFAULT_ILLEGAL_STRINGS_2 = (  ) + DEFAULT_ILLEGAL_STRINGS_COMMON



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



def bookComparePedantic( book1, book2,
                        compareQuotes=DEFAULT_COMPARE_QUOTES,
                        comparePunctuation=DEFAULT_COMPARE_PUNCTUATION,
                        compareDigits=DEFAULT_COMPARE_DIGITS,
                        illegalStrings1=DEFAULT_ILLEGAL_STRINGS_1, # Case sensitive
                        illegalStrings2=DEFAULT_ILLEGAL_STRINGS_2, # Case sensitive
                        breakOnOne=False ):
    """
    Given two Bible book objects, compare the two carefully
        and return differences.

    This is typically used to compare a translation and a matching back-translation.

    The returned list is sorted by C:V
    Each list entry is a 2-tuple, being BCV and error message.
    """
    if BibleOrgSysGlobals.debugFlag:
        if debuggingThisModule:
            print( exp("bookComparePedantic( {}, {}, {!r}, {!r}, {}, {}, {}, {} )") \
                    .format( book1, book2, compareQuotes, comparePunctuation, compareDigits,
                                        illegalStrings1, illegalStrings2, breakOnOne ) )
        assert( book1.BBB == book2.BBB )
        assert( book1.workName != book2.workName )

    bcResults = []
    len1, len2 = len(book1), len(book2)
    #print( 'len', len1, len2 )
    ix1 = ix2 = 0
    numMismatchedMarkers = 0
    C = V = '0'
    while ix1<len1 and ix2<len2:
        entry1, entry2 = book1._processedLines[ix1], book2._processedLines[ix2] # InternalBibleEntry objects
        ix1 += 1; ix2 += 1
        #print( 'entry', entry1, entry2 )
        marker1, line1 = entry1.getMarker(), entry1.getOriginalText()
        marker2, line2 = entry2.getMarker(), entry2.getOriginalText()

        if marker1 == 'c': C, V = line1.split()[0], '0'
        elif marker1 == 'v':
            if C == '0': C = '1' # Some one chapter books might not have a C marker
            V = line1.split()[0]
        elif C == '0': V = str( int(V) + 1 )
        #print( '{} {}:{} {}/{}={}/{}'.format( book1.BBB, C, V, marker1, marker2, line1, line2 ) )
        #print( ' ', entry1.getOriginalText() )
        #print( ' ', entry1.getAdjustedText() )
        #print( ' ', entry1.getCleanText() )

        if marker1 == marker2:
            numMismatchedMarkers = 0
            if not line1 and not line2: continue
            for quoteChar in compareQuotes:
                c1, c2 = line1.count( quoteChar ), line2.count( quoteChar )
                if c1 != c2:
                    try: quoteName = unicodedata.name( quoteChar )
                    except ValueError: quoteName = quoteChar
                    bcResults.append( ((C,V),"Mismatched {} quote: {} vs {}".format( quoteName, c1, c2 )) )
                    if breakOnOne: break
            for punctChar in comparePunctuation:
                c1, c2 = line1.count( punctChar ), line2.count( punctChar )
                if c1 != c2:
                    try: punctName = unicodedata.name( punctChar )
                    except ValueError: punctName = punctChar
                    bcResults.append( ((C,V),"Mismatched {} punctuation: {} vs {}".format( punctName, c1, c2 )) )
                    if breakOnOne: break
            for digit in compareDigits:
                c1, c2 = line1.count( digit ), line2.count( digit )
                if c1 != c2:
                    bcResults.append( ((C,V),"Mismatched {} digit: {} vs {}".format( digit, c1, c2 )) )
                    if breakOnOne: break
            if marker1 not in ( 'id','ide','rem', ): # Don't do illegal strings in these non-Bible-text fields
                extras = entry1.getExtras()
                if extras is None: extras = () # So it's always iterable
                for iString in illegalStrings1:
                    if iString in entry1.getCleanText(): # So markers don't confuse things
                        bcResults.append( ((C,V),"Illegal {!r} string in Bible1".format( iString )) )
                    for extra in extras:
                        #print( extra )
                        #print( ' ', extra.getType() )
                        #print( ' ', extra.getIndex() )
                        #print( ' ', extra.getText() )
                        #print( ' ', extra.getCleanText() )
                        if iString in extra.getCleanText(): # So markers don't confuse things
                            bcResults.append( ((C,V),"Illegal {!r} string in Bible1".format( iString )) )
                extras = entry2.getExtras()
                if extras is None: extras = () # So it's always iterable
                for iString in illegalStrings2:
                    if iString in entry2.getCleanText(): # So markers don't confuse things
                        bcResults.append( ((C,V),"Illegal {!r} string in Bible2".format( iString )) )
                    for extra in extras:
                        #print( extra )
                        #print( ' ', extra.getType() )
                        #print( ' ', extra.getIndex() )
                        #print( ' ', extra.getText() )
                        #print( ' ', extra.getCleanText() )
                        if iString in extra.getCleanText(): # So markers don't confuse things
                            bcResults.append( ((C,V),"Illegal {!r} string in Bible1".format( iString )) )
        else: # markers are different
            numMismatchedMarkers += 1
            if numMismatchedMarkers < MAX_MISMATCHED_MARKERS:
                bcResults.append( ((C,V),"Mismatched markers: {!r} vs {!r}".format( marker1, marker2 )) )
            else: break # things are too bad -- not worth continuing

    return bcResults
# end of bookComparePedantic


def _doCompare( parameters ):
    BBB, Bible1, Bible2 = parameters
    return bookComparePedantic( Bible1[BBB], Bible2[BBB] )


def CompareBibles( Bible1, Bible2,
                        compareQuotes=DEFAULT_COMPARE_QUOTES,
                        comparePunctuation=DEFAULT_COMPARE_PUNCTUATION,
                        compareDigits=DEFAULT_COMPARE_DIGITS,
                        illegalStrings1=DEFAULT_ILLEGAL_STRINGS_1, # Case sensitive
                        illegalStrings2=DEFAULT_ILLEGAL_STRINGS_2, # Case sensitive
                        breakOnOne=False ):
    """
    Runs a series of checks and count on each book of the Bible
        in order to try to determine what are the normal standards.
    """
    if BibleOrgSysGlobals.debugFlag:
        if debuggingThisModule: print( exp("CompareBibles( {}, {} )").format( Bible1, Bible2 ) )
        assert( isinstance( Bible1, Bible ) )
        assert( isinstance( Bible2, Bible ) )
        assert( Bible1.abbreviation != Bible2.abbreviation or Bible1.name != Bible2.name )
    if BibleOrgSysGlobals.verbosityLevel > 0: print( _("Running CompareBibles…") )

    len1, len2 = len(Bible1), len(Bible2)
    #numBooks = min( len1, len2 )
    commonBooks = []
    for bBook in Bible1:
        if bBook.BBB in Bible2: commonBooks.append( bBook.BBB )
    numBooks = len( commonBooks )

    if BibleOrgSysGlobals.verbosityLevel > 2: print( exp("Running bookComparePedantic on both Bibles…") )
    bResults = OrderedDict()
    # TODO: Work out why multiprocessing is slower here -- yes, coz it has to pickle and unpickle entire Bible books
    if 0 and BibleOrgSysGlobals.maxProcesses > 1: # Check all the books as quickly as possible
        if BibleOrgSysGlobals.verbosityLevel > 1:
            print( exp("Comparing {} books using {} CPUs…").format( numBooks, BibleOrgSysGlobals.maxProcesses ) )
            print( "  NOTE: Outputs (including error and warning messages) from scanning various books may be interspersed." )
        with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
            results = pool.map( _doCompare, [(BBB,Bible1,Bible2) for BBB in commonBooks] ) # have the pool do our loads
            assert len(results) == numBooks
            for j,BBB in enumerate( commonBooks ):
                bResults[BBB] = results[j] # Saves them in the correct order
    else: # Just single threaded
        for BBB in commonBooks: # Do individual book prechecks
            if BibleOrgSysGlobals.verbosityLevel > 3: print( "  " + exp("Comparing {}…").format( BBB ) )
            bResults[BBB] = bookComparePedantic( Bible1[BBB], Bible2[BBB], compareQuotes=compareQuotes,
                                                comparePunctuation=comparePunctuation, compareDigits=compareDigits,
                                                illegalStrings1=illegalStrings1, illegalStrings2=illegalStrings2,
                                                breakOnOne=breakOnOne )
    return bResults
# end of CompareBibles



def demo():
    """
    Demonstration program to handle command line parameters and then run what they want.
    """
    from USFMBible import USFMBible
    if BibleOrgSysGlobals.verbosityLevel > 0: print( "{} Demo".format( ProgNameVersion ) )

    # Load a USFM Bible and BT
    if BibleOrgSysGlobals.verbosityLevel > 0: print( "\nLoading USFM Bible…" )
    name1, encoding1, testFolder1 = "MBTV", 'utf-8', "../../../../../Data/Work/Matigsalug/Bible/MBTV/" # You can put your test folder here
    name2, encoding2, testFolder2 = "MS-BT", 'utf-8', "../../../../../Data/Work/Matigsalug/Bible/MBTBT/" # You can put your test folder here
    MS_ILLEGAL_STRINGS_1 = ( 'c','f','j','o','q','v','x','z', ) + DEFAULT_ILLEGAL_STRINGS_1
    MS_ILLEGAL_STRINGS_2 = ( 'We ',' we ',' us ',' us.',' us,',' us:',' us;',' us!',' us?',
                             'Our ',' our ','You ','you ','you.','you,','you:','you;','you!','you?',
                             'Your ','your ','yours ',' the the ', ) + DEFAULT_ILLEGAL_STRINGS_2

    if os.access( testFolder1, os.R_OK ):
        UB1 = USFMBible( testFolder1, name1, encoding1 )
        UB1.load()
        if BibleOrgSysGlobals.verbosityLevel > 0: print( UB1 )
        if BibleOrgSysGlobals.strictCheckingFlag:
            UB1.check()
        #UB1.doAllExports( "OutputFiles", wantPhotoBible=False, wantODFs=False, wantPDFs=False )
    else: print( "Sorry, test folder {!r} is not readable on this computer.".format( testFolder1 ) )

    if os.access( testFolder2, os.R_OK ):
        UB2 = USFMBible( testFolder2, name2, encoding2 )
        UB2.load()
        if BibleOrgSysGlobals.verbosityLevel > 0: print( UB2 )
        if BibleOrgSysGlobals.strictCheckingFlag:
            UB2.check()
        #UB2.doAllExports( "OutputFiles", wantPhotoBible=False, wantODFs=False, wantPDFs=False )
    else: print( "Sorry, test folder {!r} is not readable on this computer.".format( testFolder2 ) )

    if 1: # Test one book
        if BibleOrgSysGlobals.verbosityLevel > 0: print( "\nTesting one book only…" )
        BBB = 'JDE'
        result = bookComparePedantic( UB1[BBB], UB2[BBB], illegalStrings1=MS_ILLEGAL_STRINGS_1, illegalStrings2=MS_ILLEGAL_STRINGS_2 )
        if BibleOrgSysGlobals.verbosityLevel > 0:
            print( "Comparing {} gave:".format( BBB ) )
            print( ' ', result )

    if 1: # Test the whole Bible
        if BibleOrgSysGlobals.verbosityLevel > 0: print( "\nTesting for whole Bible…" )
        results = CompareBibles( UB1, UB2, illegalStrings1=MS_ILLEGAL_STRINGS_1, illegalStrings2=MS_ILLEGAL_STRINGS_2 )
        if BibleOrgSysGlobals.verbosityLevel > 0:
            print( "\nComparing the entire Bibles gave:" )
            for BBB,bookResults in results.items():
                if bookResults:
                    print( '\n{}:'.format( BBB ) )
                    for result in bookResults:
                        C, V, resultString = result[0][0], result[0][1], result[1]
                        resultString = resultString.replace( 'Bible1', name1 ).replace( 'Bible2', name2 )
                        print( '{}:{} {}'.format( C, V, resultString ) )
            #print( results )
# end of demo


def main():
    """
    Main program to handle command line parameters and then run what they want.
    """
    from UnknownBible import UnknownBible
    if BibleOrgSysGlobals.verbosityLevel > 0: print( ProgNameVersion )
    #if BibleOrgSysGlobals.print( BibleOrgSysGlobals.commandLineArguments )

    fp1, fp2 = BibleOrgSysGlobals.commandLineArguments.Bible1, BibleOrgSysGlobals.commandLineArguments.Bible2
    allOkay = True
    if not os.path.exists( fp1 ): logging.critical( "Bible1 filepath {!r} is invalid—aborting".format( fp1 ) ); allOkay = False
    if not os.path.exists( fp2 ): logging.critical( "Bible2 filepath {!r} is invalid—aborting".format( fp2 ) ); allOkay = False

    if allOkay:
        UnkB1 = UnknownBible( fp1 )
        result1 = UnkB1.search( autoLoadAlways=True, autoLoadBooks=True )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Bible1 loaded", result1 )
        if isinstance( result1, Bible ):
            Bible1 = result1
        else:
            logging.critical( "Unable to load Bible1 from {!r}—aborting".format( fp1 ) ); allOkay = False
    if allOkay:
        UnkB2 = UnknownBible( fp2 )
        result2 = UnkB2.search( autoLoadAlways=True, autoLoadBooks=True )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Bible2 loaded", result2 )
        if isinstance( result2, Bible ):
            Bible2 = result2
        else:
            logging.critical( "Unable to load Bible2 from {!r}—aborting".format( fp2 ) ); allOkay = False

    if allOkay:
        results = CompareBibles( Bible1, Bible2 )
        if BibleOrgSysGlobals.verbosityLevel > 0:
            name1 = Bible1.abbreviation if Bible1.abbreviation else Bible1.name
            name2 = Bible2.abbreviation if Bible2.abbreviation else Bible2.name
            print( "\nComparing the entire Bibles gave:" )
            for BBB,bookResults in results.items():
                if bookResults:
                    print( '\n{}:'.format( BBB ) )
                    for result in bookResults:
                        C, V, resultString = result[0][0], result[0][1], result[1]
                        resultString = resultString.replace( 'Bible1', name1 ).replace( 'Bible2', name2 )
                        print( '{}:{} {}'.format( C, V, resultString ) )
            #print( results )
# end of main


if __name__ == '__main__':
    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    import sys
    if 'win' in sys.platform: # Convert stdout so we don't get zillions of UnicodeEncodeErrors
        from io import TextIOWrapper
        sys.stdout = TextIOWrapper( sys.stdout.detach(), sys.stdout.encoding, 'namereplace' if sys.version_info >= (3,5) else 'backslashreplace' )

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( ProgName, ProgVersion )
    parser.add_argument('Bible1', help="Bible folder or file path 1" )
    parser.add_argument('Bible2', help="Bible folder or file path 2" )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    main()

    BibleOrgSysGlobals.closedown( ProgName, ProgVersion )
# end of CompareBibles.py