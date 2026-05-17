//! I/O utilities for reading SFM, USFM, and ESFM files.

use std::fs::File;
use std::io::{BufRead, BufReader};
use std::path::Path;
use compact_str::CompactString;

/// Large dummy value used in marker splitting, similar to Python implementation.
const LARGE_DUMMY_VALUE: usize = 999999;
/// Unicode Byte Order Marker (BOM)
pub const BOM: char = '\u{feff}';

/// Split a USFM marker from its following text.
///
/// Ported from Python `splitUSFMMarkerFromText`.
pub fn split_usfm_marker_from_text(line: &str) -> (Option<CompactString>, CompactString) {
    if line.is_empty() {
        return (None, CompactString::new(""));
    }
    if !line.starts_with('\\') {
        return (None, CompactString::new(line));
    }

    let line_after_leading_backslash = &line[1..];
    let ix_sp = line_after_leading_backslash.find(' ').unwrap_or(LARGE_DUMMY_VALUE);
    let ix_as = line_after_leading_backslash.find('*').unwrap_or(LARGE_DUMMY_VALUE);
    let ix_bs = line_after_leading_backslash.find('\\').unwrap_or(LARGE_DUMMY_VALUE);

    let ix = ix_sp.min(ix_as).min(ix_bs);

    if ix == LARGE_DUMMY_VALUE {
        (Some(CompactString::new(line_after_leading_backslash)), CompactString::new(""))
    } else {
        let (marker, text) = if ix == ix_bs {
            if line_after_leading_backslash.len() > ix_bs + 1
                && line_after_leading_backslash.as_bytes()[ix_bs + 1] == b'*'
            {
                // Self-closed marker like \ts\*
                (&line_after_leading_backslash[..ix_bs + 2], &line_after_leading_backslash[ix_bs + 2..])
            } else {
                (&line_after_leading_backslash[..ix_bs], &line_after_leading_backslash[ix_bs..])
            }
        } else if ix == ix_as {
            (&line_after_leading_backslash[..ix_as + 1], &line_after_leading_backslash[ix_as + 1..])
        } else {
            // ix == ix_sp
            (&line_after_leading_backslash[..ix_sp], &line_after_leading_backslash[ix_sp + 1..])
        };
        (Some(CompactString::new(marker)), CompactString::new(text))
    }
}

/// A line in an SFM/USFM/ESFM file.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SfmLine {
    pub marker: CompactString,
    pub text: CompactString,
}

/// Fetch content from a URL or read from a local file.
fn read_lines<P: AsRef<Path>>(path_or_url: P) -> Result<Vec<String>, Box<dyn std::error::Error>> {
    let path_str = path_or_url.as_ref().to_string_lossy();
    if path_str.starts_with("https://") || path_str.starts_with("http://") {
        let response = ureq::get(path_str.as_ref()).call()?;
        let body = response.into_body().read_to_string()?;
        Ok(body.lines().map(|s| s.to_string()).collect())
    } else {
        let file = File::open(path_or_url)?;
        let reader = BufReader::new(file);
        let mut lines = Vec::new();
        for line in reader.lines() {
            lines.push(line?);
        }
        Ok(lines)
    }
}

/// Implementation for USFMFile.read
pub fn read_usfm_file<P: AsRef<Path>>(
    path: P,
    ignore_sfms: &[&str],
) -> Result<Vec<SfmLine>, Box<dyn std::error::Error>> {
    let file_lines = read_lines(path)?;
    let mut result: Vec<SfmLine> = Vec::new();
    let mut marker: Option<CompactString> = None;

    for (i, mut line) in file_lines.into_iter().enumerate() {
        if i == 0 && line.starts_with(BOM) {
            line.remove(0);
        }
        if line.is_empty() {
            continue;
        }
        if line.starts_with('#') {
            continue;
        }

        if !line.starts_with('\\') {
            if result.is_empty() {
                // Ignore non-USFM line before any marker
                continue;
            } else {
                // Continuation line
                if let Some(m) = &marker {
                    if !ignore_sfms.contains(&m.as_str()) {
                        if let Some(last) = result.last_mut() {
                            last.text.push(' ');
                            last.text.push_str(&line);
                        }
                    }
                }
                continue;
            }
        }

        let (m, t) = split_usfm_marker_from_text(&line);
        if let Some(m_val) = m {
            marker = Some(m_val.clone());
            if !ignore_sfms.contains(&m_val.as_str()) {
                result.push(SfmLine {
                    marker: m_val,
                    text: t,
                });
            }
        }
    }
    Ok(result)
}

/// Implementation for ESFMFile.read
pub fn read_esfm_file<P: AsRef<Path>>(
    path: P,
    ignore_sfms: &[&str],
) -> Result<Vec<SfmLine>, Box<dyn std::error::Error>> {
    let file_lines = read_lines(path)?;
    let mut result: Vec<SfmLine> = Vec::new();
    let mut marker: Option<CompactString> = None;

    for (i, mut line) in file_lines.into_iter().enumerate() {
        if i == 0 && line.starts_with(BOM) {
            line.remove(0);
        }
        if line.is_empty() {
            continue;
        }
        if line.starts_with('#') {
            continue;
        }

        let current_line = line.trim_start();
        if current_line.is_empty() {
            continue;
        }

        if !current_line.starts_with('\\') {
            if result.is_empty() {
                continue;
            } else {
                if let Some(m) = &marker {
                    if !ignore_sfms.contains(&m.as_str()) {
                        if let Some(last) = result.last_mut() {
                            last.text.push(' ');
                            last.text.push_str(current_line);
                        }
                    }
                }
                continue;
            }
        }

        let (m, t) = split_usfm_marker_from_text(current_line);
        if let Some(m_val) = m {
            marker = Some(m_val.clone());
            if !ignore_sfms.contains(&m_val.as_str()) {
                result.push(SfmLine {
                    marker: m_val,
                    text: t,
                });
            }
        }
    }
    Ok(result)
}

/// Implementation for SFMLines.read
pub fn read_sfm_lines<P: AsRef<Path>>(
    path: P,
    ignore_sfms: &[&str],
) -> Result<Vec<SfmLine>, Box<dyn std::error::Error>> {
    let file_lines = read_lines(path)?;
    let mut result: Vec<SfmLine> = Vec::new();
    let mut marker: Option<CompactString> = None;

    for (i, mut line) in file_lines.into_iter().enumerate() {
        if i == 0 && line.starts_with(BOM) {
            line.remove(0);
        }
        if line.is_empty() {
            continue;
        }
        if line.starts_with('#') {
            continue;
        }

        if !line.starts_with('\\') {
            if result.is_empty() {
                continue;
            } else {
                if let Some(m) = &marker {
                    if !ignore_sfms.contains(&m.as_str()) {
                        if let Some(last) = result.last_mut() {
                            last.text.push(' ');
                            last.text.push_str(&line);
                        }
                    }
                }
                continue;
            }
        }

        let line_after_backslash = &line[1..];
        let si1 = line_after_backslash.find(' ');
        let si2 = line_after_backslash.find('\\');

        let (m_str, t_str) = if let Some(pos2) = si2 {
            if si1.is_none() || pos2 < si1.unwrap() {
                (&line_after_backslash[..pos2], &line_after_backslash[pos2..])
            } else {
                let pos1 = si1.unwrap();
                (&line_after_backslash[..pos1], &line_after_backslash[pos1 + 1..])
            }
        } else if let Some(pos1) = si1 {
            (&line_after_backslash[..pos1], &line_after_backslash[pos1 + 1..])
        } else {
            (line_after_backslash, "")
        };

        let m_val = CompactString::new(m_str);
        marker = Some(m_val.clone());
        if !ignore_sfms.contains(&m_val.as_str()) {
            result.push(SfmLine {
                marker: m_val,
                text: CompactString::new(t_str),
            });
        }
    }
    Ok(result)
}

/// Implementation for SFMRecords.read
pub fn read_sfm_records<P: AsRef<Path>>(
    path: P,
    key: Option<&str>,
    ignore_sfms: &[&str],
    ignore_entries: &[&str],
    change_pairs: &[(String, String)],
) -> Result<Vec<Vec<SfmLine>>, Box<dyn std::error::Error>> {
    let file_lines = read_lines(path)?;
    let mut result = Vec::new();
    let mut current_record: Vec<SfmLine> = Vec::new();
    let mut current_key = key.map(|s| s.to_string());

    let change_marker = |m: &str| -> CompactString {
        for (find, replace) in change_pairs {
            if find == m {
                return CompactString::new(replace);
            }
        }
        CompactString::new(m)
    };

    for (i, mut line) in file_lines.into_iter().enumerate() {
        if i == 0 && line.starts_with(BOM) {
            line.remove(0);
        }
        if line.is_empty() {
            continue;
        }
        if line.starts_with('#') {
            continue;
        }

        if !line.starts_with('\\') {
            if current_record.is_empty() {
                continue; // Error in Python, but we follow its structure
            } else {
                if let Some(last) = current_record.last_mut() {
                    last.text.push(' ');
                    last.text.push_str(&line);
                }
                continue;
            }
        }

        let line_after_backslash = &line[1..];
        let si1 = line_after_backslash.find(' ');
        let si2 = line_after_backslash.find('\\');

        let (m_str, t_str) = if let Some(pos2) = si2 {
            if si1.is_none() || pos2 < si1.unwrap() {
                (&line_after_backslash[..pos2], &line_after_backslash[pos2..])
            } else {
                let pos1 = si1.unwrap();
                (&line_after_backslash[..pos1], &line_after_backslash[pos1 + 1..])
            }
        } else if let Some(pos1) = si1 {
            (&line_after_backslash[..pos1], &line_after_backslash[pos1 + 1..])
        } else {
            (line_after_backslash, "")
        };

        let marker = change_marker(m_str);
        let text = CompactString::new(t_str);

        if current_key.is_none() && !ignore_sfms.contains(&marker.as_str()) {
            current_key = Some(marker.to_string());
        }

        if let Some(k) = &current_key {
            if marker.as_str() == k {
                // Save previous record
                if !current_record.is_empty() {
                    let first_text = current_record[0].text.as_str();
                    if !ignore_entries.contains(&first_text) {
                        let mut stripped = Vec::new();
                        for l in current_record {
                            if !ignore_sfms.contains(&l.marker.as_str()) {
                                stripped.push(l);
                            }
                        }
                        if !stripped.is_empty() {
                            result.push(stripped);
                        }
                    }
                }
                current_record = Vec::new();
            }
        }
        current_record.push(SfmLine { marker, text });
    }

    // Save last record
    if !current_record.is_empty() {
        let first_text = current_record[0].text.as_str();
        if !ignore_entries.contains(&first_text) {
            let mut stripped = Vec::new();
            for l in current_record {
                if !ignore_sfms.contains(&l.marker.as_str()) {
                    stripped.push(l);
                }
            }
            if !stripped.is_empty() {
                result.push(stripped);
            }
        }
    }

    Ok(result)
}
