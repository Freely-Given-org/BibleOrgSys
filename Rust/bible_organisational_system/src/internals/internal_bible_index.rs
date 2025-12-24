use std::collections::HashMap;
// use std::error::Error;
use std::io::{Error, ErrorKind};
use std::{fmt, usize};


// #[derive(Debug, PartialEq)]
// pub enum LookupError<'a> {
//     CVNotFound(&'a (&'a str, &'a str)),
//     // ValueIsNone(String),
// }

// impl<'a> fmt::Display for LookupError<'a> {
//     #[inline]
//     fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
//         match self {
//             LookupError::CVNotFound(t,k) => write!(f, "{} abbreviation '{}' not found", t,k),
//             // LookupError::ValueIsNone(k) => write!(f, "Key '{}' found but value is None", k),
//         }
//     }
// }

// impl Error for LookupError<'_> {}


#[derive(Debug)]
pub enum MarkerStringError {
    InvalidLength(usize),
    NotAllowed(String),
}

impl fmt::Display for MarkerStringError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            MarkerStringError::InvalidLength(c) =>
                write!(f, "MarkerString length must be between 1 and 4 characters (not {})", c),
            MarkerStringError::NotAllowed(s) =>
                write!(f, "MarkerString `{}` is not an allowed value", s),
        }
    }
}

const ALLOWED_MARKER_STRINGS: &[&str] = &["s1","s2","s3", "p", "q1", "q2"];

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MarkerString(String);

impl MarkerString {
    pub fn new(s: impl Into<String>) -> Result<Self, MarkerStringError> {
        let s = s.into();
        let len = s.len(); // For byte-length (because USFM/ESFM markers are ASCII only)

        if !(1..=4).contains(&len) {
            return Err(MarkerStringError::InvalidLength(len));
        }

        if !ALLOWED_MARKER_STRINGS.contains(&s.as_str()) {
            return Err(MarkerStringError::NotAllowed(s));
        }

        Ok(Self(s))
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}


#[derive(Debug)]
pub struct InternalBibleLine {
    pub marker: MarkerString,
    pub text: String,
}

impl InternalBibleLine {
    pub fn new(marker: MarkerString, text: String) -> Self {
        Self {
            marker, text,
        }
    }
}


#[derive(Debug)]
pub struct InternalBibleLines {
    pub lines: Vec<InternalBibleLine>,
}

impl InternalBibleLines {
    pub fn new(lines: Vec<InternalBibleLine>) -> Self {
        Self {
            lines,
        }
    }
    pub fn len(&self) -> usize {
        self.lines.len()
    }
    pub fn add_line(&mut self, line: InternalBibleLine) {
        self.lines.push(line);
    }
}


#[derive(Debug)]
pub struct InternalBibleBookCVIndexEntry {
    pub entry_index: usize,
    pub entry_count: u16,
    pub context: Vec<MarkerString>,
}

impl InternalBibleBookCVIndexEntry {
    pub fn new(entry_index: usize, entry_count: u16, context: Vec<MarkerString>) -> Self {
        Self {
            entry_index,
            entry_count,
            context,
        }
    }
}



#[derive(Debug)]
pub struct InternalBibleBookCVIndex<'a> {
    pub work_name: &'a str,
    pub book_code: &'a str,
    given_entries: &'a Vec<InternalBibleBookCVIndexEntry>,
    cv_index_map: HashMap<(&'a str, &'a str), usize>, // Key is (chapter,verse), Value is index into given_entries
}

impl<'a> InternalBibleBookCVIndex<'a> {
    pub fn new(work_name: &'a str, book_code: &'a str, given_entries: &'a Vec<InternalBibleBookCVIndexEntry>) -> Self {
        Self {
            work_name,
            book_code,
            given_entries,
            cv_index_map: HashMap::new(), // Empty -- to be filled in later
        }
    }

    // pub fn build_index_map(&mut self){
    //     for (i, cv) in self.given_entries.iter().enumerate() {
    //         self.cv_index_map.insert(*cv, i);
    //     }
    // }

    pub fn get_verse_entries(&self, cv:&(&str,&str), strict:bool) -> Result<&[InternalBibleBookCVIndexEntry], Error> {
        // If strict is false, after failing a dictionary lookup,
        // it will also loop through the index looking for bridged verses starting with that verse
        println!("get_verse_entries( {:?} {})", cv, strict);
        let array_index:usize = *self.cv_index_map.get(cv).ok_or_else(|| Error::new(ErrorKind::NotFound, format!("CV key '{}:{}' not found in {}", cv.0, cv.1, self.book_code)))?;
        println!("   got array_index = {})", array_index);
        let index_entry = self.given_entries.get(array_index).unwrap();
        println!("   got index_entry = {:?})", index_entry);
        let index_count:u16 = index_entry.entry_count;
        println!("   got index_count = {:?})", index_count);
        Ok(&self.given_entries[array_index..array_index+index_count as usize])
    }
}

pub fn add_numbers(a: i32, b: i32) -> i32 {
    a + b
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_bible_line() {
        let test_bible_line = &InternalBibleLine::new(MarkerString::new("s1".to_string()).unwrap(), "Some text".to_string());
        println!("Got a test line {:?}", test_bible_line);
    }

    #[test]
    fn test_bible_lines() {
        let test_bible_lines = &InternalBibleLines::new(vec![InternalBibleLine::new(MarkerString::new("s1".to_string()).unwrap(), "Some text".to_string())]);
        println!("Got test lines {:?}", test_bible_lines);
    }

    #[test]
    fn test_bible_lines_add_line() {
        let test_bible_lines = &mut InternalBibleLines::new(vec![InternalBibleLine::new(MarkerString::new("s1".to_string()).unwrap(), "Some text".to_string())]);
        println!("Got test lines {:?}", test_bible_lines);
        test_bible_lines.add_line(InternalBibleLine::new(MarkerString::new("p".to_string()).unwrap(), "Some more text".to_string()));
        println!("Got {} test lines after adding a line {:?}", test_bible_lines.len(), test_bible_lines);
    }

    #[test]
    fn test_cv_index_entry() {
        let test_cv_index_entry = &InternalBibleBookCVIndexEntry::new(456, 12, vec![MarkerString::new("s1".to_string()).unwrap(), MarkerString::new("p".to_string()).unwrap()]);
        println!("Got a test index entry {:?}", test_cv_index_entry);
    }

    #[test]
    fn test_cv_index_get_verse_entries() {
        let mut test_entries: Vec<InternalBibleBookCVIndexEntry> = vec![
            InternalBibleBookCVIndexEntry::new(0, 2, vec![MarkerString::new("s1".to_string()).unwrap(), MarkerString::new("p".to_string()).unwrap()]),
            InternalBibleBookCVIndexEntry::new(2, 1, vec![MarkerString::new("s2".to_string()).unwrap(), MarkerString::new("q1".to_string()).unwrap()]),
            InternalBibleBookCVIndexEntry::new(3, 1, vec![MarkerString::new("s3".to_string()).unwrap(), MarkerString::new("p".to_string()).unwrap()]),
        ];
        let test_cv_index = &InternalBibleBookCVIndex::new("My Bible", "ABC", &mut test_entries);
        println!("Got a test index {:?}", test_cv_index);
        let result = test_cv_index.get_verse_entries(&("1","2"), true);
        println!("Got a {} test index result {:?}", result.as_ref().map(|r| r.len()).unwrap_or(0), result);
    }
}
