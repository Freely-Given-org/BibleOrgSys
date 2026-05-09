# Intro

The Bible Organisational System (BibleOrgSys or BOS) located at [[https://GitHub.com/Freely-Given-org/BibleOrgSys]]
was originally written in Python 3.0 starting back around 2009
(when most Python libraries were not yet updated from Python 2, so it had few external dependencies).
It eventually grew into a large project that could easily import Bible originals and Bible translations
in a large range of formats, save them in memory and index them for easy retrieval,
and optionally export them in an almos equally large number of formats.
The main goal of BibleOrgSys was for the code to be easy to read,
and available even to a relative novice to perhaps add a mixing feature.

None of the code was optimised (as programming time was limited as secondary to actual Bible translation work),
and it ended up using a lot of memory,
as well as being relatively slow to run (although speed was always a lower priority).

Now in the mid-2020's with the easy availability of Rust and PyO3 tools,
the opportunity has arisen to convert many of the BOS internals to Rust.
This is primarily to use less memory when multiple Bibles are loaded,
but also offers the possibility of increased efficiency/speed.

The BOS has always attempted to use multiple cores to load Bibles
that store their books in separate files (e.g., USFM and ESFM).
We hope to improve that multiprocessing ability of the package
by also taking advantage of Rust's multiprocessing abilities.

The BOS has provided the Bible lookup for the [OpenBibleData (Bible website)](https://GitHub.com/Freely-Given-org/OpenBibleData)
and [Biblelator (Bible-translation editor)](https://GitHub.com/Freely-Given-org/Biblelator) Python projects.

Robert Hunt.
May 2026.
