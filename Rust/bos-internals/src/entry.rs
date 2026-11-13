//! Core Bible entry types.
//!
//! This module defines:
//! - `InternalBibleExtra` - Footnotes, cross-references, figures, and other annotations
//! - `InternalBibleEntry` - A single line/entry of Bible text

use rkyv::with::Map;

use crate::bos_markers::{ExtraType, custom_content, custom_nesting, is_end_marker};
use crate::entry_extras::InternalBibleExtraList;
use crate::error::ValidationError;
use crate::have_strict_checking_flag;
use crate::marker_ids::MarkerId;
use crate::rkyv_with::{BoxStrAsString, MarkerAsString, U32AsUsize};

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
    #[rkyv(with = U32AsUsize)]
    index: u32, // Index into the adjusted text of the (single-line) entry
    #[rkyv(with = BoxStrAsString)]
    note_text: Box<str>,
    #[rkyv(with = BoxStrAsString)]
    clean_note_text: Box<str>,
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
        note_text: impl AsRef<str>,
        clean_note_text: impl AsRef<str>,
    ) -> Result<Self, ValidationError> {
        let note_text = note_text.as_ref();
        let clean_note_text = clean_note_text.as_ref();

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
            index: Self::index_to_u32(index),
            note_text: note_text.into(),
            clean_note_text: clean_note_text.into(),
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
        note_text: impl AsRef<str>,
        clean_note_text: impl AsRef<str>,
    ) -> Self {
        Self {
            extra_type,
            index: Self::index_to_u32(index),
            note_text: note_text.as_ref().into(),
            clean_note_text: clean_note_text.as_ref().into(),
        }
    }

    /// The index is stored as a `u32` (as it's an offset into the text of a single line).
    #[inline]
    fn index_to_u32(index: usize) -> u32 {
        u32::try_from(index).expect("Extra index into the adjusted text must fit in a u32")
    }

    /// Get the extra type.
    #[inline]
    pub fn extra_type(&self) -> ExtraType {
        self.extra_type
    }

    /// Get the index into the adjusted text.
    #[inline]
    pub fn index(&self) -> usize {
        self.index as usize
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

/// Represents a single line/entry in the internal Bible processedLines format.
///
/// Each entry holds:
/// - The (standardised) marker (e.g., `s1` instead of `s`) or an end marker (e.g., `¬v`) or a custom nesting marker (e.g., `intro`)
/// - The original marker as it appeared in the source (if it's different)
/// - Multiple levels of text processing:
///   - `original_text`: Full USFM with all markup and notes
///   - `adjusted_text`: Notes removed but formatting retained (but only if adjustments were needed; otherwise None to save space)
///   - `clean_text`: Notes and formatting removed (plain text, no backslashes, but only if adjustments were needed; otherwise None to save space)
/// - Any extras (footnotes, cross-refs, etc.) that were extracted from the original text, associated with their index in the adjusted text
///
/// For end markers (e.g., `¬v`) and added nesting markers (e.g., `intro`),
/// only `marker` and `original_text` are set; other fields are None.
///
/// # Memory use
///
/// A Bible has a few hundred thousand of these entries, so the struct is kept small (72 bytes):
/// - the markers are stored as two-byte interned IDs (see `MarkerId`)
/// - the texts are stored as boxed strings (and an empty text doesn't use any heap memory)
/// - the extras list is a boxed slice (so an empty list doesn't use any heap memory either)
///
/// The archived (serialised) layout is the same as if these were all plain strings and vectors.
///
/// # Example
///
/// ```
/// use bos_internals::InternalBibleEntry;
///
/// // Regular entry
/// let entry = InternalBibleEntry::new(
///     "v~",
///     "v",
///     "In the beginning...",
///     "In the beginning...",
///     None,
///     "In the beginning...",
/// ).unwrap();
///
/// assert_eq!(entry.marker(), "v~");
/// assert_eq!(entry.clean_text(), "In the beginning...");
///
/// // End marker
/// let end = InternalBibleEntry::end_marker("¬v", "").unwrap();
/// assert!(end.is_end_marker());
/// ```
#[derive(Debug, Clone, PartialEq, rkyv::Archive, rkyv::Serialize, rkyv::Deserialize)]
pub struct InternalBibleEntry {
    #[rkyv(with = MarkerAsString)]
    marker: MarkerId,
    #[rkyv(with = Map<MarkerAsString>)]
    original_marker: Option<MarkerId>, // Only set for regular entries, None for added nesting and end markers
    #[rkyv(with = BoxStrAsString)]
    original_text: Box<str>,
    #[rkyv(with = Map<BoxStrAsString>)]
    adjusted_text: Option<Box<str>>, // None if the same as original_text (no adjustments needed)
    extras: Option<InternalBibleExtraList>, // Extras apply to the adjusted text, None if no extras
    #[rkyv(with = Map<BoxStrAsString>)]
    clean_text: Option<Box<str>>, // None if the same as adjusted_text (no cleaning needed)
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
        marker: impl AsRef<str>,
        original_marker: impl AsRef<str>,
        original_text: impl AsRef<str>,
        adjusted_text: impl AsRef<str>,
        extras: Option<InternalBibleExtraList>,
        clean_text: impl AsRef<str>,
    ) -> Result<Self, ValidationError> {
        let marker = marker.as_ref();
        let clean_text = clean_text.as_ref().trim();
        let adjusted_text = adjusted_text.as_ref();
        let original_text = original_text.as_ref();

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

        // We try to save memory here by not storing multiple identical copies of strings
        //  We don't store the adjusted_text if it's identical to the original text (as it is much of the time, i.e., for verses without notes, xrefs, figs)
        //  nor do we store the clean_text if it's identical to the original text (as it is much of the time, i.e., for plain text verses)
        Ok(Self {
            marker: MarkerId::intern(marker),
            original_marker: Some(MarkerId::intern(original_marker.as_ref())),
            original_text: original_text.into(),
            adjusted_text: if adjusted_text==original_text {assert!(extras.is_none()); None} else {Some(adjusted_text.into())},
            extras,
            clean_text: if clean_text==original_text {None} else {Some(clean_text.into())},
        })
    }

    /// Create a new entry without validation.
    ///
    /// Use with caution - prefer `new()` for safety.
    #[inline]
    pub fn new_unchecked(
        marker: impl AsRef<str>,
        original_marker: impl AsRef<str>,
        original_text: impl AsRef<str>,
        adjusted_text: impl AsRef<str>,
        extras: Option<InternalBibleExtraList>,
        clean_text: impl AsRef<str>,
    ) -> Self {
        let marker = marker.as_ref();
        let original_text = original_text.as_ref();
        let adjusted_text = adjusted_text.as_ref();
        let clean_text = clean_text.as_ref().trim();

        if have_strict_checking_flag() || cfg!(debug_assertions) {
            assert!(!marker.is_empty(), "Marker cannot be empty");
            assert!(!marker.contains('\\') && !marker.contains(' ') && !marker.contains('*'), "Invalid character in marker: '{}'", marker);
            assert!(!adjusted_text.contains('\n') && !adjusted_text.contains('\r'), "Newlines in adjusted_text: '{}'", adjusted_text);
            assert!(!clean_text.contains('\n') && !clean_text.contains('\r'), "Newlines in clean_text: '{}'", clean_text);
            assert!(!clean_text.contains('\\'), "Backslash in clean_text: '{}'", clean_text);
            assert!(!original_text.contains('\n') && !original_text.contains('\r'), "Newlines in original_text: '{}'", original_text);
        }

        Self {
            marker: MarkerId::intern(marker),
            original_marker: Some(MarkerId::intern(original_marker.as_ref())),
            original_text: original_text.into(),
            adjusted_text: if adjusted_text==original_text {None} else {Some(adjusted_text.into())},
            extras,
            clean_text: if clean_text==adjusted_text {None} else {Some(clean_text.into())},
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
        marker: impl AsRef<str>,
        text: impl AsRef<str>,
    ) -> Result<Self, ValidationError> {
        let marker = marker.as_ref();
        if !is_end_marker(marker) {
            return Err(ValidationError::InvalidEndMarker(marker.to_string()));
        }
        Ok(Self {
            marker: MarkerId::intern(marker),
            original_marker: None,
            original_text: text.as_ref().into(),
            adjusted_text: None,
            extras: None,
            clean_text: None,
        })
    }

    /// Create an added nesting marker entry (e.g., `intro`, `chapters`).
    ///
    /// These markers are added by BOS to provide structure.
    pub fn nesting_marker(marker: impl AsRef<str>) -> Self {
        Self {
            marker: MarkerId::intern(marker.as_ref()),
            original_marker: None,
            original_text: "".into(),
            adjusted_text: None,
            extras: None,
            clean_text: None,
        }
    }

    /// Create an entry with just marker and clean text.
    ///
    /// Used for simple markers that don't have complex processing.
    pub fn simple(marker: impl AsRef<str>, text: impl AsRef<str>) -> Self {
        Self {
            marker: MarkerId::intern(marker.as_ref()),
            original_marker: None,
            original_text: text.as_ref().into(),
            adjusted_text: None,
            extras: None,
            clean_text: None,
        }
    }

    // --- Getters ---

    /// Get the (adjusted) marker.
    #[inline]
    pub fn marker(&self) -> &str {
        self.marker.as_str()
    }

    /// Get the interned ID of the (adjusted) marker
    ///     (which can be compared faster than the marker strings).
    #[inline]
    pub fn marker_id(&self) -> MarkerId {
        self.marker
    }

    /// Get the original marker before adjustment.
    #[inline]
    pub fn original_marker(&self) -> &str {
        self.original_marker.unwrap_or(self.marker).as_str()
    }

    /// Get the adjusted text (notes removed, formatting retained).
    #[inline]
    pub fn adjusted_text(&self) -> &str {
        self.adjusted_text.as_deref().unwrap_or_else(|| self.original_text.as_ref())
    }

    // /// Get the text (alias for adjusted_text).
    // #[inline]
    // pub fn text(&self) -> Option<&str> {
    //     self.adjusted_text.as_deref()
    // }

    /// Get the clean text (notes and formatting removed).
    #[inline]
    pub fn clean_text(&self) -> &str {
        self.clean_text.as_deref().unwrap_or_else(|| self.adjusted_text())
    }

    /// Get the clean text with ESFM underlines converted to spaces.
    pub fn clean_text_no_underlines(&self) -> String {
        self.clean_text() // Falls back to the adjusted text (not the original text which might still contain notes)
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
    pub fn original_text(&self) -> &str {
        self.original_text.as_ref()
    }

    // /// Get the full text (alias for original_text).
    // #[inline]
    // pub fn full_text(&self) -> Option<&str> {
    //     self.original_text.as_deref()
    // }

    // --- Predicates ---

    /// Check if this is an end marker.
    #[inline]
    pub fn is_end_marker(&self) -> bool {
        is_end_marker(self.marker())
    }

    /// Check if this is a custom content marker.
    #[inline]
    pub fn is_custom_content(&self) -> bool {
        custom_content::is_custom_content(self.marker())
    }

    /// Check if this is a custom nesting marker.
    #[inline]
    pub fn is_custom_nesting(&self) -> bool {
        custom_nesting::is_custom_nesting(self.marker())
    }

    /// Check if this entry has extras.
    #[inline]
    pub fn has_extras(&self) -> bool {
        self.extras.as_ref().is_some_and(|e| !e.is_empty())
    }

    // // --- Mutators ---

    // /// Set the clean text.
    // ///
    // /// This also updates adjusted_text and original_text if extras is None.
    // ///
    // /// # Panics
    // ///
    // /// Panics if extras is not None (use with caution).
    // pub fn set_clean_text(&mut self, new_value: impl Into<CompactString>) {
    //     assert!(self.extras.is_none(), "Cannot set clean_text when extras exist");
    //     let new_value = new_value.into();
    //     self.clean_text = new_value.clone();
    //     self.adjusted_text = Some(new_value.clone());
    //     self.original_text = Some(new_value);
    // }
}

impl std::fmt::Display for InternalBibleEntry {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        let abbrev = if self.clean_text().len() > 80 {
            format!(
                "{}...{}",
                &self.clean_text()[..40],
                &self.clean_text()[self.clean_text().len() - 40..]
            )
        } else {
            self.clean_text().to_string()
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
    fn test_entry_sizes() {
        // These are stored in their hundreds of thousands, so we don't want them to grow accidentally
        assert_eq!(std::mem::size_of::<InternalBibleEntry>(), 72);
        assert_eq!(std::mem::size_of::<InternalBibleExtra>(), 40);
    }

    #[test]
    fn test_clean_text_no_underlines_excludes_notes() {
        // A verse with a cross-reference but no character formatting:
        //  the clean text is the same as the adjusted text (so it isn't stored separately)
        let entry = InternalBibleEntry::new_unchecked(
            "v~",
            "v~",
            r"In \x + \xo 1:1 \xt Psal. 33.6.\x*the beginning_of time",
            "In the beginning_of time",
            None,
            "In the beginning_of time",
        );
        assert_eq!(entry.clean_text(), "In the beginning_of time");
        assert_eq!(entry.clean_text_no_underlines(), "In the beginning of time");
    }

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
            "v~",
            "v",
            "In the beginning...",
            "In the beginning...",
            None,
            "In the beginning...",
        )
        .unwrap();

        assert_eq!(entry.marker(), "v~");
        assert_eq!(entry.original_marker(), "v");
        assert_eq!(entry.original_text(), "In the beginning...");
        assert_eq!(entry.adjusted_text(), "In the beginning...");
        assert_eq!(entry.clean_text(), "In the beginning...");
        assert!(!entry.has_extras());
    }

    #[test]
    fn test_internal_bible_entry_end_marker() {
        let entry = InternalBibleEntry::end_marker("¬v", "1").unwrap();
        assert!(entry.is_end_marker());
        assert_eq!(entry.marker(), "¬v");
        assert_eq!(entry.original_marker(), "¬v");
        assert_eq!(entry.original_text(), "1");
        assert_eq!(entry.adjusted_text(), "1");
        assert_eq!(entry.clean_text(), "1");
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
        let result = InternalBibleEntry::new("v", "v", "text", "text", None, "bad\\clean");
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
