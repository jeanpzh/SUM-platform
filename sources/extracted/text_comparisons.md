# Extracted-text comparison notes

Normalized whitespace/case comparisons are candidate signals. Exact page-subdocument matches are reported separately from whole-file hashes.
Only locally extracted text is compared; differences in annexes, amendment clauses, signatures, tables, and scans require visual review.

- DOC-083 vs DOC-084: similarity=0.8521; retain as separate records pending clause/page diff.
- DOC-072 vs DOC-096: NOT_COMPARED; one or both candidate files are not locally present.
- DOC-005 vs DOC-079 p.1–2: normalized extracted text similarity=1.00000; byte hashes remain distinct because DOC-079 is a 2-page RR plus 18-page annex bundle. Keep DOC-005 (approval) and DOC-002 (annex) as distinct logical documents; retain the DOC-079 URL as a matching source for both components.
- DOC-002 vs DOC-079 p.3–20: normalized extracted text similarity=1.00000; byte hashes remain distinct because DOC-079 is a 2-page RR plus 18-page annex bundle. Keep DOC-005 (approval) and DOC-002 (annex) as distinct logical documents; retain the DOC-079 URL as a matching source for both components.
