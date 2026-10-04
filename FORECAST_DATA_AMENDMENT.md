# Data-quality amendment before forecast results — October 2, 2026

The original FORECAST_PLAN.md remains unchanged, SHA-256
`79639532752370666391452301efbf3dab828d6a3e9ae91bfd0ded94723d8a9b`.
The first run stopped in the December 2020 BTC warm-up file before fitting any
model, producing any forecast or computing performance. It created no results
directory. A schema-only audit then examined all 245 checksum-verified archives:
2,147,125 rows, 29 rejected closing timestamps across 29 files. The full audit
is saved in `research/forecast_archive_audit.json` and its examples contain only
public timestamps. No return or forecast outcomes informed this amendment.

The original phrase "reject malformed records" is now made operationally
explicit for this observed timestamp fault: discard the ENTIRE affected bar as
unavailable, without repairing its timestamp or retaining its prices/volumes.
Its UTC day is incomplete and cannot enter the required 31-complete-day feature
window. A rejected 00:05 bar also makes its entry/exit label unavailable. Count
these rejected records separately from genuinely absent bars and keep both in
coverage diagnostics. Every original model, feature, sample, cost and progression
gate remains unchanged, including the coverage requirements.

Only the exact closing-timestamp fault receives this treatment. Invalid opening
times, wrong archive months, duplicates, disorder, wrong schema, other malformed
fields or invalid checksums still stop the study. Original files are preserved
byte-for-byte. The preceding opening-time ordering checks apply even to discarded
records, so skipping cannot conceal a duplicate or out-of-month bar.

This is a disclosed pre-result data-handling clarification, not a retrospective
change to improve performance. Both plan and amendment fingerprints are checked
by the runner. If coverage is insufficient, the study fails that gate; do not
reduce its threshold or shorten required history after seeing results.
