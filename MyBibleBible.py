#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# MyBibleBible.py
#
# Module handling "MyBible" Bible module files
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
Module reading and loading MyBible Bible databases.
These can be downloaded from: http://mybible.zone/b-eng.php?q=mybible&k=bibles&qq=2&q=bbl
The format can be found from: http://mybible.zone/creat-eng.php
    and was here: https://docs.google.com/document/d/12rf4Pqy13qhnAW31uKkaWNTBDTtRbNW0s7cM0vcimlA/edit?pref=2&pli=1

The filename.SQLite3 is the module abbreviation.

A MyBible Bible module file has three tables
    TABLE info (name TEXT, value TEXT);
    TABLE "books" ("book_color" TEXT, "book_number" NUMERIC, "short_name" TEXT, "long_name" TEXT);
    TABLE "verses" ("book_number" NUMERIC, "chapter" NUMERIC, "verse" NUMERIC, "text" TEXT);
    UNIQUE INDEX verses_index on "verses" (book_number, chapter, verse);

Here is a typical info table:
    PRAGMA foreign_keys=OFF;
    BEGIN TRANSACTION;
    CREATE TABLE info (name TEXT, value TEXT);
    INSERT INTO "info" VALUES('description','International Standard Version');
    INSERT INTO "info" VALUES('chapter_string','Chapter');
    INSERT INTO "info" VALUES('language','en');
    INSERT INTO "info" VALUES('language_iso639-2b','eng');
    INSERT INTO "info" VALUES('russian_numbering','false');
    INSERT INTO "info" VALUES('strong_numbers','false');
    INSERT INTO "info" VALUES('right_to_left','false');
    COMMIT;

Should look for books_all table first.
Here is a typical books table:
    PRAGMA foreign_keys=OFF;
    BEGIN TRANSACTION;
    CREATE TABLE "books" ("book_color" TEXT, "book_number" NUMERIC, "short_name" TEXT, "long_name" TEXT);
    INSERT INTO "books" VALUES('#ccccff',10,'Gen','Genesis');
    INSERT INTO "books" VALUES('#ccccff',20,'Exo','Exodus');
    INSERT INTO "books" VALUES('#ccccff',30,'Lev','Leviticus');
    INSERT INTO "books" VALUES('#ccccff',40,'Num','Numbers');
    INSERT INTO "books" VALUES('#ccccff',50,'Deu','Deuteronomy');
    INSERT INTO "books" VALUES('#ffcc99',60,'Josh','Joshua');
    …
    INSERT INTO "books" VALUES('#00ff00',710,'3Jn','3 John');
    INSERT INTO "books" VALUES('#00ff00',720,'Jud','Jude');
    INSERT INTO "books" VALUES('#ff7c80',730,'Rev','Revelation');
    COMMIT;

Here is a typical verses table segment (one verse per SQLite3 table row):
    …
    INSERT INTO "verses" VALUES(730,22,17,'<n>{Concluding Invitation}</n> d The Spirit and the bride say, "Come!" Let everyone who hears this say, "Come!" Let everyone who is thirsty come! Let anyone who wants the water of life take it as a gift! ');
    INSERT INTO "verses" VALUES(730,22,18,'<n>{Concluding Warning}</n> d I warn everyone who hears the words of the prophecy in this book: If anyone adds anything to them, God will strike him with the plagues that are written in this book. ');
    INSERT INTO "verses" VALUES(730,22,19,'If anyone takes away any words from the book of this prophecy, God will take away his portion of the tree of life and the holy city that are described in this book. ');
    INSERT INTO "verses" VALUES(730,22,20,'<n>{Epilogue}</n> d The one who is testifying to these things says, "Yes, I am coming soon!" Amen! Come, Lord Jesus! ');
    INSERT INTO "verses" VALUES(730,22,21,'May the grace of the Lord Jesus be with all the saints. Amen. <n>{Other mss. lack Amen}</n> ');
    CREATE UNIQUE INDEX verses_index on "verses" (book_number, chapter, verse);
    COMMIT;
"""

from gettext import gettext as _

LastModifiedDate = '2016-04-10' # by RJH
ShortProgName = "MyBibleBible"
ProgName = "MyBible Bible format handler"
ProgVersion = '0.10'
ProgNameVersion = '{} v{}'.format( ShortProgName, ProgVersion )
ProgNameVersionDate = '{} {} {}'.format( ProgNameVersion, _("last modified"), LastModifiedDate )

debuggingThisModule = True


import logging, os
import sqlite3
import multiprocessing
from collections import OrderedDict

import BibleOrgSysGlobals
from Bible import Bible, BibleBook
from BibleOrganizationalSystems import BibleOrganizationalSystem



FILENAME_ENDINGS_TO_ACCEPT = ( '.SQLITE3', ) # Must be UPPERCASE
BIBLE_FILENAME_ENDINGS_TO_ACCEPT = ( '.SQLITE3', '.COMMENTARIES.SQLITE3', ) # Must be UPPERCASE
FILENAME_PARTS_TO_REJECT = ( '.DICTIONARY.', '.CROSSREFERENCES.', ) # Must be UPPERCASE


# NOTE that color values can vary between modules
BOOK_TABLE = {
    'GEN': ( 0xccccff, 10, 'Быт', 'Бытие', 'Gen', 'Genesis'),
    'EXO': ( 0xccccff, 20, 'Исх', 'Исход', 'Exo', 'Exodus'),
    'LEV': ( 0xccccff, 30, 'Лев', 'Левит', 'Lev', 'Leviticus'),
    'NUM': ( 0xccccff, 40, 'Чис', 'Числа', 'Num', 'Numbers'),
    'DEU': ( 0xccccff, 50, 'Втор', 'Второзаконие', 'Deu', 'Deuteronomy'),
    'JOS': ( 0xffcc99, 60, 'Нав', 'Иисус Навин', 'Josh', 'Joshua'),
    'JDG': ( 0xffcc99, 70, 'Суд', 'Судьи', 'Judg', 'Judges'),
    'RUT': ( 0xffcc99, 80, 'Руфь', 'Руфь', 'Ruth', 'Ruth'),
    'SA1': ( 0xffcc99, 90, '1Цар', '1-я Царств', '1Sam', '1 Samuel'),
    'SA2': ( 0xffcc99, 100, '2Цар', '2-я Царств', '2Sam', '2 Samuel'),
    'KI1': ( 0xffcc99, 110, '3Цар', '3-я Царств', '1Kin', '1 Kings'),
    'KI2': ( 0xffcc99, 120, '4Цар', '4-я Царств', '2Kin', '2 Kings'),
    'JDT': ( 0xffcc99, 180, 'Иудф', 'Иудифь', 'Jdth', 'Judith'),
    'CH1': ( 0xffcc99, 130, '1Пар', '1-я Паралипоменон', '1Chr', '1 Chronicles'),
    'CH2': ( 0xffcc99, 140, '2Пар', '2-я Паралипоменон', '2Chr', '2 Chronicles'),
    'EZR': ( 0xffcc99, 150, 'Ездр', 'Ездра', 'Ezr', 'Ezra'),
    'NEH': ( 0xffcc99, 160, 'Неем', 'Неемия', 'Neh', 'Nehemiah'),
    'LES': ( 0xffcc99, 165, '2Езд', '2-я Ездры', '2Esd', '2 Esdras'), # Was 740 -- NOT SURE ABOUT THIS ONE -- 2nd Ezra
    'TOB': ( 0xffcc99, 170, 'Тов', 'Товит', 'Tob', 'Tobit'),
    'EST': ( 0xffcc99, 190, 'Есф', 'Есфирь', 'Esth', 'Esther'),
    'JOB': ( 0x66ff99, 220, 'Иов', 'Иов', 'Job', 'Job'),
    'PSA': ( 0x66ff99, 230, 'Пс', 'Псалтирь', 'Ps', 'Psalms'),
    'PRO': ( 0x66ff99, 240, 'Прит', 'Притчи', 'Prov', 'Proverbs'),
    'ECC': ( 0x66ff99, 250, 'Еккл', 'Екклесиаст', 'Eccl', 'Ecclesiastes'),
    'SNG': ( 0x66ff99, 260, 'Песн', 'Песня Песней', 'Song', 'Song of Solomon'),
    'WIS': ( 0x66ff99, 270, 'Прем', 'Премудрость Соломона', 'Wis', 'Wisdom of Solomon'),
    'SIR': ( 0x66ff99, 280, 'Сир', 'Сирах', 'Sir', 'Sirach'),
    'ISA': ( 0xff9fb4, 290, 'Ис', 'Исаия', 'Isa', 'Isaiah'),
    'JER': ( 0xff9fb4, 300, 'Иер', 'Иеремия', 'Jer', 'Jeremiah'),
    'PAZ': ( 0xff9fb4, 305, '???', '???', 'Azar', 'Azariah'),
    'LAM': ( 0xff9fb4, 310, 'Плач', 'Плач Иеремии', 'Lam', 'Lamentations'),
    'LJE': ( 0xff9fb4, 315, 'Посл', 'Послание Иеремии', 'Let', 'Letter of Jeremiah'),
    'BAR': ( 0xff9fb4, 320, 'Вар', 'Варух', 'Bar', 'Baruch'),
    'SUS': ( 0xff9fb4, 325, '???', '???', 'Sus', 'Susanna'),
    'EZE': ( 0xff9fb4, 330, 'Иез', 'Иезекииль', 'Ezek', 'Ezekiel'),
    'DAN': ( 0xff9fb4, 340, 'Дан', 'Даниил', 'Dan', 'Daniel'),
    'BEL': ( 0xff9fb4, 345, '???', '???', 'Bel', 'Bel and Dragon'),
    'HOS': ( 0xffff99, 350, 'Ос', 'Осия', 'Hos', 'Hosea'),
    'JOL': ( 0xffff99, 360, 'Иоил', 'Иоиль', 'Joel', 'Joel'),
    'AMO': ( 0xffff99, 370, 'Ам', 'Амос', 'Am', 'Amos'),
    'OBA': ( 0xffff99, 380, 'Авд', 'Авдий', 'Oba', 'Obadiah'),
    'JNA': ( 0xffff99, 390, 'Ион', 'Иона', 'Jona', 'Jonah'),
    'MIC': ( 0xffff99, 400, 'Мих', 'Михей', 'Mic', 'Micah'),
    'NAH': ( 0xffff99, 410, 'Наум', 'Наум', 'Nah', 'Nahum'),
    'HAB': ( 0xffff99, 420, 'Авв', 'Аввакум', 'Hab', 'Habakkuk'),
    'ZEP': ( 0xffff99, 430, 'Соф', 'Софония', 'Zeph', 'Zephaniah'),
    'HAG': ( 0xffff99, 440, 'Агг', 'Аггей', 'Hag', 'Haggai'),
    'ZEC': ( 0xffff99, 450, 'Зах', 'Захария', 'Zech', 'Zechariah'),
    'MAL': ( 0xffff99, 460, 'Мал', 'Малахия', 'Mal', 'Malachi'),
    'MA1': ( 0xd3d3d3, 462, '1Мак', '1-я Маккавейская', '1Mac', '1 Maccabees'), # Was 200
    'MA2': ( 0xd3d3d3, 464, '2Мак', '2-я Маккавейская', '2Mac', '2 Maccabees'), # Was 210
    'MA3': ( 0xd3d3d3, 466, '3Мак', '3-я Маккавейская', '3Mac', '3 Maccabees'), # MAN appears at 466 in KJ-1769
    'EZ5': ( 0xd3d3d3, 468, '3Езд', '3-я Ездры', '3Esd', '3 Esdras'), # Was 750 -- NOT SURE ABOUT THIS ONE -- 3rd Ezra
    'MAT': ( 0xff6600, 470, 'Мат', 'От Матфея', 'Mat', 'Matthew'),
    'MRK': ( 0xff6600, 480, 'Мар', 'От Марка', 'Mar', 'Mark'),
    'LUK': ( 0xff6600, 490, 'Лук', 'От Луки', 'Luk', 'Luke'),
    'JHN': ( 0xff6600, 500, 'Ин', 'От Иоанна', 'John', 'John'),
    'ACT': ( 0x00ffff, 510, 'Деян', 'Деяния', 'Acts', 'Acts'),
    'JAM': ( 0x00ff00, 660, 'Иак', 'Иакова', 'Jam', 'James'),
    'PE1': ( 0x00ff00, 670, '1Пет', '1-е Петра', '1Pet', '1 Peter'),
    'PE2': ( 0x00ff00, 680, '2Пет', '2-е Петра', '2Pet', '2 Peter'),
    'JN1': ( 0x00ff00, 690, '1Ин', '1-е Иоанна', '1Jn', '1 John'),
    'JN2': ( 0x00ff00, 700, '2Ин', '2-е Иоанна', '2Jn', '2 John'),
    'JN3': ( 0x00ff00, 710, '3Ин', '3-е Иоанна', '3Jn', '3 John'),
    'JDE': ( 0x00ff00, 720, 'Иуд', 'Иуды', 'Jud', 'Jude'),
    'ROM': ( 0xffff00, 520, 'Рим', 'К Римлянам', 'Rom', 'Romans'),
    'CO1': ( 0xffff00, 530, '1Кор', '1-е Коринфянам', '1Cor', '1 Corinthians'),
    'CO2': ( 0xffff00, 540, '2Кор', '2-е Коринфянам', '2Cor', '2 Corinthians'),
    'GAL': ( 0xffff00, 550, 'Гал', 'К Галатам', 'Gal', 'Galatians'),
    'EPH': ( 0xffff00, 560, 'Еф', 'К Ефесянам', 'Eph', 'Ephesians'),
    'PHP': ( 0xffff00, 570, 'Флп', 'К Филиппийцам', 'Phil', 'Philippians'),
    'COL': ( 0xffff00, 580, 'Кол', 'К Колоссянам', 'Col', 'Colossians'),
    'TH1': ( 0xffff00, 590, '1Фес', '1-е Фессалоникийцам', '1Ths', '1 Thessalonians'),
    'TH2': ( 0xffff00, 600, '2Фес', '2-е Фессалоникийцам', '2Ths', '2 Thessalonians'),
    'TI1': ( 0xffff00, 610, '1Тим', '1-е Тимофею', '1Tim', '1 Timothy'),
    'TI2': ( 0xffff00, 620, '2Тим', '2-е Тимофею', '2Tim', '2 Timothy'),
    'TIT': ( 0xffff00, 630, 'Тит', 'К Титу', 'Tit', 'Titus'),
    'PHM': ( 0xffff00, 640, 'Флм', 'К Филимону', 'Phlm', 'Philemon'),
    'HEB': ( 0xffff00, 650, 'Евр', 'К Евреям', 'Heb', 'Hebrews'),
    'REV': ( 0xff7c80, 730, 'Откр', 'Откровение', 'Rev', 'Revelation'),
    'LAO': ( 0x00ff00, 780, 'Лаод', 'К Лаодикийцам', 'Lao', 'Letter to the Laodiceans'),
    'MAN': ( 0x66ff99, 790, 'Мол', 'Молитва Манассии', 'Man', 'Prayer of Manasseh'), # Can also appear at 466
    }
# Create a pivot table by book number
BOOKNUMBER_TABLE = {}
# Check the table
for BBB,stuff in BOOK_TABLE.items():
    #print( BBB, stuff )
    assert len(stuff) == 6
    for something in stuff: assert something # shouldn't be blank
    assert BibleOrgSysGlobals.BibleBooksCodes.getReferenceNumber(BBB)
    color, bookNumber, rusAbbrev, rusName, engAbbrev, engName = stuff
    assert bookNumber not in BOOKNUMBER_TABLE
    BOOKNUMBER_TABLE[bookNumber] = (BBB,color,rusAbbrev,rusName,engAbbrev,engName)
assert len(BOOKNUMBER_TABLE) == len(BOOK_TABLE)



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



def MyBibleBibleFileCheck( givenFolderName, strictCheck=True, autoLoad=False, autoLoadBooks=False ):
    """
    Given a folder, search for MyBible Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number of Bibles found.

    if autoLoad is true and exactly one MyBible Bible is found,
        returns the loaded MyBibleBible object.
    """
    if BibleOrgSysGlobals.verbosityLevel > 2: print( "MyBibleBibleFileCheck( {}, {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad, autoLoadBooks ) )
    if BibleOrgSysGlobals.debugFlag:
        assert givenFolderName and isinstance( givenFolderName, str )
        assert autoLoad in (True,False,)

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( _("MyBibleBibleFileCheck: Given {!r} folder is unreadable").format( givenFolderName ) )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( _("MyBibleBibleFileCheck: Given {!r} path is not a folder").format( givenFolderName ) )
        return False

    # Find all the files and folders in this folder
    if BibleOrgSysGlobals.verbosityLevel > 3: print( " MyBibleBibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
    foundFolders, foundFiles = [], []
    for something in os.listdir( givenFolderName ):
        somepath = os.path.join( givenFolderName, something )
        if os.path.isdir( somepath ): foundFolders.append( something )
        elif os.path.isfile( somepath ):
            somethingUpper = something.upper()
            somethingUpperProper, somethingUpperExt = os.path.splitext( somethingUpper )
            ignore = False
            for stuff in FILENAME_PARTS_TO_REJECT:
                if stuff in somethingUpper: ignore=True; break
            if ignore: continue
            #if not somethingUpperExt[1:] in extensionsToIgnore: # Compare without the first dot
            if somethingUpperExt in FILENAME_ENDINGS_TO_ACCEPT:
                foundFiles.append( something )
    if '__MACOSX' in foundFolders:
        foundFolders.remove( '__MACOSX' )  # don't visit these directories

    # See if there's an MyBibleBible project here in this given folder
    numFound = 0
    looksHopeful = False
    lastFilenameFound = None
    for thisFilename in sorted( foundFiles ):
        lastFilenameFound = thisFilename
        numFound += 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "MyBibleBibleFileCheck got", numFound, givenFolderName, lastFilenameFound )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            MyBB = MyBibleBible( givenFolderName, lastFilenameFound )
            if autoLoad or autoLoadBooks: MyBB.preload()
            if autoLoadBooks: MyBB.loadBooks() # Load and process the database
            return MyBB
        return numFound
    elif looksHopeful and BibleOrgSysGlobals.verbosityLevel > 2: print( "    Looked hopeful but no actual files found" )

    # Look one level down
    numFound = 0
    foundProjects = []
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
        if not os.access( tryFolderName, os.R_OK ): # The subfolder is not readable
            logging.warning( _("MyBibleBibleFileCheck: {!r} subfolder is unreadable").format( tryFolderName ) )
            continue
        if BibleOrgSysGlobals.verbosityLevel > 3: print( "    MyBibleBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
        foundSubfolders, foundSubfiles = [], []
        for something in os.listdir( tryFolderName ):
            somepath = os.path.join( givenFolderName, thisFolderName, something )
            if os.path.isdir( somepath ): foundSubfolders.append( something )
            elif os.path.isfile( somepath ):
                somethingUpper = something.upper()
                somethingUpperProper, somethingUpperExt = os.path.splitext( somethingUpper )
                ignore = False
                for stuff in FILENAME_PARTS_TO_REJECT:
                    if stuff in somethingUpper: ignore=True; break
                if ignore: continue
                #if not somethingUpperExt[1:] in extensionsToIgnore: # Compare without the first dot
                if somethingUpperExt in FILENAME_ENDINGS_TO_ACCEPT:
                    foundSubfiles.append( something )

        # See if there's an MyBible project here in this folder
        for thisFilename in sorted( foundSubfiles ):
            foundProjects.append( (tryFolderName, thisFilename,) )
            lastFilenameFound = thisFilename
            numFound += 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "MyBibleBibleFileCheck foundProjects", numFound, foundProjects )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            if BibleOrgSysGlobals.debugFlag: assert len(foundProjects) == 1
            MyBB = MyBibleBible( foundProjects[0][0], foundProjects[0][1] )
            if autoLoad or autoLoadBooks: MyBB.preload()
            if autoLoadBooks: MyBB.loadBooks() # Load and process the database
            return MyBB
        return numFound
# end of MyBibleBibleFileCheck



class MyBibleBible( Bible ):
    """
    Class for reading, validating, and converting MyBibleBible files.
    """
    def __init__( self, sourceFolder, givenFilename, encoding='utf-8' ):
        """
        Constructor: just sets up the Bible object.
        """
         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = 'MyBible Bible object'
        self.objectTypeString = 'MyBible'

        # Now we can set our object variables
        self.sourceFolder, self.sourceFilename, self.encoding = sourceFolder, givenFilename, encoding
        self.sourceFilepath =  os.path.join( self.sourceFolder, self.sourceFilename )

        # Do a preliminary check on the readability of our file
        if not os.access( self.sourceFilepath, os.R_OK ):
            logging.critical( _("MyBibleBible: File {!r} is unreadable").format( self.sourceFilepath ) )

        filenameBits = os.path.splitext( self.sourceFilename )
        self.name = self.abbreviation = filenameBits[0]
        self.fileExtension = filenameBits[1]

        #if self.fileExtension.upper().endswith('X'):
            #logging.warning( _("MyBibleBible: File {!r} is encrypted").format( self.sourceFilepath ) )
    # end of MyBibleBible.__init__


    def preload( self ):
        """
        Load the metadata from the SQLite3 database.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("preload()") )

        if BibleOrgSysGlobals.verbosityLevel > 2: print( _("Preloading {}…").format( self.sourceFilepath ) )

        fileExtensionUpper = self.fileExtension.upper()
        if fileExtensionUpper not in FILENAME_ENDINGS_TO_ACCEPT:
            logging.critical( "{} doesn't appear to be a MyBible file".format( self.sourceFilename ) )
        elif not self.sourceFilename.upper().endswith( BIBLE_FILENAME_ENDINGS_TO_ACCEPT[0] ):
            logging.critical( "{} doesn't appear to be a MyBible Bible file".format( self.sourceFilename ) )

        connection = sqlite3.connect( self.sourceFilepath )
        connection.row_factory = sqlite3.Row # Enable row names
        self.cursor = connection.cursor()

        # First get the settings
        if self.suppliedMetadata is None: self.suppliedMetadata = {}
        self.suppliedMetadata['MyBible'] = {}
        self.cursor.execute( 'select * from info' )
        rows = self.cursor.fetchall()
        for row in rows:
            assert len(row) == 2 # name, value
            name, value = row
            #if debuggingThisModule: print( '  INFO', name, repr(value) )
            assert name in ( 'description', 'chapter_string',
                            'language', 'language_iso639-2b', 'region', 'russian_numbering',
                            'strong_numbers', 'strong_numbers_prefix',
                            'right_to_left', 'contains_accents',
                            'detailed_info', 'introduction_string', 'Introduction',
                            'is_footnotes', )
            # NOTE: detailed_info may contain HTML formatting
            if value == 'false': value = False
            elif value == 'true': value = True
            self.suppliedMetadata['MyBible'][name] = value
        #print( self.suppliedMetadata['MyBible'] ); halt

        if self.suppliedMetadata['MyBible']['language'] == 'ru':
            self.BOS = BibleOrganizationalSystem( 'GENERIC-81-RUS' )
        else: self.BOS = BibleOrganizationalSystem( 'GENERIC-KJV-81-ENG' )

        # Now get the book info -- try the books_all table first to see if it exists
        self.suppliedMetadata['MyBible']['BookInfo'] = OrderedDict()

        loadedBookInfo = False
        try:
            self.cursor.execute( 'select * from books_all' )
            rows = self.cursor.fetchall()
            #print( "  BOOKS_ALL rows", len(rows) )
            isPresent = True
            for j, row in enumerate( rows ):
                assert len(row) == 5
                bookColor, bookNumber, shortName, longName, isPresent = row
                #print( bookColor, bookNumber, shortName, longName, isPresent )
                if BibleOrgSysGlobals.debugFlag: assert bookNumber in BOOKNUMBER_TABLE
                if len(rows) == 66: BBB = BibleOrgSysGlobals.BibleBooksCodes.getBBBFromReferenceNumber( j+1 )
                else:
                    BBB = self.BOS.getBBB( longName ) # Might not work for other languages
                    if BBB is None: BBB = self.BOS.getBBB( shortName ) # Might not work for other languages
                #print( "  Got1 BBB", BBB, repr(longName) )
                assert BBB
                self.suppliedMetadata['MyBible']['BookInfo'][BBB] = { 'bookNumber':bookNumber, 'longName':longName,
                                                'shortName':shortName, 'isPresent':isPresent, 'bookColor':bookColor }
            if BibleOrgSysGlobals.verbosityLevel > 1:
                print( "  Loaded book info ({}) from BOOKS_ALL table".format( len(rows) ) )
            loadedBookInfo = True
        except sqlite3.OperationalError: pass # Table is not in older module versions

        if not loadedBookInfo: # from newer books_all table
            try:
                self.cursor.execute( 'select * from books' )
                rows = self.cursor.fetchall()
                #print( "  BOOKS rows", len(rows) )
                isPresent = True
                for j, row in enumerate( rows ):
                    try: bookColor, bookNumber, shortName, longName = row
                    except ValueError: bookColor, bookNumber, shortName, longName, isPresent = row
                    #print( bookColor, bookNumber, shortName, longName, isPresent )
                    if BibleOrgSysGlobals.debugFlag: assert bookNumber in BOOKNUMBER_TABLE
                    longName = longName.strip() # Why do some have a \n at the end???
                    if len(rows) == 66: BBB = BibleOrgSysGlobals.BibleBooksCodes.getBBBFromReferenceNumber( j+1 )
                    else:
                        BBB = self.BOS.getBBB( longName ) # Might not work for other languages
                        if BBB is None: BBB = self.BOS.getBBB( shortName ) # Might not work for other languages
                        if BBB is None and shortName=='3Ма': BBB = 'MA3' # Cant't track down why this fails ???
                    #print( "  Got2 BBB", BBB, repr(longName), repr(shortName) )
                    assert BBB
                    self.suppliedMetadata['MyBible']['BookInfo'][BBB] = { 'bookNumber':bookNumber, 'longName':longName,
                                                    'shortName':shortName, 'isPresent':isPresent, 'bookColor':bookColor }
                if BibleOrgSysGlobals.verbosityLevel > 1:
                    print( "  Loaded book info ({}) from (old) BOOKS table".format( len(rows) ) )
                loadedBookInfo = True
            except sqlite3.OperationalError: pass # Table is not in older module versions

        if not loadedBookInfo:
            if '.commentaries.' not in self.sourceFilename:
                logging.critical( "MyBibleBible.preload for {} had no books table".format( self.sourceFilename ) )
        #print( self.suppliedMetadata['MyBible'] ); halt
        self.preloadDone = True
    # end of MyBibleBible.preload


    def loadBooks( self ):
        """
        Load all the books out of the SQLite3 database.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("loadBooks()") )
        assert self.preloadDone

        if BibleOrgSysGlobals.verbosityLevel > 2: print( _("Loading {}…").format( self.sourceFilepath ) )

        for BBB in self.suppliedMetadata['MyBible']['BookInfo']:
            #print( 'isPresent', self.suppliedMetadata['MyBible']['BookInfo'][BBB]['isPresent'] )
            if self.suppliedMetadata['MyBible']['BookInfo'][BBB]['isPresent']:
                self.loadBook( BBB )
            elif BibleOrgSysGlobals.verbosityLevel > 1:
                print( "   {} is not present in this Bible".format( BBB ) )

        self.cursor.close()
        self.applySuppliedMetadata( 'MyBible' ) # Copy some to self.settingsDict
        self.doPostLoadProcessing()
    # end of MyBibleBible.loadBooks


    def loadBook( self, BBB ):
        """
        Load the requested book out of the SQLite3 database.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("loadBook( {} )").format( BBB ) )
        assert self.preloadDone

        if BBB in self.books:
            if BibleOrgSysGlobals.debugFlag: print( "  {} is already loaded -- returning".format( BBB ) )
            return # Already loaded
        if BBB in self.triedLoadingBook:
            logging.warning( "We had already tried loading MyBibleBible {} for {}".format( BBB, self.name ) )
            return # We've already attempted to load this book
        self.triedLoadingBook[BBB] = True
        self.bookNeedsReloading[BBB] = False
        if BibleOrgSysGlobals.verbosityLevel > 2 or BibleOrgSysGlobals.debugFlag: print( _("MyBibleBible: Loading {} from {}…").format( BBB, self.sourceFilepath ) )

        if '.commentaries.' in self.sourceFilename: self.__loadBibleCommentaryBook( BBB )
        else: self.__loadBibleBook( BBB )
    # end of MyBibleBible.loadBook


    def __loadBibleBook( self, BBB ):
        """
        Load the requested Bible book out of the SQLite3 database.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("__loadBibleBook( {} )").format( BBB ) )

        lastC = None
        def importVerseLine( name, BBB, C, V, originalLine, bookObject ):
            """
            Change MyBible format codes to our codes
                and then add the line to the given bookObject
            """
            nonlocal lastC

            #if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                #print( exp("importVerseLine( {!r}, {} {}:{}, {!r}, ... )").format( name, BBB, C, V, originalLine ) )

            if originalLine is None: # We don't have an entry for this C:V
                return

            while originalLine and originalLine[-1] in '\r\n': # RHB
                originalLine = originalLine[:-1]
            assert '\n' not in originalLine and '\r' not in originalLine
            line = originalLine

            if line.endswith( '<BR>' ): line = line[:-4] # CSLU

            # Change MyBible format codes
            line = line.replace( '<n>{', '\\f ' ).replace( '}</n>', '\\f*' ) # ISV
            line = line.replace( '<n>', '\\f ' ).replace( '</n>', '\\f*' )
            line = line.replace( '<f>', '\\fn ' ).replace( '</f>', '\\fn*' ) # BTI
            line = line.replace( '<i>', '\\add ' ).replace( '</i>', '\\add*' )
            line = line.replace( '<b>', '\\bd ' ).replace( '</b>', '\\bd*' ) # RHB
            line = line.replace( '<e>', '\\em ' ).replace( '</e>', '\\em*' )
            line = line.replace( '<J>', '\\wj ' ).replace( '</J>', '\\wj*' ).replace( '<J/>', '\\wj*' ) # ¥­£¥
            line = line.replace( '<S>', '\\str ' ).replace( '</S>', '\\str*' )
            line = line.replace( '<t>', '\\qm ' ).replace( '</t>', '\\m ' )
            line = line.replace( '<br/>', '\\m ' )
            line = line.replace( '<pb/>', '\\p ' )
            line = line.replace( '<p>', '\\p ' ) # KJ-1769
            line = line.replace( '<br>', '\\m ' ) # RHB

            # Check for left-overs
            if '<' in line or '>' in line: # or '{' in line or '}' in line: RSTI has braces
                print( exp("importVerseLine( {!r} failed at {} {}:{} {!r} from {!r} )").format( name, BBB, C, V, line, originalLine ) )
                if debuggingThisModule: halt

            # Ok, use the adjusted info
            if C!=lastC:
                bookObject.addLine( 'c', str(C) )
                lastC = C
            #print( BBB, C, V, repr(line) )
            bookObject.addLine( 'v', '{} {}'.format( V, line ) )
        # end of importVerseLine


        # Main code for loadBook()
        if BBB not in self.suppliedMetadata['MyBible']['BookInfo'] \
        or not self.suppliedMetadata['MyBible']['BookInfo'][BBB]['isPresent']:
            return

        # Create the empty book
        thisBook = BibleBook( self, BBB )
        thisBook.objectNameString = "MyBible Bible Book object"
        thisBook.objectTypeString = "MyBible"

        C = V = 1

        #ourGlobals = {}
        #continued = ourGlobals['haveParagraph'] = False
        haveLines = False
        mbBookNumber = self.suppliedMetadata['MyBible']['BookInfo'][BBB]['bookNumber']
        #print( repr(mbBookNumber) )
        self.cursor.execute('select chapter,verse,text from verses where book_number=?', (mbBookNumber,) )
        for row in self.cursor.fetchall():
            C, V, line = row
            #try:
                #row = self.cursor.fetchone()
                #C, V, line = row
            #except TypeError: # This reference is missing (row is None)
                ##print( "something wrong at", BBB, C, V )
                ##if BibleOrgSysGlobals.debugFlag: halt
                ##print( row )
                #line = None
            #print ( mbBookNumber, BBB, C, V, "MyBib file line is", repr(line) )
            if line is None: logging.warning( "MyBibleBible.loadBibleBook: Found missing verse line at {} {}:{}".format( BBB, C, V ) )
            else: # line is not None
                if not line: logging.warning( "MyBibleBible.loadBibleBook: Found blank verse line at {} {}:{}".format( BBB, C, V ) )
                else:
                    haveLines = True

                    ## Some modules end lines with \r\n or have it in the middle!
                    ##   (We just ignore these for now)
                    #while line and line[-1] in '\r\n': line = line[:-1]
                    #if '\r' in line or '\n' in line: # (in the middle)
                        #logging.warning( "MyBibleBible.load: Found CR or LF characters in verse line at {} {}:{}".format( BBB, C, V ) )
                    #line = line.replace( '\r\n', ' ' ).replace( '\r', ' ' ).replace( '\n', ' ' )

            importVerseLine( self.name, BBB, C, V, line, thisBook ) # handle any formatting and save the line

        if haveLines:
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "  MyBible loadBibleBook saving", BBB )
            self.saveBook( thisBook )
        #else: print( "Not saving", BBB )

        #if ourGlobals['haveParagraph']:
            #thisBook.addLine( 'p', '' )
            #ourGlobals['haveParagraph'] = False
    # end of MyBibleBible.__loadBibleBook


    def __loadBibleCommentaryBook( self, BBB ):
        """
        Load the requested Bible book out of the SQLite3 database.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
            print( exp("__loadBibleCommentaryBook( {} )").format( BBB ) )

        lastC = None
        def importCommentaryLine( name, BBB, C, V, footnoteNumber, originalLine, bookObject ):
            """
            Change MyBible format codes to our codes
                and then add the line to the given bookObject
            """
            nonlocal lastC

            #if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                #print( exp("importCommentaryLine( {!r}, {} {}:{}, {!r},{!r}, ... )").format( name, BBB, C, V, footnoteNumber, originalLine ) )

            if originalLine is None: # We don't have an entry for this C:V
                return
            assert '\n' not in originalLine and '\r' not in originalLine
            line = originalLine

            # Change MyBible format codes
            line = line.replace( '<n>{', '\\f ' ).replace( '}</n>', '\\f*' ) # ISV
            line = line.replace( '<n>', '\\f ' ).replace( '</n>', '\\f*' )
            line = line.replace( '<i>', '\\add ' ).replace( '</i>', '\\add*' )
            line = line.replace( '<e>', '\\em ' ).replace( '</e>', '\\em*' )
            line = line.replace( '<J>', '\\wj ' ).replace( '</J>', '\\wj*' )
            line = line.replace( '<S>', '\\str ' ).replace( '</S>', '\\str*' )
            line = line.replace( '<t>', '\\qm ' ).replace( '</t>', '\\m ' )
            line = line.replace( '<br/>', '\\m ' ).replace( '<pb/>', '\\p ' )

            # Check for left-overs
            if '<' in line or '>' in line or '=' in line or '{' in line or '}' in line:
                if '<a ' not in line:
                    print( exp("importCommentaryLine( {!r} failed at {} {}:{} {!r} from {!r} )").format( name, BBB, C, V, line, originalLine ) )
                    if debuggingThisModule:
                        halt

            # Ok, use the adjusted info
            if C!=lastC:
                bookObject.addLine( 'c', str(C) )
                lastC = C
            #print( BBB, C, V, repr(line) )
            bookObject.addLine( 'v', '{} {}'.format( V, line ) )
        # end of importCommentaryLine


        # Main code for loadBook()
        #if BBB not in self.suppliedMetadata['MyBible']['BookInfo'] \
        #or not self.suppliedMetadata['MyBible']['BookInfo'][BBB]['isPresent']:
            #return

        # Create the empty book
        thisBook = BibleBook( self, BBB )
        thisBook.objectNameString = "MyBible Bible Book object"
        thisBook.objectTypeString = "MyBible"

        C = V = 1

        #ourGlobals = {}
        #continued = ourGlobals['haveParagraph'] = False
        haveLines = False
        footnoteMarker = None
        mbBookNumber = BOOK_TABLE[BBB][1]
        #print( repr(mbBookNumber) )
        if self.suppliedMetadata['MyBible']['is_footnotes']:
            self.cursor.execute('select chapter_number_from,verse_number_from,chapter_number_to,verse_number_to,marker,text from commentaries where book_number=?', (mbBookNumber,) )
        else:
            self.cursor.execute('select chapter_number_from,verse_number_from,chapter_number_to,verse_number_to,text from commentaries where book_number=?', (mbBookNumber,) )
        for row in self.cursor.fetchall():
            if self.suppliedMetadata['MyBible']['is_footnotes']:
                C, V, C2, V2, footnoteMarker, line = row
                #print( '{!r}:{!r}-{!r}:{!r} {!r}:{!r}'.format( C, V, C2, V2, footnoteMarker, line ) )
            else: # not footnotes
                C, V, C2, V2, line = row
                #print( '{!r}:{!r}-{!r}:{!r} {!r}'.format( C, V, C2, V2, line ) )
            if C2 is not None or V2 is not None:
                if C2 is None or C2==C:
                    assert V2 > V
                    V = '{}-{}'.format( V, V2 ) # Make a verse bridge
                else: halt # it's across a chapter boundary -- not finished
            #try:
                #row = self.cursor.fetchone()
                #C, V, line = row
            #except TypeError: # This reference is missing (row is None)
                ##print( "something wrong at", BBB, C, V )
                ##if BibleOrgSysGlobals.debugFlag: halt
                ##print( row )
                #line = None
            #print ( mbBookNumber, BBB, C, V, "MyBib file line is", repr(line) )
            if line is None: logging.warning( "MyBibleBible.loadBibleCommentaryBook: Found missing commentary line at {} {}:{}".format( BBB, C, V ) )
            else: # line is not None
                if not line: logging.warning( "MyBibleBible.loadBibleCommentaryBook: Found blank commentary line at {} {}:{}".format( BBB, C, V ) )
                else:
                    haveLines = True

                    ## Some modules end lines with \r\n or have it in the middle!
                    ##   (We just ignore these for now)
                    #while line and line[-1] in '\r\n': line = line[:-1]
                    #if '\r' in line or '\n' in line: # (in the middle)
                        #logging.warning( "MyBibleBible.load: Found CR or LF characters in verse line at {} {}:{}".format( BBB, C, V ) )
                    #line = line.replace( '\r\n', ' ' ).replace( '\r', ' ' ).replace( '\n', ' ' )

            importCommentaryLine( self.name, BBB, C, V, footnoteMarker, line, thisBook ) # handle any formatting and save the line

        if haveLines:
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "  MyBible loadBibleCommentaryBook saving", BBB )
            self.saveBook( thisBook )
        #else: print( "Not saving", BBB )

        #if ourGlobals['haveParagraph']:
            #thisBook.addLine( 'p', '' )
            #ourGlobals['haveParagraph'] = False
    # end of MyBibleBible.__loadBibleCommentaryBook
# end of MyBibleBible class



def testMyBB( indexString, MyBBfolder, MyBBfilename ):
    """
    Crudely demonstrate the MyBible Bible class.
    """
    #print( "tMSB", MyBBfolder )
    import VerseReferences
    #testFolder = "../../../../../Data/Work/Bibles/MyBible modules/" # Must be the same as below

    #TUBfolder = os.path.join( MyBBfolder, MyBBfilename )
    if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Demonstrating the MyBible Bible class {}…").format( indexString) )
    if BibleOrgSysGlobals.verbosityLevel > 0: print( "  Test folder/filename are {!r} {!r}".format( MyBBfolder, MyBBfilename ) )
    MyBB = MyBibleBible( MyBBfolder, MyBBfilename )
    MyBB.preload()
    #MyBB.load() # Load and process the file
    if BibleOrgSysGlobals.verbosityLevel > 1: print( MyBB ) # Just print a summary
    #print( MyBB.suppliedMetadata['MyBible'] )
    if MyBB is not None:
        if BibleOrgSysGlobals.strictCheckingFlag: MyBB.check()
        for reference in ( ('OT','GEN','1','1'), ('OT','GEN','1','3'), ('OT','PSA','3','0'), ('OT','PSA','3','1'), \
                            ('OT','DAN','1','21'),
                            ('NT','MAT','3','5'), ('NT','JDE','1','4'), ('NT','REV','22','21'), \
                            ('DC','BAR','1','1'), ('DC','MA1','1','1'), ('DC','MA2','1','1',), ):
            (t, b, c, v) = reference
            if t=='OT' and len(MyBB)==27: continue # Don't bother with OT references if it's only a NT
            if t=='NT' and len(MyBB)==39: continue # Don't bother with NT references if it's only a OT
            if t=='DC' and len(MyBB)<=66: continue # Don't bother with DC references if it's too small
            svk = VerseReferences.SimpleVerseKey( b, c, v )
            #print( svk, ob.getVerseDataList( reference ) )
            try:
                shortText = svk.getShortText()
                verseText = MyBB.getVerseText( svk )
                if BibleOrgSysGlobals.verbosityLevel > 1: print( reference, shortText, verseText )
            except KeyError:
                if BibleOrgSysGlobals.verbosityLevel > 1: print( '  testMyBB', reference, "not found!!!" )
                #if BibleOrgSysGlobals.debugFlag and debuggingThisModule: raise

        if 0: # Now export the Bible and compare the round trip
            MyBB.toMyBible()
            #doaResults = MyBB.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
            if BibleOrgSysGlobals.strictCheckingFlag: # Now compare the original and the derived USX XML files
                outputFolder = "OutputFiles/BOS_MyBible_Reexport/"
                if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nComparing original and re-exported MyBible files…" )
                result = BibleOrgSysGlobals.fileCompare( MyBBfilename, MyBBfilename, MyBBfolder, outputFolder )
                if BibleOrgSysGlobals.debugFlag:
                    if not result: halt
# end of testMyBB


def demo():
    """
    Main program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( ProgNameVersion )


    if 1: # demo the file checking code
        testFolder = "Tests/DataFilesForTests/MyBibleTest/"
        result1 = MyBibleBibleFileCheck( testFolder )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "TestA1", result1 )
        result2 = MyBibleBibleFileCheck( testFolder, autoLoad=True )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "TestA2", result2 )
        result3 = MyBibleBibleFileCheck( testFolder, autoLoadBooks=True )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "TestA3", result3 )


    if 1: # individual modules in the test folder
        testFolder = "../../../../../Data/Work/Bibles/MyBible modules/"
        names = ('CSLU',)
        for j, name in enumerate( names):
            fullname = name + '.SQLite3'
            pathname = os.path.join( testFolder, fullname )
            if os.path.exists( pathname ):
                indexString = 'B' + str( j+1 )
                if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nMyBib {}/ Trying {}".format( indexString, fullname ) )
                testMyBB( indexString, testFolder, fullname )


    if 1: # individual modules in the output folder
        testFolder = "OutputFiles/BOS_MyBibleExport"
        names = ("Matigsalug",)
        for j, name in enumerate( names):
            fullname = name + '.SQLite3'
            pathname = os.path.join( testFolder, fullname )
            if os.path.exists( pathname ):
                indexString = 'C' + str( j+1 )
                if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nMyBib {}/ Trying {}".format( indexString, fullname ) )
                testMyBB( indexString, testFolder, fullname )


    if 1: # all discovered modules in the test folder
        testFolder = "Tests/DataFilesForTests/theWordRoundtripTestFiles/"
        foundFolders, foundFiles = [], []
        for something in os.listdir( testFolder ):
            somepath = os.path.join( testFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ) and somepath.endswith('.SQLite3'):
                ignore = False
                somethingUpper = something.upper()
                for stuff in FILENAME_PARTS_TO_REJECT:
                    if stuff in somethingUpper: ignore=True; break
                if ignore: continue
                foundFiles.append( something )

        if BibleOrgSysGlobals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nD: Trying all {} discovered modules…".format( len(foundFiles) ) )
            parameters = [('D'+str(j+1),testFolder,filename) for j,filename in enumerate(sorted(foundFiles))]
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.starmap( testMyBB, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
        else: # Just single threaded
            for j, someFile in enumerate( sorted( foundFiles ) ):
                indexString = 'D' + str( j+1 )
                if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nMyBib {}/ Trying {}".format( indexString, someFile ) )
                #myTestFolder = os.path.join( testFolder, someFolder+'/' )
                testMyBB( indexString, testFolder, someFile )
                #break # only do the first one.........temp

    if 1: # all discovered modules in the test folder
        testFolder = "../../../../../Data/Work/Bibles/MyBible modules/"
        foundFolders, foundFiles = [], []
        for something in os.listdir( testFolder ):
            somepath = os.path.join( testFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ) and somepath.endswith('.SQLite3'):
                ignore = False
                somethingUpper = something.upper()
                for stuff in FILENAME_PARTS_TO_REJECT:
                    if stuff in somethingUpper: ignore=True; break
                if ignore: continue
                foundFiles.append( something )

        if BibleOrgSysGlobals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nE: Trying all {} discovered modules…".format( len(foundFiles) ) )
            parameters = [('E'+str(j+1),testFolder,filename) for j,filename in enumerate(sorted(foundFiles))]
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.starmap( testMyBB, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
        else: # Just single threaded
            for j, someFile in enumerate( sorted( foundFiles ) ):
                indexString = 'E' + str( j+1 )
                if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nMyBib {}/ Trying {}".format( indexString, someFile ) )
                #myTestFolder = os.path.join( testFolder, someFolder+'/' )
                testMyBB( indexString, testFolder, someFile )
                #break # only do the first one.........temp
# end of demo

if __name__ == '__main__':
    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    import sys
    if 'win' in sys.platform: # Convert stdout so we don't get zillions of UnicodeEncodeErrors
        from io import TextIOWrapper
        sys.stdout = TextIOWrapper( sys.stdout.detach(), sys.stdout.encoding, 'namereplace' )

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( ProgName, ProgVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    demo()

    BibleOrgSysGlobals.closedown( ProgName, ProgVersion )
# end of MyBibleBible.py