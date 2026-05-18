//! Python bindings for Bible discovery logic.

use std::path::Path;
use pyo3::prelude::*;
use pyo3::types::PyDict;
use bos_internals::discovery::{BookDiscoveryResults, AggregateDiscoveryResults, BibleDiscoveryResults, discover_book, discover_bible};
use bos_internals::discovery_filenames::{self, DiscoveryOptions, DiscoveryResults};
use bos_internals::format_discovery::{self, BibleFormat, DetectedBible};
use crate::cv_index_bindings::PyInternalBibleEntryList;
use indexmap::IndexMap;

#[pyclass(name = "DiscoveryOptions", module = "bible_organisational_system", from_py_object)]
#[derive(Clone, Default)]
pub struct PyDiscoveryOptions {
    #[pyo3(get, set)]
    pub strict_check: bool,
}

#[pymethods]
impl PyDiscoveryOptions {
    #[new]
    fn new(strict_check: Option<bool>) -> Self {
        Self {
            strict_check: strict_check.unwrap_or(false),
        }
    }
}

#[pyclass(name = "DetectedBible", module = "bible_organisational_system")]
pub struct PyDetectedBible {
    pub inner: DetectedBible,
}

#[pymethods]
impl PyDetectedBible {
    #[getter]
    fn format(&self) -> String { self.inner.format.name().to_string() }
    #[getter]
    fn path(&self) -> String { self.inner.path.to_string_lossy().to_string() }
    #[getter]
    fn name(&self) -> String { self.inner.name.clone() }
    #[getter]
    fn confidence(&self) -> u8 { self.inner.confidence }

    fn __repr__(&self) -> String {
        format!("DetectedBible(format='{}', name='{}', path='{}')", self.inner.format.name(), self.inner.name, self.inner.path.display())
    }
}

#[pyfunction]
#[pyo3(name = "detectBibles")]
pub fn py_detect_bibles(py: Python, root: &str, strict: bool) -> PyResult<Vec<PyDetectedBible>> {
    let results = format_discovery::detect_bibles(Path::new(root), strict);
    Ok(results.into_iter().map(|b| PyDetectedBible { inner: b }).collect())
}

#[pyclass(name = "DiscoveryResults", module = "bible_organisational_system", from_py_object)]
#[derive(Clone)]
pub struct PyDiscoveryResults {
    pub(crate) inner: DiscoveryResults,
}

#[pymethods]
impl PyDiscoveryResults {
    #[getter]
    fn folder(&self) -> String { self.inner.folder.to_string_lossy().to_string() }
    #[getter]
    fn pattern(&self) -> String { self.inner.pattern.to_string() }
    #[getter]
    #[pyo3(name = "fileExtension")]
    fn file_extension(&self) -> String { self.inner.file_extension.to_string() }
    #[getter]
    #[pyo3(name = "matchedFiles")]
    fn matched_files(&self) -> Vec<(String, String)> { self.inner.matched_files.clone() }
    #[getter]
    #[pyo3(name = "unusedFilenames")]
    fn unused_filenames(&self) -> Vec<String> { self.inner.unused_filenames.clone() }

    fn to_dict(&self, py: Python) -> PyResult<Py<PyDict>> {
        let dict = PyDict::new(py);
        dict.set_item("folder", self.folder())?;
        dict.set_item("pattern", self.pattern())?;
        dict.set_item("fileExtension", self.file_extension())?;
        dict.set_item("matchedFiles", self.matched_files())?;
        dict.set_item("unusedFilenames", self.unused_filenames())?;
        Ok(dict.into())
    }
}

#[pyfunction]
#[pyo3(name = "discoverFilenames")]
pub fn py_discover_filenames<'py>(
    py: Python<'py>,
    folder: &str,
    is_usx: bool,
    options: Option<PyDiscoveryOptions>,
) -> PyResult<Bound<'py, PyDiscoveryResults>> {
    let options = options.unwrap_or_default().inner_options();
    let results = discovery_filenames::discover_filenames(folder, is_usx, &options)
        .map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
    Bound::new(py, PyDiscoveryResults { inner: results })
}

impl PyDiscoveryOptions {
    fn inner_options(&self) -> DiscoveryOptions {
        DiscoveryOptions {
            strict_check: self.strict_check,
        }
    }
}

#[pyclass(name = "BookDiscoveryResults", module = "bible_organisational_system", from_py_object)]
#[derive(Clone)]
pub struct PyBookDiscoveryResults {
    pub(crate) inner: BookDiscoveryResults,
}

#[pymethods]
impl PyBookDiscoveryResults {
    #[getter]
    fn chapter_count(&self) -> Option<u16> { self.inner.chapter_count }
    #[getter]
    fn verse_count(&self) -> Option<u16> { self.inner.verse_count }
    #[getter]
    fn completed_verse_count(&self) -> u16 { self.inner.completed_verse_count }
    #[getter]
    fn percentage_progress(&self) -> Option<u8> { self.inner.percentage_progress }
    #[getter]
    fn word_count(&self) -> u32 { self.inner.word_count }

    fn __getitem__<'py>(&self, py: Python<'py>, key: &str) -> PyResult<Bound<'py, PyAny>> {
        let dict = self.to_dict(py)?;
        let bound_dict = dict.into_bound(py);
        match bound_dict.get_item(key)? {
            Some(val) => Ok(val),
            None => Err(pyo3::exceptions::PyKeyError::new_err(key.to_string())),
        }
    }
    
    // Convert to dict for easier Python access to all fields
    fn to_dict(&self, py: Python) -> PyResult<Py<PyDict>> {
        let dict = PyDict::new(py);
        dict.set_item("chapterCount", self.inner.chapter_count)?;
        dict.set_item("verseCount", self.inner.verse_count)?;
        dict.set_item("completedVerseCount", self.inner.completed_verse_count)?;
        dict.set_item("percentageProgress", self.inner.percentage_progress)?;
        dict.set_item("havePopulatedCVmarkers", self.inner.have_populated_cv_markers)?;
        dict.set_item("haveParagraphMarkers", self.inner.have_paragraph_markers)?;
        dict.set_item("haveIntroductoryMarkers", self.inner.have_introductory_markers)?;
        dict.set_item("haveMainHeadings", self.inner.have_main_headings)?;
        dict.set_item("mainHeadingsCount", self.inner.main_headings_count)?;
        dict.set_item("haveSectionHeadings", self.inner.have_section_headings)?;
        dict.set_item("sectionHeadingsCount", self.inner.section_headings_count)?;
        dict.set_item("haveSectionReferences", self.inner.have_section_references)?;
        dict.set_item("sectionReferencesCount", self.inner.section_references_count)?;
        dict.set_item("haveTables", self.inner.have_tables)?;
        dict.set_item("haveLists", self.inner.have_lists)?;
        dict.set_item("figuresCount", self.inner.figures_count)?;
        dict.set_item("haveFootnotes", self.inner.have_footnotes)?;
        dict.set_item("haveFootnoteOrigins", self.inner.have_footnote_origins)?;
        dict.set_item("footnotesCount", self.inner.footnotes_count)?;
        dict.set_item("haveCrossReferences", self.inner.have_cross_references)?;
        dict.set_item("haveCrossReferenceOrigins", self.inner.have_cross_reference_origins)?;
        dict.set_item("crossReferencesCount", self.inner.cross_references_count)?;
        dict.set_item("sectionReferencesParenthesisRatio", self.inner.section_references_parenthesis_ratio)?;
        dict.set_item("footnotesPeriodRatio", self.inner.footnotes_period_ratio)?;
        dict.set_item("crossReferencesPeriodRatio", self.inner.cross_references_period_ratio)?;
        dict.set_item("haveIntroductoryText", self.inner.have_introductory_text)?;
        dict.set_item("haveVerseText", self.inner.have_verse_text)?;
        dict.set_item("haveNestedUSFMarkers", self.inner.have_nested_usf_markers)?;
        dict.set_item("seemsFinished", self.inner.seems_finished)?;
        dict.set_item("notStarted", self.inner.not_started)?;
        dict.set_item("partlyDone", self.inner.partly_done)?;
        dict.set_item("wordCount", self.inner.word_count)?;
        dict.set_item("uniqueWordCount", self.inner.unique_word_count)?;
        dict.set_item("allWordCounts", self.inner.all_word_counts.clone().into_pyobject(py)?)?;
        dict.set_item("allCaseInsensitiveWordCounts", self.inner.all_case_insensitive_word_counts.clone().into_pyobject(py)?)?;
        dict.set_item("mainTextWordCounts", self.inner.main_text_word_counts.clone().into_pyobject(py)?)?;
        dict.set_item("mainTextCaseInsensitiveWordCounts", self.inner.main_text_case_insensitive_word_counts.clone().into_pyobject(py)?)?;
        
        Ok(dict.into())
    }
}

#[pyclass(name = "AggregateDiscoveryResults", module = "bible_organisational_system", from_py_object)]
#[derive(Clone)]
pub struct PyAggregateDiscoveryResults {
    pub(crate) inner: AggregateDiscoveryResults,
}

#[pymethods]
impl PyAggregateDiscoveryResults {
    fn to_dict(&self, py: Python) -> PyResult<Py<PyDict>> {
        let dict = PyDict::new(py);
        dict.set_item("otBookCount", self.inner.ot_book_count)?;
        dict.set_item("otBookCodes", self.inner.ot_book_codes.clone())?;
        dict.set_item("ntBookCount", self.inner.nt_book_count)?;
        dict.set_item("ntBookCodes", self.inner.nt_book_codes.clone())?;
        dict.set_item("dcBookCount", self.inner.dc_book_count)?;
        dict.set_item("dcBookCodes", self.inner.dc_book_codes.clone())?;
        dict.set_item("otherBookCount", self.inner.other_book_count)?;
        dict.set_item("otherBookCodes", self.inner.other_book_codes.clone())?;
        dict.set_item("notStartedBookCodes", self.inner.not_started_book_codes.clone())?;
        dict.set_item("otNotStartedBookCodes", self.inner.ot_not_started_book_codes.clone())?;
        dict.set_item("ntNotStartedBookCodes", self.inner.nt_not_started_book_codes.clone())?;
        dict.set_item("dcNotStartedBookCodes", self.inner.dc_not_started_book_codes.clone())?;
        dict.set_item("otherNotStartedBookCodes", self.inner.other_not_started_book_codes.clone())?;
        dict.set_item("seemsFinishedBookCodes", self.inner.seems_finished_book_codes.clone())?;
        dict.set_item("otSeemsFinishedBookCodes", self.inner.ot_seems_finished_book_codes.clone())?;
        dict.set_item("ntSeemsFinishedBookCodes", self.inner.nt_seems_finished_book_codes.clone())?;
        dict.set_item("dcSeemsFinishedBookCodes", self.inner.dc_seems_finished_book_codes.clone())?;
        dict.set_item("otherSeemsFinishedBookCodes", self.inner.other_seems_finished_book_codes.clone())?;
        dict.set_item("partlyDoneBookCodes", self.inner.partly_done_book_codes.clone())?;
        dict.set_item("otPartlyDoneBookCodes", self.inner.ot_partly_done_book_codes.clone())?;
        dict.set_item("ntPartlyDoneBookCodes", self.inner.nt_partly_done_book_codes.clone())?;
        dict.set_item("dcPartlyDoneBookCodes", self.inner.dc_partly_done_book_codes.clone())?;
        dict.set_item("otherPartlyDoneBookCodes", self.inner.other_partly_done_book_codes.clone())?;
        dict.set_item("percentageProgressByBook", self.inner.percentage_progress_by_book.clone())?;
        dict.set_item("otPercentageProgressByBook", self.inner.ot_percentage_progress_by_book.clone())?;
        dict.set_item("ntPercentageProgressByBook", self.inner.nt_percentage_progress_by_book.clone())?;
        dict.set_item("dcPercentageProgressByBook", self.inner.dc_percentage_progress_by_book.clone())?;
        dict.set_item("percentageProgressByVerse", self.inner.percentage_progress_by_verse.clone())?;
        dict.set_item("otPercentageProgressByVerse", self.inner.ot_percentage_progress_by_verse.clone())?;
        dict.set_item("ntPercentageProgressByVerse", self.inner.nt_percentage_progress_by_verse.clone())?;
        dict.set_item("dcPercentageProgressByVerse", self.inner.dc_percentage_progress_by_verse.clone())?;
        dict.set_item("verseCount", self.inner.verse_count)?;
        dict.set_item("otVerseCount", self.inner.ot_verse_count)?;
        dict.set_item("ntVerseCount", self.inner.nt_verse_count)?;
        dict.set_item("dcVerseCount", self.inner.dc_verse_count)?;
        dict.set_item("otherVerseCount", self.inner.other_verse_count)?;
        dict.set_item("completedVerseCount", self.inner.completed_verse_count)?;
        dict.set_item("otCompletedVerseCount", self.inner.ot_completed_verse_count)?;
        dict.set_item("ntCompletedVerseCount", self.inner.nt_completed_verse_count)?;
        dict.set_item("dcCompletedVerseCount", self.inner.dc_completed_verse_count)?;
        dict.set_item("otherCompletedVerseCount", self.inner.other_completed_verse_count)?;
        dict.set_item("wordCount", self.inner.word_count)?;
        dict.set_item("sectionReferencesParenthesisFlag", self.inner.section_references_parenthesis_flag)?;
        dict.set_item("footnotesPeriodFlag", self.inner.footnotes_period_flag)?;
        dict.set_item("crossReferencesPeriodFlag", self.inner.cross_references_period_flag)?;
        
        // Categorical summary counts
        dict.set_item("havePopulatedCVmarkers", self.inner.have_populated_cv_markers)?;
        dict.set_item("otHavePopulatedCVmarkers", self.inner.ot_have_populated_cv_markers)?;
        dict.set_item("ntHavePopulatedCVmarkers", self.inner.nt_have_populated_cv_markers)?;
        dict.set_item("dcHavePopulatedCVmarkers", self.inner.dc_have_populated_cv_markers)?;
        dict.set_item("otherHavePopulatedCVmarkers", self.inner.other_have_populated_cv_markers)?;

        dict.set_item("haveParagraphMarkers", self.inner.have_paragraph_markers)?;
        dict.set_item("otHaveParagraphMarkers", self.inner.ot_have_paragraph_markers)?;
        dict.set_item("ntHaveParagraphMarkers", self.inner.nt_have_paragraph_markers)?;
        dict.set_item("dcHaveParagraphMarkers", self.inner.dc_have_paragraph_markers)?;
        dict.set_item("otherHaveParagraphMarkers", self.inner.other_have_paragraph_markers)?;

        dict.set_item("haveIntroductoryMarkers", self.inner.have_introductory_markers)?;
        dict.set_item("otHaveIntroductoryMarkers", self.inner.ot_have_introductory_markers)?;
        dict.set_item("ntHaveIntroductoryMarkers", self.inner.nt_have_introductory_markers)?;
        dict.set_item("dcHaveIntroductoryMarkers", self.inner.dc_have_introductory_markers)?;
        dict.set_item("otherHaveIntroductoryMarkers", self.inner.other_have_introductory_markers)?;

        dict.set_item("haveMainHeadings", self.inner.have_main_headings)?;
        dict.set_item("otHaveMainHeadings", self.inner.ot_have_main_headings)?;
        dict.set_item("ntHaveMainHeadings", self.inner.nt_have_main_headings)?;
        dict.set_item("dcHaveMainHeadings", self.inner.dc_have_main_headings)?;
        dict.set_item("otherHaveMainHeadings", self.inner.other_have_main_headings)?;

        dict.set_item("haveSectionHeadings", self.inner.have_section_headings)?;
        dict.set_item("otHaveSectionHeadings", self.inner.ot_have_section_headings)?;
        dict.set_item("ntHaveSectionHeadings", self.inner.nt_have_section_headings)?;
        dict.set_item("dcHaveSectionHeadings", self.inner.dc_have_section_headings)?;
        dict.set_item("otherHaveSectionHeadings", self.inner.other_have_section_headings)?;

        dict.set_item("haveSectionReferences", self.inner.have_section_references)?;
        dict.set_item("otHaveSectionReferences", self.inner.ot_have_section_references)?;
        dict.set_item("ntHaveSectionReferences", self.inner.nt_have_section_references)?;
        dict.set_item("dcHaveSectionReferences", self.inner.dc_have_section_references)?;
        dict.set_item("otherHaveSectionReferences", self.inner.other_have_section_references)?;

        dict.set_item("haveTables", self.inner.have_tables)?;
        dict.set_item("otHaveTables", self.inner.ot_have_tables)?;
        dict.set_item("ntHaveTables", self.inner.nt_have_tables)?;
        dict.set_item("dcHaveTables", self.inner.dc_have_tables)?;
        dict.set_item("otherHaveTables", self.inner.other_have_tables)?;

        dict.set_item("haveLists", self.inner.have_lists)?;
        dict.set_item("otHaveLists", self.inner.ot_have_lists)?;
        dict.set_item("ntHaveLists", self.inner.nt_have_lists)?;
        dict.set_item("dcHaveLists", self.inner.dc_have_lists)?;
        dict.set_item("otherHaveLists", self.inner.other_have_lists)?;

        dict.set_item("haveFootnotes", self.inner.have_footnotes)?;
        dict.set_item("otHaveFootnotes", self.inner.ot_have_footnotes)?;
        dict.set_item("ntHaveFootnotes", self.inner.nt_have_footnotes)?;
        dict.set_item("dcHaveFootnotes", self.inner.dc_have_footnotes)?;
        dict.set_item("otherHaveFootnotes", self.inner.other_have_footnotes)?;

        dict.set_item("haveFootnoteOrigins", self.inner.have_footnote_origins)?;
        dict.set_item("otHaveFootnoteOrigins", self.inner.ot_have_footnote_origins)?;
        dict.set_item("ntHaveFootnoteOrigins", self.inner.nt_have_footnote_origins)?;
        dict.set_item("dcHaveFootnoteOrigins", self.inner.dc_have_footnote_origins)?;
        dict.set_item("otherHaveFootnoteOrigins", self.inner.other_have_footnote_origins)?;

        dict.set_item("haveCrossReferences", self.inner.have_cross_references)?;
        dict.set_item("otHaveCrossReferences", self.inner.ot_have_cross_references)?;
        dict.set_item("ntHaveCrossReferences", self.inner.nt_have_cross_references)?;
        dict.set_item("dcHaveCrossReferences", self.inner.dc_have_cross_references)?;
        dict.set_item("otherHaveCrossReferences", self.inner.other_have_cross_references)?;

        dict.set_item("haveCrossReferenceOrigins", self.inner.have_cross_reference_origins)?;
        dict.set_item("otHaveCrossReferenceOrigins", self.inner.ot_have_cross_reference_origins)?;
        dict.set_item("ntHaveCrossReferenceOrigins", self.inner.nt_have_cross_reference_origins)?;
        dict.set_item("dcHaveCrossReferenceOrigins", self.inner.dc_have_cross_reference_origins)?;
        dict.set_item("otherHaveCrossReferenceOrigins", self.inner.other_have_cross_reference_origins)?;

        dict.set_item("haveIntroductoryText", self.inner.have_introductory_text)?;
        dict.set_item("otHaveIntroductoryText", self.inner.ot_have_introductory_text)?;
        dict.set_item("ntHaveIntroductoryText", self.inner.nt_have_introductory_text)?;
        dict.set_item("dcHaveIntroductoryText", self.inner.dc_have_introductory_text)?;
        dict.set_item("otherHaveIntroductoryText", self.inner.other_have_introductory_text)?;

        dict.set_item("haveVerseText", self.inner.have_verse_text)?;
        dict.set_item("otHaveVerseText", self.inner.ot_have_verse_text)?;
        dict.set_item("ntHaveVerseText", self.inner.nt_have_verse_text)?;
        dict.set_item("dcHaveVerseText", self.inner.dc_have_verse_text)?;
        dict.set_item("otherHaveVerseText", self.inner.other_have_verse_text)?;

        dict.set_item("haveNestedUSFMarkers", self.inner.have_nested_usf_markers)?;
        dict.set_item("otHaveNestedUSFMarkers", self.inner.ot_have_nested_usf_markers)?;
        dict.set_item("ntHaveNestedUSFMarkers", self.inner.nt_have_nested_usf_markers)?;
        dict.set_item("dcHaveNestedUSFMarkers", self.inner.dc_have_nested_usf_markers)?;
        dict.set_item("otherHaveNestedUSFMarkers", self.inner.other_have_nested_usf_markers)?;

        Ok(dict.into())
    }
}

#[pyclass(name = "BibleDiscoveryResults", module = "bible_organisational_system", from_py_object)]
#[derive(Clone)]
pub struct PyBibleDiscoveryResults {
    pub(crate) inner: BibleDiscoveryResults,
}

#[pymethods]
impl PyBibleDiscoveryResults {
    #[getter]
    fn all(&self) -> PyAggregateDiscoveryResults {
        PyAggregateDiscoveryResults { inner: self.inner.all.clone() }
    }
    
    #[getter]
    fn books(&self, py: Python) -> PyResult<Py<PyDict>> {
        let dict = PyDict::new(py);
        for (bbb, results) in &self.inner.books {
            let py_results = PyBookDiscoveryResults { inner: results.clone() };
            // Return dict instead of object for subscriptable access
            dict.set_item(bbb, py_results.to_dict(py)?)?;
        }
        Ok(dict.into())
    }

    #[getter]
    fn books_as_objects(&self, py: Python) -> PyResult<Py<PyDict>> {
        let dict = PyDict::new(py);
        for (bbb, results) in &self.inner.books {
            let py_results = PyBookDiscoveryResults { inner: results.clone() };
            dict.set_item(bbb, py_results.into_pyobject(py)?)?;
        }
        Ok(dict.into())
    }

    fn get_book_results(&self, bbb: &str) -> Option<PyBookDiscoveryResults> {
        self.inner.books.get(bbb).map(|r| PyBookDiscoveryResults { inner: r.clone() })
    }
}

#[pyfunction]
#[pyo3(name = "discoverBook")]
pub fn py_discover_book<'py>(
    py: Python<'py>,
    entries: &PyInternalBibleEntryList,
    bbb: &str,
) -> PyResult<Bound<'py, PyBookDiscoveryResults>> {
    let results = discover_book(&entries.inner, bbb);
    Bound::new(py, PyBookDiscoveryResults { inner: results })
}

#[pyfunction]
#[pyo3(name = "discoverBible")]
pub fn py_discover_bible<'py>(
    py: Python<'py>,
    books_dict: &Bound<'py, PyDict>,
) -> PyResult<Bound<'py, PyBibleDiscoveryResults>> {
    let mut books = IndexMap::new();

    for (key, value) in books_dict.iter() {
        let bbb: String = key.extract()?;
        let py_list: PyRef<PyInternalBibleEntryList> = value.extract()?;
        books.insert(bbb, py_list.inner.clone());
    }

    let results = discover_bible(&books);
    Bound::new(py, PyBibleDiscoveryResults { inner: results })
}
