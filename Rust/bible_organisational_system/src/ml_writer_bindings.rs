//! Python bindings for MlWriter.

use pyo3::prelude::*;
use bos_internals::ml_writer::{self, MlWriter, MlOutputType, HumanReadable, SectionName};

#[pyclass(name = "MlOutputType", module = "bible_organisational_system")]
#[derive(Clone, Copy)]
pub enum PyMlOutputType {
    Xml,
    Html,
}

#[pyclass(name = "HumanReadable", module = "bible_organisational_system")]
#[derive(Clone, Copy)]
pub enum PyHumanReadable {
    All,
    Header,
    NoIndentation,
    NlSpace,
}

#[pyclass(name = "SectionName", module = "bible_organisational_system")]
#[derive(Clone, Copy)]
pub enum PySectionName {
    NoSection,
    Header,
    Main,
}

#[pyclass(name = "MlWriter", module = "bible_organisational_system")]
pub struct PyMlWriter {
    inner: MlWriter,
}

#[pymethods]
impl PyMlWriter {
    #[new]
    fn new(path: String, output_type: PyMlOutputType) -> Self {
        let ot = match output_type {
            PyMlOutputType::Xml => MlOutputType::Xml,
            PyMlOutputType::Html => MlOutputType::Html,
        };
        Self {
            inner: MlWriter::new(path, ot),
        }
    }

    #[setter]
    fn set_space_before_selfclose_tag(&mut self, value: bool) {
        self.inner.space_before_selfclose_tag = value;
    }

    #[setter]
    fn set_halt_on_errors(&mut self, value: bool) {
        self.inner.halt_on_errors = value;
    }

    #[getter]
    fn lines_written(&self) -> usize {
        self.inner.lines_written
    }

    fn set_human_readable(&mut self, value: PyHumanReadable, indent_size: usize) {
        let hr = match value {
            PyHumanReadable::All => HumanReadable::All,
            PyHumanReadable::Header => HumanReadable::Header,
            PyHumanReadable::NoIndentation => HumanReadable::NoIndentation,
            PyHumanReadable::NlSpace => HumanReadable::NlSpace,
        };
        self.inner.set_human_readable(hr, indent_size);
    }

    fn set_section_name(&mut self, name: PySectionName) {
        let sn = match name {
            PySectionName::NoSection => SectionName::NoSection,
            PySectionName::Header => SectionName::Header,
            PySectionName::Main => SectionName::Main,
        };
        self.inner.set_section_name(sn);
    }

    fn start(&mut self, line_endings: char, no_auto_xml: bool, write_bom: bool) -> PyResult<()> {
        self.inner.start(line_endings, no_auto_xml, write_bom)
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))
    }

    fn write_line_text(&mut self, text: String, no_nl: Option<bool>) -> PyResult<usize> {
        self.inner.write_line_text(&text, no_nl)
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))
    }

    fn write_line_open(&mut self, tag: String, attrib_info: Option<Vec<(String, String)>>, no_nl: Option<bool>) -> PyResult<()> {
        let attribs: Option<Vec<(&str, &str)>> = attrib_info.as_ref().map(|v| {
            v.iter().map(|(n, val)| (n.as_str(), val.as_str())).collect()
        });
        self.inner.write_line_open(&tag, attribs.as_deref(), no_nl)
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))
    }

    fn write_line_close(&mut self, tag: String) -> PyResult<()> {
        self.inner.write_line_close(&tag)
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))
    }

    fn write_line_open_close(&mut self, tag: String, text: String, attrib_info: Option<Vec<(String, String)>>) -> PyResult<usize> {
        let attribs: Option<Vec<(&str, &str)>> = attrib_info.as_ref().map(|v| {
            v.iter().map(|(n, val)| (n.as_str(), val.as_str())).collect()
        });
        self.inner.write_line_open_close(&tag, &text, attribs.as_deref())
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))
    }

    fn write_line_open_selfclose(&mut self, tag: String, attrib_info: Option<Vec<(String, String)>>) -> PyResult<usize> {
        let attribs: Option<Vec<(&str, &str)>> = attrib_info.as_ref().map(|v| {
            v.iter().map(|(n, val)| (n.as_str(), val.as_str())).collect()
        });
        self.inner.write_line_open_selfclose(&tag, attribs.as_deref())
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))
    }

    fn close(&mut self, write_final_nl: bool) -> PyResult<()> {
        self.inner.close(write_final_nl)
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))
    }

    fn get_file_position(&mut self) -> PyResult<u64> {
        self.inner.get_file_position()
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))
    }
}

#[pyfunction]
#[pyo3(name = "escapeCharacters")]
pub fn py_escape_characters(s: &str) -> String {
    ml_writer::escape_characters(s)
}
