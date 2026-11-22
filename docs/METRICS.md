# Metrics — PackVote

Every figure on the public [/stats](https://packvote.shadyels.com/stats) page comes from `GET /stats` (`backend/app/services/stats.py`, payload in `backend/app/schemas/stats.py`), except the funnel shares, the round-1 share and the mean rounds, which `frontend/src/pages/Stats.tsx` computes from fields the endpoint already returns.

## Source Tables

- `ai_call_logs`: one row per network attempt. Used columns: `trip_id`, `iteration_number`, `attempt`, `prompt_version`, `provider`, `model_used`, `latency_ms`, `token_count_input`, `token_count_output`, `token_count_total`, `finish_reason`, `response_valid`, `created_at`.
- `itineraries`: one row per option (an itinerary option, not a generation). Used columns: `trip_id`, `iteration_number`, `prompt_version`, `created_at`.
- `trips`: `status`, `current_iteration`, `created_at`.
- `users`, `participants`, `votes`: row counts only.

Thinking tokens are billed as output, and a provider may leave them out of `token_count_output` while counting them in `token_count_total`. Billable output is derived as `token_count_total − token_count_input`, falling back to `token_count_output`, then 0 (see [Cost](#cost-at-list-price)).

## Totals

Row counts for trips, users, participants, votes and itineraries (options). `AI attempts` is the row count of `ai_call_logs`, including attempts whose trip has since been deleted. `Tokens in` and `Tokens out` are the sums of `token_count_input` and `token_count_output` over all attempts. `Tokens out` may exclude thinking tokens.

## Trips by Current Status

Trips grouped by their current `status`, with every status shown (zero when none). The page labels it "where trips are now, not history."

## Last 30 Days

Trips created per UTC day, and tokens in plus tokens out per UTC day, for the last 30 days including today. Each series reads at most the 100,000 most recent rows (see [Sampling](#caveats)).

## Conversion Funnel

- **Created**: `totals.trips`.
- **Reached voting**: trips with `current_iteration >= 1`. The column is set when a generation's options are written, so this counts trips that got at least one successful round.
- **Finalized**: trips with `status = FINALIZED`.
- **Share of created**: each stage divided by created. Shown as "—" when there are no trips.

No stage is counted for preferences submitted. The endpoint has no preference count, so the funnel starts at trip creation.

## Finalized in Round 1 and Mean Rounds to Finalize

Both are computed in the frontend from `voting.iterations_to_finalize`, which groups FINALIZED trips by their `current_iteration`.

- **Finalized in round 1**: trips with `iterations = 1`, divided by `finalized_trips`.
- **Mean rounds to finalize**: `Σ(iterations × trips) / finalized_trips`.

## Voting Averages

- **Avg participants per trip**: `participants / trips`, over all trips.
- **Avg votes per trip**: `votes / trips_reached_voting`.

## Valid Rate

Valid attempts divided by all attempts, from `ai_call_logs.response_valid`. Null when there are no attempts.

This is counted per attempt, not per run. A run that succeeds on its second try contributes one invalid and one valid attempt. A run whose valid response was discarded because the trip was reset during generation still counts as valid.

## Runs and Runs Succeeded

- **Runs**: rows with `attempt = 1`, one per generation run.
- **Runs succeeded**: the count of valid attempts (the code sets it from `valid_attempts`). This matches the number of successful runs only while each run stops at its first valid response, which is how the retry loop in `AI-ARCHITECTURE.md` works.

## Attempts per Run

For each `k`, the number of runs that used exactly `k` attempts. Each run has at most one row per attempt number, so the rows with `attempt = k` count the runs with at least `k` attempts. The "exactly `k`" figure is that count minus the count for `k + 1`.

## Latency (p50, p95, Histogram)

- **Unit**: one AI attempt. Latency is measured around the provider's `create()` call only, so retry backoff is excluded. Failed attempts that reached the provider are included.
- **Sample**: the newest 100,000 rows with a non-null `latency_ms`, sorted in Python. `sample_size` is the number of rows used.
- **Percentiles**: nearest-rank. `p50` is the value at index `ceil(0.5 × n) − 1` of the sorted list, and `p95` is the same at `0.95`.
- **Histogram**: attempts per bucket, with edges at 0, 5, 10, 20, 30, 60 and 120 seconds. The last bucket is open-ended.
- **Per prompt version**: the same percentiles computed over that version's attempts.

Attempts refused by PackVote's own rate limiter make no request and are not logged, so they do not appear here.

## Finish Reasons

Attempts grouped by `finish_reason`, most frequent first. A null value means the request failed before a response came back and is shown as "none (request failed)". A high count of `length` is the signal described in `AI-ARCHITECTURE.md` for thinking tokens eating into the output budget.

## Tokens per Itinerary (by Prompt Version)

For each prompt version: `(tokens in + billable output)` summed over all of that version's attempts, failed ones included, divided by that version's itineraries. Null when the version has no itineraries or no attempts. Displayed rounded.

This divides by options, not generations, so a generation that produces five options counts five in the denominator.

## Cost at List Price

Cost is a list-price estimate, not a bill. Actual spend on Gemini's free tier is $0.

- **Prices**: `AI_PRICES_USD_PER_1M` in `backend/app/core/config.py`, as `(input, output)` USD per 1 million tokens. The only entry is `gemini-3.6-flash`, at `(0.75, 3.75)` as of `AI_PRICES_AS_OF` (2026-11-19). Matching strips a leading `models/` from the model name.
- **Formula, per model**: `(Σ token_count_input × input price + Σ billable output × output price) / 1,000,000`.
- **Billable output, per attempt**: `coalesce(token_count_total − token_count_input, token_count_output, 0)`. Thinking tokens are therefore billed at the output rate.
- **Unpriced models**: a model with no price entry has a null cost. It is listed in `pricing.unpriced_models` and left out of every total. `totals.cost_usd` silently sums priced models only. Per-version and cost-per-finalized figures become null rather than partial when any attempt used an unpriced model.

## Cost per Itinerary (by Prompt Version)

Cost of all of a version's attempts, failed ones included, divided by that version's itineraries. Null when the version has no itineraries, no attempts, or any attempt used an unpriced model.

Like tokens per itinerary, this divides by options.

## Cost per Finalized Trip

Cost of every attempt on a FINALIZED trip, across all of its iterations and failed attempts included, divided by `finalized_trips`. Null when there are no finalized trips, no attempts on them, or any of those attempts used an unpriced model.

If a finalized trip is deleted, its attempts stop being linked to a trip and its row leaves `finalized_trips`, so both sides of the division drop it.

## Per-Prompt-Version Table

One row per prompt version seen on either `itineraries` or `ai_call_logs`. Rows with itineraries come first, newest first. Versions that exist only in the logs come next, and the unversioned row comes last.

- **Generations**: distinct `(trip, iteration)` pairs in `itineraries` for the version. A generation that wrote three options counts once.
- **Itineraries**: option rows for the version.
- **Attempts**, **valid rate**, **p50 and p95 latency**, **tokens per itinerary** and **cost per itinerary**: as defined above, over all of the version's attempts.
- **Unversioned row** (`prompt_version` null): attempts logged before migration `0002`. The backfill copied the version onto attempts whose run produced an itinerary. Attempts of runs that never produced one, and orphaned attempts whose trip was deleted, stay null.

Generations and itineraries count successful runs only. Attempts, latency and cost include failures.

## Prompt Quality

Source: `backend/evals/results.json`, written by `cd backend && uv run python -m evals.run`. See the Eval Harness section in `AI-ARCHITECTURE.md`. The section is hidden when the file is absent.

The header shows the run date, the generation model, the judge model and the number of cases.

Per prompt version (`v3` and `v4`), over paired cases only (cases where both versions returned a response):

- **Cases**: paired cases. The same number for both versions.
- **Judged cases**: cases where the judge returned a parseable score. The judge runs only on schema-valid responses.
- **Pass every check**: share of paired cases that pass every applicable gating check.
- **Check pass rates**: the share of applicable cases passing each check. The count shown is the number of applicable cases.
  - `json_valid`: the response parses as JSON.
  - `schema_valid`: the response validates against the itinerary schema.
  - `option_count`: the number of options equals the number requested.
  - `day_count`: every option has one entry per trip day.
  - `time_field`: the version followed its own time instruction. `v3` must leave every activity time null, and `v4` must give every activity a valid time-of-day slot.
  - `destination_respected`: only for fixed-destination cases. The destination's city name appears in every option's `destination_name`.
  - `time_slots` (informational, not in "Pass every check"): every activity has a valid time-of-day slot. A `v3` response cannot pass this by following its own prompt, which is why it is not gating.
- **Judge means**: 1 to 5 for `preference_fit`, `conflict_handling`, `specificity` and `budget_realism`. Overall is the mean of those four means.

## Reading the Funnel as a Campaign

Read as an acquisition funnel, the same three stages appear:

- **Creation**: trips created and participants added to them.
- **Optimization**: generation quality (valid rate, attempts per run, prompt quality), cost per itinerary and per finalized trip, and the per-version comparisons. Each prompt version is measured on the same figures, so changes can be compared.
- **Reporting**: `/stats` itself. It returns aggregates only. No field carries prompts, raw responses, error messages, emails, names, titles or destinations.

## Caveats

- **List prices, not spend.** Costs are estimates at list price as of `AI_PRICES_AS_OF` (2026-11-19). Per the comment in `backend/app/core/config.py`, the Gemini 3.6 Flash prices are valid through 2026-12-31 and double to `(1.50, 7.50)` from 2027-01-01. After that date, cost figures use the old prices until `AI_PRICES_USD_PER_1M` is updated.
- **Free tier.** Actual spend on Gemini's free tier is $0. The cost figures show what the same tokens would cost at list price.
- **Unversioned early runs.** Failed runs before migration `0002` have no prompt version. Older versions' valid rate and cost therefore leave out their worst runs.
- **Rate-limited attempts are not logged.** Attempts refused by PackVote's own AI rate limiter make no request and have no row.
- **Not stored.** Emails sent are not stored.
- **No finalization timestamp.** Time-to-finalize cannot be shown.
- **Deleted trips.** Deleted trips drop out of every count except AI attempts, which show as orphaned.
- **Unpriced models.** Their cost is left out of every total. They are listed on the page.
- **Sampling.** Latency and daily activity use the newest 100,000 rows. `sampling.truncated` reports when that cap applies.
- **Per-attempt latency.** Latency figures include failed attempts.
- **Synthetic prompt quality.** Prompt quality comes from 12 synthetic offline cases, not live traffic.
- **Self-grading.** When the judge model is the same as the generation model, the judge may favour its own output. This is the default, because `EVAL_JUDGE_MODEL` is empty unless set.
- **Budget check omitted.** `budget_in_range` is not checked, because the prompt does not say whether a budget is per person or for the whole group. `budget_realism` inherits that ambiguity.
- **Low traffic.** With few trips, one trip moves a percentage by a large amount. A 100% or 0% figure from one trip is not a trend.
- **Caching.** `/stats` results are cached per process for 60 seconds.
