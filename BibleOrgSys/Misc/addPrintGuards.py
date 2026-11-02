#!/usr/bin/env -S uv run
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MPL-2.0
#
# addPrintGuards.py
#
# One-shot maintenance codemod: wrap bare vPrint/dPrint/fnPrint statements
#   in exact-condition `if` guards so that message f-strings are only built
#   when the message can actually be printed.
#
# Copyright (C) 2026 Robert Hunt
# Author: Robert Hunt <Freely.Given.org+BOS@gmail.com>
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Wrap bare vPrint/dPrint/fnPrint statements in exact-condition guards.

Background: Python evaluates call arguments eagerly, so
    dPrint( 'Info', DEBUGGING_THIS_MODULE, f'{expensive!r}' )
builds the f-string even when nothing will be printed. Wrapping the call as
    if (DEBUGGING_THIS_MODULE) or BibleOrgSysGlobals.debugFlag \
    or BibleOrgSysGlobals.verbosityLevel >= 3:
        dPrint( 'Info', DEBUGGING_THIS_MODULE, f'{expensive!r}' )
reduces the disabled cost to a couple of name lookups (~50x cheaper).

The guard conditions replicate the exact print decisions of the functions
    (BibleOrgSysGlobals.vPrint/dPrint/fnPrint) so console output is unchanged
    in every mode (normal, quiet, verbose, --debug, and DEBUGGING_THIS_MODULE
    set to any truthy integer, e.g., 99 to activate 'Never' lines):
        dPrint( L, INC, ... ) -> if (INC) or debugFlag or verbosityLevel >= N
        vPrint( L, INC, ... ) -> if (INC) or verbosityLevel >= N
        fnPrint( INC, ... )   -> if (INC) or debugFlag
    where N is the numeric value of the (literal) level L from LEVEL_NAME_DICT.
    (When INC is truthy the guard always defers to the function itself,
    so integer increaseLevels and expressions keep their exact semantics.)

Call sites already sitting under a debug/verbosity flavoured `if` are left
untouched, as are calls with non-literal levels, calls sharing a line with
other code, and calls containing multi-line string literals (all reported).

Also updates the LAST_MODIFIED_DATE line in each changed file.

Usage:
    addPrintGuards.py [--write] [--update-mod-dates] [--verbose] [paths...]

Default is a DRY RUN (reports only); pass --write to apply changes.
Default path is the BibleOrgSys package folder of this repo.
"""

import sys
import os
import ast
import io
import re
import tokenize
from pathlib import Path


LAST_MODIFIED_DATE = '2026-10-06' # by RJH
SHORT_PROGRAM_NAME = "addPrintGuards"
PROGRAM_NAME = "Add print guards codemod"
PROGRAM_VERSION = '0.90'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'


# Must match BibleOrgSysGlobals.LEVEL_NAME_DICT
LEVEL_NAME_DICT = { 'Quiet':1, 'Q':1,
                    'Normal':2, 'N':2,
                    'Informative':3, 'Info':3, 'I':3,
                    'Verbose':4, 'V':4,
                    'Never': 5,
                    }

PRINT_FUNCTION_NAMES = ( 'vPrint', 'dPrint', 'fnPrint' )

# If an ancestor `if` test mentions any of these, we consider the call site already guarded
ALREADY_GUARDED_REGEX = re.compile(
    r'debugFlag|verbosityLevel|DEBUGGING|[dD]ebugging|forceDebug|[pP]rintFlag|printProcessingMessages' )

EXCLUDED_FOLDER_NAMES = { '.git', '.hg', '.svn', '__pycache__', '.venv', 'venv',
                          'target', 'node_modules', 'snap', '.idea', '.antigravitycli' }

def isExcludedFolderName( folderName:str ) -> bool:
    """
    Exclude version-control, cache, build, and virtual-environment folders
        (including ad-hoc venv names like 'venv314').
    """
    return folderName in EXCLUDED_FOLDER_NAMES or 'venv' in folderName.lower()
# end of isExcludedFolderName

LAST_MODIFIED_DATE_LINE_REGEX = re.compile( r"^(LAST_MODIFIED_DATE = ')\d{4}-\d{2}-\d{2}('.*)$", re.MULTILINE )


def findMultilineStringTokenSpans( source:str ) -> list[tuple[int,int]]:
    """
    Return the (startLine, endLine) spans of string tokens that span multiple
        physical lines (triple-quoted strings/f-strings, backslash-continued strings).

    These are DANGEROUS to reindent (interior lines are string content).
    NOTE: Implicitly-concatenated single-line strings/f-strings across lines are
        SAFE (each physical line's string is self-contained) and not included,
        even though Python 3.12+ merges them into one multi-line AST node.
    """
    fstringMiddleType = getattr( tokenize, 'FSTRING_MIDDLE', None )
    spans = []
    try:
        for token in tokenize.generate_tokens( io.StringIO( source ).readline ):
            if ( token.type == tokenize.STRING or token.type == fstringMiddleType ) \
            and token.start[0] != token.end[0]:
                spans.append( (token.start[0], token.end[0]) )
    except (tokenize.TokenError, IndentationError):
        pass # fall back to wrapping nothing? No: simply no spans detected (parse would have failed already)
    return spans
# end of findMultilineStringTokenSpans


class FileResult:
    """Statistics and the new source text for one processed file."""
    def __init__( self, filepath:Path ):
        self.filepath = filepath
        self.wrapped = 0
        self.alreadyGuarded = 0
        self.skipped:list[str] = []
        self.modDateUpdated = False
        self.newSource = None # None means unchanged
    # end of FileResult.__init__


def findModuleObjectName( tree, source:str, isGlobalsModule:bool ) -> str|None:
    """
    Return the name bound to the BibleOrgSysGlobals module object in this file
        (usually 'BibleOrgSysGlobals'), or None if it isn't bound.
    """
    for node in ast.walk( tree ):
        if isinstance( node, ast.Import ):
            for alias in node.names:
                if alias.name == 'BibleOrgSysGlobals' or alias.name.endswith( '.BibleOrgSysGlobals' ):
                    return alias.asname or alias.name.split( '.' )[0]
        elif isinstance( node, ast.ImportFrom ):
            for alias in node.names:
                if alias.name == 'BibleOrgSysGlobals':
                    return alias.asname or 'BibleOrgSysGlobals'
    # Fallback: attribute usage implies the name is somehow available
    if not isGlobalsModule and re.search( r'\bBibleOrgSysGlobals\.\w', source ):
        return 'BibleOrgSysGlobals'
    return None
# end of findModuleObjectName


def resolveLevelExpression( levelNode ) -> int|None:
    """
    Resolve a level argument expression to a single (minimum) integer level.

    Handles string literals (via LEVEL_NAME_DICT, defaulting to 4 like vPrint),
        integer literals, and ternaries ('Info' if cond else 'Verbose')
        where both branches resolve -- the MINIMUM is used
        (a message only prints if verbosity >= its actual level,
        and its actual level is always >= the minimum,
        so the guard never suppresses a message that would print).

    Returns None for anything else (caller skips that call site).
    """
    if isinstance( levelNode, ast.Constant ) and isinstance( levelNode.value, str ):
        return LEVEL_NAME_DICT.get( levelNode.value, 4 ) # KeyError defaults to verbose in vPrint
    if isinstance( levelNode, ast.Constant ) and isinstance( levelNode.value, int ):
        return levelNode.value
    if isinstance( levelNode, ast.IfExp ): # 'Info' if cond else 'Verbose'
        bodyLevel = resolveLevelExpression( levelNode.body )
        elseLevel = resolveLevelExpression( levelNode.orelse )
        if bodyLevel is not None and elseLevel is not None:
            return min( bodyLevel, elseLevel )
    return None
# end of resolveLevelExpression


def buildGuard( funcName:str, call, source:str ) -> str|None:
    """
    Build the exact-condition guard string for the given print call,
        or return None if this call must be skipped (non-literal level etc.).
    """
    if funcName == 'fnPrint':
        if not call.args: return None
        increaseSegment = ast.get_source_segment( source, call.args[0] )
        if increaseSegment is None: return None
        return f'({increaseSegment.strip()}) or {{DBG}}'

    # vPrint / dPrint need a resolvable level (arg 0) and an increase expression (arg 1)
    if len( call.args ) < 2: return None
    levelNum = resolveLevelExpression( call.args[0] )
    if levelNum is None:
        return None
    increaseSegment = ast.get_source_segment( source, call.args[1] )
    if increaseSegment is None: return None
    increaseExpr = increaseSegment.strip()
    if funcName == 'dPrint':
        return f'({increaseExpr}) or {{DBG}} or {{VERB}} >= {levelNum}'
    # vPrint
    return f'({increaseExpr}) or {{VERB}} >= {levelNum}'
# end of buildGuard


def processFile( filepath:Path, write:bool, updateModDates:bool, verbose:bool ) -> FileResult:
    """
    Process one Python file: wrap all unguarded bare print-call statements.
    """
    result = FileResult( filepath )
    isGlobalsModule = filepath.name == 'BibleOrgSysGlobals.py'
    try:
        source = filepath.read_text( encoding='utf-8' )
    except (OSError, UnicodeDecodeError) as err:
        result.skipped.append( f'unreadable: {err}' )
        return result
    try:
        tree = ast.parse( source )
    except SyntaxError as err:
        result.skipped.append( f'unparseable: {err.msg} at line {err.lineno}' )
        return result

    # Build a parent map
    parentOf = {}
    for node in ast.walk( tree ):
        for child in ast.iter_child_nodes( node ):
            parentOf[id(child)] = node

    # Multi-line string TOKEN spans (dangerous to reindent) for the whole file
    multilineStringSpans = findMultilineStringTokenSpans( source )

    def insideOwnDefinition( node ) -> bool:
        """Is this node inside the body of vPrint/dPrint/fnPrint themselves?"""
        while id(node) in parentOf:
            node = parentOf[id(node)]
            if isinstance( node, (ast.FunctionDef, ast.AsyncFunctionDef) ):
                return node.name in PRINT_FUNCTION_NAMES
        return False

    def alreadyGuardedCheck( node ) -> bool:
        """Does any ancestor `if` test look like a debug/verbosity guard?"""
        while id(node) in parentOf:
            node = parentOf[id(node)]
            if isinstance( node, ast.If ):
                testSource = ast.get_source_segment( source, node.test ) or ''
                if ALREADY_GUARDED_REGEX.search( testSource ):
                    return True
        return False

    # Collect candidate edits: list of (startLine, endLine, indentString, guardString)
    edits = []
    for node in ast.walk( tree ):
        if not ( isinstance( node, ast.Expr ) and isinstance( node.value, ast.Call ) ):
            continue
        func = node.value.func
        if not ( isinstance( func, ast.Name ) and func.id in PRINT_FUNCTION_NAMES ):
            continue
        call = node.value

        if insideOwnDefinition( node ):
            result.skipped.append( f'line {node.lineno}: inside a print-function definition' )
            continue
        if alreadyGuardedCheck( node ):
            result.alreadyGuarded += 1
            continue

        guard = buildGuard( func.id, call, source )
        if guard is None:
            result.skipped.append( f'line {node.lineno}: non-literal level or missing arguments' )
            continue

        # Must be a clean standalone statement: only whitespace before it on its first line
        sourceLines = source.splitlines( keepends=True )
        firstLine = sourceLines[node.lineno-1]
        if firstLine[:node.col_offset].strip():
            result.skipped.append( f'line {node.lineno}: shares a line with other code' )
            continue
        # No other statement may follow it on its final line (e.g., after a semicolon)
        tail = sourceLines[node.end_lineno-1][node.end_col_offset:].strip()
        if tail.startswith( ';' ):
            result.skipped.append( f'line {node.lineno}: semicolon after statement' )
            continue

        # Don't touch statements containing multi-line string TOKENS
        #   (reindenting their interior lines would change the string contents)
        if any( spanStart <= node.end_lineno and node.lineno <= spanEnd
                for spanStart, spanEnd in multilineStringSpans ):
            result.skipped.append( f'line {node.lineno}: contains a multi-line string literal' )
            continue

        indent = firstLine[:node.col_offset]
        indentUnit = '\t' if indent.startswith( '\t' ) else '    '
        edits.append( (node.lineno, node.end_lineno, indent, indentUnit, guard) )

    if not edits:
        return result

    # Work out the flag names for the guard conditions
    if isGlobalsModule:
        moduleObjectName = None # bare global names
    else:
        moduleObjectName = findModuleObjectName( tree, source, isGlobalsModule )
        if moduleObjectName is None:
            result.skipped.append( f'needs BibleOrgSysGlobals module-object import to wrap {len(edits)} calls -- add import first' )
            return result

    # Apply edits bottom-up so line numbers don't shift
    lines = source.splitlines( keepends=True )
    for startLine, endLine, indent, indentUnit, guard in sorted( edits, reverse=True ):
        if moduleObjectName is None:
            guardText = guard.replace( '{DBG}', 'debugFlag' ).replace( '{VERB}', 'verbosityLevel' )
        else:
            guardText = guard.replace( '{DBG}', f'{moduleObjectName}.debugFlag' ) \
                             .replace( '{VERB}', f'{moduleObjectName}.verbosityLevel' )
        guardLine = f'{indent}if {guardText}:\n'
        for ix in range( startLine-1, endLine ): # reindent the original statement
            if lines[ix].strip():
                lines[ix] = indentUnit + lines[ix]
        lines.insert( startLine-1, guardLine )
        result.wrapped += 1

    newSource = ''.join( lines )

    if updateModDates:
        newSource2, count = LAST_MODIFIED_DATE_LINE_REGEX.subn( rf'\g<1>{LAST_MODIFIED_DATE}\g<2>', newSource, count=1 )
        if count:
            newSource = newSource2
            result.modDateUpdated = True

    result.newSource = newSource
    if write:
        filepath.write_text( newSource, encoding='utf-8' )
    return result
# end of processFile


def main( argv ) -> int:
    """
    Parse the simple command line and process the requested paths.
    """
    write = '--write' in argv
    updateModDates = '--update-mod-dates' in argv
    verbose = '--verbose' in argv
    paths = [ a for a in argv if not a.startswith( '--' ) ]
    if not paths:
        paths = [ str( Path( __file__ ).resolve().parent.parent ) ] # The BibleOrgSys package folder

    pythonFilepaths = []
    for pathString in paths:
        path = Path( pathString )
        if path.is_file():
            pythonFilepaths.append( path )
        else:
            for dirpath, dirnames, filenames in os.walk( path ):
                dirnames[:] = [ d for d in dirnames if not isExcludedFolderName( d ) ]
                for filename in filenames:
                    if filename.endswith( '.py' ) and filename != Path( __file__ ).name:
                        pythonFilepaths.append( Path( dirpath ) / filename )

    grandWrapped = grandGuarded = grandSkipped = grandFilesChanged = 0
    for filepath in sorted( pythonFilepaths ):
        result = processFile( filepath, write, updateModDates, verbose )
        if verbose or result.wrapped or result.skipped:
            parts = []
            if result.wrapped: parts.append( f'{result.wrapped} wrapped' )
            if result.alreadyGuarded: parts.append( f'{result.alreadyGuarded} already guarded' )
            if result.modDateUpdated: parts.append( 'mod-date bumped' )
            if parts:
                print( f'{filepath}: {", ".join(parts)}' )
            for skipReason in result.skipped:
                print( f'  SKIPPED {filepath}:{skipReason}' )
        grandWrapped += result.wrapped
        grandGuarded += result.alreadyGuarded
        grandSkipped += len( result.skipped )
        if result.newSource is not None: grandFilesChanged += 1

    print( f"\n{'APPLIED' if write else 'DRY RUN'}: {grandWrapped} calls wrapped, "
           f'{grandGuarded} already guarded, {grandSkipped} skipped, '
           f"{grandFilesChanged} files {'would be ' if not write else ''}changed." )
    return 0
# end of main


if __name__ == '__main__':
    sys.exit( main( sys.argv[1:] ) )
# end of addPrintGuards.py
