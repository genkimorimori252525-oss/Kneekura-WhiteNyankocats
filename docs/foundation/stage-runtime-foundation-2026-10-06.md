# Stage Runtime Foundation — 2026-10-06

Status: Android playable-stage checkpoint implementation started.

## Goal

The next checkpoint is not another metadata viewer. It is:

ネコ基地風一覧 -> stage select -> real stage definition -> battle start -> enemy spawn -> base win/loss

The battle renderer is intentionally primitive at this checkpoint. Original image/model/animation payloads are still kept out of Git. The purpose is to prove that the game-data path and battle state path are usable on Android before the PC runtime is expanded.

## Primary evidence

The exact JP 15.7.1 export has now been re-checked directly from the recoverable beginning of split_InstallPack.apk. DataLocal contains 8,955 entries and is the stage-definition source. It contains 6,355 `stage*.csv`-style files after excluding StageName/Stage_option. Of these, 6,333 are concrete battle-layout files covered by the runtime grammar after accounting for three-digit Labyrinth floors and the two Space Invasion layouts; the remaining stage-prefixed CSVs are auxiliary/config data such as `stageNormal*.csv`, `stage.csv`, stage conditions and skip/hint settings. MapLocal has 608 entries, but those entries are PNG map/stage imagery; it is not the primary stage-CSV source.

TBCML public source defines the stage schema used by this implementation:

- StageInfo: width, enemy-base HP, production-frame bounds, background id, max enemy count, castle enemy id.
- StageEnemyData: enemy id, count, first spawn frame, min/max respawn frame interval, enemy-base HP trigger percentage, z range, boss flag, enemy magnification.
- MapStageDataStage: energy, XP, music and rewards.
- StageOptionInfo: rarity/deploy/cost restrictions.

TBCML also provides the filename map for the major stage families. The Android importer follows those filename rules rather than inferring categories from display text. Direct JP 15.7.1 DataLocal inspection confirms representative exact files such as stage00.csv, stageRN000_00.csv, stageRS000_00.csv and stageRC000_00.csv, together with Map_option.csv, Stage_option.csv, 1,279 MapStageData files, and t_unit.csv.

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

Unknown future prefixes are retained as その他(prefix) instead of being dropped. The current JP DataLocal also contains additional prefixes such as G, Normal, RPR and RSR; these stay preserved until their exact semantics are promoted from evidence.\n\nExact current JP stage-file counts include RN 324, RNA 286, RND 217, RS 1,215, RC 847, RCA 459, RA 1,147, RB 74, RH 85, RM 1, RQ 60, RR 50, RT 2, RV 260, EX 192, DM 49, L 113, Z 432, W 144, Space 146 and 57 numeric main-story stage files.\n\nMap_option.csv also directly contains named maps for the Crazed/Manic line (for example 狂乱のネコ降臨 through 狂乱の巨神降臨 and 大狂乱のネコ降臨 through 大狂乱の巨神降臨), plus historical collaboration map names such as 魔法少女まどか☆マギカ, Evangelion, 初音ミク, らんま1/2 and Street Fighter. This is stronger evidence that these stage definitions can be preserved locally than relying on an active event schedule.

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
- enemy spawn count/timing/base-HP trigger/magnification from imported StageEnemyData; zero spawn-count is treated as unlimited, matching the JP CSV comment;
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

## Exact stage auxiliary CSV contract

JP 15.7.1 DataLocal was decoded again for this checkpoint. The exact files are present in the verified pack:

- `Map_option.csv`
- `Stage_option.csv`
- 1,279 `MapStageData*.csv` files
- representative stage files including `stage00.csv`, `stageRN000_00.csv`, `stageRS017_00.csv`, and `stageRC000_00.csv`

The exact 15.7.1 `Map_option.csv` header has 20 columns:

`stageID, 星解放, 裏星解放, 星1倍率, 星2倍率, 星3倍率, 星4倍率, ゲリラset, 報酬リセットType, 1度きり表示, 表示順, インターバル, 挑戦フラグ, マップ難易度, クリア後非表示, XP2倍広告, 生産額倍率, 統率力フラグ, ステージ全表示設定, マップ名`

Therefore the current-version importer treats map id as column 0, star count/unlock as column 1, star magnifications as columns 3-6, difficulty mask as column 13, and map name as column 19. This intentionally differs from older helper-source layouts where the name column is earlier.

The exact `Stage_option.csv` header is:

`mapID, 対応★, stageID, レア度制限, 出撃制限数, スロット編成数制限, 生産コスト制限条件下限, 上限, groupID`

This confirms that stage restrictions join on absolute map id + stage id, with star id in column 1 and restriction fields in columns 3-8.

The exact `MapStageDataS_017.csv` for 狂乱のネコ降臨 contains stage row:

`200,4000,33,99,34,100,1103,1,-1`

This independently confirms the runtime-facing order used by TBCML: energy, clear XP, start BGM, enemy-base HP percentage for boss BGM, boss BGM, first reward probability/id/amount, then reward type/additional reward fields.

The exact `stageRS017_00.csv` has width 4400, enemy-base HP 400000 and max enemy count 10. Its enemy rows include the same first-spawn frame, repeat interval, base-HP trigger and magnification fields used by the current StageDefinition importer.

For reference, `stageRN000_00.csv` has width 4200/base HP 60000/max enemy count 7. These values are now treated as regression anchors for the Android importer.


### Main-story MapStageData equivalent and late stage shapes

The exact pack also resolves a gap left by the generic TBCML map helper:

- 日本編 stage metadata/rewards: `stageNormal0.csv`
- 未来編 chapters: `stageNormal1_0.csv` .. `stageNormal1_2.csv`
- 宇宙編 chapters: `stageNormal2_0.csv` .. `stageNormal2_2.csv`
- Space invasion reward metadata: `stageNormal2_2_Invasion.csv` and `stageNormal2_2_Invasion_Z.csv`
- concrete invasion battle layouts: `stageSpace09_Invasion_00.csv` and `stageSpace09_Invasion_Z_00.csv`

These use the same MapStageData-like stage-row ordering for energy/XP/music/reward data, so the Android importer now attaches that metadata to main-story stages as well.

Labyrinth stage indices are not limited to two digits: the verified pack includes `stageL000_100.csv` through `stageL000_112.csv`. The runtime grammar therefore accepts two- or three-digit stage indices for generic stage families.

A direct manifest pass counts 6,333 concrete battle-layout files under the current importer grammar. It leaves only auxiliary/config stage-prefixed CSVs outside the battle catalog rather than silently dropping real floors or invasion battles.
