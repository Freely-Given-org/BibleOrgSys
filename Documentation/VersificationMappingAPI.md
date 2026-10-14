# Versification mapping engine and conversion APIs

Stage two provides offline reference conversion through `BOSReference`. It uses
the attributed Copenhagen snapshot already shipped with BOS; no external
repository, download, or new Python dependency is required. The reference remains
**`1-draft`**. A successful mapping is a statement about the selected numbering
profiles, not proof that two translations have identical wording or content.

The [data preparation guide](VersificationMappings.md) describes provenance,
reference-book choices, audit findings, and maintenance. The
[data attribution](../BibleOrgSys/DataFiles/VersificationMappings/README.md)
and unmodified upstream notices still apply. The copied source JSON remains
unchanged; revision 2 of the separately versioned BOS supplement corrects 54
reviewed English/Latin relationships before the engine compiles them. See the
[complete sniffing audit](VersificationSniffingAudit.md) for the 46 additions
after the initial eight English/Hebrew corrections.

## Selecting a system and converting one reference

Names are case-sensitive. The new profiles are `org`, `eng`, `lxx`, `vul`, `rsc`,
`rso`, `ethiopian_custom`, and `BOSReference`. All are available in the existing
`BibleVersificationSystems` registry, including their chapter/verse counts.
`ethiopian_custom` has counts but is disabled for mapping because the supplied
arrays cannot establish a complete system.

```python
from BibleOrgSys.Reference.BibleVersificationSystems import BibleVersificationSystem

english = BibleVersificationSystem('eng')
assert english.convertToReferenceVersification('GEN', '31', '55') == ('GEN', '32', '1', None)
assert english.convertFromReferenceVersification('GEN', '32', '1') == ('GEN', '31', '55', None)
assert english.convertToVersification('lxx', 'GEN', '31', '55') == ('GEN', '32', '1', None)
```

`convertToVersification(targetSystem, BBB, C, V, S=None)` combines the two
reference conversions internally. The target may also be a
`BibleVersificationSystem` instance. These three single-reference methods retain
the four-tuple return shape **only for an exact singleton**. They now raise a
typed exception for every other result; the former stubs' unchanged-reference
fallback is gone. Passing `detailed=True` returns a `MappingResult` instead.

Inputs use BOS book codes, not automatically inferred USFM codes. Chapters and
verses may be decimal strings or integers, but not booleans. Results contain
normalised decimal strings. An absent/empty suffix becomes `None`. Verse suffixes
are lowercase letters and require an explicit validated declaration. Chapter
zero/introduction references are invalid; verse zero is allowed only where a
title has been declared for that chapter.

Historical BOS names such as `KJV`, `Original`, `Septuagint`, `Vulgate`, and
`BibMaxRef` remain separate count systems. Their counts are unchanged; they have
no verified mapping profile. Converting with these names reports `unsupported`,
even when the input and output names are identical. Do not alias `KJV` to `eng`
merely because many of their counts agree. An unknown name passed to the
`BibleVersificationSystem` constructor raises `UnknownVersificationSystemError`.

## Structured results and exceptions

```python
from BibleOrgSys.Reference.BibleVersificationMappings import (
    MappingStatus, get_default_mapping_engine,
)

engine = get_default_mapping_engine()
result = engine.convert('rsc', 'BOSReference', [('PSA', 9, 22)])
assert result.status == MappingStatus.AMBIGUOUS
assert result.references == ()
assert set(result.alternatives) == {
    (('PSA', '10', '0', None),),
    (('PSA', '10', '1', None),),
}
```

The engine's `convert(source_system, target_system, references)` always returns
an immutable `MappingResult`; it needs only the Python standard library. It can
be used independently of the native dependencies used by the older BOS modules.
The input is an ordered iterable of three- or four-element reference tuples.
Repeated inputs are stably deduplicated. Empty passages, malformed references,
and requesting both a whole verse and one of its segments are invalid.

| Status | Meaning | Default single-reference API |
| --- | --- | --- |
| `exact` | The whole request has one supported destination group. The group can contain multiple references. | Returns a tuple for one reference; raises `MultipleReferencesError` for a larger group. |
| `ambiguous` | Multiple interpretations exist, an intermediate leg was ambiguous, or the bounded search could not establish uniqueness. | Raises `AmbiguousMappingError`. |
| `unsupported` | A profile, relationship, title, segment, or textual bridge is unavailable or quarantined. | Raises `UnsupportedMappingError`. |
| `partial` | Only part of a required group was requested, the passage cannot be completely mapped, or some composed alternatives failed. | Raises `PartialMappingError`. |
| `invalid` | The request has invalid syntax or is outside a known system's supplied book/chapter/verse domain. | Raises `InvalidReferenceError`. |

The exceptions above inherit `VersificationMappingError` (`ValueError`) and
retain the full result as `.result`. `result.require_single()` applies the same
rules as the single-reference APIs. Unknown engine profile names produce an
`unsupported` result, allowing callers to handle historical count-only systems.

Result fields:

- `source_system`, `target_system`, and normalised `source_references` describe
  the request. Invalid syntax can leave `source_references` empty.
- `references` is populated **only for `exact`**. It is the complete destination
  group, not a collection of alternatives or a partially mapped passage.
- `alternatives` holds complete candidate destination groups for an ambiguous
  or partial result. It may be empty. A partial result can include candidates
  that completed both legs while other interpretations failed; these must not
  be treated as an exact answer. Intermediate reference-system addresses are
  never returned as if they were destination-system addresses.
- `diagnostics` contains machine-readable `code`, human-readable `message`, the
  affected `system`, and, when available, references and the source `rule`.
- `provenance` records rules/declared identities used in successful candidate
  paths. Errors identify unusable rules in their diagnostics.
- `reference_version`, `data_revision`, and `mapping_policy_version` identify
  the address-space version, mapping-data revision, and engine-policy revision.
  The reference remains `1-draft`; the current policy version is `3`.
  Bundled `data_revision` is the pinned source commit followed by
  `+bos-supplement-2.<sha256>`, where the digest covers the supplement's canonical
  JSON (sorted keys, compact separators, UTF-8). The earlier bare commit and
  policy `1` identify results produced without this supplement. Store these
  fields alongside persisted converted references, and recompute affected old
  results rather than treating their former `exact` status as a content guarantee.

`getMappingCapabilities()` on a system, or `engine.capabilities(name)`, reports
profile availability as `partial` or `unsupported`. It is not a guarantee for
every reference. The per-request result remains authoritative.

## Passages, ranges, splits, and merges

```python
passage = engine.convert('eng', 'BOSReference', [('GEN', 31, 55), ('GEN', 32, 1)])
assert passage.references == (('GEN', '32', '1', None), ('GEN', '32', '2', None))
span = engine.convert_range('eng', 'BOSReference', ('GEN', 31, 55), ('GEN', 32, 1))
assert span == passage
```

The BOS wrapper equivalents are
`convertReferencesToVersification(targetSystem, references)` and
`convertRangeToVersification(targetSystem, startRef, endRef)`. Both always return
`MappingResult`. Use `BOSReference` as the target for a passage's first leg, or
as the source system to map a reference passage into another profile.

Ranges are inclusive and may cross chapters within one book. They expand
numbered verses according to the source counts, retaining any excluded verse
numbers so gaps cannot silently disappear. Intermediate chapter titles are not
inserted automatically; provide an explicit passage when titles are required.
Cross-book ranges need an explicit ordered passage because counts do not define
a book order. Segment ranges also need an explicit list of declared segments.
Range expansion is capped at 10,000 references; a larger range is invalid.

### Reviewed English/Hebrew group corrections

The Copenhagen standard `eng.json` only records the latter Hebrew member of
several English verses, or leaves an incomplete identity for Numbers 26:1.
Its title mappings for the four Psalms below omit Hebrew verse 1. BOS's
[`mapping-supplement.json`](../BibleOrgSys/DataFiles/VersificationMappings/mapping-supplement.json)
replaces those relationships with these whole groups:

| `eng` reference (OET-RV convention) | `org` / `BOSReference` group (OET-LV convention) |
| --- | --- |
| `NUM 26:1` | `NUM 25:19` + `NUM 26:1` |
| `SA1 20:42` | `SA1 20:42` + `SA1 21:1` |
| `KI1 22:43` | `KI1 22:43-44` |
| `CH1 12:4` | `CH1 12:4-5` |
| `PSA 51:0` | `PSA 51:1-2` |
| `PSA 52:0` | `PSA 52:1-2` |
| `PSA 54:0` | `PSA 54:1-2` |
| `PSA 60:0` | `PSA 60:1-2` |

The first four supplement the English numbered verses. The last four use BOS's
verse-zero convention for a Psalm title (`\d` in USFM), leaving English body
verse 1 mapped to Hebrew verse 3. Surrounding numbering shifts are preserved.
These rules apply to the declared `eng` profile; they do not infer the profile
of a loaded Bible or change any other source system.

```python
result = engine.convert('eng', 'org', [('NUM', 26, 1)])
assert result.status == MappingStatus.EXACT
assert result.references == (('NUM', '25', '19', None), ('NUM', '26', '1', None))
assert engine.convert('org', 'eng', result.references).require_single() == ('NUM', '26', '1', None)
assert engine.convert('org', 'eng', [('NUM', 25, 19)]).status == MappingStatus.PARTIAL
assert engine.convert('org', 'eng', [('NUM', 26, 1)]).status == MappingStatus.PARTIAL
```

An English singleton now has an exact **two-reference** result. The default
tuple API raises `MultipleReferencesError`; use `detailed=True` or a plural
API to obtain the full group. Either Hebrew member alone is partial, including
the member that the old mapping incorrectly treated as sufficient. Supply both
members to map back exactly. `getMappedPassage()` fetches both native portions
and likewise rejects a partial inverse request.

The copied Copenhagen sniffing rules provide additional `SubdividedVerse`
evidence. They cannot simply be executed as imported mappings: Numbers and
Samuel references terminate at a semicolon without the second chapter address,
and the Psalm rules combine title/body verses using another title convention.
The supplement records the explicit completed addresses and verification of
their content in the OET texts. No endpoint is guessed at runtime.

### Further reviewed English and Latin groups

Revision 2 adds `eng PSA 13:5-6 → org PSA 13:6`,
`eng ISA 63:19 + 64:1 → org ISA 63:19`, and
`eng ACT 19:40-41 → org ACT 19:40`. Either English member alone is now partial;
the complete group converts exactly. It also adds 43 `vul` relationships, such
as `vul EXO 40:13 → org EXO 40:13-15` and
`vul MA2 2:18-19 → org MA2 2:18`. The three-verse group needs all three members
for an exact inverse. Wisdom and 2 Maccabees are included; the existing Latin
Tobit/Judith/Sirach textual restrictions still apply.

The [audit guide](VersificationSniffingAudit.md) lists the groups, evidence and
deferred conflicts. Sniffing labels do not identify every modern edition: for
example, editions may combine the Acts 19:40–41 sentences in one stored verse.
The current OET-RV source separates them; OET-LV stores both in native 19:40.
Neither `eng` nor `org` is automatically an alias for an entire translation. Select a profile that matches the edition being converted.

Bible objects can also [retrieve the mapped text](BiblePassages.md) with
`getMappedPassage(sourceSystem, references)`. The returned object retains the
complete mapping result and all native text/context portions. This is separate
from these reference-only engine methods and requires BOS's normal text loaders.

Equal-length numeric `mappedVerses` ranges expand positionally. An intentional
split or merge is a relationship between **whole groups**, not several competing
singleton matches. All references in the required source group must be supplied
together. An incomplete group produces `partial`. Group output remains together
through both conversion legs; it is never reduced to the first matching verse.

The solver enumerates complete disjoint covers of the requested passage.
Output follows the input passage and each chosen rule's order, rather than being
sorted by destination address; duplicate destinations are stably deduplicated.
Reverse indexes include explicit rules **and declared identities**, so collisions
remain visible. Duplicate identical relationships do not create ambiguity.
Same-system calls validate native addresses and return identity directly; they
do not depend on a cross-system bridge. Counts, exclusions, declared titles and
suffixes are still checked. Cross-system conversions retain an ambiguous first
leg even when its final candidates converge. A failing alternative cannot be
discarded to turn another alternative into an exact result.

Applications that can display an explicitly labelled combined passage may opt in
with `engine.convert_passage(source, target, references)`. Strict `convert()` and
legacy scalar methods retain their incomplete-group errors. The passage method
completes connected atomic and merged groups on both conversion legs, retaining
gaps, native suffixes, and rule order. Competing relationships, unsupported
rules and missing mappings remain non-exact; the method never guesses a split.
Expansion is bounded to 10,000 visited addresses.

For example, `convert_passage('eng', 'org', [('ACT', 19, 41)])` returns:

- `requested_references`: English Acts 19:41;
- `source_references`: English Acts 19:40–41;
- `references`: original Acts 19:40;
- `status`: `exact` for that complete group, and `is_expanded`: `True`.

The result does **not** claim that original verse 40 is precisely English verse
41 alone. Applications should display the full source/native coverage whenever
`is_expanded` is true. Reference-only conversion cannot detect an edition's
stored verse bridges; use `getMappedPassage(..., expandGroups=True)` for that.

Search is bounded to 64 distinct candidate groups and 10,000 search steps per
leg/candidate, with at most 64 composed candidates retained. Truncation produces
`ALTERNATIVE_LIMIT` and a non-exact result, possibly with no candidates. Large or
highly overlapping passages can hit this limit; callers must not interpret the
reported candidates as exhaustive. Split large requests only where doing so
preserves complete mapping and merged-verse groups.

## Bundled policy and explicit gaps

The Copenhagen definitions describe differences from a base. The bundled
adapter deliberately permits unchanged addresses for books shared with `org`,
after validating both domains, exclusions, and restrictions. This is a declared
interpretation of those delta definitions; equal chapter maxima in unrelated
systems are never sufficient to infer identity. An explicit source mapping
replaces its identity. An explicit segment mapping also suppresses the whole
source verse's identity.

- `org` addresses remain unchanged in `BOSReference` where usable. Latin `LAO`
  is explicitly native to `vul`, which supplies its reference counts. `eng` LAO
  is still unsupported because that additional bridge has not been established.
- LXX source `DNG` can map through valid explicit rules into reference `DAN`.
  The separate reference `DNG` composite is still blocked. LXX source `EZN`
  uses the 23-chapter combined Ezra/Nehemiah definition: its first chapters map
  into `EZR`, and later chapters into `NEH`.
- Reference `PAZ`, `DNG`, `EZ6`, `MQ1`, `MQ3`, `REP`, and `BA4` remain unavailable
  pending bridge/edition review. Their draft counts are retained in the catalogue.
- Vulgate `TOB`, `JDT`, and `SIR` are unsupported in both directions because the
  upstream documentation explicitly excludes their different textual traditions.
  `ethiopian_custom` is disabled as a whole; missing chapters are not inferred.
- Undeclared Greek Esther destination segments remain unsupported. Segment
  labels containing whitespace or `-` are preserved in the source data, but are
  not stripped or guessed into valid labels. No arbitrary suffix is carried
  through a whole-verse relationship.
- Verse-zero declarations come from explicit rules mentioning those titles;
  they are not enabled for all Psalms/chapters. Reference titles also identify
  the corresponding `org` title addresses.
- Unequal upstream ranges are quarantined until reviewed as intentional groups.
  Reversed, out-of-bounds, excluded, and undefined endpoints are also quarantined
  in both directions. Unparseable spans block their identifiable chapter (or
  book/system if the scope cannot be narrowed). Quarantine propagates through
  connected relationships, including identities, so a defective alternative
  cannot be removed to manufacture an exact result.
- Custom `basedOn` inheritance is not resolved in this stage. Such definitions
  are explicitly unsupported. The copied custom example is not registered.

`conversionReady: false` and `identityMappingAssumed: false` in the generated
stage-one catalogue/audit retain their original meanings: the dataset is not
globally certified and the structural auditor does not infer identities. They
are not runtime feature switches. The engine applies the documented policy
above and reports the result for each request.

## Supplying complete definitions to the engine

The constructor accepts BOS-coded dictionaries, copied on construction. This is
a low-level API for callers with independently established definitions; it does
not register a new system in the legacy registry or attach one to a loaded Bible.

```python
from BibleOrgSys.Reference.BibleVersificationMappings import VersificationMappingEngine

custom = VersificationMappingEngine(
    {'maxVerses': {'GEN': [3]}},
    {'split': {
        'maxVerses': {'GEN': [2]},
        'groupMappings': [{'source': 'GEN 1:1', 'target': 'GEN 1:1-2'}],
        'mappedVerses': {'GEN 1:2': 'GEN 1:3'},
    }},
    reference_version='example-1', data_revision='example-data-1',
)
split = custom.convert('split', 'BOSReference', [('GEN', 1, 1)])
assert split.status == MappingStatus.EXACT
assert len(split.references) == 2
assert custom.convert('BOSReference', 'split', split.references).require_single() == ('GEN', '1', '1', None)
```

`maxVerses` maps a book to a complete chapter-count array. Optional fields are
`mappedVerses` (source-to-reference span dictionary), `groupMappings` (list of
`source`/`target` group objects), `identityBooks` (source-book-to-reference-book
dictionary), `excludedVerses` and `mergedVerses` (span lists), `partialVerses`
(whole-verse-to-valid-suffix-list dictionary), `verseZeroReferences` (individual
title addresses), `unsupportedBooks` (book-to-reason dictionary), and
`disabledReason` (string). Span syntax is `BBB C:V`, optionally with a suffix,
or `BBB C:V-V` within one chapter. Each side of a `groupMappings` object may
instead be a nonempty ordered list of spans, for example
`{'source': 'NUM 26:1', 'target': ['NUM 25:19', 'NUM 26:1']}`. Lists may cross
chapters or books; each member retains its explicit address and order. Repeated
members, whole-verse/segment overlaps, and groups exceeding 10,000 references
are rejected/quarantined. An optional `provenance` string identifies a reviewed
group in the result. Lists are not accepted for positional `mappedVerses`.
Inheritance must be flattened and reviewed by
the caller before supplying definitions. Invalid domain metadata can raise
`ValueError` (including `VersificationDataError`) at construction; unusable mapping rules are quarantined
and exposed through conversion diagnostics.

Identity is opt-in for custom definitions. Empty `identityBooks` means an
unmapped address stays unsupported. An equal-length relationship that must be
treated atomically belongs in `groupMappings`, not `mappedVerses`. Do not promote
an upstream unequal range to a group without evidence. For reference-definition
metadata, supply counts, exclusions, merged groups, segments, and title addresses
as appropriate; mapping rules belong in the source definitions.

## Validation and Bible integration

```sh
.venv/bin/python -m unittest discover -s Tests -p 'test_BibleVersificationMappings*.py' -v
python -m BibleOrgSys.Reference.Converters.BibleVersificationMappingsConverter --check
.venv/bin/python -m unittest Tests.test_BibleVersificationSupplement
```

The suites cover real chapter boundaries, Psalm titles and overlaps, LXX
reordering and combined books, Deuterocanonical/Latin coverage and restrictions,
synthetic splits/merges, partial groups, malformed-data quarantine, inverse
collisions, ambiguous composition, range expansion, typed exceptions, legacy
registry compatibility, and isolated zip-resource execution. The wrapper tests
require BOS's existing native dependencies; pure-engine tests do not.

Set `BOS_VERSIFICATION_TEST_WHEEL` to a built wheel's absolute path to additionally
audit and execute conversions directly from that distribution in an isolated
interpreter outside the checkout. The source snapshot and attribution are tested
byte-for-byte. A clean audit proves reproducibility, not universal coverage.

The [Bible integration guide](BibleVersification.md) describes load-time
declarations, metadata precedence, Bible-level conversion methods, and persistence
implemented in stage three. Conversion does not rewrite Bible text or change its
stored verse numbers. Remaining textual bridges,
custom inheritance, and segment normalisation require separately evidenced data
decisions and regression tests before being enabled.
