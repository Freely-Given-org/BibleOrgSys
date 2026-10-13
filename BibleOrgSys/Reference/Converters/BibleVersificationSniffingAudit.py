# SPDX-License-Identifier: MPL-2.0
"""Reproducible triage of the Copenhagen sniffing rows, not a rule importer.

Tradition labels are candidates for comparison only. Counts, edition-specific
notations, textual restrictions, and surrounding mappings can prevent a rule
from describing a registered BOS profile. Only reviewed mapping-supplement
entries affect runtime conversion. The report retains every row's coordinates.
"""

from collections import Counter
import re

from BibleOrgSys.Reference.Converters.BibleVersificationMappingsConverter import (
    VersificationDataError, bos_book_code,
)


GROUP_TYPES = frozenset(('SubdividedVerse', 'MergedVerses'))
_PATTERN = re.compile(r'([1-4]?[A-Za-z0-9]+)\.([0-9]+):([0-9]+)(?:-(?:([0-9]+):)?([0-9]+))?')
_SOURCE_CODES = {'1Ch': '1CH', '2Ch': '2CH', '1Sa': '1SA', '2Sa': '2SA',
                 '1Ki': '1KI', '2Ki': '2KI', '1Es': '1ES', '2Es': '2ES',
                 '1Co': '1CO', '2Co': '2CO', '1Jn': '1JN', '3Jn': '3JN',
                 '2Ma': '2MA', 'Ps2': 'PS2', 'LJe': 'LJE'}
_PROFILE_LABELS = {'eng': 'English', 'vul': 'Latin', 'lxx': 'Greek'}
# Review notes apply only to still-disagreeing candidates in the pinned snapshot.
# They never change the engine or certify the existing rule as correct.
_REVIEW_NOTES = {
    ('lxx', 'Exo.28:22-28:43'): 'Greek sniffing expects chapter 28 to end at 39; bundled lxx ends at 43 and has no matching shifts.',
    ('vul', 'Exo.39:1-39:43'): 'The chapter includes duplicated/moved material and shifted neighbours, but vul has no explicit chapter-39 mappings. A group-only patch would collide with existing identities; reconcile the entire passage first.',
    ('lxx', 'Deu.14:14-14:29'): 'Greek sniffing ends chapter 14 at 28; bundled lxx ends at 29 without the following shift.',
    ('lxx', 'Pro.20:20-22'): 'Bundled lxx has no chapter-20 mappings corroborating the proposed relocation to verse 9; verify the witness and surrounding text.',
    ('lxx', 'Isa.63:19-64:12'): 'Greek sniffing expects 12 verses in chapter 64; bundled lxx has 11, like org.',
    ('lxx', 'Hos.1:10-2:23'): 'Greek sniffing expects 23 verses in chapter 2; bundled lxx has 25, like org. The difference here is positional, not a missing group.',
    ('lxx', 'Mic.5:1-5:15'): 'Greek sniffing expects 15 verses in chapter 5; bundled lxx has 14, like org. Do not copy the English shift into lxx.',
    ('lxx', 'Zep.2:15-3:2'): 'Greek sniffing ends chapter 2 at 14; bundled lxx ends at 15 without the proposed chapter transfer.',
    ('eng', 'Bar.3:34-38'): 'Counts agree with the row, but eng lacks both the group and all following chapter-3 shifts. Verify the text and correct the whole passage together; a group-only patch would collide with verse-35 identity.',
    ('vul', 'Wis.17:9-17:21'): 'The Greek comparison expects 21 verses, but org has 20 and supplies no chapter-17 mappings. The reference edition must be resolved first.',
    ('vul', '2Ma.15:37-15:39'): 'Raw vul instead relates 36 and 37 to org 36, then 38-40 to org 37-39. That places the division a verse earlier than the sniffing row; text verification must choose between them.',
}


def sniffing_references(text, system, engine, bundle):
    """Expand only complete numeric row addresses using the named domain.

    No suffix conversion, missing endpoint, edition label or book-combination
    bridge is inferred. Counts are needed only for explicit cross-chapter ranges.
    """
    match = _PATTERN.fullmatch(text)
    if not match:
        raise VersificationDataError('Incomplete, segmented, absent, or unsupported sniffing address.')
    raw, chapter, first, end_chapter, last = match.groups()
    book = bos_book_code(_SOURCE_CODES.get(raw, raw.upper()), system, bundle['bookCodes'])
    chapter, first = int(chapter), int(first)
    end_chapter, last = int(end_chapter or chapter), int(last or first)
    if (end_chapter, last) < (chapter, first):
        raise VersificationDataError('Reversed sniffing span.')
    domain = engine._domains[system]
    counts = domain.counts.get(book, ())
    if not 1 <= chapter <= end_chapter <= len(counts):
        raise VersificationDataError('Sniffing span is outside this profile.')
    result = []
    for c in range(chapter, end_chapter+1):
        lo = first if c == chapter else 1
        hi = last if c == end_chapter else counts[c-1]
        if not 0 <= lo <= hi <= counts[c-1] or len(result) + hi-lo+1 > 10000:
            raise VersificationDataError('Sniffing verse range is outside this profile.')
        result.extend((book, str(c), str(v), None) for v in range(lo, hi+1))
    if any(domain.issue(r) for r in result):
        raise VersificationDataError('Sniffing endpoints are undeclared or excluded in this profile.')
    return tuple(result)


def _assess(rule, row_index, kind, values, profile, engine, bundle, corrections):
    # A reviewed correction has precedence over incomplete upstream notation.
    reviewed = [c for c in corrections if c['system'] == profile
                and c['evidence']['copenhagenRule'] == rule['name']
                and c['evidence'].get('copenhagenRangeIndex') == row_index]
    if reviewed:
        return {'status': 'reviewed-correction', 'corrections': [c['id'] for c in reviewed],
                'reason': 'Explicit supplement with recorded evidence and bidirectional regression tests.'}
    label = _PROFILE_LABELS[profile]
    source_columns = [i for i, labels in enumerate(rule['columns']) if label in labels]
    if len(source_columns) != 1:
        return {'status': 'edition-not-selected',
                'reason': f'No unique unqualified {label} column; qualified editions are not profile aliases.'}
    source_index = source_columns[0]
    labels = [label for column in rule['columns'] for label in column]
    reference_label = 'Hebrew' if 'Hebrew' in labels else 'Greek'
    reference_columns = [i for i, column in enumerate(rule['columns']) if reference_label in column]
    if len(reference_columns) != 1:
        return {'status': 'reference-edition-unresolved', 'reason': 'No unqualified Hebrew/Greek comparison column.'}
    reference_index = reference_columns[0]
    source_text, target_text = values[source_index], values[reference_index]
    if profile == 'vul' and source_text.startswith(('Sir.', 'Tob.', 'Jdt.')):
        return {'status': 'textual-tradition-blocked',
                'reason': 'The standard-mappings README explicitly withholds this Latin textual bridge.'}
    if source_index == reference_index:
        return {'status': 'same-column',
                'reason': 'This row does not distinguish these candidate traditions; it does not certify profile equivalence.'}
    if source_text.startswith(('Est.', 'Esg.', 'Tob.', 'Bar.6:', '1Es.', '2Es.')):
        return {'status': 'witness-or-book-bridge-review',
                'reason': 'Witness identity, combined/extract books or surrounding Esdras mappings need reconciliation before a group-only patch.'}
    # English titles in these rows are attached to body verse 1. BOS uses 0.
    # Compare the complete title+body passage, without changing either boundary.
    title = (profile == 'eng' and kind == 'SubdividedVerse'
             and re.fullmatch(r'Psa\.[0-9]+:1', source_text)
             and 'EngTitleSeparate' in labels)
    try:
        source = sniffing_references(source_text, profile, engine, bundle)
        target = sniffing_references(target_text, 'org', engine, bundle)
        if title:
            source = ((source[0][0], source[0][1], '0', None),) + source
        forward = engine.convert(profile, 'org', source)
        inverse = engine.convert('org', profile, target)
    except ValueError as error:
        return {'status': 'notation-or-domain-review', 'reason': str(error)}
    observed = {'forwardStatus': forward.status.value, 'inverseStatus': inverse.status.value,
                'source': [list(r) for r in source], 'target': [list(r) for r in target],
                'returnedReferences': [list(r) for r in forward.references]}
    if title:
        if (forward.status.value == inverse.status.value == 'exact'
                and forward.references == target and inverse.references == source):
            return {'status': 'title-convention-covered', 'reason': 'Separate BOS title plus body verse already covers the row.', **observed}
        return {'status': 'title-convention-review', 'reason': 'The row combines a title/body or edition-specific segments; do not merge numbered body verses automatically.', **observed}
    if source == target and source_text == target_text:
        return {'status': 'no-group-difference', 'reason': 'The listed whole-verse groups are identical in these two columns.', **observed}
    if (len(source) == len(target) and forward.status.value == inverse.status.value == 'exact'
            and forward.references == target and inverse.references == source
            and all(engine.convert(profile, 'org', [s]).references == (t,)
                    and engine.convert('org', profile, [t]).references == (s,)
                    for s, t in zip(source, target))):
        return {'status': 'positional-alignment-covered',
                'reason': 'These columns already align verse by verse; another column causes the row\'s split/merge classification.', **observed}
    # A successful whole-group call is insufficient: the old engine could also
    # map either half independently as exact, losing the distinction between parts.
    atomic = all(engine.convert(a, b, [ref]).status.value != 'exact'
                 for a, b, group in ((profile, 'org', source), ('org', profile, target))
                 if len(group) > 1 for ref in group)
    if (forward.status.value == inverse.status.value == 'exact'
            and forward.references == target and inverse.references == source and atomic):
        return {'status': 'already-covered', 'reason': 'The complete group and its partial-member contract agree.', **observed}
    return {'status': 'candidate-needs-review',
            'reason': _REVIEW_NOTES.get((profile, rule['name']),
                'The proposed group differs from compiled relationships. Tradition labels alone cannot authorise a correction; verify edition counts, content and neighbouring shifts.'),
            **observed}


def build_sniffing_report(bundle, engine):
    """Inventory all rows, retaining explicit assessments for every split/merge."""
    corrections = bundle['supplement']['corrections']
    rows, type_counts, statuses = [], Counter(), Counter()
    for rule_index, rule in enumerate(bundle['supplementEvidence']):
        for row_index, row in enumerate(rule['ranges']):
            if len(row) != 1:
                raise VersificationDataError('Expected one sniffing row type.')
            kind, values = next(iter(row.items()))
            type_counts[kind] += 1
            entry = {'ruleIndex': rule_index, 'rangeIndex': row_index, 'rule': rule['name'],
                     'type': kind, 'columns': rule['columns'], 'references': values,
                     'sniffingTests': rule.get('tests', [])}
            if len(values) != len(rule['columns']):
                entry['status'] = 'malformed-row'
                entry['reason'] = 'The verbatim row has fewer/more values than declared columns; column alignment cannot be inferred.'
            elif kind in GROUP_TYPES:
                entry['profiles'] = {profile: _assess(rule, row_index, kind, values, profile, engine, bundle, corrections)
                                     for profile in _PROFILE_LABELS}
                statuses.update(a['status'] for a in entry['profiles'].values())
            else:
                entry['status'] = 'positional-row' if kind == 'OneToOne' else 'textual-content-review'
                entry['reason'] = ('Positional mappings are outside this split/merge audit.' if kind == 'OneToOne'
                                   else 'Missing, duplicated, moved or extended content needs textual/segment review; not promoted to a whole-verse group.')
            rows.append(entry)
    return {'formatVersion': 1, 'sourceSnapshot': bundle['manifest']['snapshotCommit'],
            'mappingDataRevision': engine.data_revision, 'dataLicense': 'CC-BY-SA-4.0',
            'scope': 'Audit of every Copenhagen sniffing row; explicit split/merge assessments for eng, vul and lxx. '
                     'Candidate labels are comparisons, never automatic aliases or runtime mappings. '
                     'Unreviewed findings do not change the existing runtime profile.',
            'ruleCount': len(bundle['supplementEvidence']), 'rowCount': len(rows),
            'splitMergeRowCount': sum(type_counts[t] for t in GROUP_TYPES),
            'rowTypeCounts': dict(sorted(type_counts.items())), 'assessmentCounts': dict(sorted(statuses.items())),
            'unmatchedProfiles': {'rsc': 'No Russian Protestant edition column is identified.',
                                  'rso': 'Slavonic/Bulgarian columns are not Russian Orthodox profile aliases.',
                                  'ethiopian_custom': 'No Ethiopian edition column; the profile remains disabled.'},
            'rows': rows}
