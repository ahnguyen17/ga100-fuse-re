# 64→96 GB Path via FF Append (derived Oct 2 2026, post-decode)

**The lever astra's decode exposed:** Hynix OPT_FBP_DISABLE lives in FF chain 1, offset 19
(row 280, data 0x4290 → mask 0x852 = bits 1,4,6,11). FBP 6,11 are DEFECTIVE (hard rows
26/27, unrevivable), but **bits 1,4 are disable-only** — and FF records are APPENDABLE
(last-writer-wins, rows 222–331, 39 blank rows available above row 280 on our dump).

**Derived append record (python-verified):** `0x420004C1` at any blank row >280
(chain=1, offset=19, data=0x4200) → post-append OPT_FBP_DISABLE shadow = 0x840,
clearing exactly bits 1 and 4. 16→20 active FBPAs (5120-bit, same bus width class as the
Samsung 40GB geometry), theoretical 96 GiB (2 full + 4 half stacks of 16 Gb Hynix dies).

**Three gates before this is real (all currently open):**
1. **FF-pool analog write** — external group's PG199 card: FF row write accepted digitally,
   analog burn FAILED (FPF rows burned fine). No positive FF-pool burn evidence anywhere.
   Same verification problem as the RIR redirect, minus even a spent-slot structure to probe.
2. **96 GB geometry values** — CFG1/LMR for 20-FBPA/16Gb-die config unknown; current unlock
   uses CFG1 0x02779000 (A100-80GB value, 4096-bit). Needs jonpry-class FB-geometry RE or a
   community source. targetFbBytes would be 0x1800000000.
3. **FB-Falcon boot retrain of revived channels** — plausible that boot trains any
   non-disabled channel automatically (mask is consumed at HBM init), but unproven; our Aug
   notes flagged "boot-time channel retrain" as a separate wall. It was written assuming the
   mask could never change — needs re-examination, not assumption either way.

**Ordering vs the Gen3 redirect:** HIGHER payoff (+32 GB permanent VRAM vs transfer speed),
SIMILAR risk class (one-way OTP, unvalidated burn mechanism, could brick the best card),
MORE unknowns (geometry + retrain on top of the burn). Neither is go while the burn
mechanism is unproven.

**Deterministic alternative:** second Hynix 8GB card (~$400-600) → +64 GB with the existing,
proven unlock. Strictly dominates on risk; loses only if 96 GB monolithic capacity (single
context > 64 GB) is the specific need.

Volatile paths all confirmed dead earlier: CTRL_OPT override fused off (FUSE_EN_SW_OVERRIDE=0,
all 170HX), CFG1/LMR runtime writes value-gated at the port (Aug 16 proof).

---

## CORRECTION (2026-10-03): target is 80 GiB, not 96 GiB

Capacity model error in the original note: FBP 1,4 = 2 FBP × 2 FBPA × 4 GiB = **+16 GiB →
80 GiB total** (10 FBP, 20 FBPA — the same FBPA count as the Samsung 40 GB card, at 4 GiB/FBPA
for 16 Gb dies). The "96 GiB" figure required reviving FBP 6,11 which are DEFECTIVE (hard
rows 26/27) — dead silicon, not disable-only. The append record itself (0x420004C1, clearing
disable bits 1,4 → mask 0x840) is unchanged. Geometry follow-up: whether a 20-FBPA Hynix
config keeps CFG1 0x02779000 with only LMR adjustment is under analysis.

## Addendum 2 (2026-10-03): VRAM sweep — 80 GiB confirmed, append recipe INCOMPLETE, RIR-for-VRAM dead

Full sweep: `artifacts/vram-sweep.md`. Three material findings:

1. **Capacity: 80 GiB confirmed** (10 FBP × 20 FBPA × 4 GiB). The 96 GiB figure required
   reviving defective FBP 6,11 — dead silicon.
2. **⚠️ The published append `0x420004C1` is NOT a complete revival recipe.** Offline scanning
   found THREE separate 24-bit expanded partition-disable masks in chain 1 (bit-fields at
   offsets 5:3, 6:11, 19:15), each reading `0xc0330c` (Hynix) / `0x000c30` (Samsung) and each
   independently reproducing the cards' expanded FBP masks. The append changes only the
   (1,19) field and leaves all three untouched. Until those masks are shown to be derived
   rather than independent enables, no single-record append can claim FBPA revival.
3. **RIR-for-VRAM: definitively dead.** All 2,048 addresses reachable from the Hynix slot
   `0x0923` were enumerated against the actual FF pool — zero can change or orphan
   chain-1/offset-19. (General note: "RIR only forces ones" is false for a *blank* slot with
   DATA=0, but the Samsung card has no disable-only FBP to reclaim anyway.)

**Geometry solved on paper:** LMR encodes `MiB = MAG[9:4] << SCALE[3:0]`; the coherent
Hynix 20-FBPA pair is `CFG1=0x02779000` + `LMR=0x28B` + `targetFbBytes=0x1400000000` —
identical to the A100 PCIe 80 GB pair. The open problem is enabling/training the partitions,
not the constants.

No volatile path survives (CTRL overrides fused off; runtime CFG1/LMR port-gated; no
host-injectable FF shadow cache; IFF-skip unsupported; unknown chains are research, not
transport). Ranked paths and the single evidence that would unlock each: see the sweep.
