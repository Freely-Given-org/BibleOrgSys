# SPDX-License-Identifier: MPL-2.0
"""Tests for the BookCode type and its helpers.

Run with:
    .venv/bin/python -m unittest discover -s Tests -p test_BookCode.py
"""
import typing
import unittest

from BibleOrgSys.Reference.BookCode import BookCode, isBookCodeFormat, makeBookCode
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

    def test_verse_ref_field_is_book_code(self):
        self.assertIs(typing.get_type_hints(VerseRef)['BBB'], BookCode)


if __name__ == '__main__':
    unittest.main()
