# Declaring a Bible's versification and converting references

The third implementation stage connects the bundled mapping engine to Bible
objects and loading. All formats derived from `Bible`/`InternalBible` share the
declaration and conversion methods. The existing `getVersification()` still
reports the chapter/verse structure observed in the loaded books.

A declaration selects the numbering profile used to interpret references. It
does not renumber the Bible, rewrite text, choose a canon, verify a translation's
textual equivalence, or prove that a requested passage exists in that Bible.
Conversions also work before books are loaded, making them useful with lazy
loaders and partial Bibles.

For text as well as addresses, use the [passage retrieval API](BiblePassages.md):
`targetBible.getMappedPassage(sourceSystem, references)` maps a complete passage
and retrieves all corresponding native text portions and contexts. Use
`getPassageData(references)` when the references are already native.

References use the selected profile's BOS book identities (for example, `EZN`
for the combined Ezra/Nehemiah source in `lxx`). A declaration does not rename
books selected by an existing format loader. If an import uses a different book
identity, that correspondence must be established explicitly before connecting
converted references to text retrieval; it is not guessed from similar names.

The data remain bundled and attributed; no upstream checkout, download, or new
runtime dependency is needed. See the [mapping API guide](VersificationMappingAPI.md)
for mapping statuses, grouped passages, limitations, and the draft reference policy.

## Explicit declarations

```python
from BibleOrgSys.Bible import Bible

english = Bible(versification='eng')
assert english.getVersificationSystemName() == 'eng'
assert english.convertToReferenceVersification('GEN', 31, 55) == ('GEN', '32', '1', None)
assert english.convertFromReferenceVersification('GEN', 32, 1) == ('GEN', '31', '55', None)

greek = Bible(versification='lxx')
assert english.convertToVersification(greek, 'GEN', 31, 55) == ('GEN', '32', '1', None)
```

`versification=` is an optional, keyword-only constructor argument on `Bible`,
`USFMBible`, `USXXMLBible`, `PTX8Bible`, `ESFMBible`, `OSISXMLBible`, `PickledBible`,
and `UnknownBible`. Existing positional arguments retain their meanings.

Every Bible format also supports `bible.setVersificationSystem('eng')`, including
formats whose constructors do not yet have this keyword. Call it after creating
the object and before `load()`, `loadBooks()`, or `preload()`. The setter returns
the Bible for chaining. Changing it later changes reference interpretation only.
It is never necessary to reload or renumber the text to change a declaration.

Names are case-sensitive BOS registry names. A `BibleVersificationSystem` object
can be supplied instead of a name. Unknown caller names raise
`UnknownVersificationSystemError` without changing the current declaration;
wrong argument types raise `TypeError`. No profile is guessed from the Bible's
name, language, file format, observed verse counts, or generic organisational
system used by an exporter.

Historical names such as `KJV`, `Original`, and `Vulgate` still select their
independent BOS count-only systems. They can be declared but have no verified
conversion profile. `ethiopian_custom` is also unavailable for conversion.
`getMappingCapabilities()` explains availability; individual conversion results
remain authoritative.

## Loading a Bible

This complete example creates a small local USFM fixture, loads it, and leaves
the loaded verse address and text intact:

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from BibleOrgSys.Formats.USFMBible import USFMBible
from BibleOrgSys.Reference.VerseReferences import SimpleVerseKey

with TemporaryDirectory() as folder:
    Path(folder, '01GEN.usfm').write_text(
        '\\id GEN Example\n\\usfm 3.0\n\\h Genesis\n\\c 1\n\\p\n\\v 1 Example text.\n',
        encoding='utf-8',
    )
    loaded = USFMBible(folder, versification='eng')
    loaded.load()
    assert loaded.convertToReferenceVersification('GEN', 1, 1) == ('GEN', '1', '1', None)
    assert 'Example text.' in loaded.getVerseText(SimpleVerseKey('GEN', '1', '1'))
```

For a real project, pass its folder to the same constructor. With automatic
format detection, use `UnknownBible(path, versification='eng').search(autoLoadBooks=True)`.
The declaration is applied to the returned Bible after the format checker has
loaded it, preserving metadata evidence from the loader. Detection-only calls
keep their existing count/status return values. A declaration does not resolve
multiple detected Bibles or alter which one the existing detection API selects.
Only the selected format's module is imported during automatic loading.

## Precedence and conflicts

1. An explicit constructor/setter declaration takes precedence over metadata.
2. Without an explicit declaration, all available metadata observations must
   resolve to the same system. No metadata source wins merely by loading last.
3. Disagreeing recognised names leave the Bible in `conflict`; conversion is
   `ambiguous`, with no guessed candidate references.
4. Unknown, blank, malformed, or unimplemented custom metadata leaves it
   `unresolved`; conversion is `unsupported`. Another recognised declaration
   does not erase that uncertainty.
5. With no declaration at all, the Bible is `undeclared`; conversion is
   `unsupported`. There is no default English or KJV mapping.

```python
english.suppliedMetadata = {'Project': {'VersificationSystem': 'vul'}}
english.applySuppliedMetadata('Project')
declaration = english.getVersificationDeclaration()
assert declaration['system'] == 'eng'
assert declaration['source'] == 'caller'
assert declaration['diagnostics'][0]['code'] == 'VERSIFICATION_CONFLICT'

english.clearVersificationSystem()  # Clear only the caller's override.
assert english.getVersificationSystemName() == 'vul'
english.setVersificationSystem('eng')
```

`getVersificationDeclaration()` returns a detached dictionary with `status`
(`declared`, `undeclared`, `unresolved`, or `conflict`), effective `system`,
`source` (`caller`, `metadata`, or `None`), explicit choice, metadata observations,
and diagnostics. Each observation includes its source, field, raw value,
namespace, interpreted system, and any blocking reason. Reapplying a source
refreshes that source's observations rather than accumulating duplicate records.

Diagnostics use `UNDECLARED_VERSIFICATION`, `VERSIFICATION_CONFLICT`, and
`UNRESOLVED_VERSIFICATION_METADATA`. Overrides preserve these diagnostics even
when conversion succeeds. Inspect the declaration or request `detailed=True` to
see them; the default exact four-tuple result cannot carry diagnostic fields.
`getVersificationSystem()` returns a fresh system object when resolved, otherwise
`None`. `clearVersificationSystem()` re-evaluates the retained metadata.

Direct assignments to `settingsDict` are not declarations. Use the setter for
caller intent, or apply metadata through the loader's existing metadata API.

## Metadata recognised by this stage

| Source | Field and interpretation |
| --- | --- |
| Generic `applySuppliedMetadata()` sources, including `File` and `Project` | `Versification` or `VersificationSystem`, ignoring field-name case and surrounding whitespace; values use exact BOS names after trimming surrounding whitespace. |
| `PTX8` project settings and `PTX7`/`SSF` supplied metadata | `Versification`, interpreted in the Paratext namespace below. |
| Plain USFM and USX project folders | Direct-child `Settings.xml` and `*.ssf` files, with a `ScriptureText` root and `Versification` element. Multiple files/elements are retained independently. Parent directories are not searched. Other settings are left to their existing loaders. |
| OSIS files | `refSystem` under the header `work` matching `osisText/@osisIDWork`. Other works and `osisRefWork` do not declare this Bible's numbering. |

The verified Paratext built-ins resolve as follows:

| Numeric ID | Paratext name | Bundled BOS profile |
| --- | --- | --- |
| `1` | `Original` | `org` |
| `2` | `Septuagint` | `lxx` |
| `3` | `Vulgate` | `vul` |
| `4` | `English` | `eng` |
| `5` | `RussianProtestant` | `rsc` |
| `6` | `RussianOrthodox` | `rso` |

These numeric/name identities follow SIL's
[`ScrVersType` enumeration](https://github.com/sillsdev/libpalaso/blob/master/SIL.Scripture/Versification.cs)
(checked 2026-10-12); their pairing with bundled profiles follows the copied
[Copenhagen standard definitions](../BibleOrgSys/DataFiles/VersificationMappings/Copenhagen/versification-mappings/standard-mappings/README.md).
The aliases apply only to Paratext metadata, not to explicit BOS caller names.
Exact bundled profile names are also accepted in that namespace.

Paratext ID `0`, `Unknown`, and custom names are unresolved. Any local `.vrs`
file or supplied custom versification table blocks automatic use of its presumed
base profile. An unreadable project directory also prevents assuming there are
no overrides. An explicit caller declaration may override this uncertainty, with
the reason retained. This stage does not parse custom VRS rules into a new mapping
profile or infer inheritance. ESFM offers the explicit declaration API; its own
metadata conventions are unchanged.

OSIS exact BOS names are recognised. `Bible.KJV` is recognised as historical BOS
`KJV`, which remains count-only. Generic `Bible` and other unverified identifiers
are unresolved. The work-aware header scan runs before either native or Python
text parsing and before parallel workers are started. Multi-file disagreements
therefore survive loading. Flat `suppliedMetadata['OSIS']['RefSystem']` values are
not used, because older parsers may have overwritten them with another work's
scheme. Files without their own work declaration remain undeclared.

## Reference and passage APIs

Bible objects expose the same single-reference calls and result/exception
contract as the [system APIs](VersificationMappingAPI.md):

- `convertToReferenceVersification(BBB, C, V, S=None, detailed=False)`
- `convertFromReferenceVersification(BBB, C, V, S=None, detailed=False)`
- `convertToVersification(targetSystem, BBB, C, V, S=None, detailed=False)`

`detailed` is keyword-only. The target can be a name, system object, or another
Bible whose declaration is resolved. Both source and target Bible diagnostics
are attached to the result. An unresolved target cannot silently become the
source's scheme. Mapping ambiguity, exclusions, unsupported textual bridges,
and invalid references retain the engine's existing behavior.

For groups, discontinuous passages, or ranges, these always return `MappingResult`:

- `convertReferencesToVersification(targetSystem, references)`
- `convertReferencesFromReferenceVersification(references)`
- `convertRangeToVersification(targetSystem, startRef, endRef)`
- `convertRangeFromReferenceVersification(startRef, endRef)`

```python
from BibleOrgSys.Reference.BibleVersificationMappings import MappingStatus

passage = english.convertRangeToVersification(
    'BOSReference', ('GEN', 31, 55), ('GEN', 32, 1),
)
assert passage.status == MappingStatus.EXACT
assert passage.references == (('GEN', '32', '1', None), ('GEN', '32', '2', None))
restored = english.convertReferencesFromReferenceVersification(passage.references)
assert restored.references == (('GEN', '31', '55', None), ('GEN', '32', '1', None))
```

For actual text access, pass the resulting addresses to the appropriate Bible's
existing retrieval methods. Resolve unsupported or ambiguous results explicitly
before attempting retrieval. Exact numbering correspondence does not guarantee
that a partial Bible has the corresponding book or verse loaded/available.

## Persistence and compatibility

The declaration is saved as a versioned JSON string containing only names and
metadata evidence. Compiled engine tables are shared separately and never saved
on a Bible object. Ordinary Python pickle/deepcopy, the minimal BOS attribute
archive (including its zipped form), and fast `.BOSBible` containers preserve it.
Fast-container declarations are available before their books are loaded.

Old objects without the field remain undeclared, even if their raw settings
contain a plausible name. A new caller override when opening a saved Bible takes
precedence while retaining the saved declaration as evidence. No changes to
stored Bible verse addresses or the pickle format version are needed.

The integration also repairs the missing version-header slot in the legacy BOS
attribute writer and several fast-loader defects that prevented a fresh archive
from reopening correctly. Other pre-existing limitations of non-minimal legacy
archive modes are outside the declaration feature's scope.

## Tests and remaining data work

```sh
.venv/bin/python -m unittest Tests.test_BibleVersificationMappingsData Tests.test_BibleVersificationMappings Tests.test_BibleVersificationLoading
python -m BibleOrgSys.Reference.Converters.BibleVersificationMappingsConverter --check
```

Set `BOS_VERSIFICATION_TEST_WHEEL` to a newly built wheel to additionally verify
packaged data, isolated engine use, and loading/conversion from an extracted
wheel outside the checkout. Integration tests use BOS's existing native modules.
They cover real USFM/USX/Paratext/OSIS loading, both OSIS parser paths, parallel
headers, metadata precedence, ambiguity, unchanged text/counts, automatic format
detection, and declaration persistence. The Python examples above also run as tests.

The planned three implementation stages are complete. `BOSReference` remains
`1-draft`; unresolved textual bridges, segment inventories, and custom inheritance
still require evidenced data decisions. Their unsupported results remain explicit.
