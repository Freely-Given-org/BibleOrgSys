//! Parsing utilities for USFM text and attributes.
//!
//! This module provides functions for parsing:
//! - Leading integers from strings (for verse numbers like "17a")
//! - Word attributes from USFM3 `\w` fields
//! - Figure attributes from USFM2/USFM3 `\fig` fields
//! - Text abbreviation for display

use std::collections::HashMap;

use crate::error::ParseError;

/// Extract the leading integer from a string.
///
/// This is especially useful for verse numbers like "17a", "17-25", etc.
///
/// # Examples
///
/// ```
/// use bos_internals::parsing::get_small_leading_int;
/// use bos_internals::error::ParseError;
///
/// assert_eq!(get_small_leading_int("17").unwrap(), 17);
/// assert_eq!(get_small_leading_int("17a").unwrap(), 17);
/// assert_eq!(get_small_leading_int("17-25").unwrap(), 17);
/// assert_eq!(get_small_leading_int("-1").unwrap(), -1);
/// assert_eq!(get_small_leading_int("200something").unwrap(), 200);
/// assert!(matches!(get_small_leading_int("abc"), Err(ParseError::NoLeadingInt(_))));
/// assert!(matches!(get_small_leading_int("-2"), Err(ParseError::IntOutOfRange(-2, _))));
/// assert!(matches!(get_small_leading_int("201"), Err(ParseError::IntOutOfRange(201, _))));
/// ```
pub fn get_small_leading_int(s: &str) -> Result<i16, ParseError> {
    let mut end = 0;
    let bytes = s.as_bytes();
    
    if bytes.is_empty() {
        return Err(ParseError::NoLeadingInt(s.to_string()));
    }

    if bytes[0] == b'-' {
        end = 1;
    }

    while end < bytes.len() && bytes[end].is_ascii_digit() {
        end += 1;
    }

    if end == 0 || (end == 1 && bytes[0] == b'-') {
        return Err(ParseError::NoLeadingInt(s.to_string()));
    }

    let val: i32 = s[..end]
        .parse()
        .map_err(|_| ParseError::NoLeadingInt(s.to_string()))?;

    if val < -1 || val > 200 {
        return Err(ParseError::IntOutOfRange(val, s.to_string()));
    }

    Ok(val as i16)
}

/// Extract the leading integer from a string.
/// Needed for ESFM word numbers which can be larger than 32767 (e.g., "46168", "381561") but must be non-negative.
///
/// # Examples
///
/// ```
/// use bos_internals::parsing::get_positive_leading_int;
/// use bos_internals::error::ParseError;
///
/// assert_eq!(get_positive_leading_int("17").unwrap(), 17);
/// assert_eq!(get_positive_leading_int("17a").unwrap(), 17);
/// assert_eq!(get_positive_leading_int("17-25").unwrap(), 17);
/// assert_eq!(get_positive_leading_int("400000").unwrap(), 400000);
/// assert!(matches!(get_positive_leading_int("abc"), Err(ParseError::NoLeadingInt(_))));
/// assert!(matches!(get_positive_leading_int("-1"), Err(ParseError::NoLeadingInt(_)))); // No digits at start
/// assert!(matches!(get_positive_leading_int("400001"), Err(ParseError::IntOutOfRange(400001, _))));
/// ```
pub fn get_positive_leading_int(s: &str) -> Result<u32, ParseError> {
    let mut end = 0;
    let bytes = s.as_bytes();

    while end < bytes.len() && bytes[end].is_ascii_digit() {
        end += 1;
    }

    if end == 0 {
        return Err(ParseError::NoLeadingInt(s.to_string()));
    }

    let val: u32 = s[..end]
        .parse()
        .map_err(|_| ParseError::NoLeadingInt(s.to_string()))?;

    if val > 400_000 {
        return Err(ParseError::IntOutOfRange(val as i32, s.to_string()));
    }

    Ok(val)
}

/// Result of parsing word attributes from USFM3 `\w` field.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WordWithAttributes {
    /// The word itself (before the pipe).
    pub word: String,
    /// The lemma (dictionary form).reasonMarker
    pub lemma: Option<String>,
    /// Strong's number(s).
    pub strong: Option<String>,
    /// Additional attributes (x-* attributes have prefix removed).
    pub extra: HashMap<String, String>,
}

impl WordWithAttributes {
    /// Create a new WordWithAttributes with just a word.
    pub fn new(word: impl Into<String>) -> Self {
        Self {
            word: word.into(),
            lemma: None,
            strong: None,
            extra: HashMap::new(),
        }
    }
}

/// Parse word attributes from a USFM3 `\w` field.
///
/// The format is: `word|attribute1="value1" attribute2="value2"`
/// or simply: `word|lemma` (unnamed lemma)
///
/// # Arguments
///
/// * `word_attribute_string` - The full string including the pipe separator
///
/// # Examples
///
/// ```
/// use bos_internals::parsing::parse_word_attributes;
///
/// let attrs = parse_word_attributes("word|lemma").unwrap();
/// assert_eq!(attrs.word, "word");
/// assert_eq!(attrs.lemma, Some("lemma".to_string()));
///
/// let attrs = parse_word_attributes("word|lemma=\"test\" strong=\"H1234\"").unwrap();
/// assert_eq!(attrs.word, "word");
/// assert_eq!(attrs.lemma, Some("test".to_string()));
/// assert_eq!(attrs.strong, Some("H1234".to_string()));
/// ```
pub fn parse_word_attributes(word_attribute_string: &str) -> Result<WordWithAttributes, ParseError> {
    // Split on first pipe
    let pipe_pos = word_attribute_string
        .find('|')
        .ok_or(ParseError::MissingPipeSeparator)?;

    let word = &word_attribute_string[..pipe_pos];
    let attribute_string = &word_attribute_string[pipe_pos + 1..];

    let mut result = WordWithAttributes::new(word);

    // If no equals sign, assume it's a single unnamed lemma
    if !attribute_string.contains('=') && !attribute_string.contains('"') && !attribute_string.contains('\'') {
        result.lemma = Some(attribute_string.to_string());
        return Ok(result);
    }

    // Parse named attributes using a state machine
    let mut state = ParserState::ReadyForName;
    let mut name = String::new();
    let mut value = String::new();
    let mut quote_char: Option<char> = None;

    for ch in attribute_string.chars() {
        match state {
            ParserState::ReadyForName => {
                if !ch.is_whitespace() {
                    name.clear();
                    value.clear();
                    name.push(ch);
                    state = ParserState::ReadingName;
                }
            }
            ParserState::ReadingName => {
                if ch.is_alphanumeric() || ch == '-' {
                    name.push(ch);
                } else if ch == '=' {
                    state = ParserState::ReadyForValue;
                } else {
                    return Err(ParseError::InvalidAttributeName(name));
                }
            }
            ParserState::ReadyForValue => {
                if ch == '"' || ch == '\'' {
                    quote_char = Some(ch);
                    state = ParserState::ReadingValue;
                } else if !ch.is_whitespace() {
                    value.push(ch);
                    quote_char = None;
                    state = ParserState::ReadingValue;
                }
            }
            ParserState::ReadingValue => {
                if Some(ch) == quote_char || (quote_char.is_none() && ch.is_whitespace()) {
                    // End of value - store it
                    store_attribute(&mut result, &name, &value);
                    name.clear();
                    value.clear();
                    state = ParserState::ReadyForName;
                } else {
                    value.push(ch);
                }
            }
        }
    }

    // Handle final attribute if we ended in ReadingValue state
    if state == ParserState::ReadingValue && !name.is_empty() {
        store_attribute(&mut result, &name, &value);
    }

    Ok(result)
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum ParserState {
    ReadyForName,
    ReadingName,
    ReadyForValue,
    ReadingValue,
}

fn store_attribute(result: &mut WordWithAttributes, name: &str, value: &str) {
    // Strip x- prefix for convenience
    let clean_name = name.strip_prefix("x-").unwrap_or(name);

    match clean_name {
        "lemma" => result.lemma = Some(value.to_string()),
        "strong" => result.strong = Some(value.to_string()),
        _ => {
            result.extra.insert(clean_name.to_string(), value.to_string());
        }
    }
}

/// Figure attribute names in USFM3 format.
const FIGURE_ATTR_NAMES_USFM3: [&str; 6] = ["alt", "src", "size", "loc", "copy", "ref"];

/// Better (more descriptive) names for figure attributes.
const BETTER_ATTR_NAMES_USFM3: [&str; 6] = [
    "altDescription",
    "sourceFilename",
    "relativeSize",
    "locationOrRange",
    "copyrightOrRightsHolder",
    "referenceCV",
];

/// Figure attribute names for USFM2 (determined by position).
const FIGURE_ATTR_NAMES_USFM2: [&str; 7] = [
    "altDescription",
    "sourceFilename",
    "relativeSize",
    "locationOrRange",
    "copyrightOrRightsHolder",
    "caption",
    "referenceCV",
];

/// Result of parsing figure attributes.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct UsfmFigureAttributes {
    /// USFM version (2 or 3).
    pub usfm_version: u8,
    /// Figure caption.
    pub caption: Option<String>,
    /// Alt description.
    pub alt_description: Option<String>,
    /// Source filename.
    pub source_filename: Option<String>,
    /// Relative size (e.g., "span", "col").
    pub relative_size: Option<String>,
    /// Location or range.
    pub location_or_range: Option<String>,
    /// Copyright or rights holder.
    pub copyright_or_rights_holder: Option<String>,
    /// Reference C:V.
    pub reference_cv: Option<String>,
}

impl Default for UsfmFigureAttributes {
    fn default() -> Self {
        Self {
            usfm_version: 3,
            caption: None,
            alt_description: None,
            source_filename: None,
            relative_size: None,
            location_or_range: None,
            copyright_or_rights_holder: None,
            reference_cv: None,
        }
    }
}

/// Parse figure attributes from USFM2 or USFM3 `\fig` field.
///
/// USFM2 format: `DESC|FILE|SIZE|LOC|COPY|CAP|REF`
/// USFM3 format: `caption text|src="filename" size="size" ref="reference"`
///
/// # Examples
///
/// ```
/// use bos_internals::parsing::parse_figure_attributes;
///
/// // USFM3 format
/// let attrs = parse_figure_attributes(r#"At once they left.|src="avnt016.jpg" size="span" ref="1.18""#).unwrap();
/// assert_eq!(attrs.usfm_version, 3);
/// assert_eq!(attrs.caption, Some("At once they left.".to_string()));
/// assert_eq!(attrs.source_filename, Some("avnt016.jpg".to_string()));
///
/// // USFM2 format
/// let attrs = parse_figure_attributes("desc|file.jpg|span|loc|copyright|Caption text|1:18").unwrap();
/// assert_eq!(attrs.usfm_version, 2);
/// assert_eq!(attrs.alt_description, Some("desc".to_string()));
/// ```
pub fn parse_figure_attributes(figure_attribute_string: &str) -> Result<UsfmFigureAttributes, ParseError> {
    let mut result = UsfmFigureAttributes::default();

    // Detect USFM3 vs USFM2
    // USFM3 has exactly one pipe and contains '='
    if figure_attribute_string.matches('|').count() == 1 && figure_attribute_string.contains('=') {
        // USFM3 format
        result.usfm_version = 3;

        let pipe_pos = figure_attribute_string.find('|').unwrap();
        result.caption = Some(figure_attribute_string[..pipe_pos].to_string());
        let attribute_string = &figure_attribute_string[pipe_pos + 1..];

        // Parse named attributes
        let mut state = ParserState::ReadyForName;
        let mut name = String::new();
        let mut value = String::new();
        let mut quote_char: Option<char> = None;

        for ch in attribute_string.chars() {
            match state {
                ParserState::ReadyForName => {
                    if !ch.is_whitespace() {
                        name.clear();
                        value.clear();
                        name.push(ch);
                        state = ParserState::ReadingName;
                    }
                }
                ParserState::ReadingName => {
                    if ch.is_alphabetic() {
                        name.push(ch);
                    } else if ch == '=' {
                        state = ParserState::ReadyForValue;
                    }
                }
                ParserState::ReadyForValue => {
                    if ch == '"' {
                        quote_char = Some(ch);
                        state = ParserState::ReadingValue;
                    } else if !ch.is_whitespace() {
                        value.push(ch);
                        quote_char = None;
                        state = ParserState::ReadingValue;
                    }
                }
                ParserState::ReadingValue => {
                    if Some(ch) == quote_char || (quote_char.is_none() && ch.is_whitespace()) {
                        store_figure_attribute(&mut result, &name, &value);
                        name.clear();
                        value.clear();
                        state = ParserState::ReadyForName;
                    } else {
                        value.push(ch);
                    }
                }
            }
        }

        if state == ParserState::ReadingValue && !name.is_empty() {
            store_figure_attribute(&mut result, &name, &value);
        }
    } else {
        // USFM2 format - attributes separated by pipes
        result.usfm_version = 2;

        let parts: Vec<&str> = figure_attribute_string.split('|').collect();
        for (i, part) in parts.iter().enumerate() {
            if i < FIGURE_ATTR_NAMES_USFM2.len() {
                store_figure_attribute_by_name(&mut result, FIGURE_ATTR_NAMES_USFM2[i], part);
            }
        }
    }

    Ok(result)
}

fn store_figure_attribute(result: &mut UsfmFigureAttributes, name: &str, value: &str) {
    // Convert short USFM3 names to better names
    let better_name = FIGURE_ATTR_NAMES_USFM3
        .iter()
        .position(|&n| n == name)
        .map(|i| BETTER_ATTR_NAMES_USFM3[i])
        .unwrap_or(name);

    store_figure_attribute_by_name(result, better_name, value);
}

fn store_figure_attribute_by_name(result: &mut UsfmFigureAttributes, name: &str, value: &str) {
    let value = if value.is_empty() {
        None
    } else {
        Some(value.to_string())
    };

    match name {
        "caption" => result.caption = value,
        "altDescription" => result.alt_description = value,
        "sourceFilename" => result.source_filename = value,
        "relativeSize" => result.relative_size = value,
        "locationOrRange" => result.location_or_range = value,
        "copyrightOrRightsHolder" => result.copyright_or_rights_holder = value,
        "referenceCV" => result.reference_cv = value,
        _ => {} // Unknown attribute
    }
}

/// Abbreviate a string to `head…tail` if it exceeds `MAX_CHARS` characters,
/// keeping `KEEP` characters on each side. Returns the original string if short enough.
///
/// Uses a ring buffer to find the tail offset in a single pass over the string,
/// handling multi-byte characters correctly.
pub fn abbreviate<const MAX_CHARS: usize, const KEEP: usize>(s: &str) -> String {
    let mut head_end = 0;
    let mut count = 0;
    let mut indexes = [0; KEEP];
    let mut indexes_current = 0;
    for (byte_offset, _) in s.char_indices() {
        if count == KEEP {
            head_end = byte_offset;
        }
        indexes_current = (indexes_current + 1) % KEEP;
        indexes[indexes_current] = byte_offset;
        count += 1;
    }
    if count <= MAX_CHARS {
        return s.to_string();
    }
    format!("{}…{}", &s[..head_end], &s[indexes[(indexes_current + 1) % KEEP]..])
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_get_small_leading_int() {
        assert_eq!(get_small_leading_int("17").unwrap(), 17);
        assert_eq!(get_small_leading_int("17a").unwrap(), 17);
        assert_eq!(get_small_leading_int("17-25").unwrap(), 17);
        assert_eq!(get_small_leading_int("-1").unwrap(), -1);
        assert_eq!(get_small_leading_int("0").unwrap(), 0);
        assert_eq!(get_small_leading_int("123abc456").unwrap(), 123);
        assert!(get_small_leading_int("abc").is_err());
        assert!(get_small_leading_int("").is_err());
    }

    #[test]
    fn test_parse_word_attributes_simple_lemma() {
        let attrs = parse_word_attributes("word|lemma").unwrap();
        assert_eq!(attrs.word, "word");
        assert_eq!(attrs.lemma, Some("lemma".to_string()));
        assert_eq!(attrs.strong, None);
    }

    #[test]
    fn test_parse_word_attributes_named() {
        let attrs = parse_word_attributes(r#"word|lemma="test" strong="H1234""#).unwrap();
        assert_eq!(attrs.word, "word");
        assert_eq!(attrs.lemma, Some("test".to_string()));
        assert_eq!(attrs.strong, Some("H1234".to_string()));
    }

    #[test]
    fn test_parse_word_attributes_with_x_prefix() {
        let attrs = parse_word_attributes(r#"word|x-morph="verb""#).unwrap();
        assert_eq!(attrs.word, "word");
        assert_eq!(attrs.extra.get("morph"), Some(&"verb".to_string()));
    }

    #[test]
    fn test_parse_word_attributes_missing_pipe() {
        let result = parse_word_attributes("word");
        assert!(matches!(result, Err(ParseError::MissingPipeSeparator)));
    }

    #[test]
    fn test_parse_figure_attributes_usfm3() {
        let attrs = parse_figure_attributes(r#"At once they left.|src="avnt016.jpg" size="span" ref="1.18""#).unwrap();
        assert_eq!(attrs.usfm_version, 3);
        assert_eq!(attrs.caption, Some("At once they left.".to_string()));
        assert_eq!(attrs.source_filename, Some("avnt016.jpg".to_string()));
        assert_eq!(attrs.relative_size, Some("span".to_string()));
        assert_eq!(attrs.reference_cv, Some("1.18".to_string()));
    }

    #[test]
    fn test_parse_figure_attributes_usfm2() {
        let attrs = parse_figure_attributes("Description|file.jpg|span|loc|copyright|Caption|1:18").unwrap();
        assert_eq!(attrs.usfm_version, 2);
        assert_eq!(attrs.alt_description, Some("Description".to_string()));
        assert_eq!(attrs.source_filename, Some("file.jpg".to_string()));
        assert_eq!(attrs.relative_size, Some("span".to_string()));
        assert_eq!(attrs.location_or_range, Some("loc".to_string()));
        assert_eq!(attrs.copyright_or_rights_holder, Some("copyright".to_string()));
        assert_eq!(attrs.caption, Some("Caption".to_string()));
        assert_eq!(attrs.reference_cv, Some("1:18".to_string()));
    }
}
