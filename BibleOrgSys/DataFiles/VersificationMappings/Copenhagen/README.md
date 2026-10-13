#  Copenhagen Alliance Versification Working Group

This directory contains work by the Versification Working Group of the Copenhagen Alliance.  The Working Group members are:

- Mark Howe, United Bible Societies
- David Instone-Brewer, Tyndale House
- Chris Vaughn, YouVersion
- Andi Wu, Global Bible Initiative
- Tim Steenwyk, SIL International
- Jonathan Robie, SIL International

Software that needs to align resources or resolve references in links faces a challenge:  there are many versification schemes, so the same verse reference may not refer to the same text across manuscripts, critical editions, and translations.  The Versification Working Group is working to help software systems bridge across these versification schemes.

Here are the deliverables this Working Group is working on.

## Versification Mappings

A **versification mapping** identifies the versification of a specific Scripture text by describing how it differs from a base text. The `versification-mappings` directory specifies a JSON format for versification mappings. The JSON format was created by Mark Howe of UBS, based on the VRS versification format used in Paratext.

## Versification Sniffing

**Versification sniffing** refers to applying a set of rules to a Scripture text in order to identify its versification.  The original set of rules used for this was created by David Instone-Brewer.  The JSON format was created by Chris Vaughn and Jonathan Robie.
