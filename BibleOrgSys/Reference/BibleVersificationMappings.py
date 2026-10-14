# SPDX-License-Identifier: MPL-2.0
"""Conservative, offline verse-reference mapping through BOSReference.

References use BOS book codes and (BBB, chapter, verse, suffix) tuples. Results
are immutable and distinguish an exact group from competing alternatives.
Only an exact singleton can be returned by the legacy four-tuple APIs.

See Documentation/VersificationMappingAPI.md for the contract, policy, and
deliberately unsupported portions of the bundled Copenhagen snapshot.
"""

from __future__ import annotations

from collections import defaultdict, deque
from copy import deepcopy
from dataclasses import dataclass, replace
from enum import Enum
from functools import lru_cache
import hashlib
import json
import re

from BibleOrgSys.Reference.Converters.BibleVersificationMappingsConverter import (
    VersificationDataError, bos_book_code, build_reference, load_bundle, parse_reference_span,
)


Reference = tuple[str, str, str, str | None]


class MappingStatus(str, Enum):
    EXACT = 'exact'
    AMBIGUOUS = 'ambiguous'
    UNSUPPORTED = 'unsupported'
    PARTIAL = 'partial'
    INVALID = 'invalid'


@dataclass(frozen=True)
class MappingDiagnostic:
    code: str
    message: str
    system: str
    references: tuple[Reference, ...] = ()
    rule: str | None = None


@dataclass(frozen=True)
class MappingResult:
    source_system: str
    target_system: str
    source_references: tuple[Reference, ...]
    status: MappingStatus
    # Populated only when the entire requested passage has an exact mapping.
    references: tuple[Reference, ...] = ()
    # Each alternative is a complete candidate group in target_system.
    alternatives: tuple[tuple[Reference, ...], ...] = ()
    diagnostics: tuple[MappingDiagnostic, ...] = ()
    provenance: tuple[str, ...] = ()
    reference_version: str = ''
    data_revision: str = ''
    mapping_policy_version: str = '3'
    # The caller's original selection when complete-group expansion was used.
    requested_references: tuple[Reference, ...] = ()

    @property
    def is_expanded(self):
        return bool(self.requested_references and
                    set(self.requested_references) != set(self.source_references))

    def require_single(self) -> Reference:
        """Return the exact singleton or raise an exception retaining this result."""
        if self.status != MappingStatus.EXACT:
            exception = {
                MappingStatus.AMBIGUOUS: AmbiguousMappingError,
                MappingStatus.UNSUPPORTED: UnsupportedMappingError,
                MappingStatus.PARTIAL: PartialMappingError,
                MappingStatus.INVALID: InvalidReferenceError,
            }[self.status]
            raise exception(self)
        if len(self.references) != 1:
            raise MultipleReferencesError(self)
        return self.references[0]


class VersificationMappingError(ValueError):
    def __init__(self, result: MappingResult):
        self.result = result
        reason = result.diagnostics[0].message if result.diagnostics else 'The result contains multiple references.'
        super().__init__(f'{result.source_system} → {result.target_system}: {result.status.value}: {reason}')


class UnsupportedMappingError(VersificationMappingError):
    pass


class AmbiguousMappingError(VersificationMappingError):
    pass


class PartialMappingError(VersificationMappingError):
    pass


class InvalidReferenceError(VersificationMappingError):
    pass


class MultipleReferencesError(VersificationMappingError):
    pass


class UnknownVersificationSystemError(ValueError):
    pass


def normalize_reference(reference) -> Reference:
    """Normalise numbers and empty suffixes; never guess USFM/BOS book aliases."""
    if not isinstance(reference, (tuple, list)) or len(reference) not in (3, 4):
        raise ValueError('Expected a (BBB, C, V[, S]) reference.')
    bbb, chapter, verse = reference[:3]
    suffix = reference[3] if len(reference) == 4 else None
    if not isinstance(bbb, str) or not re.fullmatch(r'[A-Z0-9]{3}', bbb):
        raise ValueError('A reference needs a three-character BOS book code.')
    for value in (chapter, verse):
        if type(value) not in (str, int) or not re.fullmatch(r'[0-9]+', str(value)):
            raise ValueError('Chapter and verse must be nonnegative integers or decimal strings.')
    if int(chapter) < 1:
        raise ValueError('Chapter zero and introduction references cannot be mapped.')
    if suffix not in (None, '') and (not isinstance(suffix, str) or not re.fullmatch(r'[a-z]+', suffix)):
        raise ValueError('A verse suffix must contain lowercase letters.')
    return bbb, str(int(chapter)), str(int(verse)), suffix or None


def _unique(values):
    return tuple(dict.fromkeys(values))


def _points(text):
    span = parse_reference_span(text)
    points = span.points()
    if points is None:
        raise VersificationDataError('Segment ranges need an explicit segment inventory; range not expanded.')
    return tuple((span.book, str(span.chapter), str(v), span.first_suffix or None)
                 for v in range(span.first, span.last + 1))


def _whole(reference):
    return reference[:3] + (None,)


def _group_points(value):
    """Expand an explicit ordered group; lists can cross chapters or books.

    The span parser remains deliberately limited to a single chapter. No
    semicolon shorthand or missing cross-chapter endpoint is inferred here.
    """
    spans = [value] if isinstance(value, str) else value
    if not isinstance(spans, (list, tuple)) or not spans:
        raise VersificationDataError('A mapping group needs a span or a nonempty list of spans.')
    result = tuple(ref for span in spans for ref in _points(span))
    if len(result) > 10000 or len(set(result)) != len(result):
        raise VersificationDataError('Mapping groups must be distinct and contain at most 10000 references.')
    if any(r[3] and _whole(r) in result for r in result):
        raise VersificationDataError('A mapping group cannot mix a whole verse with its segment.')
    return result


def _apply_supplement(systems, reference_definition, bundle):
    """Apply reviewed replacements to adapted copies, failing on stale evidence.

    Corrections replace complete raw rules, explicitly restating any surviving
    range. They cannot silently override a changed upstream rule or another
    correction. The JSON content digest versions results, including metadata.
    """
    supplement = bundle['supplement']
    if (supplement['formatVersion'] != 1 or not re.fullmatch(r'[1-9][0-9]*', supplement['version'])
            or supplement['sourceSnapshot'] != bundle['manifest']['snapshotCommit']):
        raise VersificationDataError('Unsupported supplement format, version, or source snapshot.')
    evidence_rules = {row['name']: row for row in bundle['supplementEvidence']}
    if supplement['evidenceFile'] != 'Copenhagen/versification-sniffing/rules/merged_rules.json':
        raise VersificationDataError('Unknown supplement evidence file.')
    reference_domain = _Domain('BOSReference', reference_definition)
    seen_ids, touched = set(), defaultdict(set)
    for correction in supplement['corrections']:
        identifier, name = correction['id'], correction['system']
        if not identifier or identifier in seen_ids or name not in systems:
            raise VersificationDataError('Duplicate/empty supplement id or unknown system.')
        seen_ids.add(identifier)
        if (not correction['reason'] or not correction['evidence']['verification']
                or correction['evidence']['copenhagenRule'] not in evidence_rules):
            raise VersificationDataError(f'Missing supplement evidence: {identifier}')
        definition = systems[name]
        source, target = _group_points(correction['source']), _group_points(correction['target'])
        for role, domain, points in (('source', _Domain(name, definition), source),
                                    ('reference', reference_domain, target)):
            if any(domain.issue(r) for r in points):
                raise VersificationDataError(f'Supplement endpoint outside declared domain: {identifier}')
            for address, expected in correction.get(role + 'ChapterCounts', {}).items():
                book, chapter = address.split()
                counts = domain.counts.get(book, ())
                if (type(expected) is not int or not 1 <= int(chapter) <= len(counts)
                        or counts[int(chapter)-1] != expected):
                    raise VersificationDataError(f'Stale supplement chapter evidence: {identifier}: {address}')
        if 'copenhagenRangeIndex' in correction['evidence']:
            rows = evidence_rules[correction['evidence']['copenhagenRule']]['ranges']
            index = correction['evidence']['copenhagenRangeIndex']
            if (type(index) is not int or not 0 <= index < len(rows)
                    or len(rows[index]) != 1
                    or not set(rows[index]) <= {'SubdividedVerse', 'MergedVerses'}):
                raise VersificationDataError(f'Invalid supplement evidence row: {identifier}')
        if touched[name].intersection(source):
            raise VersificationDataError(f'Overlapping supplement groups: {identifier}')
        touched[name].update(source)
        mappings = definition['mappedVerses']
        original_pairs, remaining_pairs = {}, {}
        for left, expected in correction['replaceMappings'].items():
            if mappings.get(left) != expected:
                raise VersificationDataError(f'Stale supplement replacement: {identifier}: {left}')
            original_pairs.update(zip(_points(left), _points(expected), strict=True))
            del mappings[left]
        for left, right in correction['remainingMappings'].items():
            if left in mappings:
                raise VersificationDataError(f'Supplement remainder overwrites a rule: {identifier}')
            mappings[left] = right
            remaining_pairs.update(zip(_points(left), _points(right), strict=True))
        if remaining_pairs != {s: t for s, t in original_pairs.items() if s not in source}:
            raise VersificationDataError(f'Supplement must preserve unaffected range members: {identifier}')
        definition.setdefault('groupMappings', []).append({
            'source': correction['source'], 'target': correction['target'],
            'provenance': f'BOS supplement {identifier} revision {supplement["version"]}',
        })
    for name, points in touched.items():
        for left in systems[name]['mappedVerses']:
            try:
                overlap = points.intersection(_points(left))
            except ValueError:
                continue  # The compiler still quarantines malformed upstream rules.
            if overlap:
                raise VersificationDataError(f'Supplement group overlaps remaining mapping: {name}: {left}')
    payload = json.dumps(supplement, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    return f'{supplement["sourceSnapshot"]}+bos-supplement-{supplement["version"]}.{hashlib.sha256(payload).hexdigest()}'


@dataclass(frozen=True)
class _Relation:
    source: tuple[Reference, ...]
    target: tuple[Reference, ...]
    provenance: str


class _Domain:
    def __init__(self, name, definition):
        self.name = name
        self.counts = {}
        for book, counts in definition.get('maxVerses', {}).items():
            if not re.fullmatch(r'[A-Z0-9]{3}', book) or not isinstance(counts, (list, tuple)) or not counts:
                raise VersificationDataError(f'Invalid counts for {name}/{book}')
            if any(type(v) not in (int, str) or not re.fullmatch(r'[0-9]+', str(v)) for v in counts):
                raise VersificationDataError(f'Invalid counts for {name}/{book}')
            self.counts[book] = tuple(map(int, counts))
        self.excluded = set()
        for text in definition.get('excludedVerses', ()):
            self.excluded.update(_points(text))
        self.segments = {}
        for text, labels in definition.get('partialVerses', {}).items():
            ref, = _points(text)
            # Whitespace and '-' are deliberately not interpreted as segment names.
            self.segments[ref] = tuple(s for s in labels if isinstance(s, str) and re.fullmatch(r'[a-z]+', s))
        self.zeros = set(_points(text)[0] for text in definition.get('verseZeroReferences', ()))
        self.merged = tuple(_points(text) for text in definition.get('mergedVerses', ()))

    def issue(self, ref):
        book, chapter, verse, suffix = ref
        chapters = self.counts.get(book)
        if not chapters:
            return 'BOOK_NOT_IN_SYSTEM', 'Book is not defined in this versification.'
        if int(chapter) > len(chapters) or int(verse) > chapters[int(chapter) - 1]:
            return 'OUTSIDE_SYSTEM', 'Reference is outside the supplied chapter/verse counts.'
        if ref in self.excluded or _whole(ref) in self.excluded:
            return 'EXCLUDED_VERSE', 'This verse is explicitly excluded from the system.'
        if verse == '0' and _whole(ref) not in self.zeros:
            return 'UNDECLARED_TITLE', 'Verse zero is not declared for this chapter.'
        if suffix and suffix not in self.segments.get(_whole(ref), ()):
            return 'UNDECLARED_SEGMENT', 'This verse segment has no validated declaration.'
        return None

    def references(self):
        for book, counts in self.counts.items():
            for chapter, maximum in enumerate(counts, 1):
                for verse in range(1, maximum + 1):
                    ref = (book, str(chapter), str(verse), None)
                    if ref not in self.excluded:
                        yield ref
        yield from sorted(self.zeros)


class _Table:
    def __init__(self, name, definition, domain, reference_domain, blocked_reference_books):
        self.name = name
        self.domain = domain
        self.reference_domain = reference_domain
        self.forward = defaultdict(list)
        self.reverse = defaultdict(list)
        self.forward_blocks = defaultdict(list)
        self.reverse_blocks = defaultdict(list)
        self.forward_scopes = []
        self.reverse_scopes = []
        self.disabled = definition.get('disabledReason')
        if definition.get('basedOn'):
            self.disabled = 'Custom inheritance is not resolved; supply a complete reference-directed definition.'
        touched = set()
        segmented = set()

        def block_scope(text, scopes, diagnostic):
            # A malformed span poisons its whole chapter; never infer corrected endpoints.
            if isinstance(text, (list, tuple)) and text:
                for span in text:
                    block_scope(span, scopes, diagnostic)
                return
            match = re.match(r'^([A-Z0-9]{3})(?: ([0-9]+):)?', text) if isinstance(text, str) else None
            chapter = str(int(match[2])) if match and match[2] else None
            scopes.append((match[1] if match else None, chapter, diagnostic))

        def record(left, right, *, grouped=False, origin=None):
            provenance = f'{name}: {origin + ": " if origin else ""}{left} = {right}'
            diagnostic = MappingDiagnostic('INVALID_MAPPING_RULE', 'The mapping rule is not usable.', name, rule=provenance)
            source = target = None
            problems = []
            for text, side, scopes in ((left, 'source', self.forward_scopes), (right, 'target', self.reverse_scopes)):
                try:
                    points = _group_points(text) if grouped else _points(text)
                    if side == 'source':
                        source = points
                    else:
                        target = points
                except (ValueError, TypeError) as error:
                    problems.append(str(error))
                    block_scope(text, scopes, diagnostic)
            if source:
                touched.update(source)
                segmented.update(_whole(r) for r in source if r[3])
                problems.extend(f'Source {r}: {domain.issue(r)[1]}' for r in source if domain.issue(r))
                problems.extend(definition['unsupportedBooks'][r[0]] for r in source
                                if r[0] in definition.get('unsupportedBooks', {}))
            if target:
                problems.extend(f'Target {r}: {reference_domain.issue(r)[1]}' for r in target if reference_domain.issue(r))
                if any(r[0] in blocked_reference_books for r in target):
                    problems.append('The destination uses an unresolved reference book/bridge.')
            if source and target and not grouped and len(source) != len(target):
                problems.append('Unequal upstream ranges have not been verified as an intentional group mapping.')
            if problems:
                diagnostic = MappingDiagnostic('INVALID_MAPPING_RULE', ' '.join(_unique(problems)), name,
                                               tuple(source or ()), provenance)
                for r in source or ():
                    self.forward_blocks[r].append(diagnostic)
                    if r[3]:
                        self.forward_blocks[_whole(r)].append(diagnostic)
                for r in target or ():
                    self.reverse_blocks[r].append(diagnostic)
                    if r[3]:
                        self.reverse_blocks[_whole(r)].append(diagnostic)
                return
            pairs = [(source, target)] if grouped else [((s,), (t,)) for s, t in zip(source, target)]
            for sources, targets in pairs:
                self._add(_Relation(sources, targets, provenance))

        for left, right in definition.get('mappedVerses', {}).items():
            record(left, right)
        for group in definition.get('groupMappings', ()):
            record(group['source'], group['target'], grouped=True, origin=group.get('provenance'))
        # Restrictions poison both directions even when no rule exists.
        for book, reason in definition.get('unsupportedBooks', {}).items():
            diagnostic = MappingDiagnostic('UNSUPPORTED_BOOK_MAPPING', reason, name)
            self.forward_scopes.append((book, None, diagnostic))
            destination = definition.get('identityBooks', {}).get(book, book)
            self.reverse_scopes.append((destination, None, diagnostic))
        for source in domain.references():
            if source in touched or _whole(source) in segmented:
                continue
            destination_book = definition.get('identityBooks', {}).get(source[0])
            if destination_book is None:
                continue
            target = (destination_book, *source[1:])
            if reference_domain.issue(target) or target[0] in blocked_reference_books:
                continue
            self._add(_Relation((source,), (target,), f'{name}: declared delta identity {source}'))
        self._propagate_blocks()

    def _propagate_blocks(self):
        """Quarantine connected relationships, including otherwise implicit identities.

        A malformed source span can disable a chapter without enumerating its
        endpoints. Its inverse identities must not resurrect those references.
        Likewise, a valid rule sharing an unusable endpoint cannot be selected
        merely because the unusable alternative was discarded.
        """
        queue = deque()
        for reverse, index, blocks, scopes in (
                (False, self.forward, self.forward_blocks, self.forward_scopes),
                (True, self.reverse, self.reverse_blocks, self.reverse_scopes)):
            for ref in index:
                issues = list(blocks.get(ref, ()))
                if ref[3]:
                    issues.extend(blocks.get(_whole(ref), ()))
                issues.extend(d for book, chapter, d in scopes
                              if (book is None or book == ref[0]) and (chapter is None or chapter == ref[1]))
                queue.extend((reverse, ref, issue) for issue in issues)
        visited = set()
        while queue:
            reverse, ref, diagnostic = queue.popleft()
            if (reverse, ref, diagnostic) in visited:
                continue
            visited.add((reverse, ref, diagnostic))
            blocks = self.reverse_blocks if reverse else self.forward_blocks
            if diagnostic not in blocks[ref]:
                blocks[ref].append(diagnostic)
            index = self.reverse if reverse else self.forward
            for relation in index.get(ref, ()):
                queue.extend((False, r, diagnostic) for r in relation.source)
                queue.extend((True, r, diagnostic) for r in relation.target)

    def _add(self, relation):
        for ref in relation.source:
            if not any(r.source == relation.source and r.target == relation.target for r in self.forward[ref]):
                self.forward[ref].append(relation)
        for ref in relation.target:
            if not any(r.source == relation.source and r.target == relation.target for r in self.reverse[ref]):
                self.reverse[ref].append(relation)

    def apply(self, references, *, reverse=False, max_alternatives=64):
        """Solve complete disjoint covers of the requested passage, never zip groups."""
        domain = self.reference_domain if reverse else self.domain
        index = self.reverse if reverse else self.forward
        blocks = self.reverse_blocks if reverse else self.forward_blocks
        scopes = self.reverse_scopes if reverse else self.forward_scopes
        diagnostics = []
        if self.disabled:
            return MappingStatus.UNSUPPORTED, (), (MappingDiagnostic('UNSUPPORTED_SYSTEM', self.disabled, self.name),), ()
        for ref in references:
            problem = domain.issue(ref)
            if problem:
                diagnostics.append(MappingDiagnostic(problem[0], problem[1], domain.name, (ref,)))
            diagnostics.extend(blocks.get(ref, ()))
            if ref[3]:
                diagnostics.extend(blocks.get(_whole(ref), ()))
            diagnostics.extend(d for book, chapter, d in scopes
                               if (book is None or book == ref[0]) and (chapter is None or chapter == ref[1]))
        # Requesting only part of a source verse bridge does not identify its text.
        for group in domain.merged:
            if set(group) & set(references) and not set(group) <= set(references):
                diagnostics.append(MappingDiagnostic('INCOMPLETE_MERGED_VERSE',
                    'Request the complete merged-verse group.', domain.name, group))
        if diagnostics:
            codes = {d.code for d in diagnostics}
            if codes <= {'BOOK_NOT_IN_SYSTEM', 'OUTSIDE_SYSTEM'}:
                status = MappingStatus.INVALID
            elif 'INCOMPLETE_MERGED_VERSE' in codes:
                status = MappingStatus.PARTIAL
            else:
                status = MappingStatus.UNSUPPORTED
            return status, (), _unique(diagnostics), ()

        solutions = {}
        # Iterative search avoids recursion limits on whole chapters/books.
        stack = [(frozenset(references), (), ())]
        incomplete_groups = []
        missing = []
        search_steps = 0
        truncated = False
        while stack:
            remaining, output, provenance = stack.pop()
            search_steps += 1
            if search_steps > 10000 or len(solutions) >= max_alternatives:
                truncated = True
                break
            if not remaining:
                solutions.setdefault(_unique(output), provenance)
                continue
            ref = next(r for r in references if r in remaining)
            choices = index.get(ref, ())
            if not choices:
                missing.append(ref)
            for relation in reversed(choices):
                needed, produced = (relation.target, relation.source) if reverse else (relation.source, relation.target)
                if set(needed) <= remaining:
                    stack.append((remaining - set(needed), output + produced, provenance + (relation.provenance,)))
                else:
                    incomplete_groups.append(needed)
        provenance = _unique(p for paths in solutions.values() for p in paths)
        if truncated:
            diagnostics.append(MappingDiagnostic('ALTERNATIVE_LIMIT',
                'Alternative search was bounded; these candidates are not exhaustive.', self.name))
        if solutions:
            output_domain = self.domain if reverse else self.reference_domain
            if any(set(group) & set(output) and not set(group) <= set(output)
                   for output in solutions for group in output_domain.merged):
                return MappingStatus.PARTIAL, (), (MappingDiagnostic('INCOMPLETE_MERGED_VERSE',
                    'The result would identify only part of a target merged verse.', output_domain.name),), provenance
            status = MappingStatus.AMBIGUOUS if len(solutions) > 1 or truncated else MappingStatus.EXACT
            if status == MappingStatus.AMBIGUOUS:
                diagnostics.append(MappingDiagnostic('COMPETING_MAPPINGS',
                    'Several complete relationships are possible; no alternative was selected.', self.name, references))
            return status, tuple(solutions), tuple(diagnostics), provenance
        if truncated:
            return MappingStatus.AMBIGUOUS, (), tuple(diagnostics), ()
        if incomplete_groups:
            return MappingStatus.PARTIAL, (), (MappingDiagnostic('INCOMPLETE_MAPPING_GROUP',
                'The requested references cover only part of a mapping group.', domain.name,
                _unique(r for group in incomplete_groups for r in group)),), ()
        status = MappingStatus.PARTIAL if any(r in index for r in references) else MappingStatus.UNSUPPORTED
        return status, (), (MappingDiagnostic('NO_MAPPING',
            'No complete mapping exists for these references; identity was not assumed.', domain.name,
            _unique(missing)),), ()


class VersificationMappingEngine:
    """Map complete passages through an explicit reference address space.

    Definitions supplied directly to this constructor use BOS codes. Numeric
    ``mappedVerses`` spans must have equal lengths. Intentional splits/merges
    belong in ``groupMappings``. Identity is opt-in through ``identityBooks``
    (a source-book to reference-book dictionary). Definitions are copied.
    """

    def __init__(self, reference_definition, systems, *, reference_name='BOSReference',
                 reference_version='custom', data_revision='custom', blocked_reference_books=()):
        self.reference_name = reference_name
        self.reference_version = reference_version
        self.data_revision = data_revision
        self._definitions = deepcopy(systems)
        if reference_name in systems:
            raise VersificationDataError('The reference name must not also name a source system.')
        self._reference_definition = deepcopy(reference_definition)
        self._reference = _Domain(reference_name, self._reference_definition)
        self._domains = {name: _Domain(name, definition) for name, definition in self._definitions.items()}
        self._domains[reference_name] = self._reference
        self._blocked_reference_books = frozenset(blocked_reference_books)
        self._tables = {}

    @classmethod
    def from_bundled_data(cls, *, bundle=None):
        """Adapt the pinned snapshot; unreviewed bridges remain explicit gaps."""
        bundle = load_bundle() if bundle is None else bundle
        reference = build_reference(bundle)
        codes = bundle['bookCodes']

        def translate(text, system):
            return bos_book_code(text[:3], system, codes) + text[3:]

        reference_definition = {'maxVerses': {b: d['maxVerses'] for b, d in reference['books'].items()},
                                'partialVerses': {}, 'verseZeroReferences': []}
        # Titles are declared only where explicit source rules actually mention them.
        reference_zeros = set()
        systems = {}
        base_books = bundle['systems']['org']['maxVerses']
        for name, raw in bundle['systems'].items():
            definition = {
                'maxVerses': {bos_book_code(b, name, codes): v for b, v in raw['maxVerses'].items()},
                'mappedVerses': {translate(s, name): translate(t, 'org') for s, t in raw['mappedVerses'].items()},
                'excludedVerses': [translate(s, name) for s in raw.get('excludedVerses', ())],
                'mergedVerses': [translate(s, name) for s in raw.get('mergedVerses', ())],
                'partialVerses': {translate(s, name): labels for s, labels in raw.get('partialVerses', {}).items()},
                'identityBooks': {bos_book_code(b, name, codes): bos_book_code(b, 'org', codes)
                                  for b in raw['maxVerses'] if b in base_books},
                'verseZeroReferences': [], 'unsupportedBooks': {},
            }
            source_zeros = set()
            for left, right in definition['mappedVerses'].items():
                for text, zeros in ((left, source_zeros), (right, reference_zeros)):
                    try:
                        span = parse_reference_span(text)
                        if span.first == 0:
                            zeros.add(f'{span.book} {span.chapter}:0')
                    except ValueError:
                        pass  # The compiler will quarantine this rule in both directions.
            definition['verseZeroReferences'] = sorted(source_zeros)
            for restriction in bundle['policy']['mappingRestrictions']:
                if restriction['system'] == name:
                    definition['unsupportedBooks'].update({bos_book_code(b, name, codes): restriction['reason']
                                                          for b in restriction['books']})
            if name == 'ethiopian_custom':
                definition['disabledReason'] = bundle['policy']['systemNotes'][name]
            systems[name] = definition
        # The reference LAO address space is explicitly copied from vul, not from eng.
        systems['vul']['identityBooks']['LAO'] = 'LAO'
        reference_definition['verseZeroReferences'] = sorted(reference_zeros)
        # The reference adopts org numbering; a declared reference title also
        # identifies an org title at the same address.
        systems['org']['verseZeroReferences'] = sorted(reference_zeros)
        data_revision = _apply_supplement(systems, reference_definition, bundle)
        return cls(reference_definition, systems, reference_version=reference['version'],
                   data_revision=data_revision,
                   blocked_reference_books=('PAZ', 'DNG', 'EZ6', 'MQ1', 'MQ3', 'REP', 'BA4'))

    def get_system_names(self):
        return (*self._definitions, self.reference_name)

    def get_legacy_tables(self, name):
        """Adapt counts for the existing BOS registry without adding metadata keys."""
        domain = self._domains[name]
        cv = {book: {'numChapters': str(len(counts)), **{str(c): str(v) for c, v in enumerate(counts, 1)}}
              for book, counts in domain.counts.items()}
        omitted = defaultdict(list)
        for book, chapter, verse, suffix in sorted(domain.excluded):
            if suffix is None:
                omitted[book].append((chapter, verse))
        return {'CV': cv, 'omitted': dict(omitted), 'combined': {}, 'reordered': {}}

    def capabilities(self, name):
        if name not in self._domains:
            return {'status': 'unsupported', 'reason': 'No verified mapping profile; legacy counts are not a mapping.'}
        disabled = self._definitions.get(name, {}).get('disabledReason')
        if self._definitions.get(name, {}).get('basedOn'):
            disabled = 'Custom inheritance has not been resolved.'
        return {'status': 'unsupported' if disabled else 'partial',
                'reason': disabled or 'Per-reference results describe available and unsupported relationships.',
                'reference': self.reference_name, 'referenceVersion': self.reference_version,
                'dataRevision': self.data_revision}

    def audit_reference_coverage(self, name):
        """Inventory numbered reference addresses missing from compiled relations.

        Group members count as represented even when a singleton request would
        be partial. Collisions also count as represented, not certified exact.
        All reference books are audited, so absent source books remain visible.
        This checks address coverage, not whether relationships preserve text.
        """
        if name not in self._definitions:
            raise UnknownVersificationSystemError(name)
        table = self._table(name)
        books = {}
        gaps = defaultdict(lambda: defaultdict(list))
        for ref in sorted(self._reference.references(), key=lambda r: (r[0], int(r[1]), int(r[2]))):
            book = books.setdefault(ref[0], {'referenceCount': 0, 'representedCount': 0,
                                             'unmappedCount': 0, 'blockedCount': 0})
            blocked = (table.disabled or ref[0] in self._blocked_reference_books
                       or ref in table.reverse_blocks or self._reference.issue(ref)
                       or any((b is None or b == ref[0]) and (c is None or c == ref[1])
                              for b, c, _ in table.reverse_scopes))
            category = 'blocked' if blocked else 'represented' if ref in table.reverse else 'unmapped'
            book['referenceCount'] += 1
            book[category + 'Count'] += 1
            if category != 'represented':
                gaps[ref[0]][category].append(ref)
        for book, counts in books.items():
            for category in ('unmapped', 'blocked'):
                ranges = []
                for ref in gaps[book][category]:
                    chapter, verse = int(ref[1]), int(ref[2])
                    if ranges and ranges[-1][0] == chapter and ranges[-1][2] + 1 == verse:
                        ranges[-1][2] = verse
                    else:
                        ranges.append([chapter, verse, verse])
                counts[category + 'Ranges'] = [f'{book} {c}:{v}' + (f'-{end}' if end != v else '')
                                               for c, v, end in ranges]
        return {'scope': 'Whole numbered reference verses and declared verse-zero titles; '
                         'represented includes atomic groups and ambiguous relationships, not proof of text coverage.',
                'dataRevision': self.data_revision,
                **{key: sum(book[key] for book in books.values())
                   for key in ('referenceCount', 'representedCount', 'unmappedCount', 'blockedCount')},
                'books': books}

    def _table(self, name):
        if name not in self._tables:
            self._tables[name] = _Table(name, self._definitions[name], self._domains[name],
                                        self._reference, self._blocked_reference_books)
        return self._tables[name]

    def convert_range(self, source_system, target_system, start_reference, end_reference):
        """Map an inclusive same-book range as one passage, including any verse gaps.

        Cross-book ordering and segment-range expansion require explicit caller
        input through convert(); neither is guessed from numeric chapter maxima.
        """
        if source_system not in self._domains:
            return self.convert(source_system, target_system, [start_reference])
        try:
            start = normalize_reference(start_reference)
            end = normalize_reference(end_reference)
            if start[0] != end[0]:
                raise ValueError('A cross-book range needs an explicit ordered reference list.')
            if start[3] or end[3]:
                if start == end:
                    return self.convert(source_system, target_system, [start])
                raise ValueError('A segment range needs an explicit list of declared segments.')
            if (int(start[1]), int(start[2])) > (int(end[1]), int(end[2])):
                raise ValueError('Range end precedes its start.')
            domain = self._domains[source_system]
            for endpoint in (start, end):
                problem = domain.issue(endpoint)
                if problem:
                    return self.convert(source_system, target_system, [endpoint])
            expanded = []
            for chapter in range(int(start[1]), int(end[1]) + 1):
                first = int(start[2]) if chapter == int(start[1]) else 1
                last = int(end[2]) if chapter == int(end[1]) else domain.counts[start[0]][chapter - 1]
                for verse in range(first, last + 1):
                    expanded.append((start[0], str(chapter), str(verse), None))
                    if len(expanded) > 10000:
                        raise ValueError('Range exceeds the 10000-reference expansion limit.')
            return self.convert(source_system, target_system, expanded)
        except (TypeError, ValueError) as error:
            return MappingResult(source_system, target_system, (), MappingStatus.INVALID,
                diagnostics=(MappingDiagnostic('RANGE_SYNTAX', str(error), source_system),),
                reference_version=self.reference_version, data_revision=self.data_revision)

    def convert(self, source_system, target_system, references) -> MappingResult:
        """Map an ordered iterable of references, without enlarging the request.

        Unsupported system names return an unsupported result so callers can use
        this method with historical BOS count-only systems. Syntax errors and
        references outside a known system return invalid results.
        Same-system requests validate native addresses and return them directly;
        an unavailable or indivisible cross-system bridge cannot change identity.
        """
        try:
            references = _unique(normalize_reference(r) for r in references)
            if not references:
                raise ValueError('At least one reference is required.')
            if any(r[3] and _whole(r) in references for r in references):
                raise ValueError('Do not request a whole verse and one of its segments together.')
        except (ValueError, TypeError) as error:
            return MappingResult(source_system, target_system, (), MappingStatus.INVALID,
                                 diagnostics=(MappingDiagnostic('REFERENCE_SYNTAX', str(error), source_system),),
                                 reference_version=self.reference_version, data_revision=self.data_revision)

        def result(status, candidates=(), diagnostics=(), provenance=()):
            return MappingResult(source_system, target_system, references, status,
                references=candidates[0] if status == MappingStatus.EXACT else (),
                alternatives=candidates if status in (MappingStatus.AMBIGUOUS, MappingStatus.PARTIAL) else (),
                diagnostics=_unique(diagnostics), provenance=_unique(provenance),
                reference_version=self.reference_version, data_revision=self.data_revision)

        for name in (source_system, target_system):
            if name not in self._domains:
                return result(MappingStatus.UNSUPPORTED, diagnostics=(MappingDiagnostic('UNSUPPORTED_SYSTEM',
                    'No verified mapping profile exists for this system; no legacy alias is inferred.', name),))
        if source_system == target_system:
            issues = [MappingDiagnostic(*problem, source_system, (ref,)) for ref in references
                      if (problem := self._domains[source_system].issue(ref))]
            if source_system == self.reference_name:
                issues.extend(MappingDiagnostic('UNRESOLVED_REFERENCE_BOOK',
                    'Reference book needs a verified bridge.', source_system, (ref,))
                    for ref in references if ref[0] in self._blocked_reference_books)
            if issues:
                status = MappingStatus.INVALID if all(d.code in ('BOOK_NOT_IN_SYSTEM', 'OUTSIDE_SYSTEM') for d in issues) else MappingStatus.UNSUPPORTED
                return result(status, diagnostics=issues)
            return result(MappingStatus.EXACT, (references,))
        if source_system == self.reference_name:
            issues = [MappingDiagnostic('UNRESOLVED_REFERENCE_BOOK', 'Reference book needs a verified bridge.',
                                        source_system, (r,)) for r in references if r[0] in self._blocked_reference_books]
            for ref in references:
                problem = self._reference.issue(ref)
                if problem:
                    issues.append(MappingDiagnostic(*problem, source_system, (ref,)))
            for group in self._reference.merged:
                if set(group) & set(references) and not set(group) <= set(references):
                    return result(MappingStatus.PARTIAL, diagnostics=(MappingDiagnostic('INCOMPLETE_MERGED_VERSE',
                        'Request the complete merged-verse group.', source_system, group),))
            if issues:
                status = MappingStatus.INVALID if all(d.code in ('BOOK_NOT_IN_SYSTEM', 'OUTSIDE_SYSTEM') for d in issues) else MappingStatus.UNSUPPORTED
                return result(status, diagnostics=issues)
        legs = []
        if source_system != self.reference_name:
            legs.append((self._table(source_system), False))
        if target_system != self.reference_name:
            legs.append((self._table(target_system), True))
        candidates = (references,)
        diagnostics, provenance = [], []
        ambiguous = False
        failed = []
        for table, reverse in legs:
            next_candidates = []
            for candidate in candidates:
                status, outputs, issues, origins = table.apply(candidate, reverse=reverse)
                diagnostics.extend(issues)
                provenance.extend(origins)
                if status in (MappingStatus.EXACT, MappingStatus.AMBIGUOUS):
                    ambiguous |= status == MappingStatus.AMBIGUOUS
                    next_candidates.extend(outputs)
                else:
                    failed.append(status)
            candidates = _unique(next_candidates)
            if len(candidates) > 64:
                candidates = candidates[:64]
                ambiguous = True
                diagnostics.append(MappingDiagnostic('ALTERNATIVE_LIMIT',
                    'Composed alternatives were bounded; candidates are not exhaustive.', self.reference_name))
            if not candidates:
                break
        if failed:
            status = MappingStatus.PARTIAL if candidates or MappingStatus.PARTIAL in failed else (
                MappingStatus.INVALID if set(failed) == {MappingStatus.INVALID} else MappingStatus.UNSUPPORTED)
        elif ambiguous or len(candidates) > 1 or not candidates:
            status = MappingStatus.AMBIGUOUS
        else:
            status = MappingStatus.EXACT
        return result(status, candidates, diagnostics, provenance)

    def convert_passage(self, source_system, target_system, references):
        """Opt in to the smallest connected, unambiguous complete mapping group.

        Strict conversion is tried first. Only incomplete atomic/merged groups
        can be enlarged. Follow explicit relationships in both directions on
        both legs, including groups crossing chapters or containing gaps. Never
        choose between competing relationships or infer an enclosing verse range.
        source_references describes the complete coverage; requested_references
        retains the original selection so applications can label combined text.
        """
        strict = self.convert(source_system, target_system, references)
        requested = strict.source_references
        if strict.status != MappingStatus.PARTIAL or not strict.diagnostics or any(
                d.code not in ('INCOMPLETE_MAPPING_GROUP', 'INCOMPLETE_MERGED_VERSE')
                for d in strict.diagnostics):
            return replace(strict, requested_references=requested)
        names = _unique((source_system, self.reference_name, target_system))
        tables = [self._table(name) for name in names if name != self.reference_name]
        coverage = {name: [] for name in names}
        pending, visited = deque(), set()

        def include(name, group):
            existing = coverage[name]
            added = [ref for ref in group if ref not in existing]
            if not added:
                return
            # Insert missing members in the rule's order, at the first member
            # already selected. Preserve the caller's order for complete groups.
            position = next((n for n, ref in enumerate(existing) if ref in group), len(existing))
            existing[:] = [ref for ref in existing if ref not in group]
            existing[position:position] = group
            pending.extend((name, ref) for ref in added)

        include(source_system, requested)
        while pending:
            name, ref = pending.popleft()
            if (name, ref) in visited:
                continue
            visited.add((name, ref))
            if len(visited) > 10000:
                return replace(strict, requested_references=requested, diagnostics=strict.diagnostics + (
                    MappingDiagnostic('EXPANSION_LIMIT', 'Complete-group expansion exceeds 10000 addresses.', name),))
            for group in self._domains[name].merged:
                if ref in group:
                    include(name, group)
            for table in tables:
                if name not in (table.name, self.reference_name):
                    continue
                index = table.reverse if name == self.reference_name else table.forward
                choices = index.get(ref, ())
                if len(choices) > 1:
                    return replace(strict, status=MappingStatus.AMBIGUOUS, requested_references=requested,
                        diagnostics=strict.diagnostics + (MappingDiagnostic('COMPETING_MAPPINGS',
                            'Complete-group expansion touches competing relationships; none was selected.', name, (ref,)),))
                if choices:
                    relation, = choices
                    include(table.name, relation.source)
                    include(self.reference_name, relation.target)
        # A group discovered on the target leg can insert an earlier member.
        # Project its complete order back, rather than appending that earlier
        # verse after the initially requested later member.
        backward = self.convert(target_system, source_system, coverage[target_system])
        source_coverage = (backward.references if backward.status == MappingStatus.EXACT
                           and set(backward.references) == set(coverage[source_system])
                           else coverage[source_system])
        source_coverage = list(source_coverage)
        for group in self._domains[source_system].merged:
            if set(group) <= set(source_coverage) and not set(group) <= set(requested):
                position = next(n for n, ref in enumerate(source_coverage) if ref in group)
                source_coverage[:] = [ref for ref in source_coverage if ref not in group]
                source_coverage[position:position] = group
        expanded = self.convert(source_system, target_system, source_coverage)
        return replace(expanded, requested_references=requested)


@lru_cache(maxsize=1)
def get_default_mapping_engine():
    """Share privately compiled immutable relationships across BOS system objects."""
    return VersificationMappingEngine.from_bundled_data()
