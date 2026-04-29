Rust package: bos_books_codes
(PyO3 package is in bos_books_codes_py)

# To update source table
cp -a /srv/FreelyGiven/BibleOrgSys/BibleOrgSys/DataFiles/DerivedFiles/BibleBooksCodes_Tables.tsv .

# To test
clear; cargo test --package bos_books_codes --lib -- tests --show-output
