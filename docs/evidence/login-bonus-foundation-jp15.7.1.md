# Login Bonus Foundation — exact JP 15.7.1

Status: original comeback template identified; runtime selection/claim hook is
still deliberately unconnected.

Machine-readable evidence:
`docs/evidence/login-bonus-foundation-jp15.7.1.json`.

## Exact files

The verified JP 15.7.1 `DataLocal` pack contains:

- `DailyLoginEventData.csv` — 159 event rows;
- `DailyLoginEventGrade.json`;
- `StampData.csv` — 31 rows;
- `Gatyaitembuy.csv`, used to resolve reward item indexes.

The 31-row `StampData.csv` is the ordinary stamp table and is kept separate
from the comeback event logic.

## Comeback template: event 949

`DailyLoginEventData.csv` row/event **949** is:

```text
949,901,255,0,0,19,0,...
```

Using the variable reward-group layout reconstructed independently by Battle
Cats Complete, it resolves to exactly seven days.

`Gatyaitembuy.csv` is indexed below its header; in that namespace:

- item index 6 = XP;
- item index 20 = にゃんこチケット;
- item index 21 = レアチケット.

The exact local seven-day sequence is:

| Day | Reward |
| --- | --- |
| 1 | レアチケット ×1 + にゃんこチケット ×3 |
| 2 | XP 1,000,000 + にゃんこチケット ×3 |
| 3 | にゃんこチケット ×3 |
| 4 | にゃんこチケット ×3 |
| 5 | XP 1,000,000 + にゃんこチケット ×3 |
| 6 | にゃんこチケット ×3 |
| 7 | レアチケット ×2 + にゃんこチケット ×3 |

Exact local totals:

- にゃんこチケット ×21
- レアチケット ×3
- XP 2,000,000

This reward signature is highly distinctive and matches the player-facing
structure publicly described for Battle Cats comeback login bonuses: seven days,
21 Cat Tickets and 3 Rare Tickets. Recent public guides disagree on the XP total,
which is evidence that live/server-era reward quantities may have changed.

Therefore community pages are used only to identify/corroborate the feature.
They do **not** override the exact local 15.7.1 row.

Reconnaissance reference:
`https://game8.jp/battlecats/654298`

## Background asset

The row's sixth header value is `19`. Earlier server-manifest work for this
project independently found `loginbg_019.png` in the current-X image lane:

```text
source=current-x
family=XImageServer
name=loginbg_019.png
```

That is another reason to reuse the original event/scene rather than recreate a
Kneekura stamp screen.

## DailyLoginEventGrade is not silently merged with event 949

`DailyLoginEventGrade.json` currently contains stamp IDs 35052–35057,
grades 0–5, with condition parameter family 268.

Those IDs correspond to separate rows in `DailyLoginEventData.csv`, but no
exact evidence yet proves that they are the selector for comeback event 949.

They remain a separate mechanism until Phase-C tracing shows the selection path.

## Approved Kneekura behavior

The local offline implementation will use original template **949** as the
fallback comeback stamp definition:

```text
day 1 -> ... -> day 7 -> next eligible day -> day 1
```

The approved local-day rules remain:

- one claim on a newly observed local day;
- same day cannot claim twice;
- clock rollback gives nothing;
- a large forward jump grants one next stamp, not every skipped stamp.

If Phase C later proves that a server-downloaded exact JP configuration
supersedes row 949, the exact imported server version may take precedence with
provenance recorded. We will not silently substitute a wiki/community reward
table.

## Product path

The target is still the **original Battle Cats login-stamp scene**.

The next missing proof is not the reward table anymore. It is:

1. which original runtime/event decision activates row 949;
2. which state chooses the current stamp index;
3. which original reward grant path is called on confirmation.

Until those are observed, the provider remains default-off and no claim hook is
installed.
