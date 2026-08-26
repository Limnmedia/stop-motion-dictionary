# Candidate Normalization Report

This is a review queue, not an automatic page-creation plan. No database rows or Markdown pages were changed.

Candidates classified: 1324

| Classification | Count |
|---|---:|
| NEW TERM | 166 |
| ALIAS | 108 |
| MERGE/DUPLICATE | 30 |
| NOT A TERM | 4 |
| REVIEW | 1016 |

`normalized_candidate_terms.tsv` preserves the candidate label, graph evidence, nearest existing term, similarity score, and classification rationale.

Classification rules are conservative: repeated unresolved labels are provisional `NEW TERM` candidates; one-off labels remain `REVIEW`; close lexical matches are `ALIAS` or `MERGE/DUPLICATE`; structural labels are `NOT A TERM`.
