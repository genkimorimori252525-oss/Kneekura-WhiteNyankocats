# KNEEKURA Update 1.01 — native combat + Godzilla animation gate

Status (2026-10-09): **NATIVE POLICY COMPILED/TESTED; ORIGINAL GAME HOOK UNBOUND; NO APK/APPLICATION RELEASE**.

## Exact owner source

- Exact JP15.7.1 owner ZIP SHA256: `38c3bbb8d2cf2101793c9462617d4293e19fc99588b6655fd40299fd61a0ef56`.
- ARM64 `libnative-lib.so` SHA256: `333d2974ab2ff881fd70087fd62dea7d12d82addbc55cab2f2a675ad67e3a7e2`.
- ELF build ID: `8cb3815648eb9642da10bfb039d71bff7a3519bd`. This matches the repository shim's exact-version guard.
- Original library exposes Java JNI functions including `MyActivity_appUpdateDraw`; it **does not expose a verified battle hit/stat or enemy-castle HP deduction symbol** in the inspected dynamic symbol table. Do not infer that an update/draw JNI entry point is a valid damage hook.

## New native decision engine, not a runtime hook

The source `native/kneekura-shim/src/kneekura_battle101.c` and header `kneekura_battle101.h` add a **separate ABI v1** and feature bit 7. The existing shim ABI v2 is unchanged, and `KNEEKURA_DEFAULT_FEATURE_MASK=0` still disables all behavior.

- `kneekura_battle101_base_hit` yields exact **28,000** for No.289 form2 Lv30, and **50,000 per hit** for No.703 form0 Lv30. Earlier forms and other levels are untouched. It must only be called at the base-hit-stat boundary **before** enemy/trait modifiers.
- `kneekura_battle101_castle_hit` yields up to **one point per three-hit attack sequence**, independent across deployed No.703 form0 instances, with deduplication per hit index, next-sequence reset and missed-hit handling. It must only be called at the original **post-modifier, pre-castle-HP-debit** seam. The host must supply original battle instance ID, deployed cat instance ID, monotonic attack sequence ID and true 0-based hit index. The original castle-target decision must be verified (not guessed from enemy type or coordinates). Non-Godzilla cats bypass unchanged.
- State is **battle-local in memory**, bounded to 256 actors. Caller resets it at battle creation and releases actor slots only at verified despawn. Single battle-simulation-thread assumption needs original-engine confirmation.
- Unexpected context or full tracker returns a negative error and zero Godzilla castle damage; the eventual hook must **check the return status and abort that castle HP debit**. It may not silently debit native default damage. Product features remain OFF until original callsite, inputs and rollback are validated.
- The reference-only Python policy remains separate; C host tests compile both feature OFF and feature ON. Passing tests here **does not mean Godzilla is usable in a shipped APK**.

## Animation source and model

The owner's 150 MB original APK ZIP contains `ImageDataLocal`, `ImageLocal`, `UnitLocal`, but **neither the full No.703 cat rig nor enemy Godzilla No.552 rig** is in the inspected local asset manifests. Catalog and prior historical/current server filename indexes record normal collaboration animation assets in downloaded Server families; owner-held **ImageDataServer/ImageServer pack bodies** are necessary for a real transformation.

The new `tools/base_mod/godzilla_animation_gate.py` reads existing `build_server_manifest_index.py` **metadata-only JSON**, demands PNG + imgcut + mamodel + 4 maanim tracks, and detects ambiguity between enemy visual stem candidates `550_e`/`551_e`/`552_e` without assuming catalog No.552 equals the graphics asset ID. It identifies target `702_f` for the confirmed first form and explicitly excludes `702_c` (second form), `702_s`, `702_u`.

Even when metadata is complete, it is **not** an animation converter. Original enemy animations face the opposite direction from allied units; actual model orientation/mirror, rig hierarchy, sprite-coordinate mapping, motion frames 130/170/210, and playable 450f cycle need evidence and original-game tests. BCU community reference for enemy-to-unit animations: https://www.reddit.com/r/BattleCatsUltimate/comments/1ppvvt3/looking_for_enemy_as_unit_packs/ ; open source animation viewer/format reference: https://github.com/omochikaeri15/Battle-Cats-Complete . They are secondary technique clues, not exact JP15.7.1 proof.

## Release/user gate

1. Do not edit original `DataLocal.list/.pack`; prior direct edits triggered H01. A `DownloadLocal` overlay's parser precedence also requires original-device proof.
2. Map original game base-hit-stat and castle HP-debit native callsites with trustworthy exact-version read-only trace, original on/off behavior and return values; **no guessed offsets**, no unconditional Frida shipping dependency.
3. Validate native hook on disposable research package and stage with no real player SAVE. Confirm first form visual/animation, three hits, multiple cats, castle total=1 and other cats unaffected, original UI and offline boot.
4. Only after verified same-signature incremental installation, original SAVE preservation, restart and rollback may 1.01 be called an installable update.
5. Existing native level cap migration remains the only proven device-facing update part. Never mutate player SAVE in this combat module.

Related: [1.01 readiness](../updates/update-1.01-readiness.md), [UGOD-001 Issue #3](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/issues/3), [Draft PR #4](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/pull/4).