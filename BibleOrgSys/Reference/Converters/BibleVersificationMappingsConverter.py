#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Audit BOS's bundled Copenhagen data and build its provisional reference catalogue.

The raw structural findings are retained separately from compiled relationship
coverage, which applies BOS's reviewed supplement and declared identity policy.
A successful run means that findings are reproducible, not that every mapping
is correct. See DataFiles/VersificationMappings/README.md.

The module uses only the standard library and package resources. Neither the
Copenhagen repository nor BOS's native extensions are needed to reproduce the
checked-in reference and coverage report::

    python -m BibleOrgSys.Reference.Converters.BibleVersificationMappingsConverter --check

CHANGELOG:
    2026-10-22 Bundle the verified BibleTags Greek NT profile.
    2026-10-21 Bundle reviewed KJV NT and VLT v3 mapping profiles.
    2026-10-22 Include KJV OT and explicit OET-RV/OET-LV source profiles.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
from importlib.resources import files
import json
from pathlib import Path
import re


STANDARD_SYSTEMS = ('org', 'eng', 'lxx', 'vul', 'rsc', 'rso', 'ethiopian_custom')
GENERATED_FILES = ('BOSReference.json', 'coverage-report.json', 'sniffing-audit-report.json')
_REFERENCE_PATTERN = re.compile(
    r'(?P<book>[A-Z1-6]{3}) (?P<chapter>[0-9]+):'
    r'(?P<first>[0-9]+)(?P<first_suffix>[a-z]*)'
    r'(?:-(?P<last>[0-9]+)(?P<last_suffix>[a-z]*))?'
)


class VersificationDataError(ValueError):
    """Bundled data is corrupt, structurally unusable, or cannot be reproduced."""


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise VersificationDataError(f'Duplicate JSON key: {key!r}')
        result[key] = value
    return result


def _read_json(resource):
    return json.loads(resource.read_text(encoding='utf-8'), object_pairs_hook=_unique_object)


def _resource_root():
    return files('BibleOrgSys').joinpath('DataFiles', 'VersificationMappings')


def _relative_resource(root, relative):
    """Manifest entries must stay inside the bundled dataset."""
    parts = relative.split('/')
    if not relative or any(p in ('', '.', '..') for p in parts) or '\\' in relative:
        raise VersificationDataError(f'Invalid bundled path: {relative!r}')
    return root.joinpath(*parts)


def load_bundle(root=None):
    """Read and verify the local snapshot; return new mutable objects each time.

    ``root`` is an optional directory containing a complete copy of the bundle,
    primarily for maintainers and tests. It never refers to an upstream checkout.
    """
    root = _resource_root() if root is None else Path(root)
    manifest = _read_json(root.joinpath('source-manifest.json'))
    expected_paths = {
        'Copenhagen/LICENSE.md',
        'Copenhagen/README.md',
        'Copenhagen/versification-mappings/README.md',
        'Copenhagen/versification-mappings/standard-mappings/README.md',
        'Copenhagen/versification-mappings/json-schema/versification_schema.json',
        'Copenhagen/versification-mappings/sample-custom-mappings/one_versification.json',
        'Copenhagen/versification-sniffing/README.md',
        'Copenhagen/versification-sniffing/rules/merged_rules.json',
        *(f'Copenhagen/versification-mappings/standard-mappings/{name}.json'
          for name in STANDARD_SYSTEMS),
    }
    manifest_paths = [entry['path'] for entry in manifest['files']]
    if set(manifest_paths) != expected_paths or len(manifest_paths) != len(expected_paths):
        raise VersificationDataError('Source manifest must cover each bundled source exactly once')
    for entry in manifest['files']:
        resource = _relative_resource(root, entry['path'])
        actual = hashlib.sha256(resource.read_bytes()).hexdigest()
        if actual != entry['sha256']:
            raise VersificationDataError(f"Source checksum mismatch: {entry['path']}")
    upstream = root.joinpath('Copenhagen', 'versification-mappings')
    return {
        'manifest': manifest,
        'systems': {name: _read_json(upstream.joinpath('standard-mappings', f'{name}.json'))
                    for name in STANDARD_SYSTEMS},
        'sample': _read_json(upstream.joinpath('sample-custom-mappings', 'one_versification.json')),
        'bookCodes': _read_json(root.joinpath('book-codes.json')),
        'policy': _read_json(root.joinpath('reference-policy.json')),
        'legacy': _read_json(root.joinpath('legacy-inventory.json')),
        'supplement': _read_json(root.joinpath('mapping-supplement.json')),
        'additionalMappings': [_read_json(root.joinpath(filename)) for filename in
                               ('luther-mapping.json', 'kjv-mapping.json', 'vlt-mapping.json',
                                'bibletags-nt-mapping.json', 'oet-rv-mapping.json', 'oet-lv-mapping.json')],
        'supplementEvidence': _read_json(root.joinpath('Copenhagen', 'versification-sniffing',
                                                      'rules', 'merged_rules.json')),
    }


def bos_book_code(usfm_book: str, system: str, book_codes: dict) -> str:
    """Resolve catalogue identity, including LXX's combined Ezra-Nehemiah.

    This crosswalk does not establish passage equivalence or merge witnesses.
    Mapping destinations must be resolved in their destination system's context.
    """
    override = book_codes['systemOverrides'].get(system, {}).get(usfm_book)
    if override:
        return override['bosCode']
    try:
        return book_codes['books'][usfm_book]['bosCode']
    except KeyError as error:
        raise VersificationDataError(f'Unknown source book code: {usfm_book}') from error


def _verse_counts(values):
    if not isinstance(values, list) or not values:
        raise VersificationDataError('Chapter counts must be a nonempty list')
    result = []
    for value in values:
        if type(value) is int and value >= 0:
            result.append(value)
        elif isinstance(value, str) and re.fullmatch(r'[0-9]+', value):
            result.append(int(value))
        else:
            raise VersificationDataError(f'Invalid verse count: {value!r}')
    return result


def build_reference(bundle: dict) -> dict:
    """Build the versioned counts catalogue without copying mapping assumptions.

    All org book counts are preserved numerically, including the 66-book core.
    Extra entries use a named source, never the maximum across several editions.
    Composite/extract views remain labelled; canonical passage identity is a
    separate decision for the mapping-engine stage.
    """
    policy, systems = bundle['policy'], bundle['systems']
    base_name = policy['baseSystem']
    base = systems[base_name]['maxVerses']
    if len(policy['coreBooks']) != 66 or len(set(policy['coreBooks'])) != 66:
        raise VersificationDataError('Reference policy must identify 66 distinct core books')
    if not set(policy['coreBooks']) <= set(base):
        raise VersificationDataError('Reference core includes a book absent from its base')
    if set(base) & set(policy['extensions']):
        raise VersificationDataError('An extension must not replace a base book')
    if policy['corrections']:
        raise VersificationDataError('Corrections require an explicit, tested application step')
    books = {}
    for usfm in [*base, *policy['extensions']]:
        extension = policy['extensions'].get(usfm)
        source = extension['sourceSystem'] if extension else base_name
        try:
            counts = _verse_counts(systems[source]['maxVerses'][usfm])
        except KeyError as error:
            raise VersificationDataError(f'Missing reference count source: {source}/{usfm}') from error
        bbb = bos_book_code(usfm, source, bundle['bookCodes'])
        if bbb in books:
            raise VersificationDataError(f'Two reference entries resolve to {bbb}')
        note = extension['reason'] if extension else policy['baseBookNotes'].get(usfm)
        books[bbb] = {
            'usfmBook': usfm,
            'name': bundle['bookCodes']['books'][usfm]['name'],
            'sourceSystem': source,
            'sourcePath': f'Copenhagen/versification-mappings/standard-mappings/{source}.json',
            'sourcePointer': f'/maxVerses/{usfm}',
            'role': extension['role'] if extension else (
                'core-book' if usfm in policy['coreBooks'] else 'additional-book-or-witness'),
            'status': extension['status'] if extension else ('requires-review' if note else 'counts-only'),
            'maxVerses': counts,
            'notes': [note] if note else [],
        }
    return {
        'formatVersion': 1,
        'name': policy['name'],
        'version': policy['version'],
        'status': policy['status'],
        'conversionReady': False,
        'sourceSnapshot': bundle['manifest']['snapshotCommit'],
        'dataLicense': bundle['manifest']['dataLicense'],
        'description': policy['description'],
        'coreBasis': policy['coreBasis'],
        'books': books,
        'mappingRestrictions': policy['mappingRestrictions'],
        'unresolvedBridgeDecisions': policy['bridgeDecisions'],
    }


@dataclass(frozen=True)
class ReferenceSpan:
    """A source address range, retaining suffixes and verse-zero titles."""

    book: str
    chapter: int
    first: int
    last: int
    first_suffix: str = ''
    last_suffix: str = ''
    is_range: bool = False

    def points(self) -> tuple[str, ...] | None:
        """Expand numeric spans only; a suffix range needs a segment inventory."""
        if self.is_range and (self.first_suffix or self.last_suffix):
            return None
        # Avoid unbounded allocation for a malformed or accidentally huge range.
        if self.last - self.first > 10000:
            return None
        return tuple(f'{self.book} {self.chapter}:{verse}{self.first_suffix}'
                     for verse in range(self.first, self.last + 1))


def parse_reference_span(text: str) -> ReferenceSpan:
    """Parse the observed Copenhagen grammar, which exceeds its JSON schema.

    Only intra-chapter ranges are supplied by this snapshot. Unsupported grammar
    is reported, not silently coerced into another reference convention.
    """
    match = _REFERENCE_PATTERN.fullmatch(text) if isinstance(text, str) else None
    if not match:
        raise VersificationDataError(f'Unsupported reference syntax: {text!r}')
    book, chapter, first, first_suffix, last, last_suffix = match.groups()
    is_range = last is not None
    first, last = int(first), int(last) if is_range else int(first)
    last_suffix = last_suffix if is_range else first_suffix
    if int(chapter) < 1:
        raise VersificationDataError(f'Chapter zero is not defined by these arrays: {text!r}')
    if last < first or (last == first and first_suffix and last_suffix
                        and last_suffix < first_suffix):
        raise VersificationDataError(f'Reversed range: {text!r}')
    return ReferenceSpan(book, int(chapter), first, last, first_suffix, last_suffix, is_range)


def audit_system(name: str, definition: dict, base: dict, *, incomplete_counts=False) -> dict:
    """Inspect one definition without correcting or resolving its mapping rules.

    ``base`` describes mapping destinations (org for the standard files). Bound
    findings refer to the supplied arrays, not an inferred or inherited Bible.
    Overlaps are recorded as relationships requiring review, not all condemned as
    errors: some represent legitimate splits, merges, or alternative packaging.
    """
    issues = []

    def issue(code, location, message, severity='review', **details):
        issues.append(dict(code=code, severity=severity, location=location,
                           message=message, **details))

    allowed = {'maxVerses', 'mappedVerses', 'excludedVerses', 'mergedVerses',
               'partialVerses', 'basedOn', 'verification'}
    for field in sorted(set(definition) - allowed):
        issue('UNKNOWN_FIELD', field, 'Field is absent from the upstream schema.', 'error')
    counts = {}
    for book, values in definition.get('maxVerses', {}).items():
        try:
            counts[book] = _verse_counts(values)
        except VersificationDataError as error:
            issue('INVALID_COUNTS', f'maxVerses/{book}', str(error), 'error')
    if not counts:
        issue('MISSING_COUNTS', 'maxVerses', 'No usable chapter counts supplied.', 'error')
    string_counts = sum(isinstance(v, str) for values in definition.get('maxVerses', {}).values()
                        if isinstance(values, list) for v in values)
    if string_counts:
        issue('SCHEMA_COUNT_TYPE', 'maxVerses',
              'The upstream schema requires numbers; source counts are decimal strings.',
              'normalization', count=string_counts)
    if incomplete_counts:
        issue('INCOMPLETE_CUSTOM_COUNTS', 'maxVerses',
              'Arrays do not define the chapters referenced by the rules; no chapter indexes '
              'or basedOn declaration are supplied. No inheritance is inferred.')
    if 'basedOn' in definition:
        issue('INHERITANCE_NOT_RESOLVED', 'basedOn',
              'Stage one preserves inheritance but audits the supplied arrays and rules only.',
              base=definition['basedOn'])
    base_counts = {b: _verse_counts(v) for b, v in base.get('maxVerses', {}).items()}
    zero_refs = set()
    suffix_refs = set()

    def inspect_reference(text, role, location):
        try:
            span = parse_reference_span(text)
        except VersificationDataError as error:
            code = 'REVERSED_RANGE' if str(error).startswith('Reversed range') else 'REFERENCE_SYNTAX'
            issue(code, location, str(error), 'error', reference=text, role=role)
            return None
        limits = counts if role == 'source' else base_counts
        if span.book not in limits:
            issue('UNDEFINED_BOOK', location, 'Book has no count definition in this system.',
                  reference=text, role=role)
        elif span.chapter > len(limits[span.book]):
            issue('CHAPTER_OUTSIDE_COUNTS', location, 'Chapter is outside the supplied count array.',
                  reference=text, role=role)
        elif span.last > limits[span.book][span.chapter - 1]:
            issue('VERSE_OUTSIDE_COUNTS', location, 'Verse is above the supplied chapter maximum.',
                  reference=text, role=role, maximum=limits[span.book][span.chapter - 1])
        if span.first == 0:
            zero_refs.add(text)
        if span.first_suffix or span.last_suffix:
            suffix_refs.add(text)
            issue('SCHEMA_REFERENCE_SYNTAX', location,
                  'Lettered reference is not accepted by the upstream schema.', 'normalization',
                  reference=text, role=role)
            segments = (definition if role == 'source' else base).get('partialVerses', {})
            for verse, suffix in {(span.first, span.first_suffix), (span.last, span.last_suffix)}:
                if suffix and suffix not in segments.get(f'{span.book} {span.chapter}:{verse}', []):
                    issue('UNDECLARED_SEGMENT', location,
                          'Lettered endpoint has no matching partialVerses declaration.',
                          reference=f'{span.book} {span.chapter}:{verse}{suffix}', role=role)
        return span

    rules = definition.get('mappedVerses', {})
    source_uses, target_uses = defaultdict(list), defaultdict(list)
    unequal = 0
    for left, right in rules.items():
        location = f'mappedVerses/{left}'
        spans = [inspect_reference(left, 'source', location),
                 inspect_reference(right, 'target', location)]
        if not all(spans):
            continue
        expanded = [span.points() for span in spans]
        for side, points, uses in zip(('source', 'target'), expanded, (source_uses, target_uses)):
            if points is None:
                issue('RANGE_NOT_EXPANDED', location,
                      'Range needs a segment inventory or exceeds the audit expansion limit.', role=side)
            else:
                for point in points:
                    uses[point].append(left)
        if all(points is not None for points in expanded) and len(expanded[0]) != len(expanded[1]):
            unequal += 1
            issue('UNEQUAL_RANGE_LENGTHS', location,
                  'A positional zip would lose information; retain the full relationship.',
                  source=left, target=right,
                  sourceLength=len(expanded[0]), targetLength=len(expanded[1]))
    for code, uses in [('SOURCE_OVERLAP', source_uses), ('TARGET_OVERLAP', target_uses)]:
        overlaps = defaultdict(list)
        for point, owners in uses.items():
            if len(owners) > 1:
                overlaps[tuple(sorted(owners))].append(point)
        for owners, points in sorted(overlaps.items()):
            issue(code, 'mappedVerses',
                  'Several explicit rules cover these addresses; a single-valued dictionary '
                  'could discard a relationship. No implicit identities have been added.',
                  references=sorted(points), rules=[{'source': s, 'target': rules[s]} for s in owners])
    for field in ('excludedVerses', 'mergedVerses'):
        for index, text in enumerate(definition.get(field, [])):
            inspect_reference(text, 'source', f'{field}/{index}')
    for text, labels in definition.get('partialVerses', {}).items():
        location = f'partialVerses/{text}'
        inspect_reference(text, 'source', location)
        if not isinstance(labels, list) or not labels or any(not isinstance(s, str) or not s for s in labels):
            issue('INVALID_SEGMENT_LABELS', location, 'Expected a nonempty list of nonempty strings.', 'error')
            continue
        if any(s != s.strip() for s in labels):
            issue('SEGMENT_LABEL_WHITESPACE', location,
                  'Source labels contain whitespace. It is preserved pending a normalization rule.', labels=labels)
        if len(set(labels)) != len(labels):
            issue('DUPLICATE_SEGMENT_LABEL', location, 'Repeated segment label.', 'error', labels=labels)
    return {
        'name': name,
        'status': 'audit-only',
        'conversionReady': False,
        'bookCount': len(counts),
        'chapterCount': sum(map(len, counts.values())),
        'explicitMappingRuleCount': len(rules),
        'excludedVerseEntryCount': len(definition.get('excludedVerses', [])),
        'mergedVerseEntryCount': len(definition.get('mergedVerses', [])),
        'partialVerseEntryCount': len(definition.get('partialVerses', {})),
        'unequalRangeRuleCount': unequal,
        'verseZeroReferences': sorted(zero_refs),
        'letteredReferences': sorted(suffix_refs),
        'issueCounts': dict(sorted(Counter(i['code'] for i in issues).items())),
        'issues': issues,
    }


def audit_inheritance(definitions: dict) -> list[dict]:
    """Find unknown bases and cycles without inventing inheritance semantics."""
    issues = []
    cycles = set()
    for name in sorted(definitions):
        chain = []
        current = name
        while current is not None:
            if not isinstance(current, str) or current not in definitions:
                issues.append({'code': 'UNKNOWN_BASE', 'system': name, 'base': current})
                break
            if current in chain:
                cycle = tuple(sorted(chain[chain.index(current):]))
                if cycle not in cycles:
                    issues.append({'code': 'INHERITANCE_CYCLE', 'systems': list(cycle)})
                    cycles.add(cycle)
                break
            chain.append(current)
            current = definitions[current].get('basedOn')
    return issues


def build_coverage_report(bundle: dict, reference: dict | None = None) -> dict:
    """Produce deterministic findings and inventory gaps from bundled inputs only."""
    # Local import avoids a module-initialisation cycle: the runtime adapter
    # also uses the pure resource loader and catalogue builder above.
    from BibleOrgSys.Reference.BibleVersificationMappings import VersificationMappingEngine

    reference = build_reference(bundle) if reference is None else reference
    engine = VersificationMappingEngine.from_bundled_data(bundle=bundle)
    systems, policy, codes = bundle['systems'], bundle['policy'], bundle['bookCodes']
    base = systems[policy['baseSystem']]
    audits = {}
    for name, definition in systems.items():
        audit = audit_system(name, definition, base, incomplete_counts=name == 'ethiopian_custom')
        audit['mappingTargetSystem'] = policy['baseSystem']
        restricted = {book for rule in policy['mappingRestrictions'] if rule['system'] == name
                      for book in rule['books']}
        audit['books'] = {}
        for book, counts in definition['maxVerses'].items():
            bbb = bos_book_code(book, name, codes)
            audit['books'][book] = {
                'bosBook': bbb,
                'chapterCount': len(counts),
                'inReferenceCatalogue': bbb in reference['books'],
                'status': 'unmapped-textual-tradition' if book in restricted else (
                    'underspecified-custom-counts' if name == 'ethiopian_custom' else 'counts-only'),
                'explicitMappingRuleCount': sum(s.startswith(book + ' ') for s in definition['mappedVerses']),
                'identityMappingAssumed': False,
            }
        audit['documentedRestrictions'] = [r for r in policy['mappingRestrictions'] if r['system'] == name]
        audit['compiledReferenceCoverage'] = engine.audit_reference_coverage(name)
        audits[name] = audit
    reference_codes = set(reference['books'])
    legacy_gaps = {name: sorted(set(books) - reference_codes)
                   for name, books in bundle['legacy']['systems'].items()}
    legacy_gaps = {name: books for name, books in legacy_gaps.items() if books}
    sample = audit_system('sample:one_versification', bundle['sample'], base)
    return {
        'formatVersion': 2,
        'sourceSnapshot': bundle['manifest']['snapshotCommit'],
        'referenceName': reference['name'],
        'referenceVersion': reference['version'],
        'dataLicense': bundle['manifest']['dataLicense'],
        'mappingDataRevision': engine.data_revision,
        'mappingSupplementVersion': bundle['supplement']['version'],
        'additionalProfiles': {profile['name']: {
            'version': profile['version'], 'scope': profile['scope'],
            'compiledReferenceCoverage': engine.audit_reference_coverage(profile['name']),
        } for profile in bundle.get('additionalMappings', ())},
        'conversionReady': False,
        'scope': 'Raw structural findings plus separately labelled compiled reference coverage. '
                 'Compiled coverage includes the BOS supplement and declared delta identities; '
                 'neither section certifies text equivalence or resolves custom inheritance.',
        'referenceBookCount': len(reference['books']),
        'referenceCoreBookCount': len(policy['coreBooks']),
        'referenceExtensions': {book: {'bosBook': bos_book_code(book, ext['sourceSystem'], codes), **ext}
                                for book, ext in policy['extensions'].items()},
        'booksMissingFromReferenceByLegacySystem': legacy_gaps,
        'legacyBooksMissingFromReference': sorted(set().union(*(set(v) for v in legacy_gaps.values()))),
        'bookCodeChoicesRequiringContext': {b: v for b, v in codes['books'].items() if v['alternatives']},
        'systemBookCodeOverrides': codes['systemOverrides'],
        'inheritanceIssues': audit_inheritance({**systems, 'sample:one_versification': bundle['sample']}),
        'systems': audits,
        'sampleCustomDefinition': sample,
        'unresolvedBridgeDecisions': policy['bridgeDecisions'],
    }


def generated_documents(bundle: dict) -> dict[str, str]:
    """Return reproducible UTF-8 JSON text; no clocks or absolute paths included."""
    from BibleOrgSys.Reference.BibleVersificationMappings import VersificationMappingEngine
    from BibleOrgSys.Reference.Converters.BibleVersificationSniffingAudit import build_sniffing_report

    reference = build_reference(bundle)
    report = build_coverage_report(bundle, reference)
    sniffing = build_sniffing_report(bundle, VersificationMappingEngine.from_bundled_data(bundle=bundle))
    return {name: json.dumps(obj, ensure_ascii=False, indent=2) + '\n'
            for name, obj in zip(GENERATED_FILES, (reference, report, sniffing))}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--check', action='store_true', help='Fail if checked-in generated files are stale.')
    mode.add_argument('--write', action='store_true', help='Regenerate the three derived JSON files.')
    parser.add_argument('--output-dir', type=Path, help='Alternative directory for --write/--check output.')
    args = parser.parse_args(argv)
    try:
        bundle = load_bundle()
        documents = generated_documents(bundle)
        root = args.output_dir if args.output_dir is not None else _resource_root()
        if args.write:
            if not isinstance(root, Path):
                raise VersificationDataError('Use --output-dir when running from a zipped package.')
            root.mkdir(parents=True, exist_ok=True)
            for name, text in documents.items():
                root.joinpath(name).write_text(text, encoding='utf-8')
        elif args.check:
            stale = [name for name, text in documents.items()
                     if not root.joinpath(name).is_file()
                     or root.joinpath(name).read_text(encoding='utf-8') != text]
            if stale:
                raise VersificationDataError('Generated files are stale: ' + ', '.join(stale))
        reference = json.loads(documents['BOSReference.json'])
        report = json.loads(documents['coverage-report.json'])
        print(f"{reference['name']} {reference['version']}: {len(reference['books'])} catalogue entries; "
              'draft coverage; consult the mapping API for per-reference support.')
        for name, audit in report['systems'].items():
            coverage = audit['compiledReferenceCoverage']
            print(f"  {name}: {audit['bookCount']} books, {audit['explicitMappingRuleCount']} explicit rules, "
                  f"{len(audit['issues'])} structural findings; "
                  f"{coverage['unmappedCount']} unmapped / {coverage['blockedCount']} blocked reference addresses")
        print('Legacy book codes without a reference entry: ' + ', '.join(report['legacyBooksMissingFromReference']))
        sniffing = json.loads(documents['sniffing-audit-report.json'])
        print(f"Sniffing audit: {sniffing['ruleCount']} rules, {sniffing['rowCount']} rows, "
              f"{sniffing['splitMergeRowCount']} split/merge rows; "
              f"{len(bundle['supplement']['corrections'])} reviewed corrections.")
        return 0
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f'Versification data error: {error}\n')


if __name__ == '__main__':
    raise SystemExit(main())
