# Phase C Device Trace Runbook

Purpose: capture the first real original Battle Cats request lifecycle without
changing the original UI or response behavior.

Research package:

`jp.kn.trace.battlecats`

Original launcher:

`jp.co.ponos.battlecats.MyActivity`

## Before the trace

Build/install the isolated research split set using the owner-local patch kit and
your exact JP 15.7.1 export.

The build must pass `parity-report.json` first.

The research build may contain Frida Gadget. Personal MAX and Practice Clean
must not.

### Gadget / agent compatibility

For current Frida 17.x Gadget, use the patch kit's compiled
`research/frida/trace_service_bridge.bundle.js`. It contains an explicitly
imported `frida-java-bridge`, as required since Frida 17 removed language
bridges from the core runtime.

The readable raw `trace_service_bridge.js` remains usable with Frida 16.7.19,
where the Java bridge is still built into the runtime.

## Pick one low-risk original action

Use one action only per capture.

Good first candidates:

- open a menu that performs an announcement/event refresh;
- return to the main base screen after startup and wait for one service refresh.

Avoid purchase/receipt/account-transfer actions for the first trace.

The goal is lifecycle evidence, not exercising every endpoint.

## Normal-connectivity capture

On the PC with the phone connected over ADB:

```powershell
python -m tools.base_mod.capture_service_trace \
  --label normal \
  --seconds 30 \
  --output trace-out
```

During the 30-second window, perform the chosen action once in the **original
Battle Cats screen**.

Expected files:

- `trace-out/kneekura-service-trace-normal.log`
- `trace-out/kneekura-service-trace-normal-summary.json`

The raw log already contains only sanitized `KNEEKURA_TRACE` metadata.
Do not replace it with a full unfiltered logcat unless a crash needs separate
diagnosis.

## Airplane-mode capture

Enable airplane mode manually on the phone.

Kill/restart the research build if needed, then run:

```powershell
python -m tools.base_mod.capture_service_trace \
  --label airplane \
  --seconds 30 \
  --output trace-out
```

Perform the same original action once.

The tool deliberately does not toggle airplane mode itself.

## Minimum evidence for promotion

The normal run should ideally contain:

1. `trace_ready`;
2. `newHttpRequest` call;
3. returned request handle;
4. one or more original response callbacks;
5. final `onResponseFinish`.

The airplane run should reveal the original failure/fallback behavior for the
same action.

A callback sequence does not need to match a guessed textbook order to be
valid. The observed order becomes the contract.

## What to return to the project

The useful files are the two summary JSON files and, when needed, the sanitized
`KNEEKURA_TRACE` logs.

They contain no captured HTTP body bytes or header values by design.

## Promotion rule

After the trace:

- only the observed request family may receive a local-provider experiment;
- unknown requests must call the exact original `newHttpRequest`;
- feature OFF must call the exact original method;
- original native `onResponse*` callbacks remain the response ingress;
- if the Java bridge does not expose enough information, fall back to inspecting
  the exact native `MyActivity_request` dispatcher—not global TLS/socket hooks.

## Failure cases

If the research build does not boot:

- do not compensate by patching unrelated scenes;
- capture install error and logcat;
- record the exact signed split hashes and parity report.

If the trace script changes behavior or crashes:

- discard the trace;
- remove the research instrumentation;
- keep Personal/Practice artifacts unchanged.

If no service request occurs:

- choose another low-risk original menu/event refresh action;
- do not infer a hook contract from static code alone.
