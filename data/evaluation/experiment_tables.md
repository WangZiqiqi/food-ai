# Food-AI Experiment Tables

Generated from current 2026-06-03 repaired benchmark/freeze artifacts.

## Corpus and Graph Scale
| Artifact | Articles | Success | Errors | Merged claims | Evidence items | Multi-evidence claims | Unique subjects | Unique outcomes | Zero-claim articles | Over-specific foods |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 141-paper baseline | 141 | 141 | 0 | 700 | 722 | 18 | 215 | 464 | 44 | 27 |
| 850-paper current graph | 850 | 850 | 0 | 3786 | 4101 | 227 | 621 | 2555 | 103 | 159 |

## Claim Direction Distribution
| Artifact | Positive | Neutral | Negative |
| --- | ---: | ---: | ---: |
| 850-paper current graph | 2767 | 934 | 85 |

## QA Benchmark Composition
| Benchmark | Count | Description | Evidence lookup | Reason | Comparison | No-answer | Boundary |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Repaired clean graph-positive QA | 120 | 41 | 25 | 25 | 29 | 0 | 0 |
| Independent food-science v1 | 55 | 12 | 29 | 0 | 4 | 8 | 19 |

## Retrieval Evaluation on Repaired Clean 120
| Retrieval setting | Claim hit@10 | Claim recall@10 | PMID hit@10 | PMID recall@10 | PMID recall@20 | MRR |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Claim vectors, natural question | 1.0000 | 0.9889 | 1.0000 | 0.9924 | 0.9972 | 0.9572 |

## Full Agent Evaluation on Repaired Clean 120
| Question type | Count | Success rate | JSON parse rate | Claim recall | PMID hit | PMID recall | Avg. tool calls |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| comparison | 29 | 1.0000 | 1.0000 | 0.9885 | 1.0000 | 0.9885 | 38.76 |
| description | 41 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.9760 | 24.73 |
| evidence_lookup | 25 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 24.00 |
| reason | 25 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.9800 | 30.08 |
| overall | 120 | 1.0000 | 1.0000 | 0.9972 | 1.0000 | 0.9848 | 29.08 |

## Independent v1 Label-Repaired Evaluation
| Metric | Value |
| --- | ---: |
| count | 55 |
| graph_positive_count | 47 |
| no_answer_count | 8 |
| no_answer_correct | 1.0 |
| abstention_rate | 1.0 |
| pmid_labeled_count | 2 |
| pmid_recall | 1.0 |

## Independent v1 Expert Review
| Subset | Count | Usefulness | PMID traceability | Abstention/boundary honesty | Usefulness>=4 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Likely answerable | 28 | 4.482 | 0.964 | None | 0.929 |
| Boundary | 19 | 3.842 | 0.845 | 0.776 | 0.632 |
| Likely no-answer | 8 | 4.562 | 0.938 | 1.0 | 1.0 |
| Overall | 55 | 4.273 | 0.919 | 0.843 | 0.836 |

## Raw Abstract Document Vector Baseline on Repaired Clean 120
| Setting | Graph-positive count | PMID hit@10 | PMID recall@10 | PMID hit@20 | PMID recall@20 | False abstention |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Raw abstract natural top-20, no abstention | 120 | 0.8583 | 0.7323 | 0.9333 | 0.8308 | 0.0000 |
