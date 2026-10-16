PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS experimental_forecasts (
    id TEXT PRIMARY KEY,
    model_id TEXT NOT NULL,
    instrument_key TEXT NOT NULL,
    observation_session TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    body TEXT NOT NULL,
    UNIQUE(model_id, instrument_key, observation_session)
);
CREATE TABLE IF NOT EXISTS experimental_outcomes (
    id TEXT PRIMARY KEY,
    forecast_id TEXT NOT NULL REFERENCES experimental_forecasts(id),
    revision INTEGER NOT NULL CHECK(revision>0),
    recorded_at TEXT NOT NULL,
    body TEXT NOT NULL,
    UNIQUE(forecast_id, revision)
);
CREATE TRIGGER IF NOT EXISTS experimental_forecasts_no_update
BEFORE UPDATE ON experimental_forecasts BEGIN SELECT RAISE(ABORT,'IMMUTABLE_FORECAST'); END;
CREATE TRIGGER IF NOT EXISTS experimental_forecasts_no_delete
BEFORE DELETE ON experimental_forecasts BEGIN SELECT RAISE(ABORT,'IMMUTABLE_FORECAST'); END;
CREATE TRIGGER IF NOT EXISTS experimental_outcomes_no_update
BEFORE UPDATE ON experimental_outcomes BEGIN SELECT RAISE(ABORT,'IMMUTABLE_OUTCOME'); END;
CREATE TRIGGER IF NOT EXISTS experimental_outcomes_no_delete
BEFORE DELETE ON experimental_outcomes BEGIN SELECT RAISE(ABORT,'IMMUTABLE_OUTCOME'); END;
