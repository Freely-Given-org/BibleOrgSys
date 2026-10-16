# Retrieving passages across versification systems

Every `Bible`/`InternalBible` format provides `getMappedPassage` and
`getPassageData`. These methods retrieve BOS text entries and context, without
HTML, application navigation, or OET-specific assumptions. They use the existing
[versification declarations](BibleVersification.md) and
[mapping engine](VersificationMappingAPI.md).

## Map and retrieve a complete passage

For a loaded or preloaded Bible whose source text uses original numbering:

```python
targetBible.setVersificationSystem('org')
passage = targetBible.getMappedPassage(
    'eng', [('MAL', 4, verse) for verse in range(1, 7)],
    combineAdjacent=True,
)
assert passage.mapping.references == tuple(
    ('MAL', '3', str(verse), None) for verse in range(19, 25)
)
for portion in passage.portions:
    nativeReference, entries, context = portion
    # Render, compare, export, or otherwise consume the native entries.
```

`sourceSystem` can be a system name, a `BibleVersificationSystem`, or another
Bible. Both source and destination Bible declarations are respected, including
metadata conflicts and explicit overrides. No source profile is assumed.

The references are an ordered iterable of `(BBB, C, V[, suffix])` tuples using
BOS book codes. Supply an entire merge group together. A scalar conversion or
mapping only a passage's endpoints cannot replace a complete passage conversion.

The return value is `MappedBiblePassage`:

- `mapping` is the exact `MappingResult`, retaining source/destination references,
  diagnostics, provenance, and mapping-data revision.
- `portions` is a tuple of `PassagePortion` named tuples. Each has `reference`
  (native `(BBB, C, V)` with any suffix appended to V), `entries`
  (`InternalBibleEntryList`), and `context` (the starting context marker list).
- `native_references` lists the actual stored verse coverage, including bridges
  and suffixes. Word identifiers and entries retain their native values.

By default, each distinct stored verse span is a separate portion. With
`combineAdjacent=True`, consecutive native addresses in the same chapter are
joined. Chapter/book changes, gaps, and reordered destinations remain separate.
Intervening verses are never fetched merely because they lie between two mapped
addresses. Entries retain their original numbering, markup, notes, and extras.

`convertReferencesFromVersification(sourceSystem, references)` offers the same
incoming reference conversion without loading text. It returns `MappingResult`
for every status, complementing `convertReferencesToVersification`.

## Explicitly retrieve an indivisible combined passage

```python
passage = targetBible.getMappedPassage('eng', [('ACT', 19, 41)], expandGroups=True)
assert passage.mapping.requested_references == (('ACT', '19', '41', None),)
assert passage.mapping.source_references == (
    ('ACT', '19', '40', None), ('ACT', '19', '41', None),
)
assert passage.mapping.is_expanded
assert passage.native_references == (('ACT', '19', '40', None),)
```

This opt-in completes unambiguous mapping groups, then retrieves their full native
text. It also accounts for indivisible stored bridges, such as an English edition
storing `\v 40-41`: coverage is mapped back and completed until the retrieved text
and the mapped source passage agree. An unsupported or ambiguous extra portion
raises a mapping error; it is never silently presented as the requested verse.

Renderers should label expanded results with their complete source and native
references (for example, “Combined passage: English Acts 19:40–41; native Acts
19:40”). The requested verse remains available in `requested_references` for
navigation. BOS neither renumbers entries/word identifiers nor invents textual
splits. A same-system request for separately stored English verse 41 retrieves
only verse 41, independently of its cross-system mapping group.

The Bible's `convertReferencesFromVersification` and
`convertReferencesToVersification` methods also accept `expandGroups=True` for
reference-only use. Their default remains strict.

## Native retrieval, bridges, and suffixes

```python
portions = targetBible.getPassageData([
    ('MAL', '3', '19'), ('MAL', '3', '20'),
])
```

Native retrieval does not require a versification declaration or perform a
mapping round trip. It validates reference syntax, loads available books when
needed, and retrieves all portions before returning. An empty native request
returns `()`; an empty mapped request is an invalid mapping.

A stored USFM bridge such as `\v 2-3` is indivisible and is returned once when
both verses are requested. Requesting just verse 3 also returns that complete
stored span; this API does not invent a textual division. `portion.reference`
identifies the first requested address in the portion, while its entries retain
the actual stored verse label (`2-3`). With the default strict mapping option, the mapping result still describes the
requested references, not a claim that the text can be sliced that finely.
`expandGroups=True` instead reports the complete source coverage as above.

A whole verse stored as `4a` and `4b` includes both entries. An explicit request
for `('GEN', 1, 4, 'b')` requires that suffix to exist and never falls back to the
whole verse or another suffix. Use the four-tuple form for input suffixes.
Repeated storage spans are deduplicated in request order; identical text in
different verses remains separate.

Returned entry lists and contexts are detached from the retrieval cache. Optional
`chapterCache={}` can be shared between calls for the same live Bible instances;
discard it after reloading/editing text or releasing those instances. It is
caller-owned, not added to a Bible's saved state, and must not be persisted.

## Source passages taken from BOS entries

```python
from BibleOrgSys.Internals.InternalBiblePassages import passageReferencesFromEntries

entries, context = sourceBible.getContextVerseData(('PSA', '3'))
references = passageReferencesFromEntries(('PSA', '3'), entries, sourceBible)
passage = targetBible.getMappedPassage(sourceBible, references)
```

`passageReferencesFromEntries` expands numeric verse bridges, retains suffixes,
and follows chapter markers throughout the supplied entries. A `d` field before
the first numbered verse contributes verse zero only where BOS has not reported
`UNDECLARED_TITLE` for the source profile. Titles included in verse 1 do not
produce invented zero addresses. This handles intermediate titles that a plain
range expansion intentionally does not insert. Unsupported verse-label syntax
raises `ValueError`. Extraction alone does not certify an exact mapping.

Malformed-label errors identify the Bible edition and its source file or folder
when available, as well as the book, chapter, and offending label. If the source
profile is supplied separately from its Bible, pass `sourceBible=sourceBible`
(or a descriptive edition name) to retain this diagnostic context:

```python
references = passageReferencesFromEntries(
    ('SA1', '13'), entries, 'eng', sourceBible=sourceBible,
)
```

Editorial book introductions and headers are not scripture addresses. Continue
to retrieve those with `getContextVerseData`; their pairing/display policy belongs
to the application. `getMappedPassage` rejects introduction/chapter-zero inputs.

## Failure and edition boundaries

Non-exact mappings raise the corresponding existing `VersificationMappingError`
subclass (`AmbiguousMappingError`, `PartialMappingError`, `UnsupportedMappingError`,
or `InvalidReferenceError`) before loading destination text. With expansion
enabled, a further mapping failure can arise after inspecting a stored bridge. The exception's
`result` retains diagnostics and alternatives. No same-number fallback is used.

If an exact mapping points to absent text, `MissingPassageBookError` or
`MissingPassageVerseError` is raised. Both derive from `KeyError` and expose the
missing native `reference`. These types and the result/portion types are in
`BibleOrgSys.Internals.InternalBiblePassages`. A successful result always contains
the full requested group; callers are not given a partially retrieved passage.
Failed requests may still have loaded books or populated the caller's cache.

Mapping and missing-passage exceptions support pickling, including their result
or reference and added exception notes, for use with multiprocessing. Applications
which need prompt failure reporting and detection of crashed workers can use
the BOS [parallel task runner](ParallelTasks.md).

Book identities must match those of the selected profile. If an import stores a
combined book under a different name or splits it across physical books, the
application must explicitly adapt the exact converted references and pass them
to `getPassageData`. BOS does not infer edition-specific aliases or chapter
offsets from book names.

These APIs do not strengthen the draft mapping data's claims. Existing unsupported
books, ambiguous relationships, quarantined rules, and search limits remain in
force; see the [mapping policy](VersificationMappingAPI.md).

Offline regression tests:

```sh
.venv/bin/python -m unittest discover -s Tests -p test_InternalBiblePassages.py
```
