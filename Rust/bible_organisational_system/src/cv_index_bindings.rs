//! Python bindings for the CV Index types.
//!
//! This module provides PyO3 bindings for:
//! - `PyChapterVerse` - Chapter:Verse reference
//! - `PyCVIndexEntry` - Index entry for a single C:V reference
//! - `PyInternalBibleEntry` - A single Bible text entry (backward-compatible with Python API)
//! - `PyInternalBibleEntryList` - Collection of Bible entries
//! - `PyInternalBibleBookCVIndex` - CV index for fast verse lookup

use pyo3::exceptions::{PyIndexError, PyKeyError, PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::PyBytes;

use bos_internals::{
    CVIndexEntry, ChapterVerse, InternalBibleBookCVIndex, InternalBibleEntry,
    InternalBibleEntryList, markers::is_end_marker,
};

use crate::extra_bindings::PyInternalBibleExtraList;

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
#[pyclass(
    name = "ChapterVerse",
    module = "bible_organisational_system",
    from_py_object
)]
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
    fn intro(verse_line: usize) -> Self {
        Self {
            inner: ChapterVerse::intro(verse_line.try_into().unwrap()),
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
    fn chapter_int(&self) -> PyResult<i16> {
        self.inner
            .chapter_int()
            .map_err(|e| PyValueError::new_err(e.to_string()))
    }

    /// Get the leading integer from the verse.
    fn verse_int(&self) -> PyResult<i16> {
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
    fn parse_verse_range(&self) -> Option<(i16, i16)> {
        self.inner.parse_verse_range()
    }

    /// Check if this reference contains the given verse number.
    fn contains_verse(&self, verse_num: i16) -> bool {
        self.inner.contains_verse(verse_num)
    }

    fn __repr__(&self) -> String {
        format!(
            "ChapterVerse('{}', '{}')",
            self.inner.chapter(),
            self.inner.verse()
        )
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
/// Backward-compatible with the Python InternalBibleEntry class.
///
/// Constructor accepts either:
/// - Full 6-arg form: (marker, originalMarker, adjustedText, cleanText, extras, originalText)
/// - Simple 2-arg form: (marker, cleanText) — creates entry with all text fields set to cleanText
///
/// Supports both snake_case properties and camelCase getter methods.
#[pyclass(
    name = "InternalBibleEntry",
    module = "bible_organisational_system",
    from_py_object
)]
#[derive(Debug, Clone)]
pub struct PyInternalBibleEntry {
    pub(crate) inner: InternalBibleEntry,
}

#[pymethods]
#[allow(non_snake_case)]
impl PyInternalBibleEntry {
    /// Create a new InternalBibleEntry.
    ///
    /// Matches the Python constructor signature:
    ///     InternalBibleEntry(marker, originalMarker, adjustedText, cleanText, extras, originalText)
    ///
    /// For end markers / added nesting markers, originalMarker through originalText should be None.
    #[new]
    #[pyo3(signature = (marker, original_marker, adjusted_text=None, clean_text=None, extras=None, original_text=None))]
    fn new(
        marker: &str,
        original_marker: Option<&str>,
        adjusted_text: Option<&str>,
        clean_text: Option<&str>,
        extras: Option<&PyInternalBibleExtraList>,
        original_text: Option<&str>,
    ) -> PyResult<Self> {
        // If only marker and one other arg given (2-arg form: marker + clean_text)
        // The second arg is original_marker in the signature but acts as clean_text
        if adjusted_text.is_none() && extras.is_none() && original_text.is_none() {
            if let Some(text) = original_marker
                && (clean_text.is_none() || clean_text.unwrap().is_empty())
            {
                // 2-arg simple form: (marker, clean_text)
                return Ok(Self {
                    inner: InternalBibleEntry::simple(marker, text),
                });
            } else {
                // End marker or nesting marker (marker only)
                if is_end_marker(marker) {
                    return InternalBibleEntry::end_marker(marker)
                        .map(|inner| Self { inner })
                        .map_err(|e| PyValueError::new_err(e.to_string()));
                } else {
                    return Ok(Self {
                        inner: InternalBibleEntry::nesting_marker(marker),
                    });
                }
            }
        }

        // Full 6-arg form
        let orig_marker = original_marker.ok_or_else(|| {
            PyValueError::new_err(format!("originalMarker is required for regular entries (marker={} original_marker={:?} adjusted_text={:?} clean_text={:?} extras={:?} original_text={:?})", marker, original_marker, adjusted_text, clean_text, extras, original_text))
        })?;
        let adj_text = adjusted_text
            .ok_or_else(|| PyValueError::new_err(format!("adjustedText is required for regular entries (marker={} original_marker={:?} adjusted_text={:?} clean_text={:?} extras={:?} original_text={:?})", marker, original_marker, adjusted_text, clean_text, extras, original_text)))?;
        let cln_text = clean_text
            .ok_or_else(|| PyValueError::new_err(format!("cleanText is required for regular entries (marker={} original_marker={:?} adjusted_text={:?} clean_text={:?} extras={:?} original_text={:?})", marker, original_marker, adjusted_text, clean_text, extras, original_text)))?;
        let orig_text = original_text
            .ok_or_else(|| PyValueError::new_err(format!("originalText is required for regular entries (marker={} original_marker={:?} adjusted_text={:?} clean_text={:?} extras={:?} original_text={:?})", marker, original_marker, adjusted_text, clean_text, extras, original_text)))?;

        let rust_extras = extras.map(|e| e.inner.clone());

        InternalBibleEntry::new(
            marker,
            orig_marker,
            adj_text,
            cln_text,
            rust_extras,
            orig_text,
        )
        .map(|inner| Self { inner })
        .map_err(|e| PyValueError::new_err(e.to_string()))
    }

    // --- snake_case properties (Rust-style) ---

    /// Get the (adjusted) marker.
    #[getter]
    fn marker(&self) -> &str {
        self.inner.marker()
    }

    /// Get the original marker before adjustment.
    #[getter(originalMarker)]
    fn original_marker(&self) -> Option<&str> {
        self.inner.original_marker()
    }

    /// Get the adjusted text (notes removed, formatting retained).
    #[getter(adjustedText)]
    fn adjusted_text(&self) -> Option<&str> {
        self.inner.adjusted_text()
    }

    /// Get the clean text (notes and formatting removed).
    #[getter(cleanText)]
    fn clean_text(&self) -> &str {
        self.inner.clean_text()
    }

    /// Get the extras (footnotes, cross-refs, etc.).
    #[getter]
    fn extras(&self) -> Option<PyInternalBibleExtraList> {
        self.inner
            .extras()
            .map(|e| PyInternalBibleExtraList::from(e.clone()))
    }

    /// Get the original text (full USFM).
    #[getter(originalText)]
    fn original_text(&self) -> Option<&str> {
        self.inner.original_text()
    }

    // --- camelCase getter methods (Python backward compat) ---

    /// Get the marker (Python compat).
    fn getMarker(&self) -> &str {
        self.inner.marker()
    }

    /// Get the original marker (Python compat).
    fn getOriginalMarker(&self) -> Option<&str> {
        self.inner.original_marker()
    }

    /// Get the adjusted text (Python compat).
    fn getAdjustedText(&self) -> Option<&str> {
        self.inner.adjusted_text()
    }

    /// Get the adjusted text — alias (Python compat).
    fn getText(&self) -> Option<&str> {
        self.inner.adjusted_text()
    }

    /// Get the clean text, optionally removing ESFM underlines (Python compat).
    #[pyo3(signature = (remove_esfm_underlines=false))]
    fn getCleanText(&self, remove_esfm_underlines: bool) -> String {
        if remove_esfm_underlines {
            self.inner.clean_text_no_underlines()
        } else {
            self.inner.clean_text().to_string()
        }
    }

    /// Get the extras (Python compat).
    fn getExtras(&self) -> Option<PyInternalBibleExtraList> {
        self.inner
            .extras()
            .map(|e| PyInternalBibleExtraList::from(e.clone()))
    }

    /// Get the original text (Python compat).
    fn getOriginalText(&self) -> Option<&str> {
        self.inner.original_text()
    }

    /// Get the full text — returns originalText (Python compat).
    fn getFullText(&self) -> Option<&str> {
        self.inner.original_text()
    }

    // --- Mutators ---

    /// Set the clean text (also sets adjusted and original text).
    /// Only works when extras is None.
    fn setCleanText(&mut self, new_value: &str) -> PyResult<()> {
        if self.inner.has_extras() {
            return Err(PyValueError::new_err(
                "Cannot set cleanText when extras exist",
            ));
        }
        self.inner.set_clean_text(new_value);
        Ok(())
    }

    // --- Predicates ---

    /// Check if this is an end marker.
    fn is_end_marker(&self) -> bool {
        self.inner.is_end_marker()
    }

    /// Check if this entry has extras (footnotes, cross-refs).
    fn has_extras(&self) -> bool {
        self.inner.has_extras()
    }

    // --- Standard Python methods ---

    fn __len__(&self) -> usize {
        6
    }

    fn __getitem__(&self, key_index: isize) -> PyResult<Py<PyAny>> {
        Python::attach(|py| match key_index {
            0 => Ok(self.inner.marker().into_pyobject(py)?.into_any().unbind()),
            1 => Ok(self
                .inner
                .original_marker()
                .into_pyobject(py)?
                .into_any()
                .unbind()),
            2 => Ok(self
                .inner
                .adjusted_text()
                .into_pyobject(py)?
                .into_any()
                .unbind()),
            3 => Ok(self
                .inner
                .clean_text()
                .into_pyobject(py)?
                .into_any()
                .unbind()),
            4 => match self.inner.extras() {
                Some(e) => {
                    let py_extras = PyInternalBibleExtraList::from(e.clone());
                    Ok(py_extras.into_pyobject(py)?.into_any().unbind())
                }
                None => Ok(py.None()),
            },
            5 => Ok(self
                .inner
                .original_text()
                .into_pyobject(py)?
                .into_any()
                .unbind()),
            _ => Err(PyIndexError::new_err(format!(
                "Invalid {} index number",
                key_index
            ))),
        })
    }

    fn __eq__(&self, other: &PyInternalBibleEntry) -> bool {
        self.inner == other.inner
    }

    fn __ne__(&self, other: &PyInternalBibleEntry) -> bool {
        self.inner != other.inner
    }

    fn __repr__(&self) -> String {
        let abbrev_adj = match self.inner.adjusted_text() {
            Some(t) if t.len() > 100 => format!("{}…{}", &t[..50], &t[t.len() - 50..]),
            Some(t) => t.to_string(),
            None => String::new(),
        };
        let abbrev_clean = if self.inner.clean_text().len() > 100 {
            format!(
                "{}…{}",
                &self.inner.clean_text()[..50],
                &self.inner.clean_text()[self.inner.clean_text().len() - 50..]
            )
        } else {
            self.inner.clean_text().to_string()
        };
        let abbrev_orig = match self.inner.original_text() {
            Some(t) if t.len() > 100 => format!("{}…{}", &t[..50], &t[t.len() - 50..]),
            Some(t) => t.to_string(),
            None => String::new(),
        };

        let mut result = format!(
            "InternalBibleEntry object:\n    {} = {:?}",
            self.inner.marker(),
            abbrev_clean
        );
        if self.inner.original_marker() != Some(self.inner.marker())
            || self
                .inner
                .original_text()
                .map(|t| t != self.inner.clean_text())
                .unwrap_or(false)
        {
            result += &format!(
                "\n  from Original {} = {:?}",
                self.inner.original_marker().unwrap_or(""),
                abbrev_orig
            );
        }
        if self.inner.adjusted_text() != self.inner.original_text() {
            result += &format!("\n          adjusted to {:?}", abbrev_adj);
        }
        if self.inner.has_extras()
            && let Some(extras) = self.inner.extras()
        {
            result += &format!("\n         with {}", extras);
        }
        result
    }

    fn __str__(&self) -> String {
        let abbrev = if self.inner.clean_text().len() > 100 {
            format!(
                "{}…{}",
                &self.inner.clean_text()[..50],
                &self.inner.clean_text()[self.inner.clean_text().len() - 50..]
            )
        } else {
            self.inner.clean_text().to_string()
        };
        format!(
            "InternalBibleEntry object: {} = {:?}{}",
            self.inner.marker(),
            abbrev,
            if self.inner.has_extras() {
                "+extras"
            } else {
                ""
            }
        )
    }
}

impl From<InternalBibleEntry> for PyInternalBibleEntry {
    fn from(entry: InternalBibleEntry) -> Self {
        Self { inner: entry }
    }
}

impl From<&InternalBibleEntry> for PyInternalBibleEntry {
    fn from(entry: &InternalBibleEntry) -> Self {
        Self {
            inner: entry.clone(),
        }
    }
}

// ============================================================================
// PyInternalBibleEntryList
// ============================================================================

/// A list of Bible entries.
///
/// This represents the processed lines of a Bible book or a slice of entries.
/// Backward-compatible with the Python InternalBibleEntryList class.
#[pyclass(
    name = "InternalBibleEntryList",
    module = "bible_organisational_system",
    from_py_object
)]
#[derive(Clone, Debug, rkyv::Archive, rkyv::Serialize, rkyv::Deserialize)]
pub struct PyInternalBibleEntryList {
    pub(crate) inner: InternalBibleEntryList,
}

#[pymethods]
impl PyInternalBibleEntryList {
    /// Create a new entry list, optionally from existing data.
    #[new]
    #[pyo3(signature = (initial_data=None))]
    fn new(initial_data: Option<&Bound<'_, PyAny>>) -> PyResult<Self> {
        let mut inner = InternalBibleEntryList::new();
        if let Some(data) = initial_data {
            let iter = data.try_iter()?;
            for item in iter {
                let item = item?;
                let entry: PyRef<PyInternalBibleEntry> = item.extract()?;
                inner.push(entry.inner.clone());
            }
        }
        Ok(Self { inner })
    }

    /// Get the number of entries.
    fn __len__(&self) -> usize {
        self.inner.len()
    }

    /// Check if the list is empty.
    fn is_empty(&self) -> bool {
        self.inner.is_empty()
    }

    /// Get an entry by index. Supports negative indexing and slicing.
    fn __getitem__(&self, index: &Bound<'_, PyAny>) -> PyResult<Py<PyAny>> {
        Python::attach(|py| {
            // Try slice first
            if let Ok(slice) = index.cast::<pyo3::types::PySlice>() {
                let len = self.inner.len();
                let indices = slice.indices(len as isize)?;
                let mut result = InternalBibleEntryList::new();
                let mut i = indices.start;
                while (indices.step > 0 && i < indices.stop)
                    || (indices.step < 0 && i > indices.stop)
                {
                    if i >= 0 && (i as usize) < len {
                        result.push(self.inner[i as usize].clone());
                    }
                    i += indices.step;
                }
                let py_list = PyInternalBibleEntryList { inner: result };
                return Ok(py_list.into_pyobject(py)?.into_any().unbind());
            }
            // Otherwise integer index
            let idx: isize = index.extract()?;
            let len = self.inner.len() as isize;
            let resolved = if idx < 0 { len + idx } else { idx };
            if resolved < 0 || resolved >= len {
                return Err(PyIndexError::new_err(format!("Index {} out of range", idx)));
            }
            let entry = PyInternalBibleEntry::from(&self.inner[resolved as usize]);
            Ok(entry.into_pyobject(py)?.into_any().unbind())
        })
    }

    /// Iterate over entries.
    fn __iter__(slf: PyRef<'_, Self>) -> PyInternalBibleEntryListIter {
        PyInternalBibleEntryListIter {
            entries: slf.inner.clone(),
            index: 0,
        }
    }

    fn __bool__(&self) -> bool {
        !self.inner.is_empty()
    }

    /// Add an entry to the list.
    fn append(&mut self, entry: &PyInternalBibleEntry) {
        self.inner.push(entry.inner.clone());
    }

    /// Remove and return the last entry.
    fn pop(&mut self) -> Option<PyInternalBibleEntry> {
        self.inner.pop().map(PyInternalBibleEntry::from)
    }

    /// Extend with another entry list.
    fn extend(&mut self, other: &PyInternalBibleEntryList) {
        self.inner.extend(&other.inner);
    }

    /// Support the + operator to combine lists (Python compat).
    fn __add__(&self, other: &PyInternalBibleEntryList) -> Self {
        let mut combined = self.inner.clone();
        combined.extend(&other.inner);
        Self { inner: combined }
    }

    /// Search for the first entry with the given marker (Python compat: `contains`).
    #[pyo3(signature = (search_marker, max_lines=None))]
    fn contains(&self, search_marker: &str, max_lines: Option<usize>) -> Option<usize> {
        self.inner.contains_marker(search_marker, max_lines)
    }

    /// Find the first entry with the given marker (alias).
    #[pyo3(signature = (marker, max_lines=None))]
    fn find_marker(&self, marker: &str, max_lines: Option<usize>) -> Option<usize> {
        self.inner.contains_marker(marker, max_lines)
    }

    /// Get a slice of entries.
    fn slice(&self, start: usize, end: usize) -> Self {
        Self {
            inner: self.inner.slice(start, end),
        }
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

    fn __str__(&self) -> String {
        format!("{}", self.inner)
    }

    // Pickling support using rkyv zero-copy serialization.
    fn __getstate__(&self, py: Python) -> PyResult<Py<PyAny>> {
        let bytes = rkyv::to_bytes::<rkyv::rancor::Error>(self)
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
        Ok(PyBytes::new(py, &bytes).into())
    }

    fn __setstate__(&mut self, state: &Bound<'_, PyAny>) -> PyResult<()> {
        let bytes = state.extract::<&[u8]>()?;
        *self = rkyv::from_bytes::<Self, rkyv::rancor::Error>(bytes)
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
        Ok(())
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
/// - entryIndex: The index into the entry list where this CV starts
/// - entryCount: The count of entries for this CV
/// - context: The context markers that were open at this point
///
/// Supports both snake_case properties and camelCase getter methods.
#[pyclass(
    name = "CVIndexEntry",
    module = "bible_organisational_system",
    from_py_object
)]
#[derive(Clone)]
pub struct PyCVIndexEntry {
    inner: CVIndexEntry,
}

#[pymethods]
#[allow(non_snake_case)]
impl PyCVIndexEntry {
    /// Create a new CV index entry.
    ///
    /// Args:
    ///     entry_index: The starting index into the entry list
    ///     entry_count: Number of entries for this C:V
    ///     context: Optional list of context markers
    #[new]
    #[pyo3(signature = (entry_index, entry_count, context=None))]
    fn new(entry_index: usize, entry_count: u16, context: Option<Vec<String>>) -> Self {
        let ctx = context
            .unwrap_or_default()
            .into_iter()
            .map(|s| s.into())
            .collect();
        Self {
            inner: CVIndexEntry::new(entry_index, entry_count, ctx),
        }
    }

    // --- snake_case properties ---

    /// Get the starting entry index.
    #[getter(entryIndex)]
    fn entry_index(&self) -> usize {
        self.inner.entry_index()
    }

    /// Get the entry count for this C:V.
    #[getter(entryCount)]
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

    // --- camelCase getter methods (Python backward compat) ---

    /// Get the entry index (Python compat).
    fn getEntryIndex(&self) -> usize {
        self.inner.entry_index()
    }

    /// Get the next entry index (Python compat).
    fn getNextEntryIndex(&self) -> usize {
        self.inner.next_entry_index()
    }

    /// Get the entry count (Python compat).
    fn getEntryCount(&self) -> u16 {
        self.inner.entry_count()
    }

    /// Get the context list (Python compat).
    fn getContextList(&self) -> Vec<String> {
        self.inner.context().iter().map(|s| s.to_string()).collect()
    }

    // --- Standard Python methods ---

    fn __len__(&self) -> usize {
        3
    }

    fn __getitem__(&self, key_index: isize) -> PyResult<Py<PyAny>> {
        Python::attach(|py| match key_index {
            0 => Ok(self
                .inner
                .entry_index()
                .into_pyobject(py)?
                .into_any()
                .unbind()),
            1 => Ok(self
                .inner
                .entry_count()
                .into_pyobject(py)?
                .into_any()
                .unbind()),
            2 => Ok(self.context().into_pyobject(py)?.into_any().unbind()),
            _ => Err(PyIndexError::new_err("Index out of range")),
        })
    }

    fn __repr__(&self) -> String {
        format!(
            "InternalBibleBookCVIndexEntry object: ix={} cnt={} ixE={}{}",
            self.inner.entry_index(),
            self.inner.entry_count(),
            self.inner.next_entry_index(),
            if self.inner.context().is_empty() {
                String::new()
            } else {
                format!(" ctxt={:?}", self.context())
            }
        )
    }

    fn __str__(&self) -> String {
        self.__repr__()
    }
}

impl From<CVIndexEntry> for PyCVIndexEntry {
    fn from(entry: CVIndexEntry) -> Self {
        Self { inner: entry }
    }
}

impl From<&CVIndexEntry> for PyCVIndexEntry {
    fn from(entry: &CVIndexEntry) -> Self {
        Self {
            inner: entry.clone(),
        }
    }
}

// ============================================================================
// Helper function
// ============================================================================

/// Extract a ChapterVerse from a Python object (tuple or ChapterVerse).
fn extract_chapter_verse(obj: &Bound<'_, PyAny>) -> PyResult<ChapterVerse> {
    if let Ok((c, v)) = obj.extract::<(String, String)>() {
        Ok(ChapterVerse::new(&c, &v))
    } else if let Ok(cv) = obj.extract::<PyRef<PyChapterVerse>>() {
        Ok(cv.inner.clone())
    } else {
        Err(PyValueError::new_err(
            "Expected (str, str) tuple or ChapterVerse",
        ))
    }
}

// ============================================================================
// PyInternalBibleBookCVIndex
// ============================================================================

/// Index for fast Chapter:Verse lookup in a Bible book.
///
/// The index maps (Chapter, Verse) references to entry ranges.
/// Accepts both (str, str) tuples and ChapterVerse objects for keys.
///
/// Special cases:
/// - Chapter `-1`: Book introduction
/// - Verse `0`: Chapter introduction / section headings before first verse
/// - Verse ranges: e.g., `17-25` for bridged verses
/// - Verse lists: e.g., `5,6,7` for multiple verses in one entry
/// - Verse suffixes: e.g., `17a`, `17b`
#[pyclass(
    name = "InternalBibleBookCVIndex",
    module = "bible_organisational_system"
)]
#[derive(rkyv::Archive, rkyv::Serialize, rkyv::Deserialize)]
pub struct PyInternalBibleBookCVIndex {
    inner: InternalBibleBookCVIndex,
}

#[pymethods]
#[allow(non_snake_case)]
impl PyInternalBibleBookCVIndex {
    /// Create a new empty CV index.
    ///
    /// Args:
    ///     work_name: Name of the work/Bible (e.g., "ESV", "KJV")
    ///     book_code: Three-letter book code (e.g., "GEN", "MAT")
    #[new]
    fn new(work_name: &str, book_code: &str) -> Self {
        print!("HERE IN new with work_name={} book_code={}", work_name, book_code);
        Self {
            inner: InternalBibleBookCVIndex::new(work_name, book_code),
        }
    }

    // Pickle needs args for _new_ before it can call _setstate_
    fn __getnewargs__(&self) -> (String, String) {
        print!("HERE IN _getnewargs_ with work_name={} book_code={}", self.inner.work_name(), self.inner.book_code());
        (
            self.inner.work_name().to_string(),
            self.inner.book_code().to_string(),
        )
    }
    
    // === Properties (snake_case) ===

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

    /// Get direct access to the underlying entries.
    #[getter]
    fn entries(&self) -> PyInternalBibleEntryList {
        PyInternalBibleEntryList::from(self.inner.entries().clone())
    }

    // === Properties (camelCase backward compat) ===

    /// Get the work name (Python compat).
    #[getter(workName)]
    fn work_name_compat(&self) -> &str {
        self.inner.work_name()
    }

    /// Get the book code (Python compat: BBB).
    #[getter(BBB)]
    fn bbb(&self) -> &str {
        self.inner.book_code()
    }

    /// Check if indexed (Python compat: _indexedFlag).
    #[getter(_indexedFlag)]
    fn indexed_flag(&self) -> bool {
        self.inner.is_indexed()
    }

    /// Get the entries list (Python compat: givenBibleEntries).
    #[getter(givenBibleEntries)]
    fn given_bible_entries(&self) -> PyInternalBibleEntryList {
        PyInternalBibleEntryList::from(self.inner.entries().clone())
    }

    // === Python protocol methods ===

    /// Get the number of CV entries in the index.
    fn __len__(&self) -> usize {
        self.inner.len()
    }

    /// Check if the index is empty.
    fn is_empty(&self) -> bool {
        self.inner.is_empty()
    }

    /// Check if a (C,V) tuple or ChapterVerse exists in the index.
    fn __contains__(&self, key: &Bound<'_, PyAny>) -> bool {
        if let Ok(cv) = extract_chapter_verse(key) {
            self.inner.contains(&cv)
        } else {
            false
        }
    }

    /// Get a CVIndexEntry for a (C,V) tuple key.
    fn __getitem__(&self, key: (String, String)) -> PyResult<PyCVIndexEntry> {
        let cv = ChapterVerse::new(&key.0, &key.1);
        self.inner
            .get_index_entry(&cv)
            .map(PyCVIndexEntry::from)
            .ok_or_else(|| PyKeyError::new_err(format!("({:?}, {:?})", key.0, key.1)))
    }

    /// Iterate over (C,V) tuples.
    fn __iter__(slf: PyRef<'_, Self>) -> PyCVIndexIter {
        let keys: Vec<(String, String)> = slf
            .inner
            .iter()
            .map(|(cv, _)| (cv.chapter().to_string(), cv.verse().to_string()))
            .collect();
        PyCVIndexIter { keys, index: 0 }
    }

    /// Iterate over ((C,V), CVIndexEntry) pairs.
    fn items(&self) -> Vec<((String, String), PyCVIndexEntry)> {
        self.inner
            .iter()
            .map(|(cv, entry)| {
                (
                    (cv.chapter().to_string(), cv.verse().to_string()),
                    PyCVIndexEntry::from(entry),
                )
            })
            .collect()
    }

    /// Get all chapters in the index.
    fn chapters(&self) -> Vec<String> {
        self.inner
            .chapters()
            .into_iter()
            .map(|s| s.to_string())
            .collect()
    }

    // === snake_case methods (Rust-style, take ChapterVerse objects) ===

    /// Check if a CV exists in the index (accepts tuple or ChapterVerse).
    fn contains(&self, key: &Bound<'_, PyAny>) -> PyResult<bool> {
        let cv = extract_chapter_verse(key)?;
        Ok(self.inner.contains(&cv))
    }

    /// Get verse entries using a ChapterVerse object.
    #[pyo3(signature = (cv, strict=true))]
    fn get_verse_entries(
        &self,
        cv: &PyChapterVerse,
        strict: bool,
    ) -> PyResult<PyInternalBibleEntryList> {
        self.inner
            .get_verse_entries(&cv.inner, strict)
            .map(PyInternalBibleEntryList::from)
            .map_err(|x| PyRuntimeError::new_err(x.to_string()))
    }

    /// Get verse entries with context using a ChapterVerse object.
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
            .map_err(|x| PyRuntimeError::new_err(x.to_string()))
    }

    /// Get all entries for a chapter (snake_case).
    fn get_chapter_entries(&self, chapter: &str) -> PyResult<PyInternalBibleEntryList> {
        self.inner
            .get_chapter_entries(chapter)
            .map(PyInternalBibleEntryList::from)
            .map_err(|x| PyRuntimeError::new_err(x.to_string()))
    }

    /// Get the CV index entry for a specific ChapterVerse reference.
    fn get_index_entry(&self, cv: &PyChapterVerse) -> Option<PyCVIndexEntry> {
        self.inner
            .get_index_entry(&cv.inner)
            .map(PyCVIndexEntry::from)
    }

    /// Build the CV index from processed entries (snake_case).
    fn build(&mut self, entries: &PyInternalBibleEntryList) -> PyResult<()> {
        self.inner
            .build(entries.inner.clone())
            .map_err(|e| PyValueError::new_err(e.to_string()))
    }

    /// Validate the index structure.
    fn validate(&self) -> Vec<String> {
        self.inner.validate()
    }

    // === camelCase methods (Python backward compat, accept tuples) ===

    /// Build the CV index from processed entries (Python compat).
    fn makeBookCVIndex(&mut self, entries: &PyInternalBibleEntryList) -> PyResult<()> {
        self.inner
            .build(entries.inner.clone())
            .map_err(|e| PyValueError::new_err(e.to_string()))
    }

    /// Get verse entries for a (C,V) tuple key.
    #[pyo3(signature = (cv_key, strict=true))]
    fn getVerseEntries(
        &self,
        cv_key: (String, String),
        strict: bool,
    ) -> PyResult<PyInternalBibleEntryList> {
        let cv = ChapterVerse::new(&cv_key.0, &cv_key.1);
        self.inner
            .get_verse_entries(&cv, strict)
            .map(PyInternalBibleEntryList::from)
            .map_err(|_| PyKeyError::new_err(format!("({:?}, {:?})", cv_key.0, cv_key.1)))
    }

    /// Get verse entries with context for a (C,V) tuple key.
    #[pyo3(signature = (cv_key, strict=false, complete=false))]
    fn getVerseEntriesWithContext(
        &self,
        cv_key: (String, String),
        strict: bool,
        complete: bool,
    ) -> PyResult<(PyInternalBibleEntryList, Vec<String>)> {
        let cv = ChapterVerse::new(&cv_key.0, &cv_key.1);
        self.inner
            .get_verse_entries_with_context(&cv, strict, complete)
            .map(|(entries, context)| {
                (
                    PyInternalBibleEntryList::from(entries),
                    context.into_iter().map(|s| s.to_string()).collect(),
                )
            })
            .map_err(|_| PyKeyError::new_err(format!("({:?}, {:?})", cv_key.0, cv_key.1)))
    }

    /// Get all entries for a chapter (Python compat).
    fn getChapterEntries(&self, chapter: &str) -> PyResult<PyInternalBibleEntryList> {
        self.inner
            .get_chapter_entries(chapter)
            .map(PyInternalBibleEntryList::from)
            .map_err(|_| PyKeyError::new_err(format!("Chapter {:?}", chapter)))
    }

    /// Get chapter entries with context markers (Python compat).
    fn getChapterEntriesWithContext(
        &self,
        chapter: &str,
    ) -> PyResult<(PyInternalBibleEntryList, Vec<String>)> {
        let start_cv = ChapterVerse::new(chapter, "0");
        let first_entry = self
            .inner
            .get_index_entry(&start_cv)
            .ok_or_else(|| PyKeyError::new_err(format!("({:?}, '0')", chapter)))?;

        let context: Vec<String> = first_entry
            .context()
            .iter()
            .map(|s| s.to_string())
            .collect();

        // Try to find the start of the next chapter
        let next_c = (chapter.parse::<i32>().unwrap_or(0) + 1).to_string();
        let next_cv = ChapterVerse::new(&next_c, "0");

        let end_index = if let Some(next_entry) = self.inner.get_index_entry(&next_cv) {
            next_entry.entry_index()
        } else if chapter == "-1" {
            // For intro, try chapter 1
            let cv1 = ChapterVerse::new("1", "0");
            self.inner
                .get_index_entry(&cv1)
                .map(|e| e.entry_index())
                .unwrap_or(self.inner.entries().len())
        } else {
            self.inner.entries().len()
        };

        let entries = self
            .inner
            .entries()
            .slice(first_entry.entry_index(), end_index);
        Ok((PyInternalBibleEntryList::from(entries), context))
    }

    /// Get all entries (Python compat alias for entries property).
    fn getEntries(&self) -> PyInternalBibleEntryList {
        PyInternalBibleEntryList::from(self.inner.entries().clone())
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

    // Pickling support using rkyv zero-copy serialization.
    fn __getstate__(&self, py: Python) -> PyResult<Py<PyAny>> {
        let bytes = rkyv::to_bytes::<rkyv::rancor::Error>(self)
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
        Ok(PyBytes::new(py, &bytes).into())
    }

    fn __setstate__(&mut self, state: &Bound<'_, PyAny>) -> PyResult<()> {
        let bytes = state.extract::<&[u8]>()?;
        *self = rkyv::from_bytes::<Self, rkyv::rancor::Error>(bytes)
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
        Ok(())
    }
}

// ============================================================================
// CV Index Iterator
// ============================================================================

/// Iterator for PyInternalBibleBookCVIndex, yields (C, V) string tuples.
#[pyclass]
pub struct PyCVIndexIter {
    keys: Vec<(String, String)>,
    index: usize,
}

#[pymethods]
impl PyCVIndexIter {
    fn __iter__(slf: PyRef<'_, Self>) -> PyRef<'_, Self> {
        slf
    }

    fn __next__(&mut self) -> Option<(String, String)> {
        if self.index < self.keys.len() {
            let key = self.keys[self.index].clone();
            self.index += 1;
            Some(key)
        } else {
            None
        }
    }
}
