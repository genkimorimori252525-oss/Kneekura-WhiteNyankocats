# Clock / Sidecar / Profile Service Contract

Status: Phase-B foundation. No Battle Cats hook is connected yet.

## Shipping default

`KNEEKURA_DEFAULT_FEATURE_MASK = 0`.

The native shim constructor still performs no filesystem or network access.
Sidecar load/save functions check the `LOCAL_STATE` feature bit **before**
opening any path. Therefore merely loading `libkneekura.so` remains inert.

Pure encode/decode/clock helpers exist so their semantics can be tested without
installing a hook.

## Profile modes

The sidecar has two explicit modes:

- `PERSONAL_MAX`
- `PRACTICE_CLEAN`

This is Kneekura extension metadata. It does not replace the original Battle
Cats save and it never targets the official app sandbox.

## Local-day policy

The clock core accepts an **observed epoch day** from a future confirmed host
boundary. It does not call the device clock itself yet.

Approved behavior:

- first observed day may claim one stamp;
- same day cannot claim twice;
- moving the clock backward never creates a new eligible day;
- moving the clock far forward creates one eligible claim, not one per skipped
  day;
- claiming advances one stamp and wraps modulo the configured cycle length.

Keeping the clock input explicit avoids prematurely hooking the medium-confidence
JP 15.7.1 date utility.

## Sidecar format v1

Fixed 64-byte binary record:

- 8-byte magic `KNYSCAR1`;
- schema version;
- payload length;
- CRC-32 of payload;
- profile mode;
- login cycle index;
- last seen epoch day;
- last claimed epoch day;
- event snapshot version;
- gacha config version;
- extension flags.

The serializer writes integer fields in little-endian form and validates magic,
schema and CRC on read.

## Atomic persistence

When `LOCAL_STATE` is enabled explicitly:

1. encode to memory;
2. write `<path>.tmp` mode 0600;
3. fsync temporary file;
4. move previous primary to `<path>.bak`;
5. rename temp to primary;
6. fsync parent directory when available.

Load first tries primary and then the backup. This gives the extension state an
independent recovery path without modifying original Battle Cats save bytes.

## What remains intentionally absent

- no `JNI_OnLoad`;
- no function interception;
- no network access;
- no call to the medium-confidence wall-clock candidate;
- no automatic sidecar load in the constructor;
- no original save mutation.

Phase C must prove a host boundary before any of these service APIs are wired
into original runtime decisions.