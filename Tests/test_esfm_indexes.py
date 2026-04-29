"""Integration test: load a real ESFM file and verify Rust-backed indexes.

Requires network access to download OET-RV Haggai from GitHub.
Run with:  uv run pytest tests/test_esfm_indexes.py -v
"""

import os
import tempfile
import urllib.request

import pytest

from BibleOrgSys import BibleOrgSysGlobals
from BibleOrgSys.Formats import ESFMBible
from bible_organisational_system import (
    InternalBibleBookCVIndex,
    InternalBibleBookSectionIndex,
    InternalBibleEntryList,
    ChapterVerse,
)

HAG_URL = (
    "https://raw.githubusercontent.com/Freely-Given-org/OpenEnglishTranslation--OET"
    "/refs/heads/main/translatedTexts/ReadersVersion/OET-RV_HAG.ESFM"
)


@pytest.fixture(scope="module")
def haggai_entries() -> InternalBibleEntryList:
    """Download and parse OET-RV Haggai, returning the processed entry list."""
    BibleOrgSysGlobals.preloadCommonData()

    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "OET-RV_HAG.ESFM")
        urllib.request.urlretrieve(HAG_URL, filepath)

        bible = ESFMBible.ESFMBible(
            tmpdir, givenName="OET-RV", givenAbbreviation="OET-RV"
        )
        bible.loadBooks()

        books = list(bible.books.values())
        assert len(books) == 1, f"Expected 1 book, got {len(books)}"
        return books[0]._processedLines


@pytest.fixture(scope="module")
def cv_index(haggai_entries: InternalBibleEntryList) -> InternalBibleBookCVIndex:
    idx = InternalBibleBookCVIndex("OET-RV", "HAG")
    idx.build(haggai_entries)
    return idx


@pytest.fixture(scope="module")
def section_index(
    haggai_entries: InternalBibleEntryList,
) -> InternalBibleBookSectionIndex:
    idx = InternalBibleBookSectionIndex("OET-RV", "HAG")
    idx.makeBookSectionIndex(haggai_entries)
    return idx


class TestCVIndex:
    def test_is_indexed(self, cv_index: InternalBibleBookCVIndex):
        assert cv_index.is_indexed

    def test_chapter_count(self, cv_index: InternalBibleBookCVIndex):
        # chapters() includes '-1' for intro/header content
        real_chapters = [c for c in cv_index.chapters() if c != "-1"]
        assert len(real_chapters) == 2

    def test_chapter_1_verses(self, cv_index: InternalBibleBookCVIndex):
        assert ("1", "1") in cv_index
        assert ("1", "15") in cv_index
        assert ("1", "16") not in cv_index

    def test_chapter_2_verses(self, cv_index: InternalBibleBookCVIndex):
        assert ("2", "1") in cv_index
        assert ("2", "23") in cv_index
        assert ("2", "24") not in cv_index

    def test_no_chapter_3(self, cv_index: InternalBibleBookCVIndex):
        assert ("3", "1") not in cv_index

    def test_verse_lookup_returns_entries(self, cv_index: InternalBibleBookCVIndex):
        entries = cv_index.get_verse_entries(ChapterVerse("1", "1"))
        assert len(entries) > 0

    def test_chapter_lookup_returns_entries(self, cv_index: InternalBibleBookCVIndex):
        entries = cv_index.get_chapter_entries("1")
        assert len(entries) > 0


class TestSectionIndex:
    def test_is_indexed(self, section_index: InternalBibleBookSectionIndex):
        assert section_index._indexedFlag

    def test_has_sections(self, section_index: InternalBibleBookSectionIndex):
        assert len(section_index) > 0

    def test_table_of_contents(self, section_index: InternalBibleBookSectionIndex):
        toc = section_index.items()
        assert len(toc) > 0
        names = [entry.sectionName for _cv, entry in toc]
        assert any("rebuild" in n.lower() or "temple" in n.lower() for n in names)
