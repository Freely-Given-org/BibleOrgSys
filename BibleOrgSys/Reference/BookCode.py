# SPDX-License-Identifier: MPL-2.0
"""The BookCode type for BOS book codes (often called BBB).

A BOS book code is a three-character uppercase ASCII string such as 'GEN',
'MAT', '1SA' or 'PS2'. BOS code conventionally names these values BBB, so
this type is called BookCode to avoid confusion with all the BBB variables.

For now BookCode is a plain alias of str. Annotations using it document
intent, and type checkers such as ty treat it exactly like str, so no
existing code or literal like 'GEN' needs changing.

Once ty is in regular use, BookCode could become a distinct type:
    BookCode = NewType('BookCode', str)
ty would then reject a plain str wherever a BookCode is expected, until each
place that creates a book code (parsers, lookup tables, literals) returns or
wraps it as BookCode(...). makeBookCode() below is the natural checked entry
point for that.
"""

from __future__ import annotations

import re
import sys


LAST_MODIFIED_DATE = '2026-11-14' # by Claude
SHORT_PROGRAM_NAME = "BookCode"
PROGRAM_NAME = "BOS book code type"
PROGRAM_VERSION = '1.1.0'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'


type BookCode = str

BOOK_CODE_PATTERN = re.compile(r'[A-Z0-9]{3}')


def isBookCodeFormat( text:object ) -> bool:
    """True if text has the form of a BOS book code (three of A-Z or 0-9).

    This checks the form only, not that the code is a known book.
    """
    return isinstance(text, str) and BOOK_CODE_PATTERN.fullmatch(text) is not None


def makeBookCode( text:str ) -> BookCode:
    """Return text as a BookCode, raising ValueError if it has the wrong form."""
    if not isBookCodeFormat(text):
        raise ValueError(f"A BOS book code is three characters from A-Z or 0-9, not {text!r}")
    return sys.intern(text) # So that all the stored copies of this book code share the one string object


def internBookCodes( data:object ) -> object:
    """Make every book code in a (possibly nested) dict, list, or tuple share one string object.

    Book codes that come out of a JSON or pickle file, or that are sliced out of a line of text,
    are separate string objects (taking about 48 bytes each) even when they have the same value.
    This replaces each one (whether a dict key, a dict value, or a list or tuple item) with
    the interned copy, which then costs nothing beyond the reference to it.

    Dicts and lists are updated in place (dict key order is kept).
    Tuples can't be changed, so a new tuple is made if anything inside it changed.
    Returns the given object (or its replacement if it was a string or a tuple).
    """
    dataType = type( data )
    if dataType is str:
        return sys.intern(data) if len(data)==3 and BOOK_CODE_PATTERN.fullmatch(data) is not None else data
    if dataType is dict:
        newItems = [(internBookCodes(key) if type(key) in (str,tuple) else key, internBookCodes(value)) for key,value in data.items()]
        if any( newKey is not key or newValue is not value for (newKey,newValue),(key,value) in zip(newItems, data.items()) ):
            data.clear()
            data.update( newItems )
    elif dataType is list:
        for j,item in enumerate( data ):
            newItem = internBookCodes( item )
            if newItem is not item: data[j] = newItem
    elif dataType is tuple:
        newItems = [internBookCodes( item ) for item in data]
        if any( newItem is not item for newItem,item in zip(newItems, data) ):
            return tuple( newItems )
    return data
