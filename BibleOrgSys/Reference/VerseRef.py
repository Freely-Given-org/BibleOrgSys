# SPDX-License-Identifier: MPL-2.0
"""A named (BBB, C, V, S) verse reference.

VerseRef is a typing.NamedTuple, so it is still a tuple. It compares and hashes
equal to the plain four-tuple with the same values, unpacks as
``BBB, C, V, S = ref``, and still supports ``ref[0]``. Code that passes or
expects plain tuples keeps working, so callers can migrate one file at a time.
New code should use the field names instead of numeric indexes.

str(ref) gives a compact display form such as 'GEN 1:1' or 'PSA 9:22a';
repr(ref) gives the full VerseRef(BBB=..., C=..., V=..., S=...) form.
"""

from __future__ import annotations

from typing import NamedTuple

from BibleOrgSys.Reference.BookCode import BookCode


LAST_MODIFIED_DATE = '2026-11-04' # by Claude
SHORT_PROGRAM_NAME = "VerseRef"
PROGRAM_NAME = "Named verse reference type"
PROGRAM_VERSION = '1.0.0'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'


class VerseRef(NamedTuple):
    """A single verse address, optionally narrowed to a lettered segment.

    The versification mapping code normalises C and V to decimal strings
    (see BibleVersificationMappings.normalize_reference). This type itself does
    no validation, so it can also carry unnormalised values in transit.
    """
    BBB: BookCode         # BOS book code, e.g. 'GEN'
    C: str                # Chapter number, e.g. '1'
    V: str                # Verse number, e.g. '1' ('0' for a declared title)
    S: str | None = None  # Optional lowercase segment suffix, e.g. 'a'

    def whole_verse(self) -> VerseRef:
        """Return the same address without any segment suffix."""
        return self._replace(S=None) if self.S is not None else self

    def __str__(self) -> str:
        return f'{self.BBB} {self.C}:{self.V}{self.S or ""}'
