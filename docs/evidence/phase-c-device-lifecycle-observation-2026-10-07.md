# Phase C device lifecycle observation — 2026-10-07

Status: **device trace succeeded; selective-local-response target not yet promoted**

Target:
- JP 15.7.1
- research package: `jp.kn.trace.battlecats`
- original launcher: `jp.co.ponos.battlecats.MyActivity`
- observation-only Frida Gadget path
- no HTTP body capture
- response header values redacted

## Normal-connectivity summary

30-second startup capture:
- trace ready: true
- event count: 20
- request returns: 2
- response lifecycles: 2
- method calls:
  - `isNetworkAvailable`: 1
  - `newHttpRequest`: 2
  - `newResponse`: 1
  - `onResponseCodeHeaders`: 1
  - `onResponseFinish`: 1
  - `onResponseData`: 0

Observed response topology:
- request 1: `newResponse`
- request 2: `onResponseCodeHeaders -> onResponseFinish`

## Airplane-mode summary

30-second startup capture:
- trace ready: true
- event count: 14
- request returns: 1
- response lifecycles: 1
- method calls:
  - `isNetworkAvailable`: 1
  - `newHttpRequest`: 1
  - `newResponse`: 1
  - `onResponseCodeHeaders`: 0
  - `onResponseFinish`: 0
  - `onResponseData`: 0

Observed response topology:
- request 1: `newResponse`

## Confirmed facts

1. `MyActivity.newHttpRequest` is a live request boundary on the owner device.
2. Its return value is an integer request identifier used by the response ingress.
3. Normal startup produced two requests, while airplane startup produced one.
4. At least two response ingress patterns are real:
   - `newResponse`-only
   - `onResponseCodeHeaders -> onResponseFinish`
5. The second normal-connectivity request is absent from the airplane-mode capture, so request issuance is not a simple unconditional send-and-fail model.
6. No `onResponseData` call occurred in these startup captures.
7. The observed order is the contract; no guessed textbook callback order should replace it.

## Not yet promoted

Do **not** implement a local responder yet from counts alone.

Still required from the sanitized raw traces:
- request URL family/path (query already redacted)
- HTTP status code for each response ingress
- `onResponseFinish` boolean
- relevant non-sensitive request flags
- confirmation that normal/airplane request 1 are the same request family

Only after those fields are correlated should one request family be selected for the first local-response experiment.

## Promotion rule

The first experiment must remain selective:
- recognized exact request family -> local response
- unknown request -> exact original `newHttpRequest`
- feature OFF -> exact original path
- original native `onResponse*` methods remain response ingress
