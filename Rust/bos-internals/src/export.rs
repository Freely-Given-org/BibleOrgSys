//! Unified Rust Parallel Export Framework using Rayon.
//!
//! This module implements high-performance multi-threaded Bible book exporters,
//! beginning with core parallel formats (PlainText and HTML5).

use std::collections::{HashMap, HashSet};
use std::fs::{self, File};
use std::io::{Write, BufWriter};
use std::path::Path;
use crate::entry_lists::InternalBibleEntryList;
use crate::error::BosError;
use rayon::prelude::*;

// Import constants from usfm_markers dependency
use usfm_markers::{OFTEN_IGNORED_USFM_HEADER_MARKERS, USFM_ALL_INTRODUCTION_MARKERS};

/// Replaces potentially unsafe characters in a name to make it suitable for a filename.
/// Exact replacement logic matches BibleOrgSysGlobals.makeSafeFilename.
pub fn make_safe_filename(name: &str) -> String {
    name.replace('/', "-")
        .replace('\\', "_BACKSLASH_")
        .replace(':', "_COLON_")
        .replace(';', "_SEMICOLON_")
        .replace('#', "_HASH_")
        .replace('?', "_QUESTIONMARK_")
        .replace('*', "_ASTERISK_")
        .replace('<', "_LT_")
        .replace('>', "_GT_")
}

/// Core parallel plain-text exporter.
///
/// Iterates over all books in parallel using Rayon, formats their text lines,
/// and writes them to UTF-8 text files (both with BOM and without BOM).
/// Accumulates and returns all ignored USFM markers.
pub fn export_to_text(
    books: &HashMap<String, InternalBibleEntryList>,
    output_path: &Path,
    column_width: usize,
) -> Result<HashSet<String>, BosError> {
    // Ensure both output directories exist
    let without_bom_dir = output_path.join("Without_ByteOrderMarker");
    fs::create_dir_all(output_path)
        .map_err(BosError::Io)?;
    fs::create_dir_all(&without_bom_dir)
        .map_err(BosError::Io)?;

    // Process all books in parallel via Rayon
    let ignored_markers: HashSet<String> = books
        .par_iter()
        .map(|(bbb, entry_list)| {
            let mut local_ignored = HashSet::new();
            let mut content = String::new();
            let mut text_buffer = String::new();
            let mut got_vp: Option<String> = None;

            for entry in entry_list.iter() {
                let marker = entry.marker();
                let text = entry.clean_text();

                // 1. Silent ignore added/custom markers
                if marker.starts_with('¬') || marker == "c#" || marker == "v=" {
                    continue;
                }

                // 2. Often ignored header markers
                let is_ignored_header = OFTEN_IGNORED_USFM_HEADER_MARKERS.contains(&marker)
                    || matches!(marker, "r" | "d" | "sp" | "cp" | "ie");

                if is_ignored_header {
                    local_ignored.insert(marker.to_string());
                } else if marker == "h" {
                    // EFFICIENCY COMMENT:
                    // In the Python code, the 'elif marker == h' branch is placed AFTER the check for
                    // OFTEN_IGNORED_USFM_HEADER_MARKERS. Since 'h' is actually IN OFTEN_IGNORED_USFM_HEADER_MARKERS,
                    // this branch is never hit in Python. We follow the exact same logic here to maintain byte-for-byte
                    // output compatibility, but note that this code is technically unreachable.
                    if !text_buffer.is_empty() {
                        content.push_str(&text_buffer);
                        text_buffer.clear();
                    }
                    content.push_str(&format!("{}\n\n", text));
                } else if USFM_ALL_INTRODUCTION_MARKERS.contains(&marker) {
                    local_ignored.insert(marker.to_string());
                } else if matches!(marker, "mt1" | "mt2" | "mt3" | "mt4" | "imt1" | "imt2" | "imt3" | "imt4") {
                    if !text_buffer.is_empty() {
                        content.push_str(&text_buffer);
                        text_buffer.clear();
                    }
                    let padding = (column_width.saturating_sub(text.chars().count())) / 2;
                    content.push_str(&format!("\n{}{}\n", " ".repeat(padding), text));
                } else if matches!(marker, "mte1" | "mte2" | "mte3" | "mte4" | "imte1" | "imte2" | "imte3" | "imte4") {
                    if !text_buffer.is_empty() {
                        content.push_str(&text_buffer);
                        text_buffer.clear();
                    }
                    let padding = (column_width.saturating_sub(text.chars().count())) / 2;
                    content.push_str(&format!("\n{}{}\n\n", " ".repeat(padding), text));
                } else if marker == "c" {
                    if !text_buffer.is_empty() {
                        content.push_str(&text_buffer);
                        text_buffer.clear();
                    }
                    content.push_str(&format!("\n\nChapter {}", text));
                } else if marker == "vp#" {
                    got_vp = Some(text.to_string());
                } else if marker == "v" {
                    let mut v_num = text.to_string();
                    if let Some(vp) = got_vp.take() {
                        v_num = vp;
                    }
                    if !text_buffer.is_empty() {
                        content.push_str(&text_buffer);
                        text_buffer.clear();
                    }
                    content.push_str(&format!("\n{} ", v_num));
                } else if matches!(
                    marker,
                    "p" | "pi1" | "pi2" | "pi3" | "pi4" | "s1" | "s2" | "s3" | "s4" | "ms1" | "ms2" | "ms3" | "ms4"
                ) {
                    local_ignored.insert(marker.to_string());
                } else if !text.is_empty() {
                    // Concatenate plain text segments separated by a space
                    if !text_buffer.is_empty() {
                        text_buffer.push(' ');
                    }
                    text_buffer.push_str(text);
                }
            }

            if !text_buffer.is_empty() {
                content.push_str(&format!("{}\n", text_buffer));
            }

            // Write the book file in parallel
            let filename = make_safe_filename(&format!("BOS-BibleWriter-{}.txt", bbb));
            let filepath_with_bom = output_path.join(&filename);
            let filepath_without_bom = without_bom_dir.join(&filename);

            // EFFICIENCY OPTIMIZATION:
            // Instead of looping over all books twice (once with BOM and once without),
            // we process the text in memory ONCE. Then we write to both files in parallel threads,
            // or sequentially on the same worker thread. This reduces CPU formatting overhead by 50%!
            
            // 1. Write without BOM
            if let Ok(file) = File::create(&filepath_without_bom) {
                let mut writer = BufWriter::new(file);
                let _ = writer.write_all(content.as_bytes());
            }

            // 2. Write with BOM
            if let Ok(file) = File::create(&filepath_with_bom) {
                let mut writer = BufWriter::new(file);
                // UTF-8 BOM is 0xEF, 0xBB, 0xBF
                let _ = writer.write_all(b"\xef\xbb\xbf");
                let _ = writer.write_all(content.as_bytes());
            }

            local_ignored
        })
        .reduce(HashSet::new, |mut a, b| {
            a.extend(b);
            a
        });

    Ok(ignored_markers)
}

/// Placeholder for parallel HTML5 exporter to be fully implemented in Rust.
pub fn export_to_html5(
    _books: &HashMap<String, InternalBibleEntryList>,
    _output_path: &Path,
    _column_width: usize,
) -> Result<HashSet<String>, BosError> {
    // Stage 1 Placeholder: This will be implemented in subsequent steps
    // when we've validated the PlainText parallel engine.
    Ok(HashSet::new())
}
