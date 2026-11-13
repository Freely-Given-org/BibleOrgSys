//! rkyv field wrappers.
//!
//! The in-memory forms of our entries and indexes are optimised for size
//! (interned marker IDs, boxed strings, shared lists),
//! but these wrappers archive them in exactly the same layout
//! as the simpler types that they replaced (strings and vectors),
//! so the serialised (.BOSBible) file format is unchanged.

use std::sync::Arc;

use rkyv::rancor::{Fallible, Source};
use rkyv::ser::{Allocator, Writer};
use rkyv::string::{ArchivedString, StringResolver};
use rkyv::vec::{ArchivedVec, VecResolver};
use rkyv::with::{ArchiveWith, DeserializeWith, SerializeWith};
use rkyv::{Archive, Deserialize, Place, Serialize};

use crate::marker_ids::MarkerId;

/// Archives a `MarkerId` as its marker string.
pub struct MarkerAsString;

impl ArchiveWith<MarkerId> for MarkerAsString {
    type Archived = ArchivedString;
    type Resolver = StringResolver;

    fn resolve_with(field: &MarkerId, resolver: Self::Resolver, out: Place<Self::Archived>) {
        ArchivedString::resolve_from_str(field.as_str(), resolver, out);
    }
}

impl<S> SerializeWith<MarkerId, S> for MarkerAsString
where
    S: Fallible + Writer + ?Sized,
    S::Error: Source,
{
    fn serialize_with(field: &MarkerId, serializer: &mut S) -> Result<Self::Resolver, S::Error> {
        ArchivedString::serialize_from_str(field.as_str(), serializer)
    }
}

impl<D: Fallible + ?Sized> DeserializeWith<ArchivedString, MarkerId, D> for MarkerAsString {
    fn deserialize_with(field: &ArchivedString, _: &mut D) -> Result<MarkerId, D::Error> {
        Ok(MarkerId::intern(field.as_str()))
    }
}

/// Archives a `Box<str>` as a string.
pub struct BoxStrAsString;

impl ArchiveWith<Box<str>> for BoxStrAsString {
    type Archived = ArchivedString;
    type Resolver = StringResolver;

    fn resolve_with(field: &Box<str>, resolver: Self::Resolver, out: Place<Self::Archived>) {
        ArchivedString::resolve_from_str(field, resolver, out);
    }
}

impl<S> SerializeWith<Box<str>, S> for BoxStrAsString
where
    S: Fallible + Writer + ?Sized,
    S::Error: Source,
{
    fn serialize_with(field: &Box<str>, serializer: &mut S) -> Result<Self::Resolver, S::Error> {
        ArchivedString::serialize_from_str(field, serializer)
    }
}

impl<D: Fallible + ?Sized> DeserializeWith<ArchivedString, Box<str>, D> for BoxStrAsString {
    fn deserialize_with(field: &ArchivedString, _: &mut D) -> Result<Box<str>, D::Error> {
        Ok(field.as_str().into())
    }
}

/// Archives a `Box<[T]>` or an `Arc<[T]>` exactly like a `Vec<T>`.
pub struct SliceAsVec;

macro_rules! impl_slice_as_vec {
    ($container:ident) => {
        impl<T: Archive> ArchiveWith<$container<[T]>> for SliceAsVec {
            type Archived = ArchivedVec<T::Archived>;
            type Resolver = VecResolver;

            fn resolve_with(field: &$container<[T]>, resolver: Self::Resolver, out: Place<Self::Archived>) {
                ArchivedVec::resolve_from_len(field.len(), resolver, out);
            }
        }

        impl<T, S> SerializeWith<$container<[T]>, S> for SliceAsVec
        where
            T: Serialize<S>,
            S: Fallible + Allocator + Writer + ?Sized,
        {
            fn serialize_with(field: &$container<[T]>, serializer: &mut S) -> Result<Self::Resolver, S::Error> {
                ArchivedVec::serialize_from_slice(field, serializer)
            }
        }

        impl<T, D> DeserializeWith<ArchivedVec<T::Archived>, $container<[T]>, D> for SliceAsVec
        where
            T: Archive,
            D: Fallible + ?Sized,
            ArchivedVec<T::Archived>: Deserialize<Vec<T>, D>,
        {
            fn deserialize_with(field: &ArchivedVec<T::Archived>, deserializer: &mut D) -> Result<$container<[T]>, D::Error> {
                let vec: Vec<T> = field.deserialize(deserializer)?;
                Ok(vec.into())
            }
        }
    };
}
impl_slice_as_vec!(Box);
impl_slice_as_vec!(Arc);

/// Archives a `u32` in the same way as a `usize`.
pub struct U32AsUsize;

impl ArchiveWith<u32> for U32AsUsize {
    type Archived = rkyv::Archived<usize>;
    type Resolver = ();

    fn resolve_with(field: &u32, _: Self::Resolver, out: Place<Self::Archived>) {
        (*field as usize).resolve((), out);
    }
}

impl<S: Fallible + ?Sized> SerializeWith<u32, S> for U32AsUsize {
    fn serialize_with(_: &u32, _: &mut S) -> Result<Self::Resolver, S::Error> {
        Ok(())
    }
}

impl<D: Fallible + ?Sized> DeserializeWith<rkyv::Archived<usize>, u32, D> for U32AsUsize {
    fn deserialize_with(field: &rkyv::Archived<usize>, _: &mut D) -> Result<u32, D::Error> {
        Ok(field.to_native() as u32)
    }
}
