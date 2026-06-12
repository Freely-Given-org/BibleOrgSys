//! Unified Rust Parallel Export Framework using Rayon.
//!
//! This module implements high-performance multi-threaded Bible book exporters,
//! for core parallel formats (PlainText and HTML5).

use std::collections::{HashMap, HashSet};
use std::fs::{self, File};
use std::io::{Write, BufWriter};
use std::path::Path;
use crate::entry_lists::InternalBibleEntryList;
use crate::bos_markers::ExtraType;
use crate::error::BosError;
use rayon::prelude::*;
use regex::Regex;
use std::sync::LazyLock;

// Import constants from usfm_markers dependency
use usfm_markers::{
    OFTEN_IGNORED_USFM_HEADER_MARKERS, USFM_ALL_INTRODUCTION_MARKERS,
    USFM_PRECHAPTER_MARKERS,
};

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

// Struct to store accumulated HTML5 notes (thread-local / book-local)
struct Html5Globals {
    next_footnote_index: usize,
    next_endnote_index: usize,
    next_xref_index: usize,
    footnote_html5: Vec<String>,
    endnote_html5: Vec<String>,
    xref_html5: Vec<String>,
}

fn live_cv(cv: &str) -> String {
    let mut cv = cv.trim();
    if cv.len() < 3 {
        return String::new();
    }
    if cv.ends_with(':') {
        cv = &cv[..cv.len() - 1];
    }
    let mut result = format!("C{}", cv.trim().replace(':', "V"));
    for bridge_char in &['-', '–', '—'] {
        if let Some(ix) = result.find(*bridge_char) {
            result = result[..ix].to_string();
        }
    }
    format!("#{}", result)
}

fn live_local(text: &str) -> String {
    let mut t = text.replace("\\ior ", "<span class=\"outlineReferenceRange\">").replace("\\ior*", "</span>");
    static RE: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"([1-9][0-9]{0,2}):([1-9][0-9]{0,2})").unwrap());
    if let Some(captures) = RE.captures(&t) {
        let whole = captures.get(0).unwrap().as_str();
        let ch = captures.get(1).unwrap().as_str();
        let vs = captures.get(2).unwrap().as_str();
        t = t.replace(whole, &format!("<a class=\"CVReference\" href=\"#C{}V{}\">{}</a>", ch, vs, whole));
    }
    t
}

fn process_note(
    raw_contents: &str,
    globals: &mut Html5Globals,
    note_type: &str,
    _bbb: &str,
    _c: &str,
    _v: &str,
) -> String {
    let is_footnote = note_type == "footnote";
    let fn_index = if is_footnote {
        let idx = globals.next_footnote_index;
        globals.next_footnote_index += 1;
        idx
    } else {
        let idx = globals.next_endnote_index;
        globals.next_endnote_index += 1;
        idx
    };

    let marker_list = usfm_markers::get_marker_list_from_text(raw_contents, true, false);
    let mut _caller = String::new();
    let mut origin = String::new();
    let mut origin_cv = String::new();
    let mut fn_text = String::new();
    let mut fn_title = String::new();

    if !marker_list.is_empty() {
        let mut span_open = false;
        for info in marker_list {
            if span_open {
                fn_text.push_str("</span>");
                span_open = false;
            }
            match info.marker {
                None => {
                    _caller = info.text.to_string();
                }
                Some("fr") => {
                    origin = info.text.to_string();
                    origin_cv = origin.trim().to_string();
                    if origin_cv.ends_with(':') || origin_cv.ends_with('.') {
                        origin_cv.pop();
                    }
                    origin_cv = origin_cv.trim().to_string();
                }
                Some("ft") => {
                    fn_text.push_str(info.text);
                    fn_title.push_str(info.text);
                }
                Some("fk") => {
                    fn_text.push_str(&format!("<span class=\"{}Keyword\">", note_type));
                    fn_text.push_str(info.text);
                    fn_title.push_str(info.text);
                    span_open = true;
                }
                Some("fq") => {
                    fn_text.push_str(&format!("<span class=\"{}TranslationQuotation\">", note_type));
                    fn_text.push_str(info.text);
                    fn_title.push_str(info.text);
                    span_open = true;
                }
                Some("fqa") => {
                    fn_text.push_str(&format!("<span class=\"{}AlternateTranslation\">", note_type));
                    fn_text.push_str(info.text);
                    fn_title.push_str(info.text);
                    span_open = true;
                }
                Some("fl") => {
                    fn_text.push_str(&format!("<span class=\"{}Label\">", note_type));
                    fn_text.push_str(info.text);
                    fn_title.push_str(info.text);
                    span_open = true;
                }
                Some(_) => {
                    fn_text.push_str(info.text);
                    fn_title.push_str(info.text);
                }
            }
        }
        if span_open {
            fn_text.push_str("</span>");
        }
    } else {
        let parts: Vec<&str> = raw_contents.splitn(2, ' ').collect();
        if parts.len() == 2 {
            _caller = parts[0].to_string();
            fn_text = parts[1].to_string();
            fn_title = parts[1].to_string();
        } else {
            fn_text = raw_contents.to_string();
            fn_title = raw_contents.to_string();
        }
    }

    let prefix = if is_footnote { "FNote" } else { "ENote" };
    let id_name = format!("{}{}", prefix, fn_index);
    let note_html5 = format!(
        "<a class=\"{}LinkSymbol\" title=\"{}\" href=\"#{}\">[fn]</a>",
        note_type, fn_title.replace('"', "&quot;").replace('<', "&lt;").replace('>', "&gt;"), id_name
    );

    let mut end_html5 = format!("<p id=\"{}\" class=\"{}\">", id_name, note_type);
    if !origin_cv.is_empty() {
        end_html5.push_str(&format!(
            "<a class=\"{}Origin\" title=\"Go back up to {} in the text\" href=\"{}\">{}</a> ",
            note_type, origin_cv, live_cv(&origin_cv), origin
        ));
    }
    end_html5.push_str(&format!(
        "<span class=\"{}Entry\">{}</span>",
        note_type, fn_text
    ));
    end_html5.push_str("</p>");

    if is_footnote {
        globals.footnote_html5.push(end_html5);
    } else {
        globals.endnote_html5.push(end_html5);
    }

    note_html5
}

fn process_xref(
    raw_contents: &str,
    globals: &mut Html5Globals,
    _bbb: &str,
    c: &str,
    v: &str,
) -> String {
    let xref_index = globals.next_xref_index;
    globals.next_xref_index += 1;

    let marker_list = usfm_markers::get_marker_list_from_text(raw_contents, true, false);
    let mut _caller = String::new();
    let mut origin_cv = String::new();
    let mut xref_text = String::new();

    if !marker_list.is_empty() {
        for info in marker_list {
            match info.marker {
                None => {
                    _caller = info.text.to_string();
                }
                Some("xo") => {
                    origin_cv = info.text.trim().to_string();
                    if origin_cv.ends_with(':') || origin_cv.ends_with('.') {
                        origin_cv.pop();
                    }
                    origin_cv = origin_cv.trim().to_string();
                }
                Some("xt") => {
                    xref_text.push_str(info.text);
                }
                Some(_) => {
                    xref_text.push_str(info.text);
                }
            }
        }
    } else {
        if raw_contents.starts_with("+ ") || raw_contents.starts_with("- ") {
            _caller = raw_contents[..1].to_string();
            xref_text = raw_contents[2..].trim().to_string();
        } else {
            xref_text = raw_contents.trim().to_string();
        }
    }

    let xref_html5 = format!(
        "<a class=\"xrefLinkSymbol\" title=\"{}\" href=\"#XRef{}\">[xr]</a>",
        xref_text.replace('"', "&quot;").replace('<', "&lt;").replace('>', "&gt;"), xref_index
    );

    let mut end_html5 = format!("<p id=\"XRef{}\" class=\"xref\">", xref_index);
    let mut final_origin_cv = origin_cv;
    if final_origin_cv.is_empty() {
        final_origin_cv = format!("{}:{}", c, v);
    }
    if !final_origin_cv.is_empty() {
        end_html5.push_str(&format!(
            "<a class=\"xrefOrigin\" title=\"Go back up to {} in the text\" href=\"{}\">{}</a> ",
            final_origin_cv, live_cv(&final_origin_cv), final_origin_cv
        ));
    }
    end_html5.push_str(&format!(
        "<span class=\"xrefEntry\">{}</span>",
        xref_text
    ));
    end_html5.push_str("</p>");

    globals.xref_html5.push(end_html5);

    xref_html5
}

fn format_html_verse_text(
    bbb: &str,
    c: &str,
    v: &str,
    given_text: &str,
    extras: Option<&crate::entry_extras::InternalBibleExtraList>,
    globals: &mut Html5Globals,
) -> String {
    let mut adj_text = given_text.to_string();
    let mut offset: isize = 0;
    
    if let Some(extras_list) = extras {
        for extra in extras_list.iter() {
            let extra_type = extra.extra_type();
            let extra_index = extra.index();
            let extra_text = extra.text();

            let adj_index = (extra_index as isize - offset) as usize;
            
            // Generate HTML for the extra
            let formatted_extra = match extra_type {
                ExtraType::Footnote => process_note(extra_text, globals, "footnote", bbb, c, v),
                ExtraType::Endnote => process_note(extra_text, globals, "endnote", bbb, c, v),
                ExtraType::CrossRef => process_xref(extra_text, globals, bbb, c, v),
                ExtraType::Figure => {
                    println!("toHTML5: figure not handled yet at {} {}:{}", bbb, c, v);
                    String::new()
                }
                ExtraType::Strongs => String::new(),
                ExtraType::Semantic => String::new(),
                ExtraType::VersePublished => format!("\\vp {}\\vp*", extra_text),
                ExtraType::WordWithAttributes => String::new(),
            };
            
            // Insert it
            if adj_index <= adj_text.len() {
                adj_text.insert_str(adj_index, &formatted_extra);
                offset -= formatted_extra.len() as isize;
            }
        }
    }

    let mut text = adj_text;
    text = text.replace("\\ior ", "<span class=\"outlineReferenceRange\">").replace("\\ior*", "</span>");
    text = text.replace("\\bk ", "<span class=\"bookName\">").replace("\\bk*", "</span>");
    text = text.replace("\\+bk ", "<span class=\"bookName\">").replace("\\+bk*", "</span>");
    text = text.replace("\\iqt ", "<span class=\"introductionQuotedText\">").replace("\\iqt*", "</span>");

    text = text.replace("\\add ", "<span class=\"addedText\">").replace("\\add*", "</span>");
    text = text.replace("\\+add ", "<span class=\"addedText\">").replace("\\+add*", "</span>");
    text = text.replace("\\nd ", "<span class=\"divineName\">").replace("\\nd*", "</span>");
    text = text.replace("\\+nd ", "<span class=\"divineName\">").replace("\\+nd*", "</span>");
    text = text.replace("\\wj ", "<span class=\"wordsOfJesus\">").replace("\\wj*", "</span>");
    text = text.replace("\\sig ", "<span class=\"signature\">").replace("\\sig*", "</span>");
    text = text.replace("\\+sig ", "<span class=\"signature\">").replace("\\+sig*", "</span>");
    if bbb == "GLS" {
        text = text.replace("\\k ", "<span class=\"glossaryKeyword\">").replace("\\k*", "</span>");
    } else {
        text = text.replace("\\k ", "<span class=\"keyword\">").replace("\\k*", "</span>");
    }
    text = text.replace("\\w ", "<span class=\"wordlistEntry\">").replace("\\w*", "</span>");
    text = text.replace("\\+w ", "<span class=\"wordlistEntry\">").replace("\\+w*", "</span>");
    text = text.replace("\\rq ", "<span class=\"quotationReference\">").replace("\\rq*", "</span>");
    text = text.replace("\\qs ", "<span class=\"Selah\">").replace("\\qs*", "</span>");
    text = text.replace("\\+qs ", "<span class=\"Selah\">").replace("\\+qs*", "</span>");
    text = text.replace("\\ca ", "<span class=\"alternativeChapterNumber\">(").replace("\\ca*", ")</span>");
    text = text.replace("\\va ", "<span class=\"alternativeVerseNumber\">(").replace("\\va*", ")</span>");

    // Direct formatting
    text = text.replace("\\bdit ", "<span class=\"boldItalic\">").replace("\\bdit*", "</span>");
    text = text.replace("\\+bdit ", "<span class=\"boldItalic\">").replace("\\+bdit*", "</span>");
    text = text.replace("\\it ", "<span class=\"italic\">").replace("\\it*", "</span>");
    text = text.replace("\\+it ", "<span class=\"italic\">").replace("\\+it*", "</span>");
    text = text.replace("\\bd ", "<span class=\"bold\">").replace("\\bd*", "</span>");
    text = text.replace("\\+bd ", "<span class=\"bold\">").replace("\\+bd*", "</span>");
    text = text.replace("\\sc ", "<span class=\"smallCaps\">").replace("\\sc*", "</span>");
    text = text.replace("\\+sc ", "<span class=\"smallCaps\">").replace("\\+sc*", "</span>");

    text
}

fn get_ip_html_class(marker: &str) -> &'static str {
    match marker {
        "ip" => "introductionParagraph",
        "ipi" => "introductionParagraphIndented",
        "ipq" => "introductionQuoteParagraph",
        "ipr" => "introductionRightAlignedParagraph",
        "im" => "introductionFlushLeftParagraph",
        "imi" => "introductionIndentedFlushLeftParagraph",
        "imq" => "introductionFlushLeftQuoteParagraph",
        "iq1" => "introductionPoetryParagraph1",
        "iq2" => "introductionPoetryParagraph2",
        "iq3" => "introductionPoetryParagraph3",
        "iq4" => "introductionPoetryParagraph4",
        "iex" => "introductionExplanation",
        _ => "introductionParagraph",
    }
}

fn get_pq_html_class(marker: &str) -> &'static str {
    match marker {
        "p" => "proseParagraph",
        "m" => "flushLeftParagraph",
        "pmo" => "embeddedOpeningParagraph",
        "pm" => "embeddedParagraph",
        "pmc" => "embeddedClosingParagraph",
        "pmr" => "embeddedRefrainParagraph",
        "pi1" => "indentedProseParagraph1",
        "pi2" => "indentedProseParagraph2",
        "pi3" => "indentedProseParagraph3",
        "pi4" => "indentedProseParagraph4",
        "mi" => "indentedFlushLeftParagraph",
        "cls" => "closureParagraph",
        "pc" => "centeredProseParagraph",
        "pr" => "rightAlignedProseParagraph",
        "ph1" => "hangingProseParagraph1",
        "ph2" => "hangingProseParagraph2",
        "ph3" => "hangingProseParagraph3",
        "ph4" => "hangingProseParagraph4",
        "q1" => "poetryParagraph1",
        "q2" => "poetryParagraph2",
        "q3" => "poetryParagraph3",
        "q4" => "poetryParagraph4",
        "qr" => "rightAlignedPoetryParagraph",
        "qc" => "centeredPoetryParagraph",
        "qm1" => "embeddedPoetryParagraph1",
        "qm2" => "embeddedPoetryParagraph2",
        "qm3" => "embeddedPoetryParagraph3",
        "qm4" => "embeddedPoetryParagraph4",
        _ => "proseParagraph",
    }
}

fn write_header(
    writer: &mut crate::ml_writer::MlWriter,
    my_bbb: &str,
    bible_name: &str,
    book_order: &[String],
    book_names: &HashMap<String, String>,
    filename_dict: &HashMap<String, String>,
    control_dict: &HashMap<String, String>,
) -> Result<(), Box<dyn std::error::Error>> {
    writer.write_line_open("head", None, None)?;
    writer.write_line_text("<meta http-equiv=\"Content-Type\" content=\"text/html;charset=utf-8\">", Some(true))?;
    writer.write_line_text("<link rel=\"stylesheet\" type=\"text/css\" href=\"BibleBook.css\">", Some(true))?;
    if let Some(title) = control_dict.get("HTML5Title") {
        if !title.is_empty() {
            writer.write_line_open_close("title", title, None)?;
        }
    }
    writer.write_line_close("head")?;

    writer.write_line_open("body", None, None)?;

    writer.write_line_open("header", None, None)?;
    if my_bbb == "home" {
        writer.write_line_open_close("p", "Home", Some(&[("class", "homeNonlink")]))?;
    } else {
        writer.write_line_open_close("a", "Home", Some(&[("href", "index.html"), ("class", "homeLink")]))?;
    }
    if my_bbb == "about" {
        writer.write_line_open_close("p", "About", Some(&[("class", "homeNonlink")]))?;
    } else {
        writer.write_line_open_close("a", "About", Some(&[("href", "about.html"), ("class", "aboutLink")]))?;
    }

    writer.write_line_open_close("h1", bible_name, Some(&[("class", "mainHeader")]))?;

    if book_order.contains(&my_bbb.to_string()) {
        if let Some(ix) = book_order.iter().position(|r| r == my_bbb) {
            if ix > 0 {
                if let Some(prev_filename) = filename_dict.get(&book_order[ix - 1]) {
                    writer.write_line_open_close("a", "Previous book", Some(&[("href", prev_filename), ("class", "bookNav")]))?;
                }
            }
            writer.write_line_open_close("a", "Book start", Some(&[("href", "#C1V1"), ("class", "bookNav")]))?;
            if ix < book_order.len() - 1 {
                if let Some(next_filename) = filename_dict.get(&book_order[ix + 1]) {
                    writer.write_line_open_close("a", "Next book", Some(&[("href", next_filename), ("class", "bookNav")]))?;
                }
            }
        }
    }
    writer.write_line_close("header")?;

    // Create the nav bar for books
    writer.write_line_open("nav", None, None)?;
    writer.write_line_open("ul", None, None)?;
    for bbb in book_order {
        let bk_name = book_names.get(bbb).map(|s| s.as_str()).unwrap_or(bbb.as_str());
        if bbb == my_bbb {
            writer.write_line_text(&format!("<li class=\"bookNameEntry\"><span class=\"currentBookName\">{}</span></li>", bk_name), Some(true))?;
        } else {
            let filename = filename_dict.get(bbb).map(|s| s.as_str()).unwrap_or("");
            writer.write_line_text(&format!("<li class=\"bookNameEntry\"><a class=\"bookNameLink\" href=\"{}\">{}</a></li>", filename, bk_name), Some(true))?;
        }
    }
    writer.write_line_close("ul")?;
    writer.write_line_close("nav")?;

    Ok(())
}

fn write_footer(
    writer: &mut crate::ml_writer::MlWriter,
    program_name: &str,
    program_version: &str,
    today_str: &str,
) -> Result<(), Box<dyn std::error::Error>> {
    writer.write_line_open("footer", None, None)?;
    writer.write_line_open("p", Some(&[("class", "footerLine")]), None)?;
    writer.write_line_open("a", Some(&[("href", "http://www.w3.org/html/logo/")]), None)?;
    writer.write_line_text("<img src=\"http://www.w3.org/html/logo/badge/html5-badge-h-css3-semantics.png\" width=\"165\" height=\"64\" alt=\"HTML5 Powered with CSS3 / Styling, and Semantics\" title=\"HTML5 Powered with CSS3 / Styling, and Semantics\">", Some(true))?;
    writer.write_line_close("a")?;
    writer.write_line_text(&format!("This page automatically created {} by {} v{}", today_str, program_name, program_version), None)?;
    writer.write_line_close("p")?;
    writer.write_line_close("footer")?;
    writer.write_line_close("body")?;

    Ok(())
}

fn write_end_notes(
    writer: &mut crate::ml_writer::MlWriter,
    globals: &Html5Globals,
) -> Result<(), Box<dyn std::error::Error>> {
    if !globals.footnote_html5.is_empty() || !globals.endnote_html5.is_empty() || !globals.xref_html5.is_empty() {
        writer.write_line_open("div", None, None)?;
        
        if !globals.footnote_html5.is_empty() {
            writer.write_line_open_close("h3", "Footnotes", Some(&[("class", "footnotesHeader")]))?;
            writer.write_line_open("div", Some(&[("class", "footnoteLine")]), None)?;
            for line in &globals.footnote_html5 {
                writer.write_line_text(line, Some(true))?;
            }
            writer.write_line_close("div")?;
        }
        
        if !globals.endnote_html5.is_empty() {
            writer.write_line_open_close("h3", "Endnotes", Some(&[("class", "endnotesHeader")]))?;
            writer.write_line_open("div", Some(&[("class", "endnoteLine")]), None)?;
            for line in &globals.endnote_html5 {
                writer.write_line_text(line, Some(true))?;
            }
            writer.write_line_close("div")?;
        }
        
        if !globals.xref_html5.is_empty() {
            writer.write_line_open_close("h3", "Cross References", Some(&[("class", "xrefsHeader")]))?;
            writer.write_line_open("div", Some(&[("class", "xrefSection")]), None)?;
            for line in &globals.xref_html5 {
                writer.write_line_text(line, Some(true))?;
            }
            writer.write_line_close("div")?;
        }
        
        writer.write_line_close("div")?; // endNotes
    }
    Ok(())
}

/// Core parallel HTML5 book exporter.
pub fn export_to_html5(
    books: &HashMap<String, InternalBibleEntryList>,
    output_path: &Path,
    bible_name: &str,
    book_order: &[String],
    book_names: &HashMap<String, String>,
    filename_dict: &HashMap<String, String>,
    control_dict: &HashMap<String, String>,
    program_name: &str,
    program_version: &str,
    today_str: &str,
    xref_callback: Option<&(dyn Fn(&str) -> String + Sync)>,
) -> Result<(HashSet<String>, HashSet<String>), BosError> {
    fs::create_dir_all(output_path).map_err(BosError::Io)?;

    let results: Vec<(HashSet<String>, HashSet<String>)> = books
        .par_iter()
        .map(|(bbb, entry_list)| {
            let mut local_ignored = HashSet::new();
            let mut local_unhandled = HashSet::new();

            let filename = filename_dict.get(bbb).cloned().unwrap_or_else(|| format!("{}.html", bbb));
            let filepath = output_path.join(&filename);

            let mut writer = crate::ml_writer::MlWriter::new(&filepath, crate::ml_writer::MlOutputType::Html);
            writer.set_human_readable(crate::ml_writer::HumanReadable::All, 2);
            
            if let Err(e) = writer.start('\n', true, false) {
                println!("Error starting MlWriter for book {}: {:?}", bbb, e);
                return (local_ignored, local_unhandled);
            }
            
            if let Err(e) = writer.write_line_text("<!DOCTYPE html>", Some(true)) {
                println!("Error writing doctype for book {}: {:?}", bbb, e);
                return (local_ignored, local_unhandled);
            }
            
            if let Err(e) = writer.write_line_open("html", None, None) {
                println!("Error opening html tag for book {}: {:?}", bbb, e);
                return (local_ignored, local_unhandled);
            }

            if let Err(e) = write_header(&mut writer, bbb, bible_name, book_order, book_names, filename_dict, control_dict) {
                println!("Error writing header for book {}: {:?}", bbb, e);
                return (local_ignored, local_unhandled);
            }

            let mut globals = Html5Globals {
                next_footnote_index: 0,
                next_endnote_index: 0,
                next_xref_index: 0,
                footnote_html5: Vec::new(),
                endnote_html5: Vec::new(),
                xref_html5: Vec::new(),
            };

            let mut have_open_section = false;
            let mut have_open_paragraph = false;
            let mut have_open_list_item = false;
            let mut have_open_verse = false;
            let mut have_open_list = HashMap::new();
            let mut got_vp: Option<String> = None;
            let mut c = "-1".to_string();
            let mut v = "-1".to_string();

            for entry in entry_list.iter() {
                let marker = entry.marker();
                let text = entry.adjusted_text().unwrap_or("");
                let extras = entry.extras();
                let has_extras = entry.has_extras();

                if marker.contains('¬') || crate::bos_markers::custom_nesting::is_custom_nesting(marker) || marker == "v=" {
                    continue;
                }

                if USFM_PRECHAPTER_MARKERS.contains(&marker) {
                    v = (v.parse::<i32>().unwrap_or(0) + 1).to_string();
                }

                if OFTEN_IGNORED_USFM_HEADER_MARKERS.contains(&marker) || marker == "ie" {
                    local_ignored.insert(marker.to_string());
                } else if matches!(marker, "mt1" | "mt2" | "mt3" | "mt4" | "imt1" | "imt2" | "imt3" | "imt4") {
                    if have_open_paragraph {
                        let _ = writer.write_line_close("p");
                        have_open_paragraph = false;
                    }
                    let t_class = if marker.starts_with("mt") { "mainTitle" } else { "introductionMainTitle" };
                    let marker_char = marker.chars().nth(2).unwrap_or('1');
                    let class_name = format!("{}{}", t_class, marker_char);
                    if !text.is_empty() {
                        let _ = writer.write_line_open_close("h1", text, Some(&[("class", &class_name)]));
                    }
                } else if matches!(marker, "is1" | "is2" | "is3" | "is4") {
                    if have_open_paragraph {
                        let _ = writer.write_line_close("p");
                        have_open_paragraph = false;
                    }
                    if !text.is_empty() {
                        let marker_char = marker.chars().nth(2).unwrap_or('1');
                        let class_name = format!("introductionSectionHeading{}", marker_char);
                        let _ = writer.write_line_open_close("h3", text, Some(&[("class", &class_name)]));
                    }
                } else if matches!(marker, "ip" | "ipi" | "ipq" | "ipr" | "im" | "imi" | "imq" | "iq1" | "iq2" | "iq3" | "iq4" | "iex") {
                    if have_open_paragraph {
                        let _ = writer.write_line_close("p");
                        have_open_paragraph = false;
                    }
                    if !have_open_section {
                        let _ = writer.write_line_open("section", Some(&[("class", "regularSection")]), None);
                        have_open_section = true;
                    }
                    if !text.is_empty() || has_extras {
                        let formatted = format_html_verse_text(bbb, &c, &v, text, extras, &mut globals);
                        let class_name = get_ip_html_class(marker);
                        let _ = writer.write_line_open_close("p", &formatted, Some(&[("class", class_name)]));
                    }
                } else if marker == "iot" {
                    if have_open_paragraph {
                        let _ = writer.write_line_close("p");
                        have_open_paragraph = false;
                    }
                    if !text.is_empty() {
                        let _ = writer.write_line_open_close("h3", text, Some(&[("class", "introductionOutlineTitle")]));
                    }
                } else if matches!(marker, "io1" | "io2" | "io3" | "io4") {
                    if !text.is_empty() {
                        let marker_char = marker.chars().nth(2).unwrap_or('1');
                        let class_name = format!("introductionOutlineEntry{}", marker_char);
                        let _ = writer.write_line_open_close("p", &live_local(text), Some(&[("class", &class_name)]));
                    }
                } else if marker == "ib" {
                    let _ = writer.write_line_open_close("p", " ", Some(&[("class", "introductionBlankParagraph")]));
                } else if marker == "periph" {
                    if have_open_paragraph {
                        let _ = writer.write_line_close("p");
                        have_open_paragraph = false;
                    }
                    let _ = writer.write_line_open_close("p", " ", Some(&[("class", "peripheralContent")]));
                } else if matches!(marker, "mte1" | "mte2" | "mte3" | "mte4" | "imte1" | "imte2" | "imte3" | "imte4") {
                    if have_open_paragraph {
                        let _ = writer.write_line_close("p");
                        have_open_paragraph = false;
                    }
                    if !text.is_empty() {
                        let marker_char = marker.chars().nth(3).unwrap_or('1');
                        let class_name = format!("endTitle{}", marker_char);
                        let _ = writer.write_line_open_close("h1", text, Some(&[("class", &class_name)]));
                    }
                } else if marker == "c" {
                    v = "0".to_string();
                    if have_open_verse {
                        let _ = writer.write_line_close("span");
                        have_open_verse = false;
                    }
                    let _ = writer.write_line_open_close("span", " ", Some(&[("class", "chapterStart"), ("id", &format!("CS{}", text))]));
                } else if marker == "cp" {
                    local_ignored.insert(marker.to_string());
                } else if marker == "c#" {
                    c = text.to_string();
                    if !have_open_paragraph {
                        let _ = writer.write_line_open("p", Some(&[("class", "unknownParagraph")]), None);
                        have_open_paragraph = true;
                    }
                    let _ = writer.write_line_open_close("span", text, Some(&[("class", "chapterNumber"), ("id", &format!("CT{}", text))]));
                    let _ = writer.write_line_open_close("span", "&nbsp;", Some(&[("class", "chapterNumberPostspace")]));
                } else if marker == "vp#" {
                    got_vp = Some(text.to_string());
                } else if marker == "v" {
                    if have_open_verse {
                        let _ = writer.write_line_close("span");
                    }
                    v = text.to_string();
                    let mut display_v = v.clone();
                    if let Some(vp) = got_vp.take() {
                        display_v = vp;
                    }
                    let _ = writer.write_line_open("span", Some(&[("class", "verse"), ("id", &format!("C{}V{}", c, v))]), None);
                    have_open_verse = true;
                    if display_v == "1" {
                        let _ = writer.write_line_open_close("span", " ", Some(&[("class", "verseOnePrespace")]));
                        let _ = writer.write_line_open_close("span", &display_v, Some(&[("class", "verseOneNumber")]));
                        let _ = writer.write_line_open_close("span", "&nbsp;", Some(&[("class", "verseOnePostspace")]));
                    } else if !display_v.is_empty() {
                        let _ = writer.write_line_open_close("span", " ", Some(&[("class", "verseNumberPrespace")]));
                        let _ = writer.write_line_open_close("span", &display_v, Some(&[("class", "verseNumber")]));
                        let _ = writer.write_line_open_close("span", "&nbsp;", Some(&[("class", "verseNumberPostspace")]));
                    }
                } else if matches!(marker, "ms1" | "ms2" | "ms3" | "ms4") {
                    if have_open_verse {
                        let _ = writer.write_line_close("span");
                        have_open_verse = false;
                    }
                    if have_open_paragraph {
                        let _ = writer.write_line_close("p");
                        have_open_paragraph = false;
                    }
                    if !text.is_empty() {
                        let marker_char = marker.chars().nth(2).unwrap_or('1');
                        let class_name = format!("majorSectionHeading{}", marker_char);
                        let _ = writer.write_line_open_close("h2", text, Some(&[("class", &class_name)]));
                    }
                } else if matches!(marker, "s1" | "s2" | "s3" | "s4") {
                    if have_open_verse {
                        let _ = writer.write_line_close("span");
                        have_open_verse = false;
                    }
                    if have_open_paragraph {
                        let _ = writer.write_line_close("p");
                        have_open_paragraph = false;
                    }
                    if marker == "s1" {
                        if have_open_section {
                            let _ = writer.write_line_close("section");
                        }
                        let _ = writer.write_line_open("section", Some(&[("class", "regularSection")]), None);
                        have_open_section = true;
                    }
                    if !text.is_empty() || has_extras {
                        let formatted = format_html_verse_text(bbb, &c, &v, text, extras, &mut globals);
                        let marker_char = marker.chars().nth(1).unwrap_or('1');
                        let class_name = format!("sectionHeading{}", marker_char);
                        let _ = writer.write_line_open_close("h3", &formatted, Some(&[("class", &class_name)]));
                    }
                } else if matches!(marker, "r" | "sr" | "mr") {
                    if have_open_verse {
                        let _ = writer.write_line_close("span");
                        have_open_verse = false;
                    }
                    if have_open_paragraph {
                        let _ = writer.write_line_close("p");
                        have_open_paragraph = false;
                    }
                    if !have_open_section {
                        let _ = writer.write_line_open("section", Some(&[("class", "regularSection")]), None);
                        have_open_section = true;
                    }
                    let r_class = match marker {
                        "r" => "sectionCrossReference",
                        "sr" => "sectionReferenceRange",
                        "mr" => "majorSectionReferenceRange",
                        _ => "sectionCrossReference",
                    };
                    if !text.is_empty() {
                        let resolved = if let Some(cb) = xref_callback {
                            cb(text)
                        } else {
                            text.to_string()
                        };
                        let _ = writer.write_line_open_close("p", &resolved, Some(&[("class", r_class)]));
                    }
                } else if marker == "d" {
                    if !text.is_empty() || has_extras {
                        let formatted = format_html_verse_text(bbb, &c, &v, text, extras, &mut globals);
                        let _ = writer.write_line_open_close("p", &formatted, Some(&[("class", "descriptiveTitle")]));
                    }
                } else if marker == "sp" {
                    if !text.is_empty() {
                        let _ = writer.write_line_open_close("p", text, Some(&[("class", "speaker")]));
                    }
                } else if matches!(
                    marker,
                    "p" | "m" | "pmo" | "pm" | "pmc" | "pmr" | "pi1" | "pi2" | "pi3" | "pi4" | "mi" | "cls" | "pc" | "pr" | "ph1" | "ph2" | "ph3" | "ph4" |
                    "q1" | "q2" | "q3" | "q4" | "qr" | "qc" | "qm1" | "qm2" | "qm3" | "qm4"
                ) {
                    if have_open_list_item {
                        let _ = writer.write_line_close("span");
                        have_open_list_item = false;
                    }
                    for lx in &["4", "3", "2", "1"] {
                        if let Some(true) = have_open_list.get(*lx) {
                            let _ = writer.write_line_close("p");
                            have_open_list.insert(lx.to_string(), false);
                        }
                    }
                    if have_open_verse {
                        let _ = writer.write_line_close("span");
                        have_open_verse = false;
                    }
                    if have_open_paragraph {
                        let _ = writer.write_line_close("p");
                    }
                    let class_name = get_pq_html_class(marker);
                    let _ = writer.write_line_open("p", Some(&[("class", class_name)]), None);
                    have_open_paragraph = true;
                } else if matches!(marker, "li1" | "li2" | "li3" | "li4" | "ili1" | "ili2" | "ili3" | "ili4") {
                    let is_li = marker.starts_with("li");
                    let m_idx = if is_li { 2 } else { 3 };
                    let m = marker.chars().nth(m_idx).unwrap_or('1').to_string();
                    let p_class = if is_li { format!("list{}", m) } else { format!("introductionList{}", m) };
                    let i_class = if is_li { format!("listItem{}", m) } else { format!("introductionListItem{}", m) };
                    
                    if !have_open_list.get(&m).copied().unwrap_or(false) {
                        let _ = writer.write_line_open("p", Some(&[("class", &p_class)]), None);
                        have_open_list.insert(m.clone(), true);
                    }
                    if is_li {
                        let _ = writer.write_line_open("span", Some(&[("class", &i_class)]), None);
                        have_open_list_item = true;
                    } else if !text.is_empty() {
                        let formatted = format_html_verse_text(bbb, &c, &v, text, extras, &mut globals);
                        let _ = writer.write_line_open_close("span", &formatted, Some(&[("class", &i_class)]));
                    }
                } else if marker == "b" {
                    if have_open_verse {
                        let _ = writer.write_line_close("span");
                        have_open_verse = false;
                    }
                    if have_open_paragraph {
                        let _ = writer.write_line_close("p");
                        have_open_paragraph = false;
                    }
                    let _ = writer.write_line_open_close("p", " ", Some(&[("class", "blankParagraph")]));
                } else if matches!(marker, "v~" | "p~") {
                    if !have_open_paragraph {
                        let _ = writer.write_line_open("p", Some(&[("class", "unknownParagraph")]), None);
                        have_open_paragraph = true;
                    }
                    if !have_open_verse {
                        let _ = writer.write_line_open("span", Some(&[("class", "verse")]), None);
                        have_open_verse = true;
                    }
                    if !text.is_empty() || has_extras {
                        let formatted = format_html_verse_text(bbb, &c, &v, text, extras, &mut globals);
                        let _ = writer.write_line_open_close("span", &formatted, Some(&[("class", "verseText")]));
                    }
                } else if matches!(marker, "nb" | "cl" | "vp#") {
                    local_ignored.insert(marker.to_string());
                } else {
                    local_unhandled.insert(marker.to_string());
                }
            }

            if have_open_list_item {
                let _ = writer.write_line_close("span");
            }
            for lx in &["4", "3", "2", "1"] {
                if let Some(true) = have_open_list.get(*lx) {
                    let _ = writer.write_line_close("p");
                }
            }
            if have_open_verse {
                let _ = writer.write_line_close("span");
            }
            if have_open_paragraph {
                let _ = writer.write_line_close("p");
            }
            if have_open_section {
                let _ = writer.write_line_close("section");
            }

            let _ = write_end_notes(&mut writer, &globals);
            let _ = write_footer(&mut writer, program_name, program_version, today_str);

            let _ = writer.write_line_close("html");
            let _ = writer.close(true);

            (local_ignored, local_unhandled)
        })
        .collect();

    // Reduce vectors into the final two sets
    let mut final_ignored = HashSet::new();
    let mut final_unhandled = HashSet::new();
    for (ignored, unhandled) in results {
        final_ignored.extend(ignored);
        final_unhandled.extend(unhandled);
    }

    Ok((final_ignored, final_unhandled))
}
