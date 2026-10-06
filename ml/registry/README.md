# Registry boundary

P8's minimal local file registry lives in alphalens_training.artifacts, tightly
coupled to its contract/checksums/trusted local skops boundary. Storage is ignored
data/ or .local-data/. TEST_ONLY and research-only VALIDATED_BASELINE statuses;
no PRODUCTION status or promotion API. No hosted MLflow or deployed model.
See [P8 contract](../../docs/ml/p8-baseline-machine-learning.md).
