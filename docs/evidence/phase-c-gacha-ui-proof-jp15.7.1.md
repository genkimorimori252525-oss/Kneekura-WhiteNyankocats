# Phase C Gacha UI Proof — Exact JP 15.7.1 Derived Set

The deterministic tiny-gacha builder was run against the exact owned JP 15.7.1
export (SHA-256 `38c3bbb8d2cf2101793c9462617d4293e19fc99588b6655fd40299fd61a0ef56`).

It derives the first append-only proof set as:

- new Rare Gacha set id: **1089**
- cloned existing BannerON option set: **49**
- banner flag: **1**
- tiny pool:
  - unit 37 — rarity id 2 (Rare)
  - unit 30 — rarity id 3 (Super Rare)
  - unit 34 — rarity id 4 (Uber Rare)

All three ids already exist in the exact local R1 union. Explicit test/cheat id
673 is excluded.

The cloned option metadata is the original visible row's metadata with only the
set id changed to 1089. The proof keeps R2/R3 empty and replaces no original
rows.

This evidence does **not** define a live rarity probability vector and does not
invent a server visibility schedule. It therefore proves the exact data target
without claiming that the original Rare Gacha scene will already select set
1089. That selection question remains the next runtime/provider gate.
