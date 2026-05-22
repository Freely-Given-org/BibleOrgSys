//! OSIS XML Bible format parser with parallel processing support.

use std::fs::File;
use std::io::Read;
use std::path::Path;
use std::collections::HashMap;
use quick_xml::Reader;
use quick_xml::events::Event;
use quick_xml::events::attributes::Attributes;
use crate::markers::{ExtraType, normalize_marker};
use crate::error::BosError;
use rayon::prelude::*;

/// Results of OSIS parsing.
pub struct OsisParseResults {
    pub metadata: HashMap<String, String>,
    pub books: HashMap<String, Vec<(String, String)>>,
}

#[derive(Debug, Default)]
struct ParserState {
    current_bbb: Option<String>,
    current_c: Option<String>,
    current_v: Option<String>,
    in_header: bool,
    header_metadata: HashMap<String, String>,
    raw_lines: Vec<(String, String)>,
    current_marker: Option<String>,
    current_text: String,
    tag_stack: Vec<String>,
    lg_level: Option<String>,
}

pub fn parse_osis<P: AsRef<Path>>(path: P) -> Result<OsisParseResults, BosError> {
    let mut file = File::open(&path).map_err(BosError::Io)?;
    let mut content = String::new();
    file.read_to_string(&mut content).map_err(BosError::Io)?;

    // 1. Find book boundaries for parallel processing
    let book_slices = find_book_slices(&content);

    // 2. Parse header metadata
    let metadata = parse_header(&content);

    // 3. Parse books in parallel
    let books: HashMap<String, Vec<(String, String)>> = book_slices.par_iter()
        .map(|(bbb, slice)| {
            let lines = parse_osis_slice(slice, Some(bbb));
            (bbb.clone(), lines)
        })
        .collect();

    // 4. Fallback to single-threaded if no book divs found
    if books.is_empty() {
        let lines_map = parse_osis_single_threaded(&content);
        return Ok(OsisParseResults {
            metadata,
            books: lines_map,
        });
    }

    Ok(OsisParseResults {
        metadata,
        books,
    })
}

fn find_book_slices(content: &str) -> Vec<(String, &str)> {
    let mut slices = Vec::new();
    let mut start_indices = Vec::new();
    
    let mut pos = 0;
    while let Some(start) = content[pos..].find("<div") {
        let abs_start = pos + start;
        let end_tag = content[abs_start..].find('>').map(|i| abs_start + i);
        if let Some(abs_tag_end) = end_tag {
            let tag_content = &content[abs_start..abs_tag_end];
            if tag_content.contains("type=\"book\"") || tag_content.contains("type='book'") {
                if let Some(id_pos) = tag_content.find("osisID=\"") {
                    let id_start = id_pos + 8;
                    if let Some(id_len) = tag_content[id_start..].find('"') {
                        let osis_id = &tag_content[id_start..id_start + id_len];
                        if let Ok(bbb) = bos_books_codes::osis_book_code_to_bos_book_code(osis_id, true) {
                            start_indices.push((bbb.to_string(), abs_start));
                        }
                    }
                }
            }
        }
        pos = abs_start + 4;
    }

    for i in 0..start_indices.len() {
        let (bbb, start) = &start_indices[i];
        let end = if i + 1 < start_indices.len() {
            start_indices[i + 1].1
        } else {
            content.len()
        };
        slices.push((bbb.clone(), &content[*start..end]));
    }

    slices
}

fn parse_header(content: &str) -> HashMap<String, String> {
    let mut metadata = HashMap::new();
    if let Some(start) = content.find("<header>") {
        if let Some(end) = content[start..].find("</header>") {
            let header_content = &content[start..start + end + 9];
            let mut reader = Reader::from_str(header_content);
            reader.config_mut().trim_text(true);
            let mut buf = Vec::new();
            let mut current_tag = String::new();
            
            loop {
                match reader.read_event_into(&mut buf) {
                    Ok(Event::Start(e)) => {
                        current_tag = String::from_utf8_lossy(e.name().as_ref()).to_string();
                    }
                    Ok(Event::Text(e)) => {
                        let text = e.unescape().map(|c| c.into_owned()).unwrap_or_default();
                        if !current_tag.is_empty() {
                            metadata.insert(current_tag.clone(), text);
                        }
                    }
                    Ok(Event::End(_)) => {
                        current_tag.clear();
                    }
                    Ok(Event::Eof) => break,
                    _ => {}
                }
                buf.clear();
            }
        }
    }
    metadata
}

fn parse_osis_slice(slice: &str, initial_bbb: Option<&str>) -> Vec<(String, String)> {
    let mut reader = Reader::from_str(slice);
    reader.config_mut().trim_text(true);
    let mut state = ParserState::default();
    if let Some(bbb) = initial_bbb {
        state.current_bbb = Some(bbb.to_string());
    }
    let mut buf = Vec::new();

    loop {
        match reader.read_event_into(&mut buf) {
            Ok(Event::Start(e)) => {
                let name = String::from_utf8_lossy(e.name().as_ref()).to_string();
                state.tag_stack.push(name.clone());
                match name.as_str() {
                    "div" => handle_div_start(&mut state, e.attributes()),
                    "chapter" => handle_chapter_start(&mut state, e.attributes()),
                    "verse" => handle_verse_start(&mut state, e.attributes()),
                    "p" => {
                        flush_current_line(&mut state);
                        state.current_marker = Some("p".to_string());
                    }
                    "lg" => {
                        flush_current_line(&mut state);
                        state.lg_level = None;
                        for attr in e.attributes().flatten() {
                            if attr.key.as_ref() == b"level" {
                                state.lg_level = Some(String::from_utf8_lossy(&attr.value).to_string());
                            }
                        }
                    }
                    "l" => {
                        flush_current_line(&mut state);
                        let mut level = None;
                        for attr in e.attributes().flatten() {
                            if attr.key.as_ref() == b"level" {
                                level = Some(String::from_utf8_lossy(&attr.value).to_string());
                            }
                        }
                        let lg_lvl = state.lg_level.as_deref().unwrap_or("1");
                        let lvl = level.as_deref().unwrap_or(lg_lvl);
                        state.current_marker = Some(format!("q{}", lvl));
                    }
                    "q" => {
                        flush_current_line(&mut state);
                        let mut level = None;
                        for attr in e.attributes().flatten() {
                            if attr.key.as_ref() == b"level" {
                                level = Some(String::from_utf8_lossy(&attr.value).to_string());
                            }
                        }
                        let lvl = level.as_deref().unwrap_or("1");
                        state.current_marker = Some(format!("q{}", lvl));
                    }
                    "w" => {
                        flush_current_line(&mut state);
                        state.current_marker = Some("w".to_string());
                        handle_word_start(&mut state, e.attributes());
                    }
                    "note" => {
                        flush_current_line(&mut state);
                        handle_note_start(&mut state, e.attributes());
                    }
                    "hi" => {
                        flush_current_line(&mut state);
                        handle_hi_start(&mut state, e.attributes());
                    }
                    "divineName" => {
                        flush_current_line(&mut state);
                        state.current_marker = Some("nd".to_string());
                    }
                    "title" => {
                        flush_current_line(&mut state);
                        handle_title_start(&mut state, e.attributes());
                    }
                    _ => {}
                }
            }
            Ok(Event::End(e)) => {
                let name = String::from_utf8_lossy(e.name().as_ref()).to_string();
                state.tag_stack.pop();
                match name.as_str() {
                    "w" | "note" | "hi" | "divineName" | "q" | "l" | "p" => {
                        let marker = state.current_marker.clone().unwrap_or_else(|| "p~".to_string());
                        let normalized = normalize_marker(&marker);
                        flush_current_line(&mut state);
                        state.raw_lines.push((format!("{}*", normalized), "".to_string()));
                    }
                    "title" => {
                        flush_current_line(&mut state);
                    }
                    "verse" => {
                        flush_current_line(&mut state);
                        state.current_v = None;
                    }
                    "chapter" => {
                        flush_current_line(&mut state);
                        state.current_c = None;
                    }
                    _ => {}
                }
            }
            Ok(Event::Empty(e)) => {
                let name = String::from_utf8_lossy(e.name().as_ref()).to_string();
                match name.as_str() {
                    "chapter" => handle_chapter_start(&mut state, e.attributes()),
                    "verse" => handle_verse_start(&mut state, e.attributes()),
                    _ => {}
                }
            }
            Ok(Event::Text(e)) => {
                let text = e.unescape().map(|c| c.into_owned()).unwrap_or_default();
                let cleaned = clean_text(&text);
                if !cleaned.is_empty() {
                    state.current_text.push_str(&cleaned);
                }
            }
            Ok(Event::Eof) => break,
            _ => {}
        }
        buf.clear();
    }
    flush_current_line(&mut state);
    state.raw_lines
}

fn parse_osis_single_threaded(content: &str) -> HashMap<String, Vec<(String, String)>> {
    let mut reader = Reader::from_str(content);
    reader.config_mut().trim_text(true);
    let mut state = ParserState::default();
    let mut buf = Vec::new();
    let mut books = HashMap::new();

    loop {
        match reader.read_event_into(&mut buf) {
            Ok(Event::Start(e)) => {
                let name = String::from_utf8_lossy(e.name().as_ref()).to_string();
                state.tag_stack.push(name.clone());
                match name.as_str() {
                    "div" => {
                        let old_bbb = state.current_bbb.clone();
                        handle_div_start(&mut state, e.attributes());
                        if old_bbb != state.current_bbb {
                             if let Some(old) = old_bbb {
                                 flush_current_line(&mut state);
                                 books.insert(old, std::mem::take(&mut state.raw_lines));
                             }
                        }
                    }
                    "chapter" => handle_chapter_start(&mut state, e.attributes()),
                    "verse" => handle_verse_start(&mut state, e.attributes()),
                    "p" => {
                        flush_current_line(&mut state);
                        state.current_marker = Some("p".to_string());
                    }
                    "lg" => {
                        flush_current_line(&mut state);
                        state.lg_level = None;
                        for attr in e.attributes().flatten() {
                            if attr.key.as_ref() == b"level" {
                                state.lg_level = Some(String::from_utf8_lossy(&attr.value).to_string());
                            }
                        }
                    }
                    "l" => {
                        flush_current_line(&mut state);
                        let mut level = None;
                        for attr in e.attributes().flatten() {
                            if attr.key.as_ref() == b"level" {
                                level = Some(String::from_utf8_lossy(&attr.value).to_string());
                            }
                        }
                        let lg_lvl = state.lg_level.as_deref().unwrap_or("1");
                        let lvl = level.as_deref().unwrap_or(lg_lvl);
                        state.current_marker = Some(format!("q{}", lvl));
                    }
                    "q" => {
                        flush_current_line(&mut state);
                        let mut level = None;
                        for attr in e.attributes().flatten() {
                            if attr.key.as_ref() == b"level" {
                                level = Some(String::from_utf8_lossy(&attr.value).to_string());
                            }
                        }
                        let lvl = level.as_deref().unwrap_or("1");
                        state.current_marker = Some(format!("q{}", lvl));
                    }
                    "w" => {
                        flush_current_line(&mut state);
                        state.current_marker = Some("w".to_string());
                        handle_word_start(&mut state, e.attributes());
                    }
                    "note" => {
                        flush_current_line(&mut state);
                        handle_note_start(&mut state, e.attributes());
                    }
                    "hi" => {
                        flush_current_line(&mut state);
                        handle_hi_start(&mut state, e.attributes());
                    }
                    "divineName" => {
                        flush_current_line(&mut state);
                        state.current_marker = Some("nd".to_string());
                    }
                    "title" => {
                        flush_current_line(&mut state);
                        handle_title_start(&mut state, e.attributes());
                    }
                    _ => {}
                }
            }
            Ok(Event::End(e)) => {
                let name = String::from_utf8_lossy(e.name().as_ref()).to_string();
                state.tag_stack.pop();
                match name.as_str() {
                    "w" | "note" | "hi" | "divineName" | "q" | "l" | "p" => {
                        let marker = state.current_marker.clone().unwrap_or_else(|| "p~".to_string());
                        let normalized = normalize_marker(&marker);
                        flush_current_line(&mut state);
                        state.raw_lines.push((format!("{}*", normalized), "".to_string()));
                    }
                    "title" => {
                        flush_current_line(&mut state);
                    }
                    "verse" => {
                        flush_current_line(&mut state);
                        state.current_v = None;
                    }
                    "chapter" => {
                        flush_current_line(&mut state);
                        state.current_c = None;
                    }
                    _ => {}
                }
            }
            Ok(Event::Empty(e)) => {
                let name = String::from_utf8_lossy(e.name().as_ref()).to_string();
                match name.as_str() {
                    "chapter" => handle_chapter_start(&mut state, e.attributes()),
                    "verse" => handle_verse_start(&mut state, e.attributes()),
                    _ => {}
                }
            }
            Ok(Event::Text(e)) => {
                let text = e.unescape().map(|c| c.into_owned()).unwrap_or_default();
                let cleaned = clean_text(&text);
                if !cleaned.is_empty() {
                    state.current_text.push_str(&cleaned);
                }
            }
            Ok(Event::Eof) => break,
            _ => {}
        }
        buf.clear();
    }
    flush_current_line(&mut state);
    if let Some(bbb) = state.current_bbb {
        books.insert(bbb, state.raw_lines);
    }
    books
}

fn handle_div_start(state: &mut ParserState, attrs: Attributes) {
    let mut div_type = None;
    let mut osis_id = None;

    for attr in attrs.flatten() {
        match attr.key.as_ref() {
            b"type" => div_type = Some(String::from_utf8_lossy(&attr.value).to_string()),
            b"osisID" => osis_id = Some(String::from_utf8_lossy(&attr.value).to_string()),
            _ => {}
        }
    }

    if div_type.as_deref() == Some("book") {
        if let Some(id) = osis_id {
            if let Ok(bbb) = bos_books_codes::osis_book_code_to_bos_book_code(&id, true) {
                state.current_bbb = Some(bbb.to_string());
                state.current_c = None;
                state.current_v = None;
            }
        }
    }
}

fn handle_chapter_start(state: &mut ParserState, attrs: Attributes) {
    for attr in attrs.flatten() {
        if attr.key.as_ref() == b"osisID" {
            let val = String::from_utf8_lossy(&attr.value).to_string();
            if let Some(pos) = val.find('.') {
                let c = &val[pos+1..];
                flush_current_line(state);
                state.current_c = Some(c.to_string());
                state.current_v = None;
                state.raw_lines.push(("c".to_string(), c.to_string()));
            }
        }
    }
}

fn handle_verse_start(state: &mut ParserState, attrs: Attributes) {
    for attr in attrs.flatten() {
        if attr.key.as_ref() == b"osisID" {
            let val = String::from_utf8_lossy(&attr.value).to_string();
            let parts: Vec<&str> = val.split('.').collect();
            if parts.len() >= 3 {
                let v = parts[2];
                flush_current_line(state);
                state.current_v = Some(v.to_string());
                state.raw_lines.push(("v".to_string(), v.to_string()));
            }
        }
    }
}

fn handle_word_start(state: &mut ParserState, attrs: Attributes) {
    let mut lemma = None;
    let mut morph = None;
    for attr in attrs.flatten() {
        match attr.key.as_ref() {
            b"lemma" => lemma = Some(String::from_utf8_lossy(&attr.value).to_string()),
            b"morph" => morph = Some(String::from_utf8_lossy(&attr.value).to_string()),
            _ => {}
        }
    }
    let mut attr_str = String::new();
    if let Some(l) = lemma {
        let clean_l = if l.starts_with("strong:") { &l[7..] } else { &l };
        attr_str.push_str(&format!("|strong=\"{}\"", clean_l));
    }
    if let Some(m) = morph {
        if !attr_str.is_empty() { attr_str.push(' '); }
        attr_str.push_str(&format!("x-morph=\"{}\"", m));
    }
    state.current_text.push_str(&attr_str);
}

fn handle_note_start(state: &mut ParserState, attrs: Attributes) {
    let mut note_type = None;
    for attr in attrs.flatten() {
        if attr.key.as_ref() == b"type" {
            note_type = Some(String::from_utf8_lossy(&attr.value).to_string());
        }
    }
    state.current_marker = Some(match note_type.as_deref() {
        Some("crossReference") => "x".to_string(),
        _ => "f".to_string(),
    });
}

fn handle_hi_start(state: &mut ParserState, attrs: Attributes) {
    let mut hi_type = None;
    for attr in attrs.flatten() {
        if attr.key.as_ref() == b"type" {
            hi_type = Some(String::from_utf8_lossy(&attr.value).to_string());
        }
    }
    state.current_marker = Some(match hi_type.as_deref() {
        Some("italic") => "it".to_string(),
        Some("bold") => "bd".to_string(),
        Some("small-caps") => "sc".to_string(),
        _ => "em".to_string(),
    });
}

fn handle_title_start(state: &mut ParserState, attrs: Attributes) {
    let mut title_type = None;
    let mut level = None;
    let mut canonical = None;

    for attr in attrs.flatten() {
        match attr.key.as_ref() {
            b"type" => title_type = Some(String::from_utf8_lossy(&attr.value).to_string()),
            b"level" => level = Some(String::from_utf8_lossy(&attr.value).to_string()),
            b"canonical" => canonical = Some(String::from_utf8_lossy(&attr.value).to_string()),
            _ => {}
        }
    }

    let marker = if state.current_c.is_some() {
        if title_type.as_deref() == Some("parallel") {
            "sr".to_string()
        } else if canonical.as_deref() == Some("true") {
            "d".to_string()
        } else if let Some(lvl) = level {
            format!("s{}", lvl)
        } else {
            "s".to_string()
        }
    } else {
        if title_type.as_deref() == Some("main") {
            if let Some(lvl) = level {
                format!("mt{}", lvl)
            } else {
                "mt".to_string()
            }
        } else {
            if let Some(lvl) = level {
                format!("imt{}", lvl)
            } else {
                "imt".to_string()
            }
        }
    };

    state.current_marker = Some(marker);
}

fn flush_current_line(state: &mut ParserState) {
    if !state.current_text.is_empty() {
        let marker = state.current_marker.take().unwrap_or_else(|| {
            if state.current_v.is_some() { "v~".to_string() } else { "p~".to_string() }
        });
        let normalized = normalize_marker(&marker);
        let text = std::mem::take(&mut state.current_text);
        state.raw_lines.push((normalized.to_string(), text));
    }
}

fn clean_text(s: &str) -> String {
    let mut result = s.replace('\t', " ").replace("\r\n", " ").replace('\n', " ").replace('\r', " ");
    while result.contains("  ") {
        result = result.replace("  ", " ");
    }
    result
}
