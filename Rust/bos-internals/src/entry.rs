//! Core Bible entry types.
//!
//! This module defines:
//! - `InternalBibleExtra` - Footnotes, cross-references, figures, and other annotations
//! - `InternalBibleEntry` - A single line/entry of Bible text

use compact_str::CompactString;

use crate::entry_extras::InternalBibleExtraList;
use crate::error::ValidationError;
use crate::markers::{ExtraType, custom_content, custom_nesting, is_end_marker};

/// Represents an "extra" element that was extracted from the main text flow.
///
/// Extras include footnotes, cross-references, figures, Strong's numbers, etc.
/// Each extra contains an index back to its position in the adjusted text.
///
/// # Fields
///
/// - `extra_type`: The type of extra (footnote, cross-ref, etc.)
/// - `index`: Position in the adjusted text where this extra was extracted
/// - `note_text`: Full text including USFM markers
/// - `clean_note_text`: Plain text without USFM markers
///
/// # Example
///
/// ```
/// use bos_internals::{InternalBibleExtra, ExtraType};
///
/// let extra = InternalBibleExtra::new(
///     ExtraType::Footnote,
///     15,
///     r"\fr 1:1 \ft This is a footnote",
///     "This is a footnote",
/// ).unwrap();
///
/// assert_eq!(extra.extra_type(), ExtraType::Footnote);
/// assert_eq!(extra.index(), 15);
/// ```
#[derive(Debug, Clone, PartialEq, Eq, rkyv::Archive, rkyv::Serialize, rkyv::Deserialize)]
pub struct InternalBibleExtra {
    extra_type: ExtraType,
    index: usize,
    note_text: CompactString,
    clean_note_text: CompactString,
}

impl InternalBibleExtra {
    /// Create a new InternalBibleExtra with validation.
    ///
    /// # Errors
    ///
    /// Returns `ValidationError` if:
    /// - `note_text` is empty
    /// - `note_text` contains newlines
    /// - `clean_note_text` contains backslashes
    pub fn new(
        extra_type: ExtraType,
        index: usize,
        note_text: impl Into<CompactString>,
        clean_note_text: impl Into<CompactString>,
    ) -> Result<Self, ValidationError> {
        let note_text = note_text.into();
        let clean_note_text = clean_note_text.into();

        // Validation
        if note_text.is_empty() {
            return Err(ValidationError::EmptyNoteText);
        }
        if note_text.contains('\n') || note_text.contains('\r') {
            return Err(ValidationError::InvalidNewlineInNote);
        }
        if clean_note_text.contains('\\') {
            return Err(ValidationError::BackslashInCleanText(format!("{} extra: '{}'", extra_type, clean_note_text)));
        }

        Ok(Self {
            extra_type,
            index,
            note_text,
            clean_note_text,
        })
    }

    /// Create a new InternalBibleExtra without validation.
    ///
    /// # Safety
    ///
    /// The caller must ensure:
    /// - `note_text` is not empty
    /// - `note_text` contains no newlines
    /// - `clean_note_text` contains no backslashes
    #[inline]
    pub fn new_unchecked(
        extra_type: ExtraType,
        index: usize,
        note_text: impl Into<CompactString>,
        clean_note_text: impl Into<CompactString>,
    ) -> Self {
        Self {
            extra_type,
            index,
            note_text: note_text.into(),
            clean_note_text: clean_note_text.into(),
        }
    }

    /// Get the extra type.
    #[inline]
    pub fn extra_type(&self) -> ExtraType {
        self.extra_type
    }

    /// Get the index into the adjusted text.
    #[inline]
    pub fn index(&self) -> usize {
        self.index
    }

    /// Get the full note text with USFM markers.
    #[inline]
    pub fn note_text(&self) -> &str {
        &self.note_text
    }

    /// Get the note text (alias for `note_text`).
    #[inline]
    pub fn text(&self) -> &str {
        &self.note_text
    }

    /// Get the clean note text without USFM markers.
    #[inline]
    pub fn clean_note_text(&self) -> &str {
        &self.clean_note_text
    }

    /// Get the clean text (alias for `clean_note_text`).
    #[inline]
    pub fn clean_text(&self) -> &str {
        &self.clean_note_text
    }
}

impl std::fmt::Display for InternalBibleExtra {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "Extra({} @ {} = {:?})", self.extra_type, self.index, self.note_text)
    }
}

/// Represents a single line/entry in the internal Bible format.
///
/// Each entry holds:
/// - The adjusted marker (e.g., `s1` instead of `s`)
/// - The original marker as it appeared in the source
/// - Multiple levels of text processing:
///   - `original_text`: Full USFM with all markup and notes
///   - `adjusted_text`: Notes removed but formatting retained
///   - `clean_text`: Notes and formatting removed (plain text)
/// - Any extras (footnotes, cross-refs, etc.) that were extracted
///
/// For end markers (e.g., `¬v`) and added nesting markers (e.g., `intro`),
/// only `marker` and `clean_text` are set; other fields are None.
///
/// # Example
///
/// ```
/// use bos_internals::InternalBibleEntry;
///
/// // Regular entry
/// let entry = InternalBibleEntry::new(
///     "v",
///     "v",
///     "1 In the beginning...",
///     "In the beginning...",
///     None,
///     "1 In the beginning...",
/// ).unwrap();
///
/// assert_eq!(entry.marker(), "v");
/// assert_eq!(entry.clean_text(), "In the beginning...");
///
/// // End marker
/// let end = InternalBibleEntry::end_marker("¬v", "").unwrap();
/// assert!(end.is_end_marker());
/// ```
#[derive(Debug, Clone, PartialEq, rkyv::Archive, rkyv::Serialize, rkyv::Deserialize)]
pub struct InternalBibleEntry {
    marker: CompactString,
    original_marker: Option<CompactString>,
    adjusted_text: Option<CompactString>,
    clean_text: CompactString,
    extras: Option<InternalBibleExtraList>,
    original_text: Option<CompactString>,
}

impl InternalBibleEntry {
    /// Create a new regular entry with all fields.
    ///
    /// # Errors
    ///
    /// Returns `ValidationError` if:
    /// - `marker` is empty or contains invalid characters
    /// - `clean_text` contains backslashes
    /// - Text fields contain newlines
    pub fn new(
        marker: impl Into<CompactString>,
        original_marker: impl Into<CompactString>,
        adjusted_text: impl Into<CompactString>,
        clean_text: impl Into<CompactString>,
        extras: Option<InternalBibleExtraList>,
        original_text: impl Into<CompactString>,
    ) -> Result<Self, ValidationError> {
        let marker = marker.into();
        let clean_text = clean_text.into();
        let adjusted_text = adjusted_text.into();
        let original_text = original_text.into();

        // Validate marker
        if marker.is_empty() {
            return Err(ValidationError::EmptyMarker);
        }
        if marker.contains('\\') || marker.contains(' ') || marker.contains('*') {
            return Err(ValidationError::InvalidMarkerCharacters(marker.to_string()));
        }

        // Validate texts
        if clean_text.contains('\n') || clean_text.contains('\r') {
            return Err(ValidationError::InvalidNewlineInAdjustedText);
        }
        if adjusted_text.contains('\n') || adjusted_text.contains('\r') {
            return Err(ValidationError::InvalidNewlineInAdjustedText);
        }
        if original_text.contains('\n') || original_text.contains('\r') {
            return Err(ValidationError::InvalidNewlineInOriginalText);
        }

        if clean_text.contains('\\') {
            return Err(ValidationError::BackslashInCleanText(format!("{} marker: '{}'", marker, clean_text)));
        }

        Ok(Self {
            marker,
            original_marker: Some(original_marker.into()),
            adjusted_text: Some(adjusted_text),
            clean_text,
            extras,
            original_text: Some(original_text),
        })
    }

    /// Create a new entry without validation.
    ///
    /// Use with caution - prefer `new()` for safety.
    #[inline]
    pub fn new_unchecked(
        marker: impl Into<CompactString>,
        original_marker: impl Into<CompactString>,
        adjusted_text: impl Into<CompactString>,
        clean_text: impl Into<CompactString>,
        extras: Option<InternalBibleExtraList>,
        original_text: impl Into<CompactString>,
    ) -> Self {
        Self {
            marker: marker.into(),
            original_marker: Some(original_marker.into()),
            adjusted_text: Some(adjusted_text.into()),
            clean_text: clean_text.into(),
            extras,
            original_text: Some(original_text.into()),
        }
    }

    /// Create an end marker entry (e.g., `¬v`, `¬p`).
    ///
    /// End markers only have `marker` and `clean_text` set.
    ///
    /// # Errors
    ///
    /// Returns `ValidationError` if the marker doesn't start with `¬`.
    pub fn end_marker(
        marker: impl Into<CompactString>,
        text: impl Into<CompactString>,
    ) -> Result<Self, ValidationError> {
        let marker = marker.into();
        if !is_end_marker(&marker) {
            return Err(ValidationError::InvalidEndMarker(marker.to_string()));
        }
        Ok(Self {
            marker,
            original_marker: None,
            adjusted_text: None,
            clean_text: text.into(),
            extras: None,
            original_text: None,
        })
    }

    /// Create an added nesting marker entry (e.g., `intro`, `chapters`).
    ///
    /// These markers are added by BOS to provide structure.
    pub fn nesting_marker(marker: impl Into<CompactString>) -> Self {
        Self {
            marker: marker.into(),
            original_marker: None,
            adjusted_text: None,
            clean_text: CompactString::new(""),
            extras: None,
            original_text: None,
        }
    }

    /// Create an entry with just marker and clean text.
    ///
    /// Used for simple markers that don't have complex processing.
    pub fn simple(marker: impl Into<CompactString>, clean_text: impl Into<CompactString>) -> Self {
        let marker = marker.into();
        let clean_text = clean_text.into();
        Self {
            original_marker: Some(marker.clone()),
            adjusted_text: Some(clean_text.clone()),
            original_text: Some(clean_text.clone()),
            marker,
            clean_text,
            extras: None,
        }
    }

    // --- Getters ---

    /// Get the (adjusted) marker.
    #[inline]
    pub fn marker(&self) -> &str {
        &self.marker
    }

    /// Get the original marker before adjustment.
    #[inline]
    pub fn original_marker(&self) -> Option<&str> {
        self.original_marker.as_deref()
    }

    /// Get the adjusted text (notes removed, formatting retained).
    #[inline]
    pub fn adjusted_text(&self) -> Option<&str> {
        self.adjusted_text.as_deref()
    }

    /// Get the text (alias for adjusted_text).
    #[inline]
    pub fn text(&self) -> Option<&str> {
        self.adjusted_text.as_deref()
    }

    /// Get the clean text (notes and formatting removed).
    #[inline]
    pub fn clean_text(&self) -> &str {
        &self.clean_text
    }

    /// Get the clean text with ESFM underlines converted to spaces.
    pub fn clean_text_no_underlines(&self) -> String {
        self.clean_text
            .replace("_ _", " ")
            .replace("_ ", " ")
            .replace(" _", " ")
            .replace('_', " ")
    }

    /// Get the extras (footnotes, cross-refs, etc.).
    #[inline]
    pub fn extras(&self) -> Option<&InternalBibleExtraList> {
        self.extras.as_ref()
    }

    /// Get the original text (full USFM).
    #[inline]
    pub fn original_text(&self) -> Option<&str> {
        self.original_text.as_deref()
    }

    /// Get the full text (alias for original_text).
    #[inline]
    pub fn full_text(&self) -> Option<&str> {
        self.original_text.as_deref()
    }

    // --- Predicates ---

    /// Check if this is an end marker.
    #[inline]
    pub fn is_end_marker(&self) -> bool {
        is_end_marker(&self.marker)
    }

    /// Check if this is a custom content marker.
    #[inline]
    pub fn is_custom_content(&self) -> bool {
        custom_content::is_custom_content(&self.marker)
    }

    /// Check if this is a custom nesting marker.
    #[inline]
    pub fn is_custom_nesting(&self) -> bool {
        custom_nesting::is_custom_nesting(&self.marker)
    }

    /// Check if this entry has extras.
    #[inline]
    pub fn has_extras(&self) -> bool {
        self.extras.as_ref().is_some_and(|e| !e.is_empty())
    }

    // --- Mutators ---

    /// Set the clean text.
    ///
    /// This also updates adjusted_text and original_text if extras is None.
    ///
    /// # Panics
    ///
    /// Panics if extras is not None (use with caution).
    pub fn set_clean_text(&mut self, new_value: impl Into<CompactString>) {
        assert!(self.extras.is_none(), "Cannot set clean_text when extras exist");
        let new_value = new_value.into();
        self.clean_text = new_value.clone();
        self.adjusted_text = Some(new_value.clone());
        self.original_text = Some(new_value);
    }
}

impl std::fmt::Display for InternalBibleEntry {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        let abbrev = if self.clean_text.len() > 80 {
            format!(
                "{}...{}",
                &self.clean_text[..40],
                &self.clean_text[self.clean_text.len() - 40..]
            )
        } else {
            self.clean_text.to_string()
        };

        write!(
            f,
            "Entry({} = {:?}{})",
            self.marker,
            abbrev,
            if self.has_extras() { " +extras" } else { "" }
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_internal_bible_extra_new() {
        let extra = InternalBibleExtra::new(ExtraType::Footnote, 15, r"\fr 1:1 \ft Note", "Note").unwrap();

        assert_eq!(extra.extra_type(), ExtraType::Footnote);
        assert_eq!(extra.index(), 15);
        assert_eq!(extra.note_text(), r"\fr 1:1 \ft Note");
        assert_eq!(extra.clean_note_text(), "Note");
    }

    #[test]
    fn test_internal_bible_extra_validation() {
        // Empty note text
        let result = InternalBibleExtra::new(ExtraType::Footnote, 0, "", "");
        assert!(matches!(result, Err(ValidationError::EmptyNoteText)));

        // Newline in note
        let result = InternalBibleExtra::new(ExtraType::Footnote, 0, "line1\nline2", "text");
        assert!(matches!(result, Err(ValidationError::InvalidNewlineInNote)));

        // Backslash in clean text
        let result = InternalBibleExtra::new(ExtraType::Footnote, 0, "note", "\\bad");
        assert!(matches!(result, Err(ValidationError::BackslashInCleanText(_))));
    }

    #[test]
    fn test_internal_bible_entry_new() {
        let entry = InternalBibleEntry::new(
            "v",
            "v",
            "1 In the beginning...",
            "In the beginning...",
            None,
            "1 In the beginning...",
        )
        .unwrap();

        assert_eq!(entry.marker(), "v");
        assert_eq!(entry.original_marker(), Some("v"));
        assert_eq!(entry.adjusted_text(), Some("1 In the beginning..."));
        assert_eq!(entry.clean_text(), "In the beginning...");
        assert!(!entry.has_extras());
    }

    #[test]
    fn test_internal_bible_entry_end_marker() {
        let entry = InternalBibleEntry::end_marker("¬v", "1").unwrap();
        assert!(entry.is_end_marker());
        assert_eq!(entry.marker(), "¬v");
        assert_eq!(entry.clean_text(), "1");
        assert!(entry.original_marker().is_none());
        assert!(entry.adjusted_text().is_none());
    }

    #[test]
    fn test_internal_bible_entry_nesting_marker() {
        let entry = InternalBibleEntry::nesting_marker("intro");
        assert!(entry.is_custom_nesting());
        assert_eq!(entry.marker(), "intro");
        assert_eq!(entry.clean_text(), "");
    }

    #[test]
    fn test_internal_bible_entry_validation() {
        // Empty marker
        let result = InternalBibleEntry::new("", "v", "text", "text", None, "text");
        assert!(matches!(result, Err(ValidationError::EmptyMarker)));

        // Invalid marker characters
        let result = InternalBibleEntry::new("\\v", "v", "text", "text", None, "text");
        assert!(matches!(result, Err(ValidationError::InvalidMarkerCharacters(_))));

        // Backslash in clean text
        let result = InternalBibleEntry::new("v", "v", "text", "\\bad", None, "text");
        assert!(matches!(result, Err(ValidationError::BackslashInCleanText(_))));

        // Invalid end marker
        let result = InternalBibleEntry::end_marker("v", "");
        assert!(matches!(result, Err(ValidationError::InvalidEndMarker(_))));
    }

    #[test]
    fn test_clean_text_no_underlines() {
        let entry = InternalBibleEntry::simple("p", "word_ _with_ underlines_here");
        assert_eq!(entry.clean_text_no_underlines(), "word with underlines here");
    }
}
