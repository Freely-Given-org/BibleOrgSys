use criterion::{Criterion, criterion_group, criterion_main};
use std::hint::black_box;

use bos_books_codes::{bos_book_code_to_usfm_abbrev, usfm_abbrev_to_bos_book_code, english_name_to_bos_book_code};

pub fn criterion_benchmark1(c: &mut Criterion) {
    c.bench_function("BBB to USFM to BBB", |b| {
        b.iter(|| {
            usfm_abbrev_to_bos_book_code(
                bos_book_code_to_usfm_abbrev(black_box("KI1")).unwrap().unwrap(),
            )
        })
    });
}

pub fn criterion_benchmark2(c: &mut Criterion) {
    c.bench_function("English text to BBB", |b| {
        b.iter(|| {
            english_name_to_bos_book_code(black_box("1 Cor")).unwrap()
        })
    });
}

criterion_group!(benches, criterion_benchmark1, criterion_benchmark2);
criterion_main!(benches);
