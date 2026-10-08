# Phase C Server Asset Download Gate — Exact JP 15.7.1

Status: **classified. The observed 615 MB screen is the original server-asset bootstrap gate, not gacha-schedule evidence.**

## Owner-device result

The final Phase C smoke passed the product/static gates but did not reach the
Rare Gacha scene. The isolated research package stopped at the original
additional-game-data download screen.

The old smoke-result field `schedule_provider_required=true` is therefore
invalid as a causal conclusion. The banner question was answered before the
banner UI was reachable.

## Exact JP 15.7.1 proof

The exact owner export contains 35 original `assets/download_0.tsv` through
`assets/download_34.tsv` tables.

Their archive sizes sum to:

- **645,599,537 bytes**
- **615.691697 MiB**
- 645.599537 decimal MB

That directly matches the device's 615 MB prompt.

The export also contains no files under:

`shared/jp.co.ponos.battlecats/files/`

so a freshly installed isolated package has no preseeded server-asset cache.

The native download-version vector has 35 entries and the final lane resolves
to the same original URL shape independently reconstructed by TBCML:

`battlecats_150400_34_00.zip`

with exact lane-34 archive size **15,366,935 bytes**, matching the project's
earlier current-X metadata probe.

## Correct interpretation

The runtime order is now:

```text
install isolated research package
        |
        v
original Battle Cats boot
        |
        v
missing original server-asset cache
        |
        v
615.69 MiB original download gate
        |
        v
original menu / Rare Gacha scene
        |
        v
only here can set-1089 visibility be judged
```

Therefore no gacha visibility-schedule provider is justified yet.

## Preservation-first crossing

The proof build keeps the original Battle Cats downloader. It does not add a
custom CDN downloader or copy server credentials into this repository.

For the isolated research flavor only, the flavor `MyActivity` can map
`getFilesDir()` to its app-specific external files directory. This allows the
unchanged original downloader to populate the required cache while making that
cache accessible to ADB without root.

Personal MAX and Practice Clean do **not** enable this storage redirect.

The final smoke runner also stops uninstalling the research package between
retries so a completed original server-asset download survives normal
same-signature `-r` upgrades.

## Next runtime question

After the one-time original asset bootstrap completes:

1. confirm the unchanged normal Battle Cats UI is reached;
2. open the normal Rare Gacha scene;
3. do **not** draw yet;
4. check whether append-only set 1089 is exposed.

Only if the original Rare Gacha scene is reached and set 1089 is absent should
Phase C promote a narrow local gacha-visibility schedule provider.
