# SPDX-License-Identifier: MPL-2.0
"""Adapt Paratext enhanced resources to USX, retaining their word links.

The input tree is changed only in memory. Word-group records retain source
attributes, native verse labels, and an XML path (relative to usx_book), so
repeated surface words and many-to-many links remain distinguishable. Offsets
into BOS's processed text are deliberately not inferred from these paths.
"""
import re

import bos_books_codes_py


def normaliseEnhancedUSX(root, BBB):
    """Return native (chapter, verse) -> word-group records for enhanced USX.

    Ordinary USX is left alone. Enhanced files use a book wrapper and may put
    the only verse address in pubnumber. Prefer sid when supplied: pubnumber
    can be a display label. Never guess an address from an ambiguous label.
    """
    wrappers = root.findall('usx_book')
    if not wrappers:
        return None
    if len(wrappers) != 1 or len(root) != 1:
        raise ValueError('Enhanced USX must contain exactly one usx_book')
    wrapper = wrappers[0]
    if bos_books_codes_py.usfm_abbrev_to_bos_book_code(wrapper.get('code', '')) != BBB:
        raise ValueError(f'Enhanced USX book identity does not match {BBB}')
    root[:] = list(wrapper)
    groups = {}
    chapter, verse = '-1', '-1'

    def walk(element, path, context='text'):
        nonlocal chapter, verse
        if element.tag == 'chapter':
            if 'eid' in element.attrib:
                return
            chapter = element.get('number')
            if chapter is None:
                raise ValueError(f'Missing enhanced USX chapter number in {BBB}')
            verse = '0'
        elif element.tag == 'verse':
            if 'eid' in element.attrib:
                return
            number = element.get('number')
            sid = element.get('sid')
            if sid:
                match = re.fullmatch(r'([A-Z0-9]{3}) (\d+):(.+)', sid)
                if not match or bos_books_codes_py.usfm_abbrev_to_bos_book_code(match[1]) != BBB \
                        or match[2] != chapter or (number is not None and number != match[3]):
                    raise ValueError(f'Conflicting enhanced USX verse address: {sid}')
                number = match[3]
            if number is None:
                number = element.get('pubnumber')
            if number and re.fullmatch(r'\d+(?:,\s*\d+)+', number):
                verses = [int(v) for v in number.split(',')]
                if verses == list(range(verses[0], verses[-1]+1)):
                    number = f'{verses[0]}-{verses[-1]}'
            if not number or not re.fullmatch(r'\d+[a-z]?(?:-\d+[a-z]?)?', number):
                raise ValueError(f'Unusable enhanced USX verse address at {BBB} {chapter}: {number!r}')
            element.set('number', number)
            verse = number
        elif element.tag == 'note':
            context = 'note'
        elif element.tag == 'para':
            style = element.get('style', '')
            if style.startswith(('s', 'ms', 'mt', 'imt', 'is', 'toc')) or style in ('r', 'd', 'sp'):
                context = 'heading'
        if element.tag == 'wg':
            records = groups.setdefault((chapter, verse), [])
            records.append({'text': ''.join(element.itertext()),
                            'attributes': dict(element.attrib),
                            'xmlPath': path, 'context': context})
            # Existing USX character processing preserves text and nested styles.
            # Link attributes are retained above, rather than inserted into prose.
            element.tag = 'char'
            element.attrib.clear()
            element.set('style', 'w')
        for index, child in enumerate(element):
            walk(child, (*path, index), context)

    for index, element in enumerate(root):
        walk(element, (index,))
    return groups
