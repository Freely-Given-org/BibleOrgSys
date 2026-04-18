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
/// ```ignore
/// use bos_internals::indexes::InternalBibleBookCVIndex;
///
/// let mut index = InternalBibleBookCVIndex::new("ESV", "GEN");
/// // After building index...
/// let entries = index.get_verse_entries(&ChapterVerse::new("1", "1"), true)?;
/// ```
#[derive(Debug, rkyv::Archive, rkyv::Serialize, rkyv::Deserialize)]
pub struct InternalBibleBookCVIndex {
    /// Name of the work/Bible.
    work_name: CompactString,
    /// Three-letter book code (e.g., "GEN", "MAT").
    book_code: CompactString,
    /// The CV -> entry mapping.
    index_data: IndexMap<ChapterVerse, CVIndexEntry>,
    /// The processed entries this index references.
    entries: InternalBibleEntryList,
    /// Whether the index has been built.
    indexed: bool,
}

impl InternalBibleBookCVIndex {
    /// Create a new empty CV index.
    pub fn new(work_name: impl Into<CompactString>, book_code: impl Into<CompactString>) -> Self {
        Self {
            work_name: work_name.into(),
            book_code: book_code.into(),
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
    pub fn book_code(&self) -> &str {
        &self.book_code
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
    pub fn get_verse_entries(
        &self,
        cv: &ChapterVerse,
        strict: bool,
    ) -> Result<InternalBibleEntryList, LookupError> {
        if !self.indexed {
            return Err(LookupError::NotIndexed);
        }

        // Try direct lookup first
        if let Some(entry) = self.index_data.get(cv) {
            return Ok(self
                .entries
                .slice(entry.entry_index(), entry.next_entry_index()));
        }

        if strict {
            return Err(LookupError::CVNotFound(cv.clone()));
        }

        // Non-strict: search for verse ranges containing this verse
        let desired_v = cv
            .verse_int()
            .map_err(|_| LookupError::CVNotFound(cv.clone()))?;

        for (key, entry) in &self.index_data {
            if key.chapter() == cv.chapter() {
                // Check verse ranges (e.g., "17-25")
                if let Some((start, end)) = key.parse_verse_range()
                    && start <= desired_v
                    && desired_v <= end
                {
                    return Ok(self
                        .entries
                        .slice(entry.entry_index(), entry.next_entry_index()));
                }
                // Check verse lists (e.g., "5,6,7")
                if key.is_verse_list() && key.contains_verse(desired_v) {
                    return Ok(self
                        .entries
                        .slice(entry.entry_index(), entry.next_entry_index()));
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
            let entries = self
                .entries
                .slice(entry.entry_index(), entry.next_entry_index());
            let context = entry.context.clone();

            // If complete and verse is 1, prepend verse 0 entries
            if complete && cv.verse() == "1" {
                let cv0 = ChapterVerse::new(cv.chapter(), "0");
                if let Some(entry0) = self.index_data.get(&cv0) {
                    let mut combined = self
                        .entries
                        .slice(entry0.entry_index(), entry0.next_entry_index());
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
        let desired_v = cv
            .verse_int()
            .map_err(|_| LookupError::CVNotFound(cv.clone()))?;

        for (key, entry) in &self.index_data {
            if key.chapter() == cv.chapter() && key.contains_verse(desired_v) {
                let entries = self
                    .entries
                    .slice(entry.entry_index(), entry.next_entry_index());
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
    pub fn get_chapter_entries(
        &self,
        chapter: &str,
    ) -> Result<InternalBibleEntryList, LookupError> {
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

        let mut current_chapter: Option<CompactString> = Some(CompactString::from("-1"));
        let mut current_verse: Option<CompactString> = Some(CompactString::from("0"));
        let mut current_start: usize = 0;
        let mut context: Vec<CompactString> = Vec::new();

        for (i, entry) in self.entries.iter().enumerate() {
            let marker = entry.marker();

            // Handle nesting markers - push onto context
            if is_nesting_marker(marker) && !is_end_marker(marker) {
                context.push(CompactString::from(marker));
            }

            // Handle end markers - pop from context
            if is_end_marker(marker)
                && let Some(base) = crate::markers::base_marker(marker)
                && let Some(pos) = context.iter().rposition(|m| m == base)
            {
                context.remove(pos);
            }

            // Handle chapter markers
            if marker == "c" {
                // Save previous verse if any
                if let (Some(c), Some(v)) = (&current_chapter, &current_verse) {
                    let cv = ChapterVerse::new(c.as_str(), v.as_str());
                    let entry_count = (i - current_start) as u16;
                    self.index_data.insert(
                        cv,
                        CVIndexEntry::new(current_start, entry_count, context.clone()),
                    );
                }

                current_chapter = Some(CompactString::from(entry.clean_text()));
                current_verse = Some(CompactString::from("0"));
                current_start = i;
            }

            // Handle verse markers
            if marker == "v" {
                // Save previous verse if any
                if let (Some(c), Some(v)) = (&current_chapter, &current_verse) {
                    let cv = ChapterVerse::new(c.as_str(), v.as_str());
                    let entry_count = (i - current_start) as u16;
                    self.index_data.insert(
                        cv,
                        CVIndexEntry::new(current_start, entry_count, context.clone()),
                    );
                }

                // Start new verse - extract verse number from clean text
                let verse_text = entry.clean_text();
                let verse_num = verse_text.split_whitespace().next().unwrap_or(verse_text);
                current_verse = Some(CompactString::from(verse_num));
                current_start = i;
            }

            // Handle introduction (before chapter 1)
            if marker == "intro" {
                current_chapter = Some(CompactString::from("-1"));
                current_verse = Some(CompactString::from("0"));
                current_start = i;
            }
        }

        // Save final verse
        if let (Some(c), Some(v)) = (&current_chapter, &current_verse) {
            let cv = ChapterVerse::new(c.as_str(), v.as_str());
            let entry_count = (self.entries.len() - current_start) as u16;
            self.index_data.insert(
                cv,
                CVIndexEntry::new(current_start, entry_count, context.clone()),
            );
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
            self.work_name, self.book_code
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

        // Chapter 1
        entries.push(InternalBibleEntry::simple("c", "1"));
        entries.push(InternalBibleEntry::simple("p", ""));
        entries.push(InternalBibleEntry::simple("v", "1"));
        entries.push(InternalBibleEntry::simple("v~", "In the beginning..."));
        entries.push(InternalBibleEntry::simple("v", "2"));
        entries.push(InternalBibleEntry::simple("v~", "And the earth was..."));

        // Chapter 2
        entries.push(InternalBibleEntry::simple("c", "2"));
        entries.push(InternalBibleEntry::simple("v", "1"));
        entries.push(InternalBibleEntry::simple("v~", "Thus the heavens..."));

        entries
    }

    #[test]
    fn test_build_index() {
        let mut index = InternalBibleBookCVIndex::new("ESV", "GEN");
        let entries = create_test_entries();

        index.build(entries).unwrap();

        assert!(index.is_indexed());
        assert!(!index.is_empty());
        assert!(index.contains(&ChapterVerse::new("1", "0")));
        assert!(index.contains(&ChapterVerse::new("1", "1")));
        assert!(index.contains(&ChapterVerse::new("1", "2")));
        assert!(index.contains(&ChapterVerse::new("2", "0")));
    }

    #[test]
    fn test_get_verse_entries() {
        let mut index = InternalBibleBookCVIndex::new("ESV", "GEN");
        index.build(create_test_entries()).unwrap();

        let entries = index
            .get_verse_entries(&ChapterVerse::new("1", "1"), true)
            .unwrap();
        assert!(!entries.is_empty());
        assert_eq!(entries[0].marker(), "v");
    }

    #[test]
    fn test_get_chapter_entries() {
        let mut index = InternalBibleBookCVIndex::new("ESV", "GEN");
        index.build(create_test_entries()).unwrap();

        let entries = index.get_chapter_entries("1").unwrap();
        assert!(!entries.is_empty());
        // Chapter 1 should have: c, p, v, v~, v, v~ = 6 entries
        assert_eq!(entries.len(), 6);
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
}
