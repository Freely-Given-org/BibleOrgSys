#!/usr/bin/env -S uv run
# -\*- coding: utf-8 -\*-
# SPDX-License-Identifier: MPL-2.0
#
# ScriptureBurritoBible.py
#
# Module handling Scripture Burrito (SB) XML/JSON metadata
#   along with USFM, USX or USJ Bible books in folders or ZIP archives
# This module handles any text SBs with B/C/V encoding,
#   i.e., Bibles and commentaries, etc.
#
# Copyright (C) 2022-2026 Robert Hunt
# Author: Robert Hunt <Freely.Given.org+BOS@gmail.com>
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Module for defining and manipulating complete or partial SB Bible bundles
    saved in folders or ZIP archives on the local filesystem.

See https://docs.burrito.bible/en/develop/index.html
as well as various repositories at https://github.com/bible-technology.

CHANGELOG:
    2026-10-27 Add historical metadata adapters, USJ input and Scripture Burrito ZIP export.

"""

import os
import logging
import multiprocessing
from pathlib import Path, PurePosixPath
import json
import copy
import hashlib
import re
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import bos_books_codes_py

from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint
from BibleOrgSys.Bible import Bible
from BibleOrgSys.Formats.USFMBibleBook import USFMBibleBook
from BibleOrgSys.Formats.USXXMLBibleBook import USXXMLBibleBook


LAST_MODIFIED_DATE = '2026-10-27'
SHORT_PROGRAM_NAME = 'ScriptureBurrito'
PROGRAM_NAME = 'Scripture Burrito (SB) Bible handler'
PROGRAM_VERSION = '0.02'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'
DEBUGGING_THIS_MODULE = False

# Reader compatibility is structural, not a whitelist of version strings.
# Export only a schema whose shape we have checked; never label guessed output
# with a future version number. See Documentation/ScriptureBurrito.md.
WRITE_SCHEMA_VERSION = '1.0.0'
WRITE_SCHEMA_VERSIONS = ('1.0.0-rc2', WRITE_SCHEMA_VERSION)
_METADATA_FILENAMES = ('metadata.json', 'metadata.xml')
_USFM_MIMES = {'text/x-usfm', 'application/x-usfm', 'text/x-burrito-sfm'}
_USX_MIMES = {'text/x-usx', 'application/usx+xml', 'text/x-burrito-usx'}
_USJ_MIMES = {'application/usj+json', 'application/x-usj', 'text/x-usj'}
_SCOPE_BOOK_CODES = set(('GEN EXO LEV NUM DEU JOS JDG RUT 1SA 2SA 1KI 2KI 1CH 2CH EZR NEH EST JOB '
    'PSA PRO ECC SNG ISA JER LAM EZK DAN HOS JOL AMO OBA JON MIC NAM HAB ZEP HAG ZEC MAL '
    'MAT MRK LUK JHN ACT ROM 1CO 2CO GAL EPH PHP COL 1TH 2TH 1TI 2TI TIT PHM HEB JAS 1PE 2PE 1JN 2JN 3JN JUD REV '
    'TOB JDT ESG WIS SIR BAR LJE S3Y SUS BEL 1MA 2MA 3MA 4MA 1ES 2ES MAN PS2 ODA PSS JSA JDB TBS SST '
    'DNT BLT EZA 5EZ 6EZ DAG PS3 2BA LBA JUB ENO 1MQ 2MQ 3MQ REP 4BA LAO').split())
_PERIPHERAL_ROLES = {'FRT': 'preface', 'INT': 'introduction', 'BAK': 'x-backMatter',
                     'GLO': 'glo', 'CNC': 'cnc', 'TDX': 'tdx', 'NDX': 'ndx'}


def _safe_relative_path(name):
    """A portable ingredient path, confined to the bundle even on Windows."""
    if not isinstance(name, str) or not name or any(c in name for c in '\\:?*"><|\x00'):
        raise ValueError(f'Invalid Scripture Burrito ingredient path: {name!r}')
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in ('', '.', '..') for part in name.split('/')):
        raise ValueError(f'Unsafe Scripture Burrito ingredient path: {name!r}')
    return path


class _Bundle:
    """Read folders and ZIPs without extracting untrusted archive members."""
    def __init__(self, path, burritoPath=None):
        self.path = Path(path)
        self.prefix = ''
        if burritoPath is not None:
            _safe_relative_path(burritoPath)
        if self.path.is_dir():
            if burritoPath:
                selected = (self.path/burritoPath).resolve()
                if not selected.is_relative_to(self.path.resolve()):
                    raise ValueError('Selected burrito escapes its wrapper')
                self.path = selected
            self.metadataName = next((n for n in _METADATA_FILENAMES if (self.path/n).is_file()), None)
        else:
            with zipfile.ZipFile(self.path) as archive:
                names = archive.namelist()
                if len(names) != len(set(names)):
                    raise ValueError('Duplicate paths in Scripture Burrito ZIP')
                for name in names:
                    _safe_relative_path(name.rstrip('/'))
                candidates = [n for n in names if PurePosixPath(n).name in _METADATA_FILENAMES]
                rootNames = [n for n in candidates if '/' not in n]
                candidates = rootNames or candidates
                if len(candidates) != 1:
                    raise ValueError('Expected one metadata.json or metadata.xml in Scripture Burrito ZIP')
                candidate = PurePosixPath(candidates[0])
                self.metadataName = candidate.name
                self.prefix = '' if str(candidate.parent) == '.' else f'{candidate.parent}/'
                if burritoPath:
                    self.prefix += burritoPath + '/'
                    self.metadataName = next((n for n in _METADATA_FILENAMES if self.prefix+n in names), None)
        if self.metadataName is None:
            raise FileNotFoundError(f'No Scripture Burrito metadata in {self.path}')

    def read(self, name):
        relative = _safe_relative_path(name)
        if self.path.is_dir():
            path = (self.path/relative).resolve()
            if not path.is_relative_to(self.path.resolve()):
                raise ValueError(f'Ingredient escapes bundle through a symlink: {name}')
            return path.read_bytes()
        with zipfile.ZipFile(self.path) as archive:
            try:
                info = archive.getinfo(self.prefix + str(relative))
            except KeyError as error:
                raise FileNotFoundError(f'Missing Scripture Burrito ingredient: {name}') from error
            if info.file_size > 256 * 1024 * 1024:
                raise ValueError(f'Text ingredient is too large to load: {name}')
            return archive.read(info)


def _xml_root(data):
    # SB and USX do not need DTDs or custom entities.
    if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
        raise ValueError('DTD/entity declarations are not supported in Scripture Burrito XML')
    return ET.fromstring(data)


def _legacy_xml_metadata(data):
    """Project the 0.1 XML fields needed by the reader; retain the original too."""
    root = _xml_root(data)
    for element in root.iter():
        element.tag = element.tag.rsplit('}', 1)[-1]
    if root.tag != 'burritoMetadata':
        raise ValueError('Not Scripture Burrito 0.1 XML metadata')
    identification = root.find('identification')
    metadata = {'schemaVersion': root.get('schemaVersion'), 'identification': {},
                'type': {'flavor': root.findtext('type/flavor'),
                         'flavorType': root.findtext('type/flavorType')},
                'ingredients': {}}
    if identification is not None:
        for field in ('name', 'abbreviation', 'description'):
            values = {e.get('lang', 'und'): e.text or '' for e in identification.findall(field)}
            if values:
                metadata['identification'][field] = values
    for ingredient in root.findall('ingredients/ingredient'):
        descriptor = {e.tag: e.text or '' for e in ingredient if e.tag != 'path'}
        if 'size' in descriptor:
            descriptor['size'] = int(descriptor['size'])
        name = ingredient.findtext('path')
        if name in metadata['ingredients']:
            raise ValueError(f'Duplicate ingredient {name!r}')
        metadata['ingredients'][name] = descriptor
    metadata['languages'] = [{'tag': e.findtext('bcp47'),
        'name': {n.get('lang', 'und'): n.text or '' for n in e.findall('name')}}
        for e in root.findall('languages/language')]
    return metadata


def _read_metadata(bundle, *, allowWrapper=False):
    data = bundle.read(bundle.metadataName)
    metadata = (_legacy_xml_metadata(data) if bundle.metadataName.endswith('.xml')
                else json.loads(data.decode('utf-8-sig')))
    if not isinstance(metadata, dict):
        raise ValueError('Scripture Burrito metadata must be an object')
    if metadata.get('format') == 'scripture burrito wrapper':
        if allowWrapper: return metadata
        raise ValueError('This is a Scripture Burrito wrapper; select a contained burrito with burritoPath')
    if metadata.get('format', 'scripture burrito') != 'scripture burrito':
        raise ValueError('Not Scripture Burrito metadata: incorrect format')
    if not all(k in metadata for k in ('identification', 'type', 'ingredients')):
        raise ValueError('Scripture Burrito metadata needs identification, type and ingredients')
    if not isinstance(metadata['ingredients'], dict):
        raise ValueError('Scripture Burrito ingredients must be a path-to-descriptor object')
    return metadata


def _ingredient_format(name, descriptor):
    mime = descriptor.get('mimeType', '').split(';', 1)[0].strip().lower()
    suffix = PurePosixPath(name).suffix.lower()
    if mime in _USFM_MIMES:
        return 'USFM'
    if mime in _USX_MIMES:
        return 'USX'
    if mime in _USJ_MIMES:
        return 'USJ'
    if descriptor.get('role') in ('localedata', 'versification', 'timing',
            'copyrightStatement', 'license', 'styleSheet', 'font', 'illustration'):
        return None
    if mime in ('application/xml', 'text/xml') and (suffix == '.usx' or descriptor.get('scope')):
        return 'USX'
    if mime == 'application/json' and (descriptor.get('role') == 'text' or suffix == '.usj'):
        return 'USJ'
    # Older tools sometimes used generic MIME types for USFM/USX.
    if mime in ('', 'text/plain', 'application/octet-stream'):
        if suffix in ('.sfm', '.usfm'): return 'USFM'
        if suffix == '.usx': return 'USX'
        if suffix == '.usj': return 'USJ'
    return None


def _ingredient_scope(descriptor):
    scope = descriptor.get('scope')
    if scope is not None:
        if not isinstance(scope, dict):
            raise ValueError('Scripture Burrito ingredient scope must be an object')
        return scope
    # 0.1 used a combined string for either book scope or peripheral role.
    scope = {}
    for selector in descriptor.get('scopeOrRole', '').split(';'):
        match = re.fullmatch(r'([A-Z0-9]{3})(?:\s+(.+))?', selector.strip())
        if match:
            scope[match[1]] = [match[2]] if match[2] else []
    return scope


def _usj_to_usx(document):
    """USJ uses USX node names and attributes, with marker replacing style."""
    def convert(node):
        if not isinstance(node, dict) or not isinstance(node.get('type'), str):
            raise ValueError('Malformed USJ node')
        kind = node['type']
        allowed = {'USJ', 'book', 'chapter', 'verse', 'para', 'char', 'note',
                   'table', 'row', 'cell', 'ms', 'ref', 'figure', 'optbreak', 'sidebar', 'periph'}
        if kind not in allowed:
            raise ValueError(f'Unsupported USJ node type {kind!r}; refusing to discard content')
        element = ET.Element('usx' if kind == 'USJ' else kind)
        for key, value in node.items():
            if key in ('type', 'content'): continue
            if not isinstance(value, (str, int, float, bool)):
                raise ValueError(f'Unsupported USJ attribute {key!r}')
            element.set('style' if key == 'marker' else key,
                        str(value).lower() if isinstance(value, bool) else str(value))
        content = node.get('content', [])
        if not isinstance(content, list):
            raise ValueError('USJ content must be an array')
        for child in content:
            if isinstance(child, str):
                if len(element): element[-1].tail = (element[-1].tail or '') + child
                else: element.text = (element.text or '') + child
            else:
                element.append(convert(child))
        return element
    if not isinstance(document, dict) or document.get('type') != 'USJ':
        raise ValueError('Not a USJ document')
    return convert(document)


def _text_books(data, filetype):
    """Return (USFM code, parser type, bytes), including multi-book ingredients."""
    if filetype == 'USFM':
        text = data.decode('utf-8-sig')
        matches = list(re.finditer(r'(?m)^\\id\s+([A-Za-z0-9]{3})(?=\s|$)', text))
        if not matches:
            raise ValueError('USFM ingredient has no book identification (\\id)')
        if text[:matches[0].start()].strip():
            raise ValueError('Unexpected content before first USFM book identification')
        return [(match[1].upper(), 'USFM',
                 text[match.start():matches[i+1].start() if i+1 < len(matches) else len(text)].encode('utf-8'))
                for i, match in enumerate(matches)]
    root = _usj_to_usx(json.loads(data.decode('utf-8-sig'))) if filetype == 'USJ' else _xml_root(data)
    if root.tag != 'usx':
        raise ValueError('XML text ingredient must have a usx root')
    results, bookRoot, code = [], None, None
    for child in root:
        if child.tag == 'book':
            if bookRoot is not None:
                results.append((code, 'USX', ET.tostring(bookRoot, encoding='utf-8')))
            code = child.get('code', '').upper()
            bookRoot = ET.Element('usx', root.attrib)
        if bookRoot is None:
            raise ValueError('USX content precedes its book identification')
        bookRoot.append(child)
    if bookRoot is None:
        raise ValueError('USX ingredient has no book element')
    results.append((code, 'USX', ET.tostring(bookRoot, encoding='utf-8')))
    return results


def ScriptureBurritoBibleFileCheck(givenFolderName, strictCheck=True, autoLoad=False, autoLoadBooks=False):
    """Find a text burrito in a folder/ZIP or one directory level below it."""
    path = Path(givenFolderName)
    if not path.exists(): return False
    def find_burritos(candidate):
        try:
            metadata = _read_metadata(_Bundle(candidate), allowWrapper=True)
            if metadata.get('format') == 'scripture burrito wrapper':
                found = []
                paths = set()
                for entry in metadata.get('contents', {}).get('burritos', []):
                    selected = str(_safe_relative_path(entry['path']))
                    if selected in paths: raise ValueError('Duplicate burrito path in wrapper')
                    paths.add(selected)
                    child = _read_metadata(_Bundle(candidate, selected))
                    if any(_ingredient_format(n, d) for n, d in child['ingredients'].items()):
                        found.append((candidate, selected))
                return found
            if not strictCheck or any(_ingredient_format(n, d) for n, d in metadata['ingredients'].items()):
                return [(candidate, None)]
        except (OSError, ValueError, TypeError, KeyError, AttributeError, ET.ParseError, zipfile.BadZipFile):
            pass
        return []
    found = find_burritos(path)
    if not found and path.is_dir():
        for child in sorted(path.iterdir()):
            if child.name not in BibleOrgSysGlobals.COMMONLY_IGNORED_FOLDERS and (child.is_dir() or child.suffix.lower() == '.zip'):
                found.extend(find_burritos(child))
    if len(found) == 1 and (autoLoad or autoLoadBooks):
        bible = ScriptureBurritoBible(found[0][0], burritoPath=found[0][1])
        bible.preload()
        if autoLoadBooks: bible.loadBooks()
        return bible
    return len(found) or None


class ScriptureBurritoBible(Bible):
    """Read 0.1 XML/JSON, 0.2+, 1.x and compatible working-draft text burritos.

    Unknown metadata is retained. USFM, USX and USJ ingredients may coexist.
    Multiple representations of the same book prefer ``preferredFormat``;
    conflicting fragments/editions in the same format are rejected explicitly.
    ``verifyIntegrity`` checks declared sizes and hashes (old examples use dummy
    checksums, hence this is opt-in). ZIPs can also have one enclosing directory.
    """
    def __init__(self, givenFolderName, givenName=None, encoding='utf-8', *,
                 preferredFormat='USFM', verifyIntegrity=False, burritoPath=None):
        super().__init__()
        if preferredFormat not in ('USFM', 'USX', 'USJ'):
            raise ValueError('preferredFormat must be USFM, USX or USJ')
        self.objectNameString, self.objectTypeString = 'Scripture Burrito Bible object', 'SB'
        self.sourceFolder = self.sourceFilepath = Path(givenFolderName)
        self.givenName = self.name = givenName
        self.encoding = encoding
        self.preferredFormat, self.verifyIntegrity = preferredFormat, verifyIntegrity
        self.burritoPath = burritoPath
        self._bookSources = {}
        self.ingredientFormats = {}

    def preload(self):
        if self.preloadDone: return
        self.loadSBMetadata()
        self.applySuppliedMetadata('SB')
        self.preloadDone = True

    def loadSBMetadata(self):
        bundle = _Bundle(self.sourceFilepath, self.burritoPath)
        metadata = _read_metadata(bundle)
        if self.suppliedMetadata is None: self.suppliedMetadata = {}
        self.suppliedMetadata['SB'] = metadata
        if bundle.metadataName.endswith('.xml'):
            self.suppliedMetadata['SBXML'] = bundle.read(bundle.metadataName).decode('utf-8-sig')
        self.sbVersion = metadata.get('meta', {}).get('version', metadata.get('schemaVersion', 'unknown'))
        if not str(self.sbVersion).startswith(('0.1', '0.2', '0.3', '1.0', '2.0')):
            logging.warning('Reading unfamiliar Scripture Burrito version %s by its ingredient structure', self.sbVersion)
        if metadata.get('confidential'):
            logging.warning('This Scripture Burrito is marked confidential')
        self._bookSources = {}
        self.ingredientFormats = {}
        self.possibleFilenameDict = {}
        self.maximumPossibleFilenameTuples = []
        self.givenBookList = []
        self.availableBBBs = set()
        priorities = {f: i for i, f in enumerate([self.preferredFormat] +
                     [f for f in ('USFM', 'USX', 'USJ') if f != self.preferredFormat])}
        candidates = {}
        for name, descriptor in metadata['ingredients'].items():
            _safe_relative_path(name)
            if not isinstance(descriptor, dict):
                raise ValueError(f'Invalid ingredient descriptor: {name}')
            filetype = _ingredient_format(name, descriptor)
            data = bundle.read(name) if filetype or self.verifyIntegrity else None
            if self.verifyIntegrity:
                _verify_ingredient(name, data, descriptor)
            if not filetype: continue # styles, licenses, LDML, versification, audio, etc.
            if (filetype == 'USX' and descriptor.get('mimeType', '').split(';', 1)[0].strip().lower()
                    in ('application/xml', 'text/xml') and _xml_root(data).tag != 'usx'):
                continue # A scoped XML ancillary file is not necessarily USX.
            books = _text_books(data, filetype)
            scope = _ingredient_scope(descriptor)
            actualCodes = {code for code, _, _ in books}
            if scope and set(scope) != actualCodes:
                raise ValueError(f'Ingredient {name}: declared scope {list(scope)} differs from content {sorted(actualCodes)}')
            for code, parserType, bookData in books:
                try: BBB = bos_books_codes_py.usfm_abbrev_to_bos_book_code(code)
                except (KeyError, ValueError) as error:
                    raise ValueError(f'Unsupported Scripture Burrito book code {code!r} in {name}') from error
                if not BBB:
                    raise ValueError(f'Unsupported Scripture Burrito book code {code!r} in {name}')
                candidate = (priorities[filetype], name, parserType, bookData, scope.get(code, []))
                if BBB in candidates:
                    previous = candidates[BBB]
                    if previous[4] != candidate[4]:
                        raise ValueError(f'Multiple different scopes for {code}: {previous[1]} and {name}; merge/select these ingredients first')
                    if previous[0] == candidate[0] and previous[3] != bookData:
                        raise ValueError(f'Ambiguous text ingredients for {code}: {previous[1]} and {name}')
                    if previous[0] <= candidate[0]: continue
                candidates[BBB] = candidate
                self.ingredientFormats[BBB] = filetype
        for BBB, (_, name, parserType, _, _) in candidates.items():
            self._bookSources[BBB] = (name, parserType)
            self.possibleFilenameDict[BBB] = name
            self.maximumPossibleFilenameTuples.append((BBB, name))
            self.givenBookList.append(BBB)
            self.availableBBBs.add(BBB)
        flavorType = metadata['type'].get('flavorType', {})
        if candidates and isinstance(flavorType, dict):
            declared = flavorType.get('currentScope', {})
            actual = {bos_books_codes_py.bos_book_code_to_usfm_abbrev(b).upper() for b in candidates}
            missing = set(declared) - actual
            if missing:
                raise ValueError(f'No supported text ingredients for declared books: {sorted(missing)}')

    def applySuppliedMetadata(self, applyMetadataType):
        if applyMetadataType != 'SB':
            return super().applySuppliedMetadata(applyMetadataType)
        metadata = self.suppliedMetadata['SB']
        meta = metadata.get('meta', {})
        locale = meta.get('defaultLocale', meta.get('defaultLanguage', 'en'))
        def localized(value):
            if isinstance(value, str): return value
            if isinstance(value, dict):
                return value.get(locale) or value.get('en') or next(iter(value.values()), None)
            return None
        identification = metadata.get('identification', {})
        self.name = self.givenName or localized(identification.get('name')) or self.sourceFilepath.stem
        self.abbreviation = localized(identification.get('abbreviation'))
        self.settingsDict['Name'] = self.name
        if self.abbreviation: self.settingsDict['Abbreviation'] = self.abbreviation
        languages = metadata.get('languages', [])
        if languages:
            self.settingsDict['LanguageCode'] = languages[0].get('tag', languages[0].get('bcp47'))
        # Keep arbitrary future fields, nested arrays, false and zero verbatim in
        # suppliedMetadata, rather than flattening them into a lossy string map.

    def _loadBookMP(self, BBB_Filename_duple):
        BBB, _ = BBB_Filename_duple
        name, parserType = self._bookSources[BBB]
        data = _Bundle(self.sourceFilepath, self.burritoPath).read(name)
        if self.verifyIntegrity:
            _verify_ingredient(name, data, self.suppliedMetadata['SB']['ingredients'][name])
        for code, _, bookData in _text_books(data, self.ingredientFormats[BBB]):
            if bos_books_codes_py.usfm_abbrev_to_bos_book_code(code) == BBB:
                # USX's existing loader assumes the filename contains its book
                # code. Give it a private canonical filename, never alter input.
                with tempfile.TemporaryDirectory(prefix='bos-sb-book-') as temporary:
                    filename = f'{code}.{ "usfm" if parserType == "USFM" else "usx"}'
                    (Path(temporary)/filename).write_bytes(bookData)
                    bookClass = USFMBibleBook if parserType == 'USFM' else USXXMLBibleBook
                    book = bookClass(self, BBB)
                    book.load(filename, temporary, 'utf-8')
                    book.validateMarkers()
                return book
        raise ValueError(f'Ingredient {name} no longer contains {BBB}')

    def loadBook(self, BBB, filename=None):
        if not self.preloadDone: self.preload()
        if BBB in self.books and not self.bookNeedsReloading.get(BBB): return
        if BBB not in self._bookSources: raise KeyError(f'No Scripture Burrito ingredient for {BBB}')
        if filename is not None and filename != self.possibleFilenameDict[BBB]:
            raise ValueError('Filename must match the metadata ingredient')
        book = self._loadBookMP((BBB, filename))
        self.stashBook(book)
        self.triedLoadingBook[BBB] = True
        self.bookNeedsReloading[BBB] = False

    def loadBooks(self):
        if not self.preloadDone: self.preload()
        if not self._bookSources:
            raise ValueError('This Scripture Burrito contains no supported USFM, USX or USJ Bible text')
        # Use our per-ingredient dispatcher, not the USFM/USX container loaders:
        # those expect different container attributes and multiprocessing APIs.
        for BBB in self.givenBookList:
            self.loadBook(BBB)
        self.doPostLoadProcessing()

    def load(self):
        self.loadBooks()


def _verify_ingredient(name, data, descriptor):
    if 'size' in descriptor and descriptor['size'] != len(data):
        raise ValueError(f'Ingredient size mismatch: {name}')
    checksums = descriptor.get('checksum', {})
    if isinstance(checksums, str): checksums = {'md5': checksums} # 0.1
    for algorithm, expected in checksums.items():
        try: actual = hashlib.new(algorithm.replace('-', '_'), data).hexdigest()
        except ValueError:
            logging.warning('Unsupported checksum algorithm %s for %s', algorithm, name)
            continue
        if actual != expected:
            raise ValueError(f'Ingredient {algorithm} checksum mismatch: {name}')


def _publication_scope(data, kind):
    """Describe observed verse numbers, never claim unwritten chapters/books.

    SB 1.0 cannot express verse zero or verse suffixes: retain those bytes, and
    describe their chapter as a whole (the narrowest available selector).
    """
    if kind == 'USFM':
        markers = re.findall(r'\\(c|v)\s+([^\s\\]+)', data.decode('utf-8-sig'))
    else:
        markers = [('c' if e.tag == 'chapter' else 'v', e.get('number'))
                   for e in _xml_root(data).iter() if e.tag in ('chapter', 'verse') and 'number' in e.attrib]
    chapters, chapter = {}, None
    for marker, number in markers:
        if marker == 'c':
            if not re.fullmatch(r'[1-9][0-9]*', number):
                raise ValueError(f'Cannot express chapter {number!r} in SB scope')
            chapter = number
            chapters.setdefault(chapter, set())
        elif chapter is None:
            raise ValueError('Verse appears before chapter in publication file')
        elif re.fullmatch(r'[1-9][0-9]*(?:-[1-9][0-9]*)?', number):
            first, _, last = number.partition('-')
            if last and (int(last) < int(first) or int(last)-int(first) > 10000):
                raise ValueError(f'Invalid verse range {number}')
            if chapters[chapter] is not None:
                chapters[chapter].update(range(int(first), int(last or first)+1))
        else:
            logging.warning('SB 1.0 scope cannot express verse %s:%s; using chapter scope', chapter, number)
            chapters[chapter] = None
    selectors = []
    for chapter, verses in chapters.items():
        if not verses:
            selectors.append(chapter)
            continue
        numbers = sorted(verses)
        start = end = numbers[0]
        for number in numbers[1:] + [None]:
            if number is not None and number == end + 1:
                end = number
            else:
                selectors.append(f'{chapter}:{start}' + (f'-{end}' if end != start else ''))
                start = end = number
    return selectors


def _validate_export_metadata(metadata):
    """Required publication decisions and common errors, without dependencies.

    This is not a replacement for upstream JSON Schema validation.
    """
    for field in ('idAuthorities', 'identification', 'languages', 'copyright', 'confidential', 'type'):
        if field not in metadata:
            raise ValueError(f'Scripture Burrito export metadata requires {field!r}')
    for field in ('idAuthorities', 'identification', 'copyright', 'type'):
        if not isinstance(metadata[field], dict):
            raise ValueError(f'{field} must be an object')
    if not isinstance(metadata['confidential'], bool):
        raise ValueError('confidential must be a boolean')
    def localized(value):
        return isinstance(value, dict) and bool(value) and all(isinstance(v, str) and v for v in value.values())
    identification = metadata['identification']
    if not localized(identification.get('name')):
        raise ValueError('identification.name must be a nonempty locale map')
    primary = identification.get('primary', {})
    if not isinstance(primary, dict) or len(primary) != 1:
        raise ValueError('identification.primary needs one authority and a stable project ID')
    authority, identifiers = next(iter(primary.items()))
    if authority not in metadata['idAuthorities'] or not metadata['idAuthorities'][authority].get('id'):
        raise ValueError('The primary authority must be declared in idAuthorities')
    if not identifiers or not isinstance(identifiers, dict):
        raise ValueError('identification.primary must contain a stable project ID')
    for details in identifiers.values():
        if not isinstance(details, dict) or not isinstance(details.get('revision'), str) or not details['revision']:
            raise ValueError('Each primary ID requires a nonempty revision string')
        if not details.get('timestamp'):
            raise ValueError('Each primary ID requires a timestamp')
        try:
            datetime.fromisoformat(details['timestamp'].replace('Z', '+00:00'))
        except (ValueError, TypeError, AttributeError) as error:
            raise ValueError('Primary timestamps must be ISO 8601 dates/datetimes') from error
    if not isinstance(metadata['languages'], list) or not metadata['languages']:
        raise ValueError('languages requires at least one language')
    for language in metadata['languages']:
        if not language.get('tag') or not localized(language.get('name')):
            raise ValueError('Each language needs a BCP-47 tag and localized name')
    copyright = metadata['copyright']
    alternatives = int(copyright.get('publicDomain') is True) + int('licenses' in copyright) + int('shortStatements' in copyright)
    if alternatives != 1:
        raise ValueError('The SB 1.0 copyright schema requires exactly one of publicDomain=true, licenses or shortStatements')
    for license in copyright.get('licenses', []):
        if not isinstance(license, dict) or len(set(license) & {'url', 'ingredient'}) != 1:
            raise ValueError('Each copyright license needs exactly one url or ingredient')
    for agency in metadata.get('agencies', []):
        if not agency.get('id') or not localized(agency.get('name')) or not agency.get('roles'):
            raise ValueError('Each agency needs id, localized name and roles')
    if copyright.get('publicDomain') is not True and not any(
            'rightsHolder' in agency.get('roles', []) for agency in metadata.get('agencies', [])):
        raise ValueError('A copyrighted translation needs an agency with the rightsHolder role')
    flavorType = metadata['type'].get('flavorType', {})
    flavor = flavorType.get('flavor', {})
    if flavorType.get('name') != 'scripture' or flavor.get('name') != 'textTranslation':
        raise ValueError('The writer exports scripture/textTranslation burritos')
    enums = {
        'projectType': ('standard', 'daughter', 'studyBible', 'studyBibleAdditions', 'backTranslation', 'auxiliary', 'transliterationManual', 'transliterationWithEncoder'),
        'translationType': ('firstTranslation', 'newTranslation', 'revision', 'studyOrHelpMaterial'),
        'audience': ('basic', 'common', 'common-literary', 'literary', 'liturgical', 'children')}
    for field, values in enums.items():
        if flavor.get(field) not in values:
            raise ValueError(f'type.flavorType.flavor.{field} must be one of {values}')


def createScriptureBurritoBible(bibleObject, outputFolderpath=None, metadataDict=None, *,
        sourceFiles=None, extraIngredients=None, filename=None, validationSchema=None, schemaVersion=None):
    """Write a complete ZIP and return its Path; replace an old ZIP only on success.

    ``metadataDict`` is a native SB metadata template (or a JSON filename).
    It must explicitly describe identity, revision, language, rights, confidentiality
    and translation type. Generated fields (format, version, date, generator,
    currentScope, ingredients) are computed from the actual output.

    Normally the Bible's USFM3 exporter supplies the text. ``sourceFiles`` maps
    BOS book codes to existing USFM/USX/USJ paths to preserve publication bytes,
    e.g. OET's cleaned USFM. It must match the loaded Bible's books exactly.
    ``extraIngredients`` maps archive paths to descriptors containing a local
    ``source`` path plus mimeType and optional role/lang/scope. Metadata license
    references can point at these files. No surrounding folder enters the ZIP.
    ``validationSchema`` optionally names a local upstream metadata.schema.json;
    it requires jsonschema and resolves references locally, never via the network.
    ``schemaVersion`` selects 1.0.0 (default) or 1.0.0-rc2; otherwise a version
    explicitly set in the template is respected.
    """
    if not bibleObject.books:
        raise ValueError('Load Bible books before exporting Scripture Burrito')
    if isinstance(metadataDict, (str, Path)):
        metadataDict = json.loads(Path(metadataDict).read_text(encoding='utf-8-sig'))
    if not isinstance(metadataDict, dict):
        raise ValueError('Supply a Scripture Burrito metadata dictionary or JSON template path')
    metadata = copy.deepcopy(metadataDict)
    meta = metadata.setdefault('meta', {})
    if meta.get('category', 'source') != 'source':
        raise ValueError('The writer currently exports source burritos; derived burritos need a recipe')
    requestedVersion = schemaVersion or meta.get('version', WRITE_SCHEMA_VERSION)
    if requestedVersion not in WRITE_SCHEMA_VERSIONS:
        raise ValueError(f'Writer supports {WRITE_SCHEMA_VERSIONS}; cannot claim {requestedVersion} conformance')
    timestamp = datetime.now(timezone.utc).isoformat(timespec='seconds')
    metadata['format'] = 'scripture burrito'
    meta.update(version=requestedVersion, category='source', dateCreated=timestamp,
                generator={'softwareName': 'BibleOrgSys ScriptureBurrito', 'softwareVersion': PROGRAM_VERSION})
    if not meta.get('defaultLocale'):
        raise ValueError('Supply meta.defaultLocale (the language of the metadata)')
    _validate_export_metadata(metadata)
    locale = meta['defaultLocale']
    abbreviation = metadata['identification'].get('abbreviation', {})
    defaultName = abbreviation.get(locale) or next(iter(abbreviation.values()), None) or 'ScriptureBurrito'
    filename = filename or f'{BibleOrgSysGlobals.makeSafeFilename(defaultName)}.zip'
    if _safe_relative_path(filename).name != filename or not filename.lower().endswith('.zip'):
        raise ValueError('filename must be a simple .zip filename')
    outputFolder = Path(outputFolderpath or BibleOrgSysGlobals.DEFAULT_WRITEABLE_OUTPUT_FOLDERPATH/'BOS_ScriptureBurrito_Export')
    outputFolder.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.bos-sb-', dir=outputFolder) as temporary:
        work = Path(temporary)
        if sourceFiles is None:
            exportFolder = work/'usfm'
            if not bibleObject.toUSFM3(exportFolder):
                raise ValueError('USFM3 export failed')
            sourceFiles = {}
            for path in sorted(exportFolder.glob('*.usfm')):
                books = _text_books(path.read_bytes(), 'USFM')
                if len(books) != 1: raise ValueError(f'Expected one exported book in {path}')
                BBB = bos_books_codes_py.usfm_abbrev_to_bos_book_code(books[0][0])
                if BBB in sourceFiles: raise ValueError(f'Duplicate USFM export for {BBB}')
                sourceFiles[BBB] = path
            metadata['type']['flavorType']['flavor']['usfmVersion'] = '3.0'
        if set(sourceFiles) != set(bibleObject.books):
            raise ValueError('sourceFiles must match the loaded Bible books exactly')
        version = metadata['type']['flavorType']['flavor'].get('usfmVersion')
        if not isinstance(version, str) or not re.fullmatch(r'\d+\.\d+(\..+)?', version):
            raise ValueError('Supply flavor.usfmVersion for the publication files')
        files, ingredients, scope = {}, {}, {}
        def add(name, data, descriptor):
            _safe_relative_path(name)
            if name in files or name in _METADATA_FILENAMES:
                raise ValueError(f'Duplicate/reserved ingredient path {name}')
            if not descriptor.get('mimeType'):
                raise ValueError(f'Ingredient {name} needs mimeType')
            files[name] = data
            ingredients[name] = dict(descriptor, size=len(data),
                checksum={'md5': hashlib.md5(data).hexdigest(), 'sha3-256': hashlib.sha3_256(data).hexdigest()})
        for BBB, source in sourceFiles.items():
            source = Path(source)
            kind = _ingredient_format(source.name, {})
            if kind not in ('USFM', 'USX', 'USJ'):
                raise ValueError(f'Unsupported publication file: {source}')
            # Published SB 1.0 does not yet define USJ text ingredients.
            if kind == 'USJ': raise ValueError('USJ export requires a newer SB schema; use USFM or USX for SB 1.0')
            data = source.read_bytes()
            books = _text_books(data, kind)
            if len(books) != 1 or bos_books_codes_py.usfm_abbrev_to_bos_book_code(books[0][0]) != BBB:
                raise ValueError(f'Publication file {source} does not contain exactly {BBB}')
            code = books[0][0]
            extension, mime = ('usfm', 'text/x-usfm') if kind == 'USFM' else ('usx', 'application/xml')
            descriptor = {'mimeType': mime}
            if code in _SCOPE_BOOK_CODES:
                selectors = _publication_scope(data, kind)
                if not selectors:
                    raise ValueError(f'No chapters in {source}; do not advertise an untranslated book')
                scope[code] = selectors
                descriptor['scope'] = {code: selectors}
            elif code in _PERIPHERAL_ROLES:
                descriptor['role'] = _PERIPHERAL_ROLES[code]
            else:
                raise ValueError(f'Book code {code} is not supported by the SB 1.0 scope schema')
            add(f'ingredients/{code}.{extension}', data, descriptor)
        for name, descriptor in (extraIngredients or {}).items():
            descriptor = dict(descriptor)
            source = descriptor.pop('source')
            descriptor.pop('size', None)
            descriptor.pop('checksum', None)
            if _ingredient_format(name, descriptor):
                raise ValueError('Supply Bible text via sourceFiles, not extraIngredients')
            add(name, Path(source).read_bytes(), descriptor)
        metadata['ingredients'] = ingredients
        if not scope: raise ValueError('A textTranslation burrito needs at least one Scripture book')
        metadata['type']['flavorType']['currentScope'] = scope
        for license in metadata['copyright'].get('licenses', []):
            if 'ingredient' in license and license['ingredient'] not in ingredients:
                raise ValueError(f'Missing license ingredient: {license["ingredient"]}')
        if 'normalization' in meta:
            import unicodedata
            form = meta['normalization']
            if form not in ('NFC', 'NFD'): raise ValueError('normalization must be NFC or NFD')
            for name, data in files.items():
                if ingredients[name]['mimeType'] in ('text/x-usfm', 'application/xml'):
                    if not unicodedata.is_normalized(form, data.decode('utf-8-sig')):
                        raise ValueError(f'{name} does not use the declared {form} normalization')
        if validationSchema is not None:
            _validate_schema(metadata, validationSchema)
        archivePath = work/filename
        with zipfile.ZipFile(archivePath, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('metadata.json', json.dumps(metadata, ensure_ascii=False, indent=2) + '\n')
            for name, data in files.items(): archive.writestr(name, data)
        destination = outputFolder/filename
        os.replace(archivePath, destination)
    return destination


def _validate_schema(metadata, schemaPath):
    """Resolve the upstream split schema entirely offline."""
    try:
        import jsonschema
        from referencing import Registry, Resource
    except ImportError as error:
        raise ImportError('Install jsonschema to use validationSchema') from error
    schemaPath = Path(schemaPath).resolve()
    schema = json.loads(schemaPath.read_text(encoding='utf-8'))
    # Resolve on demand: upstream checkouts can contain unrelated experimental
    # schemas which are not valid JSON and are not referenced by metadata.
    def retrieve(uri):
        prefixes = ('https://burrito.bible/schema/', schemaPath.parent.as_uri() + '/')
        prefix = next((prefix for prefix in prefixes if uri.startswith(prefix)), None)
        if prefix is None:
            raise ValueError(f'Schema reference is not local: {uri}')
        path = (schemaPath.parent / _safe_relative_path(uri[len(prefix):])).resolve()
        if not path.is_relative_to(schemaPath.parent):
            raise ValueError(f'Schema reference escapes schema folder: {uri}')
        return Resource.from_contents(json.loads(path.read_text(encoding='utf-8')))
    registry = Registry(retrieve=retrieve)
    validator = jsonschema.validators.validator_for(schema)
    validator(schema, registry=registry, format_checker=jsonschema.FormatChecker()).validate(metadata)


def __processScriptureBurritoBible( parametersTuple ): # for demo
    """
    Special shim function used below for multiprocessing.
    """
    codeLetter, mainFolderName, subFolderName = parametersTuple
    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 2:
        vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nSB {codeLetter} Trying {subFolderName}" )
    SB_Bible = ScriptureBurritoBible( mainFolderName, subFolderName )
    SB_Bible.load()
    if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE: # Print the index of a small book
        BBB = 'JN1'
        if BBB in SB_Bible:
            SB_Bible.books[BBB].debugPrint()
            for entryKey in SB_Bible.books[BBB]._CVIndex:
                vPrint( 'Quiet', DEBUGGING_THIS_MODULE, BBB, entryKey, SB_Bible.books[BBB]._CVIndex.getVerseEntries( entryKey ) )
# end of __processScriptureBurritoBible


def briefDemo() -> None:
    """
    Demonstrate reading and checking some Bible databases.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    testFolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'SBTest/' )


    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        result1 = ScriptureBurritoBibleFileCheck( testFolder )
        if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 2:
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, "SB TestA1", result1 )
        result2 = ScriptureBurritoBibleFileCheck( testFolder, autoLoad=True )
        if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 2:
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, "SB TestA2", result2 )
        result3 = ScriptureBurritoBibleFileCheck( testFolder, autoLoadBooks=True )
        if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 2:
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, "SB TestA3", result3 )


    BiblesFolderpath = Path( '/srv/Bibles/' )
    if 1: # Open access Bibles from SB
        sampleFolder = BiblesFolderpath.joinpath( 'Scripture Burrito Bibles/' )
        foundFolders, foundFiles = [], []
        for something in os.listdir( sampleFolder ):
            somepath = os.path.join( sampleFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something ); break
            elif os.path.isfile( somepath ): foundFiles.append( something )

        if 0 and BibleOrgSysGlobals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
            #dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nTrying all {len(foundFolders)} discovered modules…" )
            if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 2:
                vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Loading {len(foundFolders)} SB modules using {BibleOrgSysGlobals.maxProcesses} processes…" )
            if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 2:
                vPrint( 'Normal', DEBUGGING_THIS_MODULE, "  NOTE: Outputs (including error and warning messages) from loading various modules may be interspersed." )
            parameters = [('F'+str(j+1),os.path.join(sampleFolder, folderName+'/'),folderName) \
                                                for j,folderName in enumerate(sorted(foundFolders))]
            BibleOrgSysGlobals.alreadyMultiprocessing = True
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.map( __processScriptureBurritoBible, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            for j, folderName in enumerate( sorted( foundFolders ) ):
                if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 2:
                    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nSB F{j+1}/ Trying '{folderName}/'…" )
                myTestFolder = os.path.join( sampleFolder, folderName+'/' )
                SB_Bible = ScriptureBurritoBible( myTestFolder, folderName )
                SB_Bible.load()
                if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE: # Print the index of a small book
                    BBB = 'JN1'
                    if BBB in SB_Bible:
                        SB_Bible.books[BBB].debugPrint()
                        for entryKey in SB_Bible.books[BBB]._CVIndex:
                            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, BBB, entryKey, SB_Bible.books[BBB]._CVIndex.getVerseEntries( entryKey ) )


    if 0: # Older versions of bundles from Haiola
        sampleFolder = BiblesFolderpath.joinpath( 'Scripture Burrito Bibles/sb_textTranslation/' )
        foundFolders, foundFiles = [], []
        for something in os.listdir( sampleFolder ):
            somepath = os.path.join( sampleFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something ); break
            elif os.path.isfile( somepath ): foundFiles.append( something )

        if BibleOrgSysGlobals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
            #dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nTrying all {len(foundFolders)} discovered modules…" )
            if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 2:
                vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Loading {len(foundFolders)} SB modules using {BibleOrgSysGlobals.maxProcesses} processes…" )
            if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 2:
                vPrint( 'Normal', DEBUGGING_THIS_MODULE, "  NOTE: Outputs (including error and warning messages) from loading various modules may be interspersed." )
            parameters = [('G'+str(j+1),os.path.join(sampleFolder, folderName+'/'),folderName) \
                                                for j,folderName in enumerate(sorted(foundFolders))]
            BibleOrgSysGlobals.alreadyMultiprocessing = True
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.map( __processScriptureBurritoBible, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            for j, folderName in enumerate( sorted( foundFolders ) ):
                if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 2:
                    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nSB G{j+1}/ Trying '{folderName}/'…" )
                myTestFolder = os.path.join( sampleFolder, folderName+'/' )
                SB_Bible = ScriptureBurritoBible( myTestFolder, folderName )
                SB_Bible.load()
                if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE: # Print the index of a small book
                    BBB = 'JN1'
                    if BBB in SB_Bible:
                        SB_Bible.books[BBB].debugPrint()
                        for entryKey in SB_Bible.books[BBB]._CVIndex:
                            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, BBB, entryKey, SB_Bible.books[BBB]._CVIndex.getVerseEntries( entryKey ) )


    if 0: # all discovered modules in the test folder
        foundFolders, foundFiles = [], []
        for something in os.listdir( testFolder ):
            somepath = os.path.join( testFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something ); break
            elif os.path.isfile( somepath ): foundFiles.append( something )

        if BibleOrgSysGlobals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
            #dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nTrying all {len(foundFolders)} discovered modules…" )
            if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 2:
                vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Loading {len(foundFolders)} SB modules using {BibleOrgSysGlobals.maxProcesses} processes…" )
            if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 2:
                vPrint( 'Normal', DEBUGGING_THIS_MODULE, "  NOTE: Outputs (including error and warning messages) from loading various modules may be interspersed." )
            parameters = [('H'+str(j+1),os.path.join(testFolder, folderName+'/'),folderName) \
                                                for j,folderName in enumerate(sorted(foundFolders))]
            BibleOrgSysGlobals.alreadyMultiprocessing = True
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.map( __processScriptureBurritoBible, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            for j, folderName in enumerate( sorted( foundFolders ) ):
                if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 2:
                    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nSB H{j+1}/ Trying '{folderName}/'…" )
                myTestFolder = os.path.join( testFolder, folderName+'/' )
                SB_Bible = ScriptureBurritoBible( myTestFolder, folderName )
                SB_Bible.load()
                if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE: # Print the index of a small book
                    BBB = 'JN1'
                    if BBB in SB_Bible:
                        SB_Bible.books[BBB].debugPrint()
                        for entryKey in SB_Bible.books[BBB]._CVIndex:
                            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, BBB, entryKey, SB_Bible.books[BBB]._CVIndex.getVerseEntries( entryKey ) )

    if 00:
        testFolders = (
                    BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'SBTest/'),
                    ) # You can put your SB test folder here

        for testFolder in testFolders:
            if os.access( testFolder, os.R_OK ):
                DB = ScriptureBurritoBible( testFolder )
                DB.loadSBMetadata()
                DB.preload()
                if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 1:
                    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, DB )
                if BibleOrgSysGlobals.strictCheckingFlag: DB.check()
                DB.loadBooks()
                #DBErrors = DB.getCheckResults()
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, DBErrors )
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, DB.getVersification() )
                #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, DB.getAddedUnits() )
                #for ref in ('GEN','Genesis','GeNeSiS','Gen','MrK','mt','Prv','Xyz',):
                    ##dPrint( 'Quiet', DEBUGGING_THIS_MODULE, "Looking for", ref )
                    #dPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Tried finding '{ref}' in '{name}': got '{UB.getXRefBBB( ref )}'" )
            else: vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"Sorry, test folder '{testFolder}' is not readable on this computer." )

    #if BibleOrgSysGlobals.commandLineArguments.export:
    #    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"NOTE: This is {PROGRAM_NAME} V{PROGRAM_VERSION} -- i.e., not even alpha quality software!" )
    #       pass
# end of ScriptureBurritoBible.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    testFolder = BibleOrgSysGlobals.BOS_TEST_DATA_FOLDERPATH.joinpath( 'SBTest/' )


    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        result1 = ScriptureBurritoBibleFileCheck( testFolder )
        if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 2:
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, "SB TestA1", result1 )
        result2 = ScriptureBurritoBibleFileCheck( testFolder, autoLoad=True )
        if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 2:
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, "SB TestA2", result2 )
        result3 = ScriptureBurritoBibleFileCheck( testFolder, autoLoadBooks=True )
        if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 2:
            vPrint( 'Normal', DEBUGGING_THIS_MODULE, "SB TestA3", result3 )

    BiblesFolderpath = Path( '/srv/Bibles/' )
    if 1: # Open access Bibles from SB
        sampleFolder = BiblesFolderpath.joinpath( 'Scripture Burrito Bibles/' )
        foundFolders, foundFiles = [], []
        for something in os.listdir( sampleFolder ):
            somepath = os.path.join( sampleFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )

        if 0 and BibleOrgSysGlobals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
            #dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nTrying all {len(foundFolders)} discovered modules…" )
            if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 2:
                vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Loading {len(foundFolders)} SB modules using {BibleOrgSysGlobals.maxProcesses} processes…" )
            if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 2:
                vPrint( 'Normal', DEBUGGING_THIS_MODULE, "  NOTE: Outputs (including error and warning messages) from loading various modules may be interspersed." )
            parameters = [('F'+str(j+1),os.path.join(sampleFolder, folderName+'/'),folderName) \
                                                for j,folderName in enumerate(sorted(foundFolders))]
            BibleOrgSysGlobals.alreadyMultiprocessing = True
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.map( __processScriptureBurritoBible, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            for j, folderName in enumerate( sorted( foundFolders ) ):
                if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 2:
                    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nSB F{j+1}/ Trying '{folderName}/'…" )
                myTestFolder = os.path.join( sampleFolder, folderName+'/' )
                SB_Bible = ScriptureBurritoBible( myTestFolder, folderName )
                SB_Bible.load()
                if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE: # Print the index of a small book
                    BBB = 'JN1'
                    if BBB in SB_Bible:
                        SB_Bible.books[BBB].debugPrint()
                        for entryKey in SB_Bible.books[BBB]._CVIndex:
                            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, BBB, entryKey, SB_Bible.books[BBB]._CVIndex.getVerseEntries( entryKey ) )


    if 0: # Older versions of bundles from Haiola
        sampleFolder = BiblesFolderpath.joinpath( 'SB Bibles/Haiola SB test versions/' )
        foundFolders, foundFiles = [], []
        for something in os.listdir( sampleFolder ):
            somepath = os.path.join( sampleFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )

        if BibleOrgSysGlobals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
            #dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nTrying all {len(foundFolders)} discovered modules…" )
            if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 2:
                vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Loading {len(foundFolders)} SB modules using {BibleOrgSysGlobals.maxProcesses} processes…" )
            if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 2:
                vPrint( 'Normal', DEBUGGING_THIS_MODULE, "  NOTE: Outputs (including error and warning messages) from loading various modules may be interspersed." )
            parameters = [('G'+str(j+1),os.path.join(sampleFolder, folderName+'/'),folderName) \
                                                for j,folderName in enumerate(sorted(foundFolders))]
            BibleOrgSysGlobals.alreadyMultiprocessing = True
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.map( __processScriptureBurritoBible, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            for j, folderName in enumerate( sorted( foundFolders ) ):
                if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 2:
                    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nSB G{j+1}/ Trying '{folderName}/'…" )
                myTestFolder = os.path.join( sampleFolder, folderName+'/' )
                SB_Bible = ScriptureBurritoBible( myTestFolder, folderName )
                SB_Bible.load()
                if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE: # Print the index of a small book
                    BBB = 'JN1'
                    if BBB in SB_Bible:
                        SB_Bible.books[BBB].debugPrint()
                        for entryKey in SB_Bible.books[BBB]._CVIndex:
                            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, BBB, entryKey, SB_Bible.books[BBB]._CVIndex.getVerseEntries( entryKey ) )


    if 0: # all discovered modules in the test folder
        foundFolders, foundFiles = [], []
        for something in os.listdir( testFolder ):
            somepath = os.path.join( testFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )

        if BibleOrgSysGlobals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
            #dPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nTrying all {len(foundFolders)} discovered modules…" )
            if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 2:
                vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"Loading {len(foundFolders)} SB modules using {BibleOrgSysGlobals.maxProcesses} processes…" )
            if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 2:
                vPrint( 'Normal', DEBUGGING_THIS_MODULE, "  NOTE: Outputs (including error and warning messages) from loading various modules may be interspersed." )
            parameters = [('H'+str(j+1),os.path.join(testFolder, folderName+'/'),folderName) \
                                                for j,folderName in enumerate(sorted(foundFolders))]
            BibleOrgSysGlobals.alreadyMultiprocessing = True
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.map( __processScriptureBurritoBible, parameters ) # have the pool do our loads
                assert len(results) == len(parameters) # Results (all None) are actually irrelevant to us here
            BibleOrgSysGlobals.alreadyMultiprocessing = False
        else: # Just single threaded
            for j, folderName in enumerate( sorted( foundFolders ) ):
                if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.verbosityLevel >= 2:
                    vPrint( 'Normal', DEBUGGING_THIS_MODULE, f"\nSB H{j+1}/ Trying '{folderName}/'…" )
                myTestFolder = os.path.join( testFolder, folderName+'/' )
                SB_Bible = ScriptureBurritoBible( myTestFolder, folderName )
                SB_Bible.load()
                if BibleOrgSysGlobals.debugFlag and DEBUGGING_THIS_MODULE: # Print the index of a small book
                    BBB = 'JN1'
                    if BBB in SB_Bible:
                        SB_Bible.books[BBB].debugPrint()
                        for entryKey in SB_Bible.books[BBB]._CVIndex:
                            vPrint( 'Quiet', DEBUGGING_THIS_MODULE, BBB, entryKey, SB_Bible.books[BBB]._CVIndex.getVerseEntries( entryKey ) )

    #if BibleOrgSysGlobals.commandLineArguments.export:
    #    vPrint( 'Quiet', DEBUGGING_THIS_MODULE, f"NOTE: This is {PROGRAM_NAME} V{PROGRAM_VERSION} -- i.e., not even alpha quality software!" )
    #       pass
# end of ScriptureBurritoBible.fullDemo

if __name__ == '__main__':
    from multiprocessing import set_start_method, freeze_support
    set_start_method('fork') # The default was changed on POSIX systems from 'fork' to 'forkserver' in Python3.14
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of ScriptureBurritoBible.py
