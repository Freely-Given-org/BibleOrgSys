# SPDX-FileCopyrightText: © 2026 Robert Hunt <Freely.Given.org+BOS@gmail.com>
# SPDX-License-Identifier: MPL-2.0
"""Complete passage retrieval in native or mapped versification.

Public Bible methods delegate here; this module has no application, renderer,
or navigation dependencies. Mapping results describe references, while portions
describe the text actually stored (including indivisible USFM verse bridges).
"""
from dataclasses import dataclass, replace
import re
from typing import NamedTuple

from bible_organisational_system import InternalBibleEntryList
from BibleOrgSys.Reference.BibleVersification import BibleVersificationMixin, _system_name
from BibleOrgSys.Reference.BibleVersificationMappings import (
    MappingDiagnostic, MappingResult, MappingStatus, PartialMappingError, VersificationMappingError,
    get_default_mapping_engine, normalize_reference,
)


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
    def __init__(self, reference):
        self.reference = reference
        super().__init__(reference[0])

    def __reduce__(self):
        return type(self), (self.reference,), self.__dict__


class MissingPassageVerseError(KeyError):
    """A requested native verse or exact suffix is absent from the edition."""
    def __init__(self, reference):
        self.reference = reference
        super().__init__(reference)


def _passage_source_description(source, BBB):
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


def _verse_references(BBB, C, value, source=None):
    """Expand a stored numeric bridge; preserve an explicit verse suffix."""
    match = re.fullmatch(r'(\d+)([a-z]*)(?:-(\d+))?', value)
    if not match:
        raise ValueError(f'Unsupported source verse label {BBB} {C}:{value!r} '
                         f'[{_passage_source_description(source, BBB)}]')
    first, suffix, last = match.groups()
    if last:
        if suffix or int(last) < int(first):
            raise ValueError(f'Unsupported source verse bridge {BBB} {C}:{value!r} '
                             f'[{_passage_source_description(source, BBB)}]')
        return tuple(normalize_reference((BBB,C,v)) for v in range(int(first),int(last)+1))
    return (normalize_reference((BBB,C,first,suffix)),)


def passageReferencesFromEntries(reference, entries, sourceSystem, *, sourceBible=None):
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


def get_passage_data(bible, references, *, chapter_cache=None, combine_adjacent=False):
    """Implementation of Bible.getPassageData; validate/fetch before returning."""
    references = tuple(normalize_reference(ref) for ref in references)
    cache = {} if chapter_cache is None else chapter_cache
    portions, seen = [], set()

    def fetch(reference):
        BBB, C, V, suffix = reference
        native = (BBB,C,V + (suffix or ''))
        if BBB not in bible and BBB not in bible.availableBBBs:
            raise MissingPassageBookError(native)
        bible.loadBookIfNecessary(BBB)
        if BBB not in bible:
            raise MissingPassageBookError(native)
        cache_key = (id(bible),BBB,C)
        if cache_key not in cache:
            index = bible.books[BBB]._CVIndex
            bulk_getter = getattr(index, 'getChapterVerseEntriesWithContext', None)
            # Support installed native BOS indexes predating the bulk getter.
            cache[cache_key] = (bulk_getter(C) if bulk_getter else {
                verse: bible.getContextVerseData((BBB,C,verse), strict=True)
                for (chapter,verse), _entry in index.items() if chapter == C})
        chapter = cache[cache_key]
        key = native[2]
        if not suffix and key not in chapter:
            # Non-strict scalar lookup may return only one stored suffix. A
            # request for the whole verse must include every stored segment.
            segments = sorted(k for k in chapter if re.fullmatch(re.escape(V)+r'[a-z]+', k))
            if segments:
                for segment in segments:
                    fetch((BBB,C,V,segment[len(V):]))
                return
        if key not in chapter:
            try:
                # Four-tuple legacy access ignores S: pass the suffix in V.
                # Numeric lookups can match a bridge; suffixes must be exact.
                chapter[key] = bible.getContextVerseData(native, strict=bool(suffix))
            except KeyError as error:
                raise MissingPassageVerseError(native) from error
        data = chapter[key]
        if data is None or not data[0]:
            raise MissingPassageVerseError(native)
        entries, context = data
        labels = tuple(e.getCleanText() for e in entries if e.getMarker() == 'v')
        span = (BBB,C,labels or (key,))
        if span not in seen:
            seen.add(span)
            portions.append(PassagePortion(native, entries, context))

    for reference in references:
        fetch(reference)
    return _copy_portions(portions, combine_adjacent, bible)


def _copy_portions(portions, combine_adjacent, bible):
    """Detach data from caches, optionally coalescing adjacent native addresses.

    Never bridge gaps, book/chapter changes, or reordering. Do not infer a text
    envelope between the first and last destination of a disjoint mapping.
    """
    joined, previous = [], None
    for reference, entries, context in portions:
        BBB, C, V = reference
        first = _verse_references(BBB,C,V,bible)[0]
        adjacent = combine_adjacent and previous and previous[:2] == first[:2] and (
            (previous[3] is None and first[3] is None and int(first[2]) == int(previous[2])+1)
            or (previous[2] == first[2] and previous[3] and first[3]
                and len(previous[3]) == len(first[3]) == 1 and ord(first[3]) == ord(previous[3])+1))
        if adjacent:
            joined[-1].entries.extend(entries)
        else:
            copied = InternalBibleEntryList()
            copied.extend(entries)
            joined.append(PassagePortion(reference, copied, list(context)))
        labels = [e.getCleanText() for e in entries if e.getMarker() == 'v']
        previous = _verse_references(BBB,C,labels[-1],bible)[-1] if labels else first
    return tuple(joined)


def get_mapped_passage(bible, source_system, references, *, chapter_cache=None, combine_adjacent=False,
                       expand_groups=False, allow_absent=False):
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
                 and not (ref[3] and (*ref[:3], None) in result.references)]
        if not extra:
            return MappedBiblePassage(replace(result, requested_references=requested), portions, native)
        stored_coverage = tuple(dict.fromkeys((
            *((*ref[:3], None) if (*ref[:3], None) in result.references else ref for ref in native),
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
