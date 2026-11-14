# SPDX-FileCopyrightText: © 2026 Robert Hunt <Freely.Given.org+BOS@gmail.com>
# SPDX-License-Identifier: MPL-2.0
"""Complete passage retrieval in native or mapped versification.

Public Bible methods delegate here; this module has no application, renderer,
or navigation dependencies. Mapping results describe references, while portions
describe the text actually stored (including indivisible USFM verse bridges).

CHANGELOG:
    2026-10-31 Accept native verse-label ranges/lists before scalar validation.
    2026-11-04 Use named VerseRef fields instead of numeric tuple indexes.
"""
from dataclasses import dataclass, replace
from functools import lru_cache
import re
from typing import NamedTuple

from bible_organisational_system import InternalBibleEntryList
from BibleOrgSys.Reference.BibleVersification import BibleVersificationMixin, _system_name
from BibleOrgSys.Reference.BibleVersificationMappings import (
    MappingDiagnostic, MappingResult, MappingStatus, PartialMappingError, VersificationMappingError,
    get_default_mapping_engine, normalize_reference,
)
from BibleOrgSys.Reference.VerseRef import VerseRef
from BibleOrgSys.Reference.BookCode import BookCode


class PassagePortion(NamedTuple):
    """Native (BBB,C,V-with-suffix), detached entries, and starting context.

    The reference identifies the first requested address in this portion. The
    entries retain their own verse labels: an indivisible stored bridge can
    contain more text than the requested address alone. No text is renumbered.
    """
    reference: tuple[str, str, str]
    entries: InternalBibleEntryList
    context: list[str]


@dataclass(frozen=True)
class MappedBiblePassage:
    """Mapping provenance and retrieved text; allowAbsent can explicitly be partial."""
    mapping: MappingResult
    portions: tuple[PassagePortion, ...]
    native_references: tuple = ()
    absent_source_references: tuple = ()


class MissingPassageBookError(KeyError):
    """The requested native book is absent from this loaded/available edition."""
    def __init__(self, reference) -> None:
        self.reference = reference
        super().__init__(reference[0])

    def __reduce__(self):
        return type(self), (self.reference,), self.__dict__


class MissingPassageVerseError(KeyError):
    """A requested native verse or exact suffix is absent from the edition."""
    def __init__(self, reference) -> None:
        self.reference = reference
        super().__init__(reference)


def _passage_source_description(source, BBB:BookCode):
    """Identify the edition and, where available, the offending source file."""
    if source is None:
        return 'Bible not supplied'
    if isinstance(source, str):
        return source
    if isinstance(source, BibleVersificationMixin):
        names = tuple(dict.fromkeys(str(value) for value in (
            getattr(source, 'abbreviation', None), getattr(source, 'name', None),
            getattr(source, 'givenName', None)) if value))
        book = getattr(source, 'books', {}).get(BBB)
        path = (getattr(book, 'sourceFilepath', None) or getattr(source, 'sourceFilepath', None)
                or getattr(source, 'sourceFolder', None))
        description = 'Bible ' + (' / '.join(names) or source.getAName() or type(source).__name__)
        return f'{description}; source {path}' if path else description
    return f'versification {_system_name(source)} (Bible not supplied)'


# These patterns are used for every verse of every edition, so they're compiled once here
_VERSE_LIST_LABEL = re.compile(r'\d+[a-z]*(?:,\d+[a-z]*)+') # e.g., '12,11'
_VERSE_OR_BRIDGE_LABEL = re.compile(r'(\d+)([a-z]*)(?:-(\d+)([a-z]*))?') # e.g., '5', '5a', '5-7', '5b-6a'
_STORED_VERSE_LABEL = re.compile(r'\d+[a-z]*(?:-\d+[a-z]*|(?:,\d+[a-z]*)+)?') # Any of the above
_FIRST_VERSE_LABEL = re.compile(r'1(?:[a-z]+|-\d+[a-z]*)?') # e.g., '1a', '1-2' (but not plain '1')
_LEADING_DIGITS = re.compile(r'\d+')


class _UnsupportedVerseLabel(ValueError):
    """Raised by _expand_verse_label; _verse_references adds the source description."""


@lru_cache(maxsize=262_144)
def _expand_verse_label(BBB:BookCode, C, value) -> tuple[VerseRef, ...]:
    """Expand one stored verse label into its references.

    The same (book, chapter, label) is looked up again and again (for every edition,
    and every time that any verse in its chapter is fetched), so the results are remembered.
    (Failures aren't remembered: they're raised again each time.)
    """
    if _VERSE_LIST_LABEL.fullmatch(value):
        # Some USFM resources explicitly list reordered verses, e.g. MSG's
        # Acts 27:12,11. This is a list, never an inferred enclosing range.
        return tuple(dict.fromkeys(ref for label in value.split(',')
                                   for ref in _expand_verse_label(BBB,C,label)))
    match = _VERSE_OR_BRIDGE_LABEL.fullmatch(value)
    if not match:
        raise _UnsupportedVerseLabel(f'Unsupported source verse label {BBB} {C}:{value!r}')
    first, suffix, last, last_suffix = match.groups()
    if last:
        if int(last) - int(first) >= 10000:
            raise _UnsupportedVerseLabel(f'Source verse bridge exceeds 10000 addresses: {BBB} {C}:{value!r}')
        if int(last) < int(first) or (int(last) == int(first)
                and (not suffix or not last_suffix or len(suffix) != 1 or len(last_suffix) != 1 or suffix > last_suffix)):
            raise _UnsupportedVerseLabel(f'Unsupported source verse bridge {BBB} {C}:{value!r}')
        if int(first) == int(last):
            return tuple(normalize_reference((BBB,C,first,chr(s)))
                         for s in range(ord(suffix),ord(last_suffix)+1))
        return tuple(normalize_reference((BBB,C,v,
                     suffix if v == int(first) else last_suffix if v == int(last) else None))
                     for v in range(int(first),int(last)+1))
    return (normalize_reference((BBB,C,first,suffix)),)


def _verse_references(BBB:BookCode, C, value, source=None) -> tuple[VerseRef, ...]:
    """Expand a stored numeric bridge; preserve an explicit verse suffix."""
    try:
        return _expand_verse_label(BBB, C, value)
    except _UnsupportedVerseLabel as error:
        raise ValueError(f'{error} [{_passage_source_description(source, BBB)}]') from None
    except TypeError: # Unhashable parameters can't be remembered (and are probably wrong anyway)
        return _expand_verse_label.__wrapped__(BBB, C, value)


@lru_cache(maxsize=32_768)
def _labels_by_verse(BBB:BookCode, C, labels:tuple[str, ...]) -> dict:
    """Map each verse number in a chapter to the (label, references) pairs of the stored portions touching it.

    Most editions have exactly the same labels in a given chapter, and the same chapter
    is asked about for verse after verse, so the results are remembered.
    """
    labelsByVerse = {}
    for label in labels:
        if _STORED_VERSE_LABEL.fullmatch(label):
            refs = _expand_verse_label(BBB, C, label)
            if len(refs) == 1:
                labelsByVerse.setdefault(refs[0].V, []).append((label, refs))
            else: # A bridge or list (but only add this label once for each verse number)
                versesDone = set()
                for ref in refs:
                    if ref.V not in versesDone:
                        versesDone.add(ref.V)
                        labelsByVerse.setdefault(ref.V, []).append((label, refs))
    return labelsByVerse


class _ChapterPassageData:
    """The stored verse labels of one chapter of one edition, with their entries fetched only when needed.

    Fetching one verse needs to know every stored label in its chapter
    (because a verse can be stored inside bridges like '1-2a' and '2b-3'),
    but it doesn't need the entries of the other verses.
    So we get the list of labels (which is cheap) but only get entries for the labels that are asked for.
    """
    __slots__ = ('bible', 'BBB', 'C', 'index', 'labels', 'data', '_labelsByVerse', '_numLabelsIndexed')

    def __init__(self, bible, BBB:BookCode, C:str, data:dict|None=None) -> None:
        """A caller can supply the complete data for the chapter (a dict of label -> (entries, context))."""
        self.bible, self.BBB, self.C = bible, BBB, C
        self.index = index = bible.books[BBB]._CVIndex
        self.data = {} # label -> (entries, context)
        if data is None:
            labelGetter = getattr(index, 'getChapterVerseLabels', None)
            if labelGetter:
                self.labels = labelGetter(C)
            else: # Support installed native BOS indexes predating the labels getter.
                bulkGetter = getattr(index, 'getChapterVerseEntriesWithContext', None)
                if bulkGetter:
                    data = bulkGetter(C)
                else:
                    self.labels = [verse for (chapter,verse), _entry in index.items() if chapter == C]
        if data is not None:
            self.data = data
            self.labels = list(data)
        self._labelsByVerse, self._numLabelsIndexed = None, -1

    def __contains__(self, label:str) -> bool:
        return label in self.data or label in self.labels

    def get(self, label:str):
        """Return (entries, context) for a stored label of this chapter."""
        try: return self.data[label]
        except KeyError: pass
        result = self.data[label] = self.index.getVerseEntriesWithContext((self.C,label), True, False)
        return result

    def add(self, label:str, data) -> None:
        """Remember data which was found for a label that isn't itself stored, e.g., a verse inside a bridge."""
        if label not in self.labels:
            self.labels.append(label)
        self.data[label] = data

    def labels_touching(self, V:str, suffix) -> list[str]:
        """Return (in order) every label with a stored portion touching the given whole verse or verse segment."""
        if self._numLabelsIndexed != len(self.labels):
            try:
                self._labelsByVerse = _labels_by_verse(self.BBB, self.C, tuple(self.labels))
            except _UnsupportedVerseLabel as error:
                raise ValueError(f'{error} [{_passage_source_description(self.bible, self.BBB)}]') from None
            self._numLabelsIndexed = len(self.labels)
        found = [(label, refs) for label, refs in self._labelsByVerse.get(V, ())
                 if not suffix or any(ref.V == V and ref.S == suffix for ref in refs)]
        if len(found) > 1:
            found.sort(key=lambda labelRefs: (int(_LEADING_DIGITS.match(labelRefs[0])[0]), labelRefs[1][0].S or ''))
        return [label for label, _refs in found]


def _native_reference_points(reference, bible) -> tuple[VerseRef, ...] | tuple[VerseRef]:
    """Expand a native verse label; keep scalar mapping validation unchanged.

    A separate suffix can accompany a numeric verse, but must not be appended
    to a range/list or to an already suffixed label with unclear scope.
    """
    if (isinstance(reference, (tuple,list)) and len(reference) in (3,4)
            and isinstance(reference[2], str) and not reference[2].isdecimal()
            and (len(reference) == 3 or reference[3] in (None,''))):
        return _verse_references(*reference[:3], source=bible)
    return (normalize_reference(reference),)


def passageReferencesFromEntries(reference, entries, sourceSystem, *, sourceBible=None) -> tuple[VerseRef, ...]:
    """Extract ordered scripture references from a BOS entry list.

    reference supplies the starting (BBB,C[,V]); c fields update the chapter.
    Numeric bridges expand, explicit suffixes remain separate, and repeated
    references are deduplicated. A d field before the first numbered verse is
    included as zero only if BOS does not report UNDECLARED_TITLE for the source
    profile. Thus titles stored inside verse 1 do not create invented addresses.
    Editorial introductions produce no scripture references. Unsupported source
    labels raise ValueError rather than silently dropping part of a passage.

    sourceSystem accepts a name, BibleVersificationSystem, or declared Bible.
    If numbering is supplied separately, sourceBible can identify the edition
    (a Bible object or descriptive name) for malformed-label diagnostics.
    This extracts addresses, not a promise that their subsequent mapping is exact.
    """
    if not isinstance(reference, (tuple, list)) or len(reference) not in (2,3,4):
        raise ValueError('Expected a starting (BBB,C[,V[,S]]) reference.')
    BBB, C = str(reference[0]), str(reference[1])
    numbered = False
    references = []
    for entry in entries:
        marker, value = entry.getMarker(), entry.getCleanText()
        if marker == 'c':
            C, numbered = value, False
        elif marker == 'v':
            references.extend(_verse_references(BBB,C,value,sourceBible if sourceBible is not None else sourceSystem))
            numbered = True
        elif marker == 'd' and not numbered and int(C) > 0:
            title = normalize_reference((BBB,C,0))
            if isinstance(sourceSystem, BibleVersificationMixin):
                declaration = sourceSystem.convertReferencesToVersification(sourceSystem, (title,))
            else:
                name = _system_name(sourceSystem)
                declaration = get_default_mapping_engine().convert(name, name, (title,))
            if not any(d.code == 'UNDECLARED_TITLE' for d in declaration.diagnostics):
                references.append(title)
    return tuple(dict.fromkeys(references))


def get_passage_data(bible, references, *, chapter_cache=None, combine_adjacent:bool=False):
    """Implementation of Bible.getPassageData; validate/fetch before returning."""
    references = tuple(point for ref in references for point in _native_reference_points(ref,bible))
    cache = {} if chapter_cache is None else chapter_cache
    portions, seen = [], set()

    def fetch(reference, *, stored:bool=False) -> None:
        BBB, C, V, suffix = reference
        key = V + (suffix or '') # The stored verse label, e.g. '5' or '5a'
        native = (BBB,C,key)
        if BBB not in bible and BBB not in bible.availableBBBs:
            raise MissingPassageBookError(native)
        bible.loadBookIfNecessary(BBB)
        if BBB not in bible:
            raise MissingPassageBookError(native)
        cache_key = (id(bible),BBB,C)
        try: chapter = cache[cache_key]
        except KeyError:
            chapter = cache[cache_key] = _ChapterPassageData(bible, BBB, C)
        if type(chapter) is dict: # The caller supplied the chapter's data in their cache
            chapter = cache[cache_key] = _ChapterPassageData(bible, BBB, C, chapter)
        if not stored and V.isdigit() and V != '0':
            # Include every stored portion touching this whole verse, including
            # partial bridges (1-2a, 2b-3). Scalar lookup can return just one.
            labels = chapter.labels_touching(V, suffix)
            if labels and labels != [key]:
                for label in labels:
                    fetch((BBB,C,label,None), stored=True)
                return
        if key not in chapter:
            try:
                # Four-tuple legacy access ignores S: pass the suffix in V.
                # Numeric lookups can match a bridge; suffixes must be exact.
                chapter.add(key, bible.getContextVerseData(native, strict=bool(suffix)))
            except KeyError as error:
                raise MissingPassageVerseError(native) from error
        data = chapter.get(key)
        if data is None:
            raise MissingPassageVerseError(native)
        entries, context = data
        if not entries:
            raise MissingPassageVerseError(native)

        def leading_titles(values) -> list:
            titles = []
            for entry in values:
                if entry.getMarker() == 'v':
                    break
                if entry.getMarker() == 'd':
                    titles.append(entry)
            return titles

        if key == '0' and not leading_titles(entries):
            # USX and USFM indexes sometimes attach a Psalm title to verse 1
            # while verse 0 contains only the chapter marker. Retrieve the title
            # independently; never copy the numbered verse into its place.
            for label in tuple(chapter.labels):
                if _FIRST_VERSE_LABEL.fullmatch(label):
                    candidate, _context = chapter.get(label)
                    titles = leading_titles(candidate)
                    if titles:
                        entries = InternalBibleEntryList()
                        for title in titles:
                            entries.append(title)
                        break
        elif key != '0':
            titles = leading_titles(entries)
            if titles:
                detached = InternalBibleEntryList()
                before_verse = True
                for entry in entries:
                    if entry.getMarker() == 'v':
                        before_verse = False
                    if not (before_verse and entry.getMarker() == 'd'):
                        detached.append(entry)
                entries = detached
        labels = tuple(e.getCleanText() for e in entries if e.getMarker() == 'v')
        span = (BBB,C,labels or (key,))
        if span not in seen:
            seen.add(span)
            portions.append(PassagePortion(native, entries, context))

    for reference in references:
        fetch(reference)
    return _copy_portions(portions, combine_adjacent, bible)


def _is_next_address(previous: VerseRef, current: VerseRef) -> bool:
    """True if current directly follows previous in the same chapter.

    That is either the next whole verse (5 then 6), or the next single-letter
    segment of the same verse (5a then 5b). Gaps and reordering never count.
    """
    if (previous.BBB, previous.C) != (current.BBB, current.C):
        return False
    if previous.S is None and current.S is None:
        return int(current.V) == int(previous.V) + 1
    return bool(previous.V == current.V and previous.S and current.S
                and len(previous.S) == len(current.S) == 1
                and ord(current.S) == ord(previous.S) + 1)


def _copy_portions(portions, combine_adjacent, bible) -> tuple:
    """Detach data from caches, optionally coalescing adjacent native addresses.

    Never bridge gaps, book/chapter changes, or reordering. Do not infer a text
    envelope between the first and last destination of a disjoint mapping.
    """
    joined, previous = [], None
    for reference, entries, context in portions:
        BBB, C, V = reference
        first = _verse_references(BBB,C,V,bible)[0]
        if combine_adjacent and previous is not None and _is_next_address(previous, first):
            joined[-1].entries.extend(entries)
        else:
            copied = InternalBibleEntryList()
            copied.extend(entries)
            joined.append(PassagePortion(reference, copied, list(context)))
        labels = [e.getCleanText() for e in entries if e.getMarker() == 'v']
        previous = _verse_references(BBB,C,labels[-1],bible)[-1] if labels else first
    return tuple(joined)


def get_mapped_passage(bible, source_system, references, *, chapter_cache=None, combine_adjacent:bool=False,
                       expand_groups:bool=False, allow_absent:bool=False):
    """Retrieve mapped text, optionally completing mapping AND stored bridges.

    Stored labels and entries are never renumbered or sliced. When expansion is
    requested, additional text in a stored bridge must also have known source
    coverage. Feed that coverage back through mapping until both are complete.
    """
    if allow_absent:
        requested = tuple(normalize_reference(ref) for ref in references)
        try:
            return get_mapped_passage(bible,source_system,requested,
                chapter_cache=chapter_cache,combine_adjacent=combine_adjacent,expand_groups=expand_groups)
        except VersificationMappingError as error:
            result = error.result
            # Only an explicit reviewed absence may be omitted. Unknown books,
            # ambiguous mappings, undeclared titles and missing data still fail.
            if not result.diagnostics or any(d.code != 'NO_REFERENCE_COUNTERPART'
                    or d.system != result.source_system for d in result.diagnostics):
                raise
            absent = tuple(dict.fromkeys(ref for d in result.diagnostics for ref in d.references))
            remaining = tuple(ref for ref in requested if ref not in absent)
            if len(remaining) == len(requested):
                raise
            if remaining:
                mapped = get_mapped_passage(bible,source_system,remaining,
                    chapter_cache=chapter_cache,combine_adjacent=combine_adjacent,expand_groups=expand_groups)
                coverage = tuple(dict.fromkeys((*requested,*mapped.mapping.source_references)))
                mapping = replace(mapped.mapping,status=MappingStatus.PARTIAL,
                    source_references=coverage,requested_references=requested,
                    diagnostics=mapped.mapping.diagnostics+result.diagnostics)
                return replace(mapped,mapping=mapping,absent_source_references=absent)
            return MappedBiblePassage(replace(result,status=MappingStatus.PARTIAL,
                requested_references=requested),(),(),absent)
    selection = tuple(references)
    requested = None
    cache = {} if chapter_cache is None else chapter_cache
    while True:
        result = bible.convertReferencesFromVersification(source_system, selection, expandGroups=expand_groups)
        if result.status != MappingStatus.EXACT:
            result.require_single() # Raise the specific mapping error with its result.
        if requested is None:
            requested = result.requested_references or result.source_references
        portions = get_passage_data(bible, result.references,
            chapter_cache=cache, combine_adjacent=combine_adjacent)
        native = tuple(dict.fromkeys(ref for portion in portions for ref in (
            passageReferencesFromEntries(portion.reference, portion.entries, bible) or
            _verse_references(*portion.reference,source=bible))))
        if not expand_groups:
            return MappedBiblePassage(result, portions, native)
        # Whole-verse requests legitimately retrieve every stored suffix.
        extra = [ref for ref in native if ref not in result.references
                 and not (ref.S and ref.whole_verse() in result.references)]
        if not extra:
            return MappedBiblePassage(replace(result, requested_references=requested), portions, native)
        stored_coverage = tuple(dict.fromkeys((
            # A partial endpoint in an indivisible stored bridge requires the
            # rest of that verse too. Expansion retrieves all its stored parts
            # on the next pass before returning an exact complete passage.
            *(ref.whole_verse() for ref in native),
            *result.references)))
        coverage = bible.convertReferencesToVersification(source_system, stored_coverage, expandGroups=True)
        if coverage.status != MappingStatus.EXACT:
            coverage.require_single()
        expanded = tuple(dict.fromkeys((*coverage.references, *result.source_references)))
        if set(expanded) <= set(result.source_references) or len(expanded) > 10000:
            raise PartialMappingError(replace(result, status=MappingStatus.PARTIAL, references=(),
                requested_references=requested, diagnostics=result.diagnostics + (
                    MappingDiagnostic('INCOMPLETE_STORED_BRIDGE',
                        'Stored text extends beyond the provable complete passage.', result.target_system, native),)))
        selection = expanded
