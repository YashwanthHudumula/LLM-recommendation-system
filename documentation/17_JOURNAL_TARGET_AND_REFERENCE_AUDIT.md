# Journal target and reference audit

Audit date: **2026-08-25**

## Target

Primary target: **Information Processing & Management (Elsevier)**.

The journal's official scope covers computing and information science, including social computing and related information-system research. Its current journal page reports a 2025 CiteScore of 18.6 and Impact Factor of 6.9. Current third-party category data displayed during this audit place the journal in Q1; quartile assignments can change by database, category, and year, so the submitting author must recheck the desired ranking source on submission day.

The manuscript is prepared as an anonymized, single-column Word article with an abstract below 250 words, six keywords, separate highlights, and restrained scholarly styling. The live author guide was not reliably retrievable in this environment, so the editorial portal remains the authority for final limits and files.

Official journal page: https://www.sciencedirect.com/journal/information-processing-and-management

Official author-guide endpoint: https://www.sciencedirect.com/journal/information-processing-and-management/publish/guide-for-authors

Ranking cross-check used on the audit date: https://www.letpub.com/journal-selector/journal/3564

## Reference verification decisions

- Zhang et al. (2023), FaiRLLM: DOI 10.1145/3604915.3608860.
- Jiang et al. (2024), item-side fairness: DOI 10.1145/3589334.3648158.
- Sah and Lian (2025), PerFairX: DOI 10.1109/ICCVW69036.2025.00289.
- Deldjoo and Di Noia, CFaiRLLM: final ACM TIST record verified, DOI 10.1145/3725853.
- Sah et al. (2025), FairEval: retained explicitly as arXiv preprint, DOI 10.48550/arXiv.2504.07801.
- Sah et al. (2026), uncertainty/fairness awareness: retained explicitly as arXiv preprint, DOI 10.48550/arXiv.2602.02582.
- Rotar et al. (2026), prompted provider exposure: retained explicitly as arXiv preprint, DOI 10.48550/arXiv.2603.12935.
- Classic exposure, evaluation, personality-item-pool, and dataset references were checked against their DOI landing metadata.
- The proposal citation “Ma et al. (2026), Rethinking Fairness in LLM-Based Recommender Systems, arXiv:2606.28340” was excluded because a targeted arXiv/title search did not verify the record.

## Submission cautions

Q1 is a ranking status, not an acceptance guarantee. The empirical contribution should be presented as a controlled audit of frozen model snapshots, not as a universal causal claim. The author team must complete identities, affiliations, CRediT roles, funding, competing interests, acknowledgments, repository DOI, and any institutional ethics determination before submission.

## Manuscript artifact gate

The anonymized Word manuscript is `manuscript/IPM_anonymized_manuscript_v1.docx`, SHA-256
`89bad3f3a5970067fc367480f7d5129b5fba09410c9450487f61c4323626c561`.

- 4,190 source words; 248-word abstract; six keywords.
- Five highlights, each 68–83 characters (all below 85).
- Five embedded 400-DPI figures and two in-text summary tables.
- Thirteen rendered pages inspected at original resolution.
- Table-header and image-alt accessibility audit: zero high, medium, or low findings.
- Privacy scrub completed after accessibility normalization.
- Final visual QA accepted after correcting a split table header and an orphaned discussion
  heading; the first eight pages of the final rerender were byte-identical to the already
  inspected preceding render, and pages 9–13 were inspected again.

The manuscript deliberately withholds author identity, funding, competing interests, public
repository URL, and archival DOI. `manuscript/TITLE_PAGE_REQUIRED_FIELDS.md` is the handoff
checklist for those submission-time fields.
