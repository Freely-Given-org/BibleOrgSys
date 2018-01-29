#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# FreeBibleConvert.py
#
# Given a text export of the Free Bible New Testament, convert it to USFM2 files.
#
# Copyright (C) 2018 Robert Hunt
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
Given the MediaWiki text export of the Free Bible New Testament from LibreOffice,
    convert it to USFM2 files.
"""

from gettext import gettext as _

LastModifiedDate = '2018-01-29' # by RJH
ShortProgName = "FreeBibleConvert"
ProgName = "FreeBible Convert to USFM2"
ProgVersion = '0.05'
ProgNameVersion = '{} v{}'.format( ProgName, ProgVersion )
ProgNameVersionDate = '{} {} {}'.format( ProgNameVersion, _("last modified"), LastModifiedDate )

debuggingThisModule = False


import sys, os.path, logging
from datetime import datetime

# BibleOrgSys imports
if __name__ == '__main__': sys.path.append( '../BibleOrgSys/' )
import BibleOrgSysGlobals
from NoisyReplaceFunctions import noisyFind, noisyReplaceAll, noisyDeleteAll, noisyRegExReplaceAll


def splitAndWriteBooks( entireBibleText, folderpath ):
    """
    """
    writtenCount = 0
    splitOnString = '\\id '
    for splitText in entireBibleText.split( splitOnString ):
        # print( "here", writtenCount, repr(splitText[:40]) )
        if not splitText: continue # coz it gets a blank one right at the beginning
        assert splitText[3] == ' '
        bookID = splitText[:3]
        # print( "  Got book id", repr(bookID) )
        assert bookID in BibleOrgSysGlobals.BibleBooksCodes.getAllUSFMBooksCodes( toUpper=True )
        splitText = splitOnString + splitText
        
        # Last chance to fix things up (e.g., by bookID)
        if splitText[-1] != '\n': splitText += '\n' # Ensure that we have a final newline character in each file
        # if bookID == 'FRT':
        
        filepath = os.path.join( folderpath, 'FBV_{}.usfm'.format( bookID ) )
        if BibleOrgSysGlobals.verbosityLevel > 2:
            print( "Writing {}...".format( filepath ) )
        with open( filepath, 'wt', encoding='utf-8' ) as bookFile:
            bookFile.write( splitText )
        if BibleOrgSysGlobals.verbosityLevel > 3: 
            print( "  {} characters ({} lines) written".format( len(splitText), splitText.count('\n') ) )
        writtenCount += 1
    if BibleOrgSysGlobals.verbosityLevel > 0:
        print( "{} books written to {}".format( writtenCount, folderpath ) )
# end of splitAndWriteBooks


def main():
    """
    Main program to handle command line parameters and then run what they want.
    """
    idLine = "Free Bible Version New Testament Version 2.1.1"
    if BibleOrgSysGlobals.verbosityLevel>0: print( ProgNameVersion )

    filepath = '/Users/Robert/Desktop/FBVNT2.1.1.LOExport.txt'
    if BibleOrgSysGlobals.verbosityLevel > 0:
        print( "Loading {}...".format( filepath ) )
    with open( filepath, 'rt', encoding='utf-8' ) as textFile:
        originalText = textFile.read()
    if BibleOrgSysGlobals.verbosityLevel > 1:
        print( "  Loaded {:,} characters ({:,} lines)".format( len(originalText), originalText.count('\n') ) )

    # Preparation by inserting some lines at the beginning
    entireText = '\\id FRT -- {}\n'.format( idLine )
    entireText += '\\rem Converted by {!r}\n'.format( ProgNameVersionDate )
    entireText += '\\rem Converted from \'{}\'\n'.format( filepath )
    entireText += '\\rem Converted {}\n'.format( datetime.now() )
    entireText += originalText
    
    # More preparation
    entireText = noisyReplaceAll( entireText, '\n\r', '\n' ) # Makes it easier later
    entireText = noisyReplaceAll( entireText, '\r\n', '\n' ) # Makes it easier later
    entireText = noisyReplaceAll( entireText, '﻿', '' ) # Remove zero-width space or whatever it is
    entireText = noisyReplaceAll( entireText, '<div style="text-align:center;"></div>', '' ) # Remove blank lines at beginning
    entireText = entireText.replace( "<div style=\"text-align:center;\">'''Free Bible Version '''</div>", '\\mt1 Free Bible Version', 1 )
    entireText = entireText.replace( "<div style=\"text-align:center;\">'''New Testament'''</div>", '\\mt2 New Testament', 1 )
    entireText = noisyReplaceAll( entireText, '<div style="margin-left:0cm;margin-right:0cm;"><sup>', '<sup>' )
    
    # Fix specific mistakes and inconsistencies/irregularities
    entireText = noisyReplaceAll( entireText, '“</sup>', '</sup>“' )
    entireText = noisyReplaceAll( entireText, '<sup> <ref ', '<ref ' )
    entireText = noisyReplaceAll( entireText, '"><sup> ', '"> ' )
    entireText = noisyReplaceAll( entireText, '</sup></ref>', '</ref>' )
    entireText = noisyReplaceAll( entireText, '<sup> </sup>', ' ' )
    entireText = noisyRegExReplaceAll( entireText, '<span style="color:#0000ff;"><u>(\\S)</u></span>', '\\1' ) # Often surrounding a comma
    entireText = noisyRegExReplaceAll( entireText, '<span style="color:#0000ff;">(\\S)</span>', '\\1' ) # Often surrounding a comma
    entireText = noisyRegExReplaceAll( entireText, '<span style="color:#800080;">( )</span>', '\\1' ) # Don't need a regex for this one
    entireText = noisyRegExReplaceAll( entireText, '<nowiki>(.+?)</nowiki>', '\\1' )

    # Book divisions
    entireText = noisyRegExReplaceAll( entireText, 
        "<div style=\"text-align:center;\">'''Free Bible Version(.+?)'''</div>",
        '\n\\\\id \\1 -- Free BibleVersion\\n\\\\h \\1\\n\\\\toc1 \\1\\n\\\\mt1 \\1' )
    entireText = noisyRegExReplaceAll( entireText,
        "\n<div style=\"text-align:center;\">'''Free Bible Version'''</div>\n\n?<div style=\"text-align:center;\">'''(.+?)'''</div>",
        '\n\\\\id \\1 -- {}\\n\\\\h \\1\\n\\\\toc1 \\1\\n\\\\mt1 \\1'.format( idLine ) )

    entireText = noisyRegExReplaceAll( entireText, '<div style="text-align:center;">(.+?)</div>', '\\\\pc \\1' ) # Centred paragraphs
    
    # Chapters, verses, and footnotes
    entireText = noisyRegExReplaceAll( entireText, "\\n\\n'''(\\d{1,3})'''", '\\n\\\\c \\1\\n\\\\p' ) # Could be wrong if some chapters don't start a new paragraph
    entireText = noisyRegExReplaceAll( entireText, '<sup> ?(\\d{1,3}) ?</sup>', '\\n\\\\v \\1 ' )
    entireText = noisyRegExReplaceAll( entireText, '<ref name="ftn(\\d{1,4})"> ?', '\\\\f + \\\\fXXX ' )
    entireText = noisyRegExReplaceAll( entireText, '\\\\fXXX (\\d{1,3}:\\d{1,3}\\.) ', '\\\\fr \\1 \\\\ft ' )
    entireText = noisyRegExReplaceAll( entireText, '\\\\fXXX (\\d{1,3}\\.) ', '\\\\fr \\1 \\\\ft ' ) # For single chapter books
    entireText = noisyReplaceAll( entireText, '</ref>', '\\f*' )
    entireText = noisyReplaceAll( entireText, '\n\n\\f*', '\\f*' )
    entireText = noisyReplaceAll( entireText, '\n\\f*', '\\f*' )
    
    # Some extra paragraphs
    entireText = noisyReplaceAll( entireText, '\n\n\\v ', '\n\\p\n\\v ' )
    entireText = noisyRegExReplaceAll( entireText, '\n([^\s\\\\<])', '\n\\\\p \\1' )
    
    # Stuff at start of file
    
    # Stuff at end of file
    entireText = noisyReplaceAll( entireText, 
        '\n\\v 21 May the grace of the Lord Jesus be with the believers. Amen.\n',
        '\n\\v 21 May the grace of the Lord Jesus be with the believers. Amen.\n\\id BAK -- {}\n\\h Back matter\n\\toc1 Back matter\n'.format( idLine ) )
    entireText = noisyRegExReplaceAll( entireText, '<div style="margin-left:0cm;margin-right:0cm;">(.+?)</div>', '\\\\pm \\1' )
    entireText = noisyRegExReplaceAll( entireText, '\n<u>(.+?)</u>\n', '\n\\\\s1 \\1' )
    entireText = noisyReplaceAll( entireText, '<references/>', '' )
    
    # Check
    noisyFind( entireText, '<', logging.critical ); noisyFind( entireText, '>', logging.critical )
    noisyFind( entireText, "'''", logging.critical )
    noisyFind( entireText, 'fXXX', logging.critical )

    # Clean-up
    entireText = noisyReplaceAll( entireText, '<u>', '\\em ')
    entireText = noisyReplaceAll( entireText, '</u>', '\\em*')
    entireText = noisyDeleteAll( entireText, '</div>' )
    entireText = noisyDeleteAll( entireText, '<sup></sup>' )
    entireText = noisyDeleteAll( entireText, '<sup>' )
    entireText = noisyDeleteAll( entireText, '</sup>' )
    while '  ' in entireText:
        entireText = noisyReplaceAll( entireText, '  ', ' ' )
    while '\n\n' in entireText:
        entireText = noisyReplaceAll( entireText, '\n\n', '\n' )
    while ' \n' in entireText:
        entireText = noisyReplaceAll( entireText, ' \n', '\n' )

    # Adjust book IDs, etc
    for name,bookID in ( ('Matthew','MAT'), ('Mark','MRK'), ('Luke','LUK'), ('John','JHN'), ('Acts','ACT'),
                        ('Romans','ROM'), ('First Corinthians','1CO'), ('Second Corinthians','2CO'),
                        ('Galatians','GAL'), ('Ephesians','MAT'), ('Philippians','PHP'), ('Colossians','COL'),
                        ('First Thessalonians','1TH'), ('Second Thessalonians','2TH'), ('First Timothy','1TI'), ('Second Timothy','2TI'),
                        ('Titus','TIT'), ('Philemon','PHM'), ('Hebrews','HEB'), ('James','JAS'),
                        ('First Peter','1PE'), ('Second Peter','2PE'),
                        ('First John','1JN'), ('Second John','2JN'), ('Third John','3JN'),
                        ('Jude','JUD'), ('Revelation','REV'), ):
        entireText = entireText.replace( '\\id '+name+' ', '\\id '+bookID+' ' )
    entireText = noisyReplaceAll( entireText, '\\h First ', '\\h 1 ')
    entireText = noisyReplaceAll( entireText, '\\h Second ', '\\h 2 ')
    entireText = noisyReplaceAll( entireText, '\\h Third ', '\\h 3 ')
    
    # Write the temp output (for debugging)
    outputFolderpath = '/Users/Robert/Desktop/FBVNT/'
    if 1: # Write out entire file for checking
        if not os.path.exists( outputFolderpath):
            os.makedirs( outputFolderpath )
        filepath = os.path.join( outputFolderpath, 'FBV.NT.usfm' )
        if BibleOrgSysGlobals.verbosityLevel > 1:
            print( "Writing temp file {}...".format( filepath ) )
        with open( filepath, 'wt', encoding='utf-8' ) as BibleTextFile:
            BibleTextFile.write( entireText )
            
    # Write out the USFM files
    USFMFolderpath = os.path.join( outputFolderpath, 'USFM/' )
    if not os.path.exists( USFMFolderpath):
        os.makedirs( USFMFolderpath )
    splitAndWriteBooks( entireText, USFMFolderpath )
# end of FreeBibleConvert.main


if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support() # Multiprocessing support for frozen Windows executables

    # import sys
    # if 'win' in sys.platform: # Convert stdout so we don't get zillions of UnicodeEncodeErrors
        # from io import TextIOWrapper
        # sys.stdout = TextIOWrapper( sys.stdout.detach(), sys.stdout.encoding, 'namereplace' if sys.version_info >= (3,5) else 'backslashreplace' )

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( ProgName, ProgVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    main()

    BibleOrgSysGlobals.closedown( ProgName, ProgVersion )
# end of FreeBibleConvert.py
