# Whole-universe saved analysis and bounded expansion planning

Search uses the verified saved ordinary-equity master, independently of the
500-stock collection cohort. A master-only or unsupported stock detail retains
exact identity and explicit unavailable prices/models. Dated aliases do not
establish listing intervals, delistings, sector or market capitalization.

Stock details now provide descriptive price volatility/drawdown independently
of ML eligibility when valid saved slots permit calculation. Known action
lookback exclusions, missing/invalid price slots and unqualified observed grids
fail closed. No annualization, dividend-inclusive risk or complete exchange
calendar is claimed. Saved model observation and generation dates are visible;
page reads never create a fresh forecast. Forecast history displays original
model/score/time and qualified or pending outcomes in a table, with original
records still inspectable.

`python -m workers.nse_market.coverage_plan --root .local-data/nse-market-expansion
--universe-root <existing-saved-master-root> --session 2026-10-23` prepares a
read-only deterministic proposal. It orders approved pending identities first,
then evidence age and stable ISIN; no score drives collection selection. Counts
separate saved candle/action checkpoints, conditional action calls, missing
calendar metadata, expired master refresh and conservative run reservations.
The command does not collect, grant permissions or activate the candidate cohort.

A full3207-equity daily cycle needs13 batches at250/run:7800 reserved GETs,
versus1800/day currently approved. Rotating these over at least5 capacity days
does not produce full daily coverage. Incremental remaining-work counts change
with genuine receipts and are reported separately in the final report.
Two target-session stock calls do not establish the61-session ML lookback.
Historical bootstrap ranges, provider capacity, exact recurring cadence,
retention rights and storage require their own approval/evidence. No provider
bulk endpoint or cross-session reusable corporate-action cache is assumed.

Rankings consider all eligible saved model outputs before Top5/10/20 selection;
there is no arbitrary302-stock sample cap. Model compatibility is distinct from
independent acceptance: all rankings remain `EXPERIMENTAL_RESEARCH`.
