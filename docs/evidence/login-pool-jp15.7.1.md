# Login pool / five-slot scheduler proof — JP 15.7.1

The exact local `DailyLoginEventData.csv` contains 159 parseable event rows.

For the first Kneekura player-facing pool, the static eligibility gate is:

- at least 6 reward days;
- every day contains a reward;
- no reward kind `-1`.

This excludes one-day/system-like definitions until they are individually
classified instead of blindly exposing all 159 rows.

The resulting JP 15.7.1 pool has **106 campaigns**. Its ordered ID list hashes
to:

`01be0f23d8f8b196755eb28d9765e2e8fd7d7ddb02a66ae72d3df2d647a4bbe0`

The pure scheduler maintains five unique active campaigns, advances each at
most once per newly observed local day, refuses same-day/backward-clock claims,
grants only one stamp after a large forward jump, and replaces a completed slot
with a new campaign that starts on the next local day.

This is a state-machine foundation only. The original Battle Cats login scene
selection/reward-settlement hook remains deliberately disconnected until the
original runtime provider is proven.
