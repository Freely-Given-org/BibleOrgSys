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
use std::hash::{Hash, Hasher};

use crate::error::ParseError;
use crate::parsing::get_small_leading_int;

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
#[derive(Clone, PartialEq, Eq)]
pub struct ChapterVerse {
    // The chapter and the verse are stored in one string (with a separator character between them)
    //  which takes half the memory of two strings (and there's one of these for every verse of every loaded Bible).
    // Almost all references fit in the 24 bytes of the string itself, i.e., without any heap allocation.
    text: CompactString,
}

/// Separates the chapter from the verse in the stored string
///     (a character which can't sensibly occur in a chapter 'number').
const SEPARATOR: char = '\0';

impl ChapterVerse {
    /// Create a new ChapterVerse from chapter and verse strings.
    #[inline]
    pub fn new(chapter: impl AsRef<str>, verse: impl AsRef<str>) -> Self {
        let (chapter, verse) = (chapter.as_ref(), verse.as_ref());
        debug_assert!(!chapter.contains(SEPARATOR), "Chapter can't contain a NUL character: {chapter:?}");
        let mut text = CompactString::with_capacity(chapter.len() + 1 + verse.len());
        text.push_str(chapter);
        text.push(SEPARATOR);
        text.push_str(verse);
        Self { text }
    }

    /// Create an introduction reference (chapter -1).
    ///
    /// The verse_line parameter indicates which line of the introduction.
    #[inline]
    pub fn intro(verse_line: u16) -> Self {
        Self::new("-1", verse_line.to_string())
    }

    /// Create a chapter introduction reference (verse 0).
    ///
    /// This is used for section headings and other content at the start of a chapter.
    #[inline]
    pub fn chapter_intro(chapter: impl AsRef<str>) -> Self {
        Self::new(chapter, "0")
    }

    /// Get the position of the separator in the stored string.
    #[inline]
    fn separator_index(&self) -> usize {
        self.text.as_bytes().iter().position(|&byte| byte == SEPARATOR as u8).unwrap_or(self.text.len())
    }

    /// Get the chapter string.
    #[inline]
    pub fn chapter(&self) -> &str {
        &self.text[..self.separator_index()]
    }

    /// Get the verse string.
    #[inline]
    pub fn verse(&self) -> &str {
        self.text.get(self.separator_index() + 1..).unwrap_or("")
    }

    /// Get the leading integer from the chapter.
    ///
    /// This handles negative numbers (like -1 for intro).
    pub fn chapter_int(&self) -> Result<i16, ParseError> {
        get_small_leading_int(self.chapter())
    }

    /// Get the leading integer from the verse.
    ///
    /// This handles suffixed verses like `17a` and ranges like `17-25`.
    pub fn verse_int(&self) -> Result<i16, ParseError> {
        get_small_leading_int(self.verse())
    }

    /// Check if this is an introduction reference (chapter -1).
    #[inline]
    pub fn is_intro(&self) -> bool {
        self.chapter() == "-1"
    }

    /// Check if this is a chapter introduction (verse 0).
    #[inline]
    pub fn is_chapter_intro(&self) -> bool {
        self.verse() == "0"
    }

    /// Check if the verse contains a range (e.g., `17-25`).
    #[inline]
    pub fn is_verse_range(&self) -> bool {
        self.verse().contains('-') && !self.verse().starts_with('-')
    }

    /// Check if the verse contains a list (e.g., `5,6,7`).
    #[inline]
    pub fn is_verse_list(&self) -> bool {
        self.verse().contains(',')
    }

    /// Check if the verse has a suffix (e.g., `17a`, `17b`).
    pub fn has_verse_suffix(&self) -> bool {
        self.verse().chars().last().map(|c| c.is_alphabetic()).unwrap_or(false)
    }

    /// Parse a verse range into (start, end) integers.
    ///
    /// Returns None if this is not a verse range.
    pub fn parse_verse_range(&self) -> Option<(i16, i16)> {
        if !self.is_verse_range() {
            return None;
        }

        let parts: Vec<&str> = self.verse().splitn(2, '-').collect();
        if parts.len() != 2 {
            return None;
        }

        let start = get_small_leading_int(parts[0]).ok()?;
        let end = get_small_leading_int(parts[1]).ok()?;
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
            for part in self.verse().split(',') {
                if let Ok(v) = get_small_leading_int(part.trim())
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

// Hashes the chapter and then the verse (exactly as when they were two separate fields)
//  so that hash-ordered containers of these (in memory and in serialised files) are unchanged.
impl Hash for ChapterVerse {
    fn hash<H: Hasher>(&self, state: &mut H) {
        self.chapter().hash(state);
        self.verse().hash(state);
    }
}

/// The serialised form: the chapter and the verse as two separate strings.
///
/// (This was also the in-memory form before the two were combined into one string,
///  so the serialised file format is unchanged.)
#[derive(rkyv::Archive, rkyv::Serialize, rkyv::Deserialize)]
#[rkyv(archived = ArchivedChapterVerse, resolver = ChapterVerseResolver)]
pub struct ChapterVerseParts {
    chapter: CompactString,
    verse: CompactString,
}

impl ChapterVerse {
    fn to_parts(&self) -> ChapterVerseParts {
        ChapterVerseParts { chapter: self.chapter().into(), verse: self.verse().into() }
    }
}

impl rkyv::Archive for ChapterVerse {
    type Archived = ArchivedChapterVerse;
    type Resolver = ChapterVerseResolver;

    fn resolve(&self, resolver: Self::Resolver, out: rkyv::Place<Self::Archived>) {
        self.to_parts().resolve(resolver, out);
    }
}

impl<S> rkyv::Serialize<S> for ChapterVerse
where
    S: rkyv::rancor::Fallible + ?Sized,
    ChapterVerseParts: rkyv::Serialize<S>,
{
    fn serialize(&self, serializer: &mut S) -> Result<Self::Resolver, S::Error> {
        self.to_parts().serialize(serializer)
    }
}

impl<D: rkyv::rancor::Fallible + ?Sized> rkyv::Deserialize<ChapterVerse, D> for ArchivedChapterVerse {
    fn deserialize(&self, _: &mut D) -> Result<ChapterVerse, D::Error> {
        Ok(ChapterVerse::new(self.chapter.as_str(), self.verse.as_str()))
    }
}

impl fmt::Debug for ChapterVerse {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "CV({}:{})", self.chapter(), self.verse())
    }
}

impl fmt::Display for ChapterVerse {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}:{}", self.chapter(), self.verse())
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
    fn test_size_and_parts() {
        assert_eq!(std::mem::size_of::<ChapterVerse>(), 24);

        for (chapter, verse) in [("3", "16"), ("-1", "0"), ("119", "175-176"), ("1", ""), ("", ""), ("1", "5,6,7"),
                                 ("150", "a verse 'number' which is too long to store inline")] {
            let cv = ChapterVerse::new(chapter, verse);
            assert_eq!((cv.chapter(), cv.verse()), (chapter, verse));
        }
        assert_ne!(ChapterVerse::new("1", "12"), ChapterVerse::new("11", "2"));
    }

    #[test]
    fn test_serialisation_round_trip() {
        let cv = ChapterVerse::new("119", "175-176");
        let bytes = rkyv::to_bytes::<rkyv::rancor::Error>(&cv).unwrap();
        assert_eq!(rkyv::from_bytes::<ChapterVerse, rkyv::rancor::Error>(&bytes).unwrap(), cv);
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
