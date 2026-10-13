# SPDX-License-Identifier: MPL-2.0
"""Bible-level versification declarations, metadata policy, and conversion facade.

Declarations describe numbering; they do not rewrite or certify loaded text.
Only names and declaration evidence are persisted, never compiled mapping tables.
See Documentation/BibleVersification.md for precedence and format-specific limits.
"""

from dataclasses import replace
import json
from pathlib import Path
from xml.etree import ElementTree

from BibleOrgSys.Reference.BibleVersificationMappings import (
    MappingDiagnostic, MappingStatus, UnknownVersificationSystemError, get_default_mapping_engine,
)


# SIL.Scripture/Versification.cs, ScrVersType (legacy numeric order), and the
# bundled Copenhagen standard-mappings README. These aliases are PTX-specific;
# a BOS caller's 'Original' or 'Vulgate' still means the historical BOS system.
PARATEXT_SYSTEMS = dict(zip(
    ('1', '2', '3', '4', '5', '6', 'Original', 'Septuagint', 'Vulgate',
     'English', 'RussianProtestant', 'RussianOrthodox'),
    ('org', 'lxx', 'vul', 'eng', 'rsc', 'rso') * 2,
))


def _system_name(system):
    if isinstance(system, str):
        return system
    from BibleOrgSys.Reference.BibleVersificationSystems import BibleVersificationSystem
    if isinstance(system, BibleVersificationSystem):
        return system.getVersificationSystemName()
    raise TypeError('A versification must be a BOS system name or BibleVersificationSystem.')


def _known_system(name):
    if name in get_default_mapping_engine().get_system_names():
        return True
    from BibleOrgSys.Reference.BibleVersificationSystems import BibleVersificationSystems
    return name in BibleVersificationSystems().loadData()


def _resolve_metadata(value, namespace):
    if type(value) not in (str, int):
        return None
    name = str(value).strip()
    if namespace == 'paratext':
        # A custom name or 0 is deliberately not treated as its presumed base.
        return PARATEXT_SYSTEMS.get(name) or (name if name in get_default_mapping_engine().get_system_names() else None)
    if namespace == 'osis' and name == 'Bible.KJV':
        return 'KJV'  # Recognised count-only profile, never an alias for eng.
    return name if name and _known_system(name) else None


class BibleVersificationMixin:
    """Shared by InternalBible and every format loader; old pickles need no migration."""

    def _readVersificationState(self):
        saved = getattr(self, '_versificationState', None)
        if saved is None:
            return {'version': 1, 'explicit': None, 'metadata': []}
        state = json.loads(saved)
        if state.get('version') != 1:
            raise ValueError('Unsupported saved Bible versification declaration version.')
        return state

    def _saveVersificationState(self, state):
        # A string survives both ordinary pickle and the restricted BOS attribute
        # serializer (including dataLevel=1). Read access always returns new objects.
        self._versificationState = json.dumps(state, ensure_ascii=False, sort_keys=True)

    def _restoreVersificationState(self, saved):
        """Restore a BOS attribute archive without overriding a new caller choice."""
        explicit = self._readVersificationState()['explicit']
        self._versificationState = saved
        restored = self._readVersificationState()
        if explicit is not None:
            if restored['explicit'] is not None:
                self._recordVersificationMetadata('Saved Bible', 'VersificationSystem', restored['explicit'])
            self.setVersificationSystem(explicit)

    def setVersificationSystem(self, system):
        """Declare an explicit numbering system, taking precedence over all metadata.

        Unknown caller names raise without changing the current declaration.
        Known historical count-only systems may be declared but cannot convert.
        Returns self for use before load()/loadBooks() on any format.
        """
        name = _system_name(system)
        if not _known_system(name):
            raise UnknownVersificationSystemError(f'Unknown versification system: {name!r}')
        state = self._readVersificationState()
        state['explicit'] = name
        self._saveVersificationState(state)
        return self

    def clearVersificationSystem(self):
        """Clear the caller override; metadata declarations and conflicts remain."""
        state = self._readVersificationState()
        state['explicit'] = None
        self._saveVersificationState(state)
        return self

    def _recordVersificationMetadata(self, source, field, value, *, namespace='bos', reason=None):
        """Replace one source/field observation, retaining independent observations."""
        state = self._readVersificationState()
        record = {'source': source, 'field': field, 'value': value, 'namespace': namespace,
                  'system': _resolve_metadata(value, namespace), 'reason': reason}
        # Metadata loaders may supply a malformed non-scalar. Preserve its printed
        # representation rather than allowing it to become a declaration.
        if type(value) not in (str, int, bool, type(None)):
            record['value'] = repr(value)
        state['metadata'] = [r for r in state['metadata'] if (r['source'], r['field']) != (source, field)]
        state['metadata'].append(record)
        self._saveVersificationState(state)

    def _clearVersificationMetadataSource(self, source):
        state = self._readVersificationState()
        state['metadata'] = [r for r in state['metadata'] if r['source'] != source]
        self._saveVersificationState(state)

    def getVersificationDeclaration(self):
        """Return detached evidence, resolution status, chosen name, and diagnostics.

        With no caller override, every observation must resolve to the same name.
        Unknown/custom metadata blocks automatic selection even if another source
        supplies a recognised name. An override preserves all conflicting evidence.
        """
        state = self._readVersificationState()
        observations = state['metadata']
        known = {r['system'] for r in observations if r['system'] is not None}
        unresolved = [r for r in observations if r['system'] is None or r['reason']]
        explicit = state['explicit']
        conflicts = len(known) > 1 or (explicit is not None and any(n != explicit for n in known))
        diagnostics = []
        if conflicts:
            diagnostics.append({'code': 'VERSIFICATION_CONFLICT',
                'message': 'Versification declarations disagree.' + (' The explicit caller declaration takes precedence.' if explicit else '')})
        for record in unresolved:
            diagnostics.append({'code': 'UNRESOLVED_VERSIFICATION_METADATA',
                'message': f"{record['source']} {record['field']}={record['value']!r}: "
                           + (record['reason'] or 'No verified interpretation of this declaration is available.')})
        if explicit is not None:
            status, name, source = 'declared', explicit, 'caller'
        elif conflicts:
            status, name, source = 'conflict', None, 'metadata'
        elif unresolved:
            status, name, source = 'unresolved', None, 'metadata'
        elif known:
            status, name, source = 'declared', next(iter(known)), 'metadata'
        else:
            status, name, source = 'undeclared', None, None
            diagnostics.append({'code': 'UNDECLARED_VERSIFICATION', 'message': 'No versification has been declared for this Bible.'})
        return {'status': status, 'system': name, 'source': source,
                'explicit': explicit, 'metadata': observations, 'diagnostics': diagnostics}

    def getVersificationSystemName(self):
        """Return the effective declaration, or None if it cannot be resolved."""
        return self.getVersificationDeclaration()['system']

    def getVersificationSystem(self):
        """Return a fresh BOS system object, or None; does not infer from verse counts."""
        name = self.getVersificationSystemName()
        if name is None:
            return None
        from BibleOrgSys.Reference.BibleVersificationSystems import BibleVersificationSystem
        return BibleVersificationSystem(name)

    def getMappingCapabilities(self):
        declaration = self.getVersificationDeclaration()
        return {**get_default_mapping_engine().capabilities(declaration['system']),
                'declarationStatus': declaration['status'], 'diagnostics': declaration['diagnostics']}

    def _convertVersification(self, target, references, *, from_reference=False, from_system=None, end=None):
        engine = get_default_mapping_engine()
        own = self.getVersificationDeclaration()
        incoming = from_reference or from_system is not None
        declarations = [('target' if incoming else 'source', own)]
        own_name = own['system'] or f"<{own['status']} Bible>"
        other_system = engine.reference_name if from_reference else from_system if incoming else target
        if isinstance(other_system, BibleVersificationMixin):
            other = other_system.getVersificationDeclaration()
            declarations.append(('source' if incoming else 'target', other))
            other_name = other['system'] or f"<{other['status']} Bible>"
        else:
            other_name = _system_name(other_system)
        source_name, target_name = (other_name, own_name) if incoming else (own_name, other_name)
        if end is None:
            result = engine.convert(source_name, target_name, references)
        else:
            result = engine.convert_range(source_name, target_name, references, end)
        diagnostics = tuple(MappingDiagnostic(d['code'], f"{side}: {d['message']}", 'Bible declaration')
                            for side, declaration in declarations for d in declaration['diagnostics'])
        if any(d['status'] == 'conflict' for _, d in declarations) and result.status != MappingStatus.INVALID:
            result = replace(result, status=MappingStatus.AMBIGUOUS)
        return replace(result, diagnostics=diagnostics + result.diagnostics)

    def convertToReferenceVersification(self, BBB, C, V, S=None, *, detailed=False):
        result = self.convertReferencesToVersification(get_default_mapping_engine().reference_name, [(BBB, C, V, S)])
        return result if detailed else result.require_single()

    def convertFromReferenceVersification(self, BBB, C, V, S=None, *, detailed=False):
        result = self.convertReferencesFromReferenceVersification([(BBB, C, V, S)])
        return result if detailed else result.require_single()

    def convertToVersification(self, targetSystem, BBB, C, V, S=None, *, detailed=False):
        """Target may be a name, system object, or another Bible's declaration."""
        result = self.convertReferencesToVersification(targetSystem, [(BBB, C, V, S)])
        return result if detailed else result.require_single()

    def convertReferencesToVersification(self, targetSystem, references):
        return self._convertVersification(targetSystem, references)

    def convertReferencesFromVersification(self, sourceSystem, references):
        """Convert an external passage into this Bible's declared numbering.

        sourceSystem may be a name, system object, or another Bible. Declaration
        conflicts on either Bible retain the same diagnostics/status as outgoing
        conversions. This method converts references without loading any text.
        """
        if sourceSystem is None:
            raise TypeError('A source versification is required.')
        return self._convertVersification(None, references, from_system=sourceSystem)

    def convertReferencesFromReferenceVersification(self, references):
        return self._convertVersification(None, references, from_reference=True)

    def convertRangeToVersification(self, targetSystem, startRef, endRef):
        return self._convertVersification(targetSystem, startRef, end=endRef)

    def convertRangeFromReferenceVersification(self, startRef, endRef):
        return self._convertVersification(None, startRef, from_reference=True, end=endRef)

    def _applyVersificationMetadata(self, metadata_type):
        supplied = self.suppliedMetadata or {}
        namespace = 'bos'
        source = metadata_type
        reason = None
        if metadata_type in ('PTX7', 'SSF', 'PTX8'):
            project = supplied.get('PTX8' if metadata_type == 'PTX8' else 'PTX7', {})
            values = project.get('Settings' if metadata_type == 'PTX8' else 'SSF', {})
            namespace = 'paratext'
            source = 'PTX8' if metadata_type == 'PTX8' else 'PTX7'
            reason = _project_mapping_reason(getattr(self, 'sourceFolder', None))
            if project.get('Versifications'):
                reason = 'Project VRS definitions are present; custom overrides have not been resolved.'
        elif metadata_type == 'OSIS':
            # The parsers historically flatten all work headers into RefSystem.
            # Only the separate, work-aware header reader may declare a scheme.
            return
        else:
            values = supplied.get(metadata_type, {})
        self._clearVersificationMetadataSource(source)
        for field, value in values.items():
            if field.strip().lower() in ('versification', 'versificationsystem'):
                self._recordVersificationMetadata(source, field, value, namespace=namespace, reason=reason)

    def _loadVersificationProjectMetadata(self):
        """Read numbering declarations only from local Settings.xml / SSF companions."""
        folder = Path(self.sourceFolder)
        reason = _project_mapping_reason(folder)
        for path in sorted(folder.iterdir()):
            if not path.is_file() or not (path.name.lower() == 'settings.xml' or path.suffix.lower() == '.ssf'):
                continue
            self._clearVersificationMetadataSource(path.name)
            try:
                root = ElementTree.parse(path).getroot()
                if root.tag != 'ScriptureText':
                    raise ValueError('Expected a ScriptureText settings document.')
                for index, element in enumerate(root.findall('Versification')):
                    self._recordVersificationMetadata(path.name, f'Versification[{index}]', element.text,
                                                      namespace='paratext', reason=reason)
            except (OSError, ValueError, ElementTree.ParseError) as error:
                self._recordVersificationMetadata(path.name, 'Versification', None, reason=f'Cannot read project settings: {error}')

    def _loadOSISVersificationMetadata(self, filepath):
        """Scan only the header, on the parent process, before either OSIS parser runs.

        Use the work identified by osisIDWork, never osisRefWork (cross-references)
        or the last work encountered. Multiple own-work declarations are retained.
        """
        namespace = '{http://www.bibletechnologies.net/2003/OSIS/namespace}'
        source = f'OSIS:{Path(filepath).name}'
        self._clearVersificationMetadataSource(source)
        own_work = None
        try:
            with open(filepath, 'rb') as stream:
                for event, element in ElementTree.iterparse(stream, events=('start', 'end')):
                    if event == 'start' and element.tag == namespace + 'osisText':
                        own_work = element.get('osisIDWork')
                    elif event == 'end' and element.tag == namespace + 'header':
                        index = 0
                        for work in element.findall(namespace + 'work'):
                            if own_work is not None and work.get('osisWork') == own_work:
                                for ref_system in work.findall(namespace + 'refSystem'):
                                    self._recordVersificationMetadata(source, f'{own_work}.refSystem[{index}]',
                                                                     ref_system.text, namespace='osis')
                                    index += 1
                        break
                    elif event == 'start' and element.tag == namespace + 'div':
                        break  # No header; do not scan the complete Bible to guess one.
        except (OSError, ElementTree.ParseError) as error:
            self._recordVersificationMetadata(source, 'refSystem', None, reason=f'Cannot read OSIS header: {error}')


def _project_mapping_reason(folder):
    if folder is None:
        return None
    try:
        if any(path.is_file() and path.suffix.lower() == '.vrs' for path in Path(folder).iterdir()):
            return 'Project VRS definitions are present; custom overrides have not been resolved.'
    except OSError:
        return 'Project folder cannot be inspected for custom VRS overrides.'
    return None
