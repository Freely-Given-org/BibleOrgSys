//! Section-based index for table of contents navigation.
//!
//! This module provides:
//! - `SectionIndexEntry` - Index entry for a single section
//! - `InternalBibleBookSectionIndex` - Section index for a book

use compact_str::{CompactString, ToCompactString};
use indexmap::IndexMap;
use num_format::{Locale, ToFormattedString};
// use rkyv::{validation, with};

use bos_books_codes::is_chapter_verse_book;
use crate::bos_markers::{is_end_marker, title_markers};
use crate::chapter_verse::ChapterVerse;
// use crate::indexes::section_index;
use crate::parsing::get_small_leading_int;
use crate::entry_lists::InternalBibleEntryList;
use crate::error::LookupError;
use crate::{have_strict_checking_flag, verbosity_println};

// /// Markers that can define section boundaries.
// const SECTION_MARKERS: &[&str] = &[
//     "is1", // Introductory sections
//     "ms1", //"ms2", "ms3", // Major sections
//     "s1",  // Section headings
//     "iex", // Chapter introductions, e.g., in KJB-1611
//     "c",   // Chapters can also define section boundaries, especially for intro-to-content transitions
// ];

/// An entry in the section index.
///
/// Each entry represents a section (usually defined by a heading)
/// and contains the range of entries it covers.
#[derive(Debug, Clone, PartialEq, Eq, rkyv::Archive, rkyv::Serialize, rkyv::Deserialize)]
pub struct SectionIndexEntry {
    /// Chapter where this section ends.
    end_chapter_num_str: CompactString,
    /// Verse where this section ends.
    end_verse_num_str: CompactString,
    /// Index of the first entry for this section.
    start_index: u32,
    /// Number of entries in this section (inclusive).
    entry_count: u16,
    /// The marker that started this section (e.g., "Headers", "is1", "s1", "c", "c/s1").
    /// Note that "c/s1" should only occur for Psalms (where each chapter is automatically a new section)
    reason_marker: CompactString,
    /// The section name/heading text.
    section_name: String,
    /// Context markers active at this section.
    context: Vec<CompactString>,
}

impl SectionIndexEntry {
    /// Create a new section index entry.
    pub fn new(
        end_chapter: impl Into<CompactString>,
        end_verse: impl Into<CompactString>,
        start_index: u32,
        entry_count: u16,
        reason_marker: impl Into<CompactString>,
        section_name: impl Into<String>,
        context: Vec<CompactString>,
    ) -> Self {
        Self {
            end_chapter_num_str: end_chapter.into(),
            end_verse_num_str: end_verse.into(),
            start_index,
            entry_count,
            reason_marker: reason_marker.into(),
            section_name: section_name.into(),
            context,
        }
    }

    /// Get the ending chapter:verse as a ChapterVerse.
    pub fn end_cv(&self) -> ChapterVerse {
        ChapterVerse::new(self.end_chapter_num_str.as_str(), self.end_verse_num_str.as_str())
    }

    /// Get the ending chapter number.
    #[inline]
    pub fn end_chapter_num_str(&self) -> &str {
        &self.end_chapter_num_str
    }

    /// Get the ending verse number.
    #[inline]
    pub fn end_verse_num_str(&self) -> &str {
        &self.end_verse_num_str
    }

    /// Get the starting entry index.
    #[inline]
    pub fn start_index(&self) -> usize {
        self.start_index as usize
    }

    /// Get the ending entry index (inclusive).
    #[inline]
    pub fn end_index(&self) -> usize {
        self.start_index as usize + self.entry_count as usize - 1
    }

    /// Get the count of entries in this section.
    #[inline]
    pub fn entry_count(&self) -> usize {
        self.entry_count as usize
    }

    /// Get the marker that started this section.
    #[inline]
    pub fn reason_marker(&self) -> &str {
        &self.reason_marker
    }

    /// Get the section name/heading text.
    #[inline]
    pub fn section_name(&self) -> &str {
        &self.section_name
    }

    /// Get the section name and reason marker as a tuple.
    pub fn section_name_reason(&self) -> (&str, &str) {
        (&self.section_name, &self.reason_marker)
    }

    /// Get the context markers.
    #[inline]
    pub fn context(&self) -> &[CompactString] {
        &self.context
    }
}

impl std::fmt::Display for SectionIndexEntry {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "SectionEntry(ends {} lines {}-{} {} {:?} [{}])",
            self.end_cv(),
            self.start_index,
            self.entry_count,
            self.reason_marker,
            self.section_name,
            self.context.join(", "),
        )
    }
}

/// Index for section-based lookup in a Bible book.
///
/// This index maps section starting points (C:V) to section entries,
/// useful for table of contents navigation and section-based access.
/// 
/// Note that unlike the CV index,
///     the section index doesn't necessarily include all the line entries.
#[derive(Debug, rkyv::Archive, rkyv::Serialize, rkyv::Deserialize)]
pub struct InternalBibleBookSectionIndex {
    /// Name of the work/Bible.
    work_name: CompactString,
    /// Three-letter book code.
    bos_book_code: CompactString,
    /// The section -> entry mapping (keyed by starting C:V).
    index_data: IndexMap<ChapterVerse, SectionIndexEntry>,
    /// The processed entries this index references.
    line_entries: InternalBibleEntryList,
    /// Whether the index has been built.
    indexed: bool,
}

impl InternalBibleBookSectionIndex {
    /// Create a new empty section index.
    pub fn new(work_name: impl Into<CompactString>, bos_book_code: impl Into<CompactString>) -> Self {
        Self {
            work_name: work_name.into(),
            bos_book_code: bos_book_code.into(),
            index_data: IndexMap::new(),
            line_entries: InternalBibleEntryList::new(),
            indexed: false,
        }
    }

    /// Get the work name.
    #[inline]
    pub fn work_name(&self) -> &str {
        &self.work_name
    }

    /// Get the book code.
    #[inline]
    pub fn bos_book_code(&self) -> &str {
        &self.bos_book_code
    }

    /// Check if the index has been built.
    #[inline]
    pub fn is_indexed(&self) -> bool {
        self.indexed
    }

    /// Get the number of sections in the index.
    #[inline]
    pub fn len(&self) -> usize {
        self.index_data.len()
    }

    /// Check if the index is empty.
    #[inline]
    pub fn is_empty(&self) -> bool {
        self.index_data.is_empty()
    }

    /// Check if a specific section starting point exists.
    #[inline]
    pub fn contains(&self, cv: &ChapterVerse) -> bool {
        self.index_data.contains_key(cv)
    }

    /// Get an iterator over all sections.
    pub fn iter(&self) -> impl Iterator<Item = (&ChapterVerse, &SectionIndexEntry)> {
        self.index_data.iter()
    }

    /// Get entries for a section.
    ///
    /// # Arguments
    ///
    /// * `cv` - The starting chapter:verse of the section
    pub fn get_section_entries(&self, cv: &ChapterVerse) -> Result<InternalBibleEntryList, LookupError> {
        if !self.indexed {
            return Err(LookupError::NotIndexed);
        }

        let entry = self
            .index_data
            .get(cv)
            .ok_or_else(|| LookupError::SectionNotFound(cv.clone()))?;

        Ok(self
            .line_entries
            .slice(entry.start_index as usize, (entry.end_index() + 1) as usize))
    }

    /// Get section entries with context markers.
    pub fn get_section_entries_with_context(
        &self,
        cv: &ChapterVerse,
    ) -> Result<(InternalBibleEntryList, Vec<CompactString>), LookupError> {
        if !self.indexed {
            return Err(LookupError::NotIndexed);
        }

        let entry = self
            .index_data
            .get(cv)
            .ok_or_else(|| LookupError::SectionNotFound(cv.clone()))?;

        let entries = self
            .line_entries
            .slice(entry.start_index as usize, (entry.end_index() + 1) as usize);
        Ok((entries, entry.context.clone()))
    }

    /// Get the section index entry for a specific starting CV.
    pub fn get_index_entry(&self, cv: &ChapterVerse) -> Option<&SectionIndexEntry> {
        self.index_data.get(cv)
    }

    /// Get all section names as a table of contents.
    pub fn table_of_contents(&self) -> Vec<(&ChapterVerse, &str, &str)> {
        self.index_data
            .iter()
            .map(|(cv, entry)| (cv, entry.section_name(), entry.reason_marker()))
            .collect()
    }

    /// Get direct access to the underlying entries.
    #[inline]
    pub fn entries(&self) -> &InternalBibleEntryList {
        &self.line_entries
    }

    /// Get direct access to the underlying index data.
    #[inline]
    pub fn index_data(&self) -> &IndexMap<ChapterVerse, SectionIndexEntry> {
        &self.index_data
    }

    /// Reconstruct from serialized data.
    pub fn from_serialized(
        work_name: impl Into<CompactString>,
        bos_book_code: impl Into<CompactString>,
        index_data: IndexMap<ChapterVerse, SectionIndexEntry>,
        line_entries: InternalBibleEntryList,
    ) -> Self {
        Self {
            work_name: work_name.into(),
            bos_book_code: bos_book_code.into(),
            index_data,
            line_entries,
            indexed: true,
        }
    }

    /// Build the section index from processed entries.
    ///
    /// This analyzes the entry list and creates section boundaries
    /// based on section heading markers.
    pub fn build(&mut self, line_entries: InternalBibleEntryList) -> Result<(), crate::error::IndexError> {
        if line_entries.is_empty() {
            return Err(crate::error::IndexError::EmptyEntries);
        }
        log::info!(
            "Building section index for {} {} from {} entries…",
            self.work_name(),
            self.bos_book_code(),
            line_entries.len().to_formatted_string(&Locale::en)
        );

        self.line_entries = line_entries;
        self.index_data.clear();

        // Just see if we have section headings in this verse line_entry data
        let mut have_section_headings = false;
        for line_entry in self.line_entries.iter() {
            if line_entry.marker() == "s1" {
                have_section_headings = true;
                break;
            }
        }
        let process_chapters_as_section_breaks = self.bos_book_code()=="PSA" || !have_section_headings;

        let mut current_chapter_num_str = CompactString::from("-1");
        let mut current_verse_num_str = CompactString::from("0");
        let mut last_chapter_num_str = CompactString::from("-1");
        let mut last_verse_num_str = CompactString::from("0");
        let mut last_marker = "";
        let mut pending = None;
        let mut context: Vec<CompactString> = Vec::new();
        let mut book_name = String::new();
        let mut had_section_heading_since_chapters = false;
        let mut just_had_ms1 = false;
        // let mut last_bridge_start_index: Option<u16> = None;
        // let mut last_bridge_verse_num_str: Option<CompactString> = None;

        for (i, line_entry) in self.line_entries.iter().enumerate() {
            let marker = line_entry.marker();
            verbosity_println!(3, "  sectionIndex {} {} build loop (with {} existing index entries) {}: {}",
                    self.work_name(), self.bos_book_code(), self.index_data.len(), i, marker);

            // Get the very first marker
            if last_marker.is_empty() && ["id","usfm","ide","headers","h","intro","mt1"].contains(&marker) {
                assert!(pending.is_none());
                pending = Some(PendingSection {
                        start_cv: Some(ChapterVerse::new(current_chapter_num_str.as_str(), current_verse_num_str.as_str())),
                        start_index: 0,
                        reason: CompactString::from("Headers"),
                        name: self.bos_book_code().to_string(),
                        // has_content: false,
                    });
                last_marker = marker;
                continue
            }

            if marker == "h" {
                book_name = line_entry.clean_text().to_string();
                continue;
            } else if marker == "c" {
                current_chapter_num_str = CompactString::from(line_entry.clean_text());
                if !context.contains(&CompactString::from("c")) { context.push("c".into()); }
                current_verse_num_str = CompactString::from("0");
            } else if marker == "v" {
                current_verse_num_str = CompactString::from(line_entry.clean_text());
                just_had_ms1 = false;
            } else if current_chapter_num_str == "-1" && marker != "chapters" {
                current_verse_num_str = i.to_compact_string();
            } else if marker == "chapters" {
                context.push(CompactString::from("chapters"));
                current_chapter_num_str = CompactString::from("0");
                had_section_heading_since_chapters = false;
            } else if marker == "s1" || marker == "ms1" {
                had_section_heading_since_chapters = true;
                if marker == "ms1" { just_had_ms1 = true; }
            }

            if have_strict_checking_flag() || cfg!(debug_assertions) {
                println!("    build {} {} section index loop {} with {} section index entries already from the given {} entry lines\n  with current {}:{} last {}:{} context=[{}] pending={:?}",
                    self.work_name(), self.bos_book_code(), i, self.index_data.len(), self.line_entries.len(),
                    current_chapter_num_str, current_verse_num_str, last_chapter_num_str, last_verse_num_str,
                    context.join(", "), pending);
            }

            // Once we reach the chapters, i.e., after the headers and introduction,
            //  we should only need to start sections at v=, at s1 after ms1, and sometimes at c markers
            if marker == "v=" {
            // && (!process_chapters_as_section_breaks || last_marker != "c") {
                let special_verse_num = line_entry.clean_text();
                // if current_verse_num_str=="0" && special_verse_num=="1" { current_verse_num_str = CompactString::from("1"); }
                let next_line_entry = self.line_entries.get(i+1).unwrap();
                let next_marker = next_line_entry.marker();
                if ["s1","ms1"].contains(&next_marker) {
                    if have_strict_checking_flag() || cfg!(debug_assertions) {
                        println!("    build {} section index at {} {} {}:{} has v= = '{}' followed by '{}' so need to start new index entry here",
                                self.work_name(), i, self.bos_book_code(), current_chapter_num_str, current_verse_num_str, special_verse_num, next_marker);
                    }
                    let this_start_index = i as u32 - {if last_marker=="c" {1} else {0}};
                    // current_verse_num_str = CompactString::from(special_verse_num);
                    let mut finishing_verse_num_str = CompactString::from(last_verse_num_str.clone());
                    if current_verse_num_str.contains("b") { finishing_verse_num_str = CompactString::from(current_verse_num_str.replace("b", "a")); }
                    // last_bridge_start_index = Some(i as u32);
                    // last_bridge_verse_num_str = Some(CompactString::from(verse_num));
                    // if let Some(section) = pending.as_mut() {
                    //     if section.start_cv.is_none() {
                    //         section.start_cv = Some(ChapterVerse::new(
                    //             current_chapter_num_str.as_str(),
                    //             current_verse_num_str.as_str(),
                    //         ));
                    //         }
                    //     }
                    //     log::trace!("  Build {} {} section index: at entry #{} {}:{}",
                    //         self.work_name(), self.bos_book_code(), i, current_chapter_num_str, current_verse_num_str );

                    // Close previous section and start new one.
                    if let Some(mut this_pending_section) = pending.take() {
                        if this_start_index > this_pending_section.start_index {
                            if this_pending_section.start_cv.is_none() {
                                this_pending_section.start_cv = Some(ChapterVerse::new(
                                    current_chapter_num_str.as_str(),
                                    current_verse_num_str.as_str(),
                                ));
                            }
                            let mut end_idx = (i as u32).saturating_sub(1);
                            for _ in 0..4 {
                                if have_strict_checking_flag() || cfg!(debug_assertions) {
                                    println!("      Finding end of previous section that started at {}: {} marker = {}", this_pending_section.start_index, end_idx, self.line_entries.get(end_idx as usize).clone().unwrap().marker());
                                }
                                let some_previous_marker = self.line_entries.get(end_idx as usize).clone().unwrap().marker();
                                if is_end_marker(some_previous_marker)
                                || (self.index_data.len()<2 && (["id","usfm","ide"].contains(&some_previous_marker) || title_markers::ALL.contains(&some_previous_marker)))
                                    { break; }
                                end_idx = end_idx.saturating_sub(1);
                            }
                            if special_verse_num.ends_with("b") {
                                assert!(special_verse_num.to_string().starts_with(finishing_verse_num_str.as_str()));
                                finishing_verse_num_str += "a";
                            }
                            let (cv, entry) = this_pending_section.into_closed(
                                last_chapter_num_str.as_str(),
                                finishing_verse_num_str.as_str(),
                                end_idx,
                                context.clone());
                            if have_strict_checking_flag() || cfg!(debug_assertions) {
                                println!("    About to close section at {}:{} with current_chapter_num_str={} current_verse_num_str={} last_verse_num_str={}",
                                            last_chapter_num_str, finishing_verse_num_str, current_chapter_num_str, current_verse_num_str, last_verse_num_str);
                                assert_ne!(finishing_verse_num_str, "0", "Don't want to finish the previous {} {} section at {}:{}",
                                            self.work_name(), self.bos_book_code(), last_chapter_num_str, finishing_verse_num_str);
                                assert!(!self.index_data.contains_key(&cv), "{} {} section index losing data: {cv} trying to insert {}",
                                        self.work_name(), self.bos_book_code(), entry);
                            }
                            self.index_data.insert(cv, entry);
                            // context.pop();
                        }
                    }
                    // New section starts at this section marker
                    pending = Some(PendingSection {
                        start_cv: Some(ChapterVerse::new(current_chapter_num_str.as_str(),  special_verse_num)),
                        start_index: this_start_index,
                        reason: CompactString::from( if current_verse_num_str=="0" {if process_chapters_as_section_breaks {format!("c/{}", next_marker)} else {format!("{}/c", next_marker)}}
                                                     else {next_marker.to_string()}),
                        name: next_line_entry.clean_text().to_string(),
                        // has_content: false
                        });
                    if have_strict_checking_flag() || cfg!(debug_assertions) { println!("    v= pending = {:?}", pending); }
                    }
            }

            else if marker == "s1" && just_had_ms1 { // There wouldn't be another v= before this s1, so we handle it differently
                assert!(pending.is_some()); // The ms1
                // Handle previous section and start new one.
                let (cv, new_ms1_entry) = pending.take().unwrap().into_closed(
                    "0",
                    "0",
                    (i - 1) as u32,
                    context.clone());
                assert!(new_ms1_entry.reason_marker().contains("ms1"));
                let this_verse_num_str = String::from(cv.verse());
                 // If we're at v1, let's change the verse number back to "0" to prevent overwriting problems
                 // If the ms1 is mid-chapter (like in Job), then we want to keep the verse number as is, but add a "p" suffix (for 'preliminary') to prevent (later) overwriting problems
                let adj_cv = ChapterVerse::new(cv.chapter(), if this_verse_num_str=="1" {String::from("0")} else {format!("{}p", cv.verse())});
                if have_strict_checking_flag() || cfg!(debug_assertions) {
                    assert!(!self.index_data.contains_key(&adj_cv), "{} {} section index losing data: {} trying to insert {}",
                    self.work_name(), self.bos_book_code(), adj_cv, new_ms1_entry);
                }
                self.index_data.insert(adj_cv, new_ms1_entry);
                // New s1 section starts at this section marker
                pending = Some(PendingSection {
                    start_cv: Some(ChapterVerse::new(current_chapter_num_str.as_str(),  this_verse_num_str)),
                    start_index: i as u32,
                    reason: CompactString::from( if current_verse_num_str=="0" { if process_chapters_as_section_breaks {"c/s1"} else {"s1/c"} } else {"s1"}),
                    name: line_entry.clean_text().to_string(),
                    // has_content: false
                    });
                if have_strict_checking_flag() || cfg!(debug_assertions) { println!("    v= pending = {:?}", pending); }
            }

            else if marker == "c" {
                let mut next_relevant_marker = "";
                for adder in 1..9 { // Look at what's ahead
                    // println!("   After c, adder={} marker={}", adder, self.line_entries.get(i+adder).unwrap().marker());
                    if ["v","v="].contains(&self.line_entries.get(i+adder).unwrap().marker()) {
                        next_relevant_marker = self.line_entries.get(i+adder).unwrap().marker();
                        break;
                    }
                }
                if next_relevant_marker != "v=" // If it's v=, we'll handle that on the next loop instead unless we're doing a book like Psalms where we treat chapters as section breaks
                && (!had_section_heading_since_chapters || process_chapters_as_section_breaks) {
                    if have_strict_checking_flag() || cfg!(debug_assertions) {
                        println!("    build {} {} section index at {} {}:{} has c followed by '{}' so need to start new index entry here",
                            self.work_name(), self.bos_book_code(), i, current_chapter_num_str, current_verse_num_str, next_relevant_marker);
                    }
                    // New section starts at or just before this chapter marker
                    let mut start_idx = i;
                    for subber in 1..=(4.min(i as usize)) { // Look at what's just behind (e.g., a chapter label that precedes its \cl-less \c)
                        if ["cl"].contains(&self.line_entries.get(i-subber).unwrap().marker()) {
                            start_idx = i - subber;
                            break;
                        }
                    }
                    // Close previous section and start new one.
                    if let Some(mut this_pending_section) = pending.take() {
                        if i as u32 > this_pending_section.start_index {
                            if this_pending_section.start_cv.is_none() {
                                this_pending_section.start_cv = Some(ChapterVerse::new(
                                    current_chapter_num_str.as_str(),
                                    current_verse_num_str.as_str(),
                                ));
                            }
                            let mut end_idx = (i as u32).saturating_sub(1);
                            let mut found_end_marker = false;
                            for _ in 0..4 {
                                if is_end_marker(self.line_entries.get(end_idx as usize).clone().unwrap().marker()) {
                                    found_end_marker = true;
                                    break;
                                }
                                end_idx = end_idx.saturating_sub(1);
                            }
                            if !found_end_marker { end_idx = (i as u32).saturating_sub(1); } // Go back to where we where
                            if end_idx >= start_idx as u32 { end_idx = (start_idx as u32).saturating_sub(1); } // Don't overlap the section that we're about to start
                            let (cv, entry) = this_pending_section.into_closed(
                                last_chapter_num_str.as_str(),
                                last_verse_num_str.as_str(),
                                end_idx,
                                context.clone());
                            if have_strict_checking_flag() || cfg!(debug_assertions) {
                                assert!(!self.index_data.contains_key(&cv), "{} {} section index losing data: {cv} trying to insert {}",
                                        self.work_name(), self.bos_book_code(), entry);
                                }
                            self.index_data.insert(cv, entry);
                            // context.pop();
                        }
                    }
                    // println!("    build {} {} section index at {} {}:{} has c followed by '{}' so starting new index entry at {}",
                    //     self.work_name(), self.bos_book_code(), i, current_chapter_num_str, current_verse_num_str, next_relevant_marker, start_idx);
                    pending = Some(PendingSection {
                        start_cv: Some(ChapterVerse::new(current_chapter_num_str.as_str(),
                                                            if current_verse_num_str=="0" {"1"} else {current_verse_num_str.as_str()})),
                        start_index: start_idx.try_into().unwrap(),
                        reason: CompactString::from("c"),
                        name: if book_name.is_empty() {current_chapter_num_str.to_string()} else {format!("{} {}", book_name, current_chapter_num_str)},
                        // has_content: false
                        });
                    }
            }

        // The problem here is that we don't know if the following 'v=' has a 'b', e.g., '3b', in which case, this should be '3a'
        //  so might be easiest to just ignore this
        // else if ["¬s1","¬ms1","¬is1"].contains(&marker) { // We've just finished a section
        //     assert!(pending.is_some());
        //     if let Some(previously_pending_section) = pending.take() {
        //         if have_strict_checking_flag() || cfg!(debug_assertions) { println!("  Adding close '{}' section", marker); }
        //         let (cv, entry) = previously_pending_section.into_closed(
        //             current_chapter_num_str.as_str(),
        //             current_verse_num_str.as_str(),
        //             i as u32,
        //             context.clone(),
        //         );
        //     self.index_data.insert(cv, entry);
        //     }
        // }
        
        else if current_chapter_num_str == "-1" { // We're still in the pre-chapter sections
                if marker == "¬headers" {
                    if let Some(previously_pending_section) = pending.take() {
                        // if section.start_cv.is_none() {
                        //     section.start_cv = Some(ChapterVerse::new(
                        //         current_chapter_num_str.as_str(),
                        //         current_verse_num_str.as_str(),
                        //     ));
                        // }
                        // let end_idx = (i as u32).saturating_sub(1);
                        let (cv, entry) = previously_pending_section.into_closed(
                            current_chapter_num_str.as_str(),
                            current_verse_num_str.as_str(),
                            i as u32,
                            context.clone());
                        if have_strict_checking_flag() || cfg!(debug_assertions) {
                            assert!(!self.index_data.contains_key(&cv), "Losing {} {} initial section index data: {}", self.work_name(), self.bos_book_code(), cv ); }
                        self.index_data.insert(cv, entry);
                        context.clear();
                    }
                    // pending = Some(PendingSection {
                    //     start_cv: None, //Some(ChapterVerse::new(current_chapter_num_str.as_str(), current_verse_num_str.as_str())),
                    //     start_index: i+1.try_into().unwrap(),
                    //     reason: CNone,
                    //     name: entry.clean_text().to_string(),
                    //     has_content: false,
                    // });
                } else if marker == "intro" && self.line_entries.get(i+1).unwrap().marker() == "is1" {
                    assert!( pending.is_none());
                    // current_chapter_num_str = CompactString::from("0");
                    // if let Some(mut section) = pending.take() {
                    //     assert!(section.reason)
                    //     if section.start_cv.is_none() {
                    //         section.start_cv = Some(ChapterVerse::new(
                    //             current_chapter_num_str.as_str(),
                    //             current_verse_num_str.as_str(),
                    //         ));
                    //     }
                    //     let end_idx = (i as u32).saturating_sub(1);
                    //     let (cv, entry) = section.into_closed(
                    //         last_chapter_num_str.as_str(),
                    //         last_verse_num_str.as_str(),
                    //         end_idx,
                    //         context.clone(),
                    //     );
                    //     self.index_data.insert(cv, entry);
                    //     context.clear();
                    // }
                    pending = Some(PendingSection {
                        start_cv: Some(ChapterVerse::new(current_chapter_num_str.as_str(), current_verse_num_str.as_str())),
                        start_index: (i+1).try_into().unwrap(),
                        reason: CompactString::const_new("is1"),
                        name: self.line_entries.get(i+1).unwrap().clean_text().to_string(),
                        // has_content: false,
                    });
                } else if marker == "is1" {
                    // current_chapter_num_str = CompactString::from("0");
                    if let Some(previous_pending_section) = pending.take() {
                        // if section.start_cv.is_none() {
                        //     section.start_cv = Some(ChapterVerse::new(
                        //         current_chapter_num_str.as_str(),
                        //         current_verse_num_str.as_str(),
                        //     ));
                        // }
                        // let end_idx = (i as u32).saturating_sub(1);
                        if i as u32 > previous_pending_section.start_index {
                            let (cv, current_pending_section) = previous_pending_section.into_closed(
                                last_chapter_num_str.as_str(),
                                last_verse_num_str.as_str(),
                                (i - 1) as u32,
                                context.clone(),
                            );
                            if have_strict_checking_flag() || cfg!(debug_assertions) {
                                assert!(!self.index_data.contains_key(&cv), "Losing data: {cv}");
                                assert_eq!(cv.verse().parse::<u32>(), Ok(current_pending_section.start_index));
                                if current_chapter_num_str != "-1" {
                                    assert_eq!(last_verse_num_str.parse::<u16>(), Ok(current_pending_section.entry_count),
                                                "build {} {} section index loop {} with {} section index entries already, failed with {} {}\nfrom {}",
                                            self.work_name(), self.bos_book_code(), i, self.index_data.len(),
                                            last_verse_num_str, current_pending_section.entry_count, self.line_entries);
                                }
                            }
                            self.index_data.insert(cv, current_pending_section);
                            context.clear();
                        }
                    }
                    pending = Some(PendingSection {
                        start_cv: Some(ChapterVerse::new(current_chapter_num_str.as_str(), current_verse_num_str.as_str())),
                        start_index: i.try_into().unwrap(),
                        reason: CompactString::from(marker),
                        name: line_entry.clean_text().to_string(),
                        // has_content: false,
                    });
                } else if marker == "¬intro" {
                    if let Some(previously_pending_section) = pending.take() {
                        // if section.start_cv.is_none() {
                        //     section.start_cv = Some(ChapterVerse::new(
                        //         current_chapter_num_str.as_str(),
                        //         current_verse_num_str.as_str(),
                        //     ));
                        // }
                        // let end_idx = (i as u32).saturating_sub(1);
                        let (cv, entry) = previously_pending_section.into_closed(
                            current_chapter_num_str.as_str(),
                            current_verse_num_str.as_str(),
                            i as u32,
                            context.clone(),
                        );
                        assert!(["is1","Headers"].contains(&entry.reason_marker()));
                        if have_strict_checking_flag() || cfg!(debug_assertions) { assert!(!self.index_data.contains_key(&cv), "Losing data: {cv}"); }
                        self.index_data.insert(cv, entry);
                        context.clear();
                    }
                }
            }
            

            // } else if is_section_marker(marker) {
            //     log::trace!(
            //         "  Build {} {} section index: found section marker at entry #{} {}={} with {}:{}",
            //         self.work_name(),
            //         self.bos_book_code(),
            //         i,
            //         marker,
            //         entry.clean_text(),
            //         last_chapter_num_str,
            //         last_verse_num_str
            //     );
            //     if marker == "c" {
            //         let was_intro = current_chapter_num_str == "-1";
            //         if was_intro || self.bos_book_code() == "PSA" {
            //             // Transitioning from intro to content (or new Psalm): close the previous section
            //             if let Some(mut section) = pending.take() {
            //                 if section.start_cv.is_none() {
            //                     section.start_cv = Some(ChapterVerse::new(
            //                         current_chapter_num_str.as_str(),
            //                         current_verse_num_str.as_str(),
            //                     ));
            //                 }
            //                 let end_idx = (i as u32).saturating_sub(1);
            //                 let end_v_intro;
            //                 let (end_ch, end_v) = if was_intro {
            //                     end_v_intro = end_idx.to_string();
            //                     ("-1", end_v_intro.as_str())
            //                 } else {
            //                     (last_chapter_num_str.as_str(), last_verse_num_str.as_str())
            //                 };
            //                 let (cv, entry) = section.into_closed(end_ch, end_v, end_idx, context.clone());
            //                 self.index_data.insert(cv, entry);
            //                 context.clear();
            //             }
            //             // Construct section name from book_name + " " + chapter
            //             let chapter_text = entry.clean_text();
            //             let s_name = if !book_name.is_empty() {
            //                 format!("{} {}", book_name, chapter_text)
            //             } else {
            //                 "".to_string()
            //             };

            //             // Start a transition section at this c marker (will be merged with next section heading if no content)
            //             pending = Some(PendingSection {
            //                 start_cv: None,
            //                 start_index: i.try_into().unwrap(),
            //                 reason: CompactString::from("c"),
            //                 name: s_name,
            //                 has_content: false,
            //             });
            //         }

            //         current_chapter_num_str = CompactString::from(entry.clean_text());
            //         current_verse_num_str = CompactString::from("0");
            //    }
            //     if current_chapter_num_str == "-1" {
            //         // In intro mode: close previous section with -1:(i-1) addressing
            //         if let Some(mut section) = pending.take() {
            //             if section.start_cv.is_none() {
            //                 section.start_cv = Some(ChapterVerse::new(
            //                     current_chapter_num_str.as_str(),
            //                     current_verse_num_str.as_str(),
            //                 ));
            //             }
            //             let end_idx = (i as u32).saturating_sub(1);
            //             let (cv, entry) = section.into_closed("-1", &end_idx.to_string(), end_idx, context.clone());
            //             self.index_data.insert(cv, entry);
            //             context.clear();
            //         }
            //         // Start new intro section with -1:i addressing
            //         pending = Some(PendingSection {
            //             start_cv: Some(ChapterVerse::new("-1", i.to_string())),
            //             start_index: i.try_into().unwrap(),
            //             reason: CompactString::from(marker),
            //             name: entry.clean_text().to_string(),
            //             has_content: false,
            //         });
            //     } else if pending.as_ref().is_some_and(|s| !s.has_content) {
            //         // Merge heading into the section if no content seen yet
            //         let section = pending.as_mut().unwrap();
            //         let marker_prefix = if self.bos_book_code() == "PSA" && section.reason == "c" { "c/" } else { "" };
            //         section.reason = CompactString::from(format!("{}{}", marker_prefix, marker));
            //         section.name = entry.clean_text().to_string();
            //         section.start_index = i.try_into().unwrap(); // Update start_index to heading
            //     } else if marker != "c"
            //         && is_section_marker(marker)
            //         && last_bridge_start_index.is_some_and(|idx| idx + 1 == i as u32)
            //         {
            //         // A bridge verse immediately before this section heading should define the section start.
            //         if let Some(mut section) = pending.take() {
            //             if section.start_cv.is_none() {
            //                 section.start_cv = Some(ChapterVerse::new(
            //                     current_chapter_num_str.as_str(),
            //                     current_verse_num_str.as_str(),
            //                 ));
            //             }
            //             let end_idx = (i as u32).saturating_sub(1);
            //             let (cv, entry) = section.into_closed(
            //                 last_chapter_num_str.as_str(),
            //                 last_verse_num_str.as_str(),
            //                 end_idx,
            //                 context.clone(),
            //             );
            //             self.index_data.insert(cv, entry);
            //             context.clear();
            //         }
            //         let start_index = last_bridge_start_index.take().unwrap_or(i as u32);
            //         let bridge_verse = last_bridge_verse_num_str.as_deref().unwrap_or(current_verse_num_str.as_str());
            //         pending = Some(PendingSection {
            //             start_cv: Some(ChapterVerse::new(
            //                 current_chapter_num_str.as_str(),
            //                 bridge_verse,
            //             )),
            //             start_index,
            //             reason: CompactString::from(marker),
            //             name: entry.clean_text().to_string(),
            //             has_content: false,
            //         });
            //     } else {
            //         // Normal content: close previous section and start new one.
            //         if let Some(mut section) = pending.take() {
            //             if section.start_cv.is_none() {
            //                 section.start_cv = Some(ChapterVerse::new(
            //                     current_chapter_num_str.as_str(),
            //                     current_verse_num_str.as_str(),
            //                 ));
            //             }
            //             let end_idx = (i as u32).saturating_sub(1);
            //             let (cv, entry) = section.into_closed(
            //                 last_chapter_num_str.as_str(),
            //                 last_verse_num_str.as_str(),
            //                 end_idx,
            //                 context.clone(),
            //             );
            //             self.index_data.insert(cv, entry);
            //             context.clear();
            //         }
            //         // New section starts at this section marker
            //         pending = Some(PendingSection {
            //             start_cv: None,
            //             start_index: i.try_into().unwrap(),
            //             reason: CompactString::from(marker),
            //             name: entry.clean_text().to_string(),
            //             has_content: false,
            //         });
            //     }
            // } else if marker == "v" {
            //     let verse_num = entry.clean_text();
            //     current_verse_num_str = CompactString::from(verse_num);
            //     last_bridge_start_index = None;
            //     last_bridge_verse_num_str = None;
            //     if let Some(section) = pending.as_mut() {
            //         if section.start_cv.is_none() {
            //             section.start_cv = Some(ChapterVerse::new(
            //                 current_chapter_num_str.as_str(),
            //                 current_verse_num_str.as_str(),
            //             ));
            //         }
            //     }
            //     log::trace!(
            //         "  Build {} {} section index: at entry #{} {}:{}",
            //         self.work_name(),
            //         self.bos_book_code(),
            //         i,
            //         current_chapter_num_str,
            //         current_verse_num_str
            //     );
            // } else if marker == "id" {
            //     pending = Some(PendingSection {
            //         start_cv: Some(ChapterVerse::new(
            //             current_chapter_num_str.as_str(),
            //             current_verse_num_str.as_str(),
            //         )),
            //         start_index: i.try_into().unwrap(),
            //         reason: CompactString::from("Headers"),
            //         name: entry.clean_text().chars().take(3).collect::<String>(),
            //         has_content: false,
            //     });
            // }

            // if marker == "v~" {
            //     if let Some(section) = pending.as_mut() {
            //         section.has_content = true;
            //     }
            // }
            
            // End of loop
            // Record current CV for the NEXT entry to use as its "previous" CV
            // But don't update it for markers that change the CV themselves,
            // so that if a section ends with such a marker, it uses the previous CV for endCV.
            if marker != "v" && marker != "v=" && marker != "c" && !is_end_marker(marker) {
                last_chapter_num_str = current_chapter_num_str.clone();
                last_verse_num_str = current_verse_num_str.clone();
            }
            last_marker = marker;
        }
        if have_strict_checking_flag() || cfg!(debug_assertions) { println!("Section heading loop finished with {} entries and pending={:?}", self.index_data.len(), pending); }

        // Close final section
        if let Some(previously_pending_section) = pending.as_mut().filter(|s| s.start_cv.is_none()) {
            previously_pending_section.start_cv = Some(ChapterVerse::new(
                current_chapter_num_str.as_str(),
                current_verse_num_str.as_str(),
            ));
        }
        // Don't include the ¬chapters line in the final section
        let mut end_idx = (self.line_entries.len() as u32).saturating_sub(1);
        if self.line_entries.get(end_idx as usize).clone().unwrap().marker() == "¬chapters" {
             end_idx = end_idx.saturating_sub(1); // Go back to the one before
             assert!(is_end_marker(self.line_entries.get(end_idx as usize).clone().unwrap().marker()));
        }
        if let Some(previously_pending_section) = pending {
            if have_strict_checking_flag() || cfg!(debug_assertions) { println!("  Adding final section"); }
            let (cv, entry) = previously_pending_section.into_closed(
                current_chapter_num_str.as_str(),
                current_verse_num_str.as_str(),
                end_idx,
                context,
            );
            if self.index_data.contains_key(&cv) { // This can happen for alternative endings to Mark
                if have_strict_checking_flag() || cfg!(debug_assertions) {
                    assert_eq!(self.bos_book_code(), "MRK", "{} {} section index is losing a key: {}", self.work_name(), self.bos_book_code(), cv);
                }
                let suffix_char = if cv.has_verse_suffix() {cv.verse().chars().last().unwrap()} else {' '};
                let next_suffix_char = char::from_u32(suffix_char as u32 + 1).unwrap_or(suffix_char); // Convert to u32, add 1, and convert back to a char
                let without_last = match cv.verse().char_indices().next_back() {
                            Some((idx, _)) => &cv.verse()[..idx],
                            None => "", // Returns empty string if the original string was empty
                        };
                let new_verse_number = if suffix_char==' ' {cv.verse().to_string()} else {format!("{}{}", without_last, next_suffix_char)};
                self.index_data.insert(ChapterVerse::new(cv.chapter(), new_verse_number), entry); // Append another suffix
            } else {
                if have_strict_checking_flag() || cfg!(debug_assertions) { assert!(!self.index_data.contains_key(&cv), "Losing data: {cv}"); }
                self.index_data.insert(cv, entry);
            }
        }
        if have_strict_checking_flag() || cfg!(debug_assertions) { println!("Section heading build finished with {} entries", self.index_data.len()); }
        self.indexed = true;

        if have_strict_checking_flag() || cfg!(debug_assertions) {
             let validation_results = self.validate(&self.line_entries);
             if !validation_results.is_empty() {
                panic!("{} {} section index validation failed with {} issues: {:?}", self.work_name, self.bos_book_code, validation_results.len(), validation_results);
            }
        }
        Ok(())
    }

    // fn format_section_result(&self, res: Result<InternalBibleEntryList, LookupError>) -> String {
    //     match res {
    //         Ok(entries) => format!("{}", entries),
    //         Err(e) => format!("{}", e),
    //     }
    // }

    /// Validate the section index structure.
    ///
    /// Returns a list of any issues found.
    fn validate(&self, line_entries: &InternalBibleEntryList) -> Vec<String> {
        let mut issues = Vec::new();

        if !self.indexed {
            issues.push(format!("{} {} section index has not been built", self.work_name, self.bos_book_code));
            return issues;
        }

        // Check for overlapping entries,
        //  for entries containing incorrect verse numbers,
        //  and that the last line in an index segment is an end marker
        //  and that there's entries for -1:0 and 1:1.
        let mut have_m1_0 = false;
        let mut have_1_0 = false; // Surely we only need one of these???
        let mut have_1_1 = false; // Surely we only need one of these???
        let mut last_end: usize = 0;
        for (cv, index_entry) in &self.index_data {
            // println!("Validating {} {} section index {} entry: {}", self.work_name(), self.bos_book_code(), cv, index_entry);
            if cv.chapter()=="-1" && cv.verse()=="0" { have_m1_0 = true; }
            if cv.chapter()=="1" && cv.verse()=="0" { have_1_0 = true; }
            if cv.chapter()=="1" && (cv.verse()=="1" || cv.verse_int().unwrap()==1) { have_1_1 = true; } // Could be a verse bridge, e.g., '1-2'
            assert!(!cv.chapter().is_empty() && (cv.chapter().chars().all(|c| c.is_ascii_digit()) || cv.chapter() == "-1"),
                "{} {} chapter should be a non-empty string of digits or '-1': found '{}' from {}",
                self.work_name, self.bos_book_code, cv.chapter(), cv);
            assert!(!cv.verse().is_empty() && cv.verse().chars().all(|c| c.is_ascii_digit() || c=='-' || c=='b' || c=='c' || c=='p'),
                "{} {} verse should be a non-empty string of digits (or a verse bridge): found '{}' from {}",
                self.work_name, self.bos_book_code, cv.verse(), cv);

            if index_entry.start_index() < last_end {
                issues.push(format!("{} {} {}: start_index {} < previous end {}",
                    self.work_name(), self.bos_book_code(), cv, index_entry.start_index(), last_end));
            }

            if cv.chapter() == "-1"  {
                assert_eq!(cv.verse().parse::<usize>().unwrap(), index_entry.start_index(),
                    "Unexpected {} {} start index of {} for {} entry: {}",
                    self.work_name, self.bos_book_code, index_entry.start_index(), cv, index_entry);
                if !["Headers","is1"].contains(&index_entry.reason_marker()) {
                    assert_eq!(index_entry.end_verse_num_str().parse::<usize>(), Ok(index_entry.entry_count()),
                        "Unexpected {} {} end index of {} for {} entry: {}\nfrom {}",
                        self.work_name, self.bos_book_code, index_entry.entry_count(), cv, index_entry, line_entries);
                }
            }
            
            else { // We're now into the chapters

                // for processed_line_entry in self.entries.slice(entry.start_index(), entry.end_index()) {
                //     if processed_line_entry.marker() == "v" || processed_line_entry.marker() == "¬v" {
                //         assert!(processed_line_entry.clean_text().starts_with(cv.verse().to_string().as_str()), "Validating {} {} CV index entry for {} found unexpected verse marker with text {}='{}'\n\n{}:{} {}\n\n{} {}\n\n{}:{} {}",
                //             self.work_name(), self.bos_book_code(), cv, processed_line_entry.marker(),processed_line_entry.clean_text(),
                //             cv.chapter(), cv.verse_int().unwrap_or(1)-1, self.format_section_result(self.get_section_entries(&ChapterVerse::new(cv.chapter(), (cv.verse_int().unwrap_or(1) - 1).to_string().as_str()))),
                //             cv, self.format_section_result(self.get_section_entries(cv)),
                //             cv.chapter(), cv.verse_int().unwrap_or(1)+1, self.format_section_result(self.get_section_entries(&ChapterVerse::new(cv.chapter(), (cv.verse_int().unwrap_or(1) + 1).to_string().as_str()))));
                //         }
                //     }
                
                if !index_entry.reason_marker().contains("ms1") { // Check that the segment finishes with an end marker
                    let final_marker_in_entry = self.line_entries.get(index_entry.start_index() + index_entry.entry_count() as usize - 1).map(|e| e.marker()).unwrap_or("N/A");
                    if !is_end_marker(final_marker_in_entry) && cv.verse() != "0" {
                        // println!("Entry for {} {} {} is at index {} with end marker '{}'", self.work_name(), self.bos_book_code(), cv, entry.start_index(), final_marker_in_entry);
                        // assert!(cv.verse()=="0" || is_end_marker(final_marker_in_entry),
                        //     "Validating {} {} CV index entry for {} expected last entry to be an end marker but found marker '{}'",
                        //     self.work_name(), self.bos_book_code(), cv, final_marker_in_entry);
                        issues.push(format!(
                            "{} {} section index entry for {} expected last entry to be an end marker but found marker '{}'",
                            self.work_name(), self.bos_book_code(), cv, final_marker_in_entry
                        ));
                        }
                    }
                }
                last_end = index_entry.end_index() + 1; // Next section has to start after this one finishes
            }

        assert!(have_m1_0 || line_entries.get(0).unwrap().marker()=="chapters", // i.e., no preliminary markers at all!!!
                    "Expected {} {} section index '-1:0' entry:\nKeys {:?}\nHave {:?}\nFrom {:?}",
                    self.work_name(), self.bos_book_code(), self.index_data.keys(), self.index_data.iter().take(4).collect::<std::collections::HashMap<_, _>>(), line_entries.iter().take(10).collect::<std::vec::Vec<_>>());
        assert!(have_1_0 || have_1_1 || !is_chapter_verse_book(&self.bos_book_code),
                    "{} {} section index is missing 1:1 entry\nKeys {:?}\nHave {:?}\nFrom {:?}",
                    self.work_name(), self.bos_book_code(), self.index_data.keys(), self.index_data.iter().take(6).collect::<std::collections::HashMap<_, _>>(), line_entries.iter().take(10).collect::<std::vec::Vec<_>>());
        // Temporarily disabled but should it be reenabled again???
        // // Check that all entries are covered
        // if last_end != self.entries.len() {
        //     issues.push(format!(
        //         "{} {} section index covers {} entries but list has {}",
        //         self.work_name(), self.bos_book_code(), last_end, self.entries.len()));
        // }

        issues
    }
}


/// Tracks a section being built before it's finalized and inserted into the index.
#[derive(Debug)]
struct PendingSection {
    /// `None` when the start CV isn't known yet (heading appeared before first verse).
    start_cv: Option<ChapterVerse>,
    start_index: u32,
    reason: CompactString,
    name: String,
    // Whether this section has had actual content (text) yet.
    // has_content: bool,
}

impl PendingSection {
    fn into_closed(
        self,
        end_chapter: &str,
        end_verse: &str,
        end_index: u32,
        context: Vec<CompactString>,
    ) -> (ChapterVerse, SectionIndexEntry) {
        let start_cv = self.start_cv.expect("section closed before start CV was resolved");
        if have_strict_checking_flag() || cfg!(debug_assertions) {
            println!("      Wanting to close pending {} {} section with {}:{} at {} with {}:[{}]",
                start_cv, self.start_index, end_chapter, end_verse, end_index, self.reason, context.join(", "));
            assert!(end_index > self.start_index || self.reason.contains("ms1"),
                "Attempting to close {} start_index={} section at end_index={}", start_cv, self.start_index, end_index);
            assert!(get_small_leading_int(end_verse).unwrap() >= start_cv.verse_int().unwrap() || get_small_leading_int(end_chapter).unwrap() > start_cv.chapter_int().unwrap() || self.reason.contains("ms1"),
                "Attempting to close {} section at {}:{}", start_cv, end_chapter, end_verse);
            }
        let entry = SectionIndexEntry::new(
            end_chapter,
            end_verse,
            self.start_index,
            (end_index - self.start_index + 1) as u16,
            self.reason,
            self.name,
            context,
        );
        (start_cv, entry)
    }
}

// /// Check if a marker is a section-defining marker.
// fn is_section_marker(marker: &str) -> bool {
//     SECTION_MARKERS.contains(&marker)
// }

impl std::fmt::Display for InternalBibleBookSectionIndex {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        writeln!(
            f,
            "InternalBibleBookSectionIndex({} {}):",
            self.work_name, self.bos_book_code
        )?;
        if !self.indexed {
            writeln!(f, "  Not indexed")?;
        } else if self.index_data.is_empty() {
            writeln!(f, "  Empty")?;
        } else {
            writeln!(f, "  {} sections", self.index_data.len())?;
            for (i, (cv, entry)) in self.index_data.iter().enumerate() {
                if i >= 20 {
                    writeln!(f, "  ...")?;
                    break;
                }
                writeln!(f, "  {}: {}", cv, entry)?;
            }
        }
        Ok(())
    }
}

#[cfg(test)]

mod tests {
    use super::*;
    use crate::entry::InternalBibleEntry;
    use crate::set_strict_checking_flag;
    
    fn create_sample_gen_test_entries() -> InternalBibleEntryList {
        let mut entries = InternalBibleEntryList::new();

        // Section 1 (Headers)
        entries.push(InternalBibleEntry::simple("id", "GEN Test Version")); // 0
        entries.push(InternalBibleEntry::simple("usfm", "3.0")); // 1
        entries.push(InternalBibleEntry::simple("ide", "UTF-8")); // 2
        entries.push(InternalBibleEntry::simple("headers", "")); // 3
        entries.push(InternalBibleEntry::simple("h", "Genesis")); // 4
        entries.push(InternalBibleEntry::simple("mt1", "Book of Genesis")); // 5
        entries.push(InternalBibleEntry::simple("¬headers", "")); // 6

        // Section 2 (Intro)
        entries.push(InternalBibleEntry::simple("intro", "")); // 7
        entries.push(InternalBibleEntry::simple("is1", "Introduction to Genesis")); // 8
        entries.push(InternalBibleEntry::simple("ip", "An introductory paragraph.")); // 9
        entries.push(InternalBibleEntry::simple("¬intro", "")); // 10

        // Section 3
        entries.push(InternalBibleEntry::simple("chapters", "")); // 11
        entries.push(InternalBibleEntry::simple("c", "1")); // 12
        entries.push(InternalBibleEntry::simple("v=", "1")); // 13
        entries.push(InternalBibleEntry::simple("s1", "The Creation")); // 14
        entries.push(InternalBibleEntry::simple("p", "")); // 15
        entries.push(InternalBibleEntry::simple("v", "1")); // 16
        entries.push(InternalBibleEntry::simple("v~", "In the beginning...")); // 17
        entries.push(InternalBibleEntry::simple("v", "2")); // 18
        entries.push(InternalBibleEntry::simple("v~", "And the earth was without form...")); // 19
        entries.push(InternalBibleEntry::simple("¬c", "1")); // 20
        entries.push(InternalBibleEntry::simple("c", "2")); // 21
        entries.push(InternalBibleEntry::simple("nb", "")); // 22
        entries.push(InternalBibleEntry::simple("v", "1")); // 23
        entries.push(InternalBibleEntry::simple("v~", "Verse 1 of chapter 2...")); // 24
        entries.push(InternalBibleEntry::simple("¬p", "")); // 25
        
        // Section 4
        entries.push(InternalBibleEntry::simple("v=", "2")); // 26
        entries.push(InternalBibleEntry::simple("s1", "The Fall")); // 27
        entries.push(InternalBibleEntry::simple("p", "")); // 28
        entries.push(InternalBibleEntry::simple("v", "2")); // 29
        entries.push(InternalBibleEntry::simple("v~", "Verse 2 of chapter 2...")); // 30
        entries.push(InternalBibleEntry::simple("v", "3")); // 31
        entries.push(InternalBibleEntry::simple("v~", "Verse 3 of chapter 2...")); // 32
        entries.push(InternalBibleEntry::simple("¬p", "")); // 33
        entries.push(InternalBibleEntry::simple("¬c", "2")); // 34

        // Section 5
        entries.push(InternalBibleEntry::simple("c", "3")); // 35
        entries.push(InternalBibleEntry::simple("v=", "1")); // 36
        entries.push(InternalBibleEntry::simple("s1", "Chapter Three")); // 37
        entries.push(InternalBibleEntry::simple("rem", "/s1 Alternative heading")); // 38
        entries.push(InternalBibleEntry::simple("p", "")); // 39
        entries.push(InternalBibleEntry::simple("v", "1")); // 40
        entries.push(InternalBibleEntry::simple("v~", "Verse 1 of chapter 3...")); // 41
        entries.push(InternalBibleEntry::simple("v", "2")); // 42
        entries.push(InternalBibleEntry::simple("v~", "Verse 2 of chapter 3...")); // 43
        entries.push(InternalBibleEntry::simple("¬p", "")); // 44
        entries.push(InternalBibleEntry::simple("¬c", "3")); // 45
        entries.push(InternalBibleEntry::simple("¬chapters", "")); // 46

        entries
    }

    #[test]
    fn test_build_sample_gen_section_index() {
        set_strict_checking_flag( true );
        let mut section_index = InternalBibleBookSectionIndex::new("XAV", "GEN");
        section_index.build(create_sample_gen_test_entries()).unwrap();
        log::trace!("Index1:{}", section_index);
        assert!(section_index.is_indexed());

        assert_eq!(section_index.len(), 5, "{section_index}"); // Headers, is1, s1 (Creation), s1 (Fall), s1 (Chapter Three)
        let section_reasons: Vec<_> = section_index.index_data.iter().map(|(_, entry)| entry.reason_marker().to_string()).collect();
        assert_eq!(section_reasons, vec!["Headers", "is1", "s1/c", "s1", "s1/c"]);

        let first_section = section_index.index_data.get_index(0).unwrap();
        assert_eq!(first_section.0.to_string(), "-1:0"); // ID Header starts at -1:0
        assert_eq!(first_section.1.end_cv().to_string(), "-1:6"); // ID Header ends at -1:6
        assert_eq!(first_section.1.start_index(), 0); // starts at id
        assert_eq!(first_section.1.end_index(), 6); // ends at ¬headers
        assert_eq!(first_section.1.reason_marker(), "Headers");
        assert_eq!(first_section.1.section_name(), "GEN");
        assert_eq!(first_section.1.context(), Vec::<CompactString>::new());

        let second_section = section_index.index_data.get_index(1).unwrap();
        assert_eq!(second_section.0.to_string(), "-1:8"); // starts at -1:8 // was -1:8
        assert_eq!(second_section.1.end_cv().to_string(), "-1:10"); // ends at -1:10
        assert_eq!(second_section.1.start_index(), 8); // starts at is1
        assert_eq!(second_section.1.end_index(), 10); // ends at ¬intro
        assert_eq!(second_section.1.reason_marker(), "is1");
        assert_eq!(second_section.1.section_name(), "Introduction to Genesis");
        assert_eq!(second_section.1.context(), Vec::<CompactString>::new());

        let third_section = section_index.index_data.get_index(2).unwrap();
        assert_eq!(third_section.0.to_string(), "1:1"); // starts at 1:1
        assert_eq!(third_section.1.end_cv().to_string(), "2:1"); // ends at 2:1
        assert_eq!(third_section.1.start_index(), 12); // starts at the c before s1 marker
        assert_eq!(third_section.1.end_index(), 25); // ends at ¬p
        assert_eq!(third_section.1.reason_marker(), "s1/c");
        assert_eq!(third_section.1.section_name(), "The Creation");
        assert_eq!(third_section.1.context(), ["chapters", "c"]);

        let fourth_section = section_index.index_data.get_index(3).unwrap();
        assert_eq!(fourth_section.0.to_string(), "2:2"); // starts at 2:2
        assert_eq!(fourth_section.1.end_cv().to_string(), "2:3"); // ends at 2:3
        assert_eq!(fourth_section.1.start_index(), 26); // starts at the v= before s1 marker
        assert_eq!(fourth_section.1.end_index(), 34); // ends at ¬c
        assert_eq!(fourth_section.1.reason_marker(), "s1");
        assert_eq!(fourth_section.1.section_name(), "The Fall");
        assert_eq!(fourth_section.1.context(), ["chapters", "c"]);

        let fifth_section = section_index.index_data.get_index(4).unwrap();
        assert_eq!(fifth_section.0.to_string(), "3:1"); // starts at 3:1
        assert_eq!(fifth_section.1.end_cv().to_string(), "3:2"); // ends at 3:2
        assert_eq!(fifth_section.1.start_index(), 35); // starts at the c before s1 marker
        assert_eq!(fifth_section.1.end_index(), 45); // Don't include the ¬chapters
        assert_eq!(fifth_section.1.reason_marker(), "s1/c");
        assert_eq!(fifth_section.1.section_name(), "Chapter Three");
        assert_eq!(fifth_section.1.context(), ["chapters", "c"]);
    }

    #[test]
    fn test_test_kjb_mark() {
        set_strict_checking_flag( true );
        let mut entries = InternalBibleEntryList::new();
        entries.push(InternalBibleEntry::simple("id", "MRK")); // 0
        entries.push(InternalBibleEntry::simple("usfm", "3.0")); // 1
        entries.push(InternalBibleEntry::simple("ide", "UTF-8")); // 2
        entries.push(InternalBibleEntry::simple("headers", "")); // 3
        entries.push(InternalBibleEntry::simple("h", "Mark")); // 4
        entries.push(InternalBibleEntry::simple("toc1", "Mark")); // 5
        entries.push(InternalBibleEntry::simple("toc2", "Mark")); // 6
        entries.push(InternalBibleEntry::simple("toc3", "Mrk")); // 7
        entries.push(InternalBibleEntry::simple("ie", "")); // 8
        entries.push(InternalBibleEntry::simple("¬headers", "")); // 9
        entries.push(InternalBibleEntry::simple("chapters", "")); // 10
        entries.push(InternalBibleEntry::simple("cl", "CHAP")); // 11
        entries.push(InternalBibleEntry::simple("c", "1")); // 12
        entries.push(InternalBibleEntry::simple("iex", "1 The office of Iohn the Baptist. 9 Iesus is baptized, 12 tempted, 14 he preacheth: 16 calleth Peter, Andrew, Iames and Iohn: 23 healeth one that had a deuill, 29 Peters mother in law, 32 many diseased persons, 41 and cleanseth the Leper.")); // 13
        entries.push(InternalBibleEntry::simple("v", "1")); // 14
        entries.push(InternalBibleEntry::simple("v~", "¶ The beginning of the Gospel of Iesus Christ, the Sonne of God,")); // 15
        entries.push(InternalBibleEntry::simple("¬v", "1")); // 16
        entries.push(InternalBibleEntry::simple("v", "2")); // 17
        entries.push(InternalBibleEntry::simple("v~", "As it is written in the Prophets, Behold, I send my messenger before thy face, which shall prepare thy way before thee.")); // 18
        entries.push(InternalBibleEntry::simple("¬v", "2")); // 19
        entries.push(InternalBibleEntry::simple("¬c", "1")); // 20
        entries.push(InternalBibleEntry::simple("¬chapters", "")); // 21

        let mut section_index = InternalBibleBookSectionIndex::new("KJB", "TST");
        section_index.build(entries).unwrap();

        assert_eq!(section_index.len(), 2);
        let section_reasons: Vec<_> = section_index.index_data.iter().map(|(_, entry)| entry.reason_marker().to_string()).collect();
        assert_eq!(section_reasons, vec!["Headers", "c"]);

        let second_section = section_index.index_data.get_index(1).unwrap();
        assert_eq!(second_section.0.to_string(), "1:1");
        assert_eq!(second_section.1.start_index(), 11); // The 'cl' marker
        assert_eq!(second_section.1.end_index(), 20); // The '¬c' marker
    }

    #[test]
    fn test_section_index_with_single_section_heading_at_verse_2() {
        set_strict_checking_flag( true );
        let mut entries = InternalBibleEntryList::new();
        entries.push(InternalBibleEntry::simple("id", "TST")); // 0
        entries.push(InternalBibleEntry::simple("headers", "")); // 1
        entries.push(InternalBibleEntry::simple("h", "Test1")); // 2
        entries.push(InternalBibleEntry::simple("¬headers", "")); // 3
        entries.push(InternalBibleEntry::simple("chapters", "")); // 4
        entries.push(InternalBibleEntry::simple("c", "1")); // 5
        entries.push(InternalBibleEntry::simple("v", "1")); // 6
        entries.push(InternalBibleEntry::simple("v~", "First section text")); // 7
        entries.push(InternalBibleEntry::simple("¬v", "1")); // 8
        entries.push(InternalBibleEntry::simple("v=", "2")); // 9
        entries.push(InternalBibleEntry::simple("s1", "Second section")); // 10
        entries.push(InternalBibleEntry::simple("p", "")); // 11
        entries.push(InternalBibleEntry::simple("v", "2")); // 12
        entries.push(InternalBibleEntry::simple("v~", "Second section text")); // 13
        entries.push(InternalBibleEntry::simple("¬v", "2")); // 14
        entries.push(InternalBibleEntry::simple("¬c", "1")); // 15
        entries.push(InternalBibleEntry::simple("¬chapters", "")); // 16

        let mut section_index = InternalBibleBookSectionIndex::new("XSV", "TST");
        section_index.build(entries).unwrap();

        assert_eq!(section_index.len(), 3);
        let section_reasons: Vec<_> = section_index.index_data.iter().map(|(_, entry)| entry.reason_marker().to_string()).collect();
        assert_eq!(section_reasons, vec!["Headers", "c", "s1"]);

        let second_section = section_index.index_data.get_index(1).unwrap();
        assert_eq!(second_section.0.to_string(), "1:1");
        assert_eq!(second_section.1.start_index(), 5);
        assert_eq!(second_section.1.end_index(), 8);

        let third_section = section_index.index_data.get_index(2).unwrap();
        assert_eq!(third_section.0.to_string(), "1:2");
        assert_eq!(third_section.1.start_index(), 9);
        assert_eq!(third_section.1.end_index(), 15); // The '¬c' marker
    }

    #[test]
    fn test_section_index_with_ms1() {
        set_strict_checking_flag( true );
        let mut entries = InternalBibleEntryList::new();
        entries.push(InternalBibleEntry::simple("id", "JOB")); // 0
        entries.push(InternalBibleEntry::simple("headers", "")); // 1
        entries.push(InternalBibleEntry::simple("h", "Test1")); // 2
        entries.push(InternalBibleEntry::simple("¬headers", "")); // 3
        entries.push(InternalBibleEntry::simple("chapters", "")); // 4
        entries.push(InternalBibleEntry::simple("c", "1")); // 5
        entries.push(InternalBibleEntry::simple("v=", "1")); // 6
        entries.push(InternalBibleEntry::simple("ms1", "SECTION ONE: The introduction")); // 7
        entries.push(InternalBibleEntry::simple("mr", "(1:1–2:1)")); // 8
        entries.push(InternalBibleEntry::simple("s1", "Iyyov's prosperous life")); // 9
        entries.push(InternalBibleEntry::simple("rem", "/s1 Prologue; Job and His Family; Satan Tests Job")); // 10
        entries.push(InternalBibleEntry::simple("p", "")); // 11
        entries.push(InternalBibleEntry::simple("v", "1")); // 12
        entries.push(InternalBibleEntry::simple("v~", "First section text")); // 13
        entries.push(InternalBibleEntry::simple("¬v", "1")); // 14
        entries.push(InternalBibleEntry::simple("v=", "2")); // 15
        entries.push(InternalBibleEntry::simple("s1", "Second section")); // 16
        entries.push(InternalBibleEntry::simple("p", "")); // 17
        entries.push(InternalBibleEntry::simple("v", "2")); // 18
        entries.push(InternalBibleEntry::simple("v~", "Second section text")); // 19
        entries.push(InternalBibleEntry::simple("¬v", "2")); // 20
        entries.push(InternalBibleEntry::simple("¬c", "1")); // 21
        entries.push(InternalBibleEntry::simple("c", "2")); // 22
        entries.push(InternalBibleEntry::simple("v=", "1")); // 23
        entries.push(InternalBibleEntry::simple("s1", "Chapter two heading")); // 24
        entries.push(InternalBibleEntry::simple("rem", "/s1 Some alterative")); // 25
        entries.push(InternalBibleEntry::simple("p", "")); // 26
        entries.push(InternalBibleEntry::simple("v", "1")); // 27
        entries.push(InternalBibleEntry::simple("v~", "Text for 2:1.")); // 28
        entries.push(InternalBibleEntry::simple("¬v", "1")); // 29
        entries.push(InternalBibleEntry::simple("v=", "2")); // 30
        entries.push(InternalBibleEntry::simple("ms1", "SECTION TWO: Not at chapter break")); // 31
        entries.push(InternalBibleEntry::simple("mr", "(2:2–2:3)")); // 32
        entries.push(InternalBibleEntry::simple("s1", "Third section")); // 33
        entries.push(InternalBibleEntry::simple("p", "")); // 34
        entries.push(InternalBibleEntry::simple("v", "2")); // 35
        entries.push(InternalBibleEntry::simple("v~", "Text for 2:2.")); // 36
        entries.push(InternalBibleEntry::simple("¬v", "2")); // 37
        entries.push(InternalBibleEntry::simple("¬c", "2")); // 38
        entries.push(InternalBibleEntry::simple("¬chapters", "")); // 39

        let mut section_index = InternalBibleBookSectionIndex::new("PQR", "JOB");
        section_index.build(entries).unwrap();

        assert_eq!(section_index.len(), 7);
        let section_reasons: Vec<_> = section_index.index_data.iter().map(|(_, entry)| entry.reason_marker().to_string()).collect();
        assert_eq!(section_reasons, vec!["Headers", "ms1/c", "s1/c", "s1", "s1/c", "ms1", "s1"]);

        let second_section = section_index.index_data.get_index(1).unwrap();
        assert_eq!(second_section.0.to_string(), "1:0");
        assert_eq!(second_section.1.start_index(), 5);
        assert_eq!(second_section.1.end_index(), 8);

        let third_section = section_index.index_data.get_index(2).unwrap();
        assert_eq!(third_section.0.to_string(), "1:1");
        assert_eq!(third_section.1.start_index(), 9);
        assert_eq!(third_section.1.end_index(), 14);

        let fourth_section = section_index.index_data.get_index(3).unwrap();
        assert_eq!(fourth_section.0.to_string(), "1:2");
        assert_eq!(fourth_section.1.start_index(), 15);
        assert_eq!(fourth_section.1.end_index(), 21);

        let fifth_section = section_index.index_data.get_index(4).unwrap();
        assert_eq!(fifth_section.0.to_string(), "2:1");
        assert_eq!(fifth_section.1.start_index(), 22);
        assert_eq!(fifth_section.1.end_index(), 29);

        let sixth_section = section_index.index_data.get_index(5).unwrap();
        assert_eq!(sixth_section.0.to_string(), "2:2p"); // p for prelliminary
        assert_eq!(sixth_section.1.start_index(), 30);
        assert_eq!(sixth_section.1.end_index(), 32);

        let seventh_section = section_index.index_data.get_index(6).unwrap();
        assert_eq!(seventh_section.0.to_string(), "2:2");
        assert_eq!(seventh_section.1.start_index(), 33);
        assert_eq!(seventh_section.1.end_index(), 38);
    }

    #[test]
    fn test_normal_plus_midverse_section_headings() {
        set_strict_checking_flag( true );
        let mut entries = InternalBibleEntryList::new();
        entries.push(InternalBibleEntry::simple("id", "TST")); // 0
        entries.push(InternalBibleEntry::simple("headers", "")); // 1
        entries.push(InternalBibleEntry::simple("h", "Test2")); // 2
        entries.push(InternalBibleEntry::simple("¬headers", "")); // 3

        entries.push(InternalBibleEntry::simple("chapters", "")); // 4
        entries.push(InternalBibleEntry::simple("c", "1")); // 5
        entries.push(InternalBibleEntry::simple("v", "1")); // 6
        entries.push(InternalBibleEntry::simple("v~", "Verse one text")); // 7
        entries.push(InternalBibleEntry::simple("¬v", "1")); // 8
        entries.push(InternalBibleEntry::simple("v=", "2")); // 9
        entries.push(InternalBibleEntry::simple("s1", "First section heading")); // 10
        entries.push(InternalBibleEntry::simple("p", "")); // 11
        entries.push(InternalBibleEntry::simple("v", "2")); // 12
        entries.push(InternalBibleEntry::simple("v~", "Verse two text")); // 13
        entries.push(InternalBibleEntry::simple("¬v", "2")); // 14
        entries.push(InternalBibleEntry::simple("v", "3")); // 15
        entries.push(InternalBibleEntry::simple("v~", "Verse three text")); // 16
        entries.push(InternalBibleEntry::simple("¬p", "")); // 17
        entries.push(InternalBibleEntry::simple("¬s1", "")); // 18
        entries.push(InternalBibleEntry::simple("v=", "3b")); // 19
        entries.push(InternalBibleEntry::simple("s1", "Second section heading")); // 20
        entries.push(InternalBibleEntry::simple("p", "")); // 21
        entries.push(InternalBibleEntry::simple("v~", "More verse three text")); // 22
        entries.push(InternalBibleEntry::simple("¬v", "3")); // 23
        entries.push(InternalBibleEntry::simple("¬p", "")); // 24
        entries.push(InternalBibleEntry::simple("¬s1", "")); // 25
        entries.push(InternalBibleEntry::simple("¬c", "1")); // 26
        entries.push(InternalBibleEntry::simple("¬chapters", "")); // 27

        let mut section_index = InternalBibleBookSectionIndex::new("YSV", "TST");
        section_index.build(entries).unwrap();

        let sections: Vec<_> = section_index.index_data.iter().map(|(_, entry)| entry.reason_marker().to_string()).collect();
        assert_eq!(sections, vec!["Headers", "c", "s1", "s1"]);

        let second_section = section_index.index_data.get_index(1).unwrap();
        assert_eq!(second_section.0.to_string(), "1:1");
        assert_eq!(second_section.1.end_cv().to_string(), "1:1");
        assert_eq!(second_section.1.start_index(), 5);
        assert_eq!(second_section.1.end_index(), 8);

        let third_section = section_index.index_data.get_index(2).unwrap();
        assert_eq!(third_section.0.to_string(), "1:2");
        assert_eq!(third_section.1.end_cv().to_string(), "1:3a");
        assert_eq!(third_section.1.start_index(), 9);
        assert_eq!(third_section.1.end_index(), 18);

        let fourth_section = section_index.index_data.get_index(3).unwrap();
        assert_eq!(fourth_section.0.to_string(), "1:3b");
        assert_eq!(fourth_section.1.end_cv().to_string(), "1:3");
        assert_eq!(fourth_section.1.start_index(), 19);
        assert_eq!(fourth_section.1.end_index(), 26);
    }

    fn create_sample_mrk_test_entries() -> InternalBibleEntryList {
        let mut entries = InternalBibleEntryList::new();

        // Section 1 (Headers)
        entries.push(InternalBibleEntry::simple("id", "MRK Test Version")); // 0
        entries.push(InternalBibleEntry::simple("usfm", "3.0")); // 1
        entries.push(InternalBibleEntry::simple("headers", "")); // 2
        entries.push(InternalBibleEntry::simple("h", "Mark")); // 3
        entries.push(InternalBibleEntry::simple("mt1", "Mark")); // 4
        entries.push(InternalBibleEntry::simple("¬headers", "")); // 5

        entries.push(InternalBibleEntry::simple("chapters", "")); // 6

        // Section 2 Chapter begins WITHOUT a section heading (should be absorbed into the first section)
        entries.push(InternalBibleEntry::simple("c", "1")); // 7
        entries.push(InternalBibleEntry::simple("p", "")); // 8
        entries.push(InternalBibleEntry::simple("v", "1")); // 9
        entries.push(InternalBibleEntry::simple("v~", "First verse of Mark...")); // 10
        entries.push(InternalBibleEntry::simple("¬v", "1")); // 11
        entries.push(InternalBibleEntry::simple("v", "2")); // 12
        entries.push(InternalBibleEntry::simple("v~", "Verse 2 of Mark 1...")); // 13
        entries.push(InternalBibleEntry::simple("¬v", "2")); // 14

        // Section 3
        entries.push(InternalBibleEntry::simple("v=", "3")); // 15
        entries.push(InternalBibleEntry::simple("s1", "First section heading")); // 16
        entries.push(InternalBibleEntry::simple("p", "")); // 17
        entries.push(InternalBibleEntry::simple("v", "3")); // 18
        entries.push(InternalBibleEntry::simple("v~", "Verse 3 of chapter 1...")); // 19
        entries.push(InternalBibleEntry::simple("v", "4")); // 20
        entries.push(InternalBibleEntry::simple("v~", "Verse 4 of chapter 1...")); // 21
        entries.push(InternalBibleEntry::simple("¬s1", "")); // 22

        // Section 4
        entries.push(InternalBibleEntry::simple("v=", "4b")); // 23
        entries.push(InternalBibleEntry::simple("s1", "First alternative ending to Mark")); // 24
        entries.push(InternalBibleEntry::simple("p", "")); // 25
        entries.push(InternalBibleEntry::simple("v~", "No verses here--just text...")); // 26
        entries.push(InternalBibleEntry::simple("¬v", "4")); // 27
        entries.push(InternalBibleEntry::simple("¬s1", "")); // 28

        // Section 5
        entries.push(InternalBibleEntry::simple("v=", "9")); // 29
        entries.push(InternalBibleEntry::simple("s1", "Second alternative ending to Mark")); // 30
        entries.push(InternalBibleEntry::simple("p", "")); // 31
        entries.push(InternalBibleEntry::simple("v", "9")); // 32
        entries.push(InternalBibleEntry::simple("v~", "Has verses here...")); // 33
        entries.push(InternalBibleEntry::simple("¬v", "9")); // 34
        entries.push(InternalBibleEntry::simple("¬s1", "")); // 35
        entries.push(InternalBibleEntry::simple("¬c", "1")); // 36
        entries.push(InternalBibleEntry::simple("¬chapters", "")); // 37

        entries
    }

    #[test]
    fn test_build_sample_mrk_section_index() {
        set_strict_checking_flag( true );
        let mut section_index = InternalBibleBookSectionIndex::new("YSV", "MRK");
        section_index.build(create_sample_mrk_test_entries()).unwrap();
        log::trace!("Index2:{}", section_index);
        assert!(section_index.is_indexed());

        assert_eq!(section_index.len(), 5); // Headers, c, s1, s1 x2 (at end)

        let first_section = section_index.index_data.get_index(0).unwrap();
        assert_eq!(first_section.0.to_string(), "-1:0"); // ID Header starts at -1:0
        assert_eq!(first_section.1.end_cv().to_string(), "-1:5"); // ID Header ends at -1:5
        assert_eq!(first_section.1.start_index(), 0); // starts at beginning
        assert_eq!(first_section.1.end_index(), 5); // ends at '¬headers'
        assert_eq!(first_section.1.reason_marker(), "Headers");
        assert_eq!(first_section.1.section_name(), "MRK");

        let second_section = section_index.index_data.get_index(1).unwrap();
        assert_eq!(second_section.0.to_string(), "1:1"); // starts at 1:1
        assert_eq!(second_section.1.end_cv().to_string(), "1:2"); // ends at 1:2
        assert_eq!(second_section.1.start_index(), 7); // starts at c marker
        assert_eq!(second_section.1.end_index(), 14); // ends at ¬v marker
        assert_eq!(second_section.1.reason_marker(), "c");
        assert_eq!(second_section.1.section_name(), "Mark 1");

        let third_section = section_index.index_data.get_index(2).unwrap();
        assert_eq!(third_section.0.to_string(), "1:3"); // starts at 1:3
        assert_eq!(third_section.1.end_cv().to_string(), "1:4a"); // ends at 1:4a
        assert_eq!(third_section.1.start_index(), 15); // starts' at v= marker
        assert_eq!(third_section.1.end_index(), 22); // ends at '¬s1'
        assert_eq!(third_section.1.reason_marker(), "s1");
        assert_eq!(third_section.1.section_name(), "First section heading");

        let fourth_section = section_index.index_data.get_index(3).unwrap();
        assert_eq!(fourth_section.0.to_string(), "1:4b"); // starts at 1:4b
        assert_eq!(fourth_section.1.end_cv().to_string(), "1:4"); // ends at 1:4
        assert_eq!(fourth_section.1.start_index(), 23); // starts at 'v='
        assert_eq!(fourth_section.1.end_index(), 28); // ends at '¬s1'
        assert_eq!(fourth_section.1.reason_marker(), "s1");
        assert_eq!(fourth_section.1.section_name(), "First alternative ending to Mark");

        let fifth_section = section_index.index_data.get_index(4).unwrap();
        assert_eq!(fifth_section.0.to_string(), "1:9"); // starts at 1:4
        assert_eq!(fifth_section.1.end_cv().to_string(), "1:9"); // ends at 1:4
        assert_eq!(fifth_section.1.start_index(), 29); // starts at 'v='
        assert_eq!(fifth_section.1.end_index(), 36); // ends at '¬s1'
        assert_eq!(fifth_section.1.reason_marker(), "s1");
        assert_eq!(fifth_section.1.section_name(), "Second alternative ending to Mark");
    }

    fn create_sample_psa_test_entries() -> InternalBibleEntryList {
        let mut entries = InternalBibleEntryList::new();

        // Section 1 (Headers)
        entries.push(InternalBibleEntry::simple("id", "PSA Test Version")); // 0
        entries.push(InternalBibleEntry::simple("usfm", "3.0")); // 1
        entries.push(InternalBibleEntry::simple("headers", "")); // 2
        entries.push(InternalBibleEntry::simple("mt1", "Psalms")); // 3
        entries.push(InternalBibleEntry::simple("¬headers", "")); // 4

        // Section 2 (Intro)
        entries.push(InternalBibleEntry::simple("intro", "")); // 5
        entries.push(InternalBibleEntry::simple("is1", "Introduction to Psalms")); // 6
        entries.push(InternalBibleEntry::simple("ip", "An introductory paragraph.")); // 7
        entries.push(InternalBibleEntry::simple("ie", "")); // 8
        entries.push(InternalBibleEntry::simple("¬intro", "")); // 9

        // Section 3 Chapter begins WITHOUT a section heading (should be absorbed into the first section)
        entries.push(InternalBibleEntry::simple("chapters", "")); // 10
        entries.push(InternalBibleEntry::simple("c", "1")); // 11
        entries.push(InternalBibleEntry::simple("p", "")); // 12
        entries.push(InternalBibleEntry::simple("v", "1")); // 13
        entries.push(InternalBibleEntry::simple("v~", "First verse of Psalms...")); // 14
        entries.push(InternalBibleEntry::simple("¬v", "1")); // 15
        entries.push(InternalBibleEntry::simple("v", "2")); // 16
        entries.push(InternalBibleEntry::simple("v~", "Verse 2 of Psalm 1...")); // 17
        entries.push(InternalBibleEntry::simple("¬v", "2")); // 18
        entries.push(InternalBibleEntry::simple("¬p", "")); // 19

        // Section 4
        entries.push(InternalBibleEntry::simple("v=", "3")); // 20
        entries.push(InternalBibleEntry::simple("s1", "First section heading mid-chapter")); // 21
        entries.push(InternalBibleEntry::simple("p", "")); // 22
        entries.push(InternalBibleEntry::simple("v", "3")); // 23
        entries.push(InternalBibleEntry::simple("v~", "Verse 3 of Psalm 1...")); // 24
        entries.push(InternalBibleEntry::simple("¬v", "3")); // 25
        entries.push(InternalBibleEntry::simple("v", "4")); // 26
        entries.push(InternalBibleEntry::simple("v~", "Verse 4 of Psalm 1...")); // 27
        entries.push(InternalBibleEntry::simple("¬v", "4")); // 28
        entries.push(InternalBibleEntry::simple("¬p", "")); // 29
        entries.push(InternalBibleEntry::simple("¬c", "1")); // 30

        // Section 5 - chapter change without a new section heading should start a new section
        entries.push(InternalBibleEntry::simple("c", "2")); // 31
        entries.push(InternalBibleEntry::simple("p", "")); // 32
        entries.push(InternalBibleEntry::simple("v", "1")); // 33
        entries.push(InternalBibleEntry::simple("v~", "Verse 1 of Psalm 2...")); // 34
        entries.push(InternalBibleEntry::simple("¬v", "1")); // 35
        entries.push(InternalBibleEntry::simple("v", "2")); // 36
        entries.push(InternalBibleEntry::simple("v~", "Verse 2 of Psalm 2...")); // 37
        entries.push(InternalBibleEntry::simple("¬v", "2")); // 38
        entries.push(InternalBibleEntry::simple("¬p", "")); // 39

        // Section 6 - chapter change with a new section heading should start a new section
        entries.push(InternalBibleEntry::simple("c", "3")); // 40
        entries.push(InternalBibleEntry::simple("v=", "1")); // 41
        entries.push(InternalBibleEntry::simple("s1", "Psa 3 section heading")); // 42
        entries.push(InternalBibleEntry::simple("q1", "")); // 43
        entries.push(InternalBibleEntry::simple("v", "1")); // 44
        entries.push(InternalBibleEntry::simple("v~", "Verse 1 of Psalm 3...")); // 45
        entries.push(InternalBibleEntry::simple("¬v", "1")); // 46
        entries.push(InternalBibleEntry::simple("v", "2")); // 47
        entries.push(InternalBibleEntry::simple("v~", "Verse 2 of Psalm 3...")); // 48
        entries.push(InternalBibleEntry::simple("¬v", "2")); // 49
        entries.push(InternalBibleEntry::simple("¬q1", "")); // 50
        entries.push(InternalBibleEntry::simple("¬c", "3")); // 51
        entries.push(InternalBibleEntry::simple("¬chapters", "")); // 52

        entries
    }

    #[test]
    fn test_build_sample_section_index_psa() {
        set_strict_checking_flag( true );
        let mut section_index = InternalBibleBookSectionIndex::new("ZSV", "PSA");
        section_index.build(create_sample_psa_test_entries()).unwrap();
        log::trace!("PSA index:{}", section_index);
        assert!(section_index.is_indexed());

        assert_eq!(section_index.len(), 6); // Headers, is1, c, s1, c, c/s1 (merged)

        // 0: Headers
        let first_section = section_index.index_data.get_index(0).unwrap();
        assert_eq!(first_section.0.to_string(), "-1:0");
        assert_eq!(first_section.1.end_cv().to_string(), "-1:4");
        assert_eq!(first_section.1.start_index(), 0); // starts at entry index 0
        assert_eq!(first_section.1.end_index(), 4); // ends at
        assert_eq!(first_section.1.reason_marker(), "Headers");
        assert_eq!(first_section.1.section_name(), "PSA");
        assert_eq!(first_section.1.context(), Vec::<CompactString>::new());

        // 1: Intro
        let second_section = section_index.index_data.get_index(1).unwrap();
        assert_eq!(second_section.0.to_string(), "-1:6");
        assert_eq!(second_section.1.end_cv().to_string(), "-1:9");
        assert_eq!(second_section.1.start_index(), 6); // starts at 'is1'
        assert_eq!(second_section.1.end_index(), 9); // ends at '¬intro'
        assert_eq!(second_section.1.reason_marker(), "is1");
        assert_eq!(second_section.1.section_name(), "Introduction to Psalms");
        assert_eq!(second_section.1.context(), Vec::<CompactString>::new());

        // 2: Chapter 1
        let third_section = section_index.index_data.get_index(2).unwrap();
        assert_eq!(third_section.0.to_string(), "1:1");
        assert_eq!(third_section.1.end_cv().to_string(), "1:2");
        assert_eq!(third_section.1.start_index(), 11); // starts at 'c'
        assert_eq!(third_section.1.end_index(), 19); // ends at '¬p'
        assert_eq!(third_section.1.reason_marker(), "c");
        assert_eq!(third_section.1.section_name(), "1");
        assert_eq!(third_section.1.context(), ["chapters","c"]);

        // 3: Mid-chapter heading
        let fourth_section = section_index.index_data.get_index(3).unwrap();
        assert_eq!(fourth_section.0.to_string(), "1:3");
        assert_eq!(fourth_section.1.end_cv().to_string(), "1:4");
        assert_eq!(fourth_section.1.start_index(), 20); // starts at 'v='
        assert_eq!(fourth_section.1.end_index(), 30); // ends at '¬c'
        assert_eq!(fourth_section.1.reason_marker(), "s1");
        assert_eq!(fourth_section.1.section_name(), "First section heading mid-chapter");
        assert_eq!(fourth_section.1.context(), ["chapters","c"]);

        // 4: Chapter 2
        let fifth_section = section_index.index_data.get_index(4).unwrap();
        assert_eq!(fifth_section.0.to_string(), "2:1");
        assert_eq!(fifth_section.1.end_cv().to_string(), "2:2");
        assert_eq!(fifth_section.1.start_index(), 31); // starts at 'c'
        assert_eq!(fifth_section.1.end_index(), 39); // ends at '¬p'
        assert_eq!(fifth_section.1.reason_marker(), "c");
        assert_eq!(fifth_section.1.section_name(), "2");
        assert_eq!(fifth_section.1.context(), ["chapters","c"]);

        // 5: Chapter 3 (merged c/s1)
        let sixth_section = section_index.index_data.get_index(5).unwrap();
        assert_eq!(sixth_section.0.to_string(), "3:1");
        assert_eq!(sixth_section.1.end_cv().to_string(), "3:2");
        assert_eq!(sixth_section.1.start_index(), 40); // starts at 'c''
        assert_eq!(sixth_section.1.end_index(), 51); // ends at '¬c'
        assert_eq!(sixth_section.1.reason_marker(), "c/s1");
        assert_eq!(sixth_section.1.section_name(), "Psa 3 section heading");
        assert_eq!(sixth_section.1.context(), ["chapters","c"]);
    }

    fn create_kjb_style_psa_test_entries() -> InternalBibleEntryList {
        // Mimics KJB-1611 Psalms: each chapter label (\cl) comes AFTER its \c
        //  (standard USFM position), and there's a stray \cl before the first \c.
        let mut entries = InternalBibleEntryList::new();

        entries.push(InternalBibleEntry::simple("id", "KJB Test Version")); // 0
        entries.push(InternalBibleEntry::simple("usfm", "3.0")); // 1
        entries.push(InternalBibleEntry::simple("h", "Psalmes")); // 2
        entries.push(InternalBibleEntry::simple("mt1", "THE BOOKE OF PSALMES")); // 3
        entries.push(InternalBibleEntry::simple("ie", "")); // 4
        entries.push(InternalBibleEntry::simple("cl", "CHAP.")); // 5

        // Psalm 1
        entries.push(InternalBibleEntry::simple("c", "1")); // 6
        entries.push(InternalBibleEntry::simple("cl", "P S A L. I.")); // 7
        entries.push(InternalBibleEntry::simple("iex", "Arguments of the first psalm.")); // 8
        entries.push(InternalBibleEntry::simple("v", "1")); // 9
        entries.push(InternalBibleEntry::simple("v~", "First psalm blessed is the man...")); // 10
        entries.push(InternalBibleEntry::simple("¬v", "1")); // 11
        entries.push(InternalBibleEntry::simple("v", "2")); // 12
        entries.push(InternalBibleEntry::simple("v~", "First psalm but his delight is in the law...")); // 13
        entries.push(InternalBibleEntry::simple("¬v", "2")); // 14

        // Psalm 2
        entries.push(InternalBibleEntry::simple("c", "2")); // 15
        entries.push(InternalBibleEntry::simple("cl", "P S A L. II.")); // 16
        entries.push(InternalBibleEntry::simple("iex", "Arguments of the second psalm.")); // 17
        entries.push(InternalBibleEntry::simple("v", "1")); // 18
        entries.push(InternalBibleEntry::simple("v~", "Second psalm why do the heathen rage...")); // 19
        entries.push(InternalBibleEntry::simple("¬v", "1")); // 20
        entries.push(InternalBibleEntry::simple("v", "2")); // 21
        entries.push(InternalBibleEntry::simple("v~", "Second psalm the kings of the earth...")); // 22
        entries.push(InternalBibleEntry::simple("¬v", "2")); // 23

        // Psalm 3
        entries.push(InternalBibleEntry::simple("c", "3")); // 24
        entries.push(InternalBibleEntry::simple("cl", "P S A L. III.")); // 25
        entries.push(InternalBibleEntry::simple("iex", "Arguments of the third psalm.")); // 26
        entries.push(InternalBibleEntry::simple("v", "1")); // 27
        entries.push(InternalBibleEntry::simple("v~", "Third psalm Lord how are they increased...")); // 28
        entries.push(InternalBibleEntry::simple("¬v", "1")); // 29

        entries
    }

    #[test]
    fn test_chapter_labels_after_c_marker_dont_bleed_previous_section() {
        // With KJB-1611-style data (each \cl after its \c, plus a stray \cl before
        //  the first \c), sections starting at a chapter marker used to collect all
        //  the previous chapter's content because the backwards search for a
        //  preceding chapter label was unbounded.
        set_strict_checking_flag( true );
        let mut section_index = InternalBibleBookSectionIndex::new("KJB", "PSA");
        section_index.build(create_kjb_style_psa_test_entries()).unwrap();
        assert!(section_index.is_indexed());
        assert_eq!(section_index.len(), 4); // Headers + three chapters/psalms

        // Section for Psalm 1 (includes the stray preceding chapter label)
        let (psa1_entries, _) = section_index.get_section_entries_with_context(&ChapterVerse::new("1", "1")).unwrap();
        assert_eq!(psa1_entries.first().unwrap().marker(), "cl"); // the stray 'CHAP.' label
        assert_eq!(psa1_entries.iter().filter(|e| e.marker()=="v").count(), 2);
        assert!(psa1_entries.iter().all(|e| !e.clean_text().contains("second psalm")));

        // Section for Psalm 2 must NOT contain any of Psalm 1's content
        let (psa2_entries, _) = section_index.get_section_entries_with_context(&ChapterVerse::new("2", "1")).unwrap();
        assert_eq!(psa2_entries.first().unwrap().marker(), "c"); // starts at its own chapter marker
        assert!(psa2_entries.iter().any(|e| e.marker()=="cl" && e.clean_text()=="P S A L. II."));
        assert!(psa2_entries.iter().all(|e| !e.clean_text().contains("first psalm")));
        assert_eq!(psa2_entries.iter().filter(|e| e.marker()=="v").count(), 2);

        // Section for Psalm 3 must NOT contain any of Psalm 2's content
        let (psa3_entries, _) = section_index.get_section_entries_with_context(&ChapterVerse::new("3", "1")).unwrap();
        assert_eq!(psa3_entries.first().unwrap().marker(), "c");
        assert!(psa3_entries.iter().any(|e| e.marker()=="cl" && e.clean_text()=="P S A L. III."));
        assert!(psa3_entries.iter().all(|e| !e.clean_text().contains("second psalm")));
        assert_eq!(psa3_entries.iter().filter(|e| e.marker()=="v").count(), 1);

        // Same lookups via get_section_entries must agree
        let psa2_plain = section_index.get_section_entries(&ChapterVerse::new("2", "1")).unwrap();
        assert_eq!(psa2_plain.len(), psa2_entries.len());
    }

    #[test]
    fn test_table_of_contents() {
        set_strict_checking_flag( true );
        let mut section_index = InternalBibleBookSectionIndex::new("XSV", "GEN");
        section_index.build(create_sample_gen_test_entries()).unwrap();

        let toc = section_index.table_of_contents();
        assert!(!toc.is_empty());

        // Check that section names are captured
        let names: Vec<&str> = toc.iter().map(|(_, name, _)| *name).collect();
        assert!(
            names
                .iter()
                .any(|n| n.contains("Creation") || n.contains("Fall") || n == &"1" || n == &"3")
        );
    }

    #[test]
    fn test_get_section_entries() {
        set_strict_checking_flag( true );
        let mut section_index = InternalBibleBookSectionIndex::new("XSV", "GEN");
        section_index.build(create_sample_gen_test_entries()).unwrap();

        // Get first section
        if let Some((cv, _)) = section_index.iter().next() {
            let entries = section_index.get_section_entries(cv).unwrap();
            assert!(!entries.is_empty());
        }
    }

    #[test]
    fn test_oet_rv_haggai_section_index_build() {
        // Note that OET-RV Haggai has NO section headings inside verse boundaries
        set_strict_checking_flag( true );
        let content = include_str!("../../../../Tests/DataFilesForTests/OET-RV/OET-RV_HAG.ESFM");
        let mut raw_lines = Vec::new();
        for line in content.lines() {
            let (marker, text) = match line.split_once(' ') {
                Some((m, t)) => (m, t),
                None => (line, ""),
            };
            let marker = marker.strip_prefix('\\').unwrap_or(marker);
            raw_lines.push((marker.to_string(), text.to_string()));
        }

        let options = crate::processing::ProcessLinesOptions::default();
        let processed_line_entries = crate::processing::process_lines(raw_lines, "HAG", "OET-RV", &options);

        // println!("OET-RV HAG {} processed_line_entries = {}", processed_line_entries.len(), processed_line_entries);
        // OET-RV HAG processed_line_entries = InternalBibleEntryList:
        //     0/ id = "HAG - Open English Translation…ders' Version (OET-RV) v0.1.03"
        //     1/ usfm = "3.0"
        //     2/ ide = "UTF-8"
        //     3/ rem = "ESFM v0.6 HAG"
        //     4/ rem = "WORDTABLE OET-LV_OT_word_table.tsv"
        //     5/ headers = ""
        //     6/ h = "Haggai"
        //     7/ toc1 = "Haggai"
        //     8/ toc2 = "Haggai"
        //     9/ toc3 = "Hag."
        //     10/ mt1 = "Haggai"
        //     11/ ¬headers = ""
        //     12/ intro = ""
        //     13/ is1 = "Introduction"
        //     14/ ip = "This document contains a numbe… bless their living situation."
        //     15/ iot = "Main components of this account"
        //     16/ io1 = "God's command to rebuild the temple 1:1-15"
        //     17/ io1 = "Stories of comfort and hope 2:1-23"
        //     18/ ¬iot = ""
        //     19/ rem = "This is still a very early loo…dvance before using in public."
        //     20/ ie = ""
        //     21/ ¬intro = ""
        //     22/ chapters = ""
        //     23/ c = "1"
        //     24/ v= = "1"
        //     25/ s1 = "God's command to rebuild the temple"
        //     26/ rem = "/s1 The Lord's Command to Rebu… Command to Rebuild the Temple"
        //     27/ p = ""
        //     28/ c# = "1"
        //     29/ v = "1"
        //     30/ v~ = "In Dareyavesh's (Darius's¦3755…375591 son), telling them that" + extras
        //     31/ ¬v = "1"
        //     32/ v = "2"
        //     33/ v~ = "Commander-in-chief Yahweh says…2 Yahweh's¦375598 ≈residence.”"
        //     34/ ¬v = "2"
        //     35/ ¬p = ""
        //     36/ p = ""
        //     37/ v = "3"
        //     38/ v~ = "Then Yahweh¦375618 ≈gave this …gai¦375621 to tell the people:"
        //     39/ ¬v = "3"
        //     40/ ¬p = ""
        //     41/ m = ""
        //     42/ v = "4"
        //     43/ v~ = "Is it a time¦375625 for all of…Yahweh's temple lies in ruins?"
        //     44/ ¬v = "4"
        //     45/ v = "5"
        //     46/ v~ = "≈So¦375635 now Commander-in-ch…e what you're all going to do."
        //     47/ ¬v = "5"
        //     48/ v = "6"
        //     49/ v~ = "You've all planted a lot, ≈but…ets seem to be full of holes.”"
        //     50/ ¬v = "6"
        //     51/ ¬m = ""
        //     52/ p = ""
        //     53/ v = "7"
        //     54/ v~ = "≈So Commander-in-chief Yahweh¦…e what you're all going to do."
        //     55/ ¬v = "7"
        //     56/ v = "8"
        //     57/ v~ = "Go up into the hills¦375682 an…e,” says¦375692 Yahweh¦375693."
        //     58/ ¬v = "8"
        //     59/ ¬p = ""
        //     60/ p = ""
        //     61/ v = "9"
        //     62/ v~ = "“You ≈expected much, but¦37569…y ≈working on your own houses."
        //     63/ ¬v = "9"
        //     64/ v = "10"
        //     65/ v~ = "That's why the sky withholds t…il withholds its¦375733 crops."
        //     66/ ¬v = "10"
        //     67/ v = "11"
        //     68/ v~ = "I've¦375735 ≈summoned¦375735 a… onto ≈everything you all do.”"
        //     69/ ¬v = "11"
        //     70/ ¬p = ""
        //     71/ v= = "12"
        //     72/ s1 = "The people start rebuilding"
        //     73/ rem = "/s1 The People Obey the Lord's…mmand; Obedience to God's Call"
        //     74/ p = ""
        //     75/ v = "12"
        //     76/ v~ = "Then Shealtiyel's son Zerubave… the people ≈respected Yahweh."
        //     77/ ¬v = "12"
        //     78/ v = "13"
        //     79/ v~ = "Then¦375802 Yahweh's¦375805 me…m with¦375806 you¦375811 all.”"
        //     80/ ¬v = "13"
        //     81/ v = "14"
        //     82/ v~ = "Then¦375816 Yahweh ≈inspired S…49, Commander-in-chief Yahweh,"
        //     83/ ¬v = "14"
        //     84/ v = "15"
        //     85/ v~ = "on¦375856 the twenty-fourth da…esh the king¦375860 of Persia."
        //     86/ ¬v = "15"
        //     87/ ¬p = ""
        //     88/ ¬c = "1"
        //     89/ c = "2"
        //     90/ v= = "1"
        //     91/ s1 = "The splendour of the new temple"
        //     92/ rem = "/s1 The Future Glory of the Te…romised Glory of the New House"
        //     93/ p = ""
        //     94/ c# = "2"
        //     95/ v = "1"
        //     96/ v~ = "On the 21st of the seventh¦375… prophet¦375873 Haggai¦375872:"
        //     97/ ¬v = "1"
        //     98/ v = "2"
        //     99/ v~ = "Please ≈ask Shealtiyel's son Z…the rest of the people¦375898,"
        //     100/ ¬v = "2"
        //     101/ v = "3"
        //     102/ v~ = "“≈Are there any of you still a…g¦375919 in¦375902 comparison." + extras
        //     103/ ¬v = "3"
        //     104/ v = "4"
        //     105/ v~ = "Yahweh is telling you now, Zer… with you ≈as you work¦375944."
        //     106/ ¬v = "4"
        //     107/ v = "5"
        //     108/ v~ = "≈That's what I promised¦375955…Don't¦375965 be afraid¦375967," + extras
        //     109/ ¬v = "5"
        //     110/ v = "6"
        //     111/ v~ = "because¦375970 Commander-in-ch…9 and the dry land, once more." + extras
        //     112/ ¬v = "6"
        //     113/ v = "7"
        //     114/ v~ = "I'll shake¦375994 all the nati…mander-in-chief Yahweh¦376012."
        //     115/ ¬v = "7"
        //     116/ v = "8"
        //     117/ v~ = "Commander-in-chief Yahweh¦3760…er¦376016 belong¦376017 to me."
        //     118/ ¬v = "8"
        //     119/ v = "9"
        //     120/ v~ = "*I declare that this ≈temple w…sperity to this place¦376035.”"
        //     121/ ¬v = "9"
        //     122/ ¬p = ""
        //     123/ v= = "10"
        //     124/ s1 = "Haggai consults the priests"
        //     125/ rem = "/s1 Blessings Promised for Obe…e Prophet Consults the Priests"
        //     126/ p = ""
        //     127/ v = "10"
        //     128/ v~ = "On the 24th of the ninth¦37604… prophet¦376057 Haggai¦376056:"
        //     129/ ¬v = "10"
        //     130/ v = "11"
        //     131/ v~ = "Commander-in-chief Yahweh¦3760…Mosheh's ≈instructions¦376070."
        //     132/ ¬v = "11"
        //     133/ v = "12"
        //     134/ v~ = "‘≈If a priest took some meat¦3…r food  become¦376102 holy?’ ”"
        //     135/ ¬p = ""
        //     136/ p = ""
        //     137/ v~ = "“No, it wouldn't,” the priests¦376104 ≈replied."
        //     138/ ¬p = ""
        //     139/ ¬v = "12"
        //     140/ p = ""
        //     141/ v = "13"
        //     142/ v~ = "Then¦376108 Haggai¦376109 aske…ood, would it become unclean?”" + extras
        //     143/ ¬p = ""
        //     144/ p = ""
        //     145/ v~ = "“Yes, it would become unclean,…riests¦376121 answered¦376120."
        //     146/ ¬p = ""
        //     147/ ¬v = "13"
        //     148/ p = ""
        //     149/ v = "14"
        //     150/ v~ = "“≈That's what Yahweh¦376139 de…t transfers to your offerings."
        //     151/ rem = "/s1 The Lord Promises His Blessing"
        //     152/ ¬v = "14"
        //     153/ v = "15"
        //     154/ v~ = "So¦376151 now think back to be…id for Yahweh's¦376169 temple."
        //     155/ ¬v = "15"
        //     156/ v = "16"
        //     157/ v~ = "≈During that time, when someon…re was only enough for twenty."
        //     158/ ¬v = "16"
        //     159/ v = "17"
        //     160/ v~ = "Yahweh¦376205 declares that he…ill didn't¦376199 turn to him."
        //     161/ ¬v = "17"
        //     162/ v = "18"
        //     163/ v~ = "Think back to the time from wh… month¦376219). Consider that."
        //     164/ ¬v = "18"
        //     165/ v = "19"
        //     166/ v~ = "Is any grain left in¦376234 th…bless you from today onwards.”"
        //     167/ ¬v = "19"
        //     168/ ¬p = ""
        //     169/ v= = "20"
        //     170/ s1 = "God's promise to Zerubavel"
        //     171/ rem = "/s1 The Lord's Promise to Zeru…ubbabel the Lord's Signet Ring"
        //     172/ p = ""
        //     173/ v = "20"
        //     174/ v~ = "Then Yahweh¦376254 gave a seco…gai¦376259 on¦376260 the 24th:"
        //     175/ ¬v = "20"
        //     176/ v = "21"
        //     177/ v~ = "Tell Zerubavel, the governor¦3…s¦376277 and the earth¦376280."
        //     178/ ¬v = "21"
        //     179/ v = "22"
        //     180/ v~ = "I'll overthrow the thrones¦376… ≈will kill¦376285 each other."
        //     181/ ¬v = "22"
        //     182/ v = "23"
        //     183/ v~ = "Commander-in-chief Yahweh decl…6316 he's been chosen¦376319.”"
        //     184/ ¬v = "23"
        //     185/ ¬p = ""
        //     186/ ¬c = "2"
        //     187/ ¬chapters = ""

        let mut section_index = InternalBibleBookSectionIndex::new("OET-RV", "HAG");
        section_index.build(processed_line_entries).unwrap();

        // for (ee,(cv,entry)) in section_index.index_data.iter().enumerate() { println!("{}/ {} {}", ee, cv, entry); }
        // It should give the following seven entries:
        //    0 -1:0 InternalBibleBookSectionIndexEntry object: (inclusive) endCV=-1:12 ix=0–12 (cnt=13) Headers='HAG'
        //    1 -1:13 InternalBibleBookSectionIndexEntry object: (inclusive) endCV=-1:22 ix=13–22 (cnt=10) is1='Introduction'
        //    2 1:1 InternalBibleBookSectionIndexEntry object: (inclusive) endCV=1:11 ix=24–69 (cnt=46) s1='God's command to rebuild the temple'
        //    3 1:12 InternalBibleBookSectionIndexEntry object: (inclusive) endCV=1:15 ix=70–87 (cnt=18) s1='The people start rebuilding'
        //    4 2:1 InternalBibleBookSectionIndexEntry object: (inclusive) endCV=2:9 ix=88–119 (cnt=32) s1='The splendour of the new temple'
        //    5 2:10 InternalBibleBookSectionIndexEntry object: (inclusive) endCV=2:19 ix=120–164 (cnt=45) s1='Haggai consults the priests'
        //    6 2:20 InternalBibleBookSectionIndexEntry object: (inclusive) endCV=2:23 ix=165–182 (cnt=18) s1='God's promise to Zerubavel'

        assert_eq!(section_index.len(), 7);
        let sections: Vec<_> = section_index.index_data.iter().map(|(_, entry)| entry.reason_marker().to_string()).collect();
        assert_eq!(sections, vec!["Headers", "is1", "s1/c", "s1", "s1/c", "s1", "s1"]);

        // 0 -1:0 Headers='HAG'
        let (cv0, entry0) = section_index.index_data.get_index(0).unwrap();
        assert_eq!(cv0.to_string(), "-1:0");
        assert_eq!(entry0.end_cv().to_string(), "-1:11");
        assert_eq!(entry0.start_index(), 0);
        assert_eq!(entry0.end_index(), 11);
        assert_eq!(entry0.reason_marker(), "Headers");
        assert_eq!(entry0.section_name(), "HAG");

        // 1 -1:13 is1='Introduction'
        let (cv1, entry1) = section_index.index_data.get_index(1).unwrap();
        assert_eq!(cv1.to_string(), "-1:13");
        assert_eq!(entry1.end_cv().to_string(), "-1:22");
        assert_eq!(entry1.start_index(), 13);
        assert_eq!(entry1.end_index(), 22);
        assert_eq!(entry1.reason_marker(), "is1");
        assert_eq!(entry1.section_name(), "Introduction");

        // 2 1:1 s1='God\'s command to rebuild the temple':
        let (cv2, entry2) = section_index.index_data.get_index(2).unwrap();
        assert_eq!(cv2.to_string(), "1:1");
        assert_eq!(entry2.end_cv().to_string(), "1:11");
        assert_eq!(entry2.start_index(), 24);
        assert_eq!(entry2.end_index(), 72);
        assert_eq!(entry2.reason_marker(), "s1/c");
        assert_eq!(entry2.section_name(), "God's command to rebuild the temple");

        // 3 1:11 s1='The people start rebuilding'
        let (cv3, entry3) = section_index.index_data.get_index(3).unwrap();
        assert_eq!(cv3.to_string(), "1:12");
        assert_eq!(entry3.end_cv().to_string(), "1:15");
        assert_eq!(entry3.start_index(), 73);
        assert_eq!(entry3.end_index(), 91);
        assert_eq!(entry3.reason_marker(), "s1");
        assert_eq!(entry3.section_name(), "The people start rebuilding");

        // 4 2:1 s1='The splendour of the new temple'
        let (cv4, entry4) = section_index.index_data.get_index(4).unwrap();
        assert_eq!(cv4.to_string(), "2:1");
        assert_eq!(entry4.end_cv().to_string(), "2:9");
        assert_eq!(entry4.start_index(), 92);
        assert_eq!(entry4.end_index(), 126);
        assert_eq!(entry4.reason_marker(), "s1/c");
        assert_eq!(entry4.section_name(), "The splendour of the new temple");

        // 5 2:9 s1='Haggai consults the priests'
        let (cv5, entry5) = section_index.index_data.get_index(5).unwrap();
        assert_eq!(cv5.to_string(), "2:10");
        assert_eq!(entry5.end_cv().to_string(), "2:19");
        assert_eq!(entry5.start_index(), 127);
        assert_eq!(entry5.end_index(), 173);
        assert_eq!(entry5.reason_marker(), "s1");
        assert_eq!(entry5.section_name(), "Haggai consults the priests");

        // 6 2:19 s1='God\'s promise to Zerubavel'
        let (cv6, entry6) = section_index.index_data.get_index(6).unwrap();
        assert_eq!(cv6.to_string(), "2:20");
        assert_eq!(entry6.end_cv().to_string(), "2:23");
        assert_eq!(entry6.start_index(), 174);
        assert_eq!(entry6.end_index(), 192); // Don't include the ¬chapters
        assert_eq!(entry6.reason_marker(), "s1");
        assert_eq!(entry6.section_name(), "God's promise to Zerubavel");
    }

    #[test]
    fn test_oet_rv_daniel_section_index_build() {
        // Note that OET-RV Daniel is our smallest book with ms1 section headings (as well as s1 headings of course)
        set_strict_checking_flag( true );
        let content = include_str!("../../../../Tests/DataFilesForTests/OET-RV/OET-RV_DAN.ESFM");
        let mut raw_lines = Vec::new();
        for line in content.lines() {
            let (marker, text) = match line.split_once(' ') {
                Some((m, t)) => (m, t),
                None => (line, ""),
            };
            let marker = marker.strip_prefix('\\').unwrap_or(marker);
            raw_lines.push((marker.to_string(), text.to_string()));
        }

        let options = crate::processing::ProcessLinesOptions::default();
        let processed_line_entries = crate::processing::process_lines(raw_lines, "DAN", "OET-RV", &options);

        // println!("OET-RV DAN {} processed_line_entries = {}", processed_line_entries.len(), processed_line_entries);
        //     OET-RV DAN 1540 processed_line_entries = InternalBibleEntryList:
        //         0/ id = "DAN - Open English Translation…ders' Version (OET-RV) v0.1.09"
        //         1/ usfm = "3.0"
        //         2/ ide = "UTF-8"
        //         3/ rem = "ESFM v0.6 DAN"
        //         4/ rem = "WORDTABLE OET-LV_OT_word_table.tsv"
        //         5/ headers = ""
        //         6/ h = "Daniel"
        //         7/ toc1 = "Daniel"
        //         8/ toc2 = "Daniel"
        //         9/ toc3 = "Dan."
        //         10/ mt1 = "Daniel"
        //         11/ mt3 = "(or Daniyyel)"
        //         12/ ¬headers = ""
        //         13/ intro = ""
        //         14/ is1 = "Introduction"
        //         15/ ip = "This document is about Daniel …adrak, Meyshak, and Avednego)."
        //         16/ ip = "God's revelations which Daniel…uld happen in the ‘end-times’."
        //         17/ ip = "One of the themes of this docu…e also looks after his people."
        //         18/ ip = "This document about Daniel was…from the Phoenician alphabet.)"
        //         19/ iot = "Main components of this account"
        //         20/ io1 = "God's help for Daniel and his friends 1:1–6:28"
        //         21/ io1 = "God's revelations to Daniel through visions 7:1–12:13"
        //         22/ io2 = "a. The four creatures 7:1-28"
        //         23/ io2 = "b. The ram and the goat 8:1–9:27"
        //         24/ io2 = "c. The heavenly messenger 10:1–11:45"
        //         25/ io2 = "d. The time of the end 12:1-13"
        //         26/ ¬iot = ""
        //         27/ rem = "This is still a very early loo…dvance before using in public."
        //         28/ ¬is1 = "28"
        //         29/ ie = ""
        //         30/ ¬intro = ""
        //         31/ chapters = ""
        //         32/ c = "1"
        //         33/ v= = "1"
        //         34/ ms1 = "The account about Daniel and his friends"
        //         35/ mr = "(1:1–6:28)"
        //         36/ s1 = "Daniel and his friends in Babylon"
        //         37/ rem = "/s1 Daniel in Nebuchadnezzar's…lon; Daniel and his companions"
        //         38/ p = ""
        //         39/ c# = "1"
        //         40/ v = "1"
        //         41/ v~ = "In the third year¦356354 of Ye…and¦356367 besieged @the city." + extras
        //         42/ ¬v = "1"
        //         43/ v = "2"
        //         44/ v~ = "After two years, the master¦35…n his god's temple storerooms." + extras
        //         45/ ¬v = "2"
        //         46/ ¬p = ""
        //         47/ p = ""
        //         48/ v = "3"
        //         49/ v~ = "Some time later, King¦356399 N…ome of the prominent families."
        //         50/ ¬v = "3"
        //         51/ v = "4"
        //         52/ v~ = "They had to be good-looking yo…d literature of the Chaldeans,"
        //         53/ ¬v = "4"
        //         54/ v = "5"
        //         55/ v~ = "and king assigned¦356442 a dai…ing the king's¦356461 service."
        //         56/ ¬v = "5"
        //         57/ v = "6"
        //         58/ v~ = "Among the ≈young men from Yehu…el, and¦356470 Azaryah¦356470,"
        //         59/ ¬v = "6"
        //         60/ v = "7"
        //         61/ v~ = "≈but¦356472 @Ashpenaz ≈named t…¦356472 Avednego respectively."
        //         62/ ¬v = "7"
        //         63/ ¬p = ""
        //         64/ p = ""
        //         65/ v = "8"
        //         66/ v~ = "≈However Daniel ≈decided that …z to ≈eat an alternative diet."
        //         67/ ¬v = "8"
        //         68/ v = "9"
        //         69/ v~ = "≈Now God ≈had caused the chief…ike and¦356514 respect Daniel,"
        //         70/ ¬v = "9"
        //         71/ v = "10"
        //         72/ v~ = "≈but¦356519 he ≈queried, “I'm …356552 if the king got angry.”"
        //         73/ ¬v = "10"
        //         74/ ¬p = ""
        //         75/ p = ""
        //         76/ v = "11"
        //         77/ v~ = "≈So¦356555 Daniel asked the st…356561 over @the four of them,"
        //         78/ ¬v = "11"
        //         79/ v = "12"
        //         80/ v~ = "“Please test your¦356576 serva… water¦356586 to drink¦356587,"
        //         81/ ¬v = "12"
        //         82/ v = "13"
        //         83/ v~ = "then¦356589 after that¦356598,…t decision from the evidence.”"
        //         84/ ¬v = "13"
        //         85/ ¬p = ""
        //         86/ p = ""
        //         87/ v = "14"
        //         88/ v~ = "≈So¦356605 the steward ≈agreed…09 started ≈the ten-day trial."
        //         89/ ¬v = "14"
        //         90/ v = "15"
        //         91/ v~ = "At the end of the ten¦356615 d… the king's¦356629 fancy food,"
        //         92/ ¬v = "15"
        //         93/ v = "16"
        //         94/ v~ = "≈so after that, the steward ju…e choice food and¦356631 wine."
        //         95/ ¬v = "16"
        //         96/ ¬p = ""
        //         97/ p = ""
        //         98/ v = "17"
        //         99/ v~ = "≈So¦356643 God gave¦356646 tho…ams¦356660 and visions¦356659."
        //         100/ ¬v = "17"
        //         101/ ¬p = ""
        //         102/ p = ""
        //         103/ v = "18"
        //         104/ v~ = "At the end of @the three years…o King¦356667 Nevukadnetstsar." + extras
        //         105/ ¬v = "18"
        //         106/ v = "19"
        //         107/ v~ = "The king talked with each of t… in the king's¦356687 service—"
        //         108/ ¬v = "19"
        //         109/ v = "20"
        //         110/ v~ = "in every matter¦356690 of wisd… entire¦356702 kingdom¦356709."
        //         111/ ¬v = "20"
        //         112/ v = "21"
        //         113/ v~ = "Daniel continued serving there…of King¦356718 Koresh (Cyrus)."
        //         114/ ¬v = "21"
        //         115/ ¬p = ""
        //         116/ ¬s1 = ""
        //         117/ ¬c = "1"
        //         118/ c = "2"
        //         119/ v= = "1"
        //         120/ s1 = "Nevukadnetstsar's dream"
        //         121/ rem = "/s1 Daniel's wisdom; Nebuchadnezzar's Dream"
        //         122/ p = ""
        //         123/ c# = "2"
        //         124/ v = "1"
        //         125/ v~ = "Back in the second year¦356721…ng him unable to sleep¦356730."
        //         126/ ¬v = "1"
        //         127/ v = "2"
        //         128/ v~ = "*He summoned the magicians¦356…5 in front¦356746 of the king."
        //         129/ ¬v = "2"
        //         130/ v = "3"
        //         131/ v~ = "“I've¦356753 had a dream¦35675…s ≈anxious to understand *it.”"
        //         132/ ¬v = "3"
        //         133/ v = "4"
        //         134/ v~ = "The ≈astrologers spoke¦356761 …ou the interpretation¦356772.”"
        //         135/ ¬v = "4"
        //         136/ ¬p = ""
        //         137/ p = ""
        //         138/ v = "5"
        //         139/ v~ = "“≈I've already made my decisio…6790 made into a rubbish heap."
        //         140/ ¬v = "5"
        //         141/ v = "6"
        //         142/ v~ = "But¦356794 if you all explain …dream and its interpretation.”"
        //         143/ ¬v = "6"
        //         144/ ¬p = ""
        //         145/ p = ""
        //         146/ v = "7"
        //         147/ v~ = "“Let¦356814 the king¦356814 te…ve the interpretation¦356818.”"
        //         148/ ¬v = "7"
        //         149/ ¬p = ""
        //         150/ p = ""
        //         151/ v = "8"
        //         152/ v~ = "“I know for certain¦356826 tha…≈However, I've made up my mind"
        //         153/ ¬v = "8"
        //         154/ v = "9"
        //         155/ v~ = "that if you all don't¦356847 ≈…me its interpretation¦356871.”"
        //         156/ ¬v = "9"
        //         157/ ¬p = ""
        //         158/ p = ""
        //         159/ v = "10"
        //         160/ v~ = "“There's no one ≈in the whole …oger to do that before¦356877!"
        //         161/ ¬v = "10"
        //         162/ v = "11"
        //         163/ v~ = "What¦356924 you're requesting,… dreamt—only the gods¦356926.”"
        //         164/ ¬v = "11"
        //         165/ v = "12"
        //         166/ v~ = "≈That angered the king¦356939,…ise men¦356946 to be executed."
        //         167/ ¬v = "12"
        //         168/ ¬p = ""
        //         169/ p = ""
        //         170/ v = "13"
        //         171/ v~ = "≈When¦356949 the decree¦356949… friends¦356955 were included."
        //         172/ rem = "/s1 God Shows Daniel What the Dream Means"
        //         173/ ¬v = "13"
        //         174/ v = "14"
        //         175/ v~ = "Aryok¦356964 was the captain o…se and¦356963 prudent caution."
        //         176/ ¬v = "14"
        //         177/ ¬p = ""
        //         178/ p = ""
        //         179/ v = "15"
        //         180/ v~ = "He asked the king's commander … ≈explained what had happened,"
        //         181/ ¬v = "15"
        //         182/ v = "16"
        //         183/ v~ = "≈so¦356998 Daniel¦357003 went …interpretation¦357009 to *him."
        //         184/ ¬v = "16"
        //         185/ ¬p = ""
        //         186/ p = ""
        //         187/ rem = "/s1 God Reveals Nebuchadnezzar's Dream"
        //         188/ v = "17"
        //         189/ v~ = "Then Daniel went¦357017 back t…, Misha'el, and Azaryah¦357020"
        //         190/ ¬v = "17"
        //         191/ v = "18"
        //         192/ v~ = "≈so they¦357038 ≈might beg for…he Babylonian wise men¦357044."
        //         193/ ¬v = "18"
        //         194/ v = "19"
        //         195/ v~ = "Then the mystery¦357053 was re…d¦357058 of the heavens¦357059"
        //         196/ ¬v = "19"
        //         197/ v = "20"
        //         198/ v~ = "saying¦357063, “Let God's name…nd power¦357078 belong to him."
        //         199/ ¬v = "20"
        //         200/ v = "21"
        //         201/ v~ = "He moves the times¦357086 and … those who have understanding."
        //         202/ ¬v = "21"
        //         203/ v = "22"
        //         204/ v~ = "He reveals¦357100 the deep and…e light¦357106 lives with him."
        //         205/ ¬v = "22"
        //         206/ v = "23"
        //         207/ v~ = "Oh God¦357113 of my ancestors¦…ng¦357132 is wanting to know.”"
        //         208/ ¬v = "23"
        //         209/ ¬p = ""
        //         210/ ¬s1 = ""
        //         211/ v= = "24"
        //         212/ s1 = "Daniel explains the king's dream"
        //         213/ rem = "/s1 Daniel Tells the King the …t; Daniel Interprets the Dream"
        //         214/ p = ""
        //         215/ v = "24"
        //         216/ v~ = "So Daniel went to Aryok¦357143…nd its interpretation¦357164.”"
        //         217/ ¬v = "24"
        //         218/ ¬p = ""
        //         219/ p = ""
        //         220/ v = "25"
        //         221/ v~ = "Aryok¦357170 quickly took Dani…etation¦357191 of your dream.”"
        //         222/ ¬v = "25"
        //         223/ ¬p = ""
        //         224/ p = ""
        //         225/ v = "26"
        //         226/ v~ = "“Are you able to tell me the d… (also called Belteshatstsar)."
        //         227/ ¬v = "26"
        //         228/ ¬p = ""
        //         229/ p = ""
        //         230/ v = "27"
        //         231/ v~ = "“No wise men, enchanters, magi…has demanded,” replied Daniel."
        //         232/ ¬v = "27"
        //         233/ v = "28"
        //         234/ v~ = "“However, there¦357232 is a go…e you were in your bed¦357250:"
        //         235/ ¬v = "28"
        //         236/ v = "29"
        //         237/ v~ = "Oh¦357258 king¦357258, ≈as you…d you what is going to happen."
        //         238/ ¬v = "29"
        //         239/ v = "30"
        //         240/ v~ = "As for me, this mystery¦357289…aw in¦357279 your mind¦357302."
        //         241/ ¬v = "30"
        //         242/ ¬p = ""
        //         243/ p = ""
        //         244/ v = "31"
        //         245/ v~ = "“What you were looking at, ≈yo…you—a terrifying¦357323 sight."
        //         246/ ¬v = "31"
        //         247/ v = "32"
        //         248/ v~ = "The statue's¦357326 head¦35732…ghs¦357337 were bronze¦357339,"
        //         249/ ¬v = "32"
        //         250/ v = "33"
        //         251/ v~ = "its legs were made of iron, an… combination of iron and clay."
        //         252/ ¬v = "33"
        //         253/ v = "34"
        //         254/ v~ = "You continued looking until¦35…and it smashed them to pieces."
        //         255/ ¬v = "34"
        //         256/ v = "35"
        //         257/ v~ = "Then the iron, the clay, the b…filled¦357409 the whole world."
        //         258/ ¬v = "35"
        //         259/ ¬p = ""
        //         260/ p = ""
        //         261/ v = "36"
        //         262/ v~ = "“That¦357420 was the dream¦357…ing¦357420 its¦357416 meaning:"
        //         263/ ¬v = "36"
        //         264/ v = "37"
        //         265/ v~ = "You¦357425, ≈your majesty, are…¦357429 of the heavens¦357430."
        //         266/ ¬v = "37"
        //         267/ v = "38"
        //         268/ v~ = "Wherever people live, he's ≈pl…tue's gold¦357463 head¦357461."
        //         269/ ¬v = "38"
        //         270/ v = "39"
        //         271/ v~ = "≈But¦357465 another less promi…7484 after¦357465 that¦357480."
        //         272/ ¬v = "39"
        //         273/ v = "40"
        //         274/ v~ = "Then¦357486 there'll be a four…se others into ≈broken pieces."
        //         275/ ¬v = "40"
        //         276/ v = "41"
        //         277/ v~ = "And as you saw the feet¦357513…542 with¦357535 the soft clay."
        //         278/ ¬v = "41"
        //         279/ v = "42"
        //         280/ v~ = "As the feet¦357547 were partly…trong¦357559 and partly ≈weak."
        //         281/ ¬v = "42"
        //         282/ v = "43"
        //         283/ v~ = "As¦357583 you¦357566 saw¦35756… doesn't ≈integrate with clay."
        //         284/ ¬v = "43"
        //         285/ v = "44"
        //         286/ v~ = "In the days¦357593 of those ki… it will stand forever¦357618."
        //         287/ ¬v = "44"
        //         288/ v = "45"
        //         289/ v~ = "Just as you saw¦357625 that a …357652 is trustworthy¦357651.”"
        //         290/ ¬v = "45"
        //         291/ ¬p = ""
        //         292/ ¬s1 = ""
        //         293/ v= = "46"
        //         294/ s1 = "Daniel is rewarded by the king"
        //         295/ rem = "/s1 Daniel and His Friends Pro… Nebuchadnezzar Rewards Daniel"
        //         296/ p = ""
        //         297/ v = "46"
        //         298/ v~ = "Then King¦357656 Nevukadnetsts…e¦357665 be offered up to him."
        //         299/ ¬v = "46"
        //         … (1540 total entries)

        let mut section_index = InternalBibleBookSectionIndex::new("OET-RV", "DAN");
        section_index.build(processed_line_entries.clone()).unwrap();

        // for (ee,(cv,entry)) in section_index.index_data.iter().enumerate() { println!("{}/ {} {}", ee, cv, entry); }
        // It should give the following 26 entries:
        //     0/ -1:0 SectionEntry(ends -1:12 lines 0-12 Headers "DAN" [])
        //     1/ -1:14 SectionEntry(ends -1:30 lines 14-30 is1 "Introduction" [])
        //     2/ 1:0 SectionEntry(ends 0:0 lines 32-0 ms1/c "The account about Daniel and his friends" [chapters, c])
        //     3/ 1:1 SectionEntry(ends 1:21 lines 36-117 s1/c "Daniel and his friends in Babylon" [chapters, c])
        //     4/ 2:1 SectionEntry(ends 2:23 lines 118-210 s1/c "Nevukadnetstsar's dream" [chapters, c])
        //     5/ 2:24 SectionEntry(ends 2:45 lines 211-292 s1 "Daniel explains the king's dream" [chapters, c])
        //     6/ 2:46 SectionEntry(ends 2:49 lines 293-311 s1 "Daniel is rewarded by the king" [chapters, c])
        //     7/ 3:1 SectionEntry(ends 3:7 lines 312-340 s1/c "The command to worship the statue" [chapters, c])
        //     8/ 3:8 SectionEntry(ends 3:18 lines 341-383 s1 "Daniel's three friends get tattled on" [chapters, c])
        //     9/ 3:19 SectionEntry(ends 3:30 lines 384-440 s1 "Shadrak, Meyshak, and Avednego thrown into the fire" [chapters, c])
        //     10/ 4:1 SectionEntry(ends 4:18 lines 441-526 s1/c "Nevukadnetstsar's second dream" [chapters, c])
        //     11/ 4:19 SectionEntry(ends 4:33 lines 527-589 s1 "The saving/explaining of Daniel of dream of King" [chapters, c])
        //     12/ 4:34 SectionEntry(ends 4:37 lines 590-610 s1 "Nevukadnetstsar praises God" [chapters, c])
        //     13/ 5:1 SectionEntry(ends 5:31 lines 611-741 s1/c "The writing on the wall" [chapters, c])
        //     14/ 6:1 SectionEntry(ends 6:28 lines 742-863 s1/c "Daniel gets fed to the lions" [chapters, c])
        //     15/ 7:0 SectionEntry(ends 0:0 lines 864-0 ms1/c "Daniel's visions" [chapters, c])
        //     16/ 7:1 SectionEntry(ends 7:14 lines 867-937 s1/c "Daniel's vision of four creatures" [chapters, c])
        //     17/ 7:15 SectionEntry(ends 7:28 lines 938-997 s1 "The meaning of the visions" [chapters, c])
        //     18/ 8:1 SectionEntry(ends 8:14 lines 998-1055 s1/c "Daniel's sheep and goat vision" [chapters, c])
        //     19/ 8:15 SectionEntry(ends 8:27 lines 1056-1109 s1 "Gavri'el explains Daniel's vision" [chapters, c])
        //     20/ 9:1 SectionEntry(ends 9:19 lines 1110-1180 s1/c "Daniel prays for his people" [chapters, c])
        //     21/ 9:20 SectionEntry(ends 9:27 lines 1181-1213 s1 "Gavri'el explains God's revelation" [chapters, c])
        //     22/ 10:1 SectionEntry(ends 11:1 lines 1214-1309 s1/c "God's terrifying revelation to Daniel" [chapters, c])
        //     23/ 11:2 SectionEntry(ends 11:20 lines 1310-1383 s1 "The kings of Egypt and Syria" [chapters, c])
        //     24/ 11:21 SectionEntry(ends 11:45 lines 1384-1475 s1 "The evil Syrian king" [chapters, c])
        //     25/ 12:1 SectionEntry(ends 12:13 lines 1476-1538 s1/c "The ending of time" [chapters, c])

        assert_eq!(section_index.len(), 26);
        let sections: Vec<_> = section_index.index_data.iter().map(|(_, entry)| entry.reason_marker().to_string()).collect();
        assert_eq!(sections, vec!["Headers", "is1",
                                    "ms1/c", "s1/c", "s1/c", "s1", "s1", "s1/c", "s1", "s1", "s1/c", "s1", "s1", "s1/c", "s1/c",
                                    "ms1/c", "s1/c", "s1", "s1/c", "s1", "s1/c", "s1", "s1/c", "s1", "s1", "s1/c"]);

        // 0 -1:0 Headers='DAN'
        let (cv0, entry0) = section_index.index_data.get_index(0).unwrap();
        assert_eq!(cv0.to_string(), "-1:0");
        assert_eq!(entry0.end_cv().to_string(), "-1:12");
        assert_eq!(entry0.start_index(), 0);
        assert_eq!(entry0.end_index(), 12); // ends at '¬headers'
        assert_eq!(entry0.reason_marker(), "Headers");
        assert_eq!(entry0.section_name(), "DAN");

        // 1 -1:13 is1='Introduction'
        let (cv1, entry1) = section_index.index_data.get_index(1).unwrap();
        assert_eq!(cv1.to_string(), "-1:14");
        assert_eq!(entry1.end_cv().to_string(), "-1:30");
        assert_eq!(entry1.start_index(), 14);
        assert_eq!(entry1.end_index(), 30);
        assert_eq!(entry1.reason_marker(), "is1");
        assert_eq!(entry1.section_name(), "Introduction");

        // 2 1:10 ms1='The account about Daniel and his friends'
        let (cv2, entry2) = section_index.index_data.get_index(2).unwrap();
        assert_eq!(cv2.to_string(), "1:0");
        assert_eq!(entry2.end_cv().to_string(), "0:0"); // dummy
        assert_eq!(entry2.start_index(), 32); // c
        assert_eq!(entry2.end_index(), 35);
        assert_eq!(entry2.reason_marker(), "ms1/c");
        assert_eq!(entry2.section_name(), "The account about Daniel and his friends");

        // 3 1:1 s1='Daniel and his friends in Babylon'
        let (cv3, entry3) = section_index.index_data.get_index(3).unwrap();
        assert_eq!(cv3.to_string(), "1:1");
        assert_eq!(entry3.end_cv().to_string(), "1:21");
        assert_eq!(entry3.start_index(), 36); // s1
        assert_eq!(entry3.end_index(), 117);
        assert_eq!(entry3.reason_marker(), "s1/c");
        assert_eq!(entry3.section_name(), "Daniel and his friends in Babylon");

        // 4 2:1 s1='Nevukadnetstsar's dream'
        let (cv4, entry4) = section_index.index_data.get_index(4).unwrap();
        assert_eq!(cv4.to_string(), "2:1");
        assert_eq!(entry4.end_cv().to_string(), "2:23");
        assert_eq!(entry4.start_index(), 118);
        assert_eq!(entry4.end_index(), 210);
        assert_eq!(entry4.reason_marker(), "s1/c");
        assert_eq!(entry4.section_name(), "Nevukadnetstsar's dream");

        // // 5 2:1 s1='A warning for the priests'
        // let (cv5, entry5) = section_index.index_data.get_index(5).unwrap();
        // assert_eq!(cv5.to_string(), "2:1");
        // assert_eq!(entry5.end_cv().to_string(), "2:9");
        // assert_eq!(entry5.start_index(), 98);
        // assert_eq!(entry5.end_index(), 136);
        // assert_eq!(entry5.reason_marker(), "s1/c");
        // assert_eq!(entry5.section_name(), "A warning for the priests");

        // // 6 2:10 s1='The people have been unfaithful'
        // let (cv6, entry6) = section_index.index_data.get_index(6).unwrap();
        // assert_eq!(cv6.to_string(), "2:10");
        // assert_eq!(entry6.end_cv().to_string(), "2:16");
        // assert_eq!(entry6.start_index(), 137);
        // assert_eq!(entry6.end_index(), 167);
        // assert_eq!(entry6.reason_marker(), "s1");
        // assert_eq!(entry6.section_name(), "The people have been unfaithful");

        // // 7 2:19 s1='Judgement day is coming'
        // let (cv7, entry7) = section_index.index_data.get_index(7).unwrap();
        // assert_eq!(cv7.to_string(), "2:17");
        // assert_eq!(entry7.end_cv().to_string(), "3:5");
        // assert_eq!(entry7.start_index(), 168);
        // assert_eq!(entry7.end_index(), 199);
        // assert_eq!(entry7.reason_marker(), "s1");
        // assert_eq!(entry7.section_name(), "Judgement day is coming");

        // // 8 3:6 s1='Giving a tenth'
        // let (cv8, entry8) = section_index.index_data.get_index(8).unwrap();
        // assert_eq!(cv8.to_string(), "3:6");
        // assert_eq!(entry8.end_cv().to_string(), "3:12");
        // assert_eq!(entry8.start_index(), 200);
        // assert_eq!(entry8.end_index(), 227);
        // assert_eq!(entry8.reason_marker(), "s1");
        // assert_eq!(entry8.section_name(), "Giving a tenth");

        // // 9 3:13 s1='God promises mercy for some'
        // let (cv9, entry9) = section_index.index_data.get_index(9).unwrap();
        // assert_eq!(cv9.to_string(), "3:13");
        // assert_eq!(entry9.end_cv().to_string(), "3:18");
        // assert_eq!(entry9.start_index(), 228);
        // assert_eq!(entry9.end_index(), 255);
        // assert_eq!(entry9.reason_marker(), "s1");
        // assert_eq!(entry9.section_name(), "God promises mercy for some");

        // // 10 4:1 s1='Be ready for future judgement'
        // let (cv10, entry10) = section_index.index_data.get_index(10).unwrap();
        // assert_eq!(cv10.to_string(), "4:1");
        // assert_eq!(entry10.end_cv().to_string(), "4:6");
        // assert_eq!(entry10.start_index(), 256);
        // assert_eq!(entry10.end_index(), 286);
        // assert_eq!(entry10.reason_marker(), "s1/c");
        // assert_eq!(entry10.section_name(), "Be ready for future judgement");
    }

    #[test]
    fn test_oet_rv_2samuel_section_index_build() {
        // Note that OET-RV 2 Samuel has 3 section headings inside verse boundaries
        set_strict_checking_flag( true );
        let content = include_str!("../../../../Tests/DataFilesForTests/OET-RV/OET-RV_SA2.ESFM");
        let mut raw_lines = Vec::new();
        for line in content.lines() {
            let (marker, text) = match line.split_once(' ') {
                Some((m, t)) => (m, t),
                None => (line, ""),
            };
            let marker = marker.strip_prefix('\\').unwrap_or(marker);
            raw_lines.push((marker.to_string(), text.to_string()));
        }

        let options = crate::processing::ProcessLinesOptions::default();
        let processed_line_entries = crate::processing::process_lines(raw_lines, "SA2", "OET-RV", &options);

        // println!("OET-RV SA2 {} processed_line_entries = {}", processed_line_entries.len(), processed_line_entries);
        //         OET-RV SA2 added c12 line_entry 'v=' = '15b'
        //         OET-RV SA2 added c12 line_entry 'v=' = '15b'
        //         OET-RV SA2 added c12 line_entry 'v=' = '24b'
        //         OET-RV SA2 added c12 line_entry 'v=' = '24b'
        //         OET-RV SA2 added c19 line_entry 'v=' = '8b'
        //         OET-RV SA2 added c19 line_entry 'v=' = '8b'
        //         OET-RV SA2 added c19 line_entry 'v=' = '18b'
        //         OET-RV SA2 added c19 line_entry 'v=' = '18b'
        //     0/ id = "2SA - Open English Translation…ders' Version (OET-RV) v0.1.16"
        //     1/ usfm = "3.0"
        //     2/ ide = "UTF-8"
        //     3/ rem = "ESFM v0.6 SA2"
        //     4/ rem = "WORDTABLE OET-LV_OT_word_table.tsv"
        //     5/ headers = ""
        //     6/ h = "2 Shemuel"
        //     7/ toc1 = "2 Shemuel"
        //     8/ toc2 = "2 Shemuel"
        //     9/ toc3 = "2 She."
        //     10/ mt1 = "2 Shemuel"
        //     11/ ¬headers = ""
        //     12/ intro = ""
        //     13/ is1 = "Introduction"
        //     14/ ip = "Second Shemuel (commonly, but …ong to fit on a single scroll."
        //     15/ ip = "This the story of David's reig… punishment that God gave him."
        //     16/ ip = "The times of peace and prosper…d who would love God like him."
        //     17/ iot = "Main components of this account"
        //     18/ io1 = "The kingdom of David in Yehudah 1:1–4:12"
        //     19/ io1 = "The kingdom of David over all Yisrael 5:1–24:25"
        //     20/ io2 = "a. The early years 5:1–10:19"
        //     21/ io2 = "b. David takes Uriyah's wife 11:1–12:25"
        //     22/ io2 = "c. The battles and the difficulties 12:26–20:26"
        //     23/ io2 = "d. The later years 21:1–24:25"
        //     24/ ¬iot = ""
        //     25/ rem = "This is still a very early loo…dvance before using in public."
        //     26/ ie = ""
        //     27/ ¬intro = ""
        //     28/ chapters = ""
        //     29/ c = "1"
        //     30/ v= = "1"
        //     31/ s1 = "David learns about Sha'ul's death"
        //     32/ rem = "/s1 David Learns of Saul's Dea…g; David Hears of Saul's Death"
        //     33/ s4 = "Full kingdom"
        //     34/ p = ""
        //     35/ c# = "1"
        //     36/ v = "1"
        //     37/ v~ = "≈After David¦141765 returned¦1…was dead by this time¦141774.)"
        //     38/ ¬v = "1"
        //     39/ v = "2"
        //     40/ v~ = "Then¦141777 on the third¦14178…is knees and bowed¦141802 low."
        //     41/ ¬v = "2"
        //     42/ v = "3"
        //     43/ v~ = "“Where ≈have you¦141809 come from?” David¦141806 ≈asked him."
        //     44/ ¬p = ""
        //     45/ p = ""
        //     46/ v~ = "“I ≈was in Yisrael's¦141813 ca…o escape¦141814.” he ≈replied."
        //     47/ ¬v = "3"
        //     48/ v = "4"
        //     49/ v~ = "“≈Why? What happened?” David¦1…ded. “Tell me, please¦141825,”"
        //     50/ ¬p = ""
        //     51/ p = ""
        //     52/ v~ = "“&Our people¦141841 fled from …844 and his son Yonatan died.”"
        //     53/ ¬p = ""
        //     54/ ¬v = "4"
        //     55/ p = ""
        //     56/ v = "5"
        //     57/ v~ = "“How do¦141857 you¦141857 know…41853 who'd ≈brought the news."
        //     58/ ¬v = "5"
        //     59/ ¬p = ""
        //     60/ p = ""
        //     61/ v = "6"
        //     62/ v~ = "“I¦141871 happened¦141870 to b…83 overtook¦141884 him¦141884," + extras
        //     63/ ¬v = "6"
        //     64/ v = "7"
        //     65/ v~ = "and he turned¦141886 around an… and I ≈answered, ‘Here I am.’"
        //     66/ ¬v = "7"
        //     67/ v = "8"
        //     68/ v~ = "‘Who are you¦141898?’ he ≈aske…Amalekite¦141902,’ I told him."
        //     69/ ¬v = "8"
        //     70/ v = "9"
        //     71/ v~ = "Then¦141905 he said¦141905 to …live, the pain is unbearable.’"
        //     72/ ¬v = "9"
        //     73/ v = "10"
        //     74/ v~ = "≈So¦141923 I stood¦141923 over…ere to you, my master¦141948.”"
        //     75/ ¬v = "10"
        //     76/ ¬p = ""
        //     77/ p = ""
        //     78/ v = "11"
        //     79/ v~ = "Then¦141951 David¦141952 pulle…141959 with him ≈did the same,"
        //     80/ ¬v = "11"
        //     81/ v = "12"
        //     82/ v~ = "and they¦141985 mourned¦141963…raelis¦141983 had been killed."
        //     83/ ¬v = "12"
        //     84/ ¬p = ""
        //     85/ p = ""
        //     86/ v = "13"
        //     87/ v~ = "Then David¦141990 ≈asked the y…he news, “Where are you from?”"
        //     88/ ¬p = ""
        //     89/ p = ""
        //     90/ v~ = "“I'm a foreigner's son,” he ≈replied, “an Amalekite¦142004.”"
        //     91/ ¬v = "13"
        //     92/ v = "14"
        //     93/ v~ = "“How come you¦142012 weren't a…nds?” David¦142009 ≈asked him."
        //     94/ ¬v = "14"
        //     95/ v = "15"
        //     96/ v~ = "Then¦142021 David¦142022 calle…42030 him, and he died¦142031."
        //     97/ ¬v = "15"
        //     98/ v = "16"
        //     99/ v~ = "“Your blood's¦142036 on your o…s¦142051 anointed¦142050 one.”"
        //     100/ ¬v = "16"
        //     101/ ¬p = ""
        //     102/ v= = "17"
        //     103/ s1 = "David's song of mourning"
        //     104/ rem = "/s1 David's Lament for Saul an…d's Song for Saul and Jonathan"
        //     105/ s4 = "Full kingdom"
        //     106/ p = ""
        //     107/ v = "17"
        //     108/ v~ = "Then David¦142055 sang this fu…'ul¦142062 and his son Yonatan"
        //     109/ ¬v = "17"
        //     110/ v = "18"
        //     111/ v~ = "and said¦142068 that it should…75 down in the Book of Yashar:" + extras
        //     112/ ¬v = "18"
        //     113/ ¬p = ""
        //     114/ q1 = ""
        //     115/ v = "19"
        //     116/ v~ = "“Yisrael's¦142082 splendour was slain¦142086 ≈in the hills."
        //     117/ ¬q1 = ""
        //     118/ q1 = ""
        //     119/ v~ = "≈How the ≈powerful warriors have ≈died."
        //     120/ ¬q1 = ""
        //     121/ ¬v = "19"
        //     122/ q1 = ""
        //     123/ v = "20"
        //     124/ v~ = "Don't tell ‘them in Gat¦142094."
        //     125/ ¬q1 = ""
        //     126/ q1 = ""
        //     127/ v~ = "≈Don't let ‘them take the news…kelon's¦142099 streets¦142098,"
        //     128/ ¬q1 = ""
        //     129/ q1 = ""
        //     130/ v~ = "in case the Philistine ≈women¦142103 celebrate,"
        //     131/ ¬q1 = ""
        //     132/ q1 = ""
        //     133/ v~ = "and the daughters of the uncircumcised¦142109 are elated."
        //     134/ ¬q1 = ""
        //     135/ ¬v = "20"
        //     136/ b = ""
        //     137/ q1 = ""
        //     138/ v = "21"
        //     139/ v~ = "≈You mountains¦142111 in¦142112 Gilboa¦142112,"
        //     140/ ¬q1 = ""
        //     141/ q2 = ""
        //     142/ v~ = "may you have no dew or rain fall on¦142112 you,"
        //     143/ ¬q2 = ""
        //     144/ q2 = ""
        //     145/ v~ = "nor fields¦142120 producing grain for offerings."
        //     146/ ¬q2 = ""
        //     147/ q1 = ""
        //     148/ v~ = "Because it¦142124 was there¦14…as ≈splattered with his blood,"
        //     149/ ¬q1 = ""
        //     150/ q2 = ""
        //     151/ v~ = "and the leather won't¦142113 b…eserved with oil¦142131 again."
        //     152/ ¬q2 = ""
        //     153/ ¬v = "21"
        //     154/ q1 = ""
        //     155/ v = "22"
        //     156/ v~ = "From the blood¦142133 of those¦142134 slain¦142134—"
        //     157/ ¬q1 = ""
        //     158/ q2 = ""
        //     159/ v~ = "≈from the fat of the ≈warriors,"
        //     160/ ¬q2 = ""
        //     161/ q1 = ""
        //     162/ v~ = "Yonatan's bow didn't ≈retreat"
        //     163/ ¬q1 = ""
        //     164/ q2 = ""
        //     165/ v~ = "≈and¦142142 Sha'ul's sword¦142…2 didn't ≈fail on its strikes."
        //     166/ ¬q2 = ""
        //     167/ ¬v = "22"
        //     168/ b = ""
        //     169/ q1 = ""
        //     170/ v = "23"
        //     171/ v~ = "Sha'ul¦142148 and Yonatan were loved—"
        //     172/ ¬q1 = ""
        //     173/ q2 = ""
        //     174/ v~ = "≈they pleased¦142151 the people."
        //     175/ ¬q2 = ""
        //     176/ q2 = ""
        //     177/ v~ = "and even at¦142152 their death…they weren't separated¦142155."
        //     178/ ¬q2 = ""
        //     179/ q1 = ""
        //     180/ v~ = "They were swifter¦142157 than eagles¦142156."
        //     181/ ¬q1 = ""
        //     182/ q2 = ""
        //     183/ v~ = "≈they were stronger¦142159 than lions¦142158."
        //     184/ ¬q2 = ""
        //     185/ ¬v = "23"
        //     186/ b = ""
        //     187/ q1 = ""
        //     188/ v = "24"
        //     189/ v~ = "Weep for Sha'ul¦142165 you dau…ters¦142161 of Yisrael¦142162,"
        //     190/ ¬q1 = ""
        //     191/ q1 = ""
        //     192/ v~ = "the one who ≈dressed you in ni…clothes¦142167 with jewellery,"
        //     193/ ¬q1 = ""
        //     194/ q1 = ""
        //     195/ v~ = "≈and gave you all gold¦142174 ≈brooches to put on."
        //     196/ ¬q1 = ""
        //     197/ ¬v = "24"
        //     198/ b = ""
        //     199/ q1 = ""
        //     200/ v = "25"
        //     201/ v~ = "Those warriors have fallen¦142…e¦142181 of the battle¦142182."
        //     202/ ¬q1 = ""
        //     203/ q1 = ""
        //     204/ v~ = "≈Yonatan has been killed there on the hills."
        //     205/ ¬q1 = ""
        //     206/ ¬v = "25"
        //     207/ b = ""
        //     208/ q1 = ""
        //     209/ v = "26"
        //     210/ v~ = "I ≈grieve for you my dear friend Yonatan."
        //     211/ ¬q1 = ""
        //     212/ q1 = ""
        //     213/ v~ = "You were ≈so kind to me."
        //     214/ ¬q1 = ""
        //     215/ q1 = ""
        //     216/ v~ = "Your ≈friendship meant more to…¦142202 ≈who say they love me."
        //     217/ ¬q1 = ""
        //     218/ ¬v = "26"
        //     219/ b = ""
        //     220/ q1 = ""
        //     221/ v = "27"
        //     222/ v~ = "Yes, those ≈powerful warriors have fallen¦142205,"
        //     223/ ¬q1 = ""
        //     224/ q1 = ""
        //     225/ v~ = "≈and¦142207 those weapons¦1422… of war have ≈been destroyed.”"
        //     226/ ¬v = "27"
        //     227/ ¬q1 = ""
        //     228/ ¬c = "1"
        //     229/ c = "2"
        //     230/ v= = "1"
        //     231/ s1 = "The kingdom of David"
        //     232/ rem = "/s1 David Anointed King of Jud…David Anointed King Over Judah"
        //     233/ s4 = "Full kingdom"
        //     234/ p = ""
        //     235/ c# = "2"
        //     236/ v = "1"
        //     237/ v~ = "After ≈that was over, David¦14…hudah's¦142224 cities¦142223?”"
        //     238/ ¬p = ""
        //     239/ p = ""
        //     240/ v~ = "“Yes,, go,” Yahweh ≈answered."
        //     241/ ¬p = ""
        //     242/ p = ""
        //     243/ v~ = "“Where should I go?” David ≈asked again."
        //     244/ ¬p = ""
        //     245/ p = ""
        //     246/ v~ = "“To Hebron¦142234,” he said."
        //     247/ ¬p = ""
        //     248/ ¬v = "1"
        //     249/ p = ""
        //     250/ v = "2"
        //     251/ v~ = "≈So¦142236 David¦142238 took h…142247) and went there¦142237." + extras
        //     252/ ¬v = "2"
        //     253/ v = "3"
        //     254/ v~ = "He¦142254 took his men¦142249 … the surrounding towns¦142258."
        //     255/ ¬v = "3"
        //     256/ v = "4"
        //     257/ v~ = "Then¦142261 the Yehudah ≈leade…9 as king¦142270 over Yehudah."
        //     258/ ¬p = ""
        //     259/ p = ""
        //     260/ v~ = "They told him, “It was the men… buried¦142282 Sha'ul¦142285.”" + extras
        //     261/ ¬v = "4"
        //     262/ v = "5"
        //     263/ v~ = "≈So David¦142289 sent¦142288 m…2310 to bury him respectfully."
        //     264/ ¬v = "5"
        //     265/ v = "6"
        //     266/ v~ = "Now may Yahweh¦142317 ≈treat y…5 to you because you did that."
        //     267/ ¬v = "6"
        //     268/ v = "7"
        //     269/ v~ = "≈Meanwhile now that Sha'ul¦142…king¦142352 over ≈their tribe."
        //     270/ ¬v = "7"
        //     271/ ¬p = ""
        //     272/ v= = "8"
        //     273/ s1 = "Disputes between Sha'ul and David's families"
        //     274/ rem = "/s1 Ishbaal King of Israel; Is…n the Houses of David and Saul"
        //     275/ s4 = "Full kingdom"
        //     276/ p = ""
        //     277/ v = "8"
        //     278/ v~ = "However, Abner¦142356 (Ner's¦1…ysh-Boshet across to Mahanayim" + extras
        //     279/ ¬v = "8"
        //     280/ v = "9"
        //     281/ v~ = "and ≈declared him¦142376 to be…nd over all of Yisrael¦142394."
        //     282/ ¬v = "9"
        //     283/ v = "10"
        //     284/ v~ = "Iysh-Boshet ≈was forty¦142400 … he ≈ruled them for two years."
        //     285/ ¬p = ""
        //     286/ p = ""
        //     287/ v~ = "But¦142412 the tribe of Yehuda…2417 was loyal to David¦142420"
        //     288/ ¬v = "10"
        //     289/ v = "11"
        //     290/ v~ = "and *he ≈ruled them for seven¦…42434 and a half years¦142435."
        //     291/ rem = "/s1 The Battle of Gibeon; War between Israel and Judah"
        //     292/ ¬v = "11"
        //     293/ ¬p = ""
        //     294/ p = ""
        //     295/ v = "12"
        //     296/ v~ = "One day Abner¦142441 left Maha… went¦142440 to Gibeon¦142453,"
        //     297/ ¬v = "12"
        //     298/ v = "13"
        //     299/ v~ = "≈but¦142455 Yoav¦142455 (Tseru…roup on each side of the pool."
        //     … (3609 total entries)

        let mut section_index = InternalBibleBookSectionIndex::new("OET-RV", "SA2");
        section_index.build(processed_line_entries.clone()).unwrap();
        
        // for (ee,(cv,entry)) in section_index.index_data.iter().enumerate() { println!("{}/ {} {}", ee, cv, entry); }
        // It should give the following 52 entries:
        //         OET-RV SA2 added c12 line_entry 'v=' = '15b'
        //         OET-RV SA2 added c12 line_entry 'v=' = '24b'
        //         OET-RV SA2 added c19 line_entry 'v=' = '8b'
        //         OET-RV SA2 added c19 line_entry 'v=' = '18b'
        //     0/ ('-1', '0') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=-1:11 ix=0–11 (cnt=12) Headers='SA2'
        //     1/ ('-1', '13') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=-1:27 ix=13–27 (cnt=15) is1='Introduction'
        //     2/ ('1', '1') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=1:16 ix=29–101 (cnt=73) s1/c='David learns about Sha'ul's death' ctxt=["chapters", "c"]
        //     3/ ('1', '17') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=1:27 ix=102–228 (cnt=127) s1='David's song of mourning' ctxt=["chapters", "c"]
        //     4/ ('2', '1') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=2:7 ix=229–271 (cnt=43) s1/c='The kingdom of David' ctxt=["chapters", "c"]
        //     5/ ('2', '8') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=3:1 ix=272–388 (cnt=117) s1='Disputes between Sha'ul and David's families' ctxt=["chapters", "c"]
        //     6/ ('3', '2') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=3:5 ix=389–406 (cnt=18) s1='David's sons' ctxt=["chapters", "c"]
        //     7/ ('3', '6') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=3:21 ix=407–468 (cnt=62) s1='Abner switches over to David' ctxt=["chapters", "c"]
        //     8/ ('3', '22') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=3:30 ix=469–503 (cnt=35) s1='Yoav murders Abner' ctxt=["chapters", "c"]
        //     9/ ('3', '31') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=3:39 ix=504–550 (cnt=47) s1='Abnir's burial' ctxt=["chapters", "c"]
        //     10/ ('4', '1') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=4:12 ix=551–598 (cnt=48) s1/c='The murder of Iysh-Boshet' ctxt=["chapters", "c"]
        //     11/ ('5', '1') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=5:5 ix=599–622 (cnt=24) s1/c='David becomes king of all Yisrael' ctxt=["chapters", "c"]
        //     12/ ('5', '6') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=5:16 ix=623–672 (cnt=50) s1='David captures Yerushalem' ctxt=["chapters", "c"]
        //     13/ ('5', '17') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=5:25 ix=673–714 (cnt=42) s1='Defeated by David the Philistines' ctxt=["chapters", "c"]
        //     14/ ('6', '1') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=6:23 ix=715–806 (cnt=92) s1/c='The Box with the agreement is brought to Yerushalem' ctxt=["chapters", "c"]
        //     15/ ('7', '1') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=7:16 ix=807–867 (cnt=61) s1/c='Yahweh's promise to David' ctxt=["chapters", "c"]
        //     16/ ('7', '17') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=7:29 ix=868–918 (cnt=51) s1='David's prayer' ctxt=["chapters", "c"]
        //     17/ ('8', '1') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=8:18 ix=919–995 (cnt=77) s1/c='David's victories' ctxt=["chapters", "c"]
        //     18/ ('9', '1') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=9:13 ix=996–1074 (cnt=79) s1/c='David assists Mefiboshet' ctxt=["chapters", "c"]
        //     19/ ('10', '1') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=10:19 ix=1075–1154 (cnt=80) s1/c='Yisrael defeats the Ammonites and the Arameans' ctxt=["chapters", "c"]
        //     20/ ('11', '1') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=11:27 ix=1155–1264 (cnt=110) s1/c='David takes Uriyah's wife' ctxt=["chapters", "c"]
        //     21/ ('12', '1') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=12:15 ix=1265–1326 (cnt=62) s1/c='Natan brings rebuke to David' ctxt=["chapters", "c"]
        //     22/ ('12', '15b') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=12:24 ix=1327–1371 (cnt=45) s1='David's son dies' ctxt=["chapters", "c"]
        //     23/ ('12', '24b') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=12:25 ix=1372–1382 (cnt=11) s1='The birth of Shelomoh' ctxt=["chapters", "c"]
        //     24/ ('12', '26') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=12:31 ix=1383–1408 (cnt=26) s1='David captures Rabbah' ctxt=["chapters", "c"]
        //     25/ ('13', '1') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=13:22 ix=1409–1503 (cnt=95) s1/c='Amnon rapes Tamar' ctxt=["chapters", "c"]
        //     26/ ('13', '23') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=13:39 ix=1504–1577 (cnt=74) s1='Abshalom kills Amnon' ctxt=["chapters", "c"]
        //     27/ ('14', '1') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=14:24 ix=1578–1696 (cnt=119) s1/c='Abshalom returns to Yerushalem' ctxt=["chapters", "c"]
        //     28/ ('14', '25') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=14:33 ix=1697–1738 (cnt=42) s1='Abshalom and David reconcile' ctxt=["chapters", "c"]
        //     29/ ('15', '1') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=15:12 ix=1739–1786 (cnt=48) s1/c='Abshalom plans his rebellion' ctxt=["chapters", "c"]
        //     30/ ('15', '13') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=15:37 ix=1787–1887 (cnt=101) s1='The fleeing of David' ctxt=["chapters", "c"]
        //     31/ ('16', '1') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=16:4 ix=1888–1920 (cnt=33) s1/c='Dishonest Tsiva helps David' ctxt=["chapters", "c"]
        //     32/ ('16', '5') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=16:14 ix=1921–1960 (cnt=40) s1='Shimei curses David' ctxt=["chapters", "c"]
        //     33/ ('16', '15') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=16:23 ix=1961–2004 (cnt=44) s1='The conflicting advice of Hushay and Ahitofel' ctxt=["chapters", "c"]
        //     34/ ('17', '1') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=17:14 ix=2005–2061 (cnt=57) s1/c='Hushay argues against Ahitofel's advice' ctxt=["chapters", "c"]
        //     35/ ('17', '15') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=17:29 ix=2062–2129 (cnt=68) s1='The warning to David to flee' ctxt=["chapters", "c"]
        //     36/ ('18', '1') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=18:18 ix=2130–2209 (cnt=80) s1/c='Abshalom's defeat and death' ctxt=["chapters", "c"]
        //     37/ ('18', '19') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=18:33 ix=2210–2305 (cnt=96) s1='David learns about Abshalom's death' ctxt=["chapters", "c"]
        //     38/ ('19', '1') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=19:8 ix=2306–2338 (cnt=33) s1/c='Yoav scolds David' ctxt=["chapters", "c"]
        //     39/ ('19', '8b') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=19:18 ix=2339–2382 (cnt=44) s1='David returns to Yerushalem' ctxt=["chapters", "c"]
        //     40/ ('19', '18b') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=19:23 ix=2383–2409 (cnt=27) s1='David's mercy to Shimei' ctxt=["chapters", "c"]
        //     41/ ('19', '24') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=19:30 ix=2410–2442 (cnt=33) s1='David's mercy to Mefiboshet' ctxt=["chapters", "c"]
        //     42/ ('19', '31') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=19:39 ix=2443–2479 (cnt=37) s1='David's kindness to Barzillai' ctxt=["chapters", "c"]
        //     43/ ('19', '40') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=19:43 ix=2480–2506 (cnt=27) s1='Yehudah and Yisrael disagree' ctxt=["chapters", "c"]
        //     44/ ('20', '1') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=20:22 ix=2507–2616 (cnt=110) s1/c='Sheva rebels against David' ctxt=["chapters", "c"]
        //     45/ ('20', '23') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=20:26 ix=2617–2635 (cnt=19) s1='David's officials' ctxt=["chapters", "c"]
        //     46/ ('21', '1') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=21:14 ix=2636–2701 (cnt=66) s1/c='The Gibeonites' claim on Sha'ul's descendants' ctxt=["chapters", "c"]
        //     47/ ('21', '15') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=21:22 ix=2702–2739 (cnt=38) s1='Battles against Philistine giants' ctxt=["chapters", "c"]
        //     48/ ('22', '1') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=22:51 ix=2740–3199 (cnt=460) s1/c='David's song of praise' ctxt=["chapters", "c"]
        //     49/ ('23', '1') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=23:7 ix=3200–3292 (cnt=93) s1/c='David's ending speech' ctxt=["chapters", "c"]
        //     50/ ('23', '8') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=23:39 ix=3293–3494 (cnt=202) s1='David's top warriors' ctxt=["chapters", "c"]
        //     51/ ('24', '1') InternalBibleBookSectionIndexEntry object: (inclusive) endCV=24:25 ix=3495–3607 (cnt=113) s1/c='David takes a census' ctxt=["chapters", "c"]

        assert_eq!(section_index.len(), 52);
        let sections: Vec<_> = section_index.index_data.iter().map(|(_, entry)| entry.reason_marker().to_string()).collect();
        assert_eq!(sections, vec!["Headers", "is1", "s1/c", "s1", "s1/c", "s1", "s1", "s1", "s1", "s1", "s1/c", "s1/c",
                                    "s1", "s1", "s1/c", "s1/c", "s1", "s1/c", "s1/c", "s1/c", "s1/c", "s1/c", "s1", "s1",
                                    "s1", "s1/c", "s1", "s1/c", "s1", "s1/c", "s1", "s1/c", "s1", "s1", "s1/c", "s1",
                                    "s1/c", "s1", "s1/c", "s1", "s1", "s1", "s1", "s1", "s1/c", "s1", "s1/c", "s1",
                                    "s1/c", "s1/c", "s1", "s1/c"]);

        // 0 -1:0 Headers='SA2'
        let (cv0, entry0) = section_index.index_data.get_index(0).unwrap();
        assert_eq!(cv0.to_string(), "-1:0");
        assert_eq!(entry0.end_cv().to_string(), "-1:11");
        assert_eq!(entry0.start_index(), 0);
        assert_eq!(entry0.end_index(), 11); // ends at '¬headers'
        assert_eq!(entry0.reason_marker(), "Headers");
        assert_eq!(entry0.section_name(), "SA2");

        // 1 -1:13 is1='Introduction'
        let (cv1, entry1) = section_index.index_data.get_index(1).unwrap();
        assert_eq!(cv1.to_string(), "-1:13");
        assert_eq!(entry1.end_cv().to_string(), "-1:28");
        assert_eq!(entry1.start_index(), 13);
        assert_eq!(entry1.end_index(), 28);
        assert_eq!(entry1.reason_marker(), "is1");
        assert_eq!(entry1.section_name(), "Introduction");

        // 2 1:1 s1='David learns about Sha'ul's death'
        let (cv2, entry2) = section_index.index_data.get_index(2).unwrap();
        assert_eq!(cv2.to_string(), "1:1");
        assert_eq!(entry2.end_cv().to_string(), "1:16");
        assert_eq!(entry2.start_index(), 30); // c
        assert_eq!(entry2.end_index(), 103); // ¬p
        assert_eq!(entry2.reason_marker(), "s1/c");
        assert_eq!(entry2.section_name(), "David learns about Sha'ul's death");

        // 3 1:2 s1='David's song of mourning'
        let (cv3, entry3) = section_index.index_data.get_index(3).unwrap();
        assert_eq!(cv3.to_string(), "1:17");
        assert_eq!(entry3.end_cv().to_string(), "1:27");
        assert_eq!(entry3.start_index(), 104); // v=
        assert_eq!(entry3.end_index(), 231);
        assert_eq!(entry3.reason_marker(), "s1");
        assert_eq!(entry3.section_name(), "David's song of mourning");

        // 4 21:1 s1='Natan brings rebuke to David'
        let (cv21, entry21) = section_index.index_data.get_index(21).unwrap();
        assert_eq!(cv21.to_string(), "12:1");
        assert_eq!(entry21.end_cv().to_string(), "12:15a");
        assert_eq!(entry21.start_index(), 1285);
        assert_eq!(entry21.end_index(), 1347);
        assert_eq!(entry21.reason_marker(), "s1/c");
        assert_eq!(entry21.section_name(), "Natan brings rebuke to David");

        // 5 12:15b s1='David's son dies'
        let (cv22, entry22) = section_index.index_data.get_index(22).unwrap();
        assert_eq!(cv22.to_string(), "12:15b");
        assert_eq!(entry22.end_cv().to_string(), "12:24a");
        assert_eq!(entry22.start_index(), 1348);
        assert_eq!(entry22.end_index(), 1393);
        assert_eq!(entry22.reason_marker(), "s1");
        assert_eq!(entry22.section_name(), "David's son dies");

        // // 6 2:10 s1='The people have been unfaithful'
        // let (cv6, entry6) = section_index.index_data.get_index(6).unwrap();
        // assert_eq!(cv6.to_string(), "2:10");
        // assert_eq!(entry6.end_cv().to_string(), "2:16");
        // assert_eq!(entry6.start_index(), 133);
        // assert_eq!(entry6.end_index(), 162);
        // assert_eq!(entry6.reason_marker(), "s1");
        // assert_eq!(entry6.section_name(), "The people have been unfaithful");

        // // 7 2:19 s1='Judgement day is coming'
        // let (cv7, entry7) = section_index.index_data.get_index(7).unwrap();
        // assert_eq!(cv7.to_string(), "2:17");
        // assert_eq!(entry7.end_cv().to_string(), "3:5");
        // assert_eq!(entry7.start_index(), 163);
        // assert_eq!(entry7.end_index(), 193);
        // assert_eq!(entry7.reason_marker(), "s1");
        // assert_eq!(entry7.section_name(), "Judgement day is coming");

        // // 8 3:6 s1='Giving a tenth'
        // let (cv8, entry8) = section_index.index_data.get_index(8).unwrap();
        // assert_eq!(cv8.to_string(), "3:6");
        // assert_eq!(entry8.end_cv().to_string(), "3:12");
        // assert_eq!(entry8.start_index(), 194);
        // assert_eq!(entry8.end_index(), 220);
        // assert_eq!(entry8.reason_marker(), "s1");
        // assert_eq!(entry8.section_name(), "Giving a tenth");

        // // 9 3:13 s1='God promises mercy for some'
        // let (cv9, entry9) = section_index.index_data.get_index(9).unwrap();
        // assert_eq!(cv9.to_string(), "3:13");
        // assert_eq!(entry9.end_cv().to_string(), "3:18");
        // assert_eq!(entry9.start_index(), 221);
        // assert_eq!(entry9.end_index(), 247);
        // assert_eq!(entry9.reason_marker(), "s1");
        // assert_eq!(entry9.section_name(), "God promises mercy for some");
    }

    #[test]
    fn test_oet_rv_psalms_section_index_build() {
        // Note that OET-RV Psalms has five main sections (ms1 and mr) plus d fields
        set_strict_checking_flag( true );
        let content = include_str!("../../../../Tests/DataFilesForTests/OET-RV/OET-RV_PSA.ESFM");
        let mut raw_lines = Vec::new();
        for line in content.lines() {
            let (marker, text) = match line.split_once(' ') {
                Some((m, t)) => (m, t),
                None => (line, ""),
            };
            let marker = marker.strip_prefix('\\').unwrap_or(marker);
            raw_lines.push((marker.to_string(), text.to_string()));
        }

        let options = crate::processing::ProcessLinesOptions::default();
        let processed_line_entries = crate::processing::process_lines(raw_lines, "PSA", "OET-RV", &options);

        // println!("OET-RV PSA {} processed_line_entries = {}", processed_line_entries.len(), processed_line_entries);
        //     OET-RV PSA 22,583 processed_line_entries = InternalBibleEntryList:
        //         0/ id = "PSA - Open English Translation…aders' Version (OET-RV) v0.3.2"
        //         1/ usfm = "3.0"
        //         2/ ide = "UTF-8"
        //         3/ rem = "ESFM v0.6 PSA"
        //         4/ rem = "WORDTABLE OET-LV_OT_word_table.tsv"
        //         5/ headers = ""
        //         6/ h = "Songs"
        //         7/ toc1 = "Songs"
        //         8/ toc2 = "Songs"
        //         9/ toc3 = "Songs"
        //         10/ mt1 = "Songs"
        //         11/ ¬headers = ""
        //         12/ intro = ""
        //         13/ is1 = "Introduction"
        //         14/ ip = "This collection of Songs inclu…, read, or chanted with music."
        //         15/ ip = "There are many classes of the …n behalf of the entire nation."
        //         16/ ip = "Seven of these songs/poems are…ongest Song 119, and Song 145."
        //         17/ ip = "Yeshua (Jesus) and other contr…h worship since the beginning."
        //         18/ ip = "The one hundred and fifty song…ded into five sub-collections."
        //         19/ iot = "Main components of this collection"
        //         20/ io1 = "Songs 1–41"
        //         21/ io1 = "Songs 42–72"
        //         22/ io1 = "Songs 73–89"
        //         23/ io1 = "Songs 90–106"
        //         24/ io1 = "Songs 107–150"
        //         25/ ¬iot = ""
        //         26/ im = "There are a hundred and fifty …piness and trusting, and hope."
        //         27/ rem = "This is still a very early loo…dvance before using in public."
        //         28/ ¬is1 = "28"
        //         29/ ie = ""
        //         30/ cl¤ = "Song"
        //         31/ ¬intro = ""
        //         32/ chapters = ""
        //         33/ c = "1"
        //         34/ v= = "1"
        //         35/ ms1 = "First collection"
        //         36/ mr = "(Songs 1–41)"
        //         37/ s1 = "Wicked and godly roads"
        //         38/ rem = "/s1 True Happiness; The Two Ways"
        //         39/ p = ""
        //         40/ c# = "1"
        //         41/ v = "1"
        //         42/ v~ = "A person will reap the benefits"
        //         43/ ¬p = ""
        //         44/ q2 = ""
        //         45/ v~ = "if they don't take advice¦243189 from wicked¦243190 people,"
        //         46/ ¬q2 = ""
        //         47/ q2 = ""
        //         48/ v~ = "and don't stand¦243194 ≈around where sinners¦243192 ≈go,"
        //         49/ ¬q2 = ""
        //         50/ q2 = ""
        //         51/ v~ = "and don't sit and join all the scoffers."
        //         52/ ¬q2 = ""
        //         53/ ¬v = "1"
        //         54/ q1 = ""
        //         55/ v = "2"
        //         56/ v~ = "Instead, they enjoy Yahweh's¦243203 instructions"
        //         57/ ¬q1 = ""
        //         58/ q2 = ""
        //         59/ v~ = "and think about them day¦243207 and night¦243208."
        //         60/ ¬q2 = ""
        //         61/ ¬v = "2"
        //         62/ q1 = ""
        //         63/ v = "3"
        //         64/ v~ = "Those people are like trees th…nted¦243212 by a stream¦243215" + extras
        //         65/ ¬q1 = ""
        //         66/ q2 = ""
        //         67/ v~ = "and which¦243217 produce¦24321…fruit¦243218 in season¦243221."
        //         68/ ¬q2 = ""
        //         69/ q1 = ""
        //         70/ v~ = "Their leaves don't¦243223 wither¦243225,"
        //         71/ ¬q1 = ""
        //         72/ q2 = ""
        //         73/ v~ = "and they prosper in everything they do." + extras
        //         74/ ¬q2 = ""
        //         75/ ¬v = "3"
        //         76/ b = ""
        //         77/ q1 = ""
        //         78/ v = "4"
        //         79/ v~ = "But wicked¦243235 people won't prosper—"
        //         80/ ¬q1 = ""
        //         81/ q1 = ""
        //         82/ v~ = "they're like straw that¦243240…blown away by the wind¦243243."
        //         83/ ¬q1 = ""
        //         84/ ¬v = "4"
        //         85/ q1 = ""
        //         86/ v = "5"
        //         87/ v~ = "The wicked¦243252 people won't…1 when God judges¦243253 them,"
        //         88/ ¬q1 = ""
        //         89/ q1 = ""
        //         90/ v~ = "and sinners¦243254 won't be ab…f all the godly¦243256 people,"
        //         91/ ¬q1 = ""
        //         92/ ¬v = "5"
        //         93/ q1 = ""
        //         94/ v = "6"
        //         95/ v~ = "because Yahweh¦243261 knows th…chosen by godly¦243263 people,"
        //         96/ ¬q1 = ""
        //         97/ q1 = ""
        //         98/ v~ = "but¦243264 the path of wicked¦…3265 people will be destroyed."
        //         99/ ¬v = "6"
        //         100/ ¬q1 = ""
        //         101/ ¬s1 = ""
        //         102/ ¬c = "1"
        //         103/ c = "2"
        //         104/ v= = "1"
        //         105/ s1 = "God's chosen king"
        //         106/ rem = "/s1 God's Promise to His Anointed; God's Chosen King"
        //         107/ q1 = ""
        //         108/ c# = "2"
        //         109/ v = "1"
        //         110/ v~ = "Why do nations¦243270 make plans," + extras
        //         111/ ¬q1 = ""
        //         112/ q2 = ""
        //         113/ v~ = "≈and¦243271 people¦243271 grou…s devise¦243272 empty schemes?"
        //         114/ ¬q2 = ""
        //         115/ ¬v = "1"
        //         116/ q1 = ""
        //         117/ v = "2"
        //         118/ v~ = "The kings¦243278 of this world…3276 their¦243276 stand¦243276"
        //         119/ ¬q1 = ""
        //         120/ q2 = ""
        //         121/ v~ = "≈and the rulers¦243281 collabo…weh¦243287 and his chosen one,"
        //         122/ ¬q2 = ""
        //         123/ ¬v = "2"
        //         124/ q1 = ""
        //         125/ v = "3"
        //         126/ v~ = "saying, “Let's break their chains off us."
        //         127/ ¬q1 = ""
        //         128/ q1 = ""
        //         129/ v~ = "≈Let's throw¦243296 off their ropes¦243298.”"
        //         130/ ¬q1 = ""
        //         131/ ¬v = "3"
        //         132/ q1 = ""
        //         133/ v = "4"
        //         134/ v~ = "The one who sits¦243300 in¦243… heavens¦243301 laughs¦243302."
        //         135/ ¬q1 = ""
        //         136/ q1 = ""
        //         137/ v~ = "≈The master¦243303 ridicules them."
        //         138/ ¬q1 = ""
        //         139/ ¬v = "4"
        //         140/ q1 = ""
        //         141/ v = "5"
        //         142/ v~ = "Then he'll speak¦243309 to them in his anger¦243311,"
        //         143/ ¬q1 = ""
        //         144/ q1 = ""
        //         145/ v~ = "≈and¦243312 terrify¦243313 them in his fury."
        //         146/ ¬q1 = ""
        //         147/ ¬v = "5"
        //         148/ q1 = ""
        //         149/ v = "6"
        //         150/ v~ = "Yahweh says, “I myself have pl… Tsiyyon¦243320 (Zion¦243320)—"
        //         151/ ¬q1 = ""
        //         152/ q2 = ""
        //         153/ v~ = "the hill¦243321 I've¦243316 chosen to be my holy place.”"
        //         154/ ¬q2 = ""
        //         155/ ¬v = "6"
        //         156/ q1 = ""
        //         157/ v = "7"
        //         158/ v~ = "I'll¦243325 explain Yahweh's¦243328 decree¦243327." + extras
        //         159/ ¬q1 = ""
        //         160/ q1 = ""
        //         161/ v~ = "He told me, “You're my son. To…'ve¦243335 become your father."
        //         162/ ¬q1 = ""
        //         163/ ¬v = "7"
        //         164/ q1 = ""
        //         165/ v = "8"
        //         166/ v~ = "Ask me and I'll¦243339 give th…u for your inheritance¦243341."
        //         167/ ¬q1 = ""
        //         168/ q1 = ""
        //         169/ v~ = "≈The whole world will be owned by you."
        //         170/ ¬q1 = ""
        //         171/ ¬v = "8"
        //         172/ q1 = ""
        //         173/ v = "9"
        //         174/ v~ = "You'll break¦243347 those nations with¦243348 an iron bar." + extras
        //         175/ ¬q1 = ""
        //         176/ q1 = ""
        //         177/ v~ = "≈You'll smash¦243352 them to pieces like a clay pot.”"
        //         178/ ¬q1 = ""
        //         179/ ¬v = "9"
        //         180/ b = ""
        //         181/ q1 = ""
        //         182/ v = "10"
        //         183/ v~ = "So¦243354 act¦243356 wisely all you kings¦243355."
        //         184/ ¬q1 = ""
        //         185/ q1 = ""
        //         186/ v~ = "≈Be warned all you rulers¦243358 of the earth¦243359."
        //         187/ ¬q1 = ""
        //         188/ ¬v = "10"
        //         189/ q1 = ""
        //         190/ v = "11"
        //         191/ v~ = "Serve¦243361 Yahweh¦243364 with¦243365 fear¦243365."
        //         192/ ¬q1 = ""
        //         193/ q1 = ""
        //         194/ v~ = "Be happy for his goodness but¦…e¦243367 because of his power."
        //         195/ ¬q1 = ""
        //         196/ ¬v = "11"
        //         197/ q1 = ""
        //         198/ v = "12"
        //         199/ v~ = "Honour the son or he might get angry¦243374"
        //         200/ ¬q1 = ""
        //         201/ q2 = ""
        //         202/ v~ = "and you'll perish¦243376 on the way¦243377."
        //         203/ ¬q2 = ""
        //         204/ q1 = ""
        //         205/ v~ = "His severe¦243382 anger¦243382 can ignite any moment¦243381."
        //         206/ ¬q1 = ""
        //         207/ q1 = ""
        //         208/ v~ = "Everyone who goes to him to be safe will reap the benefits."
        //         209/ ¬v = "12"
        //         210/ ¬q1 = ""
        //         211/ ¬s1 = ""
        //         212/ ¬c = "2"
        //         213/ c = "3"
        //         214/ v= = "1"
        //         215/ s1 = "A prayer when under attack"
        //         216/ rem = "/s1 Trust in God under Adversity; Morning Prayer for Help"
        //         217/ c# = "3"
        //         218/ d = "A song by David¦243390 when he…son Avshalom (Absalom¦243394)."
        //         219/ q1 = ""
        //         220/ v = "1"
        //         221/ v~ = "Yahweh¦243398, how did I get so many enemies?"
        //         222/ ¬q1 = ""
        //         223/ q1 = ""
        //         224/ v~ = "≈Many people are rising¦243404 up against¦243405 me."
        //         225/ ¬q1 = ""
        //         226/ ¬v = "1"
        //         227/ q1 = ""
        //         228/ v = "2"
        //         229/ v~ = "Many people are talking¦243409 about me,"
        //         230/ ¬q1 = ""
        //         231/ q1 = ""
        //         232/ v~ = "≡saying that God¦243414 won't¦…rumental¦243415 break¦243415.)" + extras
        //         233/ ¬q1 = ""
        //         234/ ¬v = "2"
        //         235/ b = ""
        //         236/ q1 = ""
        //         237/ v = "3"
        //         238/ v~ = "≈But¦243418 you, Yahweh¦243419…otect me like a shield¦243420."
        //         239/ ¬q1 = ""
        //         240/ q1 = ""
        //         241/ v~ = "≈You honour¦243422 and encourage me."
        //         242/ ¬q1 = ""
        //         243/ ¬v = "3"
        //         244/ q1 = ""
        //         245/ v = "4"
        //         246/ v~ = "I¦243431 called¦243431 out with my voice to Yahweh¦243430,"
        //         247/ ¬q1 = ""
        //         248/ q1 = ""
        //         249/ v~ = "and¦243432 he¦243432 answered¦…rumental¦243435 break¦243435.)"
        //         250/ ¬q1 = ""
        //         251/ ¬v = "4"
        //         252/ b = ""
        //         253/ q1 = ""
        //         254/ v = "5"
        //         255/ v~ = "I laid down and¦243440 slept¦243440."
        //         256/ ¬q1 = ""
        //         257/ q1 = ""
        //         258/ v~ = "I awoke¦243441, because¦243442…weh¦243443 sustains¦243444 me."
        //         259/ ¬q1 = ""
        //         260/ ¬v = "5"
        //         261/ q1 = ""
        //         262/ v = "6"
        //         263/ v~ = "I¦243449 won't¦243447 be afrai…sands¦243450 of people¦243451—"
        //         264/ ¬q1 = ""
        //         265/ q1 = ""
        //         266/ v~ = "those all around¦243453 who've…tand¦243454 against¦243455 me."
        //         267/ ¬q1 = ""
        //         268/ ¬v = "6"
        //         269/ b = ""
        //         270/ q1 = ""
        //         271/ v = "7"
        //         272/ v~ = "≈Take action, Yahweh¦243459."
        //         273/ ¬q1 = ""
        //         274/ q1 = ""
        //         275/ v~ = "≈Save me, my god¦243462."
        //         276/ ¬q1 = ""
        //         277/ q1 = ""
        //         278/ v~ = "≈Yes, you've slapped all my enemies¦243470 on the cheek—"
        //         279/ ¬q1 = ""
        //         280/ q1 = ""
        //         281/ v~ = "you've broken¦243474 the teeth…2 of the wicked¦243473 people."
        //         282/ ¬q1 = ""
        //         283/ ¬v = "7"
        //         284/ q1 = ""
        //         285/ v = "8"
        //         286/ v~ = "Salvation belongs to Yahweh¦243477."
        //         287/ ¬q1 = ""
        //         288/ q1 = ""
        //         289/ v~ = "Your blessing¦243482 goes to y…rumental¦243483 break¦243483.)"
        //         290/ ¬v = "8"
        //         291/ ¬q1 = ""
        //         292/ ¬s1 = ""
        //         293/ ¬c = "3"
        //         294/ c = "4"
        //         295/ v= = "1"
        //         296/ s1 = "A night-time prayer"
        //         297/ rem = "/s1 Confident Plea for Deliver…emies; Evening Prayer for Help"
        //         298/ c# = "4"
        //         299/ d = "For the musical director¦24348…ged¦243486 instruments¦243486."
        //         … (22,583 total entries)

        let mut section_index = InternalBibleBookSectionIndex::new("OET-RV", "PSA");
        section_index.build(processed_line_entries.clone()).unwrap();
        
        // for (ee,(cv,entry)) in section_index.index_data.iter().enumerate() { println!("{}/ {} {}", ee, cv, entry); }
        // It should give the following 178 entries:
        //     0/ -1:0 SectionEntry(ends -1:11 lines 0-11 Headers "PSA" [])
        //     1/ -1:13 SectionEntry(ends -1:31 lines 13-31 is1 "Introduction" [])
        //     2/ 1:0 SectionEntry(ends 0:0 lines 33-36 c/ms1 "First collection" [chapters, c])
        //     3/ 1:1 SectionEntry(ends 1:6 lines 37-102 c/s1 "Wicked and godly roads" [chapters, c])
        //     4/ 2:1 SectionEntry(ends 2:12 lines 103-212 c/s1 "God's chosen king" [chapters, c])
        //     5/ 3:1 SectionEntry(ends 3:8 lines 213-293 c/s1 "A prayer when under attack" [chapters, c])
        //     6/ 4:1 SectionEntry(ends 4:8 lines 294-372 c/s1 "A night-time prayer" [chapters, c])
        //     7/ 5:1 SectionEntry(ends 5:12 lines 373-499 c/s1 "A prayer for protection" [chapters, c])
        //     8/ 6:1 SectionEntry(ends 6:10 lines 500-593 c/s1 "A prayer in time of distress" [chapters, c])
        //     9/ 7:1 SectionEntry(ends 7:17 lines 594-758 c/s1 "A prayer for justice" [chapters, c])
        //     10/ 8:1 SectionEntry(ends 8:9 lines 759-841 c/s1 "God's splendour and mankind's status" [chapters, c])
        //     11/ 9:1 SectionEntry(ends 9:20 lines 842-1021 c/s1 "Thanking Yahweh for his justice" [chapters, c])
        //     12/ 10:1 SectionEntry(ends 10:18 lines 1022-1192 c/s1 "A prayer for relief from bullies" [chapters, c])
        //     13/ 11:1 SectionEntry(ends 11:7 lines 1193-1263 c/s1 "Trusting God for fair process" [chapters, c])
        //     14/ 12:1 SectionEntry(ends 12:8 lines 1264-1345 c/s1 "The requesting of God" [chapters, c])
        //     15/ 13:1 SectionEntry(ends 13:6 lines 1346-1403 c/s1 "A prayer for help" [chapters, c])
        //     16/ 14:1 SectionEntry(ends 14:7 lines 1404-1480 c/s1 "Responding to evil people" [chapters, c])
        //     17/ 15:1 SectionEntry(ends 15:5 lines 1481-1537 c/s1 "Who does Yahweh like?" [chapters, c])
        //     18/ 16:1 SectionEntry(ends 16:11 lines 1538-1639 c/s1 "Yahweh is my security" [chapters, c])
        //     19/ 17:1 SectionEntry(ends 17:15 lines 1640-1796 c/s1 "A prayer for protection" [chapters, c])
        //     20/ 18:1 SectionEntry(ends 18:50 lines 1797-2247 c/s1 "David's song of victory" [chapters, c])
        //     21/ 19:1 SectionEntry(ends 19:14 lines 2248-2390 c/s1 "God's splendour displayed" [chapters, c])
        //     22/ 20:1 SectionEntry(ends 20:9 lines 2391-2476 c/s1 "A prayer for victory" [chapters, c])
        //     23/ 21:1 SectionEntry(ends 21:13 lines 2477-2588 c/s1 "Praise for victory" [chapters, c])
        //     24/ 22:1 SectionEntry(ends 22:31 lines 2589-2868 c/s1 "A cry of pain then a praise song" [chapters, c])
        //     25/ 23:1 SectionEntry(ends 23:6 lines 2869-2930 c/s1 "Protected and blessed by the shepherd" [chapters, c])
        //     26/ 24:1 SectionEntry(ends 24:10 lines 2931-3033 c/s1 "God the powerful King" [chapters, c])
        //     27/ 25:1 SectionEntry(ends 25:22 lines 3034-3242 c/s1 "The praying so that get to teach" [chapters, c])
        //     28/ 26:1 SectionEntry(ends 26:12 lines 3243-3346 c/s1 "A prayer of a godly person" [chapters, c])
        //     29/ 27:1 SectionEntry(ends 27:14 lines 3347-3487 c/s1 "A prayer of praise" [chapters, c])
        //     30/ 28:1 SectionEntry(ends 28:9 lines 3488-3585 c/s1 "Prayer of requesting" [chapters, c])
        //     31/ 29:1 SectionEntry(ends 29:11 lines 3586-3681 c/s1 "The incredible power of God's voice" [chapters, c])
        //     32/ 30:1 SectionEntry(ends 30:12 lines 3682-3788 c/s1 "Thanking Yahweh after sickness" [chapters, c])
        //     33/ 31:1 SectionEntry(ends 31:24 lines 3789-4030 c/s1 "Trusting Yahweh despite enemies" [chapters, c])
        //     34/ 32:1 SectionEntry(ends 32:11 lines 4031-4138 c/s1 "Admitting sin and requesting forgiveness" [chapters, c])
        //     35/ 33:1 SectionEntry(ends 33:22 lines 4139-4312 c/s1 "A praise song" [chapters, c])
        //     36/ 34:1 SectionEntry(ends 34:22 lines 4313-4524 c/s1 "Praising Yahweh's goodness together" [chapters, c])
        //     37/ 35:1 SectionEntry(ends 35:28 lines 4525-4771 c/s1 "Requesting Yahweh's help" [chapters, c])
        //     38/ 36:1 SectionEntry(ends 36:12 lines 4772-4880 c/s1 "Wicked people and Yahweh's goodness" [chapters, c])
        //     39/ 37:1 SectionEntry(ends 37:40 lines 4881-5249 c/s1 "The endings of godly and wicked people" [chapters, c])
        //     40/ 38:1 SectionEntry(ends 38:22 lines 5250-5439 c/s1 "The requesting of person suffering" [chapters, c])
        //     41/ 39:1 SectionEntry(ends 39:13 lines 5440-5570 c/s1 "The telling of sin of person suffering" [chapters, c])
        //     42/ 40:1 SectionEntry(ends 40:17 lines 5571-5737 c/s1 "A song praising Yahweh" [chapters, c])
        //     43/ 41:1 SectionEntry(ends 41:13 lines 5738-5861 c/s1 "A prayer for healing" [chapters, c])
        //     44/ 42:0 SectionEntry(ends 0:0 lines 5862-5864 c/ms1 "Second collection" [chapters, c])
        //     45/ 42:1 SectionEntry(ends 42:11 lines 5865-5979 c/s1 "Hope when depressed" [chapters, c])
        //     46/ 43:1 SectionEntry(ends 43:5 lines 5980-6045 c/s1 "The requesting at time of conflict" [chapters, c])
        //     47/ 44:1 SectionEntry(ends 44:26 lines 6046-6258 c/s1 "A prayer for help" [chapters, c])
        //     48/ 45:1 SectionEntry(ends 45:17 lines 6259-6408 c/s1 "A royal wedding song" [chapters, c])
        //     49/ 46:1 SectionEntry(ends 46:11 lines 6409-6510 c/s1 "God's right here" [chapters, c])
        //     50/ 47:1 SectionEntry(ends 47:9 lines 6511-6593 c/s1 "God the king of entire world" [chapters, c])
        //     51/ 48:1 SectionEntry(ends 48:14 lines 6594-6731 c/s1 "Yerushalem, God's city" [chapters, c])
        //     52/ 49:1 SectionEntry(ends 49:20 lines 6732-6914 c/s1 "Trusting in wealth is foolishness" [chapters, c])
        //     53/ 50:1 SectionEntry(ends 50:23 lines 6915-7124 c/s1 "The true/correct worshipping" [chapters, c])
        //     54/ 51:1 SectionEntry(ends 51:19 lines 7125-7293 c/s1 "A prayer for forgiveness" [chapters, c])
        //     55/ 52:1 SectionEntry(ends 52:9 lines 7294-7379 c/s1 "God's judgement and mercy" [chapters, c])
        //     56/ 53:1 SectionEntry(ends 53:6 lines 7380-7457 c/s1 "Fools and human wickedness" [chapters, c])
        //     57/ 54:1 SectionEntry(ends 54:7 lines 7458-7524 c/s1 "God is my helper" [chapters, c])
        //     58/ 55:1 SectionEntry(ends 55:23 lines 7525-7725 c/s1 "A prayer for a person betrayed by a friend" [chapters, c])
        //     59/ 56:1 SectionEntry(ends 56:13 lines 7726-7838 c/s1 "The praying due trusting of God" [chapters, c])
        //     60/ 57:1 SectionEntry(ends 57:11 lines 7839-7946 c/s1 "A prayer for protection from predators" [chapters, c])
        //     61/ 58:1 SectionEntry(ends 58:11 lines 7947-8042 c/s1 "Punishment for the wicked" [chapters, c])
        //     62/ 59:1 SectionEntry(ends 59:17 lines 8043-8210 c/s1 "A prayer for safety" [chapters, c])
        //     63/ 60:1 SectionEntry(ends 60:12 lines 8211-8326 c/s1 "A prayer for military help" [chapters, c])
        //     64/ 61:1 SectionEntry(ends 61:8 lines 8327-8398 c/s1 "A prayer for protection" [chapters, c])
        //     65/ 62:1 SectionEntry(ends 62:12 lines 8399-8520 c/s1 "Trusting in God" [chapters, c])
        //     66/ 63:1 SectionEntry(ends 63:11 lines 8521-8622 c/s1 "Staying close to God" [chapters, c])
        //     67/ 64:1 SectionEntry(ends 64:10 lines 8623-8719 c/s1 "Trusting God for protection" [chapters, c])
        //     68/ 65:1 SectionEntry(ends 65:13 lines 8720-8864 c/s1 "Praising and thanking God" [chapters, c])
        //     69/ 66:1 SectionEntry(ends 66:20 lines 8865-9041 c/s1 "Praising and thanking God" [chapters, c])
        //     70/ 67:1 SectionEntry(ends 67:7 lines 9042-9108 c/s1 "A song thanking God" [chapters, c])
        //     71/ 68:1 SectionEntry(ends 68:35 lines 9109-9441 c/s1 "A song of victory" [chapters, c])
        //     72/ 69:1 SectionEntry(ends 69:36 lines 9442-9752 c/s1 "A request for help" [chapters, c])
        //     73/ 70:1 SectionEntry(ends 70:5 lines 9753-9798 c/s1 "A prayer for help" [chapters, c])
        //     74/ 71:1 SectionEntry(ends 71:24 lines 9799-10003 c/s1 "Prayer for long-term protection" [chapters, c])
        //     75/ 72:1 SectionEntry(ends 72:20 lines 10004-10185 c/s1 "A prayer to bless the king" [chapters, c])
        //     76/ 73:0 SectionEntry(ends 0:0 lines 10186-10188 c/ms1 "Third collection" [chapters, c])
        //     77/ 73:1 SectionEntry(ends 73:28 lines 10189-10424 c/s1 "The need for justice" [chapters, c])
        //     78/ 74:1 SectionEntry(ends 74:23 lines 10425-10619 c/s1 "Requesting God's help" [chapters, c])
        //     79/ 75:1 SectionEntry(ends 75:10 lines 10620-10710 c/s1 "God the judge" [chapters, c])
        //     80/ 76:1 SectionEntry(ends 76:12 lines 10711-10817 c/s1 "God is victorious" [chapters, c])
        //     81/ 77:1 SectionEntry(ends 77:20 lines 10818-11003 c/s1 "God's leadership" [chapters, c])
        //     82/ 78:1 SectionEntry(ends 78:72 lines 11004-11632 c/s1 "God's past goodness" [chapters, c])
        //     83/ 79:1 SectionEntry(ends 79:13 lines 11633-11753 c/s1 "A prayer for national restoration" [chapters, c])
        //     84/ 80:1 SectionEntry(ends 80:19 lines 11754-11916 c/s1 "A prayer for national restoration" [chapters, c])
        //     85/ 81:1 SectionEntry(ends 81:16 lines 11917-12058 c/s1 "Thanking God for relief" [chapters, c])
        //     86/ 82:1 SectionEntry(ends 82:8 lines 12059-12133 c/s1 "God the defender" [chapters, c])
        //     87/ 83:1 SectionEntry(ends 83:18 lines 12134-12282 c/s1 "Praying for victory over enemies" [chapters, c])
        //     88/ 84:1 SectionEntry(ends 84:12 lines 12283-12395 c/s1 "Longing to be in Yahweh's courtyards" [chapters, c])
        //     89/ 85:1 SectionEntry(ends 85:13 lines 12396-12510 c/s1 "Prayer for national peace" [chapters, c])
        //     90/ 86:1 SectionEntry(ends 86:17 lines 12511-12663 c/s1 "God's great love" [chapters, c])
        //     91/ 87:1 SectionEntry(ends 87:7 lines 12664-12724 c/s1 "Praising Tsiyyon (Zion)" [chapters, c])
        //     92/ 88:1 SectionEntry(ends 88:18 lines 12725-12888 c/s1 "A depressed cry for help" [chapters, c])
        //     93/ 89:1 SectionEntry(ends 89:52 lines 12889-13320 c/s1 "To be sung my the goodness of God" [chapters, c])
        //     94/ 90:0 SectionEntry(ends 0:0 lines 13321-13323 c/ms1 "Fourth collection" [chapters, c])
        //     95/ 90:1 SectionEntry(ends 90:17 lines 13324-13480 c/s1 "The people and the god" [chapters, c])
        //     96/ 91:1 SectionEntry(ends 91:16 lines 13481-13624 c/s1 "God our protector" [chapters, c])
        //     97/ 92:1 SectionEntry(ends 92:15 lines 13625-13757 c/s1 "A praise song" [chapters, c])
        //     98/ 93:1 SectionEntry(ends 93:5 lines 13758-13815 c/s1 "The god King" [chapters, c])
        //     99/ 94:1 SectionEntry(ends 94:23 lines 13816-14014 c/s1 "God the judge of all" [chapters, c])
        //     100/ 95:1 SectionEntry(ends 95:11 lines 14015-14119 c/s1 "A praise song" [chapters, c])
        //     101/ 96:1 SectionEntry(ends 96:13 lines 14120-14240 c/s1 "Praise God—he deserves it" [chapters, c])
        //     102/ 97:1 SectionEntry(ends 97:12 lines 14241-14355 c/s1 "God's splendour" [chapters, c])
        //     103/ 98:1 SectionEntry(ends 98:9 lines 14356-14438 c/s1 "Praising the master" [chapters, c])
        //     104/ 99:1 SectionEntry(ends 99:9 lines 14439-14537 c/s1 "The holiness of our god" [chapters, c])
        //     105/ 100:1 SectionEntry(ends 100:5 lines 14538-14591 c/s1 "Let's thank and praise Yahweh" [chapters, c])
        //     106/ 101:1 SectionEntry(ends 101:8 lines 14592-14666 c/s1 "A good king's pledge" [chapters, c])
        //     107/ 102:1 SectionEntry(ends 102:28 lines 14667-14901 c/s1 "Prayer for relief from troubles" [chapters, c])
        //     108/ 103:1 SectionEntry(ends 103:22 lines 14902-15092 c/s1 "Yahweh's goodness" [chapters, c])
        //     109/ 104:1 SectionEntry(ends 104:35 lines 15093-15400 c/s1 "Praising the creator" [chapters, c])
        //     110/ 105:1 SectionEntry(ends 105:45 lines 15401-15771 c/s1 "Yahweh's faithfulness" [chapters, c])
        //     111/ 106:1 SectionEntry(ends 106:48 lines 15772-16193 c/s1 "Yahweh's goodness" [chapters, c])
        //     112/ 107:0 SectionEntry(ends 0:0 lines 16194-16196 c/ms1 "Fifth collection" [chapters, c])
        //     113/ 107:1 SectionEntry(ends 107:43 lines 16197-16551 c/s1 "Thanking for God's goodness" [chapters, c])
        //     114/ 108:1 SectionEntry(ends 108:13 lines 16552-16667 c/s1 "Praise, then prayer for victory" [chapters, c])
        //     115/ 109:1 SectionEntry(ends 109:31 lines 16668-16929 c/s1 "My god help me" [chapters, c])
        //     116/ 110:1 SectionEntry(ends 110:7 lines 16930-16996 c/s1 "Yahweh and his chosen king" [chapters, c])
        //     117/ 111:1 SectionEntry(ends 111:10 lines 16997-17114 c/s1 "Praise for what Yahweh's done" [chapters, c])
        //     118/ 112:1 SectionEntry(ends 112:10 lines 17115-17232 c/s1 "The blessing for a godly person" [chapters, c])
        //     119/ 113:1 SectionEntry(ends 113:9 lines 17233-17311 c/s1 "Praising Yahweh's goodness" [chapters, c])
        //     120/ 114:1 SectionEntry(ends 114:8 lines 17312-17382 c/s1 "Praising God's past miracles" [chapters, c])
        //     121/ 115:1 SectionEntry(ends 115:18 lines 17383-17545 c/s1 "Trust in Yahweh" [chapters, c])
        //     122/ 116:1 SectionEntry(ends 116:19 lines 17546-17710 c/s1 "Praise Yahweh who rescued me" [chapters, c])
        //     123/ 117:1 SectionEntry(ends 117:2 lines 17711-17736 c/s1 "Praising Yahweh's commitment to us" [chapters, c])
        //     124/ 118:1 SectionEntry(ends 118:29 lines 17737-17978 c/s1 "Not ending the love of God" [chapters, c])
        //     125/ 119:1 SectionEntry(ends 119:8 lines 17979-18049 c/s1 "Obeying Yahweh's instructions" [chapters, c])
        //     126/ 119:9 SectionEntry(ends 119:16 lines 18050-18118 s1 "Internalising Yahweh's principles" [chapters, c])
        //     127/ 119:17 SectionEntry(ends 119:24 lines 18119-18187 s1 "Pleased to obey Yahweh's instructions" [chapters, c])
        //     128/ 119:25 SectionEntry(ends 119:32 lines 18188-18256 s1 "Choosing Yahweh's way" [chapters, c])
        //     129/ 119:33 SectionEntry(ends 119:40 lines 18257-18325 s1 "Prayer for guidance" [chapters, c])
        //     130/ 119:41 SectionEntry(ends 119:48 lines 18326-18394 s1 "Trusting Yahweh's instructions" [chapters, c])
        //     131/ 119:49 SectionEntry(ends 119:56 lines 18395-18463 s1 "Comforted by Yahweh's principles" [chapters, c])
        //     132/ 119:57 SectionEntry(ends 119:64 lines 18464-18532 s1 "The loving of Law of God" [chapters, c])
        //     133/ 119:65 SectionEntry(ends 119:72 lines 18533-18601 s1 "The purpose of Yahweh's instructions" [chapters, c])
        //     134/ 119:73 SectionEntry(ends 119:80 lines 18602-18673 s1 "The justice of Yahweh's instructions" [chapters, c])
        //     135/ 119:81 SectionEntry(ends 119:88 lines 18674-18742 s1 "Requesting Yahweh's intervention" [chapters, c])
        //     136/ 119:89 SectionEntry(ends 119:96 lines 18743-18805 s1 "Trusting in Yahweh's principles" [chapters, c])
        //     137/ 119:97 SectionEntry(ends 119:104 lines 18806-18874 s1 "Appreciating Yahweh's principles" [chapters, c])
        //     138/ 119:105 SectionEntry(ends 119:112 lines 18875-18940 s1 "The peace/prosperity from law of God" [chapters, c])
        //     139/ 119:113 SectionEntry(ends 119:120 lines 18941-19009 s1 "Safety in Yahweh's instructions" [chapters, c])
        //     140/ 119:121 SectionEntry(ends 119:128 lines 19010-19078 s1 "Obeying Yahweh's instructions" [chapters, c])
        //     141/ 119:129 SectionEntry(ends 119:136 lines 19079-19147 s1 "Wanting to obey Yahweh's instructions" [chapters, c])
        //     142/ 119:137 SectionEntry(ends 119:144 lines 19148-19216 s1 "Yahweh demands obedience" [chapters, c])
        //     143/ 119:145 SectionEntry(ends 119:152 lines 19217-19285 s1 "Calling to be rescued" [chapters, c])
        //     144/ 119:153 SectionEntry(ends 119:160 lines 19286-19354 s1 "Calling to be rescued" [chapters, c])
        //     145/ 119:161 SectionEntry(ends 119:168 lines 19355-19423 s1 "Obeying Yahweh's instructions" [chapters, c])
        //     146/ 119:169 SectionEntry(ends 119:176 lines 19424-19493 s1 "A prayer for help" [chapters, c])
        //     147/ 120:1 SectionEntry(ends 120:7 lines 19494-19560 c/s1 "Asking Yahweh for peace" [chapters, c])
        //     148/ 121:1 SectionEntry(ends 121:8 lines 19561-19632 c/s1 "Yahweh our protector" [chapters, c])
        //     149/ 122:1 SectionEntry(ends 122:9 lines 19633-19708 c/s1 "Wanting peace for Yerushalem" [chapters, c])
        //     150/ 123:1 SectionEntry(ends 123:4 lines 19709-19752 c/s1 "Praying to see mercy" [chapters, c])
        //     151/ 124:1 SectionEntry(ends 124:8 lines 19753-19823 c/s1 "Thanking for Yahweh's protection" [chapters, c])
        //     152/ 125:1 SectionEntry(ends 125:5 lines 19824-19875 c/s1 "Against wicked rulers" [chapters, c])
        //     153/ 126:1 SectionEntry(ends 126:6 lines 19876-19935 c/s1 "The cheerful harvest" [chapters, c])
        //     154/ 127:1 SectionEntry(ends 127:5 lines 19936-19987 c/s1 "Children are a blessing" [chapters, c])
        //     155/ 128:1 SectionEntry(ends 128:6 lines 19988-20043 c/s1 "Prosperity for those who honour Yahweh" [chapters, c])
        //     156/ 129:1 SectionEntry(ends 129:8 lines 20044-20119 c/s1 "Praying against haters of Tsiyyon" [chapters, c])
        //     157/ 130:1 SectionEntry(ends 130:8 lines 20120-20193 c/s1 "Yahweh can redeem us" [chapters, c])
        //     158/ 131:1 SectionEntry(ends 131:3 lines 20194-20225 c/s1 "Explaing inner peace" [chapters, c])
        //     159/ 132:1 SectionEntry(ends 132:18 lines 20226-20377 c/s1 "Yahweh's resting place in Tsiyyon" [chapters, c])
        //     160/ 133:1 SectionEntry(ends 133:3 lines 20378-20415 c/s1 "Living peacefully together" [chapters, c])
        //     161/ 134:1 SectionEntry(ends 134:3 lines 20416-20445 c/s1 "Lift your hands and bless Yahweh" [chapters, c])
        //     162/ 135:1 SectionEntry(ends 135:21 lines 20446-20638 c/s1 "A praise song" [chapters, c])
        //     163/ 136:1 SectionEntry(ends 136:26 lines 20639-20856 c/s1 "A song of thankfulness" [chapters, c])
        //     164/ 137:1 SectionEntry(ends 137:9 lines 20857-20941 c/s1 "Mourning Yerushalem's destruction" [chapters, c])
        //     165/ 138:1 SectionEntry(ends 138:8 lines 20942-21027 c/s1 "A prayer of thankfulness" [chapters, c])
        //     166/ 139:1 SectionEntry(ends 139:24 lines 21028-21237 c/s1 "God's care and total knowledge" [chapters, c])
        //     167/ 140:1 SectionEntry(ends 140:13 lines 21238-21359 c/s1 "A prayer for protection" [chapters, c])
        //     168/ 141:1 SectionEntry(ends 141:10 lines 21360-21462 c/s1 "Accepting correction" [chapters, c])
        //     169/ 142:1 SectionEntry(ends 142:7 lines 21463-21533 c/s1 "A prayer for protection" [chapters, c])
        //     170/ 143:1 SectionEntry(ends 143:12 lines 21534-21658 c/s1 "A prayer to be rescued" [chapters, c])
        //     171/ 144:1 SectionEntry(ends 144:15 lines 21659-21807 c/s1 "The thanking due to victory" [chapters, c])
        //     172/ 145:1 SectionEntry(ends 145:21 lines 21808-22007 c/s1 "A praise song" [chapters, c])
        //     173/ 146:1 SectionEntry(ends 146:10 lines 22008-22110 c/s1 "Praise Yahweh the liberator" [chapters, c])
        //     174/ 147:1 SectionEntry(ends 147:20 lines 22111-22293 c/s1 "Praise Yahweh who's in control" [chapters, c])
        //     175/ 148:1 SectionEntry(ends 148:14 lines 22294-22431 c/s1 "Praise Yahweh everyone" [chapters, c])
        //     176/ 149:1 SectionEntry(ends 149:9 lines 22432-22518 c/s1 "A song of praise" [chapters, c])
        //     177/ 150:1 SectionEntry(ends 150:6 lines 22519-22581 c/s1 "Praise Yahweh everyone" [chapters, c])

        assert_eq!(section_index.len(), 178);
        let sections: Vec<_> = section_index.index_data.iter().map(|(_, entry)| entry.reason_marker().to_string()).collect();
        assert_eq!(sections, vec!["Headers", "is1",
                    "c/ms1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1",
                    "c/ms1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1",
                    "c/ms1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1",
                    "c/ms1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1",
                    "c/ms1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "s1", "s1", "s1", "s1", "s1", "s1", "s1", "s1", "s1", "s1", "s1", "s1", "s1", "s1", "s1", "s1", "s1", "s1", "s1", "s1", "s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1", "c/s1"]);
 
        // 0 -1:0 Headers='SA2'
        let (cv0, entry0) = section_index.index_data.get_index(0).unwrap();
        assert_eq!(cv0.to_string(), "-1:0");
        assert_eq!(entry0.end_cv().to_string(), "-1:11");
        assert_eq!(entry0.start_index(), 0);
        assert_eq!(entry0.end_index(), 11); // ends at '¬headers'
        assert_eq!(entry0.reason_marker(), "Headers");
        assert_eq!(entry0.section_name(), "PSA");

        // 1 -1:13 is1='Introduction'
        let (cv1, entry1) = section_index.index_data.get_index(1).unwrap();
        assert_eq!(cv1.to_string(), "-1:13");
        assert_eq!(entry1.end_cv().to_string(), "-1:31");
        assert_eq!(entry1.start_index(), 13);
        assert_eq!(entry1.end_index(), 31);
        assert_eq!(entry1.reason_marker(), "is1");
        assert_eq!(entry1.section_name(), "Introduction");

        // 2 1:0 ms1='First collection'
        let (cv2, entry2) = section_index.index_data.get_index(2).unwrap();
        assert_eq!(cv2.to_string(), "1:0");
        assert_eq!(entry2.end_cv().to_string(), "0:0");
        assert_eq!(entry2.start_index(), 33); // c
        assert_eq!(entry2.end_index(), 36); // mr
        assert_eq!(entry2.reason_marker(), "c/ms1");
        assert_eq!(entry2.section_name(), "First collection");

        // 2 1:1 s1='Wicked and godly roads'
        let (cv3, entry3) = section_index.index_data.get_index(3).unwrap();
        assert_eq!(cv3.to_string(), "1:1");
        assert_eq!(entry3.end_cv().to_string(), "1:6");
        assert_eq!(entry3.start_index(), 37); // s1
        assert_eq!(entry3.end_index(), 102); // ¬c
        assert_eq!(entry3.reason_marker(), "c/s1");
        assert_eq!(entry3.section_name(), "Wicked and godly roads");

        // 3 2:1 s1='God's chosen king'
        let (cv4, entry4) = section_index.index_data.get_index(4).unwrap();
        assert_eq!(cv4.to_string(), "2:1");
        assert_eq!(entry4.end_cv().to_string(), "2:12");
        assert_eq!(entry4.start_index(), 103); // v=
        assert_eq!(entry4.end_index(), 212);
        assert_eq!(entry4.reason_marker(), "c/s1");
        assert_eq!(entry4.section_name(), "God's chosen king");

        // 4 42:0 ms1='Second collection'
        let (cv44, entry44) = section_index.index_data.get_index(44).unwrap();
        assert_eq!(cv44.to_string(), "42:0");
        assert_eq!(entry44.end_cv().to_string(), "0:0");
        assert_eq!(entry44.start_index(), 5862);
        assert_eq!(entry44.end_index(), 5864);
        assert_eq!(entry44.reason_marker(), "c/ms1");
        assert_eq!(entry44.section_name(), "Second collection");

        // 5 42:1 s1='Hope when depressed'
        let (cv45, entry45) = section_index.index_data.get_index(45).unwrap();
        assert_eq!(cv45.to_string(), "42:1");
        assert_eq!(entry45.end_cv().to_string(), "42:11");
        assert_eq!(entry45.start_index(), 5865); // s1
        assert_eq!(entry45.end_index(), 5979);
        assert_eq!(entry45.reason_marker(), "c/s1");
        assert_eq!(entry45.section_name(), "Hope when depressed");

        // // 6 2:10 s1='The people have been unfaithful'
        // let (cv6, entry6) = section_index.index_data.get_index(6).unwrap();
        // assert_eq!(cv6.to_string(), "2:10");
        // assert_eq!(entry6.end_cv().to_string(), "2:16");
        // assert_eq!(entry6.start_index(), 133);
        // assert_eq!(entry6.end_index(), 162);
        // assert_eq!(entry6.reason_marker(), "s1");
        // assert_eq!(entry6.section_name(), "The people have been unfaithful");

        // // 7 2:19 s1='Judgement day is coming'
        // let (cv7, entry7) = section_index.index_data.get_index(7).unwrap();
        // assert_eq!(cv7.to_string(), "2:17");
        // assert_eq!(entry7.end_cv().to_string(), "3:5");
        // assert_eq!(entry7.start_index(), 163);
        // assert_eq!(entry7.end_index(), 193);
        // assert_eq!(entry7.reason_marker(), "s1");
        // assert_eq!(entry7.section_name(), "Judgement day is coming");

        // // 8 3:6 s1='Giving a tenth'
        // let (cv8, entry8) = section_index.index_data.get_index(8).unwrap();
        // assert_eq!(cv8.to_string(), "3:6");
        // assert_eq!(entry8.end_cv().to_string(), "3:12");
        // assert_eq!(entry8.start_index(), 194);
        // assert_eq!(entry8.end_index(), 220);
        // assert_eq!(entry8.reason_marker(), "s1");
        // assert_eq!(entry8.section_name(), "Giving a tenth");

        // // 9 3:13 s1='God promises mercy for some'
        // let (cv9, entry9) = section_index.index_data.get_index(9).unwrap();
        // assert_eq!(cv9.to_string(), "3:13");
        // assert_eq!(entry9.end_cv().to_string(), "3:18");
        // assert_eq!(entry9.start_index(), 221);
        // assert_eq!(entry9.end_index(), 247);
        // assert_eq!(entry9.reason_marker(), "s1");
        // assert_eq!(entry9.section_name(), "God promises mercy for some");
    }
}
