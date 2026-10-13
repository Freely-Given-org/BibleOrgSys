# BOS reference versification: data preparation

## Current implementation and boundaries

BOS now carries an attributed, pinned copy of the Copenhagen mapping data in
[`BibleOrgSys/DataFiles/VersificationMappings`](../BibleOrgSys/DataFiles/VersificationMappings/README.md).
This first stage supplies:

1. The original JSON definitions and accompanying documentation/schema.
2. An explicit policy for a Hebrew/Greek reference extended to other traditions.
3. A generated `BOSReference` **`1-draft`** counts catalogue with 102 entries.
4. A generated coverage report identifying data defects, relationships requiring
   review, and missing books.
5. An offline audit tool and regression tests.

No external repository is required at build, test, installation, or runtime.
The upstream URL and source commit are provenance, not a package dependency.
The module uses `importlib.resources`, so package data also works in a zip.

Stage two now registers `BOSReference` and the exact upstream system names in
`BibleVersificationSystems.py` and implements reference conversion, inverses,
and composition. See the [mapping API guide](VersificationMappingAPI.md) for
results, examples, and explicit coverage limits. Existing `Original` and
`BibMaxRef` remain independent count-only systems. Stage three adds
[load-time Bible declarations and conversions](BibleVersification.md).
Custom inheritance remains explicitly unsupported.

The subsequent [mapping supplement](VersificationMappingAPI.md#reviewed-englishhebrew-group-corrections)
initially added eight reviewed `eng` split/merge relationships using additional
Copenhagen sniffing evidence and text verification. Revision 2 adds 46 more
groups (`eng` and `vul`). The [sniffing audit](VersificationSniffingAudit.md)
inventories all 403 rules / 1,466 rows, including 556 split/merge rows, and records
unresolved edition and textual conflicts. It runs alongside compiled address
coverage and the original structural audit; all reports are generated offline.

## What “reference” means here

The reference core follows Copenhagen `org`: BHS/Masoretic Hebrew OT numbering
and UBS GNT/Nestle–Aland Greek NT numbering, as described in the copied upstream
README. “Original” identifies these editorial numbering conventions; it is not
a claim that chapter and verse numbers existed in the original manuscripts.

All 95 `org` book entries are retained numerically, not just the 66-book core.
The additional entries include Greek Deuterocanonical books, Orthodox books,
distinct Greek witnesses, and Ethiopian traditions. The reference does not
infer a canon or a Bible's actual contents from the available book inventory.

The per-book edition behind every additional `org` entry is not fully documented
upstream. These entries therefore have `counts-only` or `requires-review`
status. In particular, the supplied Jubilees and Enoch chapter structures are
retained as supplied, not asserted to represent every edition of those books.

Seven entries are added through explicit choices in `reference-policy.json`:

| USFM code | BOS code | Count source | Treatment |
| --- | --- | --- | --- |
| `DAG` | `DNG` | `lxx` | Provisional 12-chapter Greek Daniel composite view. Shared passages and additions still need an explicit bridge. |
| `LAO` | `LAO` | `vul` | Letter to the Laodiceans, one chapter of 20 verses; the same count also occurs in `eng`. |
| `6EZ` | `EZ6` | `vul` | Two-chapter extract view; its relationship to the larger Ezra/Esdras works requires review. |
| `1MQ` | `MQ1` | `ethiopian_custom` | Provisional 1 Meqabyan counts. |
| `3MQ` | `MQ3` | `ethiopian_custom` | Provisional 3 Meqabyan counts. |
| `REP` | `REP` | `ethiopian_custom` | Provisional Reproof counts. |
| `4BA` | `BA4` | `ethiopian_custom` | Provisional 4 Baruch counts. |

The Ethiopian extensions identify where counts are available, but the enclosing
custom file is underspecified. Their editions and completeness still need
verification. Counts are never filled in by taking maxima from different
editions. Composite views and extract views do not create independent canonical
passage identities merely because their counts appear in the catalogue.

`DAN` retains its Hebrew core numbering. `PAZ` (USFM `S3Y`), `SUS`, and `BEL`
remain separately identifiable. A future verified bridge must reconcile these with
`DNG` without creating duplicate passage identities. The same requirement
applies to Greek Esther, Baruch/Letter of Jeremiah, and Ezra/Esdras combinations.
Distinct witnesses must not be collapsed solely because their book names are
similar.

## Book-code translation

`book-codes.json` is an explicit crosswalk derived from the current BOS
`BibleBooksCodes.xml`; it records that source's SHA-256 hash. Normalisations
include `S3Y` → `PAZ`, `JDB` → `JGB`, and `1MA` → `MA1`.

Some USFM codes have several BOS identities. `DAG`, for example, can identify
Greek Daniel, additions to Daniel, or a combined Hebrew/Greek book. The default
catalogue choice is `DNG`, but alternatives remain recorded for later import
decisions. The audit does not prove that this default is the right identity for
every Bible using that USFM code.

There is one explicit source-system override: `lxx` supplies 23 chapters under
`EZR`, combining Ezra and Nehemiah, so its **source** book resolves to BOS `EZN`.
An `EZR` mapping destination in `org` still means BOS `EZR`. Never apply a source
override indiscriminately to both sides of a mapping.

The coverage report compares the reference with an attributed snapshot of all
26 existing BOS count-system inventories. Eight BOS identities remain absent:

| BOS code | Gap |
| --- | --- |
| `BA2` | 2 Baruch counts are absent from this Copenhagen snapshot. |
| `LBA` | Letter of Baruch counts are absent. |
| `MQ2` | 2 Meqabyan counts are absent, despite 1 and 3 Meqabyan being present. |
| `PS3` | The additional Psalms represented by this BOS identity are absent. |
| `DNA` | A separate additions-to-Daniel layout needs a bridge. |
| `ESA` | A separate additions-to-Esther layout needs a bridge. |
| `EZ5` | A separate 5 Ezra layout needs a bridge or additional sourced data. |
| `EZN` | The combined Ezra-Nehemiah source layout needs a bridge to separate reference books. |

These are missing identities, not necessarily eight independent missing works.
The report also lists the particular existing BOS systems affected by each gap.
There are additional textual coverage gaps, notably the Latin witnesses below,
that cannot be discovered by comparing book-code lists alone.

## Reading the coverage report

The report audits each standard definition against the **raw `org` destination
definition**, not against BOS's expanded draft catalogue. Adding a provisional
`DNG` entry therefore does not make the raw `org` defect disappear from the
report. `mappingTargetSystem` records that distinction.

The initial snapshot produces the following inventory. “Findings” counts
individual diagnostic records; several records can describe the same rule.
It is not a count of erroneous verses or a percentage of mapping coverage.

| System | Books with supplied counts | Explicit mapping rules | Findings |
| --- | ---: | ---: | ---: |
| `org` | 95 | 8 | 11 |
| `eng` | 92 | 265 | 230 |
| `lxx` | 89 | 267 | 90 |
| `vul` | 86 | 475 | 80 |
| `rsc` | 66 | 231 | 12 |
| `rso` | 79 | 374 | 311 |
| `ethiopian_custom` | 30 | 217 | 131 |

The custom example is audited separately. It supplies 49 excluded-verse entries,
29 merged-verse entries, and `basedOn: org`, exercising features absent from the
standard files. It is an example, not an additional supported Bible system.

Each book's coverage entry distinguishes available counts, explicit source-rule
counts, membership in the reference catalogue, and documented restrictions.
`identityMappingAssumed` and `conversionReady` remain false in these structural
audit documents: they neither infer identities nor certify global coverage.
The stage-two engine separately applies declared delta identities for shared
upstream books, subject to its documented restrictions and per-reference checks.
Chapter maxima alone do not prove complete verse or segment coverage.

### Findings requiring particular attention

- **Missing and inconsistent Daniel destinations:** all eight `org` rules map
  `S3Y` into `DAG`, but `org` lacks `DAG` counts. One rule also includes `S3Y`
  verse 68 while its supplied maximum is 67. The overlapping destination at
  `DAG 3:52` must be preserved rather than overwritten when building an inverse.
- **Schema/data disagreement:** the published schema specifies numeric counts,
  but the definitions use decimal strings. It also disallows the lettered
  Esther references used by `eng` and `rso`. Their destination segments are not
  enumerated in `org.partialVerses`. The audit understands the observed syntax
  while recording the disagreements; the original schema is preserved verbatim.
- **Vulgate reversed range:** `DAG 3:52-23` cannot be expanded. The apparent typo
  is preserved pending evidence for a correction. Other many-to-one and
  unequal-length ranges must not be silently zipped to the shorter length.
- **Latin textual differences:** the upstream README explicitly supplies no
  Vulgate-to-Septuagint mapping for `TOB`, `JDT`, or `SIR` because their Vorlage
  differs. These book entries are marked `unmapped-textual-tradition`, and the
  reference policy carries the restriction. Having a reference entry named
  Tobit does not make every Tobit witness interchangeable.
- **Incomplete Ethiopian arrays:** the file provides only three Exodus count
  entries while mapping rules reference Exodus 21. It supplies neither chapter
  indexes nor `basedOn`. We cannot safely recover a complete system by treating
  the arrays as sparse updates or choosing a parent system automatically.
- **Partial-verse labels:** 74 LXX entries contain trailing whitespace. Some
  labels include `-`. Both are retained exactly; segment normalisation and the
  meaning of the sentinel need an explicit policy before conversion.
- **Titles, reordering, and overlaps:** verse-zero references are listed as
  observed features, not automatically declared valid in every chapter.
  Overlapping source or target ranges retain all contributing rules. A finding
  may describe an intended split, merge, or alternative presentation rather
  than corrupt data.

### Diagnostic categories

| Category | Interpretation |
| --- | --- |
| `SCHEMA_COUNT_TYPE`, `SCHEMA_REFERENCE_SYNTAX` | A source representation differs from the copied schema. Counts can be normalised without changing numbering; suffix semantics still need review. |
| `REFERENCE_SYNTAX`, `REVERSED_RANGE`, `INVALID_COUNTS` | Structurally unusable input requiring correction or explicit rejection. |
| `UNDEFINED_BOOK`, `CHAPTER_OUTSIDE_COUNTS`, `VERSE_OUTSIDE_COUNTS` | An address cannot be established from the supplied array. This is not proof that the passage does not exist. |
| `UNEQUAL_RANGE_LENGTHS`, `RANGE_NOT_EXPANDED` | A group or segment model is needed; individual correspondences have not been guessed. |
| `SOURCE_OVERLAP`, `TARGET_OVERLAP` | Several explicit rules cover the listed addresses. Every contributing rule is retained in the finding. |
| `UNDECLARED_SEGMENT`, `SEGMENT_LABEL_WHITESPACE`, `INVALID_SEGMENT_LABELS`, `DUPLICATE_SEGMENT_LABEL` | Segment metadata needs review. |
| `INCOMPLETE_CUSTOM_COUNTS`, `INHERITANCE_NOT_RESOLVED` | The audit does not infer missing chapters or apply a parent definition. |
| `UNKNOWN_BASE`, `INHERITANCE_CYCLE` | The declared inheritance graph cannot be resolved as supplied. |

The structural auditor is purpose-built for this dataset. It is not advertised
as a general JSON Schema validator or proof of textual equivalence. It does not
enumerate implicit identities, resolve inherited rules, or test composed
source-to-reference-to-target relationships. Compiled coverage uses the mapping
engine separately, as described next.

### Compiled reference coverage

Report format `2` adds `systems.<name>.compiledReferenceCoverage`, computed from
the same engine definitions and supplement used by conversion. For every book
in `BOSReference`, it enumerates whole numbered verses and explicitly declared
verse-zero titles and separates:

- `representedCount`: addresses present in compiled relationships, including
  atomic group members and ambiguous alternatives. This is not an exactness or
  text-equivalence certificate; a group member alone may correctly be partial.
- `unmappedCount` / `unmappedRanges`: addresses with no relationship.
- `blockedCount` / `blockedRanges`: quarantined or explicitly unsupported
  addresses, including disabled systems and unresolved reference-book bridges.

Per-book counts sum to `referenceCount`, with totals also provided at system
level. Ranges are compact, inclusive, and never cross chapters. All reference
books are included, even those absent from a source's canon. Missing reference
title addresses and absent source books therefore remain visible; an unmapped
address alone is not evidence of a textual omission or permission to infer a
neighbouring mapping. Segment-level completeness and textual equivalence require
separate review. Use per-request results for exactness and ambiguity.

This audit exposes all eight originally reported missing Hebrew verses when run
without those eight corrections. With the supplement, those eight move from unmapped to
represented, while other gaps remain recorded. Tests compare both states and
also exercise complete/incomplete groups, neighbouring shifts, and loaded text.
`engine.audit_reference_coverage('eng')` returns this same inventory without
writing files. `mappingDataRevision` identifies the supplement content; the raw
`sourceSnapshot` and structural findings remain independently visible.

## Programmatic use and reproducibility

```python
from BibleOrgSys.Reference.Converters.BibleVersificationMappingsConverter import (
    load_bundle, build_reference, build_coverage_report,
)

bundle = load_bundle()  # Read local package resources and verify source hashes.
reference = build_reference(bundle)
report = build_coverage_report(bundle, reference)

assert reference['conversionReady'] is False
assert reference['books']['LAO']['maxVerses'] == [20]
print(report['legacyBooksMissingFromReference'])
```

Each call loads independent objects; there is no global mutable registry or
cache. JSON duplicate keys are rejected before information can be overwritten.
The audit and catalogue build do not modify the source objects. Generated files
contain no local absolute paths or wall-clock timestamps.

```sh
# Print findings summary without writing.
python -m BibleOrgSys.Reference.Converters.BibleVersificationMappingsConverter

# Verify source integrity and generated-file freshness.
python -m BibleOrgSys.Reference.Converters.BibleVersificationMappingsConverter --check

# Rebuild derived documents after a reviewed policy/auditor change.
python -m BibleOrgSys.Reference.Converters.BibleVersificationMappingsConverter --write

# Generate elsewhere for comparison.
python -m BibleOrgSys.Reference.Converters.BibleVersificationMappingsConverter --write --output-dir /tmp/bos-versification-review

# Run the offline regression suite.
python -m unittest discover -s Tests -p 'test_BibleVersificationMappingsData.py' -v
```

To include the actual wheel-distribution test after building a wheel, set its
path when running the same suite:

```sh
BOS_VERSIFICATION_TEST_WHEEL=/path/to/bibleorgsys-0.3.6-py3-none-any.whl python -m unittest discover -s Tests -p 'test_BibleVersificationMappingsData.py' -v
```

Without that variable, only the wheel-specific test is skipped; the isolated
zip-resource distribution test always runs. The wheel test verifies every file
in the new bundle, preservation of the existing packaged data, absence of a new
versification dependency, and a fresh audit from the wheel outside the checkout.

Exit code zero from `--check` means the source hashes and generated files agree.
It does not require zero findings; known unresolved findings are an intentional
part of this stage. Unknown or stale generated output and damaged source files
produce a nonzero exit. Reads work from installed and zipped package resources;
writing into a zipped package requires `--output-dir`.

## Maintaining the bundle

1. For an upstream update, deliberately select a source repository and exact
   commit. Copy the selected standard JSON files, custom example, schema,
   documentation, and licence notice into `Copenhagen/` without editing them.
   No automatic updater is installed, and downstream users never fetch them.
2. Update every corresponding `source-manifest.json` checksum, commit/date, and
   attribution notice. The manifest must cover exactly the bundled source files.
   A changed checksum alone is not evidence that a mapping correction is sound.
3. Review new/changed USFM book identities against `BibleBooksCodes.xml`, update
   the explicit crosswalk and its source hash, and preserve ambiguous choices.
   If existing BOS count tables change, refresh `legacy-inventory.json` from
   their `CV` keys and update its source hash. Tests compare these two local
   provenance snapshots against the repository's BOS source files.
4. Record any new reference-book choice and its rationale in
   `reference-policy.json`. Preserve the Hebrew/Greek core. A future change to
   published reference addresses requires a new reference version; mapping-rule
   corrections also need a tracked data revision.
5. Keep semantic mapping corrections in `mapping-supplement.json`, separate from
   the verbatim snapshot and from count-policy changes. Use BOS book codes,
   explicit ordered `source`/`target` groups, expected `replaceMappings`, and
   `remainingMappings` that retain every unaffected member of a replaced range.
   Record a unique id, reason, Copenhagen evidence rule and zero-based range
   index, and verification notes distinguishing textual checks from profile-data
   checks. New entries record source/reference chapter maxima as guards,
   including the selected columns' `=Last` conditions. Bump the supplement
   version for a reviewed revision. The adapter
   rejects stale old rules, overlapping corrections, invalid endpoints, missing
   evidence, stale chapter maxima, invalid evidence rows, and dropped/changed
   unaffected range members. The supplement's
   canonical JSON SHA-256 also enters result revisions, so even an unversioned
   edit is distinguishable. Reference-policy `corrections` remains reserved and
   empty; it does not apply this mapping supplement or alter reference counts.
6. Regenerate the three derived JSON files, review the full diff and coverage gaps,
   update the summary above when findings change, and run the tests and `--check`.
   Add bidirectional complete-group and partial-group regression cases for every
   correction, including every proper subset and unaffected chapter neighbours.
   Check the sniffing report for new candidates or changed edition assumptions;
   never promote all rows sharing a tradition label automatically.
   The default engine is cached in-process; restart long-running
   applications after changing installed mapping data.
7. Build a wheel and verify it contains the complete bundle, including notices,
   source JSON, policy, crosswalk, and generated documents. Run `--check` using
   only that distribution outside the checkout. Packaging explicitly includes
   the data directory as an artifact, avoiding duplicate archive entries from
   forcing files already included by package discovery. The unit suite checks zipped resources in
   an isolated interpreter without native modules or site packages.

No aliases from upstream names to historical BOS systems have yet been asserted.
For example, `eng` must not become `KJV` merely because their counts often agree.
The [stage-two engine](VersificationMappingAPI.md) preserves relationships and
reports unsupported, ambiguous, partial, and multiple-reference results. Its
availability does not resolve the remaining data restrictions or bridge choices.
