//! Interned marker IDs.
//!
//! Every `InternalBibleEntry` has a marker (e.g., `v~`, `s1`, `¬p`) and an original marker.
//! A whole Bible only uses a few dozen distinct markers,
//! so rather than storing the marker string in every entry (24 bytes each),
//! each distinct marker string is stored once (for the life of the process)
//! and the entries just hold a two-byte `MarkerId`.
//!
//! Looking up the string for an ID is lock-free (two memory reads).
//! Interning a string takes a read lock (or a write lock the first time that a marker is seen).

use std::collections::HashMap;
use std::sync::atomic::{AtomicPtr, Ordering};
use std::sync::{LazyLock, RwLock};

/// The maximum number of distinct markers that can be interned (as IDs are `u16`).
///
/// Real Bibles use well under a hundred, and even files with many custom or mistyped markers
/// only use a few hundred.
const MAX_MARKERS: usize = u16::MAX as usize + 1;

/// ID -> marker string. (A null pointer means that the ID hasn't been allocated yet.)
static MARKER_STRINGS: [AtomicPtr<&'static str>; MAX_MARKERS] =
    [const { AtomicPtr::new(std::ptr::null_mut()) }; MAX_MARKERS];

/// Marker string -> ID.
static MARKER_IDS: LazyLock<RwLock<HashMap<&'static str, u16>>> = LazyLock::new(|| RwLock::new(HashMap::new()));

/// A compact (two-byte) handle for an interned marker string.
///
/// Two `MarkerId`s are equal if and only if their marker strings are equal.
#[derive(Clone, Copy, PartialEq, Eq, Hash)]
pub struct MarkerId(u16);

impl MarkerId {
    /// Get the ID for the given marker string (allocating a new ID if it hasn't been seen before).
    ///
    /// # Panics
    ///
    /// Panics if more than 65,536 distinct markers are interned.
    pub fn intern(marker: &str) -> Self {
        // Fast path: we've seen this marker before
        if let Some(&id) = MARKER_IDS.read().unwrap_or_else(|e| e.into_inner()).get(marker) {
            return Self(id);
        }

        let mut ids = MARKER_IDS.write().unwrap_or_else(|e| e.into_inner());
        if let Some(&id) = ids.get(marker) { // Another thread might have just added it
            return Self(id);
        }
        let index = ids.len();
        assert!(index < MAX_MARKERS, "Too many distinct markers (over {MAX_MARKERS}) when adding {marker:?}");
        // These (few, small) strings are deliberately leaked -- they live for the life of the process
        let interned_marker: &'static str = Box::leak(marker.to_owned().into_boxed_str());
        let interned_ref: &'static mut &'static str = Box::leak(Box::new(interned_marker));
        MARKER_STRINGS[index].store(interned_ref, Ordering::Release);
        ids.insert(interned_marker, index as u16);
        Self(index as u16)
    }

    /// Get the marker string.
    #[inline]
    pub fn as_str(self) -> &'static str {
        let ptr = MARKER_STRINGS[self.0 as usize].load(Ordering::Acquire);
        debug_assert!(!ptr.is_null());
        // SAFETY: A `MarkerId` can only be created by `intern()` (the field is private),
        //  which stores a valid, leaked (so never freed or changed) pointer into this slot
        //  before the ID is returned.
        unsafe { *ptr }
    }
}

impl std::fmt::Debug for MarkerId {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{:?}", self.as_str())
    }
}

impl std::fmt::Display for MarkerId {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.as_str())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_intern_round_trip() {
        let v = MarkerId::intern("v~");
        let p = MarkerId::intern("¬p");
        assert_eq!(v.as_str(), "v~");
        assert_eq!(p.as_str(), "¬p");
        assert_ne!(v, p);
        assert_eq!(v, MarkerId::intern("v~"));
        assert_eq!(std::mem::size_of::<MarkerId>(), 2);
    }

    #[test]
    fn test_intern_from_many_threads() {
        let handles: Vec<_> = (0..8)
            .map(|_| {
                std::thread::spawn(|| {
                    (0..200)
                        .map(|n| {
                            let marker = format!("ztest{n}");
                            let id = MarkerId::intern(&marker);
                            assert_eq!(id.as_str(), marker);
                            id
                        })
                        .collect::<Vec<_>>()
                })
            })
            .collect();
        let results: Vec<Vec<MarkerId>> = handles.into_iter().map(|h| h.join().unwrap()).collect();
        for other in &results[1..] {
            assert_eq!(&results[0], other); // Every thread must have been given the same IDs
        }
    }
}
