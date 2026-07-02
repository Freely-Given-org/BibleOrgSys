//! Chapter:Verse index for fast verse lookup.
//!
//! This module provides:
//! - `CVIndexEntry` - Index entry for a single C:V reference
//! - `InternalBibleBookCVIndex` - Full CV index for a book

use compact_str::CompactString;
use indexmap::IndexMap;
// use log::trace;

use bos_books_codes::is_chapter_verse_book;
use num_format::Locale::ne;
use crate::bos_markers::{regular_nesting, custom_nesting, is_end_marker};
use crate::chapter_verse::ChapterVerse;
use crate::entry_lists::InternalBibleEntryList;
use crate::error::{IndexError, LookupError};
use crate::{have_strict_checking_flag, verbosity_println};

/// An entry in the CV index, representing a single Chapter:Verse reference.
///
/// Each entry stores:
/// - The index into the entry list where this CV starts
/// - The count of entries for this CV
/// - The context (list of open markers at this point)
#[derive(Debug, Clone, PartialEq, Eq, rkyv::Archive, rkyv::Serialize, rkyv::Deserialize)]
pub struct CVIndexEntry {
    /// Index of the first entry for this C:V in the entry list.
    start_index: u32,
    /// Number of entries for this C:V.
    entry_count: u8,
    /// Context markers that were open at this point (e.g., `["chapters", "c", "p"]`).
    context: Vec<CompactString>,
}

impl CVIndexEntry {
    /// Create a new CV index entry.
    #[inline]
    pub fn new(start_index: u32, entry_count: u8, context: Vec<CompactString>) -> Self {
        Self {
            start_index,
            entry_count,
            context,
        }
    }

    /// Get the starting entry index.
    #[inline]
    pub fn start_index(&self) -> usize {
        self.start_index as usize
    }

    /// Get the entry count for this C:V.
    #[inline]
    pub fn entry_count(&self) -> u8 {
        self.entry_count
    }

    /// Get the index one past the last entry for this C:V.
    #[inline]
    pub fn next_start_index(&self) -> usize {
        self.start_index as usize + self.entry_count as usize
    }

    /// Get the context markers.
    #[inline]
    pub fn context(&self) -> &[CompactString] {
        &self.context
    }
}

impl std::fmt::Display for CVIndexEntry {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "CVIndexEntry(idx={}, count={}, ctx={:?})",
            self.start_index, self.entry_count, self.context
        )
    }
}

/// Index for fast Chapter:Verse lookup in a Bible book.
///
/// The index maps `(Chapter, Verse)` references to entry ranges.
///
/// # Special Cases
///
/// - Chapter `-1`: Book introduction
/// - Verse `0`: Chapter introduction / section headings before first verse
/// - Verse ranges: e.g., `17-25` for bridged verses
/// - Verse lists: e.g., `5,6,7` for multiple verses in one entry
/// - Verse suffixes: e.g., `17a`, `17b`
///
/// # Example
///
#[derive(Debug, rkyv::Archive, rkyv::Serialize, rkyv::Deserialize)]
pub struct InternalBibleBookCVIndex {
    /// Name of the work/Bible.
    work_name: CompactString,
    /// Three-letter book code (e.g., "GEN", "MAT").
    bos_book_code: CompactString,
    /// The CV -> entry mapping.
    index_data: IndexMap<ChapterVerse, CVIndexEntry>,
    /// The processed entries this index references.
    line_entries: InternalBibleEntryList,
    /// Whether the index has been built.
    indexed: bool,
}

impl InternalBibleBookCVIndex {
    /// Create a new empty CV index.
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

    /// Get the number of CV entries in the index.
    #[inline]
    pub fn len(&self) -> usize {
        self.index_data.len()
    }

    /// Check if the index is empty.
    #[inline]
    pub fn is_empty(&self) -> bool {
        self.index_data.is_empty()
    }

    /// Check if a specific CV exists in the index.
    #[inline]
    pub fn contains(&self, cv: &ChapterVerse) -> bool {
        self.index_data.contains_key(cv)
    }

    /// Get an iterator over all CV entries.
    pub fn iter(&self) -> impl Iterator<Item = (&ChapterVerse, &CVIndexEntry)> {
        self.index_data.iter()
    }

    /// Get all chapters in the index.
    pub fn chapters(&self) -> Vec<&str> {
        let mut chapters = Vec::new();
        let mut last_chapter: Option<&str> = None;

        for cv in self.index_data.keys() {
            if Some(cv.chapter()) != last_chapter {
                chapters.push(cv.chapter());
                last_chapter = Some(cv.chapter());
            }
        }
        chapters
    }

    /// Get verse entries for a specific C:V.
    ///
    /// # Arguments
    ///
    /// * `cv` - The chapter:verse to look up
    /// * `strict` - If false, also search for verse ranges containing this verse
    ///
    /// # Errors
    ///
    /// Returns `LookupError::NotIndexed` if index hasn't been built.
    /// Returns `LookupError::CVNotFound` if the CV is not in the index.
    pub fn get_verse_entries(&self, cv: &ChapterVerse, strict: bool) -> Result<InternalBibleEntryList, LookupError> {
        if !self.indexed {
            return Err(LookupError::NotIndexed);
        }
        // Try direct lookup first
        if let Some(entry) = self.index_data.get(cv) {
            if have_strict_checking_flag() || cfg!(debug_assertions) {
                self.validate_entries_for_verse(cv, &self.line_entries.slice(entry.start_index(), entry.next_start_index()));
            }
            return Ok(self.line_entries.slice(entry.start_index(), entry.next_start_index()));
        }

        if strict {
            return Err(LookupError::CVNotFound(cv.clone()));
        }

        // Non-strict: search for verse ranges containing this verse
        let desired_v = cv.verse_int().map_err(|_| LookupError::CVNotFound(cv.clone()))?;

        for (key, entry) in &self.index_data {
            if key.chapter() == cv.chapter() {
                // Check verse ranges (e.g., "17-25")
                if let Some((start, end)) = key.parse_verse_range()
                    && start <= desired_v
                    && desired_v <= end
                {
                    return Ok(self.line_entries.slice(entry.start_index(), entry.next_start_index()));
                }
                // Check verse lists (e.g., "5,6,7")
                if key.is_verse_list() && key.contains_verse(desired_v) {
                    return Ok(self.line_entries.slice(entry.start_index(), entry.next_start_index()));
                }
            }
        }

        Err(LookupError::CVNotFound(cv.clone()))
    }

    /// Get verse entries with context markers.
    ///
    /// Returns both the entries and the context markers that were active at that point.
    ///
    /// # Arguments
    ///
    /// * `cv` - The chapter:verse to look up
    /// * `strict` - If false, also search for verse ranges
    /// * `complete` - If true, include entries from verse 0 if getting verse 1
    pub fn get_verse_entries_with_context(
        &self,
        cv: &ChapterVerse,
        strict: bool,
        complete: bool,
    ) -> Result<(InternalBibleEntryList, Vec<CompactString>), LookupError> {
        if !self.indexed {
            return Err(LookupError::NotIndexed);
        }

        // Try direct lookup
        if let Some(entry) = self.index_data.get(cv) {
            let entries = self.line_entries.slice(entry.start_index(), entry.next_start_index());
            if have_strict_checking_flag() || cfg!(debug_assertions) {
                self.validate_entries_for_verse(cv, &entries);
            }
            let context = entry.context.clone();

            // If complete and verse is 1, prepend verse 0 entries
            if complete && cv.verse() == "1" {
                let cv0 = ChapterVerse::new(cv.chapter(), "0");
                if let Some(entry0) = self.index_data.get(&cv0) {
                    let mut combined = self.line_entries.slice(entry0.start_index(), entry0.next_start_index());
                    combined.extend(&entries);
                    return Ok((combined, context));
                }
            }

            return Ok((entries, context));
        }

        if strict {
            return Err(LookupError::CVNotFound(cv.clone()));
        }

        // Non-strict: search for ranges
        let desired_v = cv.verse_int().map_err(|_| LookupError::CVNotFound(cv.clone()))?;

        for (key, entry) in &self.index_data {
            if key.chapter() == cv.chapter() && key.contains_verse(desired_v) {
                let entries = self.line_entries.slice(entry.start_index(), entry.next_start_index());
                return Ok((entries, entry.context.clone()));
            }
        }

        Err(LookupError::CVNotFound(cv.clone()))
    }

    /// Get verse entries with context markers.
    ///
    /// Returns both the entries and the context markers that were active at that point.
    ///
    /// # Arguments
    ///
    /// * `cv` - The chapter:verse to look up
    /// * `strict` - If false, also search for verse ranges
    /// * `complete` - If true, include entries from verse 0 if getting verse 1
    pub fn validate_entries_for_verse(
        &self,
        cv: &ChapterVerse,
        verse_entries: &InternalBibleEntryList,
    ) {
        let requested_verse_num_str = cv.verse();

        if cv.chapter() == "-1" { // we're into the headers and introduction
            assert_eq!(verse_entries.len(), 1,
                "validate_entries_for_verse for {} {} {} expected a single entry but found {} from {}",
                self.work_name(), self.bos_book_code(), cv, verse_entries.len(), verse_entries);
        } else if cv.verse() != "0" { // we're into actual chapters and verses
            let mut found_verse_num_str = "";
            for line_entry in verse_entries {
                let marker = line_entry.marker();
                if marker == "v" {
                    let clean_text = line_entry.clean_text();
                    assert_eq!(clean_text, requested_verse_num_str,
                        "validate_entries_for_verse for {} {} {} found unexpected v = '{}' from {}",
                        self.work_name(), self.bos_book_code(), cv, clean_text, verse_entries);
                    found_verse_num_str = clean_text;
                } else if marker == "v~" {
                    if self.bos_book_code()=="PSA" && cv.verse()=="1" { // Then it could have a 'd' field
                        // !found_verse_num_str.is_empty(),                
                        log::warn!("validate_entries_for_verse {} {} {} has {}='{}' before the desired verse from {}",
                                self.work_name(), self.bos_book_code(), cv, marker, line_entry.clean_text(), verse_entries);
                    } else {
                        assert!(!found_verse_num_str.is_empty(),                
                            "validate_entries_for_verse {} {} {} has {}='{}' before the desired verse from {}",
                            self.work_name(), self.bos_book_code(), cv, marker, line_entry.clean_text(), verse_entries);
                    }
                }
            }
            assert_eq!(found_verse_num_str, requested_verse_num_str,
                "validate_entries_for_verse {} {} {} only found v = '{}' not '{}' from {}",
                self.work_name(), self.bos_book_code(), cv, found_verse_num_str, requested_verse_num_str, verse_entries);
            }
    }

    /// Get all entries for a chapter.
    ///
    /// # Errors
    ///
    /// Returns `LookupError::ChapterNotFound` if the chapter doesn't exist.
    pub fn get_chapter_entries(&self, chapter: &str) -> Result<InternalBibleEntryList, LookupError> {
        if !self.indexed {
            return Err(LookupError::NotIndexed);
        }

        let start_cv = ChapterVerse::new(chapter, "0");

        // Find the start of this chapter
        let start_entry = self
            .index_data
            .get(&start_cv)
            .ok_or_else(|| LookupError::ChapterNotFound(chapter.to_string()))?;

        // Find the start of the next chapter (or end of entries)
        let next_chapter = (chapter.parse::<i32>().unwrap_or(0) + 1).to_string();
        let next_cv = ChapterVerse::new(&next_chapter, "0");

        let end_index = self
            .index_data
            .get(&next_cv)
            .map(|e| e.start_index())
            .unwrap_or(self.line_entries.len());

        Ok(self.line_entries.slice(start_entry.start_index(), end_index))
    }

    /// Get the CV index entry for a specific reference.
    pub fn get_index_entry(&self, cv: &ChapterVerse) -> Option<&CVIndexEntry> {
        self.index_data.get(cv)
    }

    /// Get direct access to the underlying entries.
    #[inline]
    pub fn entries(&self) -> &InternalBibleEntryList {
        &self.line_entries
    }

    /// Get direct access to the underlying index data.
    #[inline]
    pub fn index_data(&self) -> &IndexMap<ChapterVerse, CVIndexEntry> {
        &self.index_data
    }

    /// Reconstruct from serialized data.
    pub fn from_serialized(
        work_name: impl Into<CompactString>,
        bos_book_code: impl Into<CompactString>,
        index_data: IndexMap<ChapterVerse, CVIndexEntry>,
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

    /// Build the CV index from processed entries.
    ///
    /// This analyzes the given entry list (processed USFM/ESFM lines) and creates the CV -> entry mapping.
    ///
    /// # Errors
    ///
    /// Returns `IndexError` if the entry structure is invalid.
    pub fn build(&mut self, line_entries: InternalBibleEntryList) -> Result<(), IndexError> {
        if line_entries.is_empty() {
            return Err(IndexError::EmptyEntries);
        }
        verbosity_println!(3, "  Building CV index for {} {} from {} processed line entries…", self.work_name(), self.bos_book_code(), line_entries.len());
        self.line_entries = line_entries;
        
        let mut current_chapter = CompactString::new("-1");
        let mut current_verse = CompactString::new("0");
        let mut current_start_line_index: usize = 0;
        let mut context: Vec<CompactString> = Vec::new();
        let mut current_context: Vec<CompactString> = Vec::new();
        let mut last_start_line_index = 0;
        let mut last_end_line_index = 0;
        
        self.index_data.clear();
        for (i, line_entry) in self.line_entries.iter().enumerate() {
            let mut next_chapter = current_chapter.clone();
            let mut next_verse = current_verse.clone();
            let mut is_cv_start = false;
            
            let marker = line_entry.marker();
            if have_strict_checking_flag() || cfg!(debug_assertions) {
                assert!(!marker.is_empty() && !marker.contains('\\'), "Entry marker should not be empty and should not contain a backslash: found '{}'", marker);
            }
            let next_marker = self.line_entries.get(i+1).and_then(|entry| Some(entry.marker())).unwrap_or_default();

            if marker == "c" {
                next_chapter = CompactString::from(line_entry.clean_text());
                next_verse = CompactString::from("0");
                is_cv_start = true;
            } else if marker == "v" { // || (marker == "v=" && !entry.clean_text().starts_with(next_verse.as_str()))
                let verse_num = line_entry.clean_text();
                // let verse_num = verse_text.split_whitespace().next().unwrap_or(verse_text);
                next_verse = CompactString::from(verse_num);
                is_cv_start = true;
            } else if current_chapter == "-1" {
                next_verse = CompactString::from(i.to_string());
                is_cv_start = true;
            } else if crate::bos_markers::paragraph_markers::is_paragraph(marker)
                || ["b","list","v="].contains(&marker)  // v= precedes s1, ms1, is1, etc.
                || crate::bos_markers::heading_markers::is_heading(marker)
                || crate::bos_markers::major_section_markers::is_major_section(marker)
            { // Any of the above could be (but not necessarily) preliminaries to a new verse
                // Look ahead for next verse to see if this structural marker starts it
                for j in (i + 1)..self.line_entries.len() {
                    let next_entry = &self.line_entries[j];
                    let next_m = next_entry.marker();
                    if next_m == "v" { // || (next_m == "v=" && !next_entry.clean_text().starts_with(current_verse.as_str()))
                        let verse_num = next_entry.clean_text();
                        // let verse_num = text.split_whitespace().next().unwrap_or(text);
                        // assert_ne!(verse_num, current_verse);
                        if verse_num != current_verse {
                            next_verse = CompactString::from(verse_num);
                            is_cv_start = true;
                        }
                        break;
                    }
                    if next_m == "c" || next_m == "¬v" {
                        break;
                    }
                }
            }

            if is_cv_start
            && (next_chapter != current_chapter || next_verse != current_verse)
            && !["ms1","ms2","ms3","mr"].contains(&next_marker) {
                // Finish previous CV
                let cv = ChapterVerse::new(current_chapter.as_str(), current_verse.as_str());
                let line_entry_count = (i - current_start_line_index) as u8;
                // // Double-check that all verse markers in this range have the same verse number (to catch any inconsistencies)
                // for entry in self.entries.slice(current_start, i) {
                //     if entry.marker() == "v" || entry.marker() == "v=" || entry.marker() == "¬v" {
                //         let verse_num = entry.clean_text();
                //         assert!(verse_num==current_verse.as_str(), "{} {} CV index entry for {} contains inconsistent verse marker with text {}='{}'",
                //             self.work_name(), self.bos_book_code(), cv, entry.marker(), verse_num);
                //     }
                // }
                let current_end_line_index = i - 1;
                verbosity_println!(4, "  At {} {}:{} with {}:{} '{}' then '{}' about to append CV entry {}: {} {}+{} [{}] with celi={} lsli={} leli={}",
                            i, current_chapter, current_verse, next_chapter, next_verse, marker, next_marker, self.index_data.len(), cv, current_start_line_index, line_entry_count, current_context.join(", "), current_end_line_index, last_start_line_index, last_end_line_index);
                if have_strict_checking_flag() || cfg!(debug_assertions) {
                    assert!(current_start_line_index > last_start_line_index || current_start_line_index==0,
                            "{} {} {}:{} CV index entry {} start is backwards: previous start was {}, now {} (+{}-1= {})",
                            self.work_name(), self.bos_book_code(), current_chapter, current_verse, self.index_data.len(),
                            last_start_line_index, current_start_line_index, line_entry_count, current_end_line_index);
                    assert!(current_start_line_index > last_end_line_index || current_start_line_index==0,
                            "{} {} {}:{} CV index entry {} start is wrong: finished at {}, now {}+{}-1= {}",
                            self.work_name(), self.bos_book_code(), current_chapter, current_verse, self.index_data.len(),
                            last_end_line_index, current_start_line_index, line_entry_count, current_end_line_index);
                    assert!(current_end_line_index > current_start_line_index || current_chapter == "-1" || current_verse == "0",
                            "{} {} {}:{} CV index entry {} end is wrong: finished at {}, now {}+{}-1= {}",
                            self.work_name(), self.bos_book_code(), current_chapter, current_verse, self.index_data.len(),
                            last_end_line_index, current_start_line_index, line_entry_count, current_end_line_index);
                    if current_chapter != "-1" && current_verse != "0" {
                        assert!(is_end_marker(self.line_entries.get(current_end_line_index).unwrap().marker())
                                || ["ms1","ms2","ms3","mr"].contains(&self.line_entries.get(current_end_line_index).unwrap().marker()),
                                    "{} {} {}:{} CV index entry expected to finish with an end marker, not '{}'",
                                    self.work_name(), self.bos_book_code(), current_chapter, current_verse,
                                    self.line_entries.get(current_end_line_index).unwrap().marker());
                    }
                }
                if have_strict_checking_flag() || cfg!(debug_assertions) {
                    assert!(!self.index_data.contains_key(&cv), "About to lose existing index entry for {}", cv);
                }
                self.index_data
                    .insert(cv, CVIndexEntry::new(current_start_line_index as u32, line_entry_count, current_context.clone()));
                last_start_line_index = current_start_line_index;
                last_end_line_index = current_end_line_index;

                current_chapter = next_chapter;
                current_verse = next_verse;
                current_start_line_index = i;
                current_context = context.clone();
            }

            // 2. Handle nesting markers - push onto context
            if is_nesting_marker(marker) && marker != "nb" { //  && !is_end_marker(marker)
                if crate::bos_markers::paragraph_markers::is_paragraph(marker) {
                    context.retain(|m| !crate::bos_markers::paragraph_markers::is_paragraph(m));
                }
                context.push(CompactString::from(marker));
            }

            // 3. Handle end markers - pop from context
            if is_end_marker(marker) {
                if let Some(base) = crate::bos_markers::base_of_end_marker(marker)
                    && let Some(pos) = context.iter().rposition(|m| m == base)
                {
                    context.remove(pos);
                }
            }
        }

        // Finish last CV
        let cv = ChapterVerse::new(current_chapter.as_str(), current_verse.as_str());
        let line_entry_count = (self.line_entries.len() - current_start_line_index) as u8;
        let current_end_line_index = current_start_line_index + line_entry_count as usize - 1;
        if have_strict_checking_flag() || cfg!(debug_assertions) {
            assert!(current_start_line_index > last_end_line_index || current_start_line_index==0,
                    "{} {} {}:{} final CV index entry start is wrong: finished at {}, now {}+{}-1= {}",
                    self.work_name(), self.bos_book_code(), current_chapter, current_verse,
                    last_end_line_index, current_start_line_index, line_entry_count, current_end_line_index);
            assert!(current_end_line_index > current_start_line_index || !is_chapter_verse_book(self.bos_book_code()),
                    "{} {} {}:{} final CV index entry end is wrong: finished at {}, now {}+{}-1= {}",
                    self.work_name(), self.bos_book_code(), current_chapter, current_verse,
                    last_end_line_index, current_start_line_index, line_entry_count, current_end_line_index);
            assert!(!self.index_data.contains_key(&cv), "At end, about to lose existing index entry for {}", cv);
            }
        self.index_data.insert(cv, CVIndexEntry::new(current_start_line_index as u32, line_entry_count, current_context));
        self.indexed = true;

        if have_strict_checking_flag() || cfg!(debug_assertions) {
             let validation_results = self.validate();
             if !validation_results.is_empty() {
                println!("Tried to build {} {} CV index from {} line entries:", self.work_name(), self.bos_book_code(), self.line_entries.len());
                for (j,line_entry) in self.line_entries.iter().enumerate() {
                    println!("  {}/ {} = \"{}\"", j, line_entry.marker(), line_entry.clean_text());
                }
                println!("Built {} {} CV index with {} entries from {} line entries:", self.work_name(), self.bos_book_code(), self.index_data.len(), self.line_entries.len());
                for (j,index_entry) in self.index_data.iter().enumerate() {
                    println!("  {}/ {} = {}", j, index_entry.0, index_entry.1);
                }
                panic!("{} {} CV index validation failed with {} issues: {:#?}", self.work_name, self.bos_book_code, validation_results.len(), validation_results);
            }
        }

        Ok(())
    }

    fn format_verse_result(&self, res: Result<InternalBibleEntryList, LookupError>) -> String {
        match res {
            Ok(entries) => format!("{}", entries),
            Err(e) => format!("{}", e),
        }
    }

    /// Validate the CV index structure.
    ///
    /// Returns a list of any issues found.
    fn validate(&self) -> Vec<String> {
        let mut issues = Vec::new();
        if !self.indexed {
            issues.push(format!("{} {} CV index has not been built", self.work_name, self.bos_book_code));
            return issues;
        }

        // Before checking the CV index, check for line entries with verse numbers which are not digits
        let mut additional_verse_number_characters: Vec<char> = ['0','1','2','3','4','5','6','7','8','9'].to_vec(); // it's convenient to start with the digits
        let (mut c_str, mut v_str) = ("-1", "0");
        for (j,line_entry) in self.line_entries.iter().enumerate() {
            let marker = line_entry.marker();
            if marker == "c" {
                c_str = line_entry.clean_text();
            } else if marker == "v" {
                let this_v_text = line_entry.clean_text();
                if !this_v_text.chars().all(|c| c.is_ascii_digit()) {
                    log::debug!("  {} {} after {} {}:{} Found non-digits in verse number v = '{}'", self.work_name(), self.bos_book_code(), j, c_str, v_str, this_v_text);
                    for extra_char in this_v_text.chars() {
                        if !additional_verse_number_characters.contains(&extra_char) {
                            additional_verse_number_characters.push(extra_char);
                        }
                    }
                }
                v_str = this_v_text;
            }
        }
        if additional_verse_number_characters.len() > 10 {
            let extra_chars: String = additional_verse_number_characters.iter().skip(10).collect();
            log::info!("In the {} {} book, verse numbers can contain the following extra characters: {:?}",
                self.work_name(), self.bos_book_code(), extra_chars);
        }

        // Check for overlapping entries,
        //  for entries containing incorrect verse numbers,
        //  and that the last line in an index segment is an end marker
        let mut last_end_index: usize = 0;
        for (cv, entry) in &self.index_data {
            if have_strict_checking_flag() || cfg!(debug_assertions) {
                assert!(!cv.chapter().is_empty() && (cv.chapter().chars().all(|c| c.is_ascii_digit()) || cv.chapter() == "-1"),
                    "{} {} chapter should be a non-empty string of digits or '-1': found '{}' from {}",
                    self.work_name, self.bos_book_code, cv.chapter(), cv);
                assert!(!cv.verse().is_empty() && cv.verse().chars().all(|c| c.is_ascii_digit() || additional_verse_number_characters.contains(&c)),
                    "{} {} verse should be a non-empty string of digits (or a verse bridge): found '{}' from {}",
                    self.work_name, self.bos_book_code, cv.verse(), cv);
            }
            
            if entry.start_index() < last_end_index {
                issues.push(format!("{} {} {}: start_index {} < previous end {}",
                    self.work_name(), self.bos_book_code(), cv, entry.start_index(), last_end_index));
            }

            let verse_entries = self.line_entries.slice(entry.start_index(), entry.next_start_index());
            self.validate_entries_for_verse(cv, &verse_entries);

            if cv.chapter() != "-1"  {
                for processed_line_entry in &verse_entries {
                    if (have_strict_checking_flag() || cfg!(debug_assertions))
                    && (processed_line_entry.marker() == "v" || processed_line_entry.marker() == "¬v") {
                        assert!(processed_line_entry.clean_text().starts_with(cv.verse().to_string().as_str()), "Validating {} {} CV index entry for {} found unexpected verse marker with text {}='{}'\n\n{}:{} {}\n\n{} {}\n\n{}:{} {}",
                            self.work_name(), self.bos_book_code(), cv, processed_line_entry.marker(),processed_line_entry.clean_text(),
                            cv.chapter(), cv.verse_int().unwrap_or(1)-1, self.format_verse_result(self.get_verse_entries(&ChapterVerse::new(cv.chapter(), (cv.verse_int().unwrap_or(1) - 1).to_string().as_str()), true)),
                            cv, self.format_verse_result(self.get_verse_entries(cv, true)),
                            cv.chapter(), cv.verse_int().unwrap_or(1)+1, self.format_verse_result(self.get_verse_entries(&ChapterVerse::new(cv.chapter(), (cv.verse_int().unwrap_or(1) + 1).to_string().as_str()), true)));
                        }
                    }
                
                let final_marker_in_entry = self.line_entries.get(entry.start_index() + entry.entry_count() as usize - 1).map(|e| e.marker()).unwrap_or("N/A");
                if !is_end_marker(final_marker_in_entry) && cv.verse() != "0"
                    && !["ms1","ms2","ms3","mr"].contains(&final_marker_in_entry)
                 {
                    // println!("Entry for {} {} {} is at index {} with end marker '{}'", self.work_name(), self.bos_book_code(), cv, entry.start_index(), final_marker_in_entry);
                    // assert!(cv.verse()=="0" || is_end_marker(final_marker_in_entry),
                    //     "Validating {} {} CV index entry for {} expected last entry to be an end marker but found marker '{}'",
                    //     self.work_name(), self.bos_book_code(), cv, final_marker_in_entry);
                    issues.push(format!(
                        "{} {} CV index entry for {} expected last entry to be an end marker but found marker '{}' from {}",
                        self.work_name(), self.bos_book_code(), cv, final_marker_in_entry, verse_entries,
                    ));
                    }
                }
            last_end_index = entry.next_start_index();
        }

        // Check that all entries are covered
        if last_end_index != self.line_entries.len() {
            issues.push(format!(
                "{} {} CV index covers {} entries but list has {}",
                self.work_name(), self.bos_book_code(), last_end_index, self.line_entries.len()));
        }

        issues
    }
}

/// Check if a marker is a nesting marker that affects context.
fn is_nesting_marker(marker: &str) -> bool {
    regular_nesting::ALL.contains(&marker)
        || custom_nesting::is_custom_nesting(marker)
        || crate::bos_markers::paragraph_markers::is_paragraph(marker)
        || crate::bos_markers::major_section_markers::ALL.contains(&marker)
}

impl std::fmt::Display for InternalBibleBookCVIndex {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        writeln!(
            f,
            "InternalBibleBookCVIndex({} {}):",
            self.work_name, self.bos_book_code
        )?;
        if !self.indexed {
            writeln!(f, "  Not indexed")?;
        } else if self.index_data.is_empty() {
            writeln!(f, "  Empty")?;
        } else {
            writeln!(f, "  {} CV entries", self.index_data.len())?;
            for (i, (cv, entry)) in self.index_data.iter().enumerate() {
                if i >= 75 || (!cfg!(debug_assertions) && i >= 25) {
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
    use std::fs;
    use crate::set_strict_checking_flag;
    use crate::entry::InternalBibleEntry;
    use crate::ProcessLinesOptions;
    use crate::process_lines;

    fn create_test_entries_1() -> InternalBibleEntryList {
        let mut entries = InternalBibleEntryList::new();

        // Introduction
        entries.push(InternalBibleEntry::nesting_marker("intro")); // 0
        entries.push(InternalBibleEntry::simple("ip", "Introduction...")); // 1
        entries.push(InternalBibleEntry::simple("ie", "")); // 2
        entries.push(InternalBibleEntry::end_marker("¬intro", "").expect("Fail")); // 3

        // Chapter 1
        entries.push(InternalBibleEntry::nesting_marker("chapters")); // 4
        entries.push(InternalBibleEntry::simple("c", "1")); // 5
        entries.push(InternalBibleEntry::simple("s1", "Creation")); // 6
        entries.push(InternalBibleEntry::simple("p", "")); // 7
        entries.push(InternalBibleEntry::simple("v", "1")); // 8
        entries.push(InternalBibleEntry::simple("v~", "In the beginning...")); // 9
        entries.push(InternalBibleEntry::end_marker("¬v", "1").expect("Fail")); // 10
        entries.push(InternalBibleEntry::simple("v", "2")); // 11
        entries.push(InternalBibleEntry::simple("v~", "And the earth was...")); // 12
        entries.push(InternalBibleEntry::end_marker("¬v", "2").expect("Fail")); // 13
        entries.push(InternalBibleEntry::simple("p", "")); // 14
        entries.push(InternalBibleEntry::simple("v", "3")); // 15
        entries.push(InternalBibleEntry::simple("v~", "And the spirit...")); // 16
        entries.push(InternalBibleEntry::end_marker("¬v", "3").expect("Fail")); // 17
        entries.push(InternalBibleEntry::end_marker("¬p", "").expect("Fail")); // 18
        entries.push(InternalBibleEntry::end_marker("¬c", "1").expect("Fail")); // 19

        // Chapter 2
        entries.push(InternalBibleEntry::simple("c", "2")); // 20
        entries.push(InternalBibleEntry::simple("v", "1")); // 21
        entries.push(InternalBibleEntry::simple("v~", "Thus the heavens...")); // 22
        entries.push(InternalBibleEntry::end_marker("¬v", "1").expect("Fail")); // 23
        entries.push(InternalBibleEntry::end_marker("¬c", "2").expect("Fail")); // 24
        entries.push(InternalBibleEntry::end_marker("¬chapters", "").expect("Fail")); // 25

        entries
    }

    #[test]
    fn test_build_index_1() {
        set_strict_checking_flag( true );
        let mut cv_index = InternalBibleBookCVIndex::new("ESV", "GEN");
        let entries = create_test_entries_1();

        cv_index.build(entries).unwrap();
        log::trace!("CV index: {}", cv_index);
        assert!(cv_index.is_indexed());

        assert!(cv_index.contains(&ChapterVerse::new("-1", "0")));
        assert!(cv_index.contains(&ChapterVerse::new("-1", "1")));
        assert!(cv_index.contains(&ChapterVerse::new("1", "0")));
        assert!(cv_index.contains(&ChapterVerse::new("1", "1")));
        assert!(cv_index.contains(&ChapterVerse::new("1", "2")));
        assert!(cv_index.contains(&ChapterVerse::new("1", "3")));
        assert!(cv_index.contains(&ChapterVerse::new("2", "0")));
        assert!(cv_index.contains(&ChapterVerse::new("2", "1")));

        // Intro
        assert_eq!(cv_index.get_index_entry(&ChapterVerse::new("-1", "0")).unwrap().start_index(), 0);
        assert_eq!(cv_index.get_index_entry(&ChapterVerse::new("-1", "0")).unwrap().entry_count(), 1);
        assert_eq!(cv_index.get_index_entry(&ChapterVerse::new("-1", "1")).unwrap().start_index(), 1);
        assert_eq!(cv_index.get_index_entry(&ChapterVerse::new("-1", "1")).unwrap().entry_count(), 1);

        // 1:0
        assert_eq!(cv_index.get_index_entry(&ChapterVerse::new("1", "0")).unwrap().start_index(), 5);
        assert_eq!(cv_index.get_index_entry(&ChapterVerse::new("1", "0")).unwrap().entry_count(), 1);
        assert_eq!(cv_index.get_index_entry(&ChapterVerse::new("1", "0")).unwrap().context(), ["chapters"]);

        // 1:1
        assert_eq!(cv_index.get_index_entry(&ChapterVerse::new("1", "1")).unwrap().start_index(), 6);
        assert_eq!(cv_index.get_index_entry(&ChapterVerse::new("1", "1")).unwrap().entry_count(), 5);

        // 2:0
        assert_eq!(cv_index.get_index_entry(&ChapterVerse::new("2", "0")).unwrap().start_index(), 20);
        assert_eq!(cv_index.get_index_entry(&ChapterVerse::new("2", "0")).unwrap().entry_count(), 1);

        assert!(cv_index.len() == 11);
    }

    fn create_test_entries_2() -> InternalBibleEntryList {
        let mut entries = InternalBibleEntryList::new();

        entries.push(InternalBibleEntry::simple("id", "SA2")); // 0
        entries.push(InternalBibleEntry::nesting_marker("chapters")); // 1

        // Chapter 6
        entries.push(InternalBibleEntry::simple("c", "6")); // 2
        entries.push(InternalBibleEntry::simple("v", "1")); // 3
        entries.push(InternalBibleEntry::simple("v~", "Forsothe Dauid gaderide eft alle the chosun men of Israel, thritti thousynde.")); // 4
        entries.push(InternalBibleEntry::end_marker("¬v", "1").expect("Fail")); // 5
        entries.push(InternalBibleEntry::simple("v", "2")); // 6
        entries.push(InternalBibleEntry::simple("v~", "And Dauid roos, and yede, and al the puple that was with hym of the men of Juda, to brynge the arke of God, on which the name of the Lord of oostis, sittynge in cherubyn on that arke, was clepid.")); // 7
        entries.push(InternalBibleEntry::end_marker("¬v", "2").expect("Fail")); // 8
        entries.push(InternalBibleEntry::simple("v", "3")); // 9
        entries.push(InternalBibleEntry::simple("v~", "And thei puttiden the arke of God on a newe wayn, and thei token it fro the hows of Amynadab, that was in Gabaa. Forsothe Oza and Haio, the sons of Amynadab, dryueden the newe wayn.")); // 10
        entries.push(InternalBibleEntry::end_marker("¬v", "3").expect("Fail")); // 11
        entries.push(InternalBibleEntry::simple("v", "4")); // 12
        entries.push(InternalBibleEntry::simple("v~", "And whanne thei hadden take it fro the hows of Amynadab, that was in Gabaa, and kepte the arke of God, Haio yede bifor the arke.")); // 13
        entries.push(InternalBibleEntry::end_marker("¬v", "4").expect("Fail")); // 14
        entries.push(InternalBibleEntry::end_marker("¬c", "6").expect("Fail")); // 15

        entries
    }

    #[test]
    fn test_build_index_2() {
        set_strict_checking_flag( true );
        let mut cv_index = InternalBibleBookCVIndex::new("ESV", "GEN");
        let entries = create_test_entries_2();

        cv_index.build(entries).unwrap();
        log::trace!("CV index: {}", cv_index);
        assert!(cv_index.is_indexed());

        // 6:1
        assert_eq!(cv_index.get_index_entry(&ChapterVerse::new("6", "1")).unwrap().start_index(), 3);
        assert_eq!(cv_index.get_index_entry(&ChapterVerse::new("6", "1")).unwrap().entry_count(), 3);

        // 6:2
        assert_eq!(cv_index.get_index_entry(&ChapterVerse::new("6", "2")).unwrap().start_index(), 6);
        assert_eq!(cv_index.get_index_entry(&ChapterVerse::new("6", "2")).unwrap().entry_count(), 3);

        // 6:3
        assert_eq!(cv_index.get_index_entry(&ChapterVerse::new("6", "3")).unwrap().start_index(), 9);
        assert_eq!(cv_index.get_index_entry(&ChapterVerse::new("6", "3")).unwrap().entry_count(), 3);

        // 6:4
        assert_eq!(cv_index.get_index_entry(&ChapterVerse::new("6", "4")).unwrap().start_index(), 12);
        assert_eq!(cv_index.get_index_entry(&ChapterVerse::new("6", "4")).unwrap().entry_count(), 4);

        assert_eq!(cv_index.len(), 7);
    }

    #[test]
    fn test_get_verse_entries() {
        set_strict_checking_flag( true );
        let mut cv_index = InternalBibleBookCVIndex::new("ESV", "GEN");
        cv_index.build(create_test_entries_1()).unwrap();

        let entries = cv_index.get_verse_entries(&ChapterVerse::new("1", "1"), true).unwrap();
        assert!(!entries.is_empty());
        // With the new logic, the first entry for 1:1 is the section marker 's1'
        assert_eq!(entries[0].marker(), "s1");
    }

    #[test]
    fn test_get_chapter_entries() {
        set_strict_checking_flag( true );
        let mut cv_index = InternalBibleBookCVIndex::new("ESV", "GEN");
        cv_index.build(create_test_entries_1()).unwrap();

        let entries = cv_index.get_chapter_entries("1").unwrap();
        log::trace!("Chapter entries:{}", entries);
        assert!(!entries.is_empty());
        // Chapter 1 should have: c, s1, p, v, v~, ¬v, v, v~, ¬v, p, v, v~, ¬v, ¬p, ¬c = 15 entries
        assert_eq!(entries.len(), 15);
    }
    #[test]
    fn test_chapters() {
        set_strict_checking_flag( true );
        let mut cv_index = InternalBibleBookCVIndex::new("ESV", "GEN");
        cv_index.build(create_test_entries_1()).unwrap();

        let chapters = cv_index.chapters();
        assert!(chapters.contains(&"1"));
        assert!(chapters.contains(&"2"));
    }

    #[test]
    fn test_not_indexed_error() {
        set_strict_checking_flag( true );
        let index = InternalBibleBookCVIndex::new("ESV", "GEN");
        let result = index.get_verse_entries(&ChapterVerse::new("1", "1"), true);
        assert!(matches!(result, Err(LookupError::NotIndexed)));
    }

    #[test]
    fn test_oet_lv_haggai_cv_index_build() {
        set_strict_checking_flag( true );
        let content = include_str!("../../../../Tests/DataFilesForTests/OET-LV/OET-LV_HAG.ESFM");
        let mut raw_lines = Vec::new();
        for line in content.lines() {
            let (marker, text) = match line.split_once(' ') {
                Some((m, t)) => (m, t),
                None => (line, ""),
            };
            let marker = marker.strip_prefix('\\').unwrap_or(marker);
            raw_lines.push((marker.to_string(), text.to_string()));
        }

        let options = ProcessLinesOptions::default();
        let processed_line_entries = process_lines(raw_lines, "HAG", "OET-RV", &options);

        let mut cv_index = InternalBibleBookCVIndex::new("OET-RV", "HAG");
        cv_index.build(processed_line_entries).unwrap();

        // It should give 58 entries (as per ../../test_data/OET-LV_HAG_CVs.txt):
        assert_eq!(cv_index.len(), 58);

        // 0 -1:0 Headers='HAG'
        let (cv0, entry0) = cv_index.index_data.get_index(0).unwrap();
        assert_eq!(cv0.to_string(), "-1:0");
        assert_eq!(entry0.context(), Vec::<CompactString>::new());
        assert_eq!(entry0.start_index(), 0);
        assert_eq!(entry0.entry_count(), 1);
        assert_eq!(cv_index.line_entries[entry0.start_index()].marker(), "id");

        // 10 -1:10 ctxt=['headers']
        let (cv10, entry10) = cv_index.index_data.get_index(10).unwrap();
        assert_eq!(cv10.to_string(), "-1:10");
        assert_eq!(entry10.context(), ["headers"]);
        assert_eq!(entry10.start_index(), 10);
        assert_eq!(entry10.entry_count(), 1);
        assert_eq!(cv_index.line_entries[entry10.start_index()].marker(), "h");

        // 15 -1:15 ctxt=['headers']
        let (cv15, entry15) = cv_index.index_data.get_index(15).unwrap();
        assert_eq!(cv15.to_string(), "-1:15");
        assert_eq!(entry15.context(), ["headers"]);
        assert_eq!(entry15.start_index(), 15);
        assert_eq!(entry15.entry_count(), 1);
        assert_eq!(cv_index.line_entries[entry15.start_index()].marker(), "ie");

        // 16 -1:16 ctxt=['headers']
        let (cv16, entry16) = cv_index.index_data.get_index(16).unwrap();
        assert_eq!(cv16.to_string(), "-1:16");
        assert_eq!(entry16.context(), ["headers"]);
        assert_eq!(entry16.start_index(), 16);
        assert_eq!(entry16.entry_count(), 1);
        assert_eq!(cv_index.line_entries[entry16.start_index()].marker(), "¬headers");

        // 17 -1:17 ctxt=['headers']
        let (cv17, entry17) = cv_index.index_data.get_index(17).unwrap();
        assert_eq!(cv17.to_string(), "-1:17");
        assert_eq!(entry17.context(), Vec::<CompactString>::new());
        assert_eq!(entry17.start_index(), 17);
        assert_eq!(entry17.entry_count(), 1);
        assert_eq!(cv_index.line_entries[entry17.start_index()].marker(), "chapters");

        // 18 1:0 ctxt=['chapters']
        let (cv18, entry18) = cv_index.index_data.get_index(18).unwrap();
        assert_eq!(cv18.to_string(), "1:0");
        assert_eq!(entry18.context(), ["chapters"]);
        assert_eq!(entry18.start_index(), 18);
        assert_eq!(entry18.entry_count(), 1);

        // 19 1:1 ctxt=['chapters', 'c']
        let (cv19, entry19) = cv_index.index_data.get_index(19).unwrap();
        assert_eq!(cv19.to_string(), "1:1");
        assert_eq!(entry19.context(), ["chapters", "c"]);
        assert_eq!(entry19.start_index(), 19);
        assert_eq!(entry19.entry_count(), 5);
        assert_eq!(cv_index.line_entries[entry19.start_index()+entry19.entry_count() as usize-1].marker(), "¬v");

        // 20 1:2 ctxt=['chapters', 'c']
        let (cv20, entry20) = cv_index.index_data.get_index(20).unwrap();
        assert_eq!(cv20.to_string(), "1:2");
        assert_eq!(entry20.context(), ["chapters", "c"]);
        assert_eq!(entry20.start_index(), 24);
        assert_eq!(entry20.entry_count(), 3);

        // 33 1:15 ctxt=['chapters', 'c']
        let (cv33, entry33) = cv_index.index_data.get_index(33).unwrap();
        assert_eq!(cv33.to_string(), "1:15");
        assert_eq!(entry33.context(), ["chapters", "c"]);
        assert_eq!(entry33.start_index(), 63);
        assert_eq!(entry33.entry_count(), 4);

        // 34 2:0 ctxt=['chapters']
        let (cv34, entry34) = cv_index.index_data.get_index(34).unwrap();
        assert_eq!(cv34.to_string(), "2:0");
        assert_eq!(entry34.context(), ["chapters"]);
        assert_eq!(entry34.start_index(), 67);
        assert_eq!(entry34.entry_count(), 1);

        // 35 2:1 ctxt=['chapters', 'c']
        let (cv35, entry35) = cv_index.index_data.get_index(35).unwrap();
        assert_eq!(cv35.to_string(), "2:1");
        assert_eq!(entry35.context(), ["chapters", "c"]);
        assert_eq!(entry35.start_index(), 68);
        assert_eq!(entry35.entry_count(), 5);

        // 36 2:2 ctxt=['chapters', 'c']
        let (cv36, entry36) = cv_index.index_data.get_index(36).unwrap();
        assert_eq!(cv36.to_string(), "2:2");
        assert_eq!(entry36.context(), ["chapters", "c"]);
        assert_eq!(entry36.start_index(), 73);
        assert_eq!(entry36.entry_count(), 3);

        // 57 2:23 ctxt=['chapters', 'c']
        let (cv57, entry57) = cv_index.index_data.get_index(57).unwrap();
        assert_eq!(cv57.to_string(), "2:23");
        assert_eq!(entry57.context(), ["chapters", "c"]);
        assert_eq!(entry57.start_index(), 136);
        assert_eq!(entry57.entry_count(), 5);
    }

    #[test]
    fn test_oet_rv_haggai_cv_index_build() {
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

        let options = ProcessLinesOptions::default();
        let processed_line_entries = process_lines(raw_lines, "HAG", "OET-RV", &options);
        // println!("OET-RV HAG Processed lines markers = {}", processed_line_entries.iter().map(|e| e.marker()).collect::<Vec<_>>().join(", "));

        // println!("OET-RV HAG {} processed_line_entries = {}", processed_line_entries.len(), processed_line_entries);
        //     OET-RV HAG processed_line_entries = InternalBibleEntryList:
        //         0/ id = "HAG - Open English Translation…ders' Version (OET-RV) v0.1.03"
        //         1/ usfm = "3.0"
        //         2/ ide = "UTF-8"
        //         3/ rem = "ESFM v0.6 HAG"
        //         4/ rem = "WORDTABLE OET-LV_OT_word_table.tsv"
        //         5/ headers = ""
        //         6/ h = "Haggai"
        //         7/ toc1 = "Haggai"
        //         8/ toc2 = "Haggai"
        //         9/ toc3 = "Hag."
        //         10/ mt1 = "Haggai"
        //         11/ ¬headers = ""
        //         12/ intro = ""
        //         13/ is1 = "Introduction"
        //         14/ ip = "This document contains a numbe… bless their living situation."
        //         15/ iot = "Main components of this account"
        //         16/ io1 = "God's command to rebuild the temple 1:1-15"
        //         17/ io1 = "Stories of comfort and hope 2:1-23"
        //         18/ ¬iot = ""
        //         19/ rem = "This is still a very early loo…dvance before using in public."
        //         20/ ¬is1 = "20"
        //         21/ ie = ""
        //         22/ ¬intro = ""
        //         23/ chapters = ""
        //         24/ c = "1"
        //         25/ v= = "1"
        //         26/ s1 = "God's command to rebuild the temple"
        //         27/ rem = "/s1 The Lord's Command to Rebu… Command to Rebuild the Temple"
        //         28/ p = ""
        //         29/ c# = "1"
        //         30/ v = "1"
        //         31/ v~ = "In Dareyavesh's (Darius's¦3755…375591 son), telling them that" + extras
        //         32/ ¬v = "1"
        //         33/ v = "2"
        //         34/ v~ = "Commander-in-chief Yahweh says…2 Yahweh's¦375598 ≈residence.”"
        //         35/ ¬v = "2"
        //         36/ ¬p = ""
        //         37/ p = ""
        //         38/ v = "3"
        //         39/ v~ = "Then Yahweh¦375618 ≈gave this …gai¦375621 to tell the people:"
        //         40/ ¬v = "3"
        //         41/ ¬p = ""
        //         42/ m = ""
        //         43/ v = "4"
        //         44/ v~ = "Is it a time¦375625 for all of…Yahweh's temple lies in ruins?"
        //         45/ ¬v = "4"
        //         46/ v = "5"
        //         47/ v~ = "≈So¦375635 now Commander-in-ch…e what you're all going to do."
        //         48/ ¬v = "5"
        //         49/ v = "6"
        //         50/ v~ = "You've all planted a lot, ≈but…ets seem to be full of holes.”"
        //         51/ ¬v = "6"
        //         52/ ¬m = ""
        //         53/ p = ""
        //         54/ v = "7"
        //         55/ v~ = "≈So Commander-in-chief Yahweh¦…e what you're all going to do."
        //         56/ ¬v = "7"
        //         57/ v = "8"
        //         58/ v~ = "Go up into the hills¦375682 an…e,” says¦375692 Yahweh¦375693."
        //         59/ ¬v = "8"
        //         60/ ¬p = ""
        //         61/ p = ""
        //         62/ v = "9"
        //         63/ v~ = "“You ≈expected much, but¦37569…y ≈working on your own houses."
        //         64/ ¬v = "9"
        //         65/ v = "10"
        //         66/ v~ = "That's why the sky withholds t…il withholds its¦375733 crops."
        //         67/ ¬v = "10"
        //         68/ v = "11"
        //         69/ v~ = "I've¦375735 ≈summoned¦375735 a… onto ≈everything you all do.”"
        //         70/ ¬v = "11"
        //         71/ ¬p = ""
        //         72/ ¬s1 = ""
        //         73/ v= = "12"
        //         74/ s1 = "The people start rebuilding"
        //         75/ rem = "/s1 The People Obey the Lord's…mmand; Obedience to God's Call"
        //         76/ p = ""
        //         77/ v = "12"
        //         78/ v~ = "Then Shealtiyel's son Zerubave… the people ≈respected Yahweh."
        //         79/ ¬v = "12"
        //         80/ v = "13"
        //         81/ v~ = "Then¦375802 Yahweh's¦375805 me…m with¦375806 you¦375811 all.”"
        //         82/ ¬v = "13"
        //         83/ v = "14"
        //         84/ v~ = "Then¦375816 Yahweh ≈inspired S…49, Commander-in-chief Yahweh,"
        //         85/ ¬v = "14"
        //         86/ v = "15"
        //         87/ v~ = "on¦375856 the twenty-fourth da…esh the king¦375860 of Persia."
        //         88/ ¬v = "15"
        //         89/ ¬p = ""
        //         90/ ¬s1 = "1"
        //         91/ ¬c = "1"
        //         92/ c = "2"
        //         93/ v= = "1"
        //         94/ s1 = "The splendour of the new temple"
        //         95/ rem = "/s1 The Future Glory of the Te…romised Glory of the New House"
        //         96/ p = ""
        //         97/ c# = "2"
        //         98/ v = "1"
        //         99/ v~ = "On the 21st of the seventh¦375… prophet¦375873 Haggai¦375872:"
        //         100/ ¬v = "1"
        //         101/ v = "2"
        //         102/ v~ = "Please ≈ask Shealtiyel's son Z…the rest of the people¦375898,"
        //         103/ ¬v = "2"
        //         104/ v = "3"
        //         105/ v~ = "“≈Are there any of you still a…g¦375919 in¦375902 comparison." + extras
        //         106/ ¬v = "3"
        //         107/ v = "4"
        //         108/ v~ = "Yahweh is telling you now, Zer… with you ≈as you work¦375944."
        //         109/ ¬v = "4"
        //         110/ v = "5"
        //         111/ v~ = "≈That's what I promised¦375955…Don't¦375965 be afraid¦375967," + extras
        //         112/ ¬v = "5"
        //         113/ v = "6"
        //         114/ v~ = "because¦375970 Commander-in-ch…9 and the dry land, once more." + extras
        //         115/ ¬v = "6"
        //         116/ v = "7"
        //         117/ v~ = "I'll shake¦375994 all the nati…mander-in-chief Yahweh¦376012."
        //         118/ ¬v = "7"
        //         119/ v = "8"
        //         120/ v~ = "Commander-in-chief Yahweh¦3760…er¦376016 belong¦376017 to me."
        //         121/ ¬v = "8"
        //         122/ v = "9"
        //         123/ v~ = "*I declare that this ≈temple w…sperity to this place¦376035.”"
        //         124/ ¬v = "9"
        //         125/ ¬p = ""
        //         126/ ¬s1 = ""
        //         127/ v= = "10"
        //         128/ s1 = "Haggai consults the priests"
        //         129/ rem = "/s1 Blessings Promised for Obe…e Prophet Consults the Priests"
        //         130/ p = ""
        //         131/ v = "10"
        //         132/ v~ = "On the 24th of the ninth¦37604… prophet¦376057 Haggai¦376056:"
        //         133/ ¬v = "10"
        //         134/ v = "11"
        //         135/ v~ = "Commander-in-chief Yahweh¦3760…Mosheh's ≈instructions¦376070."
        //         136/ ¬v = "11"
        //         137/ v = "12"
        //         138/ v~ = "‘≈If a priest took some meat¦3…r food  become¦376102 holy?’ ”"
        //         139/ ¬p = ""
        //         140/ p = ""
        //         141/ v~ = "“No, it wouldn't,” the priests¦376104 ≈replied."
        //         142/ ¬p = ""
        //         143/ ¬v = "12"
        //         144/ p = ""
        //         145/ v = "13"
        //         146/ v~ = "Then¦376108 Haggai¦376109 aske…ood, would it become unclean?”" + extras
        //         147/ ¬p = ""
        //         148/ p = ""
        //         149/ v~ = "“Yes, it would become unclean,…riests¦376121 answered¦376120."
        //         150/ ¬p = ""
        //         151/ ¬v = "13"
        //         152/ p = ""
        //         153/ v = "14"
        //         154/ v~ = "“≈That's what Yahweh¦376139 de…t transfers to your offerings."
        //         155/ rem = "/s1 The Lord Promises His Blessing"
        //         156/ ¬v = "14"
        //         157/ v = "15"
        //         158/ v~ = "So¦376151 now think back to be…id for Yahweh's¦376169 temple."
        //         159/ ¬v = "15"
        //         160/ v = "16"
        //         161/ v~ = "≈During that time, when someon…re was only enough for twenty."
        //         162/ ¬v = "16"
        //         163/ v = "17"
        //         164/ v~ = "Yahweh¦376205 declares that he…ill didn't¦376199 turn to him."
        //         165/ ¬v = "17"
        //         166/ v = "18"
        //         167/ v~ = "Think back to the time from wh… month¦376219). Consider that."
        //         168/ ¬v = "18"
        //         169/ v = "19"
        //         170/ v~ = "Is any grain left in¦376234 th…bless you from today onwards.”"
        //         171/ ¬v = "19"
        //         172/ ¬p = ""
        //         173/ ¬s1 = ""
        //         174/ v= = "20"
        //         175/ s1 = "God's promise to Zerubavel"
        //         176/ rem = "/s1 The Lord's Promise to Zeru…ubbabel the Lord's Signet Ring"
        //         177/ p = ""
        //         178/ v = "20"
        //         179/ v~ = "Then Yahweh¦376254 gave a seco…gai¦376259 on¦376260 the 24th:"
        //         180/ ¬v = "20"
        //         181/ v = "21"
        //         182/ v~ = "Tell Zerubavel, the governor¦3…s¦376277 and the earth¦376280."
        //         183/ ¬v = "21"
        //         184/ v = "22"
        //         185/ v~ = "I'll overthrow the thrones¦376… ≈will kill¦376285 each other."
        //         186/ ¬v = "22"
        //         187/ v = "23"
        //         188/ v~ = "Commander-in-chief Yahweh decl…6316 he's been chosen¦376319.”"
        //         189/ ¬v = "23"
        //         190/ ¬p = ""
        //         191/ ¬s1 = ""
        //         192/ ¬c = "2"
        //         193/ ¬chapters = ""

        let mut cv_index = InternalBibleBookCVIndex::new("OET-RV", "HAG");
        cv_index.build(processed_line_entries).unwrap();

        // println!("OET-RV HAG {} cv index_entries = {}", cv_index.len(), cv_index);
        //     OET-RV HAG cv index_entries = InternalBibleBookCVIndex(OET-RV HAG):
        //     64 CV entries
        //     -1:0: CVIndexEntry(idx=0, count=1, ctx=[])
        //     -1:1: CVIndexEntry(idx=1, count=1, ctx=[])
        //     -1:2: CVIndexEntry(idx=2, count=1, ctx=[])
        //     -1:3: CVIndexEntry(idx=3, count=1, ctx=[])
        //     -1:4: CVIndexEntry(idx=4, count=1, ctx=[])
        //     -1:5: CVIndexEntry(idx=5, count=1, ctx=[])
        //     -1:6: CVIndexEntry(idx=6, count=1, ctx=["headers"])
        //     -1:7: CVIndexEntry(idx=7, count=1, ctx=["headers"])
        //     -1:8: CVIndexEntry(idx=8, count=1, ctx=["headers"])
        //     -1:9: CVIndexEntry(idx=9, count=1, ctx=["headers"])
        //     -1:10: CVIndexEntry(idx=10, count=1, ctx=["headers"])
        //     -1:11: CVIndexEntry(idx=11, count=1, ctx=["headers"])
        //     -1:12: CVIndexEntry(idx=12, count=1, ctx=[])
        //     -1:13: CVIndexEntry(idx=13, count=1, ctx=["intro"])
        //     -1:14: CVIndexEntry(idx=14, count=1, ctx=["intro"])
        //     -1:15: CVIndexEntry(idx=15, count=1, ctx=["intro"])
        //     -1:16: CVIndexEntry(idx=16, count=1, ctx=["intro", "iot"])
        //     -1:17: CVIndexEntry(idx=17, count=1, ctx=["intro", "iot"])
        //     -1:18: CVIndexEntry(idx=18, count=1, ctx=["intro", "iot"])
        //     -1:19: CVIndexEntry(idx=19, count=1, ctx=["intro"])
        //     -1:20: CVIndexEntry(idx=20, count=1, ctx=["intro"])
        //     -1:21: CVIndexEntry(idx=21, count=1, ctx=["intro"])
        //     -1:22: CVIndexEntry(idx=22, count=1, ctx=["intro"])
        //     -1:23: CVIndexEntry(idx=23, count=1, ctx=[])
        //     1:0: CVIndexEntry(idx=24, count=1, ctx=["chapters"])
        //     1:1: CVIndexEntry(idx=25, count=8, ctx=["chapters", "c"])
        //     1:2: CVIndexEntry(idx=33, count=4, ctx=["chapters", "c", "p"])
        //     1:3: CVIndexEntry(idx=37, count=5, ctx=["chapters", "c"])
        //     1:4: CVIndexEntry(idx=42, count=4, ctx=["chapters", "c"])
        //     1:5: CVIndexEntry(idx=46, count=3, ctx=["chapters", "c", "m"])
        //     1:6: CVIndexEntry(idx=49, count=4, ctx=["chapters", "c", "m"])
        //     1:7: CVIndexEntry(idx=53, count=4, ctx=["chapters", "c"])
        //     1:8: CVIndexEntry(idx=57, count=4, ctx=["chapters", "c", "p"])
        //     1:9: CVIndexEntry(idx=61, count=4, ctx=["chapters", "c"])
        //     1:10: CVIndexEntry(idx=65, count=3, ctx=["chapters", "c", "p"])
        //     1:11: CVIndexEntry(idx=68, count=5, ctx=["chapters", "c", "p"])
        //     1:12: CVIndexEntry(idx=73, count=7, ctx=["chapters", "c"])
        //     1:13: CVIndexEntry(idx=80, count=3, ctx=["chapters", "c", "p"])
        //     1:14: CVIndexEntry(idx=83, count=3, ctx=["chapters", "c", "p"])
        //     1:15: CVIndexEntry(idx=86, count=6, ctx=["chapters", "c", "p"])
        //     2:0: CVIndexEntry(idx=92, count=1, ctx=["chapters"])
        //     2:1: CVIndexEntry(idx=93, count=8, ctx=["chapters", "c"])
        //     2:2: CVIndexEntry(idx=101, count=3, ctx=["chapters", "c", "p"])
        //     2:3: CVIndexEntry(idx=104, count=3, ctx=["chapters", "c", "p"])
        //     2:4: CVIndexEntry(idx=107, count=3, ctx=["chapters", "c", "p"])
        //     2:5: CVIndexEntry(idx=110, count=3, ctx=["chapters", "c", "p"])
        //     2:6: CVIndexEntry(idx=113, count=3, ctx=["chapters", "c", "p"])
        //     2:7: CVIndexEntry(idx=116, count=3, ctx=["chapters", "c", "p"])
        //     2:8: CVIndexEntry(idx=119, count=3, ctx=["chapters", "c", "p"])
        //     2:9: CVIndexEntry(idx=122, count=5, ctx=["chapters", "c", "p"])
        //     2:10: CVIndexEntry(idx=127, count=7, ctx=["chapters", "c"])
        //     2:11: CVIndexEntry(idx=134, count=3, ctx=["chapters", "c", "p"])
        //     2:12: CVIndexEntry(idx=137, count=7, ctx=["chapters", "c", "p"])
        //     2:13: CVIndexEntry(idx=144, count=8, ctx=["chapters", "c"])
        //     2:14: CVIndexEntry(idx=152, count=5, ctx=["chapters", "c"])
        //     2:15: CVIndexEntry(idx=157, count=3, ctx=["chapters", "c", "p"])
        //     2:16: CVIndexEntry(idx=160, count=3, ctx=["chapters", "c", "p"])
        //     2:17: CVIndexEntry(idx=163, count=3, ctx=["chapters", "c", "p"])
        //     2:18: CVIndexEntry(idx=166, count=3, ctx=["chapters", "c", "p"])
        //     2:19: CVIndexEntry(idx=169, count=5, ctx=["chapters", "c", "p"])
        //     2:20: CVIndexEntry(idx=174, count=7, ctx=["chapters", "c"])
        //     2:21: CVIndexEntry(idx=181, count=3, ctx=["chapters", "c", "p"])
        //     2:22: CVIndexEntry(idx=184, count=3, ctx=["chapters", "c", "p"])
        //     2:23: CVIndexEntry(idx=187, count=7, ctx=["chapters", "c", "p"])

        // It should give the following 63 entries (as per ../../test_data/OET-RV_HAG_CV_index.txt): (plus one more now)
        assert_eq!(cv_index.len(), 64, "Expected 64 CV index entries but found {}: {}", cv_index.len(), cv_index);

        // 0 -1:0 Headers='HAG'
        let (cv0, entry0) = cv_index.index_data.get_index(0).unwrap();
        assert_eq!(cv0.to_string(), "-1:0");
        assert_eq!(entry0.start_index(), 0);
        assert_eq!(entry0.entry_count(), 1);
        assert_eq!(entry0.context(), Vec::<CompactString>::new());

        // 10 -1:10 ctxt=['headers']
        let (cv10, entry10) = cv_index.index_data.get_index(10).unwrap();
        assert_eq!(cv10.to_string(), "-1:10");
        assert_eq!(entry10.start_index(), 10);
        assert_eq!(entry10.entry_count(), 1);
        assert_eq!(entry10.context(), ["headers"]);

        // 23 1:0 ctxt=['chapters']
        let (cv24, entry24) = cv_index.index_data.get_index(24).unwrap();
        assert_eq!(cv24.to_string(), "1:0");
        assert_eq!(entry24.start_index(), 24);
        assert_eq!(entry24.entry_count(), 1);
        assert_eq!(entry24.context(), ["chapters"]);

        // 24 1:1 ctxt=['chapters', 'c']
        let (cv25, entry25) = cv_index.index_data.get_index(25).unwrap();
        assert_eq!(cv25.to_string(), "1:1");
        assert_eq!(entry25.start_index(), 25);
        assert_eq!(entry25.entry_count(), 8);
        assert_eq!(entry25.context(), ["chapters", "c"]);

        // 25 1:2 ctxt=['chapters', 'c', 'p']
        let (cv26, entry26) = cv_index.index_data.get_index(26).unwrap();
        assert_eq!(cv26.to_string(), "1:2");
        assert_eq!(entry26.start_index(), 33);
        assert_eq!(entry26.entry_count(), 4);
        assert_eq!(entry26.context(), ["chapters", "c", "p"]);

        // 26 1:3 ctxt=['chapters', 'c']
        let (cv27, entry27) = cv_index.index_data.get_index(27).unwrap();
        assert_eq!(cv27.to_string(), "1:3");
        assert_eq!(entry27.start_index(), 37);
        assert_eq!(entry27.entry_count(), 5);
        assert_eq!(entry27.context(), ["chapters", "c"]);

        // 38 1:15 ctxt=['chapters', 'c', 'p']
        let (cv39, entry39) = cv_index.index_data.get_index(39).unwrap();
        // println!("cv38: {}, entry38: {} then {:#?}", cv38, entry38, index.get_verse_entries(&ChapterVerse::new("1", "15"), true));
        assert_eq!(cv39.to_string(), "1:15");
        assert_eq!(entry39.start_index(), 86);
        // println!("processed line at index 87: {}", index.entries().get(87).unwrap());
        // println!("processed line at index 88: {}", index.entries().get(88).unwrap());
        assert_eq!(entry39.entry_count(), 6);
        assert_eq!(entry39.context(), ["chapters", "c", "p"]);

        // 39 2:0 ctxt=['chapters']
        let (cv40, entry40) = cv_index.index_data.get_index(40).unwrap();
        assert_eq!(cv40.to_string(), "2:0");
        assert_eq!(entry40.start_index(), 92);
        assert_eq!(entry40.entry_count(), 1);
        assert_eq!(entry40.context(), ["chapters"]);

        // 40 2:1 ctxt=['chapters', 'c']
        let (cv41, entry41) = cv_index.index_data.get_index(41).unwrap();
        assert_eq!(cv41.to_string(), "2:1");
        assert_eq!(entry41.start_index(), 93);
        assert_eq!(entry41.entry_count(), 8);
        assert_eq!(entry41.context(), ["chapters", "c"]);

        // 41 2:2 ctxt=['chapters', 'c', 'p']
        let (cv42, entry42) = cv_index.index_data.get_index(42).unwrap();
        assert_eq!(cv42.to_string(), "2:2");
        assert_eq!(entry42.start_index(), 101);
        assert_eq!(entry42.entry_count(), 3);
        assert_eq!(entry42.context(), ["chapters", "c", "p"]);

        // 42 2:3 ctxt=['chapters', 'c', 'p']
        let (cv43, entry43) = cv_index.index_data.get_index(43).unwrap();
        assert_eq!(cv43.to_string(), "2:3");
        assert_eq!(entry43.start_index(), 104);
        assert_eq!(entry43.entry_count(), 3);
        assert_eq!(entry43.context(), ["chapters", "c", "p"]);

        // 62 2:23 ctxt=['chapters', 'c', 'p']
        let (cv63, entry63) = cv_index.index_data.get_index(63).unwrap();
        assert_eq!(cv63.to_string(), "2:23");
        assert_eq!(entry63.start_index(), 187);
        assert_eq!(entry63.entry_count(), 7);
        assert_eq!(entry63.context(), ["chapters", "c", "p"]);
    }

    #[test]
    fn test_oet_rv_psalms_cv_index_build() { // This has lots of d fields, plus five ms1,mr sets
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

        let options = ProcessLinesOptions::default();
        let processed_line_entries = process_lines(raw_lines, "PSA", "OET-RV", &options);
        // println!("OET-RV PSA Processed lines markers = {}", processed_line_entries.iter().map(|e| e.marker()).collect::<Vec<_>>().join(", "));

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

        let mut cv_index = InternalBibleBookCVIndex::new("OET-RV", "HAG");
        cv_index.build(processed_line_entries).unwrap();

        // println!("OET-RV PSA {} cv index_entries = {}", cv_index.len(), cv_index);
        //     OET-RV PSA 2644 cv index_entries = InternalBibleBookCVIndex(OET-RV HAG):
        //     -1:0: CVIndexEntry(idx=0, count=1, ctx=[])
        //     -1:1: CVIndexEntry(idx=1, count=1, ctx=[])
        //     -1:2: CVIndexEntry(idx=2, count=1, ctx=[])
        //     -1:3: CVIndexEntry(idx=3, count=1, ctx=[])
        //     -1:4: CVIndexEntry(idx=4, count=1, ctx=[])
        //     -1:5: CVIndexEntry(idx=5, count=1, ctx=[])
        //     -1:6: CVIndexEntry(idx=6, count=1, ctx=["headers"])
        //     -1:7: CVIndexEntry(idx=7, count=1, ctx=["headers"])
        //     -1:8: CVIndexEntry(idx=8, count=1, ctx=["headers"])
        //     -1:9: CVIndexEntry(idx=9, count=1, ctx=["headers"])
        //     -1:10: CVIndexEntry(idx=10, count=1, ctx=["headers"])
        //     -1:11: CVIndexEntry(idx=11, count=1, ctx=["headers"])
        //     -1:12: CVIndexEntry(idx=12, count=1, ctx=[])
        //     -1:13: CVIndexEntry(idx=13, count=1, ctx=["intro"])
        //     -1:14: CVIndexEntry(idx=14, count=1, ctx=["intro"])
        //     -1:15: CVIndexEntry(idx=15, count=1, ctx=["intro"])
        //     -1:16: CVIndexEntry(idx=16, count=1, ctx=["intro"])
        //     -1:17: CVIndexEntry(idx=17, count=1, ctx=["intro"])
        //     -1:18: CVIndexEntry(idx=18, count=1, ctx=["intro"])
        //     -1:19: CVIndexEntry(idx=19, count=1, ctx=["intro"])
        //     -1:20: CVIndexEntry(idx=20, count=1, ctx=["intro", "iot"])
        //     -1:21: CVIndexEntry(idx=21, count=1, ctx=["intro", "iot"])
        //     -1:22: CVIndexEntry(idx=22, count=1, ctx=["intro", "iot"])
        //     -1:23: CVIndexEntry(idx=23, count=1, ctx=["intro", "iot"])
        //     -1:24: CVIndexEntry(idx=24, count=1, ctx=["intro", "iot"])
        //     -1:25: CVIndexEntry(idx=25, count=1, ctx=["intro", "iot"])
        //     -1:26: CVIndexEntry(idx=26, count=1, ctx=["intro"])
        //     -1:27: CVIndexEntry(idx=27, count=1, ctx=["intro"])
        //     -1:28: CVIndexEntry(idx=28, count=1, ctx=["intro"])
        //     -1:29: CVIndexEntry(idx=29, count=1, ctx=["intro"])
        //     -1:30: CVIndexEntry(idx=30, count=1, ctx=["intro"])
        //     -1:31: CVIndexEntry(idx=31, count=1, ctx=["intro"])
        //     -1:32: CVIndexEntry(idx=32, count=1, ctx=[])
        //     1:0: CVIndexEntry(idx=33, count=1, ctx=["chapters"])
        //     1:1: CVIndexEntry(idx=34, count=20, ctx=["chapters", "c"])
        //     1:2: CVIndexEntry(idx=54, count=8, ctx=["chapters", "c", "ms1"])
        //     1:3: CVIndexEntry(idx=62, count=14, ctx=["chapters", "c", "ms1"])
        //     1:4: CVIndexEntry(idx=76, count=9, ctx=["chapters", "c", "ms1"])
        //     1:5: CVIndexEntry(idx=85, count=8, ctx=["chapters", "c", "ms1"])
        //     1:6: CVIndexEntry(idx=93, count=10, ctx=["chapters", "c", "ms1"])
        //     2:0: CVIndexEntry(idx=103, count=1, ctx=["chapters", "ms1"])
        //     2:1: CVIndexEntry(idx=104, count=12, ctx=["chapters", "ms1", "c"])
        //     2:2: CVIndexEntry(idx=116, count=8, ctx=["chapters", "ms1", "c"])
        //     2:3: CVIndexEntry(idx=124, count=8, ctx=["chapters", "ms1", "c"])
        //     2:4: CVIndexEntry(idx=132, count=8, ctx=["chapters", "ms1", "c"])
        //     2:5: CVIndexEntry(idx=140, count=8, ctx=["chapters", "ms1", "c"])
        //     2:6: CVIndexEntry(idx=148, count=8, ctx=["chapters", "ms1", "c"])
        //     2:7: CVIndexEntry(idx=156, count=8, ctx=["chapters", "ms1", "c"])
        //     2:8: CVIndexEntry(idx=164, count=8, ctx=["chapters", "ms1", "c"])
        //     2:9: CVIndexEntry(idx=172, count=8, ctx=["chapters", "ms1", "c"])
        //     2:10: CVIndexEntry(idx=180, count=9, ctx=["chapters", "ms1", "c"])
        //     2:11: CVIndexEntry(idx=189, count=8, ctx=["chapters", "ms1", "c"])
        //     2:12: CVIndexEntry(idx=197, count=16, ctx=["chapters", "ms1", "c"])
        //     3:0: CVIndexEntry(idx=213, count=1, ctx=["chapters", "ms1"])
        //     3:1: CVIndexEntry(idx=214, count=13, ctx=["chapters", "ms1", "c"])
        //     3:2: CVIndexEntry(idx=227, count=8, ctx=["chapters", "ms1", "c"])
        //     3:3: CVIndexEntry(idx=235, count=9, ctx=["chapters", "ms1", "c"])
        //     3:4: CVIndexEntry(idx=244, count=8, ctx=["chapters", "ms1", "c"])
        //     3:5: CVIndexEntry(idx=252, count=9, ctx=["chapters", "ms1", "c"])
        //     3:6: CVIndexEntry(idx=261, count=8, ctx=["chapters", "ms1", "c"])
        //     3:7: CVIndexEntry(idx=269, count=15, ctx=["chapters", "ms1", "c"])
        //     3:8: CVIndexEntry(idx=284, count=10, ctx=["chapters", "ms1", "c"])
        //     4:0: CVIndexEntry(idx=294, count=1, ctx=["chapters", "ms1"])
        //     4:1: CVIndexEntry(idx=295, count=16, ctx=["chapters", "ms1", "c"])
        //     4:2: CVIndexEntry(idx=311, count=9, ctx=["chapters", "ms1", "c"])
        //     4:3: CVIndexEntry(idx=320, count=9, ctx=["chapters", "ms1", "c"])
        //     4:4: CVIndexEntry(idx=329, count=9, ctx=["chapters", "ms1", "c"])
        //     4:5: CVIndexEntry(idx=338, count=8, ctx=["chapters", "ms1", "c"])
        //     4:6: CVIndexEntry(idx=346, count=9, ctx=["chapters", "ms1", "c"])
        //     4:7: CVIndexEntry(idx=355, count=8, ctx=["chapters", "ms1", "c"])
        //     4:8: CVIndexEntry(idx=363, count=10, ctx=["chapters", "ms1", "c"])
        //     5:0: CVIndexEntry(idx=373, count=1, ctx=["chapters", "ms1"])
        //     5:1: CVIndexEntry(idx=374, count=13, ctx=["chapters", "ms1", "c"])
        //     5:2: CVIndexEntry(idx=387, count=8, ctx=["chapters", "ms1", "c"])
        //     5:3: CVIndexEntry(idx=395, count=9, ctx=["chapters", "ms1", "c"])
        //     ...

        // It should give the following entries (as per ../../test_data/OET-RV_PSA_CV_index.txt):
        assert_eq!(cv_index.len(), 2644, "Expected 2644 CV index entries but found {}: {}", cv_index.len(), cv_index);

        // 0 -1:0 Headers='PSA'
        let (cv0, entry0) = cv_index.index_data.get_index(0).unwrap();
        assert_eq!(cv0.to_string(), "-1:0");
        assert_eq!(entry0.start_index(), 0);
        assert_eq!(entry0.entry_count(), 1);
        assert_eq!(entry0.context(), Vec::<CompactString>::new());
        assert_eq!(cv_index.get_verse_entries(cv0, true).unwrap().get(0).unwrap().marker(), "id");

        // 10 -1:10 ctxt=['headers']
        let (cv10, entry10) = cv_index.index_data.get_index(10).unwrap();
        assert_eq!(cv10.to_string(), "-1:10");
        assert_eq!(entry10.start_index(), 10);
        assert_eq!(entry10.entry_count(), 1);
        assert_eq!(entry10.context(), ["headers"]);

        // 33 1:0 ctxt=['chapters']
        let (cv33, entry33) = cv_index.index_data.get_index(33).unwrap();
        assert_eq!(cv33.to_string(), "1:0");
        assert_eq!(entry33.start_index(), 33);
        assert_eq!(entry33.entry_count(), 4); // NOTE: Should include the ms1
        assert_eq!(entry33.context(), ["chapters"]);
        assert_eq!(cv_index.get_verse_entries(cv33, true).unwrap().get(0).unwrap().marker(), "c");
        assert_eq!(cv_index.get_verse_entries(cv33, true).unwrap().get(1).unwrap().marker(), "v=");

        // 34 1:1 ctxt=['chapters', 'c']
        let (cv34, entry34) = cv_index.index_data.get_index(34).unwrap();
        assert_eq!(cv34.to_string(), "1:1");
        assert_eq!(entry34.start_index(), 37);
        assert_eq!(entry34.entry_count(), 17); // Many q1/2 fields starting and stopping
        assert_eq!(entry34.context(), ["chapters", "c", "ms1"]);

        // 35 1:2 ctxt=['chapters', 'c', 'p']
        let (cv35, entry35) = cv_index.index_data.get_index(35).unwrap();
        assert_eq!(cv35.to_string(), "1:2");
        assert_eq!(entry35.start_index(), 54);
        assert_eq!(entry35.entry_count(), 8);
        assert_eq!(entry35.context(), ["chapters", "c", "ms1"]);

        // // 26 1:3 ctxt=['chapters', 'c']
        // let (cv27, entry27) = cv_index.index_data.get_index(27).unwrap();
        // assert_eq!(cv27.to_string(), "1:3");
        // assert_eq!(entry27.start_index(), 37);
        // assert_eq!(entry27.entry_count(), 5);
        // assert_eq!(entry27.context(), ["chapters", "c"]);

        // // 38 1:15 ctxt=['chapters', 'c', 'p']
        // let (cv39, entry39) = cv_index.index_data.get_index(39).unwrap();
        // // println!("cv38: {}, entry38: {} then {:#?}", cv38, entry38, index.get_verse_entries(&ChapterVerse::new("1", "15"), true));
        // assert_eq!(cv39.to_string(), "1:15");
        // assert_eq!(entry39.start_index(), 86);
        // // println!("processed line at index 87: {}", index.entries().get(87).unwrap());
        // // println!("processed line at index 88: {}", index.entries().get(88).unwrap());
        // assert_eq!(entry39.entry_count(), 6);
        // assert_eq!(entry39.context(), ["chapters", "c", "p"]);

        // // 39 2:0 ctxt=['chapters']
        // let (cv40, entry40) = cv_index.index_data.get_index(40).unwrap();
        // assert_eq!(cv40.to_string(), "2:0");
        // assert_eq!(entry40.start_index(), 92);
        // assert_eq!(entry40.entry_count(), 1);
        // assert_eq!(entry40.context(), ["chapters"]);

        // // 40 2:1 ctxt=['chapters', 'c']
        // let (cv41, entry41) = cv_index.index_data.get_index(41).unwrap();
        // assert_eq!(cv41.to_string(), "2:1");
        // assert_eq!(entry41.start_index(), 93);
        // assert_eq!(entry41.entry_count(), 8);
        // assert_eq!(entry41.context(), ["chapters", "c"]);

        // // 41 2:2 ctxt=['chapters', 'c', 'p']
        // let (cv42, entry42) = cv_index.index_data.get_index(42).unwrap();
        // assert_eq!(cv42.to_string(), "2:2");
        // assert_eq!(entry42.start_index(), 101);
        // assert_eq!(entry42.entry_count(), 3);
        // assert_eq!(entry42.context(), ["chapters", "c", "p"]);

        // // 42 2:3 ctxt=['chapters', 'c', 'p']
        // let (cv43, entry43) = cv_index.index_data.get_index(43).unwrap();
        // assert_eq!(cv43.to_string(), "2:3");
        // assert_eq!(entry43.start_index(), 104);
        // assert_eq!(entry43.entry_count(), 3);
        // assert_eq!(entry43.context(), ["chapters", "c", "p"]);

        // // 62 2:23 ctxt=['chapters', 'c', 'p']
        // let (cv63, entry63) = cv_index.index_data.get_index(63).unwrap();
        // assert_eq!(cv63.to_string(), "2:23");
        // assert_eq!(entry63.start_index(), 187);
        // assert_eq!(entry63.entry_count(), 7);
        // assert_eq!(entry63.context(), ["chapters", "c", "p"]);
    }

    #[test]
    fn test_oet_lv_cv_indexing() {
        set_strict_checking_flag( true );
        let test_folder_path = "../../Tests/DataFilesForTests/OET-LV";
        let mut books = IndexMap::new();

        let paths = fs::read_dir(test_folder_path).expect("Could not read OET-LV folder");
        for path in paths {
            let path = path.unwrap().path();
            if path.is_file() && path.extension().and_then(|s| s.to_str()) == Some("ESFM") {
                let filename = path.file_name().unwrap().to_str().unwrap();
                // OET-LV_HAG.ESFM -> HAG
                let bos_book_code = filename.split('_').nth(1).unwrap().split('.').next().unwrap();
                
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
                let processed_line_entries = process_lines(raw_lines, bos_book_code, "OET-LV", &options);

                let mut cv_index = InternalBibleBookCVIndex::new("OET-LV", bos_book_code);
                cv_index.build(processed_line_entries.clone()).unwrap();
                books.insert(bos_book_code.to_string(), processed_line_entries);
            }
        }

        assert!(!books.is_empty(), "Should have loaded some books");
        
    }

    #[test]
    fn test_oet_rv_cv_indexing() {
        set_strict_checking_flag( true );
        let test_folder_path = "../../Tests/DataFilesForTests/OET-RV";
        let mut books = IndexMap::new();

        let paths = fs::read_dir(test_folder_path).expect("Could not read OET-RV test folder");
        for path in paths {
            let path = path.unwrap().path();
            if path.is_file() && path.extension().and_then(|s| s.to_str()) == Some("ESFM") {
                let filename = path.file_name().unwrap().to_str().unwrap();
                // e.g., OET-RV_HAG.ESFM -> HAG
                let bos_book_code = filename.split('_').nth(1).unwrap().split('.').next().unwrap();
                
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
                // if cfg!(debug_assertions) { println!("Processing OET-RV {}", bos_book_code); }
                let processed_line_entries = process_lines(raw_lines, bos_book_code, "OET-RV", &options);

                let mut cv_index = InternalBibleBookCVIndex::new("OET-RV", bos_book_code);
                cv_index.build(processed_line_entries.clone()).unwrap();
                books.insert(bos_book_code.to_string(), processed_line_entries);
            }
        }

        assert!(!books.is_empty(), "Should have loaded some books");
        
    }
}
