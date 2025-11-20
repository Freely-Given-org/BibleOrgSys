use std::collections::HashMap;
//use std::error::Error;
use std::io::{Error, ErrorKind};
// use std::fmt;


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
pub struct InternalBibleBookCVIndexEntry {
    pub entry_index: usize,
    pub entry_count: u16,
    pub context: String,
}

impl InternalBibleBookCVIndexEntry {
    pub fn new(entry_index: usize, entry_count: u16, context: impl Into<String>) -> Self {
        Self {
            entry_index,
            entry_count,
            context: context.into(),
        }
    }
}



#[derive(Debug)]
pub struct InternalBibleBookCVIndex<'a> {
    pub work_name: &'a str,
    pub book_code: &'a str,
    given_entries: &'a mut Vec<String>,
    cv_index_map: HashMap<(&'a str, &'a str), usize>,
}

impl<'a> InternalBibleBookCVIndex<'a> {
    pub fn new(work_name: &'a str, book_code: &'a str, given_entries: &'a mut Vec<String>) -> Self {
        Self {
            work_name,
            book_code,
            given_entries,
            cv_index_map: HashMap::new(),
        }
    }

    pub fn get_verse_entries(&self, cv:&(&str,&str), strict:bool) -> Result<String, Error> {
        // If strict is false, after failing a dictionary lookup,
        // it will also loop through the index looking for bridged verses starting with that verse
        // let array_index:usize = *self.cv_index_map.get(cv).ok_or_else(|| Error::new(ErrorKind::NotFound, format!("CV key '{}:{}' not found in {}", cv.0, cv.1, self.book_code)))?;
        // Ok(self.given_entries.get(array_index).unwrap().clone()) // How expensive is this clone?
        println!("get_verse_entries( {:?} {})", cv, strict);
        let array_index:usize = *self.cv_index_map.get(cv).ok_or_else(|| Error::new(ErrorKind::NotFound, format!("CV key '{}:{}' not found in {}", cv.0, cv.1, self.book_code)))?;
        println!("   got array_index = {})", array_index);
        let index_entry = self.given_entries.get(array_index).unwrap();
        println!("   got index_entry = {:?})", index_entry);
        Ok(self.given_entries[array_index..array_index+).unwrap().clone()) // How expensive is this clone?
    }
}



pub fn add_numbers(a: i32, b: i32) -> i32 {
    a + b
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_cv_index_entry() {
        let test_cv_index_entry = &InternalBibleBookCVIndexEntry::new(123, 456, "My context");
        println!("Got a test index entry {:?}", test_cv_index_entry);
    }

    #[test]
    fn test_cv_index() {
        let mut test_entries = vec!["String1".to_string(),"String2".to_string()];
        let test_cv_index = &InternalBibleBookCVIndex::new("My Bible", "ABC", &mut test_entries);
        println!("Got a test index {:?}", test_cv_index);
        let result = test_cv_index.get_verse_entries(&("1","2"), true);
        println!("Got a test index result {:?}", result);
    }
}
