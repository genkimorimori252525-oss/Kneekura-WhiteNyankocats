# Stage Runtime Foundation — 2026-10-06

Status: Android playable-stage checkpoint implementation started.

## Goal

The next checkpoint is not another metadata viewer. It is:

ネコ基地風一覧 -> stage select -> real stage definition -> battle start -> enemy spawn -> base win/loss

The battle renderer is intentionally primitive at this checkpoint. Original image/model/animation payloads are still kept out of Git. The purpose is to prove that the game-data path and battle state path are usable on Android before the PC runtime is expanded.

## Primary evidence

The exact JP 15.7.1 export previously verified in this repository contains a MapLocal family with 608 manifest entries.

TBCML public source defines the stage schema used by this implementation:

- StageInfo: width, enemy-base HP, production-frame bounds, background id, max enemy count, castle enemy id.
- StageEnemyData: enemy id, count, first spawn frame, min/max respawn frame interval, enemy-base HP trigger percentage, z range, boss flag, enemy magnification.
- MapStageDataStage: energy, XP, music and rewards.
- StageOptionInfo: rarity/deploy/cost restrictions.

TBCML also provides the filename map for the major stage families. The Android importer follows those filename rules rather than inferring categories from display text.

## Filename families handled now

- stageNN.csv -> Empire of Cats / 日本編
- stageWNN_SS.csv -> Into the Future / 未来編
- stageSpaceNN_SS.csv -> Cats of the Cosmos / 宇宙編
- generic stage prefixes:
  - RN Stories of Legend / レジェンドストーリー
  - RNA Uncanny Legends / 真レジェンド
  - RND Zero Legends
  - RS regular/special events
  - RC collaboration stages
  - RCA collaboration gauntlets
  - RA gauntlets
  - RB Catamin
  - RH Enigma
  - RM Challenge
  - RQ Behemoth
  - RR Ranking Dojo
  - RT Catclaw/Dojo
  - RV Towers
  - EX continuation/EX
  - DM Aku/Makai
  - L Labyrinth
  - Z outbreaks

Unknown future prefixes are retained as その他(prefix) instead of being dropped.

## Community reconnaissance

Community databases are useful as a second, player-facing index and as a repair hint when a historical event is no longer present in the current local pack.

Cross-checks used in this phase:

- Battle Cats Wiki's Legend Stages index describes Stories of Legend, event stages, collaboration stages, Crazed stages and Awakening stages under the Legend-stage ecosystem.
- Its Crazed Cat Stages index records the recurring Crazed/Manic family.
- battlecatsinfo's stage pages expose the same concepts represented in the binary schema: base HP, stage width, enemy cap, enemy magnification, first spawn, respawn interval and base-HP trigger.
- battlecatsinfo's stage_scheme.json independently separates Stories of Legend, Special, Collaboration, Main Chapters, EX, Tower, Uncanny, Gauntlet, Enigma, Collaboration Gauntlet, Behemoth, Labyrinth and Zero Legends.
- community timing references agree that Battle Cats battle timing is 30 frames per second.

These sources are reconnaissance only. If a community lineup conflicts with a stage CSV imported from the user's owned JP data, the imported stage CSV wins.

## Historical/collaboration preservation rule

The local MapLocal pack cannot by itself guarantee every historical collaboration stage ever released.

The runtime therefore uses a provenance-aware route:

1. exact local/install stage definition;
2. exact historical/current server-stage definition when locally imported later;
3. community reconstruction only when no exact stage definition exists, clearly tagged as reconstruction.

A community reconstruction may provide lineup/timing metadata but must not silently masquerade as extracted original data.

## First battle-core contract

The first battle core is deliberately narrower than final compatibility:

- 30 simulation ticks per second;
- stage width and enemy-base HP from imported StageInfo;
- enemy spawn count/timing/base-HP trigger/magnification from imported StageEnemyData;
- basic player/enemy HP, movement, range, attack and base destruction;
- stage victory/defeat when a base reaches zero.

Not yet compatibility-complete:

- exact attack animation length/backswing timing;
- KB thresholds and knockback motion;
- waves/surges/LD/omni/abilities/traits;
- zombie burrow/revive;
- shields/barriers;
- stage restrictions and reward accounting;
- original battle sprites/animations;
- treasure/chapter magnification and full money/worker-cat economy.

Those are explicit later layers, not guessed into this checkpoint.

## Why this is useful for autonomous implementation

Every imported stage becomes a normalized StageDefinition containing its source identity plus EnemySpawn rows. That gives future agents a stable object to compare against community walkthroughs, wiki lineups, expected boss timing, screenshots/videos, exact stage CSV evidence and regression simulations.

Future work can therefore ask why stage X differs instead of manually rediscovering each stage format.