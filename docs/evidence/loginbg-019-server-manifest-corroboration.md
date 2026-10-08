# Login Background Server-Manifest Corroboration

Evidence bundle created earlier in the project:

- local artifact: `battlecats-server-manifest-index.zip`
- bundle SHA-256:
  `4064ae373d185d5e6c95495312e477546fba652d315c022c4142d0109e65e451`
- `server-manifest-index.json`
  - size: 3,906,053 bytes
  - SHA-256:
    `4f8a52ffd8978b28f791b089a3ea9fd3fda34313c798d498717acfb3ec9c3043`

Exact indexed row:

```json
{"source":"current-x","family":"XImageServer","name":"loginbg_019.png"}
```

This corroborates the exact local `DailyLoginEventData.csv` comeback row 949,
whose header background field is 19, and the exact native formatter
`loginbg_%03d.png`.

What this proves:

- the name `loginbg_019.png` is present in the current-X server image manifest;
- the original runtime has a formatter for that asset family;
- the local comeback template 949 selects background id 19.

What this does **not** prove:

- that the image payload itself has been imported into the final offline build;
- that every historical/current server manifestation of the comeback event uses
  identical reward quantities.

Shipping visual completeness therefore still requires the exact image payload
to be present locally or imported with provenance. The manifest-name evidence
alone is not treated as the asset body.
