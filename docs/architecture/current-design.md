# Kneekura WhiteNyankocats — Current Design

Status: initial compatibility-first architecture.

## Product identity

Kneekura WhiteNyankocats is a PC-capable, offline-only independent runtime that can import locally owned Battle Cats data and combine it with original custom units. It is not an in-place patcher for the installed Android game.

The default experience should preserve the familiar mobile game's screen flow, layout logic, animation timing, and battle feel as closely as evidence allows. Kneekura-only tools live behind a separate developer/sandbox surface so normal play does not feel like a debug build.

## Hard boundaries

1. Original Android files are read-only inputs.
2. Imported proprietary assets never enter Git.
3. Kneekura saves are independent from the mobile game's saves.
4. No live PONOS service is required by the runtime.
5. Unknown fields are preserved as unknown; they are not guessed into meaning.
6. Original-compatibility behavior and Kneekura extensions are separately identifiable.

## Runtime layers

```text
Platform input/rendering
        |
        v
Virtual mobile canvas
        |
        v
Original-compatible UI shell
        |
        v
GameSession interface
   |              |
LocalSession   NetworkSession (future)
   |              |
   +------v-------+
 Deterministic battle core
        |
        v
Resolved content registry
   ^              ^
Battle Cats     Custom
 importer       content
```

The actual logical canvas dimensions and simulation tick rate are not hard-coded in this design document. They must be measured from game data/code/behavior evidence before being frozen.

## Content layering

Resolved content is produced without mutating imported originals:

```text
Imported original record
        ↓
Compatibility normalization
        ↓
Optional Kneekura extension
        ↓
User override
        ↓
Resolved runtime Unit/Enemy/Stage
```

Deleting an override must restore the imported original behavior.

## Input model

Touch, mouse, keyboard, and controller inputs translate into common actions before they reach UI/gameplay code. PC support must not fork the game rules.

## Offline model

Anything the original title obtains from a remote service must either be absent or represented by a local snapshot/service model. The runtime must remain fully playable with networking disabled. Live-service authentication, advertising, purchases, and cloud-save code are out of scope.

## Modes

- **Original Compatibility Mode** — imported characters/enemies/stages and original-compatible rules/UI.
- **Kneekura Sandbox Mode** — custom units, overrides, debug visualization, unrestricted experiments, CPU-vs-CPU, and future extensions.

## Future multiplayer seam

Multiplayer is not implemented in the first phase. The architecture reserves a `GameSession` seam so UI talks to a session instead of directly mutating battle state.

The battle core should use a fixed simulation step and deterministic RNG once the original timing behavior has been measured. A future network session should exchange commands/state checks rather than redistribute imported proprietary assets. Content fingerprints must be compared before a match.

## First executable milestones

1. Inventory a device export without modifying it.
2. Identify split APK/shared-storage structure and candidate data families.
3. Import one unit's metadata and animation dependencies.
4. Reproduce one minimal battle pair.
5. Add one custom unit through the same runtime registry.
6. Expand compatibility coverage before adding large sandbox-only features.
