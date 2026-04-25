//! USFM nesting and end marker logic.

use compact_str::CompactString;

use crate::entry::InternalBibleEntry;
use crate::entry_extras::InternalBibleEntryList;
use crate::markers::{
    heading_markers, intro_list_markers, intro_outline_markers, introduction_markers,
    is_never_content_marker, main_text_list_markers, major_section_markers, paragraph_markers,
};

/// Add nesting and end markers to a list of processed Bible entries.
///
/// This is the Rust equivalent of the Python `_addNestingMarkers` function.
/// It also calls `add_verse_start_markers` internally to provide a complete
/// structural processing in one call, though the functions remain available.
/// 
/// Note that although nb is considered as a USFM paragraph marker,
///   in the BibleOrgSys nesting it acts as a NOP (no-operation)
///   so it does not cause an existing paragraph to end (¬nb is never added).
pub fn add_nesting_markers(
    entries: InternalBibleEntryList,
    work_name: &str,
    bos_book_code: &str,
) -> InternalBibleEntryList {
    log::info!(
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
    let mut current_verse = CompactString::from("-1");
    let mut last_marker: Option<CompactString> = None;
    let mut last_p_marker: Option<CompactString> = None;
    let mut last_s_marker: Option<CompactString> = None;

    // Helper functions for look-ahead
    let chapter_has_ended = |start_idx: usize, entries: &[InternalBibleEntry]| {
        for entry in entries.iter().skip(start_idx + 1) {
            let m = entry.marker();
            if m == "c" {
                return true;
            }
            if matches!(m, "v" | "v~" | "p~") {
                return false;
            }
        }
        true
    };

    let verse_has_ended = |start_idx: usize, entries: &[InternalBibleEntry]| {
        for entry in entries.iter().skip(start_idx + 1) {
            let m = entry.marker();
            if matches!(m, "v" | "c") {
                return true;
            }
            if matches!(m, "v~" | "p~") {
                return false;
            }
        }
        true
    };

    let section_has_ended = |current_marker: &str, start_idx: usize, entries: &[InternalBibleEntry]| {
        let mut other_possibilities = Vec::new();
        if let Some(level_char) = current_marker.chars().last()
            && level_char.is_ascii_digit()
            && level_char > '1'
        {
            let level = level_char.to_digit(10).unwrap();
            let base = &current_marker[..current_marker.len() - 1];
            for z in 1..level {
                other_possibilities.push(format!("{}{}", base, z));
            }
        }
        if matches!(current_marker, "s1" | "s2" | "s3" | "s4") {
            other_possibilities.push("ms1".to_string());
        }

        for entry in entries.iter().skip(start_idx + 1) {
            let m = entry.marker();
            if m == current_marker || other_possibilities.iter().any(|p| p == m) {
                return true;
            }
            if matches!(m, "v" | "v~" | "p~") {
                return false;
            }
        }
        true
    };

    let paragraph_has_ended = |start_idx: usize, entries: &[InternalBibleEntry]| {
        for entry in entries.iter().skip(start_idx + 1) {
            let m = entry.marker();
            if paragraph_markers::is_paragraph(m) || main_text_list_markers::is_main_text_list(m) {
                return true;
            }
            if matches!(m, "v" | "v~" | "p~") {
                return false;
            }
        }
        true
    };

    let find_next_relevant_marker = |start_idx: usize, entries: &[InternalBibleEntry]| {
        for entry in entries.iter().skip(start_idx + 1) {
            let m = entry.marker();
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
        for entry in entries.iter().skip(start_idx + 1) {
            let m = entry.marker();
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
            current_verse = CompactString::from(new_lines.len().to_string());
        }

        // Header and Intro logic
        if marker == "h" && !open_markers.iter().any(|m| m == "headers") {
            new_lines.push(InternalBibleEntry::nesting_marker("headers"));
            open_markers.push(CompactString::from("headers"));
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

        if let Some(last_open) = open_markers.last().map(|s| s.to_string())
            && last_open == "iot"
            && !intro_outline_markers::is_intro_outline(marker)
        {
            open_markers.pop();
            new_lines.push(InternalBibleEntry::simple("¬iot", ""));
        }
        if let Some(last_open) = open_markers.last().map(|s| s.to_string())
            && last_open == "ilist"
            && !intro_list_markers::is_intro_list(marker)
        {
            open_markers.pop();
            new_lines.push(InternalBibleEntry::simple("¬ilist", ""));
        }
        if let Some(last_open) = open_markers.last().map(|s| s.to_string())
            && last_open == "list"
            && !main_text_list_markers::is_main_text_list(marker)
            && marker != "v~"
            && marker != "p~"
        {
            let close = if let Some(next_list_m) = find_next_relevant_list_marker(j, &entries_vec) {
                !main_text_list_markers::is_main_text_list(next_list_m.as_str())
            } else {
                true
            };
            if close {
                open_markers.pop();
                new_lines.push(InternalBibleEntry::simple("¬list", ""));
            }
        }

        // Chapter logic
        if marker == "nb" {
            // nb is a NOP for nesting
        } else if marker == "c" {
            if let Some(last_open) = open_markers.last().map(|s| s.to_string())
                && (last_open == "headers" || last_open == "intro")
            {
                open_markers.pop();
                new_lines.push(InternalBibleEntry::simple(format!("¬{}", last_open), ""));
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
                if let Some(last_open_m) = open_markers.last().map(|s| s.to_string())
                    && paragraph_markers::is_paragraph(&last_open_m)
                    && let Some(nr) = next_rel.as_ref()
                    && (paragraph_markers::is_paragraph(nr.as_str()) || heading_markers::is_heading(nr.as_str()))
                {
                    open_markers.pop();
                    new_lines.push(InternalBibleEntry::simple(format!("¬{}", last_open_m), ""));
                }
                if let Some(last_open_m) = open_markers.last().map(|s| s.to_string())
                    && heading_markers::is_heading(&last_open_m)
                    && let Some(nr) = next_rel.as_ref()
                    && heading_markers::is_heading(nr.as_str())
                {
                    open_markers.pop();
                    new_lines.push(InternalBibleEntry::simple(format!("¬{}", last_open_m), ""));
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
                    } else if let Some(last_p) = &last_p_marker
                        && last_open_m == last_p.as_str()
                        && paragraph_has_ended(j, &entries_vec)
                    {
                        open_markers.pop();
                        new_lines.push(InternalBibleEntry::simple(format!("¬{}", last_open_m), ""));
                        made_change = true;
                    }
                }
                if !made_change {
                    break;
                }
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
            } else {
                true
            };
            if should_open {
                new_lines.push(InternalBibleEntry::nesting_marker("iot"));
                open_markers.push(CompactString::from("iot"));
            }
        } else if intro_list_markers::is_intro_list(marker) {
            let should_open = last_marker
                .as_ref()
                .is_none_or(|lm| !intro_list_markers::is_intro_list(lm));
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
                        if last_open_m == last_p.as_str() {
                            open_markers.pop();
                            new_lines.push(InternalBibleEntry::simple(format!("¬{}", last_open_m), ""));
                            made_change = true;
                        }
                    } else if let Some(last_s) = &last_s_marker
                        && last_open_m == last_s.as_str()
                        && section_has_ended(last_s, j, &entries_vec)
                    {
                        open_markers.pop();
                        new_lines.push(InternalBibleEntry::simple(format!("¬{}", last_open_m), ""));
                        made_change = true;
                    }
                }
                if !made_change {
                    break;
                }
            }
            if verse_has_ended(j, &entries_vec)
                && let Some(pos) = open_markers.iter().rposition(|m| m == "v")
            {
                let m = open_markers.remove(pos);
                new_lines.push(InternalBibleEntry::simple(format!("¬{}", m), current_verse.as_str()));
            }
            if let Some(lp) = &last_p_marker
                && let Some(pos) = open_markers.iter().rposition(|m| m == lp)
            {
                let m = open_markers.remove(pos);
                new_lines.push(InternalBibleEntry::simple(format!("¬{}", m), ""));
            }
            if let Some(ls) = &last_s_marker
                && let Some(pos) = open_markers.iter().rposition(|m| m == ls)
            {
                let m = open_markers.remove(pos);
                new_lines.push(InternalBibleEntry::simple(format!("¬{}", m), ""));
            }
            last_p_marker = None;
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
                        if last_open_m == last_p.as_str() {
                            open_markers.pop();
                            new_lines.push(InternalBibleEntry::simple(format!("¬{}", last_open_m), ""));
                            made_change = true;
                        }
                    } else if let Some(last_s) = &last_s_marker {
                        if last_open_m == last_s.as_str() && section_has_ended(last_s, j, &entries_vec) {
                            open_markers.pop();
                            new_lines.push(InternalBibleEntry::simple(format!("¬{}", last_open_m), ""));
                            made_change = true;
                        }
                    } else if last_open_m == "c" && chapter_has_ended(j, &entries_vec) {
                        open_markers.pop();
                        new_lines.push(InternalBibleEntry::simple("¬c", current_chapter.as_str()));
                        made_change = true;
                    } else if last_open_m == marker {
                        open_markers.pop();
                        new_lines.push(InternalBibleEntry::simple(format!("¬{}", marker), ""));
                        made_change = true;
                    }
                }
                if !made_change {
                    break;
                }
            }

            if !open_markers.iter().any(|m| m == "chapters") {
                new_lines.push(InternalBibleEntry::nesting_marker("chapters"));
                open_markers.push(CompactString::from("chapters"));
            } else if let Some(lp) = &last_p_marker
                && let Some(pos) = open_markers.iter().rposition(|m| m == lp)
            {
                let m = open_markers.remove(pos);
                new_lines.push(InternalBibleEntry::simple(format!("¬{}", m), ""));
            }

            if let Some(ls) = &last_s_marker
                && let Some(pos) = open_markers.iter().rposition(|m| m == ls)
            {
                let m = open_markers.remove(pos);
                new_lines.push(InternalBibleEntry::simple(format!("¬{}", m), ""));
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
                    } else if let Some(last_p) = &last_p_marker
                        && last_open_m == last_p.as_str()
                    {
                        open_markers.pop();
                        new_lines.push(InternalBibleEntry::simple(format!("¬{}", last_open_m), ""));
                        made_change = true;
                    }
                }
                if !made_change {
                    break;
                }
            }
            if verse_has_ended(j, &entries_vec)
                && let Some(pos) = open_markers.iter().rposition(|m| m == "v")
            {
                let m = open_markers.remove(pos);
                new_lines.push(InternalBibleEntry::simple(format!("¬{}", m), current_verse.as_str()));
            }
            if let Some(lp) = &last_p_marker
                && let Some(pos) = open_markers.iter().rposition(|m| m == lp)
            {
                let m = open_markers.remove(pos);
                new_lines.push(InternalBibleEntry::simple(format!("¬{}", m), ""));
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
                    } else if let Some(last_p) = &last_p_marker
                        && last_open_m == last_p.as_str()
                    {
                        open_markers.pop();
                        new_lines.push(InternalBibleEntry::simple(format!("¬{}", last_open_m), ""));
                        made_change = true;
                    }
                }
                if !made_change {
                    break;
                }
            }
            if verse_has_ended(j, &entries_vec)
                && let Some(pos) = open_markers.iter().rposition(|m| m == "v")
            {
                let m = open_markers.remove(pos);
                new_lines.push(InternalBibleEntry::simple(format!("¬{}", m), current_verse.as_str()));
            }
            if let Some(lp) = &last_p_marker
                && let Some(pos) = open_markers.iter().rposition(|m| m == lp)
            {
                let m = open_markers.remove(pos);
                new_lines.push(InternalBibleEntry::simple(format!("¬{}", m), ""));
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
                    } else if let Some(last_p) = &last_p_marker
                        && last_open_m == last_p.as_str()
                    {
                        open_markers.pop();
                        new_lines.push(InternalBibleEntry::simple(format!("¬{}", last_open_m), ""));
                        made_change = true;
                    }
                }
                if !made_change {
                    break;
                }
            }
            if verse_has_ended(j, &entries_vec)
                && let Some(pos) = open_markers.iter().rposition(|m| m == "v")
            {
                let m = open_markers.remove(pos);
                new_lines.push(InternalBibleEntry::simple(format!("¬{}", m), current_verse.as_str()));
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

    log::info!("    add_nesting_markers for {} finishing with {} entries", bos_book_code, new_lines.len());
    
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
                        result.push(
                            InternalBibleEntry::new(
                                "v=",
                                "v",
                                next_entry.adjusted_text().unwrap_or(""),
                                next_entry.clean_text(),
                                None,
                                next_entry.original_text().unwrap_or(""),
                            )
                            .expect("Valid internal entry"),
                        );
                        break; // Only add one v= for this preceded field
                    } else if !fields_also_preceded.contains(&next_marker)
                        && !next_marker.starts_with('¬')
                        && next_marker != "rem"
                    {
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
    use std::fs::File;
    use std::io::{BufRead, BufReader};

    #[test]
    fn test_oet_lv_haggai_nesting() {
        let file_path = "test_data/OET-LV_HAG.ESFM";
        let file = File::open(file_path).expect("Could not open OET-LV Haggai ESFM file");
        let reader = BufReader::new(file);

        let mut raw_lines = Vec::new();
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
            raw_lines.push((marker.to_string(), text.to_string()));
        }
        
        // Results should match test_data/OET-LV_HAG_rawLines.txt
        let original_count = raw_lines.len();
        println!("Original lines read: {}", original_count);
        assert_eq!(original_count, 57, "Expected 57 raw lines in Haggai ESFM file");

        let options = crate::processing::ProcessLinesOptions::default();
        let processed = crate::processing::process_lines(raw_lines, "HAG", "OET-LV", &options);
        
        println!("Final entries: {}", processed.len());

        assert_eq!(processed.len(), 141, "{}", processed.iter().map(|e| e.marker()).collect::<Vec<_>>().join(","));
        
        // Verify some key structural markers from the reference test
        assert_eq!(processed[9].marker(), "headers");
        assert_eq!(processed[16].marker(), "¬headers");
        assert_eq!(processed[17].marker(), "chapters");
        assert_eq!(processed[18].marker(), "c");
        assert_eq!(processed[140].marker(), "¬chapters");
    }

    #[test]
    fn test_oet_rv_haggai_nesting() {
        let file_path = "test_data/OET-RV_HAG.ESFM";
        let file = File::open(file_path).expect("Could not open OET-RV Haggai ESFM file");
        let reader = BufReader::new(file);

        let mut raw_lines = Vec::new();
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
            raw_lines.push((marker.to_string(), text.to_string()));
        }
        
        let original_count = raw_lines.len();
        println!("Original lines read: {}", original_count);
        assert_eq!(original_count, 81, "Expected 81 raw lines in Haggai ESFM file");

        let options = crate::processing::ProcessLinesOptions::default();
        let processed = crate::processing::process_lines(raw_lines, "HAG", "OET-RV", &options);
        
        println!("Final entries: {}", processed.len());

        assert_eq!(processed.len(), 188, "Expected 188 entries after nesting and verse start markers");
        
        // Verify some key structural markers from the reference test
        assert_eq!(processed[5].marker(), "headers");
        assert_eq!(processed[11].marker(), "¬headers");
        assert_eq!(processed[12].marker(), "intro");
        assert_eq!(processed[21].marker(), "¬intro");
        assert_eq!(processed[22].marker(), "chapters");
        assert_eq!(processed[23].marker(), "c");
        assert_eq!(processed[24].marker(), "v=");
        assert_eq!(processed[186].marker(), "¬c");
        assert_eq!(processed[187].marker(), "¬chapters");
    }
}
