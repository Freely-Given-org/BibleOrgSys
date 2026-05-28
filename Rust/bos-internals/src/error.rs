//! Error types for the BibleOrgSys internals crate.
//!
//! Uses `thiserror` for ergonomic error handling.

use thiserror::Error;

use crate::chapter_verse::ChapterVerse;

/// Errors that occur during validation of Bible entries and extras.
#[derive(Error, Debug, Clone, PartialEq, Eq)]
pub enum ValidationError {
    #[error("Empty marker is not allowed")]
    EmptyMarker,

    #[error("Marker '{0}' contains invalid characters (backslash, space, or asterisk)")]
    InvalidMarkerCharacters(String),

    #[error("Unexpected backslash in clean text: '{0}'")]
    BackslashInCleanText(String),

    #[error("Note text cannot be empty")]
    EmptyNoteText,

    #[error("Note text cannot contain newlines")]
    InvalidNewlineInNote,

    #[error("End marker must start with '¬', got '{0}'")]
    InvalidEndMarker(String),

    #[error("Adjusted text cannot contain newlines")]
    InvalidNewlineInAdjustedText,

    #[error("Original text cannot contain newlines")]
    InvalidNewlineInOriginalText,

    #[error("Unknown extra type: '{0}'")]
    UnknownExtraType(String),
}

/// Errors that occur during parsing of USFM attributes and text.
#[derive(Error, Debug, Clone, PartialEq, Eq)]
pub enum ParseError {
    #[error("No leading integer found in '{0}'")]
    NoLeadingInt(String),

    #[error("Integer {0} out of range in '{1}'")]
    IntOutOfRange(i32, String),

    #[error("Invalid word attribute format: {0}")]
    InvalidWordAttribute(String),

    #[error("Parse error: {0}")]
    Generic(String),

    #[error("Invalid figure attribute format: {0}")]
    InvalidFigureAttribute(String),

    #[error("Missing required pipe separator in word attributes")]
    MissingPipeSeparator,

    #[error("Invalid attribute name: '{0}'")]
    InvalidAttributeName(String),

    #[error("Empty attribute value for '{0}'")]
    EmptyAttributeValue(String),
}

/// Errors that occur during index lookup operations.
#[derive(Error, Debug, Clone, PartialEq, Eq)]
pub enum LookupError {
    #[error("Chapter:Verse {0} not found")]
    CVNotFound(ChapterVerse),

    #[error("Chapter '{0}' not found")]
    ChapterNotFound(String),

    #[error("Section at {0} not found")]
    SectionNotFound(ChapterVerse),

    #[error("Index has not been built yet")]
    NotIndexed,

    #[error("Invalid verse reference: {0}")]
    InvalidReference(String),
}

/// Errors that occur during index building.
#[derive(Error, Debug, Clone, PartialEq, Eq)]
pub enum IndexError {
    #[error("Duplicate CV entry at {0}")]
    DuplicateCV(ChapterVerse),

    #[error("Empty entry list - cannot build index")]
    EmptyEntries,

    #[error("Nesting error at {0}: {1}")]
    NestingError(ChapterVerse, String),

    #[error("Missing chapter marker before verse")]
    MissingChapterMarker,

    #[error("Missing verse marker in chapter")]
    MissingVerseMarker,

    #[error("Invalid marker sequence: {0}")]
    InvalidMarkerSequence(String),

    #[error("Inconsistent verse numbers at {0}: found {1}")]
    InconsistentVerseNumbers(ChapterVerse, String),
}

/// A combined result type for convenience.
pub type Result<T> = std::result::Result<T, BosError>;

/// Top-level error enum that encompasses all error types.
#[derive(Error, Debug)]
pub enum BosError {
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),

    #[error(transparent)]
    Validation(#[from] ValidationError),

    #[error(transparent)]
    Parse(#[from] ParseError),

    #[error(transparent)]
    Lookup(#[from] LookupError),

    #[error(transparent)]
    Index(#[from] IndexError),
}
