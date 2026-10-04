# Canonical glossary

| Term | Meaning |
| --- | --- |
| security_id | Stable internal identity; ticker/exchange mappings are dated attributes. |
| session_date | Exchange-local date of a completed trading session, not a guessed weekday. |
| session_close_at / event_at | Actual session close or event instant. |
| published_at | Provider/source publication time; not fiscal-period end or ingestion. |
| available_at | Earliest evidenced historical knowledge eligibility or documented conservative bound. UNKNOWN is not eligible. |
| ingested_at | Actual time AlphaLens received the captured record. Live decisions also require this <= decision time. |
| effective_from / effective_to | Half-open applicability interval [from, to), independent of when an announcement was known. |
| revision_id | Source revision identity; new filings/corrections never overwrite prior knowledge. |
| period_end | Accounting period boundary, never a proxy for publication/availability. |
| point-in-time | Reconstructing eligible revisions, identifiers and universe for a historical decision timestamp. |
| survivorship bias | Distortion from analyzing only securities that survived to today. |
| leakage / look-ahead | Using future data, labels, normalization statistics or membership in historical decisions. |
| walk-forward | Sequential train/validate/test evaluation through time; no random-shuffle primary evaluation. |
| purging / embargo | Removing overlapping training labels and applying a justified temporal separation. |
| provenance | Source, revision, timestamps, origin, schema/version and lineage. |
| freshness | FRESH, STALE, DEGRADED, UNAVAILABLE under dataset/calendar-specific rules, to implement later. |
| capability UNKNOWN | No verified evidence; neither support nor unsupportedness is assumed. |
| TEST_ONLY | Constructed edge-case fixture, never historical/provider/performance evidence. |
| prediction | Versioned forecast, not an order or guarantee. |
| risk assessment | Independent constraints/flags/uncertainty that can block or downgrade a prediction. |
| explanation | Evidence-backed contributors, risks and invalidation; attribution is not causality. |
| Portfolio Guardian | Future manual-portfolio monitoring, valuation and risk-change alerts. |
| RPO / RTO | Acceptable data loss / recovery time; values not yet approved. |

Canonical signals: WATCH, SETUP_FORMING, ENTRY_SIGNAL, HOLD, TAKE_PROFIT_REVIEW,
EXIT_SIGNAL, EXITED. Numeric model/signal thresholds remain undefined.
