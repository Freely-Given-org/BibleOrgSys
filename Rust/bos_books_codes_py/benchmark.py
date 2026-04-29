import timeit
import bos_books_codes_py  # This is the PyO3/Rust module you built
import sys

sys.path.insert( 0, '/srv/FreelyGiven/BibleOrgSys/' )
from BibleOrgSys import BibleOrgSysGlobals

LAST_MODIFIED_DATE = '2025-10-23' # by RJH
SHORT_PROGRAM_NAME = "BenchmarkBibleBooksCodes"
PROGRAM_NAME = "Bible Books Codes benchmark"
PROGRAM_VERSION = '0.10'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False

# Configure basic Bible Organisational System (BOS) set-up
parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )
BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

BBB = 'KI1'
USFM = '1Ki'
OSIS = 'Exod'
text = '1 Cor'
number = 1_000_000

# Time Python
python_time = timeit.timeit(lambda: BibleOrgSysGlobals.loadedBibleBooksCodes.getUSFMAbbreviation(BBB), number=number)
print(f"\nNative Python getUSFMAbbreviation function: {python_time:.4f} seconds (or {python_time*1_000_000_000/number:.1f} ns per run)")
# Time Rust
rust_time = timeit.timeit(lambda: bos_books_codes_py.reference_abbrev_to_usfm_abbrev_py(BBB), number=number)
print(f"Rust PyO3 reference_abbrev_to_usfm_abbrev_py function: {rust_time:.4f} seconds (or {rust_time*1_000_000_000/number:.1f} ns per run)")
# Compare
if python_time < rust_time:
    print(f"Python was {rust_time/python_time:.1f} times faster.")
elif python_time > rust_time:
    print(f"Rust was {python_time/rust_time:.1f} times faster.")

# Time Python
python_time = timeit.timeit(lambda: BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromUSFMAbbreviation(USFM), number=number)
print(f"\nNative Python getBBBFromUSFMAbbreviation function: {python_time:.4f} seconds (or {python_time*1_000_000_000/number:.1f} ns per run)")
# Time Rust
rust_time = timeit.timeit(lambda: bos_books_codes_py.usfm_abbrev_to_reference_abbrev_py(USFM), number=number)
print(f"Rust PyO3 usfm_abbrev_to_reference_abbrev_py function: {rust_time:.4f} seconds (or {rust_time*1_000_000_000/number:.1f} ns per run)")
# Compare
if python_time < rust_time:
    print(f"Python was {rust_time/python_time:.1f} times faster.")
elif python_time > rust_time:
    print(f"Rust was {python_time/rust_time:.1f} times faster.")

# Both functions
# Time Python
python_time = timeit.timeit(lambda: BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromUSFMAbbreviation(BibleOrgSysGlobals.loadedBibleBooksCodes.getUSFMAbbreviation(BBB)), number=number)
print(f"\nNative Python both functions: {python_time:.4f} seconds (or {python_time*1_000_000_000/number:.1f} ns per run)")
# Time Rust
rust_time = timeit.timeit(lambda: bos_books_codes_py.usfm_abbrev_to_reference_abbrev_py(bos_books_codes_py.reference_abbrev_to_usfm_abbrev_py(BBB)), number=number)
print(f"Rust PyO3 both functions: {rust_time:.4f} seconds (or {rust_time*1_000_000_000/number:.1f} ns per run)")
# Compare
if python_time < rust_time:
    print(f"Python was {rust_time/python_time:.1f} times faster.")
elif python_time > rust_time:
    print(f"Rust was {python_time/rust_time:.1f} times faster.")

# Time Python
python_time = timeit.timeit(lambda: BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromOSISAbbreviation(OSIS), number=number)
print(f"\nNative Python getBBBFromOSISAbbreviation function: {python_time:.4f} seconds (or {python_time*1_000_000_000/number:.1f} ns per run)")
# Time Rust
rust_time = timeit.timeit(lambda: bos_books_codes_py.osis_abbrev_to_reference_abbrev_py(OSIS), number=number)
print(f"Rust PyO3 osis_abbrev_to_reference_abbrev_py function: {rust_time:.4f} seconds (or {rust_time*1_000_000_000/number:.1f} ns per run)")
# Compare
if python_time < rust_time:
    print(f"Python was {rust_time/python_time:.1f} times faster.")
elif python_time > rust_time:
    print(f"Rust was {python_time/rust_time:.1f} times faster.")

# Time Python
python_time = timeit.timeit(lambda: BibleOrgSysGlobals.loadedBibleBooksCodes.getBBBFromEnglishText(text), number=number)
print(f"\nNative Python getBBBFromEnglishText function: {python_time:.4f} seconds (or {python_time*1_000_000_000/number:.1f} ns per run)")
# Time Rust
rust_time = timeit.timeit(lambda: bos_books_codes_py.english_name_to_reference_abbrev_py(text), number=number)
print(f"Rust PyO3 english_name_to_reference_abbrev_py function: {rust_time:.4f} seconds (or {rust_time*1_000_000_000/number:.1f} ns per run)")
# Compare
if python_time < rust_time:
    print(f"Python was {rust_time/python_time:.1f} times faster.")
elif python_time > rust_time:
    print(f"Rust was {python_time/rust_time:.1f} times faster.")


BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
