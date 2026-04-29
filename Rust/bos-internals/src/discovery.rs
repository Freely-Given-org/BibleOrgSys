//! Bible discovery logic for calculating statistics and identifying features.

use crate::entry_extras::InternalBibleEntryList;
use crate::markers::{ExtraType, is_printable_marker};
use crate::parsing::strip_word_ends_punctuation;
use indexmap::IndexMap;
use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

pub const BOOKLIST_OT39: &[&str] = &[
    "GEN", "EXO", "LEV", "NUM", "DEU", "JOS", "JDG", "RUT", "1SA", "2SA", "1KI", "2XY", "1CH", "2CH", "EZR", "NEH", "EST", "JOB", "PSA", "PRO", "ECC", "SNG", "ISA", "JER", "LAM", "EZK", "DAN", "HOS", "JOL", "AMO", "OBA", "JON", "MIC", "NAM", "HAB", "ZEP", "HAG", "ZEC", "MAL",
];
pub const BOOKLIST_NT27: &[&str] = &[
    "MAT", "MRK", "LUK", "JHN", "ACT", "ROM", "1CO", "2CO", "GAL", "EPH", "PHP", "COL", "1TH", "2TH", "1TI", "2TI", "TIT", "PHM", "HEB", "JAS", "1PE", "2PE", "1JN", "2JN", "3JN", "JUD", "REV",
];
pub const BOOKLIST_DC: &[&str] = &[
    "TOB", "JDT", "ESG", "WIS", "SIR", "BAR", "LJE", "S3Y", "SUS", "BEL", "1MA", "2MA", "3MA", "4MA", "1ES", "2ES", "MAN", "PS2", "ODA", "PSS", "EZA", "5EZ", "6EZ", "DAG", "PS3", "2BA", "LBA", "JUB", "ENO", "1MQ", "2MQ", "3MQ", "REP", "4BA", "LAO",
];

pub fn is_ot(bbb: &str) -> bool { BOOKLIST_OT39.contains(&bbb) }
pub fn is_nt(bbb: &str) -> bool { BOOKLIST_NT27.contains(&bbb) }
pub fn is_dc(bbb: &str) -> bool { BOOKLIST_DC.contains(&bbb) }

/// Discovery results for a single Bible book.
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
#[serde(rename_all = "camelCase")]
pub struct BookDiscoveryResults {
    pub chapter_count: Option<u16>,
    pub verse_count: Option<u16>,
    pub completed_verse_count: u16,
    pub percentage_progress: Option<u8>,
    pub have_populated_cv_markers: bool,
    pub have_paragraph_markers: bool,
    pub have_introductory_markers: bool,
    pub have_main_headings: bool,
    pub main_headings_count: u16,
    pub have_section_headings: bool,
    pub section_headings_count: u16,
    pub have_section_references: bool,
    pub section_references_count: u16,
    pub have_tables: bool,
    pub have_lists: bool,
    pub figures_count: u16,
    pub have_footnotes: bool,
    pub have_footnote_origins: bool,
    pub footnotes_count: u16,
    pub have_cross_references: bool,
    pub have_cross_reference_origins: bool,
    pub cross_references_count: u16,
    pub section_references_parenthesis_ratio: f32,
    pub footnotes_period_ratio: f32,
    pub cross_references_period_ratio: f32,
    pub have_introductory_text: bool,
    pub have_verse_text: bool,
    pub have_nested_usf_markers: bool,
    pub seems_finished: Option<bool>,
    pub not_started: bool,
    pub partly_done: bool,
    pub word_count: u32,
    pub unique_word_count: u32,
    pub all_word_counts: HashMap<String, u32>,
    pub all_case_insensitive_word_counts: HashMap<String, u32>,
    pub main_text_word_counts: HashMap<String, u32>,
    pub main_text_case_insensitive_word_counts: HashMap<String, u32>,
}

/// Discovery results for an entire Bible.
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
#[serde(rename_all = "camelCase")]
pub struct BibleDiscoveryResults {
    pub books: HashMap<String, BookDiscoveryResults>,
    pub all: AggregateDiscoveryResults,
}

/// Aggregated discovery results for all books.
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
#[serde(rename_all = "camelCase")]
pub struct AggregateDiscoveryResults {
    pub ot_book_count: u16,
    pub ot_book_codes: Vec<String>,
    pub nt_book_count: u16,
    pub nt_book_codes: Vec<String>,
    pub dc_book_count: u16,
    pub dc_book_codes: Vec<String>,
    pub other_book_count: u16,
    pub other_book_codes: Vec<String>,
    pub not_started_book_codes: Vec<String>,
    pub ot_not_started_book_codes: Vec<String>,
    pub nt_not_started_book_codes: Vec<String>,
    pub dc_not_started_book_codes: Vec<String>,
    pub other_not_started_book_codes: Vec<String>,
    pub seems_finished_book_codes: Vec<String>,
    pub ot_seems_finished_book_codes: Vec<String>,
    pub nt_seems_finished_book_codes: Vec<String>,
    pub dc_seems_finished_book_codes: Vec<String>,
    pub other_seems_finished_book_codes: Vec<String>,
    pub partly_done_book_codes: Vec<String>,
    pub ot_partly_done_book_codes: Vec<String>,
    pub nt_partly_done_book_codes: Vec<String>,
    pub dc_partly_done_book_codes: Vec<String>,
    pub other_partly_done_book_codes: Vec<String>,
    pub percentage_progress_by_book: String,
    pub ot_percentage_progress_by_book: String,
    pub nt_percentage_progress_by_book: String,
    pub dc_percentage_progress_by_book: String,
    pub percentage_progress_by_verse: String,
    pub ot_percentage_progress_by_verse: String,
    pub nt_percentage_progress_by_verse: String,
    pub dc_percentage_progress_by_verse: String,
    pub verse_count: u32,
    pub ot_verse_count: u32,
    pub nt_verse_count: u32,
    pub dc_verse_count: u32,
    pub other_verse_count: u32,
    pub completed_verse_count: u32,
    pub ot_completed_verse_count: u32,
    pub nt_completed_verse_count: u32,
    pub dc_completed_verse_count: u32,
    pub other_completed_verse_count: u32,
    pub word_count: u32,
    pub all_word_counts: HashMap<String, u32>,
    pub all_case_insensitive_word_counts: HashMap<String, u32>,
    pub main_text_word_counts: HashMap<String, u32>,
    pub main_text_case_insensitive_word_counts: HashMap<String, u32>,
    pub section_references_parenthesis_flag: Option<bool>,
    pub footnotes_period_flag: Option<bool>,
    pub cross_references_period_flag: Option<bool>,

    // Boolean summary counts (counts of books having these features)
    pub have_populated_cv_markers: u16,
    pub ot_have_populated_cv_markers: u16,
    pub nt_have_populated_cv_markers: u16,
    pub dc_have_populated_cv_markers: u16,
    pub other_have_populated_cv_markers: u16,

    pub have_paragraph_markers: u16,
    pub ot_have_paragraph_markers: u16,
    pub nt_have_paragraph_markers: u16,
    pub dc_have_paragraph_markers: u16,
    pub other_have_paragraph_markers: u16,

    pub have_introductory_markers: u16,
    pub ot_have_introductory_markers: u16,
    pub nt_have_introductory_markers: u16,
    pub dc_have_introductory_markers: u16,
    pub other_have_introductory_markers: u16,

    pub have_main_headings: u16,
    pub ot_have_main_headings: u16,
    pub nt_have_main_headings: u16,
    pub dc_have_main_headings: u16,
    pub other_have_main_headings: u16,

    pub have_section_headings: u16,
    pub ot_have_section_headings: u16,
    pub nt_have_section_headings: u16,
    pub dc_have_section_headings: u16,
    pub other_have_section_headings: u16,

    pub have_section_references: u16,
    pub ot_have_section_references: u16,
    pub nt_have_section_references: u16,
    pub dc_have_section_references: u16,
    pub other_have_section_references: u16,

    pub have_tables: u16,
    pub ot_have_tables: u16,
    pub nt_have_tables: u16,
    pub dc_have_tables: u16,
    pub other_have_tables: u16,

    pub have_lists: u16,
    pub ot_have_lists: u16,
    pub nt_have_lists: u16,
    pub dc_have_lists: u16,
    pub other_have_lists: u16,

    pub have_footnotes: u16,
    pub ot_have_footnotes: u16,
    pub nt_have_footnotes: u16,
    pub dc_have_footnotes: u16,
    pub other_have_footnotes: u16,

    pub have_footnote_origins: u16,
    pub ot_have_footnote_origins: u16,
    pub nt_have_footnote_origins: u16,
    pub dc_have_footnote_origins: u16,
    pub other_have_footnote_origins: u16,

    pub have_cross_references: u16,
    pub ot_have_cross_references: u16,
    pub nt_have_cross_references: u16,
    pub dc_have_cross_references: u16,
    pub other_have_cross_references: u16,

    pub have_cross_reference_origins: u16,
    pub ot_have_cross_reference_origins: u16,
    pub nt_have_cross_reference_origins: u16,
    pub dc_have_cross_reference_origins: u16,
    pub other_have_cross_reference_origins: u16,

    pub have_introductory_text: u16,
    pub ot_have_introductory_text: u16,
    pub nt_have_introductory_text: u16,
    pub dc_have_introductory_text: u16,
    pub other_have_introductory_text: u16,

    pub have_verse_text: u16,
    pub ot_have_verse_text: u16,
    pub nt_have_verse_text: u16,
    pub dc_have_verse_text: u16,
    pub other_have_verse_text: u16,

    pub have_nested_usf_markers: u16,
    pub ot_have_nested_usf_markers: u16,
    pub nt_have_nested_usf_markers: u16,
    pub dc_have_nested_usf_markers: u16,
    pub other_have_nested_usf_markers: u16,
}

impl BookDiscoveryResults {
    pub fn new() -> Self {
        Self {
            section_references_parenthesis_ratio: -1.0,
            footnotes_period_ratio: -1.0,
            cross_references_period_ratio: -1.0,
            ..Default::default()
        }
    }
}

/// Perform discovery on a single Bible book.
pub fn discover_book(entries: &InternalBibleEntryList, _bbb: &str) -> BookDiscoveryResults {
    let mut results = BookDiscoveryResults::new();
    let mut section_ref_parenth_count: u16 = 0;
    let mut footnotes_period_count: u16 = 0;
    let mut xrefs_period_count: u16 = 0;

    let mut last_marker: Option<String> = None;

    for entry in entries.iter() {
        let marker = entry.marker();
        if marker.starts_with('¬') {
            continue;
        }

        let clean_text = entry.clean_text();
        let extras = entry.extras();

        if marker == "c" {
            results.chapter_count = Some(results.chapter_count.unwrap_or(0) + 1);
        } else if marker == "v" {
            results.verse_count = Some(results.verse_count.unwrap_or(0) + 1);
            if results.chapter_count.is_none() {
                results.chapter_count = Some(1);
            }
            results.have_populated_cv_markers = true;
            if results.seems_finished.is_none() {
                results.seems_finished = Some(true);
            }
        } else if marker == "v~" {
            results.have_verse_text = true;
            results.completed_verse_count += 1;
        } else if matches!(marker, "mt" | "mt1" | "mt2" | "mt3" | "mt4") {
            results.have_main_headings = true;
            results.main_headings_count += 1;
        } else if matches!(marker, "s" | "s1" | "s2" | "s3" | "s4" | "qa") {
            results.have_section_headings = true;
            results.section_headings_count += 1;
        } else if marker == "r" && !clean_text.is_empty() {
            results.have_section_references = true;
            results.section_references_count += 1;
            if clean_text.starts_with('(') && clean_text.ends_with(')') {
                section_ref_parenth_count += 1;
            }
        } else if crate::markers::paragraph_markers::is_paragraph(marker) {
            results.have_paragraph_markers = true;
            if !clean_text.is_empty() {
                results.have_verse_text = true;
            }
        } else if matches!(marker, "is" | "is1" | "ip" | "iot" | "io1") {
            results.have_introductory_markers = true;
            if !clean_text.is_empty() {
                results.have_introductory_text = true;
            }
        } else if marker == "tr" {
            results.have_tables = true;
        } else if marker == "li" || marker == "li1" {
            results.have_lists = true;
        }

        if last_marker.as_deref() == Some("v") && (marker != "v~" || clean_text.is_empty()) {
            results.seems_finished = Some(false);
        }

        if !clean_text.is_empty() {
            if clean_text.contains("\\+") {
                results.have_nested_usf_markers = true;
            }
            results.figures_count += clean_text.matches("\\fig ").count() as u16;
            if is_printable_marker(marker) {
                count_words(marker, clean_text, true, &mut results);
            }
        }

        if let Some(extras) = extras {
            for extra in extras.iter() {
                let extra_type = extra.extra_type();
                let note_text = extra.note_text();
                let clean_note_text = extra.clean_note_text();

                if extra_type == ExtraType::Footnote {
                    results.have_footnotes = true;
                    results.footnotes_count += 1;
                    if note_text.contains("\\fr") {
                        results.have_footnote_origins = true;
                    }
                    if is_sentence_ended(clean_note_text) {
                        footnotes_period_count += 1;
                    }
                } else if extra_type == ExtraType::CrossRef {
                    results.have_cross_references = true;
                    results.cross_references_count += 1;
                    if note_text.contains("\\xo") {
                        results.have_cross_reference_origins = true;
                    }
                    if is_sentence_ended(clean_note_text) {
                        xrefs_period_count += 1;
                    }
                }

                if !matches!(extra_type, ExtraType::Figure | ExtraType::WordWithAttributes) {
                    count_words(extra_type.type_str(), clean_note_text, false, &mut results);
                }
            }
        }
        last_marker = Some(marker.to_string());
    }

    results.unique_word_count = results.all_word_counts.len() as u32;

    if results.verse_count.is_none() {
        // Front matter, etc.
    } else {
        if !results.have_verse_text {
            results.seems_finished = Some(false);
        }
        if let Some(vc) = results.verse_count {
            results.percentage_progress = Some((results.completed_verse_count as f32 * 100.0 / vc as f32).round() as u8);
            if results.percentage_progress.unwrap_or(0) > 100 {
                results.percentage_progress = Some(100);
            }
        }
        results.not_started = !results.have_verse_text;
        results.partly_done = results.have_verse_text && !results.seems_finished.unwrap_or(false);
    }

    if results.section_references_count > 0 {
        results.section_references_parenthesis_ratio = section_ref_parenth_count as f32 / results.section_references_count as f32;
    }
    if results.footnotes_count > 0 {
        results.footnotes_period_ratio = footnotes_period_count as f32 / results.footnotes_count as f32;
    }
    if results.cross_references_count > 0 {
        results.cross_references_period_ratio = xrefs_period_count as f32 / results.cross_references_count as f32;
    }

    results
}

fn is_sentence_ended(text: &str) -> bool {
    let text = text.trim();
    text.ends_with('.') || text.ends_with('።') || text.ends_with(".”") || text.ends_with("’")
}

fn count_words(marker: &str, segment: &str, is_main: bool, results: &mut BookDiscoveryResults) {
    let words = segment.replace('—', " ").replace('–', " ");
    let words = words.split_whitespace();

    for (j, raw_word) in words.enumerate() {
        if marker == "c" || (marker == "v" && j == 1 && raw_word.chars().all(|c| c.is_ascii_digit())) {
            continue;
        }

        let mut word = raw_word.to_string();
        
        // Remove internal markers (simplified version of Python logic)
        if word.contains('\\') {
            // Very basic marker removal: remove anything that looks like \+?marker*?
            // This is a rough approximation of the Python logic
            if let Ok(re) = regex::Regex::new(r"\\\+?[a-z1-4]+\*?") {
                word = re.replace_all(&word, "").to_string();
            }
        }
        
        word = strip_word_ends_punctuation(&word);
        if word.is_empty() {
            continue;
        }
        
        if !word.chars().next().unwrap().is_alphanumeric() && word.len() > 1 {
            word = word.chars().skip(1).collect();
            word = strip_word_ends_punctuation(&word);
        }

        if word.is_empty() {
            continue;
        }

        // Check if it's a number or reference
        if word.chars().all(|c| c.is_ascii_digit() || ":-,.".contains(c)) {
            continue;
        }

        results.word_count += 1;
        let lc_word = word.to_lowercase();
        
        *results.all_word_counts.entry(word.clone()).or_insert(0) += 1;
        *results.all_case_insensitive_word_counts.entry(lc_word.clone()).or_insert(0) += 1;

        if is_main {
            *results.main_text_word_counts.entry(word).or_insert(0) += 1;
            *results.main_text_case_insensitive_word_counts.entry(lc_word).or_insert(0) += 1;
        }
    }
}

/// Perform discovery on an entire Bible, using multiple cores.
pub fn discover_bible(books: &IndexMap<String, InternalBibleEntryList>) -> BibleDiscoveryResults {
    let mut results = BibleDiscoveryResults::default();

    // Parallel book processing
    results.books = books.par_iter()
        .map(|(bbb, entries)| {
            (bbb.clone(), discover_book(entries, bbb))
        })
        .collect();

    aggregate_results(&mut results);
    results
}

fn aggregate_results(results: &mut BibleDiscoveryResults) {
    let agg = &mut results.all;
    let mut section_ref_ratios = Vec::new();
    let mut footnote_ratios = Vec::new();
    let mut xref_ratios = Vec::new();

    let mut total_progress_by_book: f32 = 0.0;
    let mut ot_progress_by_book: f32 = 0.0;
    let mut nt_progress_by_book: f32 = 0.0;
    let mut dc_progress_by_book: f32 = 0.0;

    for (bbb, bk) in &results.books {
        let is_ot_book = is_ot(bbb);
        let is_nt_book = is_nt(bbb);
        let is_dc_book = is_dc(bbb);

        if is_ot_book {
            agg.ot_book_count += 1;
            agg.ot_book_codes.push(bbb.clone());
        } else if is_nt_book {
            agg.nt_book_count += 1;
            agg.nt_book_codes.push(bbb.clone());
        } else if is_dc_book {
            agg.dc_book_count += 1;
            agg.dc_book_codes.push(bbb.clone());
        } else {
            agg.other_book_count += 1;
            agg.other_book_codes.push(bbb.clone());
        }

        if bk.not_started {
            agg.not_started_book_codes.push(bbb.clone());
            if is_ot_book { agg.ot_not_started_book_codes.push(bbb.clone()); }
            else if is_nt_book { agg.nt_not_started_book_codes.push(bbb.clone()); }
            else if is_dc_book { agg.dc_not_started_book_codes.push(bbb.clone()); }
            else { agg.other_not_started_book_codes.push(bbb.clone()); }
        }
        if bk.seems_finished.unwrap_or(false) {
            agg.seems_finished_book_codes.push(bbb.clone());
            if is_ot_book { agg.ot_seems_finished_book_codes.push(bbb.clone()); }
            else if is_nt_book { agg.nt_seems_finished_book_codes.push(bbb.clone()); }
            else if is_dc_book { agg.dc_seems_finished_book_codes.push(bbb.clone()); }
            else { agg.other_seems_finished_book_codes.push(bbb.clone()); }
        }
        if bk.partly_done {
            agg.partly_done_book_codes.push(bbb.clone());
            if is_ot_book { agg.ot_partly_done_book_codes.push(bbb.clone()); }
            else if is_nt_book { agg.nt_partly_done_book_codes.push(bbb.clone()); }
            else if is_dc_book { agg.dc_partly_done_book_codes.push(bbb.clone()); }
            else { agg.other_partly_done_book_codes.push(bbb.clone()); }
        }

        // Manual expansion because macro concat_idents is unstable/tricky
        if bk.have_populated_cv_markers {
            agg.have_populated_cv_markers += 1;
            if is_ot_book { agg.ot_have_populated_cv_markers += 1; }
            else if is_nt_book { agg.nt_have_populated_cv_markers += 1; }
            else if is_dc_book { agg.dc_have_populated_cv_markers += 1; }
            else { agg.other_have_populated_cv_markers += 1; }
        }
        if bk.have_paragraph_markers {
            agg.have_paragraph_markers += 1;
            if is_ot_book { agg.ot_have_paragraph_markers += 1; }
            else if is_nt_book { agg.nt_have_paragraph_markers += 1; }
            else if is_dc_book { agg.dc_have_paragraph_markers += 1; }
            else { agg.other_have_paragraph_markers += 1; }
        }
        if bk.have_introductory_markers {
            agg.have_introductory_markers += 1;
            if is_ot_book { agg.ot_have_introductory_markers += 1; }
            else if is_nt_book { agg.nt_have_introductory_markers += 1; }
            else if is_dc_book { agg.dc_have_introductory_markers += 1; }
            else { agg.other_have_introductory_markers += 1; }
        }
        if bk.have_main_headings {
            agg.have_main_headings += 1;
            if is_ot_book { agg.ot_have_main_headings += 1; }
            else if is_nt_book { agg.nt_have_main_headings += 1; }
            else if is_dc_book { agg.dc_have_main_headings += 1; }
            else { agg.other_have_main_headings += 1; }
        }
        if bk.have_section_headings {
            agg.have_section_headings += 1;
            if is_ot_book { agg.ot_have_section_headings += 1; }
            else if is_nt_book { agg.nt_have_section_headings += 1; }
            else if is_dc_book { agg.dc_have_section_headings += 1; }
            else { agg.other_have_section_headings += 1; }
        }
        if bk.have_section_references {
            agg.have_section_references += 1;
            if is_ot_book { agg.ot_have_section_references += 1; }
            else if is_nt_book { agg.nt_have_section_references += 1; }
            else if is_dc_book { agg.dc_have_section_references += 1; }
            else { agg.other_have_section_references += 1; }
        }
        if bk.have_tables {
            agg.have_tables += 1;
            if is_ot_book { agg.ot_have_tables += 1; }
            else if is_nt_book { agg.nt_have_tables += 1; }
            else if is_dc_book { agg.dc_have_tables += 1; }
            else { agg.other_have_tables += 1; }
        }
        if bk.have_lists {
            agg.have_lists += 1;
            if is_ot_book { agg.ot_have_lists += 1; }
            else if is_nt_book { agg.nt_have_lists += 1; }
            else if is_dc_book { agg.dc_have_lists += 1; }
            else { agg.other_have_lists += 1; }
        }
        if bk.have_footnotes {
            agg.have_footnotes += 1;
            if is_ot_book { agg.ot_have_footnotes += 1; }
            else if is_nt_book { agg.nt_have_footnotes += 1; }
            else if is_dc_book { agg.dc_have_footnotes += 1; }
            else { agg.other_have_footnotes += 1; }
        }
        if bk.have_footnote_origins {
            agg.have_footnote_origins += 1;
            if is_ot_book { agg.ot_have_footnote_origins += 1; }
            else if is_nt_book { agg.nt_have_footnote_origins += 1; }
            else if is_dc_book { agg.dc_have_footnote_origins += 1; }
            else { agg.other_have_footnote_origins += 1; }
        }
        if bk.have_cross_references {
            agg.have_cross_references += 1;
            if is_ot_book { agg.ot_have_cross_references += 1; }
            else if is_nt_book { agg.nt_have_cross_references += 1; }
            else if is_dc_book { agg.dc_have_cross_references += 1; }
            else { agg.other_have_cross_references += 1; }
        }
        if bk.have_cross_reference_origins {
            agg.have_cross_reference_origins += 1;
            if is_ot_book { agg.ot_have_cross_reference_origins += 1; }
            else if is_nt_book { agg.nt_have_cross_reference_origins += 1; }
            else if is_dc_book { agg.dc_have_cross_reference_origins += 1; }
            else { agg.other_have_cross_reference_origins += 1; }
        }
        if bk.have_introductory_text {
            agg.have_introductory_text += 1;
            if is_ot_book { agg.ot_have_introductory_text += 1; }
            else if is_nt_book { agg.nt_have_introductory_text += 1; }
            else if is_dc_book { agg.dc_have_introductory_text += 1; }
            else { agg.other_have_introductory_text += 1; }
        }
        if bk.have_verse_text {
            agg.have_verse_text += 1;
            if is_ot_book { agg.ot_have_verse_text += 1; }
            else if is_nt_book { agg.nt_have_verse_text += 1; }
            else if is_dc_book { agg.dc_have_verse_text += 1; }
            else { agg.other_have_verse_text += 1; }
        }
        if bk.have_nested_usf_markers {
            agg.have_nested_usf_markers += 1;
            if is_ot_book { agg.ot_have_nested_usf_markers += 1; }
            else if is_nt_book { agg.nt_have_nested_usf_markers += 1; }
            else if is_dc_book { agg.dc_have_nested_usf_markers += 1; }
            else { agg.other_have_nested_usf_markers += 1; }
        }

        if let Some(p) = bk.percentage_progress {
            total_progress_by_book += p as f32;
            if is_ot_book { ot_progress_by_book += p as f32; }
            else if is_nt_book { nt_progress_by_book += p as f32; }
            else if is_dc_book { dc_progress_by_book += p as f32; }
        }

        agg.verse_count += bk.verse_count.unwrap_or(0) as u32;
        agg.completed_verse_count += bk.completed_verse_count as u32;
        if is_ot_book {
            agg.ot_verse_count += bk.verse_count.unwrap_or(0) as u32;
            agg.ot_completed_verse_count += bk.completed_verse_count as u32;
        } else if is_nt_book {
            agg.nt_verse_count += bk.verse_count.unwrap_or(0) as u32;
            agg.nt_completed_verse_count += bk.completed_verse_count as u32;
        } else if is_dc_book {
            agg.dc_verse_count += bk.verse_count.unwrap_or(0) as u32;
            agg.dc_completed_verse_count += bk.completed_verse_count as u32;
        } else {
            agg.other_verse_count += bk.verse_count.unwrap_or(0) as u32;
            agg.other_completed_verse_count += bk.completed_verse_count as u32;
        }

        agg.word_count += bk.word_count;
        merge_word_counts(&mut agg.all_word_counts, &bk.all_word_counts);
        merge_word_counts(&mut agg.all_case_insensitive_word_counts, &bk.all_case_insensitive_word_counts);
        merge_word_counts(&mut agg.main_text_word_counts, &bk.main_text_word_counts);
        merge_word_counts(&mut agg.main_text_case_insensitive_word_counts, &bk.main_text_case_insensitive_word_counts);

        if bk.section_references_parenthesis_ratio >= 0.0 {
            section_ref_ratios.push(bk.section_references_parenthesis_ratio);
        }
        if bk.footnotes_period_ratio >= 0.0 {
            footnote_ratios.push(bk.footnotes_period_ratio);
        }
        if bk.cross_references_period_ratio >= 0.0 {
            xref_ratios.push(bk.cross_references_period_ratio);
        }
    }

    let num_books = results.books.len() as f32;
    if num_books > 0.0 {
        agg.percentage_progress_by_book = format!("{}%", (total_progress_by_book / num_books).round());
    }
    if agg.ot_book_count > 0 {
        agg.ot_percentage_progress_by_book = format!("{}%", (ot_progress_by_book / 39.0).round());
    }
    if agg.nt_book_count > 0 {
        agg.nt_percentage_progress_by_book = format!("{}%", (nt_progress_by_book / 27.0).round());
    }
    if agg.dc_book_count > 0 {
        agg.dc_percentage_progress_by_book = format!("{}%", (dc_progress_by_book / 15.0).round());
    }

    if agg.verse_count > 0 {
        agg.percentage_progress_by_verse = format!("{}%", (agg.completed_verse_count as f32 * 100.0 / agg.verse_count as f32).round());
    }
    if agg.ot_verse_count > 0 {
        agg.ot_percentage_progress_by_verse = format!("{}%", (agg.ot_completed_verse_count as f32 * 100.0 / agg.ot_verse_count as f32).round());
    }
    if agg.nt_verse_count > 0 {
        agg.nt_percentage_progress_by_verse = format!("{}%", (agg.nt_completed_verse_count as f32 * 100.0 / agg.nt_verse_count as f32).round());
    }
    if agg.dc_verse_count > 0 {
        agg.dc_percentage_progress_by_verse = format!("{}%", (agg.dc_completed_verse_count as f32 * 100.0 / agg.dc_verse_count as f32).round());
    }

    if !section_ref_ratios.is_empty() {
        let avg = section_ref_ratios.iter().sum::<f32>() / section_ref_ratios.len() as f32;
        agg.section_references_parenthesis_flag = Some(avg > 0.8);
    }
    if !footnote_ratios.is_empty() {
        let avg = footnote_ratios.iter().sum::<f32>() / footnote_ratios.len() as f32;
        agg.footnotes_period_flag = Some(avg > 0.7);
    }
    if !xref_ratios.is_empty() {
        let avg = xref_ratios.iter().sum::<f32>() / xref_ratios.len() as f32;
        agg.cross_references_period_flag = Some(avg > 0.7);
    }
}

fn merge_word_counts(target: &mut HashMap<String, u32>, source: &HashMap<String, u32>) {
    for (word, count) in source {
        *target.entry(word.clone()).or_insert(0) += count;
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use crate::processing::{process_lines, ProcessLinesOptions};
    use bos_books_codes::is_valid_reference_abbreviation;

    #[test]
    fn test_oet_rv_discovery() {
        let test_folder_path = "../../Tests/DataFilesForTests/OET-RV";
        let mut books = IndexMap::new();

        let paths = fs::read_dir(test_folder_path).expect("Could not read OET-RV folder");
        for path in paths {
            let path = path.unwrap().path();
            if path.is_file() && path.extension().and_then(|s| s.to_str()) == Some("ESFM") {
                let filename = path.file_name().unwrap().to_str().unwrap();
                // OET-RV_HAG.ESFM -> HAG
                let bos_book_code = filename.split('_').nth(1).unwrap().split('.').next().unwrap();
                if bos_book_code != "DAG" && bos_book_code != "ES1" && bos_book_code != "ES2" { // Need to sort out these OET-RV filenames
                    assert!(is_valid_reference_abbreviation(bos_book_code), "Invalid book code: {}", bos_book_code); // Not really requred here, but a good test for bos_books_codes
                }
                
                let content = fs::read_to_string(&path).expect("Could not read file");
                let mut raw_lines = Vec::new();
                for line in content.lines() {
                    if line.trim().is_empty() { continue; }
                    let (marker, text) = match line.split_once(' ') {
                        Some((m, t)) => (m, t),
                        None => (line, ""),
                    };
                    let marker = marker.strip_prefix('\\').unwrap_or(marker);
                    raw_lines.push((marker.to_string(), text.to_string()));
                }

                let options = ProcessLinesOptions::default();
                let processed = process_lines(raw_lines, bos_book_code, "OET-RV", &options);
                books.insert(bos_book_code.to_string(), processed);
            }
        }

        assert!(!books.is_empty(), "Should have loaded some books");
        let results = discover_bible(&books);

        // Basic verification
        assert!(results.books.contains_key("HAG"));
        let hag = &results.books["HAG"];
        assert_eq!(hag.chapter_count, Some(2));
        // OET-RV Haggai has 15 + 23 = 38 verses
        assert_eq!(hag.verse_count, Some(38));
        assert_eq!(hag.completed_verse_count, 38);
        assert!(hag.word_count > 0);
        assert_eq!(hag.seems_finished, Some(true));

        println!("OET-RV Progress: {}", results.all.percentage_progress_by_verse);
        assert!(!results.all.percentage_progress_by_verse.is_empty());
    }
}
