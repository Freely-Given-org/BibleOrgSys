# SPDX-License-Identifier: MPL-2.0
"""Tests for the BookCode type and its helpers.

Run with:
    .venv/bin/python -m unittest discover -s Tests -p test_BookCode.py
"""
import typing
import unittest

from BibleOrgSys.Reference.BookCode import BookCode, internBookCodes, isBookCodeFormat, makeBookCode
from BibleOrgSys.Reference.VerseRef import VerseRef


class BookCodeTests(unittest.TestCase):
    def test_is_a_str_alias(self):
        self.assertIs(BookCode.__value__, str)
        code: BookCode = 'GEN'
        self.assertIsInstance(code, str)

    def test_format_check(self):
        for good in ('GEN', 'MAT', '1SA', 'PS2', 'LAO'):
            with self.subTest(good=good):
                self.assertTrue(isBookCodeFormat(good))
        for bad in ('gen', 'GE', 'GENE', 'GE-', '', None, 123, ' GEN', 'GEN\n'):
            with self.subTest(bad=bad):
                self.assertFalse(isBookCodeFormat(bad))

    def test_make_book_code(self):
        self.assertEqual(makeBookCode('1SA'), '1SA')
        with self.assertRaises(ValueError):
            makeBookCode('1sa')

    def test_make_book_code_shares_one_string(self):
        line = 'GEN 1:1 MAT 2:2'
        separateCopy = line[:3] # A new string object each time
        self.assertIsNot(separateCopy, line[:3])
        self.assertIs(makeBookCode(separateCopy), makeBookCode(line[:3]))

    def test_codes_from_rust_share_one_string(self):
        import bos_books_codes_py
        first = bos_books_codes_py.get_bos_book_code_from_reference_number(1)
        self.assertEqual(first, 'GEN')
        self.assertIs(first, bos_books_codes_py.get_bos_book_code_from_reference_number(1))
        self.assertIs(first, bos_books_codes_py.osis_book_code_to_bos_book_code('Gen'))
        self.assertIs(first, bos_books_codes_py.usfm_abbrev_to_bos_book_code('GEN'))
        self.assertIs(first, bos_books_codes_py.get_all_bos_book_codes()[0])
        self.assertIs(first, makeBookCode('GEN 1:1'[:3]))

    def test_intern_book_codes_in_nested_data(self):
        def separate(text): return (text + ' ')[:3] # Makes a new string object
        data = { separate('GEN'): [separate('EXO'), 5, 'Genesis'],
                 (separate('MAT'), '1'): (separate('MRK'), {separate('LUK'): None}),
                 'name': separate('JHN'), 7: 'abc' }
        expected = { 'GEN': ['EXO', 5, 'Genesis'], ('MAT', '1'): ('MRK', {'LUK': None}), 'name': 'JHN', 7: 'abc' }
        result = internBookCodes(data)
        self.assertIs(result, data) # Dicts are updated in place
        self.assertEqual(data, expected)
        self.assertEqual(list(data), list(expected)) # Key order is kept
        keys = list(data)
        self.assertIs(keys[0], makeBookCode('GEN'))
        self.assertIs(keys[1][0], makeBookCode('MAT'))
        self.assertIs(data['GEN'][0], makeBookCode('EXO'))
        self.assertIs(data[('MAT', '1')][0], makeBookCode('MRK'))
        self.assertIs(list(data[('MAT', '1')][1])[0], makeBookCode('LUK'))
        self.assertIs(data['name'], makeBookCode('JHN'))
        unchanged = ('abc', 5)
        self.assertIs(internBookCodes(unchanged), unchanged)

    def test_verse_ref_field_is_book_code(self):
        self.assertIs(typing.get_type_hints(VerseRef)['BBB'], BookCode)


if __name__ == '__main__':
    unittest.main()
