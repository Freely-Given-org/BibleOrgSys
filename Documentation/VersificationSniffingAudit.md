# Copenhagen sniffing audit and BOS supplement revision 2

BOS audited all **403 rules / 1,466 rows** in the bundled Copenhagen sniffing
snapshot. **556 rows** are explicitly tagged `SubdividedVerse` (427) or
`MergedVerses` (129). Revision 2 adds **46 reviewed mapping groups**: three for
`eng` and 43 for `vul`. Together with revision 1's eight corrections, the runtime
supplement now contains 54 groups. No external repository or online data source
is needed to run conversions, reproduce the audit, or run the tests.

The verbatim Copenhagen files, source commit, reference counts, reference
version `1-draft`, and mapping policy `2` are unchanged. Mapping data results
now identify `+bos-supplement-2.<canonical-json-sha256>` after the pinned commit.
Recompute affected stored conversions: some formerly exact singleton results
are now correctly partial until all members of their group are supplied.

## Evidence and acceptance criteria

The evidence is the copied
[`merged_rules.json`](../BibleOrgSys/DataFiles/VersificationMappings/Copenhagen/versification-sniffing/rules/merged_rules.json)
from commit `519af776ab65d89a51e37f750779250f940459ef`. Attribution to Copenhagen,
Tyndale/STEPBible TVTMS, and David Instone-Brewer is retained in the
[bundle notice](../BibleOrgSys/DataFiles/VersificationMappings/README.md).
The adapted data and generated report retain CC BY-SA 4.0; the BOS audit code
and tests have MPL-2.0 notices. No upstream sniffing program is executed.

A sniffing row describes possible numbering traditions, not an unconditional
mapping between BOS profiles. Each accepted addition was checked against its
specific unqualified tradition column, the bundled source and reference counts,
existing mapped endpoints, and surrounding shifts. Matching chapter maxima are
necessary but not sufficient. The Latin additions have explicit final-member
or duplicated-endpoint relationships in the raw standard profile; the reviewed
row establishes the complete group. The supplement records the rules removed,
the exact unchanged remainder of any wider range, the source row index, selected
columns, and count guards. The Numbers Latin addition inherits the previously
verified completion of the truncated Hebrew cross-chapter address.

Direct text checks were also made for the three new English groups. OET-LV
Psalm 13:6 contains both the trust/rejoicing and singing clauses, separated in
OET-RV 13:5–6. OET-LV Isaiah 63:19 contains both the never-ruled-us clause and the
plea to open the heavens, separated in OET-RV 63:19 and 64:1. Acts 19:40 in
OET-LV contains the speech ending and dismissal, whereas the local KJV fixture
has the dismissal in 19:41. These texts are optional maintainer evidence,
**not test or runtime dependencies**. Latin verification was against the pinned
profile data and semantic sniffing rows; it was not a fresh collation of every
Latin edition.

OET-RV also already combines the Acts passage in 19:40. Consequently, `eng`
cannot be assumed to describe every OET-RV passage. A translation can mix
numbering traditions; callers must select a profile appropriate to the edition.
The audit does not create per-translation aliases or automatically detect a
loaded Bible's versification.

## Added correspondences

BOS book codes are used below (`CH1` = 1 Chronicles, `MA2` = 2 Maccabees).
Each side is a complete, ordered group. Arrows work in both directions. A proper
subset on a multi-verse side yields `partial`, with no exact result references.
This applies even to a member formerly accepted alone. The three-member Exodus
group also rejects two-member subsets. Ranges and mappings composed through
`BOSReference` retain these requirements.

| Profile | Source group | `org` / `BOSReference` group |
| --- | --- | --- |
| `eng` | `PSA 13:5-6` | `PSA 13:6` |
| `eng` | `ISA 63:19` + `ISA 64:1` | `ISA 63:19` |
| `eng` | `ACT 19:40-41` | `ACT 19:40` |
| `vul` | `GEN 50:22` | `GEN 50:22-23` |
| `vul` | `EXO 40:13` | `EXO 40:13-15` |
| `vul` | `LEV 26:45` | `LEV 26:45-46` |
| `vul` | `NUM 11:34` | `NUM 11:34-35` |
| `vul` | `JOS 4:23-24` | `JOS 4:23` |
| `vul` | `JOS 5:14-15` | `JOS 5:14` |
| `vul` | `JOS 21:36` | `JOS 21:36-37` |
| `vul` | `JOS 21:37` | `JOS 21:38-39` |
| `vul` | `JDG 5:31-32` | `JDG 5:31` |
| `vul` | `JDG 21:24` | `JDG 21:24-25` |
| `vul` | `CH1 11:46` | `CH1 11:46-47` |
| `vul` | `CH1 12:4` | `CH1 12:4-5` |
| `vul` | `CH1 20:7` | `CH1 20:7-8` |
| `vul` | `NEH 3:30` | `NEH 3:30-31` |
| `vul` | `NEH 12:33` | `NEH 12:33-34` |
| `vul` | `JOB 16:4-5` | `JOB 16:4` |
| `vul` | `JOB 42:16` | `JOB 42:16-17` |
| `vul` | `PSA 2:12-13` | `PSA 2:12` |
| `vul` | `PSA 4:9-10` | `PSA 4:9` |
| `vul` | `PSA 10:1-2` | `PSA 11:1` |
| `vul` | `PSA 12:1` | `PSA 13:1-2` |
| `vul` | `PSA 12:2-3` | `PSA 13:3` |
| `vul` | `PSA 43:22` | `PSA 44:22-23` |
| `vul` | `PSA 55:11` | `PSA 56:11-12` |
| `vul` | `ISA 63:19` + `ISA 64:1` | `ISA 63:19` |
| `vul` | `JER 37:4` | `JER 37:4-5` |
| `vul` | `EZE 2:9` | `EZE 2:9-10` |
| `vul` | `HOS 2:23-24` | `HOS 2:25` |
| `vul` | `AMO 6:10-11` | `AMO 6:10` |
| `vul` | `MIC 5:11` | `MIC 5:10-11` |
| `vul` | `WIS 5:13-14` | `WIS 5:13` |
| `vul` | `WIS 6:1-2` | `WIS 6:1` |
| `vul` | `WIS 6:22-23` | `WIS 6:21` |
| `vul` | `WIS 9:18-19` | `WIS 9:18` |
| `vul` | `WIS 11:5-6` | `WIS 11:5` |
| `vul` | `WIS 19:12` | `WIS 19:12-13` |
| `vul` | `WIS 19:20` | `WIS 19:21-22` |
| `vul` | `MA2 2:18-19` | `MA2 2:18` |
| `vul` | `MAT 17:14` | `MAT 17:14-15` |
| `vul` | `MRK 4:40` | `MRK 4:40-41` |
| `vul` | `ACT 7:55` | `ACT 7:55-56` |
| `vul` | `ACT 14:6` | `ACT 14:6-7` |
| `vul` | `NUM 26:1` | `NUM 25:19` + `NUM 26:1` |

The [revision-1 table](VersificationMappingAPI.md#reviewed-englishhebrew-group-corrections)
records the eight earlier corrections. Those remain covered by their original
regressions, including Psalm titles at verse zero. The new Psalm 13:5–6 merge
concerns body verses, not a title.

## What remains deferred

The generated
[`sniffing-audit-report.json`](../BibleOrgSys/DataFiles/VersificationMappings/sniffing-audit-report.json)
retains every source row with its rule/range index, column labels, raw references,
and sniffing conditions. Every explicit split/merge row has a separate assessment
for `eng`, `vul`, and `lxx`. Labels such as `Greek2`, `Greek*`, `GreekUndivided`,
`Latin2`, Slavonic and Bulgarian are not silently aliased to those profiles.
`rsc`, `rso` and `ethiopian_custom` have an explicit report-level explanation for
why no matching edition column was established.

The 1,668 assessments (556 rows × 3 profiles) break down as follows. These are
row/profile counts, **not verse counts or a measure of textual completeness**.

| Assessment | Count | Meaning |
| --- | ---: | --- |
| `reviewed-correction` | 54 | Applied supplement with recorded evidence and regressions. |
| `positional-alignment-covered` | 236 | These two columns already align verse by verse; another column accounts for the row's split/merge label. |
| `title-convention-covered` | 59 | English title 0 plus body verse 1 already covers the Hebrew group. No body verse is absorbed into the title. |
| `same-column` | 842 | The row does not distinguish these candidate traditions; this does not certify equivalence of their BOS profiles. |
| `no-group-difference` | 24 | Whole-verse groups listed in the two columns are identical; no new group is implied. |
| `candidate-needs-review` | 14 | Disagrees with compiled mappings; a specific edition/content/neighbouring-shift concern is recorded. |
| `notation-or-domain-review` | 14 | Truncated/segmented notation, absent entries, or endpoints outside the profile prevent a reliable comparison. |
| `edition-not-selected` | 61 | No unique unqualified tradition column matches the candidate profile. |
| `witness-or-book-bridge-review` | 87 | Esther, Tobit, Baruch/Letter of Jeremiah or Esdras requires witness/book-bridge reconciliation. |
| `textual-tradition-blocked` | 277 | Latin Sirach/Judith/Tobit remains blocked under the existing upstream textual restriction. |

Notable deferred cases:

- **LXX Exodus 28, Deuteronomy 14, Isaiah 64, Hosea 2, Micah 5 and Zephaniah 2:**
  the sniffing Greek column's last-verse conditions disagree with the supplied
  `lxx` chapter counts. Importing those rules would mix editions. Proverbs 20's
  proposed relocation to verse 9 likewise has no supporting raw chapter maps.
- **Latin Exodus 39:** several split/merge rows occur within a larger shifted,
  duplicated and moved passage, while `vul` supplies no chapter-39 rules.
  Correcting a group alone would collide with the existing identity mappings.
- **English Baruch 3:34:** counts agree with the row, but both the 34 → 34–35
  group and all following shifts are absent. Text verification and a coherent
  correction of the whole passage are needed together.
- **Latin Wisdom 17:9:** the Greek sniffing column expects 21 verses, but `org`
  supplies 20. The reference edition needs to be established first.
- **Latin 2 Maccabees 15:37–38:** the raw profile puts the split a verse earlier
  than the sniffing rule. Neither source is automatically preferred.
- **Esdras and witness/composite books:** names and chapter counts alone do not
  establish that source and reference address the same witness or extract.
- **Latin Psalm 42:6, 125:7 and 135:27:** the sniffing endpoints exceed the
  registered profile's chapter maxima. Counts are not extended speculatively.
- **Truncated Samuel and segmented Genesis/Greek material:** no suffix inventory
  or missing endpoint is invented. The earlier text-verified English Samuel
  correction does not automatically redefine the Latin verse divisions.

The other 910 rows remain in the inventory: 734 are `OneToOne`, including two
malformed Esther rows whose values do not match the number of column labels;
176 describe missing, duplicated, moved or extended content. The latter include
`DuplicateTarget` and `LongVerseElsewhereJoin`, so they remain visible for future
text/segment review rather than being omitted from the audit. Positional and
textual-content rows are not automatically imported as groups.

An audit finding does not itself change a runtime mapping or quarantine a whole
book. Existing restrictions remain enforced, and only the reviewed supplement
changes the compiled relationships. An `exact` result in a deferred passage is
therefore a statement about the current declared profile, not resolution of the
reported textual/edition conflict. Consult both the report and per-request
status when assessing coverage.

## Reproduction and further corrections

```sh
python -m BibleOrgSys.Reference.Converters.BibleVersificationMappingsConverter --check
python -m unittest Tests.test_BibleVersificationSniffingAudit Tests.test_BibleVersificationSupplement
```

Use the project `.venv/bin/python` for native Bible loading and text retrieval
checks; the data/audit/engine tests also run under ordinary Python. A plain
Python environment skips only the native integration checks. The wheel/zip tests
run without site packages, native modules, network access or the upstream checkout.

`--write` regenerates the catalogue, coverage report and sniffing report from
bundled inputs. All three participate in `--check`. The audit parser accepts
only complete numeric notation; it does not execute Copenhagen's sniffing tests.
Recorded `=Last` conditions for accepted corrections are cross-checked in the
regression suite and retained as runtime supplement count guards.

For a further correction, establish the edition, full group and neighbouring
shifts; record its evidence and expected old rules in the supplement; add an
independent expected correspondence to the tests; and bump the supplement
revision. Test complete groups in both directions, **every proper subset**,
range/composed conversion, unaffected neighbours, and native text retrieval.
Then regenerate and inspect the reports and check the built wheel. See the
[data maintenance guide](VersificationMappings.md#maintaining-the-bundle).
