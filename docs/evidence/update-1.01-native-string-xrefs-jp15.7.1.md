# JP15.7.1 original ARM64 source-file xrefs (read-only, NOT safe hook targets)

Source: owner JP15.7.1 libnative-lib.so, SHA256 333d2974ab2ff881fd70087fd62dea7d12d82addbc55cab2f2a675ad67e3a7e2. GNU Build ID 8cb3815648eb9642da10bfb039d71bff7a3519bd.

## Static observations only

ELF .rodata begins virtual 0x18F2C0; .text begins virtual 0x317370. An AArch64 ADRP+ADD pattern scanner located these references to literal strings. The addresses below are instruction sites (not function starts, not hook targets):

| String in owned binary | String address | ADRP site | ADD site |
| --- | --- | --- | --- |
| DataLocal.pack | 0x1926CD | 0x7157E8 | 0x7157EC |
| DownloadLocal.list | 0x1A151F | 0x71C6F8 | 0x71C6FC |
| DownloadLocal.pack | 0x1AB6E4 | 0x71C714 | 0x71C718 |
| t_unit.csv | 0x19C580 | 0x8A3678 | 0x8A367C |
| enemyCastleData0.csv | 0x1A210E | 0x553348 | 0x55334C |

DataLocal.list literal at 0x1A1419 exists in the ELF but simple direct ADRP+ADD pattern did not identify a matching reference, likely because the compiler uses a different constant-load sequence.

The DownloadLocal pair appears together in code handling pack initialization; t_unit.csv is referenced in a generic original CSV load sequence. Neither observation proves that DownloadLocal overrides will win over DataLocal for unit289.csv or unit703.csv, nor does it identify original base damage or castle HP debit functions.

LLVM disassembler labels preceding stripped code as if within a large JNI function, which is not reliable evidence of internal function boundaries. No offsets or guessed battle hooks should be deployed based only on this read-only receipt.

## Next acceptance

Use a disposable original-version research package and known-good original UI to trace lookup of two only form CSVs. Resolve an actual typed castle-target HP debit seam and pre-trait base damage seam, verify the exact original behavior when native feature bit7 is OFF, and only then attach the native policy. Reject destructive reinstall and preserve all owner save progression.