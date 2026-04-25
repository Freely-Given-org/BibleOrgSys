//! Chapter:Verse index for fast verse lookup.
//!
//! This module provides:
//! - `CVIndexEntry` - Index entry for a single C:V reference
//! - `InternalBibleBookCVIndex` - Full CV index for a book

use compact_str::CompactString;
use indexmap::IndexMap;

use crate::chapter_verse::ChapterVerse;
use crate::entry_extras::InternalBibleEntryList;
use crate::error::{IndexError, LookupError};
use crate::markers::{custom_nesting, is_end_marker, regular_nesting};

/// An entry in the CV index, representing a single Chapter:Verse reference.
///
/// Each entry stores:
/// - The index into the entry list where this CV starts
/// - The count of entries for this CV
/// - The context (list of open markers at this point)
#[derive(Debug, Clone, PartialEq, Eq, rkyv::Archive, rkyv::Serialize, rkyv::Deserialize)]
pub struct CVIndexEntry {
    /// Index of the first entry for this C:V in the entry list.
    entry_index: usize,
    /// Number of entries for this C:V.
    entry_count: u16,
    /// Context markers that were open at this point (e.g., `["chapters", "c", "p"]`).
    context: Vec<CompactString>,
}

impl CVIndexEntry {
    /// Create a new CV index entry.
    #[inline]
    pub fn new(entry_index: usize, entry_count: u16, context: Vec<CompactString>) -> Self {
        Self {
            entry_index,
            entry_count,
            context,
        }
    }

    /// Get the starting entry index.
    #[inline]
    pub fn entry_index(&self) -> usize {
        self.entry_index
    }

    /// Get the entry count for this C:V.
    #[inline]
    pub fn entry_count(&self) -> u16 {
        self.entry_count
    }

    /// Get the index one past the last entry for this C:V.
    #[inline]
    pub fn next_entry_index(&self) -> usize {
        self.entry_index + self.entry_count as usize
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
            self.entry_index, self.entry_count, self.context
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
    entries: InternalBibleEntryList,
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
            entries: InternalBibleEntryList::new(),
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
            return Ok(self.entries.slice(entry.entry_index(), entry.next_entry_index()));
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
                    return Ok(self.entries.slice(entry.entry_index(), entry.next_entry_index()));
                }
                // Check verse lists (e.g., "5,6,7")
                if key.is_verse_list() && key.contains_verse(desired_v) {
                    return Ok(self.entries.slice(entry.entry_index(), entry.next_entry_index()));
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
            let entries = self.entries.slice(entry.entry_index(), entry.next_entry_index());
            let context = entry.context.clone();

            // If complete and verse is 1, prepend verse 0 entries
            if complete && cv.verse() == "1" {
                let cv0 = ChapterVerse::new(cv.chapter(), "0");
                if let Some(entry0) = self.index_data.get(&cv0) {
                    let mut combined = self.entries.slice(entry0.entry_index(), entry0.next_entry_index());
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
                let entries = self.entries.slice(entry.entry_index(), entry.next_entry_index());
                return Ok((entries, entry.context.clone()));
            }
        }

        Err(LookupError::CVNotFound(cv.clone()))
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
            .map(|e| e.entry_index())
            .unwrap_or(self.entries.len());

        Ok(self.entries.slice(start_entry.entry_index(), end_index))
    }

    /// Get the CV index entry for a specific reference.
    pub fn get_index_entry(&self, cv: &ChapterVerse) -> Option<&CVIndexEntry> {
        self.index_data.get(cv)
    }

    /// Get direct access to the underlying entries.
    #[inline]
    pub fn entries(&self) -> &InternalBibleEntryList {
        &self.entries
    }

    /// Build the CV index from processed entries.
    ///
    /// This analyzes the entry list and creates the CV -> entry mapping.
    ///
    /// # Errors
    ///
    /// Returns `IndexError` if the entry structure is invalid.
    pub fn build(&mut self, entries: InternalBibleEntryList) -> Result<(), IndexError> {
        if entries.is_empty() {
            return Err(IndexError::EmptyEntries);
        }

        self.entries = entries;
        self.index_data.clear();

        let mut current_chapter = CompactString::from("-1");
        let mut current_verse = CompactString::from("0");
        let mut current_start: usize = 0;
        let mut context: Vec<CompactString> = Vec::new();
        let mut current_context: Vec<CompactString> = Vec::new();

        for (i, entry) in self.entries.iter().enumerate() {
            let marker = entry.marker();

            let mut next_chapter = current_chapter.clone();
            let mut next_verse = current_verse.clone();
            let mut is_cv_start = false;

            if marker == "c" {
                next_chapter = CompactString::from(entry.clean_text());
                next_verse = CompactString::from("0");
                is_cv_start = true;
            } else if marker == "v" || marker == "v=" {
                let verse_text = entry.clean_text();
                let verse_num = verse_text.split_whitespace().next().unwrap_or(verse_text);
                next_verse = CompactString::from(verse_num);
                is_cv_start = true;
            } else if current_chapter == "-1" {
                next_verse = CompactString::from(i.to_string());
                is_cv_start = true;
            } else if current_verse == "0" && crate::markers::paragraph_markers::is_paragraph(marker) {
                next_verse = CompactString::from("1");
                is_cv_start = true;
            }

            if is_cv_start && (next_chapter != current_chapter || next_verse != current_verse) {
                current_chapter = next_chapter;
                current_verse = next_verse;
                current_start = i;
                current_context = context.clone();
            }

            // Always update/insert the current CV entry to include the current entry
            let cv = ChapterVerse::new(current_chapter.as_str(), current_verse.as_str());
            let entry_count = (i - current_start + 1) as u16;
            if let Some(existing) = self.index_data.get_mut(&cv) {
                existing.entry_count = (i - existing.entry_index + 1) as u16;
            } else {
                self.index_data
                    .insert(cv, CVIndexEntry::new(current_start, entry_count, current_context.clone()));
            }

            // 2. Handle nesting markers - push onto context
            if is_nesting_marker(marker) && !is_end_marker(marker) && marker != "nb" {
                if crate::markers::paragraph_markers::is_paragraph(marker) {
                    context.retain(|m| !crate::markers::paragraph_markers::is_paragraph(m));
                }
                context.push(CompactString::from(marker));
            }

            // 3. Handle end markers - pop from context
            if is_end_marker(marker) {
                if let Some(base) = crate::markers::base_marker(marker)
                    && let Some(pos) = context.iter().rposition(|m| m == base)
                {
                    context.remove(pos);
                }
            }
        }

        self.indexed = true;
        Ok(())
    }

    /// Validate the index structure.
    ///
    /// Returns a list of any issues found.
    pub fn validate(&self) -> Vec<String> {
        let mut issues = Vec::new();

        if !self.indexed {
            issues.push("Index has not been built".to_string());
            return issues;
        }

        // Check for overlapping entries
        let mut last_end: usize = 0;
        for (cv, entry) in &self.index_data {
            if entry.entry_index() < last_end {
                issues.push(format!(
                    "{}: entry_index {} < previous end {}",
                    cv,
                    entry.entry_index(),
                    last_end
                ));
            }
            last_end = entry.next_entry_index();
        }

        // Check that all entries are covered
        if last_end != self.entries.len() {
            issues.push(format!(
                "Index covers {} entries but list has {}",
                last_end,
                self.entries.len()
            ));
        }

        issues
    }
}

/// Check if a marker is a nesting marker that affects context.
fn is_nesting_marker(marker: &str) -> bool {
    regular_nesting::ALL.contains(&marker)
        || custom_nesting::is_custom_nesting(marker)
        || crate::markers::paragraph_markers::is_paragraph(marker)
        || crate::markers::major_section_markers::ALL.contains(&marker)
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

    fn create_test_entries() -> InternalBibleEntryList {
        let mut entries = InternalBibleEntryList::new();

        // Introduction
        entries.push(InternalBibleEntry::nesting_marker("intro")); // 0
        entries.push(InternalBibleEntry::simple("ip", "Introduction...")); // 1
        entries.push(InternalBibleEntry::end_marker("¬intro").expect("Fail")); // 2

        // Chapter 1
        entries.push(InternalBibleEntry::nesting_marker("chapters")); // 3
        entries.push(InternalBibleEntry::simple("c", "1")); // 4
        entries.push(InternalBibleEntry::simple("s1", "Creation")); // 5
        entries.push(InternalBibleEntry::simple("p", "")); // 6
        entries.push(InternalBibleEntry::simple("v", "1")); // 7
        entries.push(InternalBibleEntry::simple("v~", "In the beginning...")); // 8
        entries.push(InternalBibleEntry::end_marker("¬v").expect("Fail")); // 9
        entries.push(InternalBibleEntry::simple("v", "2")); // 10
        entries.push(InternalBibleEntry::simple("v~", "And the earth was...")); // 11
        entries.push(InternalBibleEntry::end_marker("¬v").expect("Fail")); // 12
        entries.push(InternalBibleEntry::simple("p", "")); // 13
        entries.push(InternalBibleEntry::simple("v", "3")); // 14
        entries.push(InternalBibleEntry::simple("v~", "And the spirit...")); // 15
        entries.push(InternalBibleEntry::end_marker("¬v").expect("Fail")); // 16
        entries.push(InternalBibleEntry::end_marker("¬p").expect("Fail")); // 17
        entries.push(InternalBibleEntry::end_marker("¬c").expect("Fail")); // 18

        // Chapter 2
        entries.push(InternalBibleEntry::simple("c", "2")); // 19
        entries.push(InternalBibleEntry::simple("v", "1")); // 20
        entries.push(InternalBibleEntry::simple("v~", "Thus the heavens...")); // 21
        entries.push(InternalBibleEntry::end_marker("¬v").expect("Fail")); // 22
        entries.push(InternalBibleEntry::end_marker("¬c").expect("Fail")); // 23
        entries.push(InternalBibleEntry::end_marker("¬chapters").expect("Fail")); // 24

        entries
    }

    #[test]
    fn test_build_index() {
        let mut index = InternalBibleBookCVIndex::new("ESV", "GEN");
        let entries = create_test_entries();

        index.build(entries).unwrap();
        log::trace!("CV index: {}", index);
        assert!(index.is_indexed());

        assert!(index.contains(&ChapterVerse::new("-1", "0")));
        assert!(index.contains(&ChapterVerse::new("1", "0")));
        assert!(index.contains(&ChapterVerse::new("1", "1")));
        assert!(index.contains(&ChapterVerse::new("1", "2")));
        assert!(index.contains(&ChapterVerse::new("1", "3")));
        assert!(index.contains(&ChapterVerse::new("2", "0")));
        assert!(index.contains(&ChapterVerse::new("2", "1")));

        // Intro
        assert_eq!(index.get_index_entry(&ChapterVerse::new("-1", "0")).unwrap().entry_index(), 0);
        assert_eq!(index.get_index_entry(&ChapterVerse::new("-1", "0")).unwrap().entry_count(), 1);
        assert_eq!(index.get_index_entry(&ChapterVerse::new("-1", "1")).unwrap().entry_index(), 1);
        assert_eq!(index.get_index_entry(&ChapterVerse::new("-1", "1")).unwrap().entry_count(), 1);

        // 1:0
        assert_eq!(index.get_index_entry(&ChapterVerse::new("1", "0")).unwrap().entry_index(), 4);
        assert_eq!(index.get_index_entry(&ChapterVerse::new("1", "0")).unwrap().entry_count(), 2);
        assert_eq!(index.get_index_entry(&ChapterVerse::new("1", "0")).unwrap().context(), ["chapters"]);

        // 1:1
        assert_eq!(index.get_index_entry(&ChapterVerse::new("1", "1")).unwrap().entry_index(), 6);
        assert_eq!(index.get_index_entry(&ChapterVerse::new("1", "1")).unwrap().entry_count(), 4);

        // 2:0
        assert_eq!(index.get_index_entry(&ChapterVerse::new("2", "0")).unwrap().entry_index(), 19);
        assert_eq!(index.get_index_entry(&ChapterVerse::new("2", "0")).unwrap().entry_count(), 1);

        assert!(index.len() == 10);
    }

    #[test]
    fn test_get_verse_entries() {
        let mut index = InternalBibleBookCVIndex::new("ESV", "GEN");
        index.build(create_test_entries()).unwrap();

        let entries = index.get_verse_entries(&ChapterVerse::new("1", "1"), true).unwrap();
        assert!(!entries.is_empty());
        // With the new logic, the first entry for 1:1 is the paragraph marker 'p'
        assert_eq!(entries[0].marker(), "p");
    }

    #[test]
    fn test_get_chapter_entries() {
        let mut index = InternalBibleBookCVIndex::new("ESV", "GEN");
        index.build(create_test_entries()).unwrap();

        let entries = index.get_chapter_entries("1").unwrap();
        log::trace!("Chapter entries:{}", entries);
        assert!(!entries.is_empty());
        // Chapter 1 should have: c, s1, p, v, v~, ¬v, v, v~, ¬v, p, v, v~, ¬v, ¬p, ¬c = 15 entries
        assert_eq!(entries.len(), 15);
    }
    #[test]
    fn test_chapters() {
        let mut index = InternalBibleBookCVIndex::new("ESV", "GEN");
        index.build(create_test_entries()).unwrap();

        let chapters = index.chapters();
        assert!(chapters.contains(&"1"));
        assert!(chapters.contains(&"2"));
    }

    #[test]
    fn test_not_indexed_error() {
        let index = InternalBibleBookCVIndex::new("ESV", "GEN");
        let result = index.get_verse_entries(&ChapterVerse::new("1", "1"), true);
        assert!(matches!(result, Err(LookupError::NotIndexed)));
    }

    #[test]
    fn test_oet_lv_haggai_cv_index_build() {
        let content = include_str!("../../test_data/OET-LV_HAG.ESFM");
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
        let entries_final = crate::processing::process_lines(raw_lines, "HAG", "OET-RV", &options);

        let mut index = InternalBibleBookCVIndex::new("OET-RV", "HAG");
        index.build(entries_final).unwrap();

        // It should give the following 58 entries (as per test_data/OET-LV_HAG_CVs.txt):
        // 0 startCV=('-1', '0') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=0 cnt=1 ixE=1
        // 1 startCV=('-1', '1') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=1 cnt=1 ixE=2
        // 2 startCV=('-1', '2') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=2 cnt=1 ixE=3
        // 3 startCV=('-1', '3') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=3 cnt=1 ixE=4
        // 4 startCV=('-1', '4') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=4 cnt=1 ixE=5
        // 5 startCV=('-1', '5') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=5 cnt=1 ixE=6
        // 6 startCV=('-1', '6') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=6 cnt=1 ixE=7
        // 7 startCV=('-1', '7') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=7 cnt=1 ixE=8
        // 8 startCV=('-1', '8') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=8 cnt=1 ixE=9
        // 9 startCV=('-1', '9') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=9 cnt=1 ixE=10
        // 10 startCV=('-1', '10') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=10 cnt=1 ixE=11 ctxt=['headers']
        // 11 startCV=('-1', '11') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=11 cnt=1 ixE=12 ctxt=['headers']
        // 12 startCV=('-1', '12') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=12 cnt=1 ixE=13 ctxt=['headers']
        // 13 startCV=('-1', '13') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=13 cnt=1 ixE=14 ctxt=['headers']
        // 14 startCV=('-1', '14') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=14 cnt=1 ixE=15 ctxt=['headers']
        // 15 startCV=('-1', '15') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=15 cnt=1 ixE=16 ctxt=['headers']
        // 16 startCV=('-1', '16') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=16 cnt=1 ixE=17 ctxt=['headers']
        // 17 startCV=('-1', '17') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=17 cnt=1 ixE=18
        // 18 startCV=('1', '0') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=18 cnt=1 ixE=19 ctxt=['chapters']
        // 19 startCV=('1', '1') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=19 cnt=5 ixE=24 ctxt=['chapters', 'c']
        // 20 startCV=('1', '2') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=24 cnt=3 ixE=27 ctxt=['chapters', 'c']
        // 21 startCV=('1', '3') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=27 cnt=3 ixE=30 ctxt=['chapters', 'c']
        // 22 startCV=('1', '4') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=30 cnt=3 ixE=33 ctxt=['chapters', 'c']
        // 23 startCV=('1', '5') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=33 cnt=3 ixE=36 ctxt=['chapters', 'c']
        // 24 startCV=('1', '6') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=36 cnt=3 ixE=39 ctxt=['chapters', 'c']
        // 25 startCV=('1', '7') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=39 cnt=3 ixE=42 ctxt=['chapters', 'c']
        // 26 startCV=('1', '8') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=42 cnt=3 ixE=45 ctxt=['chapters', 'c']
        // 27 startCV=('1', '9') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=45 cnt=3 ixE=48 ctxt=['chapters', 'c']
        // 28 startCV=('1', '10') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=48 cnt=3 ixE=51 ctxt=['chapters', 'c']
        // 29 startCV=('1', '11') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=51 cnt=3 ixE=54 ctxt=['chapters', 'c']
        // 30 startCV=('1', '12') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=54 cnt=3 ixE=57 ctxt=['chapters', 'c']
        // 31 startCV=('1', '13') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=57 cnt=3 ixE=60 ctxt=['chapters', 'c']
        // 32 startCV=('1', '14') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=60 cnt=3 ixE=63 ctxt=['chapters', 'c']
        // 33 startCV=('1', '15') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=63 cnt=4 ixE=67 ctxt=['chapters', 'c']
        // 34 startCV=('2', '0') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=67 cnt=1 ixE=68 ctxt=['chapters']
        // 35 startCV=('2', '1') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=68 cnt=5 ixE=73 ctxt=['chapters', 'c']
        // 36 startCV=('2', '2') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=73 cnt=3 ixE=76 ctxt=['chapters', 'c']
        // 37 startCV=('2', '3') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=76 cnt=3 ixE=79 ctxt=['chapters', 'c']
        // 38 startCV=('2', '4') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=79 cnt=3 ixE=82 ctxt=['chapters', 'c']
        // 39 startCV=('2', '5') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=82 cnt=3 ixE=85 ctxt=['chapters', 'c']
        // 40 startCV=('2', '6') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=85 cnt=3 ixE=88 ctxt=['chapters', 'c']
        // 41 startCV=('2', '7') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=88 cnt=3 ixE=91 ctxt=['chapters', 'c']
        // 42 startCV=('2', '8') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=91 cnt=3 ixE=94 ctxt=['chapters', 'c']
        // 43 startCV=('2', '9') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=94 cnt=3 ixE=97 ctxt=['chapters', 'c']
        // 44 startCV=('2', '10') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=97 cnt=3 ixE=100 ctxt=['chapters', 'c']
        // 45 startCV=('2', '11') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=100 cnt=3 ixE=103 ctxt=['chapters', 'c']
        // 46 startCV=('2', '12') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=103 cnt=3 ixE=106 ctxt=['chapters', 'c']
        // 47 startCV=('2', '13') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=106 cnt=3 ixE=109 ctxt=['chapters', 'c']
        // 48 startCV=('2', '14') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=109 cnt=3 ixE=112 ctxt=['chapters', 'c']
        // 49 startCV=('2', '15') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=112 cnt=3 ixE=115 ctxt=['chapters', 'c']
        // 50 startCV=('2', '16') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=115 cnt=3 ixE=118 ctxt=['chapters', 'c']
        // 51 startCV=('2', '17') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=118 cnt=3 ixE=121 ctxt=['chapters', 'c']
        // 52 startCV=('2', '18') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=121 cnt=3 ixE=124 ctxt=['chapters', 'c']
        // 53 startCV=('2', '19') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=124 cnt=3 ixE=127 ctxt=['chapters', 'c']
        // 54 startCV=('2', '20') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=127 cnt=3 ixE=130 ctxt=['chapters', 'c']
        // 55 startCV=('2', '21') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=130 cnt=3 ixE=133 ctxt=['chapters', 'c']
        // 56 startCV=('2', '22') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=133 cnt=3 ixE=136 ctxt=['chapters', 'c']
        // 57 startCV=('2', '23') CVIndexEntry=InternalBibleBookCVIndexEntry object: ix=136 cnt=5 ixE=141 ctxt=['chapters', 'c']
        assert_eq!(index.len(), 58);

        // 0 -1:0 Headers='HAG'
        let (cv0, entry0) = index.index_data.get_index(0).unwrap();
        assert_eq!(cv0.to_string(), "-1:0");
        assert_eq!(entry0.entry_index(), 0);
        assert_eq!(entry0.entry_count(), 1);
        assert_eq!(entry0.context(), Vec::<CompactString>::new());

        // 10 -1:10 ctxt=['headers']
        let (cv10, entry10) = index.index_data.get_index(10).unwrap();
        assert_eq!(cv10.to_string(), "-1:10");
        assert_eq!(entry10.entry_index(), 10);
        assert_eq!(entry10.entry_count(), 1);
        assert_eq!(entry10.context(), ["headers"]);

        // 18 1:0 ctxt=['chapters']
        let (cv18, entry18) = index.index_data.get_index(18).unwrap();
        assert_eq!(cv18.to_string(), "1:0");
        assert_eq!(entry18.entry_index(), 18);
        assert_eq!(entry18.entry_count(), 1);
        assert_eq!(entry18.context(), ["chapters"]);

        // 19 1:1 ctxt=['chapters', 'c']
        let (cv19, entry19) = index.index_data.get_index(19).unwrap();
        assert_eq!(cv19.to_string(), "1:1");
        assert_eq!(entry19.entry_index(), 19);
        assert_eq!(entry19.entry_count(), 5);
        assert_eq!(entry19.context(), ["chapters", "c"]);

        // 33 1:15 ctxt=['chapters', 'c']
        let (cv33, entry33) = index.index_data.get_index(33).unwrap();
        assert_eq!(cv33.to_string(), "1:15");
        assert_eq!(entry33.entry_index(), 63);
        assert_eq!(entry33.entry_count(), 4);
        assert_eq!(entry33.context(), ["chapters", "c"]);

        // 34 2:0 ctxt=['chapters']
        let (cv34, entry34) = index.index_data.get_index(34).unwrap();
        assert_eq!(cv34.to_string(), "2:0");
        assert_eq!(entry34.entry_index(), 67);
        assert_eq!(entry34.entry_count(), 1);
        assert_eq!(entry34.context(), ["chapters"]);

        // 35 2:1 ctxt=['chapters', 'c']
        let (cv35, entry35) = index.index_data.get_index(35).unwrap();
        assert_eq!(cv35.to_string(), "2:1");
        assert_eq!(entry35.entry_index(), 68);
        assert_eq!(entry35.entry_count(), 5);
        assert_eq!(entry35.context(), ["chapters", "c"]);

        // 57 2:23 ctxt=['chapters', 'c']
        let (cv57, entry57) = index.index_data.get_index(57).unwrap();
        assert_eq!(cv57.to_string(), "2:23");
        assert_eq!(entry57.entry_index(), 136);
        assert_eq!(entry57.entry_count(), 5);
        assert_eq!(entry57.context(), ["chapters", "c"]);
    }

    #[test]
    fn test_oet_rv_haggai_cv_index_build() {
        let content = include_str!("../../test_data/OET-RV_HAG.ESFM");
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
        let entries_final = crate::processing::process_lines(raw_lines, "HAG", "OET-RV", &options);

        let mut index = InternalBibleBookCVIndex::new("OET-RV", "HAG");
        index.build(entries_final).unwrap();

        // It should give the following 63 entries (as per test_data/OET-RV_HAG_CV_index.txt):
        assert_eq!(index.len(), 63);

        // 0 -1:0 Headers='HAG'
        let (cv0, entry0) = index.index_data.get_index(0).unwrap();
        assert_eq!(cv0.to_string(), "-1:0");
        assert_eq!(entry0.entry_index(), 0);
        assert_eq!(entry0.entry_count(), 1);
        assert_eq!(entry0.context(), Vec::<CompactString>::new());

        // 10 -1:10 ctxt=['headers']
        let (cv10, entry10) = index.index_data.get_index(10).unwrap();
        assert_eq!(cv10.to_string(), "-1:10");
        assert_eq!(entry10.entry_index(), 10);
        assert_eq!(entry10.entry_count(), 1);
        assert_eq!(entry10.context(), ["headers"]);

        // 23 1:0 ctxt=['chapters']
        let (cv23, entry23) = index.index_data.get_index(23).unwrap();
        assert_eq!(cv23.to_string(), "1:0");
        assert_eq!(entry23.entry_index(), 23);
        assert_eq!(entry23.entry_count(), 1);
        assert_eq!(entry23.context(), ["chapters"]);

        // 24 1:1 ctxt=['chapters', 'c']
        let (cv24, entry24) = index.index_data.get_index(24).unwrap();
        assert_eq!(cv24.to_string(), "1:1");
        assert_eq!(entry24.entry_index(), 24);
        assert_eq!(entry24.entry_count(), 8);
        assert_eq!(entry24.context(), ["chapters", "c"]);

        // 38 1:15 ctxt=['chapters', 'c', 'p']
        let (cv38, entry38) = index.index_data.get_index(38).unwrap();
        assert_eq!(cv38.to_string(), "1:15");
        assert_eq!(entry38.entry_index(), 84);
        assert_eq!(entry38.entry_count(), 5);
        assert_eq!(entry38.context(), ["chapters", "c", "p"]);

        // 39 2:0 ctxt=['chapters']
        let (cv39, entry39) = index.index_data.get_index(39).unwrap();
        assert_eq!(cv39.to_string(), "2:0");
        assert_eq!(entry39.entry_index(), 89);
        assert_eq!(entry39.entry_count(), 1);
        assert_eq!(entry39.context(), ["chapters"]);

        // 40 2:1 ctxt=['chapters', 'c']
        let (cv40, entry40) = index.index_data.get_index(40).unwrap();
        assert_eq!(cv40.to_string(), "2:1");
        assert_eq!(entry40.entry_index(), 90);
        assert_eq!(entry40.entry_count(), 8);
        assert_eq!(entry40.context(), ["chapters", "c"]);

        // 62 2:23 ctxt=['chapters', 'c', 'p']
        let (cv62, entry62) = index.index_data.get_index(62).unwrap();
        assert_eq!(cv62.to_string(), "2:23");
        assert_eq!(entry62.entry_index(), 182);
        assert_eq!(entry62.entry_count(), 6);
        assert_eq!(entry62.context(), ["chapters", "c", "p"]);
    }
}
