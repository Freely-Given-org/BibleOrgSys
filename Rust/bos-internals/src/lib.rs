//! BibleOrgSys Internals - Core data structures for Bible text representation.
//!
//! This crate provides the internal data structures used by BibleOrgSys for
//! representing, indexing, and manipulating Bible text. It is based on the
//! USFM3 standard with BibleOrgSys extensions.
//!
//! # Overview
//!
//! The crate is organized into several modules:
//!
//! - [`entry`] - Core types for Bible entries and extras (footnotes, cross-refs)
//! - [`entry_list`] - Typed collections for entries and extras
//! - [`indexes`] - Fast lookup indexes (CV index, section index)
//! - [`markers`] - USFM marker types and constants
//! - [`chapter_verse`] - Chapter:Verse reference type
//! - [`parsing`] - Parsing utilities for USFM attributes
//! - [`error`] - Error types
//!
//! # Key Types
//!
//! ## Entry Types
//!
//! - [`InternalBibleEntry`] - A single line of Bible text with multiple levels:
//!   - Original text (full USFM)
//!   - Adjusted text (notes removed)
//!   - Clean text (formatting removed)
//! - [`InternalBibleExtra`] - An extracted annotation (footnote, cross-ref, etc.)
//!
//! ## Collections
//!
//! - [`InternalBibleEntryList`] - Collection of entries (the processed lines of a book)
//! - [`InternalBibleExtraList`] - Collection of extras for an entry
//!
//! ## References
//!
//! - [`ChapterVerse`] - A chapter:verse reference handling special cases like:
//!   - Introduction (chapter `-1`)
//!   - Verse suffixes (`17a`, `17b`)
//!   - Verse ranges (`17-25`)
//!   - Verse lists (`5,6,7`)
//!
//! ## Indexes
//!
//! - [`InternalBibleBookCVIndex`] - Fast verse lookup by chapter:verse
//! - [`InternalBibleBookSectionIndex`] - Section-based lookup for TOC navigation
//!
//! # Example
//!
//! ```
//! use bos_internals::{
//!     InternalBibleEntry, InternalBibleEntryList,
//!     InternalBibleExtra, InternalBibleExtraList,
//!     ExtraType, ChapterVerse,
//! };
//!
//! // Create entries
//! let mut entries = InternalBibleEntryList::new();
//! entries.push(InternalBibleEntry::simple("c", "1"));
//! entries.push(InternalBibleEntry::simple("v", "1"));
//! entries.push(InternalBibleEntry::simple("v~", "In the beginning..."));
//!
//! // Create a verse reference
//! let cv = ChapterVerse::new("1", "1");
//! assert_eq!(cv.chapter(), "1");
//! assert_eq!(cv.verse(), "1");
//!
//! // Create an extra (footnote)
//! let extra = InternalBibleExtra::new(
//!     ExtraType::Footnote,
//!     5,
//!     r"\fr 1:1 \ft Note text",
//!     "Note text",
//! ).unwrap();
//! ```
//!
//! # Feature Flags
//!
//! - `python` - Enable Python bindings via PyO3

// Re-export core modules
pub mod chapter_verse;
pub mod entry;
pub mod entry_extras;
pub mod error;
pub mod indexes;
pub mod markers;
pub mod nesting;
pub mod parsing;
pub mod processing;

// Re-export commonly used types at crate root
pub use chapter_verse::ChapterVerse;
pub use entry::{InternalBibleEntry, InternalBibleExtra};
pub use entry_extras::{InternalBibleEntryList, InternalBibleExtraList};
pub use error::{BosError, IndexError, LookupError, ParseError, ValidationError};
pub use indexes::{CVIndexEntry, InternalBibleBookCVIndex, InternalBibleBookSectionIndex, SectionIndexEntry};
pub use markers::ExtraType;
pub use parsing::{
    UsfmFigureAttributes, WordWithAttributes, abbreviate, get_small_leading_int,
    parse_figure_attributes, parse_word_attributes,
};
pub use processing::{ObjectType, ProcessLinesOptions, process_lines};
