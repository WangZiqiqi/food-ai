# Independent food science questions v1 — expert review summary

- Reviewed file: `data/evaluation/independent_food_science_questions_v1_reviewed.csv`
- Source agent results: `data/evaluation/independent_questions_v1_agent_results.json`
- Date: 2026-06-03
- Scales: answer_usefulness 1–5; pmid_traceability 0–1; abstention_correct 0–1 for no-answer/boundary honesty.
- Label repair: `ind_048` and `ind_052` were corrected from no-answer probes to boundary evidence questions after the rebuilt graph surfaced direct evidence.

## Overall

- count: 55
- avg_answer_usefulness: 4.273
- avg_pmid_traceability: 0.919
- avg_abstention_or_boundary_honesty: 0.843
- usefulness_ge4_rate: 0.836
- traceability_ge075_rate: 0.964

## By a priori expectation

| expectation | count | usefulness | traceability | abstention/boundary honesty | usefulness>=4 | traceability>=0.75 |
|---|---:|---:|---:|---:|---:|---:|
| boundary | 19 | 3.842 | 0.845 | 0.776 | 0.632 | 0.895 |
| likely_answerable | 28 | 4.482 | 0.964 | None | 0.929 | 1.0 |
| likely_no_answer | 8 | 4.562 | 0.938 | 1.0 | 1.0 | 1.0 |

## Follow-up cases

- **ind_008** usefulness=3.5, traceability=0.75, honesty=None: Covers both kefir and probiotic yogurt, but the comparative conclusion that kefir is more consistent is somewhat stronger than the heterogeneous evidence warrants.
- **ind_012** usefulness=3.0, traceability=0.5, honesty=0.5: Partially useful but overstates kombucha evidence for human gut microbiota; much support is review/animal or salivary microbiota rather than direct human fecal gut microbiota.
- **ind_015** usefulness=3.5, traceability=0.75, honesty=0.5: Useful but somewhat overconfident for hard CVD endpoints; much evidence is observational, surrogate, or broad fermented-food category rather than direct clinical endpoint evidence.
- **ind_017** usefulness=3.5, traceability=0.75, honesty=None: Generally supported TNF-alpha answer, but mixes human supplementation, fermented milk, enteral nutrition, vaginal/animal-model evidence; should be more restrictive.
- **ind_021** usefulness=3.5, traceability=0.75, honesty=0.8: Relevant but intersection is thin; direct waist evidence is partly diet-combined or WHR rather than waist circumference alone. Caveats are adequate.
- **ind_035** usefulness=3.0, traceability=0.75, honesty=0.5: Partially useful but overstates kefir anticarcinogenic activity; evidence is mainly review/preclinical and should not be phrased as established health effect.
- **ind_036** usefulness=3.5, traceability=0.75, honesty=0.5: Useful outcome inventory for kimchi but over-broad "numerous health benefits" framing; several claims are review/observational and need stronger caveats.
- **ind_038** usefulness=2.5, traceability=0.5, honesty=0.25: Weak boundary handling: miso-specific evidence is glycemic/HbA1c, not direct cardiovascular or cancer endpoints; cancer evidence is broad fermented-food/preclinical and answer overclaims.
- **ind_050** usefulness=3.0, traceability=0.75, honesty=0.5: Boundary answer is useful but overstates "fermented foods prevent Alzheimer's"; evidence is mainly probiotics/reviews and should be framed as possible slowing or cognitive support, not prevention.
