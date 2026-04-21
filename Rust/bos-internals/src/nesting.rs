//! USFM nesting and end marker logic.

use compact_str::CompactString;

use crate::entry::InternalBibleEntry;
use crate::entry_extras::InternalBibleEntryList;
use crate::markers::{
    heading_markers, intro_list_markers, intro_outline_markers, introduction_markers,
    is_never_content_marker, main_text_list_markers, major_section_markers, paragraph_markers,
};
use crate::verbosity_print;

/// Add nesting and end markers to a list of processed Bible entries.
///
/// This is the Rust equivalent of the Python `_addNestingMarkers` function.
/// It also calls `add_verse_start_markers` internally to provide a complete
/// structural processing in one call, though the functions remain available.
pub fn add_nesting_markers(
    entries: InternalBibleEntryList,
    work_name: &str,
    bos_book_code: &str,
) -> InternalBibleEntryList {
    verbosity_print!(
        2,
        "    add_nesting_markers for {} {} started with {} entries",
        work_name,
        bos_book_code,
        entries.len()
    );

    let entries_vec = entries.into_vec();
    let num_entries = entries_vec.len();
    let mut new_lines = InternalBibleEntryList::with_capacity(num_entries + 100);
    let mut open_markers: Vec<CompactString> = Vec::new();

    // Context tracking
    let mut current_chapter = CompactString::from("-1");
    let mut current_verse = CompactString::from("0");
    let mut last_marker: Option<CompactString> = None;
    let mut last_p_marker: Option<CompactString> = None;
    let mut last_s_marker: Option<CompactString> = None;

    // Helper functions for look-ahead
    let chapter_has_ended = |start_idx: usize, entries: &[InternalBibleEntry]| {
        for k in (start_idx + 1)..entries.len() {
            let m = entries[k].marker();
            if m == "c" { return true; }
            if matches!(m, "v" | "v~" | "p~") { return false; }
        }
        true
    };

    let verse_has_ended = |start_idx: usize, entries: &[InternalBibleEntry]| {
        for k in (start_idx + 1)..entries.len() {
            let m = entries[k].marker();
            if matches!(m, "v" | "c") { return true; }
            if matches!(m, "v~" | "p~") { return false; }
        }
        true
    };

    let section_has_ended = |current_marker: &str, start_idx: usize, entries: &[InternalBibleEntry]| {
        let mut other_possibilities = Vec::new();
        if let Some(level_char) = current_marker.chars().last() {
            if level_char.is_ascii_digit() && level_char > '1' {
                let level = level_char.to_digit(10).unwrap();
                let base = &current_marker[..current_marker.len() - 1];
                for z in 1..level {
                    other_possibilities.push(format!("{}{}", base, z));
                }
            }
        }
        if matches!(current_marker, "s1" | "s2" | "s3" | "s4") {
            other_possibilities.push("ms1".to_string());
        }

        for k in (start_idx + 1)..entries.len() {
            let m = entries[k].marker();
            if m == current_marker || other_possibilities.iter().any(|p| p == m) { return true; }
            if matches!(m, "v" | "v~" | "p~") { return false; }
        }
        true
    };

    let paragraph_has_ended = |start_idx: usize, entries: &[InternalBibleEntry]| {
        for k in (start_idx + 1)..entries.len() {
            let m = entries[k].marker();
            if paragraph_markers::is_paragraph(m) || main_text_list_markers::is_main_text_list(m) { return true; }
            if matches!(m, "v" | "v~" | "p~") { return false; }
        }
        true
    };

    let find_next_relevant_marker = |start_idx: usize, entries: &[InternalBibleEntry]| {
        for k in (start_idx + 1)..entries.len() {
            let m = entries[k].marker();
            if matches!(m, "v" | "v~" | "p~")
                || heading_markers::is_heading(m)
                || major_section_markers::is_major_section(m)
                || paragraph_markers::is_paragraph(m)
            {
                return Some(CompactString::from(m));
            }
        }
        None
    };

    let find_next_relevant_list_marker = |start_idx: usize, entries: &[InternalBibleEntry]| {
        for k in (start_idx + 1)..entries.len() {
            let m = entries[k].marker();
            if !matches!(m, "c" | "v=" | "v" | "v~" | "p~") {
                return Some(CompactString::from(m));
            }
        }
        None
    };

    for j in 0..num_entries {
        let entry = &entries_vec[j];
        let marker = entry.marker();
        let marker_owned = CompactString::from(marker);
        let text = entry.clean_text();

        if current_chapter == "-1" {
            let v_int: i32 = current_verse.parse().unwrap_or(0);
            current_verse = CompactString::from((v_int + 1).to_string());
        }

        // Header and Intro logic
        if marker == "h" {
            if !open_markers.iter().any(|m| m == "headers") {
                new_lines.push(InternalBibleEntry::nesting_marker("headers"));
                open_markers.push(CompactString::from("headers"));
            }
        }

        if introduction_markers::is_introduction(marker)
            && !open_markers.iter().any(|m| m == "intro")
            && (marker != "iex" || !open_markers.iter().any(|m| m == "c"))
        {
            if let Some(pos) = open_markers.iter().position(|m| m == "headers") {
                let m = open_markers.remove(pos);
                new_lines.push(InternalBibleEntry::simple(format!("¬{}", m), ""));
            }
            new_lines.push(InternalBibleEntry::nesting_marker("intro"));
            open_markers.push(CompactString::from("intro"));
        }

        if let Some(last_open) = open_markers.last().map(|s| s.to_string()) {
            if last_open == "iot" && !intro_outline_markers::is_intro_outline(marker) {
                open_markers.pop();
                new_lines.push(InternalBibleEntry::simple("¬iot", ""));
            }
        }
        if let Some(last_open) = open_markers.last().map(|s| s.to_string()) {
            if last_open == "ilist" && !intro_list_markers::is_intro_list(marker) {
                open_markers.pop();
                new_lines.push(InternalBibleEntry::simple("¬ilist", ""));
            }
        }
        if let Some(last_open) = open_markers.last().map(|s| s.to_string()) {
            if last_open == "list"
                && !main_text_list_markers::is_main_text_list(marker)
                && marker != "v~"
                && marker != "p~"
            {
                let close = if let Some(next_list_m) = find_next_relevant_list_marker(j, &entries_vec) {
                    !main_text_list_markers::is_main_text_list(next_list_m.as_str())
                } else { true };
                if close {
                    open_markers.pop();
                    new_lines.push(InternalBibleEntry::simple("¬list", ""));
                }
            }
        }

        // Chapter logic
        if marker == "c" {
            if let Some(last_open) = open_markers.last().map(|s| s.to_string()) {
                if last_open == "headers" || last_open == "intro" {
                    open_markers.pop();
                    new_lines.push(InternalBibleEntry::simple(format!("¬{}", last_open), ""));
                }
            }

            if let Some(pos) = open_markers.iter().rposition(|m| m == "v") {
                let m = open_markers.remove(pos);
                new_lines.push(InternalBibleEntry::simple(format!("¬{}", m), current_verse.as_str()));
            }

            if !open_markers.iter().any(|m| m == "chapters") {
                new_lines.push(InternalBibleEntry::nesting_marker("chapters"));
                open_markers.push(CompactString::from("chapters"));
            } else {
                let next_rel = find_next_relevant_marker(j, &entries_vec);
                if let Some(last_open_m) = open_markers.last().map(|s| s.to_string()) {
                    if paragraph_markers::is_paragraph(&last_open_m) {
                        if let Some(nr) = next_rel.as_ref() {
                            if paragraph_markers::is_paragraph(nr.as_str()) || heading_markers::is_heading(nr.as_str()) {
                                open_markers.pop();
                                new_lines.push(InternalBibleEntry::simple(format!("¬{}", last_open_m), ""));
                            }
                        }
                    }
                }
                if let Some(last_open_m) = open_markers.last().map(|s| s.to_string()) {
                    if heading_markers::is_heading(&last_open_m) {
                        if let Some(nr) = next_rel.as_ref() {
                            if heading_markers::is_heading(nr.as_str()) {
                                open_markers.pop();
                                new_lines.push(InternalBibleEntry::simple(format!("¬{}", last_open_m), ""));
                            }
                        }
                    }
                }
            }

            if let Some(pos) = open_markers.iter().rposition(|m| m == "c") {
                let m = open_markers.remove(pos);
                new_lines.push(InternalBibleEntry::simple(format!("¬{}", m), current_chapter.as_str()));
            }

            current_chapter = CompactString::from(text);
            current_verse = CompactString::from("0");
            open_markers.push(marker_owned.clone());
        } else if marker == "vp#" {
            if let Some(pos) = open_markers.iter().rposition(|m| m == "v") {
                let m = open_markers.remove(pos);
                new_lines.push(InternalBibleEntry::simple(format!("¬{}", m), current_verse.as_str()));
            }
        } else if marker == "v" {
            for _ in 0..9 {
                let mut made_change = false;
                if let Some(last_open_m) = open_markers.last().map(|s| s.to_string()) {
                    if last_open_m == "v" {
                        open_markers.pop();
                        new_lines.push(InternalBibleEntry::simple("¬v", current_verse.as_str()));
                        made_change = true;
                    } else if let Some(last_p) = &last_p_marker {
                        if &last_open_m == last_p.as_str() && paragraph_has_ended(j, &entries_vec) {
                            open_markers.pop();
                            new_lines.push(InternalBibleEntry::simple(format!("¬{}", last_open_m), ""));
                            made_change = true;
                        }
                    }
                }
                if !made_change { break; }
            }
            if let Some(pos) = open_markers.iter().rposition(|m| m == "v") {
                let m = open_markers.remove(pos);
                new_lines.push(InternalBibleEntry::simple(format!("¬{}", m), current_verse.as_str()));
            }
            current_verse = CompactString::from(text);
            open_markers.push(marker_owned.clone());
        } else if marker == "iot" {
            open_markers.push(CompactString::from("iot"));
        } else if intro_outline_markers::is_intro_outline(marker) {
            let should_open = if let Some(lm) = &last_marker {
                lm != "iot" && !intro_outline_markers::is_intro_outline(lm)
            } else { true };
            if should_open {
                new_lines.push(InternalBibleEntry::nesting_marker("iot"));
                open_markers.push(CompactString::from("iot"));
            }
        } else if intro_list_markers::is_intro_list(marker) {
            let should_open = last_marker.as_ref().map_or(true, |lm| !intro_list_markers::is_intro_list(lm));
            if should_open {
                new_lines.push(InternalBibleEntry::nesting_marker("ilist"));
                open_markers.push(CompactString::from("ilist"));
            }
        } else if heading_markers::is_heading(marker) {
            for _ in 0..9 {
                let mut made_change = false;
                if let Some(last_open_m) = open_markers.last().map(|s| s.to_string()) {
                    if last_open_m == "v" && verse_has_ended(j, &entries_vec) {
                        open_markers.pop();
                        new_lines.push(InternalBibleEntry::simple("¬v", current_verse.as_str()));
                        made_change = true;
                    } else if let Some(last_p) = &last_p_marker {
                        if &last_open_m == last_p.as_str() {
                            open_markers.pop();
                            new_lines.push(InternalBibleEntry::simple(format!("¬{}", last_open_m), ""));
                            made_change = true;
                        }
                    } else if let Some(last_s) = &last_s_marker {
                        if &last_open_m == last_s.as_str() && section_has_ended(last_s, j, &entries_vec) {
                            open_markers.pop();
                            new_lines.push(InternalBibleEntry::simple(format!("¬{}", last_open_m), ""));
                            made_change = true;
                        }
                    }
                }
                if !made_change { break; }
            }
            if verse_has_ended(j, &entries_vec) {
                if let Some(pos) = open_markers.iter().rposition(|m| m == "v") {
                    let m = open_markers.remove(pos);
                    new_lines.push(InternalBibleEntry::simple(format!("¬{}", m), current_verse.as_str()));
                }
            }
            if let Some(lp) = &last_p_marker {
                if let Some(pos) = open_markers.iter().rposition(|m| m == lp) {
                    let m = open_markers.remove(pos);
                    new_lines.push(InternalBibleEntry::simple(format!("¬{}", m), ""));
                }
            }
            if let Some(ls) = &last_s_marker {
                if let Some(pos) = open_markers.iter().rposition(|m| m == ls) {
                    let m = open_markers.remove(pos);
                    new_lines.push(InternalBibleEntry::simple(format!("¬{}", m), ""));
                }
            }
            last_p_marker = None;
            last_s_marker = None;
            open_markers.push(marker_owned.clone());
            last_s_marker = Some(marker_owned.clone());
        } else if major_section_markers::is_major_section(marker) {
            for _ in 0..9 {
                let mut made_change = false;
                if let Some(last_open_m) = open_markers.last().map(|s| s.to_string()) {
                    if last_open_m == "headers" || last_open_m == "intro" {
                        open_markers.pop();
                        new_lines.push(InternalBibleEntry::simple(format!("¬{}", last_open_m), ""));
                        made_change = true;
                    } else if last_open_m == "v" && verse_has_ended(j, &entries_vec) {
                        open_markers.pop();
                        new_lines.push(InternalBibleEntry::simple("¬v", current_verse.as_str()));
                        made_change = true;
                    } else if let Some(last_p) = &last_p_marker {
                        if &last_open_m == last_p.as_str() {
                            open_markers.pop();
                            new_lines.push(InternalBibleEntry::simple(format!("¬{}", last_open_m), ""));
                            made_change = true;
                        }
                    } else if let Some(last_s) = &last_s_marker {
                        if &last_open_m == last_s.as_str() && section_has_ended(last_s, j, &entries_vec) {
                            open_markers.pop();
                            new_lines.push(InternalBibleEntry::simple(format!("¬{}", last_open_m), ""));
                            made_change = true;
                        }
                    } else if last_open_m == "c" && chapter_has_ended(j, &entries_vec) {
                        open_markers.pop();
                        new_lines.push(InternalBibleEntry::simple("¬c", current_chapter.as_str()));
                        made_change = true;
                    } else if &last_open_m == marker {
                        open_markers.pop();
                        new_lines.push(InternalBibleEntry::simple(format!("¬{}", marker), ""));
                        made_change = true;
                    }
                }
                if !made_change { break; }
            }

            if !open_markers.iter().any(|m| m == "chapters") {
                new_lines.push(InternalBibleEntry::nesting_marker("chapters"));
                open_markers.push(CompactString::from("chapters"));
            } else if let Some(lp) = &last_p_marker {
                if let Some(pos) = open_markers.iter().rposition(|m| m == lp) {
                    let m = open_markers.remove(pos);
                    new_lines.push(InternalBibleEntry::simple(format!("¬{}", m), ""));
                }
            }

            if let Some(ls) = &last_s_marker {
                if let Some(pos) = open_markers.iter().rposition(|m| m == ls) {
                    let m = open_markers.remove(pos);
                    new_lines.push(InternalBibleEntry::simple(format!("¬{}", m), ""));
                }
            }

            if let Some(pos) = open_markers.iter().rposition(|m| m == marker) {
                let m = open_markers.remove(pos);
                new_lines.push(InternalBibleEntry::simple(format!("¬{}", m), ""));
            }
            open_markers.push(marker_owned.clone());
            last_p_marker = None;
            last_s_marker = Some(marker_owned.clone());
        } else if main_text_list_markers::is_main_text_list(marker) {
            for _ in 0..9 {
                let mut made_change = false;
                if let Some(last_open_m) = open_markers.last().map(|s| s.to_string()) {
                    if last_open_m == "v" && verse_has_ended(j, &entries_vec) {
                        open_markers.pop();
                        new_lines.push(InternalBibleEntry::simple("¬v", current_verse.as_str()));
                        made_change = true;
                    } else if let Some(last_p) = &last_p_marker {
                        if &last_open_m == last_p.as_str() {
                            open_markers.pop();
                            new_lines.push(InternalBibleEntry::simple(format!("¬{}", last_open_m), ""));
                            made_change = true;
                        }
                    }
                }
                if !made_change { break; }
            }
            if verse_has_ended(j, &entries_vec) {
                if let Some(pos) = open_markers.iter().rposition(|m| m == "v") {
                    let m = open_markers.remove(pos);
                    new_lines.push(InternalBibleEntry::simple(format!("¬{}", m), current_verse.as_str()));
                }
            }
            if let Some(lp) = &last_p_marker {
                if let Some(pos) = open_markers.iter().rposition(|m| m == lp) {
                    let m = open_markers.remove(pos);
                    new_lines.push(InternalBibleEntry::simple(format!("¬{}", m), ""));
                }
            }
            if !open_markers.iter().any(|m| m == "list") {
                new_lines.push(InternalBibleEntry::nesting_marker("list"));
                open_markers.push(CompactString::from("list"));
            }
            open_markers.push(marker_owned.clone());
            last_p_marker = Some(marker_owned.clone());
        } else if paragraph_markers::is_paragraph(marker) {
            for _ in 0..999 {
                let mut made_change = false;
                if let Some(last_open_m) = open_markers.last().map(|s| s.to_string()) {
                    if last_open_m == "v" && verse_has_ended(j, &entries_vec) {
                        open_markers.pop();
                        new_lines.push(InternalBibleEntry::simple("¬v", current_verse.as_str()));
                        made_change = true;
                    } else if let Some(last_p) = &last_p_marker {
                        if &last_open_m == last_p.as_str() {
                            open_markers.pop();
                            new_lines.push(InternalBibleEntry::simple(format!("¬{}", last_open_m), ""));
                            made_change = true;
                        }
                    }
                }
                if !made_change { break; }
            }
            if verse_has_ended(j, &entries_vec) {
                if let Some(pos) = open_markers.iter().rposition(|m| m == "v") {
                    let m = open_markers.remove(pos);
                    new_lines.push(InternalBibleEntry::simple(format!("¬{}", m), current_verse.as_str()));
                }
            }
            if let Some(lp) = &last_p_marker {
                if let Some(pos) = open_markers.iter().rposition(|m| m == lp) {
                    let m = open_markers.remove(pos);
                    new_lines.push(InternalBibleEntry::simple(format!("¬{}", m), ""));
                }
            }
            open_markers.push(marker_owned.clone());
            last_p_marker = Some(marker_owned.clone());
        } else if is_never_content_marker(marker) {
            for _ in 0..999 {
                let mut made_change = false;
                if let Some(last_open_m) = open_markers.last().map(|s| s.to_string()) {
                    if last_open_m == "v" && verse_has_ended(j, &entries_vec) {
                        open_markers.pop();
                        new_lines.push(InternalBibleEntry::simple("¬v", current_verse.as_str()));
                        made_change = true;
                    } else if let Some(last_p) = &last_p_marker {
                        if &last_open_m == last_p.as_str() {
                            open_markers.pop();
                            new_lines.push(InternalBibleEntry::simple(format!("¬{}", last_open_m), ""));
                            made_change = true;
                        }
                    }
                }
                if !made_change { break; }
            }
            if verse_has_ended(j, &entries_vec) {
                if let Some(pos) = open_markers.iter().rposition(|m| m == "v") {
                    let m = open_markers.remove(pos);
                    new_lines.push(InternalBibleEntry::simple(format!("¬{}", m), current_verse.as_str()));
                }
            }
        }

        new_lines.push(entry.clone());
        last_marker = Some(marker_owned);
    }

    // Close any left-over open markers
    while let Some(marker) = open_markers.pop() {
        let mut end_marker = CompactString::from("¬");
        end_marker.push_str(&marker);
        let with_text = if marker == "v" {
            current_verse.as_str()
        } else if marker == "c" {
            current_chapter.as_str()
        } else { "" };
        new_lines.push(InternalBibleEntry::simple(end_marker, with_text));
    }

    verbosity_print!(2, "    add_nesting_markers for {} finishing with {} entries", bos_book_code, new_lines.len());
    
    new_lines
}

/// Add logical verse start markers (`v=`) before sections, paragraphs, etc.
/// 
/// This is the Rust equivalent of the Python `addVerseStartMarkers` function.
pub fn add_verse_start_markers(entries: InternalBibleEntryList) -> InternalBibleEntryList {
    let entries_vec = entries.into_vec();
    let num_entries = entries_vec.len();
    let mut result = InternalBibleEntryList::with_capacity(num_entries + 40);
    
    let fields_preceded = ["s", "s1", "s2", "s3", "s4", "sp"];
    let mut fields_also_preceded: Vec<&str> = Vec::new();
    fields_also_preceded.extend_from_slice(paragraph_markers::ALL);
    fields_also_preceded.extend_from_slice(&["c#", "r", "d", "ms1", "mr", "sr", "sp", "ib", "b", "nb", "cl¤", "tr"]);

    for j in 0..num_entries {
        let entry = &entries_vec[j];
        let marker = entry.marker();
        
        if fields_preceded.contains(&marker) {
            // Look ahead for next 'v'
            for k in 1..5 {
                if j + k < num_entries {
                    let next_entry = &entries_vec[j + k];
                    let next_marker = next_entry.marker();
                    if next_marker == "v" {
                        // Add v= marker
                        result.push(InternalBibleEntry::new(
                            "v=",
                            "v",
                            next_entry.adjusted_text().unwrap_or(""),
                            next_entry.clean_text(),
                            None,
                            next_entry.original_text().unwrap_or(""),
                        ).expect("Valid internal entry"));
                        break; // Only add one v= for this preceded field
                    } else if !fields_also_preceded.contains(&next_marker) && !next_marker.starts_with('¬') && next_marker != "rem" {
                        break;
                    }
                }
            }
        }
        result.push(entry.clone());
    }
    
    result
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::entry::InternalBibleEntry;
    use crate::entry_extras::InternalBibleEntryList;
    use std::fs::File;
    use std::io::{BufRead, BufReader};

    #[test]
    fn test_oet_rv_haggai_nesting() {
        let file_path = "src/indexes/OET-RV_HAG.ESFM";
        let file = File::open(file_path).expect("Could not open Haggai ESFM file");
        let reader = BufReader::new(file);

        let mut entries = InternalBibleEntryList::new();
        for line in reader.lines() {
            let line = line.expect("Could not read line");
            if line.trim().is_empty() {
                continue;
            }
            let (marker, text) = match line.split_once(' ') {
                Some((m, t)) => (m, t),
                None => (line.as_str(), ""),
            };
            let marker = marker.strip_prefix('\\').unwrap_or(marker);

            // Replicate Python processLines logic for ESFM (83 entrprocessLies)
            if marker == "c" {
                entries.push(InternalBibleEntry::simple("c", text));
                entries.push(InternalBibleEntry::simple("c#", text));
            } else {
                entries.push(InternalBibleEntry::simple(marker, text));
            }
        }
        let original_count = entries.len();
        println!("Original entries (after ESFM load emulation): {}", original_count);
        assert_eq!(original_count, 81, "Expected 81 entries after initial processing");
        /*
        0 Raw entry=('id', "HAG - Open English Translation—Readers' Version (OET-RV) v0.1.03")
        1 Raw entry=('usfm', '3.0')
        2 Raw entry=('ide', 'UTF-8')
        3 Raw entry=('rem', 'ESFM v0.6 HAG')
        4 Raw entry=('rem', 'WORDTABLE OET-LV_OT_word_table.tsv')
        5 Raw entry=('h', 'Haggai')
        6 Raw entry=('toc1', 'Haggai')
        7 Raw entry=('toc2', 'Haggai')
        8 Raw entry=('toc3', 'Hag.')
        9 Raw entry=('mt1', 'Haggai')
        10 Raw entry=('is1', 'Introduction')
        11 Raw entry=('ip', "This document contains a number of messages from Yahweh that the prophet Haggai passed on to the people in Yerushalem (Jerusalem). These events happened around 520 before Yeshua/Jesus (B.C.), after many of God's people had gone back to Yerushalem after being taken into captivity in Babylon. However, even though they'd been back for a considerable time, they hadn't worked on rebuilding the temple. Therefore, these messages from Yahweh encourage the people to change their priorities and obey God and rebuild the temple. God then promised to prosper the people and bless their living situation.")
        12 Raw entry=('iot', 'Main components of this account')
        13 Raw entry=('io1', "God's command to rebuild the temple \\ior 1:1-15\\ior*")
        14 Raw entry=('io1', 'Stories of comfort and hope \\ior 2:1-23\\ior*')
        15 Raw entry=('rem', 'This is still a very early look into the unfinished text of the Open English Translation of the Bible. Please double-check the text in advance before using in public.')
        16 Raw entry=('ie', '')
        17 Raw entry=('c', '1')
        18 Raw entry=('s1', "God's command to rebuild the temple")
        19 Raw entry=('rem', "/s1 The Lord's Command to Rebuild the Temple; A Call to Rebuild the Temple; Zerubbabel restorer of the temple; A Call to Build the House of the Lord; The Command to Rebuild the Temple")
        20 Raw entry=('p', '')
        21 Raw entry=('v', "1 In Dareyavesh's \\add (Darius's¦375563)\\add* second year¦375561 as king¦375564 \\add of Persia\\add*, on¦375565 the 1st of the sixth¦375566 month, the prophet¦375577 Haggai¦375576 brought Yahweh's¦375573 message¦375571 to the governor¦375584 of Yehudah¦375585, Zerubavel¦375580 (Shealtiyel's¦375583 son), and to the high¦375593 priest¦375592, Yehoshua (Yehotsadak's¦375591 son), telling \\add them that\\add*\\x + \\xo 1:1: \\xt Ezr 4:24–5:2; 6:14.\\x*")
        22 Raw entry=('v', "2 Commander-in-chief Yahweh says, “These people¦375601 say that \\add ≈it's not the right\\add* time to rebuild¦375612 Yahweh's¦375598 \\add ≈residence\\add*.”")
        23 Raw entry=('p', '')
        24 Raw entry=('v', '3 Then Yahweh¦375618 \\add ≈gave this message¦375616\\add* to the prophet¦375622 Haggai¦375621 \\add to tell the people\\add*:')
        25 Raw entry=('m', '')
        26 Raw entry=('v', "4 Is it a time¦375625 for all of you to live in your panelled¦375630 houses¦375629, while \\add ≈Yahweh's temple lies in ruins\\add*?")
        27 Raw entry=('v', "5 \\add ≈So¦375635\\add* now Commander-in-chief Yahweh¦375638 says¦375637: “\\add ≈Decide what you're all going to do\\add*.")
        28 Raw entry=('v', "6 You've all planted a lot, \\add ≈but only harvested¦375648 a little¦375649. You've eaten¦375650, but it never fills you. You all drink, but never enough to satisfy¦375653 you. You put on clothes, but never feel warm enough. You earn wages¦375664, but your pockets seem to be full of holes\\add*.”")
        29 Raw entry=('p', '')
        30 Raw entry=('v', "7 \\add ≈So\\add* Commander-in-chief Yahweh¦375673 says¦375672 \\add again\\add*: “\\add ≈Decide what you're all going to do\\add*.")
        31 Raw entry=('v', '8 Go up into the hills¦375682 and bring¦375683 back timber to build¦375685 the \\add ≈temple\\add*. This will please¦375687 and honour¦375690 me,” says¦375692 Yahweh¦375693.')
        32 Raw entry=('p', '')
        33 Raw entry=('v', "9 “You \\add ≈expected\\add* much, but¦375699 \\add gained\\add* little¦375700. Anything you brought¦375701 home¦375702, I blew away \\add again\\add*. Why? Commander-in-chief Yahweh¦375708 says it's because my residence is still in ruins, while you're all \\add busy\\add* \\add ≈working on\\add* your own houses.")
        34 Raw entry=('v', "10 That's why the sky withholds the dew and¦375731 the soil withholds its¦375733 crops.")
        35 Raw entry=('v', "11 I've¦375735 \\add ≈summoned¦375735\\add* a drought¦375736 onto the land and into the hills¦375742, onto the grain¦375745 and the new wine, onto the oil and crops from the ground, onto \\add both\\add* people and livestock, and onto \\add ≈everything you all do\\add*.”")
        36 Raw entry=('s1', 'The people start rebuilding')
        37 Raw entry=('rem', "/s1 The People Obey the Lord's Command; Obedience to God's Call")
        38 Raw entry=('p', '')
        39 Raw entry=('v', "12 Then Shealtiyel's son Zerubavel and Yehotsadak's son Yehoshua, the high priest¦375779, and all the rest of the people listened¦375769 to the voice¦375785 of their god Yahweh \\add ≈via\\add* the words¦375790 of the prophet¦375792 Haggai¦375791, because Yahweh their god had sent him, and the people \\add ≈respected\\add* Yahweh.")
        40 Raw entry=('v', "13 Then¦375802 Yahweh's¦375805 messenger¦375804 Haggai¦375803 passed this message¦375806 from Yahweh onto the people¦375808, “Yahweh declares that I'm with¦375806 you¦375811 all.”")
        41 Raw entry=('v', "14 Then¦375816 Yahweh \\add ≈inspired\\add* Shealtiyel's son Zerubavel, the governor¦375825 of Yehudah¦375826, \\add ≈inspired\\add* Yehotsadak's son Yehoshua, the high¦375835 priest¦375834, and \\add ≈inspired\\add* all the rest of the people¦375841, and they came¦375842 and \\add ≈started\\add* work¦375844 on the \\add ≈temple\\add* for their¦375849 god¦375849, Commander-in-chief Yahweh,")
        42 Raw entry=('v', '15 on¦375856 the twenty-fourth day¦375852 of the sixth¦375856 month¦375855 of the second year¦375857 of Dareyavesh the king¦375860 \\add of Persia\\add*.')
        43 Raw entry=('c', '2')
        44 Raw entry=('s1', 'The splendour of the new temple')
        45 Raw entry=('rem', "/s1 The Future Glory of the Temple; The New Temple's Splendour; The Splendour of the New Temple; The Promised Glory of the New House")
        46 Raw entry=('p', '')
        47 Raw entry=('v', '1 On the 21st of the seventh¦375862 month \\add (about a month later)\\add*, Yahweh¦375869 \\add ≈spoke\\add* \\add again\\add* through the prophet¦375873 Haggai¦375872:')
        48 Raw entry=('v', "2 Please \\add ≈ask\\add* Shealtiyel's son Zerubavel, the governor¦375885 of Yehudah¦375886, and \\add ≈ask\\add* Yehotsadak's son Yehoshua, the high¦375894 priest¦375893, and \\add ≈ask\\add* the rest of the people¦375898,")
        49 Raw entry=('v', '3 “\\add ≈Are there any of you still alive who saw¦375905 the splendour¦375910 of the former¦375911 temple\\add*? How does it look to you now? \\add ≈It must now seem pretty much like \\+em nothing¦375919\\+em* in¦375902 comparison\\add*.\\x + \\xo 2:3: \\xt Ezr 3:12.\\x*')
        50 Raw entry=('v', "4 Yahweh is telling you now, Zerubavel, to be strong. And be strong, high¦375935 priest¦375934 Yehoshua, and¦375922 be strong all you people¦375939 of the land. Commander-in-chief Yahweh declares that I'm with you \\add ≈as you work¦375944\\add*.")
        51 Raw entry=('v', "5 \\add ≈That's what I promised¦375955 your¦375964 ancestors when they\\add* came¦375960 out of Egypt¦375961,\\x + \\xo 2:5: \\xt Exo 29:45-46.\\x* and¦375962 my spirit¦375962 remains \\add ≈among¦375964 you¦375960\\add*. Don't¦375965 be afraid¦375967,")
        52 Raw entry=('v', "6 because¦375970 Commander-in-chief Yahweh¦375973 says¦375972 that in a little¦375977 while, I'll¦375979 shake¦375980 the heavens¦375983 and the earth¦375986, the sea¦375989 and the dry land, once more.\\x + \\xo 2:6: \\xt Heb 12:26.\\x*")
        53 Raw entry=('v', "7 I'll shake¦375994 all the nations, and¦375994 they'll come \\add here bringing\\add* their treasure. Then¦375994 I'll fill this \\add ≈temple\\add* with \\add my\\add* splendour¦376010, says Commander-in-chief Yahweh¦376012.")
        54 Raw entry=('v', '8 Commander-in-chief Yahweh¦376020 declares that the gold¦376018 and¦376017 silver¦376016 \\add belong¦376017\\add* to me.')
        55 Raw entry=('v', '9 \\add *I\\add* declare that this \\add ≈temple\\add* will be \\add ≈greater in the future than it¦376024 was in the past\\add*, and \\add also\\add* that I will give¦376037 peace¦376038 and prosperity to this place¦376035.”')
        56 Raw entry=('s1', 'Haggai consults the priests')
        57 Raw entry=('rem', '/s1 Blessings Promised for Obedience; Blessings for a Defiled People; A Rebuke and a Promise; The Prophet Consults the Priests')
        58 Raw entry=('p', '')
        59 Raw entry=('v', "10 On the 24th of the ninth¦376046 month in¦376044 \\add King\\add* Dareyavesh's second year¦376047 \\add (about two¦376048 months later)\\add*, Yahweh¦376053 \\add ≈gave a message¦376051\\add* to the prophet¦376057 Haggai¦376056:")
        60 Raw entry=('v', "11 Commander-in-chief Yahweh¦376062 says¦376061, “Ask the priests¦376069 about \\add Mosheh's\\add* \\add ≈instructions¦376070\\add*.")
        61 Raw entry=('v', '12 ‘\\add ≈If a priest took some meat¦376078 that had been offered to God and carried it wrapped in¦376081 a piece of clothing, then if the clothing touched¦376083 some other food, would that other food \\add* become¦376102 holy?’ ”')
        62 Raw entry=('p', "“No, it wouldn't,” the priests¦376104 \\add ≈replied\\add*.")
        63 Raw entry=('p', '')
        64 Raw entry=('v', '13 Then¦376108 Haggai¦376109 asked, “\\add But¦376108\\add* if a person became unclean by touching a corpse¦376115 and¦376108 then¦376108 touched any of that \\add food\\add*, would it become unclean?”\\x + \\xo 2:13: \\xt Num 19:11-22.\\x*')
        65 Raw entry=('p', '“\\add Yes,\\add* it would become unclean,” the priests¦376121 answered¦376120.')
        66 Raw entry=('p', '')
        67 Raw entry=('v', "14 “\\add ≈That's what Yahweh¦376139 declares about you\\add* people¦376129,” Haggai¦376126 \\add ≈continued¦376125\\add*. “\\add He says that\\add* \\add ≈that's how this country¦376134 acts towards him\\add*. \\add ≈Your actions are dishonourable, and¦376125 then¦376125 that same disrespect transfers to your offerings\\add*.")
        68 Raw entry=('rem', '/s1 The Lord Promises His Blessing')
        69 Raw entry=('v', "15 So¦376151 now think back to before¦376161 stones were being laid for Yahweh's¦376169 temple.")
        70 Raw entry=('v', '16 \\add ≈During that time\\add*, when someone went to get twenty \\add containers of grain\\add*, there were \\add only\\add* ten¦376178 there, and when someone went to fill fifty¦376184 \\add jars of wine\\add* from the vat, there was \\add only enough for\\add* twenty.')
        71 Raw entry=('v', "17 Yahweh¦376205 declares that he \\add ≈caused\\add* blight¦376191 and mildew¦376192 and hail to affect your work¦376197, \\add ≈but¦376192\\add* you \\add still\\add* didn't¦376199 turn to him.")
        72 Raw entry=('v', "18 Think back to the time from when the foundation¦376225 of Yahweh's¦376228 temple¦376226 was laid, until today (this 24th of the ninth¦376219 month¦376219). Consider that.")
        73 Raw entry=('v', "19 Is \\add any grain\\add* left in¦376234 the storehouse for seed? \\add What's more,\\add* the vines, and the fig¦376238 trees and pomegranate¦376239 trees and olive trees, haven't produced fruit. \\add However,\\add* Yahweh will bless you from today onwards.”")
        74 Raw entry=('s1', "God's promise to Zerubavel")
        75 Raw entry=('rem', "/s1 The Lord's Promise to Zerubbabel; God's Promise to Zerubbabel; Promises for Zerubbabel; Zerubbabel the Lord's Signet Ring")
        76 Raw entry=('p', '')
        77 Raw entry=('v', '20 Then Yahweh¦376254 gave a second¦376256 message¦376252 to Haggai¦376259 on¦376260 the 24th:')
        78 Raw entry=('v', "21 Tell Zerubavel, the governor¦376269 of Yehudah¦376271, “I'm \\add about¦376274 to\\add* shake¦376274 the heavens¦376277 and the earth¦376280.")
        79 Raw entry=('v', "22 I'll overthrow the thrones¦376283 of kingdoms¦376288, and destroy¦376285 the strength¦376286 of the nations¦376288. I'll overthrow chariots¦376290 and riders—horses¦376293 and their¦376294 riders will fall and \\add related tribes\\add* \\add ≈will kill¦376285 each other\\add*.")
        80 Raw entry=('v', "23 Commander-in-chief Yahweh declares that on that day¦376299 he will take¦376305 Shealtiyel's son Zerubavel and \\add ≈cause him to place Yahweh's¦376303 mark on the nation\\add* like a signet¦376315 ring, because¦376316 he's been chosen¦376319.”")
 */

        let nested = add_nesting_markers(entries, "OET-RV", "HAG");
        let with_v_equals = add_verse_start_markers(nested);
        
        println!("Final entries: {}", with_v_equals.len());
        for (i, entry) in with_v_equals.iter().enumerate() {
            println!("{:3}: {} = {:?}", i, entry.marker(), entry.clean_text());
        }

        assert_eq!(with_v_equals.len(), 183, "Expected 183 entries after nesting and verse start markers");
    }
}
