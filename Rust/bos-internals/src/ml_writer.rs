//! XML/HTML writer core logic.

use std::fs::File;
use std::io::{BufWriter, Write, Seek, SeekFrom};
use std::path::{Path, PathBuf};
use compact_str::CompactString;

/// Allowed output types for MlWriter.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MlOutputType {
    Xml,
    Html,
}

/// Human readability modes.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum HumanReadable {
    #[default]
    All,
    Header,
    NoIndentation,
    NlSpace,
}

/// Section names for finer control.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum SectionName {
    #[default]
    NoSection,
    Header,
    Main,
}

/// State for MLWriter.
pub struct MlWriter {
    output_path: PathBuf,
    output_type: MlOutputType,
    output_file: Option<BufWriter<File>>,
    
    pub space_before_selfclose_tag: bool,
    suppress_following_indent: bool,
    human_readable: HumanReadable,
    indent_per_level: usize,
    limit_columns: bool,
    max_columns: usize,
    
    section_name: SectionName,
    open_stack: Vec<CompactString>,
    current_column: usize,
    nl: CompactString,
    pub lines_written: usize,
    pub halt_on_errors: bool,
}

impl MlWriter {
    pub fn new<P: AsRef<Path>>(path: P, output_type: MlOutputType) -> Self {
        Self {
            output_path: path.as_ref().to_path_buf(),
            output_type,
            output_file: None,
            space_before_selfclose_tag: false,
            suppress_following_indent: false,
            human_readable: HumanReadable::All,
            indent_per_level: 2,
            limit_columns: true,
            max_columns: 70,
            section_name: SectionName::NoSection,
            open_stack: Vec::new(),
            current_column: 0,
            nl: CompactString::from("\n"),
            lines_written: 0,
            halt_on_errors: false,
        }
    }

    pub fn set_human_readable(&mut self, value: HumanReadable, indent_size: usize) {
        self.human_readable = value;
        self.indent_per_level = indent_size;
        if value == HumanReadable::NlSpace {
            self.limit_columns = false;
        }
    }

    pub fn set_section_name(&mut self, name: SectionName) {
        self.section_name = name;
    }

    pub fn start(&mut self, line_endings: char, no_auto_xml: bool, write_bom: bool) -> Result<(), Box<dyn std::error::Error>> {
        self.nl = match line_endings {
            'l' => CompactString::from("\n"),
            'w' => CompactString::from("\r\n"),
            _ => return Err(format!("Unknown line endings flag: {}", line_endings).into()),
        };

        let file = File::create(&self.output_path)?;
        let mut writer = BufWriter::new(file);

        if write_bom {
            writer.write_all(b"\xef\xbb\xbf")?;
        }

        self.output_file = Some(writer);
        self.current_column = 0;

        if self.output_type == MlOutputType::Xml && !no_auto_xml {
            let chars = format!("{}<?xml version=\"1.0\" encoding=\"utf-8\"?>", self.sp());
            self.current_column += chars.len();
            self.auto_write(&chars, false)?;
        }

        Ok(())
    }

    fn sp(&self) -> String {
        if self.suppress_following_indent {
            return String::new();
        }
        match self.human_readable {
            HumanReadable::NoIndentation => String::new(),
            HumanReadable::All | HumanReadable::NlSpace => " ".repeat(self.open_stack.len() * self.indent_per_level),
            HumanReadable::Header => {
                if self.section_name == SectionName::Main {
                    String::new()
                } else {
                    " ".repeat(self.open_stack.len() * self.indent_per_level)
                }
            }
        }
    }

    fn nl_char(&self) -> &str {
        match self.human_readable {
            HumanReadable::NoIndentation => "",
            HumanReadable::All => &self.nl,
            HumanReadable::NlSpace => " ",
            HumanReadable::Header => {
                if self.section_name == SectionName::Main {
                    ""
                } else {
                    &self.nl
                }
            }
        }
    }

    fn auto_write(&mut self, s: &str, no_nl: bool) -> Result<usize, Box<dyn std::error::Error>> {
        let mut chars = self.sp();
        chars.push_str(s);
        
        if !chars.is_empty() && self.suppress_following_indent {
            self.suppress_following_indent = false;
        }

        let mut length = chars.len();
        self.current_column += length;

        if no_nl {
            self.suppress_following_indent = true;
        } else {
            let final_nl = self.nl_char();
            let mut final_s = final_nl.to_string();
            
            // Override if past max columns
            if self.limit_columns && self.current_column >= self.max_columns {
                final_s = self.nl.to_string();
            }

            if final_s == self.nl.as_str() {
                self.current_column = 0;
                self.lines_written += 1;
            }
            chars.push_str(&final_s);
            length += final_s.len();
        }

        if let Some(ref mut writer) = self.output_file {
            writer.write_all(chars.as_bytes())?;
        }
        Ok(length)
    }

    pub fn write_line_text(&mut self, text: &str, no_nl: Option<bool>) -> Result<usize, Box<dyn std::error::Error>> {
        let no_nl_val = no_nl.unwrap_or_else(|| {
            self.output_type == MlOutputType::Html && !self.open_stack.is_empty() && is_html_combined_tag(&self.open_stack.last().unwrap())
        });
        self.auto_write(text, no_nl_val)
    }

    pub fn write_line_open(&mut self, tag: &str, attrib_info: Option<&[(&str, &str)]>, no_nl: Option<bool>) -> Result<(), Box<dyn std::error::Error>> {
        let no_nl_val = no_nl.unwrap_or_else(|| {
            self.output_type == MlOutputType::Html && is_html_combined_tag(tag)
        });

        let mut s = format!("<{}", tag);
        if let Some(attribs) = attrib_info {
            for (name, val) in attribs {
                s.push_str(&format!(" {}=\"{}\"", name, val));
            }
        }
        s.push('>');

        self.auto_write(&s, no_nl_val)?;
        self.open_stack.push(CompactString::from(tag));
        Ok(())
    }

    pub fn write_line_close(&mut self, tag: &str) -> Result<(), Box<dyn std::error::Error>> {
        if self.open_stack.is_empty() {
            if self.halt_on_errors {
                return Err(format!("Closed {} tag even though no tags open", tag).into());
            }
        } else {
            let expected = self.open_stack.pop().unwrap();
            if expected != tag {
                if self.halt_on_errors {
                    return Err(format!("Closed {} tag but should have closed {}", tag, expected).into());
                }
            }
        }

        let no_nl = self.output_type == MlOutputType::Html && is_html_inside_tag(tag);
        self.auto_write(&format!("</{}>", tag), no_nl)?;
        Ok(())
    }

    pub fn write_line_open_close(&mut self, tag: &str, text: &str, attrib_info: Option<&[(&str, &str)]>) -> Result<usize, Box<dyn std::error::Error>> {
        let mut s = format!("<{}", tag);
        if let Some(attribs) = attrib_info {
            for (name, val) in attribs {
                s.push_str(&format!(" {}=\"{}\"", name, val));
            }
        }
        s.push('>');
        s.push_str(text);
        s.push_str(&format!("</{}>", tag));

        let no_nl = self.output_type == MlOutputType::Html && is_html_inside_tag(tag);
        self.auto_write(&s, no_nl)
    }

    pub fn write_line_open_selfclose(&mut self, tag: &str, attrib_info: Option<&[(&str, &str)]>) -> Result<usize, Box<dyn std::error::Error>> {
        let mut s = format!("<{}", tag);
        if let Some(attribs) = attrib_info {
            for (name, val) in attribs {
                s.push_str(&format!(" {}=\"{}\"", name, val));
            }
        }
        if self.space_before_selfclose_tag {
            s.push(' ');
        }
        s.push_str("/>");
        self.auto_write(&s, false)
    }

    pub fn close(&mut self, write_final_nl: bool) -> Result<(), Box<dyn std::error::Error>> {
        if let Some(ref mut writer) = self.output_file {
            if !self.open_stack.is_empty() && self.halt_on_errors {
                return Err(format!("Have unclosed tags: {:?}", self.open_stack).into());
            }
            if write_final_nl {
                writer.write_all(self.nl.as_bytes())?;
            }
            writer.flush()?;
        }
        self.output_file = None;
        Ok(())
    }

    pub fn get_file_position(&mut self) -> Result<u64, Box<dyn std::error::Error>> {
        if let Some(ref mut writer) = self.output_file {
            writer.flush()?;
            Ok(writer.get_mut().seek(SeekFrom::Current(0))?)
        } else {
            Ok(0)
        }
    }
}

fn is_html_para_tag(tag: &str) -> bool {
    matches!(tag, "p")
}

fn is_html_inside_tag(tag: &str) -> bool {
    matches!(tag, "a" | "b" | "em" | "i" | "sup" | "sub" | "span")
}

fn is_html_combined_tag(tag: &str) -> bool {
    is_html_para_tag(tag) || is_html_inside_tag(tag)
}

pub fn escape_characters(s: &str) -> String {
    s.replace('&', "&amp;")
     .replace('"', "&quot;")
     .replace('<', "&lt;")
     .replace('>', "&gt;")
}
