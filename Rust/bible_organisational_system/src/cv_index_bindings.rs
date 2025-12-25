//! Python bindings for the CV Index types.
//!
//! This module provides PyO3 bindings for:
//! - `PyChapterVerse` - Chapter:Verse reference
//! - `PyCVIndexEntry` - Index entry for a single C:V reference
//! - `PyInternalBibleEntry` - A single Bible text entry
//! - `PyInternalBibleEntryList` - Collection of Bible entries
//! - `PyInternalBibleBookCVIndex` - CV index for fast verse lookup

use pyo3::prelude::*;
use pyo3::exceptions::{PyKeyError, PyRuntimeError, PyValueError};

use bos_internals::{
    ChapterVerse, CVIndexEntry, InternalBibleBookCVIndex,
    InternalBibleEntry, InternalBibleEntryList, LookupError,
};

/// Convert a LookupError to a PyErr.
fn lookup_error_to_pyerr(e: LookupError) -> PyErr {
    match e {
        LookupError::NotIndexed => PyRuntimeError::new_err("Index has not been built"),
        LookupError::CVNotFound(cv) => PyKeyError::new_err(format!("CV {} not found", cv)),
        LookupError::ChapterNotFound(ch) => PyKeyError::new_err(format!("Chapter {} not found", ch)),
        LookupError::SectionNotFound(cv) => PyKeyError::new_err(format!("Section at {} not found", cv)),
        LookupError::InvalidReference(msg) => PyValueError::new_err(format!("Invalid reference: {}", msg)),
    }
}

// ============================================================================
// PyChapterVerse
// ============================================================================

/// A chapter:verse reference in a Bible book.
///
/// Both chapter and verse are stored as strings to handle special cases:
/// - Chapter `-1` for introductions
/// - Verse suffixes like `17a`
/// - Verse ranges like `17-25`
/// - Verse lists like `5,6,7`
#[pyclass(name = "ChapterVerse")]
#[derive(Clone)]
pub struct PyChapterVerse {
    inner: ChapterVerse,
}

#[pymethods]
impl PyChapterVerse {
    /// Create a new ChapterVerse reference.
    ///
    /// Args:
    ///     chapter: The chapter string (e.g., "3", "-1" for intro)
    ///     verse: The verse string (e.g., "16", "17a", "17-25")
    #[new]
    fn new(chapter: &str, verse: &str) -> Self {
        Self {
            inner: ChapterVerse::new(chapter, verse),
        }
    }

    /// Create an introduction reference (chapter -1).
    #[staticmethod]
    fn intro(verse_line: u32) -> Self {
        Self {
            inner: ChapterVerse::intro(verse_line),
        }
    }

    /// Create a chapter introduction reference (verse 0).
    #[staticmethod]
    fn chapter_intro(chapter: &str) -> Self {
        Self {
            inner: ChapterVerse::chapter_intro(chapter),
        }
    }

    /// Get the chapter string.
    #[getter]
    fn chapter(&self) -> &str {
        self.inner.chapter()
    }

    /// Get the verse string.
    #[getter]
    fn verse(&self) -> &str {
        self.inner.verse()
    }

    /// Get the leading integer from the chapter.
    fn chapter_int(&self) -> PyResult<i32> {
        self.inner
            .chapter_int()
            .map_err(|e| PyValueError::new_err(e.to_string()))
    }

    /// Get the leading integer from the verse.
    fn verse_int(&self) -> PyResult<i32> {
        self.inner
            .verse_int()
            .map_err(|e| PyValueError::new_err(e.to_string()))
    }

    /// Check if this is an introduction reference (chapter -1).
    fn is_intro(&self) -> bool {
        self.inner.is_intro()
    }

    /// Check if this is a chapter introduction (verse 0).
    fn is_chapter_intro(&self) -> bool {
        self.inner.is_chapter_intro()
    }

    /// Check if the verse contains a range (e.g., "17-25").
    fn is_verse_range(&self) -> bool {
        self.inner.is_verse_range()
    }

    /// Check if the verse contains a list (e.g., "5,6,7").
    fn is_verse_list(&self) -> bool {
        self.inner.is_verse_list()
    }

    /// Check if the verse has a suffix (e.g., "17a").
    fn has_verse_suffix(&self) -> bool {
        self.inner.has_verse_suffix()
    }

    /// Parse a verse range into (start, end) integers.
    fn parse_verse_range(&self) -> Option<(i32, i32)> {
        self.inner.parse_verse_range()
    }

    /// Check if this reference contains the given verse number.
    fn contains_verse(&self, verse_num: i32) -> bool {
        self.inner.contains_verse(verse_num)
    }

    fn __repr__(&self) -> String {
        format!("ChapterVerse('{}', '{}')", self.inner.chapter(), self.inner.verse())
    }

    fn __str__(&self) -> String {
        format!("{}:{}", self.inner.chapter(), self.inner.verse())
    }

    fn __eq__(&self, other: &PyChapterVerse) -> bool {
        self.inner == other.inner
    }

    fn __hash__(&self) -> u64 {
        use std::hash::{Hash, Hasher};
        let mut hasher = std::collections::hash_map::DefaultHasher::new();
        self.inner.hash(&mut hasher);
        hasher.finish()
    }
}

impl From<ChapterVerse> for PyChapterVerse {
    fn from(cv: ChapterVerse) -> Self {
        Self { inner: cv }
    }
}

impl From<&PyChapterVerse> for ChapterVerse {
    fn from(py_cv: &PyChapterVerse) -> Self {
        py_cv.inner.clone()
    }
}

// ============================================================================
// PyInternalBibleEntry
// ============================================================================

/// A single line/entry in the internal Bible format.
///
/// Each entry contains:
/// - marker: The USFM marker (e.g., "v", "p", "c")
/// - clean_text: Plain text without USFM markers
/// - original_marker: The original marker before adjustment
/// - adjusted_text: Notes removed but formatting retained
/// - original_text: Full USFM with all markup
#[pyclass(name = "InternalBibleEntry")]
#[derive(Clone)]
pub struct PyInternalBibleEntry {
    inner: InternalBibleEntry,
}

#[pymethods]
impl PyInternalBibleEntry {
    /// Create a simple entry with just marker and text.
    #[new]
    fn new(marker: &str, clean_text: &str) -> Self {
        Self {
            inner: InternalBibleEntry::simple(marker, clean_text),
        }
    }

    /// Get the (adjusted) marker.
    #[getter]
    fn marker(&self) -> &str {
        self.inner.marker()
    }

    /// Get the original marker before adjustment.
    #[getter]
    fn original_marker(&self) -> Option<&str> {
        self.inner.original_marker()
    }

    /// Get the adjusted text (notes removed, formatting retained).
    #[getter]
    fn adjusted_text(&self) -> Option<&str> {
        self.inner.adjusted_text()
    }

    /// Get the clean text (notes and formatting removed).
    #[getter]
    fn clean_text(&self) -> &str {
        self.inner.clean_text()
    }

    /// Get the original text (full USFM).
    #[getter]
    fn original_text(&self) -> Option<&str> {
        self.inner.original_text()
    }

    /// Check if this is an end marker.
    fn is_end_marker(&self) -> bool {
        self.inner.is_end_marker()
    }

    /// Check if this entry has extras (footnotes, cross-refs).
    fn has_extras(&self) -> bool {
        self.inner.has_extras()
    }

    fn __repr__(&self) -> String {
        let text = self.inner.clean_text();
        let abbrev = if text.len() > 40 {
            format!("{}...", &text[..40])
        } else {
            text.to_string()
        };
        format!("InternalBibleEntry('{}', {:?})", self.inner.marker(), abbrev)
    }

    fn __str__(&self) -> String {
        format!("{} = {}", self.inner.marker(), self.inner.clean_text())
    }
}

impl From<InternalBibleEntry> for PyInternalBibleEntry {
    fn from(entry: InternalBibleEntry) -> Self {
        Self { inner: entry }
    }
}

impl From<&InternalBibleEntry> for PyInternalBibleEntry {
    fn from(entry: &InternalBibleEntry) -> Self {
        Self { inner: entry.clone() }
    }
}

// ============================================================================
// PyInternalBibleEntryList
// ============================================================================

/// A list of Bible entries.
///
/// This represents the processed lines of a Bible book or a slice of entries.
#[pyclass(name = "InternalBibleEntryList")]
#[derive(Clone)]
pub struct PyInternalBibleEntryList {
    inner: InternalBibleEntryList,
}

#[pymethods]
impl PyInternalBibleEntryList {
    /// Create a new empty entry list.
    #[new]
    fn new() -> Self {
        Self {
            inner: InternalBibleEntryList::new(),
        }
    }

    /// Get the number of entries.
    fn __len__(&self) -> usize {
        self.inner.len()
    }

    /// Check if the list is empty.
    fn is_empty(&self) -> bool {
        self.inner.is_empty()
    }

    /// Get an entry by index.
    fn __getitem__(&self, index: isize) -> PyResult<PyInternalBibleEntry> {
        let len = self.inner.len() as isize;
        let idx = if index < 0 { len + index } else { index };

        if idx < 0 || idx >= len {
            return Err(PyKeyError::new_err(format!("Index {} out of range", index)));
        }

        Ok(PyInternalBibleEntry::from(&self.inner[idx as usize]))
    }

    /// Iterate over entries.
    fn __iter__(slf: PyRef<'_, Self>) -> PyInternalBibleEntryListIter {
        PyInternalBibleEntryListIter {
            entries: slf.inner.clone(),
            index: 0,
        }
    }

    /// Add an entry to the list.
    fn append(&mut self, entry: &PyInternalBibleEntry) {
        self.inner.push(entry.inner.clone());
    }

    /// Get a slice of entries.
    fn slice(&self, start: usize, end: usize) -> Self {
        Self {
            inner: self.inner.slice(start, end),
        }
    }

    /// Find the first entry with the given marker.
    fn find_marker(&self, marker: &str, max_lines: Option<usize>) -> Option<usize> {
        self.inner.contains_marker(marker, max_lines)
    }

    /// Get all entries as a list of tuples (marker, clean_text).
    fn to_list(&self) -> Vec<(String, String)> {
        self.inner
            .iter()
            .map(|e| (e.marker().to_string(), e.clean_text().to_string()))
            .collect()
    }

    fn __repr__(&self) -> String {
        format!("InternalBibleEntryList({} entries)", self.inner.len())
    }
}

impl From<InternalBibleEntryList> for PyInternalBibleEntryList {
    fn from(entries: InternalBibleEntryList) -> Self {
        Self { inner: entries }
    }
}

/// Iterator for PyInternalBibleEntryList.
#[pyclass]
pub struct PyInternalBibleEntryListIter {
    entries: InternalBibleEntryList,
    index: usize,
}

#[pymethods]
impl PyInternalBibleEntryListIter {
    fn __iter__(slf: PyRef<'_, Self>) -> PyRef<'_, Self> {
        slf
    }

    fn __next__(&mut self) -> Option<PyInternalBibleEntry> {
        if self.index < self.entries.len() {
            let entry = PyInternalBibleEntry::from(&self.entries[self.index]);
            self.index += 1;
            Some(entry)
        } else {
            None
        }
    }
}

// ============================================================================
// PyCVIndexEntry
// ============================================================================

/// An entry in the CV index, representing a single Chapter:Verse reference.
///
/// Each entry stores:
/// - entry_index: The index into the entry list where this CV starts
/// - entry_count: The count of entries for this CV
/// - context: The context markers that were open at this point
#[pyclass(name = "CVIndexEntry")]
#[derive(Clone)]
pub struct PyCVIndexEntry {
    inner: CVIndexEntry,
}

#[pymethods]
impl PyCVIndexEntry {
    /// Get the starting entry index.
    #[getter]
    fn entry_index(&self) -> usize {
        self.inner.entry_index()
    }

    /// Get the entry count for this C:V.
    #[getter]
    fn entry_count(&self) -> u16 {
        self.inner.entry_count()
    }

    /// Get the index one past the last entry for this C:V.
    fn next_entry_index(&self) -> usize {
        self.inner.next_entry_index()
    }

    /// Get the context markers.
    #[getter]
    fn context(&self) -> Vec<String> {
        self.inner.context().iter().map(|s| s.to_string()).collect()
    }

    fn __repr__(&self) -> String {
        format!(
            "CVIndexEntry(idx={}, count={}, ctx={:?})",
            self.inner.entry_index(),
            self.inner.entry_count(),
            self.context()
        )
    }
}

impl From<CVIndexEntry> for PyCVIndexEntry {
    fn from(entry: CVIndexEntry) -> Self {
        Self { inner: entry }
    }
}

impl From<&CVIndexEntry> for PyCVIndexEntry {
    fn from(entry: &CVIndexEntry) -> Self {
        Self { inner: entry.clone() }
    }
}

// ============================================================================
// PyInternalBibleBookCVIndex
// ============================================================================

/// Index for fast Chapter:Verse lookup in a Bible book.
///
/// The index maps (Chapter, Verse) references to entry ranges.
///
/// Special cases:
/// - Chapter `-1`: Book introduction
/// - Verse `0`: Chapter introduction / section headings before first verse
/// - Verse ranges: e.g., `17-25` for bridged verses
/// - Verse lists: e.g., `5,6,7` for multiple verses in one entry
/// - Verse suffixes: e.g., `17a`, `17b`
///
/// Example:
///     index = InternalBibleBookCVIndex("ESV", "GEN")
///     # After building...
///     entries = index.get_verse_entries(ChapterVerse("1", "1"))
#[pyclass(name = "InternalBibleBookCVIndex")]
pub struct PyInternalBibleBookCVIndex {
    inner: InternalBibleBookCVIndex,
}

#[pymethods]
impl PyInternalBibleBookCVIndex {
    /// Create a new empty CV index.
    ///
    /// Args:
    ///     work_name: Name of the work/Bible (e.g., "ESV", "KJV")
    ///     book_code: Three-letter book code (e.g., "GEN", "MAT")
    #[new]
    fn new(work_name: &str, book_code: &str) -> Self {
        Self {
            inner: InternalBibleBookCVIndex::new(work_name, book_code),
        }
    }

    /// Get the work name.
    #[getter]
    fn work_name(&self) -> &str {
        self.inner.work_name()
    }

    /// Get the book code.
    #[getter]
    fn book_code(&self) -> &str {
        self.inner.book_code()
    }

    /// Check if the index has been built.
    #[getter]
    fn is_indexed(&self) -> bool {
        self.inner.is_indexed()
    }

    /// Get the number of CV entries in the index.
    fn __len__(&self) -> usize {
        self.inner.len()
    }

    /// Check if the index is empty.
    fn is_empty(&self) -> bool {
        self.inner.is_empty()
    }

    /// Check if a specific CV exists in the index.
    fn contains(&self, cv: &PyChapterVerse) -> bool {
        self.inner.contains(&cv.inner)
    }

    /// Check if a CV exists using __contains__ protocol.
    fn __contains__(&self, cv: &PyChapterVerse) -> bool {
        self.inner.contains(&cv.inner)
    }

    /// Get all chapters in the index.
    fn chapters(&self) -> Vec<String> {
        self.inner.chapters().into_iter().map(|s| s.to_string()).collect()
    }

    /// Get verse entries for a specific C:V.
    ///
    /// Args:
    ///     cv: The ChapterVerse to look up
    ///     strict: If False, also search for verse ranges containing this verse
    ///
    /// Returns:
    ///     InternalBibleEntryList containing the entries for this verse
    ///
    /// Raises:
    ///     RuntimeError: If the index hasn't been built
    ///     KeyError: If the CV is not found in the index
    #[pyo3(signature = (cv, strict=true))]
    fn get_verse_entries(&self, cv: &PyChapterVerse, strict: bool) -> PyResult<PyInternalBibleEntryList> {
        self.inner
            .get_verse_entries(&cv.inner, strict)
            .map(PyInternalBibleEntryList::from)
            .map_err(lookup_error_to_pyerr)
    }

    /// Get verse entries with context markers.
    ///
    /// Args:
    ///     cv: The ChapterVerse to look up
    ///     strict: If False, also search for verse ranges
    ///     complete: If True, include entries from verse 0 if getting verse 1
    ///
    /// Returns:
    ///     Tuple of (entries, context_markers)
    #[pyo3(signature = (cv, strict=true, complete=false))]
    fn get_verse_entries_with_context(
        &self,
        cv: &PyChapterVerse,
        strict: bool,
        complete: bool,
    ) -> PyResult<(PyInternalBibleEntryList, Vec<String>)> {
        self.inner
            .get_verse_entries_with_context(&cv.inner, strict, complete)
            .map(|(entries, context)| {
                (
                    PyInternalBibleEntryList::from(entries),
                    context.into_iter().map(|s| s.to_string()).collect(),
                )
            })
            .map_err(lookup_error_to_pyerr)
    }

    /// Get all entries for a chapter.
    ///
    /// Args:
    ///     chapter: The chapter number as a string
    ///
    /// Returns:
    ///     InternalBibleEntryList containing all entries in the chapter
    fn get_chapter_entries(&self, chapter: &str) -> PyResult<PyInternalBibleEntryList> {
        self.inner
            .get_chapter_entries(chapter)
            .map(PyInternalBibleEntryList::from)
            .map_err(lookup_error_to_pyerr)
    }

    /// Get the CV index entry for a specific reference.
    fn get_index_entry(&self, cv: &PyChapterVerse) -> Option<PyCVIndexEntry> {
        self.inner.get_index_entry(&cv.inner).map(PyCVIndexEntry::from)
    }

    /// Get direct access to the underlying entries.
    #[getter]
    fn entries(&self) -> PyInternalBibleEntryList {
        PyInternalBibleEntryList::from(self.inner.entries().clone())
    }

    /// Build the CV index from processed entries.
    ///
    /// This analyzes the entry list and creates the CV -> entry mapping.
    ///
    /// Args:
    ///     entries: The InternalBibleEntryList to index
    ///
    /// Raises:
    ///     ValueError: If the entry structure is invalid
    fn build(&mut self, entries: &PyInternalBibleEntryList) -> PyResult<()> {
        self.inner
            .build(entries.inner.clone())
            .map_err(|e| PyValueError::new_err(e.to_string()))
    }

    /// Validate the index structure.
    ///
    /// Returns:
    ///     List of any issues found (empty if valid)
    fn validate(&self) -> Vec<String> {
        self.inner.validate()
    }

    /// Iterate over (ChapterVerse, CVIndexEntry) pairs.
    fn items(&self) -> Vec<(PyChapterVerse, PyCVIndexEntry)> {
        self.inner
            .iter()
            .map(|(cv, entry)| (PyChapterVerse::from(cv.clone()), PyCVIndexEntry::from(entry)))
            .collect()
    }

    fn __repr__(&self) -> String {
        format!(
            "InternalBibleBookCVIndex('{}', '{}', {} entries, indexed={})",
            self.inner.work_name(),
            self.inner.book_code(),
            self.inner.len(),
            self.inner.is_indexed()
        )
    }

    fn __str__(&self) -> String {
        format!("{}", self.inner)
    }
}

/// Register the CV index types with the Python module.
pub fn register_cv_index_types(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyChapterVerse>()?;
    m.add_class::<PyInternalBibleEntry>()?;
    m.add_class::<PyInternalBibleEntryList>()?;
    m.add_class::<PyInternalBibleEntryListIter>()?;
    m.add_class::<PyCVIndexEntry>()?;
    m.add_class::<PyInternalBibleBookCVIndex>()?;
    Ok(())
}
