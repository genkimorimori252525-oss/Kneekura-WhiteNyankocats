# Runtime Contracts

These contracts refine `current-design.md`. Values that depend on the original game's implementation remain evidence-driven and are intentionally not guessed.

## 1. Virtual mobile canvas

The UI renderer owns one logical mobile canvas. Desktop window size and monitor DPI only affect presentation scale.

Required behavior:

- Preserve the measured original aspect/layout coordinate system.
- Letterbox or pillarbox instead of distorting UI.
- Convert mouse coordinates back into logical touch coordinates before hit-testing.
- Keep UI hitboxes, animation timing, and screen transitions in logical coordinates.
- Do not create a separate "PC layout" for Original Compatibility Mode.

The original logical width/height is **TBD until measured from actual data/runtime evidence**.

## 2. Input adapter

Platform input is normalized before it reaches UI/gameplay code.

```text
Touch ----\
Mouse -----+--> InputAction --> UI/GameSession
Keyboard --+
Gamepad ---/
```

Examples of abstract actions:

- pointer move
- primary press/release
- back/cancel
- confirm
- optional debug/sandbox hotkeys

Compatibility mode must not change game rules based on input device.

## 3. GameSession boundary

UI code never mutates battle state directly.

A session exposes, conceptually:

- submit command
- obtain immutable/read-only snapshot
- load/save Kneekura-local profile
- expose content fingerprint
- expose session mode/capabilities

Initial implementation: `LocalSession`.

Reserved future implementation: `NetworkSession`.

This seam exists now so multiplayer does not later require rewriting the UI or battle rules.

## 4. Battle simulation

Rendering frame rate and simulation rate are separate.

```text
Renderer: display-dependent
Battle core: fixed simulation step (rate TBD by evidence)
```

Rules:

- The fixed-step rate is not chosen by convenience; measure original behavior first.
- RNG must become seedable/deterministic before multiplayer work begins.
- Rendering may interpolate; it must not change authoritative battle state.
- Debug slow motion/frame-step wraps the simulation clock rather than altering rules.

## 5. Content registry

All runtime units/enemies/stages resolve through one registry.

Namespaces:

- `bc:...` — imported Battle Cats content
- `custom:...` — original Kneekura content

Imported content is immutable at the source layer.

Resolution order:

```text
source import
  -> compatibility normalization
  -> optional Kneekura extension
  -> user override
  -> resolved runtime record
```

Removing an override must reveal the imported value again.

## 6. Save boundary

The Android game's save is never a writable target.

Kneekura owns a separate local profile containing, for example:

- unlocked content state
- formation/loadout
- local progression
- sandbox settings
- custom content references
- local event snapshot selections

No save operation writes to the Android package or original app-private storage.

## 7. Offline service model

The runtime has no dependency on live PONOS services.

If original behavior depends on remote data, Kneekura represents only the locally available/snapshotted equivalent needed for offline play.

Examples that may require local models after evidence confirms them:

- local event schedule snapshot
- local clock policy
- content availability snapshot
- profile progression state

Out of scope:

- purchase/payment flows
- ads
- live account authentication
- cloud save
- bypassing live service checks in the installed app

## 8. UI fidelity validation

"Looks like the mobile version" is not sufficient.

For each reconstructed screen, capture evidence for:

- logical bounds
- z-order
- texture/source references
- transition timing
- touch regions
- animation state changes
- text placement rules
- scaling behavior

PC rendering passes only when the same logical scene survives multiple desktop resolutions without changing layout semantics.

## 9. Sandbox isolation

Kneekura-only tools are separate from normal play.

Recommended developer surfaces:

- unit viewer/editor
- hit/range overlays
- frame-step/slow motion
- CPU-vs-CPU
- unrestricted local formation rules
- content override inspector

Compatibility mode should remain visually clean unless the user explicitly enables a debug overlay.

## 10. Future multiplayer

Do not transmit imported proprietary asset bytes.

Before a match, peers compare fingerprints derived from normalized content definitions and locally available asset identities.

Network transport should carry:

- player/session commands
- deterministic seed/session setup
- simulation tick identity
- state hashes/checkpoints
- corrective state only if the selected netcode requires it

The exact netcode model is intentionally deferred until the deterministic local battle core exists.
