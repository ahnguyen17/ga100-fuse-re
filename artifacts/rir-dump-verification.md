# RIR + Main-Array Fuse Dump — OUR CARDS (executed Oct 2 2026)

Tool: `~/cmpunlocker/tools/fuse_rir_dump.py` (committed; CMD_READ-only, DEBUGCTRL safety
protocol, JSON output). Run: `echo '<pw>' | sudo -S python3 tools/fuse_rir_dump.py`.
Raw: `references/fuse-dump-oct2-bothcards.json` + `-output.txt`. (Hermes security gate
requires user approval for this invocation pattern — Andy approved Oct 2.)

## Evidence correction: only RIR read substitution and FF address collision verify

**Read `ff-offline-decoding.md` before using the original conclusions below.** Row287 is chain2/off39 and row288 chain2/off47, but this does NOT establish Gen3 bit identity, absent-block defaults, hardware last-writer precedence, collateral effects, or safety of removing the original row18 substitution. Claims that the entire story or safety argument verifies are overstated. Local gpcprobe uses Gen3 address0x820580, not0x820250. Source JSON rows8/9 differ; only rows0–7 are identical.

## Original observations and interpretation (qualifications above apply)

1. **RIR macro (Hynix 81:00.0): slot 15 (row 7 lo) = 0x0923 — EXACT match to their claim.**
   Decode under their 14-bit layout: addr 584 = row 18 bit 8, data=1, en=1. Other 15 slots
   0xFFFF ("spent"). DEBUGCTRL readback 0x0 after both cards — safety protocol worked.
2. **Substitution provably ACTIVE in read path:** Hynix main row 18 reads 0xfcc805f9, row 19
   (unsubstituted twin) 0xfcc804f9 — differ in exactly bit 8. Samsung card: rows 18/19 both
   0xfcc804f9 and ALL RIR slots 0x0000 (no live record, no substitution). The redirect
   mechanism is real and observable.
3. **Redirect target row 287 confirmed:** Hynix row 287 = 0x078209c2 decodes (offset=bits[12:6])
   as offset **39**; forcing bit 9 → 0x07820bc2 = offset **47**; row 288 (0x00590bc2) already
   owns offset 47 → later last-writer-wins row covers the orphaned block. Their safety
   argument holds on OUR die. Adjacent rows 285-289 walk offsets 37,38,39,47,77 — consistent
   with a chain writing sequential fields.
4. **BURN LIST CORRECTION (definitive):** 0x0923 → addr 9193 requires burning record bits
   **[2,7,9,10,15] → target 0x8FA7** (data bit stays 1; enable stays 1). Their published list
   [2,6,7,10,12,13] decodes to 0x3DE7 = addr 3961 = row 123 bit 25 — a COMPLETELY different
   redirect into the hard-fuse region. Their summary is wrong; anyone burning their list
   would not get the Gen3 divert.

## Card differences (Hynix A vs Samsung B, hard-fuse region ≤221)

- SKU-defining rows: 10/11 (0x168 vs 0x90), 12/13 (mem geometry straps), 14/15, 26-33
  (FBPA/FBP masks — Samsung 28/29=0xc30000c3 = the DISABLE==DEFECTIVE 0x24-family pattern),
  49-50 (PLL/clock bins), 55-86 (per-die random — calibration/UID class).
- No 0x20c2/0x2082 literal anywhere in the main array (DEVID lives in FF chain 2, per the
  external group — not in a scannable aligned position).
- Rows 0-9 byte-identical across cards (0x53557c3d, 0x23de954c, ...) — likely shared SKU
  header/security rows.
- Rows 488-507 nonzero on both (their "FPF/Firmware Protection" region — the rows that DID
  burn on PG199).

## Status of the Gen3 permanent path (as of Oct 2)

FEASIBLE on paper for the Hynix card: slot inventory matches, target row cover exists,
correct burn list derived. STILL NOT RECOMMENDED without: (1) burn-method verification on a
sacrificial die (PG199 showed CMD_WRITE can accept while the analog burn silently fails —
readback-verify + no-retry rule); (2) XVE override + CYA_0 second-disable handling (their
method 1+3 combo); (3) acceptance that PR#37 documented off-the-bus failure when forcing
8 GT/s while the fuse still senses set — the FF orphaning must actually clear the OPT shadow,
verifiable READ-ONLY after burn via our gpcprobe (OPT_DISABLE_GEN3_SPEED 0x820250 → 0).
Payoff: Gen3 x4 ≈ 3.9 GB/s theoretical vs 1.5 today (model-load latency, not decode).
Samsung card: RIR macro all-zeros — different state entirely, redirect recipe does not
transfer; treat as no-path until its slot semantics are understood.
