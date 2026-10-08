# Phase C Shipping Boundary — Personal / Practice

Status: repository and CI boundary audit **PASS** for the current Phase C
implementation. Final original-scene runtime visibility remains a separate
proof gate.

## Product profiles

Shipping-oriented package identities remain isolated:

- Personal MAX: `jp.kn.white.battlecats`
- Practice Clean: `jp.kn.clean.battlecats`
- disposable research: `jp.kn.trace.battlecats`

The research package is not a product flavor alias.

## Research dependency rule

Only the disposable research builder may import or inject the Frida Gadget
transport.

The following product-path builders are audited to contain no
`inject_research_gadget`, Gadget entry, trace-script entry, or
`libfrida-gadget` dependency:

- `tools/base_mod/build_owned_boot_smoke.py`
- `tools/base_mod/build_owned_static_http_bridge.py`
- `tools/base_mod/build_owned_gacha_ui_proof.py`

The repository verifier is:

`tools/base_mod/verify_shipping_boundary.py`

## Product static bridge logging

The static MyActivity bridge template contains one non-sensitive research proof
log, but its compile-time boolean is generated as:

```text
research -> true
personal -> false
practice -> false
```

CI compiles enabled static bridge DEXes for both Personal and Practice and
asserts that neither product DEX contains:

- `KNEEKURA_STATIC_HTTP`
- `jp.kn.trace.battlecats`

Thus the research proof marker is not carried into the product DEX.

## Artifact-level audit

`verify_shipping_boundary.py` can additionally scan a signed Personal or
Practice split set.

It rejects:

- `libfrida-gadget.so`;
- Frida Gadget config;
- `libbc_script.js.so`;
- Frida/research markers in manifest, DEX, or native-library surfaces;
- the research package id in a product manifest;
- a Kneekura shim whose DT_NEEDED set contains a Frida/Gadget library;
- launcher shape inconsistent with the selected build mode.

For a feature-OFF base-preserving product build, the original launcher remains:

`jp.co.ponos.battlecats.MyActivity`

For a Frida-free static bridge product build, the flavor subclass is the
launcher while it still inherits the original MyActivity scene/lifecycle host.

## Existing device evidence

The promoted Frida-free research static bridge has already passed Android
smoke:

```text
package_alive      true
local_replay_seen  true
frida_seen         false
fatal_seen         false
```

and the exact observed offline fallback path is preserved.

The research package was used because it is disposable and isolated; the same
static bridge compiler is used for Personal/Practice, with research logging
compiled out.

## Original-scene data proof

The set-1089 tiny gacha proof changes only the four original Rare Gacha
DataLocal tables and does not replace gacha/capsule/result scene code.

Exact derived proof target:

- set id 1089;
- Rare unit 37;
- Super Rare unit 30;
- Uber Rare unit 34;
- clone visible option row 49.

The live `gatya.tsv` schedule remains a separate provider gate. No schedule
or rarity vector is fabricated merely to make the banner appear.

## CI gate

The source-free patch-kit workflow now performs all of the following:

1. repository shipping-boundary audit;
2. research OFF/ON static DEX compilation;
3. Personal enabled static DEX compilation;
4. Practice enabled static DEX compilation;
5. product-Dex check for absence of research log/package markers;
6. normal Phase C preflight;
7. package-kit assembly.

A failure at any of those boundaries blocks the kit.
