# Provider ABI Contract — Phase B

Status: provider semantics exist; **no original Battle Cats hook is connected**.

The shim exposes a small product-level provider ABI so Phase C can connect one
confirmed original boundary at a time without embedding policy directly into
patch bytes.

## Feature gates

All provider feature bits default OFF:

- local events;
- Super Kneekura Gacha;
- cyclic login bonus;
- first-clear stage Cat Food.

Provider API calls are therefore pass-through/disabled in the shipping Phase-B
shim even if some research harness invokes them accidentally.

## Event visibility

`kneekura_provider_event_visible(original_visible, local_available)`

- feature OFF: return original visibility;
- feature ON: original OR locally available.

The future event hook therefore cannot hide an original active event merely
because Kneekura has no local row.

## Super Kneekura Gacha cost

`kneekura_provider_gacha_cost(kind, draws, original_cost)`

When the Super Kneekura feature is enabled:

- one draw -> 150 Cat Food;
- eleven draws -> 1500 Cat Food;
- unknown draw counts or gacha kinds -> original cost.

This ABI defines only the approved transaction policy. It does **not** select a
Battle Cats gacha id, alter the original scene, or choose unit results yet.

## Login claim

`kneekura_provider_login_claim(...)` composes the approved local-day policy
with the sidecar login cycle.

It is disabled unless provider, login and local-clock feature bits are all on.
There is no call to `system_clock` here; Phase C must supply the observed epoch
day from a confirmed original wall-clock boundary.

## Stage first-clear Cat Food

`kneekura_provider_stage_cat_food(difficulty, already_claimed)`

When enabled and not already claimed:

- 1–3 -> 1
- 4–6 -> 2
- 7–8 -> 3
- 9–10 -> 5
- 11 -> 8
- 12+ -> 10

The function is pure. Claim identity/persistence is intentionally deferred to a
later stage-reward sidecar extension so this phase cannot accidentally grant
currency to the original save.

## Preservation rule

The provider ABI is a **semantic seam**, not a hook mechanism.

It contains no:

- JNI registration;
- symbol detours;
- Frida;
- socket/network calls;
- original save writes;
- scene/UI code.

Phase C may connect an exact JP 15.7.1 boundary only after its call contract is
observed and added to the patch ledger.
