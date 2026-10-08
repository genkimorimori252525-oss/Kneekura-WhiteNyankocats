# Android Offline Alpha Contract

Status: first installable Android runtime slice.

## Purpose

This alpha is an independent, offline-only app. It is not a patched Battle Cats APK and it never writes to the official package, official save, or PONOS services.

The first Android milestone intentionally concentrates on two things the current evidence can support without pretending the battle engine is finished:

1. import the user's locally owned JP export ZIP on-device;
2. create a Kneekura-local maxed profile with the imported 882-slot unit catalog.

The deterministic battle core, original-compatible screen-by-screen UI, stage progression, and complete animation renderer remain later runtime milestones.

## Package / network boundary

- package: jp.kneekura.whitenyankocats
- no android.permission.INTERNET
- no WebView or network client
- source export chosen through Android Storage Access Framework
- no official package-private path access
- no official save mutation
- no cloud save, ads, authentication, purchase, or live event calls

A built APK must fail review if INTERNET permission appears.

## First-run import

The user selects their nyanko_battlecats_2026-10-06.zip.

The app streams the outer ZIP, extracts only split_InstallPack.apk into temporary private cache, then reads:

- DataLocal.list/.pack
- resLocal.list/.pack

It builds a local catalog from unitNNN.csv and Unit_ExplanationN_ja.csv. The source ZIP is never modified.

Imported catalog data is stored only in the app-private files directory. Temporary InstallPack bytes are deleted after import.

## Unlock state

The Kneekura profile is independent from the mobile game's profile.

For the alpha:

- every imported unit slot is marked obtained;
- default usable form is form index 0 / first form;
- evolution requirements are not applied to the first-form-only alpha;
- JP placeholder/regional slots remain visible if they exist in the imported 882-row catalog, but they do not imply that missing JP artwork exists.

## MAX resource preset

The local profile starts in resource_mode_max.

The profile initializes all currently modeled inventory buckets to 999,999,999 and the UI renders them as MAX, including headline resources such as:

- Cat Food
- XP
- NP
- tickets / Leadership
- battle items
- Catfruit / seeds / Epic / Elder / Gold
- Catseyes
- Behemoth stones
- talent-orb bucket
- generic evolution-material bucket
- local event-currency bucket

These are Kneekura-local resources, not writes to the official game's save. As exact original inventory taxonomy becomes evidenced, generic buckets can be split without changing the offline-save boundary.

## Asset boundary

Original image/model/animation/audio payloads are not committed to Git and are not bundled into the repository-built APK.

The current Android alpha therefore proves roster import, local progression state, search/detail UI, and the offline package boundary. Full historical-collaboration visual playback remains dependent on a separate local asset-cache/import milestone.

## Acceptance

The alpha passes only when:

- the Android project compiles into a debug APK;
- source manifest has no INTERNET permission;
- package name is independent from PONOS;
- host tooling tests continue to pass;
- selecting a compatible export produces the unit catalog and a maxed local profile.