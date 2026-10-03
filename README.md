# ga100-fuse-re

GA100 (NVIDIA CMP 170HX) fuse architecture reverse-engineering — field data, decoded maps,
and derived recipes from a single two-card rig (ASUS Z10PE-D8 WS, C612/Haswell-EP).
Cards: `10de:20c2` (8 GB Hynix → 64 GB) and `10de:2082` (10 GB Samsung → 40 GB),
unlocked via [cmpunlocker](https://github.com/amoghmunikote/cmpunlocker), nvidia-open 610.43.03.

## Headline results

1. **FF-pool instruction layout — decoded and anchored** (`FINDINGS.md` §1):
   `chain = word[5:0]`, `offset = word[15:6]`, `data = word[31:16]`.
   Anchored against independent OPT-shadow reads: DEVIDA/B (`0x20c2`/`0x2082`),
   OPT_FBP_DISABLE (`0x852`/`0x24`), OPT_GPC_DISABLE (`0x23`). 145 records across both SKUs,
   lossless re-encode. Full map: `artifacts/ga100-ff-instructions-both-skus.csv`.
2. **RIR macro verified** (`FINDINGS.md` §2): slot 15 = `0x0923`, substitution live in the
   read path (row 18 bit 8 provably forced). Redirect target row 287 offset 39→47 with
   last-writer-wins cover confirmed on our die.
3. **⚠️ Burn-list erratum** (`FINDINGS.md` §2): a circulated RIR burn list
   `[2,6,7,10,12,13]` is WRONG — it decodes to a different redirect (row 123). Correct bits:
   `[2,7,9,10,15]` → `0x8FA7`. Do not burn the wrong list.
4. **64 → 96 GB recipe** (Hynix 8 GB cards, FBP mask `0x852`) — FF append `0x420004C1`
   (chain 1 / offset 19) clears disable bits 1,4 → +32 GB theoretical. Gates and risks:
   `artifacts/fbp-append-96gb-path.md`, burn-readiness analysis:
   `artifacts/rir-burn-readiness-gates.md` (current verdict: NO-GO on a working card until
   FF/RIR analog-write evidence exists).

## Contents

- `FINDINGS.md` — the full 2026-10-02 field report (decode, verification, corrections, trade offer)
- `FIELD-DATA-GEN2-AUG-SEP.md` — PCIe Gen2 boot-window root cause + gpcprobe fuse map (Aug–Sep 2026)
- `artifacts/` — raw 512-row dumps (both SKUs), decoded instruction CSV, decode report +
  analysis script, external intel archive (verbatim + analysis), derived-path memos
- `tools/fuse_rir_dump.py` — read-only fuse/RIR dump tool (CMD_READ only; DEBUGCTRL safety
  protocol with readback verification). **Read-only by construction — it cannot burn fuses.**

## Safety

Everything in this repo was obtained with read-only register commands. The burn recipes are
*derived, not tested* — the repo publishes them for verification and trade against primary
burn evidence, not as working procedures. OTP is irreversible; see
`artifacts/rir-burn-readiness-gates.md` for the failure-mode analysis before touching anything.

## Conventions

Findings attributed by date, no individuals named. Single-observation claims say so.
Measurements are instrument-backed; register reads quoted raw.
