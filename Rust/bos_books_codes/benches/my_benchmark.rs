use criterion::{Criterion, criterion_group, criterion_main};
use std::hint::black_box;

use bos_books_codes::{reference_abbrev_to_usfm_abbrev, usfm_abbrev_to_reference_abbrev, osis_abbrev_to_reference_abbrev, english_name_to_reference_abbrev};

pub fn criterion_benchmark1(c: &mut Criterion) {
    c.bench_function("BBB to USFM to BBB", |b| {
        b.iter(|| {
            usfm_abbrev_to_reference_abbrev(
                reference_abbrev_to_usfm_abbrev(black_box("KI1")).unwrap(),
            )
        })
    });
}

pub fn criterion_benchmark2(c: &mut Criterion) {
    c.bench_function("English text to BBB", |b| {
        b.iter(|| {
            usfm_abbrev_to_reference_abbrev(
                english_name_to_reference_abbrev(black_box("1 Cor")).unwrap(),
            )
        })
    });
}

criterion_group!(benches, criterion_benchmark1, criterion_benchmark2);
criterion_main!(benches);
