//! Chapter:Verse reference type.
//!
//! This module provides the `ChapterVerse` type for representing Bible references.
//! Chapter and verse are stored as strings to handle special cases:
//! - Chapter `-1` for book introductions
//! - Chapter `0` for rare Roman Catholic Bibles
//! - Verse suffixes like `17a`, `17b`
//! - Verse ranges like `17-25`
//! - Verse lists like `5,6,7`

use compact_str::CompactString;
use std::fmt;

use crate::error::ParseError;
use crate::parsing::get_leading_int;

/// Represents a chapter:verse reference in a Bible book.
///
/// Both chapter and verse are stored as strings because:
/// - Chapter can be `-1` (introduction), `0` (rare RC Bibles), or positive integers
/// - Verse can be digits, suffixed (`17a`), ranges (`17-25`), or lists (`5,6,7`)
///
/// # Examples
///
/// ```
/// use bos_internals::ChapterVerse;
///
/// // Regular verse
/// let cv = ChapterVerse::new("3", "16");
/// assert_eq!(cv.chapter(), "3");
/// assert_eq!(cv.verse(), "16");
///
/// // Introduction
/// let intro = ChapterVerse::intro(5);
/// assert!(intro.is_intro());
/// assert_eq!(intro.chapter(), "-1");
///
/// // Verse with suffix
/// let cv = ChapterVerse::new("1", "17a");
/// assert_eq!(cv.verse_int().unwrap(), 17);
/// ```
#[derive(Clone, PartialEq, Eq, Hash)]
pub struct ChapterVerse {
    chapter: CompactString,
    verse: CompactString,
}

impl ChapterVerse {
    /// Create a new ChapterVerse from chapter and verse strings.
    #[inline]
    pub fn new(chapter: impl Into<CompactString>, verse: impl Into<CompactString>) -> Self {
        Self {
            chapter: chapter.into(),
            verse: verse.into(),
        }
    }

    /// Create an introduction reference (chapter -1).
    ///
    /// The verse_line parameter indicates which line of the introduction.
    #[inline]
    pub fn intro(verse_line: u16) -> Self {
        Self {
            chapter: CompactString::from("-1"),
            verse: CompactString::from(verse_line.to_string()),
        }
    }

    /// Create a chapter introduction reference (verse 0).
    ///
    /// This is used for section headings and other content at the start of a chapter.
    #[inline]
    pub fn chapter_intro(chapter: impl Into<CompactString>) -> Self {
        Self {
            chapter: chapter.into(),
            verse: CompactString::from("0"),
        }
    }

    /// Get the chapter string.
    #[inline]
    pub fn chapter(&self) -> &str {
        &self.chapter
    }

    /// Get the verse string.
    #[inline]
    pub fn verse(&self) -> &str {
        &self.verse
    }

    /// Get the leading integer from the chapter.
    ///
    /// This handles negative numbers (like -1 for intro).
    pub fn chapter_int(&self) -> Result<i16, ParseError> {
        get_leading_int(&self.chapter)
    }

    /// Get the leading integer from the verse.
    ///
    /// This handles suffixed verses like `17a` and ranges like `17-25`.
    pub fn verse_int(&self) -> Result<i16, ParseError> {
        get_leading_int(&self.verse)
    }

    /// Check if this is an introduction reference (chapter -1).
    #[inline]
    pub fn is_intro(&self) -> bool {
        self.chapter == "-1"
    }

    /// Check if this is a chapter introduction (verse 0).
    #[inline]
    pub fn is_chapter_intro(&self) -> bool {
        self.verse == "0"
    }

    /// Check if the verse contains a range (e.g., `17-25`).
    #[inline]
    pub fn is_verse_range(&self) -> bool {
        self.verse.contains('-') && !self.verse.starts_with('-')
    }

    /// Check if the verse contains a list (e.g., `5,6,7`).
    #[inline]
    pub fn is_verse_list(&self) -> bool {
        self.verse.contains(',')
    }

    /// Check if the verse has a suffix (e.g., `17a`, `17b`).
    pub fn has_verse_suffix(&self) -> bool {
        self.verse
            .chars()
            .last()
            .map(|c| c.is_alphabetic())
            .unwrap_or(false)
    }

    /// Parse a verse range into (start, end) integers.
    ///
    /// Returns None if this is not a verse range.
    pub fn parse_verse_range(&self) -> Option<(i16, i16)> {
        if !self.is_verse_range() {
            return None;
        }

        let parts: Vec<&str> = self.verse.splitn(2, '-').collect();
        if parts.len() != 2 {
            return None;
        }

        let start = get_leading_int(parts[0]).ok()?;
        let end = get_leading_int(parts[1]).ok()?;
        Some((start, end))
    }

    /// Check if this reference contains the given verse number.
    ///
    /// This handles ranges and lists properly.
    pub fn contains_verse(&self, verse_num: i16) -> bool {
        if let Some((start, end)) = self.parse_verse_range() {
            return verse_num >= start && verse_num <= end;
        }

        if self.is_verse_list() {
            for part in self.verse.split(',') {
                if let Ok(v) = get_leading_int(part.trim())
                    && v == verse_num
                {
                    return true;
                }
            }
            return false;
        }

        self.verse_int().map(|v| v == verse_num).unwrap_or(false)
    }
}

impl fmt::Debug for ChapterVerse {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "CV({}:{})", self.chapter, self.verse)
    }
}

impl fmt::Display for ChapterVerse {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}:{}", self.chapter, self.verse)
    }
}

impl From<(String, String)> for ChapterVerse {
    fn from((chapter, verse): (String, String)) -> Self {
        Self::new(chapter, verse)
    }
}

impl From<(&str, &str)> for ChapterVerse {
    fn from((chapter, verse): (&str, &str)) -> Self {
        Self::new(chapter, verse)
    }
}

impl From<(i8, i8)> for ChapterVerse {
    fn from((chapter, verse): (i8, i8)) -> Self {
        Self::new(chapter.to_string(), verse.to_string())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_new() {
        let cv = ChapterVerse::new("3", "16");
        assert_eq!(cv.chapter(), "3");
        assert_eq!(cv.verse(), "16");
    }

    #[test]
    fn test_intro() {
        let cv = ChapterVerse::intro(5);
        assert!(cv.is_intro());
        assert_eq!(cv.chapter(), "-1");
        assert_eq!(cv.verse(), "5");
        assert_eq!(cv.chapter_int().unwrap(), -1);
    }

    #[test]
    fn test_chapter_intro() {
        let cv = ChapterVerse::chapter_intro("3");
        assert!(cv.is_chapter_intro());
        assert_eq!(cv.chapter(), "3");
        assert_eq!(cv.verse(), "0");
    }

    #[test]
    fn test_verse_int() {
        let cv = ChapterVerse::new("1", "17a");
        assert_eq!(cv.verse_int().unwrap(), 17);

        let cv = ChapterVerse::new("1", "17-25");
        assert_eq!(cv.verse_int().unwrap(), 17);
    }

    #[test]
    fn test_is_verse_range() {
        let cv = ChapterVerse::new("1", "17-25");
        assert!(cv.is_verse_range());

        let cv = ChapterVerse::new("1", "17");
        assert!(!cv.is_verse_range());

        // Negative chapter shouldn't be confused with range
        let cv = ChapterVerse::new("-1", "5");
        assert!(!cv.is_verse_range());
    }

    #[test]
    fn test_parse_verse_range() {
        let cv = ChapterVerse::new("1", "17-25");
        assert_eq!(cv.parse_verse_range(), Some((17, 25)));

        let cv = ChapterVerse::new("1", "17");
        assert_eq!(cv.parse_verse_range(), None);
    }

    #[test]
    fn test_is_verse_list() {
        let cv = ChapterVerse::new("1", "5,6,7");
        assert!(cv.is_verse_list());

        let cv = ChapterVerse::new("1", "17");
        assert!(!cv.is_verse_list());
    }

    #[test]
    fn test_has_verse_suffix() {
        let cv = ChapterVerse::new("1", "17a");
        assert!(cv.has_verse_suffix());

        let cv = ChapterVerse::new("1", "17");
        assert!(!cv.has_verse_suffix());
    }

    #[test]
    fn test_contains_verse() {
        // Simple verse
        let cv = ChapterVerse::new("1", "17");
        assert!(cv.contains_verse(17));
        assert!(!cv.contains_verse(18));

        // Range
        let cv = ChapterVerse::new("1", "17-25");
        assert!(cv.contains_verse(17));
        assert!(cv.contains_verse(20));
        assert!(cv.contains_verse(25));
        assert!(!cv.contains_verse(16));
        assert!(!cv.contains_verse(26));

        // List
        let cv = ChapterVerse::new("1", "5,6,7");
        assert!(cv.contains_verse(5));
        assert!(cv.contains_verse(6));
        assert!(cv.contains_verse(7));
        assert!(!cv.contains_verse(4));
        assert!(!cv.contains_verse(8));
    }

    #[test]
    fn test_display() {
        let cv = ChapterVerse::new("3", "16");
        assert_eq!(format!("{}", cv), "3:16");

        let cv = ChapterVerse::intro(5);
        assert_eq!(format!("{}", cv), "-1:5");
    }

    #[test]
    fn test_from_tuple() {
        let cv: ChapterVerse = ("3", "16").into();
        assert_eq!(cv.chapter(), "3");
        assert_eq!(cv.verse(), "16");

        let cv: ChapterVerse = (3, 16).into();
        assert_eq!(cv.chapter(), "3");
        assert_eq!(cv.verse(), "16");
    }
}
