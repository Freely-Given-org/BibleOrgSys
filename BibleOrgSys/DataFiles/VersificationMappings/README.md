# Bundled versification mapping data

This directory is BOS's self-contained copy of the Copenhagen Alliance
versification data, together with a provisional BOS reference catalogue and a
reproducible coverage audit. No upstream repository, network connection, native
extension, or third-party Python package is needed to read or audit this bundle.

`BOSReference` version `1-draft` defines 102 candidate book or
witness entries. It is a counts catalogue, not a certified mapping system. Some
entries are composite or extract views of other entries. It does not imply 102
independent works or a particular canon. The
[stage-two mapping engine](../../../Documentation/VersificationMappingAPI.md)
now converts supported references and reports unresolved relationships explicitly.
[Bible-loading integration](../../../Documentation/BibleVersification.md) now adds
declarations, metadata resolution, and Bible-level conversions. The structural audit's
`conversionReady: false` continues to record the lack of global certification.

## Contents

| File or directory | Purpose |
| --- | --- |
| `Copenhagen/` | Byte-for-byte source snapshot: seven standard JSON definitions, one custom example, schema, documentation, licence overview, and the sniffing rules used as supplemental evidence. |
| `source-manifest.json` | Repository URLs, exact source commit, import date, original paths, and SHA-256 checksums for every copied file. |
| `book-codes.json` | Explicit USFM-to-BOS identity crosswalk, alternative BOS identities, and source-specific exceptions. |
| `legacy-inventory.json` | Book inventories from the existing BOS systems, with the source file's checksum; used to identify remaining gaps. |
| `reference-policy.json` | BOS reference choices, their reasons, known textual restrictions, and unresolved bridge decisions. |
| `mapping-supplement.json` | 54 reviewed English/Latin group corrections (revision 2), with expected old rules, unaffected remainders, evidence, attribution, and a separate revision. |
| `kjv-mapping.json` | Reviewed KJV OT/NT conversion (updated 2026-10-22), preserving all 80 historical book counts while blocking unreviewed Apocrypha conversions. |
| `bibletags-nt-mapping.json` | Reviewed BibleTags Greek NT profile (2026-10-22): split Acts 19:40–41, original 2 Corinthians 13:12–13; source evidence is recorded in the profile. |
| `vlt-mapping.json` | Reviewed VLT v3 NT source profile (2026-10-21), including its PHP 1:16-17 ordering; see [the profile guide](../../../Documentation/KJVVersification.md). |
| `wycliffe-mapping.json` | Wycliffe Zefania LAO review (2026-10-30): explicit English navigation and atomic 15–16 correspondence, preserving OBD's previous `vul` declaration elsewhere. See [the witness review and limits](../../../Documentation/WycliffeVersification.md). |
| `BOSReference.json` | Generated provisional reference catalogue, using BOS book codes and integer chapter maxima. Each book identifies its source definition. |
| `coverage-report.json` | Raw structural findings plus compiled reference-address coverage, including unmapped and blocked ranges. |
| `sniffing-audit-report.json` | All 403 sniffing rules / 1,466 rows, with explicit profile assessments for 556 split/merge rows and reasons for deferred findings. |

The detailed design, interpretation of findings, and maintenance procedure are
in [Documentation/VersificationMappings.md](../../../Documentation/VersificationMappings.md).

## Attribution and licences

The source work is the
[Copenhagen Alliance Versification Working Group's versification specification](https://github.com/Copenhagen-Alliance/versification-specification).
This snapshot was copied from the
[Freely-Given-org fork](https://github.com/Freely-Given-org/versification-specification)
at commit `519af776ab65d89a51e37f750779250f940459ef`, on 2026-10-12. The fork is
identified explicitly: its commit need not exist in the original repository.

The Working Group documentation names Mark Howe, David Instone-Brewer, Chris
Vaughn, Andi Wu, Tim Steenwyk, and Jonathan Robie. The copied
[standard-mappings README](Copenhagen/versification-mappings/standard-mappings/README.md)
credits the data contributors:

- `org`: Neil Rees (“Studge”).
- `lxx`: Reinier de Blois, Neil Rees, Mike Lothers, and Tim Steenwyk.
- `vul`: Neil Rees.
- `eng`: Reinier de Blois and Neil Rees.
- `rsc`: Peter Kirk, with corrections credited to Matjaz Crnivec.
- `rso`: Peter Kirk, with modifications credited to Matjaz Crnivec and Neil Rees.
- `ethiopian_custom`: Bible Society of Ethiopia, with modifications by Neil Rees.

The copied [licence overview](Copenhagen/LICENSE.md) declares non-code content
under [Creative Commons Attribution-ShareAlike 4.0 International](https://creativecommons.org/licenses/by-sa/4.0/).
The Copenhagen data and documentation, and BOS's adaptations of that data in
this directory, retain that licence. Preserve this attribution, the licence
link, the copied notices, and the record of modifications when redistributing.

The additional `versification-sniffing/rules/merged_rules.json` and its README
come from the same pinned commit. Copenhagen derives these rules from
Tyndale/STEPBible's TVTMS (Tyndale Versification Traditions with Methodology for
Standardisation), associated with David Instone-Brewer; see the
[STEPBible data project](https://github.com/STEPBible/STEPBible-Data) and
[STEP Bible](https://www.stepbible.org/).
The sniffing code is not copied or executed. Its rule notation is evidence for
review, not an automatically applied second mapping system.

Modifications are kept separate from the verbatim source files: BOS adds the
book-code crosswalk, reference policy, source manifest, legacy comparison,
mapping supplement, and generated reference/audit documents. Generated reference
counts are converted from decimal strings to integers. Supplement revision `1`
corrects eight incomplete `eng` relationships: Numbers 26:1, 1 Samuel 20:42,
1 Kings 22:43, 1 Chronicles 12:4, and the titles of Psalms 51, 52, 54, and 60.
Each now identifies the complete two-verse Hebrew group. Verification notes
record comparison with the Open English Translation LV/RV texts; those texts
are not bundled here or required to run the supplement. Revision `2` adds three
`eng` groups and 43 `vul` groups, including Wisdom and 2 Maccabees. The
[sniffing audit guide](../../../Documentation/VersificationSniffingAudit.md)
lists every new correction, explains verification against the pinned profile
data, and distinguishes that review from direct text collation. Edition,
notation and textual-tradition conflicts remain explicit audit findings.
The legacy book catalogue and inventory come from existing BOS data;
their source paths and hashes are recorded in their respective JSON files.

The upstream overview separately describes an Apache-2.0 code licence. **No
upstream executable code is copied.** The new BOS audit program, mapping engine, and tests
carry their own MPL-2.0 source-file notices, consistent with neighbouring BOS
Python modules. Data attribution is not replaced by the package's code licence.

## Reproduce the audit

From an installed BOS package or the BOS repository:

```sh
python -m BibleOrgSys.Reference.Converters.BibleVersificationMappingsConverter --check
```

`--check` verifies the copied source hashes, validates the supplement, and compares all three generated JSON
documents with freshly computed results. A successful exit means the audit is
reproducible, **not** that its findings are resolved.

To regenerate after an intentional policy or audit change:

```sh
python -m BibleOrgSys.Reference.Converters.BibleVersificationMappingsConverter --write
```

Use `--output-dir /path/to/review` with `--write` to inspect generated documents
without replacing the bundled versions. Running with no arguments prints a
summary without writing anything.

Run the offline tests from the repository:

```sh
python -m unittest discover -s Tests -p 'test_BibleVersificationMappingsData.py' -v
python -m unittest Tests.test_BibleVersificationSupplement
python -m unittest Tests.test_BibleVersificationSniffingAudit
```

`oet-rv-mapping.json` version 3 declares 81 source books (66 core + 15 DC).
`oet-lv-mapping.json` version 3 declares 82 (66 core + 14 Brenton DC + Swete
PSS/ODE). The LV DC mappings are fully bundled and reference-directed, with
native inventories, attribution, source hashes, chapter shifts and atomic
split/merge groups. 5,511 RV DC verse requests retrieve corresponding LV
passages with explicit group expansion; there is no external repository or
text-matching dependency.

Ordinary Greek Esther intervals and Daniel's Susanna/Bel chapters are mapped.
Esther additions, Daniel 1–12, Tobit 13:6–10, and LV PSS/ODE remain explicit
unverified bridges. LV has no LES file and omits some numbered Sirach labels.
See [the profile guide](../../../Documentation/OETVersification.md) for exact
limits, suffix semantics, attribution, source evidence and offline tests.
