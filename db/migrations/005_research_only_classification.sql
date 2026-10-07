-- D69 research classification propagation only. Production remains excluded.
-- No financial, knowledge-time, identity or eligibility rules are changed.
ALTER TABLE canonical.securities
    DROP CONSTRAINT IF EXISTS securities_classification_check;
ALTER TABLE canonical.securities
    ADD CONSTRAINT securities_classification_check
    CHECK (classification IN ('TEST_ONLY', 'RESEARCH_FIXTURE', 'RESEARCH_ONLY'));

ALTER TABLE canonical.record_revisions
    DROP CONSTRAINT IF EXISTS record_revisions_classification_check;
ALTER TABLE canonical.record_revisions
    ADD CONSTRAINT record_revisions_classification_check
    CHECK (classification IN ('TEST_ONLY', 'RESEARCH_FIXTURE', 'RESEARCH_ONLY'));
